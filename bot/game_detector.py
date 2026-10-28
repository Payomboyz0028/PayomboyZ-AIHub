# -*- coding: utf-8 -*-
"""
=============================================================================
  🎮 ROBLOX GAME & MAP FORENSIC DETECTOR
  - Accurately identifies Roblox Games, Maps, and Multi-Game Hub Targets
    from Script Content, PlaceIds, Remote Invocations, Titles, and Slugs.
  - Queries Roblox Public Platform API dynamically for unknown Place IDs.
  - Never returns generic 'Script hub' or 'Roblox' without deep forensic lookup.
=============================================================================
"""

import re
import json
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

CANONICAL_PLACE_MAP: Dict[int, Dict[str, str]] = {
    # Blox Fruits
    2753915549: {"game": "Blox Fruits 🍎", "map": "Sea 1 (Pirate Starter)"},
    4442272183: {"game": "Blox Fruits 🍎", "map": "Sea 2 (Kingdom of Rose)"},
    7449423635: {"game": "Blox Fruits 🍎", "map": "Sea 3 (Floating Turtle / Sea Events)"},
    # DOORS
    6516141723: {"game": "DOORS 🚪", "map": "The Hotel"},
    6839171747: {"game": "DOORS 🚪", "map": "The Hotel (Lobby / Modded)"},
    10793665798: {"game": "DOORS 🚪", "map": "The Mines (Floor 2)"},
    # Fisch
    16732694052: {"game": "Fisch 🎣", "map": "Moosewood / Ocean World"},
    # Blade Ball
    13775256536: {"game": "Blade Ball ⚔️", "map": "Main Arena"},
    14732610803: {"game": "Blade Ball ⚔️", "map": "Ranked / Duel Arena"},
    # Steal An Egg (SAE)
    10449761463: {"game": "Steal An Egg (SAE) 🥚", "map": "Main Island"},
    # Arsenal
    286090429: {"game": "Arsenal 🔫", "map": "Standard Matchmaking"},
    # BedWars
    6872265039: {"game": "BedWars 🛏️", "map": "Competitive Arena"},
    # Da Hood
    2788229376: {"game": "Da Hood 🔫", "map": "Main City"},
    16033173781: {"game": "Da Hood 🔫", "map": "Da Hood Aim Trainer"},
    # Rivals
    17625359962: {"game": "Rivals 🎯", "map": "Competitive FPS Arena"},
    # Pet Simulator 99
    8737899170: {"game": "Pet Simulator 99 🐾", "map": "World 1 & 2"},
    16498369169: {"game": "Pet Simulator 99 🐾", "map": "Void World"},
    # Anime Zero
    17915095344: {"game": "Anime Zero ⚡", "map": "Main Battle Dimension"},
    # King Legacy
    8542259458: {"game": "King Legacy 👑", "map": "Sea 1 & 2"},
    4520749081: {"game": "King Legacy 👑", "map": "Sea 3"},
    # Murder Mystery 2
    142823291: {"game": "Murder Mystery 2 🔪", "map": "Lobby & Rotation"},
    # Natural Disaster Survival
    189707: {"game": "Natural Disaster Survival 🌪️", "map": "Island Arena"},
    # Brookhaven RP
    4924922222: {"game": "Brookhaven RP 🏡", "map": "Township"},
    # Anime Vanguards
    17013322904: {"game": "Anime Vanguards 🛡️", "map": "Story & Infinite Defense"},
    # Anime Defenders
    17017769292: {"game": "Anime Defenders 🛡️", "map": "Defense Worlds"},
    # Anime Last Stand
    16146832113: {"game": "Anime Last Stand 🛡️", "map": "Story Stages"},
    # Project Slayers
    5956785391: {"game": "Project Slayers ⚔️", "map": "Map 1"},
    6152116144: {"game": "Project Slayers ⚔️", "map": "Map 2 (Mugen Train)"},
    # Deepwoken
    4111023553: {"game": "Deepwoken 🌊", "map": "The Etrean Luminant"},
    # Toilet Tower Defense
    6068496240: {"game": "Toilet Tower Defense 🚽", "map": "Defense Arenas"},
    # 99 Nights in the Forest
    79546208627805: {"game": "99 Nights in the Forest 🌲", "map": "Survival Forest (Main Map)"},
    126509999114328: {"game": "99 Nights in the Forest 🌲", "map": "Survival Forest (Event / Hardcore)"},
}

TITLE_REGEX_MAP: List[Tuple[str, str, str]] = [
    (r"\b(blox\s*fruit[s]?|bf)\b", "Blox Fruits 🍎", "Pirate Adventure"),
    (r"\b(doors|door)\b", "DOORS 🚪", "Hotel & Mines"),
    (r"\b(fisch|fish|fishing)\b", "Fisch 🎣", "Moosewood"),
    (r"\b(blade\s*ball|bb)\b", "Blade Ball ⚔️", "Battle Arena"),
    (r"\b(steal\s*an\s*egg|sae)\b", "Steal An Egg (SAE) 🥚", "Egg Hunt"),
    (r"\b(arsenal)\b", "Arsenal 🔫", "FPS Deathmatch"),
    (r"\b(bed\s*war[s]?)\b", "BedWars 🛏️", "Bed Defense"),
    (r"\b(da\s*hood|dh)\b", "Da Hood 🔫", "City Hood"),
    (r"\b(rivals)\b", "Rivals 🎯", "FPS 1v1 / Ranked"),
    (r"\b(pet\s*sim|ps99|psx)\b", "Pet Simulator 99 🐾", "Pet Worlds"),
    (r"\b(anime\s*zero|az)\b", "Anime Zero ⚡", "Anime Dimensions"),
    (r"\b(king\s*legacy)\b", "King Legacy 👑", "Grand Line"),
    (r"\b(murder\s*mystery|mm2)\b", "Murder Mystery 2 🔪", "Classic Horror"),
    (r"\b(anime\s*vanguards)\b", "Anime Vanguards 🛡️", "Tower Defense"),
    (r"\b(anime\s*defenders)\b", "Anime Defenders 🛡️", "Tower Defense"),
    (r"\b(project\s*slayers)\b", "Project Slayers ⚔️", "Demon Slayer World"),
    (r"\b(deepwoken)\b", "Deepwoken 🌊", "Hardcore RPG"),
    (r"\b(toilet\s*tower|ttd)\b", "Toilet Tower Defense 🚽", "Skibidi Defense"),
    (r"\b(prison\s*life)\b", "Prison Life 🚓", "Prison Yard"),
    (r"\b(99\s*nights\s*in\s*the\s*forest|nights\s*in\s*the\s*forest)\b", "99 Nights in the Forest 🌲", "Survival Forest"),
    (r"\b(ride\s*a\s*pet|rap)\b", "Ride A Pet 🐾", "Pet Island"),
    (r"\b(slap\s*battles)\b", "Slap Battles 🖐️", "Slap Arena"),
]

_ROBLOX_API_CACHE: Dict[int, str] = {}


def resolve_place_id_online(place_id: int) -> Optional[str]:
    """Queries official Roblox Web API to discover canonical game title."""
    if place_id in _ROBLOX_API_CACHE:
        return _ROBLOX_API_CACHE[place_id]

    try:
        req1 = urllib.request.Request(
            f"https://apis.roblox.com/universes/v1/places/{place_id}/universe",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req1, timeout=3.5) as r1:
            data1 = json.loads(r1.read().decode("utf-8"))
            uid = data1.get("universeId")

        if uid:
            req2 = urllib.request.Request(
                f"https://games.roblox.com/v1/games?universeIds={uid}",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req2, timeout=3.5) as r2:
                data2 = json.loads(r2.read().decode("utf-8"))
                games = data2.get("data", [])
                if games and games[0].get("name"):
                    name = games[0]["name"].strip()
                    _ROBLOX_API_CACHE[place_id] = name
                    return name
    except Exception:
        pass
    return None


def detect_roblox_game_and_map(
    raw_code: str = "",
    deobf_code: str = "",
    title: str = "",
    slug: str = "",
    sb_game_name: str = ""
) -> Dict[str, Any]:
    """
    Forensic engine to determine the exact Roblox Game and Map for any script.
    Returns:
        {
            "display": str,         # e.g. "Blox Fruits (Sea 2) 🍎" or "Multi-Game Hub"
            "game": str,            # Primary game name
            "map": str,             # Specific sub-map or mode
            "place_ids": List[int], # Detected PlaceIDs
            "is_multigame": bool,
            "confidence": float
        }
    """
    combined = (raw_code + "\n" + deobf_code)
    
    # 1. Place ID Extraction from Code
    # Explicit PlaceId comparisons (e.g. game.PlaceId == 2753915549)
    pids_cond = re.findall(r'(?:PlaceId|place_id|placeId)\s*(?:==|:|=)\s*(\d{6,12})', combined)
    # Multi-game table mappings (must be 7-12 digits and mapped to string/table/func, not VM registers like Nd[25505] = L)
    pids_table = re.findall(r'\[(\d{7,12})\]\s*=\s*(?:["\'\{]|function|\w+\.lua)', combined)
    # Generic place table mappings in scripts
    pids_hub = re.findall(r'(?:places|games|hubs|scripts)\[(\d{7,12})\]', combined, re.IGNORECASE)
    found_pids = [int(p) for p in (pids_cond + pids_table + pids_hub)]
    found_pids = list(dict.fromkeys(found_pids))

    # Match against Canonical Database
    matched_games: List[Tuple[str, str]] = []
    for pid in found_pids:
        if pid in CANONICAL_PLACE_MAP:
            info = CANONICAL_PLACE_MAP[pid]
            matched_games.append((info["game"], info["map"]))
        else:
            # Query Roblox API online for unknown PlaceId
            online_name = resolve_place_id_online(pid)
            if online_name:
                matched_games.append((f"{online_name} 🎮", f"Place ID {pid}"))

    # Multi-Game Hub branch
    if len(matched_games) > 1:
        unique_games = list(dict.fromkeys([g[0] for g in matched_games]))
        preview = ", ".join(unique_games[:3])
        if len(unique_games) > 3:
            preview += f" และอีก {len(unique_games)-3} เกม"
        return {
            "display": f"Multi-Game Hub (รองรับ: {preview})",
            "game": "Multi-Game Hub",
            "map": preview,
            "place_ids": found_pids,
            "is_multigame": True,
            "confidence": 98.0
        }
    elif len(matched_games) == 1:
        g, m = matched_games[0]
        return {
            "display": f"{g} — {m}",
            "game": g,
            "map": m,
            "place_ids": found_pids,
            "is_multigame": False,
            "confidence": 99.0
        }

    # 2. Title & Slug Acronym / Keyword Matching
    meta_text = f"{title} {slug}".lower()
    for pattern, g_name, m_name in TITLE_REGEX_MAP:
        if re.search(pattern, meta_text, re.IGNORECASE):
            return {
                "display": f"{g_name} — {m_name}",
                "game": g_name,
                "map": m_name,
                "place_ids": [],
                "is_multigame": False,
                "confidence": 95.0
            }

    # 3. In-Code Remote & Game Mechanic Signatures
    if any(k in combined for k in ["CommF_", "CommE", "Beli", "DevilFruit", "Sea 1", "Sea 2", "Sea 3", "ChestFarm"]):
        return {"display": "Blox Fruits 🍎 (Auto-Farm & Combat)", "game": "Blox Fruits 🍎", "map": "All Seas", "place_ids": [], "is_multigame": False, "confidence": 95.0}

    if any(k in combined for k in ["Crucifix", "Figure", "Seek", "Eyes", "Screech", "DupeDoor", "Rush"]):
        return {"display": "DOORS 🚪 (Hotel & Entity Bypass)", "game": "DOORS 🚪", "map": "The Hotel", "place_ids": [], "is_multigame": False, "confidence": 95.0}

    if any(k in combined for k in ["FishingRod", "FishRadar", "Moosewood", "CatchFish", "Reel"]):
        return {"display": "Fisch 🎣 (Auto-Fishing & Radar)", "game": "Fisch 🎣", "map": "Ocean Islands", "place_ids": [], "is_multigame": False, "confidence": 95.0}

    if any(k in combined for k in ["Parry", "Deflect", "BallTarget", "SpamBlock", "AutoBlock"]):
        return {"display": "Blade Ball ⚔️ (Auto-Parry & Curved Deflect)", "game": "Blade Ball ⚔️", "map": "Battle Arena", "place_ids": [], "is_multigame": False, "confidence": 95.0}

    if any(k in combined for k in ["StealEgg", "EggHatch", "EasterEgg", "DropEgg"]):
        return {"display": "Steal An Egg (SAE) 🥚", "game": "Steal An Egg (SAE) 🥚", "map": "Egg Hunt Island", "place_ids": [], "is_multigame": False, "confidence": 95.0}

    # 4. Universal FPS / Aimbot / ESP
    if any(k in combined for k in ["AimLock", "VisibilityCheck", "AimState", "FOV/Radius", "ShowAssistDots", "TargetPart", "AimAssist"]):
        return {
            "display": "Universal (ทุกเกม / FPS Universal Hub — Aimbot & ESP) 🎯",
            "game": "Universal FPS Hub",
            "map": "รองรับทุกเกมที่เป็นแนว FPS / Shooter",
            "place_ids": [],
            "is_multigame": True,
            "confidence": 92.0
        }

    # 5. Universal Movement / Fly / Utility
    if any(k in meta_text for k in ["fly", "noclip", "speed", "tpwalk", "teleport", "infjump"]):
        return {
            "display": "Universal (ทุกแมพ — Movement & Character Exploit) 🌐",
            "game": "Universal Roblox",
            "map": "ใช้งานได้ทุกแมพ",
            "place_ids": [],
            "is_multigame": True,
            "confidence": 90.0
        }

    # 6. Fallback to ScriptBlox metadata if non-generic
    if sb_game_name and sb_game_name.lower() not in ("script hub", "roblox", "universal", "all games", "unknown", ""):
        return {
            "display": f"{sb_game_name} 🎮",
            "game": sb_game_name,
            "map": "Main",
            "place_ids": [],
            "is_multigame": False,
            "confidence": 85.0
        }

    return {
        "display": "Universal Hub / ไม่ระบุแมพเจาะจง 🌐",
        "game": "Universal Hub",
        "map": "Universal",
        "place_ids": [],
        "is_multigame": True,
        "confidence": 70.0
    }
