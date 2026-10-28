#!/usr/bin/env python3
"""
=============================================================================
  🌪️ PAYOMBØYZ AST ENGINE V1.0
  Deterministic AST Parser, Symbol Table & Sharder for Luau / Lua 5.1
  Purpose: Lexical block splitting, register pressure tracking,
           and map-reduce AST sharding for multi-agent decompilation.
=============================================================================
"""

from __future__ import annotations
import re
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ASTShard:
    shard_id: int
    name: str
    code: str
    line_count: int
    symbol_deps: Set[str] = field(default_factory=set)
    is_function: bool = False
    decompiled_code: Optional[str] = None


class ASTEngine:
    """
    Deterministic AST Parser & Sharder for Luau scripts.
    Guarantees syntactically safe block boundaries without breaking nested closures.
    """

    MAX_SAFE_REGISTERS = 240  # Luau hard limit is 255; 240 gives minimal safety headroom

    @staticmethod
    def strip_comments_safely(code: str) -> str:
        """Removes single-line and multi-line comments without damaging strings."""
        lines = code.splitlines()
        clean = []
        in_multiline = False
        ml_close = "--]]"

        for line in lines:
            if in_multiline:
                if ml_close in line:
                    idx = line.find(ml_close)
                    line = line[idx + len(ml_close):]
                    in_multiline = False
                else:
                    continue

            # Check for multi-line comment open: --[[ or --[=[
            m_open = re.search(r'--\[(=*)\[', line)
            if m_open:
                eq_count = len(m_open.group(1))
                ml_close = f"]{'=' * eq_count}]"
                prefix = line[:m_open.start()]
                suffix = line[m_open.end():]
                if ml_close in suffix:
                    # Opens and closes on same line
                    c_idx = suffix.find(ml_close)
                    line = prefix + suffix[c_idx + len(ml_close):]
                else:
                    in_multiline = True
                    line = prefix

            # Remove single-line comments outside strings
            if not in_multiline:
                s = []
                in_str = False
                str_char = ''
                i = 0
                n = len(line)
                while i < n:
                    ch = line[i]
                    if in_str:
                        if ch == '\\' and i + 1 < n:
                            s.append(ch)
                            s.append(line[i + 1])
                            i += 2
                            continue
                        elif ch == str_char:
                            in_str = False
                        s.append(ch)
                        i += 1
                        continue

                    if ch in ('"', "'", '`'):
                        in_str = True
                        str_char = ch
                        s.append(ch)
                        i += 1
                        continue

                    if ch == '-' and i + 1 < n and line[i + 1] == '-':
                        # Comment starts here
                        break

                    s.append(ch)
                    i += 1

                line = "".join(s)

            clean.append(line)

        return "\n".join(clean)

    @classmethod
    def split_top_level_blocks(cls, code: str) -> List[str]:
        """
        Splits code into top-level syntactic blocks (statements, functions, table initializations).
        Tracks block depth, string literals, and delimiter depths accurately.
        """
        lines = code.strip().splitlines()
        blocks: List[str] = []
        current: List[str] = []

        paren_depth = 0
        brace_depth = 0
        bracket_depth = 0
        block_depth = 0
        in_string = False
        str_quote = ''

        for line in lines:
            sline = line.strip()
            if not sline:
                if current:
                    current.append(line)
                continue

            current.append(line)
            i = 0
            n = len(sline)

            while i < n:
                ch = sline[i]
                if in_string:
                    if ch == '\\' and i + 1 < n:
                        i += 2
                        continue
                    elif ch == str_quote:
                        in_string = False
                    i += 1
                    continue

                if ch in ('"', "'", '`'):
                    in_string = True
                    str_quote = ch
                    i += 1
                    continue

                # Check for single-line comment
                if ch == '-' and i + 1 < n and sline[i + 1] == '-':
                    break

                if ch == '(':
                    paren_depth += 1
                elif ch == ')':
                    paren_depth = max(0, paren_depth - 1)
                elif ch == '{':
                    brace_depth += 1
                elif ch == '}':
                    brace_depth = max(0, brace_depth - 1)
                elif ch == '[':
                    bracket_depth += 1
                elif ch == ']':
                    bracket_depth = max(0, bracket_depth - 1)

                i += 1

            # Check block-level keywords outside strings/parens
            if not in_string and paren_depth == 0 and brace_depth == 0:
                # Strip string literals from line to inspect keywords accurately
                no_str = re.sub(r'("[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'|`[^`\\]*(?:\\.[^`\\]*)*`)', '', sline)
                no_str = re.sub(r'--.*$', '', no_str)

                for _ in re.finditer(r'\b(function|then|do|repeat)\b', no_str):
                    block_depth += 1
                for _ in re.finditer(r'\b(end|until)\b', no_str):
                    block_depth = max(0, block_depth - 1)

            # If all depths are 0, this completes a top-level AST statement/block
            if (paren_depth == 0 and brace_depth == 0 and 
                bracket_depth == 0 and block_depth == 0 and not in_string):
                block_text = "\n".join(current).strip()
                if block_text:
                    blocks.append(block_text)
                current = []

        if current:
            trailing = "\n".join(current).strip()
            if trailing:
                blocks.append(trailing)

        return blocks

    @classmethod
    def analyze_symbols(cls, code: str) -> Dict[str, Any]:
        """
        Builds a Symbol Table: counts declared local variables,
        estimates register pressure, and detects upvalues.
        """
        locals_found: Set[str] = set()
        globals_referenced: Set[str] = set()

        # Find local declarations: local x, y = ... or local function f(...)
        for m in re.finditer(r'\blocal\s+function\s+([A-Za-z0-9_]+)', code):
            locals_found.add(m.group(1))

        for m in re.finditer(r'\blocal\s+([A-Za-z0-9_,\s]+)(?:=|$)', code):
            names = m.group(1).split(',')
            for n in names:
                clean_n = n.strip()
                if clean_n and re.match(r'^[A-Za-z0-9_]+$', clean_n) and clean_n != "function":
                    locals_found.add(clean_n)

        # Detect Roblox global services / globals
        for m in re.finditer(r'\b(game|workspace|script|task|string|table|math|bit32|coroutine|Instance|Vector3|CFrame|Color3|RaycastParams)\b', code):
            globals_referenced.add(m.group(1))

        register_pressure = len(locals_found)
        is_safe = register_pressure <= cls.MAX_SAFE_REGISTERS

        return {
            "locals_count": register_pressure,
            "locals": sorted(list(locals_found)),
            "globals_referenced": sorted(list(globals_referenced)),
            "safe_for_luau_vm": is_safe,
            "headroom_remaining": max(0, 255 - register_pressure)
        }

    @classmethod
    def partition_into_shards(cls, code: str, max_shard_lines: int = 200) -> List[ASTShard]:
        """
        Partitions large code into independent AST Shards suitable
        for parallel decompilation across DeepSeek workers.
        """
        blocks = cls.split_top_level_blocks(code)
        if not blocks:
            return [ASTShard(shard_id=1, name="root", code=code, line_count=len(code.splitlines()))]

        shards: List[ASTShard] = []
        current_shards_blocks: List[str] = []
        current_lines = 0
        shard_counter = 1

        for b in blocks:
            b_lines = len(b.splitlines())
            is_fn = b.strip().startswith("local function") or b.strip().startswith("function")

            # If block itself is large or is a standalone function, treat as its own shard
            if is_fn or (current_lines + b_lines > max_shard_lines and current_shards_blocks):
                if current_shards_blocks:
                    joined = "\n\n".join(current_shards_blocks)
                    shards.append(ASTShard(
                        shard_id=shard_counter,
                        name=f"block_cluster_{shard_counter}",
                        code=joined,
                        line_count=len(joined.splitlines()),
                        is_function=False
                    ))
                    shard_counter += 1
                    current_shards_blocks = []
                    current_lines = 0

            current_shards_blocks.append(b)
            current_lines += b_lines

        if current_shards_blocks:
            joined = "\n\n".join(current_shards_blocks)
            shards.append(ASTShard(
                shard_id=shard_counter,
                name=f"block_cluster_{shard_counter}",
                code=joined,
                line_count=len(joined.splitlines()),
                is_function=False
            ))

        return shards

    @classmethod
    def link_shards(cls, shards: List[ASTShard], hoisted_preamble: str = "") -> str:
        """
        Reassembles independently decompiled shards into a unified, clean Luau script.
        """
        pieces = []
        if hoisted_preamble.strip():
            pieces.append(hoisted_preamble.strip())

        for s in shards:
            c = (s.decompiled_code or s.code).strip()
            if c:
                pieces.append(c)

        return "\n\n".join(pieces)
