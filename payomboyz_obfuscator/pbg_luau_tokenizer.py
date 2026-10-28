"""
PayomboyZ Luau Tokenizer & Lexical Analyzer (PBG-Tokenizer)
Handles all Luau-specific extensions:
- Compound operators (+=, -=, *=, /=, //=, %=, ^=, ..=)
- Types annotations (::, :)
- Raw strings (single, double, multiline [[ ]], [=[ ]=])
- Comments (-- and --[[ ]])
- Numbers (decimal, hex, binary, scientific)
"""

import re
from typing import List, Tuple, Optional

class Token:
    def __init__(self, t_type: str, value: str, line: int = 1, col: int = 1):
        self.type = t_type   # 'KEYWORD', 'IDENT', 'NUMBER', 'STRING', 'OP', 'SYMBOL', 'COMMENT', 'WHITESPACE', 'NEWLINE'
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)})"


LUAU_KEYWORDS = {
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "if", "in", "local", "nil", "not", "or", "repeat",
    "return", "then", "true", "until", "while", "continue"
}

COMPOUND_OPS = {
    "+=", "-=", "*=", "/=", "//=", "%=", "^=", "..="
}

MULTI_CHAR_OPS = {
    "==", "~=", "<=", ">=", "..", "...", "::", "//"
}

SINGLE_CHAR_OPS = set("+-*/%^#=<>~(){}[];:,.|&")

class LuauTokenizer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.length = len(source)
        self.line = 1
        self.col = 1

    def peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx < self.length:
            return self.source[idx]
        return ""

    def advance(self) -> str:
        if self.pos < self.length:
            ch = self.source[self.pos]
            self.pos += 1
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            return ch
        return ""

    def match(self, text: str) -> bool:
        if self.source.startswith(text, self.pos):
            for _ in range(len(text)):
                self.advance()
            return True
        return False

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self.pos < self.length:
            start_line = self.line
            start_col = self.col
            ch = self.peek()

            # 1. Whitespace
            if ch in (" ", "\t", "\r"):
                buf = self.advance()
                while self.peek() in (" ", "\t", "\r"):
                    buf += self.advance()
                tokens.append(Token("WHITESPACE", buf, start_line, start_col))
                continue

            # 2. Newline
            if ch == "\n":
                self.advance()
                tokens.append(Token("NEWLINE", "\n", start_line, start_col))
                continue

            # 3. Comments (single line and multiline)
            if ch == "-" and self.peek(1) == "-":
                self.advance()
                self.advance()
                buf = "--"
                # Check multiline comment --[=*[
                if self.peek() == "[":
                    equals_count = 0
                    idx = 1
                    while self.peek(idx) == "=":
                        equals_count += 1
                        idx += 1
                    if self.peek(idx) == "[":
                        # Multiline comment
                        closing_pattern = "]" + ("=" * equals_count) + "]"
                        for _ in range(idx + 1):
                            buf += self.advance()
                        while self.pos < self.length:
                            if self.match(closing_pattern):
                                buf += closing_pattern
                                break
                            buf += self.advance()
                        tokens.append(Token("COMMENT", buf, start_line, start_col))
                        continue

                # Single line comment
                while self.pos < self.length and self.peek() != "\n":
                    buf += self.advance()
                tokens.append(Token("COMMENT", buf, start_line, start_col))
                continue

            # 4. Multiline Strings [[ ... ]] or [=*[ ... ]=*]
            if ch == "[":
                equals_count = 0
                idx = 1
                while self.peek(idx) == "=":
                    equals_count += 1
                    idx += 1
                if self.peek(idx) == "[":
                    closing_pattern = "]" + ("=" * equals_count) + "]"
                    buf = ""
                    for _ in range(idx + 1):
                        buf += self.advance()
                    while self.pos < self.length:
                        if self.match(closing_pattern):
                            buf += closing_pattern
                            break
                        buf += self.advance()
                    tokens.append(Token("STRING", buf, start_line, start_col))
                    continue

            # 5. Single / Double Quoted Strings
            if ch in ('"', "'"):
                quote = self.advance()
                buf = quote
                closed = False
                while self.pos < self.length:
                    c = self.advance()
                    buf += c
                    if c == "\\":
                        if self.pos < self.length:
                            buf += self.advance()
                    elif c == quote:
                        closed = True
                        break
                    elif c == "\n":
                        # Raw newline in single/double quoted string is a syntax error in Lua
                        break
                if closed:
                    tokens.append(Token("STRING", buf, start_line, start_col))
                else:
                    tokens.append(Token("STRING_UNTERMINATED", buf, start_line, start_col))
                continue

            # 6. Numbers (hex, binary, float, integer, scientific)
            if ch.isdigit() or (ch == "." and self.peek(1).isdigit()):
                buf = ""
                # Check hex 0x... or binary 0b...
                if ch == "0" and self.peek(1) in ("x", "X"):
                    buf += self.advance() + self.advance()
                    while self.peek() in "0123456789abcdefABCDEF_":
                        buf += self.advance()
                elif ch == "0" and self.peek(1) in ("b", "B"):
                    buf += self.advance() + self.advance()
                    while self.peek() in "01_":
                        buf += self.advance()
                else:
                    seen_dot = False
                    seen_exp = False
                    while self.pos < self.length:
                        c = self.peek()
                        if c.isdigit() or c == "_":
                            buf += self.advance()
                        elif c == "." and not seen_dot and not seen_exp:
                            seen_dot = True
                            buf += self.advance()
                        elif c in ("e", "E") and not seen_exp:
                            seen_exp = True
                            buf += self.advance()
                            if self.peek() in ("+", "-"):
                                buf += self.advance()
                        else:
                            break
                tokens.append(Token("NUMBER", buf, start_line, start_col))
                continue

            # 7. Identifiers & Keywords
            if ch.isalpha() or ch == "_":
                buf = self.advance()
                while self.peek().isalnum() or self.peek() == "_":
                    buf += self.advance()
                if buf in LUAU_KEYWORDS:
                    tokens.append(Token("KEYWORD", buf, start_line, start_col))
                else:
                    tokens.append(Token("IDENT", buf, start_line, start_col))
                continue

            # 8. Compound Operators (+=, -=, *=, /=, //=, %=, ^=, ..=)
            three_ch = self.peek() + self.peek(1) + self.peek(2)
            if three_ch in ("..=", "//="):
                self.advance()
                self.advance()
                self.advance()
                tokens.append(Token("OP", three_ch, start_line, start_col))
                continue

            two_ch = self.peek() + self.peek(1)
            if two_ch in COMPOUND_OPS or two_ch in MULTI_CHAR_OPS:
                self.advance()
                self.advance()
                tokens.append(Token("OP", two_ch, start_line, start_col))
                continue

            # 9. Single Character Operators & Symbols
            if ch in SINGLE_CHAR_OPS:
                buf = self.advance()
                tokens.append(Token("OP", buf, start_line, start_col))
                continue

            # Fallback
            tokens.append(Token("SYMBOL", self.advance(), start_line, start_col))

        return tokens
