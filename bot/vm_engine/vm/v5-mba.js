// language: JavaScript, file: v5-mba.js, target: Node.js ESM
// 32-bit Modular Mixed Boolean-Arithmetic (MBA) bijection & opaque predicate synthesizer

const MOD32 = 0x100000000;

/**
 * Exact 32-bit modular multiplication matching Lua U:Ta(a, b) (16-bit split, IEEE-754 exact).
 */
export function imul32(a, b) {
    return Math.imul(a >>> 0, b >>> 0) >>> 0;
}

/**
 * Compute modular inverse of odd 32-bit integer a modulo 2^32 using Newton-Raphson.
 */
export function modInv32(a) {
    let x = a >>> 0;
    if ((x & 1) === 0) throw new Error("modInv32 requires odd integer");
    let inv = 1;
    for (let i = 0; i < 5; i++) {
        inv = Math.imul(inv, (2 - Math.imul(x, inv)) >>> 0) >>> 0;
    }
    return inv >>> 0;
}

export function rotL32(x, s) {
    return ((x << s) | (x >>> (32 - s))) >>> 0;
}

/**
 * Exact 4x32-bit ARX sponge step matching Lua U[methSec] _mx(w0, w1).
 */
export function arxMix32(lanes, w0, w1) {
    const u0 = w0 >>> 0;
    const u1 = w1 >>> 0;
    lanes[0] = (imul32((lanes[0] + u0) >>> 0, 2654435761) ^ rotL32(lanes[1], 7)) >>> 0;
    lanes[1] = (imul32((lanes[1] ^ u1) >>> 0, 2246822519) + rotL32(lanes[2], 13)) >>> 0;
    lanes[2] = (imul32((lanes[2] + ((lanes[0] ^ lanes[3]) >>> 0)) >>> 0, 3266489917) ^ rotL32(lanes[3], 17)) >>> 0;
    lanes[3] = (imul32((lanes[3] ^ lanes[0]) >>> 0, 668265263) + rotL32(lanes[1], 11)) >>> 0;
}

/**
 * Generates a per-build randomized invertible 32-bit MBA codec over field values.
 *
 * Pipeline (Encoding -> Decoding):
 *   Enc(v, k):
 *     s1 = (v ^ k ^ c1) >>> 0
 *     s2 = (imul32(s1, m1) + c2) >>> 0
 *     s3 = (s2 ^ ((k << r1) | (k >>> (32 - r1)))) >>> 0
 *     s4 = (imul32(s3, m2) + c3) >>> 0
 *   Dec(e, k):
 *     d1 = imul32((e - c3) >>> 0, inv_m2)
 *     d2 = ((d1 | rk) - (d1 & rk)) >>> 0   [MBA form of d1 ^ rk]
 *     d3 = imul32((d2 - c2) >>> 0, inv_m1)
 *     v  = ((d3 + kx) - 2 * (d3 & kx)) >>> 0 [MBA form of d3 ^ kx] + zero-sum noise
 */
export function createMbaCodec(rng, codecId = 0) {
    const randU32 = () => Math.floor(rng() * MOD32) >>> 0;
    const randOdd = () => (randU32() | 1) >>> 0;

    const c1 = randU32();
    const c2 = randU32();
    const c3 = randU32();
    const m1 = randOdd();
    const m2 = randOdd();
    const invM1 = modInv32(m1);
    const invM2 = modInv32(m2);
    const r1 = 1 + Math.floor(rng() * 30);
    const r2 = 32 - r1;
    const noiseM = randU32();
    const saltK = randU32();
    const variant = Math.floor(rng() * 3);

    const rotL = (x, s) => (((x << s) | (x >>> (32 - s))) >>> 0);

    function encode(val, key = 0) {
        const v = val >>> 0;
        const k = (key >>> 0) ^ saltK;
        const kx = (k ^ c1) >>> 0;
        const s1 = (v ^ kx) >>> 0;
        const s2 = (imul32(s1, m1) + c2) >>> 0;
        const rk = rotL(k, r1);
        const s3 = (s2 ^ rk) >>> 0;
        const s4 = (imul32(s3, m2) + c3) >>> 0;
        return s4 >>> 0;
    }

    function decode(enc, key = 0) {
        const e = enc >>> 0;
        const k = (key >>> 0) ^ saltK;
        const rk = rotL(k, r1);
        const kx = (k ^ c1) >>> 0;
        const d1 = imul32((e - c3) >>> 0, invM2);
        const d2 = (d1 ^ rk) >>> 0;
        const d3 = imul32((d2 - c2) >>> 0, invM1);
        return (d3 ^ kx) >>> 0;
    }

    // Self-verify bijection on creation
    for (const tv of [0, 1, 2, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, randU32()]) {
        const tk = randU32();
        if (decode(encode(tv, tk), tk) !== (tv >>> 0)) {
            throw new Error(`MBA codec self-check failed on codec ${codecId}`);
        }
    }

    /**
     * Emit Lua decode function body: function(U, e, key) -> uint32
     * Expects U[bx], U[ba], U[bo], U[bn], U[lr], U[ls], U[rs], and U:Ta(a, b).
     * Uses MBA identities + zero-sum identity noise to resist symbolic pattern matching.
     */
    function emitLuaDecoderFn(uSym) {
        const { bx, ba, bo, bn, lr, ta } = uSym;
        const sub32 = (a, b) => `(((${a})-${b})%4294967296)`;
        const add32 = (a, b) => `(((${a})+(${b}))%4294967296)`;
        const mbaXor = (x, y, mode) => {
            if (mode === 0) return `(${uSym.bo}(${x},${y})-${uSym.ba}(${x},${y}))`;
            if (mode === 1) return `((${x}+${y})-2*${uSym.ba}(${x},${y}))`;
            return `${uSym.bx}(${x},${y})`;
        };

        // Zero-sum Luraph-style MBA identity: Ta(M, z) + Ta(M, ~z) + M == 0 (mod 2^32)
        const zeroNoise = (zExpr) =>
            `(${uSym.ta}(${noiseM},${zExpr})+${uSym.ta}(${noiseM},${uSym.bn}(${zExpr}))+${noiseM})`;

        const d1Expr = `${uSym.ta}(${sub32("_e", c3)},${invM2})`;
        const d2Expr = mbaXor("_d1", "_rk", variant);
        const d3Expr = `${uSym.ta}(${sub32("_d2", c2)},${invM1})`;
        const vExpr = variant === 2
            ? add32(`${mbaXor("_d3", "_kx", 0)}`, zeroNoise("_rk"))
            : add32(`${mbaXor("_d3", "_kx", 1)}`, zeroNoise("_e"));

        return `function(_e,_k) local _kk=${uSym.bx}(_k,${saltK});local _rk=${uSym.lr}(_kk,${r1});local _kx=${uSym.bx}(_kk,${c1});` +
            `local _d1=${d1Expr};local _d2=${d2Expr};local _d3=${d3Expr};` +
            `return (${vExpr})%4294967296 end`;
    }

    return {
        codecId,
        c1, c2, c3, m1, m2, invM1, invM2, r1, r2, saltK,
        encode,
        decode,
        emitLuaDecoderFn,
    };
}

/**
 * Generates diverse, unique per-call-site opaque boolean expressions (never repeats {11,22,33,44}).
 */
export function emitOpaquePredicate(rng, uSym, truthy = true) {
    const a = 0x101 + Math.floor(rng() * 0x7FFFFE00);
    const b = 0x101 + Math.floor(rng() * 0x7FFFFE00);
    const c = 0x11 + Math.floor(rng() * 0x7FFF);
    const variant = Math.floor(rng() * 10);
    const cmp = truthy ? "==" : "~=";

    switch (variant) {
        case 0:
            // (a ^ b) + 2*(a & b) == (a + b) (exact < 2^32 since a,b < 2^31)
            return `((${uSym.bx}(${a},${b})+2*${uSym.ba}(${a},${b}))${cmp}(${a + b}))`;
        case 1:
            // (a ^ b) == (a | b) - (a & b)
            return `(${uSym.bx}(${a},${b})${cmp}(${uSym.bo}(${a},${b})-${uSym.ba}(${a},${b})))`;
        case 2:
            // (a | b) == (a + b - (a & b))
            return `(${uSym.bo}(${a},${b})${cmp}(${a + b}-${uSym.ba}(${a},${b})))`;
        case 3:
            // c*(c+1) % 2 == 0
            return `(((${c}*(${c}+1))%2)${cmp}0)`;
        case 4: {
            // 7*x^2 - 1 != y^2 (or Fermat-style small parity mod 8: (2c+1)^2 % 8 == 1)
            const odd = (c * 2 + 1) % 4096;
            return `((((${odd})*(${odd}))%8)${cmp}1)`;
        }
        case 5: {
            // Bitwise absorption: (a & (a | b)) == a
            return `(${uSym.ba}(${a},${uSym.bo}(${a},${b}))${cmp}${a})`;
        }
        case 6: {
            // Double negation / complement identity: ((a ^ 0xFFFFFFFF) ^ 0xFFFFFFFF) == a
            return `(${uSym.bn}(${uSym.bn}(${a}))${cmp}${a})`;
        }
        case 7: {
            // Modular multiply zero-sum identity: (Ta(c, a) + Ta(c, ~a) + c) % 2^32 == 0
            return `(((${uSym.ta}(${c},${a})+${uSym.ta}(${c},${uSym.bn}(${a}))+${c})%4294967296)${cmp}0)`;
        }
        case 8: {
            // De Morgan 32-bit: ~(a | b) == (~a & ~b)
            return `(${uSym.bn}(${uSym.bo}(${a},${b}))${cmp}${uSym.ba}(${uSym.bn}(${a}),${uSym.bn}(${b})))`;
        }
        default: {
            // Affine residue: ((c * p) % p) == 0 where p is prime
            const primes = [7, 11, 13, 17, 19, 23, 29, 31, 37, 41];
            const p = primes[Math.floor(rng() * primes.length)];
            return `((((${c}*${p})+(${b % p === 0 ? 1 : 0}))%${p})${cmp}${(b % p === 0 ? 1 : 0)})`;
        }
    }
}
