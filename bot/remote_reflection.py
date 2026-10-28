# -*- coding: utf-8 -*-
"""
=============================================================================
  🏰 PAYOMBØYZ ROBLOX REFLECTION & REMOTE SCHEMA RESOLVER
  Eliminates Semantic Misinterpretation, Variable Shadowing & UI Hallucinations
  Capabilities:
    1. UI Loader Normalization: Binds unassigned loadstring results to canonical library names
       (replaces 'loadstring_result:...' with 'local WindUI = ...; WindUI:...').
    2. Callback Lexical Scope Unshadowing: Prevents multiple 'local function callback(...)'
       from overwriting each other by generating uniquely scoped semantic callbacks.
    3. Python Trace Leaks Stripper: Removes internal runtime diagnostic errors
       (e.g., bad argument #1 to 'v' warnings).
    4. Duplicate Trace Emission Pruning: Cleans repetitive duplicate top-level hook dumps
       caused by loop unrolling during trace emulation.
    5. Roblox Service & Remote Schema Standardization: Canonicalizes Service and RemoteEvent calls.
=============================================================================
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Set, Tuple, Optional


class RemoteReflectionEngine:
    """
    Standardizes Roblox remote calls, UI builders, and cleans trace emulation artifacts.
    """

    KNOWN_UI_LIBRARIES = {
        "windui": "WindUI",
        "rayfield": "Rayfield",
        "fluent": "Fluent",
        "orion": "OrionLib",
        "linoria": "LinoriaLib",
        "kavo": "KavoUI",
        "solaris": "SolarisUI",
        "material": "MaterialUI"
    }

    def strip_diagnostic_leaks(self, code: str) -> Tuple[str, int]:
        """
        Removes leaked internal debugger messages and python stack traces:
          -- Identified Key: "[string \"<python>\"]:1589: bad argument #1 to 'v'..."
          -- Deobfuscated via Trace Emulation
        """
        count = 0
        lines = code.splitlines()
        clean_lines = []

        leak_pattern = re.compile(
            r'^\s*--\s*(?:Identified Key:\s*\"?\[string|<python>|Reconciliation Quality Status|Pass \d \(|Total Reconciled).*$',
            re.IGNORECASE
        )

        for line in lines:
            if leak_pattern.match(line):
                count += 1
                continue
            clean_lines.append(line)

        return "\n".join(clean_lines), count

    def normalize_ui_loaders(self, code: str) -> Tuple[str, int]:
        """
        Fixes unassigned loadstring invocations followed by loadstring_result calls:
          loadstring(game:HttpGet(".../WindUI/..."))()
          local gradient = loadstring_result:Gradient(...)
          ->
          local WindUI = loadstring(game:HttpGet(".../WindUI/..."))()
          local gradient = WindUI:Gradient(...)
        """
        count = 0

        # Check if code has loadstring_result
        if "loadstring_result" not in code:
            return code, 0

        # Determine UI library name from the loadstring call
        target_lib = "Library"
        for key, name in self.KNOWN_UI_LIBRARIES.items():
            if re.search(rf'https?://[^\s"\']*?{key}', code, re.IGNORECASE):
                target_lib = name
                break

        # Check for unassigned loadstring(...)() call
        unassigned_loadstring_pat = re.compile(
            r'^\s*(loadstring\s*\(\s*game:HttpGet\s*\([^\)]+\)\s*\)\s*\(\s*\))\s*;?\s*$',
            re.MULTILINE
        )

        match = unassigned_loadstring_pat.search(code)
        if match:
            original_call = match.group(1)
            replacement = f"local {target_lib} = {original_call}"
            code = code[:match.start()] + replacement + code[match.end():]
            count += 1

        # Replace all occurrences of loadstring_result (including suffixed variants) with target_lib
        code, n_repl = re.subn(r'\bloadstring_result(?:_[A-Za-z0-9_]+)?\b', target_lib, code)
        count += n_repl

        return code, count

    def unshadow_callback_functions(self, code: str) -> Tuple[str, int]:
        """
        Resolves duplicate 'local function callback(...)' definitions that shadow each other.
        Replaces them with uniquely numbered callbacks: callback_1, callback_2, ...
        """
        count = 0
        callback_pattern = re.compile(r'\blocal\s+function\s+callback\s*\(')

        matches = list(callback_pattern.finditer(code))
        if len(matches) <= 1:
            return code, 0

        # Multi-callback collision detected: replace from back to front
        result_chars = list(code)
        counter = len(matches)

        for m in reversed(matches):
            start = m.start()
            end = m.end()
            new_decl = f"local function callback_{counter}("
            result_chars[start:end] = list(new_decl)
            counter -= 1
            count += 1

        return "".join(result_chars), count

    def prune_duplicate_emissions(self, code: str) -> Tuple[str, int]:
        """
        Prunes repetitive consecutive identical statements produced by trace hooks:
          local setclipboard = setclipboard("https://discord.gg/...")
          local setclipboard_2 = setclipboard("https://discord.gg/...")
          -> preserves single clean call
        """
        count = 0
        lines = code.splitlines()
        clean_lines: List[str] = []
        last_normalized_sig: Optional[str] = None

        for line in lines:
            sline = line.strip()
            # Normalize statement signature: strip variable declaration and digits
            # e.g., local notify_3 = WindUI:Notify(...) -> WindUI:Notify(...)
            m_assign = re.match(r'^(?:local\s+)?[A-Za-z0-9_]+(?:_\d+)?\s*=\s*(.+)$', sline)
            sig = m_assign.group(1).strip() if m_assign else sline

            # Check if sig is identical to last line and represents a duplicated notification/clipboard
            if sig and sig == last_normalized_sig and any(kw in sig for kw in ("setclipboard", "Notify", "SetTitle")):
                count += 1
                continue

            last_normalized_sig = sig
            clean_lines.append(line)

        return "\n".join(clean_lines), count

    def standardize_roblox_services(self, code: str) -> Tuple[str, int]:
        """
        Canonicalizes service indexing:
          game["GetService"](game, "Players") -> game:GetService("Players")
          workspace -> Workspace (standard Luau convention where appropriate)
        """
        count = 0

        # game["GetService"](game, "...") -> game:GetService("...")
        pat1 = re.compile(r'game\[[\'"]GetService[\'"]\]\(\s*game\s*,\s*([\'"][^\'"]+[\'"])\s*\)')
        code, n1 = pat1.subn(r'game:GetService(\1)', code)
        count += n1

        # game:service("...") -> game:GetService("...")
        pat2 = re.compile(r'game:service\(\s*([\'"][^\'"]+[\'"])\s*\)', re.IGNORECASE)
        code, n2 = pat2.subn(r'game:GetService(\1)', code)
        count += n2

        return code, count

    def run(self, code: str) -> Tuple[str, Dict[str, Any]]:
        """
        Executes full Roblox reflection and schema resolution passes.
        """
        total_leaks = 0
        total_ui = 0
        total_callbacks = 0
        total_dups = 0
        total_services = 0

        curr = code

        # Pass 1: Strip diagnostic leak comments
        curr, n_leaks = self.strip_diagnostic_leaks(curr)
        total_leaks += n_leaks

        # Pass 2: Normalize UI loader and loadstring_result
        curr, n_ui = self.normalize_ui_loaders(curr)
        total_ui += n_ui

        # Pass 3: Unshadow callback functions
        curr, n_cb = self.unshadow_callback_functions(curr)
        total_callbacks += n_cb

        # Pass 4: Prune duplicate trace emissions
        curr, n_dup = self.prune_duplicate_emissions(curr)
        total_dups += n_dup

        # Pass 5: Standardize Roblox Services
        curr, n_srv = self.standardize_roblox_services(curr)
        total_services += n_srv

        metrics = {
            "diagnostic_leaks_stripped": total_leaks,
            "ui_loaders_normalized": total_ui,
            "callbacks_unshadowed": total_callbacks,
            "duplicate_emissions_pruned": total_dups,
            "services_standardized": total_services,
            "total_transforms": total_leaks + total_ui + total_callbacks + total_dups + total_services
        }
        return curr, metrics


# Singleton instance
REMOTE_REFLECTION = RemoteReflectionEngine()
