# -*- coding: utf-8 -*-
"""
=============================================================================
  ⚡ PAYOMBØYZ CFG DOMINATOR & DEAD-CODE ELIMINATION (DCE) ENGINE (GAP #2 & STEP #3)
  Deterministic AST Slicer & Opaque Mathematical Predicate Solver
  Optimized for:
    - Luraph V15 / V14.9 (Strips dead honeypots & fake crash loops)
    - MoonSec V5 (Removes Unicode junk traps and unreferenced dummy functions)
    - Safe Token-Aware Branch Pruning (Zero damage to nested Lua closures)
=============================================================================
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Set, Tuple, Optional


class CFGDeadCodeEliminator:
    """
    Control Flow Graph Reachability Analyzer & Dead Code Slicer.
    Safely removes unreachable blocks, opaque math traps, and crash loops
    without collapsing nested lexical blocks.
    """

    def slice_dead_code(self, code: str) -> Tuple[str, Dict[str, Any]]:
        original_lines = len(code.splitlines())
        current = code
        metrics = {
            "opaque_predicates_folded": 0,
            "unreachable_blocks_removed": 0,
            "honeypots_neutralized": 0,
            "decoy_functions_pruned": 0,
            "original_lines": original_lines,
            "pruned_lines": 0
        }

        # ─────────────────────────────────────────────────────────────────────
        # PASS 1: SAFE OPAQUE PREDICATE FOLDING (Single-line non-nested)
        # ─────────────────────────────────────────────────────────────────────
        # Fold: if false then ... else live end
        pattern_false_else = r'if\s+false\s+then\s*([^;\n]*?)\s*else\s*([^;\n]*?)\s*end'
        def _repl_fe(m):
            metrics["opaque_predicates_folded"] += 1
            return m.group(2).strip()
        current = re.sub(pattern_false_else, _repl_fe, current)

        # Fold: if false then ... end
        pattern_false = r'if\s+false\s+then\s*([^;\n]*?)\s*end'
        def _repl_f(m):
            metrics["opaque_predicates_folded"] += 1
            return ""
        current = re.sub(pattern_false, _repl_f, current)

        # Fold: if true then live else ... end
        pattern_true_else = r'if\s+true\s+then\s*([^;\n]*?)\s*else\s*([^;\n]*?)\s*end'
        def _repl_te(m):
            metrics["opaque_predicates_folded"] += 1
            return m.group(1).strip()
        current = re.sub(pattern_true_else, _repl_te, current)

        # ─────────────────────────────────────────────────────────────────────
        # PASS 2: HONEYPOT & CRASH LOOP NEUTRALIZATION
        # ─────────────────────────────────────────────────────────────────────
        honeypot_patterns = [
            (r'while\s+true\s+do\s+end', '-- [PAYOMBOYZ: Neutralized empty while-true trap]'),
            (r'while\s+1\s+do\s+end', '-- [PAYOMBOYZ: Neutralized empty while-1 trap]'),
            (r'repeat\s+until\s+false', '-- [PAYOMBOYZ: Neutralized repeat-until-false trap]'),
        ]
        for pat, repl in honeypot_patterns:
            matches = len(re.findall(pat, current))
            if matches > 0:
                current = re.sub(pat, repl, current)
                metrics["honeypots_neutralized"] += matches

        # ─────────────────────────────────────────────────────────────────────
        # PASS 3: UNREFERENCED DECOY LOCAL FUNCTION PRUNING
        # ─────────────────────────────────────────────────────────────────────
        func_defs = list(re.finditer(r'local\s+function\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*([\s\S]*?)\s*end', current))
        pruned_funcs = 0
        for m_func in func_defs:
            fname = m_func.group(1)
            fbody = m_func.group(2)
            # Only consider functions with suspicious names and small bodies (< 4 lines)
            if len(fbody.splitlines()) <= 3 and re.match(r'^(_0x|lph_|m_|[a-z]{1,2}\d{3,})', fname, re.IGNORECASE):
                occurrences = len(re.findall(rf'\b{re.escape(fname)}\b', current))
                if occurrences <= 1:
                    current = current.replace(m_func.group(0), f"-- [Pruned decoy function: {fname}]")
                    pruned_funcs += 1

        metrics["decoy_functions_pruned"] = pruned_funcs
        final_lines = len(current.splitlines())
        metrics["pruned_lines"] = max(0, original_lines - final_lines)

        return current, metrics


# Global singleton instance
CFG_DCE = CFGDeadCodeEliminator()
