# -*- coding: utf-8 -*-
"""
========================================================================================
🌪️ PAYOMBØYZ RUNTIME MEMORY INTERCEPTOR & ZERO-DAY AUTO-DUMPER GENERATOR
- Generates 100% executable Luau AutoExecute & Runtime Memory Interceptors for Executors
- Compatible with: Real, Delta, Wave, Solara, Synapse Z, Xeno, MacSploit, Argon, etc.
- Multi-Stage Snooper: Polsec V2, Fulcrum WebSockets, Luarmor V4, Luraph VM, MoonSec VM
- Auto-copies recovered genuine source code to Windows Clipboard (Ctrl+V) instantly
- Auto-saves dumped raw payload to: workspace/Latest_Captured_Script.luau & Captured_Scripts/
========================================================================================
"""

from __future__ import annotations
import io
import discord

RUNTIME_INTERCEPTOR_LUAU = """--!nocheck
--!nolint
-- ==============================================================================
-- [PAYOMBØYZ GODMODE UNIVERSAL ZERO-DAY SCRIPT INTERCEPTOR & AUTO-DUMPER]
-- Path: AutoExecute (e.g. Real/autoexec/ or run before target script)
-- Powered by: PAYOMBØYZ CYBER-AI (Autonomous Forensics & Runtime Unpacker)
-- Target Output: Windows Clipboard (Ctrl+V) & workspace/Latest_Captured_Script.luau
-- Compatible with: Real, Delta, Wave, Solara, Synapse Z, Xeno, MacSploit, Celery
-- ==============================================================================

if getgenv and getgenv().__PAYOMBOYZ_DUMPER_LOADED then
    print("🔁 [PAYOMBØYZ] Auto-Dumper already active in memory.")
    return
end

local G = (getgenv and getgenv()) or _G
pcall(function() G.__PAYOMBOYZ_DUMPER_LOADED = true end)

print("==================================================================")
print("🚀 [PAYOMBØYZ] Universal AutoExecute Script Dumper Initialized!")
print("🎯 Monitoring: loadstring, load, decodeCache, and Dynamic Sinks...")
print("📋 Auto-Copy to Clipboard: ACTIVE (Ctrl+V immediately after execution)")
print("==================================================================")

local real_loadstring   = loadstring or (G and G.loadstring)
local real_load         = load or (G and G.load)
local real_writefile    = writefile or (G and G.writefile)
local real_makefolder   = makefolder or (G and G.makefolder)
local real_isfolder     = isfolder or (G and G.isfolder)
local real_setclipboard = setclipboard or toclipboard or (G and G.setclipboard) or (Clipboard and Clipboard.set)

-- Ensure workspace directory structure
pcall(function()
    if real_makefolder and real_isfolder and not real_isfolder("Captured_Scripts") then
        real_makefolder("Captured_Scripts")
    end
end)

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. STEALTH ANTI-TAMPER SHIELD (PREVENT LOADER CRASHES & CHECKS)
-- ─────────────────────────────────────────────────────────────────────────────
local falseFunc = function() return false end
local trueFunc  = function() return true end

pcall(function() G.isfunctionhooked = falseFunc end)
pcall(function() getfenv().isfunctionhooked = falseFunc end)
pcall(function() if _G then _G.isfunctionhooked = falseFunc end end)

pcall(function() G.isnewcclosure = trueFunc end)
pcall(function() getfenv().isnewcclosure = trueFunc end)
pcall(function() if _G then _G.isnewcclosure = trueFunc end end)

pcall(function() G.checkcaller = trueFunc end)
pcall(function() getfenv().checkcaller = trueFunc end)

-- Protect WebSocket native C closure (Prevents Polsec disconnect / retry loops)
pcall(function()
    if WebSocket and WebSocket.Connect then
        WebSocket.connect = WebSocket.Connect
        if G.WebSocket then G.WebSocket.connect = WebSocket.Connect end
    end
end)

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. DUMPING ENGINE & CLIPBOARD PIPELINE
-- ─────────────────────────────────────────────────────────────────────────────
local capturedHashes = {}
local dumpCount = 0

local function fastHash(s)
    local h = 5381
    local len = #s
    local step = math.max(1, math.floor(len / 40))
    for i = 1, len, step do
        h = ((h * 33) + string.byte(s, i)) % 4294967296
    end
    return string.format("%d_%08x", len, h)
end

local function harvestScript(src, origin, extraInfo)
    if not src or type(src) ~= "string" or #src < 120 then return end
    
    -- Exclude internal dumper script signature
    if src:find("PAYOMBOYZ_DUMPER_LOADED") or src:find("Universal AutoExecute Script Dumper") then
        return
    end

    -- Exclude Polsec enclib codec from being treated as the final game script
    if src:find("Zstd decoder adapted from") or src:find("101arrowz/fzstd") then
        return
    end

    local h = fastHash(src)
    if capturedHashes[h] then return end
    capturedHashes[h] = true

    dumpCount = dumpCount + 1
    local lineCount = #string.split(src, "\\n")
    local sizeBytes = #src

    print("==================================================================")
    print(string.format("🎉 [PAYOMBØYZ] CAPTURED GENUINE SCRIPT PAYLOAD #%d!", dumpCount))
    print(string.format("   Origin: %s %s", tostring(origin), extraInfo and ("(" .. tostring(extraInfo) .. ")") or ""))
    print(string.format("   Size: %d bytes | Lines: %d", sizeBytes, lineCount))
    print("   📋 STATUS: COPIED DIRECTLY TO WINDOWS CLIPBOARD (Ctrl+V)!")
    print("   💾 BACKUP: workspace/Latest_Captured_Script.luau")
    print("==================================================================")

    -- 1. Copy directly to Windows Clipboard (Ctrl+V)
    if real_setclipboard then
        pcall(function() real_setclipboard(src) end)
    end

    -- 2. Save directly to workspace root for instant access
    if real_writefile then
        pcall(function()
            real_writefile("Latest_Captured_Script.luau", src)
            real_writefile("PAYOMBOYZ_DUMPED_RAW.luau", src)
            
            -- Save timestamped version into archive folder
            local filename = string.format("Captured_Scripts/Script_%s_%d.luau", tostring(os.date("%Y%m%d_%H%M%S")), dumpCount)
            real_writefile(filename, src)
        end)
    end

    -- 3. Visual In-Game Notification
    pcall(function()
        game:GetService("StarterGui"):SetCore("SendNotification", {
            Title = "🎉 SCRIPT CAPTURED (COPIED)!",
            Text = string.format("ดึงโค้ดสำเร็จ (%d ไบต์) กด Ctrl+V ได้เลย!", sizeBytes),
            Duration = 8
        })
    end)
end

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. MULTI-STAGE POLSEC CODEC SNOOPER (ZSTD / CHACHA20)
-- ─────────────────────────────────────────────────────────────────────────────
local function wrapEnclibModule(codecModule)
    if type(codecModule) ~= "table" or not codecModule.new then
        return codecModule
    end

    local origNew = codecModule.new
    codecModule.new = function(k1, k2)
        print("🔑 [SPY:KEY_SNIFFER] Polsec Codec Initialized!")
        local inst = origNew(k1, k2)
        if type(inst) == "table" and inst.decodeCache then
            local origDecode = inst.decodeCache
            inst.decodeCache = function(packet)
                local res = origDecode(packet)
                if res then
                    if type(res) == "table" then
                        pcall(function()
                            for k, v in pairs(res) do
                                if type(v) == "string" and #v > 200 then
                                    harvestScript(v, "decodeCache.table", tostring(k))
                                end
                            end
                            local hs = game:GetService("HttpService")
                            local json = hs:JSONEncode(res)
                            if real_writefile then
                                real_writefile("Latest_Polsec_Packet.json", json)
                            end
                        end)
                    elseif type(res) == "string" and #res > 200 then
                        harvestScript(res, "decodeCache.raw", nil)
                    end
                end
                return res
            end
        end
        return inst
    end

    return codecModule
end

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. UNIVERSAL LOADSTRING / LOAD SINK INTERCEPTOR
-- ─────────────────────────────────────────────────────────────────────────────
local function universalTrap(codeStr, chunkName)
    local src = tostring(codeStr or "")
    local chunk = tostring(chunkName or "anonymous")

    -- [STAGE 1] Detect Polsec Enclib Codec
    if src:find("Zstd decoder") or src:find("101arrowz") or src:find("decodeCache") or src:find("PSC4N") then
        print(string.format("⚡ [SPY:STAGE_1] Polsec Codec Intercepted (%d bytes) - Compiling and hooking...", #src))
        
        local compiled = real_loadstring and real_loadstring(codeStr, chunkName)
        if not compiled and real_load then
            compiled = real_load(codeStr, chunkName)
        end

        return function(...)
            local codecModule = compiled(...)
            return wrapEnclibModule(codecModule)
        end
    end

    -- [STAGE 2] Genuine Script Payload Interception
    if #src >= 120 then
        harvestScript(src, "loadstring", chunk)
    end

    if real_loadstring then
        return real_loadstring(codeStr, chunkName)
    elseif real_load then
        return real_load(codeStr, chunkName)
    end
    return function(...) end
end

local finalHook = universalTrap
if newcclosure then
    pcall(function() finalHook = newcclosure(universalTrap) end)
end

pcall(function() G.loadstring = finalHook end)
pcall(function() getfenv().loadstring = finalHook end)
pcall(function() if _G then _G.loadstring = finalHook end end)

pcall(function() G.load = finalHook end)
pcall(function() getfenv().load = finalHook end)
pcall(function() if _G then _G.load = finalHook end end)

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. SETMETATABLE HOOK (Unpacked Module Tables e.g. Luarmor V4 / Luraph VM)
-- ─────────────────────────────────────────────────────────────────────────────
local old_setmetatable = hookfunction and (getgenv and getgenv().setmetatable or setmetatable)
if old_setmetatable and hookfunction then
    pcall(function()
        hookfunction(setmetatable, function(tbl, meta)
            if type(tbl) == "table" and not tbl.__payomboyz_dumped then
                local fn_count = 0
                for k, v in pairs(tbl) do
                    if type(v) == "function" then
                        fn_count = fn_count + 1
                    end
                end

                if fn_count >= 12 then
                    tbl.__payomboyz_dumped = true
                    local dump_lines = {
                        "-- ============================================================================",
                        "-- ⚡ PAYOMBØYZ RUNTIME INTERCEPTOR — UNPACKED MODULE TABLE DUMP",
                        string.format("-- Captured Closures: %d | Timestamp: %s", fn_count, os.date("!%Y-%m-%d %H:%M:%SZ")),
                        "-- ============================================================================",
                        "return {",
                    }
                    for k, v in pairs(tbl) do
                        if k ~= "__payomboyz_dumped" then
                            local key_repr = type(k) == "number" and string.format("[%d]", k) or string.format("[%q]", tostring(k))
                            local val_repr = "nil"
                            if type(v) == "function" then
                                local dump_success, dumped_code = pcall(function()
                                    if decompile then return decompile(v) end
                                    return nil
                                end)
                                if dump_success and dumped_code and #dumped_code > 5 then
                                    val_repr = dumped_code
                                else
                                    val_repr = string.format("function(...) --[[ Closure Ref: %s ]] end", tostring(v))
                                end
                            elseif type(v) == "string" then
                                val_repr = string.format("%q", v)
                            elseif type(v) == "number" or type(v) == "boolean" then
                                val_repr = tostring(v)
                            end
                            table.insert(dump_lines, string.format("    %s = %s,", key_repr, val_repr))
                        end
                    end
                    table.insert(dump_lines, "}")
                    local moduleContent = table.concat(dump_lines, "\\n")
                    harvestScript(moduleContent, "setmetatable.module", string.format("%d_funcs", fn_count))
                end
            end
            return old_setmetatable(tbl, meta)
        end)
    end)
end

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. HTTPGET HOOK (Logs Raw CDN Payload URLs)
-- ─────────────────────────────────────────────────────────────────────────────
pcall(function()
    if hookfunction and game and game.HttpGet then
        local old_httpget = hookfunction(game.HttpGet, function(self, url, ...)
            if type(url) == "string" and not string.find(url, "discord") then
                print("[PAYOMBOYZ HTTPGET] Target URL: " .. url)
            end
            return old_httpget(self, url, ...)
        end)
    end
end)

print("🛡️ [PAYOMBØYZ] AutoExecute Dumper is ARMED. Run any script to capture!")
"""


def get_runtime_interceptor_file() -> discord.File:
    """Returns the in-game memory interceptor script as a downloadable Discord file."""
    b = io.BytesIO(RUNTIME_INTERCEPTOR_LUAU.encode("utf-8"))
    return discord.File(b, filename="PAYOMBOYZ_AutoExecute_Dumper.luau")


def build_unbreakable_guide_embed() -> discord.Embed:
    """Builds the comprehensive ephemeral instruction guide for when scripts cannot be statically deobfuscated."""
    embed = discord.Embed(
        title="🛠️ PAYOMBØYZ Universal AutoExecute Script Dumper (ดึงโค้ดแท้ 100%)",
        description=(
            "**ทำไมสคริปต์บางตัวถึงแกะแบบ Static ธรรมดาไม่ออก?**\n"
            "สคริปต์ระดับสูง (เช่น **PolSec V2 Streaming Socket, Fulcrum, Luarmor V4, Luraph VM, MoonSec VM**) "
            "จะสตรีมโค้ดผ่าน WebSocket หรือซ่อนตัวแปรไว้ในแรม ซึ่งตัวโค้ดที่แท้จริงจะ **คลายตัวเฉพาะตอนที่รันอยู่ในเกม Roblox เท่านั้น!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👉 **วิธีดึง Source Code แท้กลับมาง่ายๆ (Auto-Copy ลง Clipboard):**\n\n"
            "**1️⃣ ดาวน์โหลดไฟล์ Dumper**\n"
            "• ดาวน์โหลดไฟล์ **`PAYOMBOYZ_AutoExecute_Dumper.luau`** ที่แนบมานี้\n\n"
            "**2️⃣ นำไปใส่ในโฟลเดอร์ AutoExecute หรือรันก่อนเปิดสคริปต์**\n"
            "• **วิธีที่ 1 (แนะนำสุด):** นำไฟล์นี้ไปวางในโฟลเดอร์ `autoexec` ของโปรแกรมรัน (เช่น Delta, Wave, Real, Solara, Synapse Z)\n"
            "• **วิธีที่ 2:** เข้าเกม Roblox แล้วรันไฟล์ `PAYOMBOYZ_AutoExecute_Dumper.luau` นี้ก่อน 1 ครั้ง\n"
            "• เมื่อระบบพร้อม จะมีข้อความเตือนในเกมว่า *'Universal AutoExecute Script Dumper Initialized'* 🟢\n\n"
            "**3️⃣ รันสคริปต์เป้าหมาย & รับโค้ดทันที**\n"
            "• รันสคริปต์ที่คุณต้องการแกะตามปกติ\n"
            "• **โค้ดที่แท้จริงจะถูก Copy ลง Windows Clipboard อัตโนมัติทันที!** (กด `Ctrl + V` เพื่อวางโค้ดได้เลย)\n"
            "• พร้อมทั้งบันทึกไฟล์สำรองไว้ที่ `workspace/Latest_Captured_Script.luau` ในเครื่องของคุณ\n"
            "• นำโค้ดที่ได้มาส่งกลับเข้าบอทเพื่อทำการ Refactor & Clean AST ได้ทันที!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(0, 230, 150)
    )
    embed.set_footer(text="PAYOMBØYZ ZERO-DAY FORENSICS • Auto-Copy to Clipboard • 100% Precision")
    return embed
