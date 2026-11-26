// language: JavaScript, file: v5-codegen.js, target: Node.js ESM
// Sentinel v5.3 APEX Runtime Codegen (ONYX / OPAL):
// - Shuffled Primitive Metatable `U` + Pure-Lua buffer/bit32/f64 fallbacks
// - 128-Bit (4x32-bit) ARX Integrity Derivation Key Vector `[K0..K3]` + IEEE-754 -0.0 Buffer Key + Traps + PlaceId Lock + Strict Roblox C-Engine Fingerprint
// - Zero-Oracle Sharded Function-Table Trampoline Deserializer (Drop-256 128-bit RC4+ARX + MAC32 + AoS Interleaved Rolling LCG)
// - Path-Dependent Rolling State (`_st`) + Universal Once-Per-Block Decryption + Merged Multi-Semantics & Split Micro-Op Handlers
// - Zero-Plaintext Hashed Environment Bridge & Sealed Lazy Master Constant Pool
// - Tier A Hardened Native Functions (`__PBZ_NF__`) + `__PBZ_CRASH__`
// - FASTCALL-Hoisted Dual-Mode Masked BST VM + Register Frame Pool + Ephemeral Self-Wiping Root Proto

import { V5Op, V5_OPCODE_COUNT } from "./bytecode.js";
import { emitOpaquePredicate, arxMix32 } from "./v5-mba.js";
import { emitHardenedNativeLua } from "./v5-macros-native.js";

function toUTF8Bytes(s) {
    return Array.from(Buffer.from(s, "utf8"));
}

function luaByteString(sOrBytes) {
    const bytes = Array.isArray(sOrBytes) ? sOrBytes : toUTF8Bytes(sOrBytes);
    let out = '"';
    for (const b of bytes) {
        const v = b & 0xFF;
        if (v === 34) out += '\\"';
        else if (v === 92) out += '\\\\';
        else if (v === 10) out += '\\n';
        else if (v === 13) out += '\\r';
        else if (v < 32 || v > 126) out += '\\' + v.toString().padStart(3, '0');
        else out += String.fromCharCode(v);
    }
    return out + '"';
}

function saltedFnv1a32(str, initOffset) {
    let h = initOffset >>> 0;
    const bytes = toUTF8Bytes(str);
    for (let i = 0; i < bytes.length; i++) {
        h ^= bytes[i];
        h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h >>> 0;
}

/**
 * Generates balanced Binary Search Tree dispatcher over sorted concrete opcode IDs.
 * Anti-vmmap: every internal node transforms `_op` (`bxor`/`+`) into a temp boolean local `_z`
 * so static AST matchers checking `op < K` fail completely, while runtime executes in O(log N).
 */
function buildAntiVmmapBST(entries, opVar, rng, vmSym, mode) {
    if (entries.length === 0) return "";
    if (entries.length === 1) {
        return entries[0].body;
    }

    const useTransform = mode !== "fast";
    const tmpVar = "_z";

    function buildNode(lo, hi) {
        if (lo === hi) {
            return entries[lo].body;
        }
        if (hi - lo === 1) {
            const left = entries[lo];
            const right = entries[hi];
            if (!useTransform) {
                return `if ${opVar}==${left.id} then ${left.body} else ${right.body} end`;
            }
            const form = Math.floor(rng() * 3);
            if (form === 0) {
                const k = 2 + Math.floor(rng() * 5);
                return `local ${tmpVar}=((${opVar}*${k})==${left.id * k});if ${tmpVar} then ${left.body} else ${right.body} end`;
            } else if (form === 1) {
                const off = 1 + Math.floor(rng() * 500);
                return `local ${tmpVar}=((${opVar}+${off})~=${left.id + off});if ${tmpVar} then ${right.body} else ${left.body} end`;
            } else {
                const mid = left.id;
                return `if not(${opVar}>${mid})then ${left.body} else ${right.body} end`;
            }
        }
        const midIdx = (lo + hi) >> 1;
        const pivot = entries[midIdx].id;
        const thenCode = buildNode(lo, midIdx);
        const elseCode = buildNode(midIdx + 1, hi);

        if (!useTransform) {
            return `if ${opVar}<=${pivot} then ${thenCode} else ${elseCode} end`;
        }
        const style = Math.floor(rng() * 4);
        if (style === 0) {
            const off = 1 + Math.floor(rng() * 900);
            return `local ${tmpVar}=((${opVar}+${off})<=${pivot + off});if ${tmpVar} then ${thenCode} else ${elseCode} end`;
        } else if (style === 1) {
            const off = 1 + Math.floor(rng() * 900);
            return `local ${tmpVar}=((${opVar}+${off})>${pivot + off});if ${tmpVar} then ${elseCode} else ${thenCode} end`;
        } else if (style === 2) {
            const k = 1 + Math.floor(rng() * 5);
            return `local ${tmpVar}=((${opVar}*${k})<(${(pivot + 1) * k}));if ${tmpVar} then ${thenCode} else ${elseCode} end`;
        } else {
            return `if not(${opVar}>${pivot})then ${thenCode} else ${elseCode} end`;
        }
    }

    return buildNode(0, entries.length - 1);
}

/**
 * Generates opcode handler body inside an isolated `do ... end` (or direct) block
 * using hoisted FASTCALL primitives (`vmSym`), randomized SoA slot vars (`modeSlots`),
 * per-proto shifted `_rb`/`_kb` bases, dynamic PC+Key algebraic operand decoders,
 * per-opcode reg bias, and randomized `rkOffset`.
 */
function buildOpcodeHandlerBody(op, modeCfg, vCtx) {
    const {
        uSym, vmSym, rVar, kVar, envVar, pcVar, topVar, upVar, poolVar, openUvVar,
        modeVar, k1Var, k2Var, rbVar, kbVar, stVar, mbaDecVar, isFastMode, rkOffset, qVar, cArrVars, mergeTags, rng,
    } = vCtx;

    const slots = modeSlotsCompat(modeCfg, cArrVars);
    const sA = slots[modeCfg.role.A];
    const sB = slots[modeCfg.role.B];
    const sC = slots[modeCfg.role.C];
    const sD = slots[modeCfg.role.D];
    const sOp = slots[modeCfg.role.op];

    const bias = modeCfg.opRegBias[op] || 0;

    // Direct zero-modulo array reads (operands already decrypted once per block into sA..sD on entry!)
    const emitDynDec = (arr, _spec, subtractVal = 0) => {
        const rawEl = `${arr}[${qVar}]`;
        return subtractVal > 0 ? `(${rawEl}-${subtractVal})` : rawEl;
    };

    // decA: raw 0-based field A (unbiased); regA: Lua 1-based register index (_rb + plainA)
    const decA = emitDynDec(sA, null, bias);
    const regA = bias > 0
        ? `(${emitDynDec(sA, null, 0)}+${rbVar}-${bias})`
        : `(${decA}+${rbVar})`;
    const decB = emitDynDec(sB, null, 0);
    const decC = emitDynDec(sC, null, 0);
    const decD = `${sD}[${qVar}]`;

    // Edge rolling key update on taken jump/branch
    const stJump = isFastMode ? `` : `;${stVar}=${vmSym.bx}(${stVar},${decD})`;
    const packedBranch = (fieldExpr, cmpOp, lhsFn, rhsFn) => {
        if (isFastMode) {
            return `do local _x=${decB};local _y=${decC};if(${lhsFn("_x")}${cmpOp}${rhsFn("_y")})==(${fieldExpr}~=0)then ${pcVar}=${decD} end end`;
        }
        return `do local _x=${decB};local _y=${decC};local _af=${fieldExpr};local _fl=(_af%2~=0);local _tp=(_af-(_fl and 1 or 0))/2;if(${lhsFn("_x")}${cmpOp}${rhsFn("_y")})==_fl then ${pcVar}=_tp;${stVar}=${vmSym.bx}(${stVar},${decD})end end`;
    };

    const rk = (expr) => {
        const t = `(${expr})`;
        return `((${t}<${rkOffset})and ${rVar}[${t}+${rbVar}]or ${kVar}[${t}-${rkOffset}+${kbVar}])`;
    };

    const wipeEp = isFastMode ? `` : `if _ep then for _wi=1,_ni do ${cArrVars[0]}[_wi]=nil;${cArrVars[1]}[_wi]=nil;${cArrVars[2]}[_wi]=nil;${cArrVars[3]}[_wi]=nil;${cArrVars[4]}[_wi]=nil end end;`;
    const recFrame = `if not ${openUvVar} and _fpn<64 then _tclr(${rVar});_fpn=_fpn+1;_fp[_fpn]=${rVar} end;`;
    const yieldChk = `if _tw then _sc=_sc+1;if _sc%65536==0 then _tw() end end;`;

    // Zero-table.pack fast paths for C==1 (void) and C==2 (1 return value) using 1-based _pa = decA + _rb
    const emitVarCall = (bExpr, cExpr) => {
        return `local _b=${bExpr};local _c=${cExpr};` +
            `if _c==1 then ` +
                `if _b==1 then _f() ` +
                `elseif _b==2 then _f(${rVar}[_pa+1]) ` +
                `elseif _b==3 then _f(${rVar}[_pa+1],${rVar}[_pa+2]) ` +
                `elseif _b==4 then _f(${rVar}[_pa+1],${rVar}[_pa+2],${rVar}[_pa+3]) ` +
                `elseif _b==0 then _f(${vmSym.tu}(${rVar},_pa+1,${topVar})) ` +
                `else _f(${vmSym.tu}(${rVar},_pa+1,_pa+_b-1)) end ` +
            `elseif _c==2 then ` +
                `if _b==1 then ${rVar}[_pa]=_f() ` +
                `elseif _b==2 then ${rVar}[_pa]=_f(${rVar}[_pa+1]) ` +
                `elseif _b==3 then ${rVar}[_pa]=_f(${rVar}[_pa+1],${rVar}[_pa+2]) ` +
                `elseif _b==4 then ${rVar}[_pa]=_f(${rVar}[_pa+1],${rVar}[_pa+2],${rVar}[_pa+3]) ` +
                `elseif _b==0 then ${rVar}[_pa]=_f(${vmSym.tu}(${rVar},_pa+1,${topVar})) ` +
                `else ${rVar}[_pa]=_f(${vmSym.tu}(${rVar},_pa+1,_pa+_b-1)) end ` +
            `else ` +
                `local _r;` +
                `if _b==1 then _r=${vmSym.tp}(_f()) ` +
                `elseif _b==2 then _r=${vmSym.tp}(_f(${rVar}[_pa+1])) ` +
                `elseif _b==3 then _r=${vmSym.tp}(_f(${rVar}[_pa+1],${rVar}[_pa+2])) ` +
                `elseif _b==4 then _r=${vmSym.tp}(_f(${rVar}[_pa+1],${rVar}[_pa+2],${rVar}[_pa+3])) ` +
                `elseif _b==0 then _r=${vmSym.tp}(_f(${vmSym.tu}(${rVar},_pa+1,${topVar}))) ` +
                `else _r=${vmSym.tp}(_f(${vmSym.tu}(${rVar},_pa+1,_pa+_b-1))) end;` +
                `if _c==0 then for _i=1,_r.n do ${rVar}[_pa+_i-1]=_r[_i] end;${topVar}=_pa+_r.n-1 ` +
                `else for _i=1,_c-1 do ${rVar}[_pa+_i-1]=_r[_i] end end ` +
            `end `;
    };

    switch (op) {
        case V5Op.NOP:
            return ``;
        case V5Op.LOADK:
            return `${rVar}[${regA}]=${kVar}[${decB}+${kbVar}]`;
        case V5Op.LOADK_V2:
            return `${rVar}[${decC}+${rbVar}]=${kVar}[${decA}+${kbVar}]`;
        case V5Op.LOADNIL:
            return `do local _pa=${regA};for _i=_pa,_pa+${decB} do ${rVar}[_i]=nil end end`;
        case V5Op.LOADBOOL:
            return `${rVar}[${regA}]=(${decB}~=0);if ${decC}~=0 then ${pcVar}=${decC}${stJump} end`;
        case V5Op.MOVE:
            return `${rVar}[${regA}]=${rVar}[${decB}+${rbVar}]`;
        case V5Op.MOVE_V2:
            return `${rVar}[${decB}+${rbVar}]=${rVar}[${regA}]`;
        case V5Op.GETGLOBAL:
            return `${rVar}[${regA}]=${envVar}[${kVar}[${decB}+${kbVar}]]`;
        case V5Op.GETGLOBAL_V2:
            return `${rVar}[${decC}+${rbVar}]=${envVar}[${kVar}[${decA}+${kbVar}]]`;
        case V5Op.SETGLOBAL:
            return `${envVar}[${kVar}[${decB}+${kbVar}]]=${rVar}[${regA}]`;
        case V5Op.GETTABLE:
            return `do local _t=${decC};${rVar}[${regA}]=${rVar}[${decB}+${rbVar}][${rk("_t")}]end`;
        case V5Op.GETTABLE_V2:
            return `do local _t=${decB};${rVar}[${decC}+${rbVar}]=${rVar}[${regA}][${rk("_t")}]end`;
        case V5Op.SETTABLE:
            return `do local _k=${decB};local _v=${decC};${rVar}[${regA}][${rk("_k")}]=${rk("_v")}end`;
        case V5Op.SETTABLE_V2:
            return `do local _k=${decA};local _v=${decB};${rVar}[${decC}+${rbVar}][${rk("_k")}]=${rk("_v")}end`;
        case V5Op.NEWTABLE:
            return `${rVar}[${regA}]={}`;
        case V5Op.ADD:
            return `do local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}+${rk("_y")}end`;
        case V5Op.ADD_V2:
            return `do local _x=${decA};local _y=${decB};${rVar}[${decC}+${rbVar}]=${rk("_x")}+${rk("_y")}end`;
        case V5Op.SUB:
            return `do local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}-${rk("_y")}end`;
        case V5Op.SUB_V2:
            return `do local _x=${decA};local _y=${decB};${rVar}[${decC}+${rbVar}]=${rk("_x")}-${rk("_y")}end`;
        case V5Op.MUL:
            return `do local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}*${rk("_y")}end`;
        case V5Op.DIV:
            return `do local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}/${rk("_y")}end`;
        case V5Op.MOD:
            return `do local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}%${rk("_y")}end`;
        case V5Op.POW:
            return `do local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}^${rk("_y")}end`;
        case V5Op.IDIV:
            return `do local _x=${decB};local _y=${decC};${rVar}[${regA}]=${vmSym.mf}(${rk("_x")}/${rk("_y")})end`;
        case V5Op.UNM:
            return `${rVar}[${regA}]=-${rVar}[${decB}+${rbVar}]`;
        case V5Op.NOT:
            return `${rVar}[${regA}]=not ${rVar}[${decB}+${rbVar}]`;
        case V5Op.LEN:
            return `${rVar}[${regA}]=#${rVar}[${decB}+${rbVar}]`;
        case V5Op.CONCAT:
            return `do local _b=${decB};local _e=${decC};local _acc=${rVar}[_e+${rbVar}];for _i=_e-1,_b,-1 do _acc=${rVar}[_i+${rbVar}].._acc end;${rVar}[${regA}]=_acc end`;
        case V5Op.JMP:
            return `${yieldChk}${pcVar}=${decB}${stJump}`;
        case V5Op.JMP_V2:
            return `${yieldChk}${pcVar}=${decC}${stJump}`;
        case V5Op.EQ:
            return `do local _x=${decB};local _y=${decC};if(${rk("_x")}==${rk("_y")})~=(${decA}~=0)then ${pcVar}=${pcVar}+1 end end`;
        case V5Op.LT:
            return `do local _x=${decB};local _y=${decC};if(${rk("_x")}<${rk("_y")})~=(${decA}~=0)then ${pcVar}=${pcVar}+1 end end`;
        case V5Op.LE:
            return `do local _x=${decB};local _y=${decC};if(${rk("_x")}<=${rk("_y")})~=(${decA}~=0)then ${pcVar}=${pcVar}+1 end end`;
        case V5Op.TEST:
            return `if(not ${rVar}[${regA}])==(${decC}~=0)then ${pcVar}=${pcVar}+1 end`;
        case V5Op.TESTSET:
            return isFastMode
                ? `do local _bv=${rVar}[${decB}+${rbVar}];if(not _bv)==(${decC}~=0)then ${pcVar}=${decD} else ${rVar}[${regA}]=_bv end end`
                : `do local _bv=${rVar}[${decB}+${rbVar}];local _af=${decC};local _fl=(_af%2~=0);local _tp=(_af-(_fl and 1 or 0))/2;if(not _bv)==_fl then ${pcVar}=_tp;${stVar}=${vmSym.bx}(${stVar},${decD}) else ${rVar}[${regA}]=_bv end end`;
        case V5Op.CALL:
            return `do local _pa=${regA};local _f=${rVar}[_pa];${emitVarCall(decB, decC)}end`;
        case V5Op.TAILCALL:
            return `do local _pa=${regA};local _b=${decB};local _f=${rVar}[_pa];${wipeEp}` +
                `if _b==1 then return _f() ` +
                `elseif _b==2 then return _f(${rVar}[_pa+1]) ` +
                `elseif _b==3 then return _f(${rVar}[_pa+1],${rVar}[_pa+2]) ` +
                `elseif _b==4 then return _f(${rVar}[_pa+1],${rVar}[_pa+2],${rVar}[_pa+3]) ` +
                `elseif _b==0 then return _f(${vmSym.tu}(${rVar},_pa+1,${topVar})) ` +
                `else return _f(${vmSym.tu}(${rVar},_pa+1,_pa+_b-1)) end end`;
        case V5Op.RETURN:
            return `do local _pa=${regA};local _b=${decB};` +
                `if _b==1 then ${wipeEp}${recFrame}return ` +
                `elseif _b==2 then local _r1=${rVar}[_pa];${wipeEp}${recFrame}return _r1 ` +
                `elseif _b==3 then local _r1,_r2=${rVar}[_pa],${rVar}[_pa+1];${wipeEp}${recFrame}return _r1,_r2 ` +
                `elseif _b==0 then ${wipeEp}return ${vmSym.tu}(${rVar},_pa,${topVar}) ` +
                `else ${wipeEp}return ${vmSym.tu}(${rVar},_pa,_pa+_b-2) end end`;
        case V5Op.RETURN_V2:
            return `do local _pa=${decC}+${rbVar};local _b=${decA};` +
                `if _b==1 then ${wipeEp}${recFrame}return ` +
                `elseif _b==2 then local _r1=${rVar}[_pa];${wipeEp}${recFrame}return _r1 ` +
                `elseif _b==3 then local _r1,_r2=${rVar}[_pa],${rVar}[_pa+1];${wipeEp}${recFrame}return _r1,_r2 ` +
                `elseif _b==0 then ${wipeEp}return ${vmSym.tu}(${rVar},_pa,${topVar}) ` +
                `else ${wipeEp}return ${vmSym.tu}(${rVar},_pa,_pa+_b-2) end end`;
        case V5Op.FORPREP:
            return `do local _pa=${regA};${rVar}[_pa]=${rVar}[_pa]-${rVar}[_pa+2];${pcVar}=${decB}${stJump} end`;
        case V5Op.FORLOOP:
            return `do ${yieldChk}local _pa=${regA};local _stp=${rVar}[_pa+2];local _ix=${rVar}[_pa]+_stp;${rVar}[_pa]=_ix;local _lm=${rVar}[_pa+1];` +
                `if(_stp>0 and _ix<=_lm)or(_stp<=0 and _ix>=_lm)then ${pcVar}=${decB}${stJump};${rVar}[_pa+3]=_ix end end`;
        case V5Op.TFORLOOP:
            return isFastMode
                ? `do ${yieldChk}local _pa=${regA};local _c=${decC};local _r={${rVar}[_pa](${rVar}[_pa+1],${rVar}[_pa+2])};` +
                  `for _i=1,_c do ${rVar}[_pa+2+_i]=_r[_i]end;if _r[1]~=nil then ${rVar}[_pa+2]=_r[1];${pcVar}=${decD} end end`
                : `do ${yieldChk}local _pa=${regA};local _c=${decC};local _r={${rVar}[_pa](${rVar}[_pa+1],${rVar}[_pa+2])};` +
                  `for _i=1,_c do ${rVar}[_pa+2+_i]=_r[_i]end;if _r[1]~=nil then ${rVar}[_pa+2]=_r[1];${pcVar}=${decB}${stJump} end end`;
        case V5Op.ITERPREP:
            return `do local _pa=${regA};local _it=${rVar}[_pa];local _ity=${vmSym.ty}(_it);` +
                `if _ity=="table"or _ity=="userdata"then local _ok,_mt=${vmSym.pc}(${vmSym.gm},_it);` +
                `if _ok and ${vmSym.ty}(_mt)=="table"and _mt.__iter then ${rVar}[_pa],${rVar}[_pa+1],${rVar}[_pa+2]=_mt.__iter(_it)` +
                `elseif _ity=="table"then ${rVar}[_pa]=${vmSym.nx};${rVar}[_pa+1]=_it;${rVar}[_pa+2]=nil end end end`;
        case V5Op.SETLIST:
            return `do local _pa=${regA};local _t=${rVar}[_pa];local _b=${decB};if _b==0 then _b=${topVar}-_pa end;local _bs=${decC}-1;for _i=1,_b do _t[_bs+_i]=${rVar}[_pa+_i]end end`;
        case V5Op.CLOSURE:
            return `do local _pr=${poolVar}[_pr[7][${decB}+1]];` +
                `if _pr then local _nU={};local _ul=_pr[6];for _ui=1,#_ul do local _ud=_ul[_ui];` +
                `if _ud[1]==1 then if not ${openUvVar} then ${openUvVar}={} end;local _bk;local _tg=_ud[2]+${rbVar};for _oi=1,#${openUvVar} do if ${openUvVar}[_oi][2]==_tg then _bk=${openUvVar}[_oi];break end end;` +
                `if not _bk then _bk={${rVar},_tg};${openUvVar}[#${openUvVar}+1]=_bk end;_nU[_ui]=_bk else _nU[_ui]=${upVar}[_ud[2]+1]end end;` +
                `if not _pr[4]and _pr[2]<=4 then local _np=_pr[2];` +
                `if _np==0 then ${rVar}[${regA}]=function()return _vm(_pr,_nU,${envVar})end ` +
                `elseif _np==1 then ${rVar}[${regA}]=function(_1)return _vm(_pr,_nU,${envVar},_1)end ` +
                `elseif _np==2 then ${rVar}[${regA}]=function(_1,_2)return _vm(_pr,_nU,${envVar},_1,_2)end ` +
                `elseif _np==3 then ${rVar}[${regA}]=function(_1,_2,_3)return _vm(_pr,_nU,${envVar},_1,_2,_3)end ` +
                `else ${rVar}[${regA}]=function(_1,_2,_3,_4)return _vm(_pr,_nU,${envVar},_1,_2,_3,_4)end end ` +
                `else ${rVar}[${regA}]=function(...)local _ac=${vmSym.sel}("#",...);local _ag={...};return _vm(_pr,_nU,${envVar},_ag[1],_ag[2],_ag[3],_ag[4],_ag,_ac)end end ` +
                `else ${rVar}[${regA}]=nil end end`;
        case V5Op.VARARG:
            return `do local _pa=${regA};local _b=${decB};if _b==0 then if _vac>0 then for _i=1,_vac do ${rVar}[_pa+_i-1]=_va[_i] end end;${topVar}=_pa+_vac-1 else for _i=1,_b-1 do ${rVar}[_pa+_i-1]=_va and _va[_i]or nil end end end`;
        case V5Op.SELF:
            return `do local _pa=${regA};local _o=${rVar}[${decB}+${rbVar}];local _fc=${decC};${rVar}[_pa+1]=_o;${rVar}[_pa]=_o[${rk("_fc")}]end`;
        case V5Op.GETUPVAL:
            return `do local _b=${upVar}[${decB}+1];if _b[2]then ${rVar}[${regA}]=_b[1][_b[2]]else ${rVar}[${regA}]=_b[1]end end`;
        case V5Op.SETUPVAL:
            return `do local _b=${upVar}[${decB}+1];if _b[2]then _b[1][_b[2]]=${rVar}[${regA}]else _b[1]=${rVar}[${regA}]end end`;
        case V5Op.CLOSEUPVAL:
            return `if ${openUvVar} then do local _pa=${regA};local _n=0;for _i=1,#${openUvVar} do local _b=${openUvVar}[_i];if _b[2]>=_pa then _b[1]=_b[1][_b[2]];_b[2]=nil else _n=_n+1;${openUvVar}[_n]=_b end end;for _i=_n+1,#${openUvVar} do ${openUvVar}[_i]=nil end end end`;
        case V5Op.PCALL:
            return `do local _pa=${regA};local _b=${decB};local _c=${decC};local _f=${rVar}[_pa];local _we=_b==0 and ${topVar} or _pa+_b-1;local _r;` +
                `if _b==1 then _r=${vmSym.tp}(${vmSym.pc}(_f)) ` +
                `elseif _b==2 then _r=${vmSym.tp}(${vmSym.pc}(_f,${rVar}[_pa+1])) ` +
                `elseif _b==3 then _r=${vmSym.tp}(${vmSym.pc}(_f,${rVar}[_pa+1],${rVar}[_pa+2])) ` +
                `else _r=${vmSym.tp}(${vmSym.pc}(_f,${vmSym.tu}(${rVar},_pa+1,_we))) end;` +
                `if _c==0 then for _i=1,_r.n do ${rVar}[_pa+_i-1]=_r[_i] end;${topVar}=_pa+_r.n-1 else for _i=1,_c-1 do ${rVar}[_pa+_i-1]=_r[_i] end end;` +
                `if _b==0 or _b>1 then local _ws=_c==0 and(_pa+_r.n)or(_pa+_c-1);for _wi=_ws,_we do ${rVar}[_wi]=nil end end end`;
        case V5Op.XPCALL:
            return `do local _pa=${regA};local _b=${decB};local _c=${decC};local _f=${rVar}[_pa];local _eh=${rVar}[_pa+1];local _we=_b==0 and ${topVar} or _pa+_b-1;local _r;` +
                `if _b==1 or _b==2 then _r=${vmSym.tp}(${vmSym.xpc}(_f,_eh)) ` +
                `elseif _b==3 then _r=${vmSym.tp}(${vmSym.xpc}(_f,_eh,${rVar}[_pa+2])) ` +
                `else _r=${vmSym.tp}(${vmSym.xpc}(_f,_eh,${vmSym.tu}(${rVar},_pa+2,_we))) end;` +
                `if _c==0 then for _i=1,_r.n do ${rVar}[_pa+_i-1]=_r[_i] end;${topVar}=_pa+_r.n-1 else for _i=1,_c-1 do ${rVar}[_pa+_i-1]=_r[_i] end end;` +
                `if _b==0 or _b>2 then local _ws=_c==0 and(_pa+_r.n)or(_pa+_c-1);for _wi=_ws,_we do ${rVar}[_wi]=nil end end end`;
        case V5Op.F_TEST_JMP:
            return `if(not ${rVar}[${regA}])~=(${decC}~=0)then ${pcVar}=${decB}${stJump} end`;
        case V5Op.F_TEST_JMP_V2:
            return `if(not ${rVar}[${decC}+${rbVar}])~=(${decB}~=0)then ${pcVar}=${decA}${stJump} end`;
        case V5Op.F_EQ_JMP:
            return packedBranch(decA, "==", rk, rk);
        case V5Op.F_EQ_JMP_V2:
            return isFastMode
                ? `do local _x=${decA};local _y=${decB};if(${rk("_x")}==${rk("_y")})==(${decC}~=0)then ${pcVar}=${decD} end end`
                : `do local _x=${decA};local _y=${decB};local _af=${decC};local _fl=(_af%2~=0);local _tp=(_af-(_fl and 1 or 0))/2;if(${rk("_x")}==${rk("_y")})==_fl then ${pcVar}=_tp;${stVar}=${vmSym.bx}(${stVar},${decD})end end`;
        case V5Op.F_LT_JMP:
            return packedBranch(decA, "<", rk, rk);
        case V5Op.F_LE_JMP:
            return packedBranch(decA, "<=", rk, rk);
        case V5Op.F_TESTSET_JMP:
            return isFastMode
                ? `do local _bv=${rVar}[${decB}+${rbVar}];if(not _bv)~=(${decC}~=0)then ${rVar}[${regA}]=_bv;${pcVar}=${decD} end end`
                : `do local _bv=${rVar}[${decB}+${rbVar}];local _af=${decC};local _fl=(_af%2~=0);local _tp=(_af-(_fl and 1 or 0))/2;if(not _bv)~=_fl then ${rVar}[${regA}]=_bv;${pcVar}=_tp;${stVar}=${vmSym.bx}(${stVar},${decD})end end`;
        case V5Op.F_TFORLOOP_JMP:
            return `do ${yieldChk}local _pa=${regA};local _c=${decC};local _r={${rVar}[_pa](${rVar}[_pa+1],${rVar}[_pa+2])};` +
                `for _i=1,_c do ${rVar}[_pa+2+_i]=_r[_i]end;if _r[1]~=nil then ${rVar}[_pa+2]=_r[1]else ${pcVar}=${decB}${stJump} end end`;
        case V5Op.F_GGET:
            return `do local _g=${envVar}[${kVar}[${decB}+${kbVar}]];${rVar}[${regA}]=_g;local _t=${decD};${rVar}[${decC}+${rbVar}]=_g[${rk("_t")}]end`;
        case V5Op.F_LOADKK:
            return `${rVar}[${regA}]=${kVar}[${decB}+${kbVar}];${rVar}[${decC}+${rbVar}]=${kVar}[${decD}+${kbVar}]`;
        case V5Op.F_MOVE_MOVE:
            return `${rVar}[${regA}]=${rVar}[${decB}+${rbVar}];${rVar}[${decC}+${rbVar}]=${rVar}[${decD}+${rbVar}]`;
        case V5Op.F_SELF_CALL:
            return `do local _pa=${regA};local _o=${rVar}[${decB}+${rbVar}];local _fc=${decC};local _d=${decD};${rVar}[_pa+1]=_o;local _f=_o[${rk("_fc")}];${rVar}[_pa]=_f;` +
                `${emitVarCall(`${vmSym.rs}(_d,16)`, `${vmSym.ba}(_d,65535)`)}end`;
        case V5Op.F_GGET_CALL:
            return `do local _pa=${regA};local _g=${envVar}[${kVar}[${decB}+${kbVar}]];local _fc=${decC};local _d=${decD};local _f=_g[${rk("_fc")}];${rVar}[_pa]=_f;` +
                `${emitVarCall(`${vmSym.rs}(_d,16)`, `${vmSym.ba}(_d,65535)`)}end`;
        case V5Op.F_LOADK_RET:
            return `do local _r1=${kVar}[${decB}+${kbVar}];${wipeEp}${recFrame}return _r1 end`;
        case V5Op.F_MOVE_RET:
            return `do ${rVar}[${regA}]=${rVar}[${decB}+${rbVar}];local _pa=${decC}+${rbVar};local _rb2=${decD};` +
                `if _rb2==1 then ${wipeEp}${recFrame}return ` +
                `elseif _rb2==2 then local _r1=${rVar}[_pa];${wipeEp}${recFrame}return _r1 ` +
                `elseif _rb2==0 then ${wipeEp}return ${vmSym.tu}(${rVar},_pa,${topVar}) ` +
                `else ${wipeEp}return ${vmSym.tu}(${rVar},_pa,_pa+_rb2-2) end end`;
        case V5Op.S_CALL0:
            return `do local _pa=${regA};${rVar}[_pa]=${rVar}[_pa]()end`;
        case V5Op.S_CALL1:
            return `do local _pa=${regA};${rVar}[_pa]=${rVar}[_pa](${rVar}[_pa+1])end`;
        case V5Op.S_CALL2:
            return `do local _pa=${regA};${rVar}[_pa]=${rVar}[_pa](${rVar}[_pa+1],${rVar}[_pa+2])end`;
        case V5Op.S_CALL0_VOID:
            return `do local _pa=${regA};${rVar}[_pa]()end`;
        case V5Op.S_CALL1_VOID:
            return `do local _pa=${regA};${rVar}[_pa](${rVar}[_pa+1])end`;
        case V5Op.S_CALL2_VOID:
            return `do local _pa=${regA};${rVar}[_pa](${rVar}[_pa+1],${rVar}[_pa+2])end`;
        case V5Op.S_CALL3:
            return `do local _pa=${regA};${rVar}[_pa]=${rVar}[_pa](${rVar}[_pa+1],${rVar}[_pa+2],${rVar}[_pa+3])end`;
        case V5Op.S_GETFIELD_K:
            return `${rVar}[${regA}]=${rVar}[${decB}+${rbVar}][${kVar}[${decC}+${kbVar}]]`;
        case V5Op.S_SETFIELD_K:
            return `do local _v=${decC};${rVar}[${regA}][${kVar}[${decB}+${kbVar}]]=${rk("_v")}end`;
        case V5Op.S_UPVAL_GET:
            return `do local _b=${upVar}[${decB}+1];local _uv=(_b[2]and _b[1][_b[2]]or _b[1]);${rVar}[${regA}]=_uv;local _t=${decD};${rVar}[${decC}+${rbVar}]=_uv[${rk("_t")}]end`;
        case V5Op.S_ADD_K:
            return `${rVar}[${regA}]=${rVar}[${decB}+${rbVar}]+${kVar}[${decC}+${kbVar}]`;
        case V5Op.S_SUB_K:
            return `${rVar}[${regA}]=${rVar}[${decB}+${rbVar}]-${kVar}[${decC}+${kbVar}]`;
        case V5Op.S_MUL_K:
            return `${rVar}[${regA}]=${rVar}[${decB}+${rbVar}]*${kVar}[${decC}+${kbVar}]`;
        case V5Op.S_MOD_K:
            return `${rVar}[${regA}]=${rVar}[${decB}+${rbVar}]%${kVar}[${decC}+${kbVar}]`;
        case V5Op.F_NEWTAB_SET:
            return `do local _v=${decC};local _t={};_t[${kVar}[${decB}+${kbVar}]]=${rk("_v")};${rVar}[${regA}]=_t end`;
        case V5Op.F_GGET_SET:
            return `do local _v=${decA};local _g=${envVar}[${kVar}[${decB}+${kbVar}]];${rVar}[${decD}+${rbVar}]=_g;_g[${kVar}[${decC}+${kbVar}]]=${rk("_v")}end`;
        case V5Op.F_LOADK_CALL1:
            return `do local _pa=${regA};local _kv=${kVar}[${decB}+${kbVar}];${rVar}[_pa+1]=_kv;${rVar}[_pa]=${rVar}[_pa](_kv)end`;
        case V5Op.F_LOADK_CALL1_VOID:
            return `do local _pa=${regA};local _kv=${kVar}[${decB}+${kbVar}];${rVar}[_pa+1]=_kv;${rVar}[_pa](_kv)end`;
        case V5Op.OP_MODE_SWITCH:
            return `${pcVar}=${decA};${modeVar}=${decB}${stJump}`;
        case V5Op.OP_BLK_ENTER: {
            const stepStored = (modeCfg.opEncode[V5Op.OP_STATE_STEP] ^ vCtx.kLo ^ modeCfg.mSalt) >>> 0;
            const c0 = cArrVars[0], c1 = cArrVars[1], c2 = cArrVars[2], c3 = cArrVars[3], c4 = cArrVars[4];
            return `do local _ln=${vmSym.bx}(${decA},${vmSym.ba}(${stVar},65535));local _l=${vmSym.bx}(${stVar},${vmSym.bx}(${decB},${k1Var}));` +
                `for _k=1,_ln do local _idx=${qVar}+_k;` +
                `_l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;${c0}[_idx]=${vmSym.bx}(${c0}[_idx],${vmSym.ba}(${vmSym.rs}(_l,16),255));` +
                `_l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;${c1}[_idx]=${vmSym.bx}(${c1}[_idx],${vmSym.ba}(${vmSym.rs}(_l,16),255));` +
                `_l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;${c2}[_idx]=${vmSym.bx}(${c2}[_idx],${vmSym.ba}(${vmSym.rs}(_l,16),255));` +
                `_l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;${c3}[_idx]=${vmSym.bx}(${c3}[_idx],${vmSym.ba}(${vmSym.rs}(_l,16),255));` +
                `_l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;${c4}[_idx]=${vmSym.bx}(${c4}[_idx],${vmSym.ba}(${vmSym.rs}(_l,16),255))end;` +
                `${sOp}[${qVar}]=${vmSym.bx}(${stepStored ^ vCtx.kLo},_kLo);${stVar}=${vmSym.bx}(${stVar},${decC})end`;
        }
        case V5Op.OP_STATE_STEP:
            return `${stVar}=${vmSym.bx}(${stVar},${decC})`;
        case V5Op.M_TAB_SUB_NOT: {
            const tags = mergeTags[V5Op.M_TAB_SUB_NOT];
            const branches = [
                { t: tags[0], c: `local _t=${decC};${rVar}[${regA}]=${rVar}[${decB}+${rbVar}][${rk("_t")}]` },
                { t: tags[1], c: `local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}-${rk("_y")}` },
                { t: tags[2], c: `${rVar}[${regA}]=not ${rVar}[${decB}+${rbVar}]` },
            ];
            for (let i = branches.length - 1; i > 0; i--) {
                const j = Math.floor(rng() * (i + 1));
                [branches[i], branches[j]] = [branches[j], branches[i]];
            }
            return `do local _td=${decD};if _td==${branches[0].t} then ${branches[0].c} elseif _td==${branches[1].t} then ${branches[1].c} else ${branches[2].c} end end`;
        }
        case V5Op.M_SET_ADD_LEN: {
            const tags = mergeTags[V5Op.M_SET_ADD_LEN];
            const branches = [
                { t: tags[0], c: `local _k=${decB};local _v=${decC};${rVar}[${regA}][${rk("_k")}]=${rk("_v")}` },
                { t: tags[1], c: `local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}+${rk("_y")}` },
                { t: tags[2], c: `${rVar}[${regA}]=#${rVar}[${decB}+${rbVar}]` },
            ];
            for (let i = branches.length - 1; i > 0; i--) {
                const j = Math.floor(rng() * (i + 1));
                [branches[i], branches[j]] = [branches[j], branches[i]];
            }
            return `do local _td=${decD};if _td==${branches[0].t} then ${branches[0].c} elseif _td==${branches[1].t} then ${branches[1].c} else ${branches[2].c} end end`;
        }
        case V5Op.M_ENV_MOV_UNM: {
            const tags = mergeTags[V5Op.M_ENV_MOV_UNM];
            const branches = [
                { t: tags[0], c: `${rVar}[${regA}]=${envVar}[${kVar}[${decB}+${kbVar}]]` },
                { t: tags[1], c: `${rVar}[${regA}]=${rVar}[${decB}+${rbVar}]` },
                { t: tags[2], c: `${rVar}[${regA}]=-${rVar}[${decB}+${rbVar}]` },
            ];
            for (let i = branches.length - 1; i > 0; i--) {
                const j = Math.floor(rng() * (i + 1));
                [branches[i], branches[j]] = [branches[j], branches[i]];
            }
            return `do local _td=${decD};if _td==${branches[0].t} then ${branches[0].c} elseif _td==${branches[1].t} then ${branches[1].c} else ${branches[2].c} end end`;
        }
        case V5Op.M_LDK_MUL_SGL: {
            const tags = mergeTags[V5Op.M_LDK_MUL_SGL];
            const branches = [
                { t: tags[0], c: `${rVar}[${regA}]=${kVar}[${decB}+${kbVar}]` },
                { t: tags[1], c: `local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}*${rk("_y")}` },
                { t: tags[2], c: `${envVar}[${kVar}[${decB}+${kbVar}]]=${rVar}[${regA}]` },
            ];
            for (let i = branches.length - 1; i > 0; i--) {
                const j = Math.floor(rng() * (i + 1));
                [branches[i], branches[j]] = [branches[j], branches[i]];
            }
            return `do local _td=${decD};if _td==${branches[0].t} then ${branches[0].c} elseif _td==${branches[1].t} then ${branches[1].c} else ${branches[2].c} end end`;
        }
        case V5Op.M_DIV_MOD_GUP: {
            const tags = mergeTags[V5Op.M_DIV_MOD_GUP];
            const branches = [
                { t: tags[0], c: `local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}/${rk("_y")}` },
                { t: tags[1], c: `local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}%${rk("_y")}` },
                { t: tags[2], c: `local _b=${upVar}[${decB}+1];if _b[2]then ${rVar}[${regA}]=_b[1][_b[2]]else ${rVar}[${regA}]=_b[1]end` },
            ];
            for (let i = branches.length - 1; i > 0; i--) {
                const j = Math.floor(rng() * (i + 1));
                [branches[i], branches[j]] = [branches[j], branches[i]];
            }
            return `do local _td=${decD};if _td==${branches[0].t} then ${branches[0].c} elseif _td==${branches[1].t} then ${branches[1].c} else ${branches[2].c} end end`;
        }
        case V5Op.M_CAT_POW_SUP: {
            const tags = mergeTags[V5Op.M_CAT_POW_SUP];
            const branches = [
                { t: tags[0], c: `local _b=${decB};local _e=${decC};local _acc=${rVar}[_e+${rbVar}];for _i=_e-1,_b,-1 do _acc=${rVar}[_i+${rbVar}].._acc end;${rVar}[${regA}]=_acc` },
                { t: tags[1], c: `local _x=${decB};local _y=${decC};${rVar}[${regA}]=${rk("_x")}^${rk("_y")}` },
                { t: tags[2], c: `local _x=${decB};local _y=${decC};${rVar}[${regA}]=${vmSym.mf}(${rk("_x")}/${rk("_y")})` },
                { t: tags[3], c: `local _b=${upVar}[${decB}+1];if _b[2]then _b[1][_b[2]]=${rVar}[${regA}]else _b[1]=${rVar}[${regA}]end` },
            ];
            for (let i = branches.length - 1; i > 0; i--) {
                const j = Math.floor(rng() * (i + 1));
                [branches[i], branches[j]] = [branches[j], branches[i]];
            }
            return `do local _td=${decD};if _td==${branches[0].t} then ${branches[0].c} elseif _td==${branches[1].t} then ${branches[1].c} elseif _td==${branches[2].t} then ${branches[2].c} else ${branches[3].c} end end`;
        }
        case V5Op.U_PROTO_FETCH:
            return `do local _cp=${poolVar}[_pr[7][${decB}+1]];${rVar}[${regA}]=_cp and{_cp,{}}or nil end`;
        case V5Op.U_UPVAL_BIND:
            return `do local _t=${rVar}[${regA}];if _t then local _ul=_t[1][6];local _nU=_t[2];for _ui=1,#_ul do local _ud=_ul[_ui];` +
                `if _ud[1]==1 then if not ${openUvVar} then ${openUvVar}={} end;local _bk;local _tg=_ud[2]+${rbVar};for _oi=1,#${openUvVar} do if ${openUvVar}[_oi][2]==_tg then _bk=${openUvVar}[_oi];break end end;` +
                `if not _bk then _bk={${rVar},_tg};${openUvVar}[#${openUvVar}+1]=_bk end;_nU[_ui]=_bk else _nU[_ui]=${upVar}[_ud[2]+1]end end end end`;
        case V5Op.U_CLOSURE_WRAP:
            return `do local _tb=${decB}+${rbVar};local _t=${rVar}[_tb];${rVar}[_tb]=nil;if _t then local _cp,_nU=_t[1],_t[2];` +
                `if not _cp[4]and _cp[2]<=4 then local _np=_cp[2];` +
                `if _np==0 then ${rVar}[${regA}]=function()return _vm(_cp,_nU,${envVar})end ` +
                `elseif _np==1 then ${rVar}[${regA}]=function(_1)return _vm(_cp,_nU,${envVar},_1)end ` +
                `elseif _np==2 then ${rVar}[${regA}]=function(_1,_2)return _vm(_cp,_nU,${envVar},_1,_2)end ` +
                `elseif _np==3 then ${rVar}[${regA}]=function(_1,_2,_3)return _vm(_cp,_nU,${envVar},_1,_2,_3)end ` +
                `else ${rVar}[${regA}]=function(_1,_2,_3,_4)return _vm(_cp,_nU,${envVar},_1,_2,_3,_4)end end ` +
                `else ${rVar}[${regA}]=function(...)local _ac=${vmSym.sel}("#",...);local _ag={...};return _vm(_cp,_nU,${envVar},_ag[1],_ag[2],_ag[3],_ag[4],_ag,_ac)end end ` +
                `else ${rVar}[${regA}]=nil end end`;
        case V5Op.U_FOR_STEP:
            return `do ${yieldChk}local _pa=${regA};local _stp=${rVar}[_pa+2];local _ix=${rVar}[_pa]+_stp;${rVar}[_pa]=_ix;local _lm=${rVar}[_pa+1];` +
                `local _ok=(_stp>0 and _ix<=_lm)or(_stp<=0 and _ix>=_lm);if _ok then ${rVar}[_pa+3]=_ix end;${rVar}[${decB}+${rbVar}]=_ok end`;
        case V5Op.U_TFOR_CALL:
            return `do ${yieldChk}local _pa=${regA};local _c=${decC};local _r={${rVar}[_pa](${rVar}[_pa+1],${rVar}[_pa+2])};` +
                `for _i=1,_c do ${rVar}[_pa+2+_i]=_r[_i]end;local _ok=_r[1]~=nil;if _ok then ${rVar}[_pa+2]=_r[1]end;${rVar}[${decB}+${rbVar}]=_ok end`;
        case V5Op.OP_MBA_DECODE_0:
        case V5Op.OP_MBA_DECODE_1:
        case V5Op.OP_MBA_DECODE_2:
        case V5Op.OP_MBA_DECODE_3: {
            const cIdx = op - V5Op.OP_MBA_DECODE_0;
            const decFn = `${mbaDecVar}[${cIdx + 1}]`;
            const mkExpr = isFastMode
                ? `${vmSym.bx}(${uSym.ta}(${qVar},2654435761),${k1Var})`
                : `${vmSym.bx}(${stVar},${uSym.ta}(${qVar},2654435761))`;
            return `do local _mk=${mkExpr};` +
                `${sA}[${qVar}]=${decFn}(${sA}[${qVar}],_mk);` +
                `${sB}[${qVar}]=${decFn}(${sB}[${qVar}],_mk);` +
                `${sC}[${qVar}]=${decFn}(${sC}[${qVar}],_mk);` +
                `${sOp}[${qVar}]=${decFn}(${sD}[${qVar}],_mk);` +
                `${sD}[${qVar}]=0;${pcVar}=${qVar} end`;
        }
        default:
            return ``;
    }
}

function modeSlotsCompat(modeCfg, cArrVars) {
    return cArrVars;
}

/**
 * Generates the entire Sentinel v5.2 APEX self-contained Luau payload.
 * @param {object} container
 * @param {object} ctx
 * @param {object} [options] - supports placeId, targetPlaceId, robloxOnly, nativeFuncs
 * @param {() => number} rng
 */
export function generateV5Lua(container, ctx, options = {}, rng = Math.random) {
    const usedIds = new Set();
    const ident = (minLen = 2, maxLen = 4) => {
        const first = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_";
        const rest = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
        const reserved = new Set([
            "and", "break", "do", "else", "elseif", "end", "false", "for", "function", "if",
            "in", "local", "nil", "not", "or", "repeat", "return", "then", "true", "until", "while",
            "continue", "type", "export", "U", "A", "B", "C", "D", "_z", "_vm", "_pr", "_nf", "_kLo",
            "_k0", "_k1", "_k2", "_k3", "_pp", "_oc", "_col", "_pi", "_v", "_ln", "_rb2", "_d1", "_d2", "_d3", "_kk", "_kx", "_rk", "_1", "_2", "_3", "_4",
            "_bx", "_ba", "_rs", "_mf", "_tu", "_tpack", "_tc", "_ty", "_sel", "_pc2", "_xpc2", "_nx", "_gm",
            "_tclr", "_fp", "_fpn", "_sc", "_om0", "_om1", "_tw", "_ta", "_a1", "_a2", "_a3", "_a4",
            "_vaArg", "_vacArg", "_va", "_vac", "_ep", "_ni", "_npa", "_mr", "_isVa", "_i", "_wi",
            "_k", "_l", "_idx", "_mk", "_pa", "_bv", "_b", "_c", "_f", "_r", "_r1", "_r2", "_st", "_stp", "_ix", "_lm",
            "_it", "_ity", "_ok", "_mt", "_bs", "_ul", "_ui", "_ud", "_bk", "_tg", "_oi", "_nU", "_np",
            "_ac", "_ag", "_o", "_fc", "_d", "_eh", "_we", "_ws", "_g", "_t", "_x", "_y", "_acc", "_e",
            "_q", "_n", "_uv", "_kv", "_or", "_ps", "_td", "_af", "_fl", "_tp", "_cp", "_tb", "_rf", "_tyf"
        ]);
        for (;;) {
            const len = minLen + Math.floor(rng() * (maxLen - minLen + 1));
            let s = first[Math.floor(rng() * first.length)];
            for (let i = 1; i < len; i++) s += rest[Math.floor(rng() * rest.length)];
            if (!reserved.has(s) && !usedIds.has(s)) {
                usedIds.add(s);
                return s;
            }
        }
    };

    // Allocate randomized identifiers for all VM internals (zero hardcoded _c0.._c4 / _R / _K / _E / _pc)
    const vmNames = {
        rVar: ident(2, 3),
        kVar: ident(2, 3),
        envVar: ident(2, 3),
        pcVar: ident(2, 3),
        topVar: ident(2, 3),
        upVar: ident(2, 3),
        poolVar: ident(2, 3),
        openUvVar: ident(2, 3),
        modeVar: ident(2, 3),
        k1Var: ident(2, 3),
        k2Var: ident(2, 3),
        k3Var: ident(2, 3),
        rbVar: ident(2, 3),
        kbVar: ident(2, 3),
        stVar: ident(2, 3),
        mbaDecVar: ident(2, 3),
        opVar: ident(2, 3),
        qVar: ident(2, 3),
        cArrVars: [ident(2, 3), ident(2, 3), ident(2, 3), ident(2, 3), ident(2, 3)],
    };

    // 1. Shuffled integer indices in `U` table for primitives + sharded trampoline stages
    let slotPool = Array.from({ length: 140 }, (_, i) => i + 1);
    for (let i = slotPool.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [slotPool[i], slotPool[j]] = [slotPool[j], slotPool[i]];
    }
    const allocSlot = () => slotPool.pop();

    const P = {
        bx: allocSlot(), ba: allocSlot(), bo: allocSlot(), bn: allocSlot(),
        ls: allocSlot(), rs: allocSlot(), lr: allocSlot(),
        sb: allocSlot(), sc: allocSlot(), ss: allocSlot(), sg: allocSlot(),
        tp: allocSlot(), tu: allocSlot(), tc: allocSlot(), tcon: allocSlot(),
        mf: allocSlot(), mld: allocSlot(),
        pc: allocSlot(), xpc: allocSlot(), sel: allocSlot(), ty: allocSlot(),
        nx: allocSlot(), ipa: allocSlot(), sm: allocSlot(), gm: allocSlot(),
        rg: allocSlot(), rset: allocSlot(), ts: allocSlot(),
        bcr: allocSlot(), bw8: allocSlot(), br8: allocSlot(), brf64: allocSlot(),
        ta: allocSlot(), fnv: allocSlot(),
        gf: allocSlot(), gg: allocSlot(), gr: allocSlot(), er: allocSlot(),
        shB85: allocSlot(), shRc4: allocSlot(), shLzss: allocSlot(), shParse: allocSlot(),
        nfInit: allocSlot(),
        boot: ident(2, 3),
        run: allocSlot(),
    };

    const uSym = {
        bx: `U[${P.bx}]`, ba: `U[${P.ba}]`, bo: `U[${P.bo}]`, bn: `U[${P.bn}]`,
        ls: `U[${P.ls}]`, rs: `U[${P.rs}]`, lr: `U[${P.lr}]`,
        sb: `U[${P.sb}]`, sc: `U[${P.sc}]`, ss: `U[${P.ss}]`, sg: `U[${P.sg}]`,
        tp: `U[${P.tp}]`, tu: `U[${P.tu}]`, tc: `U[${P.tc}]`, tcon: `U[${P.tcon}]`,
        mf: `U[${P.mf}]`, mld: `U[${P.mld}]`,
        pc: `U[${P.pc}]`, xpc: `U[${P.xpc}]`, sel: `U[${P.sel}]`, ty: `U[${P.ty}]`,
        nx: `U[${P.nx}]`, ipa: `U[${P.ipa}]`, sm: `U[${P.sm}]`, gm: `U[${P.gm}]`,
        rg: `U[${P.rg}]`, rset: `U[${P.rset}]`, ts: `U[${P.ts}]`,
        bcr: `U[${P.bcr}]`, bw8: `U[${P.bw8}]`, br8: `U[${P.br8}]`, brf64: `U[${P.brf64}]`,
        ta: `U[${P.ta}]`, fnv: `U[${P.fnv}]`,
        gf: `U[${P.gf}]`, gg: `U[${P.gg}]`, gr: `U[${P.gr}]`, er: `U[${P.er}]`,
    };

    const fnvOffset = (0x811c9dc5 ^ (1 + Math.floor(rng() * 0x7FFFFFFE))) >>> 0;

    // 2. Build U table entries (pure-Lua polyfills keep 100% portability)
    const bxPoly = `bit32 and bit32.bxor or(bit and bit.bxor)or function(a,b)a=a%4294967296;b=b%4294967296;local p,c=1,0 while a>0 or b>0 do local ra,rb=a%2,b%2 if ra~=rb then c=c+p end a,b,p=(a-ra)/2,(b-rb)/2,p*2 end return c end`;
    const baPoly = `bit32 and bit32.band or(bit and bit.band)or function(a,b)a=a%4294967296;b=b%4294967296;local p,c=1,0 while a>0 and b>0 do local ra,rb=a%2,b%2 if ra==1 and rb==1 then c=c+p end a,b,p=(a-ra)/2,(b-rb)/2,p*2 end return c end`;
    const boPoly = `bit32 and bit32.bor or(bit and bit.bor)or function(a,b)return(a+b)-(${uSym.ba}(a,b))end`;
    const bnPoly = `bit32 and bit32.bnot or(bit and bit.bnot)or function(a)return 4294967295-(a%4294967296)end`;
    const lsPoly = `bit32 and bit32.lshift or(bit and bit.lshift)or function(a,s)s=s%32 return((a%(2^(32-s)))*(2^s))%4294967296 end`;
    const rsPoly = `bit32 and bit32.rshift or(bit and bit.rshift)or function(a,s)s=s%32 return math.floor((a%4294967296)/(2^s))%4294967296 end`;
    const lrPoly = `bit32 and bit32.lrotate or function(a,s)s=s%32;a=a%4294967296;return((a*(2^s))%4294967296)+math.floor(a/(2^(32-s)))end`;

    const hasBufExpr = `(type(buffer)=="table")`;
    const bcrPoly = `(${hasBufExpr}and buffer.create)or function(n)return {}end`;
    const bw8Poly = `(${hasBufExpr}and buffer.writeu8)or function(b,i,v)b[i+1]=v end`;
    const br8Poly = `(${hasBufExpr}and buffer.readu8)or function(b,i)return b[i+1]or 0 end`;
    const brf64Poly = `(${hasBufExpr}and buffer.readf64)or function(b,i)local b0,b1,b2,b3,b4,b5,b6,b7=${uSym.br8}(b,i),${uSym.br8}(b,i+1),${uSym.br8}(b,i+2),${uSym.br8}(b,i+3),${uSym.br8}(b,i+4),${uSym.br8}(b,i+5),${uSym.br8}(b,i+6),${uSym.br8}(b,i+7);local sg=(b7>=128)and -1 or 1;local b7m=b7%128;local ex=b7m*16+${uSym.mf}(b6/16);local mn=((((((b6%16)*256+b5)*256+b4)*256+b3)*256+b2)*256+b1)*256+b0;if ex==0 then if mn==0 then return sg==-1 and -0 or 0 end;return sg*${uSym.mld}(mn,-1074)elseif ex==2047 then return mn==0 and(sg*(1/0))or(0/0)end;return sg*${uSym.mld}(1+mn/4503599627370496,ex-1023)end`;

    const taFn = `function(h,e)h,e=h%4294967296,e%4294967296;local u,l,m,ll=h%65536,e%65536,${uSym.mf}(h/65536),${uSym.mf}(e/65536);return(u*l+((u*ll+m*l)%65536)*65536)%4294967296 end`;
    const fnvFn = `function(s)local h=${fnvOffset};for i=1,#s do h=${uSym.ta}(${uSym.bx}(h,${uSym.sb}(s,i)),16777619)end;return h end`;

    const uEntries = [
        `[${P.bx}]=${bxPoly}`, `[${P.ba}]=${baPoly}`, `[${P.bo}]=${boPoly}`, `[${P.bn}]=${bnPoly}`,
        `[${P.ls}]=${lsPoly}`, `[${P.rs}]=${rsPoly}`, `[${P.lr}]=${lrPoly}`,
        `[${P.sb}]=string.byte`, `[${P.sc}]=string.char`, `[${P.ss}]=string.sub`, `[${P.sg}]=string.gsub`,
        `[${P.tp}]=table.pack or function(...)return{n=select("#",...),...}end`,
        `[${P.tu}]=table.unpack or unpack`,
        `[${P.tc}]=table.create or function(s,v)local t={}for i=1,s do t[i]=v end return t end`,
        `[${P.tcon}]=table.concat`,
        `[${P.mf}]=math.floor`, `[${P.mld}]=math.ldexp`,
        `[${P.pc}]=pcall`, `[${P.xpc}]=xpcall`, `[${P.sel}]=select`, `[${P.ty}]=type`,
        `[${P.nx}]=next`, `[${P.ipa}]=ipairs`, `[${P.sm}]=setmetatable`, `[${P.gm}]=getmetatable`,
        `[${P.rg}]=rawget`, `[${P.rset}]=rawset`, `[${P.ts}]=tostring`,
        `[${P.bcr}]=${bcrPoly}`, `[${P.bw8}]=${bw8Poly}`, `[${P.br8}]=${br8Poly}`, `[${P.brf64}]=${brf64Poly}`,
        `[${P.ta}]=${taFn}`, `[${P.fnv}]=${fnvFn}`,
        `[${P.gf}]=getfenv`, `[${P.gg}]=getgenv`, `[${P.gr}]=getrenv`, `[${P.er}]=error`,
    ];

    // 3. Randomized Sharded Trampoline Bootstrap States
    const stateSet = new Set();
    while (stateSet.size < 16) {
        stateSet.add(100 + Math.floor(rng() * 90000));
    }
    const uniqueStates = Array.from(stateSet);
    const ST = {
        ASSEMBLE_B85: uniqueStates[0],
        RC4_DEC: uniqueStates[1],
        LZSS_DEC: uniqueStates[2],
        PARSE_PROTOS: uniqueStates[3],
        EXEC: uniqueStates[4],
    };

    // 128-bit (4x32-bit) ARX Integrity Derivation Sponge & Security Traps (Zero 16-bit mask)
    const s0 = (0x20000000 + Math.floor(rng() * 0x5FFFFFFF)) >>> 0;
    const s1 = (0x10000000 + Math.floor(rng() * 0x6FFFFFFF)) >>> 0;
    const s2 = (0x30000000 + Math.floor(rng() * 0x4FFFFFFF)) >>> 0;
    const s3 = (0x15000000 + Math.floor(rng() * 0x5FFFFFFF)) >>> 0;
    const lanes = [s0, s1, s2, s3];
    const rW = () => (0x110011 + Math.floor(rng() * 0x7FFFFE00)) >>> 0;
    const wA0 = rW(), wA1 = rW();
    const wB0 = rW(), wB1 = rW();
    const wC0 = rW(), wC1 = rW();
    const wBv0 = rW();
    const wP10 = rW(), wP11 = rW();
    const wP20 = rW(), wP21 = rW();
    const wD0 = rW(), wD1 = rW();
    const poison1 = rW();
    const poison2 = rW();

    arxMix32(lanes, wA0, wA1);
    arxMix32(lanes, wB0, wB1);
    arxMix32(lanes, wC0, wC1);
    arxMix32(lanes, wBv0, 128); // IEEE-754 -0.0 sign-byte parity
    arxMix32(lanes, wP10, wP11);
    arxMix32(lanes, wP20, wP21);

    const targetPlaceId = Number(options.placeId || options.targetPlaceId || 0);
    const hasPlaceLock = targetPlaceId > 0;
    const robloxOnly = Boolean(options.robloxOnly || options.strictRoblox);
    const shareA = (0x10000000 + Math.floor(rng() * 0x70000000)) >>> 0;
    const shareB = ((0x20000000 + Math.floor(rng() * 0x60000000)) ^ shareA) >>> 0;
    const dynSalt = hasPlaceLock ? (targetPlaceId >>> 0) : ((shareA ^ shareB) >>> 0);
    arxMix32(lanes, dynSalt, (dynSalt ^ 2654435761) >>> 0);

    const hInst = saltedFnv1a32("Instance", fnvOffset);
    const hDm = saltedFnv1a32("DataModel", fnvOffset);
    const hWs = saltedFnv1a32("Workspace", fnvOffset);
    const hEn = saltedFnv1a32("Enums", fnvOffset);
    const hVec = saltedFnv1a32("vector", fnvOffset);
    const rfExpected = (((((hInst ^ hDm) >>> 0) + ((hWs ^ hEn) >>> 0)) >>> 0) ^ ((hVec + 16777472) >>> 0)) >>> 0;
    if (robloxOnly) {
        arxMix32(lanes, rfExpected, (rfExpected ^ 2246822519) >>> 0);
    }
    arxMix32(lanes, wD0, wD1);

    const M0 = (lanes[0] ^ ctx.K0) >>> 0;
    const M1 = (lanes[1] ^ ctx.K1) >>> 0;
    const M2 = (lanes[2] ^ ctx.K2) >>> 0;
    const M3 = (lanes[3] ^ ctx.K3) >>> 0;

    const spyNames = [
        "SimpleSpy", "Hydroxide", "RemoteSpy", "TurtleSpy", "OriginalNamecall",
        "SimpleSpyExecuted", "HydroxideExecuted", "SigmaSpy", "OctoSpy", "CobaltSpy",
        "HttpSpy", "rspy", "__DEBUG_HOOK", "__SPY_ATTACHED", "HookedNamecall", "dex_loaded", "DarkDex",
    ];
    const spyMapLit = `{${spyNames.map(nm => `[0x${saltedFnv1a32(nm, fnvOffset).toString(16)}]=true`).join(",")}}`;

    const h = (nm) => `0x${saltedFnv1a32(nm, fnvOffset).toString(16)}`;

    const dictPairsExpr = container.dictMap.length > 0
        ? `{${container.dictMap.map(d => `{${luaByteString(d.token)},${luaByteString(d.pair)}}`).join(",")}}`
        : `{}`;
    const chunksExpr = `{${container.chunks.map(c => luaByteString(c)).join(",")}}`;

    const rc4KeyExpr = `{${container.rawRc4Key.join(",")}}`;
    const invSboxExpr = `{${container.invSbox.join(",")}}`;

    const methSec = ident(2, 3);
    const methParse = ident(2, 3);
    const methEnv = ident(2, 3);

    // Security Gate Method `U[methSec]` -> returns 4x32-bit key vector (K0, K1, K2, K3)
    uEntries.push(`[${JSON.stringify(methSec)}]=function(U)` +
        `local _a,_b,_c,_d=${s0},${s1},${s2},${s3};` +
        `local function _mx(w0,w1)` +
            `_a=${uSym.bx}(${uSym.ta}((_a+w0)%4294967296,2654435761),${uSym.lr}(_b,7));` +
            `_b=(${uSym.ta}(${uSym.bx}(_b,w1),2246822519)+${uSym.lr}(_c,13))%4294967296;` +
            `_c=${uSym.bx}(${uSym.ta}((_c+${uSym.bx}(_a,_d))%4294967296,3266489917),${uSym.lr}(_d,17));` +
            `_d=(${uSym.ta}(${uSym.bx}(_d,_a),668265263)+${uSym.lr}(_b,11))%4294967296 end;` +
        `if ${emitOpaquePredicate(rng, uSym, true)} then _mx(${wA0},${wA1}) end;` +
        `if ${uSym.pc}(function() local _t=${uSym.sm}({},{[${uSym.sc}(95,95,105,110,100,101,120)]=function() return 79 end});if _t[1]~=79 then ${uSym.er}(1) end end) then _mx(${wB0},${wB1}) end;` +
        `local _ok=${uSym.pc}(function() if debug and debug.info then local _d=function() end;local _s1,_src=${uSym.pc}(debug.info,_d,"s");if _s1 and _src=="[C]" then ${uSym.er}(1) end;local _s2,_fn=${uSym.pc}(debug.info,_d,"f");if _s2 and _fn~=_d then ${uSym.er}(1) end end end);` +
        `if _ok then _mx(${wC0},${wC1}) end;` +
        // IEEE-754 -0.0 buffer derivation + zero-wipe (exact parity 128 on pure-Lua fallback)
        `local _bv=0;` +
        `if ${uSym.ty}(buffer)=="table"and buffer.create and buffer.writef64 and buffer.readu32 and buffer.fill then ` +
            `local _bf=buffer.create(24);buffer.writef64(_bf,16,0/-28);_bv=${uSym.rs}(buffer.readu32(_bf,20),24);buffer.fill(_bf,0,0,24)` +
        `else _bv=((1/(0/-28))==-math.huge)and 128 or 0 end;` +
        `_mx(${wBv0},_bv);` +
        // Exception-path side-channel traps
        `local _ok1=${uSym.pc}(function() local _x=0;local _=_x[nil];_a=${uSym.bx}(_a,${poison1}) end);` +
        `if not _ok1 then _mx(${wP10},${wP11}) end;` +
        `local _ok2=false;` +
        `if ${uSym.ty}(table)=="table"and table.freeze then _ok2=${uSym.pc}(function() local _ft=table.freeze({});_ft[1]=1;_b=${uSym.bx}(_b,${poison2}) end) end;` +
        `if not _ok2 then _mx(${wP20},${wP21}) end;` +
        // PlaceId / DataModel / Strict Roblox C-Engine Fingerprint check (full 32-bit mix, zero 65535 truncation)
        `local _ds=0;` +
        (hasPlaceLock
            ? `${uSym.pc}(function() local _g=(${uSym.ty}(game)=="userdata" and game) or (type(${uSym.gg})=="function" and ${uSym.gg}().game);if _g and ${uSym.ty}(_g)=="userdata" and _g.PlaceId then _ds=${uSym.ba}(_g.PlaceId,4294967295) end end);`
            : `${uSym.pc}(function() if game~=nil then local _tg=${uSym.ty}(game);if _tg=="userdata" then if game.ClassName=="DataModel" then _ds=${uSym.bx}(${shareA},${shareB}) end elseif _tg=="table" then _ds=${robloxOnly ? "0" : `${uSym.bx}(${shareA},${shareB})`} end else ${robloxOnly ? "_ds=0" : `_ds=${uSym.bx}(${shareA},${shareB})`} end end);`
        ) +
        `_mx(_ds,${uSym.bx}(_ds,2654435761));` +
        (robloxOnly
            ? `local _rf=0;${uSym.pc}(function() ` +
                `local _tyf=typeof;` +
                `if ${uSym.ty}(_tyf)~="function" or (debug and debug.info and debug.info(_tyf,"s")~="[C]") then return end;` +
                `if game==nil or workspace==nil or Enum==nil or Vector3==nil or Vector3.zero==nil then return end;` +
                `local _i0=${uSym.fnv}(_tyf(game));local _i1=${uSym.fnv}(game.ClassName);` +
                `local _i2=${uSym.fnv}(workspace.ClassName);local _i3=${uSym.fnv}(_tyf(Enum));` +
                `local _i4=${uSym.fnv}(_tyf(Vector3.zero));local _pv=Enum.Material.Plastic.Value;` +
                `if _i0==${hInst} and _pv==256 and (not debug or not debug.info or debug.info(game.GetService,"s")=="[C]") then ` +
                `_rf=${uSym.bx}(((${uSym.bx}(_i0,_i1)+${uSym.bx}(_i2,_i3))%4294967296),((_i4+_pv*65537)%4294967296)) end ` +
              `end);_mx(_rf,${uSym.bx}(_rf,2246822519));`
            : ``
        ) +
        // Anti-Spy + C-Closure Integrity Check
        `local _sp=${spyMapLit};local _tr=false;` +
        `${uSym.pc}(function() ` +
            `if debug and debug.gethook and debug.gethook()~=nil then _tr=true end;` +
            `if not _tr and debug and debug.info then ` +
                `local _cc={${uSym.pc},${uSym.xpc},${uSym.rg},${uSym.gm},${uSym.sb},debug.info};` +
                `if bit32 and bit32.bxor then _cc[#_cc+1]=${uSym.bx} end;` +
                `if ${uSym.ty}(buffer)=="table"and buffer.writef64 and buffer.readu32 then _cc[#_cc+1]=buffer.writef64;_cc[#_cc+1]=buffer.readu32 end;` +
                `for _ci=1,#_cc do if debug.info(_cc[_ci],"s")~="[C]" then _tr=true;break end end ` +
            `end;` +
            `if not _tr then ` +
                `local _envs={};` +
                `if ${uSym.ty}(${uSym.gg})=="function" then _envs[#_envs+1]=${uSym.gg}() end;` +
                `if ${uSym.ty}(${uSym.gf})=="function" then _envs[#_envs+1]=${uSym.gf}(0) end;` +
                `if ${uSym.ty}(_G)=="table" then _envs[#_envs+1]=_G end;` +
                `for _ei=1,#_envs do local _g=_envs[_ei];if ${uSym.ty}(_g)=="table" then for _k,_v in ${uSym.nx},_g do if _v and ${uSym.ty}(_k)=="string" and _sp[${uSym.fnv}(_k)] then _tr=true;break end end end;if _tr then break end end ` +
            `end ` +
        `end);` +
        `if not _tr then _mx(${wD0},${wD1}) end;` +
        `return ${uSym.bx}(_a,${M0}),${uSym.bx}(_b,${M1}),${uSym.bx}(_c,${M2}),${uSym.bx}(_d,${M3}) end`
    );

    // Zero-plaintext Hashed Environment Bridge builder method (exposes __PBZ_NF__ & __PBZ_CRASH__)
    uEntries.push(`[${JSON.stringify(methEnv)}]=function(U,_nf)` +
        `local _fg={};` +
        `local _fe=(${uSym.ty}(${uSym.gf})=="function" and (${uSym.gf}(0)or ${uSym.gf}()))or{};` +
        `local _ge=(${uSym.ty}(${uSym.gg})=="function" and ${uSym.gg}())or{};` +
        `local _re=(${uSym.ty}(${uSym.gr})=="function" and ${uSym.gr}())or{};` +
        `local _gl=(${uSym.ty}(_G)=="table" and _G)or{};` +
        `local _f=${uSym.fnv};` +
        `local _mt={};` +
        `local _idx=${uSym.sc}(95,95,105,110,100,101,120);` +
        `local _nidx=${uSym.sc}(95,95,110,101,119,105,110,100,101,120);` +
        `local _eobj;` +
        `_mt[_idx]=function(_,k)` +
        `local v=_fe[k];if v~=nil then if v==_gl and table.isfrozen and table.isfrozen(_gl) then return _fg end return v end;` +
        `v=_gl[k];if v~=nil then if v==_gl and table.isfrozen and table.isfrozen(_gl) then return _fg end return v end;` +
        `v=_fg[k];if v~=nil then return v end;` +
        `v=_ge[k];if v~=nil then return v end;` +
        `v=_re[k];if v~=nil then return v end;` +
        `if ${uSym.ty}(k)=="string" then local _hk=_f(k);` +
        `if _hk==${h("__PBZ_NF__")} then return _nf ` +
        `elseif _hk==${h("__PBZ_CRASH__")} then return function() while true do end end ` +
        `elseif _hk==${h("_G")} then return (${uSym.ty}(_gl)=="table" and not(table.isfrozen and table.isfrozen(_gl)) and _gl) or _fg ` +
        `elseif _hk==${h("_ENV")} then return _eobj ` +
        `elseif _hk==${h("shared")} then return (${uSym.ty}(shared)=="table" and shared) or _ge[k] or _fg ` +
        `elseif _hk==${h("unpack")} then return ${uSym.tu} ` +
        `elseif _hk==${h("typeof")} then return _fe[k] or ${uSym.ty} ` +
        `elseif _hk==${h("bit32")} then return bit32 or bit ` +
        `elseif _hk==${h("loadstring")} then return _fe.loadstring or _fe.load ` +
        `elseif _hk==${h("getfenv")} then return ${uSym.gf} or function() return _eobj end ` +
        `elseif _hk==${h("getgenv")} then return ${uSym.gg} or function() return _gl end ` +
        `elseif _hk==${h("getrenv")} then return ${uSym.gr} or function() return _gl end ` +
        `elseif _hk==${h("tick")} then return (os and os.time) ` +
        `elseif _hk==${h("time")} then return (os and os.clock) ` +
        `elseif _hk==${h("cloneref")} then return function(x) return x end ` +
        `end end;return nil end;` +
        `_mt[_nidx]=function(t,k,v)` +
        `_fg[k]=v;` +
        `if ${uSym.ty}(${uSym.gg})=="function" then ${uSym.pc}(function() _ge[k]=v end) end;` +
        `if ${uSym.ty}(_G)=="table" and not(table.isfrozen and table.isfrozen(_G)) then ${uSym.pc}(function() _G[k]=v end) end end;` +
        `_eobj=${uSym.sm}({},_mt);return _eobj end`
    );

    // 4. Sharded Function-Table Trampoline Bootstrap Stages
    const { TAG_NIL, TAG_FALSE, TAG_TRUE, TAG_NUM, TAG_STR } = container.tags;

    // Stage 1: ASSEMBLE_B85 -> (ST.RC4_DEC, _kv, _cb, _clen, nil)
    uEntries.push(`[${P.shB85}]=function(U,_kv,_a,_b,_c)` +
        `local _ch=${chunksExpr};local _al=${luaByteString(container.alphabet)};local _dp=${dictPairsExpr};` +
        `local _s=${uSym.tcon}(_ch);` +
        `for _i=1,#_dp do _s=${uSym.sg}(_s,_dp[_i][1],_dp[_i][2]) end;` +
        `local _lut={};for _i=1,85 do _lut[${uSym.sb}(_al,_i)]=_i-1 end;` +
        `local _clen=${container.cipherLen};local _cb=${uSym.bcr}(_clen);local _wp=0;` +
        `for _i=1,#_s,5 do local a,b,c,d,e=${uSym.sb}(_s,_i,_i+4);` +
        `local _v=(((_lut[a]*85+_lut[b])*85+_lut[c])*85+_lut[d])*85+_lut[e];` +
        `if _wp<_clen then ${uSym.bw8}(_cb,_wp,${uSym.ba}(${uSym.mf}(_v/16777216),255));_wp=_wp+1 end;` +
        `if _wp<_clen then ${uSym.bw8}(_cb,_wp,${uSym.ba}(${uSym.mf}(_v/65536),255));_wp=_wp+1 end;` +
        `if _wp<_clen then ${uSym.bw8}(_cb,_wp,${uSym.ba}(${uSym.mf}(_v/256),255));_wp=_wp+1 end;` +
        `if _wp<_clen then ${uSym.bw8}(_cb,_wp,${uSym.ba}(_v,255));_wp=_wp+1 end end;` +
        `return ${ST.RC4_DEC},_kv,_cb,_clen,nil end`
    );

    // Stage 2: RC4_DEC (128-bit KSA + Drop-N + Rolling ARX Keystream) -> (ST.LZSS_DEC, _kv, _pb, _clen, nil)
    uEntries.push(`[${P.shRc4}]=function(U,_kv,_cb,_cl,_c)` +
        `local _rk=${rc4KeyExpr};local _k0,_k1,_k2,_k3=_kv[1],_kv[2],_kv[3],_kv[4];` +
        `local _kb={` +
            `${uSym.ba}(_k0,255),${uSym.ba}(${uSym.rs}(_k0,8),255),${uSym.ba}(${uSym.rs}(_k0,16),255),${uSym.ba}(${uSym.rs}(_k0,24),255),` +
            `${uSym.ba}(_k1,255),${uSym.ba}(${uSym.rs}(_k1,8),255),${uSym.ba}(${uSym.rs}(_k1,16),255),${uSym.ba}(${uSym.rs}(_k1,24),255),` +
            `${uSym.ba}(_k2,255),${uSym.ba}(${uSym.rs}(_k2,8),255),${uSym.ba}(${uSym.rs}(_k2,16),255),${uSym.ba}(${uSym.rs}(_k2,24),255),` +
            `${uSym.ba}(_k3,255),${uSym.ba}(${uSym.rs}(_k3,8),255),${uSym.ba}(${uSym.rs}(_k3,16),255),${uSym.ba}(${uSym.rs}(_k3,24),255)` +
        `};` +
        `local _S={};for _i=0,255 do _S[_i]=_i end;` +
        `local _kl=#_rk;local _j=0;for _i=0,255 do local _mi=_i%_kl;local _kk=${uSym.bx}(_rk[_mi+1],_kb[(_mi%16)+1]);_j=(_j+_S[_i]+_kk)%256;_S[_i],_S[_j]=_S[_j],_S[_i] end;` +
        `local _a,_b=0,0;for _di=1,${container.rc4DropN} do _a=(_a+1)%256;_b=(_b+_S[_a])%256;_S[_a],_S[_b]=_S[_b],_S[_a] end;` +
        `local _pb=${uSym.bcr}(_cl);local _ax=${uSym.bx}(_k1,_k2);` +
        `for _k=0,_cl-1 do _a=(_a+1)%256;_b=(_b+_S[_a])%256;_S[_a],_S[_b]=_S[_b],_S[_a];` +
        `_ax=(${uSym.ta}(_ax,1664525)+1013904223)%4294967296;` +
        `local _ks=${uSym.bx}(_S[(_S[_a]+_S[_b])%256],${uSym.ba}(${uSym.rs}(_ax,16),255));` +
        `${uSym.bw8}(_pb,_k,${uSym.bx}(${uSym.br8}(_cb,_k),_ks)) end;` +
        `return ${ST.LZSS_DEC},_kv,_pb,_cl,nil end`
    );

    // Stage 3: LZSS_DEC (Zero-Oracle 9-Byte Encrypted Header + 32-bit FNV MAC) -> (ST.PARSE_PROTOS, _kv, _raw, _rawLen, nil)
    uEntries.push(`[${P.shLzss}]=function(U,_kv,_pb,_cl,_c)` +
        `local _flg=${uSym.bx}(${uSym.br8}(_pb,0),${uSym.ba}(_kv[3],255));` +
        `local _rawLen=${uSym.bx}(${uSym.br8}(_pb,1)+${uSym.br8}(_pb,2)*256+${uSym.br8}(_pb,3)*65536+${uSym.br8}(_pb,4)*16777216,_kv[4]);` +
        `local _expMac=${uSym.bx}(${uSym.br8}(_pb,5)+${uSym.br8}(_pb,6)*256+${uSym.br8}(_pb,7)*65536+${uSym.br8}(_pb,8)*16777216,_kv[1]);` +
        `local _bad=(_flg~=${container.flagRaw} and _flg~=${container.flagComp})or _rawLen<1 or _rawLen>67108864;` +
        `if _bad then _rawLen=1;_kv[1]=${uSym.bx}(_kv[1],324508639) end;` +
        `local _raw=${uSym.bcr}(_rawLen);` +
        `if not _bad then ` +
            `if _flg==${container.flagRaw} then for _i=0,_rawLen-1 do ${uSym.bw8}(_raw,_i,${uSym.br8}(_pb,9+_i)) end ` +
            `else local _p=9;local _op=0;while _p<_cl and _op<_rawLen do local _ct=${uSym.br8}(_pb,_p);_p=_p+1;` +
            `if _ct<128 then local _n=_ct+1;for _j=1,_n do if _op<_rawLen then ${uSym.bw8}(_raw,_op,${uSym.br8}(_pb,_p));_op=_op+1 end;_p=_p+1 end;` +
            `elseif _ct<192 then local _ll=_ct-125;local _lo=${uSym.br8}(_pb,_p)+1;_p=_p+1;for _j=1,_ll do if _op<_rawLen then ${uSym.bw8}(_raw,_op,${uSym.br8}(_raw,_op-_lo));_op=_op+1 end end;` +
            `else local _ll=_ct-189;local _lo=${uSym.br8}(_pb,_p)*256+${uSym.br8}(_pb,_p+1);_p=_p+2;for _j=1,_ll do if _op<_rawLen then ${uSym.bw8}(_raw,_op,${uSym.br8}(_raw,_op-_lo));_op=_op+1 end end end end end;` +
            `local _mc=${uSym.bx}(_kv[1],_kv[2]);for _mi=0,_rawLen-1 do _mc=${uSym.ta}(${uSym.bx}(_mc,${uSym.br8}(_raw,_mi)),16777619) end;` +
            `if _mc~=_expMac then _kv[2]=${uSym.bx}(_kv[2],1515870810);_kv[3]=${uSym.bx}(_kv[3],2779096485) end ` +
        `end;` +
        `return ${ST.PARSE_PROTOS},_kv,_raw,_rawLen,nil end`
    );

    // Stage 4: PARSE_PROTOS (128-bit StrPool + _rb/_kb Shifted Consts + AoS Rolling-LCG Stream) -> (ST.EXEC, _pool, _ridx, _decStr, nil)
    uEntries.push(`[${P.shParse}]=function(U,_kv,_raw,_rl,_c)` +
        `local _isb=${invSboxExpr};` +
        `local _k0,_k1,_k2,_k3=_kv[1],_kv[2],_kv[3],_kv[4];` +
        `local _kb8={${uSym.ba}(_k2,255),${uSym.ba}(${uSym.rs}(_k2,8),255),${uSym.ba}(${uSym.rs}(_k2,16),255),${uSym.ba}(${uSym.rs}(_k2,24),255),${uSym.ba}(_k3,255),${uSym.ba}(${uSym.rs}(_k3,8),255),${uSym.ba}(${uSym.rs}(_k3,16),255),${uSym.ba}(${uSym.rs}(_k3,24),255)};` +
        `local _k2m=${uSym.ba}(_k2,65535);local _k3m=${uSym.ba}(_k3,65535);` +
        `local _pos=0;` +
        `local function _ru() local _b=${uSym.br8}(_raw,_pos);_pos=_pos+1;if _b<254 then return _b elseif _b==254 then local _v=${uSym.br8}(_raw,_pos)+${uSym.br8}(_raw,_pos+1)*256;_pos=_pos+2;return _v else local _v=${uSym.br8}(_raw,_pos)+${uSym.br8}(_raw,_pos+1)*256+${uSym.br8}(_raw,_pos+2)*65536+${uSym.br8}(_raw,_pos+3)*16777216;_pos=_pos+4;return _v end end;` +
        `local _plen=_ru();local _sbuf=${uSym.bcr}(_plen);for _i=0,_plen-1 do ${uSym.bw8}(_sbuf,_i,${uSym.br8}(_raw,_pos+_i)) end;_pos=_pos+_plen;` +
        `local _scache={};` +
        `local function _decStr(_off,_ln,_sl)` +
        `local _ck=_off*65537+_ln;local _cv=_scache[_ck];if _cv~=nil then return _cv end;` +
        `local _l=${uSym.bx}(_sl,_k1);local _t={};` +
        `for _i=0,_ln-1 do _l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;` +
        `local _kby=${uSym.bx}(${uSym.ba}(${uSym.rs}(_l,16),255),_kb8[(_i%8)+1]);` +
        `local _sv=${uSym.bx}(${uSym.br8}(_sbuf,_off+_i),_kby);` +
        `_t[_i+1]=${uSym.sc}(_isb[_sv+1]) end;` +
        `local _str=${uSym.tcon}(_t);_scache[_ck]=_str;return _str end;` +
        `local _np=_ru();local _ridx=_ru()+1;local _pool={};` +
        `local _wo={${container.wireColOrder.map(x => x + 1).join(",")}};` +
        `for _pi=1,_np do ` +
        `local _npa=_ru();local _mr=_ru();local _fl=${uSym.br8}(_raw,_pos);_pos=_pos+1;` +
        `local _rb=${uSym.bx}(_ru(),_k3m);local _kb=${uSym.bx}(_ru(),_k2m);local _ps=${uSym.bx}(_ru(),_k3);` +
        `local _nk=_ru();local _K={};local _ksd={};` +
        `for _ki=1,_nk do local _tg=${uSym.br8}(_raw,_pos);_pos=_pos+1;local _ks=_ki+_kb-1;` +
        `if _tg==${TAG_NIL} then _K[_ks]=nil ` +
        `elseif _tg==${TAG_FALSE} then _K[_ks]=false ` +
        `elseif _tg==${TAG_TRUE} then _K[_ks]=true ` +
        `elseif _tg==${TAG_NUM} then _K[_ks]=${uSym.brf64}(_raw,_pos);_pos=_pos+8 ` +
        `elseif _tg==${TAG_STR} then _ksd[_ks]={_ru(),_ru(),_ru()} end end;` +
        `local _kmt={};_kmt[${uSym.sc}(95,95,105,110,100,101,120)]=function(t,i) local _sd=_ksd[i];if _sd then local _s=_decStr(_sd[1],_sd[2],_sd[3]);_ksd[i]=nil;${uSym.rset}(t,i,_s);return _s end;return nil end;` +
        `_kmt[${uSym.sc}(95,95,110,101,119,105,110,100,101,120)]=function() end;_kmt[${uSym.sc}(95,95,109,101,116,97,116,97,98,108,101)]=false;` +
        `${uSym.sm}(_K,_kmt);` +
        `local _nuv=_ru();local _uvs={};for _ui=1,_nuv do local _il=${uSym.br8}(_raw,_pos);_pos=_pos+1;_uvs[_ui]={_il,_ru()} end;` +
        `local _nc=_ru();local _chp={};for _ci=1,_nc do _chp[_ci]=_ru()+1 end;` +
        `local _ni=_ru();local _a0,_a1,_a2,_a3,_a4={},{},{},{},{};local _as={_a0,_a1,_a2,_a3,_a4};` +
        `for _j=1,_ni do for _wi=1,5 do _as[_wo[_wi]][_j]=_ru() end end;` +
        `_pool[_pi]={_K,_npa,_mr,(_fl%2==1),(${uSym.ba}(_fl,2)~=0 and 1 or 0),_uvs,_chp,_ni,_a0,_a1,_a2,_a3,_a4,(${uSym.ba}(_fl,4)~=0),(${uSym.ba}(_fl,8)~=0),(${uSym.ba}(_fl,16)~=0),_rb,_kb,_ps}` +
        `end;return ${ST.EXEC},_pool,_ridx,_decStr,nil end`
    );

    // Trampoline Driver `U[methParse]`
    uEntries.push(`[${JSON.stringify(methParse)}]=function(U,_k0,_k1,_k2,_k3)` +
        `local _tp={[${ST.ASSEMBLE_B85}]=${P.shB85},[${ST.RC4_DEC}]=${P.shRc4},[${ST.LZSS_DEC}]=${P.shLzss},[${ST.PARSE_PROTOS}]=${P.shParse}};` +
        `local _st=${ST.ASSEMBLE_B85};local _s1,_s2,_s3,_s4={_k0,_k1,_k2,_k3},nil,nil,nil;` +
        `while _st~=${ST.EXEC} do _st,_s1,_s2,_s3,_s4=U[_tp[_st]](U,_s1,_s2,_s3,_s4) end;` +
        `return _s1,_s2,_s3 end`
    );

    // Tier A Hardened Native Functions initializer (if any native functions exist)
    const nativeFuncs = Array.isArray(options?.nativeFuncs) ? options.nativeFuncs : [];
    const hasNative = nativeFuncs.length > 0;
    if (hasNative) {
        const nfAssigns = [];
        for (const nf of nativeFuncs) {
            if (!nf || !nf.fnNode) continue;
            const emitted = emitHardenedNativeLua(nf.fnNode, {
                getStrCall: (s) => {
                    const ref = container.strRefs && container.strRefs[s];
                    if (ref) return `_ds(${ref.offset},${ref.len},${ref.strSalt})`;
                    return luaByteString(s);
                },
                bxFn: "_uBx",
                envVar: "_E",
                rng,
            });
            if (emitted) {
                nfAssigns.push(`_nf[${nf.id}]=${emitted}`);
            }
        }
        uEntries.push(`[${P.nfInit}]=function(U,_nf,_E,_ds)` +
            `local _uBx=${uSym.bx};${nfAssigns.join(";")} end`
        );
    }

    // 5. Build FASTCALL-Hoisted Interpreter `U[P.run]` with Anti-vmmap Dual-Mode BST, Rolling-State Block Cipher & Merged/Split ISA
    const {
        rVar, kVar, envVar, pcVar, topVar, upVar, poolVar, openUvVar,
        modeVar, k1Var, k2Var, k3Var, rbVar, kbVar, stVar, mbaDecVar, opVar, qVar,
        cArrVars,
    } = vmNames;
    const kSecVar = "_k0";
    const twVar = "_tw";

    const vmSym = {
        ...uSym,
        bx: "_bx", ba: "_ba", rs: "_rs", mf: "_mf",
        tu: "_tu", tp: "_tpack", tc: "_tc", ty: "_ty",
        sel: "_sel", pc: "_pc2", xpc: "_xpc2", nx: "_nx", gm: "_gm",
    };

    const mbaInitExpr = `{${ctx.mbaCodecs.map(c => c.emitLuaDecoderFn({ ...vmSym, bo: uSym.bo, bn: uSym.bn, lr: uSym.lr, ta: uSym.ta })).join(",")}}`;

    const isFastMode = Boolean(ctx.isFastMode || ctx.level === "fast");

    const buildModeDispatch = (modeCfg) => {
        const usedSet = ctx.usedOps[modeCfg.modeId];
        const entries = [];
        for (let op = 0; op < V5_OPCODE_COUNT; op++) {
            if (!usedSet.has(op)) continue;
            const body = buildOpcodeHandlerBody(op, modeCfg, {
                uSym, vmSym, rVar, kVar, envVar, pcVar, topVar, upVar, poolVar, openUvVar,
                modeVar, k1Var, k2Var, rbVar, kbVar, stVar, mbaDecVar, isFastMode,
                rkOffset: ctx.rkOffset, qVar, cArrVars, kLo: ctx.kLo, mergeTags: ctx.mergeTags, rng,
            });
            entries.push({ id: modeCfg.opEncode[op], body });
        }
        entries.sort((a, b) => a.id - b.id);
        return buildAntiVmmapBST(entries, opVar, rng, vmSym, ctx.level);
    };

    const wipeEpEnd = isFastMode
        ? ``
        : `if _ep then for _wi=1,_ni do ${cArrVars[0]}[_wi]=nil;${cArrVars[1]}[_wi]=nil;${cArrVars[2]}[_wi]=nil;${cArrVars[3]}[_wi]=nil;${cArrVars[4]}[_wi]=nil end end;`;
    const recFrameEnd = `if not ${openUvVar} and _fpn<64 then _tclr(${rVar});_fpn=_fpn+1;_fp[_fpn]=${rVar} end;`;

    let dispatchLoopCode;
    let omInitLine;
    if (ctx.numModes === 2) {
        const m0 = ctx.modes[0];
        const m1 = ctx.modes[1];
        const opCol0 = cArrVars[m0.role.op];
        const opCol1 = cArrVars[m1.role.op];
        const bst0 = buildModeDispatch(m0);
        const bst1 = buildModeDispatch(m1);
        omInitLine = `local _om0,_om1=_bx(_kLo,${m0.mSalt}),_bx(_kLo,${m1.mSalt});`;
        dispatchLoopCode =
            `while ${pcVar}<=_ni do ` +
            `local ${qVar}=${pcVar};${pcVar}=${pcVar}+1;` +
            `if ${modeVar}==0 then ` +
            `local ${opVar}=_bx(${opCol0}[${qVar}],_om0);` +
            `${bst0} ` +
            `else ` +
            `local ${opVar}=_bx(${opCol1}[${qVar}],_om1);` +
            `${bst1} end end;` +
            `${wipeEpEnd}${recFrameEnd}`;
    } else {
        const m0 = ctx.modes[0];
        const opCol0 = cArrVars[m0.role.op];
        const bst0 = buildModeDispatch(m0);
        omInitLine = `local _om0=_bx(_kLo,${m0.mSalt});`;
        if (isFastMode) {
            dispatchLoopCode =
                `while ${pcVar}<=_ni do ` +
                `local ${qVar}=${pcVar};${pcVar}=${pcVar}+1;` +
                `local ${opVar}=${opCol0}[${qVar}];` +
                `${bst0} end;` +
                `${recFrameEnd}`;
        } else {
            dispatchLoopCode =
                `while ${pcVar}<=_ni do ` +
                `local ${qVar}=${pcVar};${pcVar}=${pcVar}+1;` +
                `local ${opVar}=_bx(${opCol0}[${qVar}],_om0);` +
                `${bst0} end;` +
                `${wipeEpEnd}${recFrameEnd}`;
        }
    }

    const dkInitLine = ``;

    const mbaInitLine = ctx.mbaCodecs.length > 0
        ? `local ${mbaDecVar}=${mbaInitExpr};`
        : ``;

    const fastPreUnmask = isFastMode
        ? `do local _col=${9 + ctx.modes[0].role.op};for _pi=1,#${poolVar} do local _pp=${poolVar}[_pi];local _oc=_pp[_col];for _i=1,_pp[8] do _oc[_i]=_bx(_oc[_i],_om0) end end end;`
        : ``;

    uEntries.push(`[${P.run}]=function(U,${poolVar},${kSecVar},${k1Var},${k2Var},${k3Var},${twVar})` +
        `local _bx,_ba,_rs,_mf,_tu,_tpack,_tc,_ty,_sel,_pc2,_xpc2,_nx,_gm=` +
            `U[${P.bx}],U[${P.ba}],U[${P.rs}],U[${P.mf}],U[${P.tu}],U[${P.tp}],U[${P.tc}],U[${P.ty}],U[${P.sel}],U[${P.pc}],U[${P.xpc}],U[${P.nx}],U[${P.gm}];` +
        `local _tclr=(_ty(table)=="table"and table.clear)or function(t)for _ri=1,#t do t[_ri]=nil end end;` +
        `local _kLo=_ba(${kSecVar},255);` +
        `local _fp,_fpn={},0;local _sc=0;` +
        omInitLine +
        dkInitLine +
        fastPreUnmask +
        mbaInitLine +
        `local _vm;_vm=function(_pr,${upVar},${envVar},_a1,_a2,_a3,_a4,_vaArg,_vacArg)` +
        (isFastMode
            ? `local ${kVar}=_pr[1];local _npa=_pr[2];local _mr=_pr[3];local _isVa=_pr[4];local _ni=_pr[8];local ${rbVar}=_pr[17];local ${kbVar}=_pr[18];`
            : `local ${kVar}=_pr[1];local _npa=_pr[2];local _mr=_pr[3];local _isVa=_pr[4];local ${modeVar}=_pr[5];local _ni=_pr[8];local _ep=_pr[14];local ${rbVar}=_pr[17];local ${kbVar}=_pr[18];local ${stVar}=_bx(${k2Var},_pr[19]);`
        ) +
        `local ${cArrVars[0]},${cArrVars[1]},${cArrVars[2]},${cArrVars[3]},${cArrVars[4]}=_pr[9],_pr[10],_pr[11],_pr[12],_pr[13];` +
        `local ${rVar};if _fpn>0 then ${rVar}=_fp[_fpn];_fp[_fpn]=nil;_fpn=_fpn-1 else ${rVar}=_tc(_mr+${rbVar}+4) end;` +
        `local _va,_vac;` +
        `if not _isVa and _npa<=4 then ` +
            `if _npa>=1 then ${rVar}[${rbVar}]=_a1 end;if _npa>=2 then ${rVar}[${rbVar}+1]=_a2 end;` +
            `if _npa>=3 then ${rVar}[${rbVar}+2]=_a3 end;if _npa>=4 then ${rVar}[${rbVar}+3]=_a4 end ` +
        `else ` +
            `for _i=1,((_vacArg<_npa)and _vacArg or _npa)do ${rVar}[${rbVar}+_i-1]=_vaArg[_i] end;` +
            `if _isVa then _vac=_vacArg-_npa;if _vac<0 then _vac=0 end;if _vac>0 then _va={};for _i=1,_vac do _va[_i]=_vaArg[_npa+_i] end end end ` +
        `end;` +
        `local ${pcVar}=1;local ${openUvVar};local ${topVar}=0;` +
        `${dispatchLoopCode} ` +
        `end;return _vm end`
    );

    // 6. Boot Method `U[P.boot](U, ...)` -> threads 4x32-bit key vector (_k0.._k3)
    uEntries.push(`[${JSON.stringify(P.boot)}]=function(U,...)` +
        `local _k0,_k1,_k2,_k3=U:${methSec}();` +
        `local _pl,_ri,_ds=U:${methParse}(_k0,_k1,_k2,_k3);` +
        `local _nf={};` +
        `local _env=U:${methEnv}(_nf);` +
        (hasNative ? `U[${P.nfInit}](U,_nf,_env,_ds);` : ``) +
        `local _tw;do local _t=_env[${uSym.sc}(116,97,115,107)];if ${uSym.ty}(_t)=="table"then _tw=_t[${uSym.sc}(119,97,105,116)]end end;` +
        `local _vm=U[${P.run}](U,_pl,_k0,_k1,_k2,_k3,_tw);` +
        `local _ac=${uSym.sel}("#",...);local _ag={...};` +
        `return _vm(_pl[_ri],{},_env,_ag[1],_ag[2],_ag[3],_ag[4],_ag,_ac) end`
    );

    // Shuffle all U table keys so primitives, sharded stages, and runtime appear in randomized order
    for (let i = uEntries.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [uEntries[i], uEntries[j]] = [uEntries[j], uEntries[i]];
    }

    return `local U;U=setmetatable({${uEntries.join(",")}},{});return U:${P.boot}(...)`;
}
