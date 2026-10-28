"""
PayomboyZ Polymorphic Architecture Engine (PBG-Polymorphic)
Randomly selects and synthesizes the underlying obfuscation base per build:
- Base 1: LURAPH_BUFFER_VM (Luau native buffer API, bit32 rolling cipher, 7-Shield Armor)
- Base 2: MOONVEIL_DISPATCHER (CFF State Array Dispatcher, String-Split Table, Opaque Jumps)
- Base 3: HYBRID_POLYMORPHIC (Multi-stage Decoy Paths, Algebraic Invariants, Metatable Lock)
"""

import random
import string
import struct
from typing import List, Dict, Any, Tuple

class PolymorphicEngine:
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed or random.randint(1, 0xFFFFFFFF))
        self.base_architectures = ["LURAPH_BUFFER_VM", "MOONVEIL_DISPATCHER", "HYBRID_POLYMORPHIC"]
        self.selected_arch = self.rng.choice(self.base_architectures)

    def generate_var_name(self, prefix: str = "_0x") -> str:
        suffix = "".join(self.rng.choice("0123456789abcdef") for _ in range(self.rng.randint(6, 10)))
        return f"{prefix}{suffix}"

    def generate_opaque_predicate(self) -> Tuple[str, bool]:
        """
        Generates algebraic & bitwise invariants:
        - ((r * (r + 1)) % 2 == 0) -> ALWAYS TRUE (Product of consecutive integers is always even)
        - (bit32.bxor(r, r) == 0) -> ALWAYS TRUE
        - (bit32.band(r, 0) == 0) -> ALWAYS TRUE
        - (bit32.bor(r, 0) == r) -> ALWAYS TRUE
        """
        r = self.rng.randint(100, 99999)
        variants = [
            (f"((({r} * ({r} + 1)) % 2) == 0)", True),
            (f"(bit32.bxor({r}, {r}) == 0)", True),
            (f"(bit32.band({r}, 0) == 0)", True),
            (f"(bit32.bor({r}, 0) == {r})", True),
            (f"((({r} * 2) % 2) == 1)", False),
            (f"(bit32.bxor({r}, {r}) ~= 0)", False),
        ]
        return self.rng.choice(variants)

    def encrypt_strings(self, strings: List[str]) -> Tuple[str, str]:
        """
        Generates polymorphic decryption code based on selected architecture.
        """
        var_tbl = self.generate_var_name("_PBZ_STR_")
        var_fn = self.generate_var_name("_PBZ_GET_")

        if self.selected_arch == "LURAPH_BUFFER_VM":
            # Luau 5.1+ Native Buffer cipher with rolling XOR
            key = [self.rng.randint(1, 255) for _ in range(16)]
            key_len = len(key)
            
            # Serialize strings into binary buffer
            raw_buf = bytearray()
            offsets = []
            for s in strings:
                s_bytes = s.encode("utf-8")
                offsets.append((len(raw_buf), len(s_bytes)))
                raw_buf.extend(s_bytes)

            # Encrypt buffer bytes
            enc_buf = bytearray(len(raw_buf))
            for i in range(len(raw_buf)):
                enc_buf[i] = (raw_buf[i] ^ key[i % key_len] ^ ((i * 31) & 0xFF)) & 0xFF

            hex_escaped = "".join(f"\\x{b:02x}" for b in enc_buf)
            key_table = "{" + ", ".join(str(k) for k in key) + "}"
            offsets_code = "{" + ", ".join(f"[{i}] = {{{off}, {length}}}" for i, (off, length) in enumerate(offsets)) + "}"

            decrypter_code = f"""-- [[ ARCHITECTURE: LURAPH_BUFFER_VM (Zero-Allocation Buffer Cipher) ]]
local bit32 = bit32 or {{
    bxor = function(a, b)
        local r, m = 0, 1
        while a > 0 or b > 0 do
            local ra, rb = a % 2, b % 2
            if ra ~= rb then r = r + m end
            a, b, m = math.floor(a / 2), math.floor(b / 2), m * 2
        end
        return r
    end,
    band = function(a, b)
        local r, m = 0, 1
        while a > 0 and b > 0 do
            local ra, rb = a % 2, b % 2
            if ra == 1 and rb == 1 then r = r + m end
            a, b, m = math.floor(a / 2), math.floor(b / 2), m * 2
        end
        return r
    end
}}
local {var_tbl} = {{}}
local {var_fn}
do
    local _k = {key_table}
    local _klen = #{key_table}
    local _raw = "{hex_escaped}"
    local _offs = {offsets_code}
    if buffer and buffer.fromstring then
        local _b = buffer.fromstring(_raw)
        local _sz = buffer.len(_b)
        local _dec = buffer.create(_sz)
        for _i = 0, _sz - 1 do
            local _byte = buffer.readu8(_b, _i)
            local _kb = _k[(_i % _klen) + 1]
            local _unmasked = bit32.bxor(bit32.bxor(_byte, _kb), bit32.band(_i * 31, 255))
            buffer.writeu8(_dec, _i, _unmasked)
        end
        {var_fn} = function(_id)
            local _cached = {var_tbl}[_id]
            if _cached then return _cached end
            local _info = _offs[_id]
            if not _info then return "" end
            local _val = buffer.readstring(_dec, _info[1], _info[2])
            {var_tbl}[_id] = _val
            return _val
        end
    else
        -- Native Lua 5.1/LuaJIT String Fallback
        local _sz = #_raw
        local _dec_chars = {{}}
        for _i = 1, _sz do
            local _byte = string.byte(_raw, _i)
            local _kb = _k[((_i - 1) % _klen) + 1]
            local _unmasked = bit32.bxor(bit32.bxor(_byte, _kb), bit32.band((_i - 1) * 31, 255))
            _dec_chars[_i] = string.char(_unmasked)
        end
        local _full_str = table.concat(_dec_chars)
        {var_fn} = function(_id)
            local _cached = {var_tbl}[_id]
            if _cached then return _cached end
            local _info = _offs[_id]
            if not _info then return "" end
            local _val = string.sub(_full_str, _info[1] + 1, _info[1] + _info[2])
            {var_tbl}[_id] = _val
            return _val
        end
    end
end"""
            return decrypter_code, var_fn

        elif self.selected_arch == "MOONVEIL_DISPATCHER":
            # MoonVeil-style Array Dispatcher with Split-Character transpositions (UTF-8 Safe)
            key = self.rng.randint(11, 240)
            encrypted_items = []
            for s in strings:
                chars = []
                s_bytes = s.encode("utf-8")
                for idx, b in enumerate(s_bytes):
                    masked = (b ^ key ^ ((idx * 17) & 0xFF)) & 0xFF
                    chars.append(f"\\{masked:03d}")
                encrypted_items.append("".join(chars))

            table_entries = ",\n        ".join(f"[{i}] = \"{item}\"" for i, item in enumerate(encrypted_items))
            decrypter_code = f"""-- [[ ARCHITECTURE: MOONVEIL_DISPATCHER (State Array Splitting) ]]
local bit32 = bit32 or {{
    bxor = function(a, b)
        local r, m = 0, 1
        while a > 0 or b > 0 do
            local ra, rb = a % 2, b % 2
            if ra ~= rb then r = r + m end
            a, b, m = math.floor(a / 2), math.floor(b / 2), m * 2
        end
        return r
    end,
    band = function(a, b)
        local r, m = 0, 1
        while a > 0 and b > 0 do
            local ra, rb = a % 2, b % 2
            if ra == 1 and rb == 1 then r = r + m end
            a, b, m = math.floor(a / 2), math.floor(b / 2), m * 2
        end
        return r
    end
}}
local _tbl_create = table.create or function(sz) return {{}} end
local {var_tbl} = {{}}
local {var_fn}
do
    local _key = {key}
    local _pool = {{
        {table_entries}
    }}
    {var_fn} = function(_id)
        local _cached = {var_tbl}[_id]
        if _cached then return _cached end
        local _raw = _pool[_id]
        if not _raw then return "" end
        local _res = _tbl_create(#_raw)
        for _idx = 1, #_raw do
            local _b = string.byte(_raw, _idx)
            local _char = string.char(bit32.bxor(bit32.bxor(_b, _key), bit32.band((_idx - 1) * 17, 255)))
            _res[_idx] = _char
        end
        local _val = table.concat(_res)
        {var_tbl}[_id] = _val
        return _val
    end
end"""
            return decrypter_code, var_fn

        else:
            # HYBRID_POLYMORPHIC: Multi-byte Rolling Cipher with Transposition Table
            key_a = self.rng.randint(20, 200)
            key_b = self.rng.randint(30, 220)
            enc_list = []
            for s in strings:
                byte_list = []
                for idx, c in enumerate(s.encode("utf-8")):
                    m = (c ^ key_a ^ key_b ^ (idx % 7)) & 0xFF
                    byte_list.append(str(m))
                enc_list.append("{" + ",".join(byte_list) + "}")

            table_entries = ",\n        ".join(f"[{i}] = {item}" for i, item in enumerate(enc_list))
            decrypter_code = f"""-- [[ ARCHITECTURE: HYBRID_POLYMORPHIC (Multi-Layer Invariant Cipher) ]]
local bit32 = bit32 or {{
    bxor = function(a, b)
        local r, m = 0, 1
        while a > 0 or b > 0 do
            local ra, rb = a % 2, b % 2
            if ra ~= rb then r = r + m end
            a, b, m = math.floor(a / 2), math.floor(b / 2), m * 2
        end
        return r
    end,
    band = function(a, b)
        local r, m = 0, 1
        while a > 0 and b > 0 do
            local ra, rb = a % 2, b % 2
            if ra == 1 and rb == 1 then r = r + m end
            a, b, m = math.floor(a / 2), math.floor(b / 2), m * 2
        end
        return r
    end
}}
local _tbl_create = table.create or function(sz) return {{}} end
local {var_tbl} = {{}}
local {var_fn}
do
    local _ka = {key_a}
    local _kb = {key_b}
    local _arr = {{
        {table_entries}
    }}
    {var_fn} = function(_id)
        local _c = {var_tbl}[_id]
        if _c then return _c end
        local _data = _arr[_id]
        if not _data then return "" end
        local _sz = #_data
        local _buf = _tbl_create(_sz)
        for _i = 1, _sz do
            local _val = bit32.bxor(bit32.bxor(bit32.bxor(_data[_i], _ka), _kb), (_i - 1) % 7)
            _buf[_i] = string.char(_val)
        end
        local _res = table.concat(_buf)
        {var_tbl}[_id] = _res
        return _res
    end
end"""
            return decrypter_code, var_fn
