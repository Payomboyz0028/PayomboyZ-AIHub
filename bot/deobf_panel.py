#!/usr/bin/env python3

"""

=============================================================================

  PAYOMBOYZ DEOBFUSCATOR & OBFUSCATOR INTERACTIVE DISCORD PANEL V10.0

  Fully Persistent Discord UI with Dropdowns, File Attachment, Status Check,

  DeepSeek/Gemini Human-Readable Cleanup Pipeline, Log Channel Support

=============================================================================

"""



import io

import os

import json

import time

import re
import re as _re

from pathlib import Path

from typing import Optional, Dict, Any, Tuple, List, Set, Callable



import discord

from discord import app_commands



BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "deobf_panels_config.json"
DEDICATED_CHANNELS_FILE = BASE_DIR / "dedicated_channels_config.json"

def load_dedicated_channels() -> dict:
    if not DEDICATED_CHANNELS_FILE.exists():
        return {}
    try:
        with open(DEDICATED_CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_dedicated_channel(channel_id: int, mode: str, guild_id: Optional[int] = None):
    data = load_dedicated_channels()
    data[str(channel_id)] = {
        "mode": mode,
        "guild_id": guild_id,
        "updated_at": time.time()
    }
    with open(DEDICATED_CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def remove_dedicated_channel(channel_id: int) -> bool:
    data = load_dedicated_channels()
    k = str(channel_id)
    if k in data:
        del data[k]
        with open(DEDICATED_CHANNELS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    return False

def get_dedicated_channel_mode(channel_id: int) -> Optional[str]:
    data = load_dedicated_channels()
    entry = data.get(str(channel_id))
    return entry.get("mode") if entry else None

def build_compact_guide_embed(mode: str = "deobfuscate") -> discord.Embed:
    """
    Creates the ultra-compact, sleek guide embed matching image.png (emerald/teal border).
    No buttons attached. Pinned to the bottom of the chat.
    """
    color = discord.Color.from_rgb(0, 229, 163)  # Emerald / Teal green matching image.png
    if mode in ("obfuscate", "obf"):
        embed = discord.Embed(
            title="🎮 Script Obfuscator — VM & CFF Engine",
            description="อัปโหลดไฟล์สคริปต์ (.lua / .luau / .txt) ➔ ป้องกันสคริปต์ด้วย Clyde VM + CFF ทันที (Public)",
            color=color
        )
    else:
        embed = discord.Embed(
            title="🎮 Script Deobfuscator — Universal Engine",
            description="อัปโหลดไฟล์สคริปต์ (.lua / .luau / .txt) ➔ ถอดรหัสคืนซอร์สโค้ดสะอาด 100% ทันที (Public)",
            color=color
        )
    return embed

async def post_pinned_guide(channel: discord.abc.Messageable, mode: str = "deobfuscate"):
    """Sends the compact guide embed and removes previous guide message so it is always at the bottom."""
    try:
        data = load_dedicated_channels()
        ch_key = str(getattr(channel, "id", 0))
        entry = data.get(ch_key, {})
        old_msg_id = entry.get("last_guide_id")
        if old_msg_id and hasattr(channel, "fetch_message"):
            try:
                old_msg = await channel.fetch_message(old_msg_id)
                if old_msg:
                    await old_msg.delete()
            except Exception:
                pass

        embed = build_compact_guide_embed(mode)
        view = DeobfResultActionView() if mode not in ("obfuscate", "obf") else None
        new_msg = await channel.send(embed=embed, view=view)
        if ch_key in data:
            data[ch_key]["last_guide_id"] = new_msg.id
            with open(DEDICATED_CHANNELS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[PINNED GUIDE ERROR] Could not post guide embed to channel: {e}", flush=True)

DEFAULT_PANEL_TITLE = "⚡ PAYOMBØYZ MULTI-ENGINE DEOBFUSCATOR & VIRTUALIZER"

DEFAULT_BANNER_URL = "https://raw.githubusercontent.com/PayomboyZ/Assets/main/banner.png"

DEFAULT_THUMBNAIL_URL = "https://raw.githubusercontent.com/PayomboyZ/Assets/main/avatar.png"



MODAL_CODE_MAX = 4000  # Discord modal hard limit



COLOR_MAP = {

    "crimson": discord.Color.from_rgb(220, 20, 60),

    "red": discord.Color.red(),

    "emerald": discord.Color.from_rgb(46, 204, 113),

    "green": discord.Color.green(),

    "cyan": discord.Color.from_rgb(0, 220, 255),

    "blue": discord.Color.blue(),

    "blurple": discord.Color.blurple(),

    "purple": discord.Color.purple(),

    "gold": discord.Color.gold(),

    "yellow": discord.Color.yellow(),

    "dark": discord.Color.from_rgb(20, 20, 25),

}



# Engine choices — deobfuscate (label, value)
DEOBF_ENGINES = [
    ("⚙️ Auto-Detect (วิเคราะห์อัตโนมัติ)", "auto"),
    ("🌙 MoonVeil V2+ (VM AST Dumper)", "moonveil"),
    ("🛠️ WeAreDevs / Prometheus (AST Dumper)", "wearedevs"),
    ("🛡️ Clyde Protection (Luau VM Devirt)", "clyde"),
    ("🌙 MoonSec V2 / V3 (Opcode Remapper)", "moonsec"),
    ("☕ IronBrew 2 / AztupBrew (Bytecode Lifter)", "ironbrew"),
    ("🧩 LuaObfuscator (Constant & Dead-Code Slicer)", "luaobfuscator"),
    ("🔮 Mercury v2/v3 (Zero-Day Static Dispatch)", "mercury"),
    ("🔬 Onyx-Zero (Dynamic Opcode Fingerprint)", "onyx_zero"),
    ("⚛️ Neutron 0.2.5 (PVM1 Static Decryptor)", "neutron"),
    ("🌪️ Luraph v14 / v15 / v15.1 (Universal Devirt)", "luraph"),
    ("🛡️ 2K Security & XOR Solver", "twok"),
]

# Engine choices — obfuscate (label, value)
OBF_ENGINES = [
    ("🟢 Level 1: Fast VM (Prometheus High Speed / 60 FPS)", "level1"),
    ("🟡 Level 2: Balanced Security (Prometheus Luau VM - แนะนำ)", "level2"),
    ("🔴 Level 3: Maximum Armor (Prometheus Multi-Layer Double-VM + 7-Shield Armor)", "level3"),
    ("⚡ Level 4: Prometheus Multi-Tier VM (Instruction Virtualizer)", "level4"),
    ("🛡️ Level 5: Sentinel Multi-Layer Double-VM (Dual-State CFF + Anti-Hook/Spy)", "level5"),
]



# =============================================================================

# COLOR HELPERS

# =============================================================================

def parse_panel_color(col: Optional[str]) -> discord.Color:

    if not col:

        return COLOR_MAP["cyan"]

    val = col.strip().lower()

    if val in COLOR_MAP:

        return COLOR_MAP[val]

    cleaned = val.lstrip("#").replace("0x", "")

    try:

        if len(cleaned) == 6:

            r = int(cleaned[0:2], 16)

            g = int(cleaned[2:4], 16)

            b = int(cleaned[4:6], 16)

            return discord.Color.from_rgb(r, g, b)

    except Exception:

        pass

    return COLOR_MAP["cyan"]





# =============================================================================

# CONFIG STORAGE

# =============================================================================

def load_deobf_panels() -> Dict[str, Any]:

    if not CONFIG_FILE.exists():

        return {}

    try:

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:

            return json.load(f)

    except Exception:

        return {}





def save_deobf_panel(panel_id: str, data: dict):

    panels = load_deobf_panels()

    panels[panel_id] = data

    try:

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:

            json.dump(panels, f, indent=2, ensure_ascii=False)

    except Exception as e:

        print(f"[-] Failed to save deobf panel config: {e}", flush=True)





def delete_deobf_panel(panel_id: str):

    panels = load_deobf_panels()

    if panel_id in panels:

        del panels[panel_id]

        try:

            with open(CONFIG_FILE, "w", encoding="utf-8") as f:

                json.dump(panels, f, indent=2, ensure_ascii=False)

        except Exception:

            pass





DEFAULT_DEOBF_LOG_CHANNEL_ID = 1555411076248506448





def get_log_channel_id(guild_id: Optional[int] = None) -> Optional[int]:

    """Return the configured log channel id for a guild, falling back to default."""

    if guild_id:

        panels = load_deobf_panels()

        for pdata in panels.values():

            if pdata.get("guild_id") == guild_id and pdata.get("log_channel_id"):

                return int(pdata["log_channel_id"])

    return DEFAULT_DEOBF_LOG_CHANNEL_ID





async def dispatch_result_to_channel_or_interaction(

    interaction: discord.Interaction,

    embed: discord.Embed,

    files: list[discord.File],

    action_type: str,

    filename: str,

    guild_id: Optional[int] = None,

    is_success: Optional[bool] = None

):

    """

    Deliver the output file and embed to the designated log channel (1555411076248506448).

    In the command room, send a clean ephemeral notification with a jump link so the room stays pristine.

    Accurately reflects success or failure based on the result.

    """

    if is_success is None:

        is_fail = (embed.color in (discord.Color.red(), discord.Color.gold())) or (bool(embed.title) and any(m in embed.title for m in ("❌", "⚠️", "Syntax Error")))

        is_success = not is_fail



    target_log_id = get_log_channel_id(guild_id or getattr(interaction, "guild_id", None))

    log_ch = None

    if target_log_id:

        from bot.ai_deobf_bot import bot as _bot_inst

        try:

            log_ch = _bot_inst.get_channel(target_log_id) or await _bot_inst.fetch_channel(target_log_id)

        except Exception:

            log_ch = None



    # Clone files so both the user and the audit log channel receive real attachments
    user_files = []
    log_files = []
    if files:
        for f in files:
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

    # 1. ALWAYS deliver directly to the user who requested it!
    delivered = False
    action_view = DeobfResultActionView() if action_type == "DEOBFUSCATE" else None
    try:
        await interaction.followup.send(embed=embed, files=user_files, view=action_view, ephemeral=True)
        delivered = True
    except Exception:
        try:
            await interaction.followup.send(embed=embed, files=user_files, view=action_view)
            delivered = True
        except Exception as e:
            print(f"[PANEL DISPATCH] Followup delivery fallback: {e}", flush=True)

    # 2. Mirror a copy to designated log channel if available
    if log_ch and log_ch.id != interaction.channel_id:
        user_mention = interaction.user.mention if hasattr(interaction, "user") else "ผู้ใช้"
        icon = "🔔" if action_type == "DEOBFUSCATE" else "🔒"
        try:
            await log_ch.send(
                content=f"{icon} **[{action_type} LOG]** ผลลัพธ์สำหรับ {user_mention} | ไฟล์: `{filename}`",
                embed=embed,
                files=log_files
            )
        except Exception as log_err:
            print(f"[PANEL DISPATCH] Log channel mirror skip: {log_err}", flush=True)





DEFAULT_PANEL_DESCRIPTION = (

    "**ระบบถอดรหัส (Deobfuscator) และป้องกันสคริปต์ (Obfuscator) ระดับพรีเมียม**\n"

    "รองรับทุก Architecture ของ Lua / Luau (Roblox) ด้วย Multi-Engine Pipeline\n"

    "──────────────────────────────────────────────\n"

    "**🔓 เอนจินถอดรหัส (Deobfuscator Engines v9.0)**\n"

    "• ⚙️ Auto-Detect: วิเคราะห์ลายเซ็น VM, Opcode, และ Bytecode อัตโนมัติ\n"

    "• 🛠️ WeAreDevs (Prometheus)\n"

    "• 🌙 Moonveil 2.0.2+\n"

    "• 🌪️ Luraph v15.1 & v15 / v14\n"

    "• 🌪️ Luast v1.0.1\n"

    "• ☕ IronBrew & MoonSec\n"

    "• 🛡️ 2K Security & XOR\n"

    "• 🌙 MoonSec V2 / V3\n"

    "• 📦 Base64 / A7DEV\n\n"

    "**🔒 เอนจินป้องกันโค้ด (Obfuscator v6.7.6.7)**\n"

    "• ⚡ Recommended: Multi-Layer Polymorphic VM(Double-VM + AI Mutation)\n"

    "• 🔀 CFF Mode: Control Flow Flattening + Double-VM(ป้องกัน Decompiler สูงสุด)\n"

    "• 🛡️ Double-VM: Two-Tier Instruction Virtualizer + Encrypted Constants\n"

    "• ⚡ Fast-VM: High-Performance Anti-Tamper + Vmify\n"

    "• 🤖 DeepSeek AI: Polymorphic Mutation & Semantic Virtualization\n"

    "• 📦 Minifier: Mangled Identifier Shuffling\n\n"

    "**💡 วิธีใช้งานผ่านแผงควบคุม(How to Use)**\n"

    "1. คลิกปุ่ม 🔓 Deobfuscate หรือ 🔒 Obfuscate ด้านล่าง\n"

    "2. กรอกโค้ดสคริปต์ Lua ในหน้าต่าง Popup Modal ที่เด้งขึ้นมา\n"

    "3. เลือกเอนจินที่ต้องการ หรือใส่ auto ให้ระบบสแกนอัตโนมัติ\n"

    "4. บอทจะประมวลผลและส่งไฟล์โค้ดผลลัพธ์กลับให้คุณแบบ ส่วนตัว(Private)\n"

    "5. สามารถรับสคริปได้ที่ห้อง https://discord.com/channels/1549398019970179152/1555411076248506448\n\n"

    "*(หมายเหตุ: สำหรับไฟล์สคริปต์ขนาดใหญ่เกิน 4,000 ตัวอักษร ให้ใช้คำสั่ง /deobf หรือ /obfuscate แล้วแนบไฟล์)*"

)





# =============================================================================

# EMBED BUILDER

# =============================================================================

def build_deobf_panel_embed(cfg: Optional[dict] = None) -> discord.Embed:

    c = cfg or {}

    title = c.get("title") or DEFAULT_PANEL_TITLE

    color = parse_panel_color(c.get("color", "cyan"))

    desc = c.get("description") or DEFAULT_PANEL_DESCRIPTION



    embed = discord.Embed(

        title=title,

        description=desc,

        color=color

    )



    banner = c.get("banner_url") or DEFAULT_BANNER_URL

    thumb = c.get("thumbnail_url") or DEFAULT_THUMBNAIL_URL

    if banner and banner.startswith("http"):

        embed.set_image(url=banner)

    if thumb and thumb.startswith("http"):

        embed.set_thumbnail(url=thumb)



    embed.set_footer(

        text="PAYOMBØYZ CYBER-AI V10.0 • High-Performance VM Pipeline • 24/7 Online",

        icon_url=thumb if thumb and thumb.startswith("http") else None

    )

    return embed





class EditPanelModal(discord.ui.Modal):

    """Pop-up modal allowing admins to edit panel title, description, color, and images."""

    def __init__(self, panel_id: str, pdata: dict):

        super().__init__(title="แก้ไขแผงควบคุม (Edit Panel)")

        self.panel_id = panel_id

        self.pdata = pdata



        curr_title = pdata.get("title") or DEFAULT_PANEL_TITLE

        curr_desc = pdata.get("description") or DEFAULT_PANEL_DESCRIPTION

        curr_color = pdata.get("color") or "cyan"

        curr_banner = pdata.get("banner_url") or ""

        curr_thumb = pdata.get("thumbnail_url") or ""



        self.title_input = discord.ui.TextInput(

            label="หัวข้อแผงควบคุม (Title)",

            default=curr_title[:100],

            required=False,

            max_length=100

        )

        self.desc_input = discord.ui.TextInput(

            label="ข้อความแผงควบคุม (Description)",

            style=discord.TextStyle.paragraph,

            default=curr_desc[:4000],

            required=True,

            max_length=4000

        )

        self.color_input = discord.ui.TextInput(

            label="สี Embed (เช่น cyan, gold, emerald, #HEX)",

            default=curr_color[:20],

            required=False,

            max_length=20

        )

        self.banner_input = discord.ui.TextInput(

            label="Banner URL (ลิงก์รูปภาพยาวด้านล่าง)",

            default=curr_banner[:200],

            required=False,

            max_length=200

        )

        self.thumb_input = discord.ui.TextInput(

            label="Thumbnail URL (ลิงก์รูปไอคอนขวาบน)",

            default=curr_thumb[:200],

            required=False,

            max_length=200

        )



        self.add_item(self.title_input)

        self.add_item(self.desc_input)

        self.add_item(self.color_input)

        self.add_item(self.banner_input)

        self.add_item(self.thumb_input)



    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True, thinking=True)

        panels = load_deobf_panels()

        pdata = panels.get(self.panel_id, self.pdata)



        new_title = self.title_input.value.strip() or DEFAULT_PANEL_TITLE

        new_desc = self.desc_input.value.strip() or DEFAULT_PANEL_DESCRIPTION

        new_color = self.color_input.value.strip() or "cyan"

        new_banner = self.banner_input.value.strip() or None

        new_thumb = self.thumb_input.value.strip() or None



        pdata["title"] = new_title

        pdata["description"] = new_desc

        pdata["color"] = new_color

        pdata["banner_url"] = new_banner

        pdata["thumbnail_url"] = new_thumb



        save_deobf_panel(self.panel_id, pdata)



        try:

            from bot.ai_deobf_bot import bot as _bot_inst

            ch = _bot_inst.get_channel(pdata["channel_id"]) or await _bot_inst.fetch_channel(pdata["channel_id"])

            msg = await ch.fetch_message(pdata["message_id"])

            new_embed = build_deobf_panel_embed(pdata)

            view = DeobfPanelView()

            await msg.edit(embed=new_embed, view=view)



            confirm = discord.Embed(

                title="✅ PAYOMBØYZ | แก้ไขแผงควบคุมสำเร็จ",

                description=(

                    f"อัปเดตแผงควบคุมข้อความ ID `{pdata['message_id']}` ที่ห้อง {ch.mention} เรียบร้อยแล้ว!\n"

                    f"👉 **[คลิกเพื่อไปยังแผงควบคุม]({msg.jump_url})**"

                ),

                color=discord.Color.green()

            )

            await interaction.followup.send(embed=confirm, ephemeral=True)

        except Exception as e:

            await interaction.followup.send(f"❌ บันทึกข้อมูลแล้ว แต่เกิดข้อผิดพลาดในการแก้ไขข้อความบน Discord: `{e}`", ephemeral=True)





# =============================================================================

# HUMAN-READABLE CLEANUP PIPELINE (DeepSeek primary -> Gemini Pro fallback)

# =============================================================================

async def run_human_readable_cleanup(
    deobf_code: str,
    filename: str,
    guild_id: Optional[int] = None,
    log_channel_id: Optional[int] = None,
    bot_instance=None,
) -> Tuple[str, str]:
    """
    Preserves 100% genuine deterministic compiler output without LLM mutation.
    AI acts strictly as an analytical assistant/advisor, never altering recovered code.
    """
    return deobf_code, "engine_native_clean"



    # -- Send log to log channel --

    if bot_instance and log_channel_id and ai_worker != "none":

        try:

            log_ch = bot_instance.get_channel(log_channel_id) or await bot_instance.fetch_channel(log_channel_id)

            log_bytes = io.BytesIO(cleaned_code.encode("utf-8", errors="replace"))

            safe_stem = Path(filename).stem[:40]

            log_file = discord.File(log_bytes, filename=f"{safe_stem}_cleanup_{ai_worker}.lua")

            log_embed = discord.Embed(

                title=f"\U0001f4cb Deobfuscate Log \u2014 {filename}",

                description=(

                    f"\u2022 **\u0e44\u0e1f\u0e25\u0e4c:** `{filename}`\n"

                    f"\u2022 **AI Cleanup:** `{ai_worker}`\n"

                    f"\u2022 **\u0e02\u0e19\u0e32\u0e14:** `{len(cleaned_code):,}` chars\n"

                    f"\u2022 **\u0e40\u0e27\u0e25\u0e32:** <t:{int(time.time())}:R>"

                ),

                color=discord.Color.from_rgb(0, 200, 180)

            )

            await log_ch.send(embed=log_embed, file=log_file)

            print(f"[CLEANUP] Log sent to channel {log_channel_id}", flush=True)

        except Exception as log_err:

            print(f"[CLEANUP] Failed to send log: {log_err}", flush=True)



    return cleaned_code, ai_worker





# =============================================================================

# ENGINE SELECTION VIEWS (Step 1: Dropdown)

# =============================================================================



class DeobfEngineSelect(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(label=label, value=value, default=(value == "auto"))

            for label, value in DEOBF_ENGINES

        ]

        super().__init__(

            placeholder="\U0001f6e0\ufe0f \u0e40\u0e25\u0e37\u0e2d\u0e01 Engine \u0e16\u0e2d\u0e14\u0e23\u0e2b\u0e31\u0e2a...",

            min_values=1, max_values=1,

            options=options,

            custom_id="payom_deobf_engine_select_v10"

        )



    async def callback(self, interaction: discord.Interaction):

        engine = self.values[0]

        engine_label = next((lbl for lbl, val in DEOBF_ENGINES if val == engine), engine)

        view = DeobfInputChoiceView(engine_choice=engine)

        await interaction.response.send_message(

            f"Engine: **{engine_label}**\n\u0e40\u0e25\u0e37\u0e2d\u0e01\u0e27\u0e34\u0e18\u0e35\u0e2a\u0e48\u0e07\u0e2a\u0e04\u0e23\u0e34\u0e1b\u0e15\u0e4c:",

            view=view, ephemeral=True

        )





class DeobfEngineSelectView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=120)

        self.add_item(DeobfEngineSelect())





class ObfEngineSelect(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(label=label, value=value, default=(value == "level2"))

            for label, value in OBF_ENGINES

        ]

        super().__init__(

            placeholder="⚙️ เลือก Engine เข้ารหัส...",

            min_values=1, max_values=1,

            options=options,

            custom_id="payom_obf_engine_select_v10"

        )



    async def callback(self, interaction: discord.Interaction):

        engine = self.values[0]

        engine_label = next((lbl for lbl, val in OBF_ENGINES if val == engine), engine)

        view = ObfInputChoiceView(engine_choice=engine)

        await interaction.response.send_message(

            f"Engine: **{engine_label}**\nเลือกวิธีส่งสคริปต์:",

            view=view, ephemeral=True

        )





class ObfEngineSelectView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=120)

        self.add_item(ObfEngineSelect())





class ObfInputChoiceView(discord.ui.View):

    def __init__(self, engine_choice: str):

        super().__init__(timeout=120)

        self.engine_choice = engine_choice



    @discord.ui.button(

        label="Paste Code (max 4,000 chars)",

        style=discord.ButtonStyle.primary, row=0

    )

    async def btn_paste(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_modal(ObfuscateModal(engine_choice=self.engine_choice))



    @discord.ui.button(

        label="Attach Large File (no limit)",

        style=discord.ButtonStyle.secondary, row=0

    )

    async def btn_attach(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message(

            f"📎 **แนบไฟล์ Obfuscate** (Engine: `{self.engine_choice}`)\n\n"

            "ใช้คำสั่ง `/obfuscate` แล้วแนบไฟล์ `.lua` / `.txt` โดยตรง\n"

            "• **ไม่มีจำกัดขนาด** — อ่านไฟล์ทั้งหมดโดยไม่ตัด",

            ephemeral=True

        )





# =============================================================================

# POPUP MODALS (Text paste mode)

# =============================================================================



class DeobfuscateModal(discord.ui.Modal, title="PAYOMBOYZ Deobfuscator V10.0"):
    filename_input = discord.ui.TextInput(
        label="ชื่อไฟล์ Output (ไม่บังคับ)",
        placeholder="Script.lua",
        default="Script.lua",
        required=False,
        max_length=64
    )
    code_input = discord.ui.TextInput(
        label="วางโค้ด Lua/Luau (สูงสุด 4,000 ตัวอักษร)",
        style=discord.TextStyle.paragraph,
        placeholder="วางโค้ดที่นี่ (สูงสุด 4,000 ตัวอักษร)\nสำหรับไฟล์ใหญ่ ไม่จำกัดขนาด ให้ใช้คำสั่ง /deobf",
        required=True,
        max_length=MODAL_CODE_MAX
    )

    def __init__(self, engine_choice: Optional[str] = None):
        super().__init__()
        self.engine_choice = engine_choice or "auto"

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        from bot.ai_deobf_bot import ORCHESTRATOR, save_temp_input, build_deobf_embed, QUALITY_MONITOR
        from bot import panel as _panel_perm

        code_text = self.code_input.value.strip()
        if not code_text:
            await interaction.followup.send(
                "❌ โค้ดว่างเปล่า", ephemeral=True)
            return

        engine_choice = self.engine_choice or "auto"

        filename = self.filename_input.value.strip() or "Script.lua"

        if not filename.endswith((".lua", ".txt")):

            filename += ".lua"



        temp_path = None

        try:

            temp_path = save_temp_input(code_text.encode("utf-8", errors="replace"), filename)

            # Grant full engine capabilities to all authorized users and members
            is_admin = True



            deobf_data = await ORCHESTRATOR.process_script_deobfuscation(

                str(temp_path), filename,

                user_prompt=f"Panel Modal deobf engine={engine_choice}",

                forced_engine=engine_choice if engine_choice != "auto" else None,

                is_admin=is_admin

            )

            engine_res = deobf_data.get("engine_result", {})

            ai_summary = deobf_data.get("ai_summary", "")



            # Human-Readable Cleanup Pipeline

            raw_code = engine_res.get("deobfuscated_code", "")

            if raw_code and engine_res.get("success"):

                try:

                    from bot.ai_deobf_bot import bot as _bot_inst

                    log_ch_id = get_log_channel_id(interaction.guild_id)

                    cleaned_code, cleanup_worker = await run_human_readable_cleanup(

                        raw_code, filename,

                        guild_id=interaction.guild_id,

                        log_channel_id=log_ch_id,

                        bot_instance=_bot_inst

                    )

                    engine_res["deobfuscated_code"] = cleaned_code

                    if cleanup_worker != "none":

                        ai_summary = (ai_summary or "") + f"\n\n🧹 **Human-Readable Cleanup:** `{cleanup_worker}` ✅"

                except Exception as ce:

                    print(f"[PANEL] Cleanup error: {ce}", flush=True)



            decision_info = deobf_data.get("decision_info")

            embed, files = build_deobf_embed(engine_res, filename, ai_summary, decision_info=decision_info)

            await dispatch_result_to_channel_or_interaction(

                interaction=interaction,

                embed=embed,

                files=files,

                action_type="DEOBFUSCATE",

                filename=filename,

                guild_id=interaction.guild_id

            )



        except Exception as e:

            embed_err = discord.Embed(

                title="PAYOMBØYZ Panel | ❌ Error",

                description=f"```\n{str(e)[:500]}\n```",

                color=discord.Color.red()

            )

            await interaction.followup.send(embed=embed_err, ephemeral=True)

        finally:

            if temp_path and os.path.exists(temp_path):

                try:

                    os.remove(temp_path)

                except Exception:

                    pass





class ObfuscateModal(discord.ui.Modal, title="PAYOMBOYZ Obfuscator V6.7.6.7"):
    filename_input = discord.ui.TextInput(
        label="ชื่อไฟล์ Output (ไม่บังคับ)",
        placeholder="Protected.lua",
        default="Protected.lua",
        required=False,
        max_length=64
    )
    code_input = discord.ui.TextInput(
        label="วางโค้ด Lua/Luau (สูงสุด 4,000 ตัวอักษร)",
        style=discord.TextStyle.paragraph,
        placeholder="วางโค้ดที่นี่ (สูงสุด 4,000 ตัวอักษร)\nสำหรับไฟล์ใหญ่ ไม่จำกัดขนาด ให้ใช้คำสั่ง /obfuscate",
        required=True,
        max_length=MODAL_CODE_MAX
    )

    def __init__(self, engine_choice: Optional[str] = None):
        super().__init__()
        self.engine_choice = engine_choice or "level2"

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        from bot.ai_deobf_bot import ORCHESTRATOR, save_temp_input, build_obfuscate_embed

        code_text = self.code_input.value.strip()
        if not code_text:
            await interaction.followup.send(
                "❌ โค้ดว่างเปล่า", ephemeral=True)
            return

        chosen_engine = self.engine_choice or "level2"

        filename = self.filename_input.value.strip() or "Protected.lua"

        if not filename.endswith((".lua", ".txt")):

            filename += ".lua"



        temp_path = None

        try:

            temp_path = save_temp_input(code_text.encode("utf-8", errors="replace"), filename)

            obf_data = await ORCHESTRATOR.process_script_obfuscation(

                str(temp_path), filename, engine_choice=chosen_engine

            )

            embed, files = build_obfuscate_embed(obf_data, filename)

            await dispatch_result_to_channel_or_interaction(

                interaction=interaction,

                embed=embed,

                files=files,

                action_type="OBFUSCATE",

                filename=filename,

                guild_id=interaction.guild_id

            )



        except Exception as e:

            embed_err = discord.Embed(

                title="PAYOMB\u00d8YZ Obfuscate | \u274c Error",

                description=f"```\n{str(e)[:500]}\n```",

                color=discord.Color.red()

            )

            await interaction.followup.send(embed=embed_err, ephemeral=True)

        finally:

            if temp_path and os.path.exists(temp_path):

                try:

                    os.remove(temp_path)

                except Exception:

                    pass





# =============================================================================

# FILE & CODE ATTACHMENT MODAL (Engine selection & Output rename only)

# =============================================================================



class FileConfigModal(discord.ui.Modal):

    """

    Modal that appears immediately AFTER user drops/attaches a file or code:

    Presents ONLY tool/engine choice + output filename, then processes the script.

    """

    def __init__(
        self,
        mode: str = "deobf",
        attachment: Optional[discord.Attachment] = None,
        code_text: Optional[str] = None,
        default_filename: Optional[str] = None,
        raw_bytes: Optional[bytes] = None,
        engine_choice: Optional[str] = None
    ):
        modal_title = "PAYOMBOYZ Deobfuscator V10.0" if mode == "deobf" else "PAYOMBOYZ Obfuscator V6.7.6.7"
        super().__init__(title=modal_title)
        self.mode = mode
        self.attachment = attachment
        self.code_text = code_text
        self.raw_bytes = raw_bytes
        self.engine_choice = engine_choice or ("auto" if mode == "deobf" else "level2")

        orig_name = default_filename or (attachment.filename if attachment else ("Script.lua" if mode == "deobf" else "Protected.lua"))

        self.filename_input = discord.ui.TextInput(
            label="ชื่อไฟล์ Output",
            placeholder=orig_name,
            default=orig_name,
            required=False,
            max_length=64
        )
        self.add_item(self.filename_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        from bot.ai_deobf_bot import ORCHESTRATOR, save_temp_input, build_deobf_embed, build_obfuscate_embed, QUALITY_MONITOR
        from bot import panel as _panel_perm

        output_filename = self.filename_input.value.strip() or ("Script.lua" if self.mode == "deobf" else "Protected.lua")
        if not output_filename.endswith((".lua", ".txt")):
            output_filename += ".lua"

        temp_path = None
        try:
            content_bytes = None
            if self.raw_bytes:
                content_bytes = self.raw_bytes
            elif self.attachment:
                try:
                    content_bytes = await self.attachment.read()
                except Exception as read_err:
                    print(f"[PANEL ERROR] Attachment read failed: {read_err}", flush=True)
                    content_bytes = None
            elif self.code_text:
                content_bytes = self.code_text.encode("utf-8", errors="replace")

            if not content_bytes:
                await interaction.followup.send("❌ ไม่พบเนื้อหาไฟล์หรือโค้ด กรุณาส่งใหม่อีกครั้ง", ephemeral=True)
                return

            temp_path = save_temp_input(content_bytes, output_filename)

            if self.mode == "deobf":
                engine_choice = self.engine_choice or "auto"
                # Grant full engine capabilities to all authorized users and members
                is_admin = True

                deobf_data = await ORCHESTRATOR.process_script_deobfuscation(
                    str(temp_path), output_filename,
                    user_prompt=f"FileConfigModal deobf engine={engine_choice}",
                    forced_engine=engine_choice if engine_choice != "auto" else None,
                    is_admin=is_admin
                )
                engine_res = deobf_data.get("engine_result", {})
                ai_summary = deobf_data.get("ai_summary", "")

                # Human-Readable Cleanup Pipeline
                raw_code = engine_res.get("deobfuscated_code", "")
                if raw_code and engine_res.get("success"):
                    try:
                        from bot.ai_deobf_bot import bot as _bot_inst
                        log_ch_id = get_log_channel_id(interaction.guild_id)
                        cleaned_code, cleanup_worker = await run_human_readable_cleanup(
                            raw_code, output_filename,
                            guild_id=interaction.guild_id,
                            log_channel_id=log_ch_id,
                            bot_instance=_bot_inst
                        )
                        engine_res["deobfuscated_code"] = cleaned_code
                        if cleanup_worker != "none":
                            ai_summary = (ai_summary or "") + f"\n\n🧹 **Human-Readable Cleanup:** `{cleanup_worker}` ✅"
                    except Exception as ce:
                        print(f"[PANEL] Cleanup error: {ce}", flush=True)

                decision_info = deobf_data.get("decision_info")
                embed, files = build_deobf_embed(engine_res, output_filename, ai_summary, decision_info=decision_info)
                await dispatch_result_to_channel_or_interaction(
                    interaction=interaction,
                    embed=embed,
                    files=files,
                    action_type="DEOBFUSCATE",
                    filename=output_filename,
                    guild_id=interaction.guild_id
                )

            else:
                chosen_engine = self.engine_choice or "level2"

                obf_data = await ORCHESTRATOR.process_script_obfuscation(

                    str(temp_path), output_filename, engine_choice=chosen_engine

                )

                embed, files = build_obfuscate_embed(obf_data, output_filename)

                await dispatch_result_to_channel_or_interaction(

                    interaction=interaction,

                    embed=embed,

                    files=files,

                    action_type="OBFUSCATE",

                    filename=output_filename,

                    guild_id=interaction.guild_id,

                    is_success=obf_data.get("success", False)

                )



        except Exception as e:

            embed_err = discord.Embed(

                title=f"PAYOMBØYZ | ❌ Error ({self.mode.upper()})",

                description=f"```\n{str(e)[:500]}\n```",

                color=discord.Color.red()

            )

            await interaction.followup.send(embed=embed_err)

        finally:

            if temp_path and os.path.exists(temp_path):

                try:

                    os.remove(temp_path)

                except Exception:

                    pass





class SetFilenameModal(discord.ui.Modal, title="ตั้งชื่อไฟล์ Output"):
    def __init__(self, parent_view: "EphemeralConfigView"):
        super().__init__()
        self.parent_view = parent_view
        self.filename_input = discord.ui.TextInput(
            label="ชื่อไฟล์ Output",
            placeholder=parent_view.output_filename,
            default=parent_view.output_filename,
            required=True,
            max_length=64
        )
        self.add_item(self.filename_input)

    async def on_submit(self, interaction: discord.Interaction):
        fname = self.filename_input.value.strip()
        if not fname.endswith((".lua", ".txt", ".luau")):
            fname += ".lua"
        self.parent_view.output_filename = fname
        await interaction.response.send_message(
            f"✅ ตั้งชื่อไฟล์ Output เป็น `{fname}` เรียบร้อยแล้ว! กรุณากดปุ่ม **เริ่มทำงานทันที**",
            ephemeral=True
        )


class EphemeralConfigView(discord.ui.View):
    """Ephemeral control panel visible only to the user who uploaded the file."""
    def __init__(
        self,
        mode: str,
        attachment: Optional[discord.Attachment] = None,
        author_id: Optional[int] = None,
        raw_bytes: Optional[bytes] = None,
        default_filename: Optional[str] = None,
        parent_message: Optional[discord.Message] = None
    ):
        super().__init__(timeout=300)
        self.mode = "deobf" if mode in ("deobf", "deobfuscate") else "obf"
        self.attachment = attachment
        self.author_id = author_id
        self.raw_bytes = raw_bytes
        self.output_filename = default_filename or ("Script.lua" if self.mode == "deobf" else "Protected.lua")
        self.parent_message = parent_message
        self.selected_engine = "auto" if self.mode == "deobf" else "level2"

        if self.mode == "deobf":
            options = [
                discord.SelectOption(label="⚙️ Auto-Detect (แนะนำ)", value="auto", description="วิเคราะห์และถอดรหัสอัตโนมัติ", default=True),
                discord.SelectOption(label="🌪️ Luraph V15.1 / V15 (แนะนำ)", value="luraph_v15", description="Node CFG + Branch Solver + CFF + Auto Renamer"),
                discord.SelectOption(label="🔒 Luraph v14 (Classic)", value="luraph", description="Luraph Classic AST Devirtualizer"),
                discord.SelectOption(label="🌙 MoonSec V2 / V3 / V5", value="moonsec_v5", description="Unicode Stego Unpacker & Bytecode Lifter"),
                discord.SelectOption(label="🛡️ Luarmor One-Click", value="luarmor", description="AST Memory & Remote Restorer"),
                discord.SelectOption(label="🛠️ WeAreDevs / Prometheus", value="wearedevs", description="Constant Array & Vmify Extractor"),
                discord.SelectOption(label="🌘 Moonveil 2.0.2+", value="moonveil", description="AST Constant Decryptor"),
                discord.SelectOption(label="☕ IronBrew", value="moonsec", description="IronBrew AST Devirtualizer"),
            ]
            placeholder = "⚙️ เลือก Deobfuscator Engine..."
        else:
            options = [
                discord.SelectOption(
                    label="🟢 Level 1: Fast VM (Prometheus High Speed / 60 FPS)",
                    value="level1",
                    description="Direct Dispatch High-Speed VM (เหมาะกับโค้ดลูป 60FPS)"
                ),
                discord.SelectOption(
                    label="🟡 Level 2: Balanced Security (Prometheus Luau VM - แนะนำ)",
                    value="level2",
                    description="Standard Luau VM + CFF + S-Box Keystream (สมดุลความปลอดภัย)",
                    default=True
                ),
                discord.SelectOption(
                    label="🔴 Level 3: Maximum Armor (Double-VM + 7-Shield)",
                    value="level3",
                    description="Double-VM + Deep CFF + 7-Layer Anti-Tamper Shield"
                ),
                discord.SelectOption(
                    label="⚡ Level 4: Prometheus Multi-Tier VM (Instruction Virtualizer)",
                    value="level4",
                    description="Multi-Tier Virtualizer + Neutron 4-Pillar VM-CFF Armor"
                ),
                discord.SelectOption(
                    label="🛡️ Level 5: Sentinel Multi-Layer Double-VM (Anti-Hook/Spy)",
                    value="level5",
                    description="Dual-State CFF + Anti-Hook/Spy Sentinel + Anti-AST Dump"
                ),
            ]
            placeholder = "🔒 เลือกระดับความปลอดภัย (Obfuscation Level)..."

        self.engine_select = discord.ui.Select(placeholder=placeholder, options=options, row=0)
        self.engine_select.callback = self.on_engine_change
        self.add_item(self.engine_select)

    async def on_engine_change(self, interaction: discord.Interaction):
        self.selected_engine = self.engine_select.values[0]
        for opt in self.engine_select.options:
            opt.default = (opt.value == self.selected_engine)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="ตั้งชื่อไฟล์ Output", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def btn_set_filename(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetFilenameModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="เริ่มทำงานทันที", style=discord.ButtonStyle.success, emoji="⚡", row=1)
    async def btn_run(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=f"⏳ **กำลังประมวลผลสคริปต์ `{self.output_filename}` ผ่าน Engine `{self.selected_engine}`...**\nผลลัพธ์จะถูกส่งในช่องนี้ทันทีเมื่อเสร็จสิ้น",
            embed=None,
            view=None
        )
        if self.parent_message:
            try:
                await self.parent_message.delete()
            except Exception:
                pass

        channel = interaction.channel
        guild_id = interaction.guild_id
        author_id = self.author_id or interaction.user.id
        mode_str = "deobfuscate" if self.mode == "deobf" else "obfuscate"

        import asyncio
        asyncio.create_task(self._process_and_deliver(channel, guild_id, author_id, mode_str, interaction))

    async def _process_and_deliver(self, channel, guild_id, author_id, mode_str, interaction: Optional[discord.Interaction] = None):
        from bot.ai_deobf_bot import ORCHESTRATOR, save_temp_input, build_deobf_embed, build_obfuscate_embed
        from bot import panel as _panel_perm

        temp_path = None
        try:
            content_bytes = self.raw_bytes
            if not content_bytes and self.attachment:
                try:
                    content_bytes = await self.attachment.read()
                except Exception:
                    content_bytes = None

            if not content_bytes:
                fail_txt = f"<@{author_id}> ❌ ไม่สามารถอ่านเนื้อหาไฟล์ได้ กรุณาลองใหม่อีกครั้ง"
                if channel:
                    await channel.send(fail_txt)
                    await post_pinned_guide(channel, mode_str)
                elif interaction:
                    await interaction.followup.send(fail_txt, ephemeral=True)
                return

            temp_path = save_temp_input(content_bytes, self.output_filename)

            if self.mode == "deobf":
                forced = None if self.selected_engine == "auto" else self.selected_engine
                deobf_data = await ORCHESTRATOR.process_script_deobfuscation(
                    str(temp_path),
                    self.output_filename,
                    user_prompt=f"Engine={self.selected_engine}",
                    forced_engine=forced,
                    is_admin=True
                )
                engine_res = deobf_data.get("engine_result", {})
                ai_summary = deobf_data.get("ai_summary", "")

                raw_code = engine_res.get("deobfuscated_code", "")
                if raw_code and engine_res.get("success"):
                    try:
                        from bot.ai_deobf_bot import bot as _bot_inst
                        log_ch_id = get_log_channel_id(guild_id)
                        cleaned_code, cleanup_worker = await run_human_readable_cleanup(
                            raw_code, self.output_filename,
                            guild_id=guild_id,
                            log_channel_id=log_ch_id,
                            bot_instance=_bot_inst
                        )
                        engine_res["deobfuscated_code"] = cleaned_code
                        if cleanup_worker != "none":
                            ai_summary = (ai_summary or "") + f"\n\n🧹 **Human-Readable Cleanup:** `{cleanup_worker}` ✅"
                    except Exception as ce:
                        print(f"[EPHEMERAL CLEANUP] Error: {ce}", flush=True)

                decision_info = deobf_data.get("decision_info")
                embed, files = build_deobf_embed(engine_res, self.output_filename, ai_summary, decision_info=decision_info)
                action_view = DeobfResultActionView()
                is_ok = bool(engine_res.get("success"))
                msg_content = f"<@{author_id}> ✅ ถอดรหัสเสร็จสมบูรณ์!" if is_ok else f"<@{author_id}> ⚠️ ไม่สามารถถอดรหัสแบบ Static ได้สมบูรณ์ กรุณาใช้ปุ่มแดงด้านล่างดึงจาก Memory ในเกม"

                delivered = False
                if channel:
                    try:
                        await channel.send(content=msg_content, embed=embed, files=files, view=action_view)
                        delivered = True
                    except Exception as e_send:
                        print(f"[PANEL DELIVER] channel.send error: {e_send}", flush=True)

                # Re-seek any BytesIO buffers before retry
                for f in (files or []):
                    if hasattr(f, "fp") and hasattr(f.fp, "seek"):
                        try:
                            f.fp.seek(0)
                        except Exception:
                            pass

                if not delivered and interaction:
                    try:
                        await interaction.followup.send(content=msg_content, embed=embed, files=files, view=action_view, ephemeral=True)
                        delivered = True
                    except Exception as e_fol:
                        print(f"[PANEL DELIVER] followup.send error: {e_fol}", flush=True)

                if interaction:
                    try:
                        await interaction.edit_original_response(
                            content=f"✅ ถอดรหัส `{self.output_filename}` เสร็จสมบูรณ์แล้ว!" if is_ok else f"⚠️ สคริปต์ `{self.output_filename}` ติด VM ป้องกันขั้นสูง (ส่งผลลัพธ์และสคริปต์ Memory Interceptor เรียบร้อยแล้ว)",
                            embed=None,
                            view=None
                        )
                    except Exception:
                        pass

            else:
                obf_data = await ORCHESTRATOR.process_script_obfuscation(
                    str(temp_path),
                    self.output_filename,
                    engine_choice=self.selected_engine
                )
                embed, files = build_obfuscate_embed(obf_data, self.output_filename)
                is_ok = bool(obf_data.get("success"))
                msg_content = f"<@{author_id}> ✅ Obfuscate ป้องกันโค้ดเสร็จสมบูรณ์!" if is_ok else f"<@{author_id}> ❌ การเข้ารหัสล้มเหลว: `{obf_data.get('error', 'Unknown')}`"

                delivered = False
                if channel:
                    try:
                        await channel.send(content=msg_content, embed=embed, files=files)
                        delivered = True
                    except Exception as e_send:
                        print(f"[OBF DELIVER] channel.send error: {e_send}", flush=True)

                # Re-seek any BytesIO buffers before retry
                for f in (files or []):
                    if hasattr(f, "fp") and hasattr(f.fp, "seek"):
                        try:
                            f.fp.seek(0)
                        except Exception:
                            pass

                if not delivered and interaction:
                    try:
                        await interaction.followup.send(content=msg_content, embed=embed, files=files, ephemeral=True)
                        delivered = True
                    except Exception as e_fol:
                        print(f"[OBF DELIVER] followup.send error: {e_fol}", flush=True)

                if interaction:
                    try:
                        await interaction.edit_original_response(
                            content=f"✅ ป้องกันสคริปต์ `{self.output_filename}` เสร็จสมบูรณ์แล้ว!" if is_ok else f"❌ เข้ารหัสล้มเหลว: `{obf_data.get('error', 'Unknown')}`",
                            embed=None,
                            view=None
                        )
                    except Exception:
                        pass

            # CRITICAL: Always post the pinned guide embed at the bottom right after delivering!
            if channel:
                await post_pinned_guide(channel, mode_str)

        except Exception as err:
            print(f"[PANEL PROCESS ERROR] {err}", flush=True)
            err_msg = f"<@{author_id}> ❌ เกิดข้อผิดพลาดระหว่างประมวลผล: `{str(err)[:300]}`"
            delivered_err = False
            if channel:
                try:
                    await channel.send(err_msg)
                    delivered_err = True
                except Exception:
                    pass
            if not delivered_err and interaction:
                try:
                    await interaction.followup.send(err_msg, ephemeral=True)
                except Exception:
                    pass
            if interaction:
                try:
                    await interaction.edit_original_response(content=err_msg, embed=None, view=None)
                except Exception:
                    pass
            if channel:
                await post_pinned_guide(channel, mode_str)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass


class SingleActionPromptView(discord.ui.View):
    """
    Clean interactive view with a SINGLE button: [ ⚙️ เลือกเครื่องมือ & ตั้งชื่อไฟล์ ]
    """
    def __init__(
        self,
        mode: str,
        attachment: Optional[discord.Attachment] = None,
        author_id: Optional[int] = None,
        raw_bytes: Optional[bytes] = None,
        default_filename: Optional[str] = None
    ):
        super().__init__(timeout=300)
        self.mode = mode
        self.attachment = attachment
        self.author_id = author_id
        self.raw_bytes = raw_bytes
        self.default_filename = default_filename

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ เฉพาะผู้ที่ส่งไฟล์นี้เท่านั้นที่สามารถเปิดหน้าต่างตั้งค่าได้ครับ",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="เลือกเครื่องมือ & ตั้งชื่อไฟล์",
        style=discord.ButtonStyle.primary,
        emoji="⚙️"
    )
    async def btn_open_ephemeral(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.delete()
        except Exception:
            pass

        view = EphemeralConfigView(
            mode=self.mode,
            attachment=self.attachment,
            author_id=self.author_id,
            raw_bytes=self.raw_bytes,
            default_filename=self.default_filename,
            parent_message=None
        )
        embed = discord.Embed(
            title="⚙️ กำหนดค่าการทำงาน (เฉพาะคุณ)",
            description=(
                f"**ไฟล์:** `{self.default_filename}`\n"
                f"**โหมด:** `{'🔓 Deobfuscate' if self.mode in ('deobf', 'deobfuscate') else '🔒 Obfuscate'}`\n\n"
                "• เลือก Engine ที่ต้องการจากเมนูด้านล่าง\n"
                "• กดปุ่ม **ตั้งชื่อไฟล์** หากต้องการเปลี่ยนชื่อไฟล์ Output\n"
                "• กดปุ่ม **เริ่มทำงานทันที** เพื่อเริ่มประมวลผล"
            ),
            color=discord.Color.from_rgb(0, 229, 163)
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


ACTIVE_MULTIGAME_HUBS: Dict[int, Dict[str, Any]] = {}


class MultiGameSelectView(discord.ui.View):
    """
    Interactive Discord View for Multi-Game Hubs (e.g. Ouroboros 100+ games).
    Provides a Dropdown Menu of top games + prompt to choose a game or placeId.
    """
    def __init__(
        self,
        catalog_list: List[Dict[str, Any]],
        hub_target: str,
        author_id: int,
        games_map: Optional[Dict[Any, str]] = None,
        base_url: str = ""
    ):
        super().__init__(timeout=600)
        self.catalog_list = catalog_list
        self.hub_target = hub_target
        self.author_id = author_id
        self.games_map = games_map or {}
        self.base_url = base_url

        # Build Select Menu with up to 25 games
        options = []
        for g in catalog_list[:25]:
            pid = str(g["place_id"])
            g_name = g.get("game_name", f"PlaceId {pid}")[:95]
            fname = g.get("filename", "")[:45]
            options.append(discord.SelectOption(
                label=g_name,
                value=pid,
                description=f"PlaceId: {pid} • {fname}"
            ))

        if options:
            select = discord.ui.Select(
                placeholder=f"🎮 เลือกแมพที่ต้องการแกะ (แสดง 25 จาก {len(catalog_list)} แมพ)...",
                min_values=1,
                max_values=1,
                options=options
            )
            select.callback = self.select_callback
            self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ เฉพาะผู้ขอถอดรหัสสคริปต์นี้เท่านั้นที่สามารถเลือกแมพได้ครับ",
                ephemeral=True
            )
            return False
        return True

    async def select_callback(self, interaction: discord.Interaction):
        selected_pid = int(interaction.data["values"][0])
        await interaction.response.send_message(
            f"⏳ ได้รับคำสั่ง: กำลังดาวน์โหลดและถอดรหัสสคริปต์สำหรับ PlaceId `{selected_pid}`...",
            ephemeral=False
        )

        try:
            import asyncio
            import io
            from pathlib import Path
            from bot.loader_spy_engine import spy_and_deobf

            target_script_url = None
            fn = None
            if self.games_map:
                if selected_pid in self.games_map:
                    fn = self.games_map[selected_pid]
                elif str(selected_pid) in self.games_map:
                    fn = self.games_map[str(selected_pid)]
            if fn:
                if fn.startswith("http://") or fn.startswith("https://"):
                    target_script_url = fn
                elif self.base_url:
                    target_script_url = f"{self.base_url.rstrip('/')}/{fn.lstrip('/')}"
            elif self.catalog_list:
                for g in self.catalog_list:
                    if int(g.get("place_id", 0)) == selected_pid:
                        fn = g.get("filename", "")
                        if fn.startswith("http://") or fn.startswith("https://"):
                            target_script_url = fn
                        elif self.base_url:
                            target_script_url = f"{self.base_url.rstrip('/')}/{fn.lstrip('/')}"
                        break

            deobf_target = target_script_url or self.hub_target
            spy_res = await asyncio.to_thread(spy_and_deobf, deobf_target, place_id=selected_pid)
            if spy_res.get("success"):
                conf = spy_res.get("confidence", 100.0)
                grade = spy_res.get("confidence_grade", "EXCELLENT")
                lines = spy_res.get("recovered_lines", 0)
                elapsed = spy_res.get("elapsed", 0.0)
                target_u = spy_res.get("target_url", "GitHub Raw")
                deobf_code = spy_res.get("deobfuscated_code", "")
                mg_info = spy_res.get("multigame_info", {})
                g_name = mg_info.get("selected_game_name", f"PlaceId {selected_pid}")

                embed = discord.Embed(
                    title="⚡ PAYOMBØYZ CYBER-AI | 🎮 Multi-Game Hub Deobfuscation Complete",
                    description=(
                        f"**แมพที่เลือก:** `{g_name}` (PlaceId: `{selected_pid}`)\n"
                        f"**เป้าหมาย URL:** `{target_u}`\n"
                        f"**ระดับความแม่นยำ (Confidence):** `{conf:.1f}%` ({grade}) 🎯\n"
                        f"**โครงสร้างที่กู้คืนได้:** `{lines:,} บรรทัด` (Clean Luau)\n"
                        f"**เวลาที่ใช้:** `{elapsed:.2f}s`\n"
                    ),
                    color=discord.Color.from_rgb(0, 230, 150)
                )
                file_bytes = io.BytesIO(deobf_code.encode("utf-8"))
                stem_name = Path(target_u).stem if target_u and target_u != "GitHub Raw" else f"hub_place_{selected_pid}"
                safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', stem_name or f"hub_place_{selected_pid}")
                f = discord.File(file_bytes, filename=f"{safe_name}.deobf.luau")
                await interaction.followup.send(embed=embed, file=f)
            else:
                err_text = spy_res.get('error', 'Unknown failure')
                await interaction.followup.send(
                    f"❌ ล้มเหลวในการดาวน์โหลด/ถอดรหัสแมพ PlaceId `{selected_pid}`: {err_text}"
                )
        except Exception as exc:
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(
                    f"❌ เกิดข้อผิดพลาดระหว่างถอดรหัสแมพ PlaceId `{selected_pid}`: `{exc}`"
                )
            except Exception:
                pass


class FileActionPromptView(discord.ui.View):

    """Interactive button card sent when a user drops a file or code into chat."""

    def __init__(

        self,

        attachment: Optional[discord.Attachment] = None,

        code_text: Optional[str] = None,

        author_id: Optional[int] = None,

        raw_bytes: Optional[bytes] = None,

        default_filename: Optional[str] = None

    ):

        super().__init__(timeout=300)

        self.attachment = attachment

        self.code_text = code_text

        self.author_id = author_id

        self.raw_bytes = raw_bytes

        self.default_filename = default_filename



    async def interaction_check(self, interaction: discord.Interaction) -> bool:

        if self.author_id and interaction.user.id != self.author_id:

            await interaction.response.send_message(

                "❌ เฉพาะผู้ที่ส่งไฟล์นี้เท่านั้นที่สามารถเปิดหน้าต่างตั้งค่าได้ครับ",

                ephemeral=True

            )

            return False

        return True



    @discord.ui.button(

        label="Deobfuscate (ถอดรหัส)",

        style=discord.ButtonStyle.success,

        emoji="🔓"

    )

    async def btn_deobf(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_modal(

            FileConfigModal(

                mode="deobf",

                attachment=self.attachment,

                code_text=self.code_text,

                default_filename=self.default_filename,

                raw_bytes=self.raw_bytes

            )

        )

        try:

            await interaction.message.delete()

        except Exception:

            pass



    @discord.ui.button(

        label="Obfuscate (ป้องกันโค้ด)",

        style=discord.ButtonStyle.primary,

        emoji="🔒"

    )

    async def btn_obf(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_modal(

            FileConfigModal(

                mode="obf",

                attachment=self.attachment,

                code_text=self.code_text,

                default_filename=self.default_filename,

                raw_bytes=self.raw_bytes

            )

        )

        try:

            await interaction.message.delete()

        except Exception:

            pass





# Global tracking for users who clicked Panel buttons and are preparing to drop a file

ACTIVE_PANEL_SESSIONS: dict[int, dict] = {}





class OpenConfigModalView(discord.ui.View):
    """Interactive button and dropdown sent right after user drops a file/code following a panel request."""
    def __init__(
        self,
        mode: str,
        attachment: Optional[discord.Attachment] = None,
        code_text: Optional[str] = None,
        author_id: Optional[int] = None,
        default_filename: Optional[str] = None,
        raw_bytes: Optional[bytes] = None
    ):
        super().__init__(timeout=300)
        self.mode = mode
        self.attachment = attachment
        self.code_text = code_text
        self.author_id = author_id
        self.default_filename = default_filename
        self.raw_bytes = raw_bytes
        self.selected_engine = "auto" if mode == "deobf" else "level2"

        if mode == "deobf":
            options = [
                discord.SelectOption(label="🤖 Auto-Detect (แนะนำ)", value="auto", description="วิเคราะห์และเลือก Engine อัตโนมัติ", default=True),
                discord.SelectOption(label="🌪️ Luraph V15.1 / V15 (แนะนำ)", value="luraph_v15", description="Node CFG Dominator + CFF Unflattener + AST Renamer"),
                discord.SelectOption(label="🔒 Luarmor V10 / SAE", value="luarmor", description="Luarmor AST Dumper & Memory Restorer"),
                discord.SelectOption(label="⚡ WeAreDevs (Prometheus)", value="wearedevs", description="Prometheus Bytecode Emulation Dumper"),
                discord.SelectOption(label="🌙 Moonveil 2.0.2+", value="moonveil", description="Luau AST Constant Extractor & Devirtualizer"),
                discord.SelectOption(label="🔒 Luraph v14 (Classic)", value="luraph", description="Java ANTLR / Classic VM Decompiler"),
                discord.SelectOption(label="🛡️ IronBrew", value="moonsec", description="AST Pattern Devirtualizer"),
                discord.SelectOption(label="🌙 MoonSec V2 / V3", value="moonsec_v5", description="MoonSec V2 / V3 Devirtualizer"),
                discord.SelectOption(label="🔑 2K Security / XOR", value="twok", description="Static Decryption & String Table Solver"),
                discord.SelectOption(label="🧩 Luast", value="luast", description="Control Flow De-flattener"),
                discord.SelectOption(label="📦 A7Dev / Base64", value="a7dev", description="Layered String & Bytecode Unpacker"),
            ]
            placeholder = "⚙️ เลือก Deobfuscator Engine..."
        else:
            options = [
                discord.SelectOption(
                    label="🟢 Level 1: Fast VM (Prometheus High Speed / 60 FPS)",
                    value="level1",
                    description="Direct Dispatch High-Speed VM (เหมาะกับโค้ดลูป 60FPS)"
                ),
                discord.SelectOption(
                    label="🟡 Level 2: Balanced Security (Prometheus Luau VM - แนะนำ)",
                    value="level2",
                    description="Standard Luau VM + CFF + S-Box Keystream (สมดุลความปลอดภัย)",
                    default=True
                ),
                discord.SelectOption(
                    label="🔴 Level 3: Maximum Armor (Double-VM + 7-Shield)",
                    value="level3",
                    description="Double-VM + Deep CFF + 7-Layer Anti-Tamper Shield"
                ),
                discord.SelectOption(
                    label="⚡ Level 4: Prometheus Multi-Tier VM (Instruction Virtualizer)",
                    value="level4",
                    description="Multi-Tier Virtualizer + Neutron 4-Pillar VM-CFF Armor"
                ),
                discord.SelectOption(
                    label="🛡️ Level 5: Sentinel Multi-Layer Double-VM (Anti-Hook/Spy)",
                    value="level5",
                    description="Dual-State CFF + Anti-Hook/Spy Sentinel + Anti-AST Dump"
                ),
            ]
            placeholder = "🔒 เลือกระดับความปลอดภัย (Obfuscation Level)..."

        self.engine_select = discord.ui.Select(
            placeholder=placeholder,
            options=options,
            row=0
        )
        self.engine_select.callback = self.on_engine_change
        self.add_item(self.engine_select)

    async def on_engine_change(self, interaction: discord.Interaction):
        self.selected_engine = self.engine_select.values[0]
        for opt in self.engine_select.options:
            opt.default = (opt.value == self.selected_engine)
        await interaction.response.edit_message(view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ เฉพาะผู้ที่ส่งไฟล์นี้เท่านั้นที่สามารถเปิดหน้าต่างตั้งค่าได้ครับ",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="เริ่มทำงานทันที",
        style=discord.ButtonStyle.success,
        emoji="⚡",
        row=1
    )
    async def btn_run_direct(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        modal_executor = FileConfigModal(
            mode=self.mode,
            attachment=self.attachment,
            code_text=self.code_text,
            default_filename=self.default_filename,
            raw_bytes=self.raw_bytes,
            engine_choice=self.selected_engine
        )
        try:
            await interaction.message.delete()
        except Exception:
            pass
        await modal_executor.on_submit(interaction)

    @discord.ui.button(
        label="ตั้งชื่อไฟล์ Output (Pop-up)",
        style=discord.ButtonStyle.secondary,
        emoji="✏️",
        row=1
    )
    async def btn_open(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            FileConfigModal(
                mode=self.mode,
                attachment=self.attachment,
                code_text=self.code_text,
                default_filename=self.default_filename,
                raw_bytes=self.raw_bytes,
                engine_choice=self.selected_engine
            )
        )
        try:
            await interaction.message.delete()
        except Exception:
            pass


class PanelDirectModalView(discord.ui.View):
    """Ephemeral view that lets user choose engine via Dropdown and paste text code in modal."""
    def __init__(self, mode: str):
        super().__init__(timeout=180)
        self.mode = mode
        self.selected_engine = "auto" if mode == "deobf" else "level2"

        if mode == "deobf":
            options = [
                discord.SelectOption(label="🤖 Auto-Detect (แนะนำ)", value="auto", description="วิเคราะห์และเลือก Engine อัตโนมัติ", default=True),
                discord.SelectOption(label="🌪️ Luraph V15.1 / V15 (แนะนำ)", value="luraph_v15", description="Node CFG Dominator + CFF Unflattener + AST Renamer"),
                discord.SelectOption(label="🔒 Luarmor V10 / SAE", value="luarmor", description="Luarmor AST Dumper & Memory Restorer"),
                discord.SelectOption(label="⚡ WeAreDevs (Prometheus)", value="wearedevs", description="Prometheus Bytecode Emulation Dumper"),
                discord.SelectOption(label="🌙 Moonveil 2.0.2+", value="moonveil", description="Luau AST Constant Extractor & Devirtualizer"),
                discord.SelectOption(label="🔒 Luraph v14 (Classic)", value="luraph", description="Java ANTLR / Classic VM Decompiler"),
                discord.SelectOption(label="🛡️ IronBrew", value="moonsec", description="AST Pattern Devirtualizer"),
                discord.SelectOption(label="🌙 MoonSec V2 / V3", value="moonsec_v5", description="MoonSec V2 / V3 Devirtualizer"),
                discord.SelectOption(label="🔑 2K Security / XOR", value="twok", description="Static Decryption & String Table Solver"),
                discord.SelectOption(label="🧩 Luast", value="luast", description="Control Flow De-flattener"),
                discord.SelectOption(label="📦 A7Dev / Base64", value="a7dev", description="Layered String & Bytecode Unpacker"),
            ]
            placeholder = "⚙️ เลือก Deobfuscator Engine..."
        else:
            options = [
                discord.SelectOption(label="🔒 Luarmor Hybrid V6.7.6.7 (แนะนำ)", value="luarmor", description="AST CFF + Dynamic Digest + Double-VM", default=True),
                discord.SelectOption(label="⚡ Multi-Layer VM", value="recommended", description="CFF State Machine + Double-VM"),
                discord.SelectOption(label="🌪️ Maximum CFF", value="cff", description="Flattening ลึกสุด + Double-VM"),
                discord.SelectOption(label="🛡️ Double-VM", value="double_vm", description="Two-tier Instruction Virtualizer"),
                discord.SelectOption(label="🚀 Fast-VM", value="fast_vm", description="AntiTamper + Vmify (เหมาะกับไฟล์ใหญ่)"),
                discord.SelectOption(label="📦 Minify", value="minify", description="Mangled Shuffled Identifiers"),
            ]
            placeholder = "🔒 เลือก Obfuscator Engine..."

        self.engine_select = discord.ui.Select(
            placeholder=placeholder,
            options=options,
            row=0
        )
        self.engine_select.callback = self.on_engine_change
        self.add_item(self.engine_select)

    async def on_engine_change(self, interaction: discord.Interaction):
        self.selected_engine = self.engine_select.values[0]
        for opt in self.engine_select.options:
            opt.default = (opt.value == self.selected_engine)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(
        label="วางโค้ดใน Pop-up ทันที (สูงสุด 4,000 ตัวอักษร)",
        style=discord.ButtonStyle.secondary,
        emoji="📝",
        row=1
    )
    async def btn_direct_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.mode == "deobf":
            await interaction.response.send_modal(DeobfuscateModal(engine_choice=self.selected_engine))
        else:
            await interaction.response.send_modal(ObfuscateModal(engine_choice=self.selected_engine))





class InspectCodeModal(discord.ui.Modal, title="PAYOMBOYZ AI Code Inspector"):

    code_input = discord.ui.TextInput(

        label="Paste Lua/Luau code to scan",

        style=discord.TextStyle.paragraph,

        placeholder="Paste script here to scan structure and risks...",

        required=True,

        max_length=MODAL_CODE_MAX

    )



    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True, thinking=True)

        from bot.knowledge import CODE_IDE

        code_text = self.code_input.value.strip()

        analysis = CODE_IDE.analyze_script(code_text)



        embed = discord.Embed(

            title="\U0001f50d PAYOMB\u00d8YZ Code IDE | \u0e2a\u0e23\u0e38\u0e1b\u0e1c\u0e25\u0e01\u0e32\u0e23\u0e2a\u0e41\u0e01\u0e19\u0e42\u0e04\u0e49\u0e14",

            color=discord.Color.blurple()

        )

        embed.add_field(name="\U0001f4ca Lines", value=f"`{analysis.get('lines', 0):,}`", inline=True)

        embed.add_field(name="\U0001f4e6 Functions", value=f"`{len(analysis.get('functions', []))}`", inline=True)

        embed.add_field(name="\U0001f4e1 Remotes", value=f"`{len(analysis.get('remotes', []))}`", inline=True)



        risks = analysis.get("risks", [])

        if risks:

            embed.add_field(name="\u26a0\ufe0f Risks", value="\n".join([f"\u2022 {r}" for r in risks[:5]]), inline=False)

        else:

            embed.add_field(name="\U0001f6e1\ufe0f Safety", value="\U0001f7e2 No dangerous commands found", inline=False)



        await interaction.followup.send(embed=embed, ephemeral=True)





# =============================================================================

# STATUS CHECK

# =============================================================================

async def build_status_embed() -> discord.Embed:

    embed = discord.Embed(

        title="\U0001f4e1 PAYOMB\u00d8YZ System Status \u2014 Real-Time",

        description="\u0e2a\u0e16\u0e32\u0e19\u0e30 Deobfuscate, Obfuscate, AI Providers",

        color=discord.Color.from_rgb(0, 220, 180)

    )



    provider_lines = []

    try:

        from bot.hybrid_router import HYBRID_ROUTER

        import asyncio

        health = await asyncio.to_thread(

            HYBRID_ROUTER.check_route_health,

            preferred_provider=None,

            timeout_seconds=3.0,

        )

        provider_rows = health.get("providers", [])

        grouped: dict = {}

        for item in provider_rows:

            grouped.setdefault(item.get("provider", "unknown"), []).append(item)

        label_map = {

            "gemini": "\U0001f916 Gemini Pro",

            "deepseek": "\U0001f9e0 DeepSeek V3",

            "openrouter": "\U0001f500 OpenRouter",

            "bluezygpt": "\u26a1 BluezyGPT",

            "thaillm": "\U0001f1f9\U0001f1ed ThaiLLM",

        }

        for name, items in grouped.items():

            ok = sum(1 for i in items if i.get("status") == "HEALTHY")

            emoji = "\U0001f7e2" if ok == len(items) else ("\U0001f7e1" if ok else "\U0001f534")

            provider_lines.append(f"{emoji} **{label_map.get(name, name)}**: `{ok}/{len(items)}`")

    except Exception as e:

        provider_lines.append(f"\u274c AI health check failed: `{str(e)[:80]}`")



    embed.add_field(

        name="\U0001f916 AI Provider Status",

        value="\n".join(provider_lines) if provider_lines else "No data",

        inline=False

    )

    embed.add_field(

        name="\u2699\ufe0f Local Engine Status",

        value=(

            "\U0001f7e2 **WeAreDevs (Prometheus)** \u2014 Lua 5.1 Emulation\n"

            "\U0001f7e2 **Moonveil 2.0.2+** \u2014 Luau AST Dumper\n"

            "🟢 **Luraph v15.1 / v15** — Node CFG + CFF + Auto Renamer\n"
            "🟢 **Luraph v14** — Java ANTLR / Classic Decompiler\n"

            "\U0001f7e2 **Luast v1.0.1** \u2014 CFG De-flattener\n"

            "\U0001f7e2 **IronBrew/MoonSec** \u2014 AST Devirtualizer\n"

            "\U0001f7e2 **2K Security/XOR** \u2014 Static Solver"

        ),

        inline=False

    )

    embed.add_field(

        name="\U0001f9f9 Cleanup Pipeline",

        value=(

            "\u2022 **Primary:** DeepSeek V3\n"

            "\u2022 **Fallback:** Gemini Pro (Google AI API)\n"

            "\u2022 **Log:** \u0e2a\u0e48\u0e07\u0e44\u0e1b\u0e22\u0e31\u0e07 Log Channel \u0e17\u0e35\u0e48\u0e15\u0e31\u0e49\u0e07\u0e04\u0e48\u0e32\u0e44\u0e27\u0e49\u0e2d\u0e31\u0e15\u0e42\u0e19\u0e21\u0e31\u0e15\u0e34"

        ),

        inline=False

    )

    embed.set_footer(text=f"Updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")

    return embed





# =============================================================================

# PERSISTENT MAIN PANEL VIEW

# =============================================================================

class DeobfPanelView(discord.ui.View):

    """Persistent V10 Panel — custom_ids use _v10 suffix"""

    def __init__(self):

        super().__init__(timeout=None)



    @discord.ui.button(

        label="Deobfuscate (ถอดรหัส)",

        style=discord.ButtonStyle.success,

        emoji="\U0001f513",

        custom_id="payom_panel_deobf_btn_v10",

        row=0

    )

    async def btn_deobfuscate(self, interaction: discord.Interaction, button: discord.ui.Button):

        ACTIVE_PANEL_SESSIONS[interaction.user.id] = {

            "mode": "deobf",

            "timestamp": time.time(),

            "channel_id": interaction.channel_id

        }

        embed = discord.Embed(

            title="📥 PAYOMBØYZ Deobfuscator | พร้อมรับไฟล์สคริปต์",

            description=(

                "**ขั้นตอนใช้งานง่ายๆ:**\n"

                "1. **ลากไฟล์** `.lua` / `.txt` ใส่ช่องแชทนี้แล้วกด **Enter** (ส่งข้อความ)\n"

                "   *(หรือวางโค้ดสคริปต์ลงในช่องแชทแล้วกด Enter)*\n\n"

                "2. บอทจะตอบกลับปุ่ม **[⚡ เปิด Pop-up เลือก Engine]** ให้คลิก 1 ที\n"

                "   แล้วหน้าต่าง Pop-up จะเด้งขึ้นมาให้เลือก Engine และตั้งชื่อไฟล์ทันที!\n\n"

                "*(ไม่มีการจำกัดขนาดไฟล์ และไม่ตัดโค้ด)*"

            ),

            color=discord.Color.green()

        )

        await interaction.response.send_message(

            embed=embed,

            view=PanelDirectModalView(mode="deobf"),

            ephemeral=True

        )



    @discord.ui.button(

        label="Obfuscate (ป้องกันโค้ด)",

        style=discord.ButtonStyle.primary,

        emoji="\U0001f512",

        custom_id="payom_panel_obf_btn_v10",

        row=0

    )

    async def btn_obfuscate(self, interaction: discord.Interaction, button: discord.ui.Button):

        ACTIVE_PANEL_SESSIONS[interaction.user.id] = {

            "mode": "obf",

            "timestamp": time.time(),

            "channel_id": interaction.channel_id

        }

        embed = discord.Embed(

            title="🔒 PAYOMBØYZ Obfuscator | พร้อมรับไฟล์สคริปต์",

            description=(

                "**ขั้นตอนใช้งานง่ายๆ:**\n"

                "1. **ลากไฟล์** `.lua` / `.txt` ใส่ช่องแชทนี้แล้วกด **Enter** (ส่งข้อความ)\n"

                "   *(หรือวางโค้ดสคริปต์ลงในช่องแชทแล้วกด Enter)*\n\n"

                "2. บอทจะตอบกลับปุ่ม **[⚡ เปิด Pop-up เลือก Engine]** ให้คลิก 1 ที\n"

                "   แล้วหน้าต่าง Pop-up จะเด้งขึ้นมาให้เลือก Engine และตั้งชื่อไฟล์ทันที!\n\n"

                "*(ไม่มีการจำกัดขนาดไฟล์ และไม่ตัดโค้ด)*"

            ),

            color=discord.Color.blue()

        )

        await interaction.response.send_message(

            embed=embed,

            view=PanelDirectModalView(mode="obf"),

            ephemeral=True

        )



    @discord.ui.button(

        label="Status (สถานะระบบ)",

        style=discord.ButtonStyle.secondary,

        emoji="\U0001f4e1",

        custom_id="payom_panel_status_btn_v10",

        row=1

    )

    async def btn_status(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:

            embed = await build_status_embed()

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:

            await interaction.followup.send(f"\u274c Status check failed: `{str(e)[:200]}`", ephemeral=True)



    @discord.ui.button(

        label="Inspect Code (สแกน)",

        style=discord.ButtonStyle.secondary,

        emoji="\U0001f50d",

        custom_id="payom_panel_inspect_btn_v10",

        row=1

    )

    async def btn_inspect(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_modal(InspectCodeModal())



    @discord.ui.button(

        label="Engines & Info",

        style=discord.ButtonStyle.secondary,

        emoji="\u2699\ufe0f",

        custom_id="payom_panel_engines_btn_v10",

        row=2

    )

    async def btn_engines(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="\u2699\ufe0f PAYOMB\u00d8YZ Multi-Engine Pipeline Details",

            color=discord.Color.teal()

        )

        embed.add_field(

            name="1. Universal 5-Stage Semantic Decompiler",

            value=(

                "\u2022 Stage 1: Algebraic engine (Opaque predicates)\n"

                "\u2022 Stage 2: CFG Linearizer (De-flattens CFF state machines)\n"

                "\u2022 Stage 3: Constant Folding (Table lookups -> literals)\n"

                "\u2022 Stage 4: Register Devirt (-> Roblox Services)\n"

                "\u2022 Stage 5: High-Level Idiom synthesis"

            ),

            inline=False

        )

        embed.add_field(

            name="2. Human-Readable Cleanup Pipeline (V10.0 NEW)",

            value=(

                "\u2022 **DeepSeek V3:** Cleans code to human-readable level\n"

                "\u2022 **Gemini Pro Fallback:** Kicks in if DeepSeek quota exhausted\n"

                "\u2022 **Auto Log:** Sends result to configured Log Channel"

            ),

            inline=False

        )

        embed.add_field(

            name="3. Multi-Engine Virtualizer (Obfuscation)",

            value=(

                "\u2022 Multi-Layer VM + Polymorphic mutation\n"

                "\u2022 Control Flow Flattening (defeats static analysis)\n"

                "\u2022 Execution Gate: verified by luau-compile.exe (100% runnable)"

            ),

            inline=False

        )

        embed.set_footer(text="PAYOMB\u00d8YZ CYBER-AI V10.0")

        await interaction.response.send_message(embed=embed, ephemeral=True)



    @discord.ui.button(

        label="Help (วิธีใช้งาน)",

        style=discord.ButtonStyle.secondary,

        emoji="\U0001f4d6",

        custom_id="payom_panel_help_btn_v10",

        row=2

    )

    async def btn_help(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="\U0001f4d6 คู่มือ Deobfuscate & Obfuscate V10.0",

            description=(

                "**ขั้นตอนการใช้งาน:**\n\n"

                "**1. กดปุ่ม Deobfuscate / Obfuscate**\n"

                "• หน้าต่าง **Pop-up จะเด้งขึ้นมาทันที** (1-Click Popup Modal)\n"

                "• เลือก Engine ได้โดยตรงจาก Dropdown ในหน้าต่าง Pop-up\n\n"

                "**2. การส่งโค้ด / ไฟล์**\n"

                f"• **วางโค้ดใน Pop-up:** รองรับได้สูงสุด **{MODAL_CODE_MAX:,} ตัวอักษร**\n"

                "• **แนบไฟล์ขนาดใหญ่:** พิมพ์ `/deobf` หรือ `/obfuscate` แล้วแนบไฟล์ `.lua` / `.txt` ได้เลย — **ไม่จำกัดขนาดไฟล์ & ไม่ติด Timeout**\n\n"

                "**3. ระบบประมวลผล & บันทึก Log**\n"

                "• DeepSeek / Gemini Clean Code อัตโนมัติ\n"

                "• ส่งไฟล์ Code และผลวิเคราะห์กลับให้คุณแบบส่วนตัว\n"

                "• ส่งสำเนา Log ไปยัง Log Channel ที่ตั้งค่าไว้\n\n"

                "**4. ปุ่ม Status & Inspect**\n"

                "• **Status:** เช็คความพร้อมของ Engine & AI Provider แบบ Real-Time\n"

                "• **Inspect Code:** สแกนหา Remotes, Services, URLs และโครงสร้างโค้ด"

            ),

            color=discord.Color.gold(),
        )
        embed.set_footer(text="PAYOMBØYZ SUPPORT • 24/7 Online")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="แกะสคริปไม่ออก (ดึงจาก Memory)",
        style=discord.ButtonStyle.danger,
        emoji="🛠️",
        custom_id="payom_panel_unbreakable_dump_v10",
        row=3
    )
    async def btn_unbreakable_dump(self, interaction: discord.Interaction, button: discord.ui.Button):
        from bot.runtime_interceptor_generator import build_unbreakable_guide_embed, get_runtime_interceptor_file
        embed = build_unbreakable_guide_embed()
        interceptor_file = get_runtime_interceptor_file()
        await interaction.response.send_message(embed=embed, file=interceptor_file, ephemeral=True)


class DeobfResultActionView(discord.ui.View):
    """
    Persistent action view attached to the bottom of all deobfuscation delivery messages in chat.
    Provides 1-click access to the in-game Runtime Interceptor when scripts are heavily protected.
    """
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="แกะสคริปไม่ออก (ดึงจาก Memory)",
        style=discord.ButtonStyle.danger,
        emoji="🛠️",
        custom_id="payom_result_unbreakable_dump_v10"
    )
    async def btn_unbreakable_dump(self, interaction: discord.Interaction, button: discord.ui.Button):
        from bot.runtime_interceptor_generator import build_unbreakable_guide_embed, get_runtime_interceptor_file
        embed = build_unbreakable_guide_embed()
        interceptor_file = get_runtime_interceptor_file()
        await interaction.response.send_message(embed=embed, file=interceptor_file, ephemeral=True)
