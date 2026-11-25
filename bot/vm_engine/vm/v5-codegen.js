// language: JavaScript, file: v5-codegen.js, target: Node.js ESM
// Sentinel v5.1 APEX Runtime Codegen (ONYX / OPAL):
// - Shuffled Primitive Metatable `U` + Pure-Lua buffer/bit32/f64 fallbacks
// - Non-Zero Integrity Derivation Key (K_sec != 0) + IEEE-754 -0.0 Buffer Key + Exception/C-Closure/Anti-Spy Traps + PlaceId Lock
// - Sharded Function-Table Trampoline Bootstrap Deserializer (Luraph v15 style)
// - Zero-Plaintext Hashed Environment Bridge & Sealed Lazy Master Constant Pool
// - Tier A Hardened Native Functions (`__PBZ_NF__`) + `__PBZ_CRASH__`
// - FASTCALL-Hoisted Dual-Mode Masked BST VM + Register Frame Pool + Ephemeral Self-Wiping Root Proto

import { V5Op, V5_OPCODE_COUNT, RK_OFFSET } from "./bytecode.js";
import { emitOpaquePredicate } from "./v5-mba.js";
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
 * using hoisted FASTCALL primitives (`vmSym`) and SoA slot arrays `_c0.._c4`.
 * Audited so NO local name collides with `_c0.._c4`, `_q`, `_pc`, `_R`, `_K`, `_E`, `_U`,
 * `_P`, `_O`, `_md`, `_ks`, `_mb`, `_tw`, `_tp`, `_kLo`, `_fp`, `_fpn`, or hoisted primitives.
 */
function buildOpcodeHandlerBody(op, modeCfg, vCtx) {
    const {
        uSym, vmSym, rVar, kVar, envVar, pcVar, topVar, upVar, poolVar, openUvVar,
        modeVar, kSecVar, modeSlots, mbaDecVar, isFastMode,
    } = vCtx;

    const slots = modeSlots[modeCfg.modeId];
    const sA = slots[modeCfg.role.A];
    const sB = slots[modeCfg.role.B];
    const sC = slots[modeCfg.role.C];
    const sD = slots[modeCfg.role.D];
    const sOp = slots[modeCfg.role.op];
    const ox = modeCfg.opFieldXor[op];

    const decF = (arr, x) => x === 0 ? `${arr}[_q]` : `${vmSym.bx}(${arr}[_q],${x})`;
    const decA = decF(sA, ox[0]);
    const decB = decF(sB, ox[1]);
    const decC = decF(sC, ox[2]);
    const decD = `${sD}[_q]`;

    const rk = (expr) => `((_t<${RK_OFFSET})and ${rVar}[_t+1]or ${kVar}[_t-${RK_OFFSET - 1}])`.replace(/_t/g, `(${expr})`);

    const wipeEp = isFastMode ? `` : `if _ep then for _wi=1,_ni do _c0[_wi]=nil;_c1[_wi]=nil;_c2[_wi]=nil;_c3[_wi]=nil;_c4[_wi]=nil end end;`;
    const recFrame = `if not _O and _fpn<64 then _tclr(${rVar});_fpn=_fpn+1;_fp[_fpn]=${rVar} end;`;
    const yieldChk = `if _tw then _sc=_sc+1;if _sc%65536==0 then _tw() end end;`;

    // Zero-table.pack fast paths for C==1 (void) and C==2 (1 return value)
    const emitVarCall = (bExpr, cExpr) => {
        return `local _b=${bExpr};local _c=${cExpr};` +
            `if _c==1 then ` +
                `if _b==1 then _f() ` +
                `elseif _b==2 then _f(${rVar}[_a+2]) ` +
                `elseif _b==3 then _f(${rVar}[_a+2],${rVar}[_a+3]) ` +
                `elseif _b==4 then _f(${rVar}[_a+2],${rVar}[_a+3],${rVar}[_a+4]) ` +
                `elseif _b==0 then _f(${vmSym.tu}(${rVar},_a+2,${topVar})) ` +
                `else _f(${vmSym.tu}(${rVar},_a+2,_a+_b)) end ` +
            `elseif _c==2 then ` +
                `if _b==1 then ${rVar}[_a+1]=_f() ` +
                `elseif _b==2 then ${rVar}[_a+1]=_f(${rVar}[_a+2]) ` +
                `elseif _b==3 then ${rVar}[_a+1]=_f(${rVar}[_a+2],${rVar}[_a+3]) ` +
                `elseif _b==4 then ${rVar}[_a+1]=_f(${rVar}[_a+2],${rVar}[_a+3],${rVar}[_a+4]) ` +
                `elseif _b==0 then ${rVar}[_a+1]=_f(${vmSym.tu}(${rVar},_a+2,${topVar})) ` +
                `else ${rVar}[_a+1]=_f(${vmSym.tu}(${rVar},_a+2,_a+_b)) end ` +
            `else ` +
                `local _r;` +
                `if _b==1 then _r=${vmSym.tp}(_f()) ` +
                `elseif _b==2 then _r=${vmSym.tp}(_f(${rVar}[_a+2])) ` +
                `elseif _b==3 then _r=${vmSym.tp}(_f(${rVar}[_a+2],${rVar}[_a+3])) ` +
                `elseif _b==4 then _r=${vmSym.tp}(_f(${rVar}[_a+2],${rVar}[_a+3],${rVar}[_a+4])) ` +
                `elseif _b==0 then _r=${vmSym.tp}(_f(${vmSym.tu}(${rVar},_a+2,${topVar}))) ` +
                `else _r=${vmSym.tp}(_f(${vmSym.tu}(${rVar},_a+2,_a+_b))) end;` +
                `if _c==0 then for _i=1,_r.n do ${rVar}[_a+_i]=_r[_i] end;${topVar}=_a+_r.n ` +
                `else for _i=1,_c-1 do ${rVar}[_a+_i]=_r[_i] end end ` +
            `end `;
    };

    switch (op) {
        case V5Op.NOP:
            return ``;
        case V5Op.LOADK:
            return `${rVar}[${decA}+1]=${kVar}[${decB}+1]`;
        case V5Op.LOADNIL:
            return `do local _a=${decA};for _i=_a,_a+${decB} do ${rVar}[_i+1]=nil end end`;
        case V5Op.LOADBOOL:
            return `${rVar}[${decA}+1]=(${decB}~=0);if ${decC}~=0 then ${pcVar}=${decD} end`;
        case V5Op.MOVE:
            return `${rVar}[${decA}+1]=${rVar}[${decB}+1]`;
        case V5Op.GETGLOBAL:
            return `${rVar}[${decA}+1]=${envVar}[${kVar}[${decB}+1]]`;
        case V5Op.SETGLOBAL:
            return `${envVar}[${kVar}[${decB}+1]]=${rVar}[${decA}+1]`;
        case V5Op.GETTABLE:
            return `do local _t=${decC};${rVar}[${decA}+1]=${rVar}[${decB}+1][${rk("_t")}]end`;
        case V5Op.SETTABLE:
            return `do local _k=${decB};local _v=${decC};${rVar}[${decA}+1][${rk("_k")}]=${rk("_v")}end`;
        case V5Op.NEWTABLE:
            return `${rVar}[${decA}+1]={}`;
        case V5Op.ADD:
            return `do local _x=${decB};local _y=${decC};${rVar}[${decA}+1]=${rk("_x")}+${rk("_y")}end`;
        case V5Op.SUB:
            return `do local _x=${decB};local _y=${decC};${rVar}[${decA}+1]=${rk("_x")}-${rk("_y")}end`;
        case V5Op.MUL:
            return `do local _x=${decB};local _y=${decC};${rVar}[${decA}+1]=${rk("_x")}*${rk("_y")}end`;
        case V5Op.DIV:
            return `do local _x=${decB};local _y=${decC};${rVar}[${decA}+1]=${rk("_x")}/${rk("_y")}end`;
        case V5Op.MOD:
            return `do local _x=${decB};local _y=${decC};${rVar}[${decA}+1]=${rk("_x")}%${rk("_y")}end`;
        case V5Op.POW:
            return `do local _x=${decB};local _y=${decC};${rVar}[${decA}+1]=${rk("_x")}^${rk("_y")}end`;
        case V5Op.IDIV:
            return `do local _x=${decB};local _y=${decC};${rVar}[${decA}+1]=${vmSym.mf}(${rk("_x")}/${rk("_y")})end`;
        case V5Op.UNM:
            return `${rVar}[${decA}+1]=-${rVar}[${decB}+1]`;
        case V5Op.NOT:
            return `${rVar}[${decA}+1]=not ${rVar}[${decB}+1]`;
        case V5Op.LEN:
            return `${rVar}[${decA}+1]=#${rVar}[${decB}+1]`;
        case V5Op.CONCAT:
            return `do local _b=${decB};local _e=${decC};local _acc=${rVar}[_e+1];for _i=_e-1,_b,-1 do _acc=${rVar}[_i+1].._acc end;${rVar}[${decA}+1]=_acc end`;
        case V5Op.JMP:
            return `${yieldChk}${pcVar}=${decB}`;
        case V5Op.EQ:
            return `do local _x=${decB};local _y=${decC};if(${rk("_x")}==${rk("_y")})~=(${decA}~=0)then ${pcVar}=${pcVar}+1 end end`;
        case V5Op.LT:
            return `do local _x=${decB};local _y=${decC};if(${rk("_x")}<${rk("_y")})~=(${decA}~=0)then ${pcVar}=${pcVar}+1 end end`;
        case V5Op.LE:
            return `do local _x=${decB};local _y=${decC};if(${rk("_x")}<=${rk("_y")})~=(${decA}~=0)then ${pcVar}=${pcVar}+1 end end`;
        case V5Op.TEST:
            return `if(not ${rVar}[${decA}+1])==(${decC}~=0)then ${pcVar}=${pcVar}+1 end`;
        case V5Op.TESTSET:
            return `do local _bv=${rVar}[${decB}+1];if(not _bv)==(${decC}~=0)then ${pcVar}=${decD} else ${rVar}[${decA}+1]=_bv end end`;
        case V5Op.CALL:
            return `do local _a=${decA};local _f=${rVar}[_a+1];${emitVarCall(decB, decC)}end`;
        case V5Op.TAILCALL:
            return `do local _a=${decA};local _b=${decB};local _f=${rVar}[_a+1];${wipeEp}` +
                `if _b==1 then return _f() ` +
                `elseif _b==2 then return _f(${rVar}[_a+2]) ` +
                `elseif _b==3 then return _f(${rVar}[_a+2],${rVar}[_a+3]) ` +
                `elseif _b==4 then return _f(${rVar}[_a+2],${rVar}[_a+3],${rVar}[_a+4]) ` +
                `elseif _b==0 then return _f(${vmSym.tu}(${rVar},_a+2,${topVar})) ` +
                `else return _f(${vmSym.tu}(${rVar},_a+2,_a+_b)) end end`;
        case V5Op.RETURN:
            return `do local _a=${decA};local _b=${decB};` +
                `if _b==1 then ${wipeEp}${recFrame}return ` +
                `elseif _b==2 then local _r1=${rVar}[_a+1];${wipeEp}${recFrame}return _r1 ` +
                `elseif _b==3 then local _r1,_r2=${rVar}[_a+1],${rVar}[_a+2];${wipeEp}${recFrame}return _r1,_r2 ` +
                `elseif _b==0 then ${wipeEp}return ${vmSym.tu}(${rVar},_a+1,${topVar}) ` +
                `else ${wipeEp}return ${vmSym.tu}(${rVar},_a+1,_a+_b-1) end end`;
        case V5Op.FORPREP:
            return `do local _a=${decA};${rVar}[_a+1]=${rVar}[_a+1]-${rVar}[_a+3];${pcVar}=${decB} end`;
        case V5Op.FORLOOP:
            return `do ${yieldChk}local _a=${decA};local _st=${rVar}[_a+3];local _ix=${rVar}[_a+1]+_st;${rVar}[_a+1]=_ix;local _lm=${rVar}[_a+2];` +
                `if(_st>0 and _ix<=_lm)or(_st<=0 and _ix>=_lm)then ${pcVar}=${decB};${rVar}[_a+4]=_ix end end`;
        case V5Op.TFORLOOP:
            return `do ${yieldChk}local _a=${decA};local _c=${decC};local _r={${rVar}[_a+1](${rVar}[_a+2],${rVar}[_a+3])};` +
                `for _i=1,_c do ${rVar}[_a+3+_i]=_r[_i]end;if _r[1]~=nil then ${rVar}[_a+3]=_r[1];${pcVar}=${decD} end end`;
        case V5Op.ITERPREP:
            return `do local _a=${decA};local _it=${rVar}[_a+1];local _ity=${vmSym.ty}(_it);` +
                `if _ity=="table"or _ity=="userdata"then local _ok,_mt=${vmSym.pc}(${vmSym.gm},_it);` +
                `if _ok and ${vmSym.ty}(_mt)=="table"and _mt.__iter then ${rVar}[_a+1],${rVar}[_a+2],${rVar}[_a+3]=_mt.__iter(_it)` +
                `elseif _ity=="table"then ${rVar}[_a+1]=${vmSym.nx};${rVar}[_a+2]=_it;${rVar}[_a+3]=nil end end end`;
        case V5Op.SETLIST:
            return `do local _a=${decA};local _t=${rVar}[_a+1];local _b=${decB};if _b==0 then _b=${topVar}-(_a+1)end;local _bs=${decC}-1;for _i=1,_b do _t[_bs+_i]=${rVar}[_a+1+_i]end end`;
        case V5Op.CLOSURE:
            return `do local _pr=${poolVar}[_pr[7][${decB}+1]];` +
                `if _pr then local _nU={};local _ul=_pr[6];for _ui=1,#_ul do local _ud=_ul[_ui];` +
                `if _ud[1]==1 then if not ${openUvVar} then ${openUvVar}={} end;local _bk;local _tg=_ud[2]+1;for _oi=1,#${openUvVar} do if ${openUvVar}[_oi][2]==_tg then _bk=${openUvVar}[_oi];break end end;` +
                `if not _bk then _bk={${rVar},_tg};${openUvVar}[#${openUvVar}+1]=_bk end;_nU[_ui]=_bk else _nU[_ui]=${upVar}[_ud[2]+1]end end;` +
                `if not _pr[4]and _pr[2]<=4 then local _np=_pr[2];` +
                `if _np==0 then ${rVar}[${decA}+1]=function()return _vm(_pr,_nU,${envVar})end ` +
                `elseif _np==1 then ${rVar}[${decA}+1]=function(_1)return _vm(_pr,_nU,${envVar},_1)end ` +
                `elseif _np==2 then ${rVar}[${decA}+1]=function(_1,_2)return _vm(_pr,_nU,${envVar},_1,_2)end ` +
                `elseif _np==3 then ${rVar}[${decA}+1]=function(_1,_2,_3)return _vm(_pr,_nU,${envVar},_1,_2,_3)end ` +
                `else ${rVar}[${decA}+1]=function(_1,_2,_3,_4)return _vm(_pr,_nU,${envVar},_1,_2,_3,_4)end end ` +
                `else ${rVar}[${decA}+1]=function(...)local _ac=${vmSym.sel}("#",...);local _ag={...};return _vm(_pr,_nU,${envVar},_ag[1],_ag[2],_ag[3],_ag[4],_ag,_ac)end end ` +
                `else ${rVar}[${decA}+1]=nil end end`;
        case V5Op.VARARG:
            return `do local _a=${decA};local _b=${decB};if _b==0 then if _vac>0 then for _i=1,_vac do ${rVar}[_a+_i]=_va[_i] end end;${topVar}=_a+_vac else for _i=1,_b-1 do ${rVar}[_a+_i]=_va and _va[_i]or nil end end end`;
        case V5Op.SELF:
            return `do local _a=${decA};local _o=${rVar}[${decB}+1];local _fc=${decC};${rVar}[_a+2]=_o;${rVar}[_a+1]=_o[${rk("_fc")}]end`;
        case V5Op.GETUPVAL:
            return `do local _b=${upVar}[${decB}+1];if _b[2]then ${rVar}[${decA}+1]=_b[1][_b[2]]else ${rVar}[${decA}+1]=_b[1]end end`;
        case V5Op.SETUPVAL:
            return `do local _b=${upVar}[${decB}+1];if _b[2]then _b[1][_b[2]]=${rVar}[${decA}+1]else _b[1]=${rVar}[${decA}+1]end end`;
        case V5Op.CLOSEUPVAL:
            return `if ${openUvVar} then do local _a=${decA}+1;local _n=0;for _i=1,#${openUvVar} do local _b=${openUvVar}[_i];if _b[2]>=_a then _b[1]=_b[1][_b[2]];_b[2]=nil else _n=_n+1;${openUvVar}[_n]=_b end end;for _i=_n+1,#${openUvVar} do ${openUvVar}[_i]=nil end end end`;
        case V5Op.PCALL:
            return `do local _a=${decA};local _b=${decB};local _c=${decC};local _f=${rVar}[_a+1];local _we=_b==0 and ${topVar} or _a+_b;local _r;` +
                `if _b==1 then _r=${vmSym.tp}(${vmSym.pc}(_f)) ` +
                `elseif _b==2 then _r=${vmSym.tp}(${vmSym.pc}(_f,${rVar}[_a+2])) ` +
                `elseif _b==3 then _r=${vmSym.tp}(${vmSym.pc}(_f,${rVar}[_a+2],${rVar}[_a+3])) ` +
                `else _r=${vmSym.tp}(${vmSym.pc}(_f,${vmSym.tu}(${rVar},_a+2,_we))) end;` +
                `if _c==0 then for _i=1,_r.n do ${rVar}[_a+_i]=_r[_i] end;${topVar}=_a+_r.n else for _i=1,_c-1 do ${rVar}[_a+_i]=_r[_i] end end;` +
                `if _b==0 or _b>1 then local _ws=_c==0 and(_a+_r.n+1)or(_a+_c);for _wi=_ws,_we do ${rVar}[_wi]=nil end end end`;
        case V5Op.XPCALL:
            return `do local _a=${decA};local _b=${decB};local _c=${decC};local _f=${rVar}[_a+1];local _eh=${rVar}[_a+2];local _we=_b==0 and ${topVar} or _a+_b;local _r;` +
                `if _b==1 or _b==2 then _r=${vmSym.tp}(${vmSym.xpc}(_f,_eh)) ` +
                `elseif _b==3 then _r=${vmSym.tp}(${vmSym.xpc}(_f,_eh,${rVar}[_a+3])) ` +
                `else _r=${vmSym.tp}(${vmSym.xpc}(_f,_eh,${vmSym.tu}(${rVar},_a+3,_we))) end;` +
                `if _c==0 then for _i=1,_r.n do ${rVar}[_a+_i]=_r[_i] end;${topVar}=_a+_r.n else for _i=1,_c-1 do ${rVar}[_a+_i]=_r[_i] end end;` +
                `if _b==0 or _b>2 then local _ws=_c==0 and(_a+_r.n+1)or(_a+_c);for _wi=_ws,_we do ${rVar}[_wi]=nil end end end`;
        case V5Op.F_TEST_JMP:
            return `if(not ${rVar}[${decA}+1])~=(${decC}~=0)then ${pcVar}=${decB} end`;
        case V5Op.F_EQ_JMP:
            return `do local _x=${decB};local _y=${decC};if(${rk("_x")}==${rk("_y")})==(${decA}~=0)then ${pcVar}=${decD} end end`;
        case V5Op.F_LT_JMP:
            return `do local _x=${decB};local _y=${decC};if(${rk("_x")}<${rk("_y")})==(${decA}~=0)then ${pcVar}=${decD} end end`;
        case V5Op.F_LE_JMP:
            return `do local _x=${decB};local _y=${decC};if(${rk("_x")}<=${rk("_y")})==(${decA}~=0)then ${pcVar}=${decD} end end`;
        case V5Op.F_TESTSET_JMP:
            return `do local _bv=${rVar}[${decB}+1];if(not _bv)~=(${decC}~=0)then ${rVar}[${decA}+1]=_bv;${pcVar}=${decD} end end`;
        case V5Op.F_TFORLOOP_JMP:
            return `do ${yieldChk}local _a=${decA};local _c=${decC};local _r={${rVar}[_a+1](${rVar}[_a+2],${rVar}[_a+3])};` +
                `for _i=1,_c do ${rVar}[_a+3+_i]=_r[_i]end;if _r[1]~=nil then ${rVar}[_a+3]=_r[1]else ${pcVar}=${decB} end end`;
        case V5Op.F_GGET:
            return `do local _g=${envVar}[${kVar}[${decB}+1]];${rVar}[${decA}+1]=_g;local _t=${decD};${rVar}[${decC}+1]=_g[${rk("_t")}]end`;
        case V5Op.F_LOADKK:
            return `${rVar}[${decA}+1]=${kVar}[${decB}+1];${rVar}[${decC}+1]=${kVar}[${decD}+1]`;
        case V5Op.F_MOVE_MOVE:
            return `${rVar}[${decA}+1]=${rVar}[${decB}+1];${rVar}[${decC}+1]=${rVar}[${decD}+1]`;
        case V5Op.F_SELF_CALL:
            return `do local _a=${decA};local _o=${rVar}[${decB}+1];local _fc=${decC};local _d=${decD};${rVar}[_a+2]=_o;local _f=_o[${rk("_fc")}];${rVar}[_a+1]=_f;` +
                `${emitVarCall(`${vmSym.rs}(_d,16)`, `${vmSym.ba}(_d,65535)`)}end`;
        case V5Op.F_GGET_CALL:
            return `do local _a=${decA};local _g=${envVar}[${kVar}[${decB}+1]];local _fc=${decC};local _d=${decD};local _f=_g[${rk("_fc")}];${rVar}[_a+1]=_f;` +
                `${emitVarCall(`${vmSym.rs}(_d,16)`, `${vmSym.ba}(_d,65535)`)}end`;
        case V5Op.F_LOADK_RET:
            return `do local _r1=${kVar}[${decB}+1];${wipeEp}${recFrame}return _r1 end`;
        case V5Op.F_MOVE_RET:
            return `do ${rVar}[${decA}+1]=${rVar}[${decB}+1];local _ra=${decC};local _rb=${decD};` +
                `if _rb==1 then ${wipeEp}${recFrame}return ` +
                `elseif _rb==2 then local _r1=${rVar}[_ra+1];${wipeEp}${recFrame}return _r1 ` +
                `elseif _rb==0 then ${wipeEp}return ${vmSym.tu}(${rVar},_ra+1,${topVar}) ` +
                `else ${wipeEp}return ${vmSym.tu}(${rVar},_ra+1,_ra+_rb-1) end end`;
        case V5Op.S_CALL0:
            return `do local _a=${decA};${rVar}[_a+1]=${rVar}[_a+1]()end`;
        case V5Op.S_CALL1:
            return `do local _a=${decA};${rVar}[_a+1]=${rVar}[_a+1](${rVar}[_a+2])end`;
        case V5Op.S_CALL2:
            return `do local _a=${decA};${rVar}[_a+1]=${rVar}[_a+1](${rVar}[_a+2],${rVar}[_a+3])end`;
        case V5Op.S_CALL0_VOID:
            return `do local _a=${decA};${rVar}[_a+1]()end`;
        case V5Op.S_CALL1_VOID:
            return `do local _a=${decA};${rVar}[_a+1](${rVar}[_a+2])end`;
        case V5Op.S_CALL2_VOID:
            return `do local _a=${decA};${rVar}[_a+1](${rVar}[_a+2],${rVar}[_a+3])end`;
        case V5Op.S_CALL3:
            return `do local _a=${decA};${rVar}[_a+1]=${rVar}[_a+1](${rVar}[_a+2],${rVar}[_a+3],${rVar}[_a+4])end`;
        case V5Op.S_GETFIELD_K:
            return `${rVar}[${decA}+1]=${rVar}[${decB}+1][${kVar}[${decC}+1]]`;
        case V5Op.S_SETFIELD_K:
            return `do local _v=${decC};${rVar}[${decA}+1][${kVar}[${decB}+1]]=${rk("_v")}end`;
        case V5Op.S_UPVAL_GET:
            return `do local _b=${upVar}[${decB}+1];local _uv=(_b[2]and _b[1][_b[2]]or _b[1]);${rVar}[${decA}+1]=_uv;local _t=${decD};${rVar}[${decC}+1]=_uv[${rk("_t")}]end`;
        case V5Op.S_ADD_K:
            return `${rVar}[${decA}+1]=${rVar}[${decB}+1]+${kVar}[${decC}+1]`;
        case V5Op.S_SUB_K:
            return `${rVar}[${decA}+1]=${rVar}[${decB}+1]-${kVar}[${decC}+1]`;
        case V5Op.S_MUL_K:
            return `${rVar}[${decA}+1]=${rVar}[${decB}+1]*${kVar}[${decC}+1]`;
        case V5Op.S_MOD_K:
            return `${rVar}[${decA}+1]=${rVar}[${decB}+1]%${kVar}[${decC}+1]`;
        case V5Op.OP_MODE_SWITCH:
            return `${pcVar}=${decA};${modeVar}=${decB}`;
        case V5Op.OP_DECRYPT_BLK: {
            const nopStored = (modeCfg.opEncode[V5Op.NOP] ^ vCtx.kLo ^ modeCfg.mSalt) >>> 0;
            const c0 = slots[0], c1 = slots[1], c2 = slots[2], c3 = slots[3], c4 = slots[4];
            return `do local _ln=${decA};local _l=${vmSym.bx}(${decB},${kSecVar});` +
                `for _k=1,_ln do local _idx=_q+_k;` +
                `_l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;${c0}[_idx]=${vmSym.bx}(${c0}[_idx],_l);` +
                `_l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;${c1}[_idx]=${vmSym.bx}(${c1}[_idx],_l);` +
                `_l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;${c2}[_idx]=${vmSym.bx}(${c2}[_idx],_l);` +
                `_l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;${c3}[_idx]=${vmSym.bx}(${c3}[_idx],_l);` +
                `_l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;${c4}[_idx]=${vmSym.bx}(${c4}[_idx],_l)end;` +
                `${sOp}[_q]=${vmSym.bx}(${nopStored ^ vCtx.kLo},_kLo)end`;
        }
        case V5Op.OP_MBA_DECODE_0:
        case V5Op.OP_MBA_DECODE_1:
        case V5Op.OP_MBA_DECODE_2:
        case V5Op.OP_MBA_DECODE_3: {
            const cIdx = op - V5Op.OP_MBA_DECODE_0;
            const decFn = `${mbaDecVar}[${cIdx + 1}]`;
            return `do local _mk=${vmSym.bx}(${uSym.ta}(_q,2654435761),${kSecVar});` +
                `${sA}[_q]=${decFn}(${sA}[_q],_mk);` +
                `${sB}[_q]=${decFn}(${sB}[_q],_mk);` +
                `${sC}[_q]=${decFn}(${sC}[_q],_mk);` +
                `${sOp}[_q]=${decFn}(${sD}[_q],_mk);` +
                `${sD}[_q]=0;${pcVar}=_q end`;
        }
        default:
            return ``;
    }
}

/**
 * Generates the entire Sentinel v5.1 APEX self-contained Luau payload.
 * @param {object} container
 * @param {object} ctx
 * @param {object} [options] - supports placeId, targetPlaceId, robloxOnly, nativeFuncs
 * @param {() => number} rng
 */
export function generateV5Lua(container, ctx, options = {}, rng) {
    const usedIds = new Set();
    const ident = (minLen = 2, maxLen = 4) => {
        const first = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_";
        const rest = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
        const reserved = new Set([
            "and", "break", "do", "else", "elseif", "end", "false", "for", "function", "if",
            "in", "local", "nil", "not", "or", "repeat", "return", "then", "true", "until", "while",
            "continue", "type", "export", "U", "A", "B", "C", "D", "_q", "_pc", "_kLo", "_z",
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

    const taFn = `function(h,e)local c=${uSym.ba};h,e=c(h,4294967295),c(e,4294967295);local u,r,l,m,ll=c(h,65535),${uSym.rs},c(e,65535),${uSym.rs}(h,16),${uSym.rs}(e,16);return c(u*l+${uSym.ls}(c(u*ll+m*l,65535),16),4294967295)%4294967296 end`;
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

    // Integrity derivation key & security traps
    const initialSec = 0x2000 + Math.floor(rng() * 0x5FFF);
    let expectedAcc = initialSec;
    const wA = 0x13 + Math.floor(rng() * 120);
    const wB = 0x29 + Math.floor(rng() * 120);
    const wC = 0x41 + Math.floor(rng() * 120);
    const wP1 = 0x17 + Math.floor(rng() * 120);
    const wP2 = 0x35 + Math.floor(rng() * 120);
    const wD = 0x5D + Math.floor(rng() * 120);
    const poison1 = 0x101 + Math.floor(rng() * 0xFE00);
    const poison2 = 0x101 + Math.floor(rng() * 0xFE00);
    const mixStep = (acc, w) => (((acc * 31 + w) & 0xFFFF) ^ ((w * 7) & 0xFFFF)) & 0xFFFF;
    expectedAcc = mixStep(expectedAcc, wA);
    expectedAcc = mixStep(expectedAcc, wB);
    expectedAcc = mixStep(expectedAcc, wC);
    expectedAcc = mixStep(expectedAcc, 128); // IEEE-754 -0.0 sign-byte parity
    expectedAcc = mixStep(expectedAcc, wP1);
    expectedAcc = mixStep(expectedAcc, wP2);

    const targetPlaceId = Number(options.placeId || options.targetPlaceId || 0);
    const hasPlaceLock = targetPlaceId > 0;
    const robloxOnly = Boolean(options.robloxOnly);
    const shareA = 0x1100 + Math.floor(rng() * 0x7E00);
    const shareB = ((0x1000 + Math.floor(rng() * 0xDE00)) ^ shareA) & 0xFFFF;
    const dynSalt = hasPlaceLock ? (targetPlaceId & 0xFFFF) : ((shareA ^ shareB) & 0xFFFF);
    expectedAcc = mixStep(expectedAcc, dynSalt);
    expectedAcc = mixStep(expectedAcc, wD);

    // Non-zero target derivation key: K_sec = bxor(acc, K_MASK) == K_TARGET != 0
    const K_MASK = (expectedAcc ^ ctx.K_TARGET) & 0xFFFF;

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

    // Security Gate Method `U[methSec]`
    uEntries.push(`[${JSON.stringify(methSec)}]=function(U)` +
        `local _a=${initialSec};` +
        `if ${emitOpaquePredicate(rng, uSym, true)} then local _m=${uSym.ba}(_a*31+${wA},65535);_a=${uSym.ba}(${uSym.bx}(_m,${(wA * 7) & 0xFFFF}),65535) end;` +
        `if ${uSym.pc}(function() local _t=${uSym.sm}({},{[${uSym.sc}(95,95,105,110,100,101,120)]=function() return 79 end});if _t[1]~=79 then ${uSym.er}(1) end end) then local _m=${uSym.ba}(_a*31+${wB},65535);_a=${uSym.ba}(${uSym.bx}(_m,${(wB * 7) & 0xFFFF}),65535) end;` +
        `local _ok=${uSym.pc}(function() if debug and debug.info then local _d=function() end;local _s1,_src=${uSym.pc}(debug.info,_d,"s");if _s1 and _src=="[C]" then ${uSym.er}(1) end;local _s2,_fn=${uSym.pc}(debug.info,_d,"f");if _s2 and _fn~=_d then ${uSym.er}(1) end end end);` +
        `if _ok then local _m=${uSym.ba}(_a*31+${wC},65535);_a=${uSym.ba}(${uSym.bx}(_m,${(wC * 7) & 0xFFFF}),65535) end;` +
        // IEEE-754 -0.0 buffer derivation + zero-wipe (exact parity 128 on pure-Lua fallback)
        `local _bv=0;` +
        `if ${uSym.ty}(buffer)=="table"and buffer.create and buffer.writef64 and buffer.readu32 and buffer.fill then ` +
            `local _bf=buffer.create(24);buffer.writef64(_bf,16,0/-28);_bv=${uSym.rs}(buffer.readu32(_bf,20),24);buffer.fill(_bf,0,0,24)` +
        `else _bv=((1/(0/-28))==-math.huge)and 128 or 0 end;` +
        `local _mbv=${uSym.ba}(_a*31+_bv,65535);_a=${uSym.ba}(${uSym.bx}(_mbv,${uSym.ba}(_bv*7,65535)),65535);` +
        // Exception-path side-channel traps
        `local _ok1=${uSym.pc}(function() local _x=0;local _=_x[nil];_a=${uSym.bx}(_a,${poison1}) end);` +
        `if not _ok1 then local _m=${uSym.ba}(_a*31+${wP1},65535);_a=${uSym.ba}(${uSym.bx}(_m,${(wP1 * 7) & 0xFFFF}),65535) end;` +
        `local _ok2=false;` +
        `if ${uSym.ty}(table)=="table"and table.freeze then _ok2=${uSym.pc}(function() local _ft=table.freeze({});_ft[1]=1;_a=${uSym.bx}(_a,${poison2}) end) end;` +
        `if not _ok2 then local _m=${uSym.ba}(_a*31+${wP2},65535);_a=${uSym.ba}(${uSym.bx}(_m,${(wP2 * 7) & 0xFFFF}),65535) end;` +
        // PlaceId / DataModel check
        `local _ds=0;` +
        (hasPlaceLock
            ? `${uSym.pc}(function() local _g=(${uSym.ty}(game)=="userdata" and game) or (type(${uSym.gg})=="function" and ${uSym.gg}().game);if _g and ${uSym.ty}(_g)=="userdata" and _g.PlaceId then _ds=${uSym.ba}(_g.PlaceId,65535) end end);`
            : `${uSym.pc}(function() if game~=nil then local _tg=${uSym.ty}(game);if _tg=="userdata" then if game.ClassName=="DataModel" then _ds=${uSym.bx}(${shareA},${shareB}) end elseif _tg=="table" then _ds=${robloxOnly ? "0" : `${uSym.bx}(${shareA},${shareB})`} end else ${robloxOnly ? "_ds=0" : `_ds=${uSym.bx}(${shareA},${shareB})`} end end);`
        ) +
        `local _md=${uSym.ba}(_a*31+_ds,65535);_a=${uSym.ba}(${uSym.bx}(_md,${uSym.ba}((_ds*7),65535)),65535);` +
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
        `if not _tr then local _mw=${uSym.ba}(_a*31+${wD},65535);_a=${uSym.ba}(${uSym.bx}(_mw,${(wD * 7) & 0xFFFF}),65535) end;` +
        `return ${uSym.bx}(_a,${K_MASK}) end`
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

    // Stage 1: ASSEMBLE_B85 -> (ST.RC4_DEC, _ks, _cb, _clen, nil)
    uEntries.push(`[${P.shB85}]=function(U,_ks,_a,_b,_c)` +
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
        `return ${ST.RC4_DEC},_ks,_cb,_clen,nil end`
    );

    // Stage 2: RC4_DEC -> (ST.LZSS_DEC, _ks, _pb, _clen, nil)
    uEntries.push(`[${P.shRc4}]=function(U,_ks,_cb,_cl,_c)` +
        `local _rk=${rc4KeyExpr};` +
        `local _kLo=${uSym.ba}(_ks,255);local _kHi=${uSym.ba}(${uSym.rs}(_ks,8),255);` +
        `local _S={};for _i=0,255 do _S[_i]=_i end;` +
        `local _kl=#_rk;local _j=0;for _i=0,255 do local _kv=${uSym.bx}(_rk[(_i%_kl)+1],((_i%2==1)and _kHi or _kLo));_j=(_j+_S[_i]+_kv)%256;_S[_i],_S[_j]=_S[_j],_S[_i] end;` +
        `local _pb=${uSym.bcr}(_cl);local _a,_b=0,0;` +
        `for _k=0,_cl-1 do _a=(_a+1)%256;_b=(_b+_S[_a])%256;_S[_a],_S[_b]=_S[_b],_S[_a];${uSym.bw8}(_pb,_k,${uSym.bx}(${uSym.br8}(_cb,_k),_S[(_S[_a]+_S[_b])%256])) end;` +
        `return ${ST.LZSS_DEC},_ks,_pb,_cl,nil end`
    );

    // Stage 3: LZSS_DEC -> (ST.PARSE_PROTOS, _ks, _raw, _rawLen, nil)
    uEntries.push(`[${P.shLzss}]=function(U,_ks,_pb,_cl,_c)` +
        `local _flg=${uSym.br8}(_pb,0);` +
        `local _rawLen=${uSym.br8}(_pb,1)+${uSym.br8}(_pb,2)*256+${uSym.br8}(_pb,3)*65536+${uSym.br8}(_pb,4)*16777216;` +
        `if _rawLen<0 or _rawLen>67108864 then ${uSym.er}("") end;` +
        `local _raw=${uSym.bcr}(_rawLen);` +
        `if _flg==0 then for _i=0,_rawLen-1 do ${uSym.bw8}(_raw,_i,${uSym.br8}(_pb,5+_i)) end ` +
        `else local _p=5;local _op=0;while _p<_cl do local _ct=${uSym.br8}(_pb,_p);_p=_p+1;` +
        `if _ct<128 then local _n=_ct+1;for _j=1,_n do ${uSym.bw8}(_raw,_op,${uSym.br8}(_pb,_p));_op=_op+1;_p=_p+1 end;` +
        `elseif _ct<192 then local _ll=_ct-124;local _lo=${uSym.br8}(_pb,_p)+1;_p=_p+1;for _j=1,_ll do ${uSym.bw8}(_raw,_op,${uSym.br8}(_raw,_op-_lo));_op=_op+1 end;` +
        `else local _ll=_ct-188;local _lo=${uSym.br8}(_pb,_p)*256+${uSym.br8}(_pb,_p+1);_p=_p+2;for _j=1,_ll do ${uSym.bw8}(_raw,_op,${uSym.br8}(_raw,_op-_lo));_op=_op+1 end end end end;` +
        `return ${ST.PARSE_PROTOS},_ks,_raw,_rawLen,nil end`
    );

    // Stage 4: PARSE_PROTOS -> (ST.EXEC, _pool, _ridx, _decStr, nil)
    uEntries.push(`[${P.shParse}]=function(U,_ks,_raw,_rl,_c)` +
        `local _isb=${invSboxExpr};` +
        `local _kLo=${uSym.ba}(_ks,255);local _kHi=${uSym.ba}(${uSym.rs}(_ks,8),255);` +
        `local _pos=0;` +
        `local function _ru() local _v,_m=0,1;while true do local _b=${uSym.br8}(_raw,_pos);_pos=_pos+1;_v=_v+${uSym.ba}(_b,127)*_m;if _b<128 then return _v end;_m=_m*128 end end;` +
        `local _plen=_ru();local _sbuf=${uSym.bcr}(_plen);for _i=0,_plen-1 do ${uSym.bw8}(_sbuf,_i,${uSym.br8}(_raw,_pos+_i)) end;_pos=_pos+_plen;` +
        `local _scache={};` +
        `local function _decStr(_off,_ln,_sl)` +
        `local _ck=_off*65537+_ln;local _cv=_scache[_ck];if _cv~=nil then return _cv end;` +
        `local _l=${uSym.bx}(_sl,_ks);local _t={};` +
        `for _i=0,_ln-1 do _l=(${uSym.ta}(_l,1664525)+1013904223)%4294967296;` +
        `local _kb=${uSym.bx}(${uSym.rs}(_l,16),((_i%2==1)and _kHi or _kLo));_kb=${uSym.ba}(_kb,255);` +
        `local _sv=${uSym.bx}(${uSym.br8}(_sbuf,_off+_i),_kb);` +
        `_t[_i+1]=${uSym.sc}(_isb[_sv+1]) end;` +
        `local _str=${uSym.tcon}(_t);_scache[_ck]=_str;return _str end;` +
        `local _np=_ru();local _ridx=_ru()+1;local _pool={};` +
        `for _pi=1,_np do ` +
        `local _npa=_ru();local _mr=_ru();local _fl=${uSym.br8}(_raw,_pos);_pos=_pos+1;` +
        `local _nk=_ru();local _K={};local _ksd={};` +
        `for _ki=1,_nk do local _tg=${uSym.br8}(_raw,_pos);_pos=_pos+1;` +
        `if _tg==${TAG_NIL} then _K[_ki]=nil ` +
        `elseif _tg==${TAG_FALSE} then _K[_ki]=false ` +
        `elseif _tg==${TAG_TRUE} then _K[_ki]=true ` +
        `elseif _tg==${TAG_NUM} then _K[_ki]=${uSym.brf64}(_raw,_pos);_pos=_pos+8 ` +
        `elseif _tg==${TAG_STR} then _ksd[_ki]={_ru(),_ru(),_ru()} end end;` +
        `local _kmt={};_kmt[${uSym.sc}(95,95,105,110,100,101,120)]=function(t,i) local _sd=_ksd[i];if _sd then local _s=_decStr(_sd[1],_sd[2],_sd[3]);_ksd[i]=nil;${uSym.rset}(t,i,_s);return _s end;return nil end;` +
        `_kmt[${uSym.sc}(95,95,110,101,119,105,110,100,101,120)]=function() end;_kmt[${uSym.sc}(95,95,109,101,116,97,116,97,98,108,101)]=false;` +
        `${uSym.sm}(_K,_kmt);` +
        `local _nuv=_ru();local _uvs={};for _ui=1,_nuv do local _il=${uSym.br8}(_raw,_pos);_pos=_pos+1;_uvs[_ui]={_il,_ru()} end;` +
        `local _nc=_ru();local _chp={};for _ci=1,_nc do _chp[_ci]=_ru()+1 end;` +
        `local _ni=_ru();local _a0,_a1,_a2,_a3,_a4={},{},{},{},{};` +
        `for _j=1,_ni do _a0[_j]=_ru() end;` +
        `for _j=1,_ni do _a1[_j]=_ru() end;` +
        `for _j=1,_ni do _a2[_j]=_ru() end;` +
        `for _j=1,_ni do _a3[_j]=_ru() end;` +
        `for _j=1,_ni do _a4[_j]=_ru() end;` +
        `_pool[_pi]={_K,_npa,_mr,(_fl%2==1),(${uSym.ba}(_fl,2)~=0 and 1 or 0),_uvs,_chp,_ni,_a0,_a1,_a2,_a3,_a4,(${uSym.ba}(_fl,4)~=0),(${uSym.ba}(_fl,8)~=0),(${uSym.ba}(_fl,16)~=0)}` +
        `end;return ${ST.EXEC},_pool,_ridx,_decStr,nil end`
    );

    // Trampoline Driver `U[methParse]`
    uEntries.push(`[${JSON.stringify(methParse)}]=function(U,_ks)` +
        `local _tp={[${ST.ASSEMBLE_B85}]=${P.shB85},[${ST.RC4_DEC}]=${P.shRc4},[${ST.LZSS_DEC}]=${P.shLzss},[${ST.PARSE_PROTOS}]=${P.shParse}};` +
        `local _st=${ST.ASSEMBLE_B85};local _s1,_s2,_s3,_s4=_ks,nil,nil,nil;` +
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

    // 5. Build FASTCALL-Hoisted Interpreter `U[P.run]` with Anti-vmmap Dual-Mode BST & Register Frame Pool
    const rVar = "_R";
    const kVar = "_K";
    const envVar = "_E";
    const pcVar = "_pc";
    const topVar = "_tp";
    const upVar = "_U";
    const poolVar = "_P";
    const openUvVar = "_O";
    const modeVar = "_md";
    const kSecVar = "_ks";
    const mbaDecVar = "_mb";
    const opVar = "_op";
    const twVar = "_tw";
    const cArrVars = ["_c0", "_c1", "_c2", "_c3", "_c4"];

    const vmSym = {
        ...uSym,
        bx: "_bx", ba: "_ba", rs: "_rs", mf: "_mf",
        tu: "_tu", tp: "_tpack", tc: "_tc", ty: "_ty",
        sel: "_sel", pc: "_pc2", xpc: "_xpc2", nx: "_nx", gm: "_gm",
    };

    const mbaInitExpr = `{${ctx.mbaCodecs.map(c => c.emitLuaDecoderFn(vmSym)).join(",")}}`;

    const isFastMode = Boolean(ctx.isFastMode || ctx.level === "fast");

    const buildModeDispatch = (modeCfg) => {
        const usedSet = ctx.usedOps[modeCfg.modeId];
        const entries = [];
        for (let op = 0; op < V5_OPCODE_COUNT; op++) {
            if (!usedSet.has(op)) continue;
            const body = buildOpcodeHandlerBody(op, modeCfg, {
                uSym, vmSym, rVar, kVar, envVar, pcVar, topVar, upVar, poolVar, openUvVar,
                modeVar, kSecVar, modeSlots: [cArrVars, cArrVars],
                mbaDecVar, modes: ctx.modes, twVar, kLo: ctx.kLo, isFastMode,
            });
            entries.push({ id: modeCfg.opEncode[op], body });
        }
        entries.sort((a, b) => a.id - b.id);
        return buildAntiVmmapBST(entries, opVar, rng, vmSym, ctx.level);
    };

    const wipeEpEnd = isFastMode ? `` : `if _ep then for _wi=1,_ni do _c0[_wi]=nil;_c1[_wi]=nil;_c2[_wi]=nil;_c3[_wi]=nil;_c4[_wi]=nil end end;`;
    const recFrameEnd = `if not _O and _fpn<64 then _tclr(${rVar});_fpn=_fpn+1;_fp[_fpn]=${rVar} end;`;

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
            `local _q=${pcVar};${pcVar}=${pcVar}+1;` +
            `if ${modeVar}==0 then ` +
            `local ${opVar}=_bx(${opCol0}[_q],_om0);` +
            `${bst0} ` +
            `else ` +
            `local ${opVar}=_bx(${opCol1}[_q],_om1);` +
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
                `local _q=${pcVar};${pcVar}=${pcVar}+1;` +
                `local ${opVar}=${opCol0}[_q];` +
                `${bst0} end;` +
                `${recFrameEnd}`;
        } else {
            dispatchLoopCode =
                `while ${pcVar}<=_ni do ` +
                `local _q=${pcVar};${pcVar}=${pcVar}+1;` +
                `local ${opVar}=_bx(${opCol0}[_q],_om0);` +
                `${bst0} end;` +
                `${wipeEpEnd}${recFrameEnd}`;
        }
    }

    const mbaInitLine = ctx.mbaCodecs.length > 0
        ? `local ${mbaDecVar}=${mbaInitExpr};`
        : ``;

    const fastPreUnmask = isFastMode
        ? `do local _col=${9 + ctx.modes[0].role.op};for _pi=1,#${poolVar} do local _pp=${poolVar}[_pi];local _oc=_pp[_col];for _i=1,_pp[8] do _oc[_i]=_bx(_oc[_i],_om0) end end end;`
        : ``;

    uEntries.push(`[${P.run}]=function(U,${poolVar},${kSecVar},${twVar})` +
        `local _bx,_ba,_rs,_mf,_tu,_tpack,_tc,_ty,_sel,_pc2,_xpc2,_nx,_gm=` +
            `U[${P.bx}],U[${P.ba}],U[${P.rs}],U[${P.mf}],U[${P.tu}],U[${P.tp}],U[${P.tc}],U[${P.ty}],U[${P.sel}],U[${P.pc}],U[${P.xpc}],U[${P.nx}],U[${P.gm}];` +
        `local _tclr=(_ty(table)=="table"and table.clear)or function(t)for _ri=1,#t do t[_ri]=nil end end;` +
        `local _kLo=_ba(${kSecVar},255);` +
        `local _fp,_fpn={},0;local _sc=0;` +
        omInitLine +
        fastPreUnmask +
        mbaInitLine +
        `local _vm;_vm=function(_pr,${upVar},${envVar},_a1,_a2,_a3,_a4,_vaArg,_vacArg)` +
        (isFastMode
            ? `local ${kVar}=_pr[1];local _npa=_pr[2];local _mr=_pr[3];local _isVa=_pr[4];local _ni=_pr[8];`
            : `local ${kVar}=_pr[1];local _npa=_pr[2];local _mr=_pr[3];local _isVa=_pr[4];local ${modeVar}=_pr[5];local _ni=_pr[8];local _ep=_pr[14];`
        ) +
        `local _c0,_c1,_c2,_c3,_c4=_pr[9],_pr[10],_pr[11],_pr[12],_pr[13];` +
        `local ${rVar};if _fpn>0 then ${rVar}=_fp[_fpn];_fp[_fpn]=nil;_fpn=_fpn-1 else ${rVar}=_tc(_mr+2) end;` +
        `local _va,_vac;` +
        `if not _isVa and _npa<=4 then ` +
            `if _npa>=1 then ${rVar}[1]=_a1 end;if _npa>=2 then ${rVar}[2]=_a2 end;` +
            `if _npa>=3 then ${rVar}[3]=_a3 end;if _npa>=4 then ${rVar}[4]=_a4 end ` +
        `else ` +
            `for _i=1,((_vacArg<_npa)and _vacArg or _npa)do ${rVar}[_i]=_vaArg[_i] end;` +
            `if _isVa then _vac=_vacArg-_npa;if _vac<0 then _vac=0 end;if _vac>0 then _va={};for _i=1,_vac do _va[_i]=_vaArg[_npa+_i] end end end ` +
        `end;` +
        `local ${pcVar}=1;local ${openUvVar};local ${topVar}=0;` +
        `${dispatchLoopCode} ` +
        `end;return _vm end`
    );

    // 6. Boot Method `U[P.boot](U, ...)`
    uEntries.push(`[${JSON.stringify(P.boot)}]=function(U,...)` +
        `local _ks=U:${methSec}();` +
        `local _pl,_ri,_ds=U:${methParse}(_ks);` +
        `local _nf={};` +
        `local _env=U:${methEnv}(_nf);` +
        (hasNative ? `U[${P.nfInit}](U,_nf,_env,_ds);` : ``) +
        `local _tw;do local _t=_env[${uSym.sc}(116,97,115,107)];if ${uSym.ty}(_t)=="table"then _tw=_t[${uSym.sc}(119,97,105,116)]end end;` +
        `local _vm=U[${P.run}](U,_pl,_ks,_tw);` +
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
