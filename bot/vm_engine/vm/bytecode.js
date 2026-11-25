export function emit(chunk, op, ...args) {
    chunk.code.push(op);
    for (const arg of args)
        chunk.code.push(arg);
}
export function addConst(chunk, value) {
    const i = chunk.K.indexOf(value);
    if (i >= 0)
        return i;
    chunk.K.push(value);
    return chunk.K.length - 1;
}
export const RK_OFFSET = 2048;
export function RK(kIndex) {
    return kIndex + RK_OFFSET;
}
export function isRK_K(rk) {
    return rk >= RK_OFFSET;
}
export function rkToK(rk) {
    return rk - RK_OFFSET;
}

export const V5Op = {
    NOP: 0,
    LOADK: 1,
    LOADNIL: 2,
    LOADBOOL: 3,
    MOVE: 4,
    GETGLOBAL: 5,
    SETGLOBAL: 6,
    GETTABLE: 7,
    SETTABLE: 8,
    NEWTABLE: 9,
    ADD: 10,
    SUB: 11,
    MUL: 12,
    DIV: 13,
    MOD: 14,
    POW: 15,
    IDIV: 16,
    UNM: 17,
    NOT: 18,
    LEN: 19,
    CONCAT: 20,
    JMP: 21,
    EQ: 22,
    LT: 23,
    LE: 24,
    TEST: 25,
    TESTSET: 26,
    CALL: 27,
    TAILCALL: 28,
    RETURN: 29,
    FORPREP: 30,
    FORLOOP: 31,
    TFORLOOP: 32,
    SETLIST: 33,
    CLOSURE: 34,
    VARARG: 35,
    SELF: 36,
    GETUPVAL: 37,
    SETUPVAL: 38,
    CLOSEUPVAL: 39,
    PCALL: 40,
    XPCALL: 41,
    ITERPREP: 42,
    LOADKX: 43,
    EXTRAARG: 44,
    // Fused Superoperators
    F_TEST_JMP: 45,
    F_EQ_JMP: 46,
    F_LT_JMP: 47,
    F_LE_JMP: 48,
    F_TESTSET_JMP: 49,
    F_GGET: 50,
    F_LOADKK: 51,
    F_MOVE_MOVE: 52,
    F_SELF_CALL: 53,
    F_GGET_CALL: 54,
    F_LOADK_RET: 55,
    F_MOVE_RET: 56,
    // Sentinel v5.0 Specialized & Control Opcodes
    S_CALL0: 57,
    S_CALL1: 58,
    S_CALL2: 59,
    S_GETFIELD_K: 60,
    S_SETFIELD_K: 61,
    S_UPVAL_GET: 62,
    S_ADD_K: 63,
    S_SUB_K: 64,
    S_MUL_K: 65,
    F_TFORLOOP_JMP: 66,
    OP_MODE_SWITCH: 67,
    OP_DECRYPT_BLK: 68,
    OP_MBA_DECODE_0: 69,
    OP_MBA_DECODE_1: 70,
    OP_MBA_DECODE_2: 71,
    OP_MBA_DECODE_3: 72,
    // Sentinel v5.1 APEX Hot-Loop Specialized Opcodes
    S_CALL0_VOID: 73,
    S_CALL1_VOID: 74,
    S_CALL2_VOID: 75,
    S_CALL3: 76,
    S_MOD_K: 77,
};

export const REG_OPCODE_COUNT = 57;
export const V5_OPCODE_COUNT = 78;

export function regEmit(chunk, op, A = 0, B = 0, C = 0) {
    const pos = chunk.code.length;
    chunk.code.push(op, A, B, C);
    chunk.nInstructions++;
    if (A >= 0 && A < RK_OFFSET)
        chunk.maxRegs = Math.max(chunk.maxRegs, A + 1);
    if (B >= 0 && B < RK_OFFSET)
        chunk.maxRegs = Math.max(chunk.maxRegs, B + 1);
    if (C >= 0 && C < RK_OFFSET)
        chunk.maxRegs = Math.max(chunk.maxRegs, C + 1);
    return pos;
}
export function regPatch(chunk, pos, field, value) {
    const offset = field === 'op' ? 0 : field === 'A' ? 1 : field === 'B' ? 2 : 3;
    chunk.code[pos + offset] = value;
}
export function regPC(chunk) {
    return chunk.nInstructions;
}
export function regAddConst(chunk, value) {
    const i = chunk.K.indexOf(value);
    if (i >= 0)
        return i;
    chunk.K.push(value);
    return chunk.K.length - 1;
}
export function createRegChunk() {
    return {
        K: [],
        code: [],
        nInstructions: 0,
        maxRegs: 0,
        nParams: 0,
        isVararg: false,
    };
}
export function regAddProto(parent, proto) {
    if (!parent.protos)
        parent.protos = [];
    parent.protos.push(proto);
    return parent.protos.length - 1;
}
