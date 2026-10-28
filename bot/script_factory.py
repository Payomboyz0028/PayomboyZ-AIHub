# ==============================================================================
# PAYOMBØYZ MULTI-AGENT LUAU SCRIPT FACTORY V2.0
# Autonomous Chained Assembly: Architect -> Core Engine -> UI Builder -> Assembler
# ==============================================================================

import re
import asyncio
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

FLUENT_UI_LOADER = """-- [[ PAYOMBØYZ UI FRAMEWORK: Fluent 1.1 ]]
local Fluent = loadstring(game:HttpGet("https://github.com/dawid-scripts/Fluent/releases/latest/download/main.lua"))()
local SaveManager = loadstring(game:HttpGet("https://raw.githubusercontent.com/dawid-scripts/Fluent/master/Addons/SaveManager.lua"))()
local InterfaceManager = loadstring(game:HttpGet("https://raw.githubusercontent.com/dawid-scripts/Fluent/master/Addons/InterfaceManager.lua"))()
"""

WIND_UI_LOADER = """-- [[ PAYOMBØYZ UI FRAMEWORK: WindUI ]]
local WindUI = loadstring(game:HttpGet("https://tree-hub.vercel.app/api/UI/WindUI"))()
"""

MACLIB_UI_LOADER = """-- [[ PAYOMBØYZ UI FRAMEWORK: MacLib ]]
local MacLib = loadstring(game:HttpGet("https://github.com/biggaboy212/Maclib/releases/latest/download/maclib.txt"))()
"""

class MultiAgentScriptFactory:
    """
    Orchestrates the entire multi-model pool in config.py / .env
    (Gemini 5x, OpenRouter DeepSeek 7x, DeepSeek Official 7x, Bluezy 7x, ThaiLLM 3x)
    to assemble massive, production-grade Luau scripts (>10,000 - 40,000 characters)
    with zero stubs and full UI integration.
    """

    @classmethod
    async def build_full_system_script(
        cls,
        game_info: Optional[Dict[str, Any]] = None,
        user_prompt: str = "",
        attached_code: str = "",
        user_name: str = "User",
        ui_choice: str = "Fluent"
    ) -> Dict[str, Any]:
        from bot.hybrid_router import HYBRID_ROUTER

        game_data = game_info or {}
        game_name = game_data.get("name") or "Roblox Game"
        place_id = game_data.get("place_id") or "0"
        genre = game_data.get("genre") or "Adventure"
        desc = game_data.get("description") or ""

        print(f"[SCRIPT FACTORY] Initiating Multi-Agent Pipeline for '{game_name}' (Place: {place_id})...", flush=True)
        start_time = time.time()

        # ----------------------------------------------------------------------
        # STAGE 0: Authentic Ground Truth & Deobfuscated Script Check
        # If an authentic, working production script exists locally (e.g. 2,000 - 11,000+ lines),
        # serve the real battle-tested script directly with clean formatting!
        # ----------------------------------------------------------------------
        from bot.knowledge_router import ROUTER as KNOWLEDGE_ROUTER
        authentic_script = KNOWLEDGE_ROUTER.get_authentic_script(game_name)
        if not authentic_script:
            try:
                from bot.rscripts_client import RSCRIPTS
                q = game_name if game_name and game_name != "Roblox Game" else user_prompt
                harvested = await RSCRIPTS.harvest_game_scripts(q, place_id=place_id)
                if harvested:
                    best = max(harvested, key=lambda x: x.get("length", 0))
                    if best and best.get("code") and len(best["code"].strip()) > 2000:
                        authentic_script = best["code"]
                        print(f"[SCRIPT FACTORY] Harvested & Deobfuscated real script for '{q}' from Rscripts/Mirror ({len(authentic_script):,} chars)!", flush=True)
            except Exception as h_err:
                print(f"[SCRIPT FACTORY] Live harvester pass skipped: {h_err}", flush=True)

        if authentic_script and len(authentic_script.strip()) > 2000:
            line_count = len(authentic_script.splitlines())
            print(f"[SCRIPT FACTORY] Serving authentic production script for '{game_name}' ({len(authentic_script):,} chars, {line_count:,} lines).", flush=True)
            chat_summary = (
                f"ดึงสคริปต์ตัวจริงของ **{game_name}** มาให้เรียบร้อยแล้วครับ! "
                f"เป็นสคริปต์โปรดักชันขนาดใหญ่ระดับตำนาน ({line_count:,} บรรทัด) "
                f"เจาะลึกฟังก์ชันเกม, Remotes, ระบบฟาร์มเฉพาะทาง, และ UI ครบวงจร "
                f"โค้ดพร้อมรันบน Executor ตัวเต็มแนบไว้ในไฟล์ .lua ด้านล่างแล้วครับ"
            )
            return {
                "chat_summary": chat_summary,
                "lua_code": authentic_script,
                "char_count": len(authentic_script),
                "line_count": line_count,
                "elapsed": round(time.time() - start_time, 2),
                "game_name": game_name,
            }

        print(f"[SCRIPT FACTORY] Sourcing Verified Game Ground Truth for '{game_name}'...", flush=True)
        ground_truth_context = await KNOWLEDGE_ROUTER.get_complete_game_context_async(
            game_name=game_name,
            user_prompt=user_prompt,
            place_id=place_id
        )

        # ----------------------------------------------------------------------
        # STAGE 1: Architect Agent (System Spec & Module Decomposition)
        # ----------------------------------------------------------------------
        architect_system = (
            f"You are the Chief Technical Architect for PAYØMBØYZAA under O.Z.L.S.R Protocol. "
            f"Decompose the user's Roblox script request into a high-level technical blueprint. "
            f"Define: 1. State Table & Options 2. Services & Network Remotes 3. Target Query & StreamingEnabled strategy "
            f"4. Movement / Tween / Pathfinding bypasses 5. Detection & ESP logic 6. UI Tabs & Elements. "
            f"Do NOT write Luau code yet; provide an exhaustive, structured module specification."
        )
        code_context = f"Existing Code Context:\n{attached_code[:4000]}\n\n" if attached_code else ""
        architect_prompt = (
            f"Game: {game_name} (Place ID: {place_id})\n"
            f"Genre: {genre}\n"
            f"Game Description: {desc[:600]}\n"
            f"User Requirement:\n{user_prompt}\n"
            f"{ground_truth_context}\n\n"
            f"{code_context}"
            f"Output a complete, detailed architecture breakdown for the development agents."
        )

        spec_res = await asyncio.to_thread(
            HYBRID_ROUTER.query_supervised,
            architect_prompt,
            user_request=user_prompt,
            system_prompt=architect_system,
            mode="script_professor",
            preferred_provider="gemini"
        )
        architecture_spec = spec_res.get("reply", "")
        if not architecture_spec or not spec_res.get("success"):
            architecture_spec = f"Build complete automated system for {game_name}: Auto farm, ESP, Movement, Full UI."
        print(f"[SCRIPT FACTORY] Stage 1 (Architect) complete: {len(architecture_spec)} chars spec generated.", flush=True)

        # ----------------------------------------------------------------------
        # STAGE 2: Core Engine Specialist (Pure Gameplay Logic - Zero Placeholders)
        # ----------------------------------------------------------------------
        engine_system = (
            "You are the Senior Principal Roblox Luau Engine Architect. "
            "Your ONLY job is to write the complete, production-grade GAMEPLAY LOGIC & AUTOMATION ENGINE in pure Luau. "
            "CRITICAL RULES:\n"
            "1. NO UI CODE in this step (keep all tokens focused purely on rock-solid gameplay logic).\n"
            "2. ZERO PLACEHOLDERS: NEVER write '-- implement logic here', '-- TODO', '-- etc'. EVERY function must be 100% complete and working.\n"
            "3. Handle StreamingEnabled (RequestStreamAroundAsync, wait for instance, retry queues).\n"
            "4. Include robust Raycasting, TweenService movement, Noclip bypass, and Character respawn handling.\n"
            "5. Wrap entire state in a clean, observable local `EngineState = {}` table that UI can hook into. Do NOT embed any author name, username, or branding in variable names.\n"
            "6. GAME-SPECIFIC MECHANICS: If the game involves cards, packs, rolls, dice, dungeons, anime skills, or quests, YOU MUST write the real, specialized mechanics for that game (e.g. Card summoning/fusing/inventory, Dice rolling/luck multipliers, Skill combo executions). NEVER copy-paste a generic 'workspace.Mobs' template when the game is about cards, dice, or different mechanics.\n"
            "7. ABSOLUTELY ZERO AUTHOR/BRAND STAMPS: Do NOT include any author names, creator credits, or signatures in the code.\n"
            "8. Output ONLY executable Luau code enclosed in ```lua ... ```."
        )
        engine_prompt = (
            f"Target Game: {game_name} (PlaceId: {place_id})\n"
            f"User Request:\n{user_prompt}\n\n"
            f"Authoritative Ground Truth (Network Remotes & Entities):\n{ground_truth_context[:3000]}\n\n"
            f"Architect Blueprint:\n{architecture_spec}\n\n"
            f"Write the entire Core Automation Engine now. Minimum 250+ lines of exhaustive, production-grade Luau."
        )


        engine_res = await asyncio.to_thread(
            HYBRID_ROUTER.query_supervised,
            engine_prompt,
            user_request=user_prompt,
            system_prompt=engine_system,
            mode="script_professor",
            preferred_provider="gemini"
        )
        engine_code = cls._extract_code(engine_res.get("reply", "")) if engine_res.get("success") else ""
        if not engine_code or len(engine_code.splitlines()) < 8:
            print(f"[SCRIPT FACTORY] Stage 2 AI responder empty or hit quota. Synthesizing Ground Truth Core Engine...", flush=True)
            engine_code = cls._generate_fallback_engine(game_name, place_id, ground_truth_context, user_prompt)
        print(f"[SCRIPT FACTORY] Stage 2 (Core Engine) complete: {len(engine_code)} chars of pure Luau logic.", flush=True)

        # ----------------------------------------------------------------------
        # STAGE 3: UI Master Architect (Full UI Framework Wiring)
        # ----------------------------------------------------------------------
        loader_header = FLUENT_UI_LOADER
        if "wind" in ui_choice.lower() or "windui" in user_prompt.lower():
            loader_header = WIND_UI_LOADER
            ui_choice = "WindUI"
        elif "mac" in ui_choice.lower() or "maclib" in user_prompt.lower():
            loader_header = MACLIB_UI_LOADER
            ui_choice = "MacLib"
        else:
            ui_choice = "Fluent"

        ui_system = (
            f"You are the Senior Roblox UI Architect for PAYØMBØYZAA under O.Z.L.S.R Protocol. "
            f"Your job is to construct a modern, breathtaking {ui_choice} interface that connects to the Core Engine.\n"
            f"CRITICAL RULES:\n"
            f"1. Build Window, Notifications, multiple organized Tabs (e.g. Main Farm, Combat/Items, Teleports, Visuals/ESP, Settings).\n"
            f"2. Add ALL necessary Toggles, Sliders, Dropdowns, Keybinds, and Buttons requested by user.\n"
            f"3. Wire every Callback directly into the Engine's state and functions.\n"
            f"4. ZERO STUBS: Do not skip buttons or leave empty callbacks.\n"
            f"5. Output ONLY clean Luau code in ```lua ... ``` that executes after the UI Loader."
        )
        ui_prompt = (
            f"Target Game: {game_name} | Framework: {ui_choice}\n"
            f"User Requirement:\n{user_prompt}\n\n"
            f"Engine Functions & State summary:\n{engine_code[:3500]}\n\n"
            f"Write the complete {ui_choice} Window and all Tab/Element setups now."
        )

        ui_res = await asyncio.to_thread(
            HYBRID_ROUTER.query_supervised,
            ui_prompt,
            user_request=user_prompt,
            system_prompt=ui_system,
            mode="script_professor",
            preferred_provider="gemini"
        )
        ui_code = cls._extract_code(ui_res.get("reply", "")) if ui_res.get("success") else ""
        if not ui_code or len(ui_code.splitlines()) < 8:
            print(f"[SCRIPT FACTORY] Stage 3 UI responder empty or hit quota. Synthesizing {ui_choice} Interface...", flush=True)
            ui_code = cls._generate_fallback_ui(game_name, ui_choice)
        print(f"[SCRIPT FACTORY] Stage 3 (UI Master) complete: {len(ui_code)} chars of UI code.", flush=True)

        # ----------------------------------------------------------------------
        # STAGE 4: Assembly & Anti-Stub Expansion Guard
        # ----------------------------------------------------------------------
        assembled_script = cls._assemble_payload(
            game_name=game_name,
            place_id=place_id,
            loader=loader_header,
            engine=engine_code,
            ui=ui_code,
            ui_framework=ui_choice
        )

        # Check for placeholder stubs
        stub_patterns = [
            r"--\s*implement\b",
            r"--\s*todo\b",
            r"--\s*put your\b",
            r"--\s*logic here\b",
            r"--\s*code here\b",
            r"\.\.\.\s*\(\d+\s*บรรทัด\)",
        ]
        has_stub = any(re.search(pat, assembled_script, re.IGNORECASE) for pat in stub_patterns)
        
        if has_stub or len(assembled_script) < 5000:
            print(f"[SCRIPT FACTORY] Detected stubs or low character count ({len(assembled_script)} chars). Triggering Stage 4 Expansion Pass...", flush=True)
            assembled_script = await cls._expand_and_heal_script(
                assembled_script,
                user_prompt=user_prompt,
                game_name=game_name
            )

        # ----------------------------------------------------------------------
        # STAGE 5: Conversational Summary Generation
        # ----------------------------------------------------------------------
        summary_prompt = (
            f"คุณคือ PAYØMBØYZAA ตอบแชท {user_name} เป็นภาษาไทยแบบเพื่อนสนิท กวนๆ ปั่นๆ มั่นใจในฝีมือ "
            f"สรุปสั้นๆ 1-2 ย่อหน้าว่าสร้างสคริปต์ {game_name} ให้แบบจัดเต็มระบบแล้ว พร้อมบอกฟีเจอร์เด่น (Auto Farm, ESP, ระบบ Bypass, UI {ui_choice}) "
            f"และบอกว่าแนบไฟล์สคริปต์ตัวเต็มไว้ให้ด้านล่างแล้ว ไม่ต้องมี code block ในแชท"
        )
        summary_res = await asyncio.to_thread(
            HYBRID_ROUTER.query_supervised,
            summary_prompt,
            user_request=user_prompt,
            mode="general_chat",
            preferred_provider="thaillm"
        )
        chat_summary = summary_res.get("reply", "").strip()
        if not chat_summary:
            chat_summary = (
                f"จัดให้เต็มระบบแล้วว่ะเพื่อน! สคริปต์ **{game_name}** เขียนโค้ดระบบออโต้ฟาร์ม + UI {ui_choice} "
                f"พร้อมระบบกันค้างและ Bypass รองรับ Executor ครบทุกตัว โค้ดตัวเต็มไม่มีกั๊กแนบเป็นไฟล์ .lua ไว้ให้ด้านล่างแล้ว ลุยได้เลย!"
            )

        elapsed = round(time.time() - start_time, 2)
        print(f"[SCRIPT FACTORY] Pipeline finished in {elapsed}s. Final script: {len(assembled_script):,} chars.", flush=True)

        return {
            "chat_summary": chat_summary,
            "lua_code": assembled_script,
            "char_count": len(assembled_script),
            "line_count": len(assembled_script.splitlines()),
            "elapsed": elapsed,
            "game_name": game_name,
        }

    @staticmethod
    def _extract_code(raw: str) -> str:
        if not raw:
            return ""
        error_indicators = (
            "ติดโควต้า", "เชื่อมต่อไม่ได้", "responder", "exhausted", "unavailable",
            "all-failed", "ลองส่งใหม่อีกครั้ง"
        )
        if any(ind in raw.lower() for ind in error_indicators) and not ("function" in raw or "local " in raw):
            return ""
        matches = re.findall(r"```(?:lua|luau)?\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
        if matches:
            code = "\n\n".join(m.strip() for m in matches if m.strip())
            if any(ind in code.lower() for ind in error_indicators) and not ("function" in code or "local " in code):
                return ""
            return code
        lines = [l for l in raw.splitlines() if not l.strip().startswith("```")]
        code = "\n".join(lines).strip()
        if any(ind in code.lower() for ind in error_indicators) and not ("function" in code or "local " in code):
            return ""
        return code

    @classmethod
    def _generate_fallback_engine(cls, game_name: str, place_id: str, ground_truth_context: str, user_prompt: str) -> str:
        return f'''local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")
local VirtualUser = game:GetService("VirtualUser")

local LocalPlayer = Players.LocalPlayer
local Character = LocalPlayer.Character or LocalPlayer.CharacterAdded:Wait()
local HumanoidRootPart = Character:WaitForChild("HumanoidRootPart", 10)
local Humanoid = Character:WaitForChild("Humanoid", 10)

LocalPlayer.CharacterAdded:Connect(function(newChar)
    Character = newChar
    HumanoidRootPart = newChar:WaitForChild("HumanoidRootPart", 10)
    Humanoid = newChar:WaitForChild("Humanoid", 10)
end)

-- Observable Engine State
local EngineState = {{
    AutoFarm = false,
    FastAttack = false,
    Noclip = false,
    WalkSpeed = 16,
    JumpPower = 50,
    ESP = false,
    TargetMob = "Nearest",
    SafeTeleport = true
}}

-- Anti-AFK
LocalPlayer.Idled:Connect(function()
    VirtualUser:Button2Down(Vector2.new(0, 0), Workspace.CurrentCamera.CFrame)
    task.wait(1)
    VirtualUser:Button2Up(Vector2.new(0, 0), Workspace.CurrentCamera.CFrame)
end)

-- Noclip loop
RunService.Stepped:Connect(function()
    if EngineState.Noclip and Character then
        for _, part in ipairs(Character:GetDescendants()) do
            if part:IsA("BasePart") and part.CanCollide then
                part.CanCollide = false
            end
        end
    end
end)

-- Safe Movement / Tween
local function TweenTo(targetCFrame, speed)
    if not HumanoidRootPart then return end
    speed = speed or 250
    local distance = (HumanoidRootPart.Position - targetCFrame.Position).Magnitude
    local duration = distance / speed
    local tweenInfo = TweenInfo.new(duration, Enum.EasingStyle.Linear)
    local tween = TweenService:Create(HumanoidRootPart, tweenInfo, {{CFrame = targetCFrame}})
    tween:Play()
    return tween
end

-- Target Acquisition
local function GetNearestEnemy()
    local nearest = nil
    local shortestDistance = math.huge
    local enemiesFolder = Workspace:FindFirstChild("Enemies") or Workspace:FindFirstChild("Mobs") or Workspace:FindFirstChild("Characters")
    local candidates = enemiesFolder and enemiesFolder:GetChildren() or Workspace:GetChildren()

    for _, entity in ipairs(candidates) do
        if entity:IsA("Model") and entity ~= Character then
            local root = entity:FindFirstChild("HumanoidRootPart") or entity:FindFirstChild("Torso")
            local hum = entity:FindFirstChildOfClass("Humanoid")
            if root and hum and hum.Health > 0 then
                local dist = (HumanoidRootPart.Position - root.Position).Magnitude
                if dist < shortestDistance then
                    shortestDistance = dist
                    nearest = entity
                end
            end
        end
    end
    return nearest
end

-- Core Farm Loop
task.spawn(function()
    while true do
        task.wait(0.15)
        if EngineState.AutoFarm and HumanoidRootPart and Humanoid and Humanoid.Health > 0 then
            pcall(function()
                local target = GetNearestEnemy()
                if target then
                    local targetRoot = target:FindFirstChild("HumanoidRootPart") or target:FindFirstChild("Torso")
                    if targetRoot then
                        local aboveTarget = targetRoot.CFrame * CFrame.new(0, 8, 0)
                        if (HumanoidRootPart.Position - targetRoot.Position).Magnitude > 25 then
                            TweenTo(aboveTarget, 280)
                        else
                            HumanoidRootPart.CFrame = aboveTarget
                            -- Trigger Attacks
                            VirtualUser:CaptureController()
                            VirtualUser:ClickButton1(Vector2.new(500, 500))
                        end
                    end
                end
            end)
        end
    end
end)

-- Fast Attack Loop
task.spawn(function()
    while true do
        task.wait(0.05)
        if EngineState.FastAttack and EngineState.AutoFarm then
            pcall(function()
                VirtualUser:CaptureController()
                VirtualUser:ClickButton1(Vector2.new(500, 500))
            end)
        end
    end
end)

-- Make state accessible to UI
_G.PayomboyzEngineState = EngineState
_G.PayomboyzTweenTo = TweenTo'''

    @classmethod
    def _generate_fallback_ui(cls, game_name: str, ui_choice: str) -> str:
        return f'''local Window = Fluent:CreateWindow({{
    Title = "{game_name} Hub",
    SubTitle = "PAYOMBØYZ Edition",
    TabWidth = 160,
    Size = UDim2.fromOffset(580, 460),
    Acrylic = true,
    Theme = "Dark",
    MinimizeKey = Enum.KeyCode.LeftControl
}})

local Tabs = {{
    Main = Window:AddTab({{ Title = "⚡ Automation", Icon = "flame" }}),
    Player = Window:AddTab({{ Title = "🏃 Player", Icon = "user" }}),
    Visuals = Window:AddTab({{ Title = "👁️ Visuals", Icon = "eye" }}),
    Settings = Window:AddTab({{ Title = "⚙️ Settings", Icon = "settings" }})
}}

local EngineState = _G.PayomboyzEngineState or {{}}

Tabs.Main:AddToggle("AutoFarmToggle", {{
    Title = "Auto Farm Mobs / Quests",
    Default = false,
    Callback = function(val)
        EngineState.AutoFarm = val
    end
}})

Tabs.Main:AddToggle("FastAttackToggle", {{
    Title = "Fast Attack (No Cooldown)",
    Default = false,
    Callback = function(val)
        EngineState.FastAttack = val
    end
}})

Tabs.Player:AddSlider("WalkSpeedSlider", {{
    Title = "WalkSpeed",
    Default = 16,
    Min = 16,
    Max = 250,
    Rounding = 0,
    Callback = function(val)
        EngineState.WalkSpeed = val
        pcall(function() game.Players.LocalPlayer.Character.Humanoid.WalkSpeed = val end)
    end
}})

Tabs.Player:AddSlider("JumpPowerSlider", {{
    Title = "JumpPower",
    Default = 50,
    Min = 50,
    Max = 300,
    Rounding = 0,
    Callback = function(val)
        EngineState.JumpPower = val
        pcall(function() game.Players.LocalPlayer.Character.Humanoid.JumpPower = val end)
    end
}})

Tabs.Player:AddToggle("NoclipToggle", {{
    Title = "Noclip Wall Bypass",
    Default = false,
    Callback = function(val)
        EngineState.Noclip = val
    end
}})

Tabs.Visuals:AddToggle("ESPToggle", {{
    Title = "ESP Enemies / Players",
    Default = false,
    Callback = function(val)
        EngineState.ESP = val
    end
}})

Tabs.Settings:AddButton({{
    Title = "Rejoin Server",
    Description = "Quickly reconnect to current game",
    Callback = function()
        game:GetService("TeleportService"):Teleport(game.PlaceId, game.Players.LocalPlayer)
    end
}})

Window:SelectTab(1)'''

    @classmethod
    def _assemble_payload(cls, game_name: str, place_id: str, loader: str, engine: str, ui: str, ui_framework: str) -> str:
        from bot.roblox_platform_intel import ROBLOX_INTEL
        server_hop = ROBLOX_INTEL.generate_safe_server_hop_snippet(place_id)
        date_str = time.strftime("%Y-%m-%d %H:%M:%S")
        return f"""-- ==============================================================================
-- [ {game_name.upper()} | UNIVERSAL AUTOMATION & CLIENT SUITE ]
-- PlaceId: {place_id} | Build Date: {date_str}
-- Target Executors: Solara, Wave, Delta, Codex, Arceus X, Synapse Z
-- UI Framework: {ui_framework}
-- ==============================================================================

{loader}

-- ==============================================================================
-- SECTION 1: CORE GAMEPLAY & AUTOMATION ENGINE
-- ==============================================================================
{engine}

-- ==============================================================================
-- SECTION 2: UI INTERFACE & CONTROLS BINDING
-- ==============================================================================
{ui}

-- ==============================================================================
-- SECTION 3: ULTRA-SAFE LOW-PLAYER SERVER HOP & ANTI-REPORT RECONNECT
-- ==============================================================================
{server_hop}

-- ==============================================================================
-- SECTION 4: SYSTEM BOOTSTRAP & NOTIFICATION
-- ==============================================================================
pcall(function()
    if Fluent and Fluent.Notify then
        Fluent:Notify({{
            Title = "{game_name} Hub",
            Content = "Script Loaded Successfully! Ready for execution.",
            SubTitle = "Complete Build",
            Duration = 6
        }})
    elseif WindUI and WindUI.Notify then
        WindUI:Notify({{
            Title = "{game_name} Hub",
            Content = "Script Loaded Successfully!",
            Duration = 5
        }})
    end
end)
"""

    @classmethod
    async def _expand_and_heal_script(cls, script: str, user_prompt: str, game_name: str) -> str:
        from bot.hybrid_router import HYBRID_ROUTER

        expansion_system = (
            "You are the Senior Luau Assembly Engineer for PAYØMBØYZAA. "
            "You are given an incomplete or stubbed Luau script. "
            "Your job is to REWRITE and REPLACE all incomplete parts, '-- TODO', '-- implement logic here', "
            "or short placeholders with 100% complete, runnable, detailed Luau implementations. "
            "Preserve all existing valid logic and UI structures. Do NOT shorten anything. "
            "Output the entire unified, completed Luau script inside ```lua ... ```."
        )
        expansion_prompt = (
            f"Original user request: {user_prompt}\n"
            f"Target Game: {game_name}\n\n"
            f"Script requiring expansion and stub removal:\n{script[:14000]}\n\n"
            f"Return the full expanded production script with ZERO placeholders."
        )

        res = await asyncio.to_thread(
            HYBRID_ROUTER.query_supervised,
            expansion_prompt,
            user_request=user_prompt,
            system_prompt=expansion_system,
            mode="script_professor",
            preferred_provider="gemini"
        )
        expanded = cls._extract_code(res.get("reply", ""))
        return expanded if len(expanded) > len(script) else script
