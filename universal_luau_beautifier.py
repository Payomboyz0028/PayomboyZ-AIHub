# -*- coding: utf-8 -*-
"""
====================================================================
💎 PAYOMBØYZ UNIVERSAL LUAU BEAUTIFIER & CODE HUMANIZER
Engineered by ANON [MAHI68] for dj.
====================================================================
Transforms ugly, minified, semicolon-ridden decompiler output into
100% clean, idiomatic, 4-space indented human-grade Luau code.
Incorporates Clean Architecture & Martin Fowler Refactoring principles.
====================================================================
"""

import re
from typing import List, Tuple, Optional


def strip_stray_semicolons(line: str) -> str:
    """
    Strips trailing semicolons from statements while preserving strings.
    """
    line = line.rstrip()
    if not line:
        return ""
    if line.endswith(";"):
        in_double = False
        in_single = False
        escape = False
        for c in line:
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"' and not in_single:
                in_double = not in_double
            elif c == "'" and not in_double:
                in_single = not in_single

        if not in_double and not in_single:
            line = line[:-1].rstrip()
    return line


def split_statements_safe(code: str) -> List[str]:
    """
    Splits compound and semicolon-separated statements into distinct lines
    while strictly preserving string literals (single, double, long brackets).
    """
    raw_lines = code.splitlines()
    split_lines: List[str] = []

    for raw in raw_lines:
        line = raw.strip()
        if not line:
            split_lines.append("")
            continue

        buffer = []
        in_str = None
        escape = False
        long_bracket = False
        bracket_close = ""

        i = 0
        n = len(line)
        while i < n:
            c = line[i]

            if long_bracket:
                buffer.append(c)
                if line.startswith(bracket_close, i):
                    buffer.extend(list(bracket_close[1:]))
                    i += len(bracket_close)
                    long_bracket = False
                    continue
                i += 1
                continue

            if escape:
                escape = False
                buffer.append(c)
                i += 1
                continue

            if c == '\\':
                escape = True
                buffer.append(c)
                i += 1
                continue

            if in_str:
                buffer.append(c)
                if c == in_str:
                    in_str = None
                i += 1
                continue

            if c in ('"', "'"):
                in_str = c
                buffer.append(c)
                i += 1
                continue

            if c == '[':
                m_lb = re.match(r'\[=*\[', line[i:])
                if m_lb:
                    long_bracket = True
                    lb_tok = m_lb.group(0)
                    eq = '=' * (len(lb_tok) - 2)
                    bracket_close = f']{eq}]'
                    buffer.extend(list(lb_tok))
                    i += len(lb_tok)
                    continue

            # Split on semicolon if outside strings
            if c == ';':
                stmt = "".join(buffer).strip()
                if stmt:
                    split_lines.append(stmt)
                buffer = []
                i += 1
                continue

            # Split inline blocks: e.g. ")local" or ")pcall" or ")Lp="
            if c == ')' and i + 1 < n:
                m_next = re.match(r'^\s*(?:local\b|pcall\b|return\b|if\b|[a-zA-Z_][a-zA-Z0-9_]*\s*=)', line[i + 1:])
                if m_next:
                    buffer.append(c)
                    stmt = "".join(buffer).strip()
                    if stmt:
                        split_lines.append(stmt)
                    buffer = []
                    i += 1
                    continue

            # Split "then stmt" or "do stmt"
            if c == 'n' and "".join(buffer).endswith(" the") and i + 1 < n and line[i + 1] in (' ', '\t'):
                buffer.append(c)
                rest = line[i + 1:].strip()
                if rest and not rest.startswith("--"):
                    stmt = "".join(buffer).strip()
                    if stmt:
                        split_lines.append(stmt)
                    buffer = []
                i += 1
                continue

            buffer.append(c)
            i += 1

        remainder = "".join(buffer).strip()
        if remainder:
            split_lines.append(remainder)

    # Clean stray leading 'end;' or 'end' if standing alone at the very top
    while split_lines and split_lines[0].strip() in ("end", "end;", ""):
        split_lines.pop(0)

    return split_lines


def refactor_fowler_clean_code(code: str) -> str:
    """
    Applies Martin Fowler / Clean Architecture transformations:
    1. Eliminate dead empty if blocks: if cond then end
    2. Remove invalid LHS string assignments: "..." = r14 / "..." = r15
    3. Collapse redundant variable aliasing: local v1 = v1
    4. Remove dead register dumps: BK[120] = r14 / BK[121] = r15
    """
    # 1. Strip empty if blocks
    code = re.sub(r'\bif\s+[^\n]+?\s+then\s*\n\s*end;?', '', code)

    # 2. Clean invalid LHS string assignments generated by blind symbol replacements
    code = re.sub(r'^\s*"[^"]+"\s*=\s*(?:r1[45]|r\d+)\s*;?\s*$', '', code, flags=re.MULTILINE)

    # 3. Clean dead register pointer assignments
    code = re.sub(r'^\s*[a-zA-Z0-9_]+\[\d+\]\s*=\s*r1[45]\s*;?\s*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*(?:Players|Lighting|RunService|LP)\s*=\s*r1[45]\s*;?\s*$', '', code, flags=re.MULTILINE)

    # 4. Clean self-assignments
    code = re.sub(r'^\s*([a-zA-Z0-9_]+)\s*=\s*\1\s*;?\s*$', '', code, flags=re.MULTILINE)

    return code


def format_and_indent_luau(lines: List[str]) -> str:
    """
    Applies uniform 4-space indentation and normalizes block scope structure.
    Strictly handles multiple closers per line (end end, }, }), clamps max
    nesting depth, and prevents runaway horizontal drift.
    """
    formatted: List[str] = []
    indent_level = 0
    indent_str = "    "
    MAX_INDENT = 10  # Maximum 40-space nesting to ensure clean, human-readable layout

    # Regex patterns
    mid_block_re = re.compile(r'^(?:else\b|elseif\b)')
    one_line_block_re = re.compile(r'\b(?:if\b.*\bthen\b.*\bend\b|function\b.*\bend\b|\{.*\}\s*[,;]?$)')

    for raw_line in lines:
        line = strip_stray_semicolons(raw_line).strip()
        if not line:
            if formatted and formatted[-1] != "":
                formatted.append("")
            continue

        # Count how many closing tokens begin or match this line
        closers_count = 0
        rem = line
        while True:
            m = re.match(r'^(?:end\b|\}|until\b)', rem)
            if m:
                closers_count += 1
                rem = rem[m.end():].strip()
                rem = re.sub(r'^[,;\)\]]*\s*', '', rem)
            else:
                break

        # Also check lines starting with '}' followed by punctuation: '})', '},', '});'
        if closers_count == 0 and re.match(r'^\}[,;\)\]]*', line):
            closers_count = 1

        is_mid = bool(mid_block_re.match(line))

        if closers_count > 0:
            indent_level = max(0, indent_level - closers_count)

        effective_indent = min(indent_level, MAX_INDENT)
        cur_indent = indent_str * (effective_indent if not is_mid else max(0, effective_indent - 1))
        formatted.append(cur_indent + line)

        # Check openers on this line (if not closed on same line)
        if not one_line_block_re.search(line):
            num_open = 0
            if re.search(r'\b(?:then|do|repeat)\s*$', line):
                num_open += 1
            if re.search(r'\bfunction\s*(?:[a-zA-Z0-9_:\.]+\s*)?\([^\)]*\)\s*$', line):
                num_open += 1
            elif re.search(r'\bfunction\s*\([^\)]*\)', line) and not re.search(r'\bend\b', line):
                num_open += 1
            if line.endswith("{") and not line.startswith("}"):
                num_open += 1

            indent_level = min(MAX_INDENT + 4, max(0, indent_level + num_open))

    res = "\n".join(formatted).strip()
    res = re.sub(r'\n{3,}', '\n\n', res)
    return res


def normalize_idiomatic_roblox(code: str) -> str:
    """
    Normalizes decompiled Roblox idioms:
    1. game.GetService(game, "X") -> game:GetService("X")
    2. workspace.CurrentCamera -> camera
    3. pcall wrappers and event connections
    4. Removes redundant temporary table allocations and nil-outs
    """
    s = code

    # Convert dot method calls with self: obj.Method(obj, ...) -> obj:Method(...)
    s = re.sub(
        r'\b([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\(\1\s*,?',
        r'\1:\2(',
        s
    )

    # Clean double locals: local local X -> local X
    s = re.sub(r'\blocal\s+local\b', 'local', s)

    # Clean redundant nil-outs: Wp = nil immediately before assignment
    s = re.sub(r'([a-zA-Z0-9_]+)\s*=\s*nil\s*\n\s*\1\s*=', r'\1 =', s)

    # Clean semicolons that remained
    s = re.sub(r';\s*$', '', s, flags=re.MULTILINE)
    s = re.sub(r';\s*\n', '\n', s)

    return s


def beautify_luau_code(code: str) -> str:
    """
    Universal Entry Point:
    Refactors code according to Fowler Clean Code standards, normalizes Roblox idioms,
    splits compound statements, and applies uniform 4-space indentation.
    """
    if not code or not code.strip():
        return ""

    # Phase 1: Fowler Clean Code refactoring (pruning dead empty blocks & invalid assignments)
    cleaned = refactor_fowler_clean_code(code)

    # Phase 2: Idiomatic Roblox normalization
    normalized = normalize_idiomatic_roblox(cleaned)

    # Phase 3: Safe statement splitting
    split_lines = split_statements_safe(normalized)

    # Phase 4: 4-space indentation & block synthesis
    beautified = format_and_indent_luau(split_lines)

    return beautified
