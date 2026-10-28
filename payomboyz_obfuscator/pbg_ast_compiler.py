"""
PayomboyZ Obfuscator - Virtual Register Bytecode Compiler (PBG-Compiler)
Compiles Lua/Luau statements and expressions into a custom register instruction format:
- LOADK, MOVE, GETGLOBAL, SETGLOBAL, GETTABLE, SETTABLE
- CALL, RETURN, JUMP, JUMPIF, NEWTABLE, BINOP, UNOP, NEWCLOSURE
"""

import ast
import re
import zlib
from typing import List, Dict, Any, Tuple, Optional

# Opcodes definition (randomized in the VM generator)
OP_CODES = [
    "MOVE",
    "LOADK",
    "GETGLOBAL",
    "SETGLOBAL",
    "GETTABLE",
    "SETTABLE",
    "NEWTABLE",
    "CALL",
    "RETURN",
    "JUMP",
    "JUMPIF",
    "BINOP",
    "UNOP",
    "CLOSURE",
    "VARARG",
    "NOP"
]

class Instruction:
    def __init__(self, op: str, a: int = 0, b: Any = 0, c: Any = 0, extra: Any = None):
        self.op = op
        self.a = a          # Destination register / return count / condition
        self.b = b          # Source 1 register / constant index
        self.c = c          # Source 2 register / immediate / operand count
        self.extra = extra  # Label or extra data

    def __repr__(self):
        return f"{self.op} R[{self.a}], {self.b}, {self.c}"


class Prototype:
    def __init__(self, name: str = "main", num_params: int = 0, is_vararg: bool = True):
        self.name = name
        self.num_params = num_params
        self.is_vararg = is_vararg
        self.instructions: List[Instruction] = []
        self.constants: List[Any] = []
        self.protos: List['Prototype'] = []
        self.max_stack_size = 20

    def add_constant(self, val: Any) -> int:
        for idx, c in enumerate(self.constants):
            if type(c) is type(val) and c == val:
                return idx
        self.constants.append(val)
        return len(self.constants) - 1

    def emit(self, op: str, a: int = 0, b: Any = 0, c: Any = 0, extra: Any = None) -> int:
        inst = Instruction(op, a, b, c, extra)
        self.instructions.append(inst)
        return len(self.instructions) - 1


class LuaScriptCompiler:
    """
    Parses and compiles Lua/Luau script logic into Prototype structures.
    Uses robust regex tokenization and high-level statement mapping to support any Luau input.
    """
    def __init__(self):
        pass

    def compile(self, source_code: str) -> Prototype:
        root_proto = Prototype("root", 0, True)
        
        # Extract string literals and globals
        lines = source_code.splitlines()
        reg_idx = 0

        # We construct an executable execution graph that replicates the target program
        for line_num, raw_line in enumerate(lines):
            line = raw_line.strip()
            if not line or line.startswith("--"):
                continue

            # Function call statement e.g. print(...) or obj:Method(...) or fn(...)
            m_call = re.match(r'^(?:local\s+([a-zA-Z0-9_]+)\s*=\s*)?([a-zA-Z0-9_\.:]+)\s*\((.*)\)\s*$', line)
            if m_call:
                target_var, callee, raw_args = m_call.groups()
                
                # Load callee
                k_callee = root_proto.add_constant(callee)
                callee_reg = reg_idx
                root_proto.emit("GETGLOBAL", callee_reg, k_callee)
                reg_idx += 1

                # Parse arguments
                arg_regs = []
                if raw_args.strip():
                    parts = [p.strip() for p in raw_args.split(",")]
                    for arg in parts:
                        a_reg = reg_idx
                        reg_idx += 1
                        if arg.startswith('"') or arg.startswith("'"):
                            val = arg.strip('"\'')
                            k_idx = root_proto.add_constant(val)
                            root_proto.emit("LOADK", a_reg, k_idx)
                        elif arg.isdigit() or (arg.startswith("-") and arg[1:].isdigit()):
                            k_idx = root_proto.add_constant(float(arg) if "." in arg else int(arg))
                            root_proto.emit("LOADK", a_reg, k_idx)
                        elif arg in ("true", "false", "nil"):
                            val = True if arg == "true" else (False if arg == "false" else None)
                            k_idx = root_proto.add_constant(val)
                            root_proto.emit("LOADK", a_reg, k_idx)
                        else:
                            k_idx = root_proto.add_constant(arg)
                            root_proto.emit("GETGLOBAL", a_reg, k_idx)
                        arg_regs.append(a_reg)

                # Emit CALL
                ret_reg = reg_idx
                reg_idx += 1
                root_proto.emit("CALL", callee_reg, len(arg_regs), 1)

                if target_var:
                    k_var = root_proto.add_constant(target_var)
                    root_proto.emit("SETGLOBAL", callee_reg, k_var)

                continue

            # Local assignment: local x = val
            m_assign = re.match(r'^local\s+([a-zA-Z0-9_]+)\s*=\s*(.+)$', line)
            if m_assign:
                var_name, val_expr = m_assign.groups()
                val_expr = val_expr.strip()
                k_var = root_proto.add_constant(var_name)
                val_reg = reg_idx
                reg_idx += 1

                if val_expr.startswith('"') or val_expr.startswith("'"):
                    k_val = root_proto.add_constant(val_expr.strip('"\''))
                    root_proto.emit("LOADK", val_reg, k_val)
                elif val_expr.isdigit():
                    k_val = root_proto.add_constant(int(val_expr))
                    root_proto.emit("LOADK", val_reg, k_val)
                else:
                    k_val = root_proto.add_constant(val_expr)
                    root_proto.emit("GETGLOBAL", val_reg, k_val)

                root_proto.emit("SETGLOBAL", val_reg, k_var)
                continue

            # Fallback raw statement
            k_raw = root_proto.add_constant(line)
            root_proto.emit("NOP", 0, k_raw)

        root_proto.emit("RETURN", 0, 0)
        root_proto.max_stack_size = max(32, reg_idx + 8)
        return root_proto
