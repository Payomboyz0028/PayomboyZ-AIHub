# ==============================================================================
# PAYOMBØYZ ROBLOX LINK & EXPERIENCE RESOLVER
# Resolves Roblox direct game links, share links, and experience metadata
# Auto-enriches AI prompts for BluezyGPT / PAYØMBØYZAA script intelligence
# ==============================================================================

import asyncio
import html
import json
import re
import time
import urllib.request
import urllib.parse
from typing import Any, Dict, Optional, Tuple

# In-memory cache for resolved games: key -> (timestamp, game_data)
_RESOLVER_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour cache

# Regex patterns for Roblox URLs
ROBLOX_DIRECT_GAME_RE = re.compile(
    r'https?://(?:www\.|web\.)?roblox\.com/games/(\d+)(?:/[^\s\?\#]+)?',
    re.IGNORECASE
)

ROBLOX_SHARE_LINK_RE = re.compile(
    r'https?://(?:www\.|web\.)?(?:roblox\.com/share(?:-links)?|ro\.blox\.com)[^\s<>"\']+',
    re.IGNORECASE
)

ROBLOX_ANY_LINK_RE = re.compile(
    r'https?://(?:www\.|web\.)?(?:roblox\.com/(?:games/\d+|share(?:-links)?)|ro\.blox\.com)[^\s<>"\']+',
    re.IGNORECASE
)


def contains_roblox_game_link(text: str) -> bool:
    """Checks if the text contains any Roblox game or share link."""
    if not text:
        return False
    return bool(ROBLOX_ANY_LINK_RE.search(text))


def extract_roblox_link(text: str) -> Optional[str]:
    """Extracts the first Roblox game or share link from text."""
    if not text:
        return None
    match = ROBLOX_ANY_LINK_RE.search(text)
    return match.group(0) if match else None


def clean_game_name(raw_name: str) -> str:
    """Sanitizes game name for safe display and file naming."""
    if not raw_name:
        return "RobloxGame"
    # Remove emojis and bracket prefixes like [🍀x2 Luck]
    cleaned = re.sub(r'\[.*?\]', '', raw_name)
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', '', cleaned).strip()
    return cleaned or "RobloxGame"


def _sync_fetch_url(url: str, timeout: int = 6) -> Tuple[str, str]:
    """Synchronously fetches URL and returns (final_url, html_content)."""
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        final_url = resp.geturl()
        content = resp.read().decode('utf-8', errors='ignore')
        return final_url, content


def _sync_fetch_json(url: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
    """Synchronously fetches JSON from Roblox public API."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json',
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8', errors='ignore'))
    except Exception:
        return None


def resolve_roblox_game_sync(text_or_url: str) -> Optional[Dict[str, Any]]:
    """Resolves Roblox game metadata synchronously.
    
    Returns:
        dict with place_id, universe_id, name, clean_name, description, genre, creator, playing, visits
        or None if no valid game link was found.
    """
    raw_link = extract_roblox_link(text_or_url)
    if not raw_link:
        return None

    # Check cache
    now = time.time()
    if raw_link in _RESOLVER_CACHE:
        cached_time, cached_data = _RESOLVER_CACHE[raw_link]
        if now - cached_time < _CACHE_TTL_SECONDS:
            return cached_data

    place_id: Optional[str] = None
    og_title: str = ""
    og_desc: str = ""

    # 1. Direct place ID from URL
    direct_match = ROBLOX_DIRECT_GAME_RE.search(raw_link)
    if direct_match:
        place_id = direct_match.group(1)

    # 2. Share link resolution
    if not place_id and ROBLOX_SHARE_LINK_RE.search(raw_link):
        try:
            final_url, html_content = _sync_fetch_url(raw_link, timeout=6)
            
            # Check if redirected to games/<place_id>
            redir_match = ROBLOX_DIRECT_GAME_RE.search(final_url)
            if redir_match:
                place_id = redir_match.group(1)

            # Check meta tag for start_place_id
            if not place_id:
                pid_match = re.search(r'name=["\']roblox:start_place_id["\']\s+content=["\'](\d+)["\']', html_content, re.IGNORECASE)
                if pid_match:
                    place_id = pid_match.group(1)

            # Check OpenGraph metadata
            t_match = re.search(r'property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            if t_match:
                og_title = html.unescape(t_match.group(1)).strip()

            d_match = re.search(r'property=["\']og:description["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            if d_match:
                og_desc = html.unescape(d_match.group(1)).strip()

        except Exception as share_err:
            print(f"[ROBLOX RESOLVER] Failed to resolve share link {raw_link}: {share_err}")

    if not place_id:
        # If we got title/desc from og but no place_id, build partial metadata
        if og_title:
            result = {
                "place_id": "unknown",
                "universe_id": "unknown",
                "name": og_title,
                "clean_name": clean_game_name(og_title),
                "description": og_desc[:2500],
                "genre": "RPG / Action",
                "creator": "Roblox Developer",
                "playing": 0,
                "visits": 0,
                "source_url": raw_link,
            }
            _RESOLVER_CACHE[raw_link] = (now, result)
            return result
        return None

    # 3. Query Roblox Public APIs with place_id
    universe_id: Optional[str] = None
    uni_data = _sync_fetch_json(f"https://apis.roblox.com/universes/v1/places/{place_id}/universe", timeout=4)
    if uni_data and uni_data.get("universeId"):
        universe_id = str(uni_data["universeId"])

    game_name = og_title or f"Roblox Place {place_id}"
    game_desc = og_desc or ""
    genre = "Unknown"
    creator = "Unknown"
    playing = 0
    visits = 0

    if universe_id:
        game_api_data = _sync_fetch_json(f"https://games.roblox.com/v1/games?universeIds={universe_id}", timeout=4)
        if game_api_data and game_api_data.get("data"):
            g = game_api_data["data"][0]
            game_name = g.get("name") or game_name
            game_desc = g.get("description") or game_desc
            genre = g.get("genre") or genre
            creator = (g.get("creator") or {}).get("name") or creator
            playing = g.get("playing", 0)
            visits = g.get("visits", 0)

    result = {
        "place_id": place_id,
        "universe_id": universe_id or "unknown",
        "name": game_name,
        "clean_name": clean_game_name(game_name),
        "description": game_desc[:2500],
        "genre": genre,
        "creator": creator,
        "playing": playing,
        "visits": visits,
        "source_url": raw_link,
    }

    _RESOLVER_CACHE[raw_link] = (now, result)
    return result


async def resolve_roblox_game_async(text_or_url: str) -> Optional[Dict[str, Any]]:
    """Asynchronously resolves Roblox game metadata without blocking event loop."""
    return await asyncio.to_thread(resolve_roblox_game_sync, text_or_url)


def build_game_script_prompt(game_data: Dict[str, Any], user_raw_text: str) -> str:
    """Builds an enriched, domain-specific script prompt for BluezyGPT."""
    raw_link = game_data.get("source_url", "")
    game_name = game_data.get("name", "Roblox Game")
    place_id = game_data.get("place_id", "Unknown")
    genre = game_data.get("genre", "Unknown")
    desc = game_data.get("description", "").strip()
    creator = game_data.get("creator", "Unknown")

    # Strip the raw link out of user text to see what extra instructions they gave
    extra_instructions = user_raw_text
    if raw_link:
        extra_instructions = extra_instructions.replace(raw_link, "").strip()

    # Normalize minimal prompts like "script", "สคริป", "สคริปต์"
    extra_lower = extra_instructions.lower()
    is_generic_script_ask = (
        not extra_instructions
        or extra_lower in ("script", "สคริป", "สคริปต์", "ขอสคริป", "ขอสคริปต์", "ทำสคริป", "ทำสคริปต์", "lua", "code")
    )

    if is_generic_script_ask:
        specific_goal = (
            f"ผู้ใช้ต้องการสคริปต์ Client Utility, Entity Scanner / Visual ESP สำหรับมอนสเตอร์/ผู้เล่น/ไอเทม "
            f"และระบบช่วยเหลือที่เหมาะสมกับเกมแนว {genre} / {game_name}"
        )
    else:
        specific_goal = f"ผู้ใช้ระบุคำขอเฉพาะ: {extra_instructions}"

    enriched_prompt = (
        f"ผู้ใช้ส่งลิงก์แมพ Roblox เพื่อให้สร้างสคริปต์:\n"
        f"📌 **ข้อมูลแมพ / เกม**\n"
        f"- ชื่อเกม: {game_name} (Place ID: {place_id})\n"
        f"- แนวเกม (Genre): {genre} | ผู้สร้าง: {creator}\n"
        f"- ข้อมูลและระบบเกมเพลย์:\n{desc[:1500] if desc else 'ไม่มีคำอธิบายเพิ่มเติม'}\n\n"
        f"🎯 **เป้าหมายสคริปต์**\n{specific_goal}\n\n"
        f"⚙️ **ข้อกำหนดการสร้างสคริปต์เต็มระบบ (Strict Architecture Rules)**\n"
        f"1. สรุปเป็นภาษาไทย 1-2 ย่อหน้าในข้อความแชท: อธิบายฟังก์ชันเด่นของสคริปต์ (ระบบ Auto Farm, UI, ESP, Bypass, Keybind) และบอกว่าแนบสคริปต์ตัวเต็มไว้ให้แล้ว\n"
        f"2. เขียนโค้ด Luau ตัวเต็มแบบสมบูรณ์และใช้งานได้จริงระดับ Production (Complete Executable Luau Script) ลงในบล็อก ```lua ... ```\n"
        f"   - มี UI Framework ครบชุด (Fluent / WindUI / Obsidian Glassmorphic) พร้อม Window, Tabs, Toggles, Sliders, Dropdowns ทุกตัวเชื่อม Callback เข้ากับ State ใช้งานได้จริง\n"
        f"   - มี Gameplay Automation Engine ครบถ้วนตามคำขอ (Auto Farm, Auto Collect, Teleport/Tween bypass, Raycasting, StreamingEnabled retry queue)\n"
        f"   - ห้ามตัดทอน ห้ามใช้ placeholder ห้ามเขียน '-- implement logic here' หรือ '-- TODO' เด็ดขาด ทุกฟังก์ชันต้องเขียนโค้ดเต็ม 100%\n"
        f"   - เขียนโค้ดแบบ Safe & Production-ready สำหรับรันบน Executor (Solara, Wave, Delta, Codex, Arceus X, Synapse Z)"
    )
    return enriched_prompt
