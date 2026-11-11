   import { REG_OPCODE_COUNT, RK_OFFSET } from "./bytecode.js";
import { randomBytes } from "crypto";
import { writeFileSync as _dumpWrite } from "fs";
import { encryptAndEncode } from "./lzma.js";
import { generateBootstrap } from "./bootstrap-template.js";
let _rngState = 0;
function seedRandom(s) {
    _rngState = s >>> 0;
}
function rng() {
    _rngState = (_rngState + 0x6D2B79F5) >>> 0;
    let t = Math.imul(_rngState ^ (_rngState >>> 15), 1 | _rngState);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 0x100000000;
}
const LUA_RESERVED = new Set([
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "goto", "if", "in", "local", "nil", "not", "or",
    "repeat", "return", "then", "true", "until", "while",
]);
// All hardcoded local/parameter identifiers used inside generated VM / helper / handler templates
const INTERNAL_RESERVED = new Set([
    "A", "B", "C", "_",
    "a", "b", "c", "d", "e", "f", "g", "i", "j", "k", "l", "m", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "_i", "_j", "_k", "_n", "_o", "_p", "_q", "_r", "_s", "_t", "_u", "_v", "_w", "_x", "_y", "_b", "_d", "_m", "_h", "_g", "_l", "_e", "_f", "_c",
    "_wi", "_ci", "_ri", "_np", "_ntg", "_nl", "_cw", "_jm", "_km", "_cLen", "_isVararg", "_args", "_ac",
    "_ex", "_el", "_acc", "base", "step", "idx", "lim", "it", "_tp", "ok", "ok2", "ok3", "v2", "v3", "mt", "proto", "nU",
    "_ui", "_ud", "_oi", "eh", "_ws", "_we", "_op", "_tg", "_b0", "_b1", "_b2", "_b3", "_pl", "_ph", "_hb", "_sh",
    "_isR", "_rk", "_ro", "_ip1", "_fe", "_ge", "_re", "_gl", "_fnd", "_rg", "_pe", "_ls", "_sp", "_th",
    "_dynSalt", "_rs", "_ghostTrap", "_sc", "_0v", "_0i", "_0s", "_un", "_res", "_out", "_b32", "_bxor", "_band", "_opNames",
    "_hookOk", "_p1", "_p2", "_p3", "_p4", "_rp", "_rc", "_dn", "_rb", "_rn", "_rv", "_oc", "_ln", "_lz", "_lp", "_lc", "_ct", "_ll", "_lo", "_pOk", "_pR",
    "ra", "rb", "math", "table", "string", "bit32", "bit", "buffer", "game", "workspace", "script", "task", "Instance", "Enum", "debug", "os", "coroutine",
    "type", "typeof", "pairs", "ipairs", "next", "pcall", "xpcall", "select", "tostring", "tonumber", "assert", "error", "warn", "print",
    "setmetatable", "getmetatable", "rawget", "rawset", "getfenv", "setfenv", "getgenv", "getrenv", "loadstring", "load", "unpack", "_G", "_ENV", "shared", "cloneref"
]);
let _nameCounter = 0;
let _usedNames = new Set();
function resetNames() { _nameCounter = 0; _usedNames = new Set(); }
function randomName(len = 6) {
    const pool1 = "abcdefghijklmnopqrstuvwxyzDEFGHIJKLMNOPQRSTUVWXYZ";
    const pool2 = "_abcdefghijklmnopqrstuvwxyz";
    while (true) {
        const id = _nameCounter++;
        let cand;
        if (id < pool1.length) {
            cand = pool1[id];
        } else {
            const id2 = id - pool1.length;
            if (id2 < pool2.length * pool1.length) {
                const c1 = pool2[Math.floor(id2 / pool1.length)];
                const c2 = pool1[id2 % pool1.length];
                cand = c1 + c2;
            } else {
                cand = "_";
                for (let i = 0; i < Math.max(2, Math.min(len, 4)); i++) {
                    cand += pool1[Math.floor(rng() * pool1.length)];
                }
            }
        }
        if (!LUA_RESERVED.has(cand) && !INTERNAL_RESERVED.has(cand) && !_usedNames.has(cand)) {
            _usedNames.add(cand);
            return cand;
        }
    }
}
function createNameMap(level) {
    if (level === "debug") {
        return {
            run: "_run", env: "_env", genv: "_genv",
            R: "R", K: "K", code: "code", protos: "protos",
            ip: "ip", upvalues: "upvals", varargs: "VA", vaCount: "VAC",
            maxRegs: "maxRegs", nParams: "nParams",
            handlers: "H", openUVs: "openUVs", RK: "RK", top: "_top",
            retFlag: "_rf", retVals: "_rv",
            tPack: "_tpack", tUnpack: "_tunpack",
            ic: "_ic",
            bPcall: "_pcall", bXpcall: "_xpcall", bSelect: "_select", bType: "_type",
            bTconcat: "_tconcat", bTcreate: "_tcreate", bMfloor: "_mfloor", bIpairs: "_ipairs",
            bTostring: "_tostring", bRawget: "_rawget", bSetmeta: "_setmeta",
            bBxor: "_bxor", bBand: "_band", bLsh: "_lsh", bRsh: "_rsh",
            bSbyte: "_sbyte", bSchar: "_schar",
            bBcr: "_bcr", bBlen: "_blen", bBr8: "_br8", bBw8: "_bw8", bBcp: "_bcp", bBfs: "_bfs",
            bGetmeta: "_getmeta", bNext: "_next",
            fnv: "_fnv", pk: "_pk", dec: "_dec", adv: "_adv", wLut: "_wLut",
            shCache: "_shC", oMap: "_oMap", rb: "_rb", wb: "_wb", cp: "_cp",
            shVar: "_sh", bBufVar: "_bBuf", hasScrVar: "_hasScr", deadOpVar: "_deadOp",
            s1: "_s1", s2: "_s2", s3: "_s3",
        };
    }
    return {
        run: randomName(5), env: randomName(4), genv: randomName(4),
        R: randomName(3), K: randomName(3), code: randomName(4),
        protos: randomName(4), ip: randomName(3), upvalues: randomName(5),
        varargs: randomName(4), vaCount: randomName(4),
        maxRegs: randomName(3), nParams: randomName(3),
        handlers: randomName(4), openUVs: randomName(4), RK: randomName(3), top: randomName(3),
        retFlag: randomName(3), retVals: randomName(3),
        tPack: randomName(3), tUnpack: randomName(3),
        ic: randomName(3),
        bPcall: randomName(3), bXpcall: randomName(3), bSelect: randomName(3), bType: randomName(3),
        bTconcat: randomName(3), bTcreate: randomName(3), bMfloor: randomName(3), bIpairs: randomName(3),
        bTostring: randomName(3), bRawget: randomName(3), bSetmeta: randomName(3),
        bBxor: randomName(3), bBand: randomName(3), bLsh: randomName(3), bRsh: randomName(3),
        bSbyte: randomName(3), bSchar: randomName(3),
        bBcr: randomName(3), bBlen: randomName(3), bBr8: randomName(3), bBw8: randomName(3), bBcp: randomName(3), bBfs: randomName(3),
        bGetmeta: randomName(3), bNext: randomName(3),
        fnv: randomName(4), pk: randomName(3), dec: randomName(4), adv: randomName(3), wLut: randomName(3),
        shCache: randomName(4), oMap: randomName(3), rb: randomName(3), wb: randomName(3), cp: randomName(3),
        shVar: randomName(3), bBufVar: randomName(3), hasScrVar: randomName(3), deadOpVar: randomName(3),
        s1: randomName(2), s2: randomName(2), s3: randomName(2),
    };
}
function toUTF8Bytes(s) {
    const bytes = [];
    for (let i = 0; i < s.length; i++) {
        let c = s.charCodeAt(i);
        if (c < 0x80)
            bytes.push(c);
        else if (c < 0x800)
            bytes.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f));
        else if (c >= 0xd800 && c <= 0xdbff && i + 1 < s.length) {
            const lo = s.charCodeAt(++i);
            c = ((c - 0xd800) << 10) + (lo - 0xdc00) + 0x10000;
            bytes.push(0xf0 | (c >> 18), 0x80 | ((c >> 12) & 0x3f), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f));
        }
        else
            bytes.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f));
    }
    return bytes;
}
function luaStringLiteral(s) {
    const bytes = toUTF8Bytes(s);
    let out = '"';
    for (const b of bytes) {
        if (b === 34)
            out += '\\"';
        else if (b === 92)
            out += "\\\\";
        else if (b === 10)
            out += "\\n";
        else if (b === 13)
            out += "\\r";
        else if (b === 0)
            out += "\\000";
        else if (b < 32 || b > 126)
            out += `\\${b.toString().padStart(3, '0')}`;
        else
            out += String.fromCharCode(b);
    }
    return out + '"';
}
function luaEsc(s) {
    const encChar = (code) => {
        const m = Math.floor(rng() * 3);
        if (m === 0)
            return '\\' + code;
        if (m === 1)
            return '\\' + code.toString().padStart(3, '0');
        return '\\' + code;
    };
    if (s.length >= 4 && rng() > 0.5) {
        const mid = 1 + Math.floor(rng() * (s.length - 2));
        const left = Array.from(s.slice(0, mid)).map(c => encChar(c.charCodeAt(0))).join('');
        const right = Array.from(s.slice(mid)).map(c => encChar(c.charCodeAt(0))).join('');
        return `("${left}".."${right}")`;
    }
    return '"' + Array.from(s).map(c => encChar(c.charCodeAt(0))).join('') + '"';
}
function luaStr(s) {
    let out = '"';
    for (let i = 0; i < s.length; i++) {
        const c = s.charCodeAt(i);
        if (c === 34)
            out += '\\"';
        else if (c === 92)
            out += '\\\\';
        else if (c === 10)
            out += '\\n';
        else if (c === 13)
            out += '\\r';
        else if (c === 0)
            out += '\\000';
        else if (c < 32 || c > 126)
            out += `\\${c.toString().padStart(3, '0')}`;
        else
            out += s[i];
    }
    return out + '"';
}
function featureEnabled(options, flag, levelDefault) {
    if (options.disableFeatures?.includes(flag))
        return false;
    if (options.forceFeatures?.includes(flag))
        return true;
    return levelDefault;
}
function shuffleOpcodes(doShuffle) {
    const encode = [];
    const decode = [];
    const encodeAlt = [];
    for (let i = 0; i < REG_OPCODE_COUNT; i++) {
        encode[i] = i;
        decode[i] = i;
        encodeAlt[i] = i + REG_OPCODE_COUNT;
    }
    if (!doShuffle)
        return { encode, decode, encodeAlt };
    for (let i = REG_OPCODE_COUNT - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [encode[i], encode[j]] = [encode[j], encode[i]];
    }
    for (let i = REG_OPCODE_COUNT - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [encodeAlt[i], encodeAlt[j]] = [encodeAlt[j], encodeAlt[i]];
    }
    for (let i = 0; i < REG_OPCODE_COUNT; i++)
        decode[encode[i]] = i;
    return { encode, decode, encodeAlt };
}
function generateArgPerms(doRemap) {
    const ALL_PERMS = [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]];
    const perms = [];
    for (let op = 0; op < REG_OPCODE_COUNT; op++) {
        if (!doRemap || op === 0 /* RegOp.NOP */ || op === 44 /* RegOp.EXTRAARG */ || (op >= 45 && op <= 56)) {
            perms[op] = [1, 2, 3];
        }
        else {
            perms[op] = ALL_PERMS[Math.floor(rng() * 6)];
        }
    }
    return perms;
}
function mapRegBytecode(code, encode, argPerm, encodeAlt) {
    const out = [...code];
    for (let i = 0; i < out.length; i += 4) {
        const realOp = out[i];
        if (realOp >= 0 && realOp < encode.length) {
            const A = out[i + 1], B = out[i + 2], C = out[i + 3];
            out[i] = (encodeAlt && rng() > 0.5) ? encodeAlt[realOp] : encode[realOp];
            const p = argPerm[realOp];
            out[i + p[0]] = A;
            out[i + p[1]] = B;
            out[i + p[2]] = C;
        }
    }
    return out;
}
function mapRegChunk(chunk, encode, argPerm, encodeAlt) {
    chunk.code = mapRegBytecode(chunk.code, encode, argPerm, encodeAlt);
    if (chunk.protos)
        for (const p of chunk.protos)
            mapRegChunk(p, encode, argPerm, encodeAlt);
}
const SPIRAL_PRIMES = [
    3, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79,
    83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163,
    167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241,
];
function generateSBox() {
    const sbox = Array.from({ length: 256 }, (_, i) => i);
    for (let i = 255; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [sbox[i], sbox[j]] = [sbox[j], sbox[i]];
    }
    const inverse = new Array(256);
    for (let i = 0; i < 256; i++)
        inverse[sbox[i]] = i;
    return { sbox, inverse };
}
function encodeStringBytes(raw, ctx, constIdx) {
    const b = [...raw];
    const salt = constIdx & 0xFF;
    for (let i = 0; i < b.length; i++)
        b[i] = ctx.sbox[b[i] ^ ((salt + i) & 0xFF)];
    for (let i = 0; i < b.length; i++)
        b[i] = (b[i] + ((ctx.helixSeed + salt + i * ctx.helixMul) & 0xFF)) & 0xFF;
    for (let i = b.length - 1; i > 0; i--)
        b[i] ^= ((b[i - 1] * ctx.cascadeMul + ctx.cascadeKey + salt) & 0xFF);
    for (let i = 0; i < b.length; i++) {
        const h = i >> 1;
        const k = (i & 1) === 0
            ? ((ctx.checkKeyA + salt + h * ctx.checkStepA) & 0xFF)
            : ((ctx.checkKeyB + salt + h * ctx.checkStepB) & 0xFF);
        b[i] ^= k;
    }
    for (let i = 0; i < b.length; i++)
        b[i] ^= ((i * ctx.spiralPrime + ctx.spiralOffset + salt) % 251);
    return b;
}
function serializeConstant(v, ctx, idx) {
    if (v === null || v === undefined)
        return "nil";
    if (typeof v === "boolean")
        return v ? "true" : "false";
    if (typeof v === "number") {
        if (Object.is(v, -0))
            return "-0";
        if (!Number.isFinite(v)) {
            if (v === Infinity)
                return "(1/0)";
            if (v === -Infinity)
                return "(-1/0)";
            return "(0/0)";
        }
        return String(v);
    }
    if (typeof v === "string") {
        if (ctx.encodeStrings) {
            const bytes = toUTF8Bytes(v);
            const encoded = encodeStringBytes(bytes, ctx, idx);
            return `{${encoded.join(",")}}`;
        }
        return luaStringLiteral(v);
    }
    return "nil";
}
function serializeConstants(K, ctx, allowIIFE = false) {
    if (!K || K.length === 0)
        return "{}";
    if (allowIIFE && K.length > 40) {
        const kv = ctx.level !== "debug" ? randomName(2) : "_kt";
        const parts = [`(function() local ${kv}={}`];
        for (let i = 0; i < K.length; i++) {
            parts.push(`${kv}[${i + 1}]=${serializeConstant(K[i], ctx, i)}`);
        }
        parts.push(`return ${kv} end)()`);
        return parts.join(";");
    }
    return `{${K.map((v, i) => serializeConstant(v, ctx, i)).join(",")}}`;
}
function fnv1a32(str) {
    let h = 0x811c9dc5 >>> 0;
    const bytes = toUTF8Bytes(str);
    for (let i = 0; i < bytes.length; i++) {
        h ^= bytes[i];
        h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h >>> 0;
}
function luaByteLiteral(bytes) {
    let out = '"';
    for (let i = 0; i < bytes.length; i++) {
        const b = bytes[i] & 0xFF;
        if (b === 34)
            out += '\\"';
        else if (b === 92)
            out += '\\\\';
        else if (b === 10)
            out += '\\n';
        else if (b === 13)
            out += '\\r';
        else if (b < 32 || b > 126)
            out += '\\' + b.toString().padStart(3, '0');
        else
            out += String.fromCharCode(b);
    }
    return out + '"';
}
function valWidthCode(v) {
    if (v === 0)
        return 0;
    if (v >= 0 && v <= 255)
        return 1;
    if (v >= -32768 && v <= 32767)
        return 2;
    return 3;
}
const WIDTH_BYTES = [0, 1, 2, 4];
function writeIntBytes(out, val, wCode) {
    if (wCode === 0)
        return;
    if (wCode === 1) {
        out.push(val & 0xFF);
    }
    else if (wCode === 2) {
        const u = val < 0 ? val + 65536 : val;
        out.push(u & 0xFF, (u >>> 8) & 0xFF);
    }
    else {
        const u = val >>> 0;
        out.push(u & 0xFF, (u >>> 8) & 0xFF, (u >>> 16) & 0xFF, (u >>> 24) & 0xFF);
    }
}
function packVariableBytecode(code4, ctx) {
    const nInstr = Math.floor(code4.length / 4);
    if (nInstr === 0)
        return [];
    const doShuf = ctx && ctx.doShuffle;
    const encode = ctx?.opcodeEncode;
    const encodeAlt = ctx?.opcodeAlt;
    const argPerm = ctx?.argPerm;
    const tagMask = (ctx && ctx.tagMask) ? (ctx.tagMask & 0xFF) : 0;

    const instrs = new Array(nInstr);
    const widths = new Array(nInstr);
    const salts = new Array(nInstr);
    for (let idx = 0; idx < nInstr; idx++) {
        const base = idx * 4;
        const realOp = code4[base] | 0;
        const rawA = code4[base + 1] | 0;
        const rawB = code4[base + 2] | 0;
        const rawC = code4[base + 3] | 0;
        const isJump = (realOp === 21 || realOp === 30 || realOp === 31);
        const targetIdx = isJump ? Math.max(0, Math.min(nInstr, idx + 1 + rawB)) : -1;
        const p = (argPerm && argPerm[realOp]) ? argPerm[realOp] : [1, 2, 3];
        const slots = [0, 0, 0];
        slots[p[0] - 1] = rawA;
        slots[p[1] - 1] = isJump ? (rawB * 4) : rawB;
        slots[p[2] - 1] = rawC;
        instrs[idx] = { realOp, rawA, rawB, rawC, isJump, targetIdx, p, slots };
        widths[idx] = [valWidthCode(slots[0]), valWidthCode(slots[1]), valWidthCode(slots[2])];
        salts[idx] = (ctx && ctx.level !== "debug") ? Math.floor(rng() * 4) : 0;
    }

    const byteOff = new Array(nInstr + 1);
    let changed = true;
    let pass = 0;
    while (changed && pass < 8) {
        changed = false;
        pass++;
        let off = 0;
        for (let idx = 0; idx < nInstr; idx++) {
            byteOff[idx] = off;
            const w = widths[idx];
            off += 2 + WIDTH_BYTES[w[0]] + WIDTH_BYTES[w[1]] + WIDTH_BYTES[w[2]];
        }
        byteOff[nInstr] = off;
        for (let idx = 0; idx < nInstr; idx++) {
            const ins = instrs[idx];
            if (!ins.isJump)
                continue;
            const delta = byteOff[ins.targetIdx] - byteOff[idx + 1];
            const needW = valWidthCode(delta);
            const slotB = ins.p[1] - 1;
            if (needW > widths[idx][slotB]) {
                widths[idx][slotB] = needW;
                changed = true;
            }
        }
    }
    let totalOff = 0;
    for (let idx = 0; idx < nInstr; idx++) {
        byteOff[idx] = totalOff;
        const w = widths[idx];
        totalOff += 2 + WIDTH_BYTES[w[0]] + WIDTH_BYTES[w[1]] + WIDTH_BYTES[w[2]];
    }
    byteOff[nInstr] = totalOff;

    const out = [];
    for (let idx = 0; idx < nInstr; idx++) {
        const ins = instrs[idx];
        const realOp = ins.realOp;
        let mappedOp = realOp;
        if (doShuf && encode && realOp >= 0 && realOp < encode.length) {
            mappedOp = (encodeAlt && encodeAlt[realOp] !== undefined && rng() > 0.5)
                ? encodeAlt[realOp]
                : encode[realOp];
        }
        const slots = [...ins.slots];
        if (ins.isJump) {
            slots[ins.p[1] - 1] = byteOff[ins.targetIdx] - byteOff[idx + 1];
        }
        const w = widths[idx];
        const rawTag = (w[0] & 3) | ((w[1] & 3) << 2) | ((w[2] & 3) << 4) | ((salts[idx] & 3) << 6);
        out.push(mappedOp & 0xFF);
        out.push((rawTag ^ tagMask) & 0xFF);
        writeIntBytes(out, slots[0], w[0]);
        writeIntBytes(out, slots[1], w[1]);
        writeIntBytes(out, slots[2], w[2]);
    }
    return out;
}
function serializeRegCode(code, ctx) {
    const packed = packVariableBytecode(code, ctx);
    if (ctx && (ctx.rotSeed > 0 || ctx.rotStep > 0 || ctx.rotStep2 > 0 || ctx.rotStep3 > 0)) {
        const enc = new Array(packed.length);
        for (let j = 0; j < packed.length; j++) {
            const pl = j & 0xFF;
            const ph = (j >>> 8) & 0xFF;
            const key = (ctx.rotSeed + pl * ctx.rotStep + pl * pl * ctx.rotStep2 + ph * ctx.rotStep3) & 0xFF;
            enc[j] = (packed[j] ^ key) & 0xFF;
        }
        return luaByteLiteral(enc);
    }
    return luaByteLiteral(packed);
}
function serializeRegProtos(protos, ctx) {
    if (!protos || protos.length === 0)
        return "{}";
    const pk = ctx.protoKeys;
    const usePositional = ctx.level !== "debug";
    const hasNested = protos.some(p => p.protos && p.protos.length > 0);
    if (!hasNested && protos.length <= 12) {
        const items = [];
        for (const p of protos) {
            const sK = serializeConstants(p.K, ctx);
            const sC = serializeRegCode(p.code, ctx);
            let sU = "nil";
            if (p.upvalues && p.upvalues.length > 0) {
                sU = `{${p.upvalues.map(uv => `{${uv[0]},${uv[1]}}`).join(",")}}`;
            }
            const nP = p.nParams ?? 0;
            const mR = p.maxRegs ?? 0;
            const isVA = p.isVararg ? "true" : "false";
            if (usePositional) {
                items.push(`{${sK},${sC},{},${sU},${nP},${mR},${isVA}}`);
            }
            else {
                items.push(`{${pk.pK}=${sK},${pk.pC}=${sC},${pk.pP}={},${pk.pU}=${sU},${pk.pN}=${nP},mR=${mR},vA=${isVA}}`);
            }
        }
        return `{${items.join(",")}}`;
    }
    const pv = ctx.level !== "debug" ? randomName(2) : "_pt";
    const stmts = [`(function() local ${pv}={}`];
    let nextSlot = 1;
    function emitProto(p) {
        const childSlots = [];
        if (p.protos && p.protos.length > 0) {
            for (const cp of p.protos) {
                childSlots.push(emitProto(cp));
            }
        }
        const slot = nextSlot++;
        const sK = serializeConstants(p.K, ctx);
        const sC = serializeRegCode(p.code, ctx);
        const sP = childSlots.length > 0
            ? `{${childSlots.map(s => `${pv}[${s}]`).join(",")}}`
            : "{}";
        let sU = "nil";
        if (p.upvalues && p.upvalues.length > 0) {
            sU = `{${p.upvalues.map(uv => `{${uv[0]},${uv[1]}}`).join(",")}}`;
        }
        const nP = p.nParams ?? 0;
        const mR = p.maxRegs ?? 0;
        const isVA = p.isVararg ? "true" : "false";
        if (usePositional) {
            stmts.push(`${pv}[${slot}]={${sK},${sC},${sP},${sU},${nP},${mR},${isVA}}`);
        }
        else {
            stmts.push(`${pv}[${slot}]={${pk.pK}=${sK},${pk.pC}=${sC},${pk.pP}=${sP},${pk.pU}=${sU},${pk.pN}=${nP},mR=${mR},vA=${isVA}}`);
        }
        return slot;
    }
    const rootSlots = [];
    for (const p of protos) {
        rootSlots.push(emitProto(p));
    }
    stmts.push(`return {${rootSlots.map(s => `${pv}[${s}]`).join(",")}} end)()`);
    return stmts.join(";");
}
const REG_OP_NAMES = [
    "NOP", "LOADK", "LOADNIL", "LOADBOOL", "MOVE", "GETGLOBAL", "SETGLOBAL",
    "GETTABLE", "SETTABLE", "NEWTABLE", "ADD", "SUB", "MUL", "DIV", "MOD",
    "POW", "IDIV", "UNM", "NOT", "LEN", "CONCAT", "JMP", "EQ", "LT", "LE",
    "TEST", "TESTSET", "CALL", "TAILCALL", "RETURN", "FORPREP", "FORLOOP",
    "TFORLOOP", "SETLIST", "CLOSURE", "VARARG", "SELF", "GETUPVAL", "SETUPVAL",
    "CLOSEUPVAL", "PCALL", "XPCALL", "ITERPREP", "LOADKX", "EXTRAARG",
    "F_TEST_JMP", "F_EQ_JMP", "F_LT_JMP", "F_LE_JMP", "F_TESTSET_JMP",
    "F_GGET", "F_LOADKK", "F_MOVE_MOVE", "F_SELF_CALL", "F_GGET_CALL",
    "F_LOADK_RET", "F_MOVE_RET",
];
const handlerRegistry = new Map();
function registerHandler(op, gen) {
    handlerRegistry.set(op, gen);
}
registerHandler(0 /* RegOp.NOP */, () => ``);
registerHandler(1 /* RegOp.LOADK */, (n) => `${n.R}[A+1]=${n.K}[B+1]`);
registerHandler(2 /* RegOp.LOADNIL */, (n) => `for _i=A,A+B do ${n.R}[_i+1]=nil end`);
registerHandler(3 /* RegOp.LOADBOOL */, (n) => `${n.R}[A+1]=(B~=0);if C~=0 then ${n.ip}=${n.adv}(${n.ip},${n.shVar}) end`);
registerHandler(4 /* RegOp.MOVE */, (n) => `${n.R}[A+1]=${n.R}[B+1]`);
registerHandler(43 /* RegOp.LOADKX */, (n) => `do local _,_ex,_,_,_el=${n.dec}(${n.shVar},nil,${n.ip}-1,false,nil);${n.R}[A+1]=${n.K}[_ex+1];if ${n.bBufVar} then for _wi=0,_el-1 do ${n.wb}(${n.bBufVar},${n.ip}-1+_wi,${n.deadOpVar}) end end;${n.ip}=${n.ip}+_el;${n.hasScrVar}=false end`);
registerHandler(44 /* RegOp.EXTRAARG */, () => ``);
registerHandler(5 /* RegOp.GETGLOBAL */, (n) => {
    return `do local _k=${n.K}[B+1];${n.R}[A+1]=${n.env}[_k] end`;
});
registerHandler(6 /* RegOp.SETGLOBAL */, (n) => `do ${n.env}[${n.K}[B+1]]=${n.R}[A+1];${n.ic}[1]=nil end`);
registerHandler(7 /* RegOp.GETTABLE */, (n) => `${n.R}[A+1]=${n.R}[B+1][${n.RK}(C)]`);
registerHandler(8 /* RegOp.SETTABLE */, (n) => `${n.R}[A+1][${n.RK}(B)]=${n.RK}(C)`);
registerHandler(9 /* RegOp.NEWTABLE */, (n) => `${n.R}[A+1]={}`);
registerHandler(33 /* RegOp.SETLIST */, (n) => `do local t=${n.R}[A+1];local _b=B;if _b==0 then _b=${n.top}-(A+1) end;local base=C-1;for _i=1,_b do t[base+_i]=${n.R}[A+1+_i] end end`);
registerHandler(36 /* RegOp.SELF */, (n) => `do local _o=${n.R}[B+1];${n.R}[A+2]=_o;${n.R}[A+1]=_o[${n.RK}(C)] end`);
registerHandler(10 /* RegOp.ADD */, (n) => `${n.R}[A+1]=${n.RK}(B)+${n.RK}(C)`);
registerHandler(11 /* RegOp.SUB */, (n) => `${n.R}[A+1]=${n.RK}(B)-${n.RK}(C)`);
registerHandler(12 /* RegOp.MUL */, (n) => `${n.R}[A+1]=${n.RK}(B)*${n.RK}(C)`);
registerHandler(13 /* RegOp.DIV */, (n) => `${n.R}[A+1]=${n.RK}(B)/${n.RK}(C)`);
registerHandler(14 /* RegOp.MOD */, (n) => `${n.R}[A+1]=${n.RK}(B)%${n.RK}(C)`);
registerHandler(15 /* RegOp.POW */, (n) => `${n.R}[A+1]=${n.RK}(B)^${n.RK}(C)`);
registerHandler(16 /* RegOp.IDIV */, (n) => `${n.R}[A+1]=${n.bMfloor}(${n.RK}(B)/${n.RK}(C))`);
registerHandler(17 /* RegOp.UNM */, (n) => `${n.R}[A+1]=-${n.R}[B+1]`);
registerHandler(18 /* RegOp.NOT */, (n) => `${n.R}[A+1]=not ${n.R}[B+1]`);
registerHandler(19 /* RegOp.LEN */, (n) => `${n.R}[A+1]=#${n.R}[B+1]`);
registerHandler(20 /* RegOp.CONCAT */, (n) => `do local _acc=${n.R}[C+1];for _i=C-1,B,-1 do _acc=${n.R}[_i+1].._acc end;${n.R}[A+1]=_acc end`);
registerHandler(21 /* RegOp.JMP */, (n) => `${n.ip}=${n.ip}+B`);
registerHandler(22 /* RegOp.EQ */, (n) => `if (${n.RK}(B)==${n.RK}(C))~=(A~=0) then ${n.ip}=${n.adv}(${n.ip},${n.shVar}) end`);
registerHandler(23 /* RegOp.LT */, (n) => `if (${n.RK}(B)<${n.RK}(C))~=(A~=0) then ${n.ip}=${n.adv}(${n.ip},${n.shVar}) end`);
registerHandler(24 /* RegOp.LE */, (n) => `if (${n.RK}(B)<=${n.RK}(C))~=(A~=0) then ${n.ip}=${n.adv}(${n.ip},${n.shVar}) end`);
registerHandler(25 /* RegOp.TEST */, (n) => `if (not ${n.R}[A+1])==(C~=0) then ${n.ip}=${n.adv}(${n.ip},${n.shVar}) end`);
registerHandler(26 /* RegOp.TESTSET */, (n) => `if (not ${n.R}[B+1])==(C~=0) then ${n.ip}=${n.adv}(${n.ip},${n.shVar}) else ${n.R}[A+1]=${n.R}[B+1] end`);
registerHandler(27 /* RegOp.CALL */, (n) => {
    const storeR = () => `if C==0 then for _i=1,r.n do ${n.R}[A+_i]=r[_i] end;${n.top}=A+r.n ` +
        `else for _i=1,C-1 do ${n.R}[A+_i]=r[_i] end end`;
    return `do local f=${n.R}[A+1];local r;` +
        `if B==1 then r=${n.tPack}(f()) ` +
        `elseif B==2 then r=${n.tPack}(f(${n.R}[A+2])) ` +
        `elseif B==3 then r=${n.tPack}(f(${n.R}[A+2],${n.R}[A+3])) ` +
        `elseif B==0 then r=${n.tPack}(f(${n.tUnpack}(${n.R},A+2,${n.top}))) ` +
        `else r=${n.tPack}(f(${n.tUnpack}(${n.R},A+2,A+B))) end;` +
        `${storeR()} end`;
});
registerHandler(28 /* RegOp.TAILCALL */, (n) => `do local f=${n.R}[A+1];` +
    `if B==1 then return f() ` +
    `elseif B==2 then return f(${n.R}[A+2]) ` +
    `elseif B==3 then return f(${n.R}[A+2],${n.R}[A+3]) ` +
    `elseif B==0 then return f(${n.tUnpack}(${n.R},A+2,${n.top})) ` +
    `else return f(${n.tUnpack}(${n.R},A+2,A+B)) end end`);
registerHandler(29 /* RegOp.RETURN */, (n) => `do if B==0 then return ${n.tUnpack}(${n.R},A+1,${n.top}) ` +
    `elseif B==1 then return ` +
    `else return ${n.tUnpack}(${n.R},A+1,A+B-1) end end`);
registerHandler(30 /* RegOp.FORPREP */, (n) => `${n.R}[A+1]=${n.R}[A+1]-${n.R}[A+3];${n.ip}=${n.ip}+B`);
registerHandler(31 /* RegOp.FORLOOP */, (n) => `do local step=${n.R}[A+3];local idx=${n.R}[A+1]+step;${n.R}[A+1]=idx;` +
    `local lim=${n.R}[A+2];if step>0 then if idx<=lim then ${n.ip}=${n.ip}+B;${n.R}[A+4]=idx end ` +
    `else if idx>=lim then ${n.ip}=${n.ip}+B;${n.R}[A+4]=idx end end end`);
registerHandler(32 /* RegOp.TFORLOOP */, (n) => `do local f=${n.R}[A+1];local s=${n.R}[A+2];local v=${n.R}[A+3];` +
    `local r={f(s,v)};for _i=1,C do ${n.R}[A+3+_i]=r[_i] end;` +
    `if r[1]~=nil then ${n.R}[A+3]=r[1];${n.ip}=${n.adv}(${n.ip},${n.shVar}) end end`);
registerHandler(42 /* RegOp.ITERPREP */, (n) => `do local it=${n.R}[A+1];local _tp=${n.bType}(it);if _tp=="table" or _tp=="userdata" then ` +
    `local ok,mt=${n.bPcall}(${n.bGetmeta},it);if ok and ${n.bType}(mt)=="table" and mt.__iter then ` +
    `${n.R}[A+1],${n.R}[A+2],${n.R}[A+3]=mt.__iter(it) elseif _tp=="table" then ${n.R}[A+1]=${n.bNext};${n.R}[A+2]=it;${n.R}[A+3]=nil end end end`);
registerHandler(37 /* RegOp.GETUPVAL */, (n) => `do local _b=${n.upvalues}[B+1];if _b[2] then ${n.R}[A+1]=_b[1][_b[2]] else ${n.R}[A+1]=_b[1] end end`);
registerHandler(38 /* RegOp.SETUPVAL */, (n) => `do local _b=${n.upvalues}[B+1];if _b[2] then _b[1][_b[2]]=${n.R}[A+1] else _b[1]=${n.R}[A+1] end end`);
registerHandler(39 /* RegOp.CLOSEUPVAL */, (n) => `do local _n=0;for _i=1,#${n.openUVs} do local _b=${n.openUVs}[_i];if _b[2]>=A+1 then ` +
    `_b[1]=_b[1][_b[2]];_b[2]=nil else _n=_n+1;${n.openUVs}[_n]=_b end end;` +
    `for _i=_n+1,#${n.openUVs} do ${n.openUVs}[_i]=nil end end`);
registerHandler(35 /* RegOp.VARARG */, (n) => `do if B==0 then for _i=1,${n.vaCount} do ${n.R}[A+_i]=${n.varargs}[_i] end;${n.top}=A+${n.vaCount} ` +
    `else for _i=1,B-1 do ${n.R}[A+_i]=${n.varargs}[_i] end end end`);
registerHandler(34 /* RegOp.CLOSURE */, (n, ctx) => {
    const pos = ctx.level !== "debug";
    const { pK, pC, pP, pU, pN } = ctx.protoKeys;
    const gK = pos ? "[1]" : `.${pK}`;
    const gC = pos ? "[2]" : `.${pC}`;
    const gP = pos ? "[3]" : `.${pP}`;
    const gU = pos ? "[4]" : `.${pU}`;
    const gN = pos ? "[5]" : `.${pN}`;
    const gMR = pos ? "[6]" : ".mR";
    const gVA = pos ? "[7]" : ".vA";
    return `do local proto=${n.protos}[B+1];if proto then ` +
        `local nU={};if proto${gU} then for _ui,_ud in ${n.bIpairs}(proto${gU}) do ` +
        `if _ud[1]==1 then local _b;for _oi=1,#${n.openUVs} do if ${n.openUVs}[_oi][2]==_ud[2]+1 then _b=${n.openUVs}[_oi];break end end;` +
        `if not _b then _b={${n.R},_ud[2]+1};${n.openUVs}[#${n.openUVs}+1]=_b end;nU[_ui]=_b ` +
        `else nU[_ui]=${n.upvalues}[_ud[2]+1] end end end;` +
        `${n.R}[A+1]=function(...) return ${n.run}(proto${gK},proto${gC},proto${gP},proto${gU} and nU or {},proto${gN},proto${gMR},proto${gVA},${n.env},...) end ` +
        `else ${n.R}[A+1]=nil end end`;
});
registerHandler(40 /* RegOp.PCALL */, (n) => `do local f=${n.R}[A+1];local _we=B==0 and ${n.top} or A+B;local r;` +
    `if B==1 then r=${n.tPack}(${n.bPcall}(f)) ` +
    `elseif B==2 then r=${n.tPack}(${n.bPcall}(f,${n.R}[A+2])) ` +
    `elseif B==3 then r=${n.tPack}(${n.bPcall}(f,${n.R}[A+2],${n.R}[A+3])) ` +
    `else r=${n.tPack}(${n.bPcall}(f,${n.tUnpack}(${n.R},A+2,_we))) end;` +
    `if C==0 then for _i=1,r.n do ${n.R}[A+_i]=r[_i] end;${n.top}=A+r.n ` +
    `else for _i=1,C-1 do ${n.R}[A+_i]=r[_i] end end;` +
    `if B==0 or B>1 then local _ws=C==0 and (A+r.n+1) or (A+C);for _wi=_ws,_we do ${n.R}[_wi]=nil end end end`);
registerHandler(41 /* RegOp.XPCALL */, (n) => `do local f=${n.R}[A+1];local eh=${n.R}[A+2];local _we=B==0 and ${n.top} or A+B;local r;` +
    `if B==1 or B==2 then r=${n.tPack}(${n.bXpcall}(f,eh)) ` +
    `elseif B==3 then r=${n.tPack}(${n.bXpcall}(f,eh,${n.R}[A+3])) ` +
    `else r=${n.tPack}(${n.bXpcall}(f,eh,${n.tUnpack}(${n.R},A+3,_we))) end;` +
    `if C==0 then for _i=1,r.n do ${n.R}[A+_i]=r[_i] end;${n.top}=A+r.n ` +
    `else for _i=1,C-1 do ${n.R}[A+_i]=r[_i] end end;` +
    `if B==0 or B>2 then local _ws=C==0 and (A+r.n+1) or (A+C);for _wi=_ws,_we do ${n.R}[_wi]=nil end end end`);
registerHandler(45 /* RegOp.FUSED_TEST_JMP */, (n) => {
    const v = Math.floor(rng() * 3);
    if (v === 0)
        return `do local _j=${n.code}[${n.ip}+2];if (not ${n.R}[A+1])==(C~=0) then ${n.ip}=${n.ip}+4 else ${n.ip}=${n.ip}+4+_j*4 end end`;
    if (v === 1)
        return `do local _j=${n.code}[${n.ip}+2];if (not ${n.R}[A+1])~=(C~=0) then ${n.ip}=${n.ip}+4+_j*4 else ${n.ip}=${n.ip}+4 end end`;
    return `do local _o=${n.code}[${n.ip}+2]*4;${n.ip}=${n.ip}+4;if (not ${n.R}[A+1])~=(C~=0) then ${n.ip}=${n.ip}+_o end end`;
});
registerHandler(46 /* RegOp.FUSED_EQ_JMP */, (n) => {
    const v = Math.floor(rng() * 3);
    if (v === 0)
        return `do local _j=${n.code}[${n.ip}+2];if (${n.RK}(B)==${n.RK}(C))~=(A~=0) then ${n.ip}=${n.ip}+4 else ${n.ip}=${n.ip}+4+_j*4 end end`;
    if (v === 1)
        return `do local _j=${n.code}[${n.ip}+2];if (${n.RK}(B)==${n.RK}(C))==(A~=0) then ${n.ip}=${n.ip}+4+_j*4 else ${n.ip}=${n.ip}+4 end end`;
    return `do local _lv,_rv=${n.RK}(B),${n.RK}(C);local _j=${n.code}[${n.ip}+2];if (_lv==_rv)~=(A~=0) then ${n.ip}=${n.ip}+4 else ${n.ip}=${n.ip}+4+_j*4 end end`;
});
registerHandler(47 /* RegOp.FUSED_LT_JMP */, (n) => {
    const v = Math.floor(rng() * 3);
    if (v === 0)
        return `do local _j=${n.code}[${n.ip}+2];if (${n.RK}(B)<${n.RK}(C))~=(A~=0) then ${n.ip}=${n.ip}+4 else ${n.ip}=${n.ip}+4+_j*4 end end`;
    if (v === 1)
        return `do local _j=${n.code}[${n.ip}+2];if (${n.RK}(B)<${n.RK}(C))==(A~=0) then ${n.ip}=${n.ip}+4+_j*4 else ${n.ip}=${n.ip}+4 end end`;
    return `do local _lv,_rv=${n.RK}(B),${n.RK}(C);local _o=${n.code}[${n.ip}+2]*4;${n.ip}=${n.ip}+4;if (_lv<_rv)==(A~=0) then ${n.ip}=${n.ip}+_o end end`;
});
registerHandler(48 /* RegOp.FUSED_LE_JMP */, (n) => {
    const v = Math.floor(rng() * 3);
    if (v === 0)
        return `do local _j=${n.code}[${n.ip}+2];if (${n.RK}(B)<=${n.RK}(C))~=(A~=0) then ${n.ip}=${n.ip}+4 else ${n.ip}=${n.ip}+4+_j*4 end end`;
    if (v === 1)
        return `do local _j=${n.code}[${n.ip}+2];if (${n.RK}(B)<=${n.RK}(C))==(A~=0) then ${n.ip}=${n.ip}+4+_j*4 else ${n.ip}=${n.ip}+4 end end`;
    return `do local _lv,_rv=${n.RK}(B),${n.RK}(C);local _o=${n.code}[${n.ip}+2]*4;${n.ip}=${n.ip}+4;if (_lv<=_rv)==(A~=0) then ${n.ip}=${n.ip}+_o end end`;
});
registerHandler(49 /* RegOp.FUSED_TESTSET_JMP */, (n) => {
    const v = Math.floor(rng() * 2);
    if (v === 0)
        return `do local _j=${n.code}[${n.ip}+2];if (not ${n.R}[B+1])==(C~=0) then ${n.ip}=${n.ip}+4 else ${n.R}[A+1]=${n.R}[B+1];${n.ip}=${n.ip}+4+_j*4 end end`;
    return `do local _bv=${n.R}[B+1];local _j=${n.code}[${n.ip}+2];if (not _bv)==(C~=0) then ${n.ip}=${n.ip}+4 else ${n.R}[A+1]=_bv;${n.ip}=${n.ip}+4+_j*4 end end`;
});
registerHandler(50 /* RegOp.FUSED_GGET */, (n) => {
    const v = Math.floor(rng() * 3);
    const dbg = process.env.DEBUG_VM === '1';
    const nilG = dbg ? `if _g==nil then warn("[FUSED_GGET] nil global: "..tostring(${n.K}[B+1])) end;` : '';
    if (v === 0)
        return `do local _A2=${n.code}[${n.ip}+1];local _C2=${n.code}[${n.ip}+3];local _g=${n.env}[${n.K}[B+1]];${nilG}${n.R}[A+1]=_g;if _g~=nil then ${n.R}[_A2+1]=_g[${n.RK}(_C2)] else ${n.R}[_A2+1]=nil end;${n.ip}=${n.ip}+4 end`;
    if (v === 1)
        return `do local _A2=${n.code}[${n.ip}+1];local _C2=${n.code}[${n.ip}+3];local _g=${n.env}[${n.K}[B+1]];${nilG}${n.R}[A+1]=_g;if _g~=nil then ${n.R}[_A2+1]=_g[${n.RK}(_C2)] else ${n.R}[_A2+1]=nil end;${n.ip}=${n.ip}+4 end`;
    return `do local _g=${n.env}[${n.K}[B+1]];${nilG}${n.R}[A+1]=_g;local _k=${n.RK}(${n.code}[${n.ip}+3]);if _g~=nil then ${n.R}[${n.code}[${n.ip}+1]+1]=_g[_k] else ${n.R}[${n.code}[${n.ip}+1]+1]=nil end;${n.ip}=${n.ip}+4 end`;
});
registerHandler(51 /* RegOp.FUSED_LOADKK */, (n) => {
    const v = Math.floor(rng() * 2);
    if (v === 0)
        return `do local _A2=${n.code}[${n.ip}+1];local _B2=${n.code}[${n.ip}+2];${n.R}[A+1]=${n.K}[B+1];${n.R}[_A2+1]=${n.K}[_B2+1];${n.ip}=${n.ip}+4 end`;
    return `do ${n.R}[A+1]=${n.K}[B+1];${n.R}[${n.code}[${n.ip}+1]+1]=${n.K}[${n.code}[${n.ip}+2]+1];${n.ip}=${n.ip}+4 end`;
});
registerHandler(52 /* RegOp.FUSED_MOVE_MOVE */, (n) => {
    const v = Math.floor(rng() * 2);
    if (v === 0)
        return `do local _A2=${n.code}[${n.ip}+1];local _B2=${n.code}[${n.ip}+2];${n.R}[A+1]=${n.R}[B+1];${n.R}[_A2+1]=${n.R}[_B2+1];${n.ip}=${n.ip}+4 end`;
    return `do ${n.R}[A+1]=${n.R}[B+1];${n.R}[${n.code}[${n.ip}+1]+1]=${n.R}[${n.code}[${n.ip}+2]+1];${n.ip}=${n.ip}+4 end`;
});
registerHandler(53 /* RegOp.FUSED_SELF_CALL */, (n) => {
    const v = Math.floor(rng() * 2);
    const callBody = `local _B2=${n.code}[${n.ip}+2];local _C2=${n.code}[${n.ip}+3];${n.ip}=${n.ip}+4;` +
        `local r;` +
        `if _B2==2 then r=${n.tPack}(f(${n.R}[A+2])) ` +
        `elseif _B2==3 then r=${n.tPack}(f(${n.R}[A+2],${n.R}[A+3])) ` +
        `elseif _B2==0 then r=${n.tPack}(f(${n.tUnpack}(${n.R},A+2,${n.top}))) ` +
        `else r=${n.tPack}(f(${n.tUnpack}(${n.R},A+2,A+_B2))) end;` +
        `if _C2==0 then for _i=1,r.n do ${n.R}[A+_i]=r[_i] end;${n.top}=A+r.n ` +
        `else for _i=1,_C2-1 do ${n.R}[A+_i]=r[_i] end end`;
    if (v === 0)
        return `do local _s=${n.R}[B+1];${n.R}[A+2]=_s;local f;if _s~=nil then f=_s[${n.RK}(C)] end;${n.R}[A+1]=f;${callBody} end`;
    return `do local _s=${n.R}[B+1];${n.R}[A+2]=_s;local f;if _s~=nil then f=_s[${n.RK}(C)] end;${n.R}[A+1]=f;${callBody} end`;
});
registerHandler(54 /* RegOp.FUSED_GGET_CALL */, (n) => {
    const v = Math.floor(rng() * 2);
    const readSlot2 = `local _A2=${n.code}[${n.ip}+1];local _C2=${n.code}[${n.ip}+3]`;
    const readSlot3 = `local _A3=${n.code}[${n.ip}+5];local _B3=${n.code}[${n.ip}+6];local _C3=${n.code}[${n.ip}+7]`;
    const gget = `local _g=${n.env}[${n.K}[B+1]];${n.R}[A+1]=_g;local f;if _g~=nil then f=_g[${n.RK}(_C2)] end;${n.R}[_A2+1]=f`;
    const callBody = `local r;` +
        `if _B3==1 then r=${n.tPack}(f()) ` +
        `elseif _B3==2 then r=${n.tPack}(f(${n.R}[_A3+2])) ` +
        `elseif _B3==3 then r=${n.tPack}(f(${n.R}[_A3+2],${n.R}[_A3+3])) ` +
        `elseif _B3==0 then r=${n.tPack}(f(${n.tUnpack}(${n.R},_A3+2,${n.top}))) ` +
        `else r=${n.tPack}(f(${n.tUnpack}(${n.R},_A3+2,_A3+_B3))) end;` +
        `if _C3==0 then for _i=1,r.n do ${n.R}[_A3+_i]=r[_i] end;${n.top}=_A3+r.n ` +
        `else for _i=1,_C3-1 do ${n.R}[_A3+_i]=r[_i] end end`;
    return `do ${readSlot2};${readSlot3};${gget};${n.ip}=${n.ip}+8;${callBody} end`;
});
registerHandler(55 /* RegOp.FUSED_LOADK_RET */, (n) => {
    const v = Math.floor(rng() * 2);
    if (v === 0)
        return `do ${n.R}[A+1]=${n.K}[B+1];${n.ip}=${n.ip}+4;return ${n.R}[A+1] end`;
    return `do local _v=${n.K}[B+1];${n.ip}=${n.ip}+4;return _v end`;
});
registerHandler(56 /* RegOp.FUSED_MOVE_RET */, (n) => {
    const v = Math.floor(rng() * 3);
    if (v === 0)
        return `do local _A2=${n.code}[${n.ip}+1];local _B2=${n.code}[${n.ip}+2];${n.R}[A+1]=${n.R}[B+1];${n.ip}=${n.ip}+4;if _B2==0 then return ${n.tUnpack}(${n.R},_A2+1,${n.top}) elseif _B2==1 then return else return ${n.tUnpack}(${n.R},_A2+1,_A2+_B2-1) end end`;
    if (v === 1)
        return `do ${n.R}[A+1]=${n.R}[B+1];local _A2=${n.code}[${n.ip}+1];local _B2=${n.code}[${n.ip}+2];${n.ip}=${n.ip}+4;if _B2==2 then return ${n.R}[_A2+1] elseif _B2==1 then return elseif _B2==0 then return ${n.tUnpack}(${n.R},_A2+1,${n.top}) else return ${n.tUnpack}(${n.R},_A2+1,_A2+_B2-1) end end`;
    return `do ${n.R}[A+1]=${n.R}[B+1];local _B2=${n.code}[${n.ip}+2];if _B2==0 then ${n.ip}=${n.ip}+4;return ${n.tUnpack}(${n.R},${n.code}[${n.ip}-3]+1,${n.top}) elseif _B2==1 then ${n.ip}=${n.ip}+4;return else ${n.ip}=${n.ip}+4;return ${n.tUnpack}(${n.R},${n.code}[${n.ip}-3]+1,${n.code}[${n.ip}-3]+_B2-1) end end`;
});
function computeJumpTargets(code) {
    const targets = new Set();
    for (let i = 0; i < code.length; i += 4) {
        const op = code[i];
        if (op === 21 /* RegOp.JMP */ || op === 30 /* RegOp.FORPREP */ || op === 31 /* RegOp.FORLOOP */) {
            const B = code[i + 2];
            const target = i + 4 + B * 4;
            if (target >= 0 && target < code.length)
                targets.add(target);
        }
        if (op === 3 /* RegOp.LOADBOOL */ && code[i + 3] !== 0) {
            targets.add(i + 8);
        }
    }
    return targets;
}
function flattenControlFlow(chunk) {
    let totalBlocks = 0;
    function flattenCode(code) {
        if (code.length <= 16)
            return code;
        const targets = new Set();
        targets.add(0);
        for (let i = 0; i < code.length; i += 4) {
            const op = code[i];
            if (op === 21 /* RegOp.JMP */ || op === 30 /* RegOp.FORPREP */ || op === 31 /* RegOp.FORLOOP */) {
                const B = code[i + 2];
                const t = i + 4 + B * 4;
                if (t >= 0 && t <= code.length)
                    targets.add(t);
            }
            if (op === 3 /* RegOp.LOADBOOL */ && code[i + 3] !== 0)
                targets.add(i + 8);
            if (op === 22 /* RegOp.EQ */ || op === 23 /* RegOp.LT */ || op === 24 /* RegOp.LE */ ||
                op === 25 /* RegOp.TEST */ || op === 26 /* RegOp.TESTSET */ || op === 32 /* RegOp.TFORLOOP */) {
                targets.add(i + 8);
            }
            if (op === 45 /* RegOp.FUSED_TEST_JMP */ || op === 46 /* RegOp.FUSED_EQ_JMP */ ||
                op === 47 /* RegOp.FUSED_LT_JMP */ || op === 48 /* RegOp.FUSED_LE_JMP */ ||
                op === 49 /* RegOp.FUSED_TESTSET_JMP */) {
                const _j = code[i + 6];
                const t = i + 8 + _j * 4;
                if (t >= 0 && t <= code.length)
                    targets.add(t);
                targets.add(i + 8);
            }
        }
        for (let i = 0; i < code.length; i += 4) {
            const op = code[i];
            if (op === 22 /* RegOp.EQ */ || op === 23 /* RegOp.LT */ || op === 24 /* RegOp.LE */ ||
                op === 25 /* RegOp.TEST */ || op === 26 /* RegOp.TESTSET */ || op === 32 /* RegOp.TFORLOOP */) {
                targets.delete(i + 4);
            }
            if (op === 3 /* RegOp.LOADBOOL */ && code[i + 3] !== 0)
                targets.delete(i + 4);
            if (op === 43 /* RegOp.LOADKX */)
                targets.delete(i + 4);
            if (op === 33 /* RegOp.SETLIST */ && code[i + 3] === 0)
                targets.delete(i + 4);
            if (op === 45 /* RegOp.FUSED_TEST_JMP */ || op === 46 /* RegOp.FUSED_EQ_JMP */ ||
                op === 47 /* RegOp.FUSED_LT_JMP */ || op === 48 /* RegOp.FUSED_LE_JMP */ ||
                op === 49 /* RegOp.FUSED_TESTSET_JMP */ || op === 50 /* RegOp.FUSED_GGET */ ||
                op === 51 /* RegOp.FUSED_LOADKK */ || op === 52 /* RegOp.FUSED_MOVE_MOVE */ ||
                op === 53 /* RegOp.FUSED_SELF_CALL */ || op === 55 /* RegOp.FUSED_LOADK_RET */ ||
                op === 56 /* RegOp.FUSED_MOVE_RET */) {
                targets.delete(i + 4);
            }
            if (op === 54 /* RegOp.FUSED_GGET_CALL */) {
                targets.delete(i + 4);
                targets.delete(i + 8);
            }
        }
        for (const t of targets) {
            if (t < 0 || t >= code.length)
                targets.delete(t);
        }
        const unsafeSplit = new Set();
        for (let i = 0; i < code.length; i += 4) {
            const op = code[i];
            if (op === 22 /* RegOp.EQ */ || op === 23 /* RegOp.LT */ || op === 24 /* RegOp.LE */ ||
                op === 25 /* RegOp.TEST */ || op === 26 /* RegOp.TESTSET */ || op === 32 /* RegOp.TFORLOOP */) {
                unsafeSplit.add(i + 4);
            }
            if (op === 3 /* RegOp.LOADBOOL */ && code[i + 3] !== 0)
                unsafeSplit.add(i + 4);
            if (op === 43 /* RegOp.LOADKX */)
                unsafeSplit.add(i + 4);
            if (op === 33 /* RegOp.SETLIST */ && code[i + 3] === 0)
                unsafeSplit.add(i + 4);
            if (op === 45 /* RegOp.FUSED_TEST_JMP */ || op === 46 /* RegOp.FUSED_EQ_JMP */ ||
                op === 47 /* RegOp.FUSED_LT_JMP */ || op === 48 /* RegOp.FUSED_LE_JMP */ ||
                op === 49 /* RegOp.FUSED_TESTSET_JMP */ || op === 50 /* RegOp.FUSED_GGET */ ||
                op === 51 /* RegOp.FUSED_LOADKK */ || op === 52 /* RegOp.FUSED_MOVE_MOVE */ ||
                op === 53 /* RegOp.FUSED_SELF_CALL */ || op === 55 /* RegOp.FUSED_LOADK_RET */ ||
                op === 56 /* RegOp.FUSED_MOVE_RET */) {
                unsafeSplit.add(i + 4);
            }
            if (op === 54 /* RegOp.FUSED_GGET_CALL */) {
                unsafeSplit.add(i + 4);
                unsafeSplit.add(i + 8);
            }
        }
        const splitThreshold = 3 + Math.floor(rng() * 3);
        const sortedTargets = Array.from(targets).sort((a, b) => a - b);
        for (let bi = 0; bi < sortedTargets.length; bi++) {
            const bStart = sortedTargets[bi];
            const bEnd = bi + 1 < sortedTargets.length ? sortedTargets[bi + 1] : code.length;
            const bInstrCount = (bEnd - bStart) / 4;
            if (bInstrCount > splitThreshold) {
                const candidates = [];
                for (let pos = bStart + splitThreshold * 4; pos < bEnd - 4; pos += 4) {
                    if (!unsafeSplit.has(pos) && !targets.has(pos)) {
                        candidates.push(pos);
                    }
                }
                const nSplits = Math.min(candidates.length, 1 + Math.floor(rng() * 3));
                for (let si = candidates.length - 1; si > 0; si--) {
                    const sj = Math.floor(rng() * (si + 1));
                    [candidates[si], candidates[sj]] = [candidates[sj], candidates[si]];
                }
                for (let si = 0; si < nSplits; si++) {
                    targets.add(candidates[si]);
                }
            }
        }
        const blockStarts = Array.from(targets).sort((a, b) => a - b);
        if (blockStarts.length < 3)
            return code;
        const blocks = [];
        for (let bi = 0; bi < blockStarts.length; bi++) {
            const start = blockStarts[bi];
            const end = bi + 1 < blockStarts.length ? blockStarts[bi + 1] : code.length;
            const ins = code.slice(start, end);
            const jr = [];
            const bLen = ins.length;
            for (let j = 0; j < bLen; j += 4) {
                const op = ins[j];
                if (op === 21 /* RegOp.JMP */ || op === 30 /* RegOp.FORPREP */ || op === 31 /* RegOp.FORLOOP */) {
                    jr.push({ lo: j + 2, ot: start + j + 4 + ins[j + 2] * 4 });
                }
                if (op === 45 /* RegOp.FUSED_TEST_JMP */ || op === 46 /* RegOp.FUSED_EQ_JMP */ ||
                    op === 47 /* RegOp.FUSED_LT_JMP */ || op === 48 /* RegOp.FUSED_LE_JMP */ ||
                    op === 49 /* RegOp.FUSED_TESTSET_JMP */) {
                    jr.push({ lo: j + 6, ot: start + j + 8 + ins[j + 6] * 4 });
                }
            }
            const lastOp = ins[bLen - 4];
            const secOp = bLen >= 8 ? ins[bLen - 8] : -1;
            const isTerm = lastOp === 21 /* RegOp.JMP */ || lastOp === 29 /* RegOp.RETURN */ ||
                lastOp === 28 /* RegOp.TAILCALL */ || lastOp === 30 /* RegOp.FORPREP */ ||
                lastOp === 55 /* RegOp.FUSED_LOADK_RET */ || lastOp === 56 /* RegOp.FUSED_MOVE_RET */;
            const isCondJmp = bLen >= 8 &&
                (secOp === 22 /* RegOp.EQ */ || secOp === 23 /* RegOp.LT */ || secOp === 24 /* RegOp.LE */ ||
                    secOp === 25 /* RegOp.TEST */ || secOp === 26 /* RegOp.TESTSET */ ||
                    secOp === 32 /* RegOp.TFORLOOP */) && lastOp === 21 /* RegOp.JMP */;
            const isFusedCond = bLen >= 8 &&
                (secOp === 45 /* RegOp.FUSED_TEST_JMP */ || secOp === 46 /* RegOp.FUSED_EQ_JMP */ ||
                    secOp === 47 /* RegOp.FUSED_LT_JMP */ || secOp === 48 /* RegOp.FUSED_LE_JMP */ ||
                    secOp === 49 /* RegOp.FUSED_TESTSET_JMP */) && lastOp === 0 /* RegOp.NOP */;
            if (isCondJmp || isFusedCond) {
                ins.push(21 /* RegOp.JMP */, 0, 0, 0);
                jr.push({ lo: ins.length - 2, ot: end });
            }
            else if (lastOp === 31 /* RegOp.FORLOOP */) {
                ins.push(21 /* RegOp.JMP */, 0, 0, 0);
                jr.push({ lo: ins.length - 2, ot: end });
            }
            else if (!isTerm && end < code.length) {
                ins.push(21 /* RegOp.JMP */, 0, 0, 0);
                jr.push({ lo: ins.length - 2, ot: end });
            }
            blocks.push({ os: start, oe: end, ins, jr });
        }
        for (let i = blocks.length - 1; i > 0; i--) {
            const j = Math.floor(rng() * (i + 1));
            [blocks[i], blocks[j]] = [blocks[j], blocks[i]];
        }
        const origToNew = new Map();
        let pos = 4;
        for (const b of blocks) {
            const bNew = pos;
            for (let off = 0; off < b.oe - b.os; off += 4) {
                origToNew.set(b.os + off, bNew + off);
            }
            pos += b.ins.length;
        }
        origToNew.set(code.length, pos);
        const entryTarget = origToNew.get(0);
        const entryB = (entryTarget - 4) / 4;
        for (const b of blocks) {
            const bNew = origToNew.get(b.os);
            for (const ref of b.jr) {
                let nt = origToNew.get(ref.ot);
                if (nt === undefined) {
                    for (const b2 of blocks) {
                        if (ref.ot >= b2.os && ref.ot < b2.oe) {
                            nt = origToNew.get(b2.os) + (ref.ot - b2.os);
                            break;
                        }
                    }
                    if (nt === undefined) {
                        nt = pos;
                    }
                }
                const ipAfter = bNew + ref.lo + 2;
                b.ins[ref.lo] = (nt - ipAfter) / 4;
            }
        }
        const newCode = [21 /* RegOp.JMP */, 0, entryB, 0];
        for (const b of blocks) {
            for (let i = 0; i < b.ins.length; i++) {
                newCode.push(b.ins[i]);
            }
        }
        totalBlocks += blocks.length;
        return newCode;
    }
    chunk.code = flattenCode(chunk.code);
    if (chunk.protos) {
        for (const proto of chunk.protos) {
            totalBlocks += flattenControlFlow(proto);
        }
    }
    return totalBlocks;
}
function buildFusionPatterns(enabled) {
    const patterns = [];
    const add = (id, name, slots, match) => {
        if (enabled.has(id))
            patterns.push({ id, name, slots, match });
    };
    add(54 /* RegOp.FUSED_GGET_CALL */, "GGET_CALL", 3, (c, i) => c[i] === 5 /* RegOp.GETGLOBAL */ &&
        c[i + 4] === 7 /* RegOp.GETTABLE */ &&
        c[i + 8] === 27 /* RegOp.CALL */ &&
        c[i + 4 + 2] === c[i + 1] &&
        c[i + 8 + 1] === c[i + 4 + 1]);
    add(45 /* RegOp.FUSED_TEST_JMP */, "TEST_JMP", 2, (c, i) => c[i] === 25 /* RegOp.TEST */ && c[i + 4] === 21 /* RegOp.JMP */);
    add(46 /* RegOp.FUSED_EQ_JMP */, "EQ_JMP", 2, (c, i) => c[i] === 22 /* RegOp.EQ */ && c[i + 4] === 21 /* RegOp.JMP */);
    add(47 /* RegOp.FUSED_LT_JMP */, "LT_JMP", 2, (c, i) => c[i] === 23 /* RegOp.LT */ && c[i + 4] === 21 /* RegOp.JMP */);
    add(48 /* RegOp.FUSED_LE_JMP */, "LE_JMP", 2, (c, i) => c[i] === 24 /* RegOp.LE */ && c[i + 4] === 21 /* RegOp.JMP */);
    add(49 /* RegOp.FUSED_TESTSET_JMP */, "TESTSET_JMP", 2, (c, i) => c[i] === 26 /* RegOp.TESTSET */ && c[i + 4] === 21 /* RegOp.JMP */);
    add(50 /* RegOp.FUSED_GGET */, "GGET", 2, (c, i) => c[i] === 5 /* RegOp.GETGLOBAL */ &&
        c[i + 4] === 7 /* RegOp.GETTABLE */ &&
        c[i + 4 + 2] === c[i + 1]);
    add(51 /* RegOp.FUSED_LOADKK */, "LOADKK", 2, (c, i) => c[i] === 1 /* RegOp.LOADK */ && c[i + 4] === 1 /* RegOp.LOADK */);
    add(52 /* RegOp.FUSED_MOVE_MOVE */, "MOVE_MOVE", 2, (c, i) => c[i] === 4 /* RegOp.MOVE */ && c[i + 4] === 4 /* RegOp.MOVE */);
    add(53 /* RegOp.FUSED_SELF_CALL */, "SELF_CALL", 2, (c, i) => c[i] === 36 /* RegOp.SELF */ &&
        c[i + 4] === 27 /* RegOp.CALL */ &&
        c[i + 4 + 1] === c[i + 1]);
    add(55 /* RegOp.FUSED_LOADK_RET */, "LOADK_RET", 2, (c, i) => c[i] === 1 /* RegOp.LOADK */ &&
        c[i + 4] === 29 /* RegOp.RETURN */ &&
        c[i + 4 + 1] === c[i + 1] && c[i + 4 + 2] === 2);
    add(56 /* RegOp.FUSED_MOVE_RET */, "MOVE_RET", 2, (c, i) => c[i] === 4 /* RegOp.MOVE */ && c[i + 4] === 29 /* RegOp.RETURN */);
    return patterns;
}
function applyFusionPass(chunk, enabledPatterns, fusionRate) {
    const patterns = buildFusionPatterns(enabledPatterns);
    let totalFused = 0;
    function fuseCode(code) {
        const targets = computeJumpTargets(code);
        let count = 0;
        let i = 0;
        while (i < code.length - 4) {
            let matched = false;
            for (const pat of patterns) {
                if (i + pat.slots * 4 > code.length)
                    continue;
                let targetConflict = false;
                for (let s = 1; s < pat.slots; s++) {
                    if (targets.has(i + s * 4)) {
                        targetConflict = true;
                        break;
                    }
                }
                if (targetConflict)
                    continue;
                if (!pat.match(code, i))
                    continue;
                if (rng() > fusionRate) {
                    i += 4;
                    matched = true;
                    break;
                }
                code[i] = pat.id;
                for (let s = 1; s < pat.slots; s++) {
                    code[i + s * 4] = 0 /* RegOp.NOP */;
                }
                count++;
                i += pat.slots * 4;
                matched = true;
                break;
            }
            if (!matched)
                i += 4;
        }
        return count;
    }
    totalFused += fuseCode(chunk.code);
    if (chunk.protos) {
        for (const proto of chunk.protos) {
            totalFused += applyFusionPass(proto, enabledPatterns, fusionRate);
        }
    }
    return totalFused;
}
function collectUsedOpcodes(chunk) {
    const used = new Set();
    for (let i = 0; i < chunk.code.length; i += 4)
        used.add(chunk.code[i]);
    if (chunk.protos)
        for (const p of chunk.protos) {
            for (const op of collectUsedOpcodes(p))
                used.add(op);
        }
    return used;
}
function generateHandlerNoise(n, op) {
    const savedState = _rngState;
    _rngState = ((op * 0x45D9F3B + 0xDEADBEEF) >>> 0);
    rng();
    rng();
    let noise = '';
    if (rng() < 0.7) {
        const dv = randomName(2);
        const variant = Math.floor(rng() * 6);
        if (variant === 0)
            noise = `local ${dv}=${n.ip};`;
        else if (variant === 1)
            noise = `local ${dv}=${n.bBand}(${n.ip},0xFF);`;
        else if (variant === 2)
            noise = `local ${dv}=${n.bBxor}(${n.ip},${Math.floor(rng() * 255) + 1});`;
        else if (variant === 3)
            noise = `local ${dv}=${n.top};`;
        else if (variant === 4)
            noise = `local ${dv}=${n.R}[1];`;
        else
            noise = `local ${dv}=${n.bType}(${n.R}[0]);`;
    }
    _rngState = savedState;
    return noise;
}
function buildHandlerBodies(n, ctx, usedOps) {
    const bodies = new Map();
    const doNoise = ctx.level !== "debug";
    for (const [op, gen] of handlerRegistry) {
        if (usedOps && !usedOps.has(op))
            continue;
        const shuffled = ctx.opcodeEncode[op];
        const body = gen(n, ctx);
        const p = ctx.argPerm[op];
        const slots = [n.s1, n.s2, n.s3];
        const remap = `local A,B,C=${slots[p[0] - 1]},${slots[p[1] - 1]},${slots[p[2] - 1]};`;
        const noise = doNoise ? generateHandlerNoise(n, op) : '';
        bodies.set(shuffled, remap + noise + body);
        if (ctx.opcodeAlt && ctx.opcodeAlt[op] !== undefined) {
            const altNoise = doNoise ? generateHandlerNoise(n, op) : '';
            bodies.set(ctx.opcodeAlt[op], remap + altNoise + body);
        }
    }
    return bodies;
}
function buildBuiltinCaptures(ctx) {
    const n = ctx.names;
    if (ctx.level === "debug") {
        const captures = [
            [n.bPcall, "pcall"], [n.bXpcall, "xpcall"], [n.bSelect, "select"], [n.bType, "type"],
            [n.tPack, "table.pack or function(...) return {n=select('#',...),...} end"],
            [n.tUnpack, "table.unpack or unpack"],
            [n.bTcreate, "table.create or function(s,v) local t={} for i=1,s do t[i]=v end return t end"],
            [n.bTconcat, "table.concat"], [n.bMfloor, "math.floor"], [n.bIpairs, "ipairs"],
            [n.bTostring, "tostring"], [n.bRawget, "rawget"], [n.bSetmeta, "setmetatable"],
            [n.bBxor, "(bit32 and bit32.bxor) or (bit and bit.bxor) or function(a,b) a=a%4294967296;b=b%4294967296;local p,c=1,0 while a>0 or b>0 do local ra,rb=a%2,b%2 if ra~=rb then c=c+p end a,b,p=(a-ra)/2,(b-rb)/2,p*2 end return c end"],
            [n.bBand, "(bit32 and bit32.band) or (bit and bit.band) or function(a,b) a=a%4294967296;b=b%4294967296;local p,c=1,0 while a>0 and b>0 do local ra,rb=a%2,b%2 if ra==1 and rb==1 then c=c+p end a,b,p=(a-ra)/2,(b-rb)/2,p*2 end return c end"],
            [n.bLsh, "(bit32 and bit32.lshift) or (bit and bit.lshift) or function(a,s) s=s%32 return ((a%(2^(32-s)))*(2^s))%4294967296 end"],
            [n.bRsh, "(bit32 and bit32.rshift) or (bit and bit.rshift) or function(a,s) s=s%32 return math.floor((a%4294967296)/(2^s))%4294967296 end"],
            [n.bSbyte, "string.byte"], [n.bSchar, "string.char"],
            [n.bBcr, "(type(buffer)=='table' and buffer.create) or nil"],
            [n.bBlen, "(type(buffer)=='table' and buffer.len) or nil"],
            [n.bBr8, "(type(buffer)=='table' and buffer.readu8) or nil"],
            [n.bBw8, "(type(buffer)=='table' and buffer.writeu8) or nil"],
            [n.bBcp, "(type(buffer)=='table' and buffer.copy) or nil"],
            [n.bBfs, "(type(buffer)=='table' and buffer.fromstring) or nil"],
            [n.bGetmeta, "getmetatable"], [n.bNext, "next"],
        ];
        const fullLines = captures.map(([v, g]) => `local ${v}=${g}`);
        const assignLines = captures.map(([v, g]) => `${v}=${g}`);
        const fnvFull = `local ${n.fnv}=function(_s) local _h=2166136261 for _i=1,#_s do _h=${n.bBxor}(_h,${n.bSbyte}(_s,_i));_h=(_h*403+${n.bBand}(_h,255)*16777216)%4294967296 end return _h end`;
        const fnvAssign = `${n.fnv}=function(_s) local _h=2166136261 for _i=1,#_s do _h=${n.bBxor}(_h,${n.bSbyte}(_s,_i));_h=(_h*403+${n.bBand}(_h,255)*16777216)%4294967296 end return _h end`;
        const check = `local _hookOk=true`;
        return { code: [...fullLines, fnvFull, check].join("\n"), assignOnly: [...assignLines, fnvAssign, check].join("\n") };
    }
    const scVar = randomName(3);
    const encName = (s) => {
        const codes = Array.from(s).map(c => {
            const code = c.charCodeAt(0);
            const m = Math.floor(rng() * 4);
            if (m === 0) {
                const d = 1 + Math.floor(rng() * 20);
                return `${code - d}+${d}`;
            }
            if (m === 1) {
                const d = 1 + Math.floor(rng() * 20);
                return `${code + d}-${d}`;
            }
            if (m === 2)
                return `0x${code.toString(16)}`;
            return `${code}`;
        }).join(',');
        return `${scVar}(${codes})`;
    };
    const simpleCaptures = [
        [n.bPcall, "pcall"], [n.bXpcall, "xpcall"], [n.bSelect, "select"], [n.bType, "type"],
        [n.bIpairs, "ipairs"], [n.bTostring, "tostring"], [n.bRawget, "rawget"],
        [n.bSetmeta, "setmetatable"], [n.bGetmeta, "getmetatable"], [n.bNext, "next"],
    ];
    const libCaptures = [
        [n.tPack, "table", "pack"], [n.tUnpack, "table", "unpack"],
        [n.bTcreate, "table", "create"], [n.bTconcat, "table", "concat"],
        [n.bMfloor, "math", "floor"],
        [n.bSbyte, "string", "byte"], [n.bSchar, "string", "char"],
        [n.bBxor, "bit32", "bxor"], [n.bBand, "bit32", "band"],
        [n.bLsh, "bit32", "lshift"], [n.bRsh, "bit32", "rshift"],
        [n.bBcr, "buffer", "create"], [n.bBlen, "buffer", "len"],
        [n.bBr8, "buffer", "readu8"], [n.bBw8, "buffer", "writeu8"],
        [n.bBcp, "buffer", "copy"], [n.bBfs, "buffer", "fromstring"],
    ];
    const libs = new Map();
    for (const [varName, lib, member] of libCaptures) {
        if (!libs.has(lib))
            libs.set(lib, { libVar: randomName(2), members: [] });
        libs.get(lib).members.push([varName, member]);
    }
    const lines = [];
    lines.push(`do`);
    lines.push(`local ${scVar}=("")[${luaEsc("char")}]`);
    lines.push(`local _fe=(type(getfenv)=="function" and (getfenv(0) or getfenv())) or {}`);
    lines.push(`local _ge=(type(getgenv)=="function" and getgenv()) or {}`);
    lines.push(`local _re=(type(getrenv)=="function" and getrenv()) or {}`);
    lines.push(`local _gl=(type(_G)=="table" and _G) or {}`);
    lines.push(`local function _fnd(k) return _fe[k] or _gl[k] or _ge[k] or _re[k] end`);
    const shuffledSimple = [...simpleCaptures];
    for (let i = shuffledSimple.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [shuffledSimple[i], shuffledSimple[j]] = [shuffledSimple[j], shuffledSimple[i]];
    }
    for (const [varName, globalName] of shuffledSimple) {
        lines.push(`${varName}=_fnd(${encName(globalName)}) or ${globalName}`);
    }
    const libKeys = [...libs.keys()];
    for (let i = libKeys.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [libKeys[i], libKeys[j]] = [libKeys[j], libKeys[i]];
    }
    for (const libName of libKeys) {
        const { libVar, members } = libs.get(libName);
        let fallbackLib = `(${libName} or {})`;
        if (libName === "bit32")
            fallbackLib = "(bit32 or bit or {})";
        else if (libName === "buffer")
            fallbackLib = "(type(buffer)=='table' and buffer or {})";
        lines.push(`local ${libVar}=_fnd(${encName(libName)}) or ${fallbackLib}`);
        for (const [varName, memberName] of members) {
            if (libName === "buffer") {
                lines.push(`${varName}=(${n.bType}(${libVar})=="table" and ${libVar}[${encName(memberName)}]) or nil`);
                continue;
            }
            let polyfill = `${libName}.${memberName}`;
            if (libName === "bit32") {
                if (memberName === "bxor") {
                    polyfill = `(bit32 and bit32.bxor) or (bit and bit.bxor) or function(a,b) a=a%4294967296;b=b%4294967296;local p,c=1,0 while a>0 or b>0 do local ra,rb=a%2,b%2 if ra~=rb then c=c+p end a,b,p=(a-ra)/2,(b-rb)/2,p*2 end return c end`;
                } else if (memberName === "band") {
                    polyfill = `(bit32 and bit32.band) or (bit and bit.band) or function(a,b) a=a%4294967296;b=b%4294967296;local p,c=1,0 while a>0 and b>0 do local ra,rb=a%2,b%2 if ra==1 and rb==1 then c=c+p end a,b,p=(a-ra)/2,(b-rb)/2,p*2 end return c end`;
                } else if (memberName === "lshift") {
                    polyfill = `(bit32 and bit32.lshift) or (bit and bit.lshift) or function(a,s) s=s%32 return ((a%(2^(32-s)))*(2^s))%4294967296 end`;
                } else if (memberName === "rshift") {
                    polyfill = `(bit32 and bit32.rshift) or (bit and bit.rshift) or function(a,s) s=s%32 return math.floor((a%4294967296)/(2^s))%4294967296 end`;
                }
            } else if (libName === "table" && memberName === "create") {
                polyfill = `table.create or function(s,v) local t={} for i=1,s do t[i]=v end return t end`;
            } else if (libName === "table" && memberName === "pack") {
                polyfill = `table.pack or function(...) return {n=select("#",...),...} end`;
            } else if (libName === "table" && memberName === "unpack") {
                polyfill = `table.unpack or unpack`;
            }
            lines.push(`${varName}=(${libVar} and ${libVar}[${encName(memberName)}]) or ${polyfill}`);
        }
    }
    lines.push(`end`);
    lines.push(`${n.fnv}=function(_s) local _h=2166136261 for _i=1,#_s do _h=${n.bBxor}(_h,${n.bSbyte}(_s,_i));_h=(_h*403+${n.bBand}(_h,255)*16777216)%4294967296 end return _h end`);

    const nSecState = randomName(3);
    const nSecDelta = randomName(3);
    ctx.secDeltaVar = nSecDelta;
    ctx.secStateVar = nSecState;

    const initialSeed = 0x1337 + Math.floor(rng() * 0x7FFF);
    let expectedSeed = initialSeed;

    const spyNames = [
        "SimpleSpy", "Hydroxide", "RemoteSpy", "TurtleSpy",
        "OriginalNamecall", "SimpleSpyExecuted", "HydroxideExecuted",
        "SigmaSpy", "OctoSpy"
    ];
    const spyHashEntries = spyNames.map(s => `[0x${fnv1a32(s).toString(16)}]=true`).join(",");
    const trapHashEntries = ["__DEBUG_HOOK", "__SPY_ATTACHED", "SimpleSpyExecuted", "HydroxideExecuted"]
        .map(s => `[0x${fnv1a32(s).toString(16)}]=true`).join(",");

    const securityItems = [
        // Algebraic Invariant
        {
            cond: `${n.bPcall}(function() local _x=math.floor(math.abs(-42));assert((_x*(_x+1))%2==0) end)`,
            weight: 0x17 + Math.floor(rng() * 50)
        },
        // Bitwise Invariant
        {
            cond: `${n.bBand}(${n.bBxor}(0xAA,0x55),0xFF)==0xFF and ${n.bBand}(255,15)==15`,
            weight: 0x23 + Math.floor(rng() * 50)
        },
        // Roblox DataModel & Userdata Intrinsic
        {
            cond: `${n.bPcall}(function() if game~=nil then assert(type(game)=="userdata" and game.ClassName=="DataModel") end;if workspace~=nil then assert(type(workspace)=="userdata" and workspace.ClassName=="Workspace") end end)`,
            weight: 0x31 + Math.floor(rng() * 50)
        },
        // Metatable Proxy Invariant
        {
            cond: `${n.bPcall}(function() local _t=${n.bSetmeta}({},{__index=function() return 77 end});assert(_t[1]==77) end)`,
            weight: 0x47 + Math.floor(rng() * 50)
        },
        // Anti-spoofed debug.info on fresh local closure (safe across wrapped executor builtins)
        {
            cond: `${n.bPcall}(function() if debug and debug.info then local _d=function() end;local ok,src=${n.bPcall}(debug.info,_d,"s");if ok then assert(src~="[C]") end end end)`,
            weight: 0x6B + Math.floor(rng() * 50)
        },
        // FNV-1a Hashed Anti-Spy Registry Guard (zero plaintext spy names, no islclosure false positives)
        {
            cond: `${n.bPcall}(function() local _sp={${spyHashEntries}};local _g=(type(getgenv)=="function" and getgenv()) or (type(_G)=="table" and not (table.isfrozen and table.isfrozen(_G)) and _G);if _g then for _k,_v in ${n.bNext},_g do if _v and ${n.bType}(_k)=="string" and _sp[${n.fnv}(_k)] then error(1) end end end end)`,
            weight: 0x7F + Math.floor(rng() * 50)
        },
        // MBA Opaque Invariant: (x ^ y) + 2*(x & y) == x + y (Algebraic Arithmetic Invariant)
        {
            cond: `(function() local _x=${Math.floor(rng() * 0x7FFF) + 1};local _y=${Math.floor(rng() * 0x7FFF) + 1};return (${n.bBxor}(_x,_y)+2*${n.bBand}(_x,_y))==(_x+_y) end)()`,
            weight: 0x8A + Math.floor(rng() * 40)
        },
        // MBA Opaque Invariant: (x ^ y) == (x | y) - (x & y)
        {
            cond: `(function() local _x=${Math.floor(rng() * 0x7FFF) + 1};local _y=${Math.floor(rng() * 0x7FFF) + 1};local _bor=function(a,b) return a+b-${n.bBand}(a,b) end;return ${n.bBxor}(_x,_y)==(_bor(_x,_y)-${n.bBand}(_x,_y)) end)()`,
            weight: 0x93 + Math.floor(rng() * 40)
        }
    ];

    for (let ci = securityItems.length - 1; ci > 0; ci--) {
        const cj = Math.floor(rng() * (ci + 1));
        [securityItems[ci], securityItems[cj]] = [securityItems[cj], securityItems[ci]];
    }

    for (const item of securityItems) {
        const mixed = ((expectedSeed * 31 + item.weight) & 0xFFFF) ^ (item.weight * 7);
        expectedSeed = mixed & 0xFFFF;
    }

    // Dynamic Keying: Target PlaceId or Universal Runtime Invariant (Anti-Offline Poisoning)
    const targetPlaceId = Number(ctx.targetPlaceId || 0);
    const hasPlaceLock = targetPlaceId > 0;

    // Per-build randomized 16-bit dynamic salt (No static hardcoded values)
    const universalSalt = Math.floor(rng() * 0xDE00) + 0x1100;
    const saltShareA = Math.floor(rng() * 0x7E00) + 0x1000;
    const saltShareB = (universalSalt ^ saltShareA) & 0xFFFF;

    const expectedDynSalt = hasPlaceLock
        ? (targetPlaceId & 0xFFFF)
        : universalSalt;

    expectedSeed = ((expectedSeed * 31 + expectedDynSalt) & 0xFFFF) ^ ((expectedDynSalt * 7) & 0xFFFF);

    const secLines = [
        `${nSecState}=${initialSeed}`
    ];
    for (const item of securityItems) {
        secLines.push(`if ${item.cond} then local _m=${n.bBand}((${nSecState}*31+${item.weight}),0xFFFF);${nSecState}=${n.bBand}(${n.bBxor}(_m,${item.weight * 7}),0xFFFF) end`);
    }

    if (hasPlaceLock) {
        secLines.push(`local _dynSalt=0;${n.bPcall}(function() if game~=nil and ${n.bType}(game)=="userdata" and game.ClassName=="DataModel" and game.PlaceId then _dynSalt=${n.bBand}(game.PlaceId,0xFFFF) end end);local _m=${n.bBand}((${nSecState}*31+_dynSalt),0xFFFF);${nSecState}=${n.bBand}(${n.bBxor}(_m,${n.bBand}(_dynSalt*7,0xFFFF)),0xFFFF)`);
    } else {
        secLines.push(`local _dynSalt=0;${n.bPcall}(function() if game~=nil and ${n.bType}(game)=="userdata" and game.ClassName=="DataModel" then local _rs=game:GetService("RunService");if _rs and ${n.bType}(_rs)=="userdata" then _dynSalt=${n.bBxor}(${saltShareA},${saltShareB}) end end end);local _m=${n.bBand}((${nSecState}*31+_dynSalt),0xFFFF);${nSecState}=${n.bBand}(${n.bBxor}(_m,${n.bBand}(_dynSalt*7,0xFFFF)),0xFFFF)`);
    }

    // Silent Desynchronization Sentinel (The Ghost Trap, FNV-1a Hashed)
    secLines.push(`local _ghostTrap=false;${n.bPcall}(function() if debug and debug.gethook and debug.gethook()~=nil then _ghostTrap=true end;local _th={${trapHashEntries}};local _g=(type(getgenv)=="function" and getgenv()) or (type(_G)=="table" and _G);if _g then for _k,_v in ${n.bNext},_g do if _v and ${n.bType}(_k)=="string" and _th[${n.fnv}(_k)] then _ghostTrap=true;break end end end end);if _ghostTrap then ${nSecState}=${n.bBxor}(${nSecState},1) end`);

    secLines.push(`${nSecDelta}=${n.bBxor}(${nSecState},${expectedSeed})`);

    const fullCode = [...lines, `local ${nSecState}`, `local ${nSecDelta}`, ...secLines].join("\n");
    const assignCode = [...lines, ...secLines].join("\n");
    return { code: fullCode, assignOnly: assignCode, secDeltaVar: nSecDelta, secStateVar: nSecState };
}
function buildVMRuntime(ctx, assignStyle = false) {
    const n = ctx.names;
    const { pK, pC, pP, pU, pN } = ctx.protoKeys;
    const bodies = buildHandlerBodies(n, ctx, ctx.usedOps);
    let rkThreshVar = '';
    let rkSubVar = '';
    if (ctx.level !== "debug") {
        rkThreshVar = randomName(3);
        rkSubVar = randomName(3);
        const hotRawOps = [
            10 /* RegOp.ADD */, 11 /* RegOp.SUB */, 12 /* RegOp.MUL */,
            13 /* RegOp.DIV */, 14 /* RegOp.MOD */, 15 /* RegOp.POW */,
            16 /* RegOp.IDIV */,
        ];
        const hotShuffled = new Set([
            ...hotRawOps.map(op => ctx.opcodeEncode[op]),
            ...(ctx.opcodeAlt ? hotRawOps.map(op => ctx.opcodeAlt[op]).filter(x => x !== undefined) : [])
        ]);
        const rkEsc = n.RK.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const rkRe = new RegExp(rkEsc + '\\(([A-Z])\\)', 'g');
        for (const [sOp, body] of bodies) {
            if (hotShuffled.has(sOp)) {
                const inlined = body.replace(rkRe, (_m, v) => `(${v}>=${rkThreshVar} and ${n.K}[${v}-${rkSubVar}] or ${n.R}[${v}+1])`);
                if (inlined !== body)
                    bodies.set(sOp, inlined);
            }
        }
    }

    const sortedOps = Array.from(bodies.keys()).sort((a, b) => a - b);
    const validOps = sortedOps.filter(sOp => bodies.get(sOp).trim() !== '');

    // Prepare Nested 2-Layer CFF State Machine configuration (for non-debug builds)
    const tagMask = (ctx.tagMask || 0) & 0xFF;
    const usedStateIds = new Set();
    const allocStateId = () => {
        let id;
        do {
            id = 0x1000 + Math.floor(rng() * 0xEE00);
        } while (usedStateIds.has(id));
        usedStateIds.add(id);
        return id;
    };
    const exitOuterId = allocStateId();
    const trapOuterId = allocStateId();
    const decoyOuterIds = [allocStateId(), allocStateId(), allocStateId()];
    const outerBuckets = [];
    if (ctx.level !== "debug" && validOps.length > 0) {
        const shuffledValid = [...validOps];
        for (let i = shuffledValid.length - 1; i > 0; i--) {
            const j = Math.floor(rng() * (i + 1));
            [shuffledValid[i], shuffledValid[j]] = [shuffledValid[j], shuffledValid[i]];
        }
        const nBuckets = Math.max(1, Math.min(shuffledValid.length, 4 + Math.floor(rng() * 3)));
        const hotOps = new Set();
        for (const rop of [1, 4, 5, 7, 8, 10, 11, 12, 13, 14, 15, 16, 21, 22, 23, 24, 25, 26, 27, 30, 31, 36]) {
            if (ctx.opcodeEncode[rop] !== undefined)
                hotOps.add(ctx.opcodeEncode[rop]);
            if (ctx.opcodeAlt && ctx.opcodeAlt[rop] !== undefined)
                hotOps.add(ctx.opcodeAlt[rop]);
        }
        for (let b = 0; b < nBuckets; b++) {
            outerBuckets.push({
                outerId: allocStateId(),
                hopId: null,
                iMask: 1 + Math.floor(rng() * 255),
                iBias: 256 + Math.floor(rng() * 60000),
                ops: []
            });
        }
        for (let i = 0; i < shuffledValid.length; i++) {
            outerBuckets[i % nBuckets].ops.push(shuffledValid[i]);
        }
        for (const bkt of outerBuckets) {
            const hasHot = bkt.ops.some(sOp => hotOps.has(sOp));
            if (!hasHot && rng() > 0.35) {
                bkt.hopId = allocStateId();
            }
        }
    }

    const L = [];
    const declPfx = assignStyle ? '' : 'local ';
    L.push(`${declPfx}${n.wLut}={[0]=0,1,2,4}`);
    L.push(`${declPfx}${n.shCache}={}`);
    L.push(`${declPfx}${n.pk}=function(_p) local _pl=${n.bBand}(_p,255);local _ph=${n.bBand}(${n.bRsh}(_p,8),255);return ${n.bBand}(${ctx.rotSeed}+_pl*${ctx.rotStep}+_pl*_pl*${ctx.rotStep2}+_ph*${ctx.rotStep3},255) end`);
    const roVar = assignStyle ? randomName(3) : '_ro';
    L.push(`do local _hb=(${n.bBcr}~=nil and ${n.bBlen}~=nil and ${n.bBr8}~=nil and ${n.bBw8}~=nil and ${n.bBcp}~=nil);` +
        `${n.rb}=_hb and ${n.bBr8} or function(_t,_i) return _t[_i+1] end;` +
        `${n.wb}=_hb and ${n.bBw8} or function(_t,_i,_v) _t[_i+1]=_v end;` +
        `${n.cp}=_hb and ${n.bBcp} or function(_d,_dp,_s,_sp,_l) for _k=0,_l-1 do _d[_dp+_k+1]=_s[_sp+_k+1] end end;` +
        `local function ${roVar}(_sh,_b,_p,_o,_w,_isR,_rk) ` +
        `if _w==0 then return 0,_o ` +
        `elseif _w==1 then return (_isR and ${n.bBxor}(${n.rb}(_b,_p+_o),_rk[_o+1]) or ${n.bBxor}(${n.rb}(_sh,_p+_o),${n.pk}(_p+_o))),_o+1 ` +
        `elseif _w==2 then local _b0,_b1;if _isR then _b0=${n.bBxor}(${n.rb}(_b,_p+_o),_rk[_o+1]);_b1=${n.bBxor}(${n.rb}(_b,_p+_o+1),_rk[_o+2]) else _b0=${n.bBxor}(${n.rb}(_sh,_p+_o),${n.pk}(_p+_o));_b1=${n.bBxor}(${n.rb}(_sh,_p+_o+1),${n.pk}(_p+_o+1)) end;local _u=_b0+_b1*256;if _u>=32768 then _u=_u-65536 end;return _u,_o+2 ` +
        `else local _b0,_b1,_b2,_b3;if _isR then _b0=${n.bBxor}(${n.rb}(_b,_p+_o),_rk[_o+1]);_b1=${n.bBxor}(${n.rb}(_b,_p+_o+1),_rk[_o+2]);_b2=${n.bBxor}(${n.rb}(_b,_p+_o+2),_rk[_o+3]);_b3=${n.bBxor}(${n.rb}(_b,_p+_o+3),_rk[_o+4]) else _b0=${n.bBxor}(${n.rb}(_sh,_p+_o),${n.pk}(_p+_o));_b1=${n.bBxor}(${n.rb}(_sh,_p+_o+1),${n.pk}(_p+_o+1));_b2=${n.bBxor}(${n.rb}(_sh,_p+_o+2),${n.pk}(_p+_o+2));_b3=${n.bBxor}(${n.rb}(_sh,_p+_o+3),${n.pk}(_p+_o+3)) end;local _u=_b0+_b1*256+_b2*65536+_b3*16777216;if _u>=2147483648 then _u=_u-4294967296 end;return _u,_o+4 end end;` +
        `${n.dec}=function(_sh,_b,_p,_isR,_rk) local _op,_tg;if _isR then _op=${n.bBxor}(${n.rb}(_b,_p),_rk[1]);_tg=${n.bBxor}(${n.bBxor}(${n.rb}(_b,_p+1),_rk[2]),${tagMask}) else _op=${n.bBxor}(${n.rb}(_sh,_p),${n.pk}(_p));_tg=${n.bBxor}(${n.bBxor}(${n.rb}(_sh,_p+1),${n.pk}(_p+1)),${tagMask}) end;local _o=2;local _s1,_s2,_s3;_s1,_o=${roVar}(_sh,_b,_p,_o,${n.bBand}(_tg,3),_isR,_rk);_s2,_o=${roVar}(_sh,_b,_p,_o,${n.bBand}(${n.bRsh}(_tg,2),3),_isR,_rk);_s3,_o=${roVar}(_sh,_b,_p,_o,${n.bBand}(${n.bRsh}(_tg,4),3),_isR,_rk);return _op,_s1,_s2,_s3,_o end;` +
        `${n.adv}=function(_ip1,_sh) local _tg=${n.bBxor}(${n.bBxor}(${n.rb}(_sh,_ip1),${n.pk}(_ip1)),${tagMask});return _ip1+2+${n.wLut}[${n.bBand}(_tg,3)]+${n.wLut}[${n.bBand}(${n.bRsh}(_tg,2),3)]+${n.wLut}[${n.bBand}(${n.bRsh}(_tg,4),3)] end end`);
    if (ctx.level !== "debug") {
        const oMapEntries = [];
        for (const bkt of outerBuckets) {
            for (const sOp of bkt.ops) {
                oMapEntries.push(`[${sOp}]=${bkt.outerId}`);
            }
        }
        L.push(`${declPfx}${n.oMap}={${oMapEntries.join(",")}}`);
    } else {
        L.push(`${declPfx}${n.oMap}={}`);
    }

    L.push(assignStyle
        ? `${n.run}=function(${n.K},${n.code},${n.protos},${n.upvalues},${n.nParams},${n.maxRegs},_isVararg,${n.env},...)`
        : `local function ${n.run}(${n.K},${n.code},${n.protos},${n.upvalues},${n.nParams},${n.maxRegs},_isVararg,${n.env},...)`);
    if (ctx.encodeStrings && ctx.singleDecVar) {
        const rawKVar = randomName(3);
        L.push(`local ${rawKVar}=${n.K};local ${n.K}=${n.bSetmeta}({},{__index=function(_,i) local r=${rawKVar}[i];if ${n.bType}(r)=="table" then return ${ctx.singleDecVar}(r,i) end;return r end,__newindex=function() end,__metatable=false})`);
    }
    L.push(`${n.protos}=${n.protos} or {}`);
    L.push(`${n.upvalues}=${n.upvalues} or {}`);
    L.push(`local ${n.R}=${n.bTcreate}(${n.maxRegs}+1)`);
    L.push(`local _args={...}`);
    L.push(`local _ac=${n.bSelect}("#",...)`);
    L.push(`for _i=1,((_ac<${n.nParams}) and _ac or ${n.nParams}) do ${n.R}[_i]=_args[_i] end`);
    L.push(`local ${n.varargs}={}`);
    L.push(`local ${n.vaCount}=0`);
    L.push(`if _isVararg then ${n.vaCount}=_ac-${n.nParams};if ${n.vaCount}<0 then ${n.vaCount}=0 end;for _i=1,${n.vaCount} do ${n.varargs}[_i]=_args[${n.nParams}+_i] end end`);

    const xsSeed = (0x10000000 + Math.floor(rng() * 0x6FFFFFFF)) >>> 0;
    const deadOp = ctx.deadOp ?? 254;
    const xsVar = randomName(3);
    const scrAddrVar = randomName(3);
    const scrLenVar = randomName(3);
    const rkArrVar = randomName(3);
    const curPVar = randomName(3);
    const isRollVar = randomName(3);
    const curLenVar = randomName(3);
    const invVar = randomName(3);
    const cLenVar = randomName(3);
    const wiVar = randomName(3);
    const npVar = randomName(3);
    const ntgVar = randomName(3);
    const nlVar = randomName(3);
    const cwVar = randomName(3);
    const jxVar = randomName(3);
    const jmVar = randomName(3);
    const kmVar = randomName(3);

    L.push(`local ${cLenVar}=#${n.code}`);
    L.push(`local ${n.shVar}=${n.shCache}[${n.code}]`);
    L.push(`local ${n.bBufVar}`);
    L.push(`if ${n.bBcr}~=nil and ${n.bBlen}~=nil and ${n.bBr8}~=nil and ${n.bBw8}~=nil and ${n.bBcp}~=nil then ` +
        `if not ${n.shVar} then if ${n.bBfs} then ${n.shVar}=${n.bBfs}(${n.code}) else ${n.shVar}=${n.bBcr}(${cLenVar});for _ci=1,${cLenVar} do ${n.bBw8}(${n.shVar},_ci-1,${n.bSbyte}(${n.code},_ci)) end end;${n.shCache}[${n.code}]=${n.shVar} end;` +
        `${n.bBufVar}=${n.bBcr}(${cLenVar});${n.bBcp}(${n.bBufVar},0,${n.shVar},0,${cLenVar}) ` +
        `else ` +
        `if not ${n.shVar} then ${n.shVar}=${n.bTcreate}(${cLenVar});for _ci=1,${cLenVar} do ${n.shVar}[_ci]=${n.bSbyte}(${n.code},_ci) end;${n.shCache}[${n.code}]=${n.shVar} end;` +
        `${n.bBufVar}=${n.bTcreate}(${cLenVar});for _ci=1,${cLenVar} do ${n.bBufVar}[_ci]=${n.shVar}[_ci] end end`);
    L.push(`local ${n.deadOpVar}=${deadOp}`);
    L.push(`local ${n.hasScrVar}=false`);
    if (ctx.level !== "debug") {
        L.push(`local ${xsVar}=${xsSeed}`);
        L.push(`local ${scrAddrVar}=-1`);
        L.push(`local ${scrLenVar}=0`);
        L.push(`local ${rkArrVar}=${n.bTcreate}(14);for _ri=1,14 do ${rkArrVar}[_ri]=0 end`);
        L.push(`local ${invVar}=${17 + Math.floor(rng() * 80)}`);
    }

    L.push(`local ${n.ip}=1`);
    L.push(`local ${n.openUVs}={}`);
    L.push(`local ${n.ic}={}`);
    L.push(`local ${n.top}=0`);
    const nTwVm = ctx.level !== "debug" ? randomName(2) : "_tw";
    L.push(`local ${nTwVm};do local _t=${n.env}["task"];if _t then ${nTwVm}=_t["wait"] end end`);

    if (ctx.level !== "debug") {
        const rkVariant = Math.floor(rng() * 6);
        const a = Math.floor(rng() * 200) + 10;
        const b = RK_OFFSET - a;
        if (rkVariant === 0) {
            L.push(`local ${rkThreshVar}=${a}+${b}`);
        } else if (rkVariant === 1) {
            L.push(`local ${rkThreshVar}=(${n.bBxor} and ${n.bBxor}(${RK_OFFSET ^ a},${a})) or ${RK_OFFSET}`);
        } else if (rkVariant === 2) {
            const shift = Math.floor(rng() * 3) + 1;
            L.push(`local ${rkThreshVar}=${RK_OFFSET >> shift}*${1 << shift}`);
        } else if (rkVariant === 3) {
            const rndMul = 1 + Math.floor(rng() * 100);
            const rkPow2 = 1 << Math.ceil(Math.log2(RK_OFFSET + 1));
            const rkMask = rkPow2 - 1;
            L.push(`local ${rkThreshVar}=(${n.bBand} and ${n.bBand}(${RK_OFFSET + rndMul * rkPow2},0x${rkMask.toString(16).toUpperCase()})) or ${RK_OFFSET}`);
        } else if (rkVariant === 4) {
            const m = [2, 4, 8, 16, 32, 64][Math.floor(rng() * 6)];
            L.push(`local ${rkThreshVar}=${RK_OFFSET / m}*${m}`);
        } else {
            L.push(`local ${rkThreshVar}=(${n.bBand} and ${n.bBand}(${RK_OFFSET | (Math.floor(rng() * 256) << 16)},0xFFFF)) or ${RK_OFFSET}`);
        }
        L.push(`local ${rkSubVar}=${rkThreshVar}-1`);
        L.push(`local function ${n.RK}(x) if x>=${rkThreshVar} then return ${n.K}[x-${rkSubVar}] else return ${n.R}[x+1] end end`);
    } else {
        L.push(`local function ${n.RK}(x) if x>=${RK_OFFSET} then return ${n.K}[x-${RK_OFFSET - 1}] else return ${n.R}[x+1] end end`);
    }

    if (ctx.debugTrace) {
        const entries = REG_OP_NAMES.map((name, realOp) => {
            const shuffled = ctx.opcodeEncode[realOp];
            return `[${shuffled}]="${name}"`;
        }).join(",");
        L.push(`local _opNames={${entries}}`);
    }

    const doMut = ctx.level !== "debug";
    let opqVar = '';
    if (doMut) {
        opqVar = randomName(3);
        const opqA = 2 + Math.floor(rng() * 100);
        const opqB = 2 + Math.floor(rng() * 100);
        const opqC = 2 + Math.floor(rng() * 100);
        const mbaV1 = randomName(2);
        const mbaV2 = randomName(2);
        const mbaV3 = randomName(2);
        const opqVariant = Math.floor(rng() * 16);
        if (opqVariant === 0) {
            L.push(`local ${mbaV1}=${n.bBand}(${opqA},${opqB})`);
            L.push(`local ${mbaV2}=${n.bBand}(${n.bBxor}(${opqA},0xFFFFFFFF),${opqB})`);
            L.push(`local ${opqVar}=${mbaV1}+${mbaV2}==${n.bBand}(${opqB},0xFFFFFFFF)`);
        } else if (opqVariant === 1) {
            L.push(`local ${mbaV1}=2*${n.bBand}(${opqA},${opqB})+${n.bBxor}(${opqA},${opqB})`);
            L.push(`local ${opqVar}=${mbaV1}==${opqA}+${opqB}`);
        } else if (opqVariant === 2) {
            L.push(`local ${mbaV1}=${n.bBxor}(${n.bBxor}(${opqA},${opqB}),${opqB})`);
            L.push(`local ${mbaV2}=${n.bBxor}(${n.bBxor}(${mbaV1},${opqC}),${opqC})`);
            L.push(`local ${opqVar}=${mbaV2}==${n.bBand}(${opqA},0xFFFFFFFF)`);
        } else if (opqVariant === 3) {
            L.push(`local ${mbaV1}=${n.bBxor}(${n.bBxor}(${opqA},0xFFFFFFFF),0xFFFFFFFF)`);
            L.push(`local ${mbaV2}=${n.bBand}(${n.bBxor}(${mbaV1},${opqB}),${n.bBxor}(${mbaV1},${opqB}))`);
            L.push(`local ${opqVar}=${mbaV2}==${n.bBxor}(${opqA},${opqB})`);
        } else if (opqVariant === 4) {
            L.push(`local ${mbaV1}=2*${n.bBand}(${opqA},${opqB})+${n.bBxor}(${opqA},${opqB})`);
            L.push(`local ${mbaV2}=${n.bBxor}(${n.bBxor}(${n.bBand}(${mbaV1},0xFFFF),${opqC}),${opqC})`);
            L.push(`local ${opqVar}=${mbaV2}==${n.bBand}(${opqA}+${opqB},0xFFFF)`);
        } else if (opqVariant === 5) {
            L.push(`local ${mbaV1}=${n.bBxor}(${n.bBand}(${n.bBxor}(${opqA},0xFFFFFFFF),${n.bBxor}(${opqB},0xFFFFFFFF)),0xFFFFFFFF)`);
            L.push(`local ${mbaV2}=${n.bBxor}(${opqA},${n.bBand}(${n.bBxor}(${opqA},0xFFFFFFFF),${opqB}))`);
            L.push(`local ${opqVar}=${mbaV1}==${mbaV2}`);
        } else if (opqVariant === 6) {
            L.push(`local ${mbaV1}=${n.bBxor}(${opqA},${opqB})`);
            L.push(`local ${mbaV2}=${n.bBand}(${mbaV1},${mbaV1})`);
            L.push(`local ${mbaV3}=2*${n.bBand}(${mbaV2},${opqC})+${n.bBxor}(${mbaV2},${opqC})`);
            L.push(`local ${opqVar}=${mbaV3}==${mbaV1}+${opqC}`);
        } else if (opqVariant === 7) {
            L.push(`local ${mbaV1}=${n.bBxor}(${opqA},${n.bBand}(${opqA},${opqB}))`);
            L.push(`local ${mbaV2}=${n.bBand}(${opqA},${n.bBxor}(${opqB},0xFFFFFFFF))`);
            L.push(`local ${opqVar}=${mbaV1}==${mbaV2}`);
        } else if (opqVariant === 8) {
            L.push(`local ${mbaV1}=${n.bBand}(${opqA},${opqB})`);
            L.push(`local ${mbaV2}=${n.bBxor}(${opqA},${n.bBand}(${n.bBxor}(${opqA},0xFFFFFFFF),${mbaV1}))`);
            L.push(`local ${opqVar}=${mbaV2}==${n.bBand}(${opqA},0xFFFFFFFF)`);
        } else if (opqVariant === 9) {
            L.push(`local ${mbaV1}=2*${n.bBand}(${opqA},${opqB})+${n.bBxor}(${opqA},${opqB})`);
            L.push(`local ${mbaV2}=2*${n.bBand}(${mbaV1},${opqC})+${n.bBxor}(${mbaV1},${opqC})`);
            L.push(`local ${opqVar}=${n.bBand}(${mbaV2},0xFFFF)==${n.bBand}(${opqA}+${opqB}+${opqC},0xFFFF)`);
        } else if (opqVariant === 10) {
            L.push(`local ${mbaV1}=${n.bBxor}(${opqA},${opqB})`);
            L.push(`local ${mbaV2}=${opqA}+${opqB}-2*${n.bBand}(${opqA},${opqB})`);
            L.push(`local ${opqVar}=${n.bBand}(${mbaV1},0xFFFF)==${n.bBand}(${mbaV2},0xFFFF)`);
        } else if (opqVariant === 11) {
            L.push(`local ${mbaV1}=${n.bBand}(${opqA},${opqB})`);
            L.push(`local ${mbaV2}=${n.bBand}(${mbaV1},${opqC})`);
            L.push(`local ${mbaV3}=${n.bBand}(${opqA},${n.bBand}(${opqB},${opqC}))`);
            L.push(`local ${opqVar}=${mbaV2}==${mbaV3}`);
        } else if (opqVariant === 12) {
            L.push(`local ${mbaV1}=${n.bBand}(${n.bBxor}(${opqA},${opqB}),${opqA})`);
            L.push(`local ${mbaV2}=${n.bBand}(${opqA},${n.bBxor}(${opqB},0xFFFFFFFF))`);
            L.push(`local ${mbaV3}=2*${n.bBand}(${mbaV1},${opqC})+${n.bBxor}(${mbaV1},${opqC})`);
            L.push(`local ${opqVar}=${mbaV3}==2*${n.bBand}(${mbaV2},${opqC})+${n.bBxor}(${mbaV2},${opqC})`);
        } else if (opqVariant === 13) {
            L.push(`local ${mbaV1}=${n.bBxor}(${n.bBxor}(${opqA},${opqB}),${opqC})`);
            L.push(`local ${mbaV2}=${n.bBxor}(${n.bBxor}(${mbaV1},${opqC}),${opqB})`);
            L.push(`local ${opqVar}=${mbaV2}==${n.bBand}(${opqA},0xFFFFFFFF)`);
        } else if (opqVariant === 14) {
            L.push(`local ${mbaV1}=${n.bBand}(${opqA},${n.bBxor}(${opqB},${opqC}))`);
            L.push(`local ${mbaV2}=${n.bBxor}(${n.bBand}(${opqA},${opqB}),${n.bBand}(${opqA},${opqC}))`);
            L.push(`local ${opqVar}=${mbaV1}==${mbaV2}`);
        } else {
            L.push(`local ${mbaV1}=${n.bBand}(${opqA},${opqB})+${n.bBand}(${n.bBxor}(${opqA},0xFFFFFFFF),${opqB})`);
            L.push(`local ${mbaV2}=${n.bBand}(${opqA},${n.bBxor}(${opqB},0xFFFFFFFF))+${n.bBand}(${n.bBxor}(${opqA},0xFFFFFFFF),${n.bBxor}(${opqB},0xFFFFFFFF))`);
            L.push(`local ${opqVar}=${mbaV1}+${mbaV2}==0xFFFFFFFF`);
        }
        L.push(`if not ${opqVar} then ${n.R}=${n.bTcreate}(0);${cLenVar}=0;${n.ip}=1 end`);
    }

    const opVar = randomName(2);
    L.push(`while ${n.ip}<=${cLenVar} do`);
    if (ctx.level !== "debug") {
        L.push(`local ${curPVar}=${n.ip}-1`);
        L.push(`local ${isRollVar}=(${n.hasScrVar} and ${curPVar}==${scrAddrVar})`);
        L.push(`if ${n.hasScrVar} and not ${isRollVar} then ${n.cp}(${n.bBufVar},${scrAddrVar},${n.shVar},${scrAddrVar},${scrLenVar});${n.hasScrVar}=false end`);
        L.push(`local ${opVar},${n.s1},${n.s2},${n.s3},${curLenVar}=${n.dec}(${n.shVar},${n.bBufVar},${curPVar},${isRollVar},${rkArrVar})`);
        L.push(`${n.ip}=${n.ip}+${curLenVar}`);
        L.push(`for ${wiVar}=0,${curLenVar}-1 do ${n.wb}(${n.bBufVar},${curPVar}+${wiVar},${n.deadOpVar}) end`);
        // Rolling Xorshift32 encryption over NEXT sequential instruction in working buffer
        L.push(`do local ${npVar}=${n.ip}-1;if ${npVar}+1<${cLenVar} then ` +
            `local ${ntgVar}=${n.bBxor}(${n.bBxor}(${n.rb}(${n.shVar},${npVar}+1),${n.pk}(${npVar}+1)),${tagMask});` +
            `local ${nlVar}=2+${n.wLut}[${n.bBand}(${ntgVar},3)]+${n.wLut}[${n.bBand}(${n.bRsh}(${ntgVar},2),3)]+${n.wLut}[${n.bBand}(${n.bRsh}(${ntgVar},4),3)];` +
            `if ${npVar}+${nlVar}<=${cLenVar} then local ${cwVar}=${xsVar};` +
            `for ${jxVar}=1,${nlVar} do local ${jmVar}=(${jxVar}-1)%4;if ${jmVar}==0 then ` +
            `${xsVar}=${n.bBxor}(${xsVar},${n.bBand}(${n.bLsh}(${xsVar},13),0xFFFFFFFF));` +
            `${xsVar}=${n.bBxor}(${xsVar},${n.bRsh}(${xsVar},17));` +
            `${xsVar}=${n.bBxor}(${xsVar},${n.bBand}(${n.bLsh}(${xsVar},5),0xFFFFFFFF));` +
            `${cwVar}=${xsVar} end;` +
            `local ${kmVar}=${n.bBand}(${n.bRsh}(${cwVar},${jmVar}*8),0xFF);` +
            `${rkArrVar}[${jxVar}]=${kmVar};` +
            `${n.wb}(${n.bBufVar},${npVar}+${jxVar}-1,${n.bBxor}(${n.bBxor}(${n.rb}(${n.shVar},${npVar}+${jxVar}-1),${n.pk}(${npVar}+${jxVar}-1)),${kmVar})) end;` +
            `${scrAddrVar}=${npVar};${scrLenVar}=${nlVar};${n.hasScrVar}=true ` +
            `else ${n.hasScrVar}=false end else ${n.hasScrVar}=false end end`);
    } else {
        L.push(`local ${curPVar}=${n.ip}-1`);
        L.push(`local ${opVar},${n.s1},${n.s2},${n.s3},${curLenVar}=${n.dec}(${n.shVar},${n.bBufVar},${curPVar},false,nil)`);
        L.push(`${n.ip}=${n.ip}+${curLenVar}`);
    }

    if (doMut) {
        L.push(`if ${n.ip}%${60000 + Math.floor(rng() * 40001)}<4 and ${nTwVm} then ${nTwVm}() end`);
    }
    if (doMut && process.env.NO_SEC !== '1') {
        const secInterval = 500 + Math.floor(rng() * 1500);
        const secVar = randomName(3);
        const secCheckVariant = Math.floor(rng() * 2);
        if (secCheckVariant === 0) {
            L.push(`if ${n.ip}%${secInterval * 4}<4 then local ${secVar}=${n.env}["game"];if ${secVar}~=nil and ${n.bType}(${secVar})~="userdata" and ${n.bType}(${secVar})~="table" then ${n.R}=${n.bTcreate}(0);${n.ip}=${cLenVar}+1 end end`);
        } else {
            L.push(`if ${n.ip}%${secInterval * 4}<4 then local ${secVar}=${n.env}["workspace"];if ${secVar}~=nil and ${n.bType}(${secVar})~="userdata" and ${n.bType}(${secVar})~="table" then ${n.R}=${n.bTcreate}(0);${n.ip}=${cLenVar}+1 end end`);
        }
    }
    if (ctx.debugTrace) {
        L.push(`print("[VM] p="..(${curPVar}).." "..((_opNames and _opNames[${opVar}]) or "OP"..${opVar}).." s1="..tostring(${n.s1}).." s2="..tostring(${n.s2}).." s3="..tostring(${n.s3}))`);
    }

    if (ctx.level === "debug" || outerBuckets.length === 0) {
        let isFirst = true;
        for (const sOp of validOps) {
            const body = bodies.get(sOp);
            const prefix = isFirst ? 'if' : 'elseif';
            L.push(`${prefix} ${opVar}==${sOp} then ${body}`);
            isFirst = false;
        }
        if (!isFirst)
            L.push(`end`);
    } else {
        // Multi-Layered Nested CFF State Machine (Outer State Bucket + Inner Dispatcher + MBA Opaque Predicates)
        const oStVar = randomName(3);
        const secCoupling = ctx.secDeltaVar ? `,(${ctx.secDeltaVar} or 0)` : `,0`;
        L.push(`local ${oStVar}=${n.bBxor}((${n.oMap}[${opVar}] or ${trapOuterId})${secCoupling})`);
        L.push(`while ${oStVar}~=${exitOuterId} do`);

        const outerBranches = [];
        for (const bkt of outerBuckets) {
            const innerEntries = bkt.ops.map(sOp => ({
                sel: ((sOp ^ bkt.iMask) + bkt.iBias) & 0xFFFF,
                body: bodies.get(sOp),
                isDecoy: false,
            }));
            const usedSels = new Set(innerEntries.map(e => e.sel));
            let decoySel;
            do {
                decoySel = 256 + Math.floor(rng() * 64000);
            } while (usedSels.has(decoySel));
            innerEntries.push({ sel: decoySel, body: `${n.R}=${n.bTcreate}(0);break`, isDecoy: true });
            for (let i = innerEntries.length - 1; i > 0; i--) {
                const j = Math.floor(rng() * (i + 1));
                [innerEntries[i], innerEntries[j]] = [innerEntries[j], innerEntries[i]];
            }
            const nextOuter = bkt.hopId || exitOuterId;
            const bLines = [];
            const iStVar = randomName(3);
            const oNxVar = randomName(3);
            const innerSecTerm = ctx.secDeltaVar ? `${n.bBxor}(${opVar},${bkt.iMask}),(${ctx.secDeltaVar} or 0)` : `${opVar},${bkt.iMask}`;
            bLines.push(`local ${iStVar}=${n.bBand}(${n.bBxor}(${innerSecTerm})+${bkt.iBias},0xFFFF);local ${oNxVar}=${n.bBxor}(${oStVar},${bkt.outerId ^ nextOuter})`);
            for (let k = 0; k < innerEntries.length; k++) {
                const ent = innerEntries[k];
                const kw = k === 0 ? 'if' : 'elseif';
                if (ent.isDecoy) {
                    bLines.push(`${kw} ${iStVar}==${ent.sel} and (${opqVar} and ((${invVar}*(${invVar}+1))%2==1)) then ${ent.body}`);
                } else {
                    bLines.push(`${kw} ${iStVar}==${ent.sel} then ${ent.body}`);
                }
            }
            bLines.push(`end;${oStVar}=${oNxVar}`);
            outerBranches.push({ id: bkt.outerId, isDecoy: false, code: bLines.join("\n") });

            if (bkt.hopId) {
                outerBranches.push({
                    id: bkt.hopId,
                    isDecoy: false,
                    code: `if ${opqVar} then ${oStVar}=${n.bBxor}(${oStVar},${bkt.hopId ^ exitOuterId}) else ${n.R}=${n.bTcreate}(0);${oStVar}=${exitOuterId} end`
                });
            }
        }

        for (const did of decoyOuterIds) {
            outerBranches.push({
                id: did,
                isDecoy: true,
                code: `${n.R}=${n.bTcreate}(0);${oStVar}=${exitOuterId}`
            });
        }
        outerBranches.push({
            id: trapOuterId,
            isDecoy: false,
            code: `${oStVar}=${exitOuterId}`
        });

        for (let i = outerBranches.length - 1; i > 0; i--) {
            const j = Math.floor(rng() * (i + 1));
            [outerBranches[i], outerBranches[j]] = [outerBranches[j], outerBranches[i]];
        }

        for (let bi = 0; bi < outerBranches.length; bi++) {
            const br = outerBranches[bi];
            const kw = bi === 0 ? 'if' : 'elseif';
            const cond = br.isDecoy
                ? `${oStVar}==${br.id} and (${opqVar} and ((${invVar}*(${invVar}+1))%2==1))`
                : `${oStVar}==${br.id}`;
            L.push(`${kw} ${cond} then`);
            L.push(br.code);
        }
        L.push(ctx.secDeltaVar
            ? `else if (${ctx.secDeltaVar} or 0)~=0 then ${n.R}=${n.bTcreate}(0);${n.ip}=${cLenVar}+1 end;${oStVar}=${exitOuterId} end`
            : `else ${oStVar}=${exitOuterId} end`);
        L.push(`end`);
    }

    L.push(`end`);
    L.push(`end`);
    return L.join("\n");
}
const CORE_GLOBALS = [
    "print", "warn", "error", "assert", "type", "typeof", "tostring", "tonumber",
    "pcall", "xpcall", "select", "unpack", "pairs", "ipairs", "next",
    "rawget", "rawset", "rawequal", "rawlen", "setmetatable", "getmetatable",
    "collectgarbage", "dofile", "gcinfo",
    "string", "table", "math", "bit32", "coroutine", "os", "debug", "utf8", "buffer",
    "game", "workspace", "script", "Instance", "Enum",
    "Vector3", "Vector2", "CFrame", "Color3", "BrickColor",
    "UDim", "UDim2", "Ray", "Region3", "Rect", "TweenInfo",
    "NumberSequence", "ColorSequence", "NumberRange",
    "NumberSequenceKeypoint", "ColorSequenceKeypoint",
    "PhysicalProperties", "Axes", "Faces", "PathWaypoint",
    "Random", "DateTime", "RaycastParams", "OverlapParams",
    "Font", "FloatCurveKey", "RotationCurveKey",
    "tick", "time", "wait", "task", "spawn", "delay",
    "require", "loadstring", "load", "getfenv", "setfenv", "newproxy",
    "_G", "shared", "settings", "stats", "UserSettings", "version",
];
const EXECUTOR_GLOBALS = [
    "getgenv", "getrenv", "getsenv", "getrawmetatable", "setrawmetatable",
    "hookfunction", "hookfunc", "hookmetamethod", "newcclosure",
    "clonefunction", "cloneref", "compareinstances",
    "iscclosure", "islclosure", "isexecutorclosure", "checkclosure", "isourclosure",
    "checkcaller",
    "getconnections", "firesignal", "fireclickdetector", "fireproximityprompt", "firetouchinterest",
    "getgc", "filtergc", "getinstances", "getnilinstances", "getscripts", "getrunningscripts",
    "getloadedmodules", "getcallingscript", "getactors",
    "getscriptbytecode", "dumpstring", "getscripthash", "getscriptclosure", "decompile",
    "readfile", "writefile", "appendfile", "loadfile", "listfiles",
    "isfile", "isfolder", "makefolder", "delfolder", "delfile",
    "setclipboard", "toclipboard", "getclipboard", "setrbxclipboard",
    "queue_on_teleport", "queueonteleport",
    "setthreadidentity", "getthreadidentity",
    "setidentity", "getidentity", "setthreadcontext", "getthreadcontext",
    "getnamecallmethod", "setnamecallmethod",
    "isreadonly", "setreadonly",
    "gethiddenproperty", "sethiddenproperty", "isscriptable", "setscriptable",
    "identifyexecutor", "getexecutorname", "gethwid",
    "request", "http_request", "syn", "http", "WebSocket",
    "cache",
    "Drawing", "cleardrawcache", "isrenderobj",
    "crypt", "base64",
    "lz4compress", "lz4decompress",
    "mouse1click", "mouse1press", "mouse1release",
    "mouse2click", "mouse2press", "mouse2release",
    "mousemoveabs", "mousemoverel", "mousescroll",
    "gethui", "getcustomasset", "getsynasset", "getcallbackvalue", "messagebox",
    "replicatesignal", "restorefunction", "isfunctionhooked",
    "isrbxactive", "isgameactive", "setfpscap",
    "getregistry", "getreg", "getstack",
    "rconsoleclear", "rconsolecreate", "rconsoledestroy",
    "rconsoleinput", "rconsoleprint", "rconsolesettitle", "rconsolename",
    "consoleclear", "consolecreate", "consoledestroy",
    "consoleinput", "consoleprint", "consolesettitle",
    "run_on_actor", "runonactor",
];
function buildEnvSetup(ctx) {
    const n = ctx.names;
    const L = [];
    if (ctx.level === "debug") {
        L.push(`local ${n.genv}=(type(getfenv)=="function" and getfenv(0)) or _G`);
        const entries = CORE_GLOBALS.map(g => `${g}=${g}`).join(",");
        L.push(`local ${n.env}=setmetatable({${entries}},{__index=function(_,k) local ok,v=pcall(function() return ${n.genv}[k] end);if ok then return v end;return nil end})`);
        if (ctx.includeExecutor) {
            for (const g of EXECUTOR_GLOBALS) {
                L.push(`do local ok,v=pcall(function() return ${n.genv}["${g}"] end);if ok and v~=nil then ${n.env}["${g}"]=v end end`);
            }
        }
        return L.join("\n") + "\n";
    }
    const envKey = 1 + Math.floor(rng() * 254);
    const envStep = 1 + Math.floor(rng() * 254);
    const encS = (s) => {
        const bytes = Array.from(s).map((c, i) => c.charCodeAt(0) ^ ((envKey + i * envStep) & 0xFF));
        return `{${bytes.join(",")}}`;
    };
    const dec = randomName(4);
    L.push(`local function ${dec}(_t) local _s="";for _i=1,#_t do _s=_s..${n.bSchar}(${n.bBxor}(_t[_i],${n.bBand}(${envKey}+(_i-1)*${envStep},0xFF))) end;return _s end`);
    L.push(`local ${n.genv}=(type(getfenv)=="function" and (getfenv(0) or getfenv())) or (type(_G)=="table" and _G) or (type(getgenv)=="function" and getgenv()) or (type(getrenv)=="function" and getrenv()) or {}`);
    L.push(`local ${n.env}=${n.bSetmeta}({},{[${dec}(${encS("__index")})]=function(_,k) if k=="game" then return (type(game)~="nil" and game) or ${n.genv}["game"] or (getgenv and getgenv().game) or (getrenv and getrenv().game) end;if k=="workspace" then return (type(workspace)~="nil" and workspace) or ${n.genv}["workspace"] or (getgenv and getgenv().workspace) or (getrenv and getrenv().workspace) end;if k=="script" then return (type(script)~="nil" and script) or ${n.genv}["script"] or (getgenv and getgenv().script) end;if k=="task" then return (type(task)~="nil" and task) or ${n.genv}["task"] or (getgenv and getgenv().task) or (getrenv and getrenv().task) end;if k=="Instance" then return (type(Instance)~="nil" and Instance) or ${n.genv}["Instance"] or (getgenv and getgenv().Instance) or (getrenv and getrenv().Instance) end;if k=="cloneref" then return (type(cloneref)~="nil" and cloneref) or (getgenv and getgenv().cloneref) or function(x) return x end end;if k=="buffer" then return buffer end;local ok,v=${n.bPcall}(function() return ${n.genv}[k] end);if ok and v~=nil then return v end;if type(_G)=="table" and _G[k]~=nil then return _G[k] end;if type(getgenv)=="function" then local ok2,v2=${n.bPcall}(function() return getgenv()[k] end);if ok2 and v2~=nil then return v2 end end;if type(getrenv)=="function" then local ok3,v3=${n.bPcall}(function() return getrenv()[k] end);if ok3 and v3~=nil then return v3 end end;if k=="math" then return math end;if k=="table" then return table end;if k=="string" then return string end;if k=="bit32" then return bit32 or bit end;if k=="pairs" then return pairs end;if k=="ipairs" then return ipairs end;if k=="next" then return next end;if k=="pcall" then return pcall end;if k=="xpcall" then return xpcall end;if k=="type" then return type end;if k=="typeof" then return (type(typeof)=="function" and typeof) or type end;if k=="select" then return select end;if k=="tostring" then return tostring end;if k=="tonumber" then return tonumber end;if k=="assert" then return assert end;if k=="error" then return error end;if k=="warn" then return warn end;if k=="print" then return print end;if k=="setmetatable" then return setmetatable end;if k=="getmetatable" then return getmetatable end;if k=="rawget" then return rawget end;if k=="rawset" then return rawset end;if k=="Vector3" then return Vector3 end;if k=="CFrame" then return CFrame end;if k=="Color3" then return Color3 end;if k=="UDim2" then return UDim2 end;if k=="Enum" then return Enum end;if k=="TweenInfo" then return TweenInfo end;if k=="tick" then return (type(tick)=="function" and tick) or os.time end;if k=="time" then return (type(time)=="function" and time) or os.clock end;return nil end,[${dec}(${encS("__newindex")})]=function(t,k,v) rawset(t,k,v); if type(getgenv)=="function" then ${n.bPcall}(function() getgenv()[k]=v end) end; if type(_G)=="table" then ${n.bPcall}(function() _G[k]=v end) end end})`);
    const allGlobals = ctx.includeExecutor ? [...CORE_GLOBALS, ...EXECUTOR_GLOBALS] : [...CORE_GLOBALS];
    for (let si = allGlobals.length - 1; si > 0; si--) {
        const sj = Math.floor(rng() * (si + 1));
        [allGlobals[si], allGlobals[sj]] = [allGlobals[sj], allGlobals[si]];
    }
    const namesTable = randomName(3);
    L.push(`local ${namesTable}={${allGlobals.map(g => encS(g)).join(",")}}`);
    const iV = randomName(2);
    const nV = randomName(2);
    L.push(`for ${iV}=1,#${namesTable} do local ${nV}=${dec}(${namesTable}[${iV}]);local ok,v=${n.bPcall}(function() return ${n.genv}[${nV}] end);if ok and v~=nil then ${n.env}[${nV}]=v end end`);
    L.push(`do local _u=${dec}(${encS("unpack")});if not ${n.env}[_u] then local _t=${n.env}[${dec}(${encS("table")})];if _t then ${n.env}[_u]=_t[_u] end end end`);
    L.push(`do local _ls=${dec}(${encS("loadstring")});if not ${n.env}[_ls] then ${n.env}[_ls]=${n.env}[${dec}(${encS("load")})] end end`);
    return L.join("\n") + "\n";
}
function buildEnvFragments(ctx) {
    const n = ctx.names;
    const fragments = [];
    const forwardDecls = [];
    const envKey = 1 + Math.floor(rng() * 254);
    const envStep = 1 + Math.floor(rng() * 254);
    const encS = (s) => {
        const bytes = Array.from(s).map((c, i) => c.charCodeAt(0) ^ ((envKey + i * envStep) & 0xFF));
        return `{${bytes.join(",")}}`;
    };
    const dec = randomName(4);
    const nFallbackG = randomName(4);
    forwardDecls.push(dec, nFallbackG, n.genv, n.env);
    fragments.push({ code: `${nFallbackG}={}`, layer: 0 });
    fragments.push({ code: `${dec}=function(_t) local _s="";for _i=1,#_t do _s=_s..${n.bSchar}(${n.bBxor}(_t[_i],${n.bBand}(${envKey}+(_i-1)*${envStep},0xFF))) end;return _s end`, layer: 0 });
    fragments.push({ code: `${n.genv}=(type(getfenv)=="function" and (getfenv(0) or getfenv())) or (type(getgenv)=="function" and getgenv()) or (type(_G)=="table" and not (table.isfrozen and table.isfrozen(_G)) and _G) or (type(getrenv)=="function" and getrenv()) or {}`, layer: 1 });
    fragments.push({ code: `${n.env}=${n.bSetmeta}({},{[${dec}(${encS("__index")})]=function(_,k) if k=="_G" then local _rg=(type(getgenv)=="function" and getgenv()._G);if type(_rg)=="table" and not (table.isfrozen and table.isfrozen(_rg)) then return _rg end;if type(_G)=="table" and not (table.isfrozen and table.isfrozen(_G)) then return _G end;return ${nFallbackG} end;if k=="_ENV" then return ${n.env} end;if k=="shared" then return (type(shared)=="table" and shared) or (type(getgenv)=="function" and getgenv().shared) or ${nFallbackG} end;if k=="getgenv" then return (type(getgenv)=="function" and getgenv) or function() return (type(_G)=="table" and _G) or ${n.genv} end end;if k=="getrenv" then return (type(getrenv)=="function" and getrenv) or function() return (type(_G)=="table" and _G) or ${n.genv} end end;if k=="getfenv" then return (type(getfenv)=="function" and getfenv) or function() return ${n.env} end end;if k=="setfenv" then return (type(setfenv)=="function" and setfenv) or function() end end;if k=="game" then return (type(game)~="nil" and game) or ${n.genv}["game"] or (getgenv and getgenv().game) or (getrenv and getrenv().game) end;if k=="workspace" then return (type(workspace)~="nil" and workspace) or ${n.genv}["workspace"] or (getgenv and getgenv().workspace) or (getrenv and getrenv().workspace) end;if k=="script" then return (type(script)~="nil" and script) or ${n.genv}["script"] or (getgenv and getgenv().script) end;if k=="task" then return (type(task)~="nil" and task) or ${n.genv}["task"] or (getgenv and getgenv().task) or (getrenv and getrenv().task) end;if k=="Instance" then return (type(Instance)~="nil" and Instance) or ${n.genv}["Instance"] or (getgenv and getgenv().Instance) or (getrenv and getrenv().Instance) end;if k=="cloneref" then return (type(cloneref)~="nil" and cloneref) or (getgenv and getgenv().cloneref) or function(x) return x end end;if k=="buffer" then return buffer end;local ok,v=${n.bPcall}(function() return ${n.genv}[k] end);if ok and v~=nil then return v end;if type(_G)=="table" and _G[k]~=nil then return _G[k] end;if ${nFallbackG}[k]~=nil then return ${nFallbackG}[k] end;if type(getgenv)=="function" then local ok2,v2=${n.bPcall}(function() return getgenv()[k] end);if ok2 and v2~=nil then return v2 end end;if type(getrenv)=="function" then local ok3,v3=${n.bPcall}(function() return getrenv()[k] end);if ok3 and v3~=nil then return v3 end end;if k=="math" then return math end;if k=="table" then return table end;if k=="string" then return string end;if k=="bit32" then return bit32 or bit end;if k=="pairs" then return pairs end;if k=="ipairs" then return ipairs end;if k=="next" then return next end;if k=="pcall" then return pcall end;if k=="xpcall" then return xpcall end;if k=="type" then return type end;if k=="typeof" then return (type(typeof)=="function" and typeof) or type end;if k=="select" then return select end;if k=="tostring" then return tostring end;if k=="tonumber" then return tonumber end;if k=="assert" then return assert end;if k=="error" then return error end;if k=="warn" then return warn end;if k=="print" then return print end;if k=="setmetatable" then return setmetatable end;if k=="getmetatable" then return getmetatable end;if k=="rawget" then return rawget end;if k=="rawset" then return rawset end;if k=="Vector2" then return Vector2 end;if k=="Vector3" then return Vector3 end;if k=="Vector2int16" then return Vector2int16 end;if k=="Vector3int16" then return Vector3int16 end;if k=="Region3int16" then return Region3int16 end;if k=="CFrame" then return CFrame end;if k=="Color3" then return Color3 end;if k=="UDim2" then return UDim2 end;if k=="UDim" then return UDim end;if k=="Enum" then return Enum end;if k=="TweenInfo" then return TweenInfo end;if k=="NumberRange" then return NumberRange end;if k=="ColorSequence" then return ColorSequence end;if k=="ColorSequenceKeypoint" then return ColorSequenceKeypoint end;if k=="NumberSequence" then return NumberSequence end;if k=="NumberSequenceKeypoint" then return NumberSequenceKeypoint end;if k=="Ray" then return Ray end;if k=="Rect" then return Rect end;if k=="Region3" then return Region3 end;if k=="Font" then return Font end;if k=="DateTime" then return DateTime end;if k=="Random" then return Random end;if k=="utf8" then return utf8 end;if k=="RaycastParams" then return RaycastParams end;if k=="OverlapParams" then return OverlapParams end;if k=="PhysicalProperties" then return PhysicalProperties end;if k=="PathWaypoint" then return PathWaypoint end;if k=="FloatCurveKey" then return FloatCurveKey end;if k=="RotationCurveKey" then return RotationCurveKey end;if k=="CatalogSearchParams" then return CatalogSearchParams end;if k=="DockWidgetPluginGuiInfo" then return DockWidgetPluginGuiInfo end;if k=="Axes" then return Axes end;if k=="Faces" then return Faces end;if k=="tick" then return (type(tick)=="function" and tick) or (type(os)=="table" and os.time) end;if k=="time" then return (type(time)=="function" and time) or (type(os)=="table" and os.clock) end;if k=="os" then return os end;if k=="coroutine" then return coroutine end;if k=="debug" then return debug end;if k=="unpack" then return table.unpack or unpack end;local _pe=(type(getfenv)=="function" and (getfenv(0) or getfenv())) or {};if _pe and _pe[k]~=nil then return _pe[k] end;return nil end,[${dec}(${encS("__newindex")})]=function(t,k,v) rawset(t,k,v); ${nFallbackG}[k]=v; if type(getgenv)=="function" then ${n.bPcall}(function() getgenv()[k]=v end) end; if type(_G)=="table" and not (table.isfrozen and table.isfrozen(_G)) then ${n.bPcall}(function() _G[k]=v end) end end})`, layer: 2 });
    const allGlobals = (ctx.includeExecutor ? [...CORE_GLOBALS, ...EXECUTOR_GLOBALS] : [...CORE_GLOBALS])
        .filter(g => g !== "_G" && g !== "_ENV");
    for (let si = allGlobals.length - 1; si > 0; si--) {
        const sj = Math.floor(rng() * (si + 1));
        [allGlobals[si], allGlobals[sj]] = [allGlobals[sj], allGlobals[si]];
    }
    const batchCount = 2 + Math.floor(rng() * 3);
    const batchSize = Math.ceil(allGlobals.length / batchCount);
    for (let b = 0; b < batchCount; b++) {
        const batch = allGlobals.slice(b * batchSize, (b + 1) * batchSize);
        if (batch.length === 0)
            continue;
        const nt = randomName(3);
        forwardDecls.push(nt);
        fragments.push({ code: `${nt}={${batch.map(g => encS(g)).join(",")}}`, layer: 0 });
        const iV = randomName(2);
        const nV = randomName(2);
        fragments.push({ code: `for ${iV}=1,#${nt} do local ${nV}=${dec}(${nt}[${iV}]);local ok,v=${n.bPcall}(function() return ${n.genv}[${nV}] end);if ok and v~=nil then ${n.env}[${nV}]=v end end`, layer: 3 });
    }
    fragments.push({ code: `do local _u=${dec}(${encS("unpack")});if not ${n.env}[_u] then local _t=${n.env}[${dec}(${encS("table")})];if _t then ${n.env}[_u]=_t[_u] end end end`, layer: 3 });
    fragments.push({ code: `do local _ls=${dec}(${encS("loadstring")});if not ${n.env}[_ls] then ${n.env}[_ls]=${n.env}[${dec}(${encS("load")})] end end`, layer: 3 });
    if (process.env.DEBUG_VM === '1') {
        const critGlobals = ["string", "table", "math", "pcall", "type", "tostring", "pairs", "ipairs", "next", "rawget", "setmetatable", "getmetatable", "bit32", "select", "xpcall", "loadstring", "error", "warn", "print", "game", "workspace"];
        const checks = critGlobals.map(g => `if ${n.env}[${dec}(${encS(g)})]==nil then _m[#_m+1]="${g}" end`).join(";");
        fragments.push({ code: `do local _m={};${checks};if #_m>0 then warn("[ENV_MISSING] "..table.concat(_m,",")) else warn("[ENV_OK] all globals loaded") end end`, layer: 3 });
        fragments.push({ code: `warn("[DBG_GENV] genv="..tostring(${n.genv}).." type="..type(${n.genv}))`, layer: 3 });
    }
    return { fragments, forwardDecls };
}
function buildDecoderChain(ctx, dK, dP) {
    const n = ctx.names;
    const pk = ctx.protoKeys;
    const V = ctx.layerVariants;
    const fragments = [];
    const forwardDecls = [];
    const nSingleDec = randomName(6);
    const nInv = randomName(5);
    const nCharTab = randomName(5);
    forwardDecls.push(nInv, nCharTab, nSingleDec);
    ctx.singleDecVar = nSingleDec;

    const SP = ctx.spiralPrime, SO = ctx.spiralOffset;
    const KA = ctx.checkKeyA, KB = ctx.checkKeyB, SA = ctx.checkStepA, SB = ctx.checkStepB;
    const CM = ctx.cascadeMul, CK = ctx.cascadeKey;
    const HS = ctx.helixSeed, HM = ctx.helixMul;
    const inv = ctx.sboxInverse;

    fragments.push({ code: `${nInv}={${inv.join(",")}}`, layer: 0 });
    // Zero-Hook Local ASCII Cache Table: pre-populated via raw string metatable indexing
    fragments.push({
        code: `do local _sc=("")[${luaEsc("char")}];${nCharTab}={};for _ci=0,255 do ${nCharTab}[_ci]=_sc(_ci) end end`,
        layer: 0
    });

    const sExpr = ctx.secDeltaVar ? `${n.bBand}(_0i-1+(${ctx.secDeltaVar} or 0),0xFF)` : `${n.bBand}(_0i-1,0xFF)`;

    fragments.push({
        code: `${nSingleDec}=function(_0v,_0i) ` +
            `if ${n.bType}(_0v)~="table" then return _0v end;` +
            `local _0s=${sExpr};local _n=#_0v;local _b={};` +
            `for _j=1,_n do _b[_j]=_0v[_j] end;` +
            `for _j=1,_n do _b[_j]=${n.bBxor}(_b[_j],((_j-1)*${SP}+${SO}+_0s)%251) end;` +
            `for _j=1,_n do local _h=${n.bMfloor}((_j-1)/2);local _k=((_j-1)%2==0) and ${n.bBand}(${KA}+_0s+_h*${SA},0xFF) or ${n.bBand}(${KB}+_0s+_h*${SB},0xFF);_b[_j]=${n.bBxor}(_b[_j],_k) end;` +
            `for _j=2,_n do _b[_j]=${n.bBxor}(_b[_j],${n.bBand}(_b[_j-1]*${CM}+${CK}+_0s,0xFF)) end;` +
            `for _j=1,_n do _b[_j]=${n.bBand}(_b[_j]-${n.bBand}(${HS}+_0s+(_j-1)*${HM},0xFF)+256,0xFF) end;` +
            `local _res={};` +
            `for _j=1,_n do local _un=(${nInv} and ${nInv}[${n.bBand}(_b[_j],0xFF)+1]) or _b[_j];` +
            `_res[_j]=(${nCharTab} and ${nCharTab}[${n.bBxor}(_un,${n.bBand}(_0s+_j-1,0xFF))]) or ${n.bSchar}(${n.bBxor}(_un,${n.bBand}(_0s+_j-1,0xFF))) end;` +
            `local _out=${n.bTconcat}(_res);for _j=1,_n do _b[_j]=0 end;return _out end`,
        layer: 1
    });

    const chainCalls = "";
    return { fragments, forwardDecls, chainCalls };
}
function generateJunkFragments(fragments, forwardDecls, n) {
    const count = 5 + Math.floor(rng() * 6);
    const liveRefs = n ? [
        n.R, n.K, n.code, n.ip, n.run, n.env,
        n.bBxor, n.bBand, n.bType, n.tPack, n.bSelect, n.bMfloor,
        n.bPcall, n.bTostring, n.bRawget,
    ] : [];
    const liveRef = () => liveRefs[Math.floor(rng() * liveRefs.length)];
    for (let i = 0; i < count; i++) {
        const jn = randomName(4);
        forwardDecls.push(jn);
        const layer = Math.floor(rng() * 4);
        const jType = Math.floor(rng() * (n ? 9 : 5));
        switch (jType) {
            case 0:
                fragments.push({ code: `${jn}=${Math.floor(rng() * 0xFFFFFF)}`, layer });
                break;
            case 1: {
                const len = 3 + Math.floor(rng() * 8);
                const vals = Array.from({ length: len }, () => Math.floor(rng() * 256));
                fragments.push({ code: `${jn}={${vals.join(",")}}`, layer });
                break;
            }
            case 2: {
                const ref = n ? liveRef() : '_K';
                const a = Math.floor(rng() * 200), b = 1 + Math.floor(rng() * 200);
                const fnIpairs = n ? n.bIpairs : 'ipairs';
                const fnType = n ? n.bType : 'type';
                const fnBxor = n ? n.bBxor : 'bit32.bxor';
                const fnBand = n ? n.bBand : 'bit32.band';
                fragments.push({ code: `${jn}=function(${randomName(2)}) for _i,_v in ${fnIpairs}(${ref} or {}) do if ${fnType}(_v)=="table" then for _j=1,#_v do _v[_j]=${fnBxor}(_v[_j],${fnBand}(_j*${b}+${a},0xFF)) end end end end`, layer });
                break;
            }
            case 3: {
                const x = Math.floor(rng() * 100), y = 1 + Math.floor(rng() * 50);
                const fnBand = n ? n.bBand : 'bit32.band';
                fragments.push({ code: `do ${jn}=${x};for _=${1},${y} do ${jn}=${fnBand}(${jn}*${1 + Math.floor(rng() * 7)}+${Math.floor(rng() * 200)},0xFFFF) end end`, layer });
                break;
            }
            case 4: {
                const fnType = n ? n.bType : 'type';
                fragments.push({ code: `if ${fnType}(${jn})~="number" then ${jn}=${Math.floor(rng() * 1000)} end`, layer });
                break;
            }
            case 5: {
                const ref = liveRef();
                fragments.push({ code: `${jn}=${n.bType}(${ref})`, layer });
                break;
            }
            case 6: {
                const ref = liveRef();
                fragments.push({ code: `${jn}=${n.bType}(${ref})=="table" and #${ref} or 0`, layer });
                break;
            }
            case 7: {
                const ref = liveRef();
                fragments.push({ code: `${jn}=${n.bSelect}(1,${ref},${Math.floor(rng() * 1000)})`, layer });
                break;
            }
            case 8: {
                const ref = liveRef();
                const ref2 = liveRef();
                fragments.push({ code: `${jn}=${n.bPcall}(function() return ${n.bTostring}(${ref}) end) and ${n.bType}(${ref2})`, layer });
                break;
            }
        }
    }
}
function lzssCompress(input) {
    const out = [];
    const WIN = 16384;
    const MIN_MATCH = 4;
    const MAX_MATCH = 67;
    const MAX_LIT = 128;
    const HASH_SIZE = 1 << 16;
    const HASH_MASK = HASH_SIZE - 1;
    const head = new Int32Array(HASH_SIZE).fill(-1);
    const prev = new Int32Array(input.length).fill(-1);
    function hash3(pos) {
        return ((input[pos] << 10) ^ (input[pos + 1] << 5) ^ (input[pos + 2] ?? 0)) & HASH_MASK;
    }
    let i = 0;
    let litBuf = [];
    const flushLiterals = () => {
        while (litBuf.length > 0) {
            const n = Math.min(litBuf.length, MAX_LIT);
            out.push(n - 1);
            for (let j = 0; j < n; j++)
                out.push(litBuf[j]);
            litBuf = litBuf.slice(n);
        }
    };
    while (i < input.length) {
        let bestLen = 0, bestOff = 0;
        if (i + MIN_MATCH <= input.length) {
            const h = hash3(i);
            let j = head[h];
            const limit = Math.max(0, i - WIN);
            let chain = 0;
            while (j >= limit && chain < 128) {
                let len = 0;
                while (len < MAX_MATCH && i + len < input.length && input[j + len] === input[i + len])
                    len++;
                if (len > bestLen) {
                    bestLen = len;
                    bestOff = i - j;
                }
                if (len === MAX_MATCH)
                    break;
                j = prev[j];
                if (j < 0)
                    break;
                chain++;
            }
            prev[i] = head[h];
            head[h] = i;
        }
        if (bestLen >= MIN_MATCH) {
            flushLiterals();
            if (bestOff <= 256) {
                out.push(0x80 | (bestLen - MIN_MATCH));
                out.push(bestOff - 1);
            }
            else {
                out.push(0xC0 | (bestLen - MIN_MATCH));
                out.push((bestOff >> 8) & 0xFF);
                out.push(bestOff & 0xFF);
            }
            for (let s = 1; s < bestLen && i + s + 2 < input.length; s++) {
                const sh = hash3(i + s);
                prev[i + s] = head[sh];
                head[sh] = i + s;
            }
            i += bestLen;
        }
        else {
            litBuf.push(input[i]);
            i++;
        }
    }
    flushLiterals();
    return out;
}
function rleCompress(input) {
    const out = [];
    let i = 0;
    while (i < input.length) {
        const b = input[i];
        let run = 1;
        while (i + run < input.length && input[i + run] === b && run < 258)
            run++;
        if (run >= 4) {
            out.push(0xFF, run - 3, b);
            i += run;
        }
        else if (b === 0xFF) {
            out.push(0xFF, 0x00);
            i++;
        }
        else {
            out.push(b);
            i++;
        }
    }
    return out;
}
function verifyCipherRoundtrip(rawBytes, bytes, enc, cInv, cSeed, cStep, b64, alpha, padByte) {
    const lut = {};
    for (let i = 0; i < 64; i++)
        lut[alpha.charCodeAt(i)] = i;
    lut[padByte] = 0;
    const decoded = [];
    for (let i = 0; i < b64.length; i += 4) {
        const p1 = b64.charCodeAt(i), p2 = b64.charCodeAt(i + 1), p3 = b64.charCodeAt(i + 2), p4 = b64.charCodeAt(i + 3);
        const a = lut[p1], b = lut[p2], c = lut[p3], d = lut[p4];
        decoded.push(((a << 2) | (b >> 4)) & 0xFF);
        if (p3 !== padByte)
            decoded.push((((b << 4) | (c >> 2)) & 0xFF));
        if (p4 !== padByte)
            decoded.push((((c << 6) | d) & 0xFF));
    }
    const decrypted = [];
    for (let i = 0; i < decoded.length; i++) {
        decrypted.push(cInv[decoded[i]] ^ ((cSeed + i * cStep) & 0xFF));
    }
    if (decrypted.length !== bytes.length) {
        throw new Error(`[cipher-verify] Length mismatch: decoded ${decrypted.length} vs original ${bytes.length}`);
    }
    for (let i = 0; i < bytes.length; i++) {
        if (decrypted[i] !== bytes[i]) {
            throw new Error(`[cipher-verify] Byte mismatch at ${i}: decoded ${decrypted[i]} vs original ${bytes[i]}`);
        }
    }
    const flag = bytes[0];
    let rleOut;
    if (flag === 0) {
        rleOut = bytes.slice(1);
    }
    else {
        rleOut = [];
        let rp = 1;
        while (rp < bytes.length) {
            const rb = bytes[rp];
            if (rb === 0xFF) {
                rp++;
                const rn = bytes[rp];
                if (rn === 0) {
                    rleOut.push(0xFF);
                }
                else {
                    rp++;
                    const rv = bytes[rp];
                    for (let ri = 0; ri < rn + 3; ri++)
                        rleOut.push(rv);
                }
            }
            else {
                rleOut.push(rb);
            }
            rp++;
        }
    }
    let finalBytes;
    if (flag === 0) {
        finalBytes = rleOut;
    }
    else {
        finalBytes = [];
        let lp = 0;
        while (lp < rleOut.length) {
            const ct = rleOut[lp];
            lp++;
            if (ct < 128) {
                const n = ct + 1;
                for (let j = 0; j < n; j++) {
                    finalBytes.push(rleOut[lp]);
                    lp++;
                }
            }
            else if (ct < 192) {
                const ll = ct - 124;
                const lo = rleOut[lp] + 1;
                lp++;
                const ls = finalBytes.length;
                for (let j = 1; j <= ll; j++)
                    finalBytes.push(finalBytes[ls - lo + j - 1]);
            }
            else {
                const ll = ct - 188;
                const lo = rleOut[lp] * 256 + rleOut[lp + 1];
                lp += 2;
                const ls = finalBytes.length;
                for (let j = 1; j <= ll; j++)
                    finalBytes.push(finalBytes[ls - lo + j - 1]);
            }
        }
    }
    if (finalBytes.length !== rawBytes.length) {
        throw new Error(`[cipher-verify] Final length mismatch: ${finalBytes.length} vs ${rawBytes.length}`);
    }
    for (let i = 0; i < rawBytes.length; i++) {
        if (finalBytes[i] !== rawBytes[i]) {
            throw new Error(`[cipher-verify] Final byte mismatch at ${i}: ${finalBytes[i]} vs ${rawBytes[i]}`);
        }
    }
}
function wrapCustomCipher(source, layerOpts) {
    const rawBytes = toUTF8Bytes(source);
    const tamperPrime = [65521, 65519, 65497, 65479, 65449, 65437, 65423, 65413, 65393, 65381, 65371, 65357][Math.floor(rng() * 12)];
    let tamperChecksum = 0;
    for (let i = 0; i < rawBytes.length; i++) {
        tamperChecksum = (tamperChecksum + rawBytes[i]) % tamperPrime;
    }
    const lzBytes = lzssCompress(rawBytes);
    const compBytes = rleCompress(lzBytes);
    const useCompression = compBytes.length < rawBytes.length * 0.95;
    const bytes = useCompression ? [1, ...compBytes] : [0, ...rawBytes];
    const compRatio = ((1 - bytes.length / rawBytes.length) * 100).toFixed(1);
    const expectedDecompLen = rawBytes.length;
    console.log(`[cipher] LZSS+RLE: ${rawBytes.length} → ${bytes.length} (${compRatio}% ${useCompression ? 'compressed' : 'raw-passthrough'})`);
    const { sbox: cSbox, inverse: cInv } = generateSBox();
    const cSeed = 1 + Math.floor(rng() * 254);
    const cStep = 3 + Math.floor(rng() * 30);
    const enc = new Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) {
        enc[i] = cSbox[bytes[i] ^ ((cSeed + i * cStep) & 0xFF)];
    }
    const pool = [];
    for (let cc = 33; cc <= 126; cc++) {
        if (cc === 34 || cc === 92)
            continue;
        pool.push(String.fromCharCode(cc));
    }
    for (let i = pool.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    const alpha = pool.slice(0, 64).join('');
    const padChar = pool[64];
    const padByte = padChar.charCodeAt(0);
    let b64 = '';
    for (let i = 0; i < enc.length; i += 3) {
        const a = enc[i], b = enc[i + 1] ?? 0, c = enc[i + 2] ?? 0;
        b64 += alpha[a >> 2];
        b64 += alpha[((a & 3) << 4) | (b >> 4)];
        b64 += (i + 1 < enc.length) ? alpha[((b & 15) << 2) | (c >> 6)] : padChar;
        b64 += (i + 2 < enc.length) ? alpha[c & 63] : padChar;
    }
    verifyCipherRoundtrip(rawBytes, bytes, enc, cInv, cSeed, cStep, b64, alpha, padByte);
    const nFrags = 3 + Math.floor(rng() * 3);
    const fragSize = Math.ceil(b64.length / nFrags);
    const frags = [];
    for (let i = 0; i < nFrags; i++) {
        frags.push(b64.slice(i * fragSize, (i + 1) * fragSize));
    }
    const ccArgs = (s, allowBit32 = false) => Array.from(s).map(c => {
        const code = c.charCodeAt(0);
        const maxMethod = allowBit32 ? 5 : 4;
        const method = Math.floor(rng() * maxMethod);
        if (method === 0) {
            const d = 1 + Math.floor(rng() * 50);
            return `${code - d}+${d}`;
        }
        if (method === 1) {
            const d = 1 + Math.floor(rng() * 50);
            return `${code + d}-${d}`;
        }
        if (method === 2) {
            const m = [2, 3, 4, 5][Math.floor(rng() * 4)];
            return `${code / m === Math.floor(code / m) ? `${code / m}*${m}` : `${code}`}`;
        }
        if (method === 3) {
            const x = Math.floor(rng() * 256);
            return `${nBxor}(${code ^ x},${x})`;
        }
        return `${code}`;
    }).join(',');
    const nCh = randomName(3);
    const nBy = randomName(3);
    const nSb = randomName(3);
    const nEv = randomName(3);
    const nTb = randomName(3);
    const nLd = randomName(3);
    const nBt = randomName(3);
    const nLUT = randomName(3);
    const nAl = randomName(3);
    const nDt = randomName(3);
    const nRaw = randomName(3);
    const nCnt = randomName(2);
    const nIv = randomName(3);
    const nOut = randomName(3);
    const nBxor = randomName(3);
    const nBand = randomName(3);
    const nBor = randomName(3);
    const nLsh = randomName(3);
    const nRsh = randomName(3);
    const bxorAliases = [nBxor, randomName(3), randomName(3)];
    const chAliases = [nCh, randomName(3), randomName(3)];
    const fragNames = frags.map(() => randomName(4));
    const L = [];
    let latePcall = '';
    const honeyVars = [];
    const rInt = () => {
        const val = Math.floor(rng() * 65536);
        const fmt = (val * 7 + 3) % 5;
        if (fmt === 0)
            return `0x${val.toString(16)}`;
        if (fmt === 1 && val > 5) {
            const d = (val % 97) + 1;
            return `(${val + d}-${d})`;
        }
        if (fmt === 2 && val > 20) {
            const f = [2, 3, 5, 7, 11, 13][(val >> 3) % 6];
            const q = Math.floor(val / f);
            const r = val - q * f;
            return r ? `(${q}*${f}+${r})` : `(${q}*${f})`;
        }
        if (fmt === 3 && val > 255)
            return `(0x${(val >> 8).toString(16)}*256+${val & 0xFF})`;
        return `${val}`;
    };
    const rByte = () => {
        const val = Math.floor(rng() * 256);
        const fmt = (val * 13 + 7) % 4;
        if (fmt === 0)
            return `0x${val.toString(16)}`;
        if (fmt === 1 && val > 3) {
            const d = (val % 29) + 1;
            return `(${val + d}-${d})`;
        }
        if (fmt === 2)
            return `0x${val.toString(16).padStart(2, '0')}`;
        return `${val}`;
    };
    const rArr = (n) => Array.from({ length: n }, () => {
        const val = Math.floor(rng() * 256);
        const fmt = (val * 11 + 5) % 4;
        if (fmt === 0)
            return `0x${val.toString(16)}`;
        if (fmt === 1 && val > 5) {
            const d = (val % 19) + 1;
            return `${val + d}-${d}`;
        }
        if (fmt === 2)
            return `0x${val.toString(16).padStart(2, '0')}`;
        return `${val}`;
    }).join(',');
    let _mod16Ctr = 0;
    const polyMod16 = () => {
        const v = _mod16Ctr++ % 6;
        if (v === 0)
            return '65536';
        if (v === 1)
            return '0x10000';
        if (v === 2)
            return '(256*256)';
        if (v === 3)
            return '(0x100*256)';
        if (v === 4)
            return '(128*512)';
        return '(0x80*0x200)';
    };
    const emitHoneypot = () => {
        const variant = Math.floor(rng() * 10);
        const v = randomName(3);
        honeyVars.push(v);
        switch (variant) {
            case 0:
                L.push(`local ${v}={${rArr(16 + Math.floor(rng() * 48))}}`);
                break;
            case 1: {
                const a = rInt(), b = rInt(), c = rInt();
                L.push(`local ${v}=${nBxor}(${nBand}(${a},0xFF),${nRsh}(${b},${2 + Math.floor(rng() * 6)}))+${c}`);
                break;
            }
            case 2: {
                const n = randomName(2);
                const iters = 4 + Math.floor(rng() * 12);
                const mul = 1 + Math.floor(rng() * 7);
                const add = Math.floor(rng() * 256);
                L.push(`local ${v}=${rInt()};for ${n}=1,${iters} do ${v}=${nBand}(${v}*${mul}+${add},0xFFFF) end`);
                break;
            }
            case 3: {
                const ref = honeyVars.length > 1 ? honeyVars[Math.floor(rng() * (honeyVars.length - 1))] : `${rInt()}`;
                L.push(`local ${v};if type(${ref})=="number" then ${v}=${nBxor}(${ref},${rInt()}) else ${v}=${rInt()} end`);
                break;
            }
            case 4: {
                const t1 = honeyVars.length > 1 ? honeyVars[Math.floor(rng() * (honeyVars.length - 1))] : `{${rArr(8)}}`;
                L.push(`local ${v}={};if type(${t1})=="table" then for _k=1,#${t1} do ${v}[_k]=${nBxor}(${t1}[_k],${rByte()}) end end`);
                break;
            }
            case 5: {
                const a = rInt(), b = rByte(), c = rByte();
                L.push(`local ${v}=${a};do ${v}=${nBor}(${nLsh}(${nBand}(${v},0xF),4),${b});${v}=${nBxor}(${v},${c}) end`);
                break;
            }
            case 6: {
                const ref = fragNames.length > 0 ? fragNames[Math.floor(rng() * fragNames.length)] : `""`;
                const pos = 1 + Math.floor(rng() * 100);
                L.push(`local ${v}=(type(${ref})=="string" and #${ref}>${pos}) and ${nBy}(${ref},${pos}) or ${rByte()}`);
                break;
            }
            case 7: {
                const vals = Array.from({ length: 3 + Math.floor(rng() * 3) }, () => rInt());
                let expr = `${vals[0]}`;
                for (let i = 1; i < vals.length; i++)
                    expr = `${nBxor}(${expr},${vals[i]})`;
                L.push(`local ${v}=${expr}`);
                break;
            }
            case 8: {
                const a = rInt(), b = 3 + Math.floor(rng() * 13), c = rInt();
                L.push(`local ${v}=(${a}*${b}+${c})%${251 + Math.floor(rng() * 5)}`);
                break;
            }
            case 9: {
                const ref = honeyVars.length > 1 ? honeyVars[Math.floor(rng() * (honeyVars.length - 1))] : `${rInt()}`;
                if (latePcall) {
                    L.push(`local ${v}=${latePcall}(function() return ${nBand}(${ref}+${rInt()},0xFFFF) end) and ${rInt()} or ${rInt()}`);
                }
                else {
                    L.push(`local ${v}=${nBxor}(${rInt()},${rByte()})`);
                }
                break;
            }
        }
    };
    const honeypots = (n) => { for (let i = 0; i < n; i++)
        emitHoneypot(); };
    const emitPreBootDead = () => {
        const variant = Math.floor(rng() * 22);
        const v = randomName(3);
        honeyVars.push(v);
        switch (variant) {
            case 0: {
                const n2 = randomName(2), iters = 3 + Math.floor(rng() * 10);
                L.push(`local ${v}=${rInt()};for ${n2}=1,${iters} do ${v}=(${v}*${2 + Math.floor(rng() * 6)}+${rByte()})%${polyMod16()} end`);
                break;
            }
            case 1: {
                L.push(`local ${v}={};for ${randomName(1)}=1,${3 + Math.floor(rng() * 8)} do ${v}[#${v}+1]=${rByte()} end`);
                break;
            }
            case 2: {
                const ops = ['+', '-', '*'];
                const op = ops[Math.floor(rng() * 3)];
                L.push(`local ${v}=(${rInt()}${op}${rInt()})%${251 + Math.floor(rng() * 5)}`);
                break;
            }
            case 3: {
                const ref = honeyVars.length > 1 ? honeyVars[Math.floor(rng() * (honeyVars.length - 1))] : `${rInt()}`;
                L.push(`local ${v};if type(${ref})=="number" then ${v}=${ref}+${rInt()} else ${v}=${rInt()} end`);
                break;
            }
            case 4: {
                const v2 = randomName(2), v3 = randomName(2);
                L.push(`do local ${v2}=${rInt()};local ${v3}=${rInt()};local ${v}=(${v2}+${v3})%${251 + Math.floor(rng() * 5)} end`);
                break;
            }
            case 5: {
                L.push(`local ${v}={${rArr(8 + Math.floor(rng() * 32))}}`);
                break;
            }
            case 6: {
                const n2 = randomName(2);
                L.push(`local ${v}=${rInt()};local ${n2}=0;while ${n2}<${3 + Math.floor(rng() * 6)} do ${v}=(${v}+${rByte()})%${polyMod16()};${n2}=${n2}+1 end`);
                break;
            }
            case 7: {
                const n2 = randomName(2);
                L.push(`local ${v}=${rInt()};local ${n2}=0;repeat ${v}=(${v}*${2 + Math.floor(rng() * 4)}+${rByte()})%${polyMod16()};${n2}=${n2}+1 until ${n2}>=${3 + Math.floor(rng() * 5)}`);
                break;
            }
            case 8: {
                L.push(`local ${v}=type(${rInt()})~="string" and ${rInt()} or ${rInt()}`);
                break;
            }
            case 9: {
                const v2 = randomName(2);
                L.push(`local ${v}=${rInt()};do local ${v2}=${rInt()};if ${v}>${v2} then ${v}=${v}-${v2} else ${v}=${v}+${v2} end end`);
                break;
            }
            case 10: {
                const n2 = randomName(2), seed = rInt(), mul = 3 + Math.floor(rng() * 5);
                L.push(`local ${v}=${seed};local ${n2}=1;while ${n2}<=${4 + Math.floor(rng() * 8)} do ${v}=(${v}*${mul}+${n2})%${polyMod16()};${n2}=${n2}+1 end`);
                break;
            }
            case 11: {
                const v2 = randomName(2), v3 = randomName(2);
                L.push(`local ${v}=${rInt()};local ${v2}=${rInt()};local ${v3}=0;for ${randomName(1)}=1,${3 + Math.floor(rng() * 5)} do ${v3}=${v3}+(${v}+${v2})%${251 + Math.floor(rng() * 5)};${v}=(${v}+${rByte()})%${polyMod16()} end`);
                break;
            }
            case 12: {
                const n2 = randomName(1), n3 = randomName(1);
                L.push(`local ${v}=0;for ${n2}=1,${2 + Math.floor(rng() * 3)} do for ${n3}=1,${2 + Math.floor(rng() * 3)} do ${v}=${v}+${n2}*${n3} end end`);
                break;
            }
            case 13: {
                const ref = honeyVars.length > 1 ? honeyVars[Math.floor(rng() * (honeyVars.length - 1))] : `${rInt()}`;
                L.push(`local ${v}=${rInt()};if ${v}>${rInt()} then ${v}=${v}-${rByte()} elseif type(${ref})=="number" then ${v}=${v}+${rByte()} else ${v}=0 end`);
                break;
            }
            case 14: {
                const v2 = randomName(2), limit = 4 + Math.floor(rng() * 8);
                L.push(`local ${v}=${rInt()};local ${v2}=${rInt()};for ${randomName(1)}=1,${limit} do if ${v}>${v2} then ${v}=(${v}-${v2})%${polyMod16()} else ${v}=(${v}+${v2})%${polyMod16()} end end`);
                break;
            }
            case 15: {
                const a = rInt(), b = 3 + Math.floor(rng() * 13), c = rInt();
                L.push(`local ${v}=(${a}*${b}+${c})%${251 + Math.floor(rng() * 5)};${v}=(${v}*${v}+${rByte()})%${polyMod16()}`);
                break;
            }
            case 16: {
                const t = randomName(2), len = 4 + Math.floor(rng() * 6), idx = randomName(1);
                L.push(`local ${t}={${rArr(len)}};local ${v}=0;for ${idx}=1,${len} do ${v}=${v}+${t}[${idx}] end`);
                break;
            }
            case 17: {
                const base = 2 + Math.floor(rng() * 8), exp = 2 + Math.floor(rng() * 4);
                L.push(`local ${v}=${rInt()};for ${randomName(1)}=1,${exp} do ${v}=(${v}*${base}+${rByte()})%${polyMod16()} end`);
                break;
            }
            case 18: {
                const v2 = randomName(2), v3 = randomName(2);
                L.push(`local ${v},${v2},${v3}=${rInt()},${rInt()},${rInt()};${v},${v2}=${v2},${v}`);
                break;
            }
            case 19: {
                const n2 = randomName(2);
                L.push(`local ${v}=${rInt()};local ${n2}=0;while true do ${v}=(${v}+${rByte()})%${polyMod16()};${n2}=${n2}+1;if ${n2}>=${2 + Math.floor(rng() * 6)} then break end end`);
                break;
            }
            case 20: {
                const t = randomName(2), len = 3 + Math.floor(rng() * 5), idx1 = randomName(1), idx2 = randomName(1);
                L.push(`local ${t}={};for ${idx1}=1,${len} do ${t}[#${t}+1]=${rByte()} end;local ${v}=0;for ${idx2}=1,#${t} do ${v}=(${v}+${t}[${idx2}])%${polyMod16()} end`);
                break;
            }
            case 21: {
                const v2 = randomName(2), v3 = randomName(2);
                const a = rInt(), b = rInt();
                L.push(`local ${v}=${a};local ${v2}=${b};local ${v3};if ${v}>${v2} then ${v3}=${v}-${v2} else ${v3}=${v2}-${v} end;${v}=(${v3}*${2 + Math.floor(rng() * 6)}+${rByte()})%${polyMod16()}`);
                break;
            }
        }
    };
    const preBootCount = 2 + Math.floor(rng() * 3);
    for (let pb = 0; pb < preBootCount; pb++)
        emitPreBootDead();
    const emitSafeHoneypot = () => {
        const variant = Math.floor(rng() * 6);
        const v = randomName(3);
        honeyVars.push(v);
        switch (variant) {
            case 0:
                L.push(`local ${v}={${rArr(8 + Math.floor(rng() * 24))}}`);
                break;
            case 1: {
                const a = rInt(), b = 3 + Math.floor(rng() * 13), c = rInt();
                L.push(`local ${v}=(${a}*${b}+${c})%${251 + Math.floor(rng() * 5)}`);
                break;
            }
            case 2: {
                const n2 = randomName(2), iters = 4 + Math.floor(rng() * 8);
                L.push(`local ${v}=${rInt()};for ${n2}=1,${iters} do ${v}=(${v}*${3 + Math.floor(rng() * 5)}+${rByte()})%${polyMod16()} end`);
                break;
            }
            case 3: {
                const ref = honeyVars.length > 1 ? honeyVars[Math.floor(rng() * (honeyVars.length - 1))] : `${rInt()}`;
                L.push(`local ${v};if type(${ref})=="number" then ${v}=${ref}+${rInt()} else ${v}=${rInt()} end`);
                break;
            }
            case 4: {
                const codes = Array.from({ length: 3 + Math.floor(rng() * 5) }, () => 65 + Math.floor(rng() * 26));
                L.push(`local ${v}=${nCh}(${codes.join(",")})`);
                break;
            }
            case 5: {
                L.push(`local ${v}={};for ${randomName(1)}=1,${4 + Math.floor(rng() * 12)} do ${v}[#${v}+1]=${rByte()} end`);
                break;
            }
        }
    };
    const safeHoneypots = (n) => { for (let i = 0; i < n; i++)
        emitSafeHoneypot(); };
    const polyLuaEsc = (s) => {
        const escaped = Array.from(s).map(c => {
            const code = c.charCodeAt(0);
            const fmt = Math.floor(rng() * 3);
            if (fmt === 0)
                return `\\${code}`;
            if (fmt === 1)
                return `\\${code.toString().padStart(3, '0')}`;
            return `\\${code}`;
        }).join('');
        return `"${escaped}"`;
    };
    const charPatterns = [
        () => `("")[${polyLuaEsc("char")}]`,
        () => `((nil or "")[${polyLuaEsc("char")}])`,
        () => `((false or "")[${polyLuaEsc("char")}])`,
        () => `(("" or "")[${polyLuaEsc("char")}])`,
        () => `(true and "" or nil)[${polyLuaEsc("char")}]`,
        () => `(function() return "" end)()[${polyLuaEsc("char")}]`,
        () => `({[1]=""})[1][${polyLuaEsc("char")}]`,
        () => `(select(1,""))[${polyLuaEsc("char")}]`,
    ];
    const lsCharCodes = (chVar) => {
        return Array.from("loadstring").map(c => {
            const code = c.charCodeAt(0);
            const m = Math.floor(rng() * 4);
            if (m === 0) {
                const d = 1 + Math.floor(rng() * 30);
                return `${code - d}+${d}`;
            }
            if (m === 1) {
                const d = 1 + Math.floor(rng() * 30);
                return `${code + d}-${d}`;
            }
            if (m === 2)
                return `0x${code.toString(16)}`;
            return `${code}`;
        }).join(',');
    };
    const encodedLsExpr = (chVar) => {
        const codes = lsCharCodes(chVar);
        const gfLocal = randomName(2);
        const fnCodes = Array.from("function").map(c => {
            const code = c.charCodeAt(0);
            const m = Math.floor(rng() * 4);
            if (m === 0) {
                const d = 1 + Math.floor(rng() * 30);
                return `${code - d}+${d}`;
            }
            if (m === 1) {
                const d = 1 + Math.floor(rng() * 30);
                return `${code + d}-${d}`;
            }
            if (m === 2)
                return `0x${code.toString(16)}`;
            return `${code}`;
        }).join(',');
        const envExpr = `(function() local ${gfLocal}=getfenv;return (type(${gfLocal})==${chVar}(${fnCodes}) and ${gfLocal}(0) or _G) end)()`;
        const p = Math.floor(rng() * 3);
        if (p === 0)
            return `${envExpr}[${chVar}(${codes})]`;
        if (p === 1)
            return `(function() local _e=${envExpr};return _e end)()[${chVar}(${codes})]`;
        return `({[0]=${envExpr}})[0][${chVar}(${codes})]`;
    };
    const bootVariant = Math.floor(rng() * 4);
    const nLdBoot = randomName(3);
    if (bootVariant === 0) {
        L.push(`local ${nCh}=${charPatterns[Math.floor(rng() * charPatterns.length)]()}`);
        L.push(`local ${nLdBoot}=${encodedLsExpr(nCh)}`);
        safeHoneypots(1 + Math.floor(rng() * 2));
    }
    else if (bootVariant === 1) {
        L.push(`local ${nCh}=${charPatterns[Math.floor(rng() * charPatterns.length)]()}`);
        if (rng() > 0.5)
            emitPreBootDead();
        L.push(`local ${nLdBoot}=${encodedLsExpr(nCh)}`);
        safeHoneypots(1 + Math.floor(rng() * 2));
    }
    else if (bootVariant === 2) {
        L.push(`local ${nCh},${nLdBoot}`);
        emitPreBootDead();
        L.push(`do ${nCh}=${charPatterns[Math.floor(rng() * charPatterns.length)]()};${nLdBoot}=${encodedLsExpr(nCh)} end`);
        safeHoneypots(1 + Math.floor(rng() * 2));
    }
    else {
        emitPreBootDead();
        L.push(`local ${nCh}=${charPatterns[Math.floor(rng() * charPatterns.length)]()}`);
        emitPreBootDead();
        L.push(`local ${nLdBoot}=${encodedLsExpr(nCh)}`);
        emitPreBootDead();
    }
    const vmKey = 1 + Math.floor(rng() * 254);
    const encodeVmStr = (s) => '{' + Array.from(s).map(c => {
        const enc = (c.charCodeAt(0) + vmKey) % 256;
        const m2 = Math.floor(rng() * 3);
        if (m2 === 0)
            return `${enc}`;
        if (m2 === 1) {
            const d = 1 + Math.floor(rng() * 20);
            return `${enc - d}+${d}`;
        }
        return `0x${enc.toString(16).padStart(2, '0')}`;
    }).join(',') + '}';
    const vmDk = randomName(3), vmProg = randomName(3), vmRes = randomName(3);
    const vmPc = randomName(2), vmIns = randomName(2), vmOp = randomName(2);
    const vmEs = randomName(2), vmDkArg = randomName(2);
    const vmDkTmp = randomName(2), vmDkI = randomName(2);
    const dkVariant = Math.floor(rng() * 3);
    if (dkVariant === 0) {
        L.push(`local ${vmDk}=function(${vmDkArg}) local ${vmDkTmp}="" for ${vmDkI}=1,#${vmDkArg} do ${vmDkTmp}=${vmDkTmp}..${nCh}((${vmDkArg}[${vmDkI}]-${vmKey})%256) end return ${vmDkTmp} end`);
    }
    else if (dkVariant === 1) {
        const vmDkArr = randomName(2);
        L.push(`local ${vmDk}=function(${vmDkArg}) local ${vmDkArr}={} for ${vmDkI}=1,#${vmDkArg} do ${vmDkArr}[${vmDkI}]=${nCh}((${vmDkArg}[${vmDkI}]-${vmKey})%256) end local ${vmDkTmp}="" for ${vmDkI}=1,#${vmDkArr} do ${vmDkTmp}=${vmDkTmp}..${vmDkArr}[${vmDkI}] end return ${vmDkTmp} end`);
    }
    else {
        L.push(`local ${vmDk}=function(${vmDkArg}) local ${vmDkTmp}="" local ${vmDkI}=0 while ${vmDkI}<#${vmDkArg} do ${vmDkI}=${vmDkI}+1;${vmDkTmp}=${vmDkTmp}..${nCh}((${vmDkArg}[${vmDkI}]-${vmKey})%256) end return ${vmDkTmp} end`);
    }
    safeHoneypots(1);
    const keyEntries = [
        { name: "byte", varN: randomName(3), encoded: encodeVmStr("byte") },
        { name: "sub", varN: randomName(3), encoded: encodeVmStr("sub") },
        { name: "function", varN: randomName(3), encoded: encodeVmStr("function") },
        { name: "table", varN: randomName(3), encoded: encodeVmStr("table") },
        { name: "loadstring", varN: randomName(3), encoded: encodeVmStr("loadstring") },
        { name: "load", varN: randomName(3), encoded: encodeVmStr("load") },
        { name: "bit32", varN: randomName(3), encoded: encodeVmStr("bit32") },
        { name: "rawset", varN: randomName(3), encoded: encodeVmStr("rawset") },
        { name: "rawget", varN: randomName(3), encoded: encodeVmStr("rawget") },
        { name: "type", varN: randomName(3), encoded: encodeVmStr("type") },
        { name: "pcall", varN: randomName(3), encoded: encodeVmStr("pcall") },
        { name: "game", varN: randomName(3), encoded: encodeVmStr("game") },
        { name: "script", varN: randomName(3), encoded: encodeVmStr("script") },
        { name: "getfenv", varN: randomName(3), encoded: encodeVmStr("getfenv") },
        { name: "concat", varN: randomName(3), encoded: encodeVmStr("concat") },
        { name: "Workspace", varN: randomName(3), encoded: encodeVmStr("Workspace") },
    ];
    const kn = (nm) => keyEntries.find(e => e.name === nm).varN;
    const keyOrder = keyEntries.map((_, i) => i);
    for (let i = keyOrder.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [keyOrder[i], keyOrder[j]] = [keyOrder[j], keyOrder[i]];
    }
    for (const idx of keyOrder) {
        L.push(`local ${keyEntries[idx].varN}=${keyEntries[idx].encoded}`);
        if (rng() > 0.5)
            safeHoneypots(1);
    }
    safeHoneypots(1);
    const opPool = Array.from({ length: 30 }, (_, i) => i + 1);
    for (let i = opPool.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [opPool[i], opPool[j]] = [opPool[j], opPool[i]];
    }
    const OP_STR = opPool[0];
    const OP_ENV = opPool[1];
    const OP_IDX = opPool[2];
    const OP_IOR = opPool[3];
    const OP_NOP = opPool[4];
    const strOps = [
        `{${OP_STR},1,${kn("byte")}}`,
        `{${OP_STR},2,${kn("sub")}}`,
    ];
    if (rng() > 0.5)
        [strOps[0], strOps[1]] = [strOps[1], strOps[0]];
    const envOp = `{${OP_ENV},3,${kn("getfenv")}}`;
    const globOps = [
        `{${OP_IDX},4,3,${kn("table")}}`,
        `{${OP_IOR},5,3,${kn("loadstring")},${kn("load")}}`,
        `{${OP_IDX},6,3,${kn("bit32")}}`,
        `{${OP_IDX},7,3,${kn("rawset")}}`,
        `{${OP_IDX},8,3,${kn("rawget")}}`,
        `{${OP_IDX},9,3,${kn("type")}}`,
        `{${OP_IDX},10,3,${kn("pcall")}}`,
        `{${OP_IDX},11,3,${kn("game")}}`,
        `{${OP_IDX},12,3,${kn("script")}}`,
    ];
    for (let i = globOps.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [globOps[i], globOps[j]] = [globOps[j], globOps[i]];
    }
    const nopInstr = () => `{${OP_NOP},${20 + Math.floor(rng() * 10)},${rByte()}}`;
    const progEntries = [];
    if (rng() > 0.5)
        progEntries.push(nopInstr());
    for (const op of strOps) {
        progEntries.push(op);
        if (rng() > 0.5)
            progEntries.push(nopInstr());
    }
    progEntries.push(envOp);
    if (rng() > 0.5)
        progEntries.push(nopInstr());
    for (const op of globOps) {
        progEntries.push(op);
        if (rng() > 0.5)
            progEntries.push(nopInstr());
    }
    L.push(`local ${vmProg}={${progEntries.join(",")}}`);
    if (rng() > 0.5)
        safeHoneypots(1);
    L.push(`local ${vmRes}={}`);
    L.push(`local ${vmEs}=""`);
    const cases = [
        { op: OP_STR, code: `${vmRes}[${vmIns}[2]]=${vmEs}[${vmDk}(${vmIns}[3])]` },
        { op: OP_ENV, code: (() => {
                const envSrc = `return (type(getfenv)=='function' and getfenv(0)) or _G`;
                const envCodes = Array.from(envSrc).map(c => {
                    const code = c.charCodeAt(0);
                    const m = Math.floor(rng() * 3);
                    if (m === 0) {
                        const d = 1 + Math.floor(rng() * 50);
                        return `${code - d}+${d}`;
                    }
                    if (m === 1) {
                        const d = 1 + Math.floor(rng() * 50);
                        return `${code + d}-${d}`;
                    }
                    return `${code}`;
                }).join(',');
                return `${vmRes}[${vmIns}[2]]=${nLdBoot}(${nCh}(${envCodes}))()`;
            })() },
        { op: OP_IDX, code: `${vmRes}[${vmIns}[2]]=${vmRes}[${vmIns}[3]][${vmDk}(${vmIns}[4])]` },
        { op: OP_IOR, code: `${vmRes}[${vmIns}[2]]=${vmRes}[${vmIns}[3]][${vmDk}(${vmIns}[4])] or ${vmRes}[${vmIns}[3]][${vmDk}(${vmIns}[5])]` },
        { op: OP_NOP, code: `${vmRes}[${vmIns}[2]]=${vmIns}[3]` },
    ];
    for (let i = cases.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [cases[i], cases[j]] = [cases[j], cases[i]];
    }
    let ifChain = `if ${vmOp}==${cases[0].op} then ${cases[0].code}`;
    for (let i = 1; i < cases.length; i++) {
        ifChain += ` elseif ${vmOp}==${cases[i].op} then ${cases[i].code}`;
    }
    ifChain += ` end`;
    const loopVariant = Math.floor(rng() * 3);
    if (loopVariant === 0) {
        L.push(`for ${vmPc}=1,#${vmProg} do local ${vmIns}=${vmProg}[${vmPc}];local ${vmOp}=${vmIns}[1];${ifChain} end`);
    }
    else if (loopVariant === 1) {
        L.push(`local ${vmPc}=1;while ${vmPc}<=#${vmProg} do local ${vmIns}=${vmProg}[${vmPc}];local ${vmOp}=${vmIns}[1];${ifChain};${vmPc}=${vmPc}+1 end`);
    }
    else {
        L.push(`local ${vmPc}=0;repeat ${vmPc}=${vmPc}+1;local ${vmIns}=${vmProg}[${vmPc}];local ${vmOp}=${vmIns}[1];${ifChain} until ${vmPc}>=#${vmProg}`);
    }
    safeHoneypots(1);
    L.push(`local ${nBy}=${vmRes}[1]`);
    L.push(`local ${nSb}=${vmRes}[2]`);
    L.push(`local ${nEv}=${vmRes}[3]`);
    L.push(`local ${nTb}=${vmRes}[4]`);
    L.push(`local ${nLd}=${vmRes}[5]`);
    L.push(`local ${nBt}=${vmRes}[6]`);
    const nRawSet = randomName(3);
    const nRawGet = randomName(3);
    L.push(`local ${nRawSet}=${vmRes}[7]`);
    L.push(`local ${nRawGet}=${vmRes}[8]`);
    const nCType = randomName(3);
    const nCPcall = randomName(3);
    const nCGame = randomName(3);
    const nCScript = randomName(3);
    L.push(`local ${nCType}=${vmRes}[9]`);
    L.push(`local ${nCPcall}=${vmRes}[10]`);
    latePcall = nCPcall;
    L.push(`local ${nCGame}=${vmRes}[11]`);
    L.push(`local ${nCScript}=${vmRes}[12]`);
    L.push(`local ${nBxor}=${nBt}[${vmDk}(${encodeVmStr("bxor")})]`);
    L.push(`local ${nBand}=${nBt}[${vmDk}(${encodeVmStr("band")})]`);
    L.push(`local ${nBor}=${nBt}[${vmDk}(${encodeVmStr("bor")})]`);
    L.push(`local ${nLsh}=${nBt}[${vmDk}(${encodeVmStr("lshift")})]`);
    L.push(`local ${nRsh}=${nBt}[${vmDk}(${encodeVmStr("rshift")})]`);
    L.push(`local ${bxorAliases[1]}=${nBxor};local ${bxorAliases[2]}=${nBxor}`);
    L.push(`local ${chAliases[1]}=${nCh};local ${chAliases[2]}=${nCh}`);
    const aliasInsertIdx = L.length;
    const nConcat = randomName(3);
    L.push(`local ${nConcat}=${nTb}[${vmDk}(${encodeVmStr("concat")})]`);
    const nTU = randomName(3);
    L.push(`local ${nTU}=${nTb}[${vmDk}(${encodeVmStr("unpack")})]`);
    const nTw = randomName(2);
    L.push(`local ${nTw};do local _t=${nEv}[${vmDk}(${encodeVmStr("task")})] if _t then ${nTw}=_t[${vmDk}(${encodeVmStr("wait")})] end end`);
    honeypots(1 + Math.floor(rng() * 2));
    const fragRotKey = 1 + Math.floor(rng() * 93);
    const fragOrder = frags.map((_, i) => i);
    for (let i = fragOrder.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [fragOrder[i], fragOrder[j]] = [fragOrder[j], fragOrder[i]];
    }
    for (const idx of fragOrder) {
        if (rng() > 0.4)
            honeypots(1);
        L.push(`local ${fragNames[idx]}=${luaStr(frags[idx])}`);
    }
    honeypots(1);
    const chunks = [cInv.slice(0, 64), cInv.slice(64, 128), cInv.slice(128, 192), cInv.slice(192)];
    const chunkNames = [randomName(3), randomName(3), randomName(3), randomName(3)];
    const chunkKeys = [1 + Math.floor(rng() * 254), 1 + Math.floor(rng() * 254), 1 + Math.floor(rng() * 254), 1 + Math.floor(rng() * 254)];
    const chunkOrder = [0, 1, 2, 3];
    for (let i = 3; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [chunkOrder[i], chunkOrder[j]] = [chunkOrder[j], chunkOrder[i]];
    }
    for (const idx of chunkOrder) {
        const encoded = chunks[idx].map(v => v ^ chunkKeys[idx]);
        L.push(`local ${chunkNames[idx]}={${encoded.join(",")}}`);
        if (rng() > 0.5)
            honeypots(1);
    }
    honeypots(1);
    const alphaXorKey = 1 + Math.floor(rng() * 254);
    const alphaCodes = Array.from(alpha).map(c => (c.charCodeAt(0) ^ alphaXorKey)).join(',');
    const nGuard = randomName(3);
    const nTmpChk = randomName(2);
    const hookByte = 65 + Math.floor(rng() * 26);
    const nDec = randomName(3);
    const nRle = randomName(3);
    const nCf = randomName(2);
    const corruptKey = 1 + Math.floor(rng() * 254);
    L.push(`local ${nDt},${nAl},${nLUT},${nCnt},${nIv},${nDec},${nRle},${nOut},${nGuard},${nTmpChk},${nCf}`);
    const nSt = randomName(2);
    const usedSt = new Set();
    const genStId = () => { let id; do {
        id = 1 + Math.floor(rng() * 65534);
    } while (usedSt.has(id)); usedSt.add(id); return id; };
    const ST_INIT = genStId(), ST_DECODE = genStId();
    const ST_RLE = genStId(), ST_LZSS = genStId(), ST_SEC = genStId();
    const ST_EXEC = genStId(), ST_EXIT = genStId();
    const nFakeCount = 2 + Math.floor(rng() * 3);
    const fakeStIds = Array.from({ length: nFakeCount }, () => genStId());
    const cfStates = [];
    cfStates.push({ id: ST_INIT, nextId: ST_DECODE, lines: [
            `${nDt}=${fragNames.join("..")}`,
            `${nAl}={${alphaCodes}}`,
            `${nLUT}={};for _i=1,64 do ${nLUT}[${nBxor}(${nAl}[_i],${alphaXorKey})]=_i-1 end;${nLUT}[${padByte}]=0`,
            (() => {
                const lutVar = Math.floor(rng() * 3);
                if (lutVar === 0) {
                    return `${nIv}={};for _k=1,128 do if _k<=64 then ${nIv}[_k]=${nBxor}(${chunkNames[0]}[_k],${chunkKeys[0]}) else ${nIv}[_k]=${nBxor}(${chunkNames[1]}[_k-64],${chunkKeys[1]}) end end;for _k=1,128 do if _k<=64 then ${nIv}[128+_k]=${nBxor}(${chunkNames[2]}[_k],${chunkKeys[2]}) else ${nIv}[192+_k-64]=${nBxor}(${chunkNames[3]}[_k-64],${chunkKeys[3]}) end end`;
                }
                else if (lutVar === 1) {
                    const cTbl = randomName(2);
                    const kTbl = randomName(2);
                    return `${nIv}={};local ${cTbl}={${chunkNames.join(',')}};local ${kTbl}={${chunkKeys.join(',')}};for _k=0,255 do local _ci=(_k>=192 and 4) or (_k>=128 and 3) or (_k>=64 and 2) or 1;${nIv}[_k+1]=${nBxor}(${cTbl}[_ci][_k-(_ci-1)*64+1],${kTbl}[_ci]) end`;
                }
                else {
                    return `${nIv}={};for _k=1,64 do ${nIv}[_k]=${nBxor}(${chunkNames[0]}[_k],${chunkKeys[0]}) end;for _k=1,64 do ${nIv}[64+_k]=${nBxor}(${chunkNames[1]}[_k],${chunkKeys[1]}) end;for _k=1,64 do ${nIv}[128+_k]=${nBxor}(${chunkNames[2]}[_k],${chunkKeys[2]}) end;for _k=1,64 do ${nIv}[192+_k]=${nBxor}(${chunkNames[3]}[_k],${chunkKeys[3]}) end`;
                }
            })(),
        ] });
    cfStates.push({ id: ST_DECODE, nextId: ST_RLE, lines: [
            `${nDec}={};${nCnt}=0`,
            `for _i=1,#${nDt},4 do`,
            `if _i%${30000 + Math.floor(rng() * 20001)}==1 and ${nTw} then ${nTw}() end`,
            `local _p1,_p2,_p3,_p4=${nBy}(${nDt},_i,_i+3)`,
            `local a,b,c,d=${nLUT}[_p1],${nLUT}[_p2],${nLUT}[_p3],${nLUT}[_p4]`,
            `${nCnt}=${nCnt}+1;${nDec}[${nCnt}]=${nBxor}(${nIv}[${nBor}(${nLsh}(a,2),${nRsh}(b,4))+1],${nBand}(${cSeed}+(${nCnt}-1)*${cStep},0xFF))`,
            `if _p3~=${padByte} then ${nCnt}=${nCnt}+1;${nDec}[${nCnt}]=${nBxor}(${nIv}[${nBand}(${nBor}(${nLsh}(b,4),${nRsh}(c,2)),0xFF)+1],${nBand}(${cSeed}+(${nCnt}-1)*${cStep},0xFF)) end`,
            `if _p4~=${padByte} then ${nCnt}=${nCnt}+1;${nDec}[${nCnt}]=${nBxor}(${nIv}[${nBand}(${nBor}(${nLsh}(c,6),d),0xFF)+1],${nBand}(${cSeed}+(${nCnt}-1)*${cStep},0xFF)) end`,
            `end`,
            `${nCf}=${nDec}[1]`,
        ] });
    cfStates.push({ id: ST_RLE, nextId: ST_LZSS, lines: [
            `if ${nCf}==0 then ${nRle}={};for _i=2,${nCnt} do ${nRle}[_i-1]=${nDec}[_i] end;${nCnt}=${nCnt}-1 else`,
            `${nRle}={};local _rp=2;local _rc=0;local _dn=${nCnt}`,
            `while _rp<=_dn do local _rb=${nDec}[_rp];if _rb==255 then _rp=_rp+1;local _rn=${nDec}[_rp];if _rn==0 then _rc=_rc+1;${nRle}[_rc]=255 else _rp=_rp+1;local _rv=${nDec}[_rp];for _ri=1,_rn+3 do _rc=_rc+1;${nRle}[_rc]=_rv end end else _rc=_rc+1;${nRle}[_rc]=_rb end;_rp=_rp+1 end`,
            `${nCnt}=_rc`,
            `end`,
        ] });
    const BATCH = 150 + Math.floor(rng() * 101);
    cfStates.push({ id: ST_LZSS, nextId: ST_SEC, lines: [
            `if ${nCf}==0 then`,
            `${nTmpChk}=0;for _i=1,#${nRle} do ${nTmpChk}=(${nTmpChk}+${nRle}[_i])%${tamperPrime} end`,
            `${nOut}={};local _oc=0;local _ln=#${nRle};for _i=1,_ln,${BATCH} do _oc=_oc+1;local _e=_i+${BATCH - 1};if _e>_ln then _e=_ln end;${nOut}[_oc]=${nCh}(${nTU}(${nRle},_i,_e)) end`,
            `else`,
            `local _lz={};local _lp=1;local _lc=0;local _rn=#${nRle}`,
            `while _lp<=_rn do if _lp%${35000 + Math.floor(rng() * 30001)}==1 and ${nTw} then ${nTw}() end;local _ct=${nRle}[_lp];_lp=_lp+1;if _ct<128 then local _n=_ct+1;for _i=1,_n do _lc=_lc+1;_lz[_lc]=${nRle}[_lp];_lp=_lp+1 end elseif _ct<192 then local _ll=_ct-124;local _lo=${nRle}[_lp]+1;_lp=_lp+1;local _ls=_lc;for _j=1,_ll do _lc=_lc+1;_lz[_lc]=_lz[_ls-_lo+_j] end else local _ll=_ct-188;local _lo=${nRle}[_lp]*256+${nRle}[_lp+1];_lp=_lp+2;local _ls=_lc;for _j=1,_ll do _lc=_lc+1;_lz[_lc]=_lz[_ls-_lo+_j] end end end`,
            `${nTmpChk}=0;for _i=1,_lc do ${nTmpChk}=(${nTmpChk}+_lz[_i])%${tamperPrime} end`,
            `${nOut}={};local _oc=0;for _i=1,_lc,${BATCH} do _oc=_oc+1;local _e=_i+${BATCH - 1};if _e>_lc then _e=_lc end;${nOut}[_oc]=${nCh}(${nTU}(_lz,_i,_e)) end`,
            `end`,
        ] });
    const secL = [];
    secL.push(`${nGuard}=${nTmpChk}==${tamperChecksum}`);
    secL.push(`${nGuard}=${nGuard} and ${nCType}(${nLd})==${nCh}(${ccArgs("function", true)})`);
    secL.push(`${nGuard}=${nGuard} and ${nCType}(${nBt})==${nCh}(${ccArgs("table", true)})`);
    secL.push(`${nGuard}=${nGuard} and ${nCh}(${hookByte})==${luaEsc(String.fromCharCode(hookByte))}`);
    secL.push(`${nGuard}=${nGuard} and ${nBxor}(0,0)==0`);
    secL.push(`${nGuard}=${nGuard} and ${nCType}(${nCGame})==${nCh}(${ccArgs("userdata", true)})`);
    secL.push(`${nGuard}=${nGuard} and (function() local _ok,_r=${nCPcall}(function() return ${nCGame}[${vmDk}(${kn("Workspace")})] end);return _ok and ${nCType}(_r)==${nCh}(${ccArgs("userdata", true)}) end)()`);
    secL.push(`${nGuard}=${nGuard} and (function() local _ok,_r=${nCPcall}(function() return ${nCScript} end);return _ok and (_r==nil or ${nCType}(_r)==${nCh}(${ccArgs("userdata", true)})) end)()`);
    if (layerOpts?.outerPipelineKey) {
        secL.push(`${nGuard}=${nGuard} and ${nRawGet}(${nEv},${nCh}(${ccArgs(layerOpts.outerPipelineKey, true)}))==${layerOpts.expectedOuterFp}`);
    }
    if (layerOpts) {
        secL.push(`${nGuard}=${nGuard} and ${nRawGet}(${nEv},${nCh}(${ccArgs(layerOpts.signalKey, true)}))==nil`);
    }
    if (layerOpts) {
        const nFp = randomName(3);
        const buildFactorXor = tamperChecksum ^ (bytes.length % tamperPrime) ^ cSeed ^ cStep
            ^ cInv[0] ^ cInv[127] ^ cInv[255] ^ (alpha.charCodeAt(0) ^ alphaXorKey) ^ nFrags;
        const fpSecret = layerOpts.ownFingerprint ^ buildFactorXor;
        secL.push(`local ${nFp}=${nBxor}(${nTmpChk},${bytes.length % tamperPrime},${cSeed},${cStep},${nIv}[1],${nIv}[128],${nIv}[256],${nAl}[1],${nFrags})`);
        secL.push(`${nFp}=${nBxor}(${nFp},${fpSecret})`);
        secL.push(`if ${nGuard} then ${nRawSet}(${nEv},${nCh}(${ccArgs(layerOpts.ownPipelineKey, true)}),${nFp}) end`);
    }
    if (process.env.NO_SEC === '1') {
        secL.length = 0;
        secL.push(`${nGuard}=true`);
    }
    const cShuffle = randomName(2);
    secL.push(`if not ${nGuard} then local ${cShuffle}=#${nOut};for _i=${cShuffle},2,-1 do local _j=1+(_i*${corruptKey}+${Math.floor(rng() * 65536)})%_i;${nOut}[_i],${nOut}[_j]=${nOut}[_j],${nOut}[_i] end;for _i=${nBand}(${cShuffle},${Math.floor(rng() * 128) + 128})+1,${cShuffle} do ${nOut}[_i]=nil end end`);
    if (layerOpts) {
        secL.push(`if not ${nGuard} then ${nRawSet}(${nEv},${nCh}(${ccArgs(layerOpts.signalKey, true)}),${Math.floor(rng() * 65536)}) end`);
    }
    cfStates.push({ id: ST_SEC, nextId: ST_EXEC, lines: secL });
    const execL = [];
    const adVar = randomName(3);
    const adProbe = randomName(3);
    const probeVal = 1 + Math.floor(rng() * 998);
    execL.push(`local ${adProbe}=true`);
    execL.push(`do local _pOk,${adVar}=${nCPcall}(${nLd},${nCh}(${ccArgs(`return ${probeVal}`, true)}));if _pOk and ${nCType}(${adVar})==${nCh}(${ccArgs("function", true)}) then local _pOk2,_pR=${nCPcall}(${adVar});${adProbe}=_pOk2 and _pR==${probeVal} else ${adProbe}=false end end`);
    const adNil = randomName(2);
    const adErr = randomName(2);
    execL.push(`do local _pOk,${adNil},${adErr}=${nCPcall}(${nLd},${nCh}(${ccArgs(")(", true)}));${adProbe}=${adProbe} and _pOk and ${adNil}==nil and ${nCType}(${adErr})==${nCh}(${ccArgs("string", true)}) end`);
    const adOk = randomName(2);
    const adFn = randomName(2);
    execL.push(`do local ${adOk},${adFn}=${nCPcall}(${nLd},${nCh}(${ccArgs("return 0", true)}));${adProbe}=${adProbe} and ${adOk}==true and ${nCType}(${adFn})==${nCh}(${ccArgs("function", true)}) end`);
    if (process.env.NO_SEC !== '1') {
        execL.push(`if not ${adProbe} then for _i=1,#${nOut} do ${nOut}[_i]=${nCh}(${Math.floor(rng() * 94) + 33}) end end`);
    }
    else {
        rng();
    }
    const fakeErrs = [
        "attempt to call a nil value", "stack overflow", "not enough memory",
        "C stack overflow", "table index is NaN", "invalid argument #1",
        "attempt to index nil with 'new'", "yield across metamethod/C-call boundary",
    ];
    for (let fe = 0; fe < 2 + Math.floor(rng() * 3); fe++) {
        const fv = randomName(2);
        const errStr = fakeErrs[Math.floor(rng() * fakeErrs.length)];
        honeyVars.push(fv);
        execL.push(`local ${fv};if ${nCType}(${nTmpChk})~=${nCh}(${ccArgs("number", true)}) then _G[${nCh}(${ccArgs("error", true)})](${nCh}(${ccArgs(errStr, true)})) end`);
    }
    const nCompiledFn = randomName(3);
    execL.push(`${nCompiledFn}=${nLd}(${nConcat}(${nOut}))`);
    execL.push(`for _i=1,#${nOut} do ${nOut}[_i]=nil end`);
    cfStates.push({ id: ST_EXEC, nextId: ST_EXIT, lines: execL });
    for (const fid of fakeStIds) {
        const fv = randomName(3);
        honeyVars.push(fv);
        const fVar = Math.floor(rng() * 4);
        const fl = [];
        if (fVar === 0)
            fl.push(`local ${fv}=${rInt()};for _k=1,${4 + Math.floor(rng() * 8)} do ${fv}=${nBand}(${fv}*${3 + Math.floor(rng() * 5)}+${rByte()},0xFFFF) end`);
        else if (fVar === 1)
            fl.push(`local ${fv}={${rArr(8 + Math.floor(rng() * 16))}}`);
        else if (fVar === 2)
            fl.push(`local ${fv}=${nBxor}(${rInt()},${rInt()});${fv}=${nBand}(${fv},0xFF)`);
        else
            fl.push(`local ${fv}=${nCType}(${rInt()})~=${nCh}(${ccArgs("number")}) and ${rInt()} or ${rInt()}`);
        cfStates.push({ id: fid, nextId: fakeStIds[Math.floor(rng() * fakeStIds.length)], lines: fl });
    }
    for (let i = cfStates.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [cfStates[i], cfStates[j]] = [cfStates[j], cfStates[i]];
    }
    L.push(`local ${nCompiledFn}`);
    L.push(`local ${nSt}=${ST_INIT}`);
    L.push(`while true do`);
    for (let i = 0; i < cfStates.length; i++) {
        const st = cfStates[i];
        L.push(`${i === 0 ? 'if' : 'elseif'} ${nSt}==${st.id} then`);
        for (const line of st.lines)
            L.push(line);
        if (st.nextId === ST_EXIT) {
            L.push(`break`);
        }
        else {
            const delta = st.id ^ st.nextId;
            L.push(`${nSt}=${nBxor}(${nSt},${delta})`);
        }
    }
    L.push(`end`);
    L.push(`end`);
    const epVar = Math.floor(rng() * 4);
    if (epVar === 1) {
        randomName(2);
    }
    else if (epVar === 2) {
        randomName(2);
    }
    else if (epVar === 3) {
        randomName(2);
        randomName(2);
    }
    L.push(`return ${nCompiledFn}()`);
    {
        const escRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        let bIdx = 0, cIdx = 0;
        for (let i = aliasInsertIdx; i < L.length; i++) {
            L[i] = L[i].replace(new RegExp('(?<![a-zA-Z0-9_])' + escRe(nBxor) + '\\(', 'g'), () => {
                return bxorAliases[bIdx++ % bxorAliases.length] + '(';
            });
            L[i] = L[i].replace(new RegExp('(?<![a-zA-Z0-9_])' + escRe(nCh) + '\\(', 'g'), () => {
                return chAliases[cIdx++ % chAliases.length] + '(';
            });
        }
    }
    return L.join("\n");
}
function generateDynamicSeed(chunk) {
    let h = 0x811c9dc5;
    const mix = (v) => { h ^= v & 0xFF; h = Math.imul(h, 0x01000193); h ^= (v >>> 8) & 0xFF; h = Math.imul(h, 0x01000193); };
    mix(Date.now());
    mix(Date.now() >>> 16);
    mix((Math.random() * 0xFFFFFFFF) >>> 0);
    mix((Math.random() * 0xFFFFFFFF) >>> 0);
    try {
        const hr = process.hrtime();
        mix(hr[0]);
        mix(hr[1]);
    }
    catch { }
    try {
        mix(process.pid);
    }
    catch { }
    try {
        const cb = randomBytes(16);
        for (let i = 0; i < 16; i += 4)
            mix(cb.readUInt32LE(i));
    }
    catch { }
    for (let i = 0; i < chunk.code.length; i += 37)
        mix(chunk.code[i]);
    mix(chunk.K.length);
    mix((chunk.protos?.length ?? 0) * 7919);
    for (let i = 0; i < Math.min(chunk.K.length, 20); i++) {
        const k = chunk.K[i];
        if (typeof k === "number")
            mix(k);
        else if (typeof k === "string") {
            for (let j = 0; j < Math.min(k.length, 8); j++)
                mix(k.charCodeAt(j));
        }
    }
    return h >>> 0;
}
function serializeBytecodeAsBinary(chunk, ctx) {
    const parts = [];
    function writeU8(v) { parts.push(v & 0xFF); }
    function writeU16(v) { parts.push(v & 0xFF, (v >>> 8) & 0xFF); }
    function writeU32(v) {
        parts.push(v & 0xFF, (v >>> 8) & 0xFF, (v >>> 16) & 0xFF, (v >>> 24) & 0xFF);
    }
    function writeI16(v) {
        const u = v < 0 ? v + 65536 : v;
        writeU16(u);
    }
    function writeF64(v) {
        const buf = Buffer.alloc(8);
        buf.writeDoubleLE(v, 0);
        for (let i = 0; i < 8; i++)
            parts.push(buf[i]);
    }
    function writeString(s) {
        const encoded = Buffer.from(s, 'utf-8');
        writeU16(encoded.length);
        for (let i = 0; i < encoded.length; i++)
            parts.push(encoded[i]);
    }
    function serializeChunk(ch) {
        writeU16(ch.nParams ?? 0);
        writeU8(ch.isVararg ? 1 : 0);
        writeU16(ch.maxRegs ?? 0);
        const code = ch.code;
        const nInstr = Math.floor(code.length / 4);
        writeU32(nInstr);
        for (let i = 0; i < code.length; i += 4) {
            writeU8(code[i]);
            writeI16(code[i + 1]);
            writeI16(code[i + 2]);
            writeI16(code[i + 3]);
        }
        const K = ch.K;
        writeU16(K.length);
        for (const k of K) {
            if (k === null || k === undefined) {
                writeU8(0);
            }
            else if (typeof k === 'boolean') {
                writeU8(1);
                writeU8(k ? 1 : 0);
            }
            else if (typeof k === 'number') {
                writeU8(2);
                writeF64(k);
            }
            else if (typeof k === 'string') {
                writeU8(3);
                writeString(k);
            }
        }
        const upvals = ch.upvalues ?? [];
        writeU16(upvals.length);
        for (const [isLocal, index] of upvals) {
            writeU8(isLocal);
            writeU16(index);
        }
        const protos = ch.protos ?? [];
        writeU16(protos.length);
        for (const proto of protos) {
            serializeChunk(proto);
        }
    }
    serializeChunk(chunk);
    return new Uint8Array(parts);
}
export function generateRegVM(chunk, options = {}) {
    const level = options.level ?? "normal";
    const seed = options.polymorphicSeed || generateDynamicSeed(chunk);
    seedRandom(seed);
    resetNames();
    const doShuffle = level !== "debug" && featureEnabled(options, "opcodeShuffle", true);
    const encodeStrings = level !== "debug" && featureEnabled(options, "stringEncoding", true);
    const includeExecutor = options.executorGlobals ?? (level !== "debug");
    const { encode, decode, encodeAlt } = shuffleOpcodes(doShuffle);
    const protoKeys = level === "max" ? {
        pK: randomName(2), pC: randomName(2), pP: randomName(2),
        pU: randomName(2), pN: randomName(2),
    } : { pK: "K", pC: "C", pP: "P", pU: "U", pN: "nParams" };
    const names = createNameMap(level);
    const rB = () => 1 + Math.floor(rng() * 254);
    const { sbox, inverse: sboxInverse } = encodeStrings
        ? generateSBox()
        : { sbox: Array.from({ length: 256 }, (_, i) => i), inverse: Array.from({ length: 256 }, (_, i) => i) };
    const helixSeed = encodeStrings ? rB() : 0;
    const helixMul = encodeStrings ? rB() : 0;
    const cascadeKey = encodeStrings ? rB() : 0;
    const cascadeMul = encodeStrings ? (1 + Math.floor(rng() * 126)) * 2 + 1 : 1;
    const checkKeyA = encodeStrings ? rB() : 0;
    const checkKeyB = encodeStrings ? rB() : 0;
    const checkStepA = encodeStrings ? rB() : 0;
    const checkStepB = encodeStrings ? rB() : 0;
    const spiralPrime = encodeStrings ? SPIRAL_PRIMES[Math.floor(rng() * SPIRAL_PRIMES.length)] : 1;
    const spiralOffset = encodeStrings ? Math.floor(rng() * 251) : 0;
    const layerVariants = [
        Math.floor(rng() * 3), Math.floor(rng() * 3), Math.floor(rng() * 2),
        Math.floor(rng() * 3), Math.floor(rng() * 3),
    ];
    const isObf = level !== "debug";
    const dispatchVariant = isObf ? (1 + Math.floor(rng() * 5)) : 0;
    const dispatchMask = isObf ? (1 + Math.floor(rng() * 254)) : 0;
    const rotSeed = isObf ? (1 + Math.floor(rng() * 254)) : 0;
    const rotStep = isObf ? (1 + Math.floor(rng() * 254)) : 0;
    const rotStep2 = isObf ? (1 + Math.floor(rng() * 254)) : 0;
    const rotStep3 = isObf ? (1 + Math.floor(rng() * 254)) : 0;
    const tagMask = isObf ? (1 + Math.floor(rng() * 254)) : 0;
    const deadOp = isObf ? (120 + Math.floor(rng() * 135)) : 254;
    const targetPlaceId = Number(options?.placeId || options?.targetPlaceId || 0);
    const ctx = {
        level, seed, names, opcodeEncode: encode, opcodeDecode: decode, opcodeAlt: encodeAlt,
        doShuffle, encodeStrings, xorKey: 0, xorStep: 0, includeExecutor, protoKeys,
        debugTrace: options.debugTrace ?? (level === "debug"),
        sbox, sboxInverse, helixSeed, helixMul, cascadeKey, cascadeMul,
        checkKeyA, checkKeyB, checkStepA, checkStepB,
        spiralPrime, spiralOffset, layerVariants,
        dispatchVariant, dispatchMask, rotSeed, rotStep, rotStep2, rotStep3, tagMask, deadOp,
        targetPlaceId,
        argPerm: generateArgPerms(isObf),
    };
    // Opcode fusion disabled in Sentinel v4.2 per dj's directive: keep 100% fine-grained atomic opcodes
    const doFusion = false;
    if (doFusion) {
        const allFusionOps = [
            45 /* RegOp.FUSED_TEST_JMP */, 46 /* RegOp.FUSED_EQ_JMP */,
            47 /* RegOp.FUSED_LT_JMP */, 48 /* RegOp.FUSED_LE_JMP */,
            49 /* RegOp.FUSED_TESTSET_JMP */, 50 /* RegOp.FUSED_GGET */,
            51 /* RegOp.FUSED_LOADKK */, 52 /* RegOp.FUSED_MOVE_MOVE */,
            53 /* RegOp.FUSED_SELF_CALL */, 54 /* RegOp.FUSED_GGET_CALL */,
            55 /* RegOp.FUSED_LOADK_RET */, 56 /* RegOp.FUSED_MOVE_RET */,
        ];
        for (let si = allFusionOps.length - 1; si > 0; si--) {
            const sj = Math.floor(rng() * (si + 1));
            [allFusionOps[si], allFusionOps[sj]] = [allFusionOps[sj], allFusionOps[si]];
        }
        const nEnabled = 7 + Math.floor(rng() * 4);
        const enabledSet = new Set(allFusionOps.slice(0, nEnabled));
        const fusionRate = 0.6 + rng() * 0.25;
        const fusionCount = applyFusionPass(chunk, enabledSet, fusionRate);
        if (fusionCount > 0) {
            console.log(`[RegVM] Fused ${fusionCount} instruction sequences (${nEnabled}/12 patterns, ${Math.round(fusionRate * 100)}% rate)`);
        }
    }
    const doCFF = featureEnabled(options, "controlFlowFlattening", level !== "debug");
    if (doCFF) {
        const cffBlocks = flattenControlFlow(chunk);
        if (cffBlocks > 0) {
            console.log(`[RegVM] CFF: ${cffBlocks} blocks shuffled (main + protos)`);
        }
    }
    if (level !== "debug") {
        const used = collectUsedOpcodes(chunk);
        used.add(0 /* RegOp.NOP */);
        used.add(44 /* RegOp.EXTRAARG */);
        ctx.usedOps = used;
        console.log(`[RegVM] Dead handler elimination: ${used.size}/${handlerRegistry.size} opcodes used`);
    }
    if (level !== "debug")
        console.log(`[RegVM] Dispatch: 2-Layer Nested CFF + Variable-Len Buffer VM (deadOp=${deadOp})`);
    const dataK = serializeConstants(chunk.K, ctx, true);
    const dataC = serializeRegCode(chunk.code, ctx);
    const dataP = serializeRegProtos(chunk.protos, ctx);
    const dK = level === "debug" ? "_dK" : randomName(3);
    const dC = level === "debug" ? "_dC" : randomName(3);
    const dP = level === "debug" ? "_dP" : randomName(3);
    const nP = chunk.nParams ?? 0;
    const mR = chunk.maxRegs ?? 0;
    const isVA = chunk.isVararg ? "true" : "false";
    let output;
    if (level === "debug") {
        const builtinCaps = buildBuiltinCaptures(ctx);
        const envSetup = buildEnvSetup(ctx);
        let decResult = null;
        if (encodeStrings) {
            decResult = buildDecoderChain(ctx, dK, dP);
        }
        const vmRuntime = buildVMRuntime(ctx);
        const parts = [];
        parts.push(builtinCaps.code);
        parts.push(envSetup);
        if (decResult) {
            parts.push(...decResult.fragments.map(f => f.code));
        }
        parts.push(vmRuntime);
        parts.push(`local ${dK}=${dataK}`);
        parts.push(`local ${dC}=${dataC}`);
        parts.push(`local ${dP}=${dataP}`);
        parts.push(`return ${names.run}(${dK},${dC},${dP},{},${nP},${mR},${isVA},${names.env})`);
        output = parts.join("\n");
    }
    else {
        const allFragments = [];
        const forwardDecls = [];
        const builtinCaps = buildBuiltinCaptures(ctx);
        const builtinNames = [
            names.bPcall, names.bXpcall, names.bSelect, names.bType,
            names.tPack, names.tUnpack, names.bTcreate, names.bTconcat,
            names.bMfloor, names.bIpairs, names.bTostring, names.bRawget,
            names.bSetmeta, names.bBxor, names.bBand, names.bLsh, names.bRsh,
            names.bSbyte, names.bSchar, names.bBcr, names.bBlen, names.bBr8,
            names.bBw8, names.bBcp, names.bBfs, names.bGetmeta, names.bNext, names.fnv,
        ];
        forwardDecls.push(...builtinNames);
        if (builtinCaps.secDeltaVar) {
            forwardDecls.push(builtinCaps.secDeltaVar, builtinCaps.secStateVar);
        }
        allFragments.push({ code: builtinCaps.assignOnly, layer: -1 });
        const envResult = buildEnvFragments(ctx);
        allFragments.push(...envResult.fragments);
        forwardDecls.push(...envResult.forwardDecls);

        let chainCalls = "";
        if (encodeStrings) {
            const decResult = buildDecoderChain(ctx, dK, dP);
            allFragments.push(...decResult.fragments);
            forwardDecls.push(...decResult.forwardDecls);
            chainCalls = decResult.chainCalls;
        }

        forwardDecls.push(
            names.wLut, names.shCache, names.pk, names.rb, names.wb,
            names.cp, names.dec, names.adv, names.oMap, names.run
        );
        const vmCode = buildVMRuntime(ctx, true);
        allFragments.push({ code: vmCode, layer: Math.floor(rng() * 3) });
        forwardDecls.push(dK, dC, dP);
        allFragments.push({ code: `${dK}=${dataK}`, layer: Math.floor(rng() * 3) });
        allFragments.push({ code: `${dC}=${dataC}`, layer: Math.floor(rng() * 3) });
        allFragments.push({ code: `${dP}=${dataP}`, layer: Math.floor(rng() * 3) });
        generateJunkFragments(allFragments, forwardDecls, names);
        const minLayer = allFragments.reduce((mn, f) => Math.min(mn, f.layer), 0);
        const maxLayer = allFragments.reduce((mx, f) => Math.max(mx, f.layer), 0);
        const sorted = [];
        for (let layer = minLayer; layer <= maxLayer; layer++) {
            const bucket = allFragments.filter(f => f.layer === layer);
            for (let i = bucket.length - 1; i > 0; i--) {
                const j = Math.floor(rng() * (i + 1));
                [bucket[i], bucket[j]] = [bucket[j], bucket[i]];
            }
            sorted.push(...bucket);
        }
        for (let i = forwardDecls.length - 1; i > 0; i--) {
            const j = Math.floor(rng() * (i + 1));
            [forwardDecls[i], forwardDecls[j]] = [forwardDecls[j], forwardDecls[i]];
        }
        const declLines = [];
        let di = 0;
        while (di < forwardDecls.length) {
            const groupSize = 3 + Math.floor(rng() * 5);
            declLines.push(`local ${forwardDecls.slice(di, di + groupSize).join(",")}`);
            di += groupSize;
        }
        const parts = [];
        parts.push(...declLines);
        if (level === "max") {
            const stA = randomName(3);
            const stB = randomName(3);
            const invVar = randomName(2);
            const hashVar = randomName(3);
            const multA = 31;
            const multB = 17;
            const offsetB = 101;
            const modM = 65536;

            const calcHash = (a, b) => {
                return ((a * multA) % modM) ^ ((b * multB + offsetB) % modM);
            };

            const usedHashes = new Set();
            const realPairs = [];
            const realHashes = [];
            for (let i = 0; i <= sorted.length + (chainCalls ? 1 : 0); i++) {
                let a, b, h;
                do {
                    a = 10 + Math.floor(rng() * 450);
                    b = 10 + Math.floor(rng() * 450);
                    h = calcHash(a, b);
                } while (usedHashes.has(h));
                usedHashes.add(h);
                realPairs.push({ a, b });
                realHashes.push(h);
            }

            const realStates = [];
            for (let i = 0; i < sorted.length; i++) {
                const nextPair = i + 1 < realPairs.length ? realPairs[i + 1] : null;
                realStates.push({
                    hash: realHashes[i],
                    pair: realPairs[i],
                    code: sorted[i].code,
                    nextPair,
                    isExit: !chainCalls && (i === sorted.length - 1)
                });
            }
            if (chainCalls) {
                const lastIdx = sorted.length;
                realStates.push({
                    hash: realHashes[lastIdx],
                    pair: realPairs[lastIdx],
                    code: chainCalls,
                    nextPair: null,
                    isExit: true
                });
            }

            // Fake / decoy states with impossible invariants
            const nFake = 10 + Math.floor(rng() * 8);
            const fakeStates = [];
            for (let fi = 0; fi < nFake; fi++) {
                let fa, fb, fh;
                do {
                    fa = 10 + Math.floor(rng() * 450);
                    fb = 10 + Math.floor(rng() * 450);
                    fh = calcHash(fa, fb);
                } while (usedHashes.has(fh));
                usedHashes.add(fh);

                const jn = randomName(3);
                const jn2 = randomName(3);
                const loopK = randomName(3);
                const fc = `local ${jn}={11,22,33,44};local ${jn2}=0;for ${loopK}=1,#${jn} do ${jn2}=_bxor(${jn2},${jn}[${loopK}]) end;${stA}=_bxor(${stA},${jn2});`;
                const nextFakePair = realPairs[Math.floor(rng() * realPairs.length)];
                fakeStates.push({
                    hash: fh,
                    pair: { a: fa, b: fb },
                    code: fc,
                    nextPair: nextFakePair,
                    isExit: false,
                    isFake: true
                });
            }

            const allSt = [...realStates, ...fakeStates];
            for (let i = allSt.length - 1; i > 0; i--) {
                const j = Math.floor(rng() * (i + 1));
                [allSt[i], allSt[j]] = [allSt[j], allSt[i]];
            }

            const emitDualTransition = (nextPair) => {
                if (!nextPair) return "";
                const tA = nextPair.a;
                const tB = nextPair.b;
                const mA = 1 + Math.floor(rng() * 15);
                // Data-dependent CFF v2: state coupled with live runtime security delta
                const deltaTerm = ctx.secDeltaVar ? `_bxor(${tA},(${ctx.secDeltaVar} or 0))` : `${tA}`;
                const transA = `${stA}=math.floor((${deltaTerm})*${mA}/${mA})`;
                const maskB = 1 + Math.floor(rng() * 65535);
                const transB = `${stB}=_bxor(_bxor(${tB},${maskB}),${maskB})`;
                return `${transA};${transB};`;
            };

            const initPair = realPairs[0];
            parts.push(`local _b32=(type(bit32)=="table" and bit32) or (type(getgenv)=="function" and type(getgenv().bit32)=="table" and getgenv().bit32) or (type(_G)=="table" and type(_G.bit32)=="table" and _G.bit32) or (type(bit)=="table" and bit) or {}`);
            parts.push(`local _bxor=_b32.bxor or function(a,b) a=tonumber(a) or 0;b=tonumber(b) or 0;local p,c=1,0 while a>0 or b>0 do local ra,rb=a%2,b%2 if ra~=rb then c=c+p end a,b,p=math.floor(a/2),math.floor(b/2),p*2 end return c end`);
            parts.push(`local _band=_b32.band or function(a,b) a=tonumber(a) or 0;b=tonumber(b) or 0;local p,c=1,0 while a>0 and b>0 do if a%2==1 and b%2==1 then c=c+p end a,b,p=math.floor(a/2),math.floor(b/2),p*2 end return c end`);
            parts.push(`local ${stA}=${initPair.a}`);
            parts.push(`local ${stB}=${initPair.b}`);
            parts.push(`local ${invVar}=${Math.floor(rng() * 50) + 7}`);
            parts.push(`while true do`);
            parts.push(`local ${hashVar}=_bxor(((${stA} or 0)*${multA})%${modM},(((${stB} or 0)*${multB}+${offsetB})%${modM}))`);

            for (let si = 0; si < allSt.length; si++) {
                const st = allSt[si];
                const kw = si === 0 ? "if" : "elseif";
                const isFake = Boolean(st.isFake);
                const cond = isFake
                    ? `${hashVar}==${st.hash} and ((${invVar}*(${invVar}+1))%2==1)`
                    : `${hashVar}==${st.hash}`;

                parts.push(`${kw} ${cond} then`);
                parts.push(st.code);
                if (st.isExit) {
                    parts.push(`break`);
                } else {
                    parts.push(emitDualTransition(st.nextPair));
                }
            }
            parts.push(`else return nil end`);
            parts.push(`end`);
            if (process.env.ENV_CHECK === '1') {
                const chkVars = [
                    ['run', names.run], ['env', names.env], ['pcall', names.bPcall],
                    ['bxor', names.bBxor], ['band', names.bBand], ['type', names.bType],
                    ['select', names.bSelect], ['tpack', names.tPack], ['tunpack', names.tUnpack],
                    ['mfloor', names.bMfloor], ['setmeta', names.bSetmeta], ['tostring', names.bTostring],
                    ['dK', dK], ['dC', dC], ['dP', dP],
                ];
                const wParts = chkVars.map(([l, v]) => `"${l}="..tostring(${v})`);
                parts.push(`warn("[ENV_CHECK] "..${wParts.join('.." "..')})`);
            }
            parts.push(`return ${names.run}(${dK},${dC},${dP},{},${nP},${mR},${isVA},${names.env})`);
        }
        else {
            for (const frag of sorted) {
                parts.push(frag.code);
            }
            if (chainCalls)
                parts.push(chainCalls);
            if (process.env.ENV_CHECK === '1') {
                const chkVars = [
                    ['run', names.run], ['env', names.env], ['pcall', names.bPcall],
                    ['bxor', names.bBxor], ['band', names.bBand], ['type', names.bType],
                    ['select', names.bSelect], ['tpack', names.tPack], ['tunpack', names.tUnpack],
                    ['mfloor', names.bMfloor], ['setmeta', names.bSetmeta], ['tostring', names.bTostring],
                    ['dK', dK], ['dC', dC], ['dP', dP],
                ];
                const wParts = chkVars.map(([l, v]) => `"${l}="..tostring(${v})`);
                parts.push(`warn("[ENV_CHECK] "..${wParts.join('.." "..')})`);
            }
            parts.push(`return ${names.run}(${dK},${dC},${dP},{},${nP},${mR},${isVA},${names.env})`);
        }
        output = parts.join("\n");
    }
    if (process.env.DUMP_RAW === '1' && level !== 'debug') {
        _dumpWrite('debug-vm-raw.lua', output, 'utf-8');
        console.log(`[RegVM] DUMP_RAW: saved ${output.length} chars to debug-vm-raw.lua`);
    }
    // Direct Native Register Virtual Machine output (Zero loadstring at runtime)
    console.log(`[RegVM] Emitting Sentinel v4.4 Variable-Length Buffer VM + 2-Layer Nested CFF`);
    output = `return(function(...) ${output} end)(...)`;
    if (!options._noWatermark) {
        const art = [
            "-- ==============================================================================",
            "--  PAYOMBØYZ SENTINEL PROTOCOL v4.4 -- VARIABLE-LEN BUFFER VM & NESTED CFF",
            "--  Cryptographic Protection: Variable-Width Buffer Bytecode + Rolling Xorshift32 + 2-Layer CFF",
            "--  Tamper Resistance: Dead-Op Wipe, Encrypted Shadow Restore & FNV-1a Anti-Hook Guards",
            "-- =============================================================================="
        ];
        output = `--[[\n${art.join('\n')}\n]]\n` + output;
    }
    if (level !== "debug" && !options.noMinify) {
        const watermarkEnd = output.indexOf(']]\n');
        if (watermarkEnd !== -1) {
            const watermark = output.substring(0, watermarkEnd + 3);
            const code = output.substring(watermarkEnd + 3);
            const oneLine = code.split('\n').filter(l => l.trim().length > 0).join(' ');
            output = watermark + '\n' + oneLine;
        }
    }
    return output;
}
//# sourceMappingURL=reg-vm-gen.js.map