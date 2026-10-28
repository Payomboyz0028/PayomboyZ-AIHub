#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ KNOWLEDGE BASE — AST & CODE INTELLIGENCE INDEXER
====================================================================
Scans and indexes 46+ production files across:
- Script/rbx folder/ (Map scripts, bypasses, logins, core libraries)
- Script/rbx folder/UI/ (Obsidian Glassmorphic 2, Fluent, WindUI, UILibrary)
Outputs:
- bot/knowledge/code_registry.json
- bot/knowledge/ui_catalog.json
- bot/knowledge/business_catalog.json
====================================================================
"""

import os
import re
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Set

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RBX_DIR = BASE_DIR / "Script" / "rbx folder"
UI_DIR = RBX_DIR / "UI"
KNOWLEDGE_DIR = BASE_DIR / "bot" / "knowledge"


def extract_ui_catalog() -> Dict[str, Any]:
    """Indexes UI libraries to build structured UI_CATALOG."""
    catalog = {
        "CreateWindow": {
            "name": "CreateWindow",
            "type": "UI.Window",
            "library": "Obsidian Glassmorphic 2.0 / Fluent",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": ["Title", "SubTitle", "TabWidth", "Size", "Acrylic", "Theme"],
            "usage": 'local Window = Fluent:CreateWindow({ Title = "PAYOMBØYZ HUB", SubTitle = "CRIMSON V4", TabWidth = 160, Size = UDim2.fromOffset(920, 600) })',
            "dependencies": ["Fluent", "TweenService", "UserInputService"]
        },
        "AddTab": {
            "name": "AddTab",
            "type": "UI.Tab",
            "library": "Obsidian Glassmorphic 2.0 / Fluent",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": ["Title", "Icon"],
            "usage": 'local Tab = Window:AddTab({ Title = "Main", Icon = "rbxassetid://10723346959" })',
            "dependencies": ["Window"]
        },
        "AddSection": {
            "name": "AddSection",
            "type": "UI.Section",
            "library": "Obsidian Glassmorphic 2.0 / Fluent",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": ["Title"],
            "usage": 'local Section = Tab:AddSection("Auto Farm Configuration")',
            "dependencies": ["Tab"]
        },
        "AddToggle": {
            "name": "AddToggle",
            "type": "UI.Toggle",
            "library": "Obsidian Glassmorphic 2.0 / Fluent",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": ["Id", "Title", "Default", "Callback"],
            "usage": 'local Toggle = Tab:AddToggle("AutoFarmToggle", { Title = "Auto Farm", Default = false, Callback = function(v) _G.AutoFarm = v end })',
            "dependencies": ["Tab", "ObsidianGlassEngine.Options"]
        },
        "AddSlider": {
            "name": "AddSlider",
            "type": "UI.Slider",
            "library": "Obsidian Glassmorphic 2.0 / Fluent",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": ["Id", "Title", "Min", "Max", "Default", "Rounding", "Callback"],
            "usage": 'local Slider = Tab:AddSlider("WalkSpeedSlider", { Title = "WalkSpeed", Min = 16, Max = 250, Default = 16, Rounding = 0, Callback = function(v) ... end })',
            "dependencies": ["Tab", "ObsidianGlassEngine.Options"]
        },
        "AddDropdown": {
            "name": "AddDropdown",
            "type": "UI.Dropdown",
            "library": "Obsidian Glassmorphic 2.0 / Fluent",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": ["Id", "Title", "Values", "Default", "Multi", "Callback"],
            "usage": 'local Dropdown = Tab:AddDropdown("ZoneSelect", { Title = "Select Zone", Values = {"Zone 1", "Zone 2"}, Default = "Zone 1", Multi = false, Callback = function(v) ... end })',
            "dependencies": ["Tab", "ObsidianGlassEngine.Options"]
        },
        "AddButton": {
            "name": "AddButton",
            "type": "UI.Button",
            "library": "Obsidian Glassmorphic 2.0 / Fluent",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": ["Title", "Callback"],
            "usage": 'local Button = Tab:AddButton({ Title = "Teleport Spawn", Callback = function() ... end })',
            "dependencies": ["Tab"]
        },
        "AddInput": {
            "name": "AddInput",
            "type": "UI.Input",
            "library": "Obsidian Glassmorphic 2.0 / Fluent",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": ["Id", "Title", "Default", "Placeholder", "Numeric", "Finished", "Callback"],
            "usage": 'local Input = Tab:AddInput("CustomKey", { Title = "Input Key", Default = "", Placeholder = "Key here...", Finished = true, Callback = function(v) ... end })',
            "dependencies": ["Tab"]
        },
        "AddKeybind": {
            "name": "AddKeybind",
            "type": "UI.Keybind",
            "library": "Obsidian Glassmorphic 2.0 / Fluent",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": ["Id", "Title", "Mode", "Default", "Callback"],
            "usage": 'local Keybind = Tab:AddKeybind("ToggleUIKey", { Title = "Toggle UI", Mode = "Toggle", Default = "RightControl", Callback = function() ... end })',
            "dependencies": ["Tab"]
        },
        "Notify": {
            "name": "Notify",
            "type": "UI.Notification",
            "library": "Obsidian Glassmorphic 2.0 / Fluent",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": ["Title", "Content", "SubContent", "Duration"],
            "usage": 'Fluent:Notify({ Title = "PAYOMBØYZ HUB", Content = "Loaded successfully!", Duration = 5 })',
            "dependencies": ["Fluent"]
        },
        "strikeLightning": {
            "name": "strikeLightning",
            "type": "UI.Effect",
            "library": "Crimson Obsidian FX Engine",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": ["targetFrame", "numSegments"],
            "usage": "strikeLightning(MainShell, 8)",
            "dependencies": ["TweenService", "UIStroke"]
        },
        "stopAllScriptOperations": {
            "name": "stopAllScriptOperations",
            "type": "Lifecycle.Cleanup",
            "library": "PayomboyZ Core Runtime",
            "source": "UI/Obsidain_Glassmophic2.txt",
            "parameters": [],
            "usage": "stopAllScriptOperations()",
            "dependencies": ["Maid", "trackedConnections", "trackedThreads"]
        },

        # --- MacLib (macOS Glassmorphic UI Library) ---
        "MacLib_Window": {
            "name": "MacLib:Window",
            "type": "UI.Window",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Title", "Subtitle", "Size", "DragStyle", "DisabledWindowControls", "ShowUserInfo", "Keybind", "AcrylicBlur"],
            "usage": 'local MacLib = loadstring(game:HttpGet("https://github.com/biggaboy212/Maclib/releases/latest/download/maclib.txt"))()\nlocal Window = MacLib:Window({ Title = "PAYOMBØYZ HUB", Subtitle = "MacLib Edition", Size = UDim2.fromOffset(868, 650), DragStyle = 1, ShowUserInfo = true, Keybind = Enum.KeyCode.RightControl, AcrylicBlur = true })',
            "dependencies": ["MacLib", "UserInputService", "TweenService"]
        },
        "MacLib_TabGroup": {
            "name": "Window:TabGroup",
            "type": "UI.TabGroup",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": [],
            "usage": "local tabGroups = { TabGroup1 = Window:TabGroup() }",
            "dependencies": ["MacLib_Window"]
        },
        "MacLib_Tab": {
            "name": "TabGroup:Tab",
            "type": "UI.Tab",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Name", "Image"],
            "usage": 'local Tab = tabGroups.TabGroup1:Tab({ Name = "Main", Image = "rbxassetid://18821914323" })',
            "dependencies": ["MacLib_TabGroup"]
        },
        "MacLib_Section": {
            "name": "Tab:Section",
            "type": "UI.Section",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Side"],
            "usage": 'local Section = Tab:Section({ Side = "Left" })',
            "dependencies": ["MacLib_Tab"]
        },
        "MacLib_Header": {
            "name": "Section:Header",
            "type": "UI.Header",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Name"],
            "usage": 'Section:Header({ Name = "Automation Settings" })',
            "dependencies": ["MacLib_Section"]
        },
        "MacLib_Button": {
            "name": "Section:Button",
            "type": "UI.Button",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Name", "Callback"],
            "usage": 'Section:Button({ Name = "Execute Teleport", Callback = function() print("Teleported!") end })',
            "dependencies": ["MacLib_Section"]
        },
        "MacLib_Toggle": {
            "name": "Section:Toggle",
            "type": "UI.Toggle",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Name", "Default", "Callback"],
            "usage": 'Section:Toggle({ Name = "Auto Farm", Default = false, Callback = function(v) _G.AutoFarm = v end })',
            "dependencies": ["MacLib_Section"]
        },
        "MacLib_Slider": {
            "name": "Section:Slider",
            "type": "UI.Slider",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Name", "Default", "Minimum", "Maximum", "Precision", "DisplayMethod", "Callback"],
            "usage": 'Section:Slider({ Name = "Speed", Default = 16, Minimum = 16, Maximum = 250, Precision = 1, DisplayMethod = "Value", Callback = function(v) ... end })',
            "dependencies": ["MacLib_Section"]
        },
        "MacLib_Dropdown": {
            "name": "Section:Dropdown",
            "type": "UI.Dropdown",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Name", "Multi", "Required", "Options", "Default", "Callback"],
            "usage": 'Section:Dropdown({ Name = "Select Target", Multi = false, Required = true, Options = {"Enemy A", "Enemy B"}, Default = "Enemy A", Callback = function(choice) ... end })',
            "dependencies": ["MacLib_Section"]
        },
        "MacLib_Input": {
            "name": "Section:Input",
            "type": "UI.Input",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Name", "Placeholder", "AcceptedCharacters", "Callback"],
            "usage": 'Section:Input({ Name = "Webhook URL", Placeholder = "https://discord.com/...", AcceptedCharacters = "All", Callback = function(text) ... end })',
            "dependencies": ["MacLib_Section"]
        },
        "MacLib_Colorpicker": {
            "name": "Section:Colorpicker",
            "type": "UI.Colorpicker",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Name", "Default", "Callback"],
            "usage": 'Section:Colorpicker({ Name = "ESP Color", Default = Color3.fromRGB(255, 0, 0), Callback = function(c) ... end })',
            "dependencies": ["MacLib_Section"]
        },
        "MacLib_Dialog": {
            "name": "Window:Dialog",
            "type": "UI.Dialog",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Title", "Description", "Buttons"],
            "usage": 'Window:Dialog({ Title = "Warning", Description = "Reset all stats?", Buttons = { { Name = "Confirm", Callback = function() end }, { Name = "Cancel" } } })',
            "dependencies": ["MacLib_Window"]
        },
        "MacLib_Notify": {
            "name": "Window:Notify",
            "type": "UI.Notification",
            "library": "MacLib",
            "source": "UI/Maclib-main/Example.lua",
            "parameters": ["Title", "Description", "Lifetime"],
            "usage": 'Window:Notify({ Title = "PAYOMBØYZ HUB", Description = "Script injected successfully!", Lifetime = 5 })',
            "dependencies": ["MacLib_Window"]
        },

        # --- In-Game IDE (Dex-Based CodeFrame) ---
        "InGame_IDE_New": {
            "name": "IDEModule.CodeFrame.new",
            "type": "UI.Editor",
            "library": "In-Game IDE (Dex Explorer Script Engine)",
            "source": "UI/In-Game-IDE-main/update8/IDEModule.lua",
            "parameters": [],
            "usage": 'local IDEModule = require(script.IDEModule)\nlocal IDE = IDEModule.CodeFrame.new()\nIDE.Gui.Parent = targetTabFrame\nIDE:SetText("-- In-Game Luau IDE\\nprint(\'Ready!\')")',
            "dependencies": ["IDEModule", "TextService", "UserInputService"]
        },
        "InGame_IDE_SetText": {
            "name": "IDE:SetText",
            "type": "UI.EditorMethod",
            "library": "In-Game IDE",
            "source": "UI/In-Game-IDE-main/update8/IDEModule.lua",
            "parameters": ["text"],
            "usage": 'IDE:SetText("local x = 10\\nprint(x)")',
            "dependencies": ["InGame_IDE_New"]
        },
        "InGame_IDE_GetText": {
            "name": "IDE:GetText",
            "type": "UI.EditorMethod",
            "library": "In-Game IDE",
            "source": "UI/In-Game-IDE-main/update8/IDEModule.lua",
            "parameters": [],
            "usage": "local sourceCode = IDE:GetText()",
            "dependencies": ["InGame_IDE_New"]
        },

        # --- WindUI (Footagesus) ---
        "WindUI_CreateWindow": {
            "name": "WindUI:CreateWindow",
            "type": "UI.Window",
            "library": "WindUI",
            "source": "UI/WindUI.txt",
            "parameters": ["Title", "Icon", "Author", "Folder", "Transparent", "Theme"],
            "usage": 'local WindUI = loadstring(game:HttpGet("https://tree-hub.vercel.app/api/UI/WindUI"))()\nlocal Window = WindUI:CreateWindow({ Title = "PAYOMBØYZ HUB", Icon = "rbxassetid://10723346959", Author = "PAYOMBØYZ", Folder = "PayomboyZ", Transparent = true, Theme = "Dark" })',
            "dependencies": ["WindUI", "TweenService"]
        },

        # --- Luau Bypass & Anti-Cheat Metatable Hooking ---
        "Bypass_HookNamecall": {
            "name": "hookmetamethod(__namecall)",
            "type": "Security.Bypass",
            "library": "Executor Core Metatable Hook",
            "source": "Security/Anti-Cheat Bypass Standard",
            "parameters": ["object", "method", "hook_function"],
            "usage": 'local oldNamecall\noldNamecall = hookmetamethod(game, "__namecall", newcclosure(function(self, ...)\n    local method = getnamecallmethod()\n    if method == "Kick" and not checkcaller() then\n        return\n    end\n    return oldNamecall(self, ...)\nend))',
            "dependencies": ["hookmetamethod", "newcclosure", "getnamecallmethod", "checkcaller"]
        },
        "Bypass_PropertySpoof": {
            "name": "Property Spoofing (__index / __newindex)",
            "type": "Security.Bypass",
            "library": "Executor Core Metatable Hook",
            "source": "Security/WalkSpeed JumpPower Spoofing",
            "parameters": ["targetInstance", "property", "spoofedValue"],
            "usage": 'local oldIndex\noldIndex = hookmetamethod(game, "__index", newcclosure(function(self, key)\n    if not checkcaller() and self:IsA("Humanoid") then\n        if key == "WalkSpeed" then return 16 end\n        if key == "JumpPower" then return 50 end\n    end\n    return oldIndex(self, key)\nend))',
            "dependencies": ["hookmetamethod", "newcclosure", "checkcaller"]
        },
        "Bypass_AntiRemoteFlag": {
            "name": "Remote Telemetry Interception",
            "type": "Security.Bypass",
            "library": "Executor Core Metatable Hook",
            "source": "Security/Remote Event Filter",
            "parameters": ["blacklistedRemotes"],
            "usage": 'local BLOCKED = { ["SecurityCheck"] = true, ["AntiCheat"] = true, ["BanEvent"] = true, ["Telemetry"] = true }\nlocal oldFire\noldFire = hookfunction(Instance.new("RemoteEvent").FireServer, newcclosure(function(self, ...)\n    if BLOCKED[self.Name] and not checkcaller() then\n        return\n    end\n    return oldFire(self, ...)\nend))',
            "dependencies": ["hookfunction", "newcclosure", "checkcaller"]
        }
    }
    return catalog


def extract_business_catalog() -> Dict[str, Any]:
    """Extracts business, pricing, terms, and executor setup info."""
    business = {
        "pricing": {
            "vip_package": {
                "name": "VIP Package",
                "price_thb": 89,
                "duration": "3 months",
                "has_free_key": True,
                "maps": [
                    "Capybara Vs Plant",
                    "Anime Card Farm",
                    "Attack On Titan Revolution (AOTR)",
                    "Arena Sniper",
                    "Gakuran",
                    "99Nights at the forest",
                    "Grow a Chicken FIGHTER!",
                    "Steal An Anime Egg",
                    "Greedy Grower",
                    "Blox Fruit",
                    "Ride A Pet"
                ]
            },
            "vvip_package": {
                "name": "VVIP Package",
                "price_thb": 129,
                "duration": "3 months",
                "has_free_key": False,
                "includes_vip_maps": True,
                "maps": [
                    "Roll Anime To Fight",
                    "Mine a Mountain",
                    "Murder Mystery 2 (MM2)",
                    "Steal An Egg (ขโมยไข่)",
                    "Anime Expedetion (AE)",
                    "Iron Soul: Dungeon",
                    "Anime Dice"
                ]
            }
        },
        "urls": {
            "official_store": "https://payomboyz.rexzy.xyz/",
            "free_key_portal": "https://payomboyz333.github.io/Anime-Card-Farm/",
            "free_scripts_channel": "〔🆓〕・สคริปฟรี"
        },
        "policies": [
            {
                "topic": "No Key Sharing",
                "rule": "1 คีย์ต่อ 1 คนเท่านั้น ห้ามหารหรือแจกจ่ายคีย์ ระบบตรวจสอบพบจะระงับคีย์ทันทีโดยไม่มีการคืนเงิน"
            },
            {
                "topic": "Risk & Ban Responsibility",
                "rule": "การรันสคริปต์มีความเสี่ยงต่อระบบตรวจจับของ Roblox ผู้ใช้ต้องยอมรับความเสี่ยงด้วยตนเอง แนะนำให้ใช้รหัสสำรอง (ไก่ตัน) เสมอ"
            },
            {
                "topic": "No Reverse Engineering or Leaking",
                "rule": "ห้ามแกะโค้ด ดัดแปลง UI หรือ bypass สคริปต์ของทางร้านเพื่อแจกจ่าย พบเจอดำเนินการแบน Blacklist ถาวร"
            },
            {
                "topic": "Refund Policy",
                "rule": "No Refund เมื่อชำระเงินและรับคีย์แล้วไม่สามารถขอคืนเงินหรือเปลี่ยนคีย์ได้ทุกกรณี เว้นแต่เป็นข้อผิดพลาดจากระบบของทางร้านเอง"
            }
        ]
    }
    return business


def scan_functions_and_remotes() -> Dict[str, Any]:
    """Scans all script files to index Functions, Remotes, and Services."""
    fn_map = {}
    remote_map = {}
    service_map = {}
    patterns = []

    # Regex patterns
    fn_pat1 = re.compile(r'(?:local\s+)?function\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)')
    fn_pat2 = re.compile(r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\s*=\s*function\s*\(([^)]*)\)')
    fn_pat3 = re.compile(r'([a-zA-Z0-9_]+):([a-zA-Z0-9_]+)\s*=\s*function\s*\(([^)]*)\)')
    
    remote_pat = re.compile(r'([a-zA-Z0-9_]+):(FireServer|InvokeServer)\s*\(([^)]*)\)')
    svc_pat = re.compile(r'game:GetService\(["\']([^"\']+)["\']\)')

    if not RBX_DIR.exists():
        return {"functions": {}, "remotes": {}, "services": {}, "patterns": []}

    for f_path in RBX_DIR.glob("*.txt"):
        name = f_path.name
        try:
            content = f_path.read_text(encoding="utf-8", errors="ignore")
            # Skip heavily obfuscated single-line bytecode dumps
            if len(content.splitlines()) < 10 and len(content) > 50000:
                continue

            # 1. Services
            for s in svc_pat.findall(content):
                service_map.setdefault(s, []).append(name)

            # 2. Remotes
            for r_var, r_method, r_args in remote_pat.findall(content):
                key = f"{r_var}:{r_method}"
                if key not in remote_map:
                    remote_map[key] = {
                        "remote_var": r_var,
                        "call_type": r_method,
                        "source": name,
                        "sample_args": r_args[:80].strip()
                    }

            # 3. Functions
            for match in fn_pat1.finditer(content):
                fn_name, args = match.groups()
                if len(fn_name) > 2 and fn_name not in fn_map:
                    fn_map[fn_name] = {
                        "name": fn_name,
                        "parameters": [a.strip() for a in args.split(",") if a.strip()],
                        "source": name,
                        "type": "Global/Local Function"
                    }
                    if len(fn_map) > 250:
                        break

            for match in fn_pat2.finditer(content):
                tbl, fn_name, args = match.groups()
                full_name = f"{tbl}.{fn_name}"
                if full_name not in fn_map:
                    fn_map[full_name] = {
                        "name": full_name,
                        "parameters": [a.strip() for a in args.split(",") if a.strip()],
                        "source": name,
                        "type": "Module Method"
                    }
                    if len(fn_map) > 400:
                        break

        except Exception as e:
            continue

    return {
        "functions": fn_map,
        "remotes": remote_map,
        "services": {k: list(set(v))[:5] for k, v in service_map.items()},
        "total_functions_indexed": len(fn_map),
        "total_remotes_indexed": len(remote_map)
    }


def build_all_catalogs():
    """Builds and serializes all 3 catalog JSON files."""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    print("[+] Building UI Catalog...")
    ui_catalog = extract_ui_catalog()
    with open(KNOWLEDGE_DIR / "ui_catalog.json", "w", encoding="utf-8") as f:
        json.dump(ui_catalog, f, indent=2, ensure_ascii=False)
    print(f"    Saved {len(ui_catalog)} UI components to ui_catalog.json")

    print("[+] Building Business Catalog...")
    business_catalog = extract_business_catalog()
    with open(KNOWLEDGE_DIR / "business_catalog.json", "w", encoding="utf-8") as f:
        json.dump(business_catalog, f, indent=2, ensure_ascii=False)
    print("    Saved pricing, packages, and policies to business_catalog.json")

    print("[+] Building Code & Remote Registry...")
    code_registry = scan_functions_and_remotes()
    with open(KNOWLEDGE_DIR / "code_registry.json", "w", encoding="utf-8") as f:
        json.dump(code_registry, f, indent=2, ensure_ascii=False)
    print(f"    Saved {code_registry['total_functions_indexed']} functions and {code_registry['total_remotes_indexed']} remotes to code_registry.json")


if __name__ == "__main__":
    build_all_catalogs()
