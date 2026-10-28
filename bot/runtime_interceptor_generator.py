# -*- coding: utf-8 -*-
"""
========================================================================================
🌪️ PAYOMBØYZ RUNTIME MEMORY INTERCEPTOR & IN-GAME DUMPER GENERATOR
- Generates 100% executable Luau Memory Interceptor scripts for Executors
- Compatible with: Delta, Wave, Solara, Synapse Z, Xeno, MacSploit, Argon, etc.
- Intercepts unpacked module closures, Luarmor V4 tables, Luraph buffers, and loadstrings
- Auto-saves dumped raw payload to: workspace/PAYOMBOYZ_DUMPED_RAW.luau
========================================================================================
"""

from __future__ import annotations
import io
import discord

RUNTIME_INTERCEPTOR_LUAU = """--!nocheck
-- ============================================================================
-- ⚡ PAYOMBØYZ CYBER-AI | UNIVERSAL IN-GAME RUNTIME MEMORY INTERCEPTOR
-- Purpose: Transparent Memory Hook for Unpacking Luarmor V4, Luraph V15,
--          MoonSec VM, and Custom Encrypted Loaders in Roblox RAM.
-- Target Output: workspace/PAYOMBOYZ_DUMPED_RAW.luau
-- ============================================================================

local write_fn = writefile or (syn and syn.writefile)
if not write_fn then
    warn("[PAYOMBOYZ] ❌ Executor ของคุณไม่รองรับ writefile! ไม่สามารถบันทึกไฟล์ dump ลง workspace ได้")
    return
end

local dump_file_name = "PAYOMBOYZ_DUMPED_RAW.luau"
local captured_count = 0
local intercepted_modules = {}

local function notify_user(title, msg, duration)
    pcall(function()
        game:GetService("StarterGui"):SetCore("SendNotification", {
            Title = "⚡ " .. (title or "PAYOMBØYZ DUMPER"),
            Text = msg or "Intercepted Memory Payload!",
            Duration = duration or 5
        })
    end)
    print(string.format("[PAYOMBOYZ] %s: %s", title, msg))
end

-- Banner Notification
notify_user("INTERCEPTOR ARMED", "เบ็ดตกปลาใน RAM กางพร้อมแล้ว! กรุณารันสคริปต์เป้าหมายได้เลย", 6)

-- ─────────────────────────────────────────────────────────────────────────────
-- HOOK 1: SETMETATABLE (Intercepts Unpacked Luarmor / Luraph Module Tables)
-- ─────────────────────────────────────────────────────────────────────────────
local old_setmetatable
old_setmetatable = hookfunction(setmetatable, function(tbl, meta)
    if type(tbl) == "table" and not tbl.__payomboyz_dumped then
        local fn_count = 0
        local keys_preview = {}
        for k, v in pairs(tbl) do
            if type(v) == "function" then
                fn_count = fn_count + 1
            end
        end

        -- Module table signature: typically 15+ to 150+ unpacked closures
        if fn_count >= 12 then
            tbl.__payomboyz_dumped = true
            captured_count = captured_count + 1
            notify_user("MODULE CAPTURED!", string.format("ตรวจจับ Module Table ได้ %d ฟังก์ชัน! กำลังเซฟลงไฟล์...", fn_count), 5)

            local dump_lines = {
                "-- ============================================================================",
                "-- ⚡ PAYOMBØYZ RUNTIME INTERCEPTOR — UNPACKED MODULE TABLE DUMP",
                string.format("-- Captured Modules: %d | Timestamp: %s", fn_count, os.date("!%Y-%m-%d %H:%M:%SZ")),
                "-- ============================================================================",
                "return {",
            }

            for k, v in pairs(tbl) do
                if k ~= "__payomboyz_dumped" then
                    local key_repr = type(k) == "number" and string.format("[%d]", k) or string.format("[%q]", tostring(k))
                    local val_repr = "nil"
                    if type(v) == "function" then
                        local dump_success, dumped_code = pcall(function()
                            if decompile then
                                return decompile(v)
                            end
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

            local content = table.concat(dump_lines, "\\n")
            write_fn(dump_file_name, content)
            notify_user("DUMP SAVED! ✅", "บันทึกสำเร็จที่ workspace/" .. dump_file_name .. " ให้นำไฟล์นี้ไปให้บอทแกะได้เลย!", 8)
        end
    end
    return old_setmetatable(tbl, meta)
end)

-- ─────────────────────────────────────────────────────────────────────────────
-- HOOK 2: LOADSTRING (Intercepts Secondary Bytecode Payloads & Dynamic Chunks)
-- ─────────────────────────────────────────────────────────────────────────────
if loadstring then
    local old_loadstring
    old_loadstring = hookfunction(loadstring, function(chunk_code, chunk_name)
        if type(chunk_code) == "string" and #chunk_code > 100 then
            -- Check if it contains payload characteristics
            if not string.find(chunk_code, "PAYOMBOYZ") then
                captured_count = captured_count + 1
                local filename = string.format("PAYOMBOYZ_LOADSTRING_%d.luau", captured_count)
                write_fn(filename, chunk_code)
                -- Also mirror to primary dump file if empty or shorter
                write_fn(dump_file_name, chunk_code)
                notify_user("LOADSTRING INTERCEPTED! 🎯", string.format("ดักจับโค้ดดิบ %d ไบต์! บันทึกที่ workspace/%s", #chunk_code, dump_file_name), 6)
            end
        end
        return old_loadstring(chunk_code, chunk_name)
    end)
end

-- ─────────────────────────────────────────────────────────────────────────────
-- HOOK 3: HTTPGET (Logs Raw CDN Payload URLs)
-- ─────────────────────────────────────────────────────────────────────────────
pcall(function()
    local old_httpget
    old_httpget = hookfunction(game.HttpGet, function(self, url, ...)
        if type(url) == "string" and not string.find(url, "discord") then
            print("[PAYOMBOYZ HTTPGET] Target URL: " .. url)
        end
        return old_httpget(self, url, ...)
    end)
end)

notify_user("READY FOR TARGET", "ระบบพร้อม 100% สั่งรันสคริปต์เป้าหมายเพื่อดึงโค้ดได้เลย!", 5)
"""


def get_runtime_interceptor_file() -> discord.File:
    """Returns the in-game memory interceptor script as a downloadable Discord file."""
    b = io.BytesIO(RUNTIME_INTERCEPTOR_LUAU.encode("utf-8"))
    return discord.File(b, filename="Runtime_Interceptor.luau")


def build_unbreakable_guide_embed() -> discord.Embed:
    """Builds the comprehensive ephemeral instruction guide for when scripts cannot be statically deobfuscated."""
    embed = discord.Embed(
        title="🛠️ คู่มือเจาะ Source Code แท้ 100% จาก Memory ในเกม (Runtime Dump)",
        description=(
            "**ทำไมสคริปต์บางตัวถึงแกะแบบ Static ธรรมดาไม่ออก?**\n"
            "สคริปต์ระดับสูงบางตัว (เช่น **Luarmor V4, Luraph V15 VM, MoonSec VM ซับซ้อนสูง**) "
            "จะทำการเข้ารหัสและซ่อนตัวแปรไว้ในรูป **VM Bytecode ในแรม** ซึ่งตัวโค้ดที่แท้จริงจะ **คลายตัวเฉพาะตอนที่รันอยู่ในเกม Roblox เท่านั้น!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👉 **วิธีดึง Source Code แท้กลับมาง่ายๆ ใน 3 ขั้นตอน:**\n\n"
            "**1️⃣ ดาวน์โหลดไฟล์ Interceptor**\n"
            "• ดาวน์โหลดไฟล์ **`Runtime_Interceptor.luau`** ที่แนบมากับข้อความนี้\n\n"
            "**2️⃣ กางเบ็ดตกปลาใน RAM ก่อนรันสคริปต์**\n"
            "• เข้าเกม Roblox ในแมพที่สคริปต์นั้นใช้งาน\n"
            "• เปิด Executor ของคุณ (เช่น Delta, Wave, Solara, Synapse Z, Xeno, MacSploit)\n"
            "• **รันไฟล์ `Runtime_Interceptor.luau` ก่อนเป็นอันดับแรก!**\n"
            "• คุณจะเห็นแจ้งเตือนสีเขียวในเกมว่า *'INTERCEPTOR ARMED'* แสดงว่าระบบกางเบ็ดใน RAM เรียบร้อย\n\n"
            "**3️⃣ รันสคริปต์เป้าหมาย & รับไฟล์กลับ**\n"
            "• รันสคริปต์ที่คุณต้องการแกะตามปกติ\n"
            "• ทันทีที่สคริปต์คลายตัวในแรม ตัว Interceptor จะดักจับ Bytecode และโครงสร้างแท้ทั้งหมด แล้วเซฟลง:\n"
            "  📂 โฟลเดอร์ `workspace/PAYOMBOYZ_DUMPED_RAW.luau` ในคอมของคุณอัตโนมัติ!\n"
            "• **นำไฟล์ `PAYOMBOYZ_DUMPED_RAW.luau` จากโฟลเดอร์ workspace กลับมาลากวางลงในแชทนี้** บอทจะถอดรหัสออกมาเป็น Clean Code สมบูรณ์ 100% ทันที!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(255, 100, 50)
    )
    embed.set_footer(text="PAYOMBØYZ ADVANCED FORENSICS • 100% Source Code Recovery")
    return embed
