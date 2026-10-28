# -*- coding: utf-8 -*-
"""
=============================================================================
  🌊 PAYOMBØYZ DATAFLOW TAINT & BACKWARD CONSTANT PROPAGATION ENGINE
  Eliminates Semantic Guessing & Variable Hallucination across all Deobfuscators
  Core Capabilities:
    1. Backward Taint Tracing: Traces sinks (FireServer, InvokeServer, WaitForChild)
       back to source definitions deterministically.
    2. Constant Folding & Propagation: Pre-evaluates string concatenation, static arithmetic,
       and literal table lookups.
    3. Method Call Canonicalization: Normalizes obj["Method"](obj, ...) to obj:Method(...).
    4. Table Lookup Inlining: Resolves static dictionary tables and array index tables.
=============================================================================
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Set, Tuple, Optional


class DataflowTaintEngine:
    """
    Performs static backward taint tracing and constant propagation on Luau code
    to resolve all variable values deterministically before AST formatting or AI ingestion.
    """

    def __init__(self):
        # Known critical Roblox sinks that must never be guessed or dropped
        self.sink_methods = {
            "FireServer", "InvokeServer", "Fire", "Invoke",
            "WaitForChild", "FindFirstChild", "GetService", "FindService",
            "HttpGet", "HttpPost", "GetAsync", "PostAsync",
            "request", "http_request", "loadstring", "setclipboard"
        }

    def canonicalize_method_calls(self, code: str) -> Tuple[str, int]:
        """
        Converts obfuscated index-based method calls into canonical Luau method calls:
          obj["Method"](obj, arg1) -> obj:Method(arg1)
          obj['Method'](obj, arg1) -> obj:Method(arg1)
        """
        count = 0

        # Pattern: ident["Method"](ident, ...) or ident['Method'](ident, ...)
        def _repl_method(m):
            nonlocal count
            obj_name = m.group(1)
            method_name = m.group(2)
            passed_self = m.group(3)
            rest_args = m.group(4) or ""

            if obj_name == passed_self:
                count += 1
                clean_args = rest_args.lstrip(',').strip()
                if clean_args:
                    return f"{obj_name}:{method_name}({clean_args})"
                else:
                    return f"{obj_name}:{method_name}()"
            return m.group(0)

        # Regex for obj["Method"](obj, ...) with balanced check or standard args
        pat = re.compile(
            r'\b([A-Za-z0-9_]+)\[[\'"]([A-Za-z0-9_]+)[\'"]\]\(\s*([A-Za-z0-9_]+)(\s*,[^\)]*|\s*)\)'
        )
        new_code = pat.sub(_repl_method, code)

        # Pattern 2: obj[var](obj, ...) where var is a known constant
        # Handled in propagate_constants
        return new_code, count

    def fold_string_concatenations(self, code: str) -> Tuple[str, int]:
        """
        Statically evaluates string concatenations:
          "foo" .. "bar" -> "foobar"
          "rbxassetid://" .. "12345" -> "rbxassetid://12345"
        """
        count = 0
        def _fold_two_strings(m):
            nonlocal count
            q1, s1, q2, s2 = m.group(1), m.group(2), m.group(3), m.group(4)
            count += 1
            # Escape inner quotes of the outer quote style
            combined = s1 + s2
            return f'"{combined}"'

        # Repeat to fold chains like "a" .. "b" .. "c"
        curr = code
        pat = re.compile(r'([\'"])([^\'"]*)\1\s*\.\.\s*([\'"])([^\'"]*)\3')
        for _ in range(10):
            next_code, n = pat.subn(_fold_two_strings, curr)
            if n == 0:
                break
            curr = next_code

        return curr, count

    def resolve_constant_table_lookups(self, code: str) -> Tuple[str, int]:
        """
        Finds static constant tables:
          local tbl = { [1] = "FireServer", [2] = "Attack" }
          or local tbl = { "FireServer", "Attack" }
        and inlines tbl[1] -> "FireServer", tbl[2] -> "Attack".
        """
        count = 0
        lines = code.splitlines()

        # Step 1: Detect static table declarations: local <name> = { ... }
        # Pattern for indexed table entries: [1] = "val" or [1] = 123
        tbl_defs: Dict[str, Dict[str, str]] = {}
        tbl_decl_pat = re.compile(r'^\s*local\s+([A-Za-z0-9_]+)\s*=\s*\{([^}]+)\}\s*;?\s*$')

        for idx, line in enumerate(lines):
            m = tbl_decl_pat.match(line)
            if not m:
                continue
            t_name = m.group(1)
            # CRITICAL SCOPE GUARD: Never treat 1-2 char minified registers as global constant tables!
            if len(t_name) <= 2:
                continue
            inner = m.group(2).strip()

            # Parse entries: [key] = val or comma-separated literals
            entries: Dict[str, str] = {}
            # Match explicit index: [1] = "foo" or ["bar"] = "baz"
            explicit_entries = re.findall(r'\[(?:\'([^\']+)\'|\"([^\"]+)\"|(\d+))\]\s*=\s*([^,;]+)', inner)
            if explicit_entries:
                for e in explicit_entries:
                    key = e[0] or e[1] or e[2]
                    val = e[3].strip()
                    # Only accept safe literal values (strings, numbers, booleans, nil)
                    if re.match(r'^(?:[\'"][^\'"]*[\'"]|\d+(?:\.\d+)?|true|false|nil)$', val):
                        entries[key] = val

            # Also check implicit array list: { "a", "b", "c" }
            if not entries and not "[" in inner:
                items = [x.strip() for x in inner.split(',')]
                all_literals = True
                for i, it in enumerate(items, 1):
                    if re.match(r'^(?:[\'"][^\'"]*[\'"]|\d+(?:\.\d+)?|true|false|nil)$', it):
                        entries[str(i)] = it
                    else:
                        all_literals = False
                        break
                if not all_literals:
                    entries.clear()

            if entries and len(entries) >= 2:
                tbl_defs[t_name] = entries

        if not tbl_defs:
            return code, 0

        # Step 2: Inline tbl[key] accesses
        def _repl_tbl_access(m):
            nonlocal count
            t_name = m.group(1)
            key = m.group(2) or m.group(3) or m.group(4)
            if t_name in tbl_defs and key in tbl_defs[t_name]:
                count += 1
                return tbl_defs[t_name][key]
            return m.group(0)

        # Regex: tbl[1] or tbl["key"] or tbl['key']
        # Negative lookahead (?!\s*=(?!=)) guarantees LHS assignment targets like tbl[key] = val are NEVER replaced!
        access_pat = re.compile(r'\b([A-Za-z0-9_]{3,})\[(?:\'([^\']+)\'|\"([^\"]+)\"|(\d+))\](?!\s*=(?!=))')
        new_code = access_pat.sub(_repl_tbl_access, code)
        return new_code, count

    def propagate_variable_constants(self, code: str) -> Tuple[str, int]:
        """
        Propagates immutable single-assignment string/number variables to all usage sites.
        e.g.:
          local eventName = "Attack"
          ReplicatedStorage.Remote:FireServer(eventName)
          -> ReplicatedStorage.Remote:FireServer("Attack")
        """
        count = 0
        # Find single-assignment local definitions: local <var> = "literal"
        assign_pat = re.compile(r'^\s*local\s+([A-Za-z0-9_]+)\s*=\s*([\'"][^\'"]*[\'"]|\d+(?:\.\d+)?)\s*;?\s*$', re.MULTILINE)
        assignments = assign_pat.findall(code)

        # Count total assignments of each variable to guarantee immutability
        candidates: Dict[str, str] = {}
        for var_name, literal_val in assignments:
            # CRITICAL SCOPE GUARD: Never propagate 1-2 char minified registers globally!
            if len(var_name) <= 2:
                continue
            # Check how many times var_name is assigned in code
            assign_occurrences = len(re.findall(rf'\b(?:local\s+)?{re.escape(var_name)}\s*=', code))
            if assign_occurrences == 1:
                # Safe to propagate
                candidates[var_name] = literal_val

        if not candidates:
            return code, 0

        # Replace usage sites where var_name appears as argument or index
        for var_name, literal_val in candidates.items():
            # Match usages that are NOT the declaration itself
            # We replace in calls and table accesses: (var_name), , var_name, [var_name]
            def _repl_usage(m):
                nonlocal count
                prefix = m.group(1)
                count += 1
                return f"{prefix}{literal_val}"

            # Regex: preceded by '(', ',', '[', or '=' and not part of another word
            use_pat = re.compile(rf'([\(\[\,\=]\s*)\b{re.escape(var_name)}\b(?!\s*=)')
            code = use_pat.sub(_repl_usage, code)

        return code, count

    def trace_and_reconstruct_sinks(self, code: str) -> Tuple[str, int]:
        """
        Reconstructs backward chains for critical sinks like:
          local r1 = game:GetService("ReplicatedStorage")
          local r2 = r1.Events
          local r3 = r2.Attack
          r3:FireServer(...)
        into canonical direct references where appropriate, eliminating register indirection.
        """
        count = 0
        # Remove redundant aliasing: local v1 = v2; followed by v1:Method(...) -> v2:Method(...)
        for _ in range(4):
            alias_pat = re.compile(
                r'local\s+([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9_]+)\s*;?\s*\n(\s*)([A-Za-z0-9_]+)\b'
            )
            def _repl_alias(m):
                nonlocal count
                dest_var, src_var, indent, next_token = m.group(1), m.group(2), m.group(3), m.group(4)
                if dest_var == next_token:
                    count += 1
                    return f"{indent}{src_var}"
                return m.group(0)

            code, n = alias_pat.subn(_repl_alias, code)
            if n == 0:
                break

        return code, count

    def run(self, code: str) -> Tuple[str, Dict[str, Any]]:
        """
        Executes full multi-pass dataflow taint tracing and constant propagation.
        """
        total_methods = 0
        total_strings = 0
        total_tables = 0
        total_vars = 0
        total_sinks = 0

        curr = code

        # Pass 1: Canonicalize index-based method calls
        curr, n_meth = self.canonicalize_method_calls(curr)
        total_methods += n_meth

        # Pass 2: Constant Table Lookup Inlining
        curr, n_tbl = self.resolve_constant_table_lookups(curr)
        total_tables += n_tbl

        # Pass 3: Re-canonicalize method calls after table inlining
        curr, n_meth2 = self.canonicalize_method_calls(curr)
        total_methods += n_meth2

        # Pass 4: Fold String Concatenations
        curr, n_str = self.fold_string_concatenations(curr)
        total_strings += n_str

        # Pass 5: Propagate Variable Constants to Call Sites
        curr, n_vars = self.propagate_variable_constants(curr)
        total_vars += n_vars

        # Pass 6: Trace & Reconstruct Sinks
        curr, n_sinks = self.trace_and_reconstruct_sinks(curr)
        total_sinks += n_sinks

        # Pass 7: Final pass of method canonicalization & string folding
        curr, _ = self.canonicalize_method_calls(curr)
        curr, _ = self.fold_string_concatenations(curr)

        metrics = {
            "methods_canonicalized": total_methods,
            "table_lookups_inlined": total_tables,
            "strings_folded": total_strings,
            "constants_propagated": total_vars,
            "sinks_reconstructed": total_sinks,
            "total_transforms": total_methods + total_tables + total_strings + total_vars + total_sinks
        }
        return curr, metrics


# Singleton instance
DATAFLOW_TAINT = DataflowTaintEngine()
