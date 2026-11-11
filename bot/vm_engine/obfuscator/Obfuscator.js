const KEYWORDS = new Set([
    "and", "break", "continue", "do", "else", "elseif", "end", "export", "false",
    "for", "function", "if", "in", "local", "nil", "not", "or",
    "repeat", "return", "then", "true", "until", "while",
]);
const PRESERVED_GLOBALS = new Set([
    // Core Lua / Luau Builtins
    "_G", "_VERSION", "assert", "collectgarbage", "error", "getfenv", "getmetatable",
    "ipairs", "load", "loadfile", "loadstring", "next", "pairs", "pcall", "print",
    "rawequal", "rawget", "rawlen", "rawset", "select", "setfenv", "setmetatable",
    "tonumber", "tostring", "type", "typeof", "unpack", "xpcall", "newproxy",

    // Standard Libraries
    "coroutine", "table", "string", "math", "bit32", "os", "debug", "utf8", "buffer", "task",

    // Roblox Globals & Datatypes
    "game", "workspace", "script", "shared", "Enum", "Faces", "Axes", "BrickColor",
    "CFrame", "Color3", "ColorSequence", "ColorSequenceKeypoint", "DateTime",
    "DockWidgetPluginGuiInfo", "Font", "Instance", "NumberRange", "NumberSequence",
    "NumberSequenceKeypoint", "OverlapParams", "PathWaypoint", "PhysicalProperties",
    "Random", "Ray", "RaycastParams", "Rect", "Region3", "Region3int16", "TweenInfo",
    "UDim", "UDim2", "Vector2", "Vector2int16", "Vector3", "Vector3int16",

    // Roblox Global Functions
    "delay", "elapsedTime", "spawn", "tick", "time", "version", "wait", "warn",
    "settings", "stats", "UserSettings", "plugin",

    // Common Roblox Services
    "Players", "RunService", "ReplicatedStorage", "ReplicatedFirst", "ServerScriptService",
    "ServerStorage", "Lighting", "StarterGui", "StarterPack", "StarterPlayer",
    "SoundService", "TweenService", "UserInputService", "ContextActionService",
    "HttpService", "TeleportService", "MarketplaceService", "BadgeService",
    "Teams", "CoreGui", "VirtualInputManager", "GuiService", "Stats", "PathfindingService",

    // Exploit & Executor APIs (Synapse, Fluxus, Delta, Wave, Codex, Arceus, Solara)
    "getgenv", "getrenv", "getreg", "getgc", "getinstances", "getnilinstances",
    "getscripts", "getrunningscripts", "getloadedmodules", "getcallingscript",
    "getconnections", "firesignal", "fireclickdetector", "fireproximityprompt",
    "firetouchinterest", "getcustomasset", "getsynasset", "hookfunction", "hookfunc",
    "hookmetamethod", "restorefunction", "isfunctionhooked", "newcclosure",
    "replaceclosure", "islclosure", "iscclosure", "isourclosure", "checkclosure",
    "checkcaller", "identifyexecutor", "getexecutorname", "rconsoleprint",
    "rconsoleclear", "rconsolewarn", "rconsoleerr", "rconsoleinfo", "request",
    "http_request", "syn", "fluxus", "krnl", "isexecutorclosure", "cloneref",
    "clonefunction", "compareinstances", "gethui", "isfile", "isfolder",
    "makefolder", "delfile", "delfolder", "readfile", "writefile", "appendfile",
    "listfiles", "getrawmetatable", "setrawmetatable", "getnamecallmethod",
    "setnamecallmethod", "isreadonly", "setreadonly", "setclipboard", "toclipboard",
    "getclipboard", "setrbxclipboard", "queue_on_teleport", "queueonteleport",
    "setthreadidentity", "getthreadidentity", "setidentity", "getidentity",
    "setthreadcontext", "getthreadcontext", "Drawing", "cleardrawcache",
    "isrenderobj", "WebSocket", "crypt", "base64", "bit", "lz4compress",
    "lz4decompress", "filtergc", "gethwid", "replicatesignal",
    "getscriptbytecode", "getscripthash", "getscriptclosure", "decompile"
]);
function isValidIdentifier(name) {
    return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name) && !KEYWORDS.has(name);
}
function generateName(index) {
    if (index < 26)
        return String.fromCharCode(97 + index);
    let s = "";
    let n = index;
    while (n >= 0) {
        s = String.fromCharCode(97 + (n % 26)) + s;
        n = Math.floor(n / 26) - 1;
    }
    return s;
}
const DEFAULT_OPTIONS = {
    renameLocals: true,
    preserveGlobals: true,
    seed: 0,
};
function collectGlobalNames(ast) {
    const globals = new Set(["self", "_ENV", "io", "package", "require", "arg"]);
    const scopes = [new Set()];
    const hasLocal = (name) => {
        for (let i = scopes.length - 1; i >= 0; i--) {
            if (scopes[i].has(name)) return true;
        }
        return false;
    };
    const push = () => scopes.push(new Set());
    const pop = () => scopes.pop();
    const addLocal = (name) => { if (name) scopes[scopes.length - 1].add(name); };
    const visitExpr = (e) => {
        if (!e || typeof e !== "object") return;
        switch (e.type) {
            case "Identifier":
                if (e.name && !hasLocal(e.name)) globals.add(e.name);
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
                push();
                e.params?.forEach((p) => { if (!p.variadic) addLocal(p.name); });
                e.body?.forEach(visitStmt);
                pop();
                break;
            case "ParenExpression":
            case "TypeAssertion":
                visitExpr(e.expression); break;
            case "IfElseExpression":
                visitExpr(e.condition); visitExpr(e.thenExp);
                e.elseifClauses?.forEach((c) => { visitExpr(c.condition); visitExpr(c.value); });
                visitExpr(e.elseExp); break;
            case "StringInterpolation":
                e.parts?.forEach((p) => { if (typeof p !== "string") visitExpr(p); });
                break;
        }
    };
    const visitStmt = (s) => {
        if (!s || typeof s !== "object") return;
        switch (s.type) {
            case "LocalStatement":
                s.values?.forEach(visitExpr);
                s.vars?.forEach((v) => addLocal(v.name));
                break;
            case "LocalFunctionStatement":
                addLocal(s.name);
                push();
                s.params?.forEach((p) => { if (!p.variadic) addLocal(p.name); });
                s.body?.forEach(visitStmt);
                pop();
                break;
            case "FunctionStatement":
                if (s.name?.base?.type === "Identifier" && !hasLocal(s.name.base.name)) {
                    globals.add(s.name.base.name);
                } else {
                    visitExpr(s.name?.base);
                }
                push();
                s.params?.forEach((p) => { if (!p.variadic) addLocal(p.name); });
                s.body?.forEach(visitStmt);
                pop();
                break;
            case "ForNumericStatement":
                visitExpr(s.start); visitExpr(s.end); if (s.step) visitExpr(s.step);
                push(); addLocal(s.var?.name); s.body?.forEach(visitStmt); pop();
                break;
            case "ForInStatement":
                s.iter?.forEach(visitExpr);
                push(); s.vars?.forEach((v) => addLocal(v.name)); s.body?.forEach(visitStmt); pop();
                break;
            case "DoStatement":
                push(); s.body?.forEach(visitStmt); pop(); break;
            case "WhileStatement":
                visitExpr(s.condition); push(); s.body?.forEach(visitStmt); pop(); break;
            case "RepeatStatement":
                push(); s.body?.forEach(visitStmt); visitExpr(s.condition); pop(); break;
            case "IfStatement":
                visitExpr(s.condition);
                push(); s.thenBody?.forEach(visitStmt); pop();
                s.elseifClauses?.forEach((c) => {
                    visitExpr(c.condition);
                    push(); c.body?.forEach(visitStmt); pop();
                });
                if (s.elseBody) { push(); s.elseBody.forEach(visitStmt); pop(); }
                break;
            case "AssignmentStatement":
                s.vars?.forEach(visitExpr); s.values?.forEach(visitExpr); break;
            case "CompoundAssignmentStatement":
                visitExpr(s.var); visitExpr(s.value); break;
            case "FunctionCallStatement":
                visitExpr(s.call); break;
            case "ReturnStatement":
                s.values?.forEach(visitExpr); break;
        }
    };
    ast.body?.forEach(visitStmt);
    return globals;
}
export function obfuscate(ast, options = {}) {
    const opts = { ...DEFAULT_OPTIONS, ...options };
    if (!opts.renameLocals)
        return ast;
    const scope = new ScopeManager(opts, collectGlobalNames(ast));
    return transformChunk(ast, scope);
}
class ScopeManager {
    flat = new Map();
    undoStack = [[]];
    nameCounter = 0;
    opts;
    reservedNames;
    constructor(opts, reservedNames = new Set()) {
        this.opts = opts;
        this.reservedNames = reservedNames;
    }
    pushScope() {
        this.undoStack.push([]);
    }
    popScope() {
        const undo = this.undoStack.pop();
        for (let i = undo.length - 1; i >= 0; i--) {
            const entry = undo[i];
            if (entry.prev === undefined) {
                this.flat.delete(entry.name);
            }
            else {
                this.flat.set(entry.name, entry.prev);
            }
        }
    }
    declare(name) {
        if (!isValidIdentifier(name))
            return name;
        if (this.opts.preserveGlobals && PRESERVED_GLOBALS.has(name))
            return name;
        let newName;
        do {
            newName = generateName(this.nameCounter++);
        } while (KEYWORDS.has(newName) || PRESERVED_GLOBALS.has(newName) || this.reservedNames.has(newName));
        const prev = this.flat.get(name);
        this.undoStack[this.undoStack.length - 1].push({ name, prev });
        this.flat.set(name, newName);
        return newName;
    }
    resolve(name) {
        if (!isValidIdentifier(name))
            return name;
        if (this.opts.preserveGlobals && PRESERVED_GLOBALS.has(name))
            return name;
        return this.flat.get(name) ?? name;
    }
}
function transformChunk(chunk, scope) {
    return {
        ...chunk,
        body: chunk.body.map((s) => transformStatement(s, scope)),
    };
}
function transformStatement(stmt, scope) {
    switch (stmt.type) {
        case "LocalStatement": {
            const values = stmt.values?.map((e) => transformExpression(e, scope));
            const vars = stmt.vars.map((v) => ({
                ...v,
                name: scope.declare(v.name),
            }));
            return { ...stmt, vars, values };
        }
        case "LocalFunctionStatement": {
            const name = scope.declare(stmt.name);
            scope.pushScope();
            const params = stmt.params.map((p) => ({
                ...p,
                name: p.variadic ? "..." : scope.declare(p.name),
            }));
            const body = stmt.body.map((s) => transformStatement(s, scope));
            scope.popScope();
            return { ...stmt, name, params, body };
        }
        case "FunctionStatement": {
            const name = transformFuncName(stmt.name, scope);
            scope.pushScope();
            const params = stmt.params.map((p) => ({
                ...p,
                name: p.variadic ? "..." : scope.declare(p.name),
            }));
            const body = stmt.body.map((s) => transformStatement(s, scope));
            scope.popScope();
            return { ...stmt, name, params, body };
        }
        case "ForNumericStatement": {
            const start = transformExpression(stmt.start, scope);
            const end = transformExpression(stmt.end, scope);
            const step = stmt.step ? transformExpression(stmt.step, scope) : undefined;
            scope.pushScope();
            const v = scope.declare(stmt.var.name);
            const varNode = { type: "Identifier", name: v, loc: stmt.var.loc };
            const body = stmt.body.map((s) => transformStatement(s, scope));
            scope.popScope();
            return {
                ...stmt,
                var: varNode,
                start,
                end,
                step,
                body,
            };
        }
        case "ForInStatement": {
            const iter = stmt.iter.map((e) => transformExpression(e, scope));
            scope.pushScope();
            const vars = stmt.vars.map((v) => ({
                ...v,
                name: scope.declare(v.name),
            }));
            const body = stmt.body.map((s) => transformStatement(s, scope));
            scope.popScope();
            return {
                ...stmt,
                vars,
                iter,
                body,
            };
        }
        case "TypeFunctionStatement":
        case "ExportTypeFunctionStatement": {
            scope.pushScope();
            const params = stmt.params.map((p) => ({
                ...p,
                name: p.variadic ? "..." : scope.declare(p.name),
            }));
            const body = stmt.body.map((s) => transformStatement(s, scope));
            scope.popScope();
            return { ...stmt, params, body };
        }
        case "DoStatement":
            scope.pushScope();
            const doBody = stmt.body.map((s) => transformStatement(s, scope));
            scope.popScope();
            return { ...stmt, body: doBody };
        case "WhileStatement": {
            const condition = transformExpression(stmt.condition, scope);
            scope.pushScope();
            const whileBody = stmt.body.map((s) => transformStatement(s, scope));
            scope.popScope();
            return {
                ...stmt,
                condition,
                body: whileBody,
            };
        }
        case "RepeatStatement": {
            scope.pushScope();
            const repeatBody = stmt.body.map((s) => transformStatement(s, scope));
            const condition = transformExpression(stmt.condition, scope);
            scope.popScope();
            return {
                ...stmt,
                body: repeatBody,
                condition,
            };
        }
        case "IfStatement": {
            const condition = transformExpression(stmt.condition, scope);
            scope.pushScope();
            const thenBody = stmt.thenBody.map((s) => transformStatement(s, scope));
            scope.popScope();
            const elseifClauses = stmt.elseifClauses.map((c) => {
                const cCond = transformExpression(c.condition, scope);
                scope.pushScope();
                const cBody = c.body.map((s) => transformStatement(s, scope));
                scope.popScope();
                return { condition: cCond, body: cBody };
            });
            let elseBody = undefined;
            if (stmt.elseBody) {
                scope.pushScope();
                elseBody = stmt.elseBody.map((s) => transformStatement(s, scope));
                scope.popScope();
            }
            return {
                ...stmt,
                condition,
                thenBody,
                elseifClauses,
                elseBody,
            };
        }
        case "AssignmentStatement":
            return {
                ...stmt,
                vars: stmt.vars.map((v) => transformVar(v, scope)),
                values: stmt.values.map((e) => transformExpression(e, scope)),
            };
        case "CompoundAssignmentStatement":
            return {
                ...stmt,
                var: transformVar(stmt.var, scope),
                value: transformExpression(stmt.value, scope),
            };
        case "FunctionCallStatement":
            return {
                ...stmt,
                call: transformExpression(stmt.call, scope),
            };
        case "ReturnStatement":
            return {
                ...stmt,
                values: stmt.values?.map((e) => transformExpression(e, scope)),
            };
        default:
            return stmt;
    }
}
function transformFuncName(fn, scope) {
    const base = fn.base.type === "Identifier"
        ? { ...fn.base, name: scope.resolve(fn.base.name) }
        : transformExpression(fn.base, scope);
    return { ...fn, base };
}
function transformVar(v, scope) {
    switch (v.type) {
        case "Identifier":
            return { ...v, name: scope.resolve(v.name) };
        case "IndexExpression":
            return {
                ...v,
                object: transformExpression(v.object, scope),
                index: transformExpression(v.index, scope),
            };
        case "MemberExpression":
            return {
                ...v,
                object: transformExpression(v.object, scope),
            };
        default:
            return v;
    }
}
function transformExpression(exp, scope) {
    switch (exp.type) {
        case "Identifier":
            return { ...exp, name: scope.resolve(exp.name) };
        case "BinaryExpression":
            return {
                ...exp,
                left: transformExpression(exp.left, scope),
                right: transformExpression(exp.right, scope),
            };
        case "UnaryExpression":
            return {
                ...exp,
                argument: transformExpression(exp.argument, scope),
            };
        case "CallExpression":
            return {
                ...exp,
                callee: transformExpression(exp.callee, scope),
                args: exp.args.map((a) => transformExpression(a, scope)),
            };
        case "MethodCallExpression":
            return {
                ...exp,
                object: transformExpression(exp.object, scope),
                args: exp.args.map((a) => transformExpression(a, scope)),
            };
        case "IndexExpression":
            return {
                ...exp,
                object: transformExpression(exp.object, scope),
                index: transformExpression(exp.index, scope),
            };
        case "MemberExpression":
            return {
                ...exp,
                object: transformExpression(exp.object, scope),
            };
        case "TableConstructor":
            return {
                ...exp,
                fields: exp.fields.map((f) => {
                    if (f.kind === "index")
                        return { ...f, index: transformExpression(f.index, scope), value: transformExpression(f.value, scope) };
                    if (f.kind === "named")
                        return { ...f, value: transformExpression(f.value, scope) };
                    return { ...f, value: transformExpression(f.value, scope) };
                }),
            };
        case "FunctionExpression": {
            scope.pushScope();
            const params = exp.params.map((p) => ({
                ...p,
                name: p.variadic ? "..." : scope.declare(p.name),
            }));
            const body = exp.body.map((s) => transformStatement(s, scope));
            scope.popScope();
            return { ...exp, params, body };
        }
        case "ParenExpression":
            return { ...exp, expression: transformExpression(exp.expression, scope) };
        case "TypeAssertion":
            return {
                ...exp,
                expression: transformExpression(exp.expression, scope),
            };
        case "IfElseExpression":
            return {
                ...exp,
                condition: transformExpression(exp.condition, scope),
                thenExp: transformExpression(exp.thenExp, scope),
                elseifClauses: exp.elseifClauses.map((c) => ({
                    condition: transformExpression(c.condition, scope),
                    value: transformExpression(c.value, scope),
                })),
                elseExp: transformExpression(exp.elseExp, scope),
            };
        case "StringInterpolation":
            return {
                ...exp,
                parts: exp.parts.map((p) => (typeof p === "string" ? p : transformExpression(p, scope))),
            };
        default:
            return exp;
    }
}
//# sourceMappingURL=Obfuscator.js.map