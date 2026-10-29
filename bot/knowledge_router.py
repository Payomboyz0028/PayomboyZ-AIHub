#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ KNOWLEDGE ROUTER & DYNAMIC LEARNING BRAIN
====================================================================
Ingests and indexes:
- Script/rbx folder/รวมBypass.txt (Anti-cheat & Hooking Bypasses)
- Script/rbx folder/UI/ (Obsidian Glassmorphic, Fluent, WindUI, Intro)
- Script/rbx folder/ (ACF, Blox Fruit, FISCH, Mine a Mountain, etc.)
- Script/rbx folder/ (ราคา.txt, วิธีโหลดตัวรัน.txt, ข้อตกลง.txt)
- Dynamic Learning Cache (learned_memory.json)
====================================================================
"""

import os
import sys
import re
import json
import time
import math
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
RBX_DIR = BASE_DIR / "Script" / "rbx folder"
UI_DIR = RBX_DIR / "UI"
MEMORY_FILE = BASE_DIR / "bot" / "learned_memory.json"


class KnowledgeRouter:
    """
    Algorithmic knowledge indexer and context router for Roblox Luau scripts,
    reverse engineering, anti-cheat bypasses, and UI frameworks.
    """
    def __init__(self, memory_file: Optional[Path | str] = None):
        self.rbx_dir = RBX_DIR
        self.ui_dir = UI_DIR
        self.memory_file = Path(memory_file) if memory_file is not None else MEMORY_FILE
        self._cache = {}
        self.priority_cache: OrderedDict[str, Any] = OrderedDict()
        self._corpus_cache: List[Dict[str, Any]] = []
        self._corpus_indexed_time: float = 0.0
        self._learned_data = self._load_learned_memory()

    def _cache_get(self, key: str) -> Optional[Any]:
        if key in self.priority_cache:
            self.priority_cache.move_to_end(key)
            return self.priority_cache[key]
        return None

    def _cache_put(self, key: str, value: Any, max_size: int = 500):
        self.priority_cache[key] = value
        self.priority_cache.move_to_end(key)
        if len(self.priority_cache) > max_size:
            self.priority_cache.popitem(last=False)

    def _load_learned_memory(self) -> Dict[str, Any]:
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "maps": {},
            "remotes": {},
            "user_rules": {},
            "last_updated": time.time()
        }

    def save_learned_memory(self):
        try:
            self._learned_data["last_updated"] = time.time()
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self._learned_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[-] Failed to save learned memory: {e}")

    def learn_new_context(self, category: str, key: str, value: Any):
        """Allows AI and users to inject new learned patterns into persistent storage."""
        if category not in self._learned_data:
            self._learned_data[category] = {}
        self._learned_data[category][key] = {
            "data": value,
            "timestamp": time.time()
        }
        self.save_learned_memory()

    def _read_file_cached(self, path: Path, max_bytes: int = 15000) -> str:
        key = str(path)
        if key in self._cache:
            return self._cache[key]
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(max_bytes)
                    self._cache[key] = content
                    return content
            except Exception:
                pass
        return ""

    def get_bypass_knowledge(self) -> str:
        """Retrieves core anti-cheat bypass architectures from รวมBypass.txt and advanced metatable hooks."""
        return """
[🛡️ PAYOMBØYZ KNOWLEDGE BASE — ANTI-CHEAT BYPASS & HOOKING PATTERNS]
Source: Script/rbx folder/รวมBypass.txt
Key Techniques:
1. Anti-Kick Metamethod Hooking:
   local oldNamecall
   oldNamecall = hookmetamethod(game, "__namecall", newcclosure(function(self, ...)
       local method = getnamecallmethod()
       if (method == "Kick" or method == "kick") and not checkcaller() then
           return
       end
       return oldNamecall(self, ...)
   end))

2. WalkSpeed / JumpPower Property Spoofing (__index & __newindex):
   local oldIndex
   oldIndex = hookmetamethod(game, "__index", newcclosure(function(self, key)
       if not checkcaller() and typeof(self) == "Instance" and self:IsA("Humanoid") then
           if key == "WalkSpeed" then return 16 end
           if key == "JumpPower" then return 50 end
       end
       return oldIndex(self, key)
   end))

3. Remote Event Telemetry Blacklist (Blocking AntiCheat / Ban remotes):
   local BLOCKED_REMOTES = { ["AntiCheat"] = true, ["SecurityCheck"] = true, ["BanEvent"] = true, ["Telemetry"] = true, ["KickRemote"] = true }
   local oldFire
   oldFire = hookfunction(Instance.new("RemoteEvent").FireServer, newcclosure(function(self, ...)
       if BLOCKED_REMOTES[self.Name] and not checkcaller() then
           return
       end
       return oldFire(self, ...)
   end))

4. Thread Neutralization in getreg():
   for _, thread in ipairs(getreg()) do
       if type(thread) == "thread" and thread ~= coroutine.running() then
           local src = debug.info(thread, 1, "s") or ""
           if src:find("AntiCheat") or src:find("Security") or src:find("Detector") then
               pcall(coroutine.close, thread)
           end
       end
   end

5. NilInstance Scanner & Purge:
   for _, inst in ipairs(getnilinstances()) do
       if inst:IsA("LocalScript") and (inst.Name:find("Anti") or inst.Name:find("Detection")) then
           inst.Disabled = true
           pcall(inst.Destroy, inst)
       end
   end
"""

    def get_ui_knowledge(self, query: str = "") -> str:
        """Retrieves UI design knowledge and syntax from Script/rbx folder/UI/."""
        q = query.lower()
        if "maclib" in q or "mac" in q:
            return """
[🍎 MACLIB UI ARCHITECTURE]
Source: Script/rbx folder/UI/Maclib-main/Example.lua
Loader: local MacLib = loadstring(game:HttpGet("https://github.com/biggaboy212/Maclib/releases/latest/download/maclib.txt"))()
Key Elements:
- Window:
  local Window = MacLib:Window({
      Title = "PAYOMBØYZ HUB",
      Subtitle = "MacLib Edition",
      Size = UDim2.fromOffset(868, 650),
      DragStyle = 1,
      ShowUserInfo = true,
      Keybind = Enum.KeyCode.RightControl,
      AcrylicBlur = true
  })
- TabGroup & Tabs:
  local tabGroups = { TabGroup1 = Window:TabGroup() }
  local Tabs = {
      Main = tabGroups.TabGroup1:Tab({ Name = "Main", Image = "rbxassetid://18821914323" }),
      Settings = tabGroups.TabGroup1:Tab({ Name = "Settings", Image = "rbxassetid://10734950309" })
  }
- Sections & Controls:
  local Section = Tabs.Main:Section({ Side = "Left" })
  Section:Header({ Name = "Automation" })
  Section:Button({ Name = "Run", Callback = function() end })
  Section:Toggle({ Name = "Auto Farm", Default = false, Callback = function(v) end })
  Section:Slider({ Name = "Speed", Default = 16, Minimum = 16, Maximum = 250, Precision = 1, DisplayMethod = "Value", Callback = function(v) end })
  Section:Dropdown({ Name = "Target", Multi = false, Required = true, Options = {"A", "B"}, Default = "A", Callback = function(choice) end })
  Section:Input({ Name = "Key", Placeholder = "Paste key...", AcceptedCharacters = "All", Callback = function(text) end })
  Section:Colorpicker({ Name = "ESP Color", Default = Color3.fromRGB(255, 0, 0), Callback = function(c) end })
  Section:Keybind({ Name = "Toggle Key", Default = Enum.KeyCode.E, Callback = function(key) end })
- Dialog & Notification:
  Window:Dialog({ Title = "Warning", Description = "Are you sure?", Buttons = { { Name = "Confirm", Callback = fn }, { Name = "Cancel" } } })
  Window:Notify({ Title = "PAYOMBØYZ HUB", Description = "Script injected!", Lifetime = 5 })
"""
        elif "ide" in q or "in-game" in q or "codeframe" in q or "editor" in q:
            return """
[💻 IN-GAME IDE (Dex Explorer Script Engine Architecture)]
Source: Script/rbx folder/UI/In-Game-IDE-main/update8/IDEModule.lua
Key Elements:
- High-Performance Virtual Line Text Frame: Supports virtually unlimited lines without memory lag (Dex Explorer technique).
- Syntax Highlighting: Automatic Luau tokenization, keyword coloring, comments, strings, numbers, and globals.
- Usage:
  local IDEModule = require(script.IDEModule) -- or raw asset
  local IDE = IDEModule.CodeFrame.new()
  IDE.Gui.Parent = targetTabFrame -- Scales to UDim2.new(1, 0, 1, 0)
- API Methods:
  IDE:SetText(code_string)
  local code = IDE:GetText()
  IDE:Focus()
  IDE:SetAutoIndent(true)
"""
        elif "fluent" in q:
            f_path = self.ui_dir / "Fluent.txt"
            snippet = self._read_file_cached(f_path, max_bytes=4000)
            return f"\n[🎨 FLUENT UI ARCHITECTURE]\n{snippet[:2000]}\n"
        elif "wind" in q:
            w_path = self.ui_dir / "WindUI.txt"
            snippet = self._read_file_cached(w_path, max_bytes=4000)
            return f"\n[🎨 WINDUI ARCHITECTURE]\n{snippet[:2000]}\n"
        else:
            # Obsidian Glassmorphic 2 default
            obs_path = self.ui_dir / "Obsidain_Glassmophic2.txt"
            snippet = self._read_file_cached(obs_path, max_bytes=4000)
            return """
[🎨 OBSIDIAN GLASSMORPHIC 2.0 UI ARCHITECTURE]
Source: Script/rbx folder/UI/Obsidain_Glassmophic2.txt
Key Elements:
- Acrylic Blur Effect & Dynamic Cyber Glow UIStroke.
- Draggable Pill HUD for Mobile/PC (Avatar, FPS, Ping, Min/Max Toggle).
- High-Performance Tabs: Window:CreateTab({ Name = "...", Icon = "..." }).
- Interactive Components: CreateToggle, CreateSlider, CreateDropdown, CreateKeybind, CreateColorpicker.
- Smooth Tween Animation using TweenService with Quad/Out Easing.
"""

    GAME_MAP_FILES = {
        "slayer": ["slayer2.luau"],
        "demon slayer": ["slayer2.luau"],
        "steal an egg": ["Steal An Egg.txt", "StealAnEgg.lua", "ของคนอื่น.txt"],
        "steal egg": ["Steal An Egg.txt", "StealAnEgg.lua"],
        "egg": ["Steal An Egg.txt", "StealAnEgg.lua"],
        "dungeon": ["DungeonLootr.lua", "Iron Soul-Dungeon.txt"],
        "iron soul": ["Iron Soul-Dungeon.txt", "Iron Soul Tower.txt", "Iron Soul Boss.txt"],
        "rivals": ["Rivals.lua"],
        "mine a mountain": ["Mine a Mountain.txt"],
        "aotr": ["AOTR.txt"],
        "attack on titan": ["AOTR.txt"],
        "99night": ["99Night.txt"],
        "blox fruit": ["Blox Fruit.txt", "BFv4t10.lua"],
        "fisch": ["FISCH.txt"],
        "anime card": ["Anime Card Farm.txt", "ACF.txt"],
        "card farm": ["Anime Card Farm.txt"],
        "anime verse card farm": ["Anime Card Farm.txt"],
        "animeverse": ["Anime Card Farm.txt", "Anime Dice.txt"],
        "anime verse": ["Anime Card Farm.txt", "Anime Dice.txt"],
        "acf": ["ACF.txt", "Anime Card Farm.txt"],
        "anime dice": ["Anime Dice.txt"],
        "dice": ["Anime Dice.txt"],
        "anime zero": ["Ai Script.txt", "AOTR.txt"],
        "zero": ["Ai Script.txt"],
        "roll anime": ["Roll Anime to FIGHT.txt"],
        "gnome": ["Roll a Gnome.txt"],
        "garden": ["Grow a garden 2.txt"],
        "chicken": ["Grow a Chicken Fighter.txt", "GrowAChickenFighter.lua"],
        "sniper": ["Sniper Arena.txt"],
        "dahood": ["DaHood.lua"],
        "mm2": ["Mm2.lua", "Master Mystery 2.txt"],
        "mystery 2": ["Master Mystery 2.txt", "Mm2.lua"],
        "ride a pet": ["Ride a pet.txt"],
        "gakuran": ["Gakuran.lua", "Gakurun.txt"],
        "jump for pets": ["JumpForPets.lua"],
        "leaf simulator": ["LeafSimulator.lua"],
        "capybara": ["CapybaraVsPlant.txt"],
        "greedy grower": ["Greedy Grower.txt"],
    }

    def get_mechanic_knowledge(self, game_name: str) -> str:
        """Retrieves verified game mechanics and remotes across all 60+ local map dumps."""
        from bot.remote_harvester import HARVESTER

        gn = game_name.lower().strip()
        matched_file: Optional[Path] = None

        # 1. Exact alias dictionary match
        for alias, file_list in self.GAME_MAP_FILES.items():
            if alias in gn:
                for fname in file_list:
                    cand = self.rbx_dir / fname
                    if cand.exists():
                        matched_file = cand
                        break
            if matched_file:
                break

        # 2. Fuzzy scan over all files in rbx_dir if no alias hit
        if not matched_file and len(gn) >= 3:
            for cand in self.rbx_dir.glob("*"):
                if cand.is_file() and any(ext in cand.suffix for ext in [".lua", ".luau", ".txt"]):
                    cand_clean = cand.stem.lower()
                    if gn in cand_clean or cand_clean in gn:
                        matched_file = cand
                        break

        # If matched, run REA-style semantic harvester
        if matched_file and matched_file.exists():
            content = self._read_file_cached(matched_file, max_bytes=80000)
            if content:
                analysis = HARVESTER.analyze_script(content)
                gt = HARVESTER.format_as_ground_truth(analysis, matched_file.stem)
                print(f"[KNOWLEDGE ROUTER] Ingested local ground truth from {matched_file.name} ({len(gt)} chars).", flush=True)
                return gt

        return ""

    def get_authentic_script(self, game_name: str) -> Optional[str]:
        """
        Retrieves the complete, real, multi-thousand-line Lua script from local dumps.
        Returns the entire script with branding/author tags stripped cleanly.
        """
        gn = game_name.lower().strip()
        matched_file: Optional[Path] = None

        for alias, file_list in self.GAME_MAP_FILES.items():
            if alias in gn:
                for fname in file_list:
                    cand = self.rbx_dir / fname
                    if cand.exists():
                        matched_file = cand
                        break
            if matched_file:
                break

        if not matched_file and len(gn) >= 3:
            for cand in self.rbx_dir.glob("*"):
                if cand.is_file() and any(ext in cand.suffix for ext in [".lua", ".luau", ".txt"]):
                    cand_clean = cand.stem.lower()
                    if gn in cand_clean or cand_clean in gn:
                        matched_file = cand
                        break

        if matched_file and matched_file.exists():
            try:
                code = matched_file.read_text(encoding="utf-8", errors="ignore")
                if len(code.strip()) > 1500:
                    print(f"[KNOWLEDGE ROUTER] Sourced authentic production script from {matched_file.name} ({len(code):,} chars, {len(code.splitlines()):,} lines).", flush=True)
                    return self.strip_all_branding(code, game_name)
            except Exception as e:
                print(f"[KNOWLEDGE ROUTER] Error reading authentic script from {matched_file}: {e}", flush=True)

        return None

    @staticmethod
    def strip_all_branding(code: str, game_name: str) -> str:
        """
        Removes any internal branding, creator names (PAYOMBØYZ, PAYOMBØYZAA, O.Z.L.S.R),
        and replaces headers with clean, authentic game titles.
        """
        if not code:
            return ""
        cleaned_lines = []
        for line in code.splitlines():
            low = line.lower()
            if any(b in low for b in ["author:", "edited by", "credit:", "payombøyz", "payomboyz", "o.z.l.s.r", "flowauth"]):
                if line.strip().startswith("--"):
                    continue
            line = re.sub(r'PAYOMBØYZAA|PAYOMBØYZ|PayomboyZ', 'GameHub', line)
            cleaned_lines.append(line)

        cleaned_code = "\n".join(cleaned_lines)
        header = f"""-- ==============================================================================
-- [ {game_name.upper()} | UNIVERSAL AUTOMATION & CLIENT SUITE ]
-- Target: Universal Roblox Executors (Solara, Wave, Delta, Codex, Synapse Z)
-- Build: Production Grade | Full Feature Set
-- ==============================================================================
"""
        return header + "\n" + cleaned_code.lstrip()

    async def get_complete_game_context_async(
        self,
        game_name: str,
        user_prompt: str = "",
        place_id: Optional[str | int] = None
    ) -> str:
        """
        Master Game Recon Pipeline:
        1. Checks local 60+ map dumps via RemoteHarvester.
        2. If unknown/missing, queries Rscripts.net API in real-time.
        3. Extracts and returns authoritative Ground Truth + Anti-Cheat Bypasses.
        """
        from bot.remote_harvester import HARVESTER
        from bot.rscripts_client import RSCRIPTS

        # Step 1: Local Knowledge Base
        local_gt = self.get_mechanic_knowledge(game_name)
        if not local_gt and user_prompt:
            local_gt = self.get_mechanic_knowledge(user_prompt)

        if local_gt and "VERIFIED REVERSE-ENGINEERING GROUND TRUTH" in local_gt:
            return f"{local_gt}\n\n{self.get_bypass_knowledge()}"

        # Step 2: Check persistent game cache (bot/knowledge/games/<clean_name>.json)
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', game_name.lower())
        cache_file = BASE_DIR / "bot" / "knowledge" / "games" / f"{clean_name}.json"
        if cache_file.exists():
            try:
                cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
                gt = HARVESTER.format_as_ground_truth(cached_data, game_name)
                print(f"[KNOWLEDGE ROUTER] Retrieved cached ground truth for '{game_name}'.", flush=True)
                return f"{gt}\n\n{self.get_bypass_knowledge()}"
            except Exception:
                pass

        # Step 3: Real-Time Rscripts.net API Harvester
        print(f"[KNOWLEDGE ROUTER] Game '{game_name}' not in local library. Triggering Rscripts Harvester...", flush=True)
        try:
            harvested = await RSCRIPTS.harvest_game_scripts(query=game_name, place_id=place_id)
            if harvested:
                best_script = harvested[0].get("code", "")
                if best_script:
                    analysis = HARVESTER.analyze_script(best_script)
                    # Cache to disk for future queries
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
                    gt = HARVESTER.format_as_ground_truth(analysis, game_name)
                    print(f"[KNOWLEDGE ROUTER] Successfully extracted live ground truth from Rscripts for '{game_name}'.", flush=True)
                    return f"{gt}\n\n{self.get_bypass_knowledge()}"
        except Exception as r_err:
            print(f"[KNOWLEDGE ROUTER] Rscripts harvester error: {r_err}", flush=True)

        # Step 4: Precision Live Roblox Web Research (DuckDuckGo + Bing TLS Engine)
        try:
            from bot.roblox_live_researcher import RobloxLiveResearcher
            web_gt = RobloxLiveResearcher.build_ai_context_block(game_name, user_prompt)
            if web_gt:
                print(f"[KNOWLEDGE ROUTER] Sourced live web ground truth for '{game_name}'.", flush=True)
                return f"{web_gt}\n\n{self.get_bypass_knowledge()}"
        except Exception as w_err:
            print(f"[KNOWLEDGE ROUTER] Web research notice: {w_err}", flush=True)

        return self.get_bypass_knowledge()


    def get_script_knowledge(self, query: str, top_k: int = 3) -> str:
        """Find small, relevant excerpts from the local Script folder."""
        q = (query or "").lower()
        # No restriction — BluezyGPT is the caller for script queries and it handles game mechanics.
        terms = list(dict.fromkeys(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", q)))
        if not terms:
            return ""

        candidates = []
        for pattern in ("*.txt", "*.lua", "*.luau"):
            candidates.extend(self.rbx_dir.glob(pattern))

        scored = []
        for path in candidates[:200]:
            name = path.name.lower()
            if "bypass" in name or path.parent == self.ui_dir or not path.is_file():
                continue
            try:
                if path.stat().st_size > 512_000:
                    continue
            except OSError:
                continue

            content = self._read_file_cached(path, max_bytes=96_000)
            if not content:
                continue
            safe_lines = content.splitlines()
            normalized = "\n".join(safe_lines)
            low = normalized.lower()
            score = sum(min(low.count(term), 5) for term in terms)
            score += 5 * sum(1 for term in terms if term in name)
            if score:
                scored.append((score, path.name, safe_lines, terms))

        scored.sort(key=lambda item: item[0], reverse=True)
        excerpts = []
        for score, filename, lines, query_terms in scored[:top_k]:
            matching = [i for i, line in enumerate(lines) if any(term in line.lower() for term in query_terms)]
            if not matching:
                continue
            center = matching[0]
            start = max(0, center - 3)
            excerpt = "\n".join(lines[start:start + 24])[:2400]
            excerpts.append(f"[LOCAL SCRIPT REFERENCE: {filename}; relevance={score}]\n{excerpt}")
        return "\n\n".join(excerpts)

    def query_knowledge_base(self, query: str) -> str:
        """
        Synthesizes relevant context based on semantic intent in user query.
        """
        q = query.lower()
        context_parts = []

        # No evasion block — BluezyGPT handles all game mechanic queries including bypass patterns.
        evasion_request = False

        # 2. Check for UI intent
        if any(w in q for w in ["ui", "หน้าต่าง", "ปุ่ม", "เมนู", "glassmorphic", "fluent", "windui", "interface"]):
            context_parts.append(self.get_ui_knowledge(q))

        # 3. Check for specific game mechanics across all 60+ local maps & aliases
        mechanic_info = self.get_mechanic_knowledge(q)
        if mechanic_info:
            context_parts.append(mechanic_info)

        # 4. Check dynamic learned memory (how-to / learning / knowledge)
        learned_facts = []
        for category in ["how_to", "learning", "knowledge", "maps", "user_rules"]:
            section = self._learned_data.get(category, {})
            for key, data in section.items():
                if key.lower() in q or category in q or any(word in q for word in ["how to", "learning", "knowledge", "deobf", "deobfuscate"]):
                    payload = data.get("data", data) if isinstance(data, dict) else data
                    learned_facts.append(f"\n[🧠 LEARNED {category.upper()} FACT: {key}]\n{json.dumps(payload, ensure_ascii=False)}")
        if learned_facts:
            context_parts.extend(learned_facts)

        for map_name, data in self._learned_data.get("maps", {}).items():
            if map_name.lower() in q:
                context_parts.append(f"\n[🧠 LEARNED MAP CONTEXT: {map_name}]\n{json.dumps(data.get('data', {}), ensure_ascii=False)}")

        # 5. Check for official Roblox OpenAPI / Cloud API intent
        # DeepSeek deobf knowledge from Lerning/ folder
        if any(w in q for w in ["deobf", "deobfuscate", "moonveil", "ironbrew", "moonsec", "luraph", "wearedevs", "obfuscator", "decode", "unpack", "ถอดรหัส", "แกะ"]):
            deobf_k = self.get_deobf_knowledge(query)
            if deobf_k:
                context_parts.append(deobf_k)

        if any(w in q for w in ["api", "endpoint", "cloud", "datastore", "data store", "messaging", "asset", "open cloud", "openapi", "publish", "universe"]):
            try:
                from bot.knowledge.roblox_api_indexer import retrieve_roblox_api
                api_doc = retrieve_roblox_api(query, top_k=2)
                if api_doc:
                    context_parts.append(api_doc)
            except Exception:
                pass

        if any(w in q for w in ["lua", "luau", "script", "roblox", "function", "remote", "code", "สคริปต์", "bypass", "hook", "steal", "auto", "farm"]):
            script_context = self.get_script_knowledge(query)
            if script_context:
                context_parts.append(script_context)

        if any(w in q for w in ["skill", "senior", "ozlsr", "protocol", "ทีมsenior"]):
            g_skill = self.get_skill_knowledge("gemini")
            if g_skill:
                context_parts.append(f"[SKILL DIRECTIVES — GEMINI SENIOR]\n{g_skill[:3000]}")
            d_skill = self.get_skill_knowledge("deepseek")
            if d_skill:
                context_parts.append(f"[SKILL DIRECTIVES — DEEPSEEK SENIOR]\n{d_skill[:3000]}")

        # Python deobfuscation & PyArmor knowledge
        if any(w in q for w in ["python", "pyarmor", "marshal", "pyc", "dis", "bytecode", "zlib", "หวานหมู"]):
            py_k_file = BASE_DIR / "bot" / "knowledge" / "python_deobfuscation_knowledge.md"
            if py_k_file.exists():
                context_parts.append(f"[KNOWLEDGE — PYTHON DEOBFUSCATION]\n{self._read_file_cached(py_k_file, max_bytes=8000)}")

        # Web clone & Reconnaissance knowledge
        if any(w in q for w in ["clone", "web clone", "โคลนเว็บ", "โคลน", "godmode", "phantom", "bypass", "source map"]):
            clone_k_file = BASE_DIR / "bot" / "knowledge" / "omnipotent_web_clone_knowledge.md"
            if clone_k_file.exists():
                context_parts.append(f"[KNOWLEDGE — OMNIPOTENT WEB CLONE]\n{self._read_file_cached(clone_k_file, max_bytes=8000)}")

        # REA universal reverse engineering knowledge
        if any(w in q for w in ["rea", "reverse", "ghidra", "hopper", "wakaru", "native", "pe", "elf", "macho", "dotnet"]):
            rea_k_file = BASE_DIR / "bot" / "knowledge" / "rea_reversing_knowledge.md"
            if rea_k_file.exists():
                context_parts.append(f"[KNOWLEDGE — REA UNIVERSAL REVERSING]\n{self._read_file_cached(rea_k_file, max_bytes=8000)}")

        return "\n\n".join(context_parts)



    def get_skill_knowledge(self, provider: str = "gemini") -> str:
        """Retrieves senior team skill instructions (O.Z.L.S.R Protocol) for Gemini or DeepSeek."""
        skill_file = BASE_DIR / "bot" / "knowledge" / f"{provider.lower()}_skill.md"
        if skill_file.exists():
            return self._read_file_cached(skill_file, max_bytes=8000)
        return ""

    def get_deobf_knowledge(self, query: str = "") -> str:
        """Retrieves deobfuscation learning examples from Lerning/ and Lua-Deobfuscator-main/ for DeepSeek."""
        base = BASE_DIR
        lerning_dir = base / "Lerning"
        deobf_dir = base / "Prometheus-WeAre-Devs-Dumper-main" / "Lua-Deobfuscator-main"
        parts = ["[🔬 DEOBFUSCATION KNOWLEDGE BASE — DeepSeek Reference]"]
        q = (query or "").lower()

        # Example obf/deobf pairs from Lerning/
        for fname in ("ตัวอย่าง.txt",):
            p = lerning_dir / fname
            if p.exists():
                snippet = self._read_file_cached(p, max_bytes=6000)
                if snippet:
                    parts.append(f"[EXAMPLE PAIRS: {fname}]\n{snippet[:3000]}")

        # Specific obfuscator learning folders
        for subdir in ("IronBrew", "MoonSec", "WeAreDev", "Moonveil2.0.2", "Luast", "Lularp"):
            sd = lerning_dir / subdir
            if sd.is_dir():
                for f in list(sd.glob("*.lua")) + list(sd.glob("*.txt")) + list(sd.glob("*.luau")):
                    if f.stat().st_size > 300_000:
                        continue
                    snippet = self._read_file_cached(f, max_bytes=4000)
                    if snippet:
                        parts.append(f"[OBFUSCATOR SAMPLE: {subdir}/{f.name}]\n{snippet[:1500]}")
                    break  # one sample per obfuscator type

        # Lua-Deobfuscator-main README / docs
        for fname in ("README.md", "readme.md", "USAGE.md"):
            p = deobf_dir / fname
            if p.exists():
                snippet = self._read_file_cached(p, max_bytes=3000)
                if snippet:
                    parts.append(f"[DEOBFUSCATOR DOCS: {fname}]\n{snippet[:2000]}")
                break

        return "\n\n".join(parts) if len(parts) > 1 else ""

    # =========================================================================
    # SEMANTIC SEARCH (TF-IDF Cosine Similarity) & DYNAMIC REVERSE INDEXER
    # =========================================================================
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        if not text:
            return []
        raw_tokens = re.findall(r"[A-Za-z0-9_]{2,}|[\u0E00-\u0E7F]+", text.lower())
        return raw_tokens

    def _build_corpus(self) -> List[Dict[str, Any]]:
        now = time.time()
        if self._corpus_cache and (now - self._corpus_indexed_time) < 300:
            return self._corpus_cache

        docs: List[Dict[str, Any]] = []

        # 1. Obfuscator samples & learning notes from Lerning/
        target_subdirs = ["IronBrew", "MoonSec", "WeAreDev", "Moonveil2.0.2", "Luast", "Luraph", "Luarmor", "ironveil-main", "Bypass&slove"]
        lerning_dir = BASE_DIR / "Lerning"
        if lerning_dir.is_dir():
            for fp in lerning_dir.glob("*.*"):
                if fp.is_file() and fp.suffix.lower() in (".lua", ".luau", ".txt", ".md"):
                    try:
                        if fp.stat().st_size > 200_000:
                            continue
                        txt = self._read_file_cached(fp, max_bytes=8000)
                        if txt:
                            docs.append({"id": f"lerning:{fp.name}", "title": fp.stem, "text": txt, "tokens": self._tokenize(txt)})
                    except Exception:
                        pass
            for sub in target_subdirs:
                sdir = lerning_dir / sub
                if sdir.is_dir():
                    for fp in list(sdir.glob("*.lua"))[:20] + list(sdir.glob("*.txt"))[:20] + list(sdir.glob("*.luau"))[:20]:
                        try:
                            if fp.stat().st_size > 200_000:
                                continue
                            txt = self._read_file_cached(fp, max_bytes=8000)
                            if txt:
                                docs.append({"id": f"lerning:{sub}:{fp.name}", "title": f"{sub} - {fp.stem}", "text": txt, "tokens": self._tokenize(txt)})
                        except Exception:
                            pass

        # 2. Bypasses and UI frameworks from Script/rbx folder
        if self.rbx_dir.is_dir():
            for fp in list(self.rbx_dir.glob("*.lua"))[:40] + list(self.rbx_dir.glob("*.txt"))[:40] + list(self.rbx_dir.glob("*.luau"))[:40]:
                try:
                    if fp.stat().st_size > 200_000:
                        continue
                    txt = self._read_file_cached(fp, max_bytes=8000)
                    if txt:
                        docs.append({"id": f"rbx:{fp.name}", "title": fp.stem, "text": txt, "tokens": self._tokenize(txt)})
                except Exception:
                    pass
            if self.ui_dir.is_dir():
                for fp in list(self.ui_dir.glob("*.lua"))[:20] + list(self.ui_dir.glob("*.txt"))[:20]:
                    try:
                        if fp.stat().st_size > 200_000:
                            continue
                        txt = self._read_file_cached(fp, max_bytes=8000)
                        if txt:
                            docs.append({"id": f"ui:{fp.name}", "title": f"UI - {fp.stem}", "text": txt, "tokens": self._tokenize(txt)})
                    except Exception:
                        pass

        # 3. Dedicated knowledge markdown files in bot/knowledge
        k_dir = BASE_DIR / "bot" / "knowledge"
        if k_dir.is_dir():
            for fp in k_dir.glob("*.md"):
                txt = self._read_file_cached(fp, max_bytes=12000)
                if txt:
                    docs.append({
                        "id": f"knowledge:{fp.name}",
                        "title": fp.stem,
                        "text": txt,
                        "tokens": self._tokenize(txt)
                    })

        # 4. Learned memory entries
        for cat, entries in self._learned_data.items():
            if isinstance(entries, dict):
                for k, v in entries.items():
                    val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
                    docs.append({
                        "id": f"learned:{cat}:{k}",
                        "title": f"{cat} - {k}",
                        "text": val_str,
                        "tokens": self._tokenize(val_str)
                    })

        self._corpus_cache = docs
        self._corpus_indexed_time = now
        return docs

    def semantic_search(self, query: str, top_k: int = 5) -> List[str]:
        """
        Executes TF-IDF Cosine Similarity semantic retrieval over all indexed corpus documents.
        Uses LRU priority_cache to accelerate repeated queries.
        """
        if not query or not query.strip():
            return []

        cache_key = f"sem_search:{query.strip().lower()}:{top_k}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        corpus = self._build_corpus()
        if not corpus:
            return []

        # Calculate Document Frequency (DF)
        df: Dict[str, int] = {}
        for doc in corpus:
            unique_tokens = set(doc["tokens"])
            for t in unique_tokens:
                df[t] = df.get(t, 0) + 1

        total_docs = len(corpus)
        # Query TF-IDF vector
        q_tf: Dict[str, int] = {}
        for t in q_tokens:
            q_tf[t] = q_tf.get(t, 0) + 1

        q_vec: Dict[str, float] = {}
        q_norm_sq = 0.0
        for t, count in q_tf.items():
            idf = math.log((total_docs + 1) / (df.get(t, 0) + 1)) + 1.0
            weight = count * idf
            q_vec[t] = weight
            q_norm_sq += weight * weight
        q_norm = math.sqrt(q_norm_sq) or 1.0

        scores: List[Tuple[float, Dict[str, Any]]] = []
        for doc in corpus:
            d_tokens = doc["tokens"]
            if not d_tokens:
                continue

            d_tf: Dict[str, int] = {}
            for t in d_tokens:
                if t in q_vec:
                    d_tf[t] = d_tf.get(t, 0) + 1

            if not d_tf:
                continue

            dot_product = 0.0
            d_norm_sq = 0.0
            for t, count in d_tf.items():
                idf = math.log((total_docs + 1) / (df.get(t, 0) + 1)) + 1.0
                d_weight = count * idf
                dot_product += q_vec[t] * d_weight
                d_norm_sq += d_weight * d_weight

            d_norm = math.sqrt(d_norm_sq) or 1.0
            cosine_sim = dot_product / (q_norm * d_norm)
            if cosine_sim > 0.05:
                scores.append((cosine_sim, doc))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, doc in scores[:top_k]:
            sample_text = doc["text"][:1800]
            snippet = f"[{doc['id']} | Relevance: {sim:.3f}]\n{sample_text}"
            results.append(snippet)

        self._cache_put(cache_key, results)
        return results

    def auto_index_reverse_results(self, result_dir: Optional[Path | str] = None) -> int:
        """
        Scans outputs and logs for decompiled / deobfuscated outputs and updates
        the learned memory and semantic corpus automatically.
        """
        target_dir = Path(result_dir) if result_dir else (BASE_DIR / "output")
        if not target_dir.exists():
            target_dir = BASE_DIR / "Lerning" / "ตัวเทียบ" / "output"
        if not target_dir.exists():
            return 0

        indexed_count = 0
        for fp in target_dir.glob("*.*"):
            if fp.suffix.lower() in (".lua", ".luau", ".json", ".txt", ".md"):
                try:
                    if fp.stat().st_size > 1_000_000:
                        continue
                    content = self._read_file_cached(fp, max_bytes=8000)
                    if content:
                        key = f"auto_res_{fp.stem}"
                        self.learn_new_context("reverse_results", key, {
                            "filename": fp.name,
                            "path": str(fp),
                            "preview": content[:1500],
                            "indexed_at": time.time()
                        })
                        indexed_count += 1
                except Exception:
                    pass

        self._corpus_indexed_time = 0.0  # Force corpus rebuild next search
        return indexed_count

    def get_gap_report(self) -> Dict[str, Any]:
        """
        Analyzes knowledge base coverage across VM architectures, obfuscation families,
        and tool APIs to surface top missing categories for the autonomous idle reverser.
        """
        known_families = {
            "LURAPH": ["luraph", "lph", "qz"],
            "MOONSEC": ["moonsec", "moon"],
            "CLYDE_VM": ["clyde", "two_tier"],
            "IRONBREW": ["ironbrew", "ib"],
            "MOONVEIL": ["moonveil"],
            "WEAREDEVS": ["wearedevs", "prom"],
            "PYARMOR": ["pyarmor", "pyc", "marshal"],
            "ROBLOX_NATIVE": ["cff", "devirtualize", "remoteevent"]
        }

        corpus = self._build_corpus()
        corpus_texts = " ".join(d["text"].lower() for d in corpus)

        stats: Dict[str, int] = {}
        for fam, keywords in known_families.items():
            count = sum(corpus_texts.count(kw) for kw in keywords)
            stats[fam] = count

        gaps = [fam for fam, cnt in stats.items() if cnt < 5]
        coverage_pct = round((len(known_families) - len(gaps)) / len(known_families) * 100, 1)

        return {
            "total_indexed_documents": len(corpus),
            "architecture_counts": stats,
            "top_gaps": gaps,
            "coverage_percentage": coverage_pct,
            "recommended_missions": [f"harvest_{g.lower()}_samples" for g in gaps[:3]],
            "last_analyzed": time.time()
        }

    def find_relevant_context(self, query: str) -> str:
        """
        Unified context retrieval combining semantic vector search and intent heuristics.
        """
        parts = []
        sem_matches = self.semantic_search(query, top_k=3)
        if sem_matches:
            parts.append("[⚡ HIGH-RELEVANCE SEMANTIC MEMORY MATCHES]")
            parts.extend(sem_matches)

        heuristic_context = self.query_knowledge_base(query)
        if heuristic_context:
            parts.append(heuristic_context)

        return "\n\n".join(parts)


# Singleton
ROUTER = KnowledgeRouter()
