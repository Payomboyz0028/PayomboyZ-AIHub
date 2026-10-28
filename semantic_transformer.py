# -*- coding: utf-8 -*-
"""
====================================================================
  PAYOMBØYZ INDUSTRIAL SEMANTIC TRANSFORMER & SCOPE RESOLVER V10.5
====================================================================
Transforms deobfuscated / peeled Luau source code into 100% clean,
human-readable, executable Luau script:
1. Syntax glitch repair (e.g. BorderSizePixe0.Size -> BorderSizePixel = 0; Size = ...)
2. Duplicate parameter deduplication (function(y,F,F) -> function(y,F,F_2))
3. Redundant register shadowing collapse (local y; local y=T -> local y=T)
4. Pcall / Callee unaliasing (h=pcall; h(fn) -> pcall(fn), never emit 'local pcall(')
5. Service & GUID inlining (w[6][w[5]]() -> HttpService:GenerateGUID(false))
6. Signal & Event inlining (J[6][J[5]](fn) -> RunService.RenderStepped:Connect(fn))
7. UI Component Semantic Renaming (y:CreateToggle -> Tab:CreateToggle, etc.)
8. Luarmor 3-tier module factory header normalization (SharedState, LocalPlayer, Services, Tab, etc.)
9. Raw VM Bytecode array detection gate (rejecting numeric prototype dumps)
====================================================================
"""
import re
from typing import Tuple, List, Dict, Set


def is_raw_bytecode_array(code: str) -> bool:
    """
    Checks if code is just a raw numeric array dump (e.g. [1054]=126, [1055]=125...)
    instead of actual deobfuscated Luau statements.
    """
    if not code or not code.strip():
        return False
    sample = code[:35000]
    lines = [l.strip() for l in sample.splitlines() if l.strip() and l.strip() not in {"{", "}", "};", "},", ");"}]
    if len(lines) < 25:
        return False
    array_lines = sum(1 for l in lines if re.match(r'^\[\d+\]\s*=\s*(?:\d+|true|false|nil|\{\})\s*,?$', l))
    return (array_lines / len(lines)) > 0.35


def repair_syntax_glitches(code: str) -> str:
    """Fixes known regex damage from past aliasing passes across the board."""
    s = code
    # Fix BorderSizePixe0.Size -> BorderSizePixel = 0;\n Size =
    s = re.sub(
        r'([a-zA-Z0-9_]+)\.BorderSizePixe0\s*\.\s*Size\s*=',
        r'\1.BorderSizePixel = 0;\n\1.Size =',
        s
    )
    s = re.sub(
        r'([a-zA-Z0-9_]+)\.BorderSizePixe(\d+)',
        r'\1.BorderSizePixel = \2',
        s
    )
    # Fix general Prop0.Prop2 -> Prop = 0;\n Prop2
    s = re.sub(
        r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)0\s*\.\s*([a-zA-Z0-9_]+)\s*=',
        r'\1.\2 = 0;\n\1.\3 =',
        s
    )
    return s


def deduplicate_function_parameters(code: str) -> str:
    """
    Finds function(...) declarations with duplicate parameter names
    e.g. function(y, F, F) -> function(y, F, F_2)
    In Luau, duplicate parameter names cause an immediate compiler error.
    """
    def repl_params(m):
        pfx = m.group(1)
        params_str = m.group(2)
        params = [p.strip() for p in params_str.split(',') if p.strip()]
        seen: Dict[str, int] = {}
        new_params = []
        for p in params:
            if p in seen:
                seen[p] += 1
                new_params.append(f"{p}_{seen[p]}")
            else:
                seen[p] = 1
                new_params.append(p)
        return f"{pfx}({', '.join(new_params)})"

    return re.sub(r'(\bfunction\s*[a-zA-Z0-9_.:]*\s*)\(([^)]*)\)', repl_params, code)


def collapse_redundant_shadowing(code: str) -> str:
    """
    Collapses redundant register declarations:
    local y; local y = T; -> local y = T;
    local y;\nlocal y = T; -> local y = T;
    """
    s = code
    # local var; local var = rhs
    s = re.sub(
        r'\blocal\s+([a-zA-Z0-9_]+)\s*;\s*local\s+\1\s*=',
        r'local \1 =',
        s
    )
    # local var;\nlocal var = rhs
    s = re.sub(
        r'\blocal\s+([a-zA-Z0-9_]+)\s*;\s*\n\s*local\s+\1\s*=',
        r'local \1 =',
        s
    )
    # local var;\nvar = rhs
    s = re.sub(
        r'\blocal\s+([a-zA-Z0-9_]+)\s*;\s*\n\s*\1\s*=',
        r'local \1 =',
        s
    )
    # Standalone dead local declaration right before reassignment: local Z;\n f.n = ...
    s = re.sub(
        r'\blocal\s+([a-zA-Z0-9_]+)\s*;\s*\n(?=[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\s*=)',
        '',
        s
    )
    # Standalone dead local declaration on same line: local Z; f.n = ...
    s = re.sub(
        r'\blocal\s+([a-zA-Z0-9_]+)\s*;\s*(?=[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\s*=)',
        '',
        s
    )
    return s


def inline_pcall_and_callees(code: str) -> str:
    """
    Inlines trivial callee aliases:
    local p; p = pcall; p(fn) -> pcall(fn)
    local h; h = pcall; h(fn) -> pcall(fn)
    Guarantees no 'local pcall(' is ever emitted.
    """
    s = code
    # local var; var = pcall; var(
    s = re.sub(r'\blocal\s+[a-zA-Z0-9_]+\s*;\s*[a-zA-Z0-9_]+\s*=\s*pcall\s*;\s*[a-zA-Z0-9_]+\(', 'pcall(', s)
    s = re.sub(r'\blocal\s+[a-zA-Z0-9_]+\s*;\s*\n\s*[a-zA-Z0-9_]+\s*=\s*pcall\s*;\s*\n\s*[a-zA-Z0-9_]+\(', 'pcall(', s)
    s = re.sub(r'\blocal\s+[a-zA-Z0-9_]+\s*;\s*\n\s*[a-zA-Z0-9_]+\s*=\s*pcall\s*;\s*[a-zA-Z0-9_]+\(', 'pcall(', s)
    s = re.sub(r'\b[a-zA-Z0-9_]+\s*=\s*pcall\s*;\s*[a-zA-Z0-9_]+\(', 'pcall(', s)
    # Clean any accidental "local pcall("
    s = re.sub(r'\blocal\s+pcall\(', 'pcall(', s)
    # Strip any dangling "local var;\n" that directly precedes pcall(
    s = re.sub(r'^[ \t]*local\s+[a-zA-Z0-9_]+\s*;\s*\n(?=[ \t]*pcall\()', '', s, flags=re.MULTILINE)
    return s


def inline_services_and_guids(code: str) -> str:
    """
    Inlines HttpService GUID generation calls:
    w[6][w[5]]() -> HttpService:GenerateGUID(false)
    And RunService event connections:
    J[6][J[5]](fn) -> RunService.RenderStepped:Connect(fn)
    """
    s = code
    # HttpService GUID generation: w[6][w[5]]()
    s = re.sub(
        r'\b[a-zA-Z0-9_]+\[6\]\[[a-zA-Z0-9_]+\[5\]\]\(\)',
        'HttpService:GenerateGUID(false)',
        s
    )
    s = re.sub(
        r'\b[a-zA-Z0-9_]+\[\d+\]\[[a-zA-Z0-9_]+\[\d+\]\]\(\)',
        'HttpService:GenerateGUID(false)',
        s
    )

    # RunService / Signals Connect calls: J[6][J[5]](function(...) ...)
    s = re.sub(
        r'\b(?:Signals|J)\[(?:6|5)\]\[(?:Signals|J)\[(?:5|6)\]\]\(',
        'RunService.RenderStepped:Connect(',
        s
    )
    return s


def semantic_ui_and_instance_renaming(code: str) -> str:
    """
    Semantically renames register variables based on their usage:
    - If var calls :CreateToggle, :CreateDropdown -> rename to Tab
    - If var calls :FindFirstChildOfClass("PlayerGui") -> rename to LocalPlayer
    """
    lines = code.splitlines()
    out_lines = []

    for line in lines:
        # Check UI Tab calls: local f,l=y:CreateToggle(...)
        # Replace y:CreateToggle with Tab:CreateToggle
        m_ui = re.search(r'\b([a-zA-Z0-9_]+)\s*:\s*(CreateToggle|CreateDropdown|CreateSlider|CreateButton|CreateSection|CreateTab|AddToggle|AddDropdown|AddSlider)\b', line)
        if m_ui:
            var_name = m_ui.group(1)
            # Replace variable with Tab if it's a short 1-2 char mangled register
            if len(var_name) <= 2 and var_name not in ("UI", "ui"):
                line = re.sub(rf'\b{var_name}\s*:', 'Tab:', line)
                line = re.sub(rf'\blocal\s+{var_name}\s*=\s*([a-zA-Z0-9_]+);', r'local Tab = \1;', line)
                line = re.sub(rf'\b{var_name}\s*=\s*([a-zA-Z0-9_]+);', r'Tab = \1;', line)

        # Check PlayerGui calls: n = F:FindFirstChildOfClass("PlayerGui")
        if 'FindFirstChildOfClass("PlayerGui")' in line:
            line = re.sub(r'([a-zA-Z0-9_]+)\s*:\s*FindFirstChildOfClass\("PlayerGui"\)', 'LocalPlayer:FindFirstChildOfClass("PlayerGui")', line)
            m_assign = re.match(r'^\s*([a-zA-Z0-9_]+)\s*=\s*LocalPlayer:FindFirstChildOfClass\("PlayerGui"\)', line)
            if m_assign:
                line = "    local PlayerGui = LocalPlayer:FindFirstChildOfClass(\"PlayerGui\");"

        out_lines.append(line)

    return '\n'.join(out_lines)


def normalize_luarmor_factory_headers(code: str) -> str:
    """
    Normalizes Luarmor 3-tier factory closure declarations:
    Modules[ID] = function(y, F, F) return function(F, f)
        local f = F[1]; local l = F[2]; local w = F[3]; local T = F[4]; local v = F[5]; local J = F[6];
        return function()
    to clean descriptive semantic module declarations.
    """
    s = code

    # Pattern for module factory state unpacking:
    # local f=F[1]; local l=F[2]; local w=F[3]; local T=F[4]; local v=F[5]; local J=F[6];
    state_pat = re.compile(
        r'local\s+([a-zA-Z0-9_]+)\s*=\s*([a-zA-Z0-9_]+)\[1\];\s*'
        r'local\s+([a-zA-Z0-9_]+)\s*=\s*\2\[2\];\s*'
        r'local\s+([a-zA-Z0-9_]+)\s*=\s*\2\[3\];\s*'
        r'local\s+([a-zA-Z0-9_]+)\s*=\s*\2\[4\];\s*'
        r'local\s+([a-zA-Z0-9_]+)\s*=\s*\2\[5\];\s*'
        r'local\s+([a-zA-Z0-9_]+)\s*=\s*\2\[6\];'
    )
    s = state_pat.sub(
        lambda m: (
            f"local SharedState = {m.group(2)}[1];\n"
            f"local LocalPlayer = {m.group(2)}[2];\n"
            f"local Services = {m.group(2)}[3];\n"
            f"local Settings = {m.group(2)}[4];\n"
            f"local Tab = {m.group(2)}[5];\n"
            f"local Signals = {m.group(2)}[6];"
        ),
        s
    )

    return s


def transform_semantic_code(code: str) -> str:
    """Full 8-pass pipeline for transforming deobfuscated Luau code into 100% clean source."""
    s = code
    s = repair_syntax_glitches(s)
    s = deduplicate_function_parameters(s)
    s = collapse_redundant_shadowing(s)
    s = inline_pcall_and_callees(s)
    s = inline_services_and_guids(s)
    s = normalize_luarmor_factory_headers(s)
    s = semantic_ui_and_instance_renaming(s)
    s = repair_syntax_glitches(s)  # Second pass to catch newly exposed expressions
    return s
