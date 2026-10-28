#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ ROBLOX PLATFORM INTELLIGENCE & TELEMETRY ENGINE V1.0
====================================================================
Deep Integration with https://www.roblox.com/ Platform APIs:
  - Universal Search & Discovery (Thai & English Semantic Mapper)
  - Place-to-Universe Multi-Resolver
  - Badges Roadmap Engine (Bosses, Quests, Tiers, Progression)
  - Live Server Telemetry (Low-Player Server Sniper for 0% Report Farm)
  - High-Res Visual Thumbnail & CDN Ingestion
====================================================================
"""

import re
import json
import asyncio
import urllib.parse
from typing import Dict, Any, List, Optional
import aiohttp

ROBLOX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
}

# Thai to Canonical Roblox Game Name dictionary
THAI_GAME_ALIASES = {
    "บล็อกฟรุต": "Blox Fruits",
    "บล็อกฟรุ๊ต": "Blox Fruits",
    "บลอกฟรุต": "Blox Fruits",
    "ดาบพิฆาตอสูร": "Project Slayers",
    "สเลเยอร์": "Project Slayers",
    "สเลเยอ": "Project Slayers",
    "ขโมยไข่": "Steal An Egg",
    "ขุดภูเขา": "Mine a Mountain",
    "อนิเมะการ์ด": "Anime Card Battle",
    "ฟิช": "Fisch",
    "ตกปลา": "Fisch",
    "ไรวัล": "Rivals",
    "เบลดบอล": "Blade Ball",
    "บอลสะท้อน": "Blade Ball",
    "ดันเจี้ยน": "Dungeon Lootr",
    "ไททัน": "Attack on Titan Revolution",
    "สไนเปอร์": "Sniper Arena",
    "ไก่ชน": "Grow a Chicken Fighter",
    "ปลูกผัก": "Grow a garden 2",
}

class RobloxPlatformIntel:
    """
    Direct interface to Roblox Platform internal and public endpoints.
    """
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=8)

    def normalize_game_name(self, query: str) -> str:
        """Translates Thai keywords to canonical Roblox game titles."""
        clean_q = query.strip()
        low = clean_q.lower()
        for th_key, en_name in THAI_GAME_ALIASES.items():
            if th_key in low:
                return en_name
        return clean_q

    async def resolve_place_to_universe(self, place_id: str | int) -> Optional[int]:
        """Resolves any Roblox Place ID into its parent Universe ID."""
        url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=ROBLOX_HEADERS) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("universeId")
        except Exception:
            pass
        return None

    async def get_universe_details(self, universe_id: int) -> Optional[Dict[str, Any]]:
        """Pulls official game metadata: Playing count, Visits, Updated, Description."""
        url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=ROBLOX_HEADERS) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        games = data.get("data", [])
                        if games:
                            return games[0]
        except Exception:
            pass
        return None

    async def get_game_thumbnail(self, universe_id: int, size: str = "512x512") -> str:
        """Fetches high-res game icon from Roblox CDN."""
        url = f"https://thumbnails.roblox.com/v1/games/icons?universeIds={universe_id}&size={size}&format=Png&isCircular=false"
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=ROBLOX_HEADERS) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get("data", [])
                        if items:
                            return items[0].get("imageUrl") or ""
        except Exception:
            pass
        return ""

    async def get_game_badges_roadmap(self, universe_id: int, limit: int = 15) -> List[Dict[str, str]]:
        """
        Extracts game badges as a progression roadmap:
        Reveals boss names, progression seas/worlds, secret quests, and milestones!
        """
        url = f"https://badges.roblox.com/v1/universes/{universe_id}/badges?limit={limit}"
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=ROBLOX_HEADERS) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        badges = data.get("data", [])
                        return [
                            {
                                "name": b.get("name", ""),
                                "description": b.get("description", "")
                            }
                            for b in badges if b.get("name")
                        ]
        except Exception:
            pass
        return []

    async def get_full_platform_intelligence(
        self,
        query_or_name: str,
        place_id: Optional[str | int] = None
    ) -> Dict[str, Any]:
        """
        Master intelligence aggregator for any game:
        1. Canonical naming & Thai translation
        2. Place/Universe resolution
        3. Official Platform stats (Playing, Visits, Updated)
        4. High-Res Thumbnail
        5. Badges Roadmap
        """
        canonical_name = self.normalize_game_name(query_or_name)
        pid = place_id

        # If place_id is not given or is 0, attempt to search
        uid = None
        if pid and str(pid) != "0":
            uid = await self.resolve_place_to_universe(pid)

        # Fetch details
        univ_data = {}
        if uid:
            univ_data = await self.get_universe_details(uid) or {}

        icon_url = ""
        badges = []
        if uid:
            icon_url = await self.get_game_thumbnail(uid)
            badges = await self.get_game_badges_roadmap(uid, limit=12)

        return {
            "query": query_or_name,
            "canonical_name": canonical_name,
            "place_id": str(pid or "0"),
            "universe_id": uid,
            "name": univ_data.get("name") or canonical_name,
            "description": univ_data.get("description") or "",
            "playing": univ_data.get("playing", 0),
            "visits": univ_data.get("visits", 0),
            "updated": univ_data.get("updated") or "",
            "genre": univ_data.get("genre") or "Adventure",
            "icon_url": icon_url,
            "badges_roadmap": badges
        }

    def generate_safe_server_hop_snippet(self, place_id: str | int = "0") -> str:
        """
        Generates robust Luau Server-Hop logic:
        Hops to lowest-player server to avoid reports, and auto-reconnects on kick.
        """
        return f"""-- [[ PAYOMBØYZ ULTRA-SAFE SERVER HOP & ANTI-REPORT MODULE ]]
local TeleportService = game:GetService("TeleportService")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer

local function HopToLowestPlayerServer()
    local targetPlace = {place_id if str(place_id) != "0" else "game.PlaceId"}
    local success, response = pcall(function()
        return game:HttpGet("https://games.roblox.com/v1/games/" .. tostring(targetPlace) .. "/servers/0?sortOrder=Asc&limit=100")
    end)
    if success and response then
        local data = HttpService:JSONDecode(response)
        if data and data.data then
            for _, server in ipairs(data.data) do
                if server.id ~= game.JobId and server.playing and server.playing < server.maxPlayers and server.playing > 0 then
                    TeleportService:TeleportToPlaceInstance(targetPlace, server.id, LocalPlayer)
                    return true
                end
            end
        end
    end
    TeleportService:Teleport(targetPlace, LocalPlayer)
end

-- Auto-Rejoin on 20-minute idle disconnect
local GuiService = game:GetService("GuiService")
GuiService.ErrorMessageChanged:Connect(function()
    task.wait(2)
    HopToLowestPlayerServer()
end)
"""

ROBLOX_INTEL = RobloxPlatformIntel()
