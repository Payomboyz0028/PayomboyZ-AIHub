# -*- coding: utf-8 -*-
"""
=============================================================================
  🧠 PAYOMBØYZ ADVANCED SEMANTIC INTENT RESOLUTION ENGINE (O.Z.L.S.R Core)
  Translates natural Thai/English user requests into deterministic operational specs:
    - DEOBFUSCATE: Lua/Luau VM devirtualization, unpackers, CFG de-flattening
    - SCRIPT_SYNTHESIS: Complete Roblox executor automations (Auto Farm, ESP, Hop, UI)
    - REVERSE_ENGINEERING: Native binaries (PE/DLL/ELF), assembly, memory AOB, crypto
    - WEB_CLONE: Website cloning, DOM/Asset reconstruction, JS bundle unbundling
    - DISCORD_BOT: Discord bots, interactive panels, select menus, modals, webhooks
    - GENERAL_CHAT: Direct peer conversation with dj / owner
=============================================================================
"""

from __future__ import annotations
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple


@dataclass
class IntentExtraction:
    primary_intent: str  # "deobfuscate", "script_synthesis", "reverse_engineering", "web_clone", "discord_bot", "chat"
    confidence: float
    secondary_intents: List[str] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    technical_depth: str = "deep"  # "quick", "standard", "deep", "surgical"
    action_plan: List[str] = field(default_factory=list)
    normalized_query: str = ""


class SemanticIntentEngine:
    """
    Multi-dimensional natural language intent parser.
    Understands colloquial Thai, gamer slang, broken grammar, technical RE terminology,
    and extracts actionable parameters without hallucination.
    """

    # 1. URL Patterns
    URL_REGEX = re.compile(r'https?://[^\s<>"\')]+', re.IGNORECASE)
    ROBLOX_LINK_REGEX = re.compile(r'roblox\.com/(?:games|th/games)/(\d+)', re.IGNORECASE)
    GITHUB_RAW_REGEX = re.compile(r'raw\.githubusercontent\.com/[^\s]+|pastebin\.com/raw/[^\s]+', re.IGNORECASE)

    # 2. Web Cloning Keywords (Thai + EN)
    WEB_CLONE_KEYWORDS = [
        "โคลนเว็บ", "โคลนเว็บไซต์", "ก๊อปเว็บ", "ก๊อปปี้เว็บ", "ดูดเว็บ", "ดูดหน้าเว็บ",
        "แกะเว็บ", "แกะโครงสร้างเว็บ", "clone web", "clone website", "scrape website",
        "copy website", "rip website", "dump website", "web cloner", "reconstruct website",
        "แกะ css", "แกะ react", "แกะ dom", "ดึง assets", "ดึงรูปเว็บ"
    ]

    # 3. Native Reverse Engineering & Binary Keywords (Thai + EN)
    RE_BINARY_KEYWORDS = [
        "reverse engineering", "reverse engineer", "รีเวิร์ส", "วิศวกรรมย้อนกลับ",
        "ghidra", "hopper", "ida pro", "x64dbg", "pe file", "pe header",
        "dissassemble", "disassembly", "แอสเซมบลี", "ภาษาแอสเซมบลี", "pseudocode", "ซูโดโค้ด",
        "decompile dll", "decompile exe", "ดีคอมไพล์", "แกะ dll", "แกะ exe", "แกะ binary",
        "iat", "eat", "import table", "export table", "section header", "entropy",
        "upx", "themida", "vmprotect", "anti-debug", "inline hook", "detour",
        "memory offset", "pointer chain", "aob scan", "pattern scan", "cheat engine",
        "evm bytecode", "sourcemap", "source map", "wakaru", "unbundle"
    ]

    # 4. Deobfuscation Keywords (Lua / Luau / JS)
    DEOBF_KEYWORDS = [
        "deob", "deobf", "deobfuscate", "deobfuscation", "unobf", "unobfuscate",
        "ถอดรหัส", "ถอดสคริป", "ถอดโค้ด", "แกะสคริปต์", "แกะสคริป", "แกะโค้ด", "ถอดให้หน่อย",
        "unpack", "devirtualize", "devirtualization", "dumper", "dump",
        "luraph", "moonsec", "ironbrew", "moonveil", "luarmor", "prometheos",
        "wearedev", "twok", "luast", "scpe", "2lua", "cff", "control flow flattening",
        "string table", "vm opcode", "dispatcher", "vm dispatch"
    ]

    # 5. Roblox Script Synthesis Keywords
    SCRIPT_SYNTHESIS_KEYWORDS = [
        "เขียนสคริป", "เขียนสคริปต์", "ทำสคริป", "ทำสคริปต์", "ขอสคริป", "ขอสคริปต์",
        "แก้สคริป", "โมสคริป", "สร้างสคริป", "โปรแมพ", "แจกสคริป", "สคริปต์แมพ",
        "make script", "build script", "generate script", "write script",
        "auto farm", "autofarm", "auto steal", "autosteal", "ขโมยไข่", "ขโมยของ",
        "ตีมอน", "ตีบอส", "ฟาร์มออโต้", "วาร์ป", "เทเลพอร์ต", "teleport",
        "esp", "aimbot", "hitbox", "hitbox expander", "noclip", "walkspeed", "fly",
        "safe hop", "server hop", "anti-afk", "antiafk", "windui", "fluent", "maclib",
        "solara", "wave", "delta", "synapse z", "executor",
        "aimlock", "auto aim", "silent aim",
    ]

    # 6. Discord Bot Engineering Keywords
    DISCORD_BOT_KEYWORDS = [
        "discord bot", "ดิสบอท", "บอทดิส", "บอท discord", "สร้างบอท", "เขียนบอท",
        "slash command", "สแลชคอมมานด์", "role bot", "get-role", "setup_panel",
        "discord panel", "ปุ่มกดในดิส", "select menu", "modal dialog", "webhook",
        "เว็บฮุก", "ดัก webhook", "discord webhook", "verify system", "ระบบยืนยันตัวตน"
    ]

    # 7. Game Dump / ReplicatedStorage Context Keywords — NOT deobf, route to script_synthesis with dump context
    DUMP_CONTEXT_KEYWORDS = [
        "replicatedstorage", "replicatedfirst", "workspace.", "serverscriptservice",
        "startergui", "startercharacterscripts", "starterplayerscripts",
        "remoteevent", "remotefunction", "bindableevent", "bindablefunction",
        "game:getservice", "game.players", "players.localplayer",
        "script.parent", "localscript", "modulescript", "script:waitforchild",
        "dump", "ดัมพ์", "dump มา", "ดึงมา", "ข้อมูลแมพ", "โครงสร้างแมพ",
        "map dump", "game dump", "service dump", "remote dump",
    ]
    # Structural signals that this is a raw game dump (not obfuscated)
    DUMP_STRUCTURE_SIGNALS = [
        r"ReplicatedStorage\.",
        r"workspace\.",
        r"game:GetService\(",
        r"RemoteEvent",
        r"RemoteFunction",
        r"Instance\.new\(",
        r"Players\.LocalPlayer",
    ]

    @classmethod
    def resolve_intent(cls, user_text: str, attached_filename: str = "", attached_content: str = "") -> IntentExtraction:
        text = (user_text or "").strip()
        lowered = text.lower()
        extracted_entities: Dict[str, Any] = {}
        scores = {
            "web_clone": 0.0,
            "reverse_engineering": 0.0,
            "deobfuscate": 0.0,
            "script_synthesis": 0.0,
            "discord_bot": 0.0,
            "dump_context": 0.0,   # NEW: game structure dump → script synthesis with context
            "chat": 0.1
        }

        # ---------------------------------------------------------------------
        # 1. URL & Target Discovery
        # ---------------------------------------------------------------------
        urls = cls.URL_REGEX.findall(text)
        if urls:
            extracted_entities["urls"] = urls
            target_url = urls[0]
            extracted_entities["target_url"] = target_url
            parsed = urllib.parse.urlparse(target_url)
            extracted_entities["domain"] = parsed.netloc

            # Check if Roblox game link
            roblox_match = cls.ROBLOX_LINK_REGEX.search(target_url)
            if roblox_match:
                extracted_entities["roblox_place_id"] = int(roblox_match.group(1))
                scores["script_synthesis"] += 3.5

            # If web cloning keyword is mentioned with a URL
            for kw in cls.WEB_CLONE_KEYWORDS:
                if kw in lowered:
                    scores["web_clone"] += 5.0
                    break
            else:
                if not roblox_match and not any(ext in target_url.lower() for ext in [".lua", ".txt", ".json", ".zip"]):
                    # Generic URL with question like "โคลนเว็บนี้", "แกะหน้านี้"
                    if any(w in lowered for w in ["โคลน", "ดูด", "ก๊อป", "clone", "copy", "rip", "แกะ"]):
                        scores["web_clone"] += 4.0

        # ---------------------------------------------------------------------
        # 2. File Attachment Analysis
        # ---------------------------------------------------------------------
        if attached_filename:
            extracted_entities["attached_filename"] = attached_filename
            fn_lower = attached_filename.lower()
            if fn_lower.endswith((".exe", ".dll", ".sys", ".bin", ".elf", ".so", ".dylib")):
                extracted_entities["binary_type"] = "pe" if fn_lower.endswith((".exe", ".dll", ".sys")) else "native"
                scores["reverse_engineering"] += 4.5
            elif fn_lower.endswith((".lua", ".luau", ".txt")):
                extracted_entities["script_type"] = "lua"
                scores["deobfuscate"] += 2.5
            elif fn_lower.endswith((".js", ".bundle.js", ".ts", ".html")):
                extracted_entities["web_type"] = "bundle"
                scores["reverse_engineering"] += 2.0
                scores["web_clone"] += 1.5

        if attached_content:
            extracted_entities["content_length"] = len(attached_content)
            # Check if payload is obfuscated Lua
            if any(sig in attached_content for sig in ["LPH-", "Luraph", "MoonSec", "IronBrew", "bytecode", "string.char"]):
                scores["deobfuscate"] += 3.0
            else:
                # Structural dump detection: count Roblox API references
                import re as _re
                dump_signal_hits = sum(
                    1 for pattern in cls.DUMP_STRUCTURE_SIGNALS
                    if _re.search(pattern, attached_content[:8000])
                )
                if dump_signal_hits >= 3:
                    scores["dump_context"] += 4.0 + dump_signal_hits * 0.5
                    extracted_entities["dump_signal_hits"] = dump_signal_hits
                    extracted_entities["is_game_dump"] = True
                elif dump_signal_hits >= 1:
                    scores["dump_context"] += 2.0
                    scores["script_synthesis"] += 1.0

        # Detect mentioned binary files in text (e.g. crack.dll, cheat.exe)
        binary_match = re.search(r'\b[a-zA-Z0-9_\-]+\.(?:exe|dll|sys|bin|elf|so|dylib)\b', text, re.I)
        if binary_match:
            extracted_entities["mentioned_binary"] = binary_match.group(0)
            scores["reverse_engineering"] += 4.0

        # Thai binary analysis phrases
        if any(w in lowered for w in ["วิเคราะห์ไฟล์", "เจาะไฟล์", "แกะไฟล์", "แงะไฟล์", "ดูดไฟล์"]):
            scores["reverse_engineering"] += 3.0

        # ---------------------------------------------------------------------
        # 3. Keyword & Semantic Matching
        # ---------------------------------------------------------------------
        # Web Clone scoring
        for kw in cls.WEB_CLONE_KEYWORDS:
            if kw in lowered:
                scores["web_clone"] += 2.5

        # RE scoring
        for kw in cls.RE_BINARY_KEYWORDS:
            if kw in lowered:
                scores["reverse_engineering"] += 2.5

        # Deobfuscate scoring
        for kw in cls.DEOBF_KEYWORDS:
            if kw in lowered:
                scores["deobfuscate"] += 2.0

        # Script Synthesis scoring
        for kw in cls.SCRIPT_SYNTHESIS_KEYWORDS:
            if kw in lowered:
                scores["script_synthesis"] += 2.0

        # Discord Bot scoring
        for kw in cls.DISCORD_BOT_KEYWORDS:
            if kw in lowered:
                scores["discord_bot"] += 2.5

        # Dump context keyword scoring (game structure context)
        for kw in cls.DUMP_CONTEXT_KEYWORDS:
            if kw in lowered:
                scores["dump_context"] += 1.5

        # ---------------------------------------------------------------------
        # 4. Contextual Disambiguation
        # ---------------------------------------------------------------------
        # If user explicitly asked "เขียนบอท discord โคลนเว็บ" -> Discord bot + Web clone
        # If user asked "แกะสคริป" -> deobfuscate
        # If user asked "ขอสคริปบล็อกฟรุต" -> script_synthesis
        # If user asked "เจาะ PE / อธิบายการทำงาน" -> reverse_engineering

        # Game name extraction
        from bot.roblox_platform_intel import THAI_GAME_ALIASES
        for alias, game_kw in THAI_GAME_ALIASES.items():
            if alias.lower() in lowered:
                extracted_entities["game_alias"] = alias
                extracted_entities["game_name"] = game_kw
                scores["script_synthesis"] += 2.0
                break

        # UI Framework extraction
        if "windui" in lowered:
            extracted_entities["ui_framework"] = "WindUI"
        elif "fluent" in lowered:
            extracted_entities["ui_framework"] = "Fluent"
        elif "maclib" in lowered:
            extracted_entities["ui_framework"] = "MacLib"

        # Determine Primary Intent
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_intents[0][0]
        max_score = sorted_intents[0][1]

        # dump_context → always resolve to script_synthesis with dump enrichment flag
        if primary == "dump_context":
            primary = "script_synthesis"
            extracted_entities["route_hint"] = "dump_context"

        # Fallback to chat if low confidence and no specific technical triggers
        if max_score < 1.0:
            primary = "chat"
            confidence = 0.5
        else:
            confidence = min(0.99, max_score / 5.0)

        secondary = [k for k, v in sorted_intents[1:] if v >= 2.0 and k != primary and k != "dump_context"]

        # Action Plan Generation
        action_plan: List[str] = []
        if primary == "web_clone":
            action_plan = [
                "CRAWL_DOM_TREE",
                "LOCALIZE_CSS_AND_FONTS",
                "EXTRACT_COMPONENT_HIERARCHY",
                "PACKAGE_OFFLINE_RECONSTRUCTION"
            ]
        elif primary == "reverse_engineering":
            action_plan = [
                "PARSE_BINARY_HEADERS",
                "EVALUATE_SECTION_ENTROPY",
                "TRACE_IMPORT_ADDRESS_TABLE",
                "SYNTHESIZE_PSEUDOCODE_EVIDENCE"
            ]
        elif primary == "deobfuscate":
            action_plan = [
                "FINGERPRINT_OBFUSCATOR_TYPE",
                "EXECUTE_HEADLESS_LUAU_TRAP",
                "DEFLATTEN_CONTROL_FLOW",
                "RECOVER_READABLE_LUAU_SOURCE"
            ]
        elif primary == "script_synthesis":
            if extracted_entities.get("route_hint") == "dump_context":
                action_plan = [
                    "INGEST_GAME_DUMP_AS_GROUND_TRUTH",
                    "EXTRACT_REMOTES_FROM_DUMP_STRUCTURE",
                    "FETCH_SCRIPTBLOX_REFERENCE_SCRIPTS",
                    "GENERATE_SCRIPT_WITH_VERIFIED_REMOTES",
                ]
            else:
                action_plan = [
                    "INGEST_GROUND_TRUTH_REMOTES",
                    "FETCH_PLATFORM_BADGES_ROADMAP",
                    "GENERATE_BYPASS_AND_AUTOMATION_CORE",
                    "ATTACH_SAFE_SERVER_HOP",
                ]
        elif primary == "discord_bot":
            action_plan = [
                "SPECIFY_BOT_COMMAND_TREE",
                "DESIGN_PERSISTENT_INTERACTIVE_UI",
                "WIRE_EVENT_LISTENERS_AND_ERROR_HANDLERS"
            ]
        else:
            action_plan = ["PROCESS_DIRECT_PEER_RESPONSE"]

        return IntentExtraction(
            primary_intent=primary,
            confidence=confidence,
            secondary_intents=secondary,
            entities=extracted_entities,
            technical_depth="surgical" if "surgical" in lowered or "bypass" in lowered else "deep",
            action_plan=action_plan,
            normalized_query=text
        )
