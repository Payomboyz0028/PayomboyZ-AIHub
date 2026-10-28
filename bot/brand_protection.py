# -*- coding: utf-8 -*-
"""
=============================================================================
  🛡️ PAYOMBØYZ INTELLECTUAL PROPERTY & BRAND PROTECTION GUARD
  Enforces zero-tolerance refusal for deobfuscating scripts belonging to
  PAYOMBØYZ / พยอมบอย. Prevents reverse-engineering our own studio's assets.
=============================================================================
"""

import unicodedata
from typing import Tuple, Union

FORBIDDEN_BRAND_MARKERS = [
    "payomboy",
    "payomboyz",
    "payombøyz",
    "payomboyzaa",
    "payomboi",
    "พยอมบอย",
    "พยอม",
    "payomboyz-hub",
    "payomboyz-logs"
]

BRAND_REFUSAL_MESSAGE = (
    "🛡️ [PAYOMBØYZ PROTECTED SCRIPT]\n"
    "ตรวจพบลายน้ำหรือตราสัญลักษณ์ของค่าย PAYOMBØYZ / พยอมบอย ในสคริปต์นี้\n"
    "ระบบปฏิเสธการถอดรหัสโดยเด็ดขาด เนื่องจากเป็นทรัพย์สินทางปัญญาของค่ายเราเอง\n"
    "ไม่อนุญาตให้แกะหรือ Deobfuscate สคริปต์ของค่ายตัวเอง"
)


def check_brand_protection(code_or_bytes: Union[str, bytes]) -> Tuple[bool, str]:
    """
    Scans code for PAYOMBØYZ brand markers across Unicode encodings and normalizations.
    Returns (is_protected, matched_term).
    """
    if not code_or_bytes:
        return False, ""

    if isinstance(code_or_bytes, bytes):
        text = code_or_bytes.decode("utf-8", errors="replace")
    else:
        text = str(code_or_bytes)

    # 1. Direct lowercase & casefold match
    folded = text.casefold()
    for m in FORBIDDEN_BRAND_MARKERS:
        if m in folded:
            return True, m

    # 2. Unicode normalization (NFKD & NFC)
    nfkd = unicodedata.normalize("NFKD", text).casefold()
    for m in FORBIDDEN_BRAND_MARKERS:
        if m in nfkd:
            return True, m

    # 3. Leetspeak / slashed-o normalization (Ø/ø -> o)
    o_normalized = nfkd.replace("ø", "o").replace("Ø", "o")
    if "payomboy" in o_normalized or "payomboyz" in o_normalized:
        return True, "payomboyz"

    return False, ""
