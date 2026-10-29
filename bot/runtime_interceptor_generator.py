# -*- coding: utf-8 -*-
"""
========================================================================================
🌪️ PAYOMBØYZ RUNTIME MEMORY INTERCEPTOR & ZERO-DAY AUTO-DUMPER GENERATOR
- Generates 100% executable Luau AutoExecute & Runtime Memory Interceptors for Executors
- Compatible with: Real, Delta, Wave, Solara, Synapse Z, Xeno, MacSploit, Argon, etc.
- Multi-Stage Snooper: Luarmor, Jnkie, Polsec V2, Fulcrum WebSockets, Luraph, MoonSec VM
- Intercepts all network sinks: game:HttpGet, game:HttpGetAsync, request, syn.request
- Intelligent Asset Filter: Blocks UI icon/spritesheet tables from overwriting real scripts
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
-- Powered by: PAYOMBØYZ CYBER-AI (Autonomous Forensics & Universal Memory Unpacker)
-- Target Output: Windows Clipboard (Ctrl+V) & workspace/Latest_Captured_Script.luau
-- Compatible with: Real, Delta, Wave, Solara, Synapse Z, Xeno, MacSploit, Celery
-- Intercepts:
--   • Luarmor (V4/V5 init scripts & CDN payloads)
--   • Jnkie / ScriptBlox / Rscripts / Pastebin / GitHub Raw
--   • Polsec V2 / Fulcrum Cloud Streaming WebSockets (decodeCache)
--   • Luraph VM / MoonSec VM / IronBrew / PSU VM Bytecode
--   • All Network Sinks (HttpGet, HttpGetAsync, request, syn.request, http_request)
--   • All Dynamic Execution Sinks (loadstring, load, loadfile)
--   • Unpacked Closure Tables (setmetatable module dumps)
-- Intelligent Filter:
--   • Filters out UI asset tables (Tree Hub CLI, Lucide icons, Spritesheets)
--   • Prevents icon libraries from overwriting your game script in clipboard!
-- ==============================================================================

if getgenv and getgenv().__PAYOMBOYZ_DUMPER_LOADED then
    print("🔁 [PAYOMBØYZ] Universal Auto-Dumper is already active in memory.")
    return
end

local G = (getgenv and getgenv()) or _G
pcall(function() G.__PAYOMBOYZ_DUMPER_LOADED = true end)

print("==================================================================")
print("🚀 [PAYOMBØYZ] UNIVERSAL ZERO-DAY AUTOEXEC SCRIPT DUMPER INITIALIZED")
print("🎯 Targets: Luarmor, Jnkie, Polsec, Luraph, HttpGet & All Loaders")
print("🛡️ Asset Filter: ACTIVE (Icons/Spritesheets will NOT stomp clipboard)")
print("📋 Auto-Copy to Clipboard: ACTIVE (Ctrl+V immediately after execution)")
print("💾 Workspace Backup: workspace/Latest_Captured_Script.luau")
print("==================================================================")

local real_loadstring   = loadstring or (G and G.loadstring)
local real_load         = load or (G and G.load)
local real_writefile    = writefile or (G and G.writefile)
local real_readfile     = readfile or (G and G.readfile)
local real_appendfile   = appendfile or (G and G.appendfile)
local real_makefolder   = makefolder or (G and G.makefolder)
local real_isfolder     = isfolder or (G and G.isfolder)
local real_setclipboard = setclipboard or toclipboard or (G and G.setclipboard) or (Clipboard and Clipboard.set) or writeclipboard
local real_hookfunc     = hookfunction or replaceclosure or (G and G.hookfunction)

-- Ensure workspace directory structure
pcall(function()
    if real_makefolder and real_isfolder then
        if not real_isfolder("Captured_Scripts") then
            real_makefolder("Captured_Scripts")
        end
        if not real_isfolder("Captured_Scripts/Assets") then
            real_makefolder("Captured_Scripts/Assets")
        end
    end
end)

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. STEALTH ANTI-TAMPER & ENVIRONMENT SPOOFING (PREVENTS LOADER DETECTION)
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

-- Protect WebSocket native C closure (Prevents Polsec / Fulcrum disconnect loops)
pcall(function()
    if WebSocket and WebSocket.Connect then
        WebSocket.connect = WebSocket.Connect
        if G.WebSocket then G.WebSocket.connect = WebSocket.Connect end
    end
end)

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. INTELLIGENT ASSET & PAYLOAD CLASSIFICATION ENGINE
-- ─────────────────────────────────────────────────────────────────────────────
local capturedHashes = {}
local dumpCount = 0
local highestClipboardPriority = 0

local function fastHash(s)
    local h = 5381
    local len = #s
    local step = math.max(1, math.floor(len / 40))
    for i = 1, len, step do
        h = ((h * 33) + string.byte(s, i)) % 4294967296
    end
    return string.format("%d_%08x", len, h)
end

-- Detects whether a string is a pure UI icon table, font mapping, or spritesheet
local function isAssetOrIconTable(src)
    if not src or type(src) ~= "string" then return true end
    
    if src:find("Tree Hub CLI") or src:find("moderated icons") or src:find("Spritesheets =") 
       or src:find("Apple SF Symbols") or src:find("7330 icons") or src:find("LucideIcons") then
        return true
    end

    local _, assetCount = src:gsub("rbxassetid://", "")
    if assetCount > 4 then
        local lines = #string.split(src, "\\n")
        if assetCount / math.max(1, lines) > 0.25 then
            return true
        end
    end

    if src:match("^%s*return%s*%{") and not src:find("function") and not src:find("local ") and not src:find("GetService") then
        return true
    end

    return false
end

-- Scores payload to determine priority for clipboard & primary output
local function scorePayload(src)
    if isAssetOrIconTable(src) then
        return 0, "ASSET_TABLE"
    end

    local isGameScript = false
    if src:find("FireServer") or src:find("InvokeServer") or src:find("VirtualInputManager") 
       or src:find("HumanoidRootPart") or src:find("hookfunction") or src:find("hookmetamethod")
       or src:find("LPH-") or src:find("LPH_") or src:find("Luarmor") or src:find("v4_init")
       or src:find("MoonSec") or src:find("PSC4N") or src:find("Polsec") or src:find("superflow")
       or src:find("CurrentRoundClient") or src:find("GunDrop") or src:find("KnifeServer") then
        return 100, "GAME_PAYLOAD"
    end

    if src:find("CreateWindow") or src:find("AddTab") or src:find("CreateTab") or src:find("AddSection") or src:find("Theme =") then
        return 60, "UI_LIBRARY"
    end

    return 40, "GENERIC_SCRIPT"
end

local function appendManifest(entryText)
    if not real_writefile then return end
    pcall(function()
        local manifestPath = "Captured_Scripts/MANIFEST.txt"
        local ts = os.date("!%Y-%m-%d %H:%M:%SZ")
        local line = string.format("[%s] %s\\n", tostring(ts), entryText)
        if real_appendfile then
            real_appendfile(manifestPath, line)
        else
            local existing = ""
            if real_readfile then
                pcall(function() existing = real_readfile(manifestPath) or "" end)
            end
            real_writefile(manifestPath, existing .. line)
        end
    end)
end

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. HARVEST PIPELINE (DEDUPLICATES, CLASSIFIES, AND COPIES TO CLIPBOARD)
-- ─────────────────────────────────────────────────────────────────────────────
local function harvestScript(src, origin, extraInfo)
    if not src or type(src) ~= "string" or #src < 100 then return end

    if src:find("PAYOMBOYZ_DUMPER_LOADED") or src:find("UNIVERSAL ZERO-DAY AUTOEXEC SCRIPT DUMPER") then
        return
    end

    if src:find("Zstd decoder adapted from") or src:find("101arrowz/fzstd") then
        return
    end

    local low = src:sub(1, 200):lower()
    if low:find("<!doctype html") or low:find("<html") or low:find("<head>") then
        return
    end

    local h = fastHash(src)
    if capturedHashes[h] then return end
    capturedHashes[h] = true

    dumpCount = dumpCount + 1
    local lineCount = #string.split(src, "\\n")
    local sizeBytes = #src
    local prio, tag = scorePayload(src)
    local timeStampStr = tostring(os.date("%Y%m%d_%H%M%S"))

    -- CASE A: PURE ASSET / ICON TABLE (TIER 0) - NEVER STOMPS THE CLIPBOARD!
    if prio == 0 then
        if real_writefile then
            pcall(function()
                local assetFile = string.format("Captured_Scripts/Assets/Asset_%s_%d.luau", timeStampStr, dumpCount)
                real_writefile(assetFile, src)
            end)
        end
        print(string.format("🛡️ [PAYOMBØYZ:ASSET_FILTER] Ignored Icon/Asset Table #%d (%d bytes) from %s - Kept real script in clipboard!", dumpCount, sizeBytes, tostring(origin)))
        appendManifest(string.format("Filtered Asset #%d (%d bytes) from %s [%s] -> Saved to Assets/", dumpCount, sizeBytes, tostring(origin), tostring(extraInfo or "")))
        return
    end

    -- CASE B: VALID SCRIPT PAYLOAD (TIER 40 - 100)
    print("==================================================================")
    print(string.format("🎉 [PAYOMBØYZ] CAPTURED SCRIPT #%d [%s | Priority: %d]!", dumpCount, tag, prio))
    print(string.format("   Origin: %s %s", tostring(origin), extraInfo and ("(" .. tostring(extraInfo) .. ")") or ""))
    print(string.format("   Size: %d bytes | Lines: %d", sizeBytes, lineCount))

    local scriptFilename = string.format("Captured_Scripts/Script_%s_%s_%d.luau", tag, timeStampStr, dumpCount)
    if real_writefile then
        pcall(function()
            real_writefile(scriptFilename, src)
        end)
    end

    local isPromotedToClipboard = false
    if prio >= highestClipboardPriority then
        highestClipboardPriority = prio
        isPromotedToClipboard = true

        if real_setclipboard then
            pcall(function() real_setclipboard(src) end)
        end

        if real_writefile then
            pcall(function()
                real_writefile("Latest_Captured_Script.luau", src)
                real_writefile("PAYOMBOYZ_DUMPED_RAW.luau", src)
            end)
        end

        print("   📋 STATUS: PROMOTED TO WINDOWS CLIPBOARD (Ctrl+V)!")
        print("   💾 BACKUP: workspace/Latest_Captured_Script.luau")

        pcall(function()
            game:GetService("StarterGui"):SetCore("SendNotification", {
                Title = string.format("🎉 %s CAPTURED!", tag),
                Text = string.format("กู้คืนโค้ดสำเร็จ (%d KB) กด Ctrl+V ได้เลย!", math.floor(sizeBytes / 1024)),
                Duration = 6
            })
        end)
    else
        print("   📁 STATUS: Saved to Captured_Scripts (Preserved higher-priority script in clipboard)")
    end

    print("==================================================================")
    appendManifest(string.format("Captured #%d [%s | Prio %d] (%d bytes) from %s [%s] -> %s", dumpCount, tag, prio, sizeBytes, tostring(origin), tostring(extraInfo or ""), isPromotedToClipboard and "[COPIED TO CLIPBOARD]" or "[STORED IN VAULT]"))
end

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. UNIVERSAL NETWORK SINK HOOKS (JNKIE, SCRIPTBLOX, LUARMOR CDN, GITHUB)
-- ─────────────────────────────────────────────────────────────────────────────
pcall(function()
    if not real_hookfunc then return end

    if game and game.HttpGet then
        local old_httpget
        old_httpget = real_hookfunc(game.HttpGet, function(self, url, ...)
            local res = old_httpget(self, url, ...)
            if type(res) == "string" and #res > 100 then
                local u_str = tostring(url or "HttpGet")
                if not u_str:find("discord") and not u_str:find("roblox.com/v1") then
                    task.spawn(function()
                        harvestScript(res, "HttpGet", u_str)
                    end)
                end
            end
            return res
        end)
    end

    if game and game.HttpGetAsync then
        local old_httpgetasync
        old_httpgetasync = real_hookfunc(game.HttpGetAsync, function(self, url, ...)
            local res = old_httpgetasync(self, url, ...)
            if type(res) == "string" and #res > 100 then
                local u_str = tostring(url or "HttpGetAsync")
                if not u_str:find("discord") and not u_str:find("roblox.com/v1") then
                    task.spawn(function()
                        harvestScript(res, "HttpGetAsync", u_str)
                    end)
                end
            end
            return res
        end)
    end

    local req_targets = {
        request,
        (syn and syn.request),
        http_request,
        (fluxus and fluxus.request),
        (krnl and krnl.request),
        (http and http.request)
    }

    for _, req_fn in ipairs(req_targets) do
        if type(req_fn) == "function" then
            pcall(function()
                local old_req
                old_req = real_hookfunc(req_fn, function(options, ...)
                    local resp = old_req(options, ...)
                    if type(resp) == "table" and type(resp.Body) == "string" and #resp.Body > 100 then
                        local target_url = (type(options) == "table" and options.Url) or "request"
                        if not tostring(target_url):find("discord") then
                            task.spawn(function()
                                harvestScript(resp.Body, "request()", target_url)
                            end)
                        end
                    end
                    return resp
                end)
            end)
        end
    end
end)

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. MULTI-STAGE POLSEC & FULCRUM CODEC SNOOPER (DECODECACHE / WEBSOCKET)
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
-- 6. UNIVERSAL LOADSTRING / LOAD / LOADFILE SINK INTERCEPTOR
-- ─────────────────────────────────────────────────────────────────────────────
local function universalTrap(codeStr, chunkName)
    local src = tostring(codeStr or "")
    local chunk = tostring(chunkName or "anonymous")

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

    if #src >= 100 then
        local originTag = "loadstring"
        if src:find("LPH-") or src:find("LPH_") or src:find("Luraph") then
            originTag = "Luraph VM"
        elseif src:find("Luarmor") or src:find("v4_init") or src:find("v5_init") then
            originTag = "Luarmor"
        elseif src:find("MoonSec") then
            originTag = "MoonSec VM"
        elseif src:find("jnkie") then
            originTag = "Jnkie"
        end
        harvestScript(src, originTag, chunk)
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
-- 7. SETMETATABLE HOOK (Luarmor V4 / Luraph VM Unpacked Module Tables)
-- ─────────────────────────────────────────────────────────────────────────────
local old_setmetatable = real_hookfunc and (getgenv and getgenv().setmetatable or setmetatable)
if old_setmetatable and real_hookfunc then
    pcall(function()
        real_hookfunc(setmetatable, function(tbl, meta)
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
                    harvestScript(moduleContent, "setmetatable (Module Table)", string.format("%d_funcs", fn_count))
                end
            end
            return old_setmetatable(tbl, meta)
        end)
    end)
end

print("🛡️ [PAYOMBØYZ] AutoExecute Dumper is ARMED. Run ANY script to capture!")
"""


def get_runtime_interceptor_file() -> discord.File:
    """Returns the in-game memory interceptor script as a downloadable Discord file."""
    b = io.BytesIO(RUNTIME_INTERCEPTOR_LUAU.encode("utf-8"))
    return discord.File(b, filename="PAYOMBOYZ_AutoExecute_Dumper.luau")


def build_unbreakable_guide_embed() -> discord.Embed:
    """Builds the comprehensive ephemeral instruction guide for when scripts cannot be statically deobfuscated."""
    embed = discord.Embed(
        title="🛠️ PAYOMBØYZ Universal AutoExecute Script Dumper (ดักจับทุกสคริปต์ 100%)",
        description=(
            "**ตัวดักจับระดับสากล (Universal Anti-Obfuscation & In-Game RAM Sniffer)**\n"
            "รองรับการดักจับสคริปต์ทุกชนิด: **Luarmor V4/V5, Jnkie, ScriptBlox, Polsec V2 Streaming, Luraph VM, MoonSec VM, HttpGet, request()**\n\n"
            "🛡️ **ระบบป้องกัน Asset Stomping (ใหม่ล่าสุด!):**\n"
            "• คัดกรองและแยกแยะตารางไอคอนของ UI Library (เช่น Tree Hub CLI, Lucide icons, Spritesheets) ไม่ให้ไปแย่งพื้นที่คลิปบอร์ดของโค้ดเกมแท้\n"
            "• โค้ดเกมตัวหลักจะถูกดันขึ้น **Priority 100** เข้า Clipboard เสมอ\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👉 **วิธีใช้งานเพื่อดึง Source Code แท้ (Auto-Copy ลง Clipboard):**\n\n"
            "**1️⃣ ดาวน์โหลดไฟล์ Dumper**\n"
            "• ดาวน์โหลดไฟล์ **`PAYOMBOYZ_AutoExecute_Dumper.luau`** ที่แนบมานี้\n\n"
            "**2️⃣ นำไปใส่ในโฟลเดอร์ AutoExecute หรือรันก่อนเปิดสคริปต์**\n"
            "• **วิธีที่ 1 (แนะนำที่สุด):** นำไฟล์นี้ไปวางในโฟลเดอร์ `autoexec` ของโปรแกรมรัน (เช่น Real, Delta, Wave, Solara, Synapse Z, Xeno)\n"
            "• **วิธีที่ 2:** เข้าเกม Roblox แล้วรันไฟล์ `PAYOMBOYZ_AutoExecute_Dumper.luau` นี้ก่อน 1 ครั้ง\n"
            "• เมื่อระบบพร้อม จะมีข้อความเตือนในเกมว่า *'UNIVERSAL ZERO-DAY AUTOEXEC SCRIPT DUMPER INITIALIZED'* 🟢\n\n"
            "**3️⃣ รันสคริปต์เป้าหมาย & รับโค้ดทันที**\n"
            "• รันสคริปต์ Luarmor, Jnkie, หรือตัวใดก็ตามที่คุณต้องการแกะ\n"
            "• **โค้ดที่แท้จริงจะถูก Copy ลง Windows Clipboard อัตโนมัติทันที!** (กด `Ctrl + V` เพื่อวางโค้ดได้เลย)\n"
            "• สคริปต์ทั้งหมดจะถูกบันทึกสำรองไว้ที่โฟลเดอร์ `workspace/Captured_Scripts/` และมีไฟล์ `MANIFEST.txt` สรุปให้ครบทุกตัว!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(0, 230, 150)
    )
    embed.set_footer(text="PAYOMBØYZ ZERO-DAY FORENSICS • Intelligent Asset Filter • 100% Precision")
    return embed
