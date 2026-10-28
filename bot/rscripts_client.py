#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ RSCRIPTS.NET REVERSE INTELLIGENCE HARVESTER V1.0
====================================================================
Programmatic API Client & Autonomous Script Harvester:
  - Queries api.rscripts.net/v1 for fresh Roblox game scripts
  - Vector search by Game Name or Place ID
  - Recursive Loadstring Resolver (drills into GitHub/Pastebin targets)
  - Anti-Scrape fallback headers
====================================================================
"""

import os
import re
import json
import time
import asyncio
import urllib.parse
from typing import Dict, Any, List, Optional
import aiohttp

BASE_API_URL = "https://api.rscripts.net/v1"
HEADERS_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

class RscriptsClient:
    """
    Client for rscripts.net REST API + Autonomous script resolver.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RSCRIPTS_API_KEY", "")
        self.session_timeout = aiohttp.ClientTimeout(total=20)

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": HEADERS_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-Api-Key"] = self.api_key
        return headers

    async def search_scripts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Searches scripts on rscripts.net by query string.
        """
        clean_q = query.strip()
        if not clean_q:
            return []

        encoded_q = urllib.parse.quote(clean_q)
        url = f"{BASE_API_URL}/search?q={encoded_q}&index=scripts&limit={limit}"

        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(url, headers=self._get_headers()) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        scripts = data.get("data", {}).get("scripts") or data.get("data") or []
                        if isinstance(scripts, list):
                            return scripts[:limit]
                    elif resp.status == 403 or resp.status == 401:
                        # Fallback to direct public search or placeId filter
                        print(f"[RSCRIPTS] API auth required ({resp.status}). Attempting public query...", flush=True)
                        return await self._fallback_public_search(clean_q, limit)
                    else:
                        print(f"[RSCRIPTS] Search failed with status {resp.status}", flush=True)
        except Exception as e:
            print(f"[RSCRIPTS] Network exception during search: {e}", flush=True)
            return await self._fallback_public_search(clean_q, limit)

        return []

    async def get_scripts_by_place(self, place_id: str | int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves scripts strictly associated with a specific Roblox Place ID.
        """
        url = f"{BASE_API_URL}/scripts?placeId={place_id}&limit={limit}&verified=true"
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(url, headers=self._get_headers()) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get("data") or []
                        if isinstance(items, list):
                            return items[:limit]
                    else:
                        print(f"[RSCRIPTS] Place search {place_id} returned {resp.status}", flush=True)
        except Exception as e:
            print(f"[RSCRIPTS] Exception querying placeId {place_id}: {e}", flush=True)

        return []

    async def _fallback_public_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Scrapes or searches open public script repositories when API key is unconfigured.
        Queries secondary open endpoints (e.g. ScriptBlox / open public aggregators).
        """
        try:
            encoded_q = urllib.parse.quote(query)
            # ScriptBlox Public Mirror API (Open, no key required)
            sb_url = f"https://scriptblox.com/api/script/search?q={encoded_q}&max={limit}"
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(sb_url, headers={"User-Agent": HEADERS_USER_AGENT}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data.get("result", {})
                        scripts = result.get("scripts", [])
                        converted = []
                        for s in scripts:
                            converted.append({
                                "id": s.get("_id") or s.get("slug"),
                                "title": s.get("title") or s.get("game", {}).get("name", "Unknown"),
                                "rawScript": s.get("script") or "",
                                "script": s.get("script") or "",
                                "views": s.get("views", 0),
                                "verified": s.get("verified", False),
                                "game": s.get("game", {}).get("name", query)
                            })
                        if converted:
                            print(f"[RSCRIPTS] Public mirror retrieved {len(converted)} candidate scripts for '{query}'.", flush=True)
                            return converted
        except Exception as e:
            print(f"[RSCRIPTS] Fallback search error: {e}", flush=True)
        return []

    async def resolve_raw_code(self, script_obj: Dict[str, Any]) -> str:
        """
        Extracts raw Lua code from a script record.
        If the script is a loader with `game:HttpGet(...)` or `loadstring(...)`,
        recursively downloads the referenced payload to reach the REAL implementation!
        """
        code = script_obj.get("rawScript") or script_obj.get("script") or ""
        if not code and script_obj.get("id"):
            # Fetch script detail
            code = await self._fetch_script_detail_code(str(script_obj["id"]))

        if not code:
            return ""

        # Recursive Loadstring Resolver
        resolved = await self._drill_loadstring(code)
        return resolved or code

    async def _fetch_script_detail_code(self, script_id: str) -> str:
        url = f"{BASE_API_URL}/scripts/{script_id}?includeScript=true"
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(url, headers=self._get_headers()) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        item = data.get("data") or {}
                        return item.get("rawScript") or item.get("script") or ""
        except Exception:
            pass
        return ""

    async def _drill_loadstring(self, code: str, depth: int = 0) -> str:
        """
        Extracts URLs from loadstring(game:HttpGet("...")) and fetches actual Lua source.
        Supports github raw, pastebin, key-system bypass (Linkvertise, Lootlabs, Work.ink), etc.
        """
        if depth > 4:
            return code

        from bot.bypass_engine import BYPASS_ENGINE

        # Regex for common loadstring patterns
        url_match = re.search(r'(?:HttpGet|HttpGetAsync|fetch|request)\s*\(\s*["\'](https?://[^"\']+)["\']', code, re.IGNORECASE)
        if not url_match:
            url_match = re.search(r'loadstring\s*\(\s*game:HttpGet\s*\(\s*["\'](https?://[^"\']+)["\']', code, re.IGNORECASE)
        if not url_match:
            # Check standalone raw URLs
            raw_url_match = re.search(r'["\'](https?://(?:raw\.githubusercontent|pastebin|scriptblox|github\.com)[^"\']+)["\']', code, re.IGNORECASE)
            if raw_url_match:
                url_match = raw_url_match

        if url_match:
            target_url = url_match.group(1).strip()
            
            # 1. Automatic Key System & Link Shortener Bypass
            if BYPASS_ENGINE.is_bypassable_url(target_url):
                print(f"[RSCRIPTS] Key-System / Gateway detected: {target_url}. Invoking BypassEngine...", flush=True)
                bypassed = BYPASS_ENGINE.bypass_url(target_url)
                if bypassed and bypassed != target_url:
                    target_url = bypassed
                    print(f"[RSCRIPTS] Bypassed destination resolved: {target_url}", flush=True)

            # Normalize github blob to raw
            if "github.com" in target_url and "/raw/" not in target_url and "/blob/" in target_url:
                target_url = target_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            elif "pastebin.com" in target_url and "/raw/" not in target_url:
                target_url = target_url.replace("pastebin.com/", "pastebin.com/raw/")

            print(f"[RSCRIPTS] Drilling into nested loader URL: {target_url} (depth={depth})...", flush=True)
            try:
                async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                    async with session.get(target_url, headers={"User-Agent": HEADERS_USER_AGENT}) as resp:
                        if resp.status == 200:
                            nested_code = await resp.text()
                            if len(nested_code.strip()) > 50:
                                return await self._drill_loadstring(nested_code, depth + 1)
            except Exception as e:
                print(f"[RSCRIPTS] Failed to fetch nested script from {target_url}: {e}", flush=True)

        return code

    async def harvest_game_scripts(self, query: str, place_id: Optional[str | int] = None) -> List[Dict[str, Any]]:
        """
        Main pipeline interface: Retrieves top scripts, resolves raw payloads into memory,
        and automatically deobfuscates protected chunks if obfuscation is detected.
        """
        candidates = []
        if place_id and str(place_id) != "0":
            candidates = await self.get_scripts_by_place(place_id, limit=3)

        if not candidates:
            candidates = await self.search_scripts(query, limit=3)

        results = []
        for item in candidates:
            raw_code = await self.resolve_raw_code(item)
            if raw_code and len(raw_code.strip()) > 100:
                # Automatic Deobfuscation pass if payload is obfuscated
                try:
                    from universal_deobfuscator import classify_target, UniversalDeobfuscatorPipeline
                    target_type = classify_target(raw_code.encode("utf-8", errors="ignore"), Path("temp.lua"))
                    if target_type not in ("PLAIN", "NOVEL_UNKNOWN"):
                        print(f"[RSCRIPTS] Harvested script '{item.get('title')}' is obfuscated ({target_type}). Deobfuscating...", flush=True)
                        import tempfile
                        with tempfile.NamedTemporaryFile("w", suffix=".lua", encoding="utf-8", delete=False) as tf:
                            tf.write(raw_code)
                            tf_path = Path(tf.name)
                        try:
                            deobf_res = UniversalDeobfuscatorPipeline().deobfuscate_file(tf_path)
                            if deobf_res.get("success") and deobf_res.get("clean_code") and len(deobf_res["clean_code"]) > 200:
                                print(f"[RSCRIPTS] Deobfuscation successful! Recovered {len(deobf_res['clean_code'])} chars clean source.", flush=True)
                                raw_code = deobf_res["clean_code"]
                        finally:
                            if tf_path.exists():
                                tf_path.unlink(missing_ok=True)
                except Exception as d_err:
                    print(f"[RSCRIPTS] Deobfuscation pass skipped: {d_err}", flush=True)

                results.append({
                    "title": item.get("title") or query,
                    "code": raw_code,
                    "length": len(raw_code),
                    "id": item.get("id")
                })

        return results

RSCRIPTS = RscriptsClient()
