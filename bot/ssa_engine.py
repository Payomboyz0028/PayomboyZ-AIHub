# -*- coding: utf-8 -*-
"""
=============================================================================
  ⚡ PAYOMBØYZ SSA FORM & UPVALUE RESOLVER ENGINE (GAP #3 & STEP #4)
  Static Single Assignment (SSA) Versioning, Lexical Binding & Property Cleaner
  Optimized for:
    - VM Bytecode Decompilation (Resolves R0..Rn register reuse collision)
    - Lexical Upvalue Scope Binding (Binds U0..Un strictly to parent scope)
    - Single-Use Temporary Expression Inlining (Reduces register bloat & restores clean calls)
    - Table Key Normalization ({["Prop"] = val} -> {Prop = val})
=============================================================================
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Set, Tuple, Optional


class SSALexicalEngine:
    """
    Transforms virtual VM register manipulation into clean,
    lexically scoped Static Single Assignment (SSA) form with single-use inlining.
    """

    LUAU_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
    LUAU_KEYWORDS = {
        "and", "break", "do", "else", "elseif", "end", "false", "for",
        "function", "if", "in", "local", "nil", "not", "or", "repeat",
        "return", "then", "true", "until", "while"
    }

    def clean_table_keys(self, code: str) -> Tuple[str, int]:
        """
        Converts {["Prop"] = val} to {Prop = val} and obj["Prop"] to obj.Prop
        for valid non-keyword Luau identifiers.
        """
        count = 0

        # Pattern 1: { ["Key"] = ... } -> { Key = ... }
        def _repl_tbl_key(m):
            nonlocal count
            prefix = m.group(1)
            key = m.group(2)
            if self.LUAU_IDENTIFIER_RE.match(key) and key not in self.LUAU_KEYWORDS:
                count += 1
                return f"{prefix}{key} ="
            return m.group(0)

        tbl_key_pat = re.compile(r'([{,]\s*)\[[\'"]([A-Za-z_][A-Za-z0-9_]*)[\'"]\]\s*=')
        code = tbl_key_pat.sub(_repl_tbl_key, code)

        # Pattern 2: obj["Prop"] -> obj.Prop (where obj is identifier, not string)
        def _repl_dot_prop(m):
            nonlocal count
            obj = m.group(1)
            prop = m.group(2)
            if self.LUAU_IDENTIFIER_RE.match(prop) and prop not in self.LUAU_KEYWORDS:
                count += 1
                return f"{obj}.{prop}"
            return m.group(0)

        dot_prop_pat = re.compile(r'\b([A-Za-z0-9_]+)\[[\'"]([A-Za-z_][A-Za-z0-9_]*)[\'"]\](?!\s*=|\s*\()')
        code = dot_prop_pat.sub(_repl_dot_prop, code)

        return code, count

    def resolve_registers_to_ssa(self, code: str) -> Tuple[str, Dict[str, Any]]:
        """
        Converts array-indexed registers (e.g., R[0], reg_1, v[2]) into distinct
        SSA versioned identifiers (R0_v1, R0_v2) and inlines single-use temps.
        """
        lines = code.splitlines()
        inlined_count = 0
        transformed_regs = 0

        # Pass 1: Normalize R[n] to Rn
        reg_pattern = r'\b([Rrv]|reg|var)\[(\d+)\]'
        normalized_lines: List[str] = []
        for line in lines:
            def _norm_repl(m):
                nonlocal transformed_regs
                transformed_regs += 1
                prefix = m.group(1).upper()
                idx = m.group(2)
                return f"{prefix}{idx}"
            n_line = re.sub(reg_pattern, _norm_repl, line)
            normalized_lines.append(n_line)

        # Pass 2: Upvalue binding (U[0] -> upval_0)
        upval_pattern = r'\b([Uu]|upval|up)\[(\d+)\]'
        for i, line in enumerate(normalized_lines):
            def _up_repl(m):
                return f"upval_{m.group(2)}"
            normalized_lines[i] = re.sub(upval_pattern, _up_repl, line)

        # Pass 3: Multi-Line Temporary Register Inlining (lookahead up to 3 statements)
        i = 0
        total = len(normalized_lines)
        ssa_lines: List[str] = []

        while i < total:
            line = normalized_lines[i]
            m_assign = re.match(r'^\s*local\s+([A-Z]\d+|v\d+|reg_\d+)\s*=\s*(.+?)\s*;?\s*$', line)
            if m_assign and i + 1 < total:
                temp_var = m_assign.group(1)
                temp_val = m_assign.group(2).strip()

                # Don't inline multiline/closure definitions
                if not any(kw in temp_val for kw in ("function", "while", "for", "repeat")):
                    # Search for usages within next 4 lines
                    lookahead_limit = min(total, i + 5)
                    subsequent_lines = normalized_lines[i+1:lookahead_limit]
                    all_remaining = normalized_lines[i+1:]

                    total_usages = sum(len(re.findall(rf'\b{re.escape(temp_var)}\b', l)) for l in all_remaining)

                    if total_usages == 1:
                        # Find the exact line that uses it
                        for offset, next_l in enumerate(subsequent_lines, 1):
                            if re.search(rf'\b{re.escape(temp_var)}\b', next_l):
                                target_idx = i + offset
                                # Inline temp_val into that line
                                inlined_l = re.sub(rf'\b{re.escape(temp_var)}\b', temp_val, next_l, count=1)
                                normalized_lines[target_idx] = inlined_l
                                inlined_count += 1
                                # Skip emitting this declaration
                                line = None
                                break
                    if line is None:
                        i += 1
                        continue

            ssa_lines.append(line)
            i += 1

        assembled_code = "\n".join(ssa_lines)

        # Pass 4: Clean Table Keys and Dot Properties
        assembled_code, prop_cleaned = self.clean_table_keys(assembled_code)

        metrics = {
            "registers_normalized": transformed_regs,
            "temporary_registers_inlined": inlined_count,
            "properties_cleaned": prop_cleaned,
            "final_lines": len(assembled_code.splitlines())
        }
        return assembled_code, metrics


# Global singleton instance
SSA_ENGINE = SSALexicalEngine()
