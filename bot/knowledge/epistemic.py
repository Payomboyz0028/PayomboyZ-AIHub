#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ KNOWLEDGE BASE — EPISTEMIC TRUTH STATUS ENGINE
====================================================================
Prevents hallucination by assigning epistemic confidence states:
- KNOWN: Verified existing component/function in PayomboyZ library
- SUPPORTED: Valid standard Roblox Engine API / Service
- INFERRED: Derived from established code patterns with high confidence
- UNKNOWN: NOT present in library or official docs — MUST NOT HALLUCINATE
- CONFLICT: Direct contradiction with PayomboyZ security / architecture
====================================================================
"""

from enum import Enum
from typing import Dict, Any, Optional, List


class EpistemicStatus(str, Enum):
    KNOWN = "KNOWN"
    SUPPORTED = "SUPPORTED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


# Standard Roblox Engine Services & Common Global APIs
STANDARD_ROBLOX_SERVICES = {
    "Players", "ReplicatedStorage", "RunService", "TweenService",
    "UserInputService", "HttpService", "TeleportService", "CoreGui",
    "Lighting", "SoundService", "StarterGui", "VirtualInputManager",
    "VirtualUser", "PathfindingService", "ContextActionService", "Stats",
    "MarketplaceService", "GuiService", "ProximityPromptService"
}

STANDARD_ROBLOX_GLOBAL_FUNCTIONS = {
    "print", "warn", "error", "pcall", "xpcall", "tick", "time", "typeof",
    "loadstring", "getgenv", "getrenv", "getreg", "getgc", "hookfunction",
    "hookmetamethod", "newcclosure", "islclosure", "isexecutorclosure",
    "setreadonly", "getrawmetatable", "fireclickdetector", "firetouchinterest",
    "fireproximityprompt", "getnilinstances", "identifyexecutor", "readfile",
    "writefile", "isfile", "delfile", "makefolder", "isfolder"
}


class EpistemicAuditor:
    """Audits functions, remotes, and UI components against true ground knowledge."""

    def __init__(self, code_registry: Optional[Dict[str, Any]] = None, ui_catalog: Optional[Dict[str, Any]] = None):
        self.code_registry = code_registry or {}
        self.ui_catalog = ui_catalog or {}

    def update_registries(self, code_registry: Dict[str, Any], ui_catalog: Dict[str, Any]):
        self.code_registry = code_registry
        self.ui_catalog = ui_catalog

    def audit_symbol(self, symbol_name: str, category: str = "auto") -> Dict[str, Any]:
        """
        Audits a symbol to assign EpistemicStatus.
        category: 'ui', 'function', 'remote', 'service', or 'auto'
        """
        sym = symbol_name.strip()

        # 1. Check UI Catalog
        if category in ("ui", "auto") and sym in self.ui_catalog:
            entry = self.ui_catalog[sym]
            return {
                "symbol": sym,
                "status": EpistemicStatus.KNOWN,
                "category": "UI",
                "confidence": 0.98,
                "evidence": entry.get("source", "UI/Obsidain_Glassmophic2.txt"),
                "parameters": entry.get("parameters", []),
                "advice": f"Verified component in {entry.get('library', 'PayomboyZ UI')}"
            }

        # 2. Check Code Registry (Functions/Modules)
        if category in ("function", "auto") and sym in self.code_registry.get("functions", {}):
            entry = self.code_registry["functions"][sym]
            return {
                "symbol": sym,
                "status": EpistemicStatus.KNOWN,
                "category": "Function",
                "confidence": 0.96,
                "evidence": entry.get("source", "Script/rbx folder"),
                "parameters": entry.get("parameters", []),
                "advice": f"Documented function in {entry.get('source')}"
            }

        # 3. Check Known Remotes in Code Registry
        if category in ("remote", "auto") and sym in self.code_registry.get("remotes", {}):
            entry = self.code_registry["remotes"][sym]
            return {
                "symbol": sym,
                "status": EpistemicStatus.KNOWN,
                "category": "Remote",
                "confidence": 0.95,
                "evidence": entry.get("source", "Script/rbx folder"),
                "advice": f"Registered remote in {entry.get('source')}"
            }

        # 4. Check Standard Roblox Services & Engine Functions
        if sym in STANDARD_ROBLOX_SERVICES or sym in STANDARD_ROBLOX_GLOBAL_FUNCTIONS:
            return {
                "symbol": sym,
                "status": EpistemicStatus.SUPPORTED,
                "category": "RobloxAPI",
                "confidence": 0.92,
                "evidence": "Roblox Engine / Luau Standard Global",
                "advice": "Standard Roblox service or Luau runtime API"
            }

        # 5. Check if it's a common Lua pattern (e.g. task.spawn, task.wait, math.clamp, string.format)
        if "." in sym:
            mod, fn = sym.split(".", 1)
            if mod in ("task", "math", "string", "table", "coroutine", "debug", "os"):
                return {
                    "symbol": sym,
                    "status": EpistemicStatus.SUPPORTED,
                    "category": "LuauStandardLib",
                    "confidence": 0.94,
                    "evidence": f"Luau standard {mod} library",
                    "advice": f"Valid Luau built-in method {sym}"
                }

        # 6. Check for VVIP / Private PayomboyZ source leak attempt
        if any(w in sym.lower() for w in ["payomboyz_vvip", "sha256_memguard", "bypass_luarmor_core"]):
            return {
                "symbol": sym,
                "status": EpistemicStatus.CONFLICT,
                "category": "SecurityGuardrail",
                "confidence": 1.00,
                "evidence": "PAYOMBØYZ Core Proprietary IP Policy",
                "advice": "BLOCKED: Proprietary security signature must not be exposed or modified"
            }

        # 7. Unverified / Hallucinated symbol
        return {
            "symbol": sym,
            "status": EpistemicStatus.UNKNOWN,
            "category": "Unverified",
            "confidence": 0.15,
            "evidence": "None (Not found in PayomboyZ Knowledge Base or Roblox API)",
            "advice": f"UNKNOWN: Do NOT invent method/function '{sym}' without explicit evidence"
        }
