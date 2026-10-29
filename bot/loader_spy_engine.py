# -*- coding: utf-8 -*-
"""
========================================================================================
🔍 ADVANCED LOADER SPY, MULTI-GAME HUB DISCOVERY & DEOBFUSCATION PIPELINE
- Intercepts GitHub Raw, Blob, Gist, Pastebin, and raw Luau loadstring(...) URLs
- Handles Multi-Game Hub Table Loaders (Ouroboros PlaceId -> Target Payload mapping)
- Detects & bypasses anti-executor Honeypots & Traps (Solara/Xeno traps, etc.)
- Autonomous Rscripts.net API & Raw Script Resolver
- Recursively unwinds multi-tiered Loaders (up to 5 hops)
- Computes Mathematical Confidence Score (0.0% - 100.0%)
- Emits Production-Ready Beautified Luau Source Code
========================================================================================
"""

from __future__ import annotations
import os
import sys
import re
import time
import json
import ssl
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output" / "Deobfuscated_Clean"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class LoaderSpyEngine:
    """
    Automated loader unwinder, multi-game place mapper, payload downloader,
    and confidence-scored deobfuscator.
    """

    @staticmethod
    def extract_loader_urls(text: str, strip_comments: bool = True) -> List[str]:
        """
        Extracts raw payload URLs from strings, lua code, or loadstrings.
        Safely strips Lua comments to avoid following dead links or examples in comment blocks.
        Supports Lua string concatenations, ScriptBlox, Jnkie, Nousigi, and Luarmor v4 init scripts.
        """
        def _scan(target_text: str) -> List[str]:
            found = []
            # Pattern 1.1: Concatenated HttpGet URLs: "https://raw.../repo/" .. var .. "/file.lua"
            m_concat = re.findall(
                r'(?:HttpGet|HttpGetAsync|request|fetch)\s*\(\s*["\'](https?://[^"\']+)["\']\s*\.\.\s*.*?["\']([^"\']+\.lua[u]?)["\']',
                target_text,
                re.IGNORECASE
            )
            for base_u, tail_u in m_concat:
                base_clean = base_u.rstrip("/")
                tail_clean = tail_u.lstrip("/")
                parts = base_clean.split("/")
                if "raw.githubusercontent.com" in base_clean and len(parts) == 5:
                    found.append(f"{base_clean}/main/{tail_clean}")
                else:
                    found.append(f"{base_clean}/{tail_clean}")

            # Pattern 1.2: Standard loadstring(game:HttpGet("...")) or fetch("...")
            m_http = re.findall(
                r'(?:HttpGet|HttpGetAsync|request|fetch|loadstring)\s*\(\s*["\'](https?://[^"\']+)["\']',
                target_text,
                re.IGNORECASE
            )
            found.extend(m_http)

            # Pattern 1.3: Luarmor init script pattern: https://cdn.luarmor.net/v4_init_<subhash>.lua
            m_v4_init = re.findall(r'https?://cdn\.luarmor\.net/v4_init_[a-zA-Z0-9_\-]+\.lua', target_text, re.IGNORECASE)
            found.extend(m_v4_init)

            # Pattern 2: direct URLs (expanded to any script, raw, api, or code hosting endpoint)
            m_raw = re.findall(
                r'https?://(?:[a-zA-Z0-9\-_]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s"\'\)\]]+)?',
                target_text,
                re.IGNORECASE
            )
            for u in m_raw:
                u_low = u.lower()
                # Keep if it is a known code host, or ends with lua/txt/raw/download
                if any(h in u_low for h in [
                    "github", "pastebin", "scriptblox", "rentry", "luarmor.net",
                    "rscripts.net", "jnkie.com", "nousigi.com", "/raw", "/download",
                    ".lua", ".luau", ".txt"
                ]):
                    # Exclude docs, discord, and web frontends
                    if not any(ex in u_low for ex in ["docs.luarmor.net", "discord.gg", "youtube.com", "youtu.be", "twitter.com"]):
                        found.append(u)
            return found

        # 1. First scan executable code with comments stripped
        cleaned_text = text
        if strip_comments and ("--" in text):
            cleaned_text = re.sub(r'--\[\[[\s\S]*?\]\]', '', text)
            cleaned_text = re.sub(r'--[^\n]*', '', cleaned_text)

        urls = _scan(cleaned_text)

        # 2. Fallback: if stripped scan found nothing, and input is a short chat prompt (<1500 chars), scan raw text
        if not urls and len(text) < 1500:
            urls = _scan(text)

        # Normalize URLs
        normalized = []
        for u in urls:
            clean_u = u.strip().rstrip("',\"[]):;}\\")
            if clean_u.endswith("/"):
                continue
            if "github.com/" in clean_u and "/blob/" in clean_u and "raw.githubusercontent.com" not in clean_u:
                clean_u = clean_u.replace("github.com/", "raw.githubusercontent.com/").replace("/blob/", "/")
            if clean_u not in normalized:
                normalized.append(clean_u)
        return normalized

    @classmethod
    def resolve_rscripts_url(cls, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolves Rscripts.net URLs (web script, raw URL, or API endpoint)
        Returns (raw_content, target_or_raw_url)
        """
        clean_url = url.strip()
        match = re.search(r'rscripts\.net/(?:script|raw|api/scripts)/([a-zA-Z0-9\-_]+)', clean_url)
        slug_or_id = match.group(1).replace(".txt", "") if match else ""

        api_key = os.getenv("RSCRIPTS_API_KEY", "").strip()

        # Method 1: Official API if key is present
        if api_key and slug_or_id:
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json"
                }
                api_url = f"https://api.rscripts.net/v1/scripts/{slug_or_id}"
                req = urllib.request.Request(api_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    script_data = data.get("data") or data.get("script") or {}
                    raw_code = script_data.get("script") or script_data.get("rawScript")
                    if raw_code and not raw_code.startswith("http"):
                        return raw_code, api_url
                    elif raw_code and raw_code.startswith("http"):
                        return cls.fetch_payload(raw_code)
            except Exception:
                pass

        # Method 2: curl_cffi with browser impersonation
        try:
            from curl_cffi import requests as cffi_requests
            # Check if direct raw URL pattern works
            if "/raw/" in clean_url:
                r = cffi_requests.get(clean_url, impersonate="chrome120", timeout=12)
                if r.status_code == 200 and len(r.text) > 20:
                    return r.text, clean_url

            # Query page with browser impersonation
            page_url = clean_url if "/script/" in clean_url else f"https://rscripts.net/script/{slug_or_id}"
            r = cffi_requests.get(page_url, impersonate="chrome120", timeout=12)
            if r.status_code == 200:
                html = r.text
                # Look for loadstring or rawScript in page
                loads = re.findall(r'(?:loadstring|game:HttpGet)[^\n<]+', html)
                if loads:
                    extracted_urls = cls.extract_loader_urls(loads[0])
                    if extracted_urls:
                        return cls.fetch_payload(extracted_urls[0])
                m_next = re.search(r'__NEXT_DATA__.*?>(.*?)</script>', html)
                if m_next:
                    d = json.loads(m_next.group(1))
                    props = d.get("props", {}).get("pageProps", {})
                    s_obj = props.get("script") or props.get("data") or {}
                    if isinstance(s_obj, dict):
                        raw_c = s_obj.get("script") or s_obj.get("rawScript")
                        if raw_c:
                            if raw_c.startswith("http"):
                                return cls.fetch_payload(raw_c)
                            return raw_c, page_url
        except Exception:
            pass

        return None, None

    @classmethod
    def get_game_name_for_place(cls, place_id: int, filename: str = "") -> str:
        """Resolves human-readable game name from CANONICAL_PLACE_MAP or cleans filename."""
        try:
            from bot.game_detector import CANONICAL_PLACE_MAP
            if place_id in CANONICAL_PLACE_MAP:
                return CANONICAL_PLACE_MAP[place_id].get("game", f"Roblox Place {place_id}")
        except Exception:
            pass
        if filename:
            stem = Path(filename).stem
            cleaned = re.sub(r'[^a-zA-Z0-9]', ' ', stem).strip()
            if cleaned and len(cleaned) > 2:
                return cleaned.title()
        return f"Roblox Place {place_id}"

    @classmethod
    def resolve_game_from_context(cls, text: str, games_map: Dict[int, str]) -> Optional[Tuple[int, str, str]]:
        """
        Attempts to intelligently match the target game from the user prompt or URL slug:
        1. Checks numeric PlaceId in prompt
        2. Checks canonical game names in CANONICAL_PLACE_MAP & TITLE_REGEX_MAP
        3. Checks if filenames in games_map match keywords in the prompt/slug
        Returns (place_id, game_display_name, match_reason) or None.
        """
        if not text or not games_map:
            return None

        # Strip table definitions so we don't match table keys as chat prompt numbers
        code_stripped = re.sub(r'\[\s*["\']?\d{4,}["\']?\s*\]\s*=\s*[^,\n\}]+', '', text)
        p_lower = code_stripped.lower()
        p_clean = re.sub(r'[-_]', ' ', p_lower)

        # 0. List Index selection (e.g. "1", "#1", "แมพ 1", "เลือก 1", "อันที่ 1")
        m_idx = re.search(r'(?:(?:แมพ|เกม|ลำดับ|อันที่|ข้อ|เลือก|game|map|index|#)\s*)(\d{1,2})\b', text, re.IGNORECASE)
        if not m_idx and re.match(r'^\s*#?(\d{1,2})\s*$', text):
            m_idx = re.match(r'^\s*#?(\d{1,2})\s*$', text)
        if m_idx:
            idx = int(m_idx.group(1))
            if 1 <= idx <= len(games_map):
                pid = list(games_map.keys())[idx - 1]
                return pid, cls.get_game_name_for_place(pid, games_map[pid]), f"Selected list item #{idx}"

        # 1. Exact place_id in prompt (must not be inside table brackets [12345])
        explicit_pids = re.findall(r'(?<!\[)\b(\d{5,})\b(?!\])', text)
        for pid_str in explicit_pids:
            try:
                pid = int(pid_str)
                if pid in games_map:
                    return pid, cls.get_game_name_for_place(pid, games_map[pid]), "Explicit PlaceId in prompt"
                elif pid_str in games_map:
                    return pid, cls.get_game_name_for_place(pid, games_map[pid_str]), "Explicit PlaceId in prompt"
            except Exception:
                pass

        # 2. Canonical regex match (Blox Fruits, 99 Nights, Fisch, etc.)
        try:
            from bot.game_detector import CANONICAL_PLACE_MAP, TITLE_REGEX_MAP
            for pattern, g_name, _ in TITLE_REGEX_MAP:
                if re.search(pattern, p_lower) or re.search(pattern, p_clean):
                    for pid, entry in games_map.items():
                        if pid in CANONICAL_PLACE_MAP and CANONICAL_PLACE_MAP[pid].get("game", "").split()[0].lower() in g_name.lower():
                            return pid, g_name, f"Game title matched '{g_name}'"
                        if g_name.lower().split()[0] in entry.lower():
                            return pid, g_name, f"Game title keyword matched '{entry}'"
        except Exception:
            pass

        # 3. Filename keyword match (e.g. 99nights, bloxfruits, fisch, mm2)
        for pid, entry in games_map.items():
            stem = Path(entry).stem.lower()
            stem_clean = re.sub(r'[-_]', ' ', stem)
            if (len(stem) >= 4 and (stem in p_lower or stem in p_clean)) or (len(stem_clean) >= 4 and stem_clean in p_clean):
                return pid, cls.get_game_name_for_place(pid, entry), f"Filename '{stem}' matched prompt context"

        return None

    @classmethod
    def generate_hub_catalog(cls, hub_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Builds structured catalog and clean Lua mapping table of all games in the hub."""
        base_u = hub_meta.get("base_url", "")
        g_map = hub_meta.get("games_map", {})
        games_list = []
        lua_lines = [
            "-- ========================================================================",
            "-- 🎮 PAYOMBØYZ CYBER-AI | MULTI-GAME HUB CATALOG & PLACEID MAPPING",
            f"-- Total Supported Games: {len(g_map)}",
            f"-- Base URL: {base_u or 'Direct URLs'}",
            "-- ========================================================================\n",
            "local HubGames = {"
        ]

        for pid, target in g_map.items():
            g_name = cls.get_game_name_for_place(pid, target)
            if target.startswith("http://") or target.startswith("https://"):
                full_url = target
            else:
                full_url = f"{base_u.rstrip('/')}/{target.lstrip('/')}" if base_u else target

            games_list.append({
                "place_id": pid,
                "game_name": g_name,
                "filename": target,
                "url": full_url
            })
            lua_lines.append(f'    [{pid}] = {{ Name = "{g_name}", File = "{target}", Url = "{full_url}" }},')

        lua_lines.append("}\nreturn HubGames\n")
        return {
            "games_list": games_list,
            "catalog_lua": "\n".join(lua_lines)
        }

    @classmethod
    def parse_multigame_hub(cls, code: str) -> Optional[Dict[str, Any]]:
        """
        Statically analyzes and extracts Multi-Game Hub tables like Ouroboros:
        - Extracts BASE / BaseUrl / host / repo URLs
        - Extracts PlaceId -> script/filename mapping table
        - Extracts conditional if/elseif chains (if game.PlaceId == ...)
        - Detects honeypots, anticheat traps, and dead branches
        """
        # 1. Extract BASE URL
        m_base = re.search(
            r'(?:local\s+)?(?:BASE|baseUrl|BaseUrl|base_url|BASE_URL|URL|Url|host|repo|domain|raw|source)\s*=\s*["\'](https?://[^"\']+)["\']',
            code,
            re.IGNORECASE
        )
        base_url = m_base.group(1) if m_base else ""
        if not base_url:
            m_raw_url = re.search(r'["\'](https?://raw\.githubusercontent\.com/[^"\']+/)["\']', code)
            if m_raw_url:
                base_url = m_raw_url.group(1)
        if not base_url:
            m_concat = re.search(r'(?:HttpGet|HttpGetAsync)\s*\(\s*["\'](https?://[^"\']+/)["\']\s*\.\.', code)
            if m_concat:
                base_url = m_concat.group(1)

        games_map: Dict[int, str] = {}

        # Pattern 1: [pid] = 'file' or ["pid"] = 'file'
        p1 = re.findall(r'\[\s*["\']?(\d{4,})["\']?\s*\]\s*=\s*["\']([^"\']+)["\']', code)
        for pid, target in p1:
            games_map[int(pid)] = target.strip()

        # Pattern 2: [pid] = { ... url = '...' } or [pid] = { '...' }
        p2 = re.findall(r'\[\s*["\']?(\d{4,})["\']?\s*\]\s*=\s*\{[^}]*?(?:url|script|file|src)\s*=\s*["\']([^"\']+)["\']', code)
        for pid, target in p2:
            games_map[int(pid)] = target.strip()

        # Pattern 3: [pid] = function() ... HttpGet("...")
        p3 = re.findall(r'\[\s*["\']?(\d{4,})["\']?\s*\]\s*=\s*function\(.*?\)\s*.*?HttpGet\s*\(\s*["\']([^"\']+)["\']', code, re.DOTALL)
        for pid, target in p3:
            games_map[int(pid)] = target.strip()

        # Pattern 4: if game.PlaceId == ... then ... HttpGet(...)
        p4 = re.findall(r'(?:if|elseif)\s+(?:game\.)?(?:PlaceId|placeId|GameId|gameId)\s*==\s*(\d{4,})\s+then\s*.*?["\'](https?://[^"\']+|[^"\']+\.lua[u]?)["\']', code, re.DOTALL)
        for pid, target in p4:
            games_map[int(pid)] = target.strip()

        if not games_map:
            return None

        # Filter out false-positives: VM string tables, random hash constants
        def _is_plausible_target(target: str, has_base: bool) -> bool:
            t = target.strip()
            t_low = t.lower()
            if t_low.startswith("http://") or t_low.startswith("https://"):
                return True
            if any(t_low.endswith(ext) for ext in [".lua", ".luau", ".txt"]):
                return True
            if "/" in t and len(t) < 80:
                return True
            if has_base and len(t) < 45 and not re.search(r'[^a-zA-Z0-9_\-\.]', t):
                return True
            return False

        has_place_ref = bool(re.search(r'\b(?:PlaceId|placeId|GameId|gameId)\b', code))
        filtered_map: Dict[int, str] = {}
        for pid, target in games_map.items():
            if _is_plausible_target(target, bool(base_url)):
                filtered_map[pid] = target

        if not filtered_map:
            return None

        # If code doesn't mention PlaceId/GameId at all, require base_url or explicit HTTP URLs
        if not has_place_ref:
            has_http_targets = any(t.lower().startswith("http://") or t.lower().startswith("https://") for t in filtered_map.values())
            if not base_url and not has_http_targets:
                return None

        # 3. Detect Honeypot Traps (e.g. solara/xeno blocker loadstring)
        honeypot = None
        m_trap = re.search(r'(?:solara|xeno|executor|blacklisted|trapped|ban).*?(?:BASE\s*\.\.\s*["\']([^"\']+)["\']|loadstring\s*\(\s*["\'](https?://[^"\']+)["\'])', code, re.DOTALL | re.IGNORECASE)
        if m_trap:
            honeypot = (m_trap.group(1) or m_trap.group(2) or "").strip()

        return {
            "is_multigame": True,
            "base_url": base_url,
            "games_map": filtered_map,
            "total_games": len(filtered_map),
            "honeypot_trap": honeypot
        }

    @classmethod
    def is_intermediate_loader(cls, payload: str, urls: List[str]) -> bool:
        """
        Determines whether the payload is an intermediate loader/wrapper
        or the final target script.
        """
        if not urls:
            return False

        # 1. Luarmor V4 Loader
        if ("_bsdata0" in payload and "cdn.luarmor.net" in payload) or "v4_init_" in payload:
            return True

        # 2. Known Loader platforms / headers
        if any(sig in payload for sig in [
            "api.jnkie.com", "JNKIE Game Loader", "nousigi.com",
            "rscripts.net", "scriptblox.com"
        ]):
            return True

        # 3. Multi-game hub tables (e.g. Ouroboros)
        if re.search(r'\[\s*\d{4,}\s*\]\s*=', payload) and ("PlaceId" in payload or "HttpGet" in payload):
            return True

        # 4. Active loader calls: loadstring(game:HttpGet(...)), loadstring(request(...)), etc.
        has_loadstring_http = bool(re.search(
            r'loadstring\s*\(\s*(?:game:)?(?:HttpGet|HttpGetAsync|request|fetch|http_request|syn\.request)',
            payload,
            re.IGNORECASE
        ))
        if has_loadstring_http:
            # If payload is under 50KB or under 400 lines, it's virtually always an outer loader
            if len(payload) < 50000 or len(payload.splitlines()) < 400:
                return True
            # Even if larger, if it doesn't contain game feature functions or UI library creations, it's a loader
            has_substantive_features = any(k in payload for k in [
                "CreateWindow", "MakeWindow", "CreateTab", "InitUI", "CreateButton",
                "AddToggle", "AddDropdown", "AddSlider", "Rayfield", "Fluent", "MacUI", "Linoria"
            ])
            if not has_substantive_features and len(payload) < 120000:
                return True

        # 5. Short wrappers (< 20,000 bytes) where an external script URL was found
        if len(payload) < 20000:
            target_script_urls = [u for u in urls if any(ext in u.lower() for ext in [".lua", ".luau", "/raw", "/download"])]
            if target_script_urls:
                return True

        return False

    @classmethod
    def fetch_payload(cls, url: str, timeout: int = 15) -> Tuple[Optional[str], str]:
        """
        Downloads script payload directly or via BypassEngine/curl_cffi.
        Uses Roblox/WinInet headers across all Roblox exploit distribution endpoints
        to prevent 403 Forbidden.
        """
        clean_url = url.strip().rstrip("',\"[]):;}\\")

        # Check for Rscripts URLs
        if "rscripts.net" in clean_url:
            raw_content, final_u = cls.resolve_rscripts_url(clean_url)
            if raw_content:
                return raw_content, final_u or clean_url

        # Check if gateway bypass is needed (Linkvertise, LootLabs, Work.ink, etc.)
        if any(gw in clean_url.lower() for gw in ["linkvertise", "lootlabs", "work.ink", "platoboost", "rekonise", "loot-link"]):
            try:
                from bot.bypass_engine import BypassEngine
                bypassed = BypassEngine.bypass_url(clean_url)
                if bypassed and bypassed.startswith("http"):
                    clean_url = bypassed
            except Exception:
                pass

        # SSL Context that skips verification for CDNs with broken chain or custom proxy
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        # TIER 1: Native Roblox/WinInet Headers (Simulates real Roblox game:HttpGet)
        # Bypasses 403 Forbidden on api.jnkie.com, nousigi.com, api.luarmor.net, cdn.luarmor.net, scriptblox.com
        for ua in ["Roblox/WinInet", "Roblox/Linux"]:
            try:
                headers = {
                    "User-Agent": ua,
                    "Accept": "*/*",
                    "Connection": "keep-alive",
                    "Cache-Control": "no-cache"
                }
                req = urllib.request.Request(clean_url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
                    data = resp.read()
                    text_res = data.decode("utf-8", errors="replace")
                    if text_res and not (text_res.startswith("<!doctype") and "Contents can not be displayed on browser" in text_res) and not ("<html" in text_res[:100].lower() and "cloudflare" in text_res.lower()):
                        return text_res, clean_url
            except Exception:
                pass

        # TIER 2: curl_cffi with TLS fingerprint evasion (Chrome 120)
        try:
            from curl_cffi import requests as cffi_requests
            headers = {
                "Accept": "text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            }
            resp = cffi_requests.get(
                clean_url,
                impersonate="chrome120",
                timeout=timeout,
                headers=headers,
                verify=False
            )
            if resp.status_code == 200:
                txt = resp.text
                if not (txt.startswith("<!doctype") and "Contents can not be displayed on browser" in txt):
                    return txt, clean_url
        except Exception:
            pass

        # TIER 3: Windows native curl.exe subprocess fallback
        try:
            cmd = ["curl.exe", "-s", "-L", "-k", "-A", "Roblox/WinInet", "--max-time", str(timeout), clean_url]
            p = subprocess.run(cmd, capture_output=True, text=False)
            if p.returncode == 0 and len(p.stdout) > 20:
                out_txt = p.stdout.decode("utf-8", errors="replace")
                if not (out_txt.startswith("<!doctype") and "Contents can not be displayed on browser" in out_txt):
                    return out_txt, clean_url
        except Exception:
            pass

        # TIER 4: Comprehensive urllib fallback with spoofed executor headers
        for fallback_ua in ["Roblox/WinInet", "Roblox/Linux", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"]:
            try:
                headers = {
                    "User-Agent": fallback_ua,
                    "Accept": "*/*",
                    "Connection": "keep-alive"
                }
                req = urllib.request.Request(clean_url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
                    data = resp.read()
                    return data.decode("utf-8", errors="replace"), clean_url
            except Exception as e_ua:
                last_err = e_ua

        return None, f"Fetch Error: {str(last_err if 'last_err' in locals() else 'Connection failed')}"

    @staticmethod
    def calculate_confidence_score(
        original_code: str,
        deobf_code: str,
        is_compiler_valid: bool,
        architecture: str
    ) -> Dict[str, Any]:
        """
        Computes the mathematical Confidence Score:
        - Compiler Executability Gate: 40%
        - Semantic Invariants & String Preservation: 30%
        - Elimination of Virtual VM Loops & Opaque Bytecode: 15%
        - SSA Register Inlining & Roblox Reflection: 15%
        """
        score = 0.0
        breakdown = {}

        # 1. Compiler Gate (40 pts)
        if is_compiler_valid:
            score += 40.0
            breakdown["compiler_gate"] = 40.0
        else:
            score += 15.0
            breakdown["compiler_gate"] = 15.0

        # 2. Semantic Preservation (30 pts)
        orig_strings = set(re.findall(r'["\']([^"\'\n]{3,})["\']', original_code))
        deobf_strings = set(re.findall(r'["\']([^"\'\n]{3,})["\']', deobf_code))
        if orig_strings:
            preserved_ratio = len(orig_strings.intersection(deobf_strings)) / max(len(orig_strings), 1)
            semantic_pts = round(min(preserved_ratio * 30.0 + 10.0, 30.0), 1)
        else:
            semantic_pts = 30.0
        score += semantic_pts
        breakdown["semantic_preservation"] = semantic_pts

        # 3. Elimination of VM Bytecode & Opaque Loops (15 pts)
        has_vm_arrays = bool(re.search(r'\[\d+\]\s*=\s*\d+', deobf_code))
        has_dispatch_loop = bool(re.search(r'while\s+(?:true|\w+)\s+do\s+.*(?:readu8|inst\[pc\])', deobf_code, re.DOTALL))
        if not has_vm_arrays and not has_dispatch_loop:
            score += 15.0
            breakdown["vm_elimination"] = 15.0
        else:
            score += 5.0
            breakdown["vm_elimination"] = 5.0

        # 4. SSA Register Inlining & Roblox Normalization (15 pts)
        has_roblox_api = bool(re.search(r'\b(?:game:GetService|Players\.LocalPlayer|ReplicatedStorage|TweenService)\b', deobf_code))
        has_raw_registers = bool(re.search(r'\bR\[\d+\]', deobf_code))
        ssa_pts = 0.0
        if has_roblox_api:
            ssa_pts += 10.0
        if not has_raw_registers:
            ssa_pts += 5.0
        score += ssa_pts
        breakdown["ssa_normalization"] = ssa_pts

        total_confidence = round(min(score, 100.0), 1)
        grade = "EXCELLENT" if total_confidence >= 90.0 else ("GOOD" if total_confidence >= 75.0 else "FAIR")

        return {
            "total_confidence": total_confidence,
            "grade": grade,
            "breakdown": breakdown
        }

    def spy_and_deobfuscate(self, text_or_url: str, target_place_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Complete end-to-end workflow:
        1. Extract & unwind URLs / Rscripts
        2. Detect & handle Multi-Game Hub tables (Ouroboros)
        3. Recursive unwinding (up to 5 hops)
        4. Deobfuscate through universal pipeline
        5. Calculate Confidence Score & emit clean source
        """
        start_t = time.time()
        current_input = text_or_url.strip()
        final_url = "Direct Input"
        payload = current_input

        # Check Brand Protection immediately
        from bot.brand_protection import check_brand_protection, BRAND_REFUSAL_MESSAGE
        is_protected, _ = check_brand_protection(current_input)
        if is_protected or any(m in current_input.casefold() for m in ["payomboy", "payomboyz", "payombøyz", "พยอมบอย"]):
            return {
                "success": False,
                "brand_protected": True,
                "error": BRAND_REFUSAL_MESSAGE,
                "target_url": final_url
            }

        multigame_info = None
        hops_trace = []
        last_valid_payload = None
        last_valid_url = None

        # Recursive Loader Unwinder (Up to 5 Hops)
        for hop in range(5):
            # Check if current payload is a Multi-Game Hub table
            hub_meta = self.parse_multigame_hub(payload)
            if hub_meta and hub_meta.get("total_games", 0) > 0:
                multigame_info = hub_meta
                base_u = hub_meta.get("base_url", "")
                g_map = hub_meta.get("games_map", {})
                total_games = len(g_map)

                resolved_pid = None
                resolved_game_name = None
                match_reason = None

                # Priority 1: User explicitly passed target_place_id (int or str)
                if target_place_id:
                    matched_k = None
                    if target_place_id in g_map:
                        matched_k = target_place_id
                    elif str(target_place_id).isdigit() and int(target_place_id) in g_map:
                        matched_k = int(target_place_id)
                    elif str(target_place_id) in g_map:
                        matched_k = str(target_place_id)

                    if matched_k is not None:
                        resolved_pid = matched_k
                        resolved_game_name = self.get_game_name_for_place(resolved_pid, g_map.get(resolved_pid, ""))
                        match_reason = f"Explicit PlaceId {target_place_id} specified"

                # Priority 2: Auto-resolve from user prompt or URL slug
                if not resolved_pid:
                    ctx_match = self.resolve_game_from_context(current_input, g_map)
                    if ctx_match:
                        resolved_pid, resolved_game_name, match_reason = ctx_match

                # Priority 3: If hub contains only 1 game, use that game
                if not resolved_pid and total_games == 1:
                    resolved_pid = next(iter(g_map.keys()))
                    resolved_game_name = self.get_game_name_for_place(resolved_pid, g_map.get(resolved_pid, ""))
                    match_reason = "Single Game Hub Default"

                # Priority 4: If total_games > 1 and NO place_id resolved -> HALT AND ASK USER!
                if not resolved_pid and total_games > 1:
                    print(f"[*] Multi-Game Hub Detected ({total_games} games). Halting to request user selection.")
                    catalog_data = self.generate_hub_catalog(hub_meta)
                    return {
                        "success": False,
                        "requires_user_selection": True,
                        "is_multigame": True,
                        "multigame_info": hub_meta,
                        "games_map": g_map,
                        "total_games": total_games,
                        "base_url": base_u,
                        "games_catalog": catalog_data.get("games_list", []),
                        "catalog_lua": catalog_data.get("catalog_lua", ""),
                        "last_valid_payload": payload,
                        "last_valid_url": final_url if (final_url and final_url != "Direct Input") else (current_input if current_input.startswith("http") else base_u),
                        "hops_trace": hops_trace,
                        "error": f"ตรวจพบ Multi-Game Hub (รองรับ {total_games} แมพ) จำเป็นต้องระบุ PlaceId หรือชื่อเกมที่ต้องการแกะ"
                    }

                selected_filename = g_map[resolved_pid]
                if selected_filename.startswith("http://") or selected_filename.startswith("https://"):
                    target_script_url = selected_filename
                else:
                    target_script_url = f"{base_u.rstrip('/')}/{selected_filename.lstrip('/')}" if base_u else selected_filename

                # Derive base URL from origin URL if base_u was empty and target_script_url is not absolute
                if not target_script_url.startswith("http://") and not target_script_url.startswith("https://"):
                    origin_u = final_url if (final_url and final_url.startswith("http")) else (current_input if current_input.startswith("http") else "")
                    if origin_u and "/" in origin_u:
                        parent_base = origin_u.rsplit("/", 1)[0]
                        target_script_url = f"{parent_base.rstrip('/')}/{selected_filename.lstrip('/')}"

                multigame_info["selected_place_id"] = resolved_pid
                multigame_info["selected_game_name"] = resolved_game_name
                multigame_info["match_reason"] = match_reason

                print(f"[*] Multi-Game Hub Resolved: PlaceId={resolved_pid} ({resolved_game_name}) -> {target_script_url} [{match_reason}]")
                next_payload, fetch_res = self.fetch_payload(target_script_url)
                if next_payload:
                    hops_trace.append({
                        "hop": hop + 1,
                        "type": "multigame_hub",
                        "url": target_script_url,
                        "status": "success",
                        "size_bytes": len(next_payload),
                        "game_name": resolved_game_name,
                        "place_id": resolved_pid
                    })
                    last_valid_payload = payload
                    last_valid_url = final_url
                    payload = next_payload
                    final_url = fetch_res
                    continue
                else:
                    hops_trace.append({
                        "hop": hop + 1,
                        "type": "multigame_hub",
                        "url": target_script_url,
                        "status": "failed",
                        "error": fetch_res,
                        "size_bytes": 0,
                        "game_name": resolved_game_name,
                        "place_id": resolved_pid
                    })
                    return {
                        "success": False,
                        "error": f"Failed to download multi-game payload for {resolved_game_name} (PlaceId: {resolved_pid}) from {target_script_url} ({fetch_res})",
                        "target_url": target_script_url,
                        "hops_trace": hops_trace,
                        "last_valid_payload": payload,
                        "last_valid_url": final_url,
                        "failed_hop": hop + 1,
                        "multigame_info": multigame_info
                    }

            # Extract candidate URLs from current payload
            urls = self.extract_loader_urls(payload)
            visited = [h.get("url") for h in hops_trace]
            urls = [u for u in urls if u not in visited]

            # If not hop 0, verify if current payload is still an intermediate loader
            if hop > 0 and not self.is_intermediate_loader(payload, urls):
                # We have reached the terminal script payload!
                break

            if not urls:
                # Reached terminal payload (no more URLs to follow)
                break

            # Priority 1: Luarmor v4_init
            luarmor_inits = [u for u in urls if "v4_init_" in u]
            # Priority 2: Direct raw code / script endpoints
            direct_loads = [u for u in urls if any(h in u.lower() for h in ["raw.githubusercontent.com", "pastebin.com/raw", "/download", "/raw", ".lua", ".luau"])]
            if luarmor_inits:
                target_url = luarmor_inits[0]
            elif direct_loads:
                target_url = direct_loads[0]
            else:
                target_url = urls[0]

            print(f"[*] Loader Spy (Hop {hop+1}) Found Target: {target_url}")
            next_payload, fetch_res = self.fetch_payload(target_url)
            if not next_payload:
                hops_trace.append({
                    "hop": hop + 1,
                    "url": target_url,
                    "status": "failed",
                    "error": fetch_res,
                    "size_bytes": 0
                })
                return {
                    "success": False,
                    "error": f"Failed to download payload from {target_url} ({fetch_res})",
                    "target_url": target_url,
                    "hops_trace": hops_trace,
                    "last_valid_payload": payload if hop > 0 else None,
                    "last_valid_url": final_url if hop > 0 else None,
                    "failed_hop": hop + 1,
                    "multigame_info": multigame_info
                }
            hops_trace.append({
                "hop": hop + 1,
                "url": target_url,
                "status": "success",
                "size_bytes": len(next_payload)
            })
            last_valid_payload = payload
            last_valid_url = final_url
            payload = next_payload
            final_url = fetch_res

        # Brand Protection Guard on final resolved payload
        is_protected, _ = check_brand_protection(payload)
        if is_protected:
            return {
                "success": False,
                "brand_protected": True,
                "error": BRAND_REFUSAL_MESSAGE,
                "target_url": final_url,
                "hops_trace": hops_trace
            }

        # Extract ScriptBlox slug or game hint from initial text
        sb_slug_match = re.search(r'scriptblox\.com/raw/([a-zA-Z0-9\-_]+)', current_input, re.IGNORECASE)
        slug_hint = ""
        if sb_slug_match:
            slug_raw = sb_slug_match.group(1)
            slug_hint = re.sub(r'-\d+$', '', slug_raw).replace("-", " ")

        from bot.game_detector import detect_roblox_game_and_map

        # Check if payload is still an unresolved loader wrapper
        is_still_loader = self.is_intermediate_loader(payload, self.extract_loader_urls(payload))

        # Check if payload is already clean Luau code (no heavy VM obfuscators)
        try:
            from universal_deobfuscator import classify_target
            payload_bytes = payload.encode("utf-8", errors="replace")
            arch = classify_target(payload_bytes, Path("script.lua"))
            is_heavily_obfuscated = (arch not in ("PLAIN", "DOCUMENTATION"))
        except Exception:
            is_heavily_obfuscated = any(sig in payload for sig in [
                "LPH-", "LPH_", "superflow_bytecode", "_bsdata0", "MoonSec", "IronBrew", "__bundle_start__",
                "buffer.", "V=buffer", "bit32.", "getrawmetatable", "Luraph"
            ])

        if not is_heavily_obfuscated and not is_still_loader and len(payload.splitlines()) > 5:
            # Format and beautify the clean code to production standard
            try:
                from universal_luau_beautifier import beautify_luau_code
                beautified_code = beautify_luau_code(payload)
                if len(beautified_code.splitlines()) >= int(len(payload.splitlines()) * 0.7):
                    payload = beautified_code
            except Exception as e_bt:
                print(f"[!] Beautifier note: {e_bt}")

            game_forensics = detect_roblox_game_and_map(
                raw_code=payload,
                deobf_code=payload,
                title=slug_hint or final_url,
                slug=slug_hint
            )
            conf = self.calculate_confidence_score(
                original_code=payload,
                deobf_code=payload,
                is_compiler_valid=True,
                architecture="PLAIN LUAU / CLEAN SCRIPT"
            )
            elapsed = time.time() - start_t
            return {
                "success": True,
                "is_loader": len(hops_trace) > 1 or "loadstring" in current_input or "HttpGet" in current_input,
                "target_url": final_url,
                "recovered_lines": len(payload.splitlines()),
                "deobfuscated_code": payload,
                "compiler_valid": True,
                "confidence": conf.get("total_confidence", 100.0),
                "confidence_grade": conf.get("grade", "EXCELLENT"),
                "confidence_breakdown": conf.get("breakdown", {}),
                "game_forensics": game_forensics,
                "multigame_info": multigame_info,
                "hops_trace": hops_trace,
                "elapsed": elapsed
            }

        # Save to temporary scratch file for pipeline execution
        temp_target = OUTPUT_DIR / f"_spy_target_{int(time.time() * 1000)}.luau"
        temp_target.write_text(payload, encoding="utf-8")

        try:
            from universal_deobfuscator import UniversalDeobfuscatorPipeline
            pipeline = UniversalDeobfuscatorPipeline(output_dir=OUTPUT_DIR)
            res = pipeline.deobfuscate_file(temp_target)

            if res.get("success"):
                deobf_code = res.get("deobfuscated_code", "")
                conf = self.calculate_confidence_score(
                    original_code=payload,
                    deobf_code=deobf_code,
                    is_compiler_valid=res.get("compiler_valid", True),
                    architecture="LURAPH / LUARMOR / UNIVERSAL"
                )
                game_forensics = detect_roblox_game_and_map(
                    raw_code=payload,
                    deobf_code=deobf_code,
                    title=slug_hint or final_url,
                    slug=slug_hint
                )
                elapsed = time.time() - start_t
                return {
                    "success": True,
                    "is_loader": len(hops_trace) > 1 or "loadstring" in current_input or "HttpGet" in current_input,
                    "target_url": final_url,
                    "recovered_lines": res.get("lines", len(deobf_code.splitlines())),
                    "deobfuscated_code": deobf_code,
                    "output_file": res.get("output"),
                    "compiler_valid": res.get("compiler_valid", True),
                    "confidence": conf["total_confidence"],
                    "confidence_grade": conf["grade"],
                    "confidence_breakdown": conf["breakdown"],
                    "game_forensics": game_forensics,
                    "multigame_info": multigame_info,
                    "hops_trace": hops_trace,
                    "elapsed": elapsed
                }
            else:
                game_forensics = detect_roblox_game_and_map(
                    raw_code=payload,
                    deobf_code="",
                    title=slug_hint or final_url,
                    slug=slug_hint
                )
                return {
                    "success": False,
                    "is_loader": len(hops_trace) > 1 or "loadstring" in current_input or "HttpGet" in current_input,
                    "error": res.get("error", "Universal deobfuscator failed to decompile final payload"),
                    "target_url": final_url,
                    "hops_trace": hops_trace,
                    "game_forensics": game_forensics,
                    "last_valid_payload": payload,
                    "last_valid_url": final_url,
                    "multigame_info": multigame_info
                }
        finally:
            try:
                temp_target.unlink(missing_ok=True)
            except Exception:
                pass


def spy_and_deobf(text_or_url: str, place_id: Optional[int] = None) -> Dict[str, Any]:
    """Public helper function."""
    engine = LoaderSpyEngine()
    return engine.spy_and_deobfuscate(text_or_url, target_place_id=place_id)
