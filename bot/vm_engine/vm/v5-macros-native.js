// language: JavaScript, file: v5-macros-native.js, target: Node.js ESM
// PAYOMBOYZ Sentinel v5.3 APEX: Macro Preprocessing, LPH_ATTRIBUTES, Execution Tiers, Lexical Free-Var Analysis & Hardened Native Luau Emitter

const OBFUSCATED_MACROS = new Set(["PBZ_OBFUSCATED", "LPH_OBFUSCATED", "MCY_OBFUSCATED"]);
const LINE_MACROS = new Set(["PBZ_LINE", "LPH_LINE", "MCY_LINE"]);
const CRASH_MACROS = new Set(["PBZ_CRASH", "LPH_CRASH", "MCY_CRASH"]);
const JIT_MACROS = new Set(["PBZ_JIT", "LPH_JIT", "MCY_JIT"]);
const JITMAX_MACROS = new Set(["PBZ_JITMAX", "LPH_JIT_MAX", "MCY_JITMAX"]);
const NO_VIRT_MACROS = new Set(["PBZ_NO_VIRTUALIZE", "LPH_NO_VIRTUALIZE", "MCY_NO_VIRTUALIZE"]);
const ATTR_MACROS = new Set(["LPH_ATTRIBUTES", "PBZ_ATTRIBUTES", "MCY_ATTRIBUTES"]);
const STRICT_ROBLOX_MACROS = new Set(["PBZ_STRICT_ROBLOX", "LPH_STRICT_ROBLOX"]);
const HOT_SIGNAL_RE = /RenderStepped|Heartbeat|Stepped/;

function extractAttrInfoFromCall(callExpr) {
    const info = { vmNone: false, tier: null, strictRoblox: false };
    const visitAttrArg = (node) => {
        if (!node || typeof node !== "object") return;
        if (node.type === "Identifier") {
            const nm = String(node.name || "").toUpperCase();
            if (nm === "NO_VIRTUALIZE" || nm === "NONE") info.vmNone = true;
            else if (nm === "FAST" || nm === "JIT") info.tier = "jit";
            else if (nm === "JIT_MAX" || nm === "JITMAX") info.tier = "jitmax";
            else if (nm === "SECURE" || nm === "ONYX" || nm === "MAX") info.tier = "max";
            else if (nm === "STRICT_ROBLOX" || nm === "ROBLOX_ONLY") info.strictRoblox = true;
        } else if (node.type === "StringLiteral") {
            const nm = String(node.value || "").toUpperCase();
            if (nm === "NONE" || nm === "NO_VIRTUALIZE") info.vmNone = true;
            else if (nm === "FAST" || nm === "JIT") info.tier = "jit";
            else if (nm === "JIT_MAX" || nm === "JITMAX") info.tier = "jitmax";
            else if (nm === "SECURE" || nm === "ONYX" || nm === "MAX") info.tier = "max";
            else if (nm === "STRICT_ROBLOX" || nm === "ROBLOX_ONLY") info.strictRoblox = true;
        } else if (node.type === "CallExpression") {
            const cname = node.callee?.type === "Identifier" ? String(node.callee.name || "").toUpperCase() : "";
            const arg0 = node.args?.[0];
            if (cname === "VM") {
                const v = (arg0?.type === "Identifier" ? arg0.name : arg0?.value || "").toUpperCase();
                if (v === "NONE") info.vmNone = true;
                else if (v === "ONYX" || v === "MAX") info.tier = "max";
            } else if (cname === "PRESET") {
                const v = (arg0?.type === "Identifier" ? arg0.name : arg0?.value || "").toUpperCase();
                if (v === "FAST") info.tier = "jit";
                else if (v === "SECURE" || v === "ONYX") info.tier = "max";
            } else if (cname === "STRICT_ROBLOX" || cname === "ROBLOX_ONLY") {
                info.strictRoblox = arg0?.type === "BooleanLiteral" ? Boolean(arg0.value) : true;
            }
            for (const a of node.args || []) visitAttrArg(a);
        } else if (node.type === "TableConstructor") {
            for (const f of node.fields || []) {
                if (f.kind === "named") {
                    const k = String(f.name || "").toUpperCase();
                    if (k === "VM" && f.value?.value && String(f.value.value).toUpperCase() === "NONE") info.vmNone = true;
                    if (k === "STRICT_ROBLOX" && f.value?.value !== false) info.strictRoblox = true;
                }
                visitAttrArg(f.value);
            }
        }
    };
    for (const arg of callExpr.args || []) visitAttrArg(arg);
    return info;
}

function parseLeadingAttributes(body, scopes) {
    const out = { vmNone: false, tier: null, strictRoblox: false, stmts: body || [] };
    if (!Array.isArray(body) || body.length === 0) return out;
    const kept = [];
    let leading = true;
    for (const st of body) {
        if (leading && st?.type === "FunctionCallStatement" && st.call?.type === "CallExpression" &&
            st.call.callee?.type === "Identifier" && !hasLocalInScopes(scopes, st.call.callee.name)) {
            const cname = st.call.callee.name;
            if (ATTR_MACROS.has(cname)) {
                const parsed = extractAttrInfoFromCall(st.call);
                if (parsed.vmNone) out.vmNone = true;
                if (parsed.tier) out.tier = parsed.tier;
                if (parsed.strictRoblox) out.strictRoblox = true;
                continue;
            }
            if (STRICT_ROBLOX_MACROS.has(cname)) {
                out.strictRoblox = true;
                continue;
            }
        }
        leading = false;
        kept.push(st);
    }
    out.stmts = kept;
    return out;
}

const LUAU_KEYWORDS = new Set([
    "and", "break", "continue", "do", "else", "elseif", "end", "export", "false",
    "for", "function", "if", "in", "local", "nil", "not", "or",
    "repeat", "return", "then", "true", "until", "while", "goto", "type",
]);

const RESERVED_MANGLED = new Set(["_G", "_ENV", "self"]);

const IMMUTABLE_GLOBALS = new Set([
    "math", "string", "table", "bit32", "bit", "os", "utf8", "buffer", "coroutine", "task",
    "Vector3", "Vector2", "Vector3int16", "Vector2int16", "CFrame", "Color3", "UDim", "UDim2",
    "Rect", "Ray", "Enum", "Instance", "NumberRange", "NumberSequence", "NumberSequenceKeypoint",
    "ColorSequence", "ColorSequenceKeypoint", "TweenInfo", "RaycastParams", "OverlapParams",
    "DateTime", "Random", "Font", "BrickColor", "PhysicalProperties", "PathWaypoint", "Faces", "Axes",
    "pairs", "ipairs", "next", "pcall", "xpcall", "select", "tonumber", "tostring",
    "type", "typeof", "unpack", "error", "assert", "print", "warn", "tick", "time",
    "wait", "spawn", "delay", "rawget", "rawset", "rawequal", "rawlen", "getmetatable", "setmetatable",
    "game", "workspace", "RunService", "Players", "ReplicatedStorage", "UserInputService",
]);

const SUPPORTED_STMT_TYPES = new Set([
    "LocalStatement", "AssignmentStatement", "CompoundAssignmentStatement", "FunctionCallStatement",
    "DoStatement", "WhileStatement", "RepeatStatement", "IfStatement",
    "ForNumericStatement", "ForInStatement", "ReturnStatement", "BreakStatement",
    "ContinueStatement", "LocalFunctionStatement", "FunctionStatement",
    "TypeStatement", "ExportTypeStatement", "TypeFunctionStatement", "ExportTypeFunctionStatement",
]);

const SUPPORTED_EXPR_TYPES = new Set([
    "Identifier", "NilLiteral", "BooleanLiteral", "NumberLiteral", "StringLiteral",
    "StringInterpolation", "VarargExpression", "BinaryExpression", "UnaryExpression",
    "CallExpression", "MethodCallExpression", "IndexExpression", "MemberExpression",
    "TableConstructor", "FunctionExpression", "ParenExpression", "TypeAssertion", "IfElseExpression",
]);

function hasLocalInScopes(scopes, name) {
    for (let i = scopes.length - 1; i >= 0; i--) {
        if (scopes[i].has(name)) return true;
    }
    return false;
}

function snapshotEnclosingLocals(scopes) {
    const out = new Set();
    for (const s of scopes) {
        for (const name of s) out.add(name);
    }
    return out;
}

function containsHotSignalName(expr) {
    if (!expr || typeof expr !== "object") return false;
    switch (expr.type) {
        case "Identifier":
            return HOT_SIGNAL_RE.test(expr.name || "");
        case "MemberExpression":
            return HOT_SIGNAL_RE.test(expr.property || "") || containsHotSignalName(expr.object);
        case "IndexExpression":
            return (expr.index?.type === "StringLiteral" && HOT_SIGNAL_RE.test(expr.index.value || "")) ||
                containsHotSignalName(expr.object);
        case "ParenExpression":
        case "TypeAssertion":
            return containsHotSignalName(expr.expression);
        case "CallExpression":
        case "MethodCallExpression":
            return containsHotSignalName(expr.object || expr.callee);
        default:
            return false;
    }
}

function checkNativeEligibility(fnNode, enclosingLocals, options = {}) {
    if (!fnNode || fnNode.type !== "FunctionExpression") return false;
    if (options.disableNative || options.native === false) return false;

    const fnScopes = [new Set()];
    let fnIsVararg = false;
    let localCount = 0;

    for (const p of fnNode.params || []) {
        if (p.variadic) {
            fnIsVararg = true;
        } else if (p.name) {
            fnScopes[0].add(p.name);
            localCount++;
        }
    }

    let ok = true;
    const varargStack = [fnIsVararg];

    const push = () => fnScopes.push(new Set());
    const pop = () => fnScopes.pop();
    const addLocal = (name) => {
        if (name) {
            fnScopes[fnScopes.length - 1].add(name);
            if (varargStack.length === 1) localCount++;
        }
    };

    const checkIdent = (name) => {
        if (!name || name === "nil" || name === "true" || name === "false") return;
        if (!hasLocalInScopes(fnScopes, name) && enclosingLocals.has(name)) {
            ok = false;
        }
    };

    const visitExpr = (e) => {
        if (!ok || !e || typeof e !== "object") return;
        if (!SUPPORTED_EXPR_TYPES.has(e.type)) {
            ok = false;
            return;
        }
        switch (e.type) {
            case "Identifier":
                checkIdent(e.name);
                break;
            case "VarargExpression":
                if (!varargStack[varargStack.length - 1]) ok = false;
                break;
            case "BinaryExpression":
                visitExpr(e.left);
                visitExpr(e.right);
                break;
            case "UnaryExpression":
                visitExpr(e.argument);
                break;
            case "CallExpression":
                visitExpr(e.callee);
                e.args?.forEach(visitExpr);
                break;
            case "MethodCallExpression":
                visitExpr(e.object);
                e.args?.forEach(visitExpr);
                break;
            case "IndexExpression":
                visitExpr(e.object);
                visitExpr(e.index);
                break;
            case "MemberExpression":
                visitExpr(e.object);
                break;
            case "TableConstructor":
                e.fields?.forEach((f) => {
                    if (f.kind === "index") visitExpr(f.index);
                    visitExpr(f.value);
                });
                break;
            case "FunctionExpression": {
                push();
                let va = false;
                for (const p of e.params || []) {
                    if (p.variadic) va = true;
                    else fnScopes[fnScopes.length - 1].add(p.name);
                }
                varargStack.push(va);
                e.body?.forEach(visitStmt);
                varargStack.pop();
                pop();
                break;
            }
            case "ParenExpression":
            case "TypeAssertion":
                visitExpr(e.expression);
                break;
            case "IfElseExpression":
                visitExpr(e.condition);
                visitExpr(e.thenExp);
                e.elseifClauses?.forEach((c) => { visitExpr(c.condition); visitExpr(c.value); });
                visitExpr(e.elseExp);
                break;
            case "StringInterpolation":
                e.parts?.forEach((p) => { if (typeof p !== "string") visitExpr(p); });
                break;
        }
    };

    const visitVar = (v) => {
        if (!ok || !v || typeof v !== "object") return;
        if (v.type === "Identifier") {
            checkIdent(v.name);
        } else if (v.type === "IndexExpression") {
            visitExpr(v.object);
            visitExpr(v.index);
        } else if (v.type === "MemberExpression") {
            visitExpr(v.object);
        } else {
            ok = false;
        }
    };

    const visitStmt = (s) => {
        if (!ok || !s || typeof s !== "object") return;
        if (!SUPPORTED_STMT_TYPES.has(s.type)) {
            ok = false;
            return;
        }
        switch (s.type) {
            case "LocalStatement":
                s.values?.forEach(visitExpr);
                s.vars?.forEach((v) => addLocal(v.name));
                break;
            case "AssignmentStatement":
                s.vars?.forEach(visitVar);
                s.values?.forEach(visitExpr);
                break;
            case "CompoundAssignmentStatement":
                visitVar(s.var);
                visitExpr(s.value);
                break;
            case "FunctionCallStatement":
                if (s.call?.type === "CallExpression" && s.call.callee?.type === "Identifier" &&
                    ATTR_MACROS.has(s.call.callee.name) && !hasLocalInScopes(fnScopes, s.call.callee.name)) {
                    break;
                }
                visitExpr(s.call);
                break;
            case "DoStatement":
                push();
                s.body?.forEach(visitStmt);
                pop();
                break;
            case "WhileStatement":
                visitExpr(s.condition);
                push();
                s.body?.forEach(visitStmt);
                pop();
                break;
            case "RepeatStatement":
                push();
                s.body?.forEach(visitStmt);
                visitExpr(s.condition);
                pop();
                break;
            case "IfStatement":
                visitExpr(s.condition);
                push();
                s.thenBody?.forEach(visitStmt);
                pop();
                s.elseifClauses?.forEach((c) => {
                    visitExpr(c.condition);
                    push();
                    c.body?.forEach(visitStmt);
                    pop();
                });
                if (s.elseBody) {
                    push();
                    s.elseBody.forEach(visitStmt);
                    pop();
                }
                break;
            case "ForNumericStatement":
                visitExpr(s.start);
                visitExpr(s.end);
                if (s.step) visitExpr(s.step);
                push();
                addLocal(s.var?.name);
                s.body?.forEach(visitStmt);
                pop();
                break;
            case "ForInStatement":
                s.iter?.forEach(visitExpr);
                push();
                s.vars?.forEach((v) => addLocal(v.name));
                s.body?.forEach(visitStmt);
                pop();
                break;
            case "LocalFunctionStatement": {
                addLocal(s.name);
                push();
                let va = false;
                for (const p of s.params || []) {
                    if (p.variadic) va = true;
                    else fnScopes[fnScopes.length - 1].add(p.name);
                }
                varargStack.push(va);
                s.body?.forEach(visitStmt);
                varargStack.pop();
                pop();
                break;
            }
            case "FunctionStatement": {
                if (s.name?.base?.type === "Identifier") {
                    checkIdent(s.name.base.name);
                } else {
                    visitExpr(s.name?.base);
                }
                push();
                if (s.name?.method) fnScopes[fnScopes.length - 1].add("self");
                let va = false;
                for (const p of s.params || []) {
                    if (p.variadic) va = true;
                    else fnScopes[fnScopes.length - 1].add(p.name);
                }
                varargStack.push(va);
                s.body?.forEach(visitStmt);
                varargStack.pop();
                pop();
                break;
            }
            case "ReturnStatement":
                s.values?.forEach(visitExpr);
                break;
        }
    };

    fnNode.body?.forEach(visitStmt);
    // Keep well below Luau's 200-local limit (hoisted globals + entry locals need headroom)
    if (localCount > 140) return false;
    return ok;
}

/**
 * Preprocess PBZ_/LPH_/MCY_ macros, execution tiers, and auto-native RunService callbacks.
 * @param {object} ast - Parsed Luau Chunk AST
 * @param {object} [options]
 * @returns {{ ast: object, nativeFuncs: Array<{ id: number, fnNode: object }> }}
 */
export function preprocessMacrosAndTiers(ast, options = {}) {
    if (!ast || typeof ast !== "object") return { ast, nativeFuncs: [] };

    let strictRoblox = false;
    const nativeFuncs = [];
    const scopes = [new Set()];
    const push = () => scopes.push(new Set());
    const pop = () => scopes.pop();
    const addLocal = (name) => {
        if (name) scopes[scopes.length - 1].add(name);
    };

    const makeNativeRef = (fnNode, loc) => {
        const id = nativeFuncs.length + 1;
        nativeFuncs.push({ id, fnNode });
        return {
            type: "IndexExpression",
            object: { type: "Identifier", name: "__PBZ_NF__", loc },
            index: { type: "NumberLiteral", value: String(id), loc },
            loc,
        };
    };

    const unwrapParensFn = (node) => {
        if (!node) return null;
        if (node.type === "FunctionExpression") return node;
        if (node.type === "ParenExpression" && node.expression?.type === "FunctionExpression") {
            return node.expression;
        }
        return null;
    };

    const tryHandleNativeCandidate = (fnExpr, loc, fallbackNode) => {
        if (!fnExpr) return fallbackNode;
        const enclosingLocals = snapshotEnclosingLocals(scopes);
        if (checkNativeEligibility(fnExpr, enclosingLocals, options)) {
            return makeNativeRef(fnExpr, loc);
        }
        fnExpr.__pbzTier = "jitmax";
        return fallbackNode;
    };

    const transformVar = (v) => {
        if (!v || typeof v !== "object") return v;
        if (v.type === "IndexExpression") {
            return { ...v, object: transformExpr(v.object), index: transformExpr(v.index) };
        }
        if (v.type === "MemberExpression") {
            return { ...v, object: transformExpr(v.object) };
        }
        return v;
    };

    const transformExpr = (e) => {
        if (!e || typeof e !== "object") return e;
        switch (e.type) {
            case "Identifier": {
                if (!hasLocalInScopes(scopes, e.name)) {
                    if (OBFUSCATED_MACROS.has(e.name)) {
                        return { type: "BooleanLiteral", value: true, loc: e.loc };
                    }
                    if (LINE_MACROS.has(e.name)) {
                        const line = e.line || e.loc?.start?.line || 1;
                        return { type: "NumberLiteral", value: String(line), loc: e.loc };
                    }
                }
                return e;
            }
            case "BinaryExpression":
                return { ...e, left: transformExpr(e.left), right: transformExpr(e.right) };
            case "UnaryExpression":
                return { ...e, argument: transformExpr(e.argument) };
            case "ParenExpression":
                return { ...e, expression: transformExpr(e.expression) };
            case "TypeAssertion":
                return { ...e, expression: transformExpr(e.expression) };
            case "IndexExpression":
                return { ...e, object: transformExpr(e.object), index: transformExpr(e.index) };
            case "MemberExpression":
                return { ...e, object: transformExpr(e.object) };
            case "TableConstructor":
                return {
                    ...e,
                    fields: e.fields?.map((f) => {
                        if (f.kind === "index") {
                            return { ...f, index: transformExpr(f.index), value: transformExpr(f.value) };
                        }
                        return { ...f, value: transformExpr(f.value) };
                    }),
                };
            case "IfElseExpression":
                return {
                    ...e,
                    condition: transformExpr(e.condition),
                    thenExp: transformExpr(e.thenExp),
                    elseifClauses: e.elseifClauses?.map((c) => ({
                        ...c,
                        condition: transformExpr(c.condition),
                        value: transformExpr(c.value),
                    })),
                    elseExp: transformExpr(e.elseExp),
                };
            case "StringInterpolation":
                return {
                    ...e,
                    parts: e.parts?.map((p) => (typeof p === "string" ? p : transformExpr(p))),
                };
            case "FunctionExpression": {
                push();
                for (const p of e.params || []) {
                    if (!p.variadic) addLocal(p.name);
                }
                const attr = parseLeadingAttributes(e.body || [], scopes);
                if (attr.strictRoblox) strictRoblox = true;
                const body = attr.stmts.map(transformStmt);
                pop();
                const outFn = { ...e, body };
                if (attr.tier) outFn.__pbzTier = attr.tier;
                else if (e.__pbzTier) outFn.__pbzTier = e.__pbzTier;
                if (attr.vmNone) {
                    return tryHandleNativeCandidate(outFn, e.loc, outFn);
                }
                return outFn;
            }
            case "CallExpression": {
                if (e.callee?.type === "Identifier" && !hasLocalInScopes(scopes, e.callee.name)) {
                    const mName = e.callee.name;
                    if (CRASH_MACROS.has(mName)) {
                        return {
                            ...e,
                            callee: { type: "Identifier", name: "__PBZ_CRASH__", loc: e.callee.loc },
                            args: [],
                        };
                    }
                    if (JIT_MACROS.has(mName) && e.args?.length >= 1) {
                        const arg0 = transformExpr(e.args[0]);
                        const fnNode = unwrapParensFn(arg0);
                        if (fnNode) fnNode.__pbzTier = "jit";
                        return arg0;
                    }
                    if (JITMAX_MACROS.has(mName) && e.args?.length >= 1) {
                        const arg0 = transformExpr(e.args[0]);
                        const fnNode = unwrapParensFn(arg0);
                        if (fnNode) fnNode.__pbzTier = "jitmax";
                        return arg0;
                    }
                    if (NO_VIRT_MACROS.has(mName) && e.args?.length >= 1) {
                        const arg0 = transformExpr(e.args[0]);
                        const fnNode = unwrapParensFn(arg0);
                        return fnNode ? tryHandleNativeCandidate(fnNode, e.loc, arg0) : arg0;
                    }
                }
                return {
                    ...e,
                    callee: transformExpr(e.callee),
                    args: e.args?.map(transformExpr),
                };
            }
            case "MethodCallExpression": {
                const obj = transformExpr(e.object);
                const args = e.args ? e.args.map(transformExpr) : [];
                let targetIdx = -1;
                if ((e.method === "Connect" || e.method === "connect") && args.length >= 1 && containsHotSignalName(obj)) {
                    targetIdx = 0;
                } else if (e.method === "BindToRenderStep" && args.length >= 3) {
                    targetIdx = 2;
                }
                if (targetIdx >= 0) {
                    const candidate = args[targetIdx];
                    const fnNode = unwrapParensFn(candidate);
                    if (fnNode && !fnNode.__pbzTier) {
                        args[targetIdx] = tryHandleNativeCandidate(fnNode, candidate.loc || e.loc, candidate);
                    }
                }
                return { ...e, object: obj, args };
            }
            default:
                return e;
        }
    };

    const transformStmt = (s) => {
        if (!s || typeof s !== "object") return s;
        switch (s.type) {
            case "LocalStatement": {
                const values = s.values?.map(transformExpr);
                s.vars?.forEach((v) => addLocal(v.name));
                return { ...s, values };
            }
            case "AssignmentStatement":
                return {
                    ...s,
                    vars: s.vars?.map(transformVar),
                    values: s.values?.map(transformExpr),
                };
            case "CompoundAssignmentStatement":
                return { ...s, var: transformVar(s.var), value: transformExpr(s.value) };
            case "FunctionCallStatement":
                return { ...s, call: transformExpr(s.call) };
            case "DoStatement": {
                push();
                const body = s.body?.map(transformStmt);
                pop();
                return { ...s, body };
            }
            case "WhileStatement": {
                const condition = transformExpr(s.condition);
                push();
                const body = s.body?.map(transformStmt);
                pop();
                return { ...s, condition, body };
            }
            case "RepeatStatement": {
                push();
                const body = s.body?.map(transformStmt);
                const condition = transformExpr(s.condition);
                pop();
                return { ...s, body, condition };
            }
            case "IfStatement": {
                const condition = transformExpr(s.condition);
                push();
                const thenBody = s.thenBody?.map(transformStmt);
                pop();
                const elseifClauses = s.elseifClauses?.map((c) => {
                    const cCond = transformExpr(c.condition);
                    push();
                    const cBody = c.body?.map(transformStmt);
                    pop();
                    return { ...c, condition: cCond, body: cBody };
                });
                let elseBody;
                if (s.elseBody) {
                    push();
                    elseBody = s.elseBody.map(transformStmt);
                    pop();
                }
                return { ...s, condition, thenBody, elseifClauses, elseBody };
            }
            case "ForNumericStatement": {
                const start = transformExpr(s.start);
                const end = transformExpr(s.end);
                const step = s.step ? transformExpr(s.step) : undefined;
                push();
                addLocal(s.var?.name);
                const body = s.body?.map(transformStmt);
                pop();
                return { ...s, start, end, step, body };
            }
            case "ForInStatement": {
                const iter = s.iter?.map(transformExpr);
                push();
                s.vars?.forEach((v) => addLocal(v.name));
                const body = s.body?.map(transformStmt);
                pop();
                return { ...s, iter, body };
            }
            case "LocalFunctionStatement": {
                addLocal(s.name);
                push();
                for (const p of s.params || []) {
                    if (!p.variadic) addLocal(p.name);
                }
                const attr = parseLeadingAttributes(s.body || [], scopes);
                if (attr.strictRoblox) strictRoblox = true;
                const body = attr.stmts.map(transformStmt);
                pop();
                const outStmt = { ...s, body };
                if (attr.tier) outStmt.__pbzTier = attr.tier;
                else if (attr.vmNone) outStmt.__pbzTier = "jitmax";
                return outStmt;
            }
            case "FunctionStatement": {
                const base = s.name?.base?.type === "Identifier"
                    ? s.name.base
                    : transformExpr(s.name?.base);
                push();
                if (s.name?.method) addLocal("self");
                for (const p of s.params || []) {
                    if (!p.variadic) addLocal(p.name);
                }
                const attr = parseLeadingAttributes(s.body || [], scopes);
                if (attr.strictRoblox) strictRoblox = true;
                const body = attr.stmts.map(transformStmt);
                pop();
                const outStmt = { ...s, name: { ...s.name, base }, body };
                if (attr.tier) outStmt.__pbzTier = attr.tier;
                else if (attr.vmNone) outStmt.__pbzTier = "jitmax";
                return outStmt;
            }
            case "ReturnStatement":
                return { ...s, values: s.values?.map(transformExpr) };
            default:
                return s;
        }
    };

    const topAttr = parseLeadingAttributes(ast.body || [], scopes);
    if (topAttr.strictRoblox) strictRoblox = true;
    const nextAst = {
        ...ast,
        body: topAttr.stmts.map(transformStmt),
    };
    if (topAttr.tier) nextAst.__pbzTier = topAttr.tier;
    return { ast: nextAst, nativeFuncs, strictRoblox };
}

/**
 * Collect all unique string literals AND free global names inside extracted native functions
 * so every string and global reference can be served from the encrypted Master String Pool.
 * @param {Array<{ id: number, fnNode: object }>} nativeFuncs
 * @returns {string[]}
 */
export function collectNativeStrings(nativeFuncs) {
    const strings = new Set();
    if (!Array.isArray(nativeFuncs) || nativeFuncs.length === 0) return [];

    const visitFn = (fnNode, outerScopes) => {
        const scopes = outerScopes.map((s) => new Set(s));
        const fnScope = new Set();
        for (const p of fnNode.params || []) {
            if (!p.variadic && p.name) fnScope.add(p.name);
        }
        scopes.push(fnScope);

        const push = () => scopes.push(new Set());
        const pop = () => scopes.pop();
        const addLocal = (name) => { if (name) scopes[scopes.length - 1].add(name); };

        const recordIdent = (name) => {
            if (!name || name === "nil" || name === "true" || name === "false") return;
            if (!hasLocalInScopes(scopes, name)) strings.add(name);
        };

        const visitExpr = (e) => {
            if (!e || typeof e !== "object") return;
            switch (e.type) {
                case "StringLiteral":
                    strings.add(e.value);
                    break;
                case "StringInterpolation": {
                    let hasExpr = false;
                    for (const p of e.parts || []) {
                        if (typeof p === "string") strings.add(p);
                        else {
                            hasExpr = true;
                            visitExpr(p);
                        }
                    }
                    if (hasExpr) strings.add("tostring");
                    break;
                }
                case "Identifier":
                    recordIdent(e.name);
                    break;
                case "BinaryExpression":
                    visitExpr(e.left); visitExpr(e.right); break;
                case "UnaryExpression":
                    visitExpr(e.argument); break;
                case "CallExpression":
                    visitExpr(e.callee); e.args?.forEach(visitExpr); break;
                case "MethodCallExpression":
                    visitExpr(e.object); e.args?.forEach(visitExpr); break;
                case "IndexExpression":
                    visitExpr(e.object); visitExpr(e.index); break;
                case "MemberExpression":
                    visitExpr(e.object); break;
                case "TableConstructor":
                    e.fields?.forEach((f) => {
                        if (f.kind === "index") visitExpr(f.index);
                        visitExpr(f.value);
                    });
                    break;
                case "FunctionExpression":
                    visitFn(e, scopes);
                    break;
                case "ParenExpression":
                case "TypeAssertion":
                    visitExpr(e.expression); break;
                case "IfElseExpression":
                    visitExpr(e.condition); visitExpr(e.thenExp);
                    e.elseifClauses?.forEach((c) => { visitExpr(c.condition); visitExpr(c.value); });
                    visitExpr(e.elseExp); break;
            }
        };

        const visitVar = (v) => {
            if (!v || typeof v !== "object") return;
            if (v.type === "Identifier") recordIdent(v.name);
            else if (v.type === "IndexExpression") { visitExpr(v.object); visitExpr(v.index); }
            else if (v.type === "MemberExpression") { visitExpr(v.object); }
        };

        const visitStmt = (s) => {
            if (!s || typeof s !== "object") return;
            switch (s.type) {
                case "LocalStatement":
                    s.values?.forEach(visitExpr);
                    s.vars?.forEach((v) => addLocal(v.name));
                    break;
                case "AssignmentStatement":
                    s.vars?.forEach(visitVar); s.values?.forEach(visitExpr); break;
                case "CompoundAssignmentStatement":
                    visitVar(s.var); visitExpr(s.value); break;
                case "FunctionCallStatement":
                    visitExpr(s.call); break;
                case "DoStatement":
                    push(); s.body?.forEach(visitStmt); pop(); break;
                case "WhileStatement":
                    visitExpr(s.condition); push(); s.body?.forEach(visitStmt); pop(); break;
                case "RepeatStatement":
                    push(); s.body?.forEach(visitStmt); visitExpr(s.condition); pop(); break;
                case "IfStatement":
                    visitExpr(s.condition);
                    push(); s.thenBody?.forEach(visitStmt); pop();
                    s.elseifClauses?.forEach((c) => { visitExpr(c.condition); push(); c.body?.forEach(visitStmt); pop(); });
                    if (s.elseBody) { push(); s.elseBody.forEach(visitStmt); pop(); }
                    break;
                case "ForNumericStatement":
                    visitExpr(s.start); visitExpr(s.end); if (s.step) visitExpr(s.step);
                    push(); addLocal(s.var?.name); s.body?.forEach(visitStmt); pop();
                    break;
                case "ForInStatement":
                    s.iter?.forEach(visitExpr);
                    push(); s.vars?.forEach((v) => addLocal(v.name)); s.body?.forEach(visitStmt); pop();
                    break;
                case "LocalFunctionStatement":
                    addLocal(s.name);
                    push();
                    for (const p of s.params || []) { if (!p.variadic) addLocal(p.name); }
                    s.body?.forEach(visitStmt);
                    pop();
                    break;
                case "FunctionStatement":
                    if (s.name?.base?.type === "Identifier") recordIdent(s.name.base.name);
                    else visitExpr(s.name?.base);
                    push();
                    if (s.name?.method) addLocal("self");
                    for (const p of s.params || []) { if (!p.variadic) addLocal(p.name); }
                    s.body?.forEach(visitStmt);
                    pop();
                    break;
                case "ReturnStatement":
                    s.values?.forEach(visitExpr); break;
            }
        };

        fnNode.body?.forEach(visitStmt);
    };

    for (const entry of nativeFuncs) {
        if (entry?.fnNode) visitFn(entry.fnNode, []);
    }
    return Array.from(strings);
}

function generateMangledIdent(index) {
    let s = "";
    let n = index;
    while (n >= 0) {
        s = String.fromCharCode(97 + (n % 26)) + s;
        n = Math.floor(n / 26) - 1;
    }
    return "_" + s;
}

function emitEntryOpaqueGuard(rng, bxFn) {
    const a = 0x101 + Math.floor(rng() * 0x1FFFFE00);
    const b = 0x101 + Math.floor(rng() * 0x1FFFFE00);
    const c = 0x11 + Math.floor(rng() * 0x7FFF);
    const form = Math.floor(rng() * 5);
    let cond;
    if (form === 0 && bxFn) {
        cond = `${bxFn}(${a},${b})~=${(a ^ b) >>> 0}`;
    } else if (form === 1) {
        cond = `((${c}*(${c}+1))%2)~=0`;
    } else if (form === 2) {
        const odd = (c * 2 + 1) % 4096;
        cond = `(((${odd}*${odd})%8)~=1)`;
    } else if (form === 3 && bxFn) {
        const mask = 1 + Math.floor(rng() * 0xFE);
        cond = `${bxFn}(${a},${c})==${((a ^ c) ^ mask) >>> 0}`;
    } else {
        const primes = [7, 11, 13, 17, 19, 23, 29, 31];
        const p = primes[Math.floor(rng() * primes.length)];
        cond = `(((${c}*${p})%${p})~=0)`;
    }
    return `if ${cond} then return end`;
}

function needsReceiverParens(expr) {
    if (!expr) return false;
    switch (expr.type) {
        case "Identifier":
        case "MemberExpression":
        case "IndexExpression":
        case "CallExpression":
        case "MethodCallExpression":
        case "ParenExpression":
            return false;
        default:
            return true;
    }
}

/**
 * Emit a single-line, zero-plaintext, mangled native Luau function expression `function(...) ... end`.
 * Returns null if fnNode contains unsupported constructs.
 * @param {object} fnNode
 * @param {{ getStrCall: (s: string) => string, bxFn?: string, envVar?: string, rng?: () => number }} ctx
 * @returns {string|null}
 */
export function emitHardenedNativeLua(fnNode, ctx = {}) {
    if (!fnNode || fnNode.type !== "FunctionExpression") return null;

    const getStrCall = ctx.getStrCall || ((s) => JSON.stringify(s));
    const bxFn = ctx.bxFn || "bit32.bxor";
    const envVar = ctx.envVar || "_ENV";
    const rng = ctx.rng || Math.random;

    let nameIdx = 0;
    const undoStack = [[]];
    const flat = new Map();

    const nextMangled = () => {
        while (true) {
            const cand = generateMangledIdent(nameIdx++);
            if (!LUAU_KEYWORDS.has(cand) && !RESERVED_MANGLED.has(cand) && cand !== envVar && cand !== bxFn) {
                return cand;
            }
        }
    };

    const pushScope = () => undoStack.push([]);
    const popScope = () => {
        const undo = undoStack.pop();
        for (let i = undo.length - 1; i >= 0; i--) {
            const { name, prev } = undo[i];
            if (prev === undefined) flat.delete(name);
            else flat.set(name, prev);
        }
    };
    const declareLocal = (name) => {
        if (name === "self") {
            const prev = flat.get("self");
            undoStack[undoStack.length - 1].push({ name: "self", prev });
            flat.set("self", "self");
            return "self";
        }
        const mangled = nextMangled();
        const prev = flat.get(name);
        undoStack[undoStack.length - 1].push({ name, prev });
        flat.set(name, mangled);
        return mangled;
    };

    // Scan immutable read-only free globals to hoist once at function entry for 120 FPS loops
    const mutatedGlobals = new Set();
    const readImmutableGlobals = new Set();
    const scanScopes = [new Set()];
    for (const p of fnNode.params || []) {
        if (!p.variadic && p.name) scanScopes[0].add(p.name);
    }
    const scanPush = () => scanScopes.push(new Set());
    const scanPop = () => scanScopes.pop();
    const scanAdd = (n) => { if (n) scanScopes[scanScopes.length - 1].add(n); };

    const scanExpr = (e) => {
        if (!e || typeof e !== "object") return;
        switch (e.type) {
            case "Identifier":
                if (e.name && !hasLocalInScopes(scanScopes, e.name) && IMMUTABLE_GLOBALS.has(e.name)) {
                    readImmutableGlobals.add(e.name);
                }
                break;
            case "BinaryExpression": scanExpr(e.left); scanExpr(e.right); break;
            case "UnaryExpression": scanExpr(e.argument); break;
            case "CallExpression": scanExpr(e.callee); e.args?.forEach(scanExpr); break;
            case "MethodCallExpression": scanExpr(e.object); e.args?.forEach(scanExpr); break;
            case "IndexExpression": scanExpr(e.object); scanExpr(e.index); break;
            case "MemberExpression": scanExpr(e.object); break;
            case "TableConstructor":
                e.fields?.forEach((f) => { if (f.kind === "index") scanExpr(f.index); scanExpr(f.value); });
                break;
            case "FunctionExpression":
                scanPush();
                for (const p of e.params || []) { if (!p.variadic) scanAdd(p.name); }
                e.body?.forEach(scanStmt);
                scanPop();
                break;
            case "ParenExpression":
            case "TypeAssertion": scanExpr(e.expression); break;
            case "IfElseExpression":
                scanExpr(e.condition); scanExpr(e.thenExp);
                e.elseifClauses?.forEach((c) => { scanExpr(c.condition); scanExpr(c.value); });
                scanExpr(e.elseExp); break;
            case "StringInterpolation":
                e.parts?.forEach((p) => { if (typeof p !== "string") scanExpr(p); });
                break;
        }
    };
    const scanVar = (v) => {
        if (!v || typeof v !== "object") return;
        if (v.type === "Identifier") {
            if (v.name && !hasLocalInScopes(scanScopes, v.name)) mutatedGlobals.add(v.name);
        } else if (v.type === "IndexExpression") { scanExpr(v.object); scanExpr(v.index); }
        else if (v.type === "MemberExpression") { scanExpr(v.object); }
    };
    const scanStmt = (s) => {
        if (!s || typeof s !== "object") return;
        switch (s.type) {
            case "LocalStatement":
                s.values?.forEach(scanExpr);
                s.vars?.forEach((v) => scanAdd(v.name));
                break;
            case "AssignmentStatement":
                s.vars?.forEach(scanVar); s.values?.forEach(scanExpr); break;
            case "CompoundAssignmentStatement":
                scanVar(s.var); scanExpr(s.value); break;
            case "FunctionCallStatement": scanExpr(s.call); break;
            case "DoStatement": scanPush(); s.body?.forEach(scanStmt); scanPop(); break;
            case "WhileStatement": scanExpr(s.condition); scanPush(); s.body?.forEach(scanStmt); scanPop(); break;
            case "RepeatStatement": scanPush(); s.body?.forEach(scanStmt); scanExpr(s.condition); scanPop(); break;
            case "IfStatement":
                scanExpr(s.condition); scanPush(); s.thenBody?.forEach(scanStmt); scanPop();
                s.elseifClauses?.forEach((c) => { scanExpr(c.condition); scanPush(); c.body?.forEach(scanStmt); scanPop(); });
                if (s.elseBody) { scanPush(); s.elseBody.forEach(scanStmt); scanPop(); }
                break;
            case "ForNumericStatement":
                scanExpr(s.start); scanExpr(s.end); if (s.step) scanExpr(s.step);
                scanPush(); scanAdd(s.var?.name); s.body?.forEach(scanStmt); scanPop();
                break;
            case "ForInStatement":
                s.iter?.forEach(scanExpr); scanPush(); s.vars?.forEach((v) => scanAdd(v.name)); s.body?.forEach(scanStmt); scanPop();
                break;
            case "LocalFunctionStatement":
                scanAdd(s.name); scanPush();
                for (const p of s.params || []) { if (!p.variadic) scanAdd(p.name); }
                s.body?.forEach(scanStmt); scanPop();
                break;
            case "FunctionStatement":
                if (s.name?.base?.type === "Identifier" && !s.name?.method && !hasLocalInScopes(scanScopes, s.name.base.name)) {
                    mutatedGlobals.add(s.name.base.name);
                } else if (s.name?.base?.type === "Identifier") {
                    scanExpr(s.name.base);
                } else {
                    scanExpr(s.name?.base);
                }
                scanPush();
                if (s.name?.method) scanAdd("self");
                for (const p of s.params || []) { if (!p.variadic) scanAdd(p.name); }
                s.body?.forEach(scanStmt); scanPop();
                break;
            case "ReturnStatement": s.values?.forEach(scanExpr); break;
        }
    };
    fnNode.body?.forEach(scanStmt);

    const hoistedGlobals = new Map();
    const hoistNames = [];
    const hoistVals = [];
    for (const gName of readImmutableGlobals) {
        if (mutatedGlobals.has(gName)) continue;
        const gLocal = nextMangled();
        hoistedGlobals.set(gName, gLocal);
        hoistNames.push(gLocal);
        hoistVals.push(`${envVar}[${getStrCall(gName)}]`);
    }

    let loopDepth = 0;
    let inForBound = false;
    let unsupported = false;

    const resolveIdent = (name) => {
        if (name === "nil" || name === "true" || name === "false") return name;
        const loc = flat.get(name);
        if (loc !== undefined) return loc;
        const hoisted = hoistedGlobals.get(name);
        if (hoisted !== undefined) return hoisted;
        return `${envVar}[${getStrCall(name)}]`;
    };

    const emitNumber = (e) => {
        const rawStr = String(e.value);
        if (inForBound) return rawStr;
        const n = Number(rawStr);
        if (Number.isInteger(n) && n >= 2 && n <= 0x7FFFFFFF && !/[.eEpP]/.test(rawStr)) {
            if (loopDepth === 0 && rng() < 0.5) {
                const k = 1 + Math.floor(rng() * 0x7FFFFF);
                return `${bxFn}(${k},${(n ^ k) >>> 0})`;
            }
            if (rng() < 0.5) {
                const k = 1 + Math.floor(rng() * (n - 1));
                return `(${k}+${n - k})`;
            }
            const k = 1 + Math.floor(rng() * 0xFFFF);
            return `(${n + k}-${k})`;
        }
        return rawStr;
    };

    const emitReceiver = (obj) => {
        const code = emitExpr(obj);
        return needsReceiverParens(obj) ? `(${code})` : code;
    };

    const emitExpr = (e) => {
        if (unsupported || !e || typeof e !== "object") {
            unsupported = true;
            return "nil";
        }
        switch (e.type) {
            case "NilLiteral":
                return "nil";
            case "BooleanLiteral":
                return e.value ? "true" : "false";
            case "NumberLiteral":
                return emitNumber(e);
            case "StringLiteral":
                return getStrCall(e.value);
            case "StringInterpolation": {
                if (!e.parts || e.parts.length === 0) return getStrCall("");
                const tsRef = resolveIdent("tostring");
                const parts = e.parts.map((p) =>
                    typeof p === "string" ? getStrCall(p) : `${tsRef}(${emitExpr(p)})`
                );
                return `(${parts.join(" .. ")})`;
            }
            case "VarargExpression":
                return "...";
            case "Identifier":
                return resolveIdent(e.name);
            case "BinaryExpression":
                return `(${emitExpr(e.left)} ${e.operator} ${emitExpr(e.right)})`;
            case "UnaryExpression": {
                const arg = emitExpr(e.argument);
                if (e.operator === "not") return `(not (${arg}))`;
                return `(${e.operator}(${arg}))`;
            }
            case "ParenExpression":
                return `(${emitExpr(e.expression)})`;
            case "TypeAssertion":
                return emitExpr(e.expression);
            case "IndexExpression":
                return `${emitReceiver(e.object)}[${emitExpr(e.index)}]`;
            case "MemberExpression":
                return `${emitReceiver(e.object)}.${e.property}`;
            case "CallExpression": {
                const callee = e.callee?.type === "FunctionExpression"
                    ? `(${emitExpr(e.callee)})`
                    : emitReceiver(e.callee);
                const args = (e.args || []).map(emitExpr).join(",");
                return `${callee}(${args})`;
            }
            case "MethodCallExpression": {
                const obj = emitReceiver(e.object);
                const args = (e.args || []).map(emitExpr).join(",");
                return `${obj}:${e.method}(${args})`;
            }
            case "TableConstructor": {
                const fields = (e.fields || []).map((f) => {
                    if (f.kind === "index") return `[${emitExpr(f.index)}]=${emitExpr(f.value)}`;
                    if (f.kind === "named") return `${f.name}=${emitExpr(f.value)}`;
                    return emitExpr(f.value);
                });
                return `{${fields.join(",")}}`;
            }
            case "IfElseExpression": {
                const cond = emitExpr(e.condition);
                const thenExp = emitExpr(e.thenExp);
                const elseifs = (e.elseifClauses || [])
                    .map((c) => ` elseif ${emitExpr(c.condition)} then ${emitExpr(c.value)}`)
                    .join("");
                const elseExp = emitExpr(e.elseExp);
                return `(if ${cond} then ${thenExp}${elseifs} else ${elseExp})`;
            }
            case "FunctionExpression": {
                pushScope();
                const params = (e.params || []).map((p) => (p.variadic ? "..." : declareLocal(p.name)));
                const body = emitBlock(e.body || []);
                popScope();
                return `function(${params.join(",")}) ${body} end`;
            }
            default:
                unsupported = true;
                return "nil";
        }
    };

    const emitVar = (v) => {
        if (!v || typeof v !== "object") {
            unsupported = true;
            return "_";
        }
        if (v.type === "Identifier") return resolveIdent(v.name);
        if (v.type === "IndexExpression") return `${emitReceiver(v.object)}[${emitExpr(v.index)}]`;
        if (v.type === "MemberExpression") return `${emitReceiver(v.object)}.${v.property}`;
        unsupported = true;
        return "_";
    };

    const emitStmt = (s) => {
        if (unsupported || !s || typeof s !== "object") return "";
        switch (s.type) {
            case "LocalStatement": {
                const vals = s.values && s.values.length > 0 ? s.values.map(emitExpr) : null;
                const names = s.vars.map((v) => declareLocal(v.name));
                return vals ? `local ${names.join(",")}=${vals.join(",")}` : `local ${names.join(",")}`;
            }
            case "AssignmentStatement": {
                const vars = s.vars.map(emitVar);
                const vals = s.values.map(emitExpr);
                return `${vars.join(",")}=${vals.join(",")}`;
            }
            case "CompoundAssignmentStatement": {
                return `${emitVar(s.var)}${s.operator}${emitExpr(s.value)}`;
            }
            case "FunctionCallStatement":
                return emitExpr(s.call);
            case "DoStatement": {
                pushScope();
                const body = emitBlock(s.body || []);
                popScope();
                return `do ${body} end`;
            }
            case "WhileStatement": {
                const cond = emitExpr(s.condition);
                pushScope();
                loopDepth++;
                const body = emitBlock(s.body || []);
                loopDepth--;
                popScope();
                return `while ${cond} do ${body} end`;
            }
            case "RepeatStatement": {
                pushScope();
                loopDepth++;
                const body = emitBlock(s.body || []);
                const cond = emitExpr(s.condition);
                loopDepth--;
                popScope();
                return `repeat ${body} until ${cond}`;
            }
            case "IfStatement": {
                let out = `if ${emitExpr(s.condition)} then `;
                pushScope();
                out += emitBlock(s.thenBody || []);
                popScope();
                for (const c of s.elseifClauses || []) {
                    out += ` elseif ${emitExpr(c.condition)} then `;
                    pushScope();
                    out += emitBlock(c.body || []);
                    popScope();
                }
                if (s.elseBody) {
                    out += ` else `;
                    pushScope();
                    out += emitBlock(s.elseBody);
                    popScope();
                }
                return `${out} end`;
            }
            case "ForNumericStatement": {
                inForBound = true;
                const start = emitExpr(s.start);
                const end = emitExpr(s.end);
                const step = s.step ? `,${emitExpr(s.step)}` : "";
                inForBound = false;
                pushScope();
                const v = declareLocal(s.var.name);
                loopDepth++;
                const body = emitBlock(s.body || []);
                loopDepth--;
                popScope();
                return `for ${v}=${start},${end}${step} do ${body} end`;
            }
            case "ForInStatement": {
                const iter = (s.iter || []).map(emitExpr).join(",");
                pushScope();
                const vars = (s.vars || []).map((v) => declareLocal(v.name));
                loopDepth++;
                const body = emitBlock(s.body || []);
                loopDepth--;
                popScope();
                return `for ${vars.join(",")} in ${iter} do ${body} end`;
            }
            case "LocalFunctionStatement": {
                const name = declareLocal(s.name);
                pushScope();
                const params = (s.params || []).map((p) => (p.variadic ? "..." : declareLocal(p.name)));
                const body = emitBlock(s.body || []);
                popScope();
                return `local function ${name}(${params.join(",")}) ${body} end`;
            }
            case "FunctionStatement": {
                let lhs;
                if (s.name?.base?.type === "Identifier") {
                    lhs = resolveIdent(s.name.base.name);
                } else {
                    lhs = emitExpr(s.name?.base);
                }
                if (s.name?.method) lhs = `${lhs}.${s.name.method}`;
                pushScope();
                const params = [];
                if (s.name?.method) params.push(declareLocal("self"));
                for (const p of s.params || []) {
                    params.push(p.variadic ? "..." : declareLocal(p.name));
                }
                const body = emitBlock(s.body || []);
                popScope();
                return `${lhs}=function(${params.join(",")}) ${body} end`;
            }
            case "ReturnStatement": {
                if (!s.values || s.values.length === 0) return "return";
                return `return ${s.values.map(emitExpr).join(",")}`;
            }
            case "BreakStatement":
                return "break";
            case "ContinueStatement":
                return "continue";
            case "TypeStatement":
            case "ExportTypeStatement":
            case "TypeFunctionStatement":
            case "ExportTypeFunctionStatement":
                return "";
            default:
                unsupported = true;
                return "";
        }
    };

    const emitBlock = (stmts) => {
        const parts = [];
        for (const st of stmts) {
            const emitted = emitStmt(st);
            if (emitted) parts.push(emitted);
            if (unsupported) return "";
        }
        return parts.join(";");
    };

    const params = (fnNode.params || []).map((p) => (p.variadic ? "..." : declareLocal(p.name)));
    const entryParts = [emitEntryOpaqueGuard(rng, bxFn)];
    const bodyStr = emitBlock(fnNode.body || []);
    if (unsupported) return null;

    if (hoistNames.length > 0) {
        const lazyChecks = hoistNames.map((nm, i) => `if ${nm}==nil then ${nm}=${hoistVals[i]} end`).join(";");
        entryParts.push(lazyChecks);
        const fullBody = bodyStr ? `${entryParts.join(";")};${bodyStr}` : entryParts.join(";");
        return `(function() local ${hoistNames.join(",")};return function(${params.join(",")}) ${fullBody} end end)()`;
    }
    const fullBody = bodyStr ? `${entryParts.join(";")};${bodyStr}` : entryParts.join(";");
    return `function(${params.join(",")}) ${fullBody} end`;
}
