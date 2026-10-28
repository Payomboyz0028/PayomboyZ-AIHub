# -*- coding: utf-8 -*-
"""
=============================================================================
🌪️ PAYOMBØYZ DUKE HUB / CYCLIC XOR UNPACKER & DEOBFUSCATOR
100% Automated Reverse Engineering for Duke Hub / AnimeDiceHub Protections
=============================================================================
"""

import re
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

class DukeHubUnpacker:
    def __init__(self):
        pass

    @staticmethod
    def is_duke_hub(content: str) -> bool:
        if "DUKE HUB" in content or "Anime Dice Hub" in content or "AnimeDiceHub" in content:
            return True
        if 'local p = "' in content and re.search(r'local\s+k\s*=\s*\{[0-9,\s]+\}', content):
            return True
        return False

    @staticmethod
    def unpack(content: str, fallback_key: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Unpacks Duke Hub protected script.
        Returns:
            dict with 'success', 'source_code', 'diagnostics', 'key', 'payload_len'
        """
        # 1. Check for payload 'p'
        p_match = re.search(r'local\s+p\s*=\s*"([^"]+)"', content)
        truncated = False
        payload_str = ""
        
        if p_match:
            payload_str = p_match.group(1)
        else:
            # Check for unterminated string literal
            p_open = re.search(r'local\s+p\s*=\s*"([^"\r\n]+)', content)
            if p_open:
                payload_str = p_open.group(1)
                truncated = True
            else:
                return {"success": False, "error": "No payload 'local p' found in script"}

        # 2. Check for key array 'k'
        k_match = re.search(r'local\s+k\s*=\s*\{([0-9,\s]+)\}', content)
        key: List[int] = []
        if k_match:
            key = [int(x.strip()) for x in k_match.group(1).split(",") if x.strip().isdigit()]
        elif fallback_key:
            key = fallback_key

        # 3. Base64 decode
        pad = len(payload_str) % 4
        padded = payload_str + ("=" * (4 - pad) if pad else "")
        try:
            raw_bytes = base64.b64decode(padded)
        except Exception as e:
            return {
                "success": False,
                "error": f"Base64 decoding failed: {e}",
                "truncated": truncated
            }

        # 4. If key is missing, attempt known plaintext derivation
        if not key:
            # Known plaintexts for Duke Hub entry points
            candidates = [
                b"-- Anime Dice Hub",
                b"-- DUKE HUB",
                b"-- AnimeDiceHub",
                b"--",
            ]
            # Try to see if previous known build key (e.g. 48-byte key from obf03-11) matches
            # Known key from 2026-10-01 build:
            known_key_11 = [162,103,17,38,238,194,156,134,133,184,238,188,23,249,198,31,104,45,6,124,132,75,242,3,151,173,176,151,190,182,37,15,28,170,152,35,2,81,146,62,180,203,10,232,131,146,194,90]
            test_dec = bytes([raw_bytes[i] ^ known_key_11[i % len(known_key_11)] for i in range(min(len(raw_bytes), 64))])
            if b"Anime Dice Hub" in test_dec or b"DUKE HUB" in test_dec or b"local " in test_dec or b"--" in test_dec[:4]:
                key = known_key_11
            else:
                return {
                    "success": False,
                    "error": "Key array 'local k' is missing from file and could not be auto-derived.",
                    "truncated": truncated,
                    "payload_len": len(raw_bytes),
                    "diagnostic": "File was truncated before the 'local k = {...}' block. Copy full script from source."
                }

        # 5. XOR Decrypt
        kl = len(key)
        decrypted = bytearray(len(raw_bytes))
        for o in range(len(raw_bytes)):
            decrypted[o] = raw_bytes[o] ^ key[o % kl]

        # 6. Decode as string / text
        try:
            source_code = decrypted.decode("utf-8")
        except UnicodeDecodeError:
            source_code = decrypted.decode("latin-1", errors="ignore")

        return {
            "success": True,
            "source_code": source_code,
            "key": key,
            "key_len": kl,
            "payload_len": len(raw_bytes),
            "lines": len(source_code.splitlines()),
            "truncated": truncated
        }

if __name__ == "__main__":
    import sys
    test_path = Path(r"c:\Users\PayomboyZ\Desktop\Games\Deobfuscate\Lerning\obf03-11.lua")
    if test_path.is_file():
        unpacker = DukeHubUnpacker()
        res = unpacker.unpack(test_path.read_text(encoding="utf-8", errors="ignore"))
        print(f"Test on obf03-11.lua: success={res['success']}, lines={res.get('lines')}, key_len={res.get('key_len')}")
