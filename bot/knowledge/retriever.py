#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ KNOWLEDGE BASE — TRI-LAYER CODE INTELLIGENCE RETRIEVER
====================================================================
Tri-Layer Knowledge Model:
  1. TEXT KNOWLEDGE   (Business, Pricing, Policies, FAQ, Terms)
  2. CODE KNOWLEDGE   (Functions, Remotes, Services, Bypass Patterns)
  3. UI KNOWLEDGE     (Components, Layouts, Methods, Gothic Typography)

Mathematical Ranking:
  FinalScore = Relevance * Quality * Recency * UsageFrequency

Returns targeted fragments only — NEVER dumps all 46 files.
====================================================================
"""

import re
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from .scoring import get_file_quality_score, calculate_recency_score, calculate_knowledge_score
from .epistemic import EpistemicAuditor, EpistemicStatus

KNOWLEDGE_DIR = Path(__file__).resolve().parent
BASE_DIR = KNOWLEDGE_DIR.parent.parent
RBX_DIR = BASE_DIR / "Script" / "rbx folder"
UI_DIR = RBX_DIR / "UI"


class KnowledgeRetriever:
    """Intelligent multi-tier retriever for PayomboyZ Knowledge Base."""

    def __init__(self):
        self.ui_catalog = self._load_json("ui_catalog.json")
        self.business_catalog = self._load_json("business_catalog.json")
        self.code_registry = self._load_json("code_registry.json")
        self.auditor = EpistemicAuditor(self.code_registry, self.ui_catalog)

    def _load_json(self, filename: str) -> Dict[str, Any]:
        p = KNOWLEDGE_DIR / filename
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    # -------------------------------------------------------------
    # Layer 1: Text Knowledge (Business / Pricing / Terms / FAQ)
    # -------------------------------------------------------------
    def retrieve_business_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Retrieves pricing, packages, policy, and shop URL context."""
        results = []
        q = query.lower()

        # Pricing query
        if any(w in q for w in ["ราคา", "price", "vip", "vvip", "บาท", "ซื้อ", "shop", "แพ็กเกจ", "package", "กี่บาท"]):
            vip = self.business_catalog.get("pricing", {}).get("vip_package", {})
            vvip = self.business_catalog.get("pricing", {}).get("vvip_package", {})
            urls = self.business_catalog.get("urls", {})

            # Calculate score
            score = calculate_knowledge_score(relevance=0.95, quality=1.00, recency=0.95)
            content = f"""[👑 PAYOMBØYZ HUB — PRICING & STORE ACCESS]
Score: {score:.3f}

• 🔱 VIP Package — {vip.get('price_thb', 89)} บาท (คีย์ 3 เดือน | มีระบบ Get Key ฟรี)
  แมพที่รองรับ ({len(vip.get('maps', []))} แมพ):
  - {', '.join(vip.get('maps', [])[:6])}
  - {', '.join(vip.get('maps', [])[6:])}

• 👑 VVIP Package — {vvip.get('price_thb', 129)} บาท (คีย์ 3 เดือน | เล่นแมพ VIP ได้ทั้งหมด)
  แมพเฉพาะ VVIP ({len(vvip.get('maps', []))} แมพ):
  - {', '.join(vvip.get('maps', []))}

• ร้านค้าหลัก: {urls.get('official_store', 'https://payomboyz.rexzy.xyz/')}
• รับคีย์ฟรี / สคริปต์ฟรี: {urls.get('free_key_portal', 'https://payomboyz333.github.io/Anime-Card-Farm/')} หรือห้อง '{urls.get('free_scripts_channel')}'
"""
            results.append({
                "layer": "TEXT_KNOWLEDGE",
                "topic": "Pricing & Packages",
                "score": score,
                "content": content
            })

        # Policy & Rules query
        if any(w in q for w in ["กฎ", "ข้อตกลง", "คืนเงิน", "แบน", "หารคีย์", "แชร์คีย์", "refund", "terms"]):
            policies = self.business_catalog.get("policies", [])
            score = calculate_knowledge_score(relevance=0.92, quality=1.00, recency=0.95)
            policy_text = "\n".join([f"• {p['topic']}: {p['rule']}" for p in policies])
            content = f"""[📕 PAYOMBØYZ HUB — RULES & POLICIES]
Score: {score:.3f}
{policy_text}
"""
            results.append({
                "layer": "TEXT_KNOWLEDGE",
                "topic": "Policies & Terms",
                "score": score,
                "content": content
            })

        return results

    # -------------------------------------------------------------
    # Layer 2: UI Knowledge (Components / Templates / Fonts)
    # -------------------------------------------------------------
    def retrieve_ui_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Retrieves exact UI component signatures, methods, and layout examples."""
        results = []
        q = query.lower()

        matched_components = []
        for name, comp in self.ui_catalog.items():
            # Match component name or relevant keywords
            if name.lower() in q or (comp.get("type", "").lower() in q):
                matched_components.append(comp)

        # If user asked generally about UI or settings/tab
        if not matched_components and any(w in q for w in ["ui", "หน้าต่าง", "เมนู", "toggle", "slider", "dropdown", "button", "tab", "settings", "glassmorphic", "fluent"]):
            # Supply default flagship component set
            for key in ["CreateWindow", "AddTab", "AddSection", "AddToggle", "AddSlider", "AddDropdown"]:
                if key in self.ui_catalog:
                    matched_components.append(self.ui_catalog[key])

        if matched_components:
            score = calculate_knowledge_score(relevance=0.92, quality=1.00, recency=0.98)
            comp_snippets = []
            for c in matched_components[:6]:
                comp_snippets.append(f"""• {c['name']} ({c['type']}):
  Library: {c['library']}
  Parameters: {', '.join(c.get('parameters', []))}
  Usage: {c['usage']}""")

            content = f"""[UI ARCHITECTURE BLUEPRINT]
Standard Aesthetics:
- Title Font: Enum.Font.Fondamento (28px Gothic Calligraphy, Color #FF233C, Dark Stroke #50000F)
- Interface Font: Enum.Font.GothamBold (11-14px)
- Shell: Dark Obsidian (#0C0306), Border Glowing Crimson Laser (#FF1432)
- Draggable Pill HUD with Min/Max & Avatar Profile

Verified Component Signatures:
{chr(10).join(comp_snippets)}
"""
            results.append({
                "layer": "UI_KNOWLEDGE",
                "topic": "UI Components & Blueprint",
                "score": score,
                "content": content
            })

        return results

    # -------------------------------------------------------------
    # Layer 3: Code Knowledge (Functions / Remotes / Game Mechanics)
    # -------------------------------------------------------------
    def retrieve_code_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Retrieves function references, remote patterns, and bypass patterns."""
        results = []
        q = query.lower()

        # 1. Anti-Cheat & Hooking Bypasses
        if any(w in q for w in ["bypass", "แอนตี้ชีท", "anti-cheat", "anticheat", "hook", "namecall", "getgc", "getreg", "ตรวจจับ"]):
            score = calculate_knowledge_score(relevance=0.96, quality=1.00, recency=0.95)
            content = f"""[ANTI-CHEAT BYPASS & HOOKING ARCHITECTURE]
1. Thread Neutralization:
   - Walk getreg(), identify suspect threads with debug.info(thread, 1, "s"), terminate via coroutine.close(thread).
2. Function Hooking:
   - Walk getgc(), filter islclosure(v) and not isexecutorclosure(v), neutralize with hookfunction(v, LPH_NO_UPVALUES(function() end)).
3. NilInstance Destruction:
   - Scan getnilinstances() for anti-cheat containers and call :Destroy().
4. Metamethod Spoofing:
   - Hook __namecall to intercept FireServer/InvokeServer while blocking unauthorized telemetry flags.
"""
            results.append({
                "layer": "CODE_KNOWLEDGE",
                "topic": "Anti-Cheat Bypasses",
                "score": score,
                "content": content
            })

        # 2. Specific Game Mechanics
        game_keywords = {
            "steal an egg": "Steal An Egg.txt",
            "steal egg": "StealAnEgg.lua",
            "murder mystery 2": "Master Mystery 2.txt",
            "murder mystery": "Master Mystery 2.txt",
            "blox fruit": "Blox Fruit.txt",
            "fisch": "FISCH.txt",
            "anime card": "ACF.txt",
            "mine a mountain": "Mine a Mountain.txt",
            "grow a chicken": "Grow a Chicken Fighter.txt",
            "greedy grower": "Greedy Grower.txt",
            "mm2": "Master Mystery 2.txt",
            "dice": "Anime Dice.txt"
        }

        matched_game_file = None
        for kw, fname in game_keywords.items():
            if kw in q:
                matched_game_file = fname
                break

        if matched_game_file:
            path = RBX_DIR / matched_game_file
            if path.exists():
                quality = get_file_quality_score(matched_game_file)
                mtime = path.stat().st_mtime
                recency = calculate_recency_score(mtime)
                score = calculate_knowledge_score(relevance=0.90, quality=quality, recency=recency)

                # Extract first 1500 bytes of plain structure
                try:
                    raw = path.read_text(encoding="utf-8", errors="ignore")
                    lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("--") and len(ln.strip()) > 5]
                    sample = "\n".join(lines[:35])
                    content = f"""[VERIFIED PRODUCTION GAMEPLAY PATTERN: {matched_game_file.replace('.txt', '')}]
Architecture Sample:
{sample[:1200]}
"""
                    results.append({
                        "layer": "CODE_KNOWLEDGE",
                        "topic": f"Mechanics: {matched_game_file}",
                        "score": score,
                        "content": content
                    })
                except Exception:
                    pass

        return results

    # -------------------------------------------------------------
    # Layer 4: Roblox Official OpenAPI Documentation (Open Cloud / Web)
    # -------------------------------------------------------------
    def retrieve_roblox_api_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Retrieves official Roblox OpenAPI documentation endpoints from Script/openapi.json."""
        from .roblox_api_indexer import ROBLOX_API_INDEXER
        q = query.lower()
        api_keywords = [
            "api", "endpoint", "cloud", "datastore", "data store", "messaging", 
            "asset", "badge", "gamepass", "inventory", "universe", "place", 
            "webhook", "publish", "ban", "user", "group", "open cloud", "openapi",
            "http", "rest", "luau-execution", "analytics"
        ]
        if any(w in q for w in api_keywords):
            endpoints = ROBLOX_API_INDEXER.search(query, top_k=2)
            if endpoints:
                content = ROBLOX_API_INDEXER.format_for_prompt(endpoints)
                score = calculate_knowledge_score(relevance=0.98, quality=1.00, recency=0.99)
                return [{
                    "layer": "ROBLOX_OPENAPI_SPEC",
                    "topic": f"Roblox API: {endpoints[0].get('path')}",
                    "score": score,
                    "content": content
                }]
        return []

    # -------------------------------------------------------------
    # Master Synthesis Retriever
    # -------------------------------------------------------------
    def retrieve(self, query: str, top_k: int = 3) -> str:
        """
        Synthesizes top relevant fragments across all 4 layers:
        1. Text Knowledge (Business / Pricing / Terms)
        2. UI Knowledge (Obsidian Glassmorphic 2.0 / Fluent)
        3. Code Knowledge (Roblox scripts, Remotes, Bypasses)
        4. Official Roblox OpenAPI Documentation (Script/openapi.json)
        """
        fragments = []
        fragments.extend(self.retrieve_business_knowledge(query))
        fragments.extend(self.retrieve_ui_knowledge(query))
        fragments.extend(self.retrieve_code_knowledge(query))
        fragments.extend(self.retrieve_roblox_api_knowledge(query))

        if not fragments:
            # If no direct match, provide general PayomboyZ library blueprint
            fragments.extend(self.retrieve_ui_knowledge("ui window tab toggle"))

        # Sort by KnowledgeScore descending
        fragments.sort(key=lambda x: x["score"], reverse=True)

        selected = fragments[:top_k]
        combined_text = "\n\n".join([f["content"] for f in selected])
        return combined_text


# Singleton
RETRIEVER = KnowledgeRetriever()
