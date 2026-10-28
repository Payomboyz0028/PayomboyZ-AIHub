# -*- coding: utf-8 -*-
"""
=============================================================================
  🔬 PAYOMBØYZ LURAPH & VM TOPOLOGY INSPECTOR v3.0 (O.Z.L.S.R PROTOCOL)
=============================================================================
Granular Variable, Token, and AST Structure Inspection:
- Detects Luraph sub-types: v14.x, v15.0, v15.1
- Differentiates CFF loops: Standard switch vs. Boolean-local dispatch trees
- Inspects native Luau buffer primitives & power-of-2 bitwise lookup tables
- Identifies virtual register naming styles (QZ, V, W, Z, l, O)
- Deterministically routes to the optimal deobfuscation engine
=============================================================================
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Optional, Tuple


class LuraphTopologyInspector:
    """
    Deep variable and structural inspector for VM and CFF protected scripts.
    """

    # Top-level Header & Banner Signatures
    LURAPH_BANNER_REGEX = re.compile(r'--\s*(?:This file was protected using Luraph Obfuscator|Decompiled from Luraph|Luraph Obfuscator|Luraph)\s+(v[0-9]+(?:\.[0-9]+)?)', re.IGNORECASE)
    LURAPH_PROTECTION_WRAPPER = re.compile(r'\.Protection\s*=\s*function\(.*?\)\s*.*?setmetatable', re.DOTALL)
    POWER2_TABLE_REGEX = re.compile(r'a\s*=\s*\{\s*\[0\]\s*=\s*1\s*,\s*2\s*,\s*4\s*,\s*8\s*,\s*16')
    BUFFER_PRIMITIVES_REGEX = re.compile(r'buffer\.(readu8|writeu8|tostring|create|len)')
    BIT32_PRIMITIVES_REGEX = re.compile(r'bit32\.(band|bnot|bxor|lshift|rshift)')

    # Encrypted Buffer Chunk Signatures
    CHUNK_Z_REGEX = re.compile(r'z\s*=\s*\[=\[\s*LPH\?')
    CHUNK_X_REGEX = re.compile(r'x\s*=\s*\[==\[\s*LPH\!')
    GENERIC_LPH_CHUNK = re.compile(r'LPH[?!%&]')

    # Dispatcher Loop & CFF Signatures
    REPEAT_UNTIL_FALSE = re.compile(r'repeat\s+(?:(?!--).)*?until\s+false', re.DOTALL)
    WHILE_TRUE_LOOP = re.compile(r'while\s+true\s+do', re.IGNORECASE)
    
    # Opcode Fetch & Dispatch Patterns
    OP_FETCH_GROUPED = re.compile(r'local\s+([a-zA-Z0-9_]+)\s*=\s*\(\s*([a-zA-Z0-9_]+)\s*\[\s*([a-zA-Z0-9_]+)\s*\]\s*\)')
    OP_FETCH_DIRECT = re.compile(r'local\s+([a-zA-Z0-9_]+)\s*=\s*([a-zA-Z0-9_]+)\s*\[\s*([a-zA-Z0-9_]+)\s*\]')
    
    # Luraph v15.1 Boolean-Local Dispatch Tree:
    # local op = ARR[PC]; local b = op <cmp> K; if b then
    BOOL_LOCAL_DISPATCH = re.compile(
        r'local\s+([a-zA-Z0-9_]+)\s*=\s*([a-zA-Z0-9_]+)\s*\[\s*([a-zA-Z0-9_]+)\s*\]\s*;?\s*'
        r'local\s+([a-zA-Z0-9_]+)\s*=\s*\1\s*(?:<|>|<=|>=|==|~=)\s*([0-9]+)\s*;?\s*'
        r'if\s+\4\s+then',
        re.DOTALL
    )

    # Generic CFF State Machine:
    # while ... do if state == 1 then ... state = 2 elseif state == 2 then ...
    CFF_STATE_MACHINE = re.compile(r'(?:if|elseif)\s+([a-zA-Z0-9_]+)\s*==\s*([0-9]+|\"[^\"]+\")\s+then\s*.*?\1\s*=\s*([0-9]+|\"[^\"]+\")', re.DOTALL)

    # Virtual Registers & Anti-Tamper
    QZ_REGISTERS = re.compile(r'QZ\s*\[')
    LPH_PREFIX = re.compile(r'LPH_[a-zA-Z0-9_]+')
    ANTI_TAMPER_DECOY = re.compile(r'(?:ChildAdded|DescendantAdded|AttributeChanged):Connect\s*\(.*?Disconnect\(\)', re.DOTALL)
    FOLDER_PROBE = re.compile(r'Instance\.new\("Folder"\)')

    @classmethod
    def inspect(cls, code: str) -> Dict[str, Any]:
        """
        Deeply inspects script code and returns comprehensive topology classification,
        confidence, detected features, and recommended deobfuscator engine.
        """
        if not code or not code.strip():
            return {
                "target_type": "unknown",
                "version": "unknown",
                "confidence": 0.0,
                "recommended_engine": "none",
                "features": {},
                "explanation": "Target script is empty"
            }

        prefix = code[:30000]
        code_len = len(code)

        # 1. Inspect Explicit Banners
        banner_match = cls.LURAPH_BANNER_REGEX.search(prefix)
        explicit_version = banner_match.group(1).lower() if banner_match else None

        # 2. Inspect Memory Buffers & Header Primitives
        has_power2_table = bool(cls.POWER2_TABLE_REGEX.search(prefix))
        has_buffer_ops = bool(cls.BUFFER_PRIMITIVES_REGEX.search(prefix))
        has_bit32_ops = bool(cls.BIT32_PRIMITIVES_REGEX.search(prefix))
        has_chunk_z = bool(cls.CHUNK_Z_REGEX.search(prefix) or cls.CHUNK_Z_REGEX.search(code[-30000:]))
        has_chunk_x = bool(cls.CHUNK_X_REGEX.search(prefix) or cls.CHUNK_X_REGEX.search(code[-30000:]))
        has_lph_chunk = bool(cls.GENERIC_LPH_CHUNK.search(prefix))

        # 3. Inspect Dispatcher & Control Flow
        has_repeat_loop = bool(cls.REPEAT_UNTIL_FALSE.search(prefix))
        has_while_true = bool(cls.WHILE_TRUE_LOOP.search(prefix))
        has_bool_local = bool(cls.BOOL_LOCAL_DISPATCH.search(code))
        has_grouped_op = bool(cls.OP_FETCH_GROUPED.search(code))
        has_direct_op = bool(cls.OP_FETCH_DIRECT.search(code))
        has_cff_switch = bool(cls.CFF_STATE_MACHINE.search(code))

        # 4. Inspect Virtual Registers & Defensive Traps
        has_qz_regs = bool(cls.QZ_REGISTERS.search(prefix))
        has_lph_prefix = bool(cls.LPH_PREFIX.search(prefix))
        has_anti_tamper = bool(cls.ANTI_TAMPER_DECOY.search(prefix) or cls.FOLDER_PROBE.search(prefix))
        has_protection_wrapper = bool(cls.LURAPH_PROTECTION_WRAPPER.search(prefix))

        # Compile Features Dictionary
        features = {
            "explicit_version": explicit_version,
            "has_power2_table": has_power2_table,
            "has_buffer_ops": has_buffer_ops,
            "has_bit32_ops": has_bit32_ops,
            "has_chunk_z": has_chunk_z,
            "has_chunk_x": has_chunk_x,
            "has_lph_chunk": has_lph_chunk,
            "has_bool_local_dispatch": has_bool_local,
            "has_repeat_loop": has_repeat_loop,
            "has_while_true": has_while_true,
            "has_grouped_op": has_grouped_op,
            "has_direct_op": has_direct_op,
            "has_cff_switch": has_cff_switch,
            "has_qz_registers": has_qz_regs,
            "has_lph_prefix": has_lph_prefix,
            "has_anti_tamper_traps": has_anti_tamper,
            "has_protection_wrapper": has_protection_wrapper,
            "code_size_bytes": code_len
        }

        # Classification Logic
        # Case A: Luraph v15.1
        if (explicit_version == "v15.1" or 
            (has_power2_table and has_buffer_ops and (has_chunk_z or has_chunk_x)) or
            (has_power2_table and has_bool_local)):
            return {
                "target_type": "luraph_v15_1",
                "version": "v15.1",
                "confidence": 0.99 if (has_buffer_ops and has_chunk_z) else 0.92,
                "recommended_engine": "node_v15_sccp",
                "features": features,
                "explanation": (
                    "Luraph v15.1 detected via power-of-2 table, native Luau buffer primitives, "
                    "multiline encrypted chunks (z/x), and boolean-local dispatch trees. "
                    "Routed to Node AST Dominator + Python SCCP REPL devirtualizer."
                )
            }

        # Case B: Luraph v15.0
        if (explicit_version == "v15.0" or 
            (has_power2_table and (has_chunk_z or has_chunk_x or has_lph_chunk)) or
            (has_power2_table and has_bit32_ops and has_while_true)):
            return {
                "target_type": "luraph_v15_0",
                "version": "v15.0",
                "confidence": 0.95,
                "recommended_engine": "node_v15_sccp",
                "features": features,
                "explanation": (
                    "Luraph v15.0 detected via powers-of-2 table and encrypted LPH chunk buffer. "
                    "Routed to Node AST Dominator + Python SCCP REPL devirtualizer."
                )
            }

        # Case C: Luraph v14.x
        if (explicit_version and explicit_version.startswith("v14")) or has_qz_regs or (has_lph_prefix and has_repeat_loop) or has_grouped_op or has_protection_wrapper:
            return {
                "target_type": "luraph_v14",
                "version": explicit_version or "v14.x",
                "confidence": 0.94 if (has_qz_regs or explicit_version) else 0.88,
                "recommended_engine": "ast_sharded_lifter",
                "features": features,
                "explanation": (
                    "Luraph v14.x detected via QZ registers, protection closure wrappers, "
                    "repeat..until false loop, or explicit v14 banner. "
                    "Routed to AST Sharded Lifter + DeepSeek R1."
                )
            }

        # Case D: Generic CFF (Control Flow Flattening)
        if has_cff_switch and not (has_power2_table or has_lph_chunk):
            return {
                "target_type": "cff_generic",
                "version": "generic_cff",
                "confidence": 0.90,
                "recommended_engine": "cff_deflattener",
                "features": features,
                "explanation": (
                    "Generic state machine control flow flattening detected. "
                    "Routed to CFG Linearization & State Unwinding engine."
                )
            }

        # Case E: Other VMs (MoonSec, IronBrew)
        if "moonsec" in code[:5000].casefold() or "stk" in prefix.casefold() and has_while_true:
            return {
                "target_type": "moonsec_vm",
                "version": "moonsec",
                "confidence": 0.89,
                "recommended_engine": "moonsec_devirt",
                "features": features,
                "explanation": "MoonSec bytecode/virtual stack structure detected."
            }

        # Case F: Simple or Unknown
        if any(w in prefix for w in ["bit.bxor", "string.char", "string.byte"]) and code_len > 2000:
            return {
                "target_type": "simple_obf",
                "version": "unknown",
                "confidence": 0.70,
                "recommended_engine": "ast_sharded_lifter",
                "features": features,
                "explanation": "General obfuscated structure without clear VM interpreter."
            }

        return {
            "target_type": "plain_or_custom",
            "version": "unknown",
            "confidence": 0.50,
            "recommended_engine": "ast_engine",
            "features": features,
            "explanation": "Standard Luau/Lua code with no distinct VM markers."
        }


# Singleton export
TOPOLOGY_INSPECTOR = LuraphTopologyInspector()
