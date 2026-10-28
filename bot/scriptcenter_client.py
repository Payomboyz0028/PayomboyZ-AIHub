"""
ScriptCenter / Shop API Client for Discord Get-Role Bot
Connects to ScriptCenter REST API (https://payomboyz-hub.scriptcenter.online/api/discord)
Handles key verification, linking, expiry checking, HWID resets, and loaders.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger("ScriptCenterClient")

WORDS = {
    "th": {
        "link": "ผูกคีย์",
        "reset": "รี HWID",
        "license": "License Key",
        "noKeys": "ยังไม่มีคีย์ที่ผูกกับบัญชีนี้",
        "lifetime": "ตลอดชีพ",
        "firstRun": "เริ่มนับเมื่อรันครั้งแรก",
        "left": "คงเหลือ",
        "days": "วัน",
        "error": "เกิดข้อผิดพลาดในการเชื่อมต่อ",
        "success_link": "ผูกคีย์และมอบสิทธิ์สำเร็จเรียบร้อยแล้ว!",
        "success_reset": "รีเซ็ต HWID สำเร็จเรียบร้อยแล้ว!",
    },
    "en": {
        "link": "Link Key",
        "reset": "Reset HWID",
        "license": "License Key",
        "noKeys": "No keys linked to this account",
        "lifetime": "Lifetime",
        "firstRun": "starts on first run",
        "left": "left",
        "days": "day(s)",
        "error": "Something went wrong",
        "success_link": "Successfully linked key!",
        "success_reset": "Successfully reset HWID!",
    },
}


class ScriptCenterClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("SC_API_BASE", "https://payomboyz-hub.scriptcenter.online/api/discord")).rstrip("/")
        self.api_key = (api_key or os.environ.get("SC_API_KEY", "")).strip()
        self._session: Optional[aiohttp.ClientSession] = None
        self._panel_cache: Optional[Dict[str, Any]] = None
        self._cache_time: float = 0

    def update_config(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        if base_url:
            self.base_url = base_url.strip().rstrip("/")
        if api_key is not None:
            self.api_key = api_key.strip()
        self._panel_cache = None
        self._cache_time = 0

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and "…" not in self.api_key and "..." not in self.api_key)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15, connect=5)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def request(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make an authenticated request to the ScriptCenter API."""
        if not self.base_url:
            return {"ok": False, "message": "SC_API_BASE is not configured in .env"}
        if not self.api_key:
            return {"ok": False, "message": "SC_API_KEY is not configured in .env"}
        if "…" in self.api_key or "..." in self.api_key:
            return {
                "ok": False,
                "message": "SC_API_KEY contains a masked token (…)! Please provide the full unmasked API Key from ScriptCenter dashboard.",
            }

        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "PAYOMBOYZ-GetRoleBot/2.0",
        }

        session = await self._get_session()
        method = "POST" if body is not None else "GET"
        data_bytes = json.dumps(body).encode("utf-8") if body is not None else None

        try:
            async with session.request(method, url, headers=headers, data=data_bytes) as resp:
                status = resp.status
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    raw_text = await resp.text()
                    return {"ok": False, "status": status, "message": f"HTTP {status}: {raw_text[:200]}"}

                if not isinstance(data, dict):
                    return {"ok": False, "status": status, "message": f"Invalid API response format (HTTP {status})"}

                if not resp.ok and "message" not in data:
                    data["message"] = f"HTTP {status}"
                return data

        except asyncio.TimeoutError:
            return {"ok": False, "message": "เชื่อมต่อ ScriptCenter API หมดเวลา (Connection Timeout)"}
        except aiohttp.ClientConnectorError as e:
            return {"ok": False, "message": f"ไม่สามารถเชื่อมต่อ Server ได้: {e}"}
        except Exception as e:
            logger.error(f"ScriptCenter API Error: {type(e).__name__}: {e}")
            return {"ok": False, "message": f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}"}

    async def get_panel(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch shop panel information (name, description, logo, menu labels)."""
        import time
        now = time.time()
        if not force_refresh and self._panel_cache and (now - self._cache_time < 300):
            return {"ok": True, "panel": self._panel_cache}

        res = await self.request("panel")
        if res.get("ok") and "panel" in res:
            self._panel_cache = res["panel"]
            self._cache_time = now
            return res
        return res

    async def link_key(self, discord_user_id: str, discord_username: str, key: str) -> Dict[str, Any]:
        """
        Link a license key to a Discord user.
        POST /link-key
        body: { discord_user_id, discord_username, key }
        """
        payload = {
            "discord_user_id": str(discord_user_id),
            "discord_username": str(discord_username),
            "key": key.strip(),
        }
        return await self.request("link-key", payload)

    async def reset_hwid(self, discord_user_id: str, key: str) -> Dict[str, Any]:
        """
        Reset HWID for a given key owned by Discord user.
        POST /reset-hwid
        body: { discord_user_id, key }
        """
        payload = {
            "discord_user_id": str(discord_user_id),
            "key": key.strip(),
        }
        return await self.request("reset-hwid", payload)

    async def get_my_keys(self, discord_user_id: str) -> Dict[str, Any]:
        """
        Get list of keys owned by Discord user.
        POST /my-keys
        body: { discord_user_id }
        """
        payload = {"discord_user_id": str(discord_user_id)}
        return await self.request("my-keys", payload)

    async def check_expiry(self, discord_user_id: str) -> Dict[str, Any]:
        """
        Check key expiry information for Discord user.
        POST /check-expiry
        body: { discord_user_id }
        """
        payload = {"discord_user_id": str(discord_user_id)}
        return await self.request("check-expiry", payload)

    async def get_loader(self, discord_user_id: str) -> Dict[str, Any]:
        """
        Get Lua loader for Discord user.
        POST /get-loader
        body: { discord_user_id }
        """
        payload = {"discord_user_id": str(discord_user_id)}
        return await self.request("get-loader", payload)

    def format_expiry_text(self, keys: List[Dict[str, Any]], lang: str = "th") -> str:
        """Format the list of keys and expiry days into human readable markdown with custom emojis."""
        w = WORDS.get(lang, WORDS["th"])
        if not keys:
            return "<:pbg_wait:1551063140349780068> *ยังไม่มีคีย์ที่ผูกกับบัญชีนี้*"

        lines = []
        for k in keys:
            key_str = k.get("key", "Unknown")
            is_lifetime = k.get("isLifetime", False)
            first_use = k.get("firstUse", False)
            days = k.get("daysRemaining", 0)

            if is_lifetime:
                status = "<a:anime_fire:1551069928105447485> ⚡ **ตลอดชีพ (LIFETIME VIP)**"
            elif first_use:
                status = f"<:pbg_wait:1551063140349780068> ⏳ **คงเหลือ {days} วัน** *(เริ่มนับเมื่อรันครั้งแรก)*"
            else:
                status = f"<:pbg_chill:1551064392139804702> 🕒 คงเหลือ **{days} วัน**"

            lines.append(f"• `{key_str}` ➔ {status}")

        return "\n".join(lines)


# Global singleton instance
_sc_client: Optional[ScriptCenterClient] = None


def get_sc_client() -> ScriptCenterClient:
    global _sc_client
    if _sc_client is None:
        _sc_client = ScriptCenterClient()
    return _sc_client
