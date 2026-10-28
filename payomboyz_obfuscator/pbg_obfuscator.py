"""
PayomboyZ Industrial Luau Obfuscator (PBG-Obf v2.0 Master Pipeline)
Reverse-engineered from Luraph v14.7-v15 and MoonVeil 2.1 architecture:
- 100% Native Luau Execution Speed (Zero GC allocations in loops, 60 FPS lag-free)
- Polymorphic Base Architecture Selector (Randomly chooses between Buffer VM, Dispatcher, and Hybrid)
- Full Luau Syntax Compatibility (Preserves varargs ..., multi-return, closures, upvalues, coroutine yielding)
- Non-linear Control Flow Flattening (CFF) with physical block scrambling
- Algebraic & Bitwise Opaque Invariants defeating static dominator tree analysis
- 7-Shield Enterprise Anti-Tamper & Anti-Debug Client Armor
"""

import os
import re
import time
import random
from typing import Dict, Any, Optional, List

from .pbg_luau_tokenizer import LuauTokenizer, Token
from .pbg_polymorphic_engine import PolymorphicEngine
from .pbg_cfg_flattener import ControlFlowFlattener
from .pbg_security_envelope import SecurityEnvelope

def _safe_unquote_lua_str(raw_val: str) -> str:
    """Safely unquotes Lua string literals without destroying UTF-8 / Thai / Unicode characters."""
    if (raw_val.startswith('"') and raw_val.endswith('"')) or (raw_val.startswith("'") and raw_val.endswith("'")):
        inner = raw_val[1:-1]
        def _dec(m):
            try:
                return chr(int(m.group(1)))
            except Exception:
                return m.group(0)
        def _hex(m):
            try:
                return chr(int(m.group(1), 16))
            except Exception:
                return m.group(0)
        inner = re.sub(r'\\([0-9]{1,3})', _dec, inner)
        inner = re.sub(r'\\x([0-9a-fA-F]{2})', _hex, inner)
        # standard escape sequences
        escapes = {'\\\\': '\\', '\\"': '"', "\\'": "'", '\\n': '\n', '\\r': '\r', '\\t': '\t', '\\a': '\a', '\\b': '\b', '\\v': '\v'}
        for esc, ch in escapes.items():
            inner = inner.replace(esc, ch)
        return inner
    elif raw_val.startswith("[[") and raw_val.endswith("]]"):
        return raw_val[2:-2]
    elif raw_val.startswith("[=") and raw_val.endswith("=]"):
        close_idx = raw_val.find("]")
        return raw_val[close_idx + 1:-close_idx - 1]
    return raw_val


class PayomboyZObfuscator:
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed or random.randint(1, 0xFFFFFFFF)
        self.poly_engine = PolymorphicEngine(self.seed)
        self.flattener = ControlFlowFlattener(self.seed)
        self.security = SecurityEnvelope()

    def obfuscate(self, source_code: str, options: Optional[Dict[str, Any]] = None) -> str:
        options = options or {}
        include_armor = options.get("security_armor", False) # False by default for offline/cross-platform compat, True in Roblox
        enable_cff = options.get("flatten_cfg", True)
        chunk_size = options.get("chunk_size", 2)

        # Step 1: Lex and Tokenize Luau Source
        tokenizer = LuauTokenizer(source_code)
        tokens = tokenizer.tokenize()

        # Step 2: Extract Strings for Polymorphic Encryption
        string_constants: List[str] = []
        string_id_map: Dict[str, int] = {}
        transformed_tokens: List[str] = []

        for tok in tokens:
            if tok.type == "STRING":
                val = _safe_unquote_lua_str(tok.value)
                if val not in string_id_map:
                    string_id_map[val] = len(string_constants)
                    string_constants.append(val)
                s_id = string_id_map[val]
                transformed_tokens.append(f"__PBZ_STR_CALL__({s_id})")
            elif tok.type == "COMMENT":
                # Strip comments for size & clean oneliner
                continue
            else:
                transformed_tokens.append(tok.value)

        code_with_str_refs = "".join(transformed_tokens)

        # Step 3: Polymorphic Encryption of Constant Pool
        decrypter_code, get_fn_name = self.poly_engine.encrypt_strings(string_constants)
        code_with_str_refs = code_with_str_refs.replace("__PBZ_STR_CALL__", get_fn_name)

        # Step 4: Control Flow Flattening (CFF) with Invariants
        if enable_cff:
            flattened_code = self.flattener.flatten(code_with_str_refs, chunk_size=chunk_size)
        else:
            flattened_code = code_with_str_refs

        # Step 5: Security Envelope (7-Shield Anti-Debug / Tamper Armor)
        armor_code = self.security.emit_armor() if include_armor else ""

        # Step 6: Assemble Protected Payload with Scope Isolation (Zero Emojis)
        arch_name = self.poly_engine.selected_arch
        full_payload = f"""return (function(...)
{armor_code}
{decrypter_code}
{flattened_code}
end)(...)
"""
        return full_payload


def obfuscate_script(source_code: str, options: Optional[Dict[str, Any]] = None) -> str:
    obf = PayomboyZObfuscator()
    return obf.obfuscate(source_code, options)
