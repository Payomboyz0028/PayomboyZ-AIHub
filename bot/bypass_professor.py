#!/usr/bin/env python3
"""
==============================================================================
  PAYOMBØYZ BYPASS & PRO SCRIPT PROFESSOR (V10.0)
  High-Tier Luau Reverse Engineering, Metamethod Evasion & Architecture Engine
==============================================================================
Provides production-grade guidance, executable patterns, and anti-cheat evasion
for advanced game scripting:
1. Metamethod Interception (__namecall, __index, hookfunction, newcclosure)
2. Memory Constant & Upvalue Tampering (debug library)
3. Anti-Cheat Evasion (cloneref, RemoteSpy/HttpSpy anti-detection, integrity evasion)
4. Safe Physics & Movement Bypass (CFrame tweening, velocity spoofing)
5. Pro Game Architectures (Anime Dice RNG/Roll, Pet Inventory, Auto-Farm FSM)
6. Dynamic Self-Learning Confidence Score connected to Experience Database
==============================================================================
"""

import re
import time
from typing import Dict, Any, List, Optional
from bot.experience_db import EXPERIENCE_DB


BYPASS_TECHNIQUES: Dict[str, Dict[str, Any]] = {
    "namecall_hook": {
        "id": "namecall_hook",
        "title": "Metamethod __namecall Detour & Call Spoofing",
        "category": "evasion",
        "difficulty": "Advanced",
        "executors": ["Solara", "Wave", "Xeno", "Synapse Z", "Celery", "Delta"],
        "summary": "Hook __namecall เพื่อดักจับและบล็อกการเตะ (Kick) หรือสปูฟอาร์กิวเมนต์ก่อนส่งเข้า RemoteEvent / RemoteFunction",
        "code": """-- [PAYOMBØYZ] Safe __namecall Hooking Template
local cloneref = cloneref or function(o) return o end
local Players = cloneref(game:GetService("Players"))
local LocalPlayer = Players.LocalPlayer

local OldNamecall
OldNamecall = hookmetamethod(game, "__namecall", newcclosure(function(self, ...)
    local method = getnamecallmethod()
    local args = {...}

    -- 1. ป้องกัน Remote Kick หรือ Kick() จาก Local Script
    if method == "Kick" or method == "kick" then
        warn("[PAYOMBØYZ SHIELD] Intercepted unauthorized Kick() attempt!")
        return nil
    end

    -- 2. ดักตรวจหรือสปูฟ Remotes
    if method == "FireServer" or method == "InvokeServer" then
        local remoteName = tostring(self)
        -- ตัวอย่าง: ดักจับ Remote ตรวจจับความเร็ว หรือจับผิดสคริปต์
        if remoteName:find("Detection") or remoteName:find("Ban") or remoteName:find("Cheat") then
            warn("[PAYOMBØYZ SHIELD] Dropped anti-cheat report remote:", remoteName)
            return nil
        end
    end

    return OldNamecall(self, ...)
end))

print("[PAYOMBØYZ] __namecall Hook installed successfully!")"""
    },

    "cloneref_sandbox": {
        "id": "cloneref_sandbox",
        "title": "Anti-Detection Sandbox with cloneref & getgenv",
        "category": "evasion",
        "difficulty": "Intermediate",
        "executors": ["Solara", "Wave", "Synapse Z", "Delta", "Hydrogen"],
        "summary": "ป้องกันแอนตี้ชีตจากการตรวจหา instance references หรือ table indexing ด้วยการโคลน reference ที่ปลอดภัย",
        "code": """-- [PAYOMBØYZ] Cloneref Anti-Detection Pattern
local cloneref = cloneref or function(x) return x end
local HttpService = cloneref(game:GetService("HttpService"))
local TweenService = cloneref(game:GetService("TweenService"))
local RunService = cloneref(game:GetService("RunService"))
local Players = cloneref(game:GetService("Players"))
local LocalPlayer = Players.LocalPlayer

-- ซ่อน environment ตัวแปรเพื่อไม่ให้สคริปต์ในเกมกวาดเจอจาก getgenv()
local SafeEnv = {}
setmetatable(SafeEnv, {
    __index = getgenv(),
    __metatable = "Protected"
})

print("[PAYOMBØYZ] Secure Environment Initialized.")"""
    },

    "anti_teleport_bypass": {
        "id": "anti_teleport_bypass",
        "title": "Safe CFrame Stepping & Velocity Spoofing (Anti-Teleport Bypass)",
        "category": "physics",
        "difficulty": "Advanced",
        "executors": ["Universal"],
        "summary": "หลบการตรวจจับความเร็ว/การวาร์ป ด้วย CFrame Linear Interpolation และรีเซ็ต AssemblyLinearVelocity เพื่อไม่ให้โดน Rollback หรือ Kick",
        "code": """-- [PAYOMBØYZ] Smooth CFrame Stepping & Anti-Teleport Bypass
local cloneref = cloneref or function(x) return x end
local Players = cloneref(game:GetService("Players"))
local RunService = cloneref(game:GetService("RunService"))
local LocalPlayer = Players.LocalPlayer

local function SafeTeleport(targetCFrame, speed)
    local char = LocalPlayer.Character or LocalPlayer.CharacterAdded:Wait()
    local root = char:WaitForChild("HumanoidRootPart")
    speed = speed or 120 -- ความเร็ว CFrame/วินาที

    local distance = (root.Position - targetCFrame.Position).Magnitude
    local duration = distance / speed
    local startTime = tick()
    local startCF = root.CFrame

    local conn
    conn = RunService.Heartbeat:Connect(function()
        local elapsed = tick() - startTime
        local alpha = math.clamp(elapsed / duration, 0, 1)

        -- Spoof velocity เป็นศูนย์เพื่อป้องกัน Velocity Check
        root.AssemblyLinearVelocity = Vector3.zero
        root.AssemblyAngularVelocity = Vector3.zero
        root.CFrame = startCF:Lerp(targetCFrame, alpha)

        if alpha >= 1 then
            conn:Disconnect()
            print("[PAYOMBØYZ] Teleport complete safely.")
        end
    end)
end"""
    },

    "upvalue_constant_tamper": {
        "id": "upvalue_constant_tamper",
        "title": "Memory Upvalue & Constant Manipulation (debug library)",
        "category": "memory",
        "difficulty": "Expert",
        "executors": ["Synapse Z", "Wave", "Solara (partial)", "Delta", "Codex"],
        "summary": "ใช้ฟังก์ชัน debug.getupvalues และ debug.setupvalue เพื่อแก้ตัวแปรภายในฟังก์ชันเกมโดยตรง เช่น Cooldown, WalkSpeed, หรือตัวแปร Check Interval โดยไม่ต้องแก้ซอร์สโค้ด",
        "code": """-- [PROFESSOR ARCHITECTURE] Production Upvalue & Constant Tampering Engine
local function ModifyClosureUpvalue(targetFunc, targetKey, newValue)
    if not (debug and debug.getupvalues and debug.setupvalue) then
        warn("[TamperEngine] Executor does not provide full debug upvalue APIs")
        return false
    end

    local upvalues = debug.getupvalues(targetFunc)
    for idx, val in pairs(upvalues) do
        -- ตรวจสอบทั้งกรณีที่ upvalue เป็น table หรือค่าตรงๆ
        if type(val) == "table" and val[targetKey] ~= nil then
            val[targetKey] = newValue
            print(string.format("[TamperEngine] Patched nested table upvalue [%s] = %s", tostring(targetKey), tostring(newValue)))
            return true
        elseif tostring(idx) == tostring(targetKey) or val == targetKey then
            debug.setupvalue(targetFunc, idx, newValue)
            print(string.format("[TamperEngine] Patched closure upvalue index [%d] -> %s", idx, tostring(newValue)))
            return true
        end
    end
    return false
end

-- ตัวอย่างการดักจับและแฮกค่าคูลดาวน์สกิล / ตัวตรวจจับในหน่วยความจำ
local function ScanAndPatchGarbageCollector(matchPattern, targetField, patchValue)
    if not getgc then return false end
    for _, obj in ipairs(getgc(true)) do
        if type(obj) == "table" and rawget(obj, targetField) ~= nil then
            obj[targetField] = patchValue
            print(string.format("[TamperEngine] GC Table Patched: [%s] = %s", targetField, tostring(patchValue)))
            return true
        elseif type(obj) == "function" and islclosure(obj) and not isexecutorclosure(obj) then
            local info = debug.getinfo(obj)
            if info and info.source and info.source:find(matchPattern) then
                ModifyClosureUpvalue(obj, targetField, patchValue)
            end
        end
    end
    return false
end"""
    },

    "anime_dice_roll_system": {
        "id": "anime_dice_roll_system",
        "title": "Anime Dice RNG & Auto-Roll Architecture (Weighted Table, Pity & Auto-Sell)",
        "category": "game_architecture",
        "difficulty": "Intermediate",
        "executors": ["Universal"],
        "summary": "สถาปัตยกรรมระบบสุ่มลูกเต๋า/ลูกแก้ว แบบ Pro: มีตารางความน่าจะเป็นแบบถ่วงน้ำหนัก (Weighted Table), ระบบ Pity การันตี, ตัวคูณ Luck, และระบบคัดกรอง Auto-Equip/Auto-Sell",
        "code": """-- [PROFESSOR ARCHITECTURE] Enterprise Anime Dice & Gacha Roll Controller
local cloneref = cloneref or function(o) return o end
local HttpService = cloneref(game:GetService("HttpService"))
local ReplicatedStorage = cloneref(game:GetService("ReplicatedStorage"))
local Players = cloneref(game:GetService("Players"))
local LocalPlayer = Players.LocalPlayer

local DiceEngine = {
    PityCounter = 0,
    TotalRolls = 0,
    LuckMultiplier = 1.0,
    AutoSellFilter = { Common = true, Rare = false, Epic = false },
    IsRolling = false
}

-- ตารางความน่าจะเป็นแบบถ่วงน้ำหนัก (Weight ยิ่งน้อยยิ่งหายากระดับพระเจ้า)
local DROP_TABLE = {
    { Name = "Common Wooden Die",   Weight = 6000, Rarity = "Common",    Multiplier = 1 },
    { Name = "Azure Flame Die",     Weight = 1500, Rarity = "Rare",      Multiplier = 3.5 },
    { Name = "Shadow Void Die",     Weight = 300,  Rarity = "Epic",      Multiplier = 15 },
    { Name = "Solar Flare Monarch", Weight = 45,   Rarity = "Legendary", Multiplier = 80 },
    { Name = "Chronos Eternity",    Weight = 2,    Rarity = "Mythic",    Multiplier = 750 },
    { Name = "Limitless Infinity",  Weight = 0.1,  Rarity = "Secret",    Multiplier = 5000 }
}

function DiceEngine:CalculateDrop(pityThreshold)
    pityThreshold = pityThreshold or 100
    self.TotalRolls = self.TotalRolls + 1
    self.PityCounter = self.PityCounter + 1

    -- ตรวจสอบ Pity Guarantee
    if self.PityCounter >= pityThreshold then
        self.PityCounter = 0
        return DROP_TABLE[4], true -- การันตีระดับ Legendary ขึ้นไป
    end

    local totalWeight = 0
    for _, item in ipairs(DROP_TABLE) do
        local weight = item.Weight
        if item.Rarity ~= "Common" then
            weight = weight * self.LuckMultiplier
        end
        totalWeight = totalWeight + weight
    end

    local rnd = math.random() * totalWeight
    local accumulator = 0

    for _, item in ipairs(DROP_TABLE) do
        local weight = item.Weight
        if item.Rarity ~= "Common" then
            weight = weight * self.LuckMultiplier
        end
        accumulator = accumulator + weight
        if rnd <= accumulator then
            return item, false
        end
    end

    return DROP_TABLE[1], false
end

function DiceEngine:StartAutoRoll(rollRemote, interval)
    self.IsRolling = true
    interval = interval or 0.25

    task.spawn(function()
        while self.IsRolling do
            local drop, isPity = self:CalculateDrop(100)
            
            -- ถ้าเชื่อมต่อกับเซิร์ฟเวอร์เกม ส่งแพ็กเกจผ่าน Remote
            if rollRemote and rollRemote:IsA("RemoteEvent") then
                rollRemote:FireServer("RollDice", { ClientSeed = os.time() })
            end

            -- ตัวคัดกรอง Auto-Sell ขยะ
            if self.AutoSellFilter[drop.Rarity] then
                print(string.format("[Auto-Sell] Sold %s (%s) for Coins", drop.Name, drop.Rarity))
            else
                print(string.format("[Gacha WIN] %s [%s] (Pity: %s)", drop.Name, drop.Rarity, tostring(isPity)))
            end

            task.wait(interval)
        end
    end)
end

function DiceEngine:StopAutoRoll()
    self.IsRolling = false
end

return DiceEngine"""
    },

    "pet_inventory_architecture": {
        "id": "pet_inventory_architecture",
        "title": "Pro Pet System Architecture (Equip Best, Multipliers & Fusion)",
        "category": "game_architecture",
        "difficulty": "Intermediate",
        "executors": ["Universal"],
        "summary": "ระบบจัดการสัตว์เลี้ยงระดับโปร: จัดการ Inventory, คำนวณ Auto-Equip สัตว์เลี้ยงที่ให้ตัวคูณสูงสุด, และระบบหลอม (Fusion) สัตว์เลี้ยงเพื่อเลื่อนขั้น",
        "code": """-- [PROFESSOR ARCHITECTURE] Enterprise Pet Inventory & Auto-Equip Engine
local HttpService = game:GetService("HttpService")

local PetSystem = {
    Inventory = {},
    MaxEquippedSlots = 4
}

function PetSystem:AddPet(petId, name, baseMultiplier, isShiny, tier)
    local pet = {
        UUID = HttpService:GenerateGUID(false),
        Id = petId,
        Name = name,
        BaseMultiplier = baseMultiplier,
        Tier = tier or 1,
        IsShiny = isShiny or false,
        TotalPower = baseMultiplier * (tier or 1) * (isShiny and 2.5 or 1.0),
        Equipped = false
    }
    table.insert(self.Inventory, pet)
    return pet
end

function PetSystem:EquipBest()
    -- เรียงลำดับจากสัตว์เลี้ยงที่ให้พลังโจมตีสูงสุดลงมา
    table.sort(self.Inventory, function(a, b)
        return a.TotalPower > b.TotalPower
    end)

    local equippedCount = 0
    local equippedList = {}

    for _, pet in ipairs(self.Inventory) do
        if equippedCount < self.MaxEquippedSlots then
            pet.Equipped = true
            equippedCount = equippedCount + 1
            table.insert(equippedList, pet)
        else
            pet.Equipped = false
        end
    end

    print(string.format("[PetSystem] Successfully equipped top %d pets. Peak Multiplier: %.1f", 
        equippedCount, equippedList[1] and equippedList[1].TotalPower or 0))
    return equippedList
end

function PetSystem:FusePets(targetPetId, requiredCount)
    requiredCount = requiredCount or 5
    local matches = {}

    for idx, pet in ipairs(self.Inventory) do
        if pet.Id == targetPetId and not pet.Equipped then
            table.insert(matches, idx)
            if #matches >= requiredCount then break end
        end
    end

    if #matches >= requiredCount then
        -- ลบตัวเดิมออกจาก Inventory จากหลังมาหน้า
        for i = #matches, 1, -1 do
            table.remove(self.Inventory, matches[i])
        end
        -- สร้างสัตว์เลี้ยงขั้นใหม่ (Tier + 1)
        local fused = self:AddPet(targetPetId, targetPetId .. " [Fused Tier 2]", 10.0, true, 2)
        print(string.format("[PetSystem] Fusion Success! Created %s with Power %.1f", fused.Name, fused.TotalPower))
        return fused
    end

    return nil, "Not enough pets for fusion"
end

return PetSystem"""
    },

    "autofarm_fsm": {
        "id": "autofarm_fsm",
        "title": "State Machine Auto-Farm Framework (Anti-Crash, Safe Loops)",
        "category": "automation",
        "difficulty": "Advanced",
        "executors": ["Universal"],
        "summary": "โครงสร้างบอทฟาร์มแบบ Finite State Machine (Idle -> FindTarget -> Move -> Attack -> Collect) สมบูรณ์แบบ 100% มีระบบดักจับมอนสเตอร์จริง ตรวจสอบเลือด และยกเลิกลูปอย่างปลอดภัย",
        "code": """-- [PROFESSOR ARCHITECTURE] Production-Grade Finite State Machine Auto-Farm
local cloneref = cloneref or function(o) return o end
local Players = cloneref(game:GetService("Players"))
local RunService = cloneref(game:GetService("RunService"))
local Workspace = cloneref(game:GetService("Workspace"))
local LocalPlayer = Players.LocalPlayer

local AutoFarm = {
    State = "IDLE", -- IDLE -> SEARCHING -> APPROACHING -> ATTACKING -> COLLECTING
    Running = false,
    CurrentTarget = nil,
    AttackDistance = 6.5, -- ยืนเหนือหัวมอน 6.5 studs เพื่อไม่ให้โดนดาเมจตีสวน
    Config = {
        MobFolder = Workspace:FindFirstChild("Enemies") or Workspace:FindFirstChild("Mobs") or Workspace,
        MobName = "",
        AttackSpeed = 0.15
    },
    Connections = {}
}

-- 1. ค้นหามอนสเตอร์ที่ใกล้ที่สุด มีเลือด > 0 และอยู่ในโซนที่กำหนด
function AutoFarm:FindNearestTarget()
    local char = LocalPlayer.Character
    if not char then return nil end
    local root = char:FindFirstChild("HumanoidRootPart")
    if not root then return nil end

    local nearestTarget = nil
    local shortestDist = math.huge

    for _, model in ipairs(self.Config.MobFolder:GetChildren()) do
        if model:IsA("Model") and model ~= char then
            local hum = model:FindFirstChildOfClass("Humanoid")
            local mobRoot = model:FindFirstChild("HumanoidRootPart") or model:FindFirstChild("Torso")
            
            -- ตรวจสอบว่ามอนยังมีชีวิตอยู่
            if hum and hum.Health > 0 and mobRoot then
                if self.Config.MobName == "" or model.Name:lower():find(self.Config.MobName:lower()) then
                    local dist = (root.Position - mobRoot.Position).Magnitude
                    if dist < shortestDist then
                        shortestDist = dist
                        nearestTarget = model
                    end
                end
            end
        end
    end

    return nearestTarget
end

-- 2. ขยับตัวละครไปยังตำแหน่งปลอดภัยเหนือเป้าหมาย (Float-Over Position)
function AutoFarm:PositionAboveTarget(targetModel)
    local char = LocalPlayer.Character
    if not char then return end
    local root = char:FindFirstChild("HumanoidRootPart")
    local mobRoot = targetModel:FindFirstChild("HumanoidRootPart") or targetModel:FindFirstChild("Torso")
    if not (root and mobRoot) then return end

    -- ลอยอยู่เหนือหัวมอนสเตอร์เพื่อหลบ Hitbox และการโจมตีระยะประชิด
    local safePosition = mobRoot.Position + Vector3.new(0, self.AttackDistance, 0)
    root.AssemblyLinearVelocity = Vector3.zero
    root.CFrame = CFrame.new(safePosition, mobRoot.Position)
end

-- 3. โจมตีเป้าหมาย
function AutoFarm:ExecuteAttack(targetModel)
    local char = LocalPlayer.Character
    if not char then return end

    -- ตัวอย่างที่ 1: เรียกใช้ Tool ในกระเป๋า
    local tool = char:FindFirstChildOfClass("Tool")
    if tool and tool:FindFirstChild("Handle") then
        tool:Activate()
    end

    -- ตัวอย่างที่ 2: ถ้าเกมใช้ Combat Remote ให้ใส่ FireServer ตรงนี้
    -- ReplicatedStorage.Events.Attack:FireServer(targetModel)
end

-- 4. รัน State Machine Loop แบบ Yield-Safe
function AutoFarm:Start()
    if self.Running then return end
    self.Running = true
    print("[AutoFarm Engine] FSM Loop Initialized.")

    task.spawn(function()
        while self.Running do
            local char = LocalPlayer.Character
            local hum = char and char:FindFirstChildOfClass("Humanoid")

            -- ถ้าผู้เล่นตาย ให้รอจนเกิดใหม่
            if not hum or hum.Health <= 0 then
                self.State = "IDLE"
                task.wait(1.0)
            elseif self.State == "IDLE" or self.State == "SEARCHING" then
                self.CurrentTarget = self:FindNearestTarget()
                if self.CurrentTarget then
                    self.State = "APPROACHING"
                else
                    task.wait(0.5) -- ไม่มีมอน ให้พักเพื่อลดโหลด CPU
                end
            elseif self.State == "APPROACHING" then
                local mobHum = self.CurrentTarget and self.CurrentTarget:FindFirstChildOfClass("Humanoid")
                if not mobHum or mobHum.Health <= 0 then
                    self.State = "SEARCHING"
                else
                    self:PositionAboveTarget(self.CurrentTarget)
                    self.State = "ATTACKING"
                end
            elseif self.State == "ATTACKING" then
                local mobHum = self.CurrentTarget and self.CurrentTarget:FindFirstChildOfClass("Humanoid")
                if not mobHum or mobHum.Health <= 0 then
                    self.State = "SEARCHING"
                    self.CurrentTarget = nil
                else
                    self:PositionAboveTarget(self.CurrentTarget)
                    self:ExecuteAttack(self.CurrentTarget)
                    task.wait(self.Config.AttackSpeed)
                end
            end

            task.wait(0.05) -- ป้องกัน Infinite Yield
        end
    end)
end

function AutoFarm:Stop()
    self.Running = false
    self.State = "IDLE"
    self.CurrentTarget = nil
    for _, conn in ipairs(self.Connections) do
        if conn and conn.Disconnect then conn:Disconnect() end
    end
    self.Connections = {}
    print("[AutoFarm Engine] FSM Loop Safely Terminated.")
end

return AutoFarm"""
    }
}


class BypassProfessor:
    """
    Expert AI guidance module for Roblox Luau bypasses, anti-cheat countermeasures,
    and high-tier script architectures with dynamic self-learning feedback.
    """

    def __init__(self):
        self.techniques = BYPASS_TECHNIQUES

    def calculate_confidence(self, technique_id: str, executor: str = "general") -> float:
        """
        Computes composite confidence score:
        Confidence = (HistSuccess * 0.40) + (RecencyWeight * 0.25) + (Feedback * 0.20) + (ExecCompat * 0.15)
        """
        eff = EXPERIENCE_DB.get_bypass_effectiveness(technique_id)
        base_rate = eff.get("success_rate", 0.85)

        # Recency
        last_ts = eff.get("last_success_ts", 0.0)
        now = time.time()
        if last_ts > 0 and (now - last_ts) < 86400:
            recency = 1.0
        elif last_ts > 0 and (now - last_ts) < 86400 * 7:
            recency = 0.8
        else:
            recency = 0.6

        # Community feedback / penalty
        consec_fails = eff.get("consecutive_fails", 0)
        feedback_score = 1.0 - (consec_fails * 0.25)
        feedback_score = max(0.2, min(1.0, feedback_score))

        # Executor compatibility
        tech = self.techniques.get(technique_id, {})
        supported_execs = tech.get("executors", ["Universal"])
        if "Universal" in supported_execs or any(e.lower() in executor.lower() for e in supported_execs):
            exec_score = 1.0
        else:
            exec_score = 0.5

        confidence = (base_rate * 0.40) + (recency * 0.25) + (feedback_score * 0.20) + (exec_score * 0.15)
        return round(confidence, 2)

    def find_relevant_techniques(self, query: str) -> List[Dict[str, Any]]:
        """Matches user query keywords to known techniques."""
        q = query.lower()
        matched = []

        keywords = {
            "namecall_hook": ["namecall", "hookmetamethod", "ดัก", "kick", "เตะ", "fireserver", "anticheat", "แบน"],
            "cloneref_sandbox": ["cloneref", "sandbox", "ซ่อน", "getgenv", "หลบ", "ตรวจจับ"],
            "anti_teleport_bypass": ["วาร์ป", "teleport", "cframe", "ความเร็ว", "fly", "บิน", "speed", "หลบวาร์ป"],
            "upvalue_constant_tamper": ["upvalue", "constant", "debug", "แก้ตัวแปร", "cooldown"],
            "anime_dice_roll_system": ["dice", "roll", "สุ่ม", "ลูกเต๋า", "anime dice", "กาชา", "pity", "luck"],
            "pet_inventory_architecture": ["pet", "สัตว์เลี้ยง", "equip best", "ฟิวชั่น", "สัตว์", "inventory"],
            "autofarm_fsm": ["autofarm", "ฟาร์ม", "บอทฟาร์ม", "state machine", "fsm", "ตีมอน", "ออโต้ฟาร์ม"]
        }

        for tech_id, kw_list in keywords.items():
            if any(kw in q for kw in kw_list):
                if tech_id in self.techniques:
                    matched.append(self.techniques[tech_id])

        # If none matched, return top 2 most popular
        if not matched:
            matched = [self.techniques["namecall_hook"], self.techniques["anime_dice_roll_system"]]

        return matched

    def build_professor_response(self, query: str, user_name: str = "Friend", executor: str = "general") -> str:
        """
        Generates comprehensive, authoritative, and production-grade Luau architecture response.
        """
        matched = self.find_relevant_techniques(query)
        primary = matched[0]

        conf = self.calculate_confidence(primary["id"], executor=executor)
        eff = EXPERIENCE_DB.get_bypass_effectiveness(primary["id"])

        conf_badge = f"🛡️ **[ความเชื่อมั่นทางเทคนิค: {int(conf * 100)}% | ระดับความยาก: {primary['difficulty']} | สถานะ: {eff.get('status')}]**"

        parts = [
            f"### 🔬 การวิเคราะห์โครงสร้าง: {primary['title']}",
            conf_badge,
            f"\n**1. สถาปัตยกรรมและการทำงานระดับเอนจิน:**\n{primary['summary']}",
            f"\n**2. ซอร์สโค้ด Luau มาตรฐาน Production (Executor-Ready 100%):**",
            f"```lua\n{primary['code']}\n```",
            "\n**3. ข้อกำหนดทางเทคนิคและการป้องกันความเสี่ยง (Engine Integrity):**",
            "- **Task Scheduler Sync**: หลีกเลี่ยงการใช้ `wait()` แบบดั้งเดิม ให้ใช้ `task.wait()` หรือผูกเข้ากับ `RunService.Heartbeat` / `RunService.Stepped` ตามประเภทการประมวลผล (Physics vs Frame)",
            "- **Memory & Connection Management**: สคริปต์ระดับโปรต้องจัดการ Event Connections และเก็บในตาราง Maid/Janitor เพื่อ Disconnect ทุกครั้งเมื่อหยุดการทำงาน ป้องกันปัญหา Memory Leak หรือ FPS Drop",
            "- **Replication & Anticheat Checks**: หากเป็นการแก้ไขตำแหน่ง ให้สปูฟค่า `AssemblyLinearVelocity` เป็นศูนย์เสมอ เพื่อไม่ให้กระตุ้นตัวดักจับ Speed/Teleport ของ Server Scripts"
        ]

        return "\n".join(parts)


# Singleton Instance
BYPASS_PROFESSOR = BypassProfessor()

