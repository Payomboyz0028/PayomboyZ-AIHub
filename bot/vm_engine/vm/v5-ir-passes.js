// language: JavaScript, file: v5-ir-passes.js, target: Node.js ESM
// Sentinel v5.3 APEX IR Transformation Pipeline:
// Per-Proto Register Permutation, Micro-Op Splitting, Unrelated Handler Merging,
// Numeric Constant Synthesis, IR State-Machine Flattening, Runtime Anti-SCCP Opaque Branches,
// Dual-Mode Partitioning, Universal Once-Per-Block Decryption + Path-Dependent Rolling Key (_st),
// Dynamic Shifted ISA (_rb/_kb) & 128-bit ARX Key Vector

import { V5Op, V5_OPCODE_COUNT, RK_OFFSET } from "./bytecode.js";
import { createMbaCodec } from "./v5-mba.js";

const COND_SKIP_OPS = new Set([
    V5Op.EQ, V5Op.LT, V5Op.LE, V5Op.TEST, V5Op.TESTSET, V5Op.TFORLOOP,
]);

const TERM_OPS = new Set([
    V5Op.JMP, V5Op.JMP_V2, V5Op.RETURN, V5Op.RETURN_V2, V5Op.TAILCALL, V5Op.FORPREP,
    V5Op.OP_MODE_SWITCH, V5Op.F_LOADK_RET, V5Op.F_MOVE_RET,
]);

const MERGE_GROUPS = [
    { op: V5Op.M_TAB_SUB_NOT, members: [V5Op.GETTABLE, V5Op.SUB, V5Op.NOT] },
    { op: V5Op.M_SET_ADD_LEN, members: [V5Op.SETTABLE, V5Op.ADD, V5Op.LEN] },
    { op: V5Op.M_ENV_MOV_UNM, members: [V5Op.GETGLOBAL, V5Op.MOVE, V5Op.UNM] },
    { op: V5Op.M_LDK_MUL_SGL, members: [V5Op.LOADK, V5Op.MUL, V5Op.SETGLOBAL] },
    { op: V5Op.M_DIV_MOD_GUP, members: [V5Op.DIV, V5Op.MOD, V5Op.GETUPVAL] },
    { op: V5Op.M_CAT_POW_SUP, members: [V5Op.CONCAT, V5Op.POW, V5Op.IDIV, V5Op.SETUPVAL] },
];

const MEMBER_TO_MERGE = new Map();
for (const g of MERGE_GROUPS) {
    g.members.forEach((m, idx) => MEMBER_TO_MERGE.set(m, { mergedOp: g.op, subIdx: idx }));
}

function redirectRefs(instrs, redirect) {
    if (redirect.size === 0) return;
    for (const ins of instrs) {
        if (ins.targetIns && redirect.has(ins.targetIns)) {
            ins.targetIns = redirect.get(ins.targetIns);
        }
        if (ins._skipIns && redirect.has(ins._skipIns)) {
            ins._skipIns = redirect.get(ins._skipIns);
        }
    }
}

function addProtoConst(proto, value) {
    const idx = proto.K.indexOf(value);
    if (idx >= 0) return idx;
    proto.K.push(value);
    return proto.K.length - 1;
}

/**
 * Convert raw 4-int flat chunk.code into linked instruction list, remap RK offsets, & resolve jump targets.
 */
function decodeRawInstrs(code, rkOffset = RK_OFFSET) {
    const remapRK = (v) => (v >= RK_OFFSET ? rkOffset + (v - RK_OFFSET) : v);
    const n = Math.floor(code.length / 4);
    const instrs = new Array(n);
    for (let i = 0; i < n; i++) {
        const b = i * 4;
        const op = code[b] | 0;
        let A = code[b + 1] | 0;
        let B = code[b + 2] | 0;
        let C = code[b + 3] | 0;
        if (op === V5Op.GETTABLE || op === V5Op.SELF) {
            C = remapRK(C);
        } else if (op === V5Op.SETTABLE || op === V5Op.ADD || op === V5Op.SUB || op === V5Op.MUL ||
            op === V5Op.DIV || op === V5Op.MOD || op === V5Op.POW || op === V5Op.IDIV ||
            op === V5Op.EQ || op === V5Op.LT || op === V5Op.LE) {
            B = remapRK(B);
            C = remapRK(C);
        }
        instrs[i] = {
            op, A, B, C, D: 0,
            targetIdx: -1,
            targetIns: null,
            noMba: false,
        };
    }
    const END_MARKER = { isEnd: true };
    for (let i = 0; i < n; i++) {
        const ins = instrs[i];
        if (ins.op === V5Op.JMP || ins.op === V5Op.FORPREP || ins.op === V5Op.FORLOOP) {
            const t = i + 1 + ins.B;
            ins.targetIdx = t;
            ins.targetIns = (t >= 0 && t < n) ? instrs[t] : END_MARKER;
        } else if ((ins.op === V5Op.LOADBOOL && ins.C !== 0) || COND_SKIP_OPS.has(ins.op)) {
            ins._skipIns = (i + 2 < n) ? instrs[i + 2] : END_MARKER;
        }
    }
    return { instrs, END_MARKER };
}

/**
 * Compute Set of instruction objects that are targets of jumps or skip instructions.
 */
function computeProtectedTargets(instrs) {
    const protectedSet = new Set();
    for (let i = 0; i < instrs.length; i++) {
        const ins = instrs[i];
        if (ins.targetIns && !ins.targetIns.isEnd) {
            protectedSet.add(ins.targetIns);
        }
        if (COND_SKIP_OPS.has(ins.op) && i + 2 < instrs.length) {
            protectedSet.add(instrs[i + 2]);
        }
        if (ins.op === V5Op.LOADBOOL && ins.C !== 0 && i + 2 < instrs.length) {
            protectedSet.add(instrs[i + 2]);
        }
    }
    return protectedSet;
}

/**
 * Collapse LOADKX + EXTRAARG into a single 32-bit LOADK(A, ki, 0) & rewire any incoming targets.
 */
function collapseLoadKX(instrs) {
    const redirect = new Map();
    const out = [];
    for (let i = 0; i < instrs.length; i++) {
        const ins = instrs[i];
        if (ins.op === V5Op.LOADKX && i + 1 < instrs.length && instrs[i + 1].op === V5Op.EXTRAARG) {
            const next = instrs[i + 1];
            const fused = {
                op: V5Op.LOADK,
                A: ins.A,
                B: next.A,
                C: 0,
                D: 0,
                targetIdx: -1,
                targetIns: null,
                noMba: false,
            };
            redirect.set(ins, fused);
            redirect.set(next, fused);
            out.push(fused);
            i++;
        } else {
            out.push(ins);
        }
    }
    for (const ins of out) {
        if (ins.targetIns && redirect.has(ins.targetIns)) {
            ins.targetIns = redirect.get(ins.targetIns);
        }
        if (ins._skipIns && redirect.has(ins._skipIns)) {
            ins._skipIns = redirect.get(ins._skipIns);
        }
    }
    return out;
}

/**
 * Compiler-level IR Numeric Constant Synthesis (L2/L3 non-hot protos):
 * Rewrites eligible integer LOADKs into arithmetic chains (P+Q, P-Q, Q*M+R) and scrubs orphaned literals.
 */
function irTransformNumericConstants(instrs, proto, ctx, rng, prob) {
    if (!proto || !Array.isArray(proto.K) || instrs.length === 0) return instrs;
    const redirect = new Map();
    const replacedKIndices = new Set();
    const out = [];

    for (let i = 0; i < instrs.length; i++) {
        const ins = instrs[i];
        const prevSkip = i > 0 && (COND_SKIP_OPS.has(instrs[i - 1].op) || (instrs[i - 1].op === V5Op.LOADBOOL && instrs[i - 1].C !== 0));
        if (ins.op === V5Op.LOADK && !prevSkip && (proto.K.length + 6 < ctx.rkOffset) && rng() < prob) {
            const v = proto.K[ins.B];
            if (typeof v === "number" && Number.isSafeInteger(v) && !Object.is(v, -0) && Math.abs(v) <= 0x7FFFFFFF && v !== 0 && v !== 1) {
                const form = Math.floor(rng() * 3);
                let seq = null;
                if (form === 0) {
                    const p = 11 + Math.floor(rng() * 50000);
                    const q = v - p;
                    if (Number.isSafeInteger(q)) {
                        const kP = addProtoConst(proto, p);
                        const kQ = addProtoConst(proto, q);
                        if (kP < ctx.rkOffset && kQ < ctx.rkOffset) {
                            seq = [
                                { op: V5Op.LOADK, A: ins.A, B: kP, C: 0, D: 0, targetIdx: -1, targetIns: null, noMba: false },
                                { op: V5Op.S_ADD_K, A: ins.A, B: ins.A, C: kQ, D: 0, targetIdx: -1, targetIns: null, noMba: false },
                            ];
                        }
                    }
                } else if (form === 1) {
                    const q = 17 + Math.floor(rng() * 50000);
                    const p = v + q;
                    if (Number.isSafeInteger(p)) {
                        const kP = addProtoConst(proto, p);
                        const kQ = addProtoConst(proto, q);
                        if (kP < ctx.rkOffset && kQ < ctx.rkOffset) {
                            seq = [
                                { op: V5Op.LOADK, A: ins.A, B: kP, C: 0, D: 0, targetIdx: -1, targetIns: null, noMba: false },
                                { op: V5Op.S_SUB_K, A: ins.A, B: ins.A, C: kQ, D: 0, targetIdx: -1, targetIns: null, noMba: false },
                            ];
                        }
                    }
                } else {
                    const m = 3 + Math.floor(rng() * 94);
                    const r = v % m;
                    const q = (v - r) / m;
                    if (Number.isSafeInteger(q) && q * m + r === v) {
                        const kQ = addProtoConst(proto, q);
                        const kM = addProtoConst(proto, m);
                        const kR = addProtoConst(proto, r);
                        if (kQ < ctx.rkOffset && kM < ctx.rkOffset && kR < ctx.rkOffset) {
                            seq = [
                                { op: V5Op.LOADK, A: ins.A, B: kQ, C: 0, D: 0, targetIdx: -1, targetIns: null, noMba: false },
                                { op: V5Op.S_MUL_K, A: ins.A, B: ins.A, C: kM, D: 0, targetIdx: -1, targetIns: null, noMba: false },
                                { op: V5Op.S_ADD_K, A: ins.A, B: ins.A, C: kR, D: 0, targetIdx: -1, targetIns: null, noMba: false },
                            ];
                        }
                    }
                }
                if (seq && proto.K.length < ctx.rkOffset) {
                    replacedKIndices.add(ins.B);
                    redirect.set(ins, seq[0]);
                    for (const s of seq) out.push(s);
                    continue;
                }
            }
        }
        out.push(ins);
    }

    for (const ins of out) {
        if (ins.targetIns && redirect.has(ins.targetIns)) ins.targetIns = redirect.get(ins.targetIns);
        if (ins._skipIns && redirect.has(ins._skipIns)) ins._skipIns = redirect.get(ins._skipIns);
    }

    // Check which original replaced K indices are still referenced anywhere else before scrubbing
    if (replacedKIndices.size > 0) {
        const stillUsed = new Set();
        for (const ins of out) {
            if (ins.op === V5Op.LOADK || ins.op === V5Op.GETGLOBAL || ins.op === V5Op.SETGLOBAL) {
                stillUsed.add(ins.B);
            } else if (ins.op === V5Op.S_GETFIELD_K || ins.op === V5Op.S_ADD_K || ins.op === V5Op.S_SUB_K || ins.op === V5Op.S_MUL_K || ins.op === V5Op.S_MOD_K) {
                stillUsed.add(ins.C);
            } else if (ins.op === V5Op.S_SETFIELD_K) {
                stillUsed.add(ins.B);
                if (ins.C >= ctx.rkOffset) stillUsed.add(ins.C - ctx.rkOffset);
            } else {
                if (ins.B >= ctx.rkOffset) stillUsed.add(ins.B - ctx.rkOffset);
                if (ins.C >= ctx.rkOffset) stillUsed.add(ins.C - ctx.rkOffset);
            }
        }
        for (const kIdx of replacedKIndices) {
            if (!stillUsed.has(kIdx)) {
                proto.K[kIdx] = 10000 + Math.floor(rng() * 900000);
            }
        }
    }
    return out;
}

/**
 * Pass 1: Compact Superoperator Fusion + Opcode Specialization.
 * Preserves jump targets cleanly because fused instructions replace sequences in the compacted array.
 */
function fuseAndSpecialize(instrs, rkOffset = RK_OFFSET) {
    const protectedSet = computeProtectedTargets(instrs);
    const redirect = new Map();
    const out = [];
    const canFuse = (start, len) => {
        if (start + len > instrs.length) return false;
        for (let k = 1; k < len; k++) {
            if (protectedSet.has(instrs[start + k])) return false;
        }
        return true;
    };

    for (let i = 0; i < instrs.length; i++) {
        const i0 = instrs[i];
        const i1 = i + 1 < instrs.length ? instrs[i + 1] : null;
        const i2 = i + 2 < instrs.length ? instrs[i + 2] : null;

        // 1. TEST/EQ/LT/LE/TESTSET/TFORLOOP + JMP (100% fused when adjacent & target-safe)
        if (i0.op === V5Op.TEST && canFuse(i, 2) && i1.op === V5Op.JMP) {
            const f = { op: V5Op.F_TEST_JMP, A: i0.A, B: 0, C: i0.C, D: 0, targetIns: i1.targetIns, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }
        if (i0.op === V5Op.EQ && canFuse(i, 2) && i1.op === V5Op.JMP) {
            const f = { op: V5Op.F_EQ_JMP, A: i0.A, B: i0.B, C: i0.C, D: 0, targetIns: i1.targetIns, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }
        if (i0.op === V5Op.LT && canFuse(i, 2) && i1.op === V5Op.JMP) {
            const f = { op: V5Op.F_LT_JMP, A: i0.A, B: i0.B, C: i0.C, D: 0, targetIns: i1.targetIns, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }
        if (i0.op === V5Op.LE && canFuse(i, 2) && i1.op === V5Op.JMP) {
            const f = { op: V5Op.F_LE_JMP, A: i0.A, B: i0.B, C: i0.C, D: 0, targetIns: i1.targetIns, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }
        if (i0.op === V5Op.TESTSET && canFuse(i, 2) && i1.op === V5Op.JMP) {
            const f = { op: V5Op.F_TESTSET_JMP, A: i0.A, B: i0.B, C: i0.C, D: 0, targetIns: i1.targetIns, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }
        if (i0.op === V5Op.TFORLOOP && canFuse(i, 2) && i1.op === V5Op.JMP) {
            const f = { op: V5Op.F_TFORLOOP_JMP, A: i0.A, B: 0, C: i0.C, D: 0, targetIns: i1.targetIns, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }

        // 2. GETGLOBAL + GETTABLE + CALL (safe temp from MemberExpression)
        if (i0.op === V5Op.GETGLOBAL && canFuse(i, 3) && i1.op === V5Op.GETTABLE && i2.op === V5Op.CALL &&
            i1.B === i0.A && i2.A === i1.A && i2.B <= 65535 && i2.C <= 65535) {
            const f = {
                op: V5Op.F_GGET_CALL,
                A: i2.A,
                B: i0.B,
                C: i1.C,
                D: ((i2.B & 0xFFFF) * 65536) + (i2.C & 0xFFFF),
                targetIns: null, targetIdx: -1, noMba: false,
            };
            redirect.set(i0, f); redirect.set(i1, f); redirect.set(i2, f);
            out.push(f); i += 2; continue;
        }

        // 3. SELF + CALL
        if (i0.op === V5Op.SELF && canFuse(i, 2) && i1.op === V5Op.CALL &&
            i1.A === i0.A && i1.B <= 65535 && i1.C <= 65535) {
            const f = {
                op: V5Op.F_SELF_CALL,
                A: i0.A,
                B: i0.B,
                C: i0.C,
                D: ((i1.B & 0xFFFF) * 65536) + (i1.C & 0xFFFF),
                targetIns: null, targetIdx: -1, noMba: false,
            };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }

        // 4. GETGLOBAL + GETTABLE -> F_GGET
        if (i0.op === V5Op.GETGLOBAL && canFuse(i, 2) && i1.op === V5Op.GETTABLE && i1.B === i0.A) {
            const f = { op: V5Op.F_GGET, A: i0.A, B: i0.B, C: i1.A, D: i1.C, targetIns: null, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }

        // 5. GETUPVAL + GETTABLE -> S_UPVAL_GET
        if (i0.op === V5Op.GETUPVAL && canFuse(i, 2) && i1.op === V5Op.GETTABLE && i1.B === i0.A) {
            const f = { op: V5Op.S_UPVAL_GET, A: i0.A, B: i0.B, C: i1.A, D: i1.C, targetIns: null, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }

        // 6. LOADK + RETURN (single return)
        if (i0.op === V5Op.LOADK && canFuse(i, 2) && i1.op === V5Op.RETURN && i1.A === i0.A && i1.B === 2) {
            const f = { op: V5Op.F_LOADK_RET, A: i0.A, B: i0.B, C: 0, D: 0, targetIns: null, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }

        // 7. MOVE + RETURN
        if (i0.op === V5Op.MOVE && canFuse(i, 2) && i1.op === V5Op.RETURN) {
            const f = { op: V5Op.F_MOVE_RET, A: i0.A, B: i0.B, C: i1.A, D: i1.B, targetIns: null, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }

        // 8. LOADK + LOADK -> F_LOADKK
        if (i0.op === V5Op.LOADK && canFuse(i, 2) && i1.op === V5Op.LOADK) {
            const f = { op: V5Op.F_LOADKK, A: i0.A, B: i0.B, C: i1.A, D: i1.B, targetIns: null, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }

        // 9. MOVE + MOVE -> F_MOVE_MOVE
        if (i0.op === V5Op.MOVE && canFuse(i, 2) && i1.op === V5Op.MOVE) {
            const f = { op: V5Op.F_MOVE_MOVE, A: i0.A, B: i0.B, C: i1.A, D: i1.B, targetIns: null, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }

        // 9b. NEWTABLE(A) + SETTABLE(A, K[B], RK(C)) -> F_NEWTAB_SET (safe when B >= rkOffset)
        if (i0.op === V5Op.NEWTABLE && canFuse(i, 2) && i1.op === V5Op.SETTABLE && i1.A === i0.A && i1.B >= rkOffset && i1.C !== i0.A) {
            const f = { op: V5Op.F_NEWTAB_SET, A: i0.A, B: i1.B - rkOffset, C: i1.C, D: 0, targetIns: null, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }

        // 9c. GETGLOBAL(tmp, K[B]) + SETTABLE(tmp, K[C], RK(val)) -> F_GGET_SET
        if (i0.op === V5Op.GETGLOBAL && canFuse(i, 2) && i1.op === V5Op.SETTABLE && i1.A === i0.A && i1.B >= rkOffset && i1.C !== i0.A) {
            const f = { op: V5Op.F_GGET_SET, A: i1.C, B: i0.B, C: i1.B - rkOffset, D: i0.A, targetIns: null, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }

        // 9d. LOADK(A+1, K[B]) + CALL(A, 2, 2) -> F_LOADK_CALL1 / CALL(A, 2, 1) -> F_LOADK_CALL1_VOID
        if (i0.op === V5Op.LOADK && canFuse(i, 2) && i1.op === V5Op.CALL && i0.A === i1.A + 1 && i1.B === 2 && (i1.C === 2 || i1.C === 1)) {
            const fOp = i1.C === 2 ? V5Op.F_LOADK_CALL1 : V5Op.F_LOADK_CALL1_VOID;
            const f = { op: fOp, A: i1.A, B: i0.B, C: 0, D: 0, targetIns: null, targetIdx: -1, noMba: false };
            redirect.set(i0, f); redirect.set(i1, f);
            out.push(f); i += 1; continue;
        }

        // 10. Specialized single ops (note: keep skip pairs untouched if preceded by non-fused skip)
        const prevSkip = i > 0 && (COND_SKIP_OPS.has(instrs[i - 1].op) || (instrs[i - 1].op === V5Op.LOADBOOL && instrs[i - 1].C !== 0));
        if (!prevSkip) {
            if (i0.op === V5Op.CALL && i0.C === 2 && (i0.B === 1 || i0.B === 2 || i0.B === 3)) {
                i0.op = i0.B === 1 ? V5Op.S_CALL0 : (i0.B === 2 ? V5Op.S_CALL1 : V5Op.S_CALL2);
                i0.B = 0; i0.C = 0;
            } else if (i0.op === V5Op.CALL && i0.C === 2 && i0.B === 4) {
                i0.op = V5Op.S_CALL3;
                i0.B = 0; i0.C = 0;
            } else if (i0.op === V5Op.CALL && i0.C === 1 && (i0.B === 1 || i0.B === 2 || i0.B === 3)) {
                i0.op = i0.B === 1 ? V5Op.S_CALL0_VOID : (i0.B === 2 ? V5Op.S_CALL1_VOID : V5Op.S_CALL2_VOID);
                i0.B = 0; i0.C = 0;
            } else if (i0.op === V5Op.GETTABLE && i0.C >= rkOffset) {
                i0.op = V5Op.S_GETFIELD_K;
                i0.C = i0.C - rkOffset;
            } else if (i0.op === V5Op.SETTABLE && i0.B >= rkOffset) {
                i0.op = V5Op.S_SETFIELD_K;
                i0.B = i0.B - rkOffset;
            } else if (i0.op === V5Op.ADD && i0.B < rkOffset && i0.C >= rkOffset) {
                i0.op = V5Op.S_ADD_K;
                i0.C = i0.C - rkOffset;
            } else if (i0.op === V5Op.SUB && i0.B < rkOffset && i0.C >= rkOffset) {
                i0.op = V5Op.S_SUB_K;
                i0.C = i0.C - rkOffset;
            } else if (i0.op === V5Op.MUL && i0.B < rkOffset && i0.C >= rkOffset) {
                i0.op = V5Op.S_MUL_K;
                i0.C = i0.C - rkOffset;
            } else if (i0.op === V5Op.MOD && i0.B < rkOffset && i0.C >= rkOffset) {
                i0.op = V5Op.S_MOD_K;
                i0.C = i0.C - rkOffset;
            }
        }

        out.push(i0);
    }

    for (const ins of out) {
        if (ins.targetIns && redirect.has(ins.targetIns)) {
            ins.targetIns = redirect.get(ins.targetIns);
        }
        if (ins._skipIns && redirect.has(ins._skipIns)) {
            ins._skipIns = redirect.get(ins._skipIns);
        }
        // Convert any remaining relative pc+1 skips into explicit block jumps (safe under CFF & Dual-Mode)
        if (ins.op === V5Op.LOADBOOL && ins.C !== 0 && ins._skipIns) {
            ins.targetIns = ins._skipIns;
        } else if (ins.op === V5Op.EQ && ins._skipIns) {
            ins.op = V5Op.F_EQ_JMP;
            ins.A = ins.A ? 0 : 1;
            ins.targetIns = ins._skipIns;
        } else if (ins.op === V5Op.LT && ins._skipIns) {
            ins.op = V5Op.F_LT_JMP;
            ins.A = ins.A ? 0 : 1;
            ins.targetIns = ins._skipIns;
        } else if (ins.op === V5Op.LE && ins._skipIns) {
            ins.op = V5Op.F_LE_JMP;
            ins.A = ins.A ? 0 : 1;
            ins.targetIns = ins._skipIns;
        } else if (ins.op === V5Op.TEST && ins._skipIns) {
            ins.op = V5Op.F_TEST_JMP;
            ins.C = ins.C ? 0 : 1;
            ins.targetIns = ins._skipIns;
        } else if ((ins.op === V5Op.TESTSET || ins.op === V5Op.TFORLOOP) && ins._skipIns) {
            ins.targetIns = ins._skipIns;
        }
    }
    return out;
}

function permuteProtoRegisters(instrs, proto, ctx, rng) {
    if (!proto || instrs.length === 0) return instrs;

    // 1. Unroll multi-register LOADNIL(A, B > 0) before register analysis
    const unrolled = [];
    const redirect = new Map();
    for (const ins of instrs) {
        if (ins.op === V5Op.LOADNIL && ins.B > 0) {
            const count = ins.B + 1;
            let first = null;
            for (let k = 0; k < count; k++) {
                const sub = { op: V5Op.LOADNIL, A: ins.A + k, B: 0, C: 0, D: 0, targetIdx: -1, targetIns: null, noMba: false };
                if (k === 0) first = sub;
                unrolled.push(sub);
            }
            redirect.set(ins, first);
        } else {
            unrolled.push(ins);
        }
    }
    redirectRefs(unrolled, redirect);

    const rk = ctx.rkOffset;
    const pinned = new Set();
    let minOpenTop = Infinity;
    const maxR = Math.max(proto.maxRegs || 0, proto.nParams || 0);

    for (let r = 0; r < (proto.nParams || 0); r++) pinned.add(r);
    for (const cp of (proto.protos || [])) {
        for (const [isLoc, idx] of (cp.upvalues || [])) {
            if (isLoc === 1) pinned.add(idx);
        }
    }

    const pinRange = (lo, hi) => {
        for (let r = lo; r <= hi; r++) pinned.add(r);
    };

    for (const ins of unrolled) {
        switch (ins.op) {
            case V5Op.CLOSEUPVAL:
                pinned.add(ins.A);
                break;
            case V5Op.CALL:
            case V5Op.TAILCALL:
            case V5Op.PCALL:
            case V5Op.XPCALL:
                if (ins.B === 0 || ins.C === 0) {
                    minOpenTop = Math.min(minOpenTop, ins.A);
                } else {
                    const hi = ins.A + Math.max(ins.B - 1, ins.C - 2, ins.op === V5Op.XPCALL ? 1 : 0);
                    pinRange(ins.A, hi);
                }
                break;
            case V5Op.SETLIST:
                if (ins.B === 0) {
                    minOpenTop = Math.min(minOpenTop, ins.A);
                } else {
                    pinRange(ins.A, ins.A + ins.B);
                }
                break;
            case V5Op.VARARG:
                if (ins.B === 0) {
                    minOpenTop = Math.min(minOpenTop, ins.A);
                } else {
                    pinRange(ins.A, ins.A + Math.max(0, ins.B - 2));
                }
                break;
            case V5Op.RETURN:
                if (ins.B === 0) {
                    minOpenTop = Math.min(minOpenTop, ins.A);
                } else if (ins.B > 2) {
                    pinRange(ins.A, ins.A + ins.B - 2);
                }
                break;
            case V5Op.SELF:
                pinRange(ins.A, ins.A + 1);
                break;
            case V5Op.CONCAT:
                pinRange(ins.B, ins.C);
                break;
            case V5Op.FORPREP:
            case V5Op.FORLOOP:
                pinRange(ins.A, ins.A + 3);
                break;
            case V5Op.ITERPREP:
                pinRange(ins.A, ins.A + 2);
                break;
            case V5Op.TFORLOOP:
                pinRange(ins.A, ins.A + 2 + ins.C);
                break;
            default:
                break;
        }
    }

    if (minOpenTop < Infinity) {
        pinRange(minOpenTop, maxR);
    }

    const limitR = Math.min(maxR, minOpenTop);
    const unpinned = [];
    for (let r = 0; r < limitR; r++) {
        if (!pinned.has(r)) unpinned.push(r);
    }
    if (unpinned.length === 0) {
        proto.maxRegs = Math.max(proto.maxRegs || 0, maxR);
        return unrolled;
    }

    const candidates = [...unpinned];
    if (minOpenTop === Infinity && maxR + 8 < rk) {
        const extra = 2 + Math.floor(rng() * 4);
        for (let k = 0; k < extra; k++) candidates.push(maxR + k);
    }
    for (let i = candidates.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
    }

    const perm = new Map();
    unpinned.forEach((r, idx) => perm.set(r, candidates[idx]));
    const mapReg = (r) => (perm.has(r) ? perm.get(r) : r);
    const mapRK = (v) => (v < rk ? mapReg(v) : v);

    let peakReg = maxR;
    for (const v of perm.values()) {
        if (v + 1 > peakReg) peakReg = v + 1;
    }

    for (const ins of unrolled) {
        switch (ins.op) {
            case V5Op.LOADK:
            case V5Op.LOADKX:
            case V5Op.LOADNIL:
            case V5Op.LOADBOOL:
            case V5Op.GETGLOBAL:
            case V5Op.SETGLOBAL:
            case V5Op.NEWTABLE:
            case V5Op.TEST:
            case V5Op.CLOSURE:
            case V5Op.GETUPVAL:
            case V5Op.SETUPVAL:
            case V5Op.CLOSEUPVAL:
            case V5Op.VARARG:
            case V5Op.SETLIST:
            case V5Op.FORPREP:
            case V5Op.FORLOOP:
            case V5Op.ITERPREP:
            case V5Op.TFORLOOP:
            case V5Op.CALL:
            case V5Op.TAILCALL:
            case V5Op.PCALL:
            case V5Op.XPCALL:
                ins.A = mapReg(ins.A);
                break;
            case V5Op.RETURN:
                if (ins.B !== 1) ins.A = mapReg(ins.A);
                break;
            case V5Op.MOVE:
            case V5Op.UNM:
            case V5Op.NOT:
            case V5Op.LEN:
            case V5Op.TESTSET:
                ins.A = mapReg(ins.A);
                ins.B = mapReg(ins.B);
                break;
            case V5Op.GETTABLE:
            case V5Op.SELF:
                ins.A = mapReg(ins.A);
                ins.B = mapReg(ins.B);
                ins.C = mapRK(ins.C);
                break;
            case V5Op.SETTABLE:
                ins.A = mapReg(ins.A);
                ins.B = mapRK(ins.B);
                ins.C = mapRK(ins.C);
                break;
            case V5Op.ADD:
            case V5Op.SUB:
            case V5Op.MUL:
            case V5Op.DIV:
            case V5Op.MOD:
            case V5Op.POW:
            case V5Op.IDIV:
                ins.A = mapReg(ins.A);
                ins.B = mapRK(ins.B);
                ins.C = mapRK(ins.C);
                break;
            case V5Op.EQ:
            case V5Op.LT:
            case V5Op.LE:
                ins.B = mapRK(ins.B);
                ins.C = mapRK(ins.C);
                break;
            case V5Op.CONCAT:
                ins.A = mapReg(ins.A);
                ins.B = mapReg(ins.B);
                ins.C = mapReg(ins.C);
                break;
            default:
                break;
        }
    }

    proto.maxRegs = peakReg;
    return unrolled;
}

function splitComplexOps(instrs, proto, rng, prob = 0.85) {
    if (!proto || instrs.length === 0) return instrs;
    const redirect = new Map();
    const out = [];
    let rTmp = -1;
    let rFlag = -1;
    const getTmp = () => {
        if (rTmp < 0) {
            rTmp = proto.maxRegs;
            proto.maxRegs += 1;
        }
        return rTmp;
    };
    const getFlag = () => {
        if (rFlag < 0) {
            rFlag = proto.maxRegs;
            proto.maxRegs += 1;
        }
        return rFlag;
    };

    for (let i = 0; i < instrs.length; i++) {
        const ins = instrs[i];
        const prevSkip = i > 0 && (COND_SKIP_OPS.has(instrs[i - 1].op) || (instrs[i - 1].op === V5Op.LOADBOOL && instrs[i - 1].C !== 0));
        if (!prevSkip && rng() < prob) {
            if (ins.op === V5Op.CLOSURE) {
                const tmp = getTmp();
                const u1 = { op: V5Op.U_PROTO_FETCH, A: tmp, B: ins.B, C: 0, D: 0, targetIns: null, noMba: true };
                const u2 = { op: V5Op.U_UPVAL_BIND, A: tmp, B: 0, C: 0, D: 0, targetIns: null, noMba: true };
                const u3 = { op: V5Op.U_CLOSURE_WRAP, A: ins.A, B: tmp, C: 0, D: 0, targetIns: null, noMba: true };
                redirect.set(ins, u1);
                out.push(u1, u2, u3);
                continue;
            }
            if (ins.op === V5Op.FORLOOP && ins.targetIns) {
                const flg = getFlag();
                const u1 = { op: V5Op.U_FOR_STEP, A: ins.A, B: flg, C: 0, D: 0, targetIns: null, noMba: true };
                const u2 = { op: V5Op.F_TEST_JMP, A: flg, B: 0, C: 1, D: 0, targetIns: ins.targetIns, noMba: false };
                redirect.set(ins, u1);
                out.push(u1, u2);
                continue;
            }
            if (ins.op === V5Op.F_TFORLOOP_JMP && ins.targetIns) {
                const flg = getFlag();
                const u1 = { op: V5Op.U_TFOR_CALL, A: ins.A, B: flg, C: ins.C, D: 0, targetIns: null, noMba: true };
                const u2 = { op: V5Op.F_TEST_JMP, A: flg, B: 0, C: 0, D: 0, targetIns: ins.targetIns, noMba: false };
                redirect.set(ins, u1);
                out.push(u1, u2);
                continue;
            }
        }
        out.push(ins);
    }
    redirectRefs(out, redirect);
    return out;
}

function mergeUnrelatedOps(instrs, ctx, rng, prob = 0.75) {
    for (let i = 0; i < instrs.length; i++) {
        const ins = instrs[i];
        if (ins.noMba) continue;
        const prevSkip = i > 0 && (COND_SKIP_OPS.has(instrs[i - 1].op) || (instrs[i - 1].op === V5Op.LOADBOOL && instrs[i - 1].C !== 0));
        if (prevSkip) continue;
        const spec = MEMBER_TO_MERGE.get(ins.op);
        if (!spec || rng() > prob) continue;
        ins.op = spec.mergedOp;
        ins.D = ctx.mergeTags[spec.mergedOp][spec.subIdx];
        ins.noMba = true;
    }
    return instrs;
}

/**
 * Randomly assign polymorphic _V2 opcode clones with swapped A/B/C operand slots (L2/L3).
 */
function assignPolymorphicVariants(instrs, rng) {
    for (let i = 0; i < instrs.length; i++) {
        const ins = instrs[i];
        if (ins.noMba || rng() > 0.45) continue;
        const prevSkip = i > 0 && (COND_SKIP_OPS.has(instrs[i - 1].op) || (instrs[i - 1].op === V5Op.LOADBOOL && instrs[i - 1].C !== 0));
        if (prevSkip) continue;

        switch (ins.op) {
            case V5Op.LOADK:
                ins.op = V5Op.LOADK_V2;
                [ins.A, ins.C] = [ins.B, ins.A];
                ins.B = 0;
                break;
            case V5Op.MOVE:
                ins.op = V5Op.MOVE_V2;
                [ins.A, ins.B] = [ins.B, ins.A];
                break;
            case V5Op.GETGLOBAL:
                ins.op = V5Op.GETGLOBAL_V2;
                [ins.A, ins.C] = [ins.B, ins.A];
                ins.B = 0;
                break;
            case V5Op.GETTABLE:
                ins.op = V5Op.GETTABLE_V2;
                { const d = ins.A, t = ins.B, k = ins.C; ins.A = t; ins.B = k; ins.C = d; }
                break;
            case V5Op.SETTABLE:
                ins.op = V5Op.SETTABLE_V2;
                { const t = ins.A, k = ins.B, v = ins.C; ins.A = k; ins.B = v; ins.C = t; }
                break;
            case V5Op.ADD:
                ins.op = V5Op.ADD_V2;
                { const d = ins.A, l = ins.B, r = ins.C; ins.A = l; ins.B = r; ins.C = d; }
                break;
            case V5Op.SUB:
                ins.op = V5Op.SUB_V2;
                { const d = ins.A, l = ins.B, r = ins.C; ins.A = l; ins.B = r; ins.C = d; }
                break;
            case V5Op.JMP:
                ins.op = V5Op.JMP_V2;
                break;
            case V5Op.RETURN:
                ins.op = V5Op.RETURN_V2;
                { const base = ins.A, cnt = ins.B; ins.A = cnt; ins.B = 0; ins.C = base; }
                break;
            case V5Op.F_TEST_JMP:
                ins.op = V5Op.F_TEST_JMP_V2;
                { const reg = ins.A, flag = ins.C; ins.A = 0; ins.B = flag; ins.C = reg; }
                break;
            case V5Op.F_EQ_JMP:
                ins.op = V5Op.F_EQ_JMP_V2;
                { const flag = ins.A, l = ins.B, r = ins.C; ins.A = l; ins.B = r; ins.C = flag; }
                break;
            default:
                break;
        }
    }
    return instrs;
}

/**
 * Pass 2: Split compacted IR into BasicBlocks, inject Realistic Decoy Blocks, and CFF-shuffle.
 */
function buildBasicBlocksAndCFF(instrs, END_MARKER, rng, options) {
    const { doCFF, needFallthrough, decoyCount, proto, rkOffset } = options;
    const emptyBlk = {
        id: 0,
        instrs: [{ op: V5Op.RETURN, A: 0, B: 1, C: 0, D: 0, targetIns: null, targetBlock: null }],
        mode: 0,
        isDecoy: false,
    };
    const END_BLOCK_INIT = { id: -1, isEnd: true, mode: 0 };
    if (instrs.length === 0) {
        return { blocks: [emptyBlk], entryBlock: emptyBlk, END_BLOCK: END_BLOCK_INIT, decoyBlocks: [] };
    }

    const targets = computeProtectedTargets(instrs);
    const insToIdx = new Map();
    instrs.forEach((ins, idx) => insToIdx.set(ins, idx));

    const splitIndices = new Set([0]);
    for (const t of targets) {
        const idx = insToIdx.get(t);
        if (idx !== undefined) splitIndices.add(idx);
    }

    // Any instruction strictly after a terminator/branch/explicit-skip starts a new block
    for (let i = 0; i < instrs.length - 1; i++) {
        const ins = instrs[i];
        const op = ins.op;
        if (TERM_OPS.has(op) || (op === V5Op.LOADBOOL && ins.C !== 0) ||
            op === V5Op.FORLOOP || op === V5Op.F_TEST_JMP || op === V5Op.F_TEST_JMP_V2 ||
            op === V5Op.F_EQ_JMP || op === V5Op.F_EQ_JMP_V2 || op === V5Op.F_LT_JMP || op === V5Op.F_LE_JMP ||
            op === V5Op.F_TESTSET_JMP || op === V5Op.F_TFORLOOP_JMP ||
            op === V5Op.TESTSET || op === V5Op.TFORLOOP) {
            splitIndices.add(i + 1);
        }
    }

    // Check unsafe split points (middle of any remaining skip pair or LOADBOOL(C~=0))
    const unsafe = new Set();
    for (let i = 0; i < instrs.length; i++) {
        const op = instrs[i].op;
        if (COND_SKIP_OPS.has(op) || (op === V5Op.LOADBOOL && instrs[i].C !== 0)) {
            unsafe.add(i + 1);
        }
    }

    if (doCFF) {
        const sortedInit = Array.from(splitIndices).sort((a, b) => a - b);
        const splitThreshold = 3 + Math.floor(rng() * 3);
        for (let bi = 0; bi < sortedInit.length; bi++) {
            const start = sortedInit[bi];
            const end = bi + 1 < sortedInit.length ? sortedInit[bi + 1] : instrs.length;
            if (end - start > splitThreshold) {
                const cands = [];
                for (let pos = start + splitThreshold; pos < end; pos++) {
                    if (!unsafe.has(pos) && !splitIndices.has(pos)) cands.push(pos);
                }
                const nSplit = Math.min(cands.length, 1 + Math.floor(rng() * 2));
                for (let k = cands.length - 1; k > 0; k--) {
                    const j = Math.floor(rng() * (k + 1));
                    [cands[k], cands[j]] = [cands[j], cands[k]];
                }
                for (let k = 0; k < nSplit; k++) splitIndices.add(cands[k]);
            }
        }
    }

    const starts = Array.from(splitIndices).sort((a, b) => a - b);
    const END_BLOCK = { id: -1, isEnd: true, mode: 0 };
    const startToBlock = new Map();
    const blocks = [];

    for (let bi = 0; bi < starts.length; bi++) {
        const s = starts[bi];
        const e = bi + 1 < starts.length ? starts[bi + 1] : instrs.length;
        const blk = {
            id: bi,
            origStart: s,
            origEnd: e,
            instrs: instrs.slice(s, e),
            mode: 0,
            isDecoy: false,
        };
        blocks.push(blk);
        startToBlock.set(s, blk);
    }

    // Wire targetIns -> targetBlock and add fallthrough JMPs when CFF shuffles
    for (let bi = 0; bi < blocks.length; bi++) {
        const blk = blocks[bi];
        for (const ins of blk.instrs) {
            if (ins.targetIns) {
                if (ins.targetIns.isEnd) {
                    ins.targetBlock = END_BLOCK;
                } else {
                    const ti = insToIdx.get(ins.targetIns);
                    const tb = startToBlock.get(ti);
                    if (!tb) throw new Error(`Broken jump target mapping at ${ti}`);
                    ins.targetBlock = tb;
                }
            }
        }
        const last = blk.instrs[blk.instrs.length - 1];
        const endsWithUncond = TERM_OPS.has(last.op) || (last.op === V5Op.LOADBOOL && last.C !== 0);
        if ((doCFF || needFallthrough) && !endsWithUncond) {
            const nextBlk = bi + 1 < blocks.length ? blocks[bi + 1] : END_BLOCK;
            blk.instrs.push({ op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: nextBlk, targetIns: null, noMba: false });
        }
    }

    if (!doCFF || blocks.length < 2) {
        return { blocks, entryBlock: blocks[0], END_BLOCK, decoyBlocks: [] };
    }

    const entryBlock = blocks[0];

    // Add realistic unreachable decoy basic blocks referencing real K constants & upvalues (anti-SCCP / anti-dead-code pruning)
    const decoyBlocks = [];
    const realTargets = [...blocks];
    if (decoyCount > 0 && proto && Array.isArray(proto.K) && proto.K.length + 12 < rkOffset) {
        const scratchA = proto.maxRegs;
        const scratchB = proto.maxRegs + 1;
        proto.maxRegs += 2;
        const existingStrIdx = [];
        for (let ki = 0; ki < proto.K.length; ki++) {
            if (typeof proto.K[ki] === "string" && proto.K[ki].length > 0) existingStrIdx.push(ki);
        }
        for (let d = 0; d < decoyCount; d++) {
            const dTarget = realTargets[Math.floor(rng() * realTargets.length)];
            const dFallback = realTargets[Math.floor(rng() * realTargets.length)];
            const kc1 = addProtoConst(proto, 13 + Math.floor(rng() * 9000));
            const kc2 = addProtoConst(proto, 7 + Math.floor(rng() * 900));
            const dInstrs = [];
            if (proto.upvalues && proto.upvalues.length > 0) {
                dInstrs.push({ op: V5Op.GETUPVAL, A: scratchA, B: d % proto.upvalues.length, C: 0, D: 0, targetBlock: null, noMba: false });
            } else if (existingStrIdx.length > 0) {
                const kStr = existingStrIdx[d % existingStrIdx.length];
                dInstrs.push({ op: V5Op.GETGLOBAL, A: scratchA, B: kStr, C: 0, D: 0, targetBlock: null, noMba: false });
            } else {
                dInstrs.push({ op: V5Op.LOADK, A: scratchA, B: kc1, C: 0, D: 0, targetBlock: null, noMba: false });
            }
            dInstrs.push(
                { op: V5Op.NEWTABLE, A: scratchB, B: 0, C: 0, D: 0, targetBlock: null, noMba: false },
                { op: V5Op.S_SETFIELD_K, A: scratchB, B: kc2, C: scratchA, D: 0, targetBlock: null, noMba: false },
                { op: V5Op.F_TEST_JMP, A: scratchB, B: 0, C: 1, D: 0, targetBlock: dTarget, noMba: false },
                { op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: dFallback, noMba: false }
            );
            const db = { id: blocks.length, origStart: -1, origEnd: -1, instrs: dInstrs, mode: 0, isDecoy: true };
            blocks.push(db);
            decoyBlocks.push(db);
        }
    } else {
        for (let d = 0; d < decoyCount; d++) {
            const dTarget = realTargets[Math.floor(rng() * realTargets.length)];
            const regA = Math.floor(rng() * 4);
            const regB = Math.floor(rng() * 4);
            const dInstrs = [
                { op: V5Op.MOVE, A: regA, B: regB, C: 0, D: 0, targetBlock: null, noMba: false },
                { op: V5Op.ADD, A: regA, B: regA, C: regB, D: 0, targetBlock: null, noMba: false },
                { op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: dTarget, noMba: false },
            ];
            const db = { id: blocks.length, origStart: -1, origEnd: -1, instrs: dInstrs, mode: 0, isDecoy: true };
            blocks.push(db);
            decoyBlocks.push(db);
        }
    }

    // Shuffle blocks (with explicit entry trampoline JMP so entryBlock can sit anywhere!)
    for (let i = blocks.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [blocks[i], blocks[j]] = [blocks[j], blocks[i]];
    }

    const headerBlk = {
        id: -2,
        origStart: -1,
        origEnd: -1,
        instrs: [{ op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: entryBlock, noMba: true }],
        mode: entryBlock.mode,
        isDecoy: false,
        isEntryHeader: true,
    };
    const finalBlocks = [headerBlk, ...blocks];
    return { blocks: finalBlocks, entryBlock: headerBlk, END_BLOCK, decoyBlocks };
}

/**
 * Bytecode-Level IR State-Machine Control-Flow Flattening (L3 non-hot protos).
 * Converts inter-block jumps/branches into state-register assignments + a binary-tree dispatcher.
 */
function irFlattenStateMachine(irGraph, proto, ctx, rng) {
    const { blocks, entryBlock, END_BLOCK } = irGraph;
    if (!proto || blocks.length < 4 || blocks.length > 22 || proto.K.length + 64 >= ctx.rkOffset) return;

    const flatBlocks = blocks.filter(b => !b.isEntryHeader && !b.isDecoy && !b.isTrampoline && b.instrs.length > 0);
    if (flatBlocks.length < 3) return;
    const flatSet = new Set(flatBlocks);

    const rState = proto.maxRegs;
    proto.maxRegs += 1;

    const usedStates = new Set();
    const stateOf = new Map();
    for (const blk of flatBlocks) {
        let sv = 10000 + Math.floor(rng() * 890000);
        while (usedStates.has(sv)) {
            sv = 10000 + ((sv - 10000 + 7919) % 890000);
        }
        usedStates.add(sv);
        stateOf.set(blk, sv);
    }

    const sortedEntries = flatBlocks
        .map(b => ({ blk: b, state: stateOf.get(b) }))
        .sort((a, b) => a.state - b.state);

    const dispBlocks = [];
    const buildDispTree = (lo, hi) => {
        if (lo === hi) {
            return sortedEntries[lo].blk;
        }
        if (hi - lo === 1) {
            const left = sortedEntries[lo];
            const right = sortedEntries[hi];
            const kLeft = addProtoConst(proto, left.state);
            const nodeBlk = {
                id: 80000 + dispBlocks.length,
                origStart: -1, origEnd: -1,
                instrs: [
                    { op: V5Op.F_EQ_JMP, A: 1, B: rState, C: ctx.rkOffset + kLeft, D: 0, targetBlock: left.blk, noMba: false },
                    { op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: right.blk, noMba: false },
                ],
                mode: 0, isDecoy: false, isDisp: true,
            };
            dispBlocks.push(nodeBlk);
            return nodeBlk;
        }
        const mid = (lo + hi) >> 1;
        const pivotState = sortedEntries[mid].state;
        const leftNode = buildDispTree(lo, mid);
        const rightNode = buildDispTree(mid + 1, hi);
        const kPivot = addProtoConst(proto, pivotState);
        const nodeBlk = {
            id: 80000 + dispBlocks.length,
            origStart: -1, origEnd: -1,
            instrs: [
                { op: V5Op.F_LE_JMP, A: 1, B: rState, C: ctx.rkOffset + kPivot, D: 0, targetBlock: leftNode, noMba: false },
                { op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: rightNode, noMba: false },
            ],
            mode: 0, isDecoy: false, isDisp: true,
        };
        dispBlocks.push(nodeBlk);
        return nodeBlk;
    };

    const dispRoot = buildDispTree(0, sortedEntries.length - 1);
    if (proto.K.length + 12 >= ctx.rkOffset) return;

    const emitStateSet = (sv) => {
        if (proto.K.length + 4 < ctx.rkOffset) {
            const p = 100 + Math.floor(rng() * 5000);
            const q = sv - p;
            const kP = addProtoConst(proto, p);
            const kQ = addProtoConst(proto, q);
            return [
                { op: V5Op.LOADK, A: rState, B: kP, C: 0, D: 0, targetBlock: null, noMba: false },
                { op: V5Op.S_ADD_K, A: rState, B: rState, C: kQ, D: 0, targetBlock: null, noMba: false },
            ];
        }
        const kS = addProtoConst(proto, sv);
        return [{ op: V5Op.LOADK, A: rState, B: kS, C: 0, D: 0, targetBlock: null, noMba: false }];
    };

    const stubBlocks = [];
    const redirectEdgeToState = (tb) => {
        const sv = stateOf.get(tb);
        const stub = {
            id: 90000 + stubBlocks.length,
            origStart: -1, origEnd: -1,
            instrs: [
                ...emitStateSet(sv),
                { op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: dispRoot, noMba: false },
            ],
            mode: 0, isDecoy: false, isDisp: true,
        };
        stubBlocks.push(stub);
        return stub;
    };

    // Redirect entry header -> set initial state -> dispRoot
    if (entryBlock && entryBlock.instrs.length === 1 && flatSet.has(entryBlock.instrs[0].targetBlock)) {
        const initState = stateOf.get(entryBlock.instrs[0].targetBlock);
        entryBlock.instrs = [
            ...emitStateSet(initState),
            { op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: dispRoot, noMba: true },
        ];
    }

    for (const blk of flatBlocks) {
        const newInstrs = [];
        for (let idx = 0; idx < blk.instrs.length; idx++) {
            const ins = blk.instrs[idx];
            if (ins.targetBlock && ins.targetBlock !== END_BLOCK && flatSet.has(ins.targetBlock)) {
                if ((ins.op === V5Op.JMP || ins.op === V5Op.JMP_V2) && idx === blk.instrs.length - 1) {
                    const sv = stateOf.get(ins.targetBlock);
                    newInstrs.push(
                        ...emitStateSet(sv),
                        { op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: dispRoot, noMba: false }
                    );
                    continue;
                }
                ins.targetBlock = redirectEdgeToState(ins.targetBlock);
            }
            newInstrs.push(ins);
        }
        blk.instrs = newInstrs;
    }

    const extraBlocks = [...dispBlocks, ...stubBlocks];
    for (const eb of extraBlocks) {
        const idx = 1 + Math.floor(rng() * blocks.length);
        blocks.splice(idx, 0, eb);
    }
}

/**
 * Compiler-level Runtime-Coupled Anti-SCCP Opaque Branch Synthesis (L2/L3 non-hot protos):
 * Guards tail jumps with non-constant-foldable runtime predicates (NEWTABLE + LEN == 0 / table truthiness)
 * so symbolic evaluators (SCCP) cannot prune decoy blocks statically.
 */
function irInjectRuntimeOpaqueBranches(irGraph, proto, ctx, rng) {
    const { blocks, END_BLOCK, decoyBlocks } = irGraph;
    if (!decoyBlocks || decoyBlocks.length === 0 || !proto || proto.K.length + 12 >= ctx.rkOffset) return;

    const candidates = blocks.filter(b => {
        if (b.isEntryHeader || b.isDecoy || b.isTrampoline || b.isDisp || b.instrs.length === 0) return false;
        const last = b.instrs[b.instrs.length - 1];
        return (last.op === V5Op.JMP || last.op === V5Op.JMP_V2) && last.targetBlock && last.targetBlock !== END_BLOCK;
    });
    if (candidates.length === 0) return;

    const rTmp = proto.maxRegs;
    const rTmp2 = proto.maxRegs + 1;
    proto.maxRegs += 2;

    const nInject = Math.min(3, candidates.length);
    for (let ci = 0; ci < nInject; ci++) {
        const blk = candidates[ci];
        const tailJmp = blk.instrs[blk.instrs.length - 1];
        const trueTarget = tailJmp.targetBlock;
        const fakeTarget = decoyBlocks[ci % decoyBlocks.length];

        const variant = Math.floor(rng() * 3);
        if (variant === 0) {
            const kZero = addProtoConst(proto, 0);
            if (kZero >= ctx.rkOffset) break;
            blk.instrs.pop();
            blk.instrs.push(
                { op: V5Op.NEWTABLE, A: rTmp, B: 0, C: 0, D: 0, targetBlock: null, noMba: false },
                { op: V5Op.LEN, A: rTmp2, B: rTmp, C: 0, D: 0, targetBlock: null, noMba: false },
                { op: V5Op.F_EQ_JMP, A: 1, B: rTmp2, C: ctx.rkOffset + kZero, D: 0, targetBlock: trueTarget, noMba: false },
                { op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: fakeTarget, noMba: false }
            );
        } else if (variant === 1) {
            blk.instrs.pop();
            blk.instrs.push(
                { op: V5Op.NEWTABLE, A: rTmp, B: 0, C: 0, D: 0, targetBlock: null, noMba: false },
                { op: V5Op.F_TEST_JMP, A: rTmp, B: 0, C: 1, D: 0, targetBlock: trueTarget, noMba: false },
                { op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: fakeTarget, noMba: false }
            );
        } else {
            const kKey = addProtoConst(proto, `_v${100 + Math.floor(rng() * 899)}`);
            const kVal = addProtoConst(proto, 17 + Math.floor(rng() * 900));
            if (Math.max(kKey, kVal) >= ctx.rkOffset) break;
            blk.instrs.pop();
            blk.instrs.push(
                { op: V5Op.NEWTABLE, A: rTmp, B: 0, C: 0, D: 0, targetBlock: null, noMba: false },
                { op: V5Op.S_SETFIELD_K, A: rTmp, B: kKey, C: ctx.rkOffset + kVal, D: 0, targetBlock: null, noMba: false },
                { op: V5Op.S_GETFIELD_K, A: rTmp2, B: rTmp, C: kKey, D: 0, targetBlock: null, noMba: false },
                { op: V5Op.F_EQ_JMP, A: 1, B: rTmp2, C: ctx.rkOffset + kVal, D: 0, targetBlock: trueTarget, noMba: false },
                { op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: fakeTarget, noMba: false }
            );
        }
    }
}

/**
 * Pass 3: Dual-Mode VM Partitioning (Level 3 ONYX).
 * Assigns each block to Mode 0 or Mode 1 and rewrites cross-mode jumps with OP_MODE_SWITCH / trampolines.
 */
function applyDualModePartition(irGraph, rng) {
    const { blocks, entryBlock, END_BLOCK } = irGraph;
    const entryMode = Math.floor(rng() * 2);
    entryBlock.mode = entryMode;

    for (const blk of blocks) {
        if (blk === entryBlock) continue;
        blk.mode = Math.floor(rng() * 2);
    }

    const trampolines = [];
    for (const blk of blocks) {
        for (const ins of blk.instrs) {
            const tb = ins.targetBlock;
            if (!tb || tb === END_BLOCK) continue;
            if (tb.mode !== blk.mode) {
                if (ins.op === V5Op.JMP || ins.op === V5Op.JMP_V2) {
                    ins.op = V5Op.OP_MODE_SWITCH;
                    ins.B = tb.mode;
                    ins.C = 0;
                    ins.noMba = true;
                } else {
                    // Conditional branch or FORPREP/FORLOOP crossing modes: redirect through 1-op trampoline
                    const tramp = {
                        id: 100000 + trampolines.length,
                        instrs: [{
                            op: V5Op.OP_MODE_SWITCH,
                            A: 0,
                            B: tb.mode,
                            C: 0,
                            D: 0,
                            targetBlock: tb,
                            noMba: true,
                        }],
                        mode: blk.mode,
                        isDecoy: false,
                        isTrampoline: true,
                    };
                    trampolines.push(tramp);
                    ins.targetBlock = tramp;
                }
            }
        }
    }

    if (trampolines.length > 0) {
        for (const t of trampolines) {
            const idx = 1 + Math.floor(rng() * blocks.length);
            blocks.splice(idx, 0, t);
        }
    }
    return entryMode;
}

/**
 * Pass 4a: Path-Dependent Rolling State (_st) + Universal Once-Per-Block Decryption (L2/L3).
 * Prepends OP_BLK_ENTER to every basic block in !isFast so all block bodies remain encrypted at rest
 * and static linear-sweep disassembly yields garbage without executing the exact runtime CFG path.
 */
function insertRollingBlockHeaders(blocks, END_BLOCK, ctx, protoSalt, rng) {
    const encryptedBlocks = new Set();
    const randU32 = () => (0x01010101 + Math.floor(rng() * 0x7EFFFFFF)) >>> 0;
    const entryBlk = blocks[0];
    END_BLOCK.entryState = 0;

    for (const blk of blocks) {
        blk.entryState = (blk === entryBlk) ? ((ctx.K2 ^ protoSalt) >>> 0) : randU32();
        blk.postState = randU32();
    }

    for (const blk of blocks) {
        const bodyLen = blk.instrs.length;
        if (bodyLen === 0) continue;
        const blockSalt = (1 + Math.floor(rng() * 0x7FFFFFFE)) >>> 0;
        const stepXor = (blk.entryState ^ blk.postState) >>> 0;
        const hdr = {
            op: V5Op.OP_BLK_ENTER,
            A: (bodyLen ^ (blk.entryState & 0xFFFF)) >>> 0,
            B: blockSalt,
            C: stepXor,
            D: 0,
            targetBlock: null,
            noMba: true,
            isDecryptHdr: true,
            bodyLen,
            blockSalt,
        };
        blk.instrs.unshift(hdr);
        ctx.usedOps[blk.mode].add(V5Op.OP_BLK_ENTER);
        ctx.usedOps[blk.mode].add(V5Op.OP_STATE_STEP);
        encryptedBlocks.add(blk);
    }
    return encryptedBlocks;
}

/**
 * Dynamic PC+Key Algebraic Operand Encoder/Decoder (4 randomized invertible 32-bit forms).
 * Shared between JS serializer prep and self-checked per build.
 */
export function encodeDynamicOperand(val, pc, spec, dk) {
    if (!spec) return val >>> 0;
    const v = val >>> 0;
    const p = pc >>> 0;
    const dkA = dk[spec.dkIdx] >>> 0;
    const dkB = dk[spec.dkIdx2] >>> 0;
    const pm = Math.imul(p, spec.mul) >>> 0;
    switch (spec.form) {
        case 0:
            return (v ^ (dkA ^ ((pm + spec.c) >>> 0))) >>> 0;
        case 1:
            return (((v + ((dkA + pm) >>> 0)) >>> 0) ^ spec.c) >>> 0;
        case 2:
            return (((v ^ spec.c) + ((dkA + pm) >>> 0)) >>> 0);
        case 3:
        default:
            return (v ^ dkA ^ ((dkB + pm) >>> 0)) >>> 0;
    }
}

export function decodeDynamicOperand(enc, pc, spec, dk) {
    if (!spec) return enc >>> 0;
    const e = enc >>> 0;
    const p = pc >>> 0;
    const dkA = dk[spec.dkIdx] >>> 0;
    const dkB = dk[spec.dkIdx2] >>> 0;
    const pm = Math.imul(p, spec.mul) >>> 0;
    switch (spec.form) {
        case 0:
            return (e ^ (dkA ^ ((pm + spec.c) >>> 0))) >>> 0;
        case 1:
            return (((e ^ spec.c) - ((dkA + pm) >>> 0)) >>> 0);
        case 2:
            return (((e - ((dkA + pm) >>> 0)) >>> 0) ^ spec.c) >>> 0;
        case 3:
        default:
            return ((e ^ dkA) ^ ((dkB + pm) >>> 0)) >>> 0;
    }
}

/**
 * Build SoA arrays [a0, a1, a2, a3, a4] for a single proto after layout,
 * applying IR transforms, per-proto _rb/_kb shifts, dynamic PC+Key operand encoding,
 * per-mode slot permutation, opcode masking, block encryption, and MBA wrapping.
 */
function finalizeProtoSoA(proto, ctx, rng, isRoot = false) {
    const isMax = ctx.level === "max";
    const isBalanced = ctx.level === "normal";
    const isFast = ctx.level === "fast";
    const tier = proto.tier || (isRoot ? "cold" : "normal");
    const hasClosures = Boolean(proto.hasClosures);
    const hasLoops = Boolean(proto.hasLoops);
    const isHot = (tier === "jit" || tier === "jitmax" || hasLoops);
    // Root top-level proto runs once; child closures hold references to upval cells, never root's _c0.._c4
    const isEphemeral = (isRoot && !isFast);

    // Per-proto randomized Register Base (_rb), Constant Base (_kb), and Rolling Proto Salt
    const regBase = isFast ? 1 : (3 + Math.floor(rng() * 17));
    const kBase = isFast ? 1 : (2 + Math.floor(rng() * 16));
    const protoSalt = (0x010101 + Math.floor(rng() * 0x7EFFFFFF)) >>> 0;

    const raw = decodeRawInstrs(proto.code, ctx.rkOffset);
    let instrs = collapseLoadKX(raw.instrs);
    if (!isFast) {
        instrs = permuteProtoRegisters(instrs, proto, ctx, rng);
    }
    if (!isFast && !isHot) {
        instrs = irTransformNumericConstants(instrs, proto, ctx, rng, isMax ? 0.65 : 0.35);
    }
    instrs = fuseAndSpecialize(instrs, ctx.rkOffset);
    if (!isFast && !isHot) {
        instrs = splitComplexOps(instrs, proto, rng, isMax ? 0.90 : 0.65);
    }
    if (!isFast) {
        const mergeProb = isHot ? 0.20 : (isMax ? 0.80 : 0.55);
        instrs = mergeUnrelatedOps(instrs, ctx, rng, mergeProb);
        instrs = assignPolymorphicVariants(instrs, rng);
    }

    const irGraph = buildBasicBlocksAndCFF(instrs, raw.END_MARKER, rng, {
        doCFF: ctx.doCFF,
        needFallthrough: !isFast,
        decoyCount: isMax ? (2 + Math.floor(rng() * 3)) : (isBalanced ? 1 : 0),
        proto,
        rkOffset: ctx.rkOffset,
    });

    if (isMax && !isHot && ctx.doCFF) {
        irFlattenStateMachine(irGraph, proto, ctx, rng);
    }

    if (!isFast && !isHot && irGraph.blocks.length >= 2) {
        irInjectRuntimeOpaqueBranches(irGraph, proto, ctx, rng);
    }

    let entryMode = 0;
    if (isMax && irGraph.blocks.length >= 2) {
        entryMode = applyDualModePartition(irGraph, rng);
    }

    let encryptedBlocks = new Set();
    if (!isFast) {
        encryptedBlocks = insertRollingBlockHeaders(irGraph.blocks, irGraph.END_BLOCK, ctx, protoSalt, rng);
    }

    // Layout blocks sequentially -> assign 1-based PC
    const blockStartPC = new Map();
    let totalInstr = 0;
    for (const blk of irGraph.blocks) {
        blockStartPC.set(blk, totalInstr + 1);
        totalInstr += blk.instrs.length;
    }
    const endPC = totalInstr + 1;

    // Resolve jump targets to concrete 1-based targetPC AND compute exact CFG Edge Rolling Keys (D = postState ^ target.entryState)
    for (const blk of irGraph.blocks) {
        for (const ins of blk.instrs) {
            if (ins.targetBlock) {
                const tPC = ins.targetBlock === irGraph.END_BLOCK ? endPC : blockStartPC.get(ins.targetBlock);
                const edgeXor = (!isFast) ? ((blk.postState ^ ins.targetBlock.entryState) >>> 0) : 0;
                if (ins.op === V5Op.OP_MODE_SWITCH) {
                    ins.A = tPC;
                    ins.D = edgeXor;
                } else if (ins.op === V5Op.F_TEST_JMP_V2) {
                    ins.A = tPC;
                    ins.D = edgeXor;
                } else if (ins.op === V5Op.JMP_V2) {
                    ins.C = tPC;
                    ins.D = edgeXor;
                } else if (ins.op === V5Op.JMP || ins.op === V5Op.FORPREP || ins.op === V5Op.FORLOOP ||
                    ins.op === V5Op.F_TEST_JMP || ins.op === V5Op.F_TFORLOOP_JMP) {
                    ins.B = tPC;
                    ins.D = edgeXor;
                } else if (ins.op === V5Op.TFORLOOP) {
                    if (!isFast) {
                        ins.B = tPC;
                        ins.D = edgeXor;
                    } else {
                        ins.D = tPC;
                    }
                } else if (ins.op === V5Op.LOADBOOL && ins.C !== 0) {
                    ins.C = tPC;
                    ins.D = edgeXor;
                } else if (ins.op === V5Op.F_EQ_JMP || ins.op === V5Op.F_LT_JMP || ins.op === V5Op.F_LE_JMP) {
                    if (!isFast) {
                        ins.A = ((tPC * 2) + (ins.A ? 1 : 0)) >>> 0;
                        ins.D = edgeXor;
                    } else {
                        ins.D = tPC;
                    }
                } else if (ins.op === V5Op.F_EQ_JMP_V2 || ins.op === V5Op.F_TESTSET_JMP || ins.op === V5Op.TESTSET) {
                    if (!isFast) {
                        ins.C = ((tPC * 2) + (ins.C ? 1 : 0)) >>> 0;
                        ins.D = edgeXor;
                    } else {
                        ins.D = tPC;
                    }
                }
            }
        }
    }

    // Collect used opcodes
    for (const blk of irGraph.blocks) {
        for (const ins of blk.instrs) {
            ctx.usedOps[blk.mode].add(ins.op);
        }
    }

    // Materialize SoA 5-column instruction buffer (zero per-instruction % 4294967296 overhead!)
    const arr0 = new Array(totalInstr);
    const arr1 = new Array(totalInstr);
    const arr2 = new Array(totalInstr);
    const arr3 = new Array(totalInstr);
    const arr4 = new Array(totalInstr);
    const cols = [arr0, arr1, arr2, arr3, arr4];

    const mbaTargets = [];
    let pc = 1;
    for (const blk of irGraph.blocks) {
        const modeCfg = ctx.modes[blk.mode];
        const isEncBlk = encryptedBlocks.has(blk);
        const startPcOfBlk = pc;

        for (let bi = 0; bi < blk.instrs.length; bi++) {
            const ins = blk.instrs[bi];
            const opId = modeCfg.opEncode[ins.op];
            const storedOp = (opId ^ ctx.kLo ^ modeCfg.mSalt) >>> 0;
            const bias = modeCfg.opRegBias[ins.op] || 0;

            const vA = ((ins.A >>> 0) + bias) >>> 0;
            const vB = ins.B >>> 0;
            const vC = ins.C >>> 0;
            const vD = ins.D >>> 0;

            cols[modeCfg.role.op][pc - 1] = storedOp;
            cols[modeCfg.role.A][pc - 1] = vA;
            cols[modeCfg.role.B][pc - 1] = vB;
            cols[modeCfg.role.C][pc - 1] = vC;
            cols[modeCfg.role.D][pc - 1] = vD;

            // Eligible instructions inside encrypted blocks get MBA wrapping BEFORE rolling block encryption
            const inEncBody = isEncBlk && bi > 0;
            if (isMax && !isHot && inEncBody && !ins.noMba && ins.D === 0 &&
                ins.op !== V5Op.OP_BLK_ENTER && ins.op !== V5Op.OP_STATE_STEP &&
                ins.op !== V5Op.OP_MODE_SWITCH && ins.op !== V5Op.NOP) {
                mbaTargets.push({ pc, mode: blk.mode, postState: blk.postState, storedOp, vA, vB, vC });
            }
            pc++;
        }
    }

    // Apply OP_MBA_DECODE_0..3 with path-coupled postState key BEFORE rolling block LCG encryption
    if (isMax && !isHot && ctx.mbaCodecs && ctx.mbaCodecs.length > 0) {
        const rate = 0.25;
        for (const t of mbaTargets) {
            if (rng() > rate) continue;
            const cIdx = Math.floor(rng() * ctx.mbaCodecs.length);
            const codec = ctx.mbaCodecs[cIdx];
            const decOp = V5Op.OP_MBA_DECODE_0 + cIdx;
            ctx.usedOps[t.mode].add(decOp);

            const modeCfg = ctx.modes[t.mode];
            const decOpId = modeCfg.opEncode[decOp];
            const decStoredOp = (decOpId ^ ctx.kLo ^ modeCfg.mSalt) >>> 0;
            const mbaKey = (t.postState ^ Math.imul(t.pc, 2654435761)) >>> 0;

            cols[modeCfg.role.op][t.pc - 1] = decStoredOp;
            cols[modeCfg.role.A][t.pc - 1] = codec.encode(t.vA, mbaKey);
            cols[modeCfg.role.B][t.pc - 1] = codec.encode(t.vB, mbaKey);
            cols[modeCfg.role.C][t.pc - 1] = codec.encode(t.vC, mbaKey);
            cols[modeCfg.role.D][t.pc - 1] = codec.encode(t.storedOp, mbaKey);
        }
    }

    // Apply Universal Rolling-State Block Cipher over every block body [startPcOfBlk+1 .. startPcOfBlk+bodyLen]
    if (!isFast) {
        let bPc = 1;
        for (const blk of irGraph.blocks) {
            if (encryptedBlocks.has(blk)) {
                const hdrIns = blk.instrs[0];
                const bodyLen = hdrIns.bodyLen;
                const blockSalt = hdrIns.blockSalt;
                let lcg = (blk.entryState ^ blockSalt ^ ctx.K1) >>> 0;
                for (let k = 1; k <= bodyLen; k++) {
                    const idx = (bPc - 1) + k;
                    for (let c = 0; c < 5; c++) {
                        lcg = (Math.imul(lcg, 1664525) + 1013904223) >>> 0;
                        cols[c][idx] = (cols[c][idx] ^ lcg) >>> 0;
                    }
                }
            }
            bPc += blk.instrs.length;
        }
    }

    const v5Protos = (proto.protos || []).map(cp => finalizeProtoSoA(cp, ctx, rng, false));
    return {
        K: proto.K,
        nInstr: totalInstr,
        arr0, arr1, arr2, arr3, arr4,
        nParams: proto.nParams ?? 0,
        maxRegs: proto.maxRegs ?? 0,
        isVararg: Boolean(proto.isVararg),
        upvalues: proto.upvalues || [],
        entryMode,
        regBase,
        kBase,
        protoSalt,
        tier,
        isHot,
        hasClosures,
        hasLoops,
        isEphemeral,
        protos: v5Protos,
    };
}

/**
 * Create Sentinel v5.2 APEX per-build IR & ISA context (128-bit KV, random RK base, dynamic operand codecs)
 * and compile chunk tree to v5 IR.
 */
export function buildV5IR(rootChunk, options, rng) {
    const level = options.level || "max";
    const isMax = level === "max";
    const isFast = level === "fast";
    const numModes = isMax ? 2 : 1;

    // 128-bit Integrity Key Vector KV = [K0, K1, K2, K3], every byte guaranteed in [1..254] (zero-free)
    const randNonZeroU32 = () => {
        const b0 = 1 + Math.floor(rng() * 254);
        const b1 = 1 + Math.floor(rng() * 254);
        const b2 = 1 + Math.floor(rng() * 254);
        const b3 = 1 + Math.floor(rng() * 254);
        return (((b3 << 24) | (b2 << 16) | (b1 << 8) | b0) >>> 0);
    };
    const K0 = randNonZeroU32();
    const K1 = randNonZeroU32();
    const K2 = randNonZeroU32();
    const K3 = randNonZeroU32();
    const KV = [K0, K1, K2, K3];
    const kBytes = [];
    for (const ki of KV) {
        kBytes.push(ki & 0xFF, (ki >>> 8) & 0xFF, (ki >>> 16) & 0xFF, (ki >>> 24) & 0xFF);
    }
    const kLo = K0 & 0xFF;
    const kHi = (K0 >>> 8) & 0xFF;

    // 4 dynamic runtime operand keys derived from K2/K3 and per-build salts
    const dkSalts = [0, 1, 2, 3].map(() => (0x101 + Math.floor(rng() * 0xFFFFFF)) >>> 0);
    const dk = [
        ((K3 ^ dkSalts[0]) & 0xFFFFFF) >>> 0,
        (((K3 >>> 16) ^ dkSalts[1]) & 0xFFFFFF) >>> 0,
        ((K2 ^ dkSalts[2]) & 0xFFFFFF) >>> 0,
        (((K2 >>> 16) ^ dkSalts[3]) & 0xFFFFFF) >>> 0,
    ];

    // Randomized per-build RK constant threshold (>= 2048 so register indices never collide)
    const rkOffset = isFast ? RK_OFFSET : (2048 + Math.floor(rng() * 12288));

    const makeCodecSpec = () => {
        const form = Math.floor(rng() * 4);
        const dkIdx = Math.floor(rng() * 4);
        let dkIdx2 = Math.floor(rng() * 4);
        if (dkIdx2 === dkIdx) dkIdx2 = (dkIdx + 1) % 4;
        const mul = 3 + 2 * Math.floor(rng() * 30); // odd 3..61
        const c = 1 + Math.floor(rng() * 0xFFFFFE);
        const spec = { form, dkIdx, dkIdx2, mul, c };
        // Self-check invertibility
        for (const tv of [0, 1, 17, 255, 2048, 16384]) {
            const tp = 1 + Math.floor(rng() * 200);
            if (decodeDynamicOperand(encodeDynamicOperand(tv, tp, spec, dk), tp, spec, dk) !== tv) {
                throw new Error("Dynamic operand codec self-check failed");
            }
        }
        return spec;
    };

    // Opcodes where field A IS a 0-based register index (safe for positive constant regBias shift)
    const A_IS_REG_OPS = new Set([
        V5Op.LOADK, V5Op.LOADNIL, V5Op.LOADBOOL, V5Op.MOVE, V5Op.GETGLOBAL, V5Op.SETGLOBAL,
        V5Op.GETTABLE, V5Op.SETTABLE, V5Op.NEWTABLE, V5Op.ADD, V5Op.SUB, V5Op.MUL, V5Op.DIV,
        V5Op.MOD, V5Op.POW, V5Op.IDIV, V5Op.UNM, V5Op.NOT, V5Op.LEN, V5Op.CONCAT,
        V5Op.TEST, V5Op.TESTSET, V5Op.CALL, V5Op.TAILCALL, V5Op.RETURN, V5Op.FORPREP, V5Op.FORLOOP,
        V5Op.TFORLOOP, V5Op.SETLIST, V5Op.CLOSURE, V5Op.VARARG, V5Op.SELF, V5Op.GETUPVAL, V5Op.SETUPVAL,
        V5Op.CLOSEUPVAL, V5Op.PCALL, V5Op.XPCALL, V5Op.ITERPREP,
        V5Op.F_TEST_JMP, V5Op.F_TESTSET_JMP, V5Op.F_GGET, V5Op.F_LOADKK, V5Op.F_MOVE_MOVE,
        V5Op.F_SELF_CALL, V5Op.F_GGET_CALL, V5Op.F_MOVE_RET,
        V5Op.S_CALL0, V5Op.S_CALL1, V5Op.S_CALL2, V5Op.S_GETFIELD_K, V5Op.S_SETFIELD_K,
        V5Op.S_UPVAL_GET, V5Op.S_ADD_K, V5Op.S_SUB_K, V5Op.S_MUL_K, V5Op.S_MOD_K,
        V5Op.F_TFORLOOP_JMP, V5Op.S_CALL0_VOID, V5Op.S_CALL1_VOID, V5Op.S_CALL2_VOID, V5Op.S_CALL3,
        V5Op.F_NEWTAB_SET, V5Op.F_LOADK_CALL1, V5Op.F_LOADK_CALL1_VOID,
        V5Op.MOVE_V2, V5Op.GETTABLE_V2, V5Op.ADD_V2, V5Op.SUB_V2,
        V5Op.M_TAB_SUB_NOT, V5Op.M_SET_ADD_LEN, V5Op.M_ENV_MOV_UNM, V5Op.M_LDK_MUL_SGL,
        V5Op.M_DIV_MOD_GUP, V5Op.M_CAT_POW_SUP,
        V5Op.U_PROTO_FETCH, V5Op.U_UPVAL_BIND, V5Op.U_CLOSURE_WRAP, V5Op.U_FOR_STEP, V5Op.U_TFOR_CALL,
    ]);

    // Per-build randomized sub-selector tags for the 6 Merged Multi-Semantics Handlers
    const mergeTags = {};
    for (const g of MERGE_GROUPS) {
        const tagPool = Array.from({ length: 250 }, (_, i) => i + 1);
        for (let i = tagPool.length - 1; i > 0; i--) {
            const j = Math.floor(rng() * (i + 1));
            [tagPool[i], tagPool[j]] = [tagPool[j], tagPool[i]];
        }
        mergeTags[g.op] = tagPool.slice(0, g.members.length);
    }

    const createModeConfig = (modeId) => {
        const pool = Array.from({ length: V5_OPCODE_COUNT }, (_, i) => i + 1);
        for (let i = pool.length - 1; i > 0; i--) {
            const j = Math.floor(rng() * (i + 1));
            [pool[i], pool[j]] = [pool[j], pool[i]];
        }
        const opEncode = new Array(V5_OPCODE_COUNT);
        const opDecode = {};
        const opFieldCodecs = new Array(V5_OPCODE_COUNT);
        const opRegBias = new Array(V5_OPCODE_COUNT).fill(0);

        for (let op = 0; op < V5_OPCODE_COUNT; op++) {
            opEncode[op] = pool[op];
            opDecode[pool[op]] = op;
            if (isFast) {
                opFieldCodecs[op] = [null, null, null];
            } else {
                opFieldCodecs[op] = [makeCodecSpec(), makeCodecSpec(), makeCodecSpec()];
                if (A_IS_REG_OPS.has(op)) {
                    // Positive integer bias added to plainA (subtracted back in Lua alongside + _rb)
                    opRegBias[op] = 2 + Math.floor(rng() * 14);
                }
            }
        }
        const slots = [0, 1, 2, 3, 4];
        for (let i = slots.length - 1; i > 0; i--) {
            const j = Math.floor(rng() * (i + 1));
            [slots[i], slots[j]] = [slots[j], slots[i]];
        }
        return {
            modeId,
            mSalt: 1 + Math.floor(rng() * 254),
            opEncode,
            opDecode,
            opFieldCodecs,
            opRegBias,
            role: { op: slots[0], A: slots[1], B: slots[2], C: slots[3], D: slots[4] },
        };
    };

    const modes = [];
    const usedOps = [];
    for (let m = 0; m < numModes; m++) {
        modes.push(createModeConfig(m));
        usedOps.push(new Set());
    }

    const mbaCodecs = isMax ? [0, 1, 2, 3].map(id => createMbaCodec(rng, id)) : [];

    const ctx = {
        level,
        isFastMode: isFast,
        doCFF: options.doCFF !== false,
        KV,
        K0, K1, K2, K3,
        K_TARGET: K0, // Legacy alias for existing checks if referenced
        kLo,
        kHi,
        kBytes,
        dk,
        dkSalts,
        rkOffset,
        numModes,
        modes,
        usedOps,
        mbaCodecs,
        mergeTags,
    };

    const v5Root = finalizeProtoSoA(rootChunk, ctx, rng, true);
    return { v5Root, ctx };
}
