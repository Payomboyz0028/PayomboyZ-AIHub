# -*- coding: utf-8 -*-
"""
==============================================================================
PAYOMBØYZ ROBLOX LIVE RESEARCH ENGINE V3.0
Autonomous Zero-Key Web Intelligence for Roblox Experiences & Events
Extracts game mechanics, active seasonal events, and place IDs.
Strictly scoped to Roblox to prevent irrelevant / external web noise.
==============================================================================
"""

import re
import time
import urllib.parse
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

# 24-hour in-memory cache to prevent redundant web queries
_RESEARCH_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 86400  # 24 hours

ROBLOX_TRUSTED_DOMAINS = [
    "roblox.com", "ro.blox.com", "roscripts.io", "scriptblox.com",
    "fischipedia.org", "bloxfruits.fandom.com", "robipedia.com", "rscripts.net"
]


class RobloxLiveResearcher:
    """
    Precision Game Research Harness strictly scoped to Roblox platform.
    Used internally to inform AI models about actual game mechanics and events.
    """

    @classmethod
    def _clean_game_query(cls, raw_name: str) -> str:
        """Strip filler Thai / English tokens from game title for clean query."""
        if not raw_name:
            return ""
        cleaned = re.sub(
            r'(?i)\b(roblox|script|lua|luau|auto\s*farm|autofarm|exploit)\b|แมพ|เกม|สคริปต์|สคริป|ขอ|หน่อย|ครับ|ค่ะ|ฟาร์ม|ฟาม',
            ' ',
            raw_name
        ).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned or raw_name.strip()

    @classmethod
    def _search_ddg(cls, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Search DuckDuckGo with zero API keys."""
        if not HAS_DDGS:
            return []
        try:
            ddg = DDGS(timeout=8)
            raw = list(ddg.text(query, max_results=max_results))
            results = []
            for r in raw:
                title = r.get("title", "")
                url = r.get("href", "")
                snippet = r.get("body", "")
                if url and (title or snippet):
                    results.append({"title": title, "url": url, "snippet": snippet})
            return results
        except Exception:
            return []

    @classmethod
    def _search_bing_cffi(cls, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Fallback Bing scraper using TLS Chrome impersonation."""
        url = "https://www.bing.com/search"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.bing.com/",
        }
        try:
            resp = cffi_requests.get(
                url,
                params={"q": query, "first": 1},
                headers=headers,
                impersonate="chrome120",
                timeout=10
            )
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for item in soup.select("li.b_algo")[:max_results]:
                title_node = item.select_one("h2 a")
                snippet_node = item.select_one(".b_caption p, .b_algoSlug")
                if title_node and title_node.get("href"):
                    link = title_node["href"]
                    if "bing.com/ck/a" in link and "&u=" in link:
                        try:
                            m_u = re.search(r'[?&]u=a1([a-zA-Z0-9_\-]+)', link)
                            if m_u:
                                import base64
                                padded = m_u.group(1) + "=="
                                decoded = base64.urlsafe_b64decode(padded).decode("utf-8", errors="ignore")
                                if decoded.startswith("http"):
                                    link = decoded
                        except Exception:
                            pass
                    results.append({
                        "title": title_node.get_text(strip=True),
                        "url": link,
                        "snippet": snippet_node.get_text(strip=True) if snippet_node else ""
                    })
            return results
        except Exception:
            return []

    @classmethod
    def research_roblox_game(cls, game_name: str, user_prompt: str = "") -> Dict[str, Any]:
        """
        Execute precision research strictly verifying Roblox context.
        Returns a structured knowledge dictionary about game mechanics and events.
        """
        clean_name = cls._clean_game_query(game_name)
        if not clean_name or len(clean_name) < 2:
            return {"is_roblox_verified": False, "game_name": game_name}

        cache_key = f"{clean_name.lower()}::{(user_prompt or '').lower()[:40]}"
        now = time.time()

        if cache_key in _RESEARCH_CACHE:
            cached = _RESEARCH_CACHE[cache_key]
            if now - cached.get("_cached_at", 0) < _CACHE_TTL:
                return cached

        # Check for event keywords in user prompt
        event_match = re.search(r'(ฮาโลวีน|halloween|กิจกรรม|event|คริสต์มาส|christmas|อัพเดท|update)', user_prompt, re.IGNORECASE)
        event_term = event_match.group(0) if event_match else ""

        # Strictly scope query to Roblox
        query_candidates = []
        if event_term:
            query_candidates.append(f'Roblox "{clean_name}" {event_term}')
        query_candidates.append(f'Roblox "{clean_name}" game')
        query_candidates.append(f'site:roblox.com/games "{clean_name}"')

        all_results: List[Dict[str, str]] = []
        for q in query_candidates:
            res = cls._search_ddg(q, max_results=3)
            if not res:
                res = cls._search_bing_cffi(q, max_results=3)
            all_results.extend(res)
            if len(all_results) >= 5:
                break

        # ----------------------------------------------------------------------
        # STRICT ROBLOX VERIFICATION GATE
        # ----------------------------------------------------------------------
        roblox_verified_entries = []
        extracted_place_id = None
        extracted_universe_id = None

        for item in all_results:
            title = item["title"]
            url = item["url"]
            snippet = item["snippet"]
            text_block = f"{title} {url} {snippet}".lower()

            is_trusted_domain = any(d in url.lower() for d in ROBLOX_TRUSTED_DOMAINS)
            is_game_url = bool(re.search(r'roblox\.com/(?:[a-zA-Z0-9_\-]+/)?games/(\d+)', url))
            
            # Proof of playable Roblox experience in text
            has_experience_proof = bool(re.search(r'\broblox\b.*?\b(game|experience|place|script|map|wiki|hub|simulator|rpg|ตกปลา|ฮาโลวีน|เด็กช่าง)\b', text_block))

            if not (is_game_url or is_trusted_domain or has_experience_proof):
                continue

            if is_game_url:
                m_place = re.search(r'roblox\.com/(?:[a-zA-Z0-9_\-]+/)?games/(\d+)', url)
                if m_place and not extracted_place_id:
                    extracted_place_id = m_place.group(1)

            m_univ = re.search(r'universeId=(\d+)', url)
            if m_univ and not extracted_universe_id:
                extracted_universe_id = m_univ.group(1)

            roblox_verified_entries.append(item)

        # If no verified Roblox entries found, return clean rejection
        if not roblox_verified_entries:
            neg_result = {
                "game_name": clean_name,
                "is_roblox_verified": False,
                "place_id": "0",
                "universe_id": None,
                "genre_tag": "Unknown",
                "has_active_event": False,
                "event_details": "",
                "constraints": [],
                "verified_snippets": [],
                "_cached_at": now
            }
            _RESEARCH_CACHE[cache_key] = neg_result
            return neg_result

        # Synthesize verified game intelligence
        combined_text = " ".join([f"{e['title']} {e['snippet']}" for e in roblox_verified_entries]).lower()
        combined_text += f" {user_prompt.lower()}"

        # Genre & Mechanic classification
        has_egg_or_pet = any(k in combined_text for k in ["egg", "pet", "ไข่", "สัตว์เลี้ยง", "hatch", "nest", "รัง", "ride a pet"])
        has_fishing = any(k in combined_text for k in ["fish", "rod", "bait", "ตกปลา", "เบ็ด", "fisch"])
        has_combat = any(k in combined_text for k in [
            "sword", "fight", "battle", "mob", "mobs", "boss", "pvp", "ตี", "ฟัน", "อาวุธ",
            "เด็กช่าง", "สถาบัน", "devil fruit", "fruit", "pirate", "marine", "combat"
        ])
        has_event = bool(event_term or any(k in combined_text for k in ["halloween", "ฮาโลวีน", "event", "กิจกรรม", "the hollow"]))

        if has_fishing:
            genre_tag = "Fishing Simulator"
            constraints = ["Focus on Rod, Cast, Shake, Reel, and Fish Selling mechanisms", "NO generic combat mobs"]
        elif has_egg_or_pet and not ("sword" in combined_text or "เด็กช่าง" in combined_text):
            genre_tag = "Pet & Egg Simulator (Non-combat)"
            constraints = ["NO combat mobs", "NO Humanoid.Health filtering", "Focus on Egg/Nest touch and Plot return"]
        elif has_combat:
            genre_tag = "Action / Combat RPG / Gang"
            constraints = ["Support Attack Remotes, Weapons, and Target Resolvers"]
        else:
            genre_tag = "Roblox Adventure"
            constraints = ["Universal movement and interaction"]

        # Build clean summary snippets for AI context
        snippets_list = []
        for e in roblox_verified_entries[:3]:
            snippets_list.append(f"• {e['title']}: {e['snippet']}")

        knowledge = {
            "game_name": clean_name,
            "is_roblox_verified": True,
            "place_id": extracted_place_id or "0",
            "universe_id": extracted_universe_id,
            "genre_tag": genre_tag,
            "has_active_event": has_event,
            "event_details": event_term if has_event else "",
            "constraints": constraints,
            "verified_snippets": snippets_list,
            "_cached_at": now
        }

        _RESEARCH_CACHE[cache_key] = knowledge
        return knowledge

    @classmethod
    def build_ai_context_block(cls, game_name: str, user_prompt: str = "") -> str:
        """
        Generate a concise, authoritative Ground Truth context block to inject into AI Prompts.
        Returns empty string if game cannot be verified as a Roblox experience.
        """
        intel = cls.research_roblox_game(game_name, user_prompt)
        if not intel.get("is_roblox_verified") or not intel.get("verified_snippets"):
            return ""

        lines = [
            f"[LIVE VERIFIED ROBLOX GROUND TRUTH: '{intel['game_name']}']",
            f"- Platform: Roblox (Verified: True)",
            f"- Identified Genre: {intel['genre_tag']}",
        ]
        if intel.get("place_id") and intel["place_id"] != "0":
            lines.append(f"- Discovered Place ID: {intel['place_id']}")
        if intel.get("has_active_event"):
            lines.append(f"- Active Event/Update: {intel['event_details']}")
        if intel.get("constraints"):
            lines.append(f"- Architectural Directives: {'; '.join(intel['constraints'])}")
        if intel.get("verified_snippets"):
            lines.append("- Verified Knowledge Snippets:")
            lines.extend(intel["verified_snippets"][:2])
        lines.append("[END ROBLOX GROUND TRUTH]\n")

        return "\n".join(lines)
