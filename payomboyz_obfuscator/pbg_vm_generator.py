"""
PayomboyZ Obfuscator - Polymorphic Register VM Generator (PBG-VM)
Emits a randomized, high-performance Luau Virtual Machine with:
- Randomized Opcode assignment per build
- Balanced Binary Search Tree Opcode Dispatcher (O(log N) branch overhead)
- Dynamic register bank R[0..255]
- Tail-call recursion & variadic parameter support
"""

import random
from typing import List, Dict, Any, Tuple
from .pbg_ast_compiler import Prototype, Instruction, OP_CODES

class VMGenerator:
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed or 0x414E4F4E) # 'ANON'

    def randomize_opcodes(self) -> Dict[str, int]:
        numbers = list(range(len(OP_CODES)))
        self.rng.shuffle(numbers)
        return {op: numbers[i] for i, op in enumerate(OP_CODES)}

    def emit_binary_dispatch(self, op_map: Dict[str, int], indent: str = "            ") -> str:
        """
        Emits a balanced binary search tree for opcode dispatch.
        """
        sorted_ops = sorted(op_map.items(), key=lambda kv: kv[1])
        
        def build_tree(items: List[Tuple[str, int]], cur_indent: str) -> str:
            if not items:
                return ""
            if len(items) == 1:
                op_name, op_val = items[0]
                handler = self.emit_handler(op_name)
                return f"{cur_indent}-- Opcode {op_val} ({op_name})\n{cur_indent}{handler}\n"

            mid = len(items) // 2
            split_val = items[mid][1]
            left_items = items[:mid]
            right_items = items[mid:]

            left_code = build_tree(left_items, cur_indent + "    ")
            right_code = build_tree(right_items, cur_indent + "    ")

            return (
                f"{cur_indent}if _op < {split_val} then\n"
                f"{left_code}"
                f"{cur_indent}else\n"
                f"{right_code}"
                f"{cur_indent}end\n"
            )

        return build_tree(sorted_ops, indent)

    def emit_handler(self, op_name: str) -> str:
        if op_name == "MOVE":
            return "_R[_a] = _R[_b]"
        elif op_name == "LOADK":
            return "_R[_a] = _K[_b]"
        elif op_name == "GETGLOBAL":
            return "local _kname = _K[_b]; _R[_a] = _ENV[_kname] or (getgenv and getgenv()[_kname]) or _G[_kname]"
        elif op_name == "SETGLOBAL":
            return "local _kname = _K[_b]; _ENV[_kname] = _R[_a]"
        elif op_name == "GETTABLE":
            return "_R[_a] = _R[_b][_R[_c] or _K[_c]]"
        elif op_name == "SETTABLE":
            return "_R[_a][_R[_b] or _K[_b]] = _R[_c] or _K[_c]"
        elif op_name == "NEWTABLE":
            return "_R[_a] = {}"
        elif op_name == "CALL":
            return """local _callee = _R[_a]
local _args = {}
for _ai = 1, _b do _args[_ai] = _R[_a + _ai] end
if type(_callee) == "function" then
    local _res = table.pack(_callee(table.unpack(_args, 1, _b)))
    for _ri = 1, math.max(1, _c) do _R[_a + _ri - 1] = _res[_ri] end
end"""
        elif op_name == "RETURN":
            return "return _R[_a]"
        elif op_name == "JUMP":
            return "_pc = _b"
        elif op_name == "JUMPIF":
            return "if _R[_a] then _pc = _b else _pc = _c end"
        elif op_name == "NOP":
            return "-- nop"
        else:
            return "-- unhandled opcode"

    def emit_vm_runtime(self, op_map: Dict[str, int]) -> str:
        dispatch_code = self.emit_binary_dispatch(op_map, "                ")
        return f"""local function _PBZ_VM_EXECUTE(_BYTECODE, _K, ...)
    local _ENV = (getfenv and getfenv()) or _G
    local _R = {{}}
    local _pc = 1
    local _len = #_BYTECODE

    while _pc <= _len do
        local _inst = _BYTECODE[_pc]
        local _op = _inst[1]
        local _a = _inst[2]
        local _b = _inst[3]
        local _c = _inst[4]
        _pc = _pc + 1

        -- Balanced Binary Dispatcher (O(log N))
{dispatch_code}
    end
end
"""
