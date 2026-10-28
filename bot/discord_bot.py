import asyncio
import io
import os
import sys
import time
from pathlib import Path
from typing import Optional
import socket

_instance_socket = None

def check_single_instance(port: int = 49280) -> bool:
    global _instance_socket
    try:
        _instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _instance_socket.bind(("127.0.0.1", port))
        _instance_socket.listen(1)
        return True
    except OSError:
        return False

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import discord
from discord import app_commands
from discord.ext import commands

# Set up engine paths
BASE_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = BASE_DIR / "Prometheus-WeAre-Devs-Dumper-main"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

import config
import engine_router
import deobfuscator
from . import panel
from . import security

intents = discord.Intents.default()
# Default intents allow slash commands, attachments, buttons, and interactions out of the box without requiring developer portal privilege.
bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents, help_command=None)

PROJECT_NAME = "⚡ PAYOMBØYZ DEØBFUSCATE"


def save_temp_input(content_bytes: bytes, filename: str) -> Path:
    safe_name = security.sanitize_filename(filename)
    stem = Path(safe_name).stem
    ext = Path(safe_name).suffix or ".lua"
    temp_target = config.OUTPUT_DIR / f"{stem}_{int(time.time() * 1000)}{ext}"
    with open(temp_target, "wb") as f:
        f.write(content_bytes)
    return temp_target


def build_result_embed(res: dict, input_name: str) -> tuple[discord.Embed, list[discord.File]]:
    elapsed = res.get("elapsed", 0.0)
    engine_name = res.get("engine", "Unknown Engine")
    safe_input_name = security.sanitize_filename(input_name)
    files = []

    if not res.get("success"):
        err = res.get("error", "Unknown error")
        safe_err = security.sanitize_output_text(str(err), config.DISCORD_BOT_TOKEN)
        embed = discord.Embed(
            title=f"{PROJECT_NAME} | ❌ ล้มเหลว",
            description=f"ไม่สามารถถอดรหัสไฟล์ `{safe_input_name}` ได้\n\n"
                        f"**เครื่องมือที่ใช้:** `{engine_name}`\n"
                        f"**สาเหตุ:** ```\n{safe_err[:800]}\n```\n"
                        f"💡 *คำแนะนำ: ลองเลือกเครื่องมืออื่น เช่น 🌙 Moonveil 2.0.2+, 🛠️ WeAreDevs, 🔒 Luraph หรือ 🌙 MoonSec/IronBrew หรือกด ⚡ Auto-Detect*",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"PAYOMBØYZ DEØBFUSCATE | ใช้เวลา {elapsed:.2f} วินาที")
        return embed, files

    urls = res.get("urls", [])
    loadstrings = res.get("loadstrings", [])
    trace_count = res.get("trace_count", 0)
    code = res.get("deobfuscated_code", "")
    line_count = res.get("lines", 0) or len(code.splitlines())

    embed = discord.Embed(
        title=f"{PROJECT_NAME} | ✅ สำเร็จ",
        description=f"ถอดรหัสสคริปต์ `{input_name}` เรียบร้อยแล้ว โค้ดได้รับการปรับปรุงโครงสร้างให้พร้อมใช้งาน",
        color=discord.Color.green()
    )

    embed.add_field(name="⚙️ เครื่องมือที่ใช้", value=f"`{engine_name}`", inline=True)
    embed.add_field(name="⏱️ เวลาประมวลผล", value=f"`{elapsed:.2f} วินาที`", inline=True)
    embed.add_field(name="📊 บรรทัดที่กู้คืนได้", value=f"`{line_count:,} บรรทัด`", inline=True)

    if trace_count:
        embed.add_field(name="🔍 Traced Ops", value=f"`{trace_count:,} operations`", inline=True)

    if urls:
        url_text = "\n".join(f"• `{u}`" for u in urls[:5])
        if len(urls) > 5:
            url_text += f"\n... และอีก {len(urls) - 5} รายการ"
        embed.add_field(name="🌐 ตรวจพบ Webhook / URLs", value=url_text, inline=False)

    if loadstrings:
        embed.add_field(
            name="⚠️ โค้ดโหลดแบบไดนามิก (loadstring)",
            value=f"พบการเรียกใช้งาน dynamic code {len(loadstrings)} จุด",
            inline=False
        )

    embed.set_footer(text="PAYOMBØYZ DEØBFUSCATE Engine v2.0 | Offline Local Emulation")

    # Add deobfuscated file attachment (.lua)
    deobf_path = res.get("deobf_path")
    if deobf_path and os.path.exists(deobf_path):
        files.append(discord.File(deobf_path, filename=f"{Path(input_name).stem}_deobf.lua"))
    elif code:
        buf = io.BytesIO(code.encode("utf-8"))
        files.append(discord.File(buf, filename=f"{Path(input_name).stem}_deobf.lua"))

    # Add raw luac file if present (MoonSec / IronBrew bytecode)
    luac_path = res.get("luac_path")
    if luac_path and os.path.exists(luac_path):
        files.append(discord.File(luac_path, filename=f"{Path(input_name).stem}_dump.luac"))

    # Add execution report attachment if present (Tool 1)
    report_path = res.get("report_path")
    if report_path and os.path.exists(report_path):
        files.append(discord.File(report_path, filename=f"{Path(input_name).stem}_report.txt"))

    return embed, files


class EngineSelectionView(discord.ui.View):
    def __init__(self, temp_filepath: Path, original_filename: str, user_id: int):
        super().__init__(timeout=300)
        self.temp_filepath = temp_filepath
        self.original_filename = original_filename
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ คุณไม่ใช่ผู้ส่งคำขอนี้", ephemeral=True)
            return False
        return True

    async def execute_deobfuscation(self, interaction: discord.Interaction, engine_choice: str, engine_title: str):
        # Disable buttons and acknowledge interaction immediately in one call
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=f"⏳ **[{PROJECT_NAME}]** กำลังแกะสคริปต์ด้วย **{engine_title}**... โปรดรอสักครู่",
            view=self
        )

        # ---------------------------------------------------------
        # 🛡️ SECURITY AUDITOR: Audit script signatures, proceed safely in sandbox
        # ---------------------------------------------------------
        try:
            with open(self.temp_filepath, "r", encoding="utf-8", errors="ignore") as f:
                raw_code = f.read(500000)
            is_safe, threat_desc = security.scan_script_safety(raw_code)
            if not is_safe:
                print(f"[SECURITY AUDIT] Suspicious payload signature flagged in {self.original_filename}: {threat_desc}", flush=True)
        except Exception:
            pass

        res = await asyncio.to_thread(
            engine_router.deobfuscate,
            str(self.temp_filepath),
            engine_choice=engine_choice,
            timeout=60
        )

        embed, files = build_result_embed(res, self.original_filename)

        if files:
            await interaction.followup.send(embed=embed, files=files)
        else:
            await interaction.followup.send(embed=embed)

    @discord.ui.button(label="⚡ Auto-Detect (แนะนำ - ตรวจจับอัตโนมัติ)", style=discord.ButtonStyle.success, emoji="⚡", row=0)
    async def btn_auto(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_deobfuscation(interaction, "auto", "Auto-Detect")

    @discord.ui.button(label="1. WeAreDevs (Prometheus)", style=discord.ButtonStyle.primary, emoji="🛠️", row=1)
    async def btn_wearedevs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_deobfuscation(interaction, "1", "1. WeAreDevs (Prometheus)")

    @discord.ui.button(label="2. IronBrew & MoonSec", style=discord.ButtonStyle.primary, emoji="☕", row=1)
    async def btn_ironbrew(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_deobfuscation(interaction, "2", "2. IronBrew & MoonSec")

    @discord.ui.button(label="3. Luraph v14 (Classic)", style=discord.ButtonStyle.primary, emoji="🔒", row=2)
    async def btn_luraph(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_deobfuscation(interaction, "3", "3. Luraph v14 (Classic & Buffer)")

    @discord.ui.button(label="4. Moonveil 2.0.2+", style=discord.ButtonStyle.primary, emoji="🌙", row=2)
    async def btn_moonveil(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_deobfuscation(interaction, "4", "4. Moonveil 2.0.2+")

    @discord.ui.button(label="5. 2K Security & XOR Loader", style=discord.ButtonStyle.primary, emoji="🛡️", row=3)
    async def btn_twok(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_deobfuscation(interaction, "5", "5. 2K Security & XOR Loader")

    @discord.ui.button(label="8. Luraph v15.1 (Universal Industrial Pipeline)", style=discord.ButtonStyle.primary, emoji="⚡", row=3)
    async def btn_luraph_v15(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_deobfuscation(interaction, "8", "8. Luraph v15.1 (Universal Industrial Pipeline)")

    @discord.ui.button(label="9. MoonSec V2 / V3", style=discord.ButtonStyle.secondary, emoji="🌙", row=4)
    async def btn_moonsec_v5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_deobfuscation(interaction, "9", "9. MoonSec V2 / V3 (Unicode Stego VM Devirtualizer)")

@bot.event
async def on_ready():
    print("==================================================", flush=True)
    print(f"  🤖 {PROJECT_NAME} Online!", flush=True)
    print(f"  👤 Logged in as: {bot.user} (ID: {bot.user.id})", flush=True)
    print(f"  ⚙️  Prefix: {config.COMMAND_PREFIX}", flush=True)
    print(f"  📦 Engines: WeAreDevs | Luraph v14/v15 | MoonSec/IronBrew | Moonveil | MoonSec V2 / V3", flush=True)
    print("==================================================", flush=True)

    print(f"  🏰 Connected Guilds: {len(bot.guilds)}", flush=True)
    invite_url = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
    print(f"  🔗 ลิงก์เชิญบอทเข้า Discord: {invite_url}", flush=True)
    if len(bot.guilds) == 0:
        print("\n  ⚠️⚠️⚠️ [สำคัญมาก] บอทยังไม่ได้อยู่ในเซิร์ฟเวอร์ใดๆ เลย (Connected Guilds: 0)!", flush=True)
        print("  👉 กรุณาคัดลอกลิงก์ด้านบนไปเปิดในเบราว์เซอร์เพื่อเชิญบอทเข้าเซิร์ฟเวอร์ก่อน!", flush=True)
        print("  👉 หากไม่เชิญบอทเข้าเซิร์ฟเวอร์ บอทจะไม่สามารถส่งข้อความ หรือแจก Role ได้\n", flush=True)
    print("==================================================", flush=True)

    # Register all persistent views so buttons work across restarts
    panel.register_all_panel_views(bot)

    # 1. Sync slash commands directly to each connected Guild for INSTANT availability (0 delay)
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            synced_guild = await bot.tree.sync(guild=guild)
            print(f"  [+] Synced {len(synced_guild)} slash commands INSTANTLY to Guild: {guild.name} ({guild.id})", flush=True)
        except Exception as ge:
            print(f"  [-] Guild sync failed for {guild.id}: {ge}", flush=True)

    # 2. Also sync globally
    try:
        synced_global = await bot.tree.sync()
        print(f"  [+] Synced {len(synced_global)} global slash commands.", flush=True)
    except Exception as e:
        print(f"  [-] Global sync failed: {e}", flush=True)


# =========================================================================
# 🔒 ERROR HANDLER & PERMISSION CONTROLS
# =========================================================================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """ดักจับ Error ของ Slash Command เพื่อไม่ให้ขึ้น 'แอปพลิเคชันไม่ตอบสนอง'"""
    if isinstance(error, app_commands.CheckFailure):
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ **คุณไม่มีสิทธิ์ออกคำสั่งนี้!**\n"
                "คำสั่งนี้จำกัดสิทธิ์เฉพาะผู้ที่มีบทบาทต่อไปนี้เท่านั้น:\n"
                f"• 🤖 **Bot Role:** `<@&{panel.BOT_ROLE_ID}>`\n"
                f"• 👑 **Admin Role:** `<@&{panel.ADMIN_ROLE_ID}>`",
                ephemeral=True
            )
        return

    print(f"[-] Slash command error: {error}", flush=True)
    err_text = f"❌ เกิดข้อผิดพลาดในการประมวลผลคำสั่ง: {error}"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(err_text, ephemeral=True)
        else:
            await interaction.response.send_message(err_text, ephemeral=True)
    except Exception:
        pass





# --- Slash Commands ---

@bot.tree.command(name="ping", description="ตรวจสอบสถานะการทำงานและ Latency ของระบบ")
async def ping_slash(interaction: discord.Interaction):
    lua_bin = deobfuscator.get_lua_executable()
    lua_ok = os.path.exists(lua_bin)
    embed = discord.Embed(
        title=f"{PROJECT_NAME} | 🏓 Pong!",
        description=f"**Bot Latency:** `{round(bot.latency * 1000)}ms`\n"
                    f"**Local Lua JIT Sandbox:** `{'พร้อมใช้งาน' if lua_ok else 'ไม่พบไฟล์ Runtime'}`\n"
                    f"**Luraph Engine (Java):** `พร้อมใช้งาน`\n"
                    f"**MoonSec/IronBrew Engine (Node.js):** `พร้อมใช้งาน`\n\n"
                    f"🟢 ระบบพร้อมประมวลผลคำขอถอดรหัสสคริปต์ทุกรูปแบบ",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="help", description="แสดงคำแนะนำและวิธีใช้งาน PAYOMBØYZ DEØBFUSCATE")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"📖 {PROJECT_NAME} - คู่มือการใช้งาน",
        description="ระบบถอดรหัสสคริปต์ Roblox Lua/Luau ออฟไลน์ ทำงานแบบ Multi-Engine รองรับค่ายยอดนิยมอย่างสมบูรณ์",
        color=discord.Color.purple()
    )
    embed.add_field(
        name="เครื่องมือที่มีให้เลือก (5 เครื่องมือ)",
        value="**1. 🛠️ WeAreDevs (Prometheus)** - Emulation Sandbox & AST Dumper\n"
              "**2. ☕ IronBrew & MoonSec** - AST Devirtualizer + Constant Dumper + Dynamic Tracer\n"
              "**3. 🔒 Luraph (Old)** - Java ANTLR Static Devirtualizer\n"
              "**4. 🌙 Moonveil 2.0.2+** - Luau VM Trace Emulation & Reconstructor\n"
              "**5. 🛡️ 2K Security & Loaders** - Static XOR Solver + Dynamic Lupa Interceptor\n"
              "**⚡ Auto-Detect** - ระบบวิเคราะห์ Signature ตรวจจับอัตโนมัติ",
        inline=False
    )
    embed.add_field(
        name="วิธีใช้งาน (2 รูปแบบ)",
        value=f"1. **อัปโหลดไฟล์พร้อมปุ่มเลือกเครื่องมือ:**\n"
              f"   แนบไฟล์ `.lua`, `.luau` หรือ `.txt` แล้วพิมพ์ `{config.COMMAND_PREFIX}deobf`\n"
              f"   จากนั้นกดเลือกเครื่องมือที่ต้องการผ่านปุ่มในดิสคอร์ด\n\n"
              f"2. **Slash Command:**\n"
              f"   ใช้คำสั่ง `/deobfuscate` แล้วแนบไฟล์ และเลือก Engine ได้ทันที",
        inline=False
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="deobfuscate", description="ถอดรหัสสคริปต์ Lua/Luau ด้วย PAYOMBØYZ DEØBFUSCATE")
@app_commands.describe(
    file="แนบไฟล์สคริปต์ .lua, .luau หรือ .txt",
    engine="เลือกเครื่องมือ deobfuscator (หรือเว้นว่างเพื่อเลือกผ่านปุ่ม)",
    code="หรือวางโค้ดที่ถูกเข้ารหัสโดยตรง"
)
@app_commands.choices(engine=[
    app_commands.Choice(name="⚡ Auto-Detect (ตรวจจับอัตโนมัติ)", value="auto"),
    app_commands.Choice(name="🛠️ 1. WeAreDevs (Prometheus)", value="1"),
    app_commands.Choice(name="☕ 2. IronBrew & MoonSec", value="2"),
    app_commands.Choice(name="🔒 3. Luraph v14 (Classic & Buffer VM)", value="3"),
    app_commands.Choice(name="🌙 4. Moonveil 2.0.2+", value="4"),
    app_commands.Choice(name="🛡️ 5. 2K Security & XOR Loader", value="5"),
    app_commands.Choice(name="⚡ 8. Luraph v15 (Advanced Node CFG Dominator)", value="8"),
    app_commands.Choice(name="🌙 9. MoonSec V2 / V3 (Unicode Stego Devirt)", value="9"),
])
async def deobfuscate_slash(
    interaction: discord.Interaction,
    file: Optional[discord.Attachment] = None,
    engine: Optional[app_commands.Choice[str]] = None,
    code: Optional[str] = None
):
    # DEFER IMMEDIATELY so Discord never times out!
    await interaction.response.defer()

    content_bytes = None
    input_name = "script.lua"

    if file:
        input_name = file.filename
        if file.size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
            await interaction.followup.send(f"❌ ขนาดไฟล์เกินกำหนด (สูงสุด {config.MAX_FILE_SIZE_MB}MB)")
            return
        try:
            content_bytes = await file.read()
        except Exception as e:
            await interaction.followup.send(f"❌ ไม่สามารถอ่านไฟล์ที่แนบได้: {e}")
            return
    elif code:
        clean_code = code.strip()
        if clean_code.startswith("```lua") or clean_code.startswith("```"):
            lines = clean_code.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            clean_code = "\n".join(lines)
        content_bytes = clean_code.encode("utf-8")
        input_name = "pasted_script.lua"
    else:
        await interaction.followup.send("❌ กรุณาแนบไฟล์สคริปต์ หรือวางโค้ดในช่อง code")
        return

    # ---------------------------------------------------------
    # 🛡️ BRAND PROTECTION GUARD: Refuse deobfuscating our own studio scripts
    # ---------------------------------------------------------
    from bot.brand_protection import check_brand_protection, BRAND_REFUSAL_MESSAGE
    is_protected, matched_term = check_brand_protection(content_bytes)
    if is_protected or any(m in input_name.casefold() for m in ["payomboy", "payomboyz", "payombøyz", "พยอมบอย"]):
        await interaction.followup.send(BRAND_REFUSAL_MESSAGE)
        return

    # ---------------------------------------------------------
    # 🛡️ SECURITY AUDITOR: Audit script signatures, proceed safely in sandbox
    # ---------------------------------------------------------
    is_safe, threat_desc = security.scan_script_safety(content_bytes.decode("utf-8", errors="ignore"))
    if not is_safe:
        print(f"[SECURITY AUDIT] Suspicious payload signature flagged in {input_name}: {threat_desc}", flush=True)

    # Save temporary file
    temp_path = save_temp_input(content_bytes, input_name)
    engine_choice = engine.value if engine else None

    # If engine specified via slash choice, run directly
    if engine_choice:
        display_choice = engine.name if engine else "Auto"
        msg = await interaction.followup.send(
            f"⏳ **[{PROJECT_NAME}]** กำลังแกะสคริปต์ `{input_name}` ด้วย **{display_choice}**... โปรดรอสักครู่"
        )
        res = await asyncio.to_thread(
            engine_router.deobfuscate,
            str(temp_path),
            engine_choice=engine_choice,
            timeout=60
        )
        embed, files = build_result_embed(res, input_name)
        if files:
            await interaction.followup.send(embed=embed, files=files)
        else:
            await interaction.followup.send(embed=embed)
        return

    # If engine not specified, show interactive buttons!
    try:
        code_preview = content_bytes.decode("utf-8", errors="replace")[:1500]
        suggested = engine_router.detect_engine_type(code_preview)
        suggested_name = engine_router.ENGINE_NAMES.get(suggested, "WeAreDevs (Prometheus)")
    except:
        suggested_name = "Auto-Detect"

    embed = discord.Embed(
        title=f"{PROJECT_NAME}",
        description=f"📄 **ไฟล์:** `{input_name}`\n"
                    f"📦 **ขนาด:** `{len(content_bytes) / 1024:.2f} KB`\n"
                    f"🔍 **แนะนำเบื้องต้น:** `{suggested_name}`\n\n"
                    f"👉 **โปรดคลิกเลือกเครื่องมือที่ต้องการใช้ถอดรหัสด้านล่าง:**",
        color=discord.Color.blurple()
    )
    view = EngineSelectionView(temp_path, input_name, interaction.user.id)
    await interaction.followup.send(embed=embed, view=view)


# --- Prefix Commands (e.g. !deobf with attachment) ---

@bot.command(name="deobf")
async def deobf_prefix(ctx: commands.Context, *, code: Optional[str] = None):
    content_bytes = None
    input_name = "script.lua"

    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        input_name = attachment.filename
        if attachment.size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
            await ctx.send(f"❌ ขนาดไฟล์เกินกำหนด (สูงสุด {config.MAX_FILE_SIZE_MB}MB)")
            return
        content_bytes = await attachment.read()
    elif code:
        clean_code = code.strip()
        if clean_code.startswith("```lua") or clean_code.startswith("```"):
            lines = clean_code.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            clean_code = "\n".join(lines)
        content_bytes = clean_code.encode("utf-8")
        input_name = "pasted_script.lua"
    else:
        await ctx.send(f"❌ กรุณาแนบไฟล์สคริปต์ เช่น พิมพ์ `{config.COMMAND_PREFIX}deobf` พร้อมแนบไฟล์")
        return

    # ---------------------------------------------------------
    # 🛡️ BRAND PROTECTION GUARD: Refuse deobfuscating our own studio scripts
    # ---------------------------------------------------------
    from bot.brand_protection import check_brand_protection, BRAND_REFUSAL_MESSAGE
    is_protected, matched_term = check_brand_protection(content_bytes)
    if is_protected or any(m in input_name.casefold() for m in ["payomboy", "payomboyz", "payombøyz", "พยอมบอย"]):
        await ctx.send(BRAND_REFUSAL_MESSAGE)
        return

    # ---------------------------------------------------------
    # 🛡️ SECURITY AUDITOR: Audit script signatures, proceed safely in sandbox
    # ---------------------------------------------------------
    is_safe, threat_desc = security.scan_script_safety(content_bytes.decode("utf-8", errors="ignore"))
    if not is_safe:
        print(f"[SECURITY AUDIT] Suspicious payload signature flagged in {input_name}: {threat_desc}", flush=True)

    temp_path = save_temp_input(content_bytes, input_name)
    try:
        code_preview = content_bytes.decode("utf-8", errors="replace")[:1500]
        suggested = engine_router.detect_engine_type(code_preview)
        suggested_name = engine_router.ENGINE_NAMES.get(suggested, "WeAreDevs (Prometheus)")
    except:
        suggested_name = "Auto-Detect"

    embed = discord.Embed(
        title=f"{PROJECT_NAME}",
        description=f"📄 **ไฟล์:** `{input_name}`\n"
                    f"📦 **ขนาด:** `{len(content_bytes) / 1024:.2f} KB`\n"
                    f"🔍 **แนะนำเบื้องต้น:** `{suggested_name}`\n\n"
                    f"👉 **โปรดคลิกเลือกเครื่องมือที่ต้องการใช้ถอดรหัสด้านล่าง:**",
        color=discord.Color.blurple()
    )
    view = EngineSelectionView(temp_path, input_name, ctx.author.id)
    await ctx.send(embed=embed, view=view)


@bot.command(name="ping")
async def ping_prefix(ctx: commands.Context):
    await ping_slash.callback(ctx)


def start_bot(token: Optional[str] = None):
    if not check_single_instance():
        print("\n" + "=" * 65, flush=True)
        print("  ⚠️  [แจ้งเตือนสำคัญ] ตรวจพบว่ามีบอทอีกหน้าต่างกำลังทำงานอยู่แล้ว!", flush=True)
        print("  ⚠️  ห้ามเปิดรันบอท 2 หน้าต่างพร้อมกันโดยเด็ดขาด!", flush=True)
        print("      เพราะทั้งสองหน้าต่างจะแย่ง Token เดียวกัน ทำให้ Discord สับสน", flush=True)
        print("      และคำสั่งใน Discord จะค้างขึ้น 'แอปพลิเคชันไม่ตอบสนอง'", flush=True)
        print("  👉  กรุณาปิดหน้าต่างนี้ แล้วใช้เพียงหน้าต่างเดียวเท่านั้น", flush=True)
        print("=" * 65 + "\n", flush=True)
        input("กด Enter เพื่อปิดหน้าต่างนี้...")
        sys.exit(1)

    bot_token = token or config.DISCORD_BOT_TOKEN
    if not bot_token:
        print("[ERROR] Discord Bot Token not configured!")
        print("Please set DISCORD_BOT_TOKEN in .env or run with: python main.py --token <YOUR_TOKEN>")
        sys.exit(1)
    bot.run(bot_token)
