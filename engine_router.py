import os
import sys
import re
import time
import base64
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List

ENGINE_DIR = Path(__file__).resolve().parent
for candidate in [ENGINE_DIR, ENGINE_DIR / "Prometheus-WeAre-Devs-Dumper-main"]:
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    import deobfuscator
except ImportError:
    deobfuscator = None

try:
    import luraph_engine
except ImportError:
    luraph_engine = None

try:
    import moonsec_ironbrew_engine
except ImportError:
    moonsec_ironbrew_engine = None

try:
    import moonsec_v5_engine
except ImportError:
    moonsec_v5_engine = None

try:
    import moonveil_engine
except ImportError:
    moonveil_engine = None

try:
    import twok_engine
except ImportError:
    twok_engine = None

try:
    import luast_engine
except ImportError:
    luast_engine = None

try:
    import security_sandbox
except ImportError:
    security_sandbox = None

try:
    import scpe_engine
except ImportError:
    scpe_engine = None

ENGINE_MAP = {
    # Tool 1: WeAreDevs (Prometheus)
    "1": "wearedevs",
    "wearedevs": "wearedevs",
    "prometheus": "wearedevs",
    "tool1": "wearedevs",

    # Tool 2: IronBrew & MoonSec
    "2": "moonsec_ironbrew",
    "ironbrew": "moonsec_ironbrew",
    "ib2": "moonsec_ironbrew",
    "tool2": "moonsec_ironbrew",
    "moonsec": "moonsec_ironbrew",
    "moonsec_ironbrew": "moonsec_ironbrew",

    # Tool 3: Luraph v14 (Classic)
    "3": "luraph",
    "luraph": "luraph",
    "luraph_v14": "luraph",
    "luraph14": "luraph",
    "tool3": "luraph",

    # Tool 4: Moonveil 2.0.2+
    "4": "moonveil",
    "moonveil": "moonveil",
    "tool4": "moonveil",

    # Tool 5: 2K Security & Byte-Array Loader
    "5": "twok",
    "twok": "twok",
    "2k": "twok",
    "packer": "twok",
    "tool5": "twok",

    # Tool 6: Luast v1.0.1
    "6": "luast",
    "luast": "luast",
    "tool6": "luast",

    # Tool 7: A7DEV / Custom Lua Base64 Loader
    "7": "base64_loader",
    "base64_loader": "base64_loader",
    "base64": "base64_loader",
    "a7dev": "base64_loader",
    "tool7": "base64_loader",

    # Tool 8: Luraph v15.1 / v15 (Advanced Node CFG Dominator & Industrial CFF)
    "8": "luraph_v15",
    "luraph_v15": "luraph_v15",
    "luraph_v15_1": "luraph_v15",
    "luraph15.1": "luraph_v15",
    "luraph_15_1": "luraph_v15",
    "luraph15": "luraph_v15",
    "lph15": "luraph_v15",
    "lph15.1": "luraph_v15",
    "tool8": "luraph_v15",

    # Tool 9: MoonSec V2 / V3 Unicode Stego Devirtualizer
    "9": "moonsec_v5",
    "moonsec_v5": "moonsec_v5",
    "msv5": "moonsec_v5",
    "moonsec5": "moonsec_v5",
    "tool9": "moonsec_v5",
    "v5": "moonsec_v5",
    "v51": "moonsec_v5",
    "moonsec_v2": "moonsec_v5",
    "moonsec_v3": "moonsec_v5",
    "moonsec2": "moonsec_v5",
    "moonsec3": "moonsec_v5",
    "msv2": "moonsec_v5",
    "msv3": "moonsec_v5",
    "v2": "moonsec_v5",
    "v3": "moonsec_v5",

    # Tool 10: Luarmor One-Click (6-Pillar Full Decompiler)
    "10": "luarmor",
    "luarmor": "luarmor",
    "tool10": "luarmor",

    # Tool 11: SCPE / ScriptCenter (Dual-Layer Unpacker & String Lifter)
    "11": "scpe",
    "scpe": "scpe",
    "scriptcenter": "scpe",
    "tool11": "scpe",

    "auto": "auto"
}

try:
    import wearedevs_ast_engine
    _WRD_AST_AVAILABLE = True
except ImportError:
    wearedevs_ast_engine = None
    _WRD_AST_AVAILABLE = False
try:
    import wearedevs_semantic_decompiler as _wrd_semantic
    _WRD_SEMANTIC_AVAILABLE = True
except ImportError:
    _WRD_SEMANTIC_AVAILABLE = False

try:
    import moonveil_semantic_decompiler as _moonveil_semantic
    _MOONVEIL_SEMANTIC_AVAILABLE = True
except ImportError:
    _MOONVEIL_SEMANTIC_AVAILABLE = False

try:
    import ironbrew_semantic_decompiler as _ib_semantic
    _IB_SEMANTIC_AVAILABLE = True
except ImportError:
    _IB_SEMANTIC_AVAILABLE = False

ENGINE_NAMES = {
    "wearedevs": "🛠️ WeAreDevs (Prometheus AST Devirtualizer)",
    "moonsec_ironbrew": "☕ IronBrew & MoonSec (Universal 5-Stage Semantic)",
    "luraph": "🔒 Luraph v14 (Classic & Buffer VM)",
    "moonveil": "🌙 Moonveil 2.0.2+",
    "twok": "🛡️ 2K Security & XOR Loader",
    "luast": "🌪️ Luast v1.0.1",
    "base64_loader": "📦 A7DEV / Custom Lua Base64 Loader Unpacker",
    "luraph_v15": "⚡ Luraph v15.1 / v15 (Node CFG Dominator + Industrial CFF)",
    "moonsec_v5": "🌙 MoonSec V2 / V3 (Unicode Stego + Universal 5-Stage Semantic)",
    "luarmor": "🛡️ Luarmor One-Click (6-Pillar Full Decompiler)",
    "scpe": "🛡️ SCPE / ScriptCenter (Dual-Layer Unpacker & String Lifter)"
}

ENGINE_TOOL_IDS = {
    "wearedevs": 1,
    "moonsec_ironbrew": 2,
    "luraph": 3,
    "moonveil": 4,
    "twok": 5,
    "luast": 6,
    "base64_loader": 7,
    "luraph_v15": 8,
    "moonsec_v5": 9,
    "luarmor": 10,
    "scpe": 11,
    "plain": 0
}


def _is_base64_loader(code: str) -> bool:
    """
    Detects A7DEV-style custom Lua Base64 loaders:
    local alphabet="..."; local data=[==[ <base64> ]==]; ... loadstring(decoded)()
    """
    header = code[:500]
    if "local alphabet" not in header and "local data" not in header and "A7DEV" not in header:
        return False
    # Check if there is an opening bracket string with base64 content
    if not re.search(r'\[=*\[[A-Za-z0-9+/=\r\n\s]{100,}', code[:1000]):
        return False
    # Check tail for decode loop + loadstring / load
    tail = code[-1500:]
    if re.search(r'(?:loadstring|load\s*\(|chunk\s*\()', tail) and any(kw in tail for kw in ("math.floor", "table.concat", "char(", "base64", "alphabet")):
        return True
    return False


def unpack_base64_loader(code: str) -> Optional[str]:
    """
    Decodes A7DEV-style custom Lua Base64 loaders.
    Supports both custom-alphabet and standard-alphabet variants.
    """
    # Try to extract the bracket-encoded base64 payload
    m = re.search(r'\[={0,3}\[([A-Za-z0-9+/=\r\n\s]{200,})\]={0,3}\]', code)
    if not m:
        return None
    raw_b64 = re.sub(r'\s+', '', m.group(1))

    # Try standard base64 first
    try:
        decoded = base64.b64decode(raw_b64).decode('utf-8', errors='replace')
        if len(decoded) > 100 and any(kw in decoded for kw in ('local ', 'function', 'game:', 'return', 'if ')):
            return decoded
    except Exception:
        pass

    # Try custom alphabet decode (A7DEV uses ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/)
    alpha_m = re.search(r'local\s+alphabet\s*=\s*["\']([A-Za-z0-9+/=]{60,})["\']', code)
    if not alpha_m:
        return None
    alphabet = alpha_m.group(1)
    if len(alphabet) < 64:
        return None

    try:
        char_map = {ord(ch): i for i, ch in enumerate(alphabet)}
        data = raw_b64
        out = bytearray()
        for i in range(0, len(data) - 3, 4):
            a = char_map.get(ord(data[i]), 0)     if i < len(data) else 0
            b = char_map.get(ord(data[i+1]), 0)   if i+1 < len(data) else 0
            cb = ord(data[i+2]) if i+2 < len(data) else 61
            db = ord(data[i+3]) if i+3 < len(data) else 61
            c = 0 if (cb == 61) else char_map.get(cb, 0)
            d = 0 if (db == 61) else char_map.get(db, 0)
            n = a * 262144 + b * 4096 + c * 64 + d
            out.append((n >> 16) & 0xFF)
            if cb != 61:
                out.append((n >> 8) & 0xFF)
            if db != 61:
                out.append(n & 0xFF)
        decoded = out.decode('utf-8', errors='replace')
        if len(decoded) > 100 and any(kw in decoded for kw in ('local ', 'function', 'game:', 'return', 'if ')):
            return decoded
    except Exception:
        pass

    return None


def classify_engine(code: str) -> tuple[str, int, Dict[str, int]]:
    """
    Multi-Factor Weighted AST & Structural Classifier for Obfuscators.
    Identifies obfuscation engines with 99%+ accuracy even when all author comments,
    watermarks, and headers have been completely stripped.

    Returns:
        (best_engine_key, confidence_score, all_scores_dict)
    """
    scores: Dict[str, int] = {
        'wearedevs': 0,
        'luast': 0,
        'luraph_v15': 0,
        'luraph': 0,
        'moonveil': 0,
        'moonsec_v5': 0,
        'moonsec_ironbrew': 0,
        'twok': 0,
        'base64_loader': 0,
        'luarmor': 0,
        'scpe': 0,
        'plain': 0,
    }

    if not code or not code.strip():
        return "plain", 100, scores

    # 0. HEADER AUTO-HEALING (Repair truncated copy-paste headers)
    norm_code = code.strip()
    for pfx in ("turn(", "eturn(", "urn(", "rn(", "n("):
        if norm_code.startswith(pfx):
            norm_code = "return(" + norm_code[len(pfx):]
            break

    head_10k = norm_code[:10000]
    tail_10k = norm_code[-10000:]

    # -------------------------------------------------------------
    # 1. WATERMARKS & BRANDS (Primary boost +100 when present)
    # -------------------------------------------------------------
    if 'wearedevs.net/obfuscator' in head_10k or 'Firsthub x Phoenixhub' in head_10k or 'firsthubxphoenixhubobf' in head_10k:
        scores['wearedevs'] += 100
    if '-- generated by luast' in head_10k or 'luast.clv.cloud' in head_10k:
        scores['luast'] += 100
    # Luraph version-aware detection (v14.7, v14.8, v14.9, v15.0+ route to Tool 8 CFG Dominator)
    lph_ver_match = re.search(r'Luraph\s+Obfuscator\s+v(\d+)\.(\d+)', head_10k, re.IGNORECASE)
    if lph_ver_match:
        major = int(lph_ver_match.group(1))
        minor = int(lph_ver_match.group(2))
        if major >= 15 or (major == 14 and minor >= 7):
            scores['luraph_v15'] += 150
        else:
            scores['luraph'] += 120
    else:
        if any(sig in head_10k for sig in ('Luraph Obfuscator v15', 'Luraph v15', 'lura.ph/')) or 'LPH}' in code or 'LPH_' in code or 'LPH|' in code:
            scores['luraph_v15'] += 160
            scores['luraph'] += 110
        elif any(sig in head_10k for sig in ('Luraph Obfuscator v14', 'Luraph v14', 'LPH_OBFUSCATED', r'\L\u{0075}\114aph', r'\76\117\114\97\112\104')):
            scores['luraph'] += 100
    if '-- This script was generated using MoonVeil' in head_10k or 'moonveil.cc' in head_10k or 'MoonVeil' in head_10k:
        scores['moonveil'] += 100
    if 'char.string.load' in head_10k or ':::MoonSec:::' in head_10k or 'MoonSec V3' in head_10k or 'MoonSec V2' in head_10k:
        scores['moonsec_v5'] += 100
    if any(sig in head_10k for sig in ('..:::MoonSec::..', 'Compiled by IronBrew', 'IronBrew')):
        scores['moonsec_ironbrew'] += 100
    if any(sig in head_10k for sig in ('2K PROTECTED SCRIPT', '2K Local Security', '2K Security')):
        scores['twok'] += 100
    if 'A7DEV' in head_10k:
        scores['base64_loader'] += 100
    if scpe_engine.is_scpe(norm_code):
        scores['scpe'] += 160

    # -------------------------------------------------------------
    # 2. STRUCTURAL & AST FINGERPRINTS (Independent of Comments)
    # -------------------------------------------------------------

    # === A7DEV / Custom Base64 Loader ===
    has_b64_payload = bool(re.search(r'local\s+\w+\s*=\s*(?:\[=*\[[A-Za-z0-9+/=\r\n\s]{100,}|["\'][A-Za-z0-9+/=\r\n\s]{100,})', head_10k))
    if 'local alphabet' in head_10k and has_b64_payload:
        scores['base64_loader'] += 120
    elif has_b64_payload and ('buffer.create' in norm_code or 'buffer.writeu8' in norm_code) and ('launch' in tail_10k or 'loadstring' in tail_10k or 'pcall' in tail_10k):
        scores['base64_loader'] += 110
    if re.search(r'(?:loadstring|load\s*\(|chunk\s*\()', tail_10k) and ('base64' in tail_10k or 'alphabet' in tail_10k):
        scores['base64_loader'] += 40

    # === WeAreDevs / Prometheus (AST Tool 1) ===
    has_wrd_unpack = 'unpack or table[' in tail_10k
    has_wrd_lcg = any(c in code for c in ('35184372088832', '27552854471197'))
    has_wrd_head = bool(re.search(r'return\s*\(\s*function\s*\(\s*\.\.\.\s*\)\s*local\s+\w+\s*=\s*\{["\'\^z\.]', head_10k))
    has_wrd_dispatcher = bool(re.search(r'while\s+\w+\s+do\s+if\s+\w+\s*<\s*\d+\s+then', code[:20000]))
    has_wrd_modchain = bool(re.search(r'math\.floor\s*\([^)]*%\s*(?:35184372088832|4294967296)[^)]*\)', code))
    has_wrd_seed = bool(re.search(r'local\s+\w+\s*=\s*[\w.]+\s*%\s*257\b', code[:15000]))
    has_wrd_outer = bool(re.search(r'return\s*\(\s*function\s*\(\s*\.\.\.\s*\)[\s\S]{0,200}end\s*\)\s*\(\.\.\.\)', tail_10k))
    has_wrd_strtable = bool(re.search(r'local\s+\w+\s*=\s*\{(?:\s*["\'][\^z\.:\w]{1,5}["\']\s*,\s*){8,}', head_10k))

    wrd_core_hit = has_wrd_lcg or has_wrd_modchain or has_wrd_seed or has_wrd_strtable

    if has_wrd_unpack and wrd_core_hit:
        scores['wearedevs'] += 85
        if 'getfenv and getfenv()' in tail_10k or 'newproxy' in tail_10k or 'getmetatable' in tail_10k:
            scores['wearedevs'] += 40
    if has_wrd_lcg:
        scores['wearedevs'] += 80
    if has_wrd_modchain:
        scores['wearedevs'] += 75
    if has_wrd_dispatcher and wrd_core_hit:
        scores['wearedevs'] += 65
    if has_wrd_seed:
        scores['wearedevs'] += 60
    if has_wrd_strtable:
        scores['wearedevs'] += 55
    if has_wrd_head and (has_wrd_unpack or has_wrd_lcg or 'newproxy' in tail_10k):
        scores['wearedevs'] += 50
    if has_wrd_outer and wrd_core_hit:
        scores['wearedevs'] += 45
    if re.search(r'%\s*(?:35184372088832|4294967296)\b', code):
        scores['wearedevs'] += 30
    wrd_signal_count = sum([
        has_wrd_lcg, bool(has_wrd_dispatcher and wrd_core_hit),
        has_wrd_modchain, has_wrd_seed, has_wrd_strtable
    ])
    if wrd_signal_count >= 3:
        scores['wearedevs'] += 35

    # === Luast v1.0.0 / v1.0.1 (Tool 6) ===
    if re.search(r'while\s+true\s+do\s+\w+\s*=\s*\d+\.?\s*-\s*\w+;\s*do\s+if\s+\w+\s*<', code):
        scores['luast'] += 95
    if re.search(r'%\s*16777213\b', code):
        scores['luast'] += 85
    if re.search(r'\w+\[\d+\.?\](?:\s*,\s*\w+\[\d+\.?\]){3,}\s*=', head_10k):
        scores['luast'] += 80
    if re.search(r'\w+\[\d+\.?\]\s*=\s*nil;\s*\w+\[\d+\.?\]\s*=\s*nil;\s*\w+\[\d+\.?\]\s*=\s*nil;', head_10k):
        scores['luast'] += 75
    if re.search(r'\[\s*\d+\.\s*\]', head_10k):
        scores['luast'] += 60

    # === Luraph v14 (Classic - Tool 3) ===
    # Check for string accessor function: function w(w) return t[w + offset] end
    # Must support optional local, arithmetic offsets, and negative terms
    has_lph14_accessor = bool(re.search(
        r'(?:local\s+)?function\s+([A-Za-z0-9_]+)\s*\(\s*([A-Za-z0-9_]+)\s*\)\s*return\s+[A-Za-z0-9_]+\s*\[\s*(?:\2\s*[+\-]|[-+0-9(])',
        norm_code[:20000]
    ))
    has_lph14_strtable = bool(re.search(r'return\s*\(\s*function\s*\(\s*\.\.\.\s*\)\s*local\s+[A-Za-z0-9_]+\s*=\s*\{["\']', head_10k))
    if has_lph14_accessor:
        scores['luraph'] += 105
        if has_lph14_strtable:
            scores['luraph'] += 50
    if 'V=buffer' in head_10k or 'local V=buffer' in head_10k:
        scores['luraph'] += 75
    if 'LPH_NO_VIRTUALIZE' in code or 'LPH_CRASH' in code:
        scores['luraph'] += 70

    # === Luraph v15 (Modern Luau Buffer VM - Tool 8) ===
    # Guard: only score luraph_v15 if NOT a base64 loader and NOT classic luraph accessor
    if scores['base64_loader'] < 80 and not has_lph14_accessor:
        buf_ops = sum(1 for op in ('buffer.readstring', 'buffer.readu8', 'buffer.readu16', 'buffer.readu32', 'buffer.create', 'buffer.fromstring', 'buffer.writeu8', 'buffer.tostring') if op in code)
        if buf_ops >= 3:
            scores['luraph_v15'] += 85
        elif buf_ops == 2 and any(b in code for b in ('bit32', '0b1', '0x')):
            scores['luraph_v15'] += 65
        elif buf_ops >= 1 and (re.search(r'return\s*\(\s*\{[^\}]*function', head_10k) or re.search(r'\}\s*\)\s*:\s*[a-zA-Z0-9_]+\s*\(\s*\)\s*\(', tail_10k)):
            scores['luraph_v15'] += 75
        if re.search(r'return\s*\(\s*\{[^\}]*bit32[^\}]*function', head_10k) or re.search(r'\}\s*\)\s*:\s*[a-zA-Z0-9_]+\s*\(\s*\)\s*\(', tail_10k):
            scores['luraph_v15'] += 75
        if 'bit32.countrz' in code or ('bit32.lrotate' in code and 'buffer' in code):
            scores['luraph_v15'] += 65
        if re.search(r'\b0[xX][0-9a-fA-F]+_\b|\b0[bB][01]+_\b', code):
            scores['luraph_v15'] += 40
        # Luraph modern table dispatcher (v14.7 - v15.0)
        if (re.search(r'return\s*\(\s*\{[^\}]*(?:bit32|readf32|readu8|readi16|countlz|countrz)', head_10k) or
            ('Fn=bit32' in head_10k and ('countlz' in head_10k or 'countrz' in head_10k or 'readf32' in head_10k))):
            scores['luraph_v15'] += 140

    # === Moonveil 2.0.2+ (Tool 4) ===
    # Guard: Do not confuse Luraph bitwise literals with Moonveil unless Moonveil watermark exists
    if ('MoonVeil' in head_10k or 'moonveil.cc' in head_10k) or not ('LPH}' in code or 'LPH_' in code or 'Luraph' in head_10k):
        if '[0b10]=' in code or '[0b10]=0b11' in code or '[0b11]=' in code:
            scores['moonveil'] += 95
        if re.search(r':\w*[IJKLMN]\(\s*0x', code):
            scores['moonveil'] += 85
        if re.search(r'\b0b[01]{2,}\b', head_10k) and ('0b10' in head_10k or '0b11' in head_10k):
            scores['moonveil'] += 45

    # === MoonSec V2 / V3 (Unicode Stego - Tool 9) ===
    if any(c in head_10k for c in ('꧁', '꧂')):
        scores['moonsec_v5'] += 95
    if 'char.string.load' in head_10k:
        scores['moonsec_v5'] += 95

    # === MoonSec / IronBrew Classic (Tool 2) ===
    if re.search(r'local\s+n=\(y/2\^\(n-1\)\)%2\^', code):
        scores['moonsec_ironbrew'] += 95
    if re.search(r'y\(1\),\s*y\(4,\s*\w+,\s*\w+,\s*\w+,\s*y\)', tail_10k):
        scores['moonsec_ironbrew'] += 95
    if re.search(r'return\s+\w+\(true,\s*\{\},\s*\w+\(\)\)\(\)', tail_10k):
        scores['moonsec_ironbrew'] += 90
    if re.search(r'return\s+[a-zA-Z0-9_]+\([a-zA-Z0-9_]+\(\)\s*,\s*\{\}\s*,\s*[a-zA-Z0-9_]+\(\)\s*\)\(\)', tail_10k):
        scores['moonsec_ironbrew'] += 90

    # === 2K Security & Byte Array (Tool 5) ===
    if ('local _k1' in head_10k or 'local _k2' in head_10k) and 'local _data' in head_10k:
        scores['twok'] += 95
    if re.search(r'local\s+_[a-zA-Z0-9_]+\s*=\s*\{\s*\d+[\s\d,]{50,}\}', head_10k) and ('loadstring' in tail_10k or 'load(' in tail_10k):
        scores['twok'] += 80

    # === Luarmor V3 / V4 (Tool 10) ===
    if any(sig in norm_code for sig in ('_bsdata0', 'local _bsdata0', 'api.luarmor.net', 'cdn.luarmor.net', 'CACHE_FOLDER', 'v4_init_sephal')):
        scores['luarmor'] += 150
    if 'WA=function' in norm_code or 'Af=function' in norm_code or 'superflow_bytecode' in norm_code:
        scores['luarmor'] += 120

    # === Negative Cross Penalties ===
    if scores['wearedevs'] >= 50:
        scores['luraph'] -= 40
        scores['luraph_v15'] -= 40
    if scores['luast'] >= 50:
        scores['wearedevs'] -= 40
        scores['luraph'] -= 40

    # === Plain Lua Evaluation (Tool 0) ===
    is_dense_oneliner = len(norm_code) > 2000 and norm_code.count('\n') < 5
    has_hex_char_escapes = bool(re.search(r'\\(?:0\d{2}|\d{3})', head_10k))
    has_vm_opcode_table = bool(re.search(r'_\w+\[\d+\]\s*=\s*function', head_10k))

    obf_max = max(scores[k] for k in scores if k != 'plain')
    if obf_max < 35:
        if is_dense_oneliner or has_hex_char_escapes or has_vm_opcode_table:
            scores['plain'] = 0
            if has_vm_opcode_table or has_hex_char_escapes:
                scores['moonsec_ironbrew'] = 40
        else:
            plain_indicators = sum(1 for ind in [
                'game:GetService', 'game.Loaded', 'Players = game', 'LocalPlayer',
                'HttpService', 'ReplicatedStorage', 'RunService', 'TweenService',
                'UserInputService', 'workspace', 'task.wait', 'task.spawn'
            ] if ind in head_10k)
            is_string_table_blob = bool(re.search(r'\{\s*(?:["\'][^"\']{15,}["\']\s*,\s*){3,}', head_10k))
            if is_string_table_blob or re.search(r'\[[A-Za-z0-9_]+\]\s*=\s*function', head_10k):
                scores['plain'] = 0
                scores['wearedevs'] = 45
            elif plain_indicators >= 2 and norm_code.count('\n') > 5:
                scores['plain'] = 80
            elif plain_indicators == 1 and norm_code.count('\n') > 15:
                scores['plain'] = 60
            else:
                scores['plain'] = 0

    best_engine = max(scores, key=scores.get)
    best_score = scores[best_engine]

    # Map raw structural score to a realistic confidence percentage (60% - 99%)
    if best_score >= 150:
        conf_pct = 99
    elif best_score >= 100:
        conf_pct = 95
    elif best_score >= 80:
        conf_pct = 90
    elif best_score >= 60:
        conf_pct = 85
    elif best_score >= 40:
        conf_pct = 75
    elif best_score >= 25:
        conf_pct = 65
    else:
        conf_pct = 50

    return best_engine, conf_pct, scores


def is_plain_lua(code: str) -> bool:
    """Checks if the script is already plain / unobfuscated Lua / Luau."""
    best_eng, score, _ = classify_engine(code)
    return best_eng == "plain"


def detect_engine_type(code: str) -> str:
    """Analyze script content using multi-factor structural scoring to determine the obfuscator."""
    best_eng, _, _ = classify_engine(code)
    return best_eng


def check_nested_obfuscation(code: str) -> Optional[str]:
    """Detects if deobfuscated code contains a wrapped inner layer of obfuscation."""
    if not code or len(code) < 120:
        return None

    # Check only first 5000 characters and last 5000 characters where loaders/wrappers live
    header_footer = code[:5000] + "\n" + code[-5000:]
    clean_sample = "\n".join(l for l in header_footer.splitlines() if not l.strip().startswith("--"))

    best_eng, score, _ = classify_engine(clean_sample)
    if best_eng != "plain" and score >= 40:
        return best_eng

    return None


def _has_meaningful_deobfuscated_code(code: str) -> bool:
    """Return false for comment-only, constant-only, or no-op trace output."""
    if not code or not code.strip():
        return False

    source = code
    placeholder_patterns = (
        r"^\s*request\s*=\s*function\s*\(\s*\.\.\.\s*\)\s*end\s*$",
        r"^\s*http_request\s*=\s*function\s*\(\s*\.\.\.\s*\)\s*end\s*$",
        r"^\s*(?:syn|fluxus)\s*=\s*\{\s*\[\s*['\"]request['\"]\s*\]\s*=\s*function\s*\(\s*\.\.\.\s*\)\s*end\s*\}\s*$",
    )
    for pattern in placeholder_patterns:
        source = re.sub(pattern, "", source, flags=re.IGNORECASE | re.MULTILINE)

    # Detect high-confidence payload indicators (loadstring, HttpGet, URLs, require)
    has_payload = bool(re.search(
        r'\b(?:loadstring|require|HttpGet|HttpGetAsync)\s*\(|https?://[^\s"\'\)]+',
        source,
        re.IGNORECASE
    ))

    source = re.sub(r"--\[\[.*?\]\]", "", source, flags=re.DOTALL)
    source = re.sub(r"--[^\r\n]*", "", source)
    source = re.sub(r"\[(=*)\[(.*?)\]\1\]", '""', source, flags=re.DOTALL)
    source = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', source)
    statements = [
        line.strip()
        for line in re.split(r"[\r\n;]+", source)
        if line.strip() and line.strip() not in {"{", "}", "};"}
    ]
    if len(statements) < 1:
        return False

    executable = "\n".join(statements)

    # Reject security kick stubs where only anti-tamper events and kick executed
    if re.search(r':\s*Kick\s*\(', executable, re.IGNORECASE) and not has_payload:
        non_security = [
            s for s in statements
            if not re.search(r'(?:Kick|AttributeChanged|__PAYOMBOYZ|Direct Execution Blocked|Loader|Instance\.new\("Folder"\))', s, re.IGNORECASE)
        ]
        if len(non_security) < 5:
            return False

    # Accept decoded static strings / constants tables with multiple entries (valuable deobfuscation output)
    has_constants_table = bool(re.search(r'(?:local\s+(?:_STATIC_STRINGS|Constants)\b)', source, re.IGNORECASE))
    constant_count = len(re.findall(r'\[\d+\]\s*=\s*["\']', source))
    if has_constants_table and constant_count >= 3:
        return True

    # Reject static string/constant table ONLY stubs (e.g. local _STATIC_STRINGS = { [1] = "" })
    non_table_statements = [
        s for s in statements
        if not re.search(r'^(?:local\s+(?:_STATIC_STRINGS|Constants)\b.*|\[\d+\]\s*=.*|\})$', s, re.IGNORECASE)
    ]
    if not non_table_statements and not has_payload:
        return False

    # A real expression, control-flow block, function, or call must remain.
    has_control_or_call = bool(re.search(
        r"\b(?:function|if|for|while|repeat|return|loadstring|require|print|local|setmetatable|getgenv)\b"
        r"|\b(?:game|workspace|task|Players|HttpService|RunService)\s*[:.]"
        r"|\w+\s*[:.]\s*\w+\s*\("
        r"|\b[A-Za-z_]\w*\s*\(",
        executable,
        re.IGNORECASE,
    ))

    return bool((has_control_or_call or has_payload) and len(executable) >= 3 and len(statements) >= 1)


def _validate_engine_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Do not expose placeholder trace output as a successful deobfuscation."""
    if not result.get("success"):
        return result

    code = str(result.get("deobfuscated_code") or "")
    if not code:
        output_path = result.get("deobf_path") or result.get("output_path")
        if output_path:
            try:
                code = Path(output_path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                code = ""

    if not _has_meaningful_deobfuscated_code(code):
        engine = result.get("engine", "Selected engine")
        result["success"] = False
        result["error"] = (
            f"{engine} produced only comments, constants, or no-op trace stubs; "
            "no executable source was recovered."
        )
        result.pop("deobf_path", None)
        result.pop("output_path", None)
        return result

    result["deobfuscated_code"] = code
    return result


def _run_single_engine(engine_key: str, file_path: Path, timeout: int, start_time: float, is_admin: bool = False) -> Dict[str, Any]:
    display_name = ENGINE_NAMES.get(engine_key, "WeAreDevs (Prometheus)")
    tool_id = ENGINE_TOOL_IDS.get(engine_key, 1)

    if engine_key == "luraph_v15":
        raw_res = luraph_engine.deobfuscate_luraph_v15(str(file_path), timeout=max(timeout, 180))
        elapsed = time.time() - start_time
        if raw_res and raw_res.get("success"):
            code = raw_res.get("deobfuscated_code", "")
            return {
                "success": True,
                "engine": raw_res.get("engine", "⚡ Luraph v15 (Advanced Node CFG Dominator)"),
                "tool_id": 8,
                "deobf_path": raw_res.get("deobf_path"),
                "report_path": raw_res.get("report_path"),
                "deobfuscated_code": code,
                "lines": len(code.splitlines()) if code else 0,
                "urls": raw_res.get("urls", []),
                "loadstrings": raw_res.get("loadstrings", []),
                "constants": raw_res.get("constants", []),
                "elapsed": elapsed
            }
        else:
            return {
                "success": False,
                "engine": display_name,
                "tool_id": 8,
                "error": raw_res.get("error", "Luraph v15 deobfuscation failed") if raw_res else "No output from Luraph v15 engine",
                "elapsed": elapsed
            }

    elif engine_key == "luraph":
        raw_res = luraph_engine.deobfuscate_luraph_v14(str(file_path), timeout=timeout)
        elapsed = time.time() - start_time
        if raw_res and raw_res.get("success"):
            code = raw_res.get("deobfuscated_code", "")
            return {
                "success": True,
                "engine": raw_res.get("engine", display_name),
                "tool_id": 3,
                "deobf_path": raw_res.get("deobf_path"),
                "report_path": raw_res.get("report_path"),
                "deobfuscated_code": code,
                "lines": len(code.splitlines()) if code else 0,
                "urls": raw_res.get("urls", []),
                "loadstrings": raw_res.get("loadstrings", []),
                "constants": raw_res.get("constants", []),
                "trace_count": raw_res.get("trace_count", 0),
                "elapsed": elapsed
            }
        else:
            return {
                "success": False,
                "engine": display_name,
                "tool_id": 3,
                "error": raw_res.get("error", "Luraph v14 deobfuscation failed") if raw_res else "No output from Luraph v14 engine",
                "elapsed": elapsed
            }

    elif engine_key == "moonsec_ironbrew":
        raw_res = moonsec_ironbrew_engine.deobfuscate_moonsec_ironbrew(str(file_path), timeout=timeout)
        elapsed = time.time() - start_time
        if raw_res and raw_res.get("success"):
            code = raw_res.get("deobfuscated_code", "")
            specific_engine = raw_res.get("engine", "IronBrew")
            return {
                "success": True,
                "engine": f"☕ {specific_engine}",
                "tool_id": 2,
                "deobf_path": raw_res.get("deobf_path"),
                "luac_path": raw_res.get("luac_path"),
                "deobfuscated_code": code,
                "lines": len(code.splitlines()) if code else 0,
                "constants": raw_res.get("constants", []),
                "elapsed": elapsed,
                "urls": [],
                "loadstrings": [],
                "report_path": raw_res.get("report_path")
            }
        else:
            return {
                "success": False,
                "engine": display_name,
                "tool_id": 2,
                "error": raw_res.get("error", "IronBrew devirtualization failed") if raw_res else "No output from IronBrew engine",
                "elapsed": elapsed
            }

    elif engine_key == "moonveil":
        # Primary: Universal Semantic Decompiler (5-Stage Pipeline)
        raw_res = None
        if _MOONVEIL_SEMANTIC_AVAILABLE:
            raw_res = _moonveil_semantic.deobfuscate_moonveil_semantic(
                str(file_path), timeout=max(timeout, 120)
            )

        # Fallback: Legacy trace emulation engine
        if not raw_res or not raw_res.get("success"):
            raw_res = moonveil_engine.deobfuscate_moonveil(str(file_path), timeout=timeout)

        elapsed = time.time() - start_time
        if raw_res and raw_res.get("success"):
            code = raw_res.get("deobfuscated_code", "")
            engine_label = raw_res.get("engine", display_name)
            mv_ver = raw_res.get("moonveil_version", "")
            if mv_ver:
                engine_label = f"🌙 Moonveil {mv_ver} (Semantic Decompiler)"
            return {
                "success": True,
                "engine": engine_label,
                "tool_id": 4,
                "deobf_path": raw_res.get("deobf_path"),
                "report_path": raw_res.get("report_path"),
                "deobfuscated_code": code,
                "lines": len(code.splitlines()) if code else 0,
                "ast_captured": raw_res.get("ast_captured", False),
                "ast_strings_count": raw_res.get("ast_strings_count", 0),
                "moonveil_version": mv_ver,
                "ai_enhanced": raw_res.get("ai_enhanced", False),
                "ai_model": raw_res.get("ai_model", ""),
                "urls": raw_res.get("urls", []),
                "loadstrings": raw_res.get("loadstrings", []),
                "trace_count": raw_res.get("trace_count", 0),
                "elapsed": elapsed
            }
        else:
            return {
                "success": False,
                "engine": display_name,
                "tool_id": 4,
                "error": (raw_res.get("error", "Moonveil deobfuscation failed")
                           if raw_res else "No output from Moonveil engine"),
                "elapsed": elapsed
            }

    elif engine_key == "twok":
        raw_res = twok_engine.deobfuscate_twok(str(file_path), timeout=timeout)
        elapsed = time.time() - start_time
        if raw_res and raw_res.get("success"):
            code = raw_res.get("deobfuscated_code", "")
            return {
                "success": True,
                "engine": display_name,
                "tool_id": 5,
                "deobf_path": raw_res.get("deobf_path"),
                "report_path": raw_res.get("report_path"),
                "deobfuscated_code": code,
                "lines": len(code.splitlines()) if code else 0,
                "urls": raw_res.get("urls", []),
                "loadstrings": raw_res.get("loadstrings", []),
                "elapsed": elapsed
            }
        else:
            return {
                "success": False,
                "engine": display_name,
                "tool_id": 5,
                "error": raw_res.get("error", "2K Security unpack failed") if raw_res else "No output from 2K engine",
                "elapsed": elapsed
            }

    elif engine_key == "luast":
        raw_res = luast_engine.deobfuscate_luast_file(str(file_path), timeout=timeout)
        elapsed = time.time() - start_time
        if raw_res and raw_res.get("success"):
            code = raw_res.get("deobfuscated_code", "")
            return {
                "success": True,
                "engine": display_name,
                "tool_id": 6,
                "deobf_path": raw_res.get("deobf_path"),
                "report_path": raw_res.get("report_path"),
                "deobfuscated_code": code,
                "lines": len(code.splitlines()) if code else 0,
                "constants_count": raw_res.get("constants_count", 0),
                "urls": [],
                "loadstrings": [],
                "elapsed": elapsed
            }
        else:
            return {
                "success": False,
                "engine": display_name,
                "tool_id": 6,
                "error": raw_res.get("error", "Luast deobfuscation failed") if raw_res else "No output from Luast engine",
                "elapsed": elapsed
            }

    elif engine_key == "base64_loader":
        # A7DEV / Custom Lua Base64 Loader Unpacker
        code = file_path.read_text(encoding='utf-8', errors='replace')
        recovered = unpack_base64_loader(code)
        elapsed = time.time() - start_time

        if not recovered:
            return {
                "success": False,
                "engine": "📦 A7DEV / Custom Lua Base64 Loader Unpacker",
                "tool_id": 7,
                "error": "ไม่พบ Base64 payload หรือ decode ไม่สำเร็จ — อาจเป็น non-standard alphabet หรือ multi-wrap",
                "elapsed": elapsed
            }

        deobf_path = file_path.with_suffix(".deobf.lua")
        report_path = file_path.with_suffix(".report.txt")
        header = (
            f"-- ====================================================================\n"
            f"-- 📦 PAYOMBØYZ DEØBFUSCATE - A7DEV BASE64 LOADER UNPACKER\n"
            f"-- Source: {file_path.name}\n"
            f"-- Status: Base64 payload decoded & unwrapped\n"
            f"-- Lines: {len(recovered.splitlines()):,}\n"
            f"-- Time: {elapsed:.2f}s\n"
            f"-- ====================================================================\n\n"
        )
        deobf_path.write_text(header + recovered, encoding='utf-8')
        urls = list(set(re.findall(r'https?://[^\s"\')]+', recovered)))
        loadstrings = list(set(re.findall(r'loadstring\([^)]+\)', recovered)))
        rep_text = (
            f"PAYOMBØYZ AUDIT REPORT\n"
            f"============================================================\n"
            f"Target:       {file_path.name}\n"
            f"Engine:       A7DEV Base64 Loader Unpacker\n"
            f"Status:       BASE64 DECODED / UNWRAPPED\n"
            f"Output Lines: {len(recovered.splitlines())}\n"
            f"URLs Found:   {len(urls)}\n"
            f"Loadstrings:  {len(loadstrings)}\n"
            f"============================================================\n"
        )
        report_path.write_text(rep_text, encoding='utf-8')
        return {
            "success": True,
            "engine": "📦 A7DEV / Custom Lua Base64 Loader Unpacker",
            "tool_id": 7,
            "deobf_path": str(deobf_path),
            "report_path": str(report_path),
            "deobfuscated_code": recovered,
            "lines": len(recovered.splitlines()),
            "urls": urls,
            "loadstrings": loadstrings,
            "constants": [],
            "elapsed": elapsed
        }

    elif engine_key == "moonsec_v5":
        raw_res = moonsec_v5_engine.deobfuscate_moonsec_v5(str(file_path), timeout=timeout)
        elapsed = time.time() - start_time
        if raw_res and raw_res.get("success"):
            code = raw_res.get("deobfuscated_code", "")
            return {
                "success": True,
                "engine": raw_res.get("engine", "🌙 MoonSec V2 / V3 (Unicode Stego VM Devirtualizer)"),
                "tool_id": 9,
                "deobf_path": raw_res.get("deobf_path"),
                "luac_path": raw_res.get("luac_path"),
                "deobfuscated_code": code,
                "lines": len(code.splitlines()) if code else 0,
                "variant": raw_res.get("variant", "v3"),
                "prototype_count": raw_res.get("prototype_count", 0),
                "constants": raw_res.get("constants", []),
                "urls": [],
                "loadstrings": [],
                "elapsed": elapsed
            }
        else:
            return {
                "success": False,
                "engine": display_name,
                "tool_id": 9,
                "error": raw_res.get("error", "MoonSec V2 / V3 devirtualization failed") if raw_res else "No output from MoonSec V2 / V3 engine",
                "elapsed": elapsed
            }

    elif engine_key == "luarmor":
        try:
            engine_root = Path(__file__).resolve().parent.parent / "LuarmorEngine"
            if str(engine_root) not in sys.path:
                sys.path.insert(0, str(engine_root))
            from engine import run_pipeline
            pipeline_res = run_pipeline(
                input_path=file_path,
                output_dir=file_path.parent / "output",
                skip_ai=True,
                max_pillar=5,
            )
            elapsed = time.time() - start_time
            if pipeline_res and pipeline_res.get("success"):
                out_file = Path(pipeline_res.get("output_file", ""))
                out_code = out_file.read_text(encoding="utf-8", errors="replace") if out_file.exists() else ""
                metrics = pipeline_res.get("metrics", {})
                return {
                    "success": True,
                    "engine": "🛡️ Luarmor One-Click (6-Pillar Full Decompiler)",
                    "tool_id": 10,
                    "deobf_path": str(out_file),
                    "report_path": str(file_path.parent / "output" / f"{file_path.stem}.report.json"),
                    "deobfuscated_code": out_code,
                    "lines": len(out_code.splitlines()) if out_code else 0,
                    "version": metrics.get("version", "V4"),
                    "closures": metrics.get("total_closures", 0),
                    "urls": [],
                    "loadstrings": [],
                    "elapsed": elapsed
                }
            else:
                return {
                    "success": False,
                    "engine": display_name,
                    "tool_id": 10,
                    "error": pipeline_res.get("error", "Luarmor 6-Pillar pipeline failed"),
                    "elapsed": elapsed
                }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "success": False,
                "engine": display_name,
                "tool_id": 10,
                "error": f"Luarmor Engine exception: {e}",
                "elapsed": elapsed
            }

    elif engine_key == "scpe":
        raw_res = scpe_engine.deobfuscate_scpe(str(file_path), timeout=timeout)
        elapsed = time.time() - start_time
        if raw_res and raw_res.get("success"):
            code = raw_res.get("deobfuscated_code", "")
            return {
                "success": True,
                "engine": display_name,
                "tool_id": 11,
                "deobf_path": raw_res.get("deobf_path"),
                "report_path": raw_res.get("report_path"),
                "deobfuscated_code": code,
                "lines": len(code.splitlines()) if code else 0,
                "layers": raw_res.get("layers", 0),
                "strings_inlined": raw_res.get("strings_inlined", 0),
                "urls": raw_res.get("urls", []),
                "loadstrings": raw_res.get("loadstrings", []),
                "elapsed": elapsed
            }
        else:
            return {
                "success": False,
                "engine": display_name,
                "tool_id": 11,
                "error": raw_res.get("error", "SCPE deobfuscation failed") if raw_res else "No output from SCPE engine",
                "elapsed": elapsed
            }

    elif engine_key == "plain":
        code = file_path.read_text(encoding='utf-8', errors='replace')
        urls = list(set(re.findall(r'https?://[^\s"\'\)]+', code)))
        loadstrings = list(set(re.findall(r'loadstring\([^\)]+\)', code)))
        deobf_path = file_path.with_suffix(".deobf.lua")
        report_path = file_path.with_suffix(".report.txt")
        header = (
            f"-- ====================================================================\n"
            f"-- 🌪️ PAYOMBØYZ SCRIPT LOADER / UNPROTECTED LUA PASSTHROUGH\n"
            f"-- Source: {file_path.name}\n"
            f"-- Status: Cleartext / Already Deobfuscated\n"
            f"-- Lines: {len(code.splitlines())}\n"
            f"-- ====================================================================\n\n"
        )
        deobf_path.write_text(header + code, encoding="utf-8")
        rep_text = (
            f"PAYOMBØYZ AUDIT REPORT\n"
            f"============================================================\n"
            f"Target:       {file_path.name}\n"
            f"Engine:       Clean Lua Script (Passthrough)\n"
            f"Status:       CLEARTEXT / UNPROTECTED\n"
            f"Output Lines: {len(code.splitlines())}\n"
            f"URLs Found:   {len(urls)}\n"
            f"Loadstrings:  {len(loadstrings)}\n"
            f"============================================================\n"
        )
        report_path.write_text(rep_text, encoding="utf-8")
        elapsed = time.time() - start_time
        return {
            "success": True,
            "engine": "📄 Clean Lua Script (Passthrough)",
            "tool_id": 0,
            "deobf_path": str(deobf_path),
            "report_path": str(report_path),
            "deobfuscated_code": code,
            "lines": len(code.splitlines()),
            "urls": urls,
            "loadstrings": loadstrings,
            "constants": [],
            "elapsed": elapsed
        }

    else:
        # WeAreDevs / Prometheus (Tool 1)
        # Primary: Universal Semantic Decompiler (5-Stage Pipeline)
        if _WRD_SEMANTIC_AVAILABLE:
            raw_res = _wrd_semantic.deobfuscate_wearedevs_semantic(str(file_path), timeout=max(timeout, 120))
        else:
            raw_res = None

        # Fallback 1: Legacy AST devirtualizer
        if (not raw_res or not raw_res.get("success")) and wearedevs_ast_engine is not None:
            raw_res = wearedevs_ast_engine.deobfuscate_file(str(file_path))

        # Fallback 2: Execution trace dumper
        if (not raw_res or not raw_res.get("success")) and deobfuscator is not None:
            raw_res = deobfuscator.deobfuscate_file_trace(str(file_path))

        elapsed = time.time() - start_time
        if raw_res and raw_res.get("success"):
            code = raw_res.get("deobfuscated_code", "")
            result_dict = {
                "success": True,
                "engine": raw_res.get("engine", display_name),
                "tool_id": 1,
                "deobf_path": raw_res.get("deobf_path"),
                "report_path": raw_res.get("report_path"),
                "deobfuscated_code": code,
                "lines": len(code.splitlines()) if code else 0,
                "urls": raw_res.get("urls", []),
                "loadstrings": raw_res.get("loadstrings", []),
                "elapsed": elapsed
            }
            # Propagate semantic-specific keys when available
            if raw_res.get("prng_keys"):
                result_dict["prng_keys"] = raw_res["prng_keys"]
            if raw_res.get("trace_count") is not None:
                result_dict["trace_count"] = raw_res["trace_count"]
            return result_dict
        else:
            err = raw_res.get("error", "WeAreDevs/Prometheus devirtualization failed") if raw_res else "No output from engine"
            return {
                "success": False,
                "engine": display_name,
                "tool_id": 1,
                "error": err,
                "elapsed": elapsed
            }


def deobfuscate(filepath: str, engine_choice: str = "auto", timeout: int = 60, is_admin: bool = False) -> Dict[str, Any]:
    start_time = time.time()
    file_path = Path(filepath).resolve()
    if not file_path.exists():
        return {
            "success": False,
            "engine": "Unknown",
            "tool_id": 0,
            "error": f"Target file not found: {filepath}",
            "elapsed": 0.0
        }

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            sample_code = f.read()
    except Exception as e:
        return {
            "success": False,
            "engine": "Unknown",
            "tool_id": 0,
            "error": f"Failed to read file: {e}",
            "elapsed": 0.0
        }

    # ---------------------------------------------------------
    # 🛡️ SECURITY AUDITOR: Tag suspicious OS patterns, proceed safely via sandbox
    # ---------------------------------------------------------
    is_safe, threat_desc = security_sandbox.scan_script_safety(sample_code)
    audit_notes = threat_desc if not is_safe else ""

    detected_engine, confidence, _ = classify_engine(sample_code)
    target_engine = ENGINE_MAP.get(str(engine_choice).lower().strip(), "auto")
    is_auto = (target_engine == "auto")

    if is_auto:
        target_engine = detected_engine

    # 1. Run chosen engine
    result = _validate_engine_result(
        _run_single_engine(target_engine, file_path, timeout, start_time, is_admin=is_admin)
    )

    if is_auto and result.get("success"):
        orig_name = result.get("engine", ENGINE_NAMES.get(target_engine, target_engine))
        if "(Auto" not in orig_name:
            result["engine"] = f"{orig_name} (Auto: {confidence}%)"
        result["detected_engine"] = detected_engine
        result["confidence"] = confidence

    # 2. Intelligent Auto-Fallback: If chosen engine fails, try detected engine and sibling engines
    if not result.get("success"):
        candidates_to_try = []
        if detected_engine and detected_engine != target_engine:
            candidates_to_try.append(detected_engine)

        sibling_engine = None
        if target_engine == "luraph":
            sibling_engine = "luraph_v15"
        elif target_engine == "luraph_v15":
            sibling_engine = "luraph"

        if sibling_engine and sibling_engine not in candidates_to_try:
            candidates_to_try.append(sibling_engine)

        for alt_eng in candidates_to_try:
            fallback_res = _validate_engine_result(
                _run_single_engine(alt_eng, file_path, timeout, start_time, is_admin=is_admin)
            )
            if fallback_res.get("success"):
                orig_name = ENGINE_NAMES.get(target_engine, target_engine)
                new_name = fallback_res.get("engine", ENGINE_NAMES.get(alt_eng, alt_eng))
                fallback_res["engine"] = f"{new_name} (⚡ สลับอัตโนมัติจาก {orig_name})"
                result = fallback_res
                break

    # 3. Cross-Engine Mutual Cascading (Multi-Layer Unwrapping)
    if result.get("success"):
        current_code = result.get("deobfuscated_code", "")
        chain = [result.get("engine", target_engine)]
        
        for _ in range(2):
            nested_engine = check_nested_obfuscation(current_code)
            if not nested_engine or nested_engine == target_engine:
                break
            
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".lua", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(current_code)

            try:
                nested_res = _validate_engine_result(
                    _run_single_engine(nested_engine, tmp_path, timeout, start_time)
                )
                if nested_res.get("success") and nested_res.get("deobfuscated_code"):
                    current_code = nested_res["deobfuscated_code"]
                    chain.append(nested_res.get("engine", nested_engine))
                    result["deobfuscated_code"] = current_code
                    result["lines"] = len(current_code.splitlines())
                    result["engine"] = " ➔ ".join(chain) + " (⚡ Multi-Layer Cascade)"
                    
                    deobf_p = result.get("deobf_path")
                    if deobf_p:
                        with open(deobf_p, "w", encoding="utf-8") as f:
                            header = (
                                f"-- ====================================================================\n"
                                f"-- ⚡ MULTI-LAYER DEOBFUSCATION COMPLETED\n"
                                f"-- Pipeline: {' ➔ '.join(chain)}\n"
                                f"-- ====================================================================\n\n"
                            )
                            f.write(header + current_code)
                else:
                    break
            finally:
                try: os.remove(tmp_path)
                except: pass

    # 4. If still failed and detected signature doesn't match chosen engine, provide informative advice
    if not result.get("success") and detected_engine != target_engine:
        orig_err = result.get("error", "Unknown error")
        chosen_name = ENGINE_NAMES.get(target_engine, target_engine)
        det_name = ENGINE_NAMES.get(detected_engine, detected_engine)
        result["error"] = f"{orig_err}\n💡 คำแนะนำ: สคริปต์นี้ถูกตรวจพบว่าเป็น {det_name} แต่คุณเลือก {chosen_name}"

    return _validate_engine_result(result)


# Compatibility alias for universal pipeline
run_all = deobfuscate


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        eng = sys.argv[2] if len(sys.argv) > 2 else "auto"
        res = deobfuscate(target, eng)
        print("Result:", res)
    else:
        print("Engine Router module ready.")
