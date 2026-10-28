function makeLoc(start, end) {
    return { start, end };
}

function createOpaquePredicate(index, loc) {
    const variant = index % 6;
    if (variant === 0) {
        // ((k * (k + 1)) % 2 == 0) - Even parity mathematical invariant
        const k = 13 + (index * 7) % 89;
        return {
            type: "BinaryExpression",
            operator: "==",
            left: {
                type: "BinaryExpression",
                operator: "%",
                left: {
                    type: "BinaryExpression",
                    operator: "*",
                    left: { type: "NumberLiteral", value: String(k), loc },
                    right: { type: "NumberLiteral", value: String(k + 1), loc },
                    loc,
                },
                right: { type: "NumberLiteral", value: "2", loc },
                loc,
            },
            right: { type: "NumberLiteral", value: "0", loc },
            loc,
        };
    } else if (variant === 1) {
        // (type(type) == "function") - Native type invariant
        return {
            type: "BinaryExpression",
            operator: "==",
            left: {
                type: "CallExpression",
                callee: { type: "Identifier", name: "type", loc },
                args: [{ type: "Identifier", name: "type", loc }],
                loc,
            },
            right: { type: "StringLiteral", value: "function", loc },
            loc,
        };
    } else if (variant === 2) {
        // (type(pcall) == "function") - Runtime presence invariant
        return {
            type: "BinaryExpression",
            operator: "==",
            left: {
                type: "CallExpression",
                callee: { type: "Identifier", name: "type", loc },
                args: [{ type: "Identifier", name: "pcall", loc }],
                loc,
            },
            right: { type: "StringLiteral", value: "function", loc },
            loc,
        };
    } else if (variant === 3) {
        // (math.abs(-1) == 1) - Transcendental math identity
        return {
            type: "BinaryExpression",
            operator: "==",
            left: {
                type: "CallExpression",
                callee: {
                    type: "MemberExpression",
                    object: { type: "Identifier", name: "math", loc },
                    property: "abs",
                    loc,
                },
                args: [{
                    type: "UnaryExpression",
                    operator: "-",
                    argument: { type: "NumberLiteral", value: "1", loc },
                    loc,
                }],
                loc,
            },
            right: { type: "NumberLiteral", value: "1", loc },
            loc,
        };
    } else if (variant === 4) {
        // (#"" == 0) - Empty string length invariant
        return {
            type: "BinaryExpression",
            operator: "==",
            left: {
                type: "UnaryExpression",
                operator: "#",
                argument: { type: "StringLiteral", value: "", loc },
                loc,
            },
            right: { type: "NumberLiteral", value: "0", loc },
            loc,
        };
    } else {
        // ((A * B + C) % D == RES) - Complex modular arithmetic
        const A = 17 + (index * 11) % 43;
        const B = 23 + (index * 13) % 37;
        const C = 5 + (index * 7) % 19;
        const D = 100 + (index * 17) % 50;
        const res = (A * B + C) % D;
        return {
            type: "BinaryExpression",
            operator: "==",
            left: {
                type: "BinaryExpression",
                operator: "%",
                left: {
                    type: "BinaryExpression",
                    operator: "+",
                    left: {
                        type: "BinaryExpression",
                        operator: "*",
                        left: { type: "NumberLiteral", value: String(A), loc },
                        right: { type: "NumberLiteral", value: String(B), loc },
                        loc,
                    },
                    right: { type: "NumberLiteral", value: String(C), loc },
                    loc,
                },
                right: { type: "NumberLiteral", value: String(D), loc },
                loc,
            },
            right: { type: "NumberLiteral", value: String(res), loc },
            loc,
        };
    }
}
function wrapWithOpaque(condition, loc, seed) {
    const opaque = createOpaquePredicate(seed, loc);
    return {
        type: "BinaryExpression",
        operator: "and",
        left: opaque,
        right: condition,
        loc,
    };
}
function transformExpression(exp, seed) {
    if (exp.type === "BinaryExpression") {
        return {
            ...exp,
            left: transformExpression(exp.left, seed),
            right: transformExpression(exp.right, seed),
        };
    }
    if (exp.type === "UnaryExpression") {
        return { ...exp, argument: transformExpression(exp.argument, seed) };
    }
    if (exp.type === "CallExpression") {
        return {
            ...exp,
            callee: transformExpression(exp.callee, seed),
            args: exp.args.map((a) => transformExpression(a, seed)),
        };
    }
    if (exp.type === "MethodCallExpression") {
        return {
            ...exp,
            object: transformExpression(exp.object, seed),
            args: exp.args.map((a) => transformExpression(a, seed)),
        };
    }
    if (exp.type === "IndexExpression") {
        return {
            ...exp,
            object: transformExpression(exp.object, seed),
            index: transformExpression(exp.index, seed),
        };
    }
    if (exp.type === "MemberExpression") {
        return { ...exp, object: transformExpression(exp.object, seed) };
    }
    if (exp.type === "TableConstructor") {
        return {
            ...exp,
            fields: exp.fields.map((f) => {
                if (f.kind === "index")
                    return { ...f, index: transformExpression(f.index, seed), value: transformExpression(f.value, seed) };
                return { ...f, value: transformExpression(f.value, seed) };
            }),
        };
    }
    if (exp.type === "FunctionExpression") {
        return {
            ...exp,
            body: exp.body.map((s) => transformStatement(s, seed)),
        };
    }
    if (exp.type === "ParenExpression") {
        return { ...exp, expression: transformExpression(exp.expression, seed) };
    }
    if (exp.type === "TypeAssertion") {
        return { ...exp, expression: transformExpression(exp.expression, seed) };
    }
    if (exp.type === "IfElseExpression") {
        return {
            ...exp,
            condition: transformExpression(exp.condition, seed),
            thenExp: transformExpression(exp.thenExp, seed),
            elseifClauses: exp.elseifClauses.map((c) => ({
                ...c,
                condition: transformExpression(c.condition, seed),
                value: transformExpression(c.value, seed),
            })),
            elseExp: transformExpression(exp.elseExp, seed),
        };
    }
    if (exp.type === "StringInterpolation") {
        return {
            ...exp,
            parts: exp.parts.map((p) => typeof p === "string" ? p : transformExpression(p, seed)),
        };
    }
    return exp;
}
function transformStatement(stmt, seed) {
    switch (stmt.type) {
        case "IfStatement": {
            seed.value++;
            const newCondition = wrapWithOpaque(transformExpression(stmt.condition, seed), stmt.condition.loc, seed.value);
            return {
                ...stmt,
                condition: newCondition,
                thenBody: stmt.thenBody.map((s) => transformStatement(s, seed)),
                elseifClauses: stmt.elseifClauses.map((c) => {
                    seed.value++;
                    return {
                        condition: wrapWithOpaque(transformExpression(c.condition, seed), c.condition.loc, seed.value),
                        body: c.body.map((s) => transformStatement(s, seed)),
                    };
                }),
                elseBody: stmt.elseBody?.map((s) => transformStatement(s, seed)),
            };
        }
        case "WhileStatement": {
            seed.value++;
            return {
                ...stmt,
                condition: wrapWithOpaque(transformExpression(stmt.condition, seed), stmt.condition.loc, seed.value),
                body: stmt.body.map((s) => transformStatement(s, seed)),
            };
        }
        case "RepeatStatement": {
            seed.value++;
            return {
                ...stmt,
                body: stmt.body.map((s) => transformStatement(s, seed)),
                condition: wrapWithOpaque(transformExpression(stmt.condition, seed), stmt.condition.loc, seed.value),
            };
        }
        case "LocalStatement":
            return {
                ...stmt,
                values: stmt.values?.map((e) => transformExpression(e, seed)),
            };
        case "AssignmentStatement":
            return {
                ...stmt,
                vars: stmt.vars.map((v) => {
                    if (v.type === "Identifier")
                        return v;
                    if (v.type === "IndexExpression")
                        return {
                            ...v,
                            object: transformExpression(v.object, seed),
                            index: transformExpression(v.index, seed),
                        };
                    return { ...v, object: transformExpression(v.object, seed) };
                }),
                values: stmt.values.map((e) => transformExpression(e, seed)),
            };
        case "CompoundAssignmentStatement":
            return {
                ...stmt,
                var: stmt.var.type === "Identifier"
                    ? stmt.var
                    : {
                        ...stmt.var,
                        object: transformExpression(stmt.var.object, seed),
                        ...(stmt.var.type === "IndexExpression" && {
                            index: transformExpression(stmt.var.index, seed),
                        }),
                    },
                value: transformExpression(stmt.value, seed),
            };
        case "FunctionCallStatement":
            return {
                ...stmt,
                call: transformExpression(stmt.call, seed),
            };
        case "ReturnStatement":
            return {
                ...stmt,
                values: stmt.values?.map((e) => transformExpression(e, seed)),
            };
        case "ForNumericStatement":
            return {
                ...stmt,
                start: transformExpression(stmt.start, seed),
                end: transformExpression(stmt.end, seed),
                step: stmt.step ? transformExpression(stmt.step, seed) : undefined,
                body: stmt.body.map((s) => transformStatement(s, seed)),
            };
        case "ForInStatement":
            return {
                ...stmt,
                iter: stmt.iter.map((e) => transformExpression(e, seed)),
                body: stmt.body.map((s) => transformStatement(s, seed)),
            };
        case "LocalFunctionStatement":
        case "FunctionStatement":
        case "TypeFunctionStatement":
        case "ExportTypeFunctionStatement":
            return {
                ...stmt,
                body: stmt.body.map((s) => transformStatement(s, seed)),
            };
        case "DoStatement":
            return {
                ...stmt,
                body: stmt.body.map((s) => transformStatement(s, seed)),
            };
        default:
            return stmt;
    }
}
export function scrambleControlFlow(ast, options = {}) {
    const enabled = options.enabled !== false;
    const seed = { value: options.seed ?? 0 };
    if (!enabled)
        return ast;
    return {
        ...ast,
        body: ast.body.map((s) => transformStatement(s, seed)),
    };
}
//# sourceMappingURL=ControlFlowScrambler.js.map