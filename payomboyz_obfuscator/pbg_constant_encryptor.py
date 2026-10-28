"""
PayomboyZ Obfuscator - Constant Pool & Bytecode Buffer Encryptor
Implements Luraph-style dynamic in-memory buffer encryption:
- Serializes strings, numbers, booleans, and prototypes into encrypted byte streams
- Multi-byte polymorphic rolling XOR cipher
- Generates inline Luau buffer unpacking routines
"""

import struct
import random
from typing import List, Any, Tuple

class ConstantEncryptor:
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed or 0x5041594F) # 'PAYO'

    def generate_key(self, length: int = 16) -> List[int]:
        return [self.rng.randint(1, 255) for _ in range(length)]

    def encrypt_bytes(self, data: bytes, key: List[int]) -> bytes:
        klen = len(key)
        out = bytearray(len(data))
        for i in range(len(data)):
            out[i] = (data[i] ^ key[i % klen] ^ ((i * 37) & 0xFF)) & 0xFF
        return bytes(out)

    def serialize_constants(self, constants: List[Any]) -> Tuple[bytes, List[int]]:
        """
        Packs constants into binary stream:
        [TypeTag: 1 byte]
          Type 1: String  -> [Len: 4 bytes][UTF-8 bytes]
          Type 2: Number  -> [Double: 8 bytes]
          Type 3: Boolean -> [Val: 1 byte]
          Type 4: Nil     -> []
        """
        buf = bytearray()
        for c in constants:
            if isinstance(c, str):
                s_bytes = c.encode('utf-8')
                buf.append(1)
                buf.extend(struct.pack("<I", len(s_bytes)))
                buf.extend(s_bytes)
            elif isinstance(c, (int, float)):
                buf.append(2)
                buf.extend(struct.pack("<d", float(c)))
            elif isinstance(c, bool):
                buf.append(3)
                buf.append(1 if c else 0)
            elif c is None:
                buf.append(4)
            else:
                s_bytes = str(c).encode('utf-8')
                buf.append(1)
                buf.extend(struct.pack("<I", len(s_bytes)))
                buf.extend(s_bytes)

        key = self.generate_key(16)
        encrypted_blob = self.encrypt_bytes(bytes(buf), key)
        return encrypted_blob, key

    def emit_buffer_unpacker(self, encrypted_blob: bytes, key: List[int], table_name: str = "_PBZ_CONST") -> str:
        """
        Emits clean, high-performance Luau buffer unpacker code.
        """
        hex_bytes = "".join(f"\\x{b:02x}" for b in encrypted_blob)
        key_table = "{" + ", ".join(str(k) for k in key) + "}"
        
        return f"""local {table_name} = {{}}
do
    local _k = {key_table}
    local _klen = #{key_table}
    local _raw = "{hex_bytes}"
    local _b = buffer.fromstring(_raw)
    local _sz = buffer.len(_b)
    local _dec = buffer.create(_sz)
    for _i = 0, _sz - 1 do
        local _byte = buffer.readu8(_b, _i)
        local _key_b = _k[(_i % _klen) + 1]
        local _unmasked = bit32.bxor(bit32.bxor(_byte, _key_b), bit32.band(_i * 37, 255))
        buffer.writeu8(_dec, _i, _unmasked)
    end
    local _offset = 0
    local _idx = 0
    while _offset < _sz do
        local _t = buffer.readu8(_dec, _offset)
        _offset = _offset + 1
        if _t == 1 then
            local _len = buffer.readu32(_dec, _offset)
            _offset = _offset + 4
            local _str = buffer.readstring(_dec, _offset, _len)
            _offset = _offset + _len
            {table_name}[_idx] = _str
        elseif _t == 2 then
            local _num = buffer.readf64(_dec, _offset)
            _offset = _offset + 8
            {table_name}[_idx] = _num
        elseif _t == 3 then
            local _bval = buffer.readu8(_dec, _offset)
            _offset = _offset + 1
            {table_name}[_idx] = (_bval == 1)
        elseif _t == 4 then
            {table_name}[_idx] = nil
        end
        _idx = _idx + 1
    end
end
"""
