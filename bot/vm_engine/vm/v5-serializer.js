// language: JavaScript, file: v5-serializer.js, target: Node.js ESM
// Sentinel v5.2 APEX Binary Container Serializer:
// Deduplicated S-Box+LCG Master String Pool (K1/K2/K3) + AoS Interleaved Rolling-LCG Proto Stream
// + Per-Proto Shifted (_rb/_kb) + LZSS + Zero-Oracle 9-Byte Header (with FNV32 Integrity MAC)
// + 128-bit RC4 + Drop-256 + Rolling ARX Keystream + Shuffled Base85+Dict

function toUTF8Bytes(s) {
    return Buffer.from(s, "utf8");
}

function lzssCompress(input) {
    const out = [];
    const WIN = 16384;
    const MIN_MATCH = 4;
    const MAX_MATCH = 67;
    const MAX_LIT = 128;
    const HASH_SIZE = 1 << 15;
    const HASH_MASK = HASH_SIZE - 1;
    const head = new Int32Array(HASH_SIZE).fill(-1);
    const prev = new Int32Array(input.length).fill(-1);
    const hash3 = (pos) => ((input[pos] << 10) ^ (input[pos + 1] << 5) ^ (input[pos + 2] ?? 0)) & HASH_MASK;

    let i = 0;
    let litBuf = [];
    const flushLit = () => {
        while (litBuf.length > 0) {
            const n = Math.min(litBuf.length, MAX_LIT);
            out.push(n - 1);
            for (let j = 0; j < n; j++) out.push(litBuf[j]);
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
            while (j >= limit && chain < 64) {
                let len = 0;
                while (len < MAX_MATCH && i + len < input.length && input[j + len] === input[i + len]) len++;
                if (len > bestLen) { bestLen = len; bestOff = i - j; }
                if (len === MAX_MATCH) break;
                j = prev[j];
                if (j < 0) break;
                chain++;
            }
            prev[i] = head[h];
            head[h] = i;
        }
        if (bestLen >= MIN_MATCH) {
            flushLit();
            if (bestOff <= 256) {
                out.push(0x80 | (bestLen - MIN_MATCH));
                out.push(bestOff - 1);
            } else {
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
        } else {
            litBuf.push(input[i]);
            i++;
        }
    }
    flushLit();
    return Uint8Array.from(out);
}

function writeVarU32(out, val) {
    let v = val >>> 0;
    while (v >= 0x80) {
        out.push((v & 0x7F) | 0x80);
        v >>>= 7;
    }
    out.push(v);
}

function writeU32LE(out, val) {
    const v = val >>> 0;
    out.push(v & 0xFF, (v >>> 8) & 0xFF, (v >>> 16) & 0xFF, (v >>> 24) & 0xFF);
}

function writeF64(out, val) {
    const b = Buffer.allocUnsafe(8);
    b.writeDoubleLE(val, 0);
    for (let i = 0; i < 8; i++) out.push(b[i]);
}

function rc4ArxCrypt(data, keyBytes, dropN, arxInit) {
    const S = new Uint8Array(256);
    for (let i = 0; i < 256; i++) S[i] = i;
    let j = 0;
    const kLen = keyBytes.length;
    for (let i = 0; i < 256; i++) {
        j = (j + S[i] + keyBytes[i % kLen]) & 0xFF;
        const t = S[i]; S[i] = S[j]; S[j] = t;
    }
    let a = 0, b = 0;
    for (let d = 0; d < dropN; d++) {
        a = (a + 1) & 0xFF;
        b = (b + S[a]) & 0xFF;
        const t = S[a]; S[a] = S[b]; S[b] = t;
    }
    const out = new Uint8Array(data.length);
    let arx = arxInit >>> 0;
    for (let k = 0; k < data.length; k++) {
        a = (a + 1) & 0xFF;
        b = (b + S[a]) & 0xFF;
        const t = S[a]; S[a] = S[b]; S[b] = t;
        const rc4Byte = S[(S[a] + S[b]) & 0xFF];
        arx = (Math.imul(arx, 1664525) + 1013904223) >>> 0;
        const arxByte = (arx >>> 16) & 0xFF;
        out[k] = data[k] ^ rc4Byte ^ arxByte;
    }
    return out;
}

function customBase85Encode(bytes, alphabet) {
    // Prefix length is stored inside the encrypted header, so pad with 0s to 4-byte multiple cleanly
    const padLen = (4 - (bytes.length % 4)) % 4;
    const padded = new Uint8Array(bytes.length + padLen);
    padded.set(bytes);
    const chars = [];
    for (let i = 0; i < padded.length; i += 4) {
        let val = ((padded[i] << 24) | (padded[i + 1] << 16) | (padded[i + 2] << 8) | padded[i + 3]) >>> 0;
        const block = new Array(5);
        for (let k = 4; k >= 0; k--) {
            block[k] = alphabet[val % 85];
            val = Math.floor(val / 85);
        }
        chars.push(block.join(""));
    }
    return chars.join("");
}

/**
 * Generates an 85-char shuffled alphabet from safe printable ASCII (excluding ", \, [, ], =, and space)
 * PLUS 6 single-char dictionary tokens mapped via string.gsub to frequent 2-char Base85 digrams.
 */
function createAlphabetAndDict(rng) {
    const safePool = [];
    for (let code = 33; code <= 126; code++) {
        if (code === 34 || code === 92 || code === 91 || code === 93 || code === 61) continue;
        // Also reserve uppercase? Wait: 94-6=88 chars + extra safe? Check count:
        // ASCII 33..126 = 94 chars. Minus ", \, [, ], = (5 chars) = 89 chars!
        // Still skip % (37) and Lua pattern magic if used directly? No, plain replacement chars just avoid regex magic in gsub!
        safePool.push(String.fromCharCode(code));
    }
    // 89 safe chars: 85 for Base85 + 4 spare chars unused OR 1-byte sentinel? Actually 89 - 85 = 4 unused chars!
    // Map top 4 most frequent Base85 pairs to the 4 unused safe chars (zero regex escaping needed if not %^$()..[*+-?)!
    const SAFE_DICT_CANDS = ["z", "y", "x", "w", "k", "j", "q", "v", "Z", "Y", "X", "W", "0", "1", "2", "3"];
    for (let i = safePool.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [safePool[i], safePool[j]] = [safePool[j], safePool[i]];
    }
    // Choose 4 dict tokens that are NOT Lua pattern special characters (avoid ^ $ ( ) % . [ ] * + - ?)
    const nonPattern = safePool.filter(ch => !("^$()%.[]*+-?".includes(ch)));
    const dictTokens = nonPattern.slice(0, 4);
    const tokSet = new Set(dictTokens);
    const alphabet = safePool.filter(ch => !tokSet.has(ch)).slice(0, 85);
    return { alphabet, dictTokens };
}

function applyDictCompression(b85, dictTokens) {
    // Count non-overlapping 2-char digrams (not containing any dictToken or Lua pattern magic)
    const freq = new Map();
    for (let i = 0; i + 1 < b85.length; i += 2) {
        const p = b85.slice(i, i + 2);
        if ("^$()%.[]*+-?".includes(p[0]) || "^$()%.[]*+-?".includes(p[1])) continue;
        freq.set(p, (freq.get(p) || 0) + 1);
    }
    const top = [...freq.entries()]
        .filter(([, cnt]) => cnt >= 8)
        .sort((a, b) => b[1] - a[1])
        .slice(0, dictTokens.length)
        .map(([pair], idx) => ({ token: dictTokens[idx], pair }));

    if (top.length === 0) return { encoded: b85, dictMap: [] };

    let s = b85;
    for (const { token, pair } of top) {
        s = s.split(pair).join(token);
    }
    return { encoded: s, dictMap: top };
}

/**
 * Serializes v5 IR chunk tree into encrypted binary container + Lua bootstrap metadata.
 */
export function serializeV5Container(v5Root, ctx, rng, extraStrings = []) {
    // 1. Randomize constant type tags & create per-build S-Box for Master String Pool
    const tags = [0, 1, 2, 3, 4];
    for (let i = tags.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [tags[i], tags[j]] = [tags[j], tags[i]];
    }
    const [TAG_NIL, TAG_FALSE, TAG_TRUE, TAG_NUM, TAG_STR] = tags;

    const sbox = Array.from({ length: 256 }, (_, i) => i);
    for (let i = 255; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [sbox[i], sbox[j]] = [sbox[j], sbox[i]];
    }
    const invSbox = new Array(256);
    for (let i = 0; i < 256; i++) invSbox[sbox[i]] = i;

    // 2. Flatten protos in post-order so child indices ALWAYS precede parent index
    const flatProtos = [];
    const protoToIdx = new Map();
    function collectPostOrder(p) {
        for (const cp of p.protos) collectPostOrder(cp);
        const idx = flatProtos.length; // 0-based
        protoToIdx.set(p, idx);
        flatProtos.push(p);
    }
    collectPostOrder(v5Root);
    const rootProtoIdx = flatProtos.length - 1; // 0-based

    // 3. Build deduplicated Master Encrypted String Pool (coupled to K1, K2, K3)
    const poolBytes = [];
    const strCache = new Map();
    const kBytes = ctx.kBytes;

    function internString(str) {
        const existing = strCache.get(str);
        if (existing) return existing;
        const utf8 = toUTF8Bytes(str);
        const offset = poolBytes.length; // 0-based byte offset in pool
        const len = utf8.length;
        const strSalt = 1 + Math.floor(rng() * 0xFFFFFF);
        let lcg = (strSalt ^ ctx.K1) >>> 0;
        for (let i = 0; i < len; i++) {
            lcg = (Math.imul(lcg, 1664525) + 1013904223) >>> 0;
            const kByte = ((lcg >>> 16) ^ kBytes[8 + (i & 7)]) & 0xFF;
            const sub = sbox[utf8[i]];
            poolBytes.push((sub ^ kByte) & 0xFF);
        }
        const entry = { offset, len, strSalt };
        strCache.set(str, entry);
        return entry;
    }

    // Randomized wire column order for interleaved instruction stream
    const wireColOrder = [0, 1, 2, 3, 4];
    for (let i = wireColOrder.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [wireColOrder[i], wireColOrder[j]] = [wireColOrder[j], wireColOrder[i]];
    }

    // 4. Write binary payload:
    //   [poolLen (varu32)] [poolBytes...]
    //   [nProtos (varu32)] [rootIdx (varu32)]
    //   For each proto pi:
    //     [nParams] [maxRegs] [flags] [encRb] [encKb]
    //     [nK] -> K entries
    //     [nUp] -> (isLocal u8, idx varu32)
    //     [nChild] -> childIdx (varu32)
    //     [nInstr] -> interleaved AoS in wireColOrder XORed with per-proto LCG(K1 ^ (pi+1)*0x9E3779B1)
    const bin = [];
    for (let i = 0; i < flatProtos.length; i++) {
        for (const k of flatProtos[i].K) {
            if (typeof k === "string") internString(k);
        }
    }
    if (Array.isArray(extraStrings)) {
        for (const s of extraStrings) {
            if (typeof s === "string") internString(s);
        }
    }

    writeVarU32(bin, poolBytes.length);
    for (let i = 0; i < poolBytes.length; i++) bin.push(poolBytes[i]);

    writeVarU32(bin, flatProtos.length);
    writeVarU32(bin, rootProtoIdx);

    const k2Mask16 = ctx.K2 & 0xFFFF;
    const k3Mask16 = ctx.K3 & 0xFFFF;

    for (let pi = 0; pi < flatProtos.length; pi++) {
        const p = flatProtos[pi];
        writeVarU32(bin, p.nParams);
        writeVarU32(bin, p.maxRegs);
        const flags =
            (p.isVararg ? 1 : 0) |
            ((p.entryMode & 1) << 1) |
            (p.isEphemeral ? 4 : 0) |
            (p.isHot ? 8 : 0) |
            (p.hasClosures ? 16 : 0);
        bin.push(flags);

        writeVarU32(bin, ((p.regBase ^ k3Mask16) >>> 0));
        writeVarU32(bin, ((p.kBase ^ k2Mask16) >>> 0));
        writeVarU32(bin, ((p.protoSalt ^ ctx.K3) >>> 0));

        writeVarU32(bin, p.K.length);
        for (const k of p.K) {
            if (k === null || k === undefined) {
                bin.push(TAG_NIL);
            } else if (typeof k === "boolean") {
                bin.push(k ? TAG_TRUE : TAG_FALSE);
            } else if (typeof k === "number") {
                bin.push(TAG_NUM);
                writeF64(bin, k);
            } else if (typeof k === "string") {
                bin.push(TAG_STR);
                const info = strCache.get(k);
                writeVarU32(bin, info.offset);
                writeVarU32(bin, info.len);
                writeVarU32(bin, info.strSalt);
            } else {
                bin.push(TAG_NIL);
            }
        }

        writeVarU32(bin, p.upvalues.length);
        for (const [isLocal, idx] of p.upvalues) {
            bin.push(isLocal & 1);
            writeVarU32(bin, idx);
        }

        writeVarU32(bin, p.protos.length);
        for (const cp of p.protos) {
            writeVarU32(bin, protoToIdx.get(cp));
        }

        writeVarU32(bin, p.nInstr);
        const cols = [p.arr0, p.arr1, p.arr2, p.arr3, p.arr4];
        let pLcg = (ctx.K1 ^ Math.imul(pi + 1, 2654435761)) >>> 0;
        for (let i = 0; i < p.nInstr; i++) {
            for (const c of wireColOrder) {
                pLcg = (Math.imul(pLcg, 1664525) + 1013904223) >>> 0;
                const val = ((cols[c][i] >>> 0) ^ pLcg) >>> 0;
                writeVarU32(bin, val);
            }
        }
    }

    const rawBytes = Uint8Array.from(bin);

    // 5. Optional LZSS compression + Zero-Oracle 9-byte Encrypted Header + 32-bit FNV MAC
    let bodyBytes = rawBytes;
    let compressedFlag = 0;
    if (rawBytes.length >= 64) {
        const comp = lzssCompress(rawBytes);
        if (comp.length + 1 < rawBytes.length * 0.96) {
            bodyBytes = comp;
            compressedFlag = 1;
        }
    }

    const flagRaw = Math.floor(rng() * 256);
    let flagComp = Math.floor(rng() * 256);
    if (flagComp === flagRaw) flagComp = (flagRaw + 73) & 0xFF;

    // 32-bit integrity MAC over rawBytes seeded by (K0 ^ K1)
    let mac32 = (ctx.K0 ^ ctx.K1) >>> 0;
    for (let i = 0; i < rawBytes.length; i++) {
        mac32 = Math.imul((mac32 ^ rawBytes[i]) >>> 0, 16777619) >>> 0;
    }

    const encFlag = ((compressedFlag ? flagComp : flagRaw) ^ (ctx.K2 & 0xFF)) & 0xFF;
    const encRawLen = (rawBytes.length ^ ctx.K3) >>> 0;
    const encMac = (mac32 ^ ctx.K0) >>> 0;

    const framed = new Uint8Array(9 + bodyBytes.length);
    framed[0] = encFlag;
    framed[1] = encRawLen & 0xFF;
    framed[2] = (encRawLen >>> 8) & 0xFF;
    framed[3] = (encRawLen >>> 16) & 0xFF;
    framed[4] = (encRawLen >>> 24) & 0xFF;
    framed[5] = encMac & 0xFF;
    framed[6] = (encMac >>> 8) & 0xFF;
    framed[7] = (encMac >>> 16) & 0xFF;
    framed[8] = (encMac >>> 24) & 0xFF;
    framed.set(bodyBytes, 9);

    // 6. 128-bit K_Bytes-coupled RC4 + Drop-256 + Rolling ARX Keystream
    const rc4KeyLen = 24;
    const rawRc4Key = new Array(rc4KeyLen);
    const derivedRc4Key = new Uint8Array(rc4KeyLen);
    for (let i = 0; i < rc4KeyLen; i++) {
        rawRc4Key[i] = Math.floor(rng() * 256);
        derivedRc4Key[i] = (rawRc4Key[i] ^ kBytes[i % 16]) & 0xFF;
    }
    const rc4DropN = 256 + (ctx.K0 % 127);
    const arxStreamInit = (ctx.K1 ^ ctx.K2) >>> 0;
    const cipherBytes = rc4ArxCrypt(framed, derivedRc4Key, rc4DropN, arxStreamInit);

    // 7. Shuffled Base85 + Dictionary Compression + Split Chunks
    const { alphabet, dictTokens } = createAlphabetAndDict(rng);
    const b85 = customBase85Encode(cipherBytes, alphabet);
    const { encoded, dictMap } = applyDictCompression(b85, dictTokens);

    // Split payload into 3-6 shuffled chunk literals for CFF assembly
    const nChunks = Math.min(Math.max(2, Math.floor(encoded.length / 8000) + 2), 6);
    const chunkSize = Math.ceil(encoded.length / nChunks);
    const chunks = [];
    for (let i = 0; i < encoded.length; i += chunkSize) {
        chunks.push(encoded.slice(i, i + chunkSize));
    }

    const strRefs = Object.create(null);
    for (const [str, info] of strCache) {
        strRefs[str] = info;
    }

    return {
        chunks,
        cipherLen: cipherBytes.length,
        alphabet: alphabet.join(""),
        dictMap,
        rawRc4Key,
        rc4DropN,
        flagRaw,
        flagComp,
        wireColOrder,
        invSbox,
        tags: { TAG_NIL, TAG_FALSE, TAG_TRUE, TAG_NUM, TAG_STR },
        rawByteLen: rawBytes.length,
        strRefs,
        strCache,
    };
}
