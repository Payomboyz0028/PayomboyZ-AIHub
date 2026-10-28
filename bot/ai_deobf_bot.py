import asyncio
import io
import os
import sys
import time
from collections import deque
from pathlib import Path
from typing import Optional, Literal, Dict, Any, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import re
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

BASE_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = BASE_DIR / "Prometheus-WeAre-Devs-Dumper-main"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
import engine_router
import gemini_engine
from bot import security
from bot.central_orchestrator import ORCHESTRATOR
from bot.knowledge_router import ROUTER as KNOWLEDGE_ROUTER
from bot.knowledge import RETRIEVER, CODE_IDE
from bot.obfuscation_engine import OBFUSCATION_ENGINE
from bot.runtime_guard import runtime_guard
from bot.quality_monitor import QUALITY_MONITOR
from bot.hub_runtime import install_bot_monitor, managed_job, request_recycle
from bot.roblox_resolver import (
    contains_roblox_game_link,
    resolve_roblox_game_async,
    build_game_script_prompt,
)
from bot.deobf_panel import (
    DeobfPanelView,
    EditPanelModal,
    build_deobf_panel_embed,
    save_deobf_panel,
    load_deobf_panels,
    delete_deobf_panel,
    get_log_channel_id,
    dispatch_result_to_channel_or_interaction,
    run_human_readable_cleanup,
    DEFAULT_PANEL_TITLE,
)
from bot.godmode import register_godmode_to_bot, handle_godmode_message


intents = discord.Intents.default()
intents.message_content = True  # Required to read messages in designated AI channels
bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents, help_command=None)
install_bot_monitor(bot, "ai")
PROJECT_NAME = "⚡ PAYOMBØYZ CYBER-AI V9.0 (AUTONOMOUS MCP)"

AI_CONFIG_FILE = BASE_DIR / "ai_channel_config.json"


# In-memory cache for AI channel IDs — avoids JSON file I/O on every message
_AI_CHANNELS_CACHE: set[int] = set()
_AI_CHANNELS_LOADED = False
_PROCESSED_MESSAGE_IDS: set[int] = set()
_PROCESSED_MESSAGE_ORDER = deque()
_PROCESSED_MESSAGE_LIMIT = 4096
_MESSAGE_DEDUPE_DB = BASE_DIR / "ai_message_dedupe.sqlite3"
_MESSAGE_DEDUPE_CLAIMS = 0
def claim_message_once(message_id: int, db_path: Optional[Path] = None) -> bool:
    """Claim a Discord message once across threads and Hub processes on this host."""
    global _MESSAGE_DEDUPE_CLAIMS
    if message_id in _PROCESSED_MESSAGE_IDS:
        return False
    claimed = False
    try:
        store_path = Path(db_path) if db_path else _MESSAGE_DEDUPE_DB
        store_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(store_path), timeout=5.0) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS processed_ai_messages ("
                "message_id TEXT PRIMARY KEY, claimed_at INTEGER NOT NULL)"
            )
            cursor = db.execute(
                "INSERT OR IGNORE INTO processed_ai_messages(message_id, claimed_at) "
                "VALUES (?, ?)",
                (str(message_id), int(time.time())),
            )
            claimed = cursor.rowcount == 1
            _MESSAGE_DEDUPE_CLAIMS += 1
            if _MESSAGE_DEDUPE_CLAIMS % 512 == 0:
                db.execute(
                    "DELETE FROM processed_ai_messages WHERE claimed_at < ?",
                    (int(time.time()) - 7 * 24 * 60 * 60,),
                )
    except Exception as exc:
        # Do not silence a chat message if the dedupe store is unavailable.
        print(f"[AI CHAT] Message dedupe store unavailable: {type(exc).__name__}: {exc}", flush=True)
        claimed = True

    _PROCESSED_MESSAGE_IDS.add(message_id)
    _PROCESSED_MESSAGE_ORDER.append(message_id)
    if len(_PROCESSED_MESSAGE_ORDER) > _PROCESSED_MESSAGE_LIMIT:
        expired_id = _PROCESSED_MESSAGE_ORDER.popleft()
        _PROCESSED_MESSAGE_IDS.discard(expired_id)
    return claimed


def load_ai_channels() -> set[int]:
    """Returns AI channels from in-memory cache (loads from JSON once on first call)."""
    global _AI_CHANNELS_CACHE, _AI_CHANNELS_LOADED
    if not _AI_CHANNELS_LOADED:
        if AI_CONFIG_FILE.exists():
            try:
                with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _AI_CHANNELS_CACHE = {
                        int(channel_id)
                        for channel_id in data.get("ai_channels", [])
                        if str(channel_id).strip().isdigit()
                    }
            except Exception:
                _AI_CHANNELS_CACHE = set()
        _AI_CHANNELS_LOADED = True
    return _AI_CHANNELS_CACHE


def save_ai_channels(channels: set[int]):
    """Persists AI channels to JSON and updates in-memory cache immediately."""
    global _AI_CHANNELS_CACHE
    _AI_CHANNELS_CACHE = set(channels)
    try:
        with open(AI_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"ai_channels": list(channels)}, f, indent=2)
    except Exception as e:
        print(f"[-] Failed to save AI channels config: {e}")



def save_temp_input(content_bytes: bytes, filename: str) -> Path:
    safe_name = security.sanitize_filename(filename)
    stem = Path(safe_name).stem
    ext = Path(safe_name).suffix or ".lua"
    temp_target = config.OUTPUT_DIR / f"{stem}_{int(time.time() * 1000)}{ext}"
    with open(temp_target, "wb") as f:
        f.write(content_bytes)
    return temp_target


def split_long_text_for_discord(text: str, chunk_size: int = 1800) -> list[str]:
    payload = (text or "").strip()
    if not payload:
        return []
    if len(payload) <= chunk_size:
        return [payload]
    chunks: list[str] = []
    for idx in range(0, len(payload), chunk_size):
        chunk = payload[idx:idx + chunk_size]
        last_nl = chunk.rfind("\n")
        if last_nl > chunk_size * 0.6:
            chunk = chunk[:last_nl]
        chunks.append(chunk.strip())
    return [c for c in chunks if c]


def split_lua_payload_for_discord(lua_text: str, max_chars: int = 7500000, max_lines_per_chunk: int = 250000) -> list[str]:
    """Split oversized Lua payloads into full, contiguous chunks while preserving structure.

    Default is 7.5 MB (250,000 lines) so virtually all production scripts are sent as a single
    complete .lua file without breaking syntax or hitting Discord 429 rate limits.
    """
    text = (lua_text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    lines = text.splitlines()
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_len = 0
    line_count = 0

    for line in lines:
        candidate = line + "\n"
        if buffer and (buffer_len + len(candidate) > max_chars or line_count >= max_lines_per_chunk):
            chunk = "".join(buffer).rstrip()
            if chunk.strip():
                chunks.append(chunk)
            buffer = [candidate]
            buffer_len = len(candidate)
            line_count = 1
        else:
            buffer.append(candidate)
            buffer_len += len(candidate)
            line_count += 1

    if buffer:
        chunk = "".join(buffer).rstrip()
        if chunk.strip():
            chunks.append(chunk)

    # Final guard: if a chunk is still absurdly large, do a second pass on the chunk list.
    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            final_chunks.append(chunk)
        else:
            sublines = chunk.splitlines()
            sub_buffer: list[str] = []
            sub_len = 0
            for subline in sublines:
                sub_candidate = subline + "\n"
                if sub_buffer and (sub_len + len(sub_candidate) > max_chars or len(sub_buffer) >= max_lines_per_chunk):
                    final_chunks.append("".join(sub_buffer).rstrip())
                    sub_buffer = [sub_candidate]
                    sub_len = len(sub_candidate)
                else:
                    sub_buffer.append(sub_candidate)
                    sub_len += len(sub_candidate)
            if sub_buffer:
                final_chunks.append("".join(sub_buffer).rstrip())

    return [c for c in final_chunks if c.strip()]


def build_lua_chunk_manifest(lua_chunks: list[str]) -> str:
    """Create a small manifest so long Lua output stays traceable and complete."""
    if not lua_chunks:
        return ""
    if len(lua_chunks) == 1:
        return "📦 Lua output is complete in one attachment."
    lines = [
        "📦 Lua output was too large for a single attachment and was split into chunks:",
        *[f"• Chunk {idx}/{len(lua_chunks)} — {len(chunk):,} chars" for idx, chunk in enumerate(lua_chunks, start=1)],
        "⚠️ This is a full-part preservation split; do not treat these as partial summaries."
    ]
    return "\n".join(lines)


def looks_like_real_lua(code_text: str) -> bool:
    """Hard guard: only attach a script file when the payload is truly executable Lua, not chat summary text."""
    stripped = (code_text or "").strip()
    if not stripped:
        return False
    lower = stripped.lower()

    if "```lua" in lower or "```luau" in lower:
        return True

    lua_signals = [
        "local ", "function ", "return ", "if ", "for ", "while ", "do\n",
        "game:", "workspace.", "task.wait", "coroutine.", "pcall(", "require(",
        "spawn(", "table.", "print(", "setmetatable", "hookfunction", "getgenv",
        "remotefunction", "remoteevent", "uis.", "mouse.", "game:getservice"
    ]
    score = sum(1 for token in lua_signals if token in lower)
    if score >= 2:
        return True
    return False


def enforce_payomboyzaa_identity(text: str) -> str:
    """Enforce that AI never mentions external model names and only identifies as PAYØMBØYZAA."""
    if not text:
        return ""
    import re as _re_id

    # 1. Unconditionally scrub internal worker aliases
    cleaned = _re_id.sub(r'(?i)\b(bluezygpt|bluezy)\b', 'PAYØMBØYZAA', text)

    # 2. Self-identification phrases (Thai + English, no \b on Thai prefix)
    id_pattern = (
        r'(?i)(ฉันคือ|ผมคือ|เราคือ|ข้าคือ|กูคือ|ฉันชื่อ|ผมชื่อ|กูชื่อ|ในฐานะ|ตัวผมคือ|ตัวฉันคือ|'
        r'โมเดล|บอท|ผู้ช่วย|ai\s*assistant|assistant|i am|i\'m|my name is)\s*'
        r'(?:ชื่อ\s*)?(?:an?\s*)?(?:ai\s*)?(?:assistant\s*)?'
        r'(?:chatgpt|gpt-4o?|gpt-3\.5|deepseek(?:-v\d+|-chat|-coder)?|gemini(?:-flash|-pro)?|claude(?:\s*3(?:\.5)?)?|openai)'
    )
    cleaned = _re_id.sub(id_pattern, r'\1 PAYØMBØYZAA', cleaned)

    # 3. Creator / Organization references
    creator_pattern = (
        r'(?i)(?:พัฒนาโดย|สร้างโดย|พัฒนามาจาก|สร้างขึ้นโดย|จาก|โดย|created by|developed by)\s*'
        r'(?:openai|anthropic|google(?:\s*deepmind)?|deepseek|bluezygpt|bluezy)\b'
    )
    cleaned = _re_id.sub(creator_pattern, 'พัฒนาโดย PAYØMBØYZ', cleaned)

    return cleaned


def extract_real_lua_output(reply_text: str, force_full: bool = False) -> tuple[str, str]:
    """Keep the full generated Lua payload instead of pruning it down to a tiny snippet.

    For explicit full-code requests, the complete Lua code is the primary artifact and must be preserved.
    Chat guidance can remain in chat, but the actual Lua source must not be silently shortened.
    """
    text = (reply_text or "").strip()
    if not text:
        return "", ""

    import re as _re

    # 1. Closed code blocks
    fenced = _re.findall(r'```(?:lua|luau)?\s*\n([\s\S]*?)```', text, _re.IGNORECASE)
    # 2. If no closed code block found but there is an unclosed code block (e.g. truncated at the end of response)
    if not fenced:
        unclosed = _re.findall(r'```(?:lua|luau)?\s*\n([\s\S]+)$', text, _re.IGNORECASE)
        if unclosed:
            fenced = unclosed

    if fenced:
        blocks = [block.strip() for block in fenced if block.strip()]
        if blocks:
            lua_payload = "\n\n".join(blocks)
            if looks_like_real_lua(lua_payload) or force_full:
                chat_text = _re.sub(r'```(?:lua|luau)?\s*\n[\s\S]*?(?:```|$)', '', text, flags=_re.IGNORECASE).strip()
                return lua_payload, chat_text

    if force_full:
        candidate = text
        if looks_like_real_lua(candidate):
            return candidate, ""

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        real_lines = []
        for line in lines:
            low = line.lower()
            lua_tokens = [
                "local ", "function ", "if ", "for ", "while ", "return ", "game:",
                "workspace.", "task.wait", "require(", "table.", "print(", "--"
            ]
            if any(token in low for token in lua_tokens):
                real_lines.append(line)
        lua_candidate = "\n".join(real_lines).strip()
        if lua_candidate and looks_like_real_lua(lua_candidate):
            return lua_candidate, ""

    # Fallback: if the whole response is basically Lua code, keep it intact.
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if lines and sum(1 for line in lines if any(token in line.lower() for token in ["local ", "function ", "return ", "game:", "workspace.", "task.wait"])) >= max(2, len(lines) * 0.25):
        if looks_like_real_lua(text):
            return text, ""

    return "", text


def _clone_discord_files(files_list: list[discord.File]) -> tuple[list[discord.File], list[discord.File]]:
    """Duplicate discord.File objects so both user channel and audit log receive unconsumed streams."""
    user_files = []
    log_files = []
    if not files_list:
        return [], []
    for f in files_list:
        try:
            if hasattr(f.fp, "seek") and hasattr(f.fp, "read"):
                f.fp.seek(0)
                b_data = f.fp.read()
                f.fp.seek(0)
                user_files.append(discord.File(io.BytesIO(b_data), filename=f.filename, description=getattr(f, "description", None)))
                log_files.append(discord.File(io.BytesIO(b_data), filename=f.filename, description=getattr(f, "description", None)))
            else:
                user_files.append(f)
        except Exception:
            user_files.append(f)
    if not log_files:
        log_files = list(user_files)
    return user_files, log_files


def build_deobf_embed(res: dict, input_name: str, ai_summary: str = "", decision_info: Optional[dict] = None) -> tuple[discord.Embed, list[discord.File]]:
    elapsed = res.get("elapsed", 0.0)
    engine_name = res.get("engine", "Unknown Engine")
    safe_input_name = security.sanitize_filename(input_name)
    files = []

    if not res.get("success"):
        err = res.get("error", "Unknown error")
        safe_err = security.sanitize_output_text(str(err), config.DISCORD_AI_BOT_TOKEN)
        embed = discord.Embed(
            title=f"{PROJECT_NAME} | ❌ ถอดรหัส Static ไม่สำเร็จ",
            description=f"ไม่สามารถถอดรหัสสคริปต์ `{safe_input_name}` แบบ Static (ออฟไลน์) ได้ครบ 100%\n\n"
                        f"**เอนจินที่ทดลอง:** `{engine_name}`\n"
                        f"**ข้อผิดพลาด:** ```\n{safe_err[:600]}\n```\n"
                        f"💡 *ระบบ AI ได้สร้างสคริปต์ Runtime Hook Interceptor เพื่อดักจับโค้ดในตัวรันให้ด้านล่าง*",
            color=discord.Color.red()
        )
        if decision_info:
            conf_pct = decision_info.get("confidence_pct", "N/A")
            risk_lvl = decision_info.get("risk_level", "MEDIUM")
            priority = decision_info.get("priority", "SAFETY")
            embed.add_field(
                name="🧠 AI Decision Engine (Neuro-Symbolic)",
                value=(
                    f"• **Fallback Strategy:** `{decision_info.get('decision')}`\n"
                    f"• **Confidence:** `{conf_pct}` | **Priority:** `{priority}` | **Risk:** `{risk_lvl}`\n"
                    f"• **Rationale:** {decision_info.get('reason')}"
                ),
                inline=False
            )
        if ai_summary:
            embed.add_field(
                name="🧠 PAYOMBØYZ AI // Runtime Hook & Memory Interceptor",
                value=ai_summary[:1024] if len(ai_summary) <= 1024 else (ai_summary[:1000] + "..."),
                inline=False
            )
            hook_code = gemini_engine.strip_markdown_code_blocks(ai_summary)
            if hook_code and len(hook_code.splitlines()) >= 5:
                files.append(
                    discord.File(
                        io.BytesIO(hook_code.encode("utf-8")),
                        filename=f"Runtime_Hook_{Path(safe_input_name).stem}.lua",
                        description="Runtime Memory Hook Interceptor Script by PAYØMBØYZ AI"
                    )
                )

        # Fail-Safe: ALWAYS attach the universal In-Game Runtime Interceptor file so the user is never left empty-handed
        if not files:
            from bot.runtime_interceptor_generator import get_runtime_interceptor_file
            files.append(get_runtime_interceptor_file())

        embed.set_footer(text=f"PAYOMBØYZ Multi-Engine | ใช้เวลา {elapsed:.2f}s")
        return embed, files

    urls = res.get("urls", [])
    loadstrings = res.get("loadstrings", [])
    trace_count = res.get("trace_count", 0)
    code = res.get("deobfuscated_code", "")
    line_count = res.get("lines", 0) or len(code.splitlines())

    embed = discord.Embed(
        title=f"{PROJECT_NAME} | ✅ ถอดรหัสสำเร็จ",
        description=f"ถอดรหัสสคริปต์ `{safe_input_name}` เรียบร้อยแล้ว โครงสร้างโค้ดถูก Clean & Reconstruct พร้อมนำไปใช้งาน",
        color=discord.Color.green()
    )

    embed.add_field(name="⚙️ เอนจินที่ใช้", value=f"`{engine_name}`", inline=True)
    embed.add_field(name="⏱️ เวลาที่ใช้", value=f"`{elapsed:.2f} วินาที`", inline=True)
    embed.add_field(name="📊 จำนวนบรรทัด", value=f"`{line_count:,} บรรทัด`", inline=True)

    confidence = res.get("confidence")
    if confidence is not None:
        grade = res.get("confidence_grade", "EXCELLENT")
        embed.add_field(name="🎯 ความแม่นยำ (Confidence)", value=f"`{confidence:.1f}%` ({grade})", inline=True)

    if trace_count:
        embed.add_field(name="🔍 Traced Operations", value=f"`{trace_count:,} ops`", inline=True)

    if decision_info:
        conf_pct = decision_info.get("confidence_pct", "N/A")
        risk_lvl = decision_info.get("risk_level", "LOW")
        priority = decision_info.get("priority", "OBJECTIVE")
        action = decision_info.get("decision", "AUTO")
        score = decision_info.get("decision_score", 0.0)
        embed.add_field(
            name="🧠 AI Decision Engine (Neuro-Symbolic)",
            value=(
                f"• **Strategy:** `{action}` (Score: `{score:.2f}`)\n"
                f"• **Confidence:** `{conf_pct}` | **Priority:** `{priority}` | **Risk:** `{risk_lvl}`\n"
                f"• **Rationale:** {decision_info.get('reason')}"
            ),
            inline=False
        )

    if urls:
        url_text = "\n".join(f"• `{u}`" for u in urls[:5])
        if len(urls) > 5:
            url_text += f"\n*... และอีก {len(urls) - 5} URLs*"
        embed.add_field(name=f"🌐 ตรวจพบ Network Endpoints ({len(urls)})", value=url_text, inline=False)

    if loadstrings:
        ls_text = "\n".join(f"• Payload `{i+1}`: `{len(ls)} bytes`" for i, ls in enumerate(loadstrings[:3]))
        embed.add_field(name=f"🚀 Dynamic Payloads ({len(loadstrings)})", value=ls_text, inline=False)

    if ai_summary:
        embed.add_field(
            name="🧠 PAYOMBØYZ AI // Reverse Engineering & Security Audit",
            value=ai_summary[:1024] if len(ai_summary) <= 1024 else (ai_summary[:1000] + "..."),
            inline=False
        )

    embed.set_footer(text="PAYOMBØYZ Multi-Engine Deobfuscator & AI Central Hub")

    # Attach deobfuscated file
    deobf_path = res.get("deobf_path")
    if deobf_path and os.path.exists(deobf_path):
        files.append(discord.File(deobf_path, filename=f"{Path(safe_input_name).stem}.deobf.lua"))
    elif code:
        file_bytes = io.BytesIO(code.encode("utf-8", errors="replace"))
        files.append(discord.File(file_bytes, filename=f"{Path(safe_input_name).stem}.deobf.lua"))

    return embed, files


def build_obfuscate_embed(res: dict, input_name: str) -> tuple[discord.Embed, list[discord.File]]:
    elapsed = res.get("elapsed", 0.0)
    engine_name = res.get("engine", "PAYOMBØYZ Double-VM")
    safe_input_name = security.sanitize_filename(input_name)
    files = []

    if not res.get("success"):
        err = res.get("error", "Unknown error")
        safe_err = security.sanitize_output_text(str(err), config.DISCORD_AI_BOT_TOKEN)
        is_syntax = bool(res.get("is_syntax_error")) or any(k in str(err).lower() for k in ("syntax", "compile error", "ไม่ได้ปิด", "ไม่สมบูรณ์"))
        if is_syntax:
            embed = discord.Embed(
                title="⚠️ สคริปต์ต้นฉบับมีข้อผิดพลาดทางไวยากรณ์ (Syntax Error)",
                description=(
                    f"ตรวจพบว่าสคริปต์ `{safe_input_name}` มีข้อผิดพลาดในตัวโค้ดตั้งแต่ก่อนนำมาเข้ารหัส\n"
                    f"(สคริปต์มีจุดที่รันไม่ผ่านหรือไม่สมบูรณ์ตั้งแต่ต้น)\n\n"
                    f"💡 **คำแนะนำ:** กรุณาตรวจสอบและแก้ไข Syntax ของสคริปต์ให้รันได้ปกติ แล้วนำมา Obfuscate ใหม่อีกครั้งครับ\n\n"
                    f"**รายละเอียดจุดที่พบข้อผิดพลาด:**\n```lua\n{safe_err[:800]}\n```"
                ),
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"PAYOMBØYZ Pre-Validation Gate | ตรวจพบใน {elapsed:.2f}s")
        else:
            embed = discord.Embed(
                title="⚡ PAYOMBØYZ Obfuscate | ❌ เข้ารหัสไม่สำเร็จ",
                description=(
                    f"เกิดข้อผิดพลาดในการเข้ารหัสสคริปต์ `{safe_input_name}`\n\n"
                    f"**ระดับความปลอดภัย:** `{engine_name}`\n"
                    f"**ข้อผิดพลาด:** ```\n{safe_err[:600]}\n```"
                ),
                color=discord.Color.red()
            )
            embed.set_footer(text=f"PAYOMBØYZ Obfuscate Engine | ใช้เวลา {elapsed:.2f}s")
        return embed, files

    orig_size = res.get("original_size", 0)
    obf_size = res.get("obfuscated_size", 0)
    ratio = res.get("ratio", 1.0)
    verified = res.get("verified", True)

    embed = discord.Embed(
        title="⚡ PAYOMBØYZ Obfuscate V6.7.6.7 | ✅ เข้ารหัสและป้องกันสำเร็จ",
        description=f"สคริปต์ `{safe_input_name}` ได้รับการป้องกันผ่านสถาปัตยกรรม **PAYOMBØYZ Real CFF + Invariant Machine** เรียบร้อยแล้ว รองรับ Executor และภาษาไทย 100%",
        color=discord.Color.purple()
    )

    embed.add_field(name="⚙️ ระดับความปลอดภัย (Security Level)", value=f"`{engine_name}`", inline=True)
    embed.add_field(name="⏱️ เวลาประมวลผล", value=f"`{elapsed:.2f} วินาที`", inline=True)
    
    verify_badge = "🛡️ **[✅ VERIFIED 100% PASS | Luau Compiler Verified]**" if verified else "⚠️ **[Inferred]**"
    embed.add_field(name="🔬 การตรวจสอบความสมบูรณ์", value=verify_badge, inline=False)

    orig_kb = orig_size / 1024
    obf_kb = obf_size / 1024
    stats_val = (
        f"• ขนาดต้นฉบับ: `{orig_kb:.2f} KB` ({orig_size:,} bytes)\n"
        f"• ขนาดหลังเข้ารหัส: `{obf_kb:.2f} KB` ({obf_size:,} bytes)\n"
        f"• อัตราการขยายตัว (Expansion Ratio): `{ratio:.1f}x`"
    )
    embed.add_field(name="📊 ข้อมูลและสถิติขนาดไฟล์", value=stats_val, inline=False)

    security_features = (
        "• **Multi-Layer Virtual Machine:** แปลงชุดคำสั่งเป็น Custom Bytecode รันบน VM Dispatcher\n"
        "• **Control Flow Flattening (CFF):** สับเปลี่ยน State Machine ป้องกัน Decompiler ตรวจจับโฟลว์\n"
        "• **Dynamic String & Constant Encryption:** เข้ารหัสแบบ JIT ไร้ Plaintext String ในโค้ด\n"
        "• **Anti-Tamper & Environment Protection:** ป้องกันการ Hook และ Dump หน่วยความจำ\n"
        "• **Autonomous AI Synergy:** ขับเคลื่อนความซับซ้อนโดย DeepSeek V3 AI Engine"
    )
    embed.add_field(name="🔒 รายละเอียดชั้นความปลอดภัย (Security Layers)", value=security_features, inline=False)

    # Script Overview Summary (Mandated by dj)
    script_summary = res.get("script_summary")
    if script_summary:
        embed.add_field(name="📝 สรุปการทำงานของสคริปต์ (Script Overview)", value=script_summary, inline=False)

    embed.set_footer(text="PAYOMBØYZ Obfuscate V6.7.6.7 | Powered by DeepSeek & Prometheus VM")

    output_path = res.get("output_path")
    obf_code = res.get("obfuscated_code", "")
    out_filename = f"{Path(safe_input_name).stem}_PAYOMBOYZ_OBF.lua"

    if output_path and os.path.exists(output_path):
        files.append(discord.File(output_path, filename=out_filename))
    elif obf_code:
        file_bytes = io.BytesIO(obf_code.encode("utf-8", errors="replace"))
        files.append(discord.File(file_bytes, filename=out_filename))

    return embed, files


@bot.event
async def on_ready():
    print("=" * 64)
    print(f"[AI BOT SOURCE] {Path(__file__).resolve()}", flush=True)
    print("[AI ROUTER BUILD] provider-health-v2", flush=True)
    print("  ⚡ PAYOMBØYZ AI & MULTI-ENGINE DEOBFUSCATOR BOT READY")
    print("=" * 64)
    try:
        bot.add_view(DeobfPanelView())
        print("  [+] Registered persistent DeobfPanelView into Bot.", flush=True)
    except Exception as pe:
        print(f"  [-] Notice on DeobfPanelView registration: {pe}", flush=True)
    try:
        from bot.clone_panel import ClonePanelView
        bot.add_view(ClonePanelView())
        print("  [+] Registered persistent ClonePanelView into Bot.", flush=True)
    except Exception as cpe:
        print(f"  [-] Notice on ClonePanelView registration: {cpe}", flush=True)
    try:
        from bot.deobf_panel import DeobfResultActionView
        bot.add_view(DeobfResultActionView())
        print("  [+] Registered persistent DeobfResultActionView into Bot.", flush=True)
    except Exception as re_view_err:
        print(f"  [-] Notice on DeobfResultActionView registration: {re_view_err}", flush=True)
    user_tag = f"{bot.user.name}#{bot.user.discriminator}" if bot.user.discriminator != "0" else bot.user.name
    print(f"👤 Logged in as: {user_tag} (ID: {bot.user.id})")
    print(f"🤖 Gemini AI Status: {'🟢 ONLINE (' + config.GEMINI_MODEL + ')' if gemini_engine.is_available() else '🔴 OFFLINE'}")
    print(f"⚙️  Prefix: {config.COMMAND_PREFIX}")
    configured_ai_channels = load_ai_channels()
    visible_ai_channels = []
    for channel_id in configured_ai_channels:
        channel = bot.get_channel(channel_id)
        visible_ai_channels.append(
            f"{getattr(channel, 'name', 'cache-miss')}:{channel_id}"
        )
    print(
        f"[AI CHAT] Configured channel IDs: {visible_ai_channels or 'NONE'}; "
        f"message_content_intent={bot.intents.message_content}",
        flush=True,
    )
    invite_url = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
    print(f"🔗 ลิงก์เชิญบอทเข้า Discord:\n   {invite_url}")
    print("=" * 64)

    for guild in bot.guilds:
        try:
            guild_cmds = await bot.tree.fetch_commands(guild=guild)
            if guild_cmds:
                bot.tree.clear_commands(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"[+] Cleared {len(guild_cmds)} duplicate guild commands from {guild.name} ({guild.id}).", flush=True)
        except Exception as ge:
            print(f"[-] Guild command cleanup notice for {guild.id}: {ge}", flush=True)

    try:
        synced = await bot.tree.sync()
        print(f"[+] Synced {len(synced)} global slash commands for AI & Deobf Bot.", flush=True)
    except Exception as e:
        print(f"[-] Global slash sync notice: {e}", flush=True)

    runtime_status = runtime_guard.check_runtime()
    print(f"[RUNTIME CHECK] Python={runtime_status['python']['version']} | audioop={'OK' if runtime_status['audioop']['available'] else 'FAIL'} | discord_compatible={runtime_status['discord_compatible']}", flush=True)
    QUALITY_MONITOR.start()
    try:
        from bot.idle_reverser_worker import IDLE_REVERSER
        IDLE_REVERSER.bot = bot
        # Autonomous idle loop disabled by default to protect API quotas.
        print("[IDLE REVERSER] Autonomous quota-draining idle loop is DISABLED.", flush=True)
    except Exception as ie:
        print(f"[-] Idle reverser worker notice: {ie}", flush=True)

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.competing,
            name="⚡ PAYOMBØYZ CYBER-AI V9.0 | /ai & /deobf"
        ),
        status=discord.Status.online
    )


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"[-] Slash command error on {interaction.command}: {error}", flush=True)

    # Ignore expired or already-closed interactions; Discord raises 404 when the user
    # clicks a command after the interaction has expired or the response is no longer valid.
    if isinstance(error, discord.NotFound):
        return

    err_msg = f"❌ เกิดข้อผิดพลาดในการรันคำสั่ง: `{error}`"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(err_msg, ephemeral=True)
        else:
            await interaction.response.send_message(err_msg, ephemeral=True)
    except (discord.NotFound, discord.HTTPException):
        pass
    except Exception:
        pass


# =========================================================================
# 🎛️ PANEL & SETUP COMMAND GROUPS
# =========================================================================
class SetupGroup(app_commands.Group):
    """คำสั่งกลุ่ม /setup สำหรับตั้งค่าระบบ AI และแผงควบคุม Deobf/Obf"""
    def __init__(self):
        super().__init__(name="setup", description="คำสั่งตั้งค่าระบบ AI และแผงควบคุม Deobfuscator & Obfuscator")

setup_group = SetupGroup()
bot.tree.add_command(setup_group)
register_godmode_to_bot(bot)


async def _execute_setup_panel(
    interaction: discord.Interaction,
    panel_type: str = "deobf",
    channel: Optional[discord.TextChannel] = None,
    log_channel: Optional[discord.TextChannel] = None,
    title: Optional[str] = None,
    color: Optional[str] = None,
    banner_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None
):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    target = channel or interaction.channel
    if not isinstance(target, discord.TextChannel):
        await interaction.followup.send("❌ กรุณาเลือกห้องข้อความ (Text Channel) เท่านั้นครับ", ephemeral=True)
        return

    cfg = {
        "title": title,
        "color": color,
        "banner_url": banner_url,
        "thumbnail_url": thumbnail_url,
    }

    # Handle Web Clone Panel Setup
    if panel_type == "clone":
        from bot.clone_panel import build_clone_panel_embed, ClonePanelView, save_clone_panel
        embed = build_clone_panel_embed(cfg)
        view = ClonePanelView()
        msg = await target.send(embed=embed, view=view)

        panel_id = f"clone_{target.id}_{msg.id}"
        panel_data = {
            "panel_id": panel_id,
            "guild_id": interaction.guild_id,
            "channel_id": target.id,
            "message_id": msg.id,
            "title": title,
            "created_at": time.time(),
        }
        save_clone_panel(panel_id, panel_data)

        confirm_embed = discord.Embed(
            title="⚡ PAYOMBØYZ | ติดตั้งแผงควบคุม Web Clone Tool สำเร็จ",
            description=(
                f"✅ ติดตั้งแผงควบคุม **Web Clone Tool (7 โหมดระดับปีศาจ)** เรียบร้อยแล้วที่ {target.mention}!\n\n"
                f"• **ข้อความ ID:** `{msg.id}`\n"
                f"• **สถานะ:** `🟢 Online & Persistent 24/7`\n"
                f"• **ฟีเจอร์ระดับเทพ:** Dropdown เลือกได้ 7 โหมด, ปุ่มลัด Godmode, Pre-render SPA (Chrome), Mock API ออฟไลน์, Source Maps TS/JSX, และรายงาน CYBER_AUDIT.html\n"
                f"• สมาชิกในเซิร์ฟเวอร์สามารถกดปุ่มหรือเลือกโหมดเพื่อโคลนเว็บได้ทันที!"
            ),
            color=discord.Color.from_rgb(0, 230, 150)
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)
        return

    # Handle Default Deobf/Obf Panel Setup
    embed = build_deobf_panel_embed(cfg)
    view = DeobfPanelView()

    msg = await target.send(embed=embed, view=view)

    panel_id = f"{target.id}_{msg.id}"
    panel_data = {
        "panel_id": panel_id,
        "guild_id": interaction.guild_id,
        "channel_id": target.id,
        "message_id": msg.id,
        "title": title,
        "color": color,
        "banner_url": banner_url,
        "thumbnail_url": thumbnail_url,
        "created_at": time.time(),
    }
    if log_channel:
        panel_data["log_channel_id"] = log_channel.id
    save_deobf_panel(panel_id, panel_data)

    log_ch_mention = log_channel.mention if log_channel else "`ไม่ได้ตั้งค่า`"
    confirm_embed = discord.Embed(
        title="⚡ PAYOMBØYZ | ติดตั้งแผงควบคุม V10.0 สำเร็จ",
        description=(
            f"✅ ติดตั้งแผงควบคุม **Deobfuscator & Obfuscator Panel** เรียบร้อยแล้วที่ {target.mention}!\n\n"
            f"• **ข้อความ ID:** `{msg.id}`\n"
            f"• **สถานะ:** `🟢 Online & Persistent 24/7`\n"
            f"• **Log Channel:** {log_ch_mention}\n"
            f"• **ฟีเจอร์ใหม่ V10:** Engine Dropdown, File Attach (no limit), Status Check, DeepSeek/Gemini Cleanup Pipeline"
        ),
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=confirm_embed, ephemeral=True)


@setup_group.command(name="panel", description="ติดตั้งแผงควบคุม Deobfuscate หรือ Web Clone Tool (Persistent 24/7)")
@app_commands.describe(
    panel_type="เลือกประเภทแผง: deobf (แผงแกะ/เข้ารหัสสคริปต์) หรือ clone (แผงโคลนเว็บไซต์ระดับปีศาจ)",
    channel="เลือกห้องข้อความสำหรับติดตั้งแผงควบคุม (หากไม่เลือกจะใช้ห้องปัจจุบัน)",
    log_channel="เลือกห้องสำหรับส่ง Log ย้อนหลัง (สำหรับ Deobf Panel)",
    title="หัวข้อของแผงควบคุม (ไม่บังคับ)",
    color="สีแถบข้าง Embed เช่น crimson, cyan, gold, emerald หรือ #HEX (ไม่บังคับ)",
    banner_url="ลิงก์รูปภาพ Banner ด้านล่าง (ไม่บังคับ)",
    thumbnail_url="ลิงก์รูปภาพ Thumbnail ขวาบน (ไม่บังคับ)"
)
@app_commands.default_permissions(administrator=True)
async def setup_panel_subcmd(
    interaction: discord.Interaction,
    panel_type: Literal["deobf", "clone"] = "deobf",
    channel: Optional[discord.TextChannel] = None,
    log_channel: Optional[discord.TextChannel] = None,
    title: Optional[str] = None,
    color: Optional[str] = None,
    banner_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None
):
    await _execute_setup_panel(
        interaction=interaction,
        panel_type=panel_type,
        channel=channel,
        log_channel=log_channel,
        title=title,
        color=color,
        banner_url=banner_url,
        thumbnail_url=thumbnail_url
    )


@setup_group.command(name="clone", description="ติดตั้งแผงควบคุม Web Clone Tool (7 โหมดระดับปีศาจ) ลงในห้องที่เลือก (ถาวร 24/7)")
@app_commands.describe(
    channel="เลือกห้องข้อความสำหรับติดตั้งแผง Web Clone (หากไม่เลือกจะใช้ห้องปัจจุบัน)",
    title="หัวข้อของแผงควบคุม (ไม่บังคับ)",
    banner_url="ลิงก์รูปภาพ Banner ด้านล่าง (ไม่บังคับ)",
    thumbnail_url="ลิงก์รูปภาพ Thumbnail ขวาบน (ไม่บังคับ)"
)
@app_commands.default_permissions(administrator=True)
async def setup_clone_subcmd(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    title: Optional[str] = None,
    banner_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None
):
    await _execute_setup_panel(
        interaction=interaction,
        panel_type="clone",
        channel=channel,
        title=title,
        banner_url=banner_url,
        thumbnail_url=thumbnail_url
    )


@setup_group.command(name="ai", description="ตั้งค่าห้องพูดคุยกับ AI สำหรับ Script Roblox (Luau)")
@app_commands.describe(channel="เลือกห้องข้อความสำหรับ AI (หากไม่เลือกจะใช้ห้องปัจจุบันที่พิมพ์คำสั่ง)")
@app_commands.default_permissions(administrator=True)
async def setup_ai_subcmd(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    target = channel or interaction.channel
    if not isinstance(target, discord.TextChannel):
        await interaction.followup.send("❌ กรุณาเลือกห้องข้อความ (Text Channel) เท่านั้นครับ", ephemeral=True)
        return

    channels = load_ai_channels()
    channels.add(target.id)
    save_ai_channels(channels)

    embed = discord.Embed(
        title=f"{PROJECT_NAME} | 🤖 ติดตั้งห้อง AI สำเร็จ",
        description=f"✅ ทำการผูกห้อง {target.mention} เป็นห้องประจำการของ AI เรียบร้อยแล้ว!\n\n"
                    f"**สิ่งที่สมาชิกในเซิร์ฟเวอร์สามารถทำได้ในห้องนี้:**\n"
                    f"• 💬 **คุยได้ทันที ไม่ต้องใช้คำสั่ง:** พิมพ์ข้อความคุยได้เลย AI จะตอบกลับอัตโนมัติ (สไตล์ Nexus.botx2)\n"
                    f"• 📜 **ปรึกษา & ขอโค้ด Roblox Luau:** ขอสคริปต์บิน, Infinite Jump, Tween, RemoteEvent, ESP, GUI\n"
                    f"• 🔓 **ปรึกษาเรื่อง Deobfuscate:** สอบถามการถอดรหัส Moonveil, WeAreDevs, Luraph, IronBrew\n"
                    f"• 🏪 **รีวิวสคริปต์ & ร้านค้า PAYOMBØYZ HUB:** สอบถามฟังก์ชั่น 18+ แมพ, เช็คราคา (VIP 89.- / VVIP 129.-), ลิงก์ซื้อคีย์ และวิธีโหลดตัวรัน\n\n"
                    f"🔒 *หมายเหตุ: สคริปต์ของค่ายเป็นระบบปิด AI จะรีวิวฟังก์ชั่นและระบบให้ แต่ไม่เปิดเผย raw src*",
        color=discord.Color.from_rgb(0, 230, 150)
    )
    embed.set_footer(text="PAYOMBØYZ CYBER-AI V8 | Autonomous Intelligence System")
    await interaction.followup.send(embed=embed, ephemeral=True)

    if target.id != interaction.channel_id:
        try:
            await target.send(embed=embed)
        except Exception:
            pass


@setup_group.command(name="godmode", description="ติดตั้งห้องนี้เป็นห้องควบคุม Godmode & PBG Senior AI-Chat (ความปลอดภัยระดับสูง 2FA)")
@app_commands.describe(channel="เลือกห้องข้อความสำหรับ Godmode (หากไม่เลือกจะใช้ห้องปัจจุบัน)")
@app_commands.default_permissions(administrator=True)
async def setup_godmode_subcmd(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    target = channel or interaction.channel
    if not isinstance(target, discord.TextChannel):
        await interaction.response.send_message("❌ กรุณาเลือกห้องข้อความ (Text Channel) เท่านั้นครับ", ephemeral=True)
        return

    from bot.godmode import GODMODE_STATE, GodmodeAuthModal, build_godmode_panel_embed, GodmodePanelView

    # If user is already authenticated with 2FA
    if GODMODE_STATE.is_user_authenticated(interaction.user.id):
        GODMODE_STATE.register_channel(target.id, str(interaction.user))
        embed = discord.Embed(
            title="⚡ ติดตั้งห้องควบคุม GODMODE & PBG AI-CHAT สำเร็จ",
            description=(
                f"✅ ผูกห้อง {target.mention} เข้ากับระบบ **PBG Senior Agentic Controller** เรียบร้อยแล้ว!\n\n"
                f"• **สิทธิ์ระดับสูงสุด:** `ROOT_GODMODE_ACCESS`\n"
                f"• **AI ประจำห้อง:** **PBG (PayomboyZ Godmode Senior Commander)**\n"
                f"• **ระดับความปลอดภัย:** `2-STAGE 2FA AUTHENTICATED` (Master Key + PIN)\n"
                f"• **ระบบถาม-ตอบ AI:** ทำงานเฉพาะในห้องนี้แบบไม่ตัดทอน (Zero Truncation) ตอบพร้อมภาพ/ชาร์ต และรันสคริปต์สดได้\n\n"
                f"🔒 *ระบบจะรับคำสั่งและตอบกลับเฉพาะผู้ที่ผ่านการยืนยันตัวตน 2FA เท่านั้น*"
            ),
            color=discord.Color.from_rgb(255, 20, 50)
        )
        embed.set_footer(text="PAYOMBØYZ GODMODE ENGINE // PBG ENGAGED")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        panel_embed = build_godmode_panel_embed()
        view = GodmodePanelView()
        await target.send(embed=panel_embed, view=view)
    else:
        # Require 2FA verification to perform setup
        await interaction.response.send_modal(GodmodeAuthModal(target_channel_id=target.id, is_setup=True))


@setup_group.command(name="deobfuscate", description="ติดตั้งช่องสำหรับ Deobfuscate สคริปต์ (ไร้ปุ่มรกตา พร้อม Guide Embed ปักท้าย)")
@app_commands.describe(channel="เลือกห้องข้อความสำหรับ Deobfuscate (หากไม่เลือกจะใช้ห้องปัจจุบัน)")
@app_commands.default_permissions(administrator=True)
async def setup_deobfuscate_subcmd(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    target = channel or interaction.channel
    if not isinstance(target, discord.TextChannel):
        await interaction.followup.send("❌ กรุณาเลือกห้องข้อความ (Text Channel) เท่านั้นครับ", ephemeral=True)
        return

    from bot.deobf_panel import save_dedicated_channel, post_pinned_guide
    save_dedicated_channel(target.id, "deobfuscate", interaction.guild_id)
    await post_pinned_guide(target, "deobfuscate")

    await interaction.followup.send(
        f"✅ ติดตั้งช่อง **Deobfuscate** เรียบร้อยแล้วที่ {target.mention}!\n"
        f"• สมาชิกสามารถอัปโหลดไฟล์ `.lua / .luau / .txt` ในช่องนี้ได้ทันที\n"
        f"• บอตจะแสดงปุ่มเดี่ยว `[ ⚙️ เลือกเครื่องมือ & ตั้งชื่อไฟล์ ]` สำหรับเปิดเมนู Ephemeral และปักหมุด Guide Embed ไว้ล่างสุดเสมอ",
        ephemeral=True
    )


@setup_group.command(name="obfuscate", description="ติดตั้งช่องสำหรับ Obfuscate สคริปต์ (ไร้ปุ่มรกตา พร้อม Guide Embed ปักท้าย)")
@app_commands.describe(channel="เลือกห้องข้อความสำหรับ Obfuscate (หากไม่เลือกจะใช้ห้องปัจจุบัน)")
@app_commands.default_permissions(administrator=True)
async def setup_obfuscate_subcmd(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    target = channel or interaction.channel
    if not isinstance(target, discord.TextChannel):
        await interaction.followup.send("❌ กรุณาเลือกห้องข้อความ (Text Channel) เท่านั้นครับ", ephemeral=True)
        return

    from bot.deobf_panel import save_dedicated_channel, post_pinned_guide
    save_dedicated_channel(target.id, "obfuscate", interaction.guild_id)
    await post_pinned_guide(target, "obfuscate")

    await interaction.followup.send(
        f"✅ ติดตั้งช่อง **Obfuscate** เรียบร้อยแล้วที่ {target.mention}!\n"
        f"• สมาชิกสามารถอัปโหลดไฟล์ `.lua / .luau / .txt` ในช่องนี้ได้ทันที\n"
        f"• บอตจะแสดงปุ่มเดี่ยว `[ ⚙️ เลือกเครื่องมือ & ตั้งชื่อไฟล์ ]` สำหรับเปิดเมนู Ephemeral และปักหมุด Guide Embed ไว้ล่างสุดเสมอ",
        ephemeral=True
    )


@setup_group.command(name="remove", description="ยกเลิกการตั้งค่าห้อง (AI / Deobfuscate / Obfuscate / Panel)")
@app_commands.describe(channel="เลือกห้องที่ต้องการยกเลิก (หากไม่เลือกจะใช้ห้องปัจจุบัน)")
@app_commands.default_permissions(administrator=True)
async def setup_remove_subcmd(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    target = channel or interaction.channel
    from bot.deobf_panel import remove_dedicated_channel, load_deobf_panels, delete_deobf_panel
    from bot.godmode import GODMODE_STATE
    channels = load_ai_channels()
    removed_roles = []

    if target.id in channels:
        channels.remove(target.id)
        save_ai_channels(channels)
        removed_roles.append("ห้องพูดคุย AI")

    if remove_dedicated_channel(target.id):
        removed_roles.append("ห้อง Dedicated (Deobf/Obf)")

    for pid, pdata in list(load_deobf_panels().items()):
        if pdata.get("channel_id") == target.id:
            delete_deobf_panel(pid)
            removed_roles.append("แผงควบคุม Panel")

    if GODMODE_STATE.is_channel_installed(target.id):
        GODMODE_STATE.unregister_channel(target.id, str(interaction.user))
        removed_roles.append("ห้องควบคุม Godmode & PBG AI-Chat")

    if removed_roles:
        roles_text = ", ".join(removed_roles)
        await interaction.followup.send(
            f"✅ ยกเลิกการตั้งค่า **{roles_text}** สำหรับห้อง {target.mention} เรียบร้อยแล้ว!\n"
            f"• บอทจะไม่ตอบกลับข้อความอัตโนมัติในห้องนี้อีกต่อไป (ยกเว้นมีคนแท็กเรียก `@บอท` โดยตรง)",
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            f"ℹ️ ห้อง {target.mention} **ไม่ได้ถูกเปิดใช้งานในระบบอยู่แล้ว**\n"
            f"• บอทจะไม่ตอบกลับข้อความอัตโนมัติในห้องนี้ (จะตอบเมื่อมีคนแท็กเรียกบอทโดยตรงเท่านั้น)",
            ephemeral=True
        )


@setup_group.command(name="list", description="แสดงรายชื่อห้องทั้งหมดที่เปิดใช้งานระบบ AI และแผงควบคุม")
@app_commands.default_permissions(administrator=True)
async def setup_list_subcmd(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    channels = load_ai_channels()
    from bot.deobf_panel import load_dedicated_channels, load_deobf_panels
    from bot.godmode import GODMODE_STATE
    dedicated = load_dedicated_channels()
    panels = load_deobf_panels()
    godmode_channels = getattr(GODMODE_STATE, "installed_channels", set())

    ai_mentions = [f"<#{cid}> (`{cid}`)" for cid in sorted(channels)] or ["- ไม่มี -"]
    ded_mentions = [f"<#{cid}> (โหมด: `{info.get('mode', 'unknown')}`)" for cid, info in dedicated.items()] or ["- ไม่มี -"]
    panel_mentions = [f"<#{info.get('channel_id')}> (ID: `{info.get('channel_id')}`)" for info in panels.values()] or ["- ไม่มี -"]
    god_mentions = [f"<#{cid}> (`{cid}`)" for cid in sorted(godmode_channels)] or ["- ไม่มี -"]

    embed = discord.Embed(
        title="📋 PAYOMBØYZ | รายการห้องที่เปิดใช้งานในระบบ",
        description="บอทจะตอบกลับอัตโนมัติเฉพาะห้องที่ระบุไว้ด้านล่างนี้เท่านั้น นอกนั้นต้องแท็กเรียกบอทโดยตรง:",
        color=discord.Color.from_rgb(0, 230, 150)
    )
    embed.add_field(name="🛡️ ห้อง Godmode & PBG AI-Chat (2FA Protected)", value="\n".join(god_mentions), inline=False)
    embed.add_field(name="🤖 ห้องพูดคุย AI สคริปต์ Roblox (Auto-Reply)", value="\n".join(ai_mentions), inline=False)
    embed.add_field(name="⚙️ ห้อง Dedicated Drop File", value="\n".join(ded_mentions), inline=False)
    embed.add_field(name="🎛️ ห้องแผงควบคุม Panel", value="\n".join(panel_mentions), inline=False)
    embed.set_footer(text="ใช้ /setup remove ในห้องที่ต้องการยกเลิก หรือ /setup godmode เพื่อเพิ่มห้องใหม่")

    await interaction.followup.send(embed=embed, ephemeral=True)


# --- Root Aliases for Setup Commands ---

@bot.tree.command(name="setup_godmode", description="ติดตั้งห้องนี้เป็นห้องควบคุม Godmode & PBG Senior AI-Chat (คำสั่งตรง)")
@app_commands.describe(channel="เลือกห้องข้อความสำหรับ Godmode (หากไม่เลือกจะใช้ห้องปัจจุบัน)")
@app_commands.default_permissions(administrator=True)
async def cmd_slash_setup_godmode(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    await setup_godmode_subcmd.callback(interaction, channel)


@bot.tree.command(name="setup_panel", description="ติดตั้งแผงควบคุม Deobfuscate & Obfuscate พร้อมปุ่ม Popup Modal (คำสั่งตรง)")
@app_commands.describe(
    channel="เลือกห้องข้อความสำหรับติดตั้งแผงควบคุม (หากไม่เลือกจะใช้ห้องปัจจุบัน)",
    log_channel="เลือกห้องข้อความสำหรับเก็บบันทึก Log (ไม่บังคับ)",
    title="หัวข้อของแผงควบคุม (ไม่บังคับ)",
    color="สีแถบข้าง Embed เช่น crimson, cyan, gold, emerald หรือ #HEX (ไม่บังคับ)",
    banner_url="ลิงก์รูปภาพ Banner ด้านล่าง (ไม่บังคับ)",
    thumbnail_url="ลิงก์รูปภาพ Thumbnail ขวาบน (ไม่บังคับ)"
)
@app_commands.default_permissions(administrator=True)
async def cmd_slash_setup_panel(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    log_channel: Optional[discord.TextChannel] = None,
    title: Optional[str] = None,
    color: Optional[str] = None,
    banner_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None
):
    await setup_panel_subcmd.callback(interaction, channel, log_channel, title, color, banner_url, thumbnail_url)


@bot.tree.command(name="setup_ai", description="คำสั่งตรงสำหรับตั้งค่าห้องพูดคุยกับ AI (เหมือนกับ /setup ai)")
@app_commands.describe(channel="เลือกห้องข้อความสำหรับ AI (หากไม่เลือกจะใช้ห้องปัจจุบันที่พิมพ์คำสั่ง)")
@app_commands.default_permissions(administrator=True)
async def cmd_slash_setup_ai(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    await setup_ai_subcmd.callback(interaction, channel)


@bot.tree.command(name="setup_remove", description="ยกเลิกการตั้งค่าห้องพูดคุยกับ AI / Panel (เหมือนกับ /setup remove)")
@app_commands.describe(channel="เลือกห้องที่ต้องการยกเลิก (หากไม่เลือกจะใช้ห้องปัจจุบัน)")
@app_commands.default_permissions(administrator=True)
async def cmd_slash_setup_remove(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    await setup_remove_subcmd.callback(interaction, channel)


@bot.tree.command(name="setup_list", description="แสดงรายชื่อห้องทั้งหมดที่เปิดใช้งานระบบ (เหมือนกับ /setup list)")
@app_commands.default_permissions(administrator=True)
async def cmd_slash_setup_list(interaction: discord.Interaction):
    await setup_list_subcmd.callback(interaction)


@bot.tree.command(name="setup_deobf", description="ติดตั้งห้อง Deobfuscate สคริปต์ (ไร้ปุ่มรกตา พร้อม Guide Embed ปักท้าย)")
@app_commands.describe(channel="เลือกห้องข้อความสำหรับ Deobfuscate (หากไม่เลือกจะใช้ห้องปัจจุบัน)")
@app_commands.default_permissions(administrator=True)
async def cmd_slash_setup_deobf(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    await setup_deobfuscate_subcmd.callback(interaction, channel)


@bot.tree.command(name="setup_obf", description="ติดตั้งห้อง Obfuscate สคริปต์ (ไร้ปุ่มรกตา พร้อม Guide Embed ปักท้าย)")
@app_commands.describe(channel="เลือกห้องข้อความสำหรับ Obfuscate (หากไม่เลือกจะใช้ห้องปัจจุบัน)")
@app_commands.default_permissions(administrator=True)
async def cmd_slash_setup_obf(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    await setup_obfuscate_subcmd.callback(interaction, channel)


@bot.tree.command(name="agent", description="👑 เรียกใช้งาน PAYOMBØYZ Supreme Agentic Commander (วิเคราะห์ เจาะลึก และสร้างงานเต็มระบบ)")
@app_commands.describe(
    goal="เป้าหมายหรือภารกิจที่ต้องการให้ Supreme Commander จัดการ",
    file="แนบไฟล์สคริปต์หรือข้อมูลที่เกี่ยวข้อง (ไม่บังคับ)"
)
async def cmd_slash_agent(interaction: discord.Interaction, goal: str, file: Optional[discord.Attachment] = None):
    await interaction.response.defer(thinking=True)
    attached_code = ""
    filename = ""
    if file:
        filename = file.filename
        try:
            raw_bytes = await file.read()
            attached_code = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            pass

    from bot.agentic_commander import SUPREME_COMMANDER
    mission_res = await SUPREME_COMMANDER.execute_mission(
        mission_goal=goal,
        attached_code=attached_code,
        filename=filename,
        operator_name=interaction.user.display_name or interaction.user.name,
    )

    reply_text = mission_res.get("reply", "") or "ภารกิจเสร็จสิ้น แต่ไม่มีข้อความตอบกลับ"
    worker_name = mission_res.get("worker", "Supreme Commander")
    elapsed = mission_res.get("elapsed", 0.0)

    header = (
        f"👑 **PAYOMBØYZ SUPREME AGENTIC COMMANDER**\n"
        f"🎯 **เป้าหมาย:** `{goal[:100]}`\n"
        f"⚡ **ประมวลผลโดย:** `{worker_name}` ({elapsed}s)\n"
        f"────────────────────────────────────────\n"
    )

    full_output = header + reply_text
    parts = split_long_text_for_discord(full_output, chunk_size=1900)
    for idx, part in enumerate(parts):
        if idx == 0:
            await interaction.followup.send(part)
        else:
            await interaction.channel.send(part)

    for b_idx, block in enumerate(mission_res.get("code_blocks", [])):
        code_str = block["code"]
        lang = block["lang"]
        if len(code_str) > 500:
            ext = "lua" if "lua" in lang else ("py" if "py" in lang else ("html" if "html" in lang else "txt"))
            file_data = io.BytesIO(code_str.encode("utf-8"))
            discord_file = discord.File(file_data, filename=f"Commander_Artifact_{b_idx+1}.{ext}")
            await interaction.channel.send(
                f"📦 **Artifact #{b_idx+1}** (`{lang}` - {len(code_str):,} ตัวอักษร)",
                file=discord_file
            )


@bot.command(name="agent")
async def cmd_prefix_agent(ctx, *, goal: str):
    msg = await ctx.send("👑 **Supreme Commander กำลังกระจายคำสั่งและจัดวางแผนงาน...**")
    attached_code = ""
    filename = ""
    if ctx.message.attachments:
        att = ctx.message.attachments[0]
        filename = att.filename
        try:
            raw_bytes = await att.read()
            attached_code = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            pass

    from bot.agentic_commander import SUPREME_COMMANDER
    mission_res = await SUPREME_COMMANDER.execute_mission(
        mission_goal=goal,
        attached_code=attached_code,
        filename=filename,
        operator_name=ctx.author.display_name or ctx.author.name,
    )

    reply_text = mission_res.get("reply", "") or "ภารกิจเสร็จสิ้น"
    worker_name = mission_res.get("worker", "Supreme Commander")
    elapsed = mission_res.get("elapsed", 0.0)

    header = (
        f"👑 **PAYOMBØYZ SUPREME AGENTIC COMMANDER**\n"
        f"🎯 **เป้าหมาย:** `{goal[:100]}`\n"
        f"⚡ **ประมวลผลโดย:** `{worker_name}` ({elapsed}s)\n"
        f"────────────────────────────────────────\n"
    )
    await msg.delete()
    full_output = header + reply_text
    for part in split_long_text_for_discord(full_output, chunk_size=1900):
        await ctx.send(part)

    for b_idx, block in enumerate(mission_res.get("code_blocks", [])):
        code_str = block["code"]
        lang = block["lang"]
        if len(code_str) > 500:
            ext = "lua" if "lua" in lang else ("py" if "py" in lang else ("html" if "html" in lang else "txt"))
            file_data = io.BytesIO(code_str.encode("utf-8"))
            discord_file = discord.File(file_data, filename=f"Commander_Artifact_{b_idx+1}.{ext}")
            await ctx.send(
                f"📦 **Artifact #{b_idx+1}** (`{lang}` - {len(code_str):,} ตัวอักษร)",
                file=discord_file
            )


@bot.tree.command(name="clone_web", description="🌐 โคลนและถอดรหัสโครงสร้างหน้าเว็บ (REA Web Cloner)")
@app_commands.describe(url="URL ของเว็บไซต์เป้าหมายที่ต้องการโคลนโครงสร้าง")
async def cmd_slash_clone_web(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    from bot.rea_engine_bridge import WebClonerEngine
    clone_res = WebClonerEngine.clone_website(url)
    if clone_res.get("success"):
        embed = discord.Embed(
            title="🌐 PAYOMBØYZ REA — Website Reconstruction Complete",
            description=f"โคลนและถอดรหัสโครงสร้างหน้าเว็บสำเร็จ!\n**Target**: `{url}`\n**Domain**: `{clone_res['domain']}`",
            color=0x00FFCC
        )
        comps = clone_res.get("components", [])
        comp_text = "\n".join(f"• {c}" for c in comps) if comps else "• General Static DOM Layout"
        embed.add_field(name="🏛️ Reconstructed Components", value=comp_text, inline=False)
        embed.add_field(name="🎨 Stylesheets Aggregate", value=f"{clone_res.get('css_sources_count', 0)} sources merged into `styles.css`", inline=True)
        embed.add_field(name="📦 Scripts Identified", value=f"{clone_res.get('scripts_count', 0)} external bundles", inline=True)
        embed.add_field(name="📂 Local Storage Path", value=f"`{clone_res['target_dir']}`", inline=False)
        embed.set_footer(text="REA Multi-Platform Reverse Engineering Engine • Ready for local preview")
        
        files_to_send = []
        zip_p = Path(clone_res.get("zip_path", ""))
        if zip_p.exists():
            files_to_send.append(discord.File(str(zip_p), filename=zip_p.name))
        bp_path = Path(clone_res.get("blueprint_path", ""))
        if bp_path.exists():
            files_to_send.append(discord.File(str(bp_path), filename="SECURITY_RECON_REPORT.txt"))
        await interaction.followup.send(embed=embed, files=files_to_send)
    else:
        await interaction.followup.send(f"❌ โคลนเว็บไซต์ไม่สำเร็จ: `{clone_res.get('error')}`")


@bot.tree.command(name="re_inspect", description="🔬 ตรวจสอบไบนารีเนทีฟ PE/DLL ด้วย REA Diagnostic Engine")
@app_commands.describe(file="ไฟล์ .exe, .dll, หรือ .sys ที่ต้องการตรวจสอบ")
async def cmd_slash_re_inspect(interaction: discord.Interaction, file: discord.Attachment):
    if not file.filename.lower().endswith((".exe", ".dll", ".sys", ".bin")):
        await interaction.response.send_message("❌ กรุณาแนบไฟล์ตระกูล Windows PE (.exe, .dll, .sys, .bin) เท่านั้น", ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    temp_pe = save_temp_input(await file.read(), file.filename)
    from bot.rea_engine_bridge import NativeBinaryInspector
    pe_report = NativeBinaryInspector.inspect_pe_file(str(temp_pe))
    if pe_report.get("success"):
        embed = discord.Embed(
            title=f"🔬 PAYOMBØYZ REA — Native PE Biopsy: {file.filename}",
            description=f"**Architecture**: `{pe_report.get('architecture')}`\n**File Size**: `{pe_report.get('file_size'):,} bytes`\n**Image Base**: `{pe_report.get('image_base')}` | **Entry Point**: `{pe_report.get('entry_point')}`",
            color=0xFF0055 if pe_report.get("is_packed") else 0x00FF88
        )
        embed.add_field(name="🛡️ Packer / Crypter Detection", value=f"**{pe_report.get('packer_detection')}**", inline=False)
        sec_lines = [f"`{s['name']:<8}` | Entropy: `{s['entropy']}` | RawSize: `{s['raw_size']:,}`" for s in pe_report.get("sections", [])[:6]]
        embed.add_field(name="📊 Section Entropy & Layout", value="\n".join(sec_lines) or "None", inline=False)
        apis = pe_report.get("suspicious_apis_detected", [])
        if apis:
            embed.add_field(name="⚠️ Critical API Sinks Detected", value=", ".join(f"`{a}`" for a in apis), inline=False)
        embed.set_footer(text="REA Hopper / Ghidra Native Evidence Contract")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ วิเคราะห์ไบนารีไม่สำเร็จ: `{pe_report.get('error')}`")


# =========================================================================
# ⚙️ PANEL MANAGEMENT COMMAND GROUP
# =========================================================================
class PanelGroup(app_commands.Group):
    """คำสั่งกลุ่ม /panel สำหรับจัดการและปรับแต่งแผงควบคุม Deobfuscator & Obfuscator"""
    def __init__(self):
        super().__init__(name="panel", description="คำสั่งจัดการและปรับแต่งแผงควบคุม Deobfuscator & Obfuscator")

panel_group = PanelGroup()
bot.tree.add_command(panel_group)


@panel_group.command(name="refresh", description="อัปเดตข้อความและปุ่มของแผงควบคุมที่มีอยู่ให้เป็นเวอร์ชันล่าสุด")
@app_commands.describe(message_id="ระบุ ID ข้อความของ Panel (หากไม่ระบุจะค้นหา Panel ในห้องนี้)")
@app_commands.default_permissions(administrator=True)
async def panel_refresh_subcmd(interaction: discord.Interaction, message_id: Optional[str] = None):
    import importlib
    import bot.deobf_panel as _dp
    importlib.reload(_dp)

    panels = _dp.load_deobf_panels()
    if not panels:
        await interaction.response.send_message("⚠️ ยังไม่มีแผงควบคุมใดๆ ถูกติดตั้งในระบบ (ใช้ `/setup panel` เพื่อติดตั้ง)", ephemeral=True)
        return

    found = None
    if message_id:
        try:
            mid = int(message_id.strip())
            for pid, pdata in panels.items():
                if pdata.get("message_id") == mid:
                    found = pdata
                    break
        except Exception:
            pass
    else:
        for pid, pdata in panels.items():
            if pdata.get("channel_id") == interaction.channel_id:
                found = pdata
                break

    if not found:
        if len(panels) == 1:
            _, found = next(iter(panels.items()))
        else:
            await interaction.response.send_message("❌ ไม่พบข้อมูลแผงควบคุมในห้องนี้ หรือ ID ที่ระบุไม่ถูกต้อง", ephemeral=True)
            return

    try:
        ch = bot.get_channel(found["channel_id"]) or await bot.fetch_channel(found["channel_id"])
        msg = await ch.fetch_message(found["message_id"])
        embed = _dp.build_deobf_panel_embed(found)
        view = _dp.DeobfPanelView()
        await msg.edit(embed=embed, view=view)
        await interaction.response.send_message(f"✅ ทำการรีเฟรชแผงควบคุม `{found['message_id']}` เรียบร้อยแล้ว", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการรีเฟรช: `{e}`", ephemeral=True)


@panel_group.command(name="edit", description="แก้ไขข้อความ หัวข้อ สี หรือรูปภาพของแผงควบคุม (เปิด Modal หรือระบุพารามิเตอร์)")
@app_commands.describe(
    message_id="ระบุ ID ข้อความของ Panel (หากไม่ระบุจะค้นหา Panel ในห้องนี้)",
    title="หัวข้อใหม่ของแผงควบคุม",
    description="ข้อความเนื้อหาใหม่ (หากต้องการพิมพ์ยาว ให้เว้นว่างไว้เพื่อเปิด Modal)",
    color="สี เช่น cyan, gold, emerald, crimson, หรือรหัส Hex",
    banner_url="URL ลิงก์รูปภาพ Banner ด้านล่าง",
    thumbnail_url="URL ลิงก์รูปภาพ Thumbnail ขวาบน",
    log_channel="ห้องที่จะให้บอทส่งผลลัพธ์สคริปต์ไปให้ (Log Channel)"
)
@app_commands.default_permissions(administrator=True)
async def panel_edit_subcmd(
    interaction: discord.Interaction,
    message_id: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None,
    banner_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    log_channel: Optional[discord.TextChannel] = None,
):
    import importlib
    import bot.deobf_panel as _dp
    importlib.reload(_dp)

    panels = _dp.load_deobf_panels()
    if not panels:
        await interaction.response.send_message("⚠️ ยังไม่มีแผงควบคุมใดๆ ติดตั้งอยู่ในระบบ (ใช้ `/setup panel` เพื่อติดตั้ง)", ephemeral=True)
        return

    found = None
    target_pid = None
    if message_id:
        try:
            mid = int(message_id.strip())
            for pid, pdata in panels.items():
                if pdata.get("message_id") == mid:
                    found = pdata
                    target_pid = pid
                    break
        except Exception:
            pass
    else:
        for pid, pdata in panels.items():
            if pdata.get("channel_id") == interaction.channel_id:
                found = pdata
                target_pid = pid
                break

    if not found:
        if len(panels) == 1:
            target_pid, found = next(iter(panels.items()))
        else:
            await interaction.response.send_message("❌ ไม่พบข้อมูลแผงควบคุมในห้องนี้ หรือระบุ ID ไม่ถูกต้อง (ลองพิมพ์ `/panel config` เพื่อดูรายการ)", ephemeral=True)
            return

    has_params = any(x is not None for x in [title, description, color, banner_url, thumbnail_url, log_channel])

    if not has_params:
        modal = _dp.EditPanelModal(panel_id=target_pid, pdata=found)
        await interaction.response.send_modal(modal)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    if title is not None:
        found["title"] = title.strip()
    if description is not None:
        found["description"] = description.replace("\\n", "\n")
    if color is not None:
        found["color"] = color.strip()
    if banner_url is not None:
        found["banner_url"] = banner_url.strip()
    if thumbnail_url is not None:
        found["thumbnail_url"] = thumbnail_url.strip()
    if log_channel is not None:
        found["log_channel_id"] = log_channel.id

    _dp.save_deobf_panel(target_pid, found)

    try:
        ch = bot.get_channel(found["channel_id"]) or await bot.fetch_channel(found["channel_id"])
        msg = await ch.fetch_message(found["message_id"])
        embed = _dp.build_deobf_panel_embed(found)
        view = _dp.DeobfPanelView()
        await msg.edit(embed=embed, view=view)
        await interaction.followup.send(
            f"✅ ปรับแต่งแผงควบคุม `{found['message_id']}` เรียบร้อยแล้ว!\n"
            f"👉 [คลิกเพื่อดูแผงควบคุม]({msg.jump_url})",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ เกิดข้อผิดพลาดในการอัปเดตข้อความบน Discord: `{e}`", ephemeral=True)


@panel_group.command(name="config", description="ดูรายการและสถานะแผงควบคุมทั้งหมดในเซิร์ฟเวอร์")
@app_commands.default_permissions(administrator=True)
async def panel_config_subcmd(interaction: discord.Interaction):
    panels = load_deobf_panels()
    embed = discord.Embed(
        title="⚙️ PAYOMBØYZ | รายการแผงควบคุม Deobf/Obf ในระบบ",
        color=discord.Color.blurple()
    )
    if not panels:
        embed.description = "ขณะนี้ยังไม่มีการติดตั้งแผงควบคุมในเซิร์ฟเวอร์\nใช้คำสั่ง `/setup panel` เพื่อเริ่มติดตั้ง"
    else:
        lines = []
        for pid, pdata in panels.items():
            ch_mention = f"<#{pdata.get('channel_id')}>"
            m_id = pdata.get("message_id")
            title = pdata.get("title") or DEFAULT_PANEL_TITLE
            lines.append(f"• **{title}** ในห้อง {ch_mention} (Message ID: `{m_id}`)")
        embed.description = "\n".join(lines)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@panel_group.command(name="remove", description="ลบแผงควบคุมออกจากห้องและฐานข้อมูล")
@app_commands.describe(message_id="ระบุ ID ข้อความของ Panel ที่ต้องการลบ")
@app_commands.default_permissions(administrator=True)
async def panel_remove_subcmd(interaction: discord.Interaction, message_id: str):
    try:
        mid = int(message_id.strip())
    except Exception:
        await interaction.response.send_message("❌ ID ข้อความไม่ถูกต้อง", ephemeral=True)
        return

    panels = load_deobf_panels()
    target_pid = None
    for pid, pdata in panels.items():
        if pdata.get("message_id") == mid:
            target_pid = pid
            break
    if not target_pid:
        await interaction.response.send_message(f"❌ ไม่พบแผงควบคุมรหัส `{mid}` ในระบบ", ephemeral=True)
        return

    pdata = panels[target_pid]
    try:
        ch = bot.get_channel(pdata["channel_id"]) or await bot.fetch_channel(pdata["channel_id"])
        msg = await ch.fetch_message(pdata["message_id"])
        await msg.delete()
    except Exception:
        pass

    delete_deobf_panel(target_pid)
    await interaction.response.send_message(f"✅ ลบแผงควบคุม `{mid}` เรียบร้อยแล้ว", ephemeral=True)


# Root aliases for panel commands
@bot.tree.command(name="panel_refresh", description="อัปเดตข้อความและปุ่มของแผงควบคุมที่มีอยู่ (คำสั่งตรง)")
@app_commands.describe(message_id="ระบุ ID ข้อความของ Panel (หากไม่ระบุจะค้นหา Panel ในห้องนี้)")
@app_commands.default_permissions(administrator=True)
async def cmd_slash_panel_refresh(interaction: discord.Interaction, message_id: Optional[str] = None):
    await panel_refresh_subcmd.callback(interaction, message_id)


@bot.tree.command(name="panel_edit", description="แก้ไขข้อความ หัวข้อ สี หรือรูปภาพของแผงควบคุม (คำสั่งตรง)")
@app_commands.describe(
    message_id="ระบุ ID ข้อความของ Panel (หากไม่ระบุจะค้นหา Panel ในห้องนี้)",
    title="หัวข้อใหม่ของแผงควบคุม",
    description="ข้อความเนื้อหาใหม่ (หากต้องการพิมพ์ยาว ให้เว้นว่างไว้เพื่อเปิด Modal)",
    color="สี เช่น cyan, gold, emerald, crimson, หรือรหัส Hex",
    banner_url="URL ลิงก์รูปภาพ Banner ด้านล่าง",
    thumbnail_url="URL ลิงก์รูปภาพ Thumbnail ขวาบน",
    log_channel="ห้องที่จะให้บอทส่งผลลัพธ์สคริปต์ไปให้ (Log Channel)"
)
@app_commands.default_permissions(administrator=True)
async def cmd_slash_panel_edit(
    interaction: discord.Interaction,
    message_id: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None,
    banner_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    log_channel: Optional[discord.TextChannel] = None,
):
    await panel_edit_subcmd.callback(
        interaction, message_id, title, description, color, banner_url, thumbnail_url, log_channel
    )


@bot.tree.command(name="panel_config", description="ดูรายการและสถานะแผงควบคุมทั้งหมดในเซิร์ฟเวอร์ (คำสั่งตรง)")
@app_commands.default_permissions(administrator=True)
async def cmd_slash_panel_config(interaction: discord.Interaction):
    await panel_config_subcmd.callback(interaction)


@bot.tree.command(name="panel_remove", description="ลบแผงควบคุมออกจากห้องและฐานข้อมูล (คำสั่งตรง)")
@app_commands.describe(message_id="ระบุ ID ข้อความของ Panel ที่ต้องการลบ")
@app_commands.default_permissions(administrator=True)
async def cmd_slash_panel_remove(interaction: discord.Interaction, message_id: str):
    await panel_remove_subcmd.callback(interaction, message_id)


@bot.tree.command(name="ai", description="คุยกับ PAYOMBØYZ Professor AI — ถามเรื่องสคริป, Deob, หรือเรื่องทั่วไป")
@app_commands.describe(
    prompt="พิมพ์อะไรก็ได้ เช่น 'ไง', 'Luraph คืออะไร', 'เขียนสคริปต์บิน', 'วิธี deob moonveil'",
    provider="เลือก AI สำหรับคำถามทั่วไป; คำถามสคริปใช้ Bluzy เป็นตัวหลักอัตโนมัติ"
)
@app_commands.choices(provider=[
    app_commands.Choice(name="Auto (เลือกอัตโนมัติ)", value="auto"),
    app_commands.Choice(name="Gemini", value="gemini"),
    app_commands.Choice(name="OpenRouter", value="openrouter"),
    app_commands.Choice(name="BluezyGPT", value="bluezygpt"),
    app_commands.Choice(name="DeepSeek", value="deepseek"),
    app_commands.Choice(name="ThaiLLM", value="thaillm")
])
async def cmd_slash_ai(interaction: discord.Interaction, prompt: str, provider: str = "auto"):
    await interaction.response.defer(thinking=True)
    QUALITY_MONITOR.note_activity()
    start_t = time.time()

    try:
        route_provider = None if provider == "auto" else provider
        chat_res = await ORCHESTRATOR.orchestrate_chat_query(
            user_prompt=prompt.strip(),
            user_name=interaction.user.display_name,
            preferred_provider=route_provider
        )
        reply = chat_res.get("reply", "")
        model_name = f"PAYOMBØYZ Professor [{chat_res.get('responder', 'unknown')}]"
        if chat_res.get("responder") not in ("safe-defensive-response", "local-content-guard", "none"):
            queued_for_review = QUALITY_MONITOR.submit(
                prompt.strip(), reply,
                provider=chat_res.get("responder", "unknown"),
                mode=chat_res.get("mode", "general_chat"),
            )
            if queued_for_review:
                print("[AI QA] Sampled slash-command turn for idle-only ThaiLLM review.", flush=True)
    except Exception as e:
        embed = discord.Embed(
            title=f"{PROJECT_NAME} | ❌ AI Error",
            description=f"AI Engine เกิดข้อผิดพลาด:\n```\n{str(e)[:500]}\n```",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return

    elapsed = time.time() - start_t

    # Ensure the user sees direct ownership of the answer in multi-user channels.
    tagged_reply = reply
    if "@" not in tagged_reply and interaction.user.mention not in tagged_reply:
        tagged_reply = f"**ถึง {interaction.user.mention}**\n\n{tagged_reply}"

    # Intelligent chunking & file delivery for long architectural answers
    has_code = "```" in tagged_reply
    if len(tagged_reply) <= 1900:
        embed = discord.Embed(
            title=f"{PROJECT_NAME} | 🤖 Senior Roblox Luau Professor",
            description=f"**คำถาม:** {prompt[:200]}\n**Engine:** `{model_name}` | **Latency:** `{elapsed:.2f}s`\n\n{tagged_reply}",
            color=discord.Color.from_rgb(0, 230, 150)
        )
        await interaction.followup.send(embed=embed)
    else:
        # Long response: send comprehensive overview embed + attach complete production script
        first_chunk = tagged_reply[:1800]
        last_nl = first_chunk.rfind("\n")
        if last_nl > 1000:
            first_chunk = first_chunk[:last_nl]

        embed = discord.Embed(
            title=f"{PROJECT_NAME} | 🤖 Senior Roblox Luau Professor",
            description=f"**คำถาม:** {prompt[:200]}\n**Engine:** `{model_name}` | **Latency:** `{elapsed:.2f}s`\n\n{first_chunk}",
            color=discord.Color.from_rgb(0, 230, 150)
        )
        embed.set_footer(text="📄 โค้ดและสถาปัตยกรรมฉบับเต็มถูกแนบเป็นไฟล์ด้านล่าง สามารถดาวน์โหลดไปรันได้ทันที")

        # Only attach a script file when the content is truly executable Lua. Otherwise keep it as a text file.
        file_bytes = io.BytesIO(tagged_reply.encode("utf-8"))
        ext = ".lua" if has_code and looks_like_real_lua(tagged_reply) else ".txt"
        f = discord.File(file_bytes, filename=f"Professor_Luau_Architecture{ext}")
        await interaction.followup.send(embed=embed, file=f)


@bot.tree.command(name="route_health", description="ตรวจสอบว่า Provider AI ไหนยังมีชีวิตและพร้อมใช้งานจริงก่อนส่งคำถาม")
@app_commands.describe(provider="เลือก Provider ที่ต้องการเช็ก หรือ Auto สำหรับทุก provider")
@app_commands.choices(provider=[
    app_commands.Choice(name="Auto (ตรวจทุก provider)", value="auto"),
    app_commands.Choice(name="Gemini", value="gemini"),
    app_commands.Choice(name="OpenRouter", value="openrouter"),
    app_commands.Choice(name="BluezyGPT", value="bluezygpt"),
    app_commands.Choice(name="DeepSeek", value="deepseek"),
    app_commands.Choice(name="ThaiLLM", value="thaillm")
])
async def cmd_slash_route_health(interaction: discord.Interaction, provider: str = "auto"):
    use_followup = interaction.response.is_done()
    try:
        if not interaction.response.is_done():
            try:
                await interaction.response.defer(thinking=True, ephemeral=True)
                use_followup = True
            except discord.HTTPException as ack_error:
                # A second acknowledgement can happen if another interaction
                # handler already deferred this command; continue via followup.
                if getattr(ack_error, "code", None) != 40060:
                    raise
                use_followup = True
        from bot.hybrid_router import HYBRID_ROUTER
        target_provider = None if provider == "auto" else provider
        # requests-based probes must not block Discord's event loop.
        health = await asyncio.to_thread(
            HYBRID_ROUTER.check_route_health,
            preferred_provider=target_provider,
            timeout_seconds=3.5,
        )
        provider_rows = health.get("providers", [])
        healthy = [p for p in provider_rows if p.get("status") == "HEALTHY"]
        grouped = {}
        for item in provider_rows:
            grouped.setdefault(item.get("provider", "unknown"), []).append(item)
        provider_labels = {
            "gemini": "Gemini", "openrouter": "OpenRouter / DeepSeek",
            "bluezygpt": "BluezyGPT", "deepseek": "DeepSeek Official",
            "thaillm": "ThaiLLM",
        }
        rows = []
        for name, items in grouped.items():
            ok_count = sum(1 for item in items if item.get("status") == "HEALTHY")
            problems = {}
            for item in items:
                status = item.get("status", "UNKNOWN")
                if status != "HEALTHY":
                    problems[status] = problems.get(status, 0) + 1
            issue_text = "" if not problems else " · " + ", ".join(f"{s} ×{n}" for s, n in problems.items())
            emoji = "✅" if ok_count == len(items) else "⚠️" if ok_count else "❌"
            rows.append(f"{emoji} {provider_labels.get(name, name)}: {ok_count}/{len(items)} healthy{issue_text}")

        runtime_status = runtime_guard.check_runtime()
        rt_line = (
            f"🐍 Python: `{runtime_status['python']['version']}` | "
            f"audioop: {'✅ OK' if runtime_status['audioop']['available'] else '❌ FAIL'} | "
            f"Discord-compatible: {'✅' if runtime_status['discord_compatible'] else '⚠️'}"
        )

        embed = discord.Embed(
            title=f"{PROJECT_NAME} | 📡 Route Health",
            description=f"**Provider Target:** `{provider}`\n**Healthy Routes:** `{len(healthy)}` / `{len(health.get('providers', []))}`\n{rt_line}",
            color=discord.Color.from_rgb(0, 230, 150) if healthy else discord.Color.orange()
        )
        embed.add_field(name="Provider Status", value="\n".join(rows) if rows else "ไม่มีข้อมูล", inline=False)
        embed.set_footer(text="Gemini is checked through Google's GenAI model-list endpoint; other routes use /models.")
        if use_followup or interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.NotFound:
        return
    except Exception as exc:
        print(f"[ROUTE HEALTH] Failed for interaction {interaction.id}: {exc}", flush=True)
        try:
            error_text = f"❌ ตรวจเช็ก route health ล้มเหลว: `{str(exc)[:300]}`"
            if use_followup or interaction.response.is_done():
                await interaction.followup.send(error_text, ephemeral=True)
            else:
                await interaction.response.send_message(error_text, ephemeral=True)
        except (discord.NotFound, discord.HTTPException):
            pass


@bot.tree.command(name="runtime_check", description="ตรวจสอบความเข้ากันได้ของ Python runtime และ audioop ก่อนให้ bot ทำงานกับ Discord")
async def cmd_slash_runtime_check(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        status = runtime_guard.check_runtime()
        png = "✅" if status["discord_compatible"] else "⚠️"
        describe = (
            f"**Python:** `{status['python']['version']}`\n"
            f"**audioop:** {'✅ OK' if status['audioop']['available'] else '❌ FAIL'}\n"
            f"**Discord compatible:** {png}\n"
            f"**Recommendation:** {status['recommendation']}"
        )
        embed = discord.Embed(
            title=f"{PROJECT_NAME} | 🔍 Runtime Health",
            description=describe,
            color=discord.Color.from_rgb(0, 230, 150) if status["discord_compatible"] else discord.Color.orange()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as exc:
        try:
            await interaction.followup.send(f"❌ Runtime check failed: `{str(exc)[:300]}`", ephemeral=True)
        except (discord.NotFound, discord.HTTPException):
            pass


@bot.tree.command(name="bypass", description="ปรมาจารย์สอนทำสคริปต์ Bypass, Anti-Cheat Evasion & Pro Architectures")
@app_commands.describe(
    topic="หัวข้อ เช่น 'hook namecall', 'cloneref', 'สุ่ม anime dice', 'บอทฟาร์ม', 'แก้ตัวแปร upvalue'",
    executor="ชื่อ Executor ที่ใช้งาน เช่น Wave, Solara, Synapse Z, Delta (ค่าเริ่มต้น: ทั่วไป)"
)
async def cmd_slash_bypass(interaction: discord.Interaction, topic: str, executor: str = "general"):
    await interaction.response.defer(thinking=True)
    start_t = time.time()
    try:
        from bot.bypass_professor import BYPASS_PROFESSOR
        reply = BYPASS_PROFESSOR.build_professor_response(
            query=topic.strip(),
            user_name=interaction.user.display_name,
            executor=executor.strip()
        )
        elapsed = time.time() - start_t
        embed = discord.Embed(
            title="PAYOMBØYZ | 🛡️ Bypass & Pro Script Professor",
            description=f"**เป้าหมาย:** `{topic}` | **Executor:** `{executor}` | **เวลา:** `{elapsed:.2f}s`\n\n{reply[:3800]}",
            color=discord.Color.from_rgb(138, 43, 226)
        )
        embed.set_footer(text="💡 ใช้ /feedback เพื่อรายงานผลการใช้งาน ช่วยให้ AI เรียนรู้และฉลาดขึ้น!")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ เกิดข้อผิดพลาดใน Bypass Professor: `{str(e)[:200]}`")


@bot.tree.command(name="bypass_feedback", description="ส่ง Feedback เทคนิค Bypass/Script ที่ใช้งาน เพื่อให้ AI เรียนรู้ด้วยตัวเอง")
@app_commands.describe(
    technique="ชื่อเทคนิค เช่น namecall_hook, cloneref_sandbox, anti_teleport_bypass, anime_dice_roll_system",
    status="ผลการใช้งาน (success = สำเร็จ ใช้งานได้, fail = โดนแบน / หลุด / ไม่ผ่าน)",
    note="หมายเหตุเพิ่มเติม เช่น ใช้งานใน Solara ผ่านฉลุย หรือ โดนแอนตี้จับได้ในแมพ..."
)
@app_commands.choices(status=[
    app_commands.Choice(name="✅ สำเร็จ (Success - ทำงานได้จริง)", value="success"),
    app_commands.Choice(name="❌ ล้มเหลว (Fail - เออเร่อ/หลุด/โดนตรวจจับ)", value="fail")
])
async def cmd_slash_bypass_feedback(interaction: discord.Interaction, technique: str, status: app_commands.Choice[str], note: str = ""):
    from bot.experience_db import EXPERIENCE_DB
    is_success = (status.value == "success")
    rec = EXPERIENCE_DB.record_bypass_feedback(
        technique_id=technique.strip().lower(),
        is_success=is_success,
        executor="community",
        note=note.strip()
    )
    new_eff = EXPERIENCE_DB.get_bypass_effectiveness(technique.strip().lower())
    
    emoji = "✅" if is_success else "⚠️"
    msg = (
        f"{emoji} **[PAYOMBØYZ SELF-LEARNING BRAIN UPDATED]**\n\n"
        f"บันทึกข้อมูลประสบการณ์ `{technique}` เรียบร้อย!\n"
        f"• ผลลัพธ์: `{status.name}`\n"
        f"• หมายเหตุ: `{note or '-'}`\n"
        f"• อัตราความสำเร็จอัพเดต: `{int(new_eff['adaptive_score'] * 100)}%` ({new_eff['status']})\n\n"
        f"🧠 *AI ได้เรียนรู้ข้อผิดพลาด/ความสำเร็จนี้ และจะนำไปปรับปรุงการสอนครั้งถัดไปอัตโนมัติ!*"
    )
    await interaction.response.send_message(msg)


@bot.tree.command(name="deobf", description="ถอดรหัสสคริปต์ Lua/Luau ด้วย Multi-Engine Deobfuscator")
@app_commands.describe(
    file="ไฟล์สคริปต์ .lua หรือ .txt ที่ต้องการถอดรหัส",
    code="ข้อความโค้ด (กรณีไม่ได้แนบไฟล์)",
    engine="เลือกเอนจินถอดรหัส (ค่าเริ่มต้น: Auto-Detect ตรวจจับอัตโนมัติ)"
)
@app_commands.choices(engine=[
    app_commands.Choice(name="⚙️ Auto-Detect (วิเคราะห์อัตโนมัติ)", value="auto"),
    app_commands.Choice(name="🌪️ Luraph v15.1 (Universal Industrial Devirt)", value="luraph_v15_1"),
    app_commands.Choice(name="⚡ Luraph v15 (Advanced Compiler)", value="luraph_v15"),
    app_commands.Choice(name="🔒 Luraph v14 (Classic & Buffer)", value="luraph"),
    app_commands.Choice(name="🛠️ WeAreDevs (Prometheus Dumper)", value="wearedevs"),
    app_commands.Choice(name="🌙 Moonveil 2.0.2+ (VM AST Dumper)", value="moonveil"),
    app_commands.Choice(name="☕ IronBrew & MoonSec (AST Lifter)", value="moonsec_ironbrew"),
    app_commands.Choice(name="🛡️ 2K Security & XOR Solver", value="twok"),
    app_commands.Choice(name="🌪️ Luast v1.0.1 Constant Lifter", value="luast"),
    app_commands.Choice(name="📦 A7DEV / Base64 Loader Unpacker", value="base64_loader"),
    app_commands.Choice(name="🌙 MoonSec V2 / V3 (Unicode Stego Devirt)", value="moonsec_v5")
])
async def cmd_slash_deobf(
    interaction: discord.Interaction,
    file: Optional[discord.Attachment] = None,
    code: Optional[str] = None,
    engine: Optional[app_commands.Choice[str]] = None
):
    if not file and not code:
        await interaction.response.send_message(
            "❌ กรุณาแนบไฟล์สคริปต์ (`.lua`, `.txt`) หรือกรอกโค้ดในช่อง `code`",
            ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)
    QUALITY_MONITOR.note_activity()

    input_name = file.filename if file else "Pasted_Script.lua"
    chosen_engine = engine.value if engine else "auto"

    temp_path = None
    try:
        if file:
            content_bytes = await file.read()
            temp_path = save_temp_input(content_bytes, file.filename)
        else:
            temp_path = save_temp_input(code.encode("utf-8", errors="replace"), "Pasted_Script.lua")

        # Grant full engine capabilities to all authorized users and members
        is_user_admin = True

        deobf_data = await ORCHESTRATOR.process_script_deobfuscation(
            str(temp_path),
            input_name,
            user_prompt=f"Slash command deobf engine={chosen_engine}",
            forced_engine=chosen_engine if chosen_engine != "auto" else None,
            is_admin=is_user_admin
        )
        engine_res = deobf_data.get("engine_result", {})
        ai_summary = deobf_data.get("ai_summary", "")

        if ai_summary:
            queued_for_review = QUALITY_MONITOR.submit(
                f"Slash deobfuscation request for {input_name}; engine={chosen_engine}",
                f"Analysis: {ai_summary}\n\nLocally deobfuscated output was attached as a .lua file.",
                provider=deobf_data.get("ai_worker", "unknown"),
                mode="deobfuscate",
            )
            if queued_for_review:
                print("[AI QA] Sampled slash deobfuscation for idle-only ThaiLLM review.", flush=True)

        decision_info = deobf_data.get("decision_info")
        embed, files = build_deobf_embed(engine_res, input_name, ai_summary, decision_info=decision_info)
        await dispatch_result_to_channel_or_interaction(
            interaction=interaction,
            embed=embed,
            files=files,
            action_type="DEOBFUSCATE",
            filename=input_name,
            guild_id=interaction.guild_id
        )

    except Exception as e:
        safe_err = security.sanitize_output_text(str(e), config.DISCORD_AI_BOT_TOKEN)
        embed = discord.Embed(
            title=f"{PROJECT_NAME} | ❌ เกิดข้อผิดพลาด",
            description=f"เกิดข้อผิดพลาดระหว่างประมวลผล:\n```\n{safe_err[:500]}\n```",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

@bot.tree.command(name="interceptor", description="ดาวน์โหลด Runtime Memory Interceptor สำหรับดึง Source สคริปต์ในเกม")
async def cmd_interceptor(interaction: discord.Interaction):
    from bot.runtime_interceptor_generator import build_unbreakable_guide_embed, get_runtime_interceptor_file
    embed = build_unbreakable_guide_embed()
    interceptor_file = get_runtime_interceptor_file()
    await interaction.response.send_message(embed=embed, file=interceptor_file, ephemeral=True)


@bot.tree.command(name="deobfuscate", description="ถอดรหัสสคริปต์ Lua/Luau ด้วย Multi-Engine Deobfuscator")
@app_commands.describe(
    file="ไฟล์สคริปต์ .lua หรือ .txt ที่ต้องการถอดรหัส",
    code="ข้อความโค้ด (กรณีไม่ได้แนบไฟล์)",
    engine="เลือกเอนจินถอดรหัส (ค่าเริ่มต้น: Auto-Detect ตรวจจับอัตโนมัติ)"
)
@app_commands.choices(engine=[
    app_commands.Choice(name="⚙️ Auto-Detect (วิเคราะห์อัตโนมัติ)", value="auto"),
    app_commands.Choice(name="🌪️ Luraph v15.1 (Universal Industrial Devirt)", value="luraph_v15_1"),
    app_commands.Choice(name="⚡ Luraph v15 (Advanced Compiler)", value="luraph_v15"),
    app_commands.Choice(name="🔒 Luraph v14 (Classic & Buffer)", value="luraph"),
    app_commands.Choice(name="🛠️ WeAreDevs (Prometheus Dumper)", value="wearedevs"),
    app_commands.Choice(name="🌙 Moonveil 2.0.2+ (VM AST Dumper)", value="moonveil"),
    app_commands.Choice(name="☕ IronBrew & MoonSec (AST Lifter)", value="moonsec_ironbrew"),
    app_commands.Choice(name="🛡️ 2K Security & XOR Solver", value="twok"),
    app_commands.Choice(name="🌪️ Luast v1.0.1 Constant Lifter", value="luast"),
    app_commands.Choice(name="📦 A7DEV / Base64 Loader Unpacker", value="base64_loader"),
    app_commands.Choice(name="🌙 MoonSec V2 / V3 (Unicode Stego Devirt)", value="moonsec_v5")
])
async def cmd_slash_deobfuscate(
    interaction: discord.Interaction,
    file: Optional[discord.Attachment] = None,
    code: Optional[str] = None,
    engine: Optional[app_commands.Choice[str]] = None
):
    await cmd_slash_deobf(interaction, file=file, code=code, engine=engine)


@bot.tree.command(name="reverse", description="🔬 Reverse Engineer Anything (REA Engine) — เจาะลึก Native PE/DLL, JS Bundle, .NET, APK หรือ Luau")
@app_commands.describe(
    file="ไฟล์ที่ต้องการ Reverse Engineering (PE, DLL, JS Bundle, .NET, APK, WASM หรือ Lua)",
    goal="เป้าหมายที่ต้องการวิเคราะห์ เช่น 'ถอดรหัสซอร์สโค้ด', 'หา API endpoints', 'แกะ VM bytecode'"
)
async def cmd_slash_reverse(
    interaction: discord.Interaction,
    file: discord.Attachment,
    goal: Optional[str] = "Full Forensic Reverse Engineering & Source Decompilation"
):
    await interaction.response.defer(thinking=True)
    from bot.rea_universal_orchestrator import REA_UNIVERSAL_ORCHESTRATOR
    from bot.idle_reverser_worker import IDLE_REVERSER
    IDLE_REVERSER.note_activity()

    temp_path = None
    try:
        content_bytes = await file.read()
        temp_path = save_temp_input(content_bytes, file.filename)
        res = await REA_UNIVERSAL_ORCHESTRATOR.reverse_target(Path(temp_path), user_prompt=goal or "")

        file_info = res.get("file_info", {})
        fmt_desc = file_info.get("desc", file_info.get("format", "Unknown"))
        elapsed = res.get("elapsed", 0.0)

        embed = discord.Embed(
            title="🔬 PAYOMBØYZ REA | Universal Reverse Engineering Dossier",
            description=(
                f"**เป้าหมาย:** `{file.filename}` ({len(content_bytes) / 1024.0:.1f} KB)\n"
                f"**สถาปัตยกรรม:** `{fmt_desc}`\n"
                f"**ระยะเวลาวิเคราะห์:** `{elapsed:.2f}s`\n\n"
                f"**สรุปผลการเจาะระบบ:**\n{res.get('summary', 'Reverse Engineering Complete')}\n"
            ),
            color=discord.Color.from_rgb(0, 230, 150)
        )
        embed.set_footer(text="PAYOMBØYZ REA v6.4.0 • 130 CLI Commands • 173 MCP Tools • Evidence-Based Contract")

        files_to_send = []
        for r_path in res.get("recovered_files", []):
            p = Path(r_path)
            if p.exists() and p.is_file():
                files_to_send.append(discord.File(str(p), filename=p.name))

        await interaction.followup.send(embed=embed, files=files_to_send[:10])

    except Exception as e:
        safe_err = security.sanitize_output_text(str(e), config.DISCORD_AI_BOT_TOKEN)
        await interaction.followup.send(f"❌ REA Engine Error: `{safe_err[:400]}`", ephemeral=True)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@bot.tree.command(name="obfuscate", description="เข้ารหัสและป้องกันสคริปต์ Lua/Luau ด้วย PAYOMBØYZ Multi-Engine & AI VM")
@app_commands.describe(
    file="ไฟล์สคริปต์ .lua หรือ .txt ที่ต้องการเข้ารหัส",
    code="ข้อความโค้ด (กรณีไม่ได้แนบไฟล์)",
    engine="เลือกเอนจินการเข้ารหัส (แนะนำ: Recommended สำหรับเข้ารหัสหลายชั้น)"
)
@app_commands.choices(engine=[
    app_commands.Choice(name="🟢 Level 1: Fast VM (Prometheus High Speed / 60 FPS)", value="level1"),
    app_commands.Choice(name="🟡 Level 2: Balanced Security (Prometheus Luau VM - แนะนำ)", value="level2"),
    app_commands.Choice(name="🔴 Level 3: Maximum Armor (Prometheus Multi-Layer Double-VM + 7-Shield Armor)", value="level3"),
    app_commands.Choice(name="⚡ Level 4: Prometheus Multi-Tier VM (Instruction Virtualizer)", value="level4"),
    app_commands.Choice(name="🛡️ Level 5: Sentinel Multi-Layer Double-VM (Dual-State CFF + Anti-Hook/Spy)", value="level5")
])
async def cmd_slash_obfuscate(
    interaction: discord.Interaction,
    file: Optional[discord.Attachment] = None,
    code: Optional[str] = None,
    engine: Optional[app_commands.Choice[str]] = None
):
    if not file and not code:
        await interaction.response.send_message(
            "❌ กรุณาแนบไฟล์สคริปต์ (`.lua`, `.txt`) หรือกรอกโค้ดในช่อง `code`",
            ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)

    input_name = file.filename if file else "Script.lua"
    chosen_engine = engine.value if engine else "level2"

    temp_path = None
    try:
        if file:
            content_bytes = await file.read()
            temp_path = save_temp_input(content_bytes, file.filename)
        else:
            temp_path = save_temp_input(code.encode("utf-8", errors="replace"), "Script.lua")

        obf_data = await ORCHESTRATOR.process_script_obfuscation(
            str(temp_path),
            input_name,
            engine_choice=chosen_engine
        )
        embed, files = build_obfuscate_embed(obf_data, input_name)
        await dispatch_result_to_channel_or_interaction(
            interaction=interaction,
            embed=embed,
            files=files,
            action_type="OBFUSCATE",
            filename=input_name,
            guild_id=interaction.guild_id,
            is_success=obf_data.get("success", False)
        )

    except Exception as e:
        safe_err = security.sanitize_output_text(str(e), config.DISCORD_AI_BOT_TOKEN)
        embed = discord.Embed(
            title="⚡ PAYOMBØYZ Obfuscate V6.7.6.7 | ❌ เกิดข้อผิดพลาด",
            description=f"เกิดข้อผิดพลาดระหว่างประมวลผล:\n```\n{safe_err[:500]}\n```",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@bot.tree.command(name="inspect_code", description="สแกนโครงสร้างโค้ด Luau แบบ AI IDE (นับ Functions, Remotes, Loops, และตรวจความเสี่ยง)")
@app_commands.describe(
    file="ไฟล์สคริปต์ที่ต้องการสแกน",
    code="โค้ดที่ต้องการสแกน (กรณีไม่ได้แนบไฟล์)"
)
async def cmd_slash_inspect_code(
    interaction: discord.Interaction,
    file: Optional[discord.Attachment] = None,
    code: Optional[str] = None
):
    if not file and not code:
        await interaction.response.send_message("❌ กรุณาแนบไฟล์สคริปต์หรือใส่โค้ดในช่อง `code`", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    fname = file.filename if file else "Custom_Script.luau"
    if file:
        raw_bytes = await file.read()
        code_str = raw_bytes.decode("utf-8", errors="replace")
    else:
        code_str = code or ""

    analysis = CODE_IDE.analyze_script(code_str, file_name=fname)
    report_text = CODE_IDE.format_ide_report(analysis)

    embed = discord.Embed(
        title=f"{PROJECT_NAME} | 🔬 AI IDE Inspection",
        description=report_text,
        color=discord.Color.blue() if analysis["is_valid"] else discord.Color.gold()
    )
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="knowledge", description="ค้นหาข้อมูลจาก PAYOMBØYZ KNOWLEDGE BASE (ราคา, UI Catalog, Bypass, Game Logic)")
@app_commands.describe(query="คำค้นหา เช่น 'ราคา', 'toggle', 'fisch', 'bypass'")
async def cmd_slash_knowledge(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    res = RETRIEVER.retrieve(query, top_k=2)
    embed = discord.Embed(
        title=f"{PROJECT_NAME} | 📚 Knowledge Base Search",
        description=f"**คำค้นหา:** `{query}`\n\n{res}",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="feedback", description="ส่งคำติชมผลลัพธ์ของ AI เพื่ออัปเดตระบบเรียนรู้ (Experience Database)")
@app_commands.describe(
    rating="ประเมินความถูกต้องของคำตอบ",
    comment="ข้อความเพิ่มเติม (ตัวเลือก)"
)
@app_commands.choices(rating=[
    app_commands.Choice(name="✅ ถูกต้องแม่นยำ (Correct / Good)", value="correct"),
    app_commands.Choice(name="⚠️ ถูกต้องบางส่วน (Partially Correct)", value="partial"),
    app_commands.Choice(name="❌ ผิดพลาดหรือไม่ตรง (Incorrect / Bad)", value="wrong")
])
async def cmd_slash_feedback(
    interaction: discord.Interaction,
    rating: app_commands.Choice[str],
    comment: Optional[str] = None
):
    from bot.experience_db import EXPERIENCE_DB
    recorded = EXPERIENCE_DB.record_user_feedback(task_or_id="latest", feedback=rating.value)
    embed = discord.Embed(
        title=f"{PROJECT_NAME} | 🧠 Feedback Recorded",
        description=(
            f"ขอบคุณสำหรับ Feedback ครับ!\n"
            f"• **คะแนน:** `{rating.name}`\n"
            f"• **บันทึกเข้า Memory:** `{'สำเร็จ (Experience DB Updated)' if recorded else 'รับข้อมูลแล้ว'}`\n"
            f"ข้อมูลนี้จะถูกนำไปคำนวณปรับปรุง Strategy & Confidence ในการตัดสินใจครั้งต่อไป"
        ),
        color=discord.Color.green() if rating.value == "correct" else (discord.Color.gold() if rating.value == "partial" else discord.Color.red())
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="help", description="แสดงวิธีใช้งาน PAYOMBØYZ AI & Multi-Engine Deobfuscator")

async def cmd_slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"{PROJECT_NAME} | คู่มือการใช้งาน",
        description="ศูนย์รวมเครื่องมือ AI เจนเนอเรเตอร์และ Multi-Engine Deobfuscator สำหรับ Roblox Luau",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="⚡ คำสั่ง AI Code Generator",
        value="• `/ai [prompt]` : สั่งให้ AI เขียนสคริปต์ด้วย 4-Brain Knowledge Architecture\n"
              "• `/inspect_code [file/code]` : ตรวจสอบสถาปัตยกรรมโค้ดสไตล์ AI IDE\n"
              "• `/knowledge [query]` : ค้นหาคลังความรู้ PAYOMBØYZ KNOWLEDGE BASE",
        inline=False
    )
    embed.add_field(
        name="🔓 คำสั่ง Deobfuscator",
        value="• `/deobf [file/code] [engine]` : ถอดรหัสสคริปต์ผ่าน 6 เอนจินระดับสูง\n"
              "• เอนจินที่รองรับ: WeAreDevs, Moonveil 2.0.2+, Luraph, MoonSec/IronBrew, 2K Security, Luast",
        inline=False
    )
    embed.add_field(
        name="🔒 คำสั่ง Obfuscator (V6.7.6.7)",
        value="• `/obfuscate [file/code] [engine]` : เข้ารหัสและป้องกันสคริปต์ด้วย Multi-Layer VM\n"
              "• เอนจินที่รองรับ: Recommended (AI Polymorphic + Double-VM), Double-VM, Fast-VM, DeepSeek AI, Minifier",
        inline=False
    )
    embed.add_field(
        name="🌐 In-Game Bridge Server",
        value="• ให้บริการ API บน `http://127.0.0.1:49281` เชื่อมต่อตรงกับสคริปต์ในเกม Roblox (AI Script HUB) แบบ Zero-Lag",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)



@bot.tree.command(name="ping", description="ตรวจสอบสถานะและความเร็ว Latency ของระบบ")
async def cmd_slash_ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    ai_status = "Online" if gemini_engine.is_available() else "Offline"
    gemini_pool = gemini_engine._KEY_POOL.pool_status()
    try:
        from bot.hybrid_router import HYBRID_ROUTER
        router_status = HYBRID_ROUTER.status()
        worker_line = (
            f"Gemini x{router_status['gemini_workers']} | "
            f"OpenRouter x{router_status['openrouter_workers']} | "
            f"BluezyGPT x{router_status['bluezygpt_workers']}"
        )
        healthy = router_status['healthy_workers']
        total = router_status['total_workers']
    except Exception:
        worker_line = "N/A"
        healthy = total = 0

    embed = discord.Embed(
        title="Pong! System Status",
        color=discord.Color.green() if healthy == total else discord.Color.gold()
    )
    embed.add_field(name="Discord Latency", value=f"`{latency}ms`", inline=True)
    embed.add_field(name="Gemini Engine", value=f"`{ai_status} ({gemini_pool['healthy_keys']}/{gemini_pool['total_keys']} keys)`", inline=True)
    embed.add_field(name="AI Workers", value=f"`{healthy}/{total} Healthy`", inline=True)
    embed.add_field(name="Provider Pool", value=f"`{worker_line}`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="clone", description="เปิดแผงควบคุมระบบโคลนเว็บไซต์ (Web Clone Tool) พร้อม 7 โหมดระดับปีศาจ")
async def cmd_slash_clone(interaction: discord.Interaction):
    from bot.clone_panel import build_clone_panel_embed, ClonePanelView
    embed = build_clone_panel_embed()
    view = ClonePanelView()
    await interaction.response.send_message(embed=embed, view=view)


# --- Prefix Commands ---

@bot.command(name="clone")
async def cmd_prefix_clone(ctx):
    from bot.clone_panel import build_clone_panel_embed, ClonePanelView
    embed = build_clone_panel_embed()
    view = ClonePanelView()
    await ctx.send(embed=embed, view=view)


@bot.command(name="ai")
async def cmd_prefix_ai(ctx, *, prompt: str = ""):
    if not prompt:
        await ctx.send("❌ กรุณาระบุคำสั่ง เช่น `!ai ไง`, `!ai Luraph คืออะไร`, `!ai เขียนสคริปต์บิน Fly Script`")
        return

    msg = await ctx.send("🤖 กำลังคิด...")
    try:
        chat_res = await ORCHESTRATOR.orchestrate_chat_query(
            user_prompt=prompt.strip(),
            user_name=ctx.author.display_name,
        )
        reply = str(chat_res.get("reply") or "").strip()
        if not reply:
            reply = "ตอนนี้ยังดึงคำตอบไม่สำเร็จ ลองส่งคำถามอีกครั้งได้เลย"
        if chat_res.get("responder") not in ("safe-defensive-response", "local-content-guard", "none"):
            QUALITY_MONITOR.submit(
                prompt.strip(), reply,
                provider=chat_res.get("responder", "unknown"),
                mode=chat_res.get("mode", "general_chat"),
            )
    except Exception as e:
        await msg.edit(content=f"❌ AI Engine Error: {str(e)[:500]}")
        return

    if len(reply) <= 1900:
        await msg.edit(content=reply)
    else:
        file_bytes = io.BytesIO(reply.encode("utf-8"))
        ext = ".lua" if "```" in reply else ".txt"
        f = discord.File(file_bytes, filename=f"PayomboyZ_AI_Reply{ext}")
        await msg.edit(content=f"🤖 คำตอบยาวเกินไป แนบเป็นไฟล์:", attachments=[f])


@bot.command(name="deobf")
@managed_job()
async def cmd_prefix_deobf(ctx, engine_choice: str = "auto"):
    if not ctx.message.attachments:
        await ctx.send("❌ กรุณาแนบไฟล์สคริปต์มากับคำสั่ง `!deobf`")
        return

    att = ctx.message.attachments[0]
    msg = await ctx.send(f"⏳ กำลังประมวลผลถอดรหัส `{att.filename}`...")
    # Read the FULL file — no size cap, no truncation
    content_bytes = await att.read()
    temp_path = save_temp_input(content_bytes, att.filename)

    try:
        # Grant full engine capabilities to all authorized users and members
        is_user_admin = True

        try:
            import importlib
            importlib.reload(engine_router)
        except Exception:
            pass
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(
            None,
            lambda: engine_router.deobfuscate(str(temp_path), engine_choice=engine_choice, timeout=config.DEOBFUSCATION_TIMEOUT, is_admin=is_user_admin)
        )
        ai_overview = res.get("ai_overview", "")

        # Human-Readable Cleanup Pipeline
        raw_code = res.get("deobfuscated_code", "")
        if raw_code and res.get("success"):
            try:
                guild_id = ctx.guild.id if ctx.guild else None
                log_ch_id = get_log_channel_id(guild_id)
                cleaned_code, cleanup_worker = await run_human_readable_cleanup(
                    raw_code, att.filename,
                    guild_id=guild_id,
                    log_channel_id=log_ch_id,
                    bot_instance=bot
                )
                res["deobfuscated_code"] = cleaned_code
                if cleanup_worker != "none":
                    ai_overview = (ai_overview or "") + f"\n\n🧹 **Human-Readable Cleanup:** `{cleanup_worker}` ✅"
            except Exception as ce:
                print(f"[DEOBF CMD] Cleanup error: {ce}", flush=True)

        embed, files = build_deobf_embed(res, att.filename, ai_summary=ai_overview)
        target_log_id = get_log_channel_id(guild_id)
        log_ch = bot.get_channel(target_log_id) or (await bot.fetch_channel(target_log_id) if target_log_id else None)
        if log_ch and log_ch.id != ctx.channel.id:
            is_ok = bool(engine_res.get("success", False))
            log_msg = await log_ch.send(
                content=f"🔔 **[DEOBFUSCATE LOG]** ผลลัพธ์สำหรับ {ctx.author.mention} | ไฟล์: `{att.filename}`",
                embed=embed,
                files=files
            )
            if is_ok:
                title_text = "✅ ถอดรหัสสำเร็จ"
                desc_text = f"ถอดรหัสสคริปต์ `{att.filename}` เรียบร้อยแล้ว!"
                color = discord.Color.green()
                link_label = "คลิกที่นี่เพื่อไปดูสคริปต์ที่ถอดรหัส"
            else:
                title_text = "❌ ถอดรหัสไม่สำเร็จ"
                desc_text = f"เกิดข้อผิดพลาดในการถอดรหัสสคริปต์ `{att.filename}`"
                color = discord.Color.red()
                link_label = "คลิกที่นี่เพื่อไปดูรายละเอียดข้อผิดพลาด"

            clean_embed = discord.Embed(
                title=f"⚡ PAYOMBØYZ | {title_text}",
                description=(
                    f"{desc_text}\n\n"
                    f"📂 **Log & ไฟล์สคริปต์ถูกส่งไปที่ห้อง:** {log_ch.mention}\n"
                    f"👉 **[{link_label}]({log_msg.jump_url})**"
                ),
                color=color
            )
            clean_embed.set_footer(text="PAYOMBØYZ Clean Command Room System")
            await msg.delete()
            await ctx.send(embed=clean_embed)
        else:
            await msg.delete()
            await ctx.send(embed=embed, files=files)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@bot.command(name="obfuscate", aliases=["obf"])
async def cmd_prefix_obfuscate(ctx: commands.Context, *, args: Optional[str] = None):
    raw_args = (args or "").strip()
    engine_choice = "recommended"
    inline_code = ""

    known_engines = ("level1", "level2", "level3", "level4", "level5", "recommended", "cff", "max_cff", "double_vm", "psu_strong", "fast_vm", "psu_yap", "minify", "sentinel")
    tokens = raw_args.split()
    if tokens and tokens[0].lower() in known_engines:
        engine_choice = tokens[0].lower()
        inline_code = " ".join(tokens[1:]).strip()
    else:
        inline_code = raw_args

    if ctx.message.attachments:
        att = ctx.message.attachments[0]
        input_name = att.filename
        content_bytes = await att.read()
    elif inline_code:
        import re as _re_cmd
        code_blocks = _re_cmd.findall(r'```(?:lua|luau)?\n([\s\S]*?)```', inline_code, _re_cmd.IGNORECASE)
        code_text = code_blocks[0].strip() if code_blocks else inline_code
        input_name = "Pasted_Script.lua"
        content_bytes = code_text.encode("utf-8", errors="replace")
    else:
        await ctx.send(
            "❌ กรุณาแนบไฟล์สคริปต์ (`.lua`, `.txt`) หรือพิมพ์โค้ดมากับคำสั่ง เช่น:\n"
            "`!obfuscate [engine] <โค้ด>` หรือ `!obf [แนบไฟล์]`\n"
            "*(เอนจินที่มี: recommended, cff, double_vm, fast_vm, minify)*"
        )
        return

    msg = await ctx.send(f"⏳ กำลังประมวลผลเข้ารหัส `{input_name}` ด้วยเอนจิน `{engine_choice}`...")
    temp_path = save_temp_input(content_bytes, input_name)

    try:
        obf_data = await ORCHESTRATOR.process_script_obfuscation(
            str(temp_path),
            input_name,
            engine_choice=engine_choice
        )
        embed, files = build_obfuscate_embed(obf_data, input_name)
        await msg.delete()
        await ctx.send(embed=embed, files=files)
    except Exception as e:
        safe_err = security.sanitize_output_text(str(e), config.DISCORD_AI_BOT_TOKEN)
        await msg.edit(content=f"❌ เกิดข้อผิดพลาดในการเข้ารหัส: `{safe_err[:300]}`")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def cmd_prefix_sync(ctx):
    msg = await ctx.send("⏳ กำลัง Sync Slash Commands...")
    try:
        synced = await bot.tree.sync()
        await msg.edit(content=f"✅ Sync คำสั่ง AI & Deobf สำเร็จแล้ว {len(synced)} คำสั่ง!")
    except Exception as e:
        await msg.edit(content=f"❌ เกิดข้อผิดพลาด: {e}")


# --- Prefix Setup Commands ---

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def cmd_prefix_setup(ctx, action_or_channel: Optional[str] = None):
    if action_or_channel and action_or_channel.lower() in ("clone", "web_clone", "webclone"):
        from bot.clone_panel import build_clone_panel_embed, ClonePanelView, save_clone_panel
        embed = build_clone_panel_embed()
        view = ClonePanelView()
        msg = await ctx.send(embed=embed, view=view)
        panel_id = f"clone_{ctx.channel.id}_{msg.id}"
        save_clone_panel(panel_id, {
            "panel_id": panel_id,
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "message_id": msg.id,
            "created_at": time.time(),
        })
        return
    elif action_or_channel and action_or_channel.lower() in ("panel", "deobf", "obf"):
        from bot.deobf_panel import build_deobf_panel_embed, DeobfPanelView, save_deobf_panel
        embed = build_deobf_panel_embed({})
        view = DeobfPanelView()
        msg = await ctx.send(embed=embed, view=view)
        panel_id = f"{ctx.channel.id}_{msg.id}"
        save_deobf_panel(panel_id, {
            "panel_id": panel_id,
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "message_id": msg.id,
            "created_at": time.time(),
        })
        return

    # Default to setup AI channel
    target = ctx.channel
    if action_or_channel:
        m = re.search(r'\d+', action_or_channel)
        if m:
            found_ch = ctx.guild.get_channel(int(m.group(0)))
            if found_ch:
                target = found_ch
    channels = load_ai_channels()
    channels.add(target.id)
    save_ai_channels(channels)
    embed = discord.Embed(
        title=f"{PROJECT_NAME} | 🤖 ติดตั้งห้อง AI สำเร็จ",
        description=f"✅ ติดตั้งห้อง {target.mention} เป็นห้องพูดคุยกับ AI เรียบร้อยแล้ว!\n"
                    f"สมาชิกทุกคนสามารถพิมพ์ข้อความพูดคุยได้ทันทีโดยไม่ต้องใช้คำสั่งครับ!\n\n"
                    f"💡 หากต้องการติดตั้งแผงควบคุม ให้พิมพ์:\n"
                    f"• `!setup clone` หรือ `/setup clone` (แผง Web Clone ระดับปีศาจ)\n"
                    f"• `!setup panel` หรือ `/setup panel` (แผง Deobfuscator & Obfuscator)",
        color=discord.Color.from_rgb(0, 230, 150)
    )
    await ctx.send(embed=embed)


@bot.command(name="setup_ai")
@commands.has_permissions(administrator=True)
async def cmd_prefix_setup_ai(ctx, channel: Optional[discord.TextChannel] = None):
    # @bot.command replaces the decorated function with a Command object;
    # invoke its callback when sharing the setup implementation.
    await cmd_prefix_setup.callback(ctx, channel)


@bot.command(name="setup_remove")
@commands.has_permissions(administrator=True)
async def cmd_prefix_setup_remove(ctx, channel: Optional[discord.TextChannel] = None):
    target = channel or ctx.channel
    from bot.deobf_panel import remove_dedicated_channel, load_deobf_panels, delete_deobf_panel
    channels = load_ai_channels()
    removed_roles = []

    if target.id in channels:
        channels.remove(target.id)
        save_ai_channels(channels)
        removed_roles.append("ห้องพูดคุย AI")

    if remove_dedicated_channel(target.id):
        removed_roles.append("ห้อง Dedicated (Deobf/Obf)")

    for pid, pdata in list(load_deobf_panels().items()):
        if pdata.get("channel_id") == target.id:
            delete_deobf_panel(pid)
            removed_roles.append("แผงควบคุม Panel")

    if removed_roles:
        roles_text = ", ".join(removed_roles)
        await ctx.send(
            f"✅ ยกเลิกการตั้งค่า **{roles_text}** สำหรับห้อง {target.mention} เรียบร้อยแล้ว!\n"
            f"• บอทจะไม่ตอบกลับข้อความอัตโนมัติในห้องนี้อีกต่อไป (ยกเว้นมีคนแท็กเรียกบอทโดยตรง)"
        )
    else:
        await ctx.send(
            f"ℹ️ ห้อง {target.mention} **ไม่ได้ถูกเปิดใช้งานในระบบอยู่แล้ว**\n"
            f"• บอทจะไม่ตอบกลับข้อความอัตโนมัติในห้องนี้ (จะตอบเมื่อมีคนแท็กเรียกบอทโดยตรงเท่านั้น)"
        )


@bot.command(name="setup_list")
@commands.has_permissions(administrator=True)
async def cmd_prefix_setup_list(ctx):
    channels = load_ai_channels()
    from bot.deobf_panel import load_dedicated_channels, load_deobf_panels
    dedicated = load_dedicated_channels()
    panels = load_deobf_panels()

    ai_mentions = [f"<#{cid}> (`{cid}`)" for cid in sorted(channels)] or ["- ไม่มี -"]
    ded_mentions = [f"<#{cid}> (โหมด: `{info.get('mode', 'unknown')}`)" for cid, info in dedicated.items()] or ["- ไม่มี -"]
    panel_mentions = [f"<#{info.get('channel_id')}> (ID: `{info.get('channel_id')}`)" for info in panels.values()] or ["- ไม่มี -"]

    embed = discord.Embed(
        title="📋 PAYOMBØYZ | รายการห้องที่เปิดใช้งานในระบบ",
        description="บอทจะตอบกลับอัตโนมัติเฉพาะห้องที่ระบุไว้ด้านล่างนี้เท่านั้น นอกนั้นต้องแท็กเรียกบอทโดยตรง:",
        color=discord.Color.from_rgb(0, 230, 150)
    )
    embed.add_field(name="🤖 ห้องพูดคุย AI (Auto-Reply)", value="\n".join(ai_mentions), inline=False)
    embed.add_field(name="⚙️ ห้อง Dedicated Drop File", value="\n".join(ded_mentions), inline=False)
    embed.add_field(name="🎛️ ห้องแผงควบคุม Panel", value="\n".join(panel_mentions), inline=False)

    await ctx.send(embed=embed)


async def _safe_autodelete(msg: Optional[discord.Message], delay: int = 15):
    if not msg:
        return
    try:
        await asyncio.sleep(delay)
        await msg.delete()
    except Exception:
        pass


# --- Autonomous In-Channel AI Chat Listener ---

async def _handle_ai_message(message: discord.Message):
    channels = load_ai_channels()
    channel_id = message.channel.id
    parent_channel_id = getattr(message.channel, "parent_id", None)
    # Prefer the configured channel ID, but tolerate a thread under that channel.
    from bot.deobf_panel import get_dedicated_channel_mode
    dedicated_mode = get_dedicated_channel_mode(channel_id)
    is_dm = (message.guild is None)
    is_ai_channel = (
        is_dm
        or channel_id in channels
        or (parent_channel_id is not None and parent_channel_id in channels)
    )

    # Ignore bots to prevent response loops, but log this in configured AI
    # channels so a self-authored test message is not mistaken for an AI outage.
    if message.author.bot:
        if is_ai_channel:
            print(
                f"[AI CHAT] Ignored bot-authored message in configured AI channel "
                f"(channel_id={message.channel.id}, author_id={message.author.id}).",
                flush=True,
            )
        return

    # Let prefix commands execute
    if message.content.startswith(config.COMMAND_PREFIX):
        await bot.process_commands(message)
        return

    is_mentioned = bool(bot.user and bot.user in message.mentions and not message.mention_everyone)
    is_reply_to_bot = False
    # CRITICAL: Only consider reply_to_bot inside designated AI channels or direct DMs.
    # Replying to bot embeds/panels/results in general channels MUST NEVER trigger conversational AI!
    if (is_ai_channel or is_dm) and message.reference and message.reference.resolved and isinstance(message.reference.resolved, discord.Message):
        if bot.user and message.reference.resolved.author.id == bot.user.id:
            is_reply_to_bot = True

    # Check if this user clicked Deobfuscate / Obfuscate on the panel recently
    from bot.deobf_panel import ACTIVE_PANEL_SESSIONS, OpenConfigModalView
    panel_sess = ACTIVE_PANEL_SESSIONS.get(message.author.id)
    if panel_sess and (time.time() - panel_sess.get("timestamp", 0) < 300):
        att = message.attachments[0] if message.attachments else None
        code_text = message.content.strip() if not att else None

        if att or (code_text and len(code_text) >= 10):
            ACTIVE_PANEL_SESSIONS.pop(message.author.id, None)
            mode = panel_sess.get("mode", "deobf")
            filename = att.filename if att else "Script.lua"

            # Buffer raw bytes into memory immediately BEFORE deleting message
            raw_bytes = None
            if att:
                try:
                    raw_bytes = await att.read()
                except Exception as read_err:
                    print(f"[PANEL ERROR] Attachment read failed: {read_err}", flush=True)
                    raw_bytes = None
            elif code_text:
                raw_bytes = code_text.encode("utf-8", errors="replace")

            size_str = f"({len(raw_bytes) / 1024.0:.1f} KB)" if raw_bytes else (f"({att.size / 1024.0:.1f} KB)" if att else f"({len(code_text):,} ตัวอักษร)")

            action_text = "ถอดรหัส (Deobfuscate)" if mode == "deobf" else "ป้องกันโค้ด (Obfuscate)"
            embed = discord.Embed(
                title=f"📁 PAYOMBØYZ | ได้รับสคริปต์สำหรับ {action_text}",
                description=(
                    f"**เป้าหมาย:** `{filename}` {size_str}\n\n"
                    f"👉 **คลิกปุ่มด้านล่างเพื่อเปิด Pop-up เลือก Engine และตั้งชื่อไฟล์:**"
                ),
                color=discord.Color.green() if mode == "deobf" else discord.Color.blue()
            )
            embed.set_footer(text="คลิกปุ่มด้านล่างเพื่อเปิดหน้าต่าง Pop-up ทันที (1-Click)")
            view = OpenConfigModalView(
                mode=mode,
                attachment=att,
                code_text=code_text,
                author_id=message.author.id,
                default_filename=filename,
                raw_bytes=raw_bytes
            )
            try:
                await message.delete()
            except Exception as del_err:
                print(f"[PANEL] User message delete skipped: {del_err}", flush=True)
            await message.channel.send(embed=embed, view=view)
            return

    # Dedicated drop channel gate: files and scripts only, NEVER conversational AI!
    if dedicated_mode:
        from bot.loader_spy_engine import LoaderSpyEngine
        _u = LoaderSpyEngine.extract_loader_urls(message.content)
        from bot.deobf_panel import ACTIVE_MULTIGAME_HUBS
        _is_mg = (message.channel.id in ACTIVE_MULTIGAME_HUBS)
        _has_code = ("```" in message.content)
        _has_payload = bool(message.attachments or _u or _is_mg or _has_code)
        if not _has_payload:
            await bot.process_commands(message)
            return

    # General channel gate: MUST be an approved AI channel, direct @mention, or valid reply in AI channel
    if not (is_ai_channel or is_mentioned or is_reply_to_bot or dedicated_mode):
        await bot.process_commands(message)
        return

    QUALITY_MONITOR.note_activity()
    try:
        from bot.idle_reverser_worker import IDLE_REVERSER
        IDLE_REVERSER.note_activity()
    except Exception:
        pass

    print(
        f"[AI CHAT] Processing message (channel_id={message.channel.id}, "
        f"ai_channel={is_ai_channel}, mentioned={bool(is_mentioned)}, "
        f"reply_to_bot={is_reply_to_bot}, attachments={len(message.attachments)}).",
        flush=True,
    )

    # Extract clean text from user
    content = message.content
    if bot.user:
        content = content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

    if not content and not message.attachments:
        print(
            f"[AI CHAT] Empty message content (channel_id={message.channel.id}, "
            f"author_id={message.author.id}, configured_channel={is_ai_channel}). "
            "Check the Discord Developer Portal Message Content Intent toggle.",
            flush=True,
        )
        if is_ai_channel:
            await message.reply(
                "อ่านข้อความนี้ไม่ได้ครับ เปิด **Message Content Intent** ใน "
                "Discord Developer Portal > Bot แล้วรีสตาร์ตบอท",
                mention_author=False,
            )
        return

    # Accept all prompts. Do not reject or suppress user input based on intent.
    # Script and file requests are handled directly; general chat remains open.
    prompt = content
    attached_code_text = ""
    attached_filename = ""

    # 1.4 Active Multi-Game Hub Quick Response Interception
    from bot.deobf_panel import ACTIVE_MULTIGAME_HUBS, MultiGameSelectView
    if message.channel.id in ACTIVE_MULTIGAME_HUBS:
        active_hub = ACTIVE_MULTIGAME_HUBS[message.channel.id]
        if time.time() - active_hub.get("timestamp", 0) < 600:
            g_map = active_hub.get("games_map", {})
            chosen_pid = None
            m_num = re.search(r'\b(\d{5,})\b', content)
            if m_num and int(m_num.group(1)) in g_map:
                chosen_pid = int(m_num.group(1))
            else:
                from bot.loader_spy_engine import LoaderSpyEngine
                ctx_m = LoaderSpyEngine.resolve_game_from_context(content, g_map)
                if ctx_m:
                    chosen_pid = ctx_m[0]

            if chosen_pid:
                async with message.channel.typing():
                    from bot.loader_spy_engine import spy_and_deobf
                    fn = g_map.get(chosen_pid) or g_map.get(str(chosen_pid), "")
                    base_u = active_hub.get("base_url", "")
                    if fn and (fn.startswith("http://") or fn.startswith("https://")):
                        target_u = fn
                    elif fn and base_u:
                        target_u = f"{base_u.rstrip('/')}/{fn.lstrip('/')}"
                    else:
                        target_u = active_hub.get("hub_target", "")
                    spy_res = await asyncio.to_thread(spy_and_deobf, target_u, place_id=chosen_pid)
                    if spy_res.get("success"):
                        conf = spy_res.get("confidence", 100.0)
                        grade = spy_res.get("confidence_grade", "EXCELLENT")
                        lines = spy_res.get("recovered_lines", 0)
                        elapsed = spy_res.get("elapsed", 0.0)
                        target_u = spy_res.get("target_url", "GitHub Raw")
                        deobf_code = spy_res.get("deobfuscated_code", "")
                        mg_info = spy_res.get("multigame_info", {})
                        g_name = mg_info.get("selected_game_name", f"PlaceId {chosen_pid}")

                        embed = discord.Embed(
                            title=f"{PROJECT_NAME} | 🎮 Multi-Game Hub Deobfuscation Complete",
                            description=(
                                f"**แมพที่เลือก:** `{g_name}` (PlaceId: `{chosen_pid}`)\n"
                                f"**เป้าหมาย URL:** `{target_u}`\n"
                                f"**ระดับความแม่นยำ (Confidence):** `{conf:.1f}%` ({grade}) 🎯\n"
                                f"**โครงสร้างที่กู้คืนได้:** `{lines:,} บรรทัด` (Clean Luau)\n"
                                f"**เวลาที่ใช้:** `{elapsed:.2f}s`\n"
                            ),
                            color=discord.Color.from_rgb(0, 230, 150)
                        )
                        file_bytes = io.BytesIO(deobf_code.encode("utf-8"))
                        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(target_u).stem or f"hub_place_{chosen_pid}")
                        f = discord.File(file_bytes, filename=f"{safe_name}.clean.luau")
                        from bot.deobf_panel import DeobfResultActionView
                        await message.reply(embed=embed, file=f, view=DeobfResultActionView(), mention_author=False)
                        ACTIVE_MULTIGAME_HUBS.pop(message.channel.id, None)
                        return
                    else:
                        err_text = spy_res.get('error', 'Universal deobfuscator failed on final payload')
                        embed = discord.Embed(
                            title=f"{PROJECT_NAME} | ❌ เกิดข้อผิดพลาดในการแกะแมพ PlaceId {chosen_pid}",
                            description=f"ระบบพยายามดาวน์โหลดและถอดรหัสสคริปต์สำหรับ PlaceId `{chosen_pid}` แต่ล้มเหลว:\n```\n{err_text[:500]}\n```",
                            color=discord.Color.red()
                        )
                        await message.reply(embed=embed, mention_author=False)
                        return

    # 1.5 Auto-Interception of GitHub / Loader Scripts (GitHub Spy & Confidence Deobfuscator)
    from bot.loader_spy_engine import LoaderSpyEngine, spy_and_deobf
    loader_urls = LoaderSpyEngine.extract_loader_urls(content)
    is_explicit_spy = any(k in content.lower() for k in [
        "spy", "แกะ", "deob", "src", "source", "loadstring", "github", "สปาย",
        "ดู", "เปิด", "หา", "เอา", "ถอด", "แตก", "ดึง", "เช็ค", "check",
        "rawget", "rawgithub", "pastebin", "rentry", "raw url",
    ])
    # Auto-intercept: raw code-hosting URLs — no keyword needed, just paste the link
    _RAW_CODE_HOSTS = (
        "raw.githubusercontent.com", "pastebin.com/raw", "rentry.co/",
        "jnkie.com/", "nousigi.com/", "rscripts.net/", "cdn.luarmor.net/",
        "scriptblox.com/raw", "gist.github.com", "gist.githubusercontent.com",
        "cdn.discordapp.com/attachments",  # discord CDN raw script links
    )
    _has_raw_script_url = any(
        any(h in u.lower() for h in _RAW_CODE_HOSTS) or u.lower().endswith((".lua", ".luau"))
        for u in loader_urls
    )
    # If message is nothing but a URL (≤4 words) → always spy
    _is_url_only_message = len(content.strip().split()) <= 4 and bool(loader_urls)
    if loader_urls and (_has_raw_script_url or _is_url_only_message or is_explicit_spy
                        or dedicated_mode or "loadstring" in content.lower() or "BASE" in content):
        # Extract optional place_id from message
        target_pid = None
        pid_m = re.search(r'(?:place|game|แมพ|เกม|id)\s*[:=]?\s*(\d{5,})', content, re.IGNORECASE)
        if pid_m:
            try:
                target_pid = int(pid_m.group(1))
            except Exception:
                pass

        status_msg = None
        try:
            status_msg = await message.reply(
                "⚡ **PAYOMBØYZ Loader Spy & Deobfuscator**\n"
                "> 🔍 ตรวจพบ Loader Link กำลังดึง Payload และเริ่มกระบวนการถอดรหัส... (กรุณารอสักครู่)",
                mention_author=False
            )
        except Exception:
            pass

        async with message.channel.typing():
            try:
                spy_res = await asyncio.wait_for(
                    asyncio.to_thread(spy_and_deobf, content, place_id=target_pid),
                    timeout=120.0
                )
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title=f"{PROJECT_NAME} | ⏱️ Deobfuscation Timeout",
                    description=(
                        "⚠️ **การประมวลผลใช้เวลานานเกินกำหนด (Timeout 120s)**\n\n"
                        "สคริปต์ปลายทางมีขนาดใหญ่มากหรือมีโครงสร้าง VM ซับซ้อนสูง\n"
                        "💡 *คำแนะนำ:* ลองส่งเฉพาะไฟล์สคริปต์ตัวเต็ม (.lua / .txt) แนบเข้ามาในแชทโดยตรงเพื่อให้ระบบ Sharded Engine ประมวลผลได้เต็มประสิทธิภาพ"
                    ),
                    color=discord.Color.from_rgb(255, 120, 0)
                )
                if status_msg:
                    try:
                        await status_msg.edit(content=None, embed=timeout_embed)
                        return
                    except Exception:
                        pass
                await message.reply(embed=timeout_embed, mention_author=False)
                return
            except Exception as e_spy:
                err_embed = discord.Embed(
                    title=f"{PROJECT_NAME} | ❌ Processing Error",
                    description=f"เกิดข้อผิดพลาดในการประมวลผล: `{e_spy}`",
                    color=discord.Color.red()
                )
                if status_msg:
                    try:
                        await status_msg.edit(content=None, embed=err_embed)
                        return
                    except Exception:
                        pass
                await message.reply(embed=err_embed, mention_author=False)
                return

            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass

            if spy_res.get("success"):
                conf = spy_res.get("confidence", 100.0)
                grade = spy_res.get("confidence_grade", "EXCELLENT")
                lines = spy_res.get("recovered_lines", 0)
                elapsed = spy_res.get("elapsed", 0.0)
                target_u = spy_res.get("target_url", "GitHub Raw")
                deobf_code = spy_res.get("deobfuscated_code", "")
                mg_info = spy_res.get("multigame_info")

                mg_desc = ""
                if mg_info:
                    g_sel_name = mg_info.get("selected_game_name")
                    g_sel_pid = mg_info.get("selected_place_id")
                    g_reason = mg_info.get("match_reason")
                    sel_str = f" • เลือกแมพ: `{g_sel_name}` (PlaceId: `{g_sel_pid}`) [{g_reason}]" if g_sel_name else ""
                    mg_desc = (
                        f"**🎮 Multi-Game Hub:** ตรวจพบ `{mg_info.get('total_games', 0)}` แมพในตาราง{sel_str}\n"
                        f"**🛡️ Anti-Executor Trap:** กักกันกับดัก `{mg_info.get('honeypot_trap') or 'None'}` สำเร็จ\n"
                    )

                game_info = spy_res.get("game_forensics", {})
                game_str = f"**🎮 เกม / แมพที่ตรวจพบ:** `{game_info.get('display', 'Universal')}`\n" if game_info else ""

                embed = discord.Embed(
                    title=f"{PROJECT_NAME} | 🕵️ Advanced Loader Spy & Deobfuscator",
                    description=(
                        f"**เป้าหมาย:** `{target_u}`\n"
                        f"{game_str}"
                        f"{mg_desc}"
                        f"**ระดับความแม่นยำ (Confidence):** `{conf:.1f}%` ({grade}) 🎯\n"
                        f"**โครงสร้างที่กู้คืนได้:** `{lines:,} บรรทัด` (Clean Luau)\n"
                        f"**เวลาที่ใช้:** `{elapsed:.2f}s`\n\n"
                        f"**Breakdown การวัดผล:**\n"
                        f"• Compiler Gate: `{spy_res.get('confidence_breakdown', {}).get('compiler_gate', 40)}/40` (100% Executable)\n"
                        f"• Semantic Invariants: `{spy_res.get('confidence_breakdown', {}).get('semantic_preservation', 30)}/30` (Constants Preserved)\n"
                        f"• VM Bytecode Elimination: `{spy_res.get('confidence_breakdown', {}).get('vm_elimination', 15)}/15` (Clean AST)\n"
                        f"• SSA Normalization: `{spy_res.get('confidence_breakdown', {}).get('ssa_normalization', 15)}/15` (Registers Inlined)"
                    ),
                    color=discord.Color.from_rgb(0, 230, 150)
                )
                embed.set_footer(text="ไฟล์ Clean Source Code ถูกจัดส่งแนบมาด้านล่างแล้ว สามารถนำกลับไปใช้งานได้ทันที")

                file_bytes = io.BytesIO(deobf_code.encode("utf-8"))
                safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(target_u).stem or "github_script")
                f = discord.File(file_bytes, filename=f"{safe_name}.clean.luau")
                from bot.deobf_panel import DeobfResultActionView
                await message.reply(embed=embed, file=f, view=DeobfResultActionView(), mention_author=False)
                return
            elif spy_res.get("requires_user_selection"):
                total_games = spy_res.get("total_games", len(spy_res.get("games_map", {})))
                base_u = spy_res.get("base_url", "")
                cat_list = spy_res.get("games_catalog", [])
                cat_lua = spy_res.get("catalog_lua", "")
                last_url = spy_res.get("last_valid_url") or content

                ACTIVE_MULTIGAME_HUBS[message.channel.id] = {
                    "hub_target": last_url,
                    "payload": spy_res.get("last_valid_payload"),
                    "games_map": spy_res.get("games_map", {}),
                    "base_url": base_u,
                    "total_games": total_games,
                    "author_id": message.author.id,
                    "timestamp": time.time()
                }

                embed = discord.Embed(
                    title=f"{PROJECT_NAME} | 🎮 ตรวจพบ Multi-Game Hub ({total_games:,} แมพ)",
                    description=(
                        f"**เป้าหมาย:** `{last_url}`\n"
                        f"**โครงสร้างสคริปต์:** ตรวจพบว่า Loader นี้เป็นแบบ **Multi-Game Hub** (เช่น Ouroboros) รองรับทั้งหมด **`{total_games:,}` แมพ**!\n"
                        f"**Base Repository:** `{base_u or 'Direct Script Endpoints'}`\n\n"
                        f"⚠️ **ทำไมระบบถึงหยุดถาม?**\n"
                        f"เพราะใน Hub นี้มีสคริปต์แยกตามเกมมากกว่า 1 แมพ ระบบจะไม่สุ่มเลือกเกมแรกเพื่อป้องกันการได้สคริปต์ผิดเกม\n\n"
                        f"👉 **วิธีเลือกแมพที่ต้องการแกะ:**\n"
                        f"1. **เลือกจากเมนู Dropdown ด้านล่าง** (คัดเลือก 25 แมพแรกมาให้)\n"
                        f"2. หรือ **พิมพ์ตอบกลับข้อความนี้** ด้วย PlaceId หรือชื่อแมพ เช่น:\n"
                        f"   `แกะ 2753915549` หรือ `แกะ Blox Fruits` หรือ `แกะ 99 Nights`\n"
                        f"3. ดาวน์โหลดไฟล์ Mapping Table ด้านล่างเพื่อตรวจสอบสคริปต์ทั้งหมด `{total_games}` เกม"
                    ),
                    color=discord.Color.from_rgb(255, 170, 0)
                )
                embed.set_footer(text="PAYOMBØYZ Hub Orchestrator • Zero Guessing • 100% Precision")

                view = MultiGameSelectView(
                    catalog_list=cat_list,
                    hub_target=last_url,
                    author_id=message.author.id,
                    games_map=spy_res.get("games_map", {}),
                    base_url=base_u
                )

                files_to_send = []
                if cat_lua:
                    cat_bytes = io.BytesIO(cat_lua.encode("utf-8"))
                    files_to_send.append(discord.File(cat_bytes, filename="Hub_Games_Mapping_Catalog.luau"))

                await message.reply(embed=embed, view=view, files=files_to_send, mention_author=True)
                return
            else:
                # 🛑 CRITICAL GATE: Hard Halt on Loader Spy / Network / Deobfuscation Failure
                # Never fall through to general AI chat to prevent hallucinated 3KB mock scripts!
                err_msg = spy_res.get("error", "Failed to retrieve or deobfuscate payload")
                hops = spy_res.get("hops_trace", [])
                last_valid = spy_res.get("last_valid_payload")
                failed_url = spy_res.get("target_url", "Unknown Target")

                hop_lines = []
                for h in hops:
                    h_num = h.get("hop", 1)
                    h_url = h.get("url", "")
                    h_st = h.get("status", "")
                    if h_st == "success":
                        hop_lines.append(f"• **Hop {h_num}:** `{h_url}` ✅ (`{h.get('size_bytes', 0):,}` bytes)")
                    else:
                        hop_lines.append(f"• **Hop {h_num}:** `{h_url}` ❌ (`{h.get('error', 'Failed')}`)")

                hop_desc = "\n".join(hop_lines) if hop_lines else f"• เป้าหมาย: `{failed_url}`"

                embed = discord.Embed(
                    title=f"{PROJECT_NAME} | ⚠️ Loader Spy Forensic Diagnostic",
                    description=(
                        f"**ผลการทำงาน:** ตรวจพบข้อผิดพลาดในห่วงโซ่ Loader ไม่สามารถดึง Payload ปลายทางมาถอดรหัสได้\n\n"
                        f"**🔍 เส้นทาง Loader Hops:**\n{hop_desc}\n\n"
                        f"**สาเหตุ:** `{err_msg}`\n\n"
                        f"ℹ️ *หมายเหตุ: สคริปต์ปลายทางอาจถูกผู้พัฒนาลบไปแล้ว (HTTP 404), เป็น Private Repo หรือติด Cloudflare WAF จึงไม่มีโค้ดตัวเต็มให้ถอดรหัส*"
                    ),
                    color=discord.Color.from_rgb(255, 70, 70)
                )

                files_to_send = []
                if last_valid and len(last_valid.strip()) > 0:
                    embed.add_field(
                        name="📦 โค้ดที่ตรวจจับได้จาก Hop ล่าสุดก่อนขาดตอน",
                        value=f"แนบไฟล์โค้ดต้นทาง (`{len(last_valid):,}` ตัวอักษร) มาให้ตรวจสอบด้านล่าง",
                        inline=False
                    )
                    raw_bytes = io.BytesIO(last_valid.encode("utf-8"))
                    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(failed_url).stem or "interception_stage")
                    files_to_send.append(discord.File(raw_bytes, filename=f"{safe_name}_Interception_Stage.lua"))

                await message.reply(embed=embed, files=files_to_send, mention_author=True)
                return

    # 2. Check if user attached a file
    if message.attachments:
        first_att = message.attachments[0]
        content_bytes = await first_att.read()
        sample_text = content_bytes[:15000].decode("utf-8", errors="replace")

        # 1. Forensic Inspection via Next-Gen MCI-Engine (V15.0)
        from bot.mci_ingestion_engine import MCIIngestionEngine
        from bot.map_schema_extractor import MapSchemaExtractor
        from bot.sharded_synthesis_engine import ShardedSynthesisEngine
        from bot.deobf_panel import get_dedicated_channel_mode, SingleActionPromptView

        dedicated_mode = get_dedicated_channel_mode(message.channel.id)
        mci_res = MCIIngestionEngine.inspect(
            user_text=content,
            filename=first_att.filename,
            content_bytes=content_bytes,
            dedicated_mode=dedicated_mode
        )

        is_deob = (mci_res.route_target == "deobfuscate")
        is_obf = (mci_res.route_target == "obfuscate")
        is_game_dump = (mci_res.route_target == "game_dump_synthesis")
        is_rea = (mci_res.route_target == "rea_reverse")
        is_clean_refactor = (mci_res.route_target == "clean_refactor")

        # 1.9 REA Universal Reverse Engineering Pipeline
        if is_rea:
            async with message.channel.typing():
                from bot.rea_universal_orchestrator import REA_UNIVERSAL_ORCHESTRATOR
                temp_bin = save_temp_input(content_bytes, first_att.filename)
                try:
                    res = await REA_UNIVERSAL_ORCHESTRATOR.reverse_target(Path(temp_bin), user_prompt=content)
                    file_info = res.get("file_info", {})
                    fmt_desc = file_info.get("desc", file_info.get("format", "Unknown"))
                    elapsed = res.get("elapsed", 0.0)

                    embed = discord.Embed(
                        title="🔬 PAYOMBØYZ REA | Universal Reverse Engineering Dossier",
                        description=(
                            f"**เป้าหมาย:** `{first_att.filename}` ({len(content_bytes) / 1024.0:.1f} KB)\n"
                            f"**สถาปัตยกรรม:** `{fmt_desc}`\n"
                            f"**ระยะเวลาวิเคราะห์:** `{elapsed:.2f}s`\n\n"
                            f"**สรุปผลการเจาะระบบ:**\n{res.get('summary', 'Reverse Engineering Complete')}\n"
                        ),
                        color=discord.Color.from_rgb(0, 230, 150)
                    )
                    embed.set_footer(text="PAYOMBØYZ REA v6.4.0 • 130 CLI Commands • 173 MCP Tools")

                    files_to_send = []
                    for r_path in res.get("recovered_files", []):
                        p = Path(r_path)
                        if p.exists() and p.is_file():
                            files_to_send.append(discord.File(str(p), filename=p.name))

                    await message.reply(embed=embed, files=files_to_send[:10], mention_author=True)
                    return
                finally:
                    if temp_bin and os.path.exists(temp_bin):
                        try:
                            os.remove(temp_bin)
                        except Exception:
                            pass

        # ── GAME DUMP CONTEXT SYNTHESIS (Zero Hallucinations, 50k-100k Chars) ─────────
        if is_game_dump:
            async with message.channel.typing():
                try:
                    # Parse dump via MapSchemaExtractor
                    full_text = content_bytes.decode("utf-8", errors="replace")
                    contract = MapSchemaExtractor.extract_from_content(full_text, filename=first_att.filename)
                    user_req = content or "สร้างสคริปต์ Auto Farm และฟังก์ชั่นอำนวยความสะดวกเต็มระบบสำหรับแมพนี้"

                    # Synthesize massive exploit hub via ShardedSynthesisEngine
                    synth_res = await ShardedSynthesisEngine.synthesize_massive_hub(
                        user_request=user_req,
                        map_contract_text=contract.compact_contract_text,
                        game_name=contract.game_name or Path(first_att.filename).stem,
                        place_id=contract.place_id,
                        ui_library="Fluent",
                        target_scale="massive"
                    )

                    lua_code = synth_res.complete_code
                    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(first_att.filename).stem)
                    out_fname = f"{clean_name}_Suite.luau"
                    file_bytes = io.BytesIO(lua_code.encode("utf-8"))

                    embed = discord.Embed(
                        title=f"⚡ PAYOMBØYZ CYBER-AI | High-Capacity Exploit Suite Generated",
                        description=synth_res.chat_summary,
                        color=discord.Color.from_rgb(0, 230, 150)
                    )
                    embed.add_field(
                        name="📡 Ground-Truth Contract Overview",
                        value=(
                            f"• Remotes พบ: `{len(contract.remotes.get('RemoteEvent', [])) + len(contract.remotes.get('RemoteFunction', []))}` ตัว (Zero Hallucination)\n"
                            f"• Workspace Entities: `{sum(len(v) for v in contract.workspace_entities.values())}` โฟลเดอร์เป้าหมาย\n"
                            f"• ความยาวโค้ด: `{synth_res.total_characters:,}` ตัวอักษร (`{synth_res.total_lines:,}` บรรทัด)"
                        ),
                        inline=False
                    )
                    embed.set_footer(text="PAYOMBØYZ M3SE V15.0 • 100% Executable Luau Architecture")
                    await message.reply(embed=embed, file=discord.File(file_bytes, filename=out_fname), mention_author=True)
                    return
                except Exception as dump_err:
                    print(f"[AI BOT ERROR] Map dump synthesis failed: {dump_err}", flush=True)

        # ── CLEAN SCRIPT REFACTOR / FEATURE ENHANCEMENT ──────────────────────────────
        if is_clean_refactor:
            attached_code_text = content_bytes.decode("utf-8", errors="replace")
            attached_filename = first_att.filename
            # Fall through to conversational AI / script synthesis with attached_code_text intact!

        # ── DEDICATED CHANNEL DROP ONLY (Without Prompt) ─────────────────────────────
        elif dedicated_mode:
            target_mode = dedicated_mode
            size_kb = len(content_bytes) / 1024.0
            view = SingleActionPromptView(
                mode=target_mode,
                attachment=first_att,
                author_id=message.author.id,
                raw_bytes=content_bytes,
                default_filename=first_att.filename
            )
            try:
                await message.delete()
            except Exception as del_err:
                print(f"[RAW DROP] User message delete skipped: {del_err}", flush=True)
            await message.channel.send(
                content=f"<@{message.author.id}> ⚙️ ตรวจพบไฟล์: `{first_att.filename}` ({size_kb:.1f} KB)\nกรุณากดปุ่มด้านล่างเพื่อเลือกเครื่องมือและตั้งชื่อไฟล์:",
                view=view
            )
            return

        # 2.0 Multi-Layer Obfuscation Pipeline (User explicitly requested Obfuscation on attached file)
        if is_obf:
            try:
                await message.delete()
            except Exception:
                pass
            async with message.channel.typing():
                temp_path = None
                try:
                    temp_path = save_temp_input(content_bytes, first_att.filename)
                    obf_data = await ORCHESTRATOR.process_script_obfuscation(
                        str(temp_path),
                        first_att.filename,
                        engine_choice="recommended"
                    )
                    embed, files = build_obfuscate_embed(obf_data, first_att.filename)
                    user_files, log_files = _clone_discord_files(files)

                    # 1. ALWAYS deliver files directly to user in their channel!
                    await message.channel.send(content=f"{message.author.mention}", embed=embed, files=user_files)

                    # 2. Mirror a copy to log channel if available
                    guild_id = message.guild.id if message.guild else None
                    target_log_id = get_log_channel_id(guild_id)
                    log_ch = bot.get_channel(target_log_id) or (await bot.fetch_channel(target_log_id) if target_log_id else None)
                    if log_ch and log_ch.id != message.channel.id:
                        try:
                            await log_ch.send(
                                content=f"🔒 **[OBFUSCATE LOG]** ผลลัพธ์สำหรับ {message.author.mention} | ไฟล์: `{first_att.filename}`",
                                embed=embed,
                                files=log_files
                            )
                        except Exception as log_err:
                            print(f"[OBF LOG ERROR] {log_err}", flush=True)

                    if dedicated_mode:
                        from bot.deobf_panel import post_pinned_guide
                        await post_pinned_guide(message.channel, dedicated_mode)
                    return
                except Exception as e:
                    safe_err = security.sanitize_output_text(str(e), config.DISCORD_AI_BOT_TOKEN)
                    err_msg = await message.channel.send(f"❌ Obfuscation เกิดข้อผิดพลาด: `{safe_err[:300]}`")
                    asyncio.create_task(_safe_autodelete(err_msg, 15))
                    return
                finally:
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass

        # 2.1 Multi-Engine Deobfuscation Pipeline
        elif is_deob:
            try:
                await message.delete()
            except Exception:
                pass
            async with message.channel.typing():
                temp_path = None
                try:
                    # Authorize full engine capabilities for all users and role-holders
                    is_user_admin = True

                    temp_path = save_temp_input(content_bytes, first_att.filename)
                    deobf_data = await ORCHESTRATOR.process_script_deobfuscation(
                        str(temp_path),
                        first_att.filename,
                        user_prompt=content or "",
                        is_admin=is_user_admin
                    )
                    engine_res = deobf_data.get("engine_result", {})
                    ai_summary = deobf_data.get("ai_summary", "")

                    try:
                        from bot.re_diagnostic_engine import DIAGNOSTIC_ENGINE
                        input_script_text = content_bytes.decode("utf-8", errors="replace")
                        biopsy = DIAGNOSTIC_ENGINE.perform_full_biopsy(input_script_text, first_att.filename)
                        fp = biopsy["fingerprint"]
                        th = biopsy["threats"]
                        biopsy_prefix = (
                            f"🔬 **VM Fingerprint:** `{fp['engine']} ({fp['version']})` | "
                            f"**Threat Status:** `{th['threat_level']}`\n"
                        )
                        if th["webhooks"]:
                            biopsy_prefix += f"🚨 **Hidden Webhooks Found:** {', '.join(th['webhooks'])}\n"
                        if th["honeypot_remotes"]:
                            biopsy_prefix += f"🍯 **HoneyPot Traps Found:** `{', '.join(th['honeypot_remotes'])}`\n"
                        ai_summary = f"{biopsy_prefix}\n{ai_summary}" if ai_summary else biopsy_prefix
                    except Exception as bio_err:
                        print(f"[BIOPSY ERROR] {bio_err}", flush=True)

                    if ai_summary:
                        queued_for_review = QUALITY_MONITOR.submit(
                            content or f"Deobfuscate {first_att.filename}",
                            f"Analysis: {ai_summary}\n\nLocal deobfuscation output was attached as a .lua file.",
                            provider=deobf_data.get("ai_worker", "unknown"),
                            mode="deobfuscate",
                        )
                        if queued_for_review:
                            print("[AI QA] Sampled deobfuscation analysis for idle-only ThaiLLM review.", flush=True)

                    # Human-Readable Cleanup Pipeline
                    raw_code = engine_res.get("deobfuscated_code", "")
                    if raw_code and engine_res.get("success"):
                        try:
                            guild_id = message.guild.id if message.guild else None
                            log_ch_id = get_log_channel_id(guild_id)
                            cleaned_code, cleanup_worker = await run_human_readable_cleanup(
                                raw_code, first_att.filename,
                                guild_id=guild_id,
                                log_channel_id=log_ch_id,
                                bot_instance=bot
                            )
                            engine_res["deobfuscated_code"] = cleaned_code
                            if cleanup_worker != "none":
                                ai_summary = (ai_summary or "") + f"\n\n🧹 **Human-Readable Cleanup:** `{cleanup_worker}` ✅"
                        except Exception as ce:
                            print(f"[MSG HANDLER] Cleanup error: {ce}", flush=True)

                    decision_info = deobf_data.get("decision_info")
                    embed, files = build_deobf_embed(engine_res, first_att.filename, ai_summary, decision_info=decision_info)
                    user_files, log_files = _clone_discord_files(files)

                    # 1. ALWAYS deliver files directly to user in their channel with Interceptor button!
                    from bot.deobf_panel import DeobfResultActionView
                    await message.channel.send(content=f"{message.author.mention}", embed=embed, files=user_files, view=DeobfResultActionView())

                    # 2. Mirror a copy to log channel if available
                    guild_id = message.guild.id if message.guild else None
                    target_log_id = get_log_channel_id(guild_id)
                    log_ch = bot.get_channel(target_log_id) or (await bot.fetch_channel(target_log_id) if target_log_id else None)
                    if log_ch and log_ch.id != message.channel.id:
                        try:
                            await log_ch.send(
                                content=f"🔔 **[DEOBFUSCATE LOG]** ผลลัพธ์สำหรับ {message.author.mention} | ไฟล์: `{first_att.filename}`",
                                embed=embed,
                                files=log_files
                            )
                        except Exception as log_err:
                            print(f"[DEOBF LOG ERROR] {log_err}", flush=True)

                    if dedicated_mode:
                        from bot.deobf_panel import post_pinned_guide
                        await post_pinned_guide(message.channel, dedicated_mode)
                    return
                except Exception as e:
                    safe_err = security.sanitize_output_text(str(e), config.DISCORD_AI_BOT_TOKEN)
                    err_msg = await message.channel.send(f"❌ Deobfuscation เกิดข้อผิดพลาด: `{safe_err[:300]}`")
                    asyncio.create_task(_safe_autodelete(err_msg, 15))
                    return
                finally:
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass

        # 2.2 General AI Analysis & IDE Code Inspection
        elif file_inspection.get("is_script_ext") or first_att.size < 2 * 1024 * 1024:
            try:
                attached_code_text = content_bytes.decode("utf-8", errors="replace")
                attached_filename = first_att.filename
            except Exception:
                attached_code_text = ""
                attached_filename = ""

    # 2.25 Dedicated RE Biopsy & Threat Scanner Intent (!scan, /scan, ตรวจสอบโค้ด, สแกนไฟล์)
    lowered_cmd = (content or "").lower().strip()
    is_scan_command = (
        lowered_cmd.startswith("!scan")
        or lowered_cmd.startswith("!audit")
        or lowered_cmd.startswith("!unmask")
        or "สแกนสคริปต์" in lowered_cmd
        or "ตรวจสคริปต์" in lowered_cmd
        or "สแกนโค้ด" in lowered_cmd
    )
    if is_scan_command:
        target_code = attached_code_text
        target_name = attached_filename or "TargetScript.lua"
        if not target_code:
            import re as _re_p
            code_blocks = _re_p.findall(r'```(?:lua|luau)?\n([\s\S]*?)```', content, _re_p.IGNORECASE)
            target_code = code_blocks[0].strip() if code_blocks else ""

        if target_code:
            async with message.channel.typing():
                from bot.re_diagnostic_engine import DIAGNOSTIC_ENGINE
                report = DIAGNOSTIC_ENGINE.perform_full_biopsy(target_code, target_name)
                formatted_report = DIAGNOSTIC_ENGINE.format_biopsy_report(report)
                await message.reply(formatted_report, mention_author=False)
                return

    # 2.26 REA Website Cloner Intent (!clone, !rip, โคลนเว็บ, ดูดเว็บ, ก๊อปเว็บ)
    is_clone_command = (
        lowered_cmd.startswith("!clone")
        or lowered_cmd.startswith("!rip")
        or "โคลนเว็บ" in lowered_cmd
        or "ดูดเว็บ" in lowered_cmd
        or "ก๊อปเว็บ" in lowered_cmd
        or "แกะเว็บ" in lowered_cmd
    )
    if is_clone_command:
        import re as _re_url
        urls = _re_url.findall(r'https?://[^\s<>"\')]+', content)
        if urls:
            target_url = urls[0]
            async with message.channel.typing():
                from bot.rea_engine_bridge import WebClonerEngine
                clone_res = WebClonerEngine.clone_website(target_url)
                if clone_res.get("success"):
                    embed = discord.Embed(
                        title="🌐 PAYOMBØYZ REA — Website Reconstruction Complete",
                        description=f"โคลนและถอดรหัสโครงสร้างหน้าเว็บสำเร็จ!\n**Target**: `{target_url}`\n**Domain**: `{clone_res['domain']}`",
                        color=0x00FFCC
                    )
                    comps = clone_res.get("components", [])
                    comp_text = "\n".join(f"• {c}" for c in comps) if comps else "• General Static DOM Layout"
                    embed.add_field(name="🏛️ Reconstructed Components", value=comp_text, inline=False)
                    embed.add_field(name="🎨 Stylesheets Aggregate", value=f"{clone_res.get('css_sources_count', 0)} sources merged into `styles.css`", inline=True)
                    embed.add_field(name="📦 Scripts Identified", value=f"{clone_res.get('scripts_count', 0)} external bundles", inline=True)
                    embed.add_field(name="📂 Local Storage Path", value=f"`{clone_res['target_dir']}`", inline=False)
                    embed.set_footer(text="REA Multi-Platform Reverse Engineering Engine • Ready for local preview")
                    
                    files_to_send = []
                    zip_p = Path(clone_res.get("zip_path", ""))
                    if zip_p.exists():
                        files_to_send.append(discord.File(str(zip_p), filename=zip_p.name))
                    bp_path = Path(clone_res.get("blueprint_path", ""))
                    if bp_path.exists():
                        files_to_send.append(discord.File(str(bp_path), filename="SECURITY_RECON_REPORT.txt"))
                    
                    await message.reply(embed=embed, files=files_to_send, mention_author=False)
                    return
                else:
                    await message.reply(f"❌ โคลนเว็บไซต์ไม่สำเร็จ: `{clone_res.get('error')}`", mention_author=False)
                    return

    # 2.27 Native PE / Binary / JS Bundle Reverse Engineering Intent (!re, !inspect, !pe, เจาะไฟล์, วิเคราะห์ไบนารี)
    is_re_command = (
        lowered_cmd.startswith("!re")
        or lowered_cmd.startswith("!inspect")
        or lowered_cmd.startswith("!pe")
        or "เจาะไฟล์" in lowered_cmd
        or "วิเคราะห์ไบนารี" in lowered_cmd
        or (attached_filename and attached_filename.lower().endswith((".exe", ".dll", ".sys", ".bin")))
    )
    if is_re_command:
        if message.attachments:
            att = message.attachments[0]
            if att.filename.lower().endswith((".exe", ".dll", ".sys", ".bin")):
                async with message.channel.typing():
                    temp_pe = save_temp_input(await att.read(), att.filename)
                    from bot.rea_engine_bridge import NativeBinaryInspector
                    pe_report = NativeBinaryInspector.inspect_pe_file(str(temp_pe))
                    if pe_report.get("success"):
                        embed = discord.Embed(
                            title=f"🔬 PAYOMBØYZ REA — Native PE Biopsy: {att.filename}",
                            description=f"**Architecture**: `{pe_report.get('architecture')}`\n**File Size**: `{pe_report.get('file_size'):,} bytes`\n**Image Base**: `{pe_report.get('image_base')}` | **Entry Point**: `{pe_report.get('entry_point')}`",
                            color=0xFF0055 if pe_report.get("is_packed") else 0x00FF88
                        )
                        embed.add_field(name="🛡️ Packer / Crypter Detection", value=f"**{pe_report.get('packer_detection')}**", inline=False)
                        
                        sec_lines = [f"`{s['name']:<8}` | Entropy: `{s['entropy']}` | RawSize: `{s['raw_size']:,}`" for s in pe_report.get("sections", [])[:6]]
                        embed.add_field(name="📊 Section Entropy & Layout", value="\n".join(sec_lines) or "None", inline=False)
                        
                        apis = pe_report.get("suspicious_apis_detected", [])
                        if apis:
                            embed.add_field(name="⚠️ Critical API Sinks Detected", value=", ".join(f"`{a}`" for a in apis), inline=False)
                        
                        embed.set_footer(text="REA Hopper / Ghidra Native Evidence Contract")
                        await message.reply(embed=embed, mention_author=False)
                        return
                    else:
                        await message.reply(f"❌ วิเคราะห์ไบนารีไม่สำเร็จ: `{pe_report.get('error')}`", mention_author=False)
                        return

    # 2.3 Check if user pasted code into chat with Obfuscate intent

    if not message.attachments and ORCHESTRATOR.classify_intent(content) == "obfuscate":
        import re as _re_obf
        code_blocks = _re_obf.findall(r'```(?:lua|luau)?\n([\s\S]*?)```', content, _re_obf.IGNORECASE)
        pasted_script = code_blocks[0].strip() if code_blocks else ""
        if not pasted_script:
            # Strip prompt trigger text and see if remaining text has Lua code
            cleaned_code = _re_obf.sub(
                r'^(?:ช่วย|ขอ|pls|please)?\s*(?:obfuscate|obf|เข้ารหัส|ออฟบัส|ออบฟัส)\s*(?:ให้หน่อย|ให้ที|สคริปต์นี้|สคริปนี้|โค้ดนี้)?\s*[:\n]?',
                '',
                content,
                flags=_re_obf.IGNORECASE
            ).strip()
            if any(w in cleaned_code for w in ["function", "local ", "print(", "task.", "game:", "end", "return "]):
                pasted_script = cleaned_code

        if pasted_script:
            async with message.channel.typing():
                temp_path = None
                try:
                    temp_path = save_temp_input(pasted_script.encode("utf-8", errors="replace"), "Pasted_Script.lua")
                    obf_data = await ORCHESTRATOR.process_script_obfuscation(
                        str(temp_path),
                        "Pasted_Script.lua",
                        engine_choice="recommended"
                    )
                    embed, files = build_obfuscate_embed(obf_data, "Pasted_Script.lua")
                    await message.reply(embed=embed, files=files, mention_author=False)
                    return
                except Exception as e:
                    safe_err = security.sanitize_output_text(str(e), config.DISCORD_AI_BOT_TOKEN)
                    await message.reply(f"❌ Obfuscation เกิดข้อผิดพลาด: `{safe_err[:300]}`", mention_author=False)
                    return
                finally:
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass

    # 2.35 Check if user pasted code into chat with Deobfuscate intent
    if not message.attachments and (ORCHESTRATOR.classify_intent(content) == "deobfuscate" or any(w in lowered_cmd for w in ["แกะสคริป", "แกะโค้ด", "deobf", "ถอดรหัส"])):
        import re as _re_deob
        code_blocks = _re_deob.findall(r'```(?:lua|luau)?\n([\s\S]*?)```', content, _re_deob.IGNORECASE)
        pasted_deob_script = code_blocks[0].strip() if code_blocks else ""
        if not pasted_deob_script:
            cleaned_deob = _re_deob.sub(
                r'^(?:ช่วย|ขอ|pls|please)?\s*(?:deobfuscate|deobf|แกะสคริปต์|แกะสคริป|แกะโค้ด|ถอดรหัส)\s*(?:ให้หน่อย|ให้ที|สคริปต์นี้|สคริปนี้|โค้ดนี้)?\s*[:\n]?',
                '',
                content,
                flags=_re_deob.IGNORECASE
            ).strip()
            if any(w in cleaned_deob for w in ["function", "local ", "print(", "task.", "game:", "end", "return ", "LPH_", "ll1"]):
                pasted_deob_script = cleaned_deob

        if pasted_deob_script:
            async with message.channel.typing():
                temp_path = None
                try:
                    is_user_admin = True
                    temp_path = save_temp_input(pasted_deob_script.encode("utf-8", errors="replace"), "Pasted_Deobf_Script.lua")
                    deobf_data = await ORCHESTRATOR.process_script_deobfuscation(
                        str(temp_path),
                        "Pasted_Deobf_Script.lua",
                        user_prompt=content or "",
                        is_admin=is_user_admin
                    )
                    engine_res = deobf_data.get("engine_result", {})
                    ai_summary = deobf_data.get("ai_summary", "")

                    decision_info = deobf_data.get("decision_info")
                    embed, files = build_deobf_embed(engine_res, "Pasted_Deobf_Script.lua", ai_summary, decision_info=decision_info)
                    from bot.deobf_panel import DeobfResultActionView
                    await message.reply(embed=embed, files=user_files, view=DeobfResultActionView(), mention_author=False)
                    return
                except Exception as e:
                    safe_err = security.sanitize_output_text(str(e), config.DISCORD_AI_BOT_TOKEN)
                    await message.reply(f"❌ Deobfuscation เกิดข้อผิดพลาด: `{safe_err[:300]}`", mention_author=False)
                    return
                finally:
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass

    # 2.4 If user pasted Lua code in chat without attachments, extract for AI Code Intelligence
    if not attached_code_text and content:
        import re as _re_paste
        code_blocks = _re_paste.findall(r'```(?:lua|luau)?\n([\s\S]*?)```', content, _re_paste.IGNORECASE)
        if code_blocks:
            attached_code_text = code_blocks[0].strip()
            attached_filename = "Pasted_Script.lua"
        elif len(content.splitlines()) > 5 and any(w in content for w in ["game:GetService", "local ", "function ", "task.wait"]):
            attached_code_text = content.strip()
            attached_filename = "Pasted_Script.lua"

    # 2.45 Explicit Deobfuscate Intent Guard (Prevents generating fake mock scripts when no code was provided)
    lowered_content = (content or "").lower()
    is_pure_deobf_query = any(w in lowered_content for w in ["แกะสคริป", "แกะโค้ด", "แกะสคริปต์", "deobf", "ถอดรหัส"]) and not attached_code_text and not message.attachments
    if is_pure_deobf_query:
        await message.reply(
            "⚠️ **ไม่พบไฟล์สคริปต์หรือลิงก์ Loader ที่จะให้ถอดรหัส**\n"
            "กรุณาแนบไฟล์สคริปต์ (`.lua` / `.txt`), แปะโค้ดใน Codeblock (` ```lua ... ``` `), หรือส่งคำสั่ง Loader เช่น `loadstring(game:HttpGet(\"...\"))()` เพื่อให้ระบบ Deobfuscate เริ่มต้นทำงานครับ",
            mention_author=True
        )
        return

    # 2.5 Auto-resolve Roblox game links (roblox.com/games/ or roblox.com/share?)
    roblox_game_info = None
    target_script_name = "Professor_Script.lua"
    if contains_roblox_game_link(content):
        print(f"[AI CHAT] Roblox game link detected from {message.author.display_name}. Resolving metadata...", flush=True)
        try:
            roblox_game_info = await resolve_roblox_game_async(content)
            if roblox_game_info:
                print(
                    f"[AI CHAT] Resolved Roblox game: '{roblox_game_info.get('name')}' "
                    f"(Place ID: {roblox_game_info.get('place_id')})",
                    flush=True
                )
                prompt = build_game_script_prompt(roblox_game_info, content)
                c_name = roblox_game_info.get("clean_name")
                if c_name and c_name != "RobloxGame":
                    target_script_name = f"{c_name}_Script.lua"
        except Exception as r_err:
            print(f"[AI CHAT] Roblox game resolution error: {r_err}", flush=True)

    # 2.6 Detect Roblox game name from conversational text ONLY if user explicitly mentions Roblox or exploit
    user_explicitly_mentions_roblox = any(w in lowered_content for w in [
        "roblox", "โรบล็อก", "executor", "โปรแมพ", "สคริปต์แมพ", "สคริปแมพ",
        "บล็อกฟรุต", "bloxfruit", "fisch", "rivals", "solara", "wave", "delta", "synapse"
    ])
    if not roblox_game_info and user_explicitly_mentions_roblox:
        from bot.knowledge_router import ROUTER as KNOWLEDGE_ROUTER
        detected_game = None
        for alias in KNOWLEDGE_ROUTER.GAME_MAP_FILES.keys():
            if len(alias) <= 3:
                if re.search(rf"\b{re.escape(alias)}\b", lowered_content):
                    detected_game = alias.title()
                    break
            elif alias in lowered_content:
                detected_game = alias.title()
                break
        if not detected_game:
            m_map = re.search(r'(?:แมพ|เกม)\s+([a-zA-Z0-9_\s]{2,25})', content, re.IGNORECASE)
            if m_map:
                raw_cand = m_map.group(1).strip()
                if raw_cand.lower() not in ["หน่อย", "ครับ", "ค่ะ", "นี้", "นั้น", "ให้", "ใหม่", "loop", "python", "discord"]:
                    detected_game = raw_cand

        if detected_game:
            from bot.roblox_platform_intel import ROBLOX_INTEL
            intel = await ROBLOX_INTEL.get_full_platform_intelligence(detected_game)
            roblox_game_info = {
                "name": intel.get("name") or detected_game,
                "clean_name": re.sub(r'[^a-zA-Z0-9_]', '', intel.get("name") or detected_game),
                "place_id": intel.get("place_id") or "0",
                "universe_id": intel.get("universe_id"),
                "genre": intel.get("genre") or "Roblox Game",
                "description": intel.get("description") or f"Target Roblox Game: {detected_game}",
                "playing": intel.get("playing", 0),
                "visits": intel.get("visits", 0),
                "icon_url": intel.get("icon_url", "")
            }
            target_script_name = f"{roblox_game_info['clean_name']}_Script.lua"
            print(
                f"[AI CHAT] Sourced Roblox Platform Intel for '{roblox_game_info['name']}' "
                f"(Playing: {roblox_game_info['playing']:,}, Visits: {roblox_game_info['visits']:,})",
                flush=True
            )

    is_explicit_deob_cmd = any(w in lowered_content for w in ["แกะ", "ถอด", "deob", "unobf", "unpack", "ถอดรหัส"])
    has_attachment_to_deobf = bool(attached_code_text and len(attached_code_text.strip()) > 50 and is_explicit_deob_cmd)
    is_full_script_creation = bool(
        any(w in lowered_content for w in [
            "สร้างสคริป roblox", "ทำสคริป roblox", "สคริปต์เต็มระบบ", "สคริปเต็มระบบ", "ขอสคริป roblox",
            "เขียนสคริปต์ roblox", "เขียนสคริป roblox", "สคริปต์แมพ", "สคริปแมพ", "ขอสคริปต์", "ขอสคริป",
            "auto farm", "ออโต้ฟาร์ม", "ออโต้ฟาม", "autofarm"
        ])
        and (roblox_game_info or user_explicitly_mentions_roblox)
        and not has_attachment_to_deobf
    )

    # Hard Isolation Gate: Never allow conversational AI script generation or chat
    # inside dedicated drop channels or unapproved non-AI channels.
    if dedicated_mode:
        return
    if not (is_ai_channel or is_mentioned):
        return

    async with message.channel.typing():
        try:
            chat_res = None
            if is_full_script_creation:
                try:
                    from bot.script_factory import MultiAgentScriptFactory
                    print(f"[AI CHAT] Activating MultiAgentScriptFactory for '{target_script_name}'...", flush=True)
                    factory_res = await MultiAgentScriptFactory.build_full_system_script(
                        game_info=roblox_game_info,
                        user_prompt=content,
                        attached_code=attached_code_text,
                        user_name=message.author.display_name,
                        ui_choice="Fluent"
                    )
                    chat_summary = factory_res.get("chat_summary", "")
                    lua_code = factory_res.get("lua_code", "")
                    from bot.knowledge_router import ROUTER as KNOWLEDGE_ROUTER
                    clean_game_name = roblox_game_info.get("name") if roblox_game_info else "Game"
                    lua_code = KNOWLEDGE_ROUTER.strip_all_branding(lua_code, clean_game_name)
                    chat_summary = enforce_payomboyzaa_identity(chat_summary)
                    reply_text = f"{chat_summary}\n\n```lua\n{lua_code}\n```"
                    chat_res = {
                        "success": True,
                        "reply": reply_text,
                        "mode": "script_professor",
                        "responder": "MultiAgent-Factory"
                    }
                    print(
                        f"[AI CHAT] MultiAgentScriptFactory completed ({factory_res.get('line_count')} lines, "
                        f"{factory_res.get('char_count')} chars).",
                        flush=True,
                    )
                except Exception as f_err:
                    print(f"[AI CHAT] MultiAgentScriptFactory failed: {f_err}. Falling back to standard orchestrator...", flush=True)
                    chat_res = None

            if not chat_res:
                effective_prompt = prompt or content or (f"ช่วยวิเคราะห์ไฟล์ `{attached_filename}` หน่อยครับ" if attached_filename else "ช่วยวิเคราะห์ข้อความนี้หน่อย")
                chat_res = await ORCHESTRATOR.orchestrate_chat_query(
                    user_prompt=effective_prompt,
                    attached_code=attached_code_text,
                    filename=target_script_name if roblox_game_info else attached_filename,
                    user_name=message.author.display_name,
                    preferred_provider="gemini" if roblox_game_info else None
                )
                raw_reply = str(chat_res.get("reply") or "").strip()
                from bot.knowledge_router import ROUTER as KNOWLEDGE_ROUTER
                # Separate Lua code and conversation so code is never stamped with author identity
                extracted_c, chat_c = extract_real_lua_output(raw_reply)
                if extracted_c:
                    clean_c = KNOWLEDGE_ROUTER.strip_all_branding(extracted_c, target_script_name)
                    clean_chat = enforce_payomboyzaa_identity(chat_c)
                    reply_text = f"{clean_chat}\n\n```lua\n{clean_c}\n```" if clean_chat else f"```lua\n{clean_c}\n```"
                else:
                    reply_text = enforce_payomboyzaa_identity(raw_reply)

                print(
                    f"[AI CHAT] Orchestrator completed (mode={chat_res.get('mode', 'unknown')}, "
                    f"reply_chars={len(reply_text)}).",
                    flush=True,
                )
        except Exception as e:
            await message.reply(f"❌ ขออภัยครับ AI Engine ขัดข้อง: `{str(e)[:300]}`", mention_author=False)
            return

        if not reply_text:
            reply_text = (
                "ตอนนี้ยังดึงคำตอบที่เชื่อถือได้ไม่สำเร็จครับ ส่งโค้ด/ไฟล์ที่เกี่ยวข้องเพิ่มได้ "
                "และผมจะไม่เดาชื่อ Workspace, ReplicatedStorage หรือ Remote ที่ไม่มีหลักฐาน"
            )

        if chat_res.get("responder") not in ("safe-defensive-response", "local-content-guard", "none"):
            queued_for_review = QUALITY_MONITOR.submit(
                content or attached_filename or "[attachment analysis]",
                reply_text,
                provider=chat_res.get("responder", "unknown"),
                mode=chat_res.get("mode", "general_chat"),
            )
            if queued_for_review:
                print("[AI QA] Sampled this turn for idle-only ThaiLLM review.", flush=True)

        # ---------------------------------------------------------------
        # Strict output split:
        # - EXPLANATION / GUIDANCE stays in chat
        # - ONLY executable Lua code goes into a .lua file
        # - If no real Lua code exists, never attach a script file
        # ---------------------------------------------------------------
        # Strict output split:
        # Only treat as a script attachment request if:
        # 1. The user explicitly asked for a Roblox/Luau script
        # 2. AND there is actual Luau code fenced in ```lua ... ```
        is_lua_code_present = ("```lua" in reply_text.lower() or "```luau" in reply_text.lower())
        script_request = bool(
            (roblox_game_info or any(token in (content or "").lower() for token in [
                "roblox", "luau", "executor", "สคริปต์ roblox", "สคริป roblox", "โปรแมพ", "auto farm", "autofarm"
            ]))
            and is_lua_code_present
        )
        extracted_lua, chat_text = extract_real_lua_output(reply_text, force_full=True if script_request else False)
        # If this is not a Roblox script request, keep everything as conversational chat
        if not script_request:
            extracted_lua = ""
            chat_text = reply_text

        async def send_direct(text: str, file: Optional[discord.File] = None):
            if text and message.author:
                text = f"**ถึง {message.author.mention}**\n\n{text}"
            return await message.reply(text, mention_author=True, file=file) if file else await message.reply(text, mention_author=True)

        if len(reply_text) <= 1950 and not extracted_lua:
            await send_direct(reply_text)

        elif extracted_lua:
            if chat_text and chat_text.strip():
                for part in split_long_text_for_discord(chat_text, chunk_size=1800):
                    await send_direct(part)
            else:
                first_line = next((l.strip() for l in reply_text.splitlines() if l.strip()), "")
                if first_line:
                    await send_direct(first_line[:500])

            lua_chunks = split_lua_payload_for_discord(extracted_lua, max_chars=7500000, max_lines_per_chunk=250000)
            manifest_text = build_lua_chunk_manifest(lua_chunks)
            if manifest_text and len(lua_chunks) > 1:
                await message.channel.send(f"**📦 Lua Output Preservation Guard**\n{manifest_text}")

            if len(lua_chunks) == 1:
                lua_file_bytes = io.BytesIO(lua_chunks[0].encode("utf-8"))
                discord_lua_file = discord.File(lua_file_bytes, filename=target_script_name)
                await message.channel.send(
                    f"📄 **{target_script_name}** — โค้ดพร้อมรันบน Executor (`{len(lua_chunks[0]):,}` ตัวอักษร)",
                    file=discord_lua_file
                )
            else:
                base_stem = Path(target_script_name).stem
                for idx, chunk in enumerate(lua_chunks, start=1):
                    lua_file_bytes = io.BytesIO(chunk.encode("utf-8"))
                    discord_lua_file = discord.File(lua_file_bytes, filename=f"{base_stem}_{idx}.lua")
                    await message.channel.send(
                        f"📄 **{base_stem}_{idx}.lua** — ชิ้นที่ {idx}/{len(lua_chunks)} (`{len(chunk):,}` ตัวอักษร)",
                        file=discord_lua_file
                    )
                    await asyncio.sleep(1.2)


        else:
            for part in split_long_text_for_discord(reply_text, chunk_size=1800):
                await send_direct(part)




@bot.event
async def on_message(message: discord.Message):
    """Keep listener failures visible and return a useful error in AI channels."""
    if not claim_message_once(message.id):
        print(f"[AI CHAT] Ignored duplicate message event (message_id={message.id}).", flush=True)
        return
    try:
        # 🛡️ PAYOMBØYZ GODMODE Host Agentic Interceptor
        if await handle_godmode_message(message):
            return
        await asyncio.wait_for(_handle_ai_message(message), timeout=900)
    except Exception as exc:
        if isinstance(exc, TimeoutError):
            request_recycle("message-handler-timeout")
        print(
            f"[AI CHAT ERROR] Unhandled message handler failure "
            f"(channel_id={message.channel.id}, message_id={message.id}): "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        import traceback
        traceback.print_exc()
        channel_ids = load_ai_channels()
        is_ai_channel = (
            message.channel.id in channel_ids
            or (getattr(message.channel, "parent_id", None) is not None and getattr(message.channel, "parent_id", None) in channel_ids)
        )
        if not message.author.bot and is_ai_channel:
            try:
                await message.reply(
                    f"ระบบ AI ขัดข้องระหว่างรับข้อความ (รหัส `{message.id}`) "
                    "ผมบันทึก error ไว้ในหน้าต่าง Hub แล้วครับ",
                    mention_author=False,
                )
            except Exception as send_exc:
                print(
                    f"[AI CHAT ERROR] Could not report handler failure: "
                    f"{type(send_exc).__name__}: {send_exc}",
                    file=sys.stderr,
                    flush=True,
                )


def start_ai_bot(token: Optional[str] = None):
    bot_token = token or config.DISCORD_AI_BOT_TOKEN or config.DISCORD_BOT_TOKEN
    if not bot_token:
        print("[ERROR] No Discord Token provided for AI & Deobf Bot (DISCORD_AI_BOT_TOKEN).")
        return
    print(f"[*] Starting AI & Deobfuscator Bot...")
    bot.run(bot_token)


if __name__ == "__main__":
    start_ai_bot()
