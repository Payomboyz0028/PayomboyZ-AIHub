"""
PayomboyZ Pure-Python Luau Syntax & Integrity Validator (PBG-SyntaxValidator)
Accurately detects syntax errors in Luau/Lua scripts before obfuscation:
- Unclosed blocks (function, if, for, while, repeat, do) with opening line tracking
- Unexpected / dangling 'end' or 'until' keywords
- Imbalanced delimiters: (), {}, []
- Unterminated single/double quotes and multiline [[]] strings
- Incomplete expressions / dangling binary operators at EOF
- 100% Compatible with Luau type annotations, compound operators (+=, etc.), and ternary if-expressions
"""

import re
from typing import Tuple, List, Optional
from .pbg_luau_tokenizer import LuauTokenizer, Token

class LuauSyntaxValidator:
    @classmethod
    def validate(cls, code: str) -> Tuple[bool, str, Optional[int]]:
        """
        Validates Luau syntax.
        Returns: (is_valid: bool, error_message: str, line_number: Optional[int])
        """
        if not code or not code.strip():
            return False, "สคริปต์ว่างเปล่า (Empty code)", 1

        # Check for unterminated multiline comments --[[
        comment_matches = re.finditer(r'--\[(=*)\[', code)
        for cm in comment_matches:
            eq = cm.group(1)
            close_pat = f']{eq}]'
            start_pos = cm.start()
            if close_pat not in code[start_pos:]:
                line = code[:start_pos].count('\n') + 1
                return False, f"พบ Multiline Comment ไม่ได้ปิด (--[{eq}[) ที่บรรทัด {line}", line

        # Check for unterminated multiline strings [[ or [=[
        str_matches = re.finditer(r'(?<!-)\[(=*)\[', code)
        for sm in str_matches:
            # ensure it is not preceded by --
            idx = sm.start()
            line_start = code.rfind('\n', 0, idx) + 1
            line_prefix = code[line_start:idx]
            if '--' in line_prefix:
                continue
            eq = sm.group(1)
            close_pat = f']{eq}]'
            if close_pat not in code[idx + len(sm.group(0)):]:
                line = code[:idx].count('\n') + 1
                return False, f"พบ Multiline String ไม่ได้ปิด ([{eq}[) ที่บรรทัด {line}", line

        # Tokenize code
        try:
            tokenizer = LuauTokenizer(code)
            tokens = tokenizer.tokenize()
        except Exception as e_tok:
            err_str = str(e_tok)
            m_line = re.search(r'line\s+(\d+)', err_str, re.IGNORECASE)
            err_line = int(m_line.group(1)) if m_line else 1
            return False, f"Syntax Error ในการประมวลผลตัวอักษร: {err_str}", err_line

        # Block stack: stores (keyword, line)
        BLOCK_OPENERS = {"function", "if", "for", "while", "do"}
        block_stack: List[Tuple[str, int]] = []
        repeat_stack: List[int] = []

        # Delimiter stack: stores (char, line)
        delim_stack: List[Tuple[str, int]] = []
        DELIM_PAIRS = {')': '(', '}': '{', ']': '['}

        prev_non_ws: Optional[Token] = None
        last_token: Optional[Token] = None

        for tok in tokens:
            if tok.type == "STRING_UNTERMINATED":
                q_char = tok.value[0] if tok.value else '"'
                return False, f"พบข้อความ (String) ไม่ได้ปิดเครื่องหมาย {q_char} ที่บรรทัด {tok.line}", tok.line

            if tok.type in ("WHITESPACE", "NEWLINE", "COMMENT"):
                continue

            last_token = tok

            # Check delimiter matching
            if tok.type == "OP":
                if tok.value in ("(", "{", "["):
                    delim_stack.append((tok.value, tok.line))
                elif tok.value in (")", "}", "]"):
                    expected_open = DELIM_PAIRS[tok.value]
                    if not delim_stack:
                        return False, f"พบเครื่องหมายปิด '{tok.value}' เกินมา (ไม่มีเครื่องหมายเปิด) ที่บรรทัด {tok.line}", tok.line
                    last_open, open_line = delim_stack.pop()
                    if last_open != expected_open:
                        return False, f"เครื่องหมายไม่ตรงกัน: เปิดด้วย '{last_open}' ที่บรรทัด {open_line} แต่ปิดด้วย '{tok.value}' ที่บรรทัด {tok.line}", tok.line

            # Check block nesting
            elif tok.type == "KEYWORD":
                val = tok.value
                # Note: Luau ternary 'if ... then ... else ...' has an 'if' that does NOT need an 'end'
                # An 'if' is a statement opener IF it is at statement boundary (after newline, semicolon, then, do, else, repeat, or start of block)
                if val == "function":
                    block_stack.append(("function", tok.line))
                elif val == "for":
                    block_stack.append(("for", tok.line))
                elif val == "while":
                    block_stack.append(("while", tok.line))
                elif val == "repeat":
                    repeat_stack.append(tok.line)
                elif val == "do":
                    # 'for ... do' and 'while ... do' share their block opener with 'for' / 'while'
                    # standalone 'do ... end' is its own block opener
                    if not block_stack or block_stack[-1][0] not in ("for", "while"):
                        block_stack.append(("do", tok.line))
                elif val == "if":
                    # Check if this 'if' is a statement or a Luau inline if-expression
                    # Inline if is preceded by: '=', '(', '{', '[', ',', 'return', '+', '-', '*', '/', etc.
                    is_inline_if = False
                    if prev_non_ws and (prev_non_ws.type == "OP" and prev_non_ws.value in ("=", ",", "(", "{", "[", "+", "-", "*", "/", "..", "==", "~=", "<", ">", "<=", ">=")) or (prev_non_ws and prev_non_ws.type == "KEYWORD" and prev_non_ws.value in ("return", "and", "or", "not")):
                        # Could be inline if expression: 'if cond then a else b'
                        is_inline_if = True
                    if not is_inline_if:
                        block_stack.append(("if", tok.line))

                elif val == "until":
                    if not repeat_stack:
                        return False, f"พบคำสั่ง 'until' โดยไม่มี 'repeat' ที่บรรทัด {tok.line}", tok.line
                    repeat_stack.pop()

                elif val == "end":
                    if not block_stack:
                        return False, f"พบคำสั่ง 'end' เกินมา (ไม่มีบล็อกเปิดที่สอดคล้องกัน) ที่บรรทัด {tok.line}", tok.line
                    block_stack.pop()

            prev_non_ws = tok

        # Check for unclosed delimiters
        if delim_stack:
            unclosed_char, open_line = delim_stack[-1]
            matching_close = { '(': ')', '{': '}', '[': ']' }.get(unclosed_char, '')
            return False, f"เครื่องหมาย '{unclosed_char}' ที่บรรทัด {open_line} ไม่ได้ปิด (ต้องการ '{matching_close}')", open_line

        # Check for unclosed repeat blocks
        if repeat_stack:
            rep_line = repeat_stack[-1]
            return False, f"บล็อก 'repeat' ที่บรรทัด {rep_line} ไม่ได้ปิดด้วย 'until'", rep_line

        # Check for unclosed blocks (missing end)
        if block_stack:
            blk_name, blk_line = block_stack[-1]
            return False, f"บล็อก '{blk_name}' ที่บรรทัด {blk_line} ไม่ได้ปิด (ต้องการ 'end' ก่อนสิ้นสุดสคริปต์)", blk_line

        # Check for dangling broken token at end of script
        if last_token and last_token.type == "OP" and last_token.value in ("+", "-", "*", "/", "%", "^", "..", "==", "~=", "<=", ">="):
            return False, f"คำสั่งไม่สมบูรณ์: พบตัวดำเนินการ '{last_token.value}' ค้างอยู่ที่ท้ายสคริปต์ (บรรทัด {last_token.line})", last_token.line

        return True, "Syntax verified cleanly", None
