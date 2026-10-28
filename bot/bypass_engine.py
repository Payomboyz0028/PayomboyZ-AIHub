# ==============================================================================
# PAYOMBØYZ UNIVERSAL KEY SYSTEM & SHORTLINK BYPASS ENGINE
# Sourced & Integrated from Lerning/Bypass&slove (Evo-Bypass, Linkvertise, Lootlabs, PyBypass, UniversalBypass)
# ==============================================================================

import re
import time
import urllib.parse
from typing import Optional, Dict, Any
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

class BypassEngine:
    """
    Autonomous Bypasser for Roblox Script Loaders, Linkvertise, LootLabs,
    Work.ink, Rekonise, Platoboost, Sub2Get, and Nested Shortener Redirects.
    """
    TIMEOUT = 12

    @classmethod
    def is_bypassable_url(cls, url: str) -> bool:
        if not url:
            return False
        low = url.lower()
        return any(domain in low for domain in [
            "linkvertise.com", "linkvertise.download", "link-to.net", "link-target.net",
            "lootlabs.gg", "loot-link.com", "loot-links.com", "lootlink.org", "lootdest.org",
            "work.ink", "workink.net",
            "rekonise.com",
            "platoboost.com", "gateway.platoboost.com",
            "sub2get.com", "sub2unlock.com", "sub4unlock.com",
            "bit.ly", "tinyurl.com", "ouo.io", "ouo.press",
            "boost.ink", "social-unlock.com"
        ])

    @classmethod
    def bypass_url(cls, url: str) -> Optional[str]:
        """
        Attempts multi-tiered bypass on target shortlink / key gateway.
        Returns final destination URL or raw direct script link.
        """
        clean_url = url.strip()
        low = clean_url.lower()

        # 1. Linkvertise & Mirrors
        if any(d in low for d in ["linkvertise", "link-to", "link-target"]):
            res = cls.bypass_linkvertise(clean_url)
            if res:
                return res

        # 2. LootLabs
        if "loot" in low:
            res = cls.bypass_lootlabs(clean_url)
            if res:
                return res

        # 3. Work.ink
        if "work.ink" in low or "workink" in low:
            res = cls.bypass_workink(clean_url)
            if res:
                return res

        # 4. Rekonise
        if "rekonise" in low:
            res = cls.bypass_rekonise(clean_url)
            if res:
                return res

        # 5. Universal Redirect Follower
        return cls.unwind_redirects(clean_url)

    @classmethod
    def bypass_linkvertise(cls, url: str) -> Optional[str]:
        """Bypasses Linkvertise through public mirrors & direct parameter extraction."""
        # Check if destination is embedded in URL query parameters
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        for key in ["r", "url", "dest", "destination", "target"]:
            if key in params and params[key][0].startswith("http"):
                return params[key][0]

        # Tier 1: Bypass API (bypass.vip)
        try:
            resp = requests.post("https://api.bypass.vip/bypass", json={"url": url}, headers=HEADERS, timeout=cls.TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("destination"):
                    return data["destination"]
        except Exception:
            pass

        # Tier 2: Bypass API (bypass.bot.nu)
        try:
            resp = requests.get(f"https://bypass.bot.nu/bypass2?url={urllib.parse.quote(url)}", headers=HEADERS, timeout=cls.TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("destination"):
                    return data["destination"]
        except Exception:
            pass

        return cls.unwind_redirects(url)

    @classmethod
    def bypass_lootlabs(cls, url: str) -> Optional[str]:
        """Bypasses LootLabs via link ID resolution."""
        match = re.search(r'lootlabs\.gg/([a-zA-Z0-9]+)', url)
        if match:
            link_id = match.group(1)
            try:
                resp = requests.get(f"https://api.lootlabs.gg/api/get-link/{link_id}", headers=HEADERS, timeout=cls.TIMEOUT)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("url"):
                        return data["url"]
            except Exception:
                pass

        return cls.unwind_redirects(url)

    @classmethod
    def bypass_workink(cls, url: str) -> Optional[str]:
        """Bypasses Work.ink via HTTP location extraction."""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=cls.TIMEOUT, allow_redirects=False)
            if "location" in resp.headers:
                return resp.headers["location"]
            soup = BeautifulSoup(resp.text, "html.parser")
            link = soup.find("a", href=True)
            if link and link["href"].startswith("http") and "work.ink" not in link["href"]:
                return link["href"]
        except Exception:
            pass
        return cls.unwind_redirects(url)

    @classmethod
    def bypass_rekonise(cls, url: str) -> Optional[str]:
        """Bypasses Rekonise by scanning unlocked payload link in response."""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=cls.TIMEOUT)
            if resp.status_code == 200:
                match = re.search(r'url["\s:]+["\'](https?://[^"\']+)["\']', resp.text)
                if match:
                    return match.group(1)
        except Exception:
            pass
        return cls.unwind_redirects(url)

    @classmethod
    def unwind_redirects(cls, url: str, max_hops: int = 8) -> str:
        """Follows redirect chains to reveal the ultimate destination link."""
        curr = url
        try:
            session = requests.Session()
            session.headers.update(HEADERS)
            for _ in range(max_hops):
                resp = session.head(curr, allow_redirects=False, timeout=cls.TIMEOUT)
                if resp.status_code in (301, 302, 303, 307, 308) and "Location" in resp.headers:
                    curr = resp.headers["Location"]
                    if not curr.startswith("http"):
                        curr = urllib.parse.urljoin(url, curr)
                else:
                    break
        except Exception:
            pass
        return curr

BYPASS_ENGINE = BypassEngine()
