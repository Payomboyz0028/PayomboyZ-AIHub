// language: JavaScript, file: v5-ir-passes.js, target: Node.js ESM
// Sentinel v5.0 IR Transformation Pipeline: Superoperators, Specialization, CFF, Decoy Injection, Dual-Mode Partitioning, Lazy Block Decrypt & MBA Wrapping

import { V5Op, V5_OPCODE_COUNT, RK_OFFSET } from "./bytecode.js";
import { createMbaCodec } from "./v5-mba.js";

const COND_SKIP_OPS = new Set([
    V5Op.EQ, V5Op.LT, V5Op.LE, V5Op.TEST, V5Op.TESTSET, V5Op.TFORLOOP,
]);

const TERM_OPS = new Set([
    V5Op.JMP, V5Op.RETURN, V5Op.TAILCALL, V5Op.FORPREP, V5Op.OP_MODE_SWITCH,
    V5Op.F_LOADK_RET, V5Op.F_MOVE_RET,
]);

/**
 * Convert raw 4-int flat chunk.code into linked instruction list & resolve jump targets.
 */
function decodeRawInstrs(code) {
    const n = Math.floor(code.length / 4);
    const instrs = new Array(n);
    for (let i = 0; i < n; i++) {
        const b = i * 4;
        instrs[i] = {
            op: code[b] | 0,
            A: code[b + 1] | 0,
            B: code[b + 2] | 0,
            C: code[b + 3] | 0,
            D: 0,
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
 * Pass 1: Compact Superoperator Fusion + Opcode Specialization.
 * Preserves jump targets cleanly because fused instructions replace sequences in the compacted array.
 */
function fuseAndSpecialize(instrs) {
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
            } else if (i0.op === V5Op.GETTABLE && i0.C >= RK_OFFSET) {
                i0.op = V5Op.S_GETFIELD_K;
                i0.C = i0.C - RK_OFFSET;
            } else if (i0.op === V5Op.SETTABLE && i0.B >= RK_OFFSET) {
                i0.op = V5Op.S_SETFIELD_K;
                i0.B = i0.B - RK_OFFSET;
            } else if (i0.op === V5Op.ADD && i0.B < RK_OFFSET && i0.C >= RK_OFFSET) {
                i0.op = V5Op.S_ADD_K;
                i0.C = i0.C - RK_OFFSET;
            } else if (i0.op === V5Op.SUB && i0.B < RK_OFFSET && i0.C >= RK_OFFSET) {
                i0.op = V5Op.S_SUB_K;
                i0.C = i0.C - RK_OFFSET;
            } else if (i0.op === V5Op.MUL && i0.B < RK_OFFSET && i0.C >= RK_OFFSET) {
                i0.op = V5Op.S_MUL_K;
                i0.C = i0.C - RK_OFFSET;
            } else if (i0.op === V5Op.MOD && i0.B < RK_OFFSET && i0.C >= RK_OFFSET) {
                i0.op = V5Op.S_MOD_K;
                i0.C = i0.C - RK_OFFSET;
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

/**
 * Pass 2: Split compacted IR into BasicBlocks, inject Decoy Blocks (L3), and CFF-shuffle.
 */
function buildBasicBlocksAndCFF(instrs, END_MARKER, rng, options) {
    const { doCFF, needFallthrough, decoyCount } = options;
    if (instrs.length === 0) {
        return [{ id: 0, instrs: [{ op: V5Op.RETURN, A: 0, B: 1, C: 0, D: 0, targetIns: null, targetBlock: null }], mode: 0, isDecoy: false }];
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
            op === V5Op.FORLOOP || op === V5Op.F_TEST_JMP ||
            op === V5Op.F_EQ_JMP || op === V5Op.F_LT_JMP || op === V5Op.F_LE_JMP ||
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
        return { blocks, entryBlock: blocks[0], END_BLOCK };
    }

    const entryBlock = blocks[0];

    // Add unreachable decoy basic blocks to poison static lifters / AI
    const realTargets = [...blocks];
    for (let d = 0; d < decoyCount; d++) {
        const dTarget = realTargets[Math.floor(rng() * realTargets.length)];
        const regA = Math.floor(rng() * 4);
        const regB = Math.floor(rng() * 4);
        const dInstrs = [
            { op: V5Op.MOVE, A: regA, B: regB, C: 0, D: 0, targetBlock: null, noMba: false },
            { op: V5Op.ADD, A: regA, B: regA, C: regB, D: 0, targetBlock: null, noMba: false },
            { op: V5Op.JMP, A: 0, B: 0, C: 0, D: 0, targetBlock: dTarget, noMba: false },
        ];
        blocks.push({ id: blocks.length, origStart: -1, origEnd: -1, instrs: dInstrs, mode: 0, isDecoy: true });
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
    return { blocks: finalBlocks, entryBlock: headerBlk, END_BLOCK };
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
                if (ins.op === V5Op.JMP) {
                    ins.op = V5Op.OP_MODE_SWITCH;
                    ins.B = tb.mode;
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
 * Pass 4a: Prepend OP_DECRYPT_BLK to eligible single-entry blocks (length >= 3).
 * Because blocks are split at ALL jump targets, entry at instrs[0] is guaranteed unique!
 */
function insertBlockDecryptHeaders(blocks, END_BLOCK, rng, prob = 0.65) {
    const encryptedBlocks = new Set();
    for (const blk of blocks) {
        if (blk.isEntryHeader || blk.isTrampoline || blk.instrs.length < 3) continue;
        // Skip blocks that start with an instruction whose preceding block might skip into it (cannot happen since we split & skip pairs stay in same block, and conditional skips stay inside blk)
        if (rng() > prob) continue;
        const bodyLen = blk.instrs.length;
        const blockSalt = 1 + Math.floor(rng() * 0xFFFFFF);
        const hdr = {
            op: V5Op.OP_DECRYPT_BLK,
            A: bodyLen,
            B: blockSalt,
            C: 0,
            D: 0,
            targetBlock: null,
            noMba: true,
            isDecryptHdr: true,
        };
        blk.instrs.unshift(hdr);
        encryptedBlocks.add(blk);
    }
    return encryptedBlocks;
}

/**
 * Build SoA arrays [a0, a1, a2, a3, a4] for a single proto after layout,
 * applying per-mode slot permutation, opcode masking, operand XOR, block encryption, and MBA wrapping.
 */
function finalizeProtoSoA(proto, ctx, rng, isRoot = false) {
    const isMax = ctx.level === "max";
    const isBalanced = ctx.level === "normal";
    const tier = proto.tier || (isRoot ? "cold" : "normal");
    const hasClosures = Boolean(proto.hasClosures);
    const hasLoops = Boolean(proto.hasLoops);
    const isHot = (tier === "jit" || tier === "jitmax" || hasLoops);
    // Root top-level proto runs once; child closures hold references to upval cells, never root's _c0.._c4
    const isEphemeral = (isRoot && ctx.level !== "fast");

    const raw = decodeRawInstrs(proto.code);
    let instrs = collapseLoadKX(raw.instrs);
    instrs = fuseAndSpecialize(instrs);

    const irGraph = buildBasicBlocksAndCFF(instrs, raw.END_MARKER, rng, {
        doCFF: ctx.doCFF,
        needFallthrough: ctx.doCFF || isMax,
        decoyCount: isMax ? (2 + Math.floor(rng() * 3)) : (isBalanced ? 1 : 0),
    });

    let entryMode = 0;
    if (isMax && irGraph.blocks.length >= 2) {
        entryMode = applyDualModePartition(irGraph, rng);
    }

    let encryptedBlocks = new Set();
    if (isMax || isBalanced) {
        encryptedBlocks = insertBlockDecryptHeaders(irGraph.blocks, irGraph.END_BLOCK, rng, isMax ? 0.65 : 0.35);
    }

    // Layout blocks sequentially -> assign 1-based PC
    const blockStartPC = new Map();
    let totalInstr = 0;
    for (const blk of irGraph.blocks) {
        blockStartPC.set(blk, totalInstr + 1);
        totalInstr += blk.instrs.length;
    }
    const endPC = totalInstr + 1;

    // Resolve jump targets to concrete 1-based targetPC
    for (const blk of irGraph.blocks) {
        for (const ins of blk.instrs) {
            if (ins.targetBlock) {
                const tPC = ins.targetBlock === irGraph.END_BLOCK ? endPC : blockStartPC.get(ins.targetBlock);
                if (ins.op === V5Op.OP_MODE_SWITCH) {
                    ins.A = tPC;
                } else if (ins.op === V5Op.JMP || ins.op === V5Op.FORPREP || ins.op === V5Op.FORLOOP ||
                    ins.op === V5Op.F_TEST_JMP || ins.op === V5Op.F_TFORLOOP_JMP) {
                    ins.B = tPC;
                } else if (ins.op === V5Op.F_EQ_JMP || ins.op === V5Op.F_LT_JMP ||
                    ins.op === V5Op.F_LE_JMP || ins.op === V5Op.F_TESTSET_JMP ||
                    (ins.op === V5Op.LOADBOOL && ins.C !== 0) ||
                    ins.op === V5Op.TESTSET || ins.op === V5Op.TFORLOOP) {
                    ins.D = tPC;
                }
            }
        }
    }

    // Collect used opcodes (note: keep NOP, MODE_SWITCH, DECRYPT_BLK, MBA_DECODE registered as needed)
    for (const blk of irGraph.blocks) {
        for (const ins of blk.instrs) {
            ctx.usedOps[blk.mode].add(ins.op);
        }
    }

    // Materialize SoA 5-column instruction buffer
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
            const ox = modeCfg.opFieldXor[ins.op];

            const vA = ((ins.A >>> 0) ^ ox[0]) >>> 0;
            const vB = ((ins.B >>> 0) ^ ox[1]) >>> 0;
            const vC = ((ins.C >>> 0) ^ ox[2]) >>> 0;
            const vD = (ins.D >>> 0); // Keep D un-masked (ox[3] === 0) so OP_MBA_DECODE can assume D === 0 cleanly

            cols[modeCfg.role.op][pc - 1] = storedOp;
            cols[modeCfg.role.A][pc - 1] = vA;
            cols[modeCfg.role.B][pc - 1] = vB;
            cols[modeCfg.role.C][pc - 1] = vC;
            cols[modeCfg.role.D][pc - 1] = vD;

            // Track eligible instructions for MBA self-decoding (outside OP_DECRYPT_BLK body, D == 0, non-control)
            const inEncBody = isEncBlk && bi > 0;
            if (isMax && !inEncBody && !ins.noMba && ins.D === 0 &&
                ins.op !== V5Op.OP_DECRYPT_BLK && ins.op !== V5Op.OP_MODE_SWITCH && ins.op !== V5Op.NOP) {
                mbaTargets.push({ pc, mode: blk.mode, storedOp, vA, vB, vC });
            }
            pc++;
        }

        // Apply OP_DECRYPT_BLK LCG+XOR encryption over body [startPcOfBlk+1 .. startPcOfBlk+bodyLen]
        if (isEncBlk) {
            const hdrIns = blk.instrs[0];
            const bodyLen = hdrIns.A;
            const blockSalt = hdrIns.B;
            ctx.usedOps[blk.mode].add(V5Op.NOP);
            let lcg = ((blockSalt ^ ctx.K_TARGET) >>> 0);
            for (let k = 1; k <= bodyLen; k++) {
                const idx = (startPcOfBlk - 1) + k;
                for (let c = 0; c < 5; c++) {
                    lcg = (Math.imul(lcg, 1664525) + 1013904223) >>> 0;
                    cols[c][idx] = (cols[c][idx] ^ lcg) >>> 0;
                }
            }
        }
    }

    // Apply OP_MBA_DECODE_0..3 over ~30% of eligible non-block-encrypted instructions in ONYX (Level 3),
    // skipping hot/jit/jitmax protos so hot loops execute at full speed while cold setup blocks keep full MBA
    if (isMax && !isHot && ctx.mbaCodecs && ctx.mbaCodecs.length > 0) {
        const rate = 0.30;
        for (const t of mbaTargets) {
            if (rng() > rate) continue;
            const cIdx = Math.floor(rng() * ctx.mbaCodecs.length);
            const codec = ctx.mbaCodecs[cIdx];
            const decOp = V5Op.OP_MBA_DECODE_0 + cIdx;
            ctx.usedOps[t.mode].add(decOp);

            const modeCfg = ctx.modes[t.mode];
            const decOpId = modeCfg.opEncode[decOp];
            const decStoredOp = (decOpId ^ ctx.kLo ^ modeCfg.mSalt) >>> 0;
            const mbaKey = (((t.pc * 2654435761) >>> 0) ^ ctx.K_TARGET) >>> 0;

            cols[modeCfg.role.op][t.pc - 1] = decStoredOp;
            cols[modeCfg.role.A][t.pc - 1] = codec.encode(t.vA, mbaKey);
            cols[modeCfg.role.B][t.pc - 1] = codec.encode(t.vB, mbaKey);
            cols[modeCfg.role.C][t.pc - 1] = codec.encode(t.vC, mbaKey);
            cols[modeCfg.role.D][t.pc - 1] = codec.encode(t.storedOp, mbaKey);
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
        tier,
        isHot,
        hasClosures,
        hasLoops,
        isEphemeral,
        protos: v5Protos,
    };
}

/**
 * Create Sentinel v5.0 per-build IR & ISA context and compile chunk tree to v5 IR.
 */
export function buildV5IR(rootChunk, options, rng) {
    const level = options.level || "max";
    const isMax = level === "max";
    const numModes = isMax ? 2 : 1;

    // Non-zero 16-bit integrity derivation key (both low & high bytes guaranteed non-zero)
    const kLo = 1 + Math.floor(rng() * 254);
    const kHi = 1 + Math.floor(rng() * 254);
    const K_TARGET = ((kHi << 8) | kLo) >>> 0;

    const createModeConfig = (modeId) => {
        const pool = Array.from({ length: V5_OPCODE_COUNT }, (_, i) => i + 1);
        for (let i = pool.length - 1; i > 0; i--) {
            const j = Math.floor(rng() * (i + 1));
            [pool[i], pool[j]] = [pool[j], pool[i]];
        }
        const opEncode = new Array(V5_OPCODE_COUNT);
        const opDecode = {};
        const opFieldXor = new Array(V5_OPCODE_COUNT);
        for (let op = 0; op < V5_OPCODE_COUNT; op++) {
            opEncode[op] = pool[op];
            opDecode[pool[op]] = op;
            if (level === "fast") {
                opFieldXor[op] = [0, 0, 0, 0];
            } else {
                opFieldXor[op] = [
                    Math.floor(rng() * 0xFFFF),
                    Math.floor(rng() * 0xFFFF),
                    Math.floor(rng() * 0xFFFF),
                    0,
                ];
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
            opFieldXor,
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
        isFastMode: level === "fast",
        doCFF: options.doCFF !== false,
        K_TARGET,
        kLo,
        kHi,
        numModes,
        modes,
        usedOps,
        mbaCodecs,
    };

    const v5Root = finalizeProtoSoA(rootChunk, ctx, rng, true);
    return { v5Root, ctx };
}
