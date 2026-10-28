#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ KNOWLEDGE BASE — SCORING & RANKING ENGINE
====================================================================
Formula:
  FinalScore = Relevance * Quality * Recency * UsageFrequency
====================================================================
"""

import time
from typing import Dict, Any

# Quality Weight Tiers
QUALITY_TIERS = {
    "OFFICIAL_CURRENT": 1.00,       # Obsidian Glassmorphic 2.0, main.luau, Wait Key.txt
    "TESTED_PRODUCTION": 0.95,      # Blox Fruit, ACF, Grow a Chicken, Mine a Mountain, etc.
    "VERIFIED_EXAMPLE": 0.90,       # Fluent, WindUI, Intro.md
    "OLD_WORKING": 0.75,            # MM2, Sniper Arena, 99Night
    "EXPERIMENTAL": 0.60,           # Ai Script.txt, string.lua.txt
    "UNKNOWN_EXTERNAL": 0.30        # ของคนอื่น.txt
}

# File to Quality Tier Mapping
FILE_QUALITY_MAP = {
    "Obsidain_Glassmophic2.txt": "OFFICIAL_CURRENT",
    "main.luau": "OFFICIAL_CURRENT",
    "Wait Key.txt": "OFFICIAL_CURRENT",
    "ราคา.txt": "OFFICIAL_CURRENT",
    "ข้อตกลง.txt": "OFFICIAL_CURRENT",
    "Logic การใช้เงิน.md": "OFFICIAL_CURRENT",
    "รวมBypass.txt": "OFFICIAL_CURRENT",
    
    "Blox Fruit.txt": "TESTED_PRODUCTION",
    "ACF.txt": "TESTED_PRODUCTION",
    "Anime Card Farm.txt": "TESTED_PRODUCTION",
    "Anime Dice.txt": "TESTED_PRODUCTION",
    "CapybaraVsPlant.txt": "TESTED_PRODUCTION",
    "FISCH.txt": "TESTED_PRODUCTION",
    "Grow a garden 2.txt": "TESTED_PRODUCTION",
    "Grow a Chicken Fighter.txt": "TESTED_PRODUCTION",
    "Mine a Mountain.txt": "TESTED_PRODUCTION",
    "Greedy Grower.txt": "TESTED_PRODUCTION",
    "Iron Soul-Dungeon.txt": "TESTED_PRODUCTION",
    "Iron Soul Boss.txt": "TESTED_PRODUCTION",
    "Iron Soul Tower.txt": "TESTED_PRODUCTION",
    "Roll Anime to FIGHT.txt": "TESTED_PRODUCTION",
    "Roll a Gnome.txt": "TESTED_PRODUCTION",
    "Steal An Egg.txt": "TESTED_PRODUCTION",
    "Steal Anime Egg.txt": "TESTED_PRODUCTION",
    "Ride a pet.txt": "TESTED_PRODUCTION",
    "AOTR.txt": "TESTED_PRODUCTION",
    "Gakurun.txt": "TESTED_PRODUCTION",
    
    "Fluent.txt": "VERIFIED_EXAMPLE",
    "WindUI.txt": "VERIFIED_EXAMPLE",
    "UILibrary.lua": "VERIFIED_EXAMPLE",
    "Intro.md": "VERIFIED_EXAMPLE",
    
    "Master Mystery 2.txt": "OLD_WORKING",
    "Sniper Arena.txt": "OLD_WORKING",
    "99Night.txt": "OLD_WORKING",
    "Aneme Expredition.txt": "OLD_WORKING",
    "Ai Log-in.txt": "OLD_WORKING",
    "Script Log-in.txt": "OLD_WORKING",
    "No-KeyVIP.txt": "OLD_WORKING",
    "No-KeyVVIP.txt": "OLD_WORKING",
    
    "Ai Script.txt": "EXPERIMENTAL",
    "string.lua.txt": "EXPERIMENTAL",
    "start.lua.txt": "EXPERIMENTAL",
    "nokey.luau": "EXPERIMENTAL",
    
    "ของคนอื่น.txt": "UNKNOWN_EXTERNAL"
}


def get_file_quality_score(filename: str) -> float:
    """Returns quality score based on designated tier (0.30 - 1.00)."""
    tier = FILE_QUALITY_MAP.get(filename, "TESTED_PRODUCTION")
    return QUALITY_TIERS.get(tier, 0.85)


def calculate_recency_score(file_mtime: float) -> float:
    """Computes decay score based on modification time (0.40 - 1.00)."""
    now = time.time()
    diff_days = (now - file_mtime) / 86400.0 if file_mtime > 0 else 30.0
    if diff_days <= 7:
        return 1.00
    elif diff_days <= 30:
        return 0.95
    elif diff_days <= 90:
        return 0.85
    elif diff_days <= 180:
        return 0.70
    return 0.50


def calculate_knowledge_score(relevance: float, quality: float, recency: float, usage_frequency: float = 1.0) -> float:
    """
    Computes final knowledge ranking score:
    FinalScore = Relevance * Quality * Recency * UsageFrequency
    Clamped to 0.0 - 1.0.
    """
    score = relevance * quality * recency * min(usage_frequency, 1.2)
    return round(max(0.0, min(1.0, score)), 4)
