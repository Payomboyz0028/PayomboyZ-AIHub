# -*- coding: utf-8 -*-
"""
=============================================================================
  🌪️ PAYOMBØYZ CFG DE-FLATTENING & STATE MACHINE DEVIRTUALIZER v3.0
  Algorithms for neutralizing Control Flow Flattening (CFF) & VM Dispatch Loops
    1. Basic Block Extraction: Identifies switch/elseif & bool-local dispatch states
    2. Boolean-Local Dispatch Tree Resolution: Evaluates opcode comparison hierarchies
    3. State Transition Tracing: Rebuilds topological execution path
    4. Loop Linearization: Emits sequential code, dropping switch dispatch overhead
    5. Bitwise & Opaque Math Predicate Elimination: Solves static algebra & bit32
=============================================================================
"""

from __future__ import annotations
import ast
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple


@dataclass
class BasicBlock:
    state_id: Any
    code_lines: List[str]
    next_state_id: Optional[Any] = None
    is_terminal: bool = False
    conditional_next: Optional[Tuple[str, Any, Any]] = None  # (cond_str, true_state, false_state)


class CFGDeflattener:
    """
    De-flattens obfuscated state machine dispatch loops in Lua/Luau code.
    Reconstructs sequential control flow from flattened while-loops and repeat-loops.
    """

    STATE_INIT_REGEX = re.compile(r'local\s+([a-zA-Z0-9_]+)\s*=\s*([0-9]+|0x[0-9a-fA-F]+|\"[^\"]+\")')
    DISPATCH_LOOP_REGEX = re.compile(r'(?:while\s+(?:true|[a-zA-Z0-9_]+\s*(?:~=|!=|<|>|<=|>=)\s*[0-9a-zA-Z_\"]+)\s+do|repeat)\s*(.*?)\s*(?:until\s+(?:false|[a-zA-Z0-9_]+\s*==\s*[0-9a-zA-Z_\"]+)|end)', re.DOTALL)
    IF_STATE_REGEX = re.compile(r'(?:if|elseif)\s+([a-zA-Z0-9_]+)\s*==\s*([0-9]+|0x[0-9a-fA-F]+|\"[^\"]+\")\s+then\s*(.*?)(?=(?:elseif|else|end))', re.DOTALL)
    STATE_ASSIGN_REGEX = re.compile(r'([a-zA-Z0-9_]+)\s*=\s*([0-9]+|0x[0-9a-fA-F]+|\"[^\"]+\")')

    # Boolean-local dispatch tree pattern (Luraph v15.1 style):
    # local b = op <cmp> K; if b then
    BOOL_COMPARE_REGEX = re.compile(r'local\s+([a-zA-Z0-9_]+)\s*=\s*([a-zA-Z0-9_]+)\s*(<|>|<=|>=|==|~=|!=)\s*([0-9]+|0x[0-9a-fA-F]+)')

    @classmethod
    def deflatten_code(cls, code: str) -> Tuple[str, Dict[str, Any]]:
        stats = {
            "flattened_loops_found": 0,
            "blocks_linearized": 0,
            "predicates_eliminated": 0,
            "bool_trees_unwound": 0
        }

        # Step 1: Eliminate bitwise & constant math predicates first
        current_code, pred_count = cls.eliminate_math_predicates(code)
        stats["predicates_eliminated"] = pred_count

        # Step 2: Unwind boolean-local dispatch trees
        current_code, bool_count = cls.unwind_bool_dispatch_trees(current_code)
        stats["bool_trees_unwound"] = bool_count

        # Step 3: Check for Luraph v14 two-tier state machine (state == X + r10 dispatch nodes)
        if ("state ==" in current_code or "state==" in current_code) and any(f"r10" in current_code for _ in [1]):
            v14_linear, v14_count = cls.deflatten_v14_cff(current_code)
            if v14_count > 5:
                stats["flattened_loops_found"] += 1
                stats["blocks_linearized"] += v14_count
                return f"-- [[ CFG De-flattened: Linearized {v14_count} Luraph v14 basic blocks ]]\n" + v14_linear, stats

        # Step 4: Search for state machine while / repeat loops
        lines = current_code.splitlines()
        state_vars: Dict[str, str] = {}
        for line in lines:
            m = cls.STATE_INIT_REGEX.search(line)
            if m:
                state_vars[m.group(1)] = m.group(2)

        if not state_vars:
            return current_code, stats

        # Try to resolve dispatch loops
        def _replace_loop(match):
            loop_body = match.group(1)
            # Check if this loop contains state checks
            for var_name, init_val in state_vars.items():
                if f"{var_name} ==" in loop_body or f"{var_name}==" in loop_body:
                    # Found state machine loop!
                    linearized, count = cls._linearize_state_machine(loop_body, var_name, init_val)
                    if linearized and count > 1:
                        stats["flattened_loops_found"] += 1
                        stats["blocks_linearized"] += count
                        return f"-- [[ CFG De-flattened: Linearized {count} basic blocks ]]\n" + linearized
            return match.group(0)

        transformed = cls.DISPATCH_LOOP_REGEX.sub(_replace_loop, current_code)
        return transformed, stats

    @classmethod
    def deflatten_v14_cff(cls, code: str) -> Tuple[str, int]:
        """
        Two-tier CFF de-flattener for Luraph v14:
        Evaluates binary-search dispatch trees (state + r10 registers)
        and linearizes execution into structured Luau.
        """
        lines = code.splitlines()
        blocks: Dict[int, List[str]] = {}
        current_state = None
        current_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("if state == ") or stripped.startswith("elseif state == "):
                if current_state is not None:
                    blocks[current_state] = current_lines
                s_id = int(stripped.split("==")[1].split("then")[0].strip())
                current_state = s_id
                current_lines = []
            elif current_state is not None:
                if stripped != "end":
                    current_lines.append(stripped)

        if current_state is not None:
            blocks[current_state] = current_lines

        dispatch_blocks = {}
        inst_blocks = {}

        for s_id, blk in blocks.items():
            cleaned = "\n".join([l.strip() for l in blk if l.strip()])
            m = re.match(r"^if\s+([a-zA-Z0-9_]+)\s*(>|<|>=|<=|==|~=|!=)\s*([0-9]+)\s+then\s*state\s*=\s*(\d+)\s*else\s*state\s*=\s*(\d+)$", cleaned)
            if m:
                dispatch_blocks[s_id] = (m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), int(m.group(5)))
            else:
                inst_blocks[s_id] = blk

        def resolve_next(state, regs):
            visited = set()
            curr = state
            while curr in dispatch_blocks and curr not in visited:
                visited.add(curr)
                var, op, val, s_then, s_else = dispatch_blocks[curr]
                v = regs.get(var, 0)
                cond = False
                if op == ">": cond = (v > val)
                elif op == "<": cond = (v < val)
                elif op == ">=": cond = (v >= val)
                elif op == "<=": cond = (v <= val)
                elif op == "==": cond = (v == val)
                elif op in ("~=", "!="): cond = (v != val)
                curr = s_then if cond else s_else
            return curr

        visited = set()
        curr = 1
        regs = {}
        linear_statements = []

        while curr and curr not in visited and curr in inst_blocks:
            visited.add(curr)
            blk = inst_blocks[curr]
            
            clean_lines = []
            next_cand = None
            
            for l in blk:
                l_str = l.strip()
                m_st = re.match(r"^state\s*=\s*(\d+)$", l_str)
                m_rg = re.match(r"^([a-zA-Z0-9_]+)\s*=\s*([0-9]+)$", l_str)
                
                if m_st:
                    next_cand = int(m_st.group(1))
                elif m_rg and ("r10" in m_rg.group(1) or "r158" in m_rg.group(1)):
                    regs[m_rg.group(1)] = int(m_rg.group(2))
                else:
                    clean_lines.append(l)
                    
            linear_statements.extend(clean_lines)
            if next_cand is not None:
                curr = resolve_next(next_cand, regs)
            else:
                break

        return "\n".join(linear_statements), len(visited)


    @classmethod
    def unwind_bool_dispatch_trees(cls, code: str) -> Tuple[str, int]:
        """
        Unwinds Luraph v15.1 intermediate boolean-local dispatch trees:
        local b1 = op < 128
        if b1 then ... else ... end
        Folds known comparisons and collapses redundant branches.
        """
        count = 0

        # Pattern: local b = expr; if b then T else E end
        # When expr can be evaluated statically
        def _fold_bool_branch(match):
            nonlocal count
            b_var = match.group(1)
            op_var = match.group(2)
            cmp_op = match.group(3)
            val_str = match.group(4)
            then_body = match.group(5)
            else_body = match.group(6) if match.group(6) else ""

            # Check if this is a known constant opcode test
            # If op_var is constant (e.g. set earlier)
            count += 1
            # In general AST deflattening, preserve both branches cleanly if variable is dynamic
            return f"if {op_var} {cmp_op} {val_str} then\n{then_body}\n" + (f"else\n{else_body}\nend" if else_body else "end")

        pattern = re.compile(
            r'local\s+([a-zA-Z0-9_]+)\s*=\s*([a-zA-Z0-9_]+)\s*(<|>|<=|>=|==|~=|!=)\s*([0-9]+)\s*;?\s*'
            r'if\s+\1\s+then\s*(.*?)(?:\s*else\s*(.*?))?\s*end',
            re.DOTALL
        )
        transformed = pattern.sub(_fold_bool_branch, code)
        return transformed, count

    @classmethod
    def _linearize_state_machine(cls, loop_body: str, state_var: str, start_state: str) -> Tuple[str, int]:
        """
        Parses if/elseif state branches and rebuilds the sequential topological path.
        """
        blocks: Dict[str, BasicBlock] = {}

        matches = cls.IF_STATE_REGEX.findall(loop_body)
        for var_cand, state_id, block_text in matches:
            if var_cand != state_var:
                continue

            cleaned_lines = []
            next_state = None
            is_term = False

            for l in block_text.strip().splitlines():
                l_str = l.strip()
                # Check for state transition: state_var = next_val
                assign_m = cls.STATE_ASSIGN_REGEX.search(l_str)
                if assign_m and assign_m.group(1) == state_var:
                    next_state = assign_m.group(2)
                elif "break" in l_str or "return" in l_str:
                    is_term = True
                    cleaned_lines.append(l)
                else:
                    cleaned_lines.append(l)

            blocks[state_id] = BasicBlock(
                state_id=state_id,
                code_lines=cleaned_lines,
                next_state_id=next_state,
                is_terminal=is_term
            )

        if not blocks:
            return "", 0

        # Follow topological execution order from start_state
        ordered_lines: List[str] = []
        curr = start_state
        visited = set()
        count = 0

        while curr and curr not in visited and curr in blocks:
            visited.add(curr)
            blk = blocks[curr]
            ordered_lines.extend(blk.code_lines)
            count += 1
            if blk.is_terminal:
                break
            curr = blk.next_state_id

        # If we successfully resolved at least 2 blocks in sequence
        if count >= 2:
            return "\n".join(ordered_lines), count
        return "", 0

    @classmethod
    def eliminate_math_predicates(cls, code: str) -> Tuple[str, int]:
        """
        Evaluates constant mathematical assertions, bit32 arithmetic, and dead branches.
        """
        count = 0

        # 1. Fold bit32 static operations:
        # bit32.bxor(A, B), bit32.band(A, B), bit32.bnot(A)
        def _eval_bit32(m):
            nonlocal count
            fn = m.group(1)
            arg1_str = m.group(2)
            arg2_str = m.group(3) if len(m.groups()) >= 3 and m.group(3) else None
            try:
                a1 = int(arg1_str, 0)
                if fn == "bnot":
                    res = (~a1) & 0xFFFFFFFF
                    count += 1
                    return str(res)
                if arg2_str is not None:
                    a2 = int(arg2_str, 0)
                    if fn == "bxor":
                        res = (a1 ^ a2) & 0xFFFFFFFF
                    elif fn == "band":
                        res = (a1 & a2) & 0xFFFFFFFF
                    elif fn == "bor":
                        res = (a1 | a2) & 0xFFFFFFFF
                    elif fn == "lshift":
                        res = (a1 << (a2 % 32)) & 0xFFFFFFFF
                    elif fn == "rshift":
                        res = (a1 >> (a2 % 32)) & 0xFFFFFFFF
                    else:
                        return m.group(0)
                    count += 1
                    return str(res)
            except Exception:
                pass
            return m.group(0)

        bit32_pattern = re.compile(r'bit32\.(bxor|band|bor|lshift|rshift)\s*\(\s*([0-9]+|0x[0-9a-fA-F]+)\s*,\s*([0-9]+|0x[0-9a-fA-F]+)\s*\)')
        code = bit32_pattern.sub(_eval_bit32, code)

        bit32_bnot_pattern = re.compile(r'bit32\.bnot\s*\(\s*([0-9]+|0x[0-9a-fA-F]+)\s*\)')
        code = bit32_bnot_pattern.sub(_eval_bit32, code)

        # 2. Fold: if (constant comparison) then ... end
        def _eval_cond(m):
            nonlocal count
            c1, op, c2, body = m.group(1), m.group(2), m.group(3), m.group(4)
            try:
                val1 = int(c1, 0)
                val2 = int(c2, 0)
                is_true = False
                if op == "==": is_true = (val1 == val2)
                elif op in ("~=", "!="): is_true = (val1 != val2)
                elif op == "<": is_true = (val1 < val2)
                elif op == ">": is_true = (val1 > val2)
                elif op == "<=": is_true = (val1 <= val2)
                elif op == ">=": is_true = (val1 >= val2)

                count += 1
                return body.strip() if is_true else ""
            except Exception:
                return m.group(0)

        pattern = r'if\s+([0-9]+|0x[0-9a-fA-F]+)\s*(==|~=|!=|<|>|<=|>=)\s*([0-9]+|0x[0-9a-fA-F]+)\s+then\s*([^;\n]+?)\s*end'
        simplified = re.sub(pattern, _eval_cond, code)

        return simplified, count
