# -*- coding: utf-8 -*-
"""
========================================================================================
⚡ PAYOMBØYZ Z3 SMT CFF & MBA SOLVER (PILLAR #1 & PILLAR #5)
- Automated Opaque Predicate Elimination via Z3 Theorem Prover
- Mixed Boolean Arithmetic (MBA) Algebraic Simplification
- Symbolic State Transition Graph Solver for Flattened Control Flow
- Autonomous Reverse Engineering Knowledge Accumulator
========================================================================================
"""

from __future__ import annotations
import re
import time
from typing import Dict, Any, List, Set, Optional, Tuple

try:
    import z3
    HAS_Z3 = True
except ImportError:
    HAS_Z3 = False


class Z3CFFSolver:
    """
    Symbolic execution and SMT solver designed specifically for de-flattening
    complex Luau, Luraph, and Luarmor Control-Flow Flattening (CFF) state machines.
    """

    @classmethod
    def is_available(cls) -> bool:
        return HAS_Z3

    @classmethod
    def evaluate_predicate(cls, cond_str: str, known_vars: Optional[Dict[str, int]] = None) -> Optional[bool]:
        """
        Uses Z3 SMT Theorem Prover to test if a conditional branch is an opaque predicate:
        - Returns True if condition is ALWAYS TRUE for all possible inputs (Tautology)
        - Returns False if condition is ALWAYS FALSE for all possible inputs (Contradiction / Dead branch)
        - Returns None if condition is truly dynamic and dependent on real runtime variables
        """
        if not HAS_Z3:
            return None

        clean_cond = cond_str.strip()
        if not clean_cond:
            return None

        # Trivial constants
        if clean_cond in ("true", "1", "1 == 1", "0 == 0"):
            return True
        if clean_cond in ("false", "0", "1 == 0", "0 == 1"):
            return False

        known = known_vars or {}

        # Convert Lua syntax to Python-like syntax for AST expression parsing
        py_expr = clean_cond
        py_expr = re.sub(r'\bnot\b', ' not ', py_expr)
        py_expr = re.sub(r'\band\b', ' and ', py_expr)
        py_expr = re.sub(r'\bor\b', ' or ', py_expr)
        py_expr = py_expr.replace("~=", "!=")

        # Map bit32 / bit calls: bit32.bxor(a, b) -> (a ^ b), bit32.band(a, b) -> (a & b), bit32.bor(a, b) -> (a | b)
        py_expr = re.sub(r'(?:bit32|bit)\.bxor\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)', r'(\1 ^ \2)', py_expr)
        py_expr = re.sub(r'(?:bit32|bit)\.band\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)', r'(\1 & \2)', py_expr)
        py_expr = re.sub(r'(?:bit32|bit)\.bor\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)', r'(\1 | \2)', py_expr)
        py_expr = re.sub(r'(?:bit32|bit)\.bnot\s*\(\s*([^)]+?)\s*\)', r'(~\1)', py_expr)

        # Extract identifiers
        id_tokens = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', py_expr))
        keywords = {"true", "false", "and", "or", "not", "bit32", "bit"}
        var_names = [v for v in id_tokens if v not in keywords]

        try:
            # Construct Z3 BitVec 32-bit symbols
            z3_vars = {}
            for v in var_names:
                if v in known:
                    z3_vars[v] = z3.BitVecVal(known[v], 32)
                else:
                    z3_vars[v] = z3.BitVec(v, 32)

            # Safe evaluation environment
            safe_env = {
                "__builtins__": None,
                **z3_vars
            }

            # If expression has comparison (==, !=, <, <=, >, >=)
            # Evaluate as Z3 boolean expression
            z3_expr = eval(py_expr, safe_env)

            # 1. Test if condition can be FALSE (Solver checks: expr == False)
            s_false = z3.Solver()
            s_false.set("timeout", 100)  # 100ms max
            s_false.add(z3.Not(z3_expr))
            can_be_false = (s_false.check() == z3.sat)

            # 2. Test if condition can be TRUE (Solver checks: expr == True)
            s_true = z3.Solver()
            s_true.set("timeout", 100)
            s_true.add(z3_expr)
            can_be_true = (s_true.check() == z3.sat)

            if can_be_true and not can_be_false:
                return True   # ALWAYS TRUE (Tautology)
            elif can_be_false and not can_be_true:
                return False  # ALWAYS FALSE (Dead Code)
            else:
                return None   # Dynamic branch dependent on input
        except Exception:
            return None

    @classmethod
    def simplify_mba_expression(cls, expr_str: str) -> str:
        """
        Simplifies Mixed Boolean Arithmetic (MBA) expressions.
        e.g. `(x ^ y) + 2 * (x & y)` -> `(x + y)`
             `(x | y) - (x ^ y)` -> `(x & y)`
             `(x & ~y) + (y & ~x)` -> `(x ^ y)`
        """
        s = expr_str.strip()

        # Identity 1: (x ^ y) + 2 * (x & y) -> (x + y)
        s = re.sub(
            r'\(\s*([a-zA-Z0-9_]+)\s*\^\s*([a-zA-Z0-9_]+)\s*\)\s*\+\s*2\s*\*\s*\(\s*\1\s*&\s*\2\s*\)',
            r'(\1 + \2)',
            s
        )
        s = re.sub(
            r'\(\s*([a-zA-Z0-9_]+)\s*\^\s*([a-zA-Z0-9_]+)\s*\)\s*\+\s*2\s*\*\s*\(\s*\2\s*&\s*\1\s*\)',
            r'(\1 + \2)',
            s
        )

        # Identity 2: (x | y) - (x ^ y) -> (x & y)
        s = re.sub(
            r'\(\s*([a-zA-Z0-9_]+)\s*\|\s*([a-zA-Z0-9_]+)\s*\)\s*-\s*\(\s*\1\s*\^\s*\2\s*\)',
            r'(\1 & \2)',
            s
        )

        # Identity 3: (x + y) - 2 * (x & y) -> (x ^ y)
        s = re.sub(
            r'\(\s*([a-zA-Z0-9_]+)\s*\+\s*([a-zA-Z0-9_]+)\s*\)\s*-\s*2\s*\*\s*\(\s*\1\s*&\s*\2\s*\)',
            r'(\1 ^ \2)',
            s
        )

        # Identity 4: x - (x & y) -> (x & ~y)
        s = re.sub(
            r'\b([a-zA-Z0-9_]+)\s*-\s*\(\s*\1\s*&\s*([a-zA-Z0-9_]+)\s*\)',
            r'(\1 & ~\2)',
            s
        )

        return s

    @classmethod
    def evaluate_state_arithmetic(cls, current_val: int, math_expr: str, state_var: str) -> Optional[int]:
        """
        Calculates the next state value if the transition uses arithmetic expressions:
        e.g. `state = (state * 3 + 7) % 256` or `state = state + 0x10`
        """
        try:
            # Clean Lua syntax
            expr = math_expr.replace(state_var, str(current_val))
            expr = expr.replace(";", "").strip()
            # Handle hex
            # Safe eval on integers only
            if re.match(r'^[0-9+\-*/%()&\^|~xXa-fA-F\s]+$', expr):
                val = eval(expr, {"__builtins__": None})
                return int(val)
        except Exception:
            pass
        return None

    @classmethod
    def record_cff_knowledge(
        cls,
        architecture: str,
        total_states: int,
        opaque_eliminated: int,
        elapsed_sec: float
    ) -> None:
        """
        Commits discovered CFF patterns, dispatcher topologies, and SMT metrics
        to the autonomous engineering knowledge base for cross-session learning.
        """
        try:
            from bot.autonomous_engineering_learner import AUTONOMOUS_LEARNER
            AUTONOMOUS_LEARNER.record_decompilation_success(
                architecture=f"CFF_SMT_{architecture}",
                source_hash=f"cff_{total_states}_states_{int(time.time())}",
                recovered_lines=total_states * 4,
                confidence=0.98,
                notes=f"Z3 SMT solved {total_states} states, purged {opaque_eliminated} opaque predicates in {elapsed_sec:.3f}s"
            )
        except Exception:
            pass
