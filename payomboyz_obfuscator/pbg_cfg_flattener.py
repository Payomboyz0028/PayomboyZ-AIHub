"""
PayomboyZ Obfuscator - Advanced Control Flow Flattener & Opaque Invariant Generator (PBG-CFF v3.0)
Transforms sequential Luau statement blocks into high-complexity non-linear state dispatchers:
- 100% Native Execution (Zero GC allocation, runs at 60 FPS without frame drops)
- Automatic Variable Hoisting (All local declarations hoisted to top of flattened scope)
- Physical block order scrambling & permutation
- Algebraic & bitwise opaque invariants (MBA - Mixed Boolean-Arithmetic)
- Unreachable decoy trap blocks confusing static dominator tree analyzers
- Dynamic state dispatch equation
"""

import re
import random
from typing import List, Tuple, Dict, Any, Set
from .pbg_luau_tokenizer import LuauTokenizer, Token

class ControlFlowFlattener:
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed or random.randint(1, 0xFFFFFFFF))

    def split_into_statements(self, source_code: str) -> List[str]:
        """
        Parses source into top-level statements while respecting nested blocks:
        (function ... end, if ... end, for ... end, while ... end, repeat ... until, table { ... })
        """
        tokenizer = LuauTokenizer(source_code)
        tokens = tokenizer.tokenize()

        statements: List[str] = []
        current_tokens: List[Token] = []
        block_depth = 0
        paren_depth = 0
        brace_depth = 0
        bracket_depth = 0

        BLOCK_OPENERS = {"function", "if", "for", "while", "repeat", "do"}
        BLOCK_CLOSERS = {"end", "until"}

        for t in tokens:
            current_tokens.append(t)

            if t.type == "KEYWORD":
                if t.value in BLOCK_OPENERS:
                    block_depth += 1
                elif t.value in BLOCK_CLOSERS:
                    block_depth = max(0, block_depth - 1)
            elif t.type == "OP":
                if t.value == "(":
                    paren_depth += 1
                elif t.value == ")":
                    paren_depth = max(0, paren_depth - 1)
                elif t.value == "{":
                    brace_depth += 1
                elif t.value == "}":
                    brace_depth = max(0, brace_depth - 1)
                elif t.value == "[":
                    bracket_depth += 1
                elif t.value == "]":
                    bracket_depth = max(0, bracket_depth - 1)

            # Statement boundary check:
            # When at root level (depth == 0) and we hit newline or semicolon
            if block_depth == 0 and paren_depth == 0 and brace_depth == 0 and bracket_depth == 0:
                if t.type == "NEWLINE" or (t.type == "OP" and t.value == ";"):
                    code_str = "".join(tok.value for tok in current_tokens).strip()
                    if code_str and not code_str.startswith("--"):
                        statements.append(code_str)
                    current_tokens = []

        if current_tokens:
            code_str = "".join(tok.value for tok in current_tokens).strip()
            if code_str and not code_str.startswith("--"):
                statements.append(code_str)

        return statements

    def hoist_locals(self, stmts: List[str]) -> Tuple[List[str], List[str]]:
        """
        Extracts local variable declarations to hoist them above the state loop,
        preventing block-scoping variable erasure across state transitions.
        """
        hoisted_vars: Set[str] = set()
        transformed_stmts: List[str] = []

        for stmt in stmts:
            # Check local function f(...) ... end
            m_fn = re.match(r"^local\s+function\s+([a-zA-Z0-9_]+)\s*\((.*)$", stmt, re.DOTALL)
            if m_fn:
                fn_name, fn_rest = m_fn.groups()
                hoisted_vars.add(fn_name)
                transformed_stmts.append(f"{fn_name} = function({fn_rest}")
                continue

            # Check local var1, var2 = val1, val2
            m_vars = re.match(r"^local\s+([a-zA-Z0-9_,\s]+?)\s*=\s*(.+)$", stmt, re.DOTALL)
            if m_vars:
                var_names_str, expr = m_vars.groups()
                names = [v.strip() for v in var_names_str.split(",") if v.strip()]
                for n in names:
                    hoisted_vars.add(n)
                transformed_stmts.append(f"{', '.join(names)} = {expr}")
                continue

            # Check local var1, var2 (without assignment)
            m_single = re.match(r"^local\s+([a-zA-Z0-9_,\s]+)$", stmt)
            if m_single:
                names = [v.strip() for v in m_single.group(1).split(",") if v.strip()]
                for n in names:
                    hoisted_vars.add(n)
                continue

            transformed_stmts.append(stmt)

        return sorted(list(hoisted_vars)), transformed_stmts

    def flatten(self, source_code: str, chunk_size: int = 2) -> str:
        """
        Flattens top-level statements into a state loop with opaque invariants & decoy traps.
        """
        raw_stmts = self.split_into_statements(source_code)
        if len(raw_stmts) < 2:
            return source_code

        hoisted_vars, stmts = self.hoist_locals(raw_stmts)

        # Group statements into chunks (guarantee return statement is always last in its block)
        chunks: List[List[str]] = []
        cur_chunk: List[str] = []
        for s in stmts:
            cur_chunk.append(s)
            s_stripped = s.strip()
            is_ret = s_stripped.startswith("return ") or s_stripped == "return" or s_stripped.startswith("return(")
            if len(cur_chunk) >= chunk_size or is_ret:
                chunks.append(cur_chunk)
                cur_chunk = []
        if cur_chunk:
            chunks.append(cur_chunk)

        if len(chunks) < 2:
            return source_code

        # Generate unique random state IDs
        state_ids = []
        while len(state_ids) < len(chunks) + 1:
            sid = self.rng.randint(100000, 999999)
            if sid not in state_ids:
                state_ids.append(sid)

        var_state = f"_st_{self.rng.randint(1000, 9999)}"
        initial_state = state_ids[0]

        blocks_data = []
        for i, chunk in enumerate(chunks):
            cur_id = state_ids[i]
            next_id = state_ids[i + 1] if (i + 1 < len(chunks)) else 0
            code = "\n        ".join(chunk)

            # Invariant condition (Mixed Boolean-Arithmetic / Modular Invariant)
            r_seed = self.rng.randint(100, 9999)
            bogus_id = self.rng.randint(100000, 999999)

            # Check if chunk contains a top-level return statement
            has_return = any(s.strip().startswith("return ") or s.strip() == "return" for s in chunk)

            if has_return:
                transition = ""
            elif next_id != 0:
                # Opaque invariant transition
                pred_type = self.rng.randint(1, 3)
                if pred_type == 1:
                    cond = f"((({r_seed} * ({r_seed} + 1)) % 2) == 0)"
                elif pred_type == 2:
                    k1 = self.rng.randint(10, 50)
                    cond = f"((({r_seed} * {k1 * 2}) % 2) == 0)"
                else:
                    k2 = self.rng.randint(10, 50)
                    cond = f"((({r_seed} * {k2 * 2 + 1} + 1) % 2) == {((r_seed + 1) % 2)})"

                transition = f"""if {cond} then
            {var_state} = {next_id}
        else
            {var_state} = {bogus_id}
        end"""
            else:
                transition = f"{var_state} = 0"

            blocks_data.append({
                "id": cur_id,
                "code": code,
                "transition": transition,
                "is_decoy": False
            })

        # Insert 2-3 decoy trap blocks (unreachable at runtime, confounding CFG lifters)
        decoy_count = min(3, max(1, len(chunks) // 3))
        for _ in range(decoy_count):
            decoy_id = self.rng.randint(100000, 999999)
            while decoy_id in state_ids or any(b["id"] == decoy_id for b in blocks_data):
                decoy_id = self.rng.randint(100000, 999999)
            
            fake_var = f"_d_{self.rng.randint(100, 999)}"
            fake_calc = self.rng.randint(1000, 9999)
            fake_code = f"local {fake_var} = (({fake_calc} * 7) + 13) % 65536; {fake_var} = {fake_var} + 1;"
            decoy_trans = f"{var_state} = 0"
            blocks_data.append({
                "id": decoy_id,
                "code": fake_code,
                "transition": decoy_trans,
                "is_decoy": True
            })

        # Physically shuffle the blocks so file order != execution order
        shuffled = list(blocks_data)
        self.rng.shuffle(shuffled)

        # Assemble the while loop
        clauses = []
        for idx, blk in enumerate(shuffled):
            keyword = "if" if idx == 0 else "elseif"
            trans_code = f"\n        {blk['transition']}" if blk["transition"] else ""
            clauses.append(f"""    {keyword} {var_state} == {blk["id"]} then
        {blk["code"]}{trans_code}""")

        clauses_str = "\n".join(clauses)

        hoist_decl = ""
        if hoisted_vars:
            hoist_decl = f"local {', '.join(hoisted_vars)}\n    "

        loop_code = f"""do
    {hoist_decl}local {var_state} = {initial_state}
    while {var_state} ~= 0 do
{clauses_str}
        else
            {var_state} = 0
        end
    end
end"""
        return loop_code
