import asyncio
import io
import os
import re
import sys
import time
import socket
from pathlib import Path
from typing import List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import discord
from discord import app_commands
from discord.ext import commands

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from bot import panel
from bot import security
from bot.hub_runtime import install_bot_monitor
from bot.scriptcenter_client import get_sc_client

intents = discord.Intents.default()
intents.guilds = True
intents.members = False  # Keep false unless privileged intent is enabled

role_bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents, help_command=None)
install_bot_monitor(role_bot, "role")
PROJECT_NAME = "🛡️ PAYOMBØYZ GET-ROLE & SCRIPT SYSTEM"


# =========================================================================
# 🔄 BOT LIFECYCLE & EVENT HANDLERS
# =========================================================================
@role_bot.event
async def on_ready():
    print("=" * 64)
    print("  🛡️ PAYOMBØYZ GET-ROLE & GET-SCRIPT SYSTEM READY")
    print("=" * 64)
    user_tag = f"{role_bot.user.name}#{role_bot.user.discriminator}" if role_bot.user.discriminator != "0" else role_bot.user.name
    print(f"👤 Logged in as: {user_tag} (ID: {role_bot.user.id})")
    print(f"🆔 Client ID: {role_bot.user.id} ({'Verified: 1548921066833838080' if str(role_bot.user.id) == '1548921066833838080' else 'Mismatch'})")
    print(f"🔑 Client Secret: {'Loaded (c4ktSW...)' if config.CLIENT_SECRET else 'Not Set'}")
    print(f"🔗 Invite URL: {config.get_bot_invite_url(str(role_bot.user.id))}")
    print(f"⚙️  Prefix: {config.COMMAND_PREFIX}")
    print(f"🏰 Connected Guilds: {len(role_bot.guilds)}")
    print("=" * 64)

    # 1. โหลดและลงทะเบียน Persistent Views ทั้งหมด
    panel.register_all_panel_views(role_bot)
    try:
        from bot.godmode import register_godmode_to_bot
        register_godmode_to_bot(role_bot)
    except Exception as ge:
        print(f"[-] Godmode registration error in role_bot: {ge}", flush=True)

    # 2. Ensure no duplicate guild-specific commands exist (clean up guild overrides)
    for guild in role_bot.guilds:
        try:
            guild_cmds = await role_bot.tree.fetch_commands(guild=guild)
            if guild_cmds:
                role_bot.tree.clear_commands(guild=guild)
                await role_bot.tree.sync(guild=guild)
                print(f"[+] Cleared {len(guild_cmds)} duplicate guild commands from {guild.name} ({guild.id}).", flush=True)
        except Exception as ge:
            print(f"[-] Guild command cleanup notice for {guild.id}: {ge}", flush=True)

    # 3. Publish commands globally only (prevents duplicates in Discord UI)
    try:
        synced = await role_bot.tree.sync()
        print(f"[+] Synced {len(synced)} Get-ROLE global slash commands successfully.", flush=True)
    except Exception as e:
        print(f"[-] Get-ROLE global slash sync failed: {e}", flush=True)

    await role_bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Get-Role & Get-Script Panels | /setup_panel"
        ),
        status=discord.Status.online
    )


@role_bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    original = getattr(error, "original", error)
    print(f"[ROLE BOT] App command error: {type(original).__name__}: {original}", flush=True)
    message = "❌ คำสั่งทำงานไม่สำเร็จ โปรดลองอีกครั้ง หากยังพบปัญหาให้แจ้งแอดมิน"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        pass


# =========================================================================
# 🔍 AUTOCOMPLETE HELPERS
# =========================================================================
def resolve_project_input(project_value: str, projects: Optional[dict] = None) -> tuple[str, Optional[dict]]:
    """Resolve either a project ID/name or an autocomplete label ending in (project_id)."""
    if not isinstance(project_value, str) or not project_value.strip():
        return "", None

    projects = projects if isinstance(projects, dict) else panel.load_projects()
    raw_value = project_value.strip()

    def find_project(value: str) -> tuple[Optional[str], Optional[dict]]:
        needle = value.strip().casefold()
        for project_id, project_data in projects.items():
            if not isinstance(project_data, dict):
                continue
            candidates = (str(project_id), str(project_data.get("id", "")), str(project_data.get("name", "")))
            if any(candidate.casefold() == needle for candidate in candidates if candidate):
                return str(project_data.get("id") or project_id), project_data
        return None, None

    project_id, project_data = find_project(raw_value)
    if project_data:
        return project_id or raw_value, project_data

    # Some Discord clients or stale command registrations pass the visible label
    # ("Project Name [No-Key] (project_id)") instead of the choice value.
    match = re.search(r"\(([^()]*)\)\s*$", raw_value)
    if match:
        project_id, project_data = find_project(match.group(1))
        if project_data:
            return project_id or match.group(1).strip(), project_data

    return raw_value, None


async def project_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    try:
        projects = panel.load_projects()
    except Exception as exc:
        print(f"[ROLE BOT] Project autocomplete failed to load projects: {type(exc).__name__}: {exc}", flush=True)
        return []

    if not isinstance(projects, dict):
        print(f"[ROLE BOT] Project autocomplete expected a dict, got {type(projects).__name__}", flush=True)
        return []

    choices = []
    current_lower = str(current or "").casefold().strip()
    for pid, pdata in projects.items():
        if not isinstance(pdata, dict):
            continue
        project_id = str(pdata.get("id") or pid).strip()
        if not project_id or len(project_id) > 100:
            continue
        name = str(pdata.get("name") or project_id)
        ptype = str(pdata.get("type", "get_role"))
        badge = "No-Key" if ptype == "get_script_no_key" else "Get-Role"
        display = f"{name} [{badge}] ({project_id})"
        if not current_lower or current_lower in project_id.casefold() or current_lower in name.casefold() or current_lower in badge.casefold():
            choices.append(app_commands.Choice(name=display[:100], value=project_id))
    return choices[:25]


async def map_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    selected_project = None
    try:
        data = interaction.data
        options = data.get("options", [])
        for opt in options:
            if opt.get("name") == "project":
                selected_project = opt.get("value")
                break
            for sub_opt in opt.get("options", []):
                if sub_opt.get("name") == "project":
                    selected_project = sub_opt.get("value")
                    break
    except Exception:
        pass

    if not selected_project:
        projects = panel.load_projects()
        selected_project = next(iter(projects.keys())) if projects else "payomboyz-hub"

    pdata = panel.get_project(selected_project)
    if not pdata:
        return []

    maps = pdata.get("maps", [])
    choices = []
    current_lower = current.lower().strip()
    for m in maps:
        mname = m.get("name", "")
        e = m.get("emoji", "🗺️")
        if not current_lower or current_lower in mname.lower():
            choices.append(app_commands.Choice(name=f"{e} {mname}"[:100], value=mname))
    return choices[:25]


async def button_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    selected_project = None
    for option in (interaction.data or {}).get("options", []):
        if option.get("name") == "project":
            selected_project = option.get("value")
            break
    if not selected_project:
        return []

    _, pdata = resolve_project_input(str(selected_project))
    if not pdata:
        return []

    needle = str(current or "").casefold().strip()
    choices = []

    def add_choice(label: str, value: str):
        if not needle or needle in label.casefold():
            choices.append(app_commands.Choice(name=label[:100], value=value))

    for index, button in enumerate(pdata.get("custom_buttons", [])):
        add_choice(f"Custom #{index + 1}: {button.get('label', 'Button')}", f"custom:{index}")

    if pdata.get("type") == "get_script_no_key" and pdata.get("map_mode") != "universal":
        for index, map_data in enumerate(pdata.get("maps", [])):
            add_choice(f"Map button: {map_data.get('name', f'Map {index + 1}')}", f"map:{index}")
        panel_buttons = pdata.get("panel_buttons", {})
        if panel_buttons.get("show_main_script", True):
            add_choice("Get Script (main button)", "builtin:main_script")
        if panel_buttons.get("show_check_maps", True):
            add_choice("Check Maps", "builtin:check_maps")
    elif pdata.get("type") == "get_script_no_key":
        if pdata.get("panel_buttons", {}).get("show_main_script", True):
            add_choice("Get Script (main button)", "builtin:main_script")
    elif pdata.get("type") == "get_role":
        panel_buttons = pdata.get("panel_buttons", {})
        require_key = pdata.get("require_key", True)
        grant_mode = pdata.get("grant_mode", "key_role" if require_key else "free_role")
        if require_key and panel_buttons.get("show_redeem_key", True):
            add_choice("Redeem Key", "builtin:redeem_key")
        elif not require_key and grant_mode == "free_role" and panel_buttons.get("show_claim_role", True):
            add_choice("Claim Role", "builtin:claim_role")
        if pdata.get("role_id") and panel_buttons.get("show_check_role", True):
            add_choice("Check Role", "builtin:check_role")
        if panel_buttons.get("show_main_script", True):
            add_choice("Get Script", "builtin:main_script")

    return choices[:25]


# =========================================================================
# 1. 📁 /create_project — สร้างโปรเจกต์ใหม่ (Requirement 1)
# =========================================================================
@role_bot.tree.command(name="create_project", description="สร้างโปรเจกต์ใหม่ วางโค้ด Loadstring และตั้งค่าระบบ (เฉพาะ Bot/Admin)")
@app_commands.describe(
    project_type="เลือกประเภทระบบ: Get-Role (มีระบบรับยศ) หรือ Get-Script-No-Key (แจกสคริปต์เลือกแมพ)",
    map_mode="เฉพาะ No-Key: เลือกแจกสคริปต์แมพเดียว หรือหลายแมพผ่านเมนู",
    role="เลือกบทบาทดิสคอร์ดสำหรับระบบ Get-Role (ค่าเริ่มต้น: VVIP Role)",
    require_key="เลือกใช้คีย์พร้อมยศ, ใช้คีย์โดยไม่รับยศ, หรือรับยศฟรี"
)
@app_commands.choices(
    project_type=[
        app_commands.Choice(name="Get-Role (ระบบรับยศดิสคอร์ด)", value="get_role"),
        app_commands.Choice(name="Get-Script-No-Key (แจกสคริปต์ฟรี เลือกแมพได้ ไม่ต้องใช้คีย์)", value="get_script_no_key"),
    ],
    map_mode=[
        app_commands.Choice(name="แมพเดียว — มีปุ่มสคริปต์หลักและปุ่มแมพ", value="single"),
        app_commands.Choice(name="หลายแมพ — แสดงปุ่มแยกตามแมพ", value="multi"),
        app_commands.Choice(name="สคริปต์ใช้ได้ทุกแมพ — ไม่มีปุ่มแยกตามเกม", value="universal"),
    ],
    require_key=[
        app_commands.Choice(name="ใช้คีย์และรับยศ (ต้องเลือก Role)", value="key_role"),
        app_commands.Choice(name="ใช้คีย์ แต่ไม่รับยศ (ไม่ต้องเลือก Role)", value="key_only"),
        app_commands.Choice(name="รับยศฟรี (ไม่ต้องใช้คีย์ ต้องเลือก Role)", value="free_role"),
        app_commands.Choice(name="ฟรีทั้งหมด (ไม่ใช้คีย์ ไม่ใช้ยศ)", value="free_open"),
    ]
)
@panel.staff_only()
async def create_project(
    interaction: discord.Interaction,
    project_type: app_commands.Choice[str],
    map_mode: Optional[app_commands.Choice[str]] = None,
    role: Optional[discord.Role] = None,
    require_key: Optional[app_commands.Choice[str]] = None
):
    grant_mode = "free_open" if project_type.value == "get_script_no_key" else (require_key.value if require_key else "key_role")
    if map_mode and map_mode.value == "universal" and project_type.value != "get_script_no_key":
        await interaction.response.send_message(
            "โหมดสคริปต์ใช้ได้ทุกแมพใช้ได้กับ Project แบบ Get-Script-No-Key เท่านั้น",
            ephemeral=True,
        )
        return
    effective_project_type = "get_script_no_key" if grant_mode == "free_open" else project_type.value
    if effective_project_type == "get_role" and grant_mode != "key_only" and role is None:
        await interaction.response.send_message(
            "เลือก Role สำหรับโหมดที่ต้องรับยศ หรือเลือก `ใช้คีย์ แต่ไม่รับยศ` เพื่อไม่ผูก Role",
            ephemeral=True,
        )
        return
    # Roleless access modes must not accidentally inherit a selected Role.
    target_role_id = role.id if role and grant_mode not in {"key_only", "free_open"} else None
    modal = panel.CreateProjectModal(
        project_type=effective_project_type,
        map_mode=(map_mode.value if map_mode else "multi") if effective_project_type == "get_script_no_key" else "single",
        role_id=target_role_id,
        grant_mode=grant_mode,
    )
    await interaction.response.send_modal(modal)


@role_bot.tree.command(name="remove_project", description="ลบ Project ที่เลือกออกจากระบบ (เฉพาะ Bot/Admin)")
@app_commands.describe(project="เลือก Project ที่ต้องการลบ")
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def remove_project(interaction: discord.Interaction, project: str):
    removed = panel.remove_project(project)
    if not removed:
        await interaction.response.send_message(
            f"❌ ไม่พบ Project `{project}` หรือบันทึกการลบไม่สำเร็จ ตรวจสอบ `/project_list` แล้วลองเลือก Project ID จากรายการ",
            ephemeral=True,
        )
        return

    if panel.get_project(removed.get("id", project)):
        await interaction.response.send_message(
            f"❌ Project `{removed.get('id', project)}` ถูกสร้างกลับจากข้อมูลเริ่มต้น กรุณารีสตาร์ตบอทหลังตรวจสอบไฟล์ projects.json",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"🗑️ ลบ Project **{removed.get('name', project)}** (`{removed.get('id', project)}`) แล้ว\n"
        "หมายเหตุ: ข้อความ Panel เดิมใน Discord จะไม่ถูกลบอัตโนมัติ ให้ลบข้อความนั้นเองหากไม่ต้องการใช้ต่อ",
        ephemeral=True,
    )


# =========================================================================
# 2. 🔑 /add_key — เพิ่มคีย์แบบ Popup Modal หลายคีย์ (Requirement 2)
# =========================================================================
@role_bot.tree.command(name="add_key", description="เพิ่มคีย์ใหม่เข้าระบบผ่าน Popup โดยใส่ได้หลายคีย์คั่นด้วย Enter หรือ , (เฉพาะ Bot/Admin)")
@app_commands.describe(project="เลือกโปรเจกต์ที่ต้องการเพิ่มคีย์ (เว้นว่างไว้สำหรับโปรเจกต์หลัก)")
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def add_key(interaction: discord.Interaction, project: Optional[str] = None):
    projects = panel.load_projects()
    pid = project or "payomboyz-hub"
    if pid not in projects:
        # ถ้าไม่มี ให้ใช้โปรเจกต์แรก
        pid = next(iter(projects.keys())) if projects else "payomboyz-hub"

    modal = panel.BulkAddKeyModal(project_id=pid)
    await interaction.response.send_modal(modal)


@role_bot.tree.command(name="add_superip", description="⚡ เพิ่ม Super Key เข้าสู่ทุกโปรเจกต์พร้อมกันในครั้งเดียว (เฉพาะ Bot/Admin)")
@panel.staff_only()
async def add_superip(interaction: discord.Interaction):
    modal = panel.BulkAddSuperIPModal()
    await interaction.response.send_modal(modal)


@role_bot.tree.command(name="add_super_ip", description="⚡ เพิ่ม Super Key เข้าสู่ทุกโปรเจกต์พร้อมกันในครั้งเดียว (เฉพาะ Bot/Admin)")
@panel.staff_only()
async def add_super_ip(interaction: discord.Interaction):
    modal = panel.BulkAddSuperIPModal()
    await interaction.response.send_modal(modal)


# =========================================================================
# 3. 🖥️ /setup_panel — ติดตั้ง Panel หน้าต่างควบคุม (Requirement 3 & 5)
# =========================================================================
@role_bot.tree.command(name="setup_panel", description="ติดตั้งกล่องข้อความ Get-Role หรือ Get-Script-No-Key (เฉพาะ Bot/Admin)")
@app_commands.describe(
    project="เลือกโปรเจกต์ที่ต้องการติดตั้งแผงควบคุม",
    channel="ห้องที่ต้องการให้บอทส่งกล่องข้อความไป (ค่าเริ่มต้น: ห้องปัจจุบัน)",
    role="บทบาทดิสคอร์ดสำหรับ Get-Role (เว้นว่างไว้จะใช้ตามที่ตั้งในโปรเจกต์)",
    title="หัวข้อของกล่องข้อความ (เว้นว่างไว้จะใช้ค่าของโปรเจกต์)",
    description="ข้อความอธิบายในกล่องข้อความ",
    color="รหัสสี Embed เช่น #FF0000 หรือ red, green, blue, gold, purple",
    image_url="ลิงก์รูปภาพแบนเนอร์ใหญ่ใน Embed",
    thumbnail_url="ลิงก์รูปภาพไอคอนขนาดเล็กมุมบนขวา"
)
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def setup_panel(
    interaction: discord.Interaction,
    project: str,
    channel: Optional[discord.TextChannel] = None,
    role: Optional[discord.Role] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None,
    image_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None
):
    projects = panel.load_projects()
    pid, pdata = resolve_project_input(project, projects)

    if not pdata:
        await interaction.response.send_message(
            f"❌ ไม่พบโปรเจกต์ `{pid}` กรุณาเลือกหนึ่งใน 3 Panel ที่ต้องการติดตั้ง",
            ephemeral=True,
        )
        return

    target_channel = channel or interaction.channel
    project_type = pdata.get("type", "get_role")
    target_role_id = None if project_type == "get_script_no_key" else (
        role.id if role else pdata.get("role_id", panel.DEFAULT_VVIP_ROLE_ID)
    )

    # ตั้งค่าคอนฟิก Embed
    cfg = pdata.get("panel_config", {})
    panel_title = title or cfg.get("title", f"{pdata.get('name', 'PAYOMBØYZ')} Panel")
    panel_desc = description or cfg.get("description", (
        "แผงควบคุมนี้สำหรับโปรเจกต์: **" + pdata.get("name", "PAYOMBØYZ HUB") + "**\n"
        "คลิกที่ปุ่มด้านล่างเพื่อดำเนินการ"
    ))
    embed_color = panel.parse_color(color or cfg.get("color", "#FF0000"))

    embed = discord.Embed(title=panel_title, description=panel_desc, color=embed_color)

    if thumbnail_url or cfg.get("thumbnail_url"):
        embed.set_thumbnail(url=thumbnail_url or cfg.get("thumbnail_url"))
    if image_url or cfg.get("image_url"):
        embed.set_image(url=image_url or cfg.get("image_url"))

    avatar_url = interaction.user.avatar.url if interaction.user.avatar else None
    user_tag = f"{interaction.user.name}#{interaction.user.discriminator}" if interaction.user.discriminator != "0" else interaction.user.name
    now_str = time.strftime("%H:%M")
    embed.set_footer(text=f"Sent by {user_tag} • วันนี้ เวลา {now_str} • {pdata.get('name', 'PAYOMBØYZ HUB')}", icon_url=avatar_url)

    # อัปเดตการบันทึก config
    pdata.setdefault("panel_config", {})
    pdata["panel_config"]["title"] = panel_title
    pdata["panel_config"]["description"] = panel_desc
    pdata["panel_config"]["color"] = color or cfg.get("color", "#FF0000")
    if image_url:
        pdata["panel_config"]["image_url"] = image_url
    if thumbnail_url:
        pdata["panel_config"]["thumbnail_url"] = thumbnail_url
    pdata["role_id"] = target_role_id
    panel.upsert_project(pdata)

    # สร้าง View ตามประเภทโปรเจกต์
    if project_type == "get_script_no_key":
        view = panel.NoKeyPanelView(pid, custom_buttons=pdata.get("custom_buttons", []))
    else:
        # Get-Role Panel (มีปุ่ม Redeem Key, Check Role, Get Script - ตัด Reset HWID และ Get Stats ออก)
        view = panel.GetRolePanelView(pid, pdata.get("default_script", panel.DEFAULT_SCRIPT), custom_buttons=pdata.get("custom_buttons", []))

    role_bot.add_view(view)

    try:
        msg = None
        project_name = str(pdata.get("name", "")).lower()
        async for old_msg in target_channel.history(limit=100):
            if old_msg.author.id != role_bot.user.id or not old_msg.embeds:
                continue
            old_title = (old_msg.embeds[0].title or "").lower()
            old_footer = (old_msg.embeds[0].footer.text or "").lower() if old_msg.embeds[0].footer else ""
            if project_name and (project_name in old_title or project_name in old_footer):
                await old_msg.edit(embed=embed, view=view)
                msg = old_msg
                break
        if msg is None:
            msg = await target_channel.send(embed=embed, view=view)
        # Keep each deployed panel addressable by its own Discord message ID.
        panel_messages = pdata.setdefault("panel_messages", {})
        panel_messages[str(msg.id)] = {
            "channel_id": target_channel.id,
            "project_id": pdata.get("id", pid),
            "type": project_type,
            "custom_buttons": list(pdata.get("custom_buttons", [])),
        }
        panel.upsert_project(pdata)
        await interaction.response.send_message(
            f"✅ **ติดตั้งหน้าต่างสำเร็จเรียบร้อย!**\n"
            f"• **โปรเจกต์:** `{pdata.get('name')}` (`{pid}`)\n"
            f"• **ประเภท:** `{project_type}`\n"
            f"• **ห้อง:** {target_channel.mention}\n"
            f"• **Message ID:** `{msg.id}`",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ บอทไม่มีสิทธิ์ส่งข้อความในห้อง {target_channel.mention}",
        )


@role_bot.tree.command(name="create_panel", description="ติดตั้งแผงควบคุมของโปรเจกต์ (Get-Role หรือ No-Key) พร้อมคลังคีย์แยก (เฉพาะ Bot/Admin)")
@app_commands.describe(
    project="เลือกโปรเจกต์ที่ต้องการติดตั้งแผงควบคุม",
    channel="ห้องที่ต้องการให้บอทส่งกล่องข้อความไป (ค่าเริ่มต้น: ห้องปัจจุบัน)",
    role="บทบาทดิสคอร์ดสำหรับ Get-Role (เว้นว่างไว้จะใช้ตามที่ตั้งในโปรเจกต์)",
    title="หัวข้อของกล่องข้อความ (เว้นว่างไว้จะใช้ค่าของโปรเจกต์)",
    description="ข้อความอธิบายในกล่องข้อความ",
    color="รหัสสี Embed เช่น #FF0000 หรือ red, green, blue, gold, purple",
    image_url="ลิงก์รูปภาพแบนเนอร์ใหญ่ใน Embed",
    thumbnail_url="ลิงก์รูปภาพไอคอนขนาดเล็กมุมบนขวา"
)
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def create_panel(
    interaction: discord.Interaction,
    project: str,
    channel: Optional[discord.TextChannel] = None,
    role: Optional[discord.Role] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None,
    image_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None
):
    await setup_panel(
        interaction=interaction,
        project=project,
        channel=channel,
        role=role,
        title=title,
        description=description,
        color=color,
        image_url=image_url,
        thumbnail_url=thumbnail_url
    )



# =========================================================================
# 4. 📝 /embed create & /embed edit — จัดการ Embed (Requirement 4)
# =========================================================================
embed_group = app_commands.Group(name="embed", description="คำสั่งจัดการสร้างและแก้ไขข้อความ Embed")


@embed_group.command(name="create", description="เปิดหน้าต่างสร้างกล่องข้อความ Embed แบบละเอียด (เฉพาะ Bot/Admin)")
@app_commands.describe(channel="เลือกห้องที่ต้องการส่ง Embed ไป (ค่าเริ่มต้น: ห้องปัจจุบัน)")
@panel.staff_only()
async def embed_create(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    target_channel = channel or interaction.channel
    modal = panel.EmbedCreateModal(channel=target_channel)
    await interaction.response.send_modal(modal)


@embed_group.command(name="edit", description="แก้ไขข้อความ Embed ที่ส่งไปแล้วด้วย Message ID (เฉพาะ Bot/Admin)")
@app_commands.describe(
    message_id="ID ของข้อความ Embed ที่ต้องการแก้ไข",
    channel="ห้องที่ข้อความนั้นตั้งอยู่ (ค่าเริ่มต้น: ห้องปัจจุบัน)"
)
@panel.staff_only()
async def embed_edit(interaction: discord.Interaction, message_id: str, channel: Optional[discord.TextChannel] = None):
    target_channel = channel or interaction.channel
    try:
        msg_id_int = int(message_id.strip())
        message = await target_channel.fetch_message(msg_id_int)
    except Exception:
        await interaction.response.send_message(f"❌ ไม่พบข้อความ ID `{message_id}` ในห้อง {target_channel.mention}", ephemeral=True)
        return

    if not message.embeds:
        await interaction.response.send_message("❌ ข้อความเป้าหมายไม่มีกล่อง Embed", ephemeral=True)
        return

    old_embed = message.embeds[0]
    initial_title = old_embed.title or ""
    initial_desc = old_embed.description or ""
    initial_color = f"#{old_embed.color.value:06x}" if old_embed.color else "#FF0000"
    initial_image = old_embed.image.url if old_embed.image else ""
    initial_footer = old_embed.footer.text if old_embed.footer else ""

    modal = panel.EmbedEditModal(
        message=message,
        initial_title=initial_title,
        initial_desc=initial_desc,
        initial_color=initial_color,
        initial_image=initial_image,
        initial_footer=initial_footer
    )
    await interaction.response.send_modal(modal)

role_bot.tree.add_command(embed_group)


# =========================================================================
# 5. 🗺️ /map GROUP & POPUP CONFIG — จัดการแมพใน No-Key (Requirement 5 & Map Popups)
# =========================================================================
map_group = app_commands.Group(name="map", description="คำสั่งจัดการแมพและสคริปต์แยกแต่ละเกม")


@map_group.command(name="add", description="เพิ่มแมพใหม่และวาง Loadstring ผ่านหน้าต่าง Popup Modal (เฉพาะ Bot/Admin)")
@app_commands.describe(project="เลือกโปรเจกต์ที่ต้องการเพิ่มแมพ")
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def map_sub_add(interaction: discord.Interaction, project: str):
    pdata = panel.get_project(project)
    if not pdata:
        await interaction.response.send_message(f"❌ ไม่พบโปรเจกต์ `{project}`", ephemeral=True)
        return
    modal = panel.MapAddModal(project_id=pdata["id"])
    await interaction.response.send_modal(modal)


@map_group.command(name="edit", description="แก้ไขข้อมูลแมพหรือเปลี่ยน Loadstring ผ่านหน้าต่าง Popup (เฉพาะ Bot/Admin)")
@app_commands.describe(
    project="เลือกโปรเจกต์",
    map_name="เลือกชื่อแมพที่ต้องการแก้ไข"
)
@app_commands.autocomplete(project=project_autocomplete, map_name=map_autocomplete)
@panel.staff_only()
async def map_sub_edit(interaction: discord.Interaction, project: str, map_name: str):
    pdata = panel.get_project(project)
    if not pdata:
        await interaction.response.send_message(f"❌ ไม่พบโปรเจกต์ `{project}`", ephemeral=True)
        return

    maps = pdata.get("maps", [])
    target_map = None
    for m in maps:
        if m.get("name", "").lower() == map_name.strip().lower():
            target_map = m
            break

    if not target_map:
        await interaction.response.send_message(f"❌ ไม่พบแมพชื่อ **{map_name}** ในโปรเจกต์ `{pdata.get('name')}`", ephemeral=True)
        return

    modal = panel.MapEditModal(project_id=pdata["id"], old_map_name=target_map["name"], current_data=target_map)
    await interaction.response.send_modal(modal)


@map_group.command(name="remove", description="ลบแมพออกจากระบบ (เฉพาะ Bot/Admin)")
@app_commands.describe(
    project="เลือกโปรเจกต์",
    map_name="เลือกชื่อแมพที่ต้องการลบ"
)
@app_commands.autocomplete(project=project_autocomplete, map_name=map_autocomplete)
@panel.staff_only()
async def map_sub_remove(interaction: discord.Interaction, project: str, map_name: str):
    ok, msg, pdata = panel.remove_map_from_project(project, map_name)
    if ok:
        await interaction.response.send_message(
            f"🗑️ {msg} ในโปรเจกต์ `{pdata.get('name')}` (คงเหลือ {len(pdata.get('maps', []))} แมพ)",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(f"⚠️ {msg}", ephemeral=True)


@map_group.command(name="list", description="ดูรายการแมพทั้งหมดที่ตั้งค่าไว้ในโปรเจกต์ (เฉพาะ Bot/Admin)")
@app_commands.describe(project="เลือกโปรเจกต์ที่ต้องการตรวจสอบ")
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def map_sub_list(interaction: discord.Interaction, project: str):
    pdata = panel.get_project(project)
    if not pdata:
        await interaction.response.send_message(f"❌ ไม่พบโปรเจกต์ `{project}`", ephemeral=True)
        return

    maps = pdata.get("maps", [])
    embed = discord.Embed(
        title=f"🗺️ รายการแมพของโปรเจกต์: {pdata.get('name')}",
        color=discord.Color.teal()
    )
    if not maps:
        embed.description = "ยังไม่มีการเพิ่มแมพใดๆ ในโปรเจกต์นี้ (ใช้คำสั่ง `/map add` เพื่อเพิ่มแมพผ่าน Popup)"
    else:
        for i, m in enumerate(maps, 1):
            e = m.get("emoji", "🗺️")
            desc = m.get("description", "พร้อมใช้งาน")
            script_preview = m.get("script", "")[:60]
            embed.add_field(
                name=f"{i}. {e} {m.get('name')}",
                value=f"• คำอธิบาย: `{desc}`\n• โค้ด: `{script_preview}...`",
                inline=False
            )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@map_group.command(name="check", description="ตรวจสอบรายชื่อแมพที่รองรับในโปรเจกต์ (สำหรับสมาชิกทุกคน)")
@app_commands.describe(project="เลือกโปรเจกต์ที่ต้องการตรวจสอบ")
@app_commands.autocomplete(project=project_autocomplete)
async def map_sub_check(interaction: discord.Interaction, project: Optional[str] = None):
    pid = project or "payomb_yz_hub_"
    pdata = panel.get_project(pid)
    if not pdata:
        projects = panel.load_projects()
        pid = next(iter(projects.keys())) if projects else "payomboyz-hub"
        pdata = panel.get_project(pid)

    maps = pdata.get("maps", []) if pdata else []
    pname = pdata.get("name", "PAYOMBØYZ HUB") if pdata else "PAYOMBØYZ HUB"

    embed = discord.Embed(
        title=f"🗺️ รายการแมพที่รองรับ: {pname}",
        color=discord.Color.teal()
    )
    if not maps:
        embed.description = "⚠️ ขณะนี้ยังไม่มีรายการแมพที่เพิ่มในระบบ"
    else:
        embed.description = (
            f"โปรเจกต์ **{pname}** รองรับเกมและแมพทั้งหมด **{len(maps)}** แมพ:\n"
            f"👇 *เลือกแมพใช้ปุ่มตามชื่อแมพ หรือคำสั่ง /get_map_script เพื่อรับไฟล์สคริปต์*\n"
        )
        for i, m in enumerate(maps, 1):
            e = m.get("emoji", "🗺️")
            desc = m.get("description", "พร้อมใช้งาน (Active)")
            embed.add_field(
                name=f"{i}. {e} {m.get('name')}",
                value=f"• สถานะ: `🟢 พร้อมใช้งาน`\n• รายละเอียด: {desc}",
                inline=False
            )
    embed.set_footer(text=f"PAYOMBØYZ HUB • ตรวจสอบล่าสุดเมื่อเวลา {time.strftime('%H:%M')}")
    await interaction.response.send_message(embed=embed, ephemeral=True)

role_bot.tree.add_command(map_group)


# --- Standalone /check_map สำหรับสมาชิกทุกคน ---
@role_bot.tree.command(name="check_map", description="ตรวจสอบรายชื่อเกมและแมพที่รองรับในโปรเจกต์ (สำหรับสมาชิกทุกคน)")
@app_commands.describe(project="เลือกโปรเจกต์ที่ต้องการตรวจสอบ")
@app_commands.autocomplete(project=project_autocomplete)
async def check_map(interaction: discord.Interaction, project: Optional[str] = None):
    await map_sub_check(interaction, project)


@role_bot.tree.command(name="get_map_script", description="รับไฟล์สคริปต์ของแมพที่เลือก โดยไม่ใช้ buttons")
@app_commands.describe(project="โปรเจกต์", map_name="ชื่อแมพที่ต้องการรับสคริปต์")
@app_commands.autocomplete(project=project_autocomplete, map_name=map_autocomplete)
async def get_map_script(interaction: discord.Interaction, project: str, map_name: str):
    pdata = panel.get_project(project)
    if not pdata:
        await interaction.response.send_message(f"❌ ไม่พบโปรเจกต์ `{project}`", ephemeral=True)
        return

    target = next(
        (m for m in pdata.get("maps", []) if m.get("name", "").casefold() == map_name.strip().casefold()),
        None,
    )
    if not target:
        await interaction.response.send_message(f"❌ ไม่พบแมพ `{map_name}` ในโปรเจกต์นี้", ephemeral=True)
        return

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in target.get("name", "map_script"))
    file = discord.File(io.BytesIO(target.get("script", "").encode("utf-8")), filename=f"{safe_name or 'map_script'}.lua")
    await interaction.response.send_message(
        content=f"📜 สคริปต์ของ **{target.get('name', map_name)}**",
        file=file,
        ephemeral=True,
    )


# --- คำสั่งเดิม /map_add, /map_remove, /map_list เพื่อความต่อเนื่อง (Backward Compatibility) ---
@role_bot.tree.command(name="map_add", description="เพิ่มแมพใหม่ผ่าน Popup Modal หรือระบุสคริปต์โดยตรง (เฉพาะ Bot/Admin)")
@app_commands.describe(
    project="เลือกโปรเจกต์ที่ต้องการเพิ่มแมพ",
    map_name="ชื่อเกมหรือแมพ (เว้นว่างไว้เพื่อเปิด Popup Modal วางโค้ดขนาดใหญ่)",
    script="โค้ด Loadstring (เว้นว่างไว้เพื่อเปิด Popup)",
    emoji="อิโมจิประจำแมพ",
    description="คำอธิบายแมพสั้นๆ"
)
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def map_add(
    interaction: discord.Interaction,
    project: str,
    map_name: Optional[str] = None,
    script: Optional[str] = None,
    emoji: Optional[str] = None,
    description: Optional[str] = None
):
    pdata = panel.get_project(project)
    if not pdata:
        await interaction.response.send_message(f"❌ ไม่พบโปรเจกต์ `{project}`", ephemeral=True)
        return

    # หากไม่ได้กรอกชื่อแมพหรือสคริปต์มา ให้เด้ง Popup Modal ทันที!
    if not map_name or not script:
        modal = panel.MapAddModal(project_id=pdata["id"])
        await interaction.response.send_modal(modal)
        return

    ok, msg, pdata = panel.add_map_to_project(pdata["id"], map_name, script, emoji, description)
    await interaction.response.send_message(
        f"✅ {msg} ในโปรเจกต์ `{pdata.get('name')}` เรียบร้อยแล้ว! (แมพทั้งหมด: {len(pdata.get('maps', []))} แมพ)",
        ephemeral=True
    )


@role_bot.tree.command(name="map_remove", description="ลบแมพออกจากระบบเลือกแมพ (เฉพาะ Bot/Admin)")
@app_commands.describe(
    project="เลือกโปรเจกต์",
    map_name="ชื่อแมพที่ต้องการลบ"
)
@app_commands.autocomplete(project=project_autocomplete, map_name=map_autocomplete)
@panel.staff_only()
async def map_remove(interaction: discord.Interaction, project: str, map_name: str):
    await map_sub_remove(interaction, project, map_name)


@role_bot.tree.command(name="map_list", description="ดูรายการแมพทั้งหมดที่ตั้งค่าไว้ในโปรเจกต์ (เฉพาะ Bot/Admin)")
@app_commands.describe(project="เลือกโปรเจกต์ที่ต้องการตรวจสอบ")
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def map_list(interaction: discord.Interaction, project: str):
    await map_sub_list(interaction, project)


# =========================================================================
# ⚙️ /project_config — ปรับแต่งการตั้งค่าโปรเจกต์แบบ Real-time
# =========================================================================
@role_bot.tree.command(name="project_config", description="ดูและปรับแต่งการตั้งค่าโปรเจกต์ (สลับโหมดคีย์/เปลี่ยนยศ/แก้ชื่อ/แก้สคริปต์หลัก) (เฉพาะ Bot/Admin)")
@app_commands.describe(
    project="เลือกโปรเจกต์ที่ต้องการปรับแต่ง",
    require_key="สลับโหมดการใช้คีย์ (เฉพาะ Get-Role)",
    role="เปลี่ยนบทบาทที่เชื่อมโยงกับโปรเจกต์",
    new_name="เปลี่ยนชื่อโปรเจกต์",
    new_script="เปลี่ยนโค้ด Loadstring หลัก (สำหรับปุ่ม Get Script)"
)
@app_commands.choices(
    require_key=[
        app_commands.Choice(name="เปิดระบบคีย์ (ต้องกรอกคีย์เพื่อรับยศ)", value=1),
        app_commands.Choice(name="ปิดระบบคีย์ (รับยศฟรีทันทีไม่ต้องใช้คีย์)", value=0),
    ]
)
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def project_config(
    interaction: discord.Interaction,
    project: str,
    require_key: Optional[app_commands.Choice[int]] = None,
    role: Optional[discord.Role] = None,
    new_name: Optional[str] = None,
    new_script: Optional[str] = None,
):
    pdata = panel.get_project(project)
    if not pdata:
        await interaction.response.send_message(f"❌ ไม่พบโปรเจกต์ `{project}`", ephemeral=True)
        return

    changes = []
    if require_key is not None:
        pdata["require_key"] = bool(require_key.value)
        status_str = "เปิดระบบคีย์ (Redeem Key)" if pdata["require_key"] else "ปิดระบบคีย์ (รับยศฟรี Claim Role)"
        changes.append(f"• **ระบบคีย์:** `{status_str}`")

    if role is not None:
        pdata["role_id"] = role.id
        changes.append(f"• **บทบาทเชื่อมโยง:** {role.mention}")

    if new_name is not None and new_name.strip():
        old_name = pdata.get("name")
        pdata["name"] = new_name.strip()
        changes.append(f"• **ชื่อโปรเจกต์:** `{old_name}` ➔ `{new_name.strip()}`")

    if new_script is not None and new_script.strip():
        old_script = pdata.get("default_script", "")
        pdata["default_script"] = new_script.strip()
        for m in pdata.get("maps", []):
            if m.get("name") == "Main Map" or m.get("script") == old_script:
                m["script"] = new_script.strip()
        preview = new_script.strip()
        if len(preview) > 60:
            preview = preview[:57] + "..."
        changes.append(f"• **สคริปต์หลัก (Get Script):** `{preview}`")

    panel.upsert_project(pdata)

    embed = discord.Embed(
        title=f"⚙️ การตั้งค่าโปรเจกต์: {pdata.get('name')}",
        color=discord.Color.blue()
    )
    if changes:
        embed.description = "✅ **อัปเดตการตั้งค่าสำเร็จ:**\n" + "\n".join(changes) + "\n\n💡 หากติดตั้งหน้าต่างแผงควบคุมไว้ แนะนำให้รัน `/setup_panel` ใหม่อีกครั้งเพื่อให้ปุ่มบนแผงอัปเดต"
    else:
        ptype = pdata.get("type", "get_role")
        r_key = pdata.get("require_key", True)
        maps = pdata.get("maps", [])
        embed.description = (
            f"• **ID:** `{pdata.get('id')}`\n"
            f"• **ประเภท:** `{ptype}`\n"
            f"• **โหมดคีย์ (require_key):** `{'ต้องใช้คีย์ (Redeem Key)' if r_key else 'รับยศฟรี (Claim Role)'}`\n"
            f"• **บทบาทเชื่อมโยง:** <@&{pdata.get('role_id')}>\n"
            f"• **จำนวนแมพที่รองรับ:** `{len(maps)}` แมพ\n\n"
            f"💡 หากต้องการแก้ไข ให้เลือก parameter ในคำสั่ง `/project_config` ได้ตลอดเวลา"
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# =========================================================================
# 6. 🛒 /ad & /add_button — ปุ่มลิงก์สั่งซื้อ & ปุ่ม Action เสริม (Requirement 6 & 7)
# =========================================================================
async def resolve_panel_project(
    interaction: discord.Interaction,
    message_id: str,
    project_hint: Optional[str] = None,
    channel: Optional[discord.TextChannel] = None,
) -> tuple[Optional[dict], Optional[discord.Message], str]:
    """Resolve the project from the selected panel message, not from a default project."""
    target_channel = channel or interaction.channel
    try:
        message = await target_channel.fetch_message(int(message_id.strip()))
    except (ValueError, discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None, None, f"ไม่พบ Panel message ID `{message_id}` ในห้อง {target_channel.mention}"

    if not role_bot.user or message.author.id != role_bot.user.id:
        return None, None, "message_id นี้ไม่ใช่ข้อความ Panel ของ Get-ROLE bot"

    projects = panel.load_projects()

    # Message ID is authoritative: separate duplicate panels can share a project name
    # without ever routing an update to another message.
    for pdata in projects.values():
        registered = pdata.get("panel_messages", {})
        if str(message.id) in registered:
            return pdata, message, ""

    if project_hint and project_hint.strip():
        project = panel.get_project(project_hint.strip())
        if project:
            return project, message, ""
        return None, None, f"ไม่พบโปรเจกต์ `{project_hint.strip()}`"

    footer = (message.embeds[0].footer.text if message.embeds and message.embeds[0].footer else "").lower()
    title = (message.embeds[0].title if message.embeds else "").lower()
    component_ids = []
    for row in message.components:
        for component in row.children:
            custom_id = getattr(component, "custom_id", None)
            if custom_id:
                component_ids.append(custom_id.lower())

    for pid, pdata in projects.items():
        name = str(pdata.get("name", "")).lower()
        if (
            pid.lower() in component_ids
            or any(pid.lower() in cid for cid in component_ids)
            or (name and (name in footer or name in title))
        ):
            return pdata, message, ""

    return None, None, "ระบบหาโปรเจกต์จาก Panel นี้ไม่พบ กรุณาระบุ project เพิ่มเติม"


async def refresh_panel_message(
    interaction: discord.Interaction,
    pdata: dict,
    message_id: str,
    channel: Optional[discord.TextChannel] = None,
) -> tuple[bool, str]:
    """Refresh only the selected panel message instead of creating a duplicate panel."""
    target_channel = channel or interaction.channel
    try:
        message = await target_channel.fetch_message(int(message_id.strip()))
    except (ValueError, discord.NotFound, discord.Forbidden, discord.HTTPException):
        return False, f"ไม่พบ Panel message ID `{message_id}` ในห้อง {target_channel.mention}"

    if message.author.id != role_bot.user.id:
        return False, "message_id นี้ไม่ใช่ข้อความ Panel ของ Get-ROLE bot"

    project_id = pdata.get("id", "")
    panel_record = pdata.get("panel_messages", {}).get(str(message.id), {})
    custom_buttons = pdata.get("custom_buttons", [])
    if pdata.get("type", "get_role") == "get_script_no_key":
        view = panel.NoKeyPanelView(project_id, custom_buttons=custom_buttons)
    else:
        view = panel.GetRolePanelView(
            project_id,
            pdata.get("default_script", panel.DEFAULT_SCRIPT),
            custom_buttons=custom_buttons,
        )

    role_bot.add_view(view)
    try:
        await message.edit(view=view)
    except discord.Forbidden:
        return False, "Bot lacks permission to edit this panel."
    except discord.HTTPException as exc:
        return False, f"Discord rejected the panel update ({type(exc).__name__}: {exc})"
    panel_record["custom_buttons"] = list(custom_buttons or [])
    pdata.setdefault("panel_messages", {})[str(message.id)] = panel_record
    panel.upsert_project(pdata)
    return True, f"อัปเดตปุ่มใน Panel message `{message_id}` แล้ว"


async def refresh_project_panels(interaction: discord.Interaction, pdata: dict) -> tuple[int, list[str]]:
    """Apply current project button configuration to every registered panel message."""
    refreshed = 0
    errors = []
    for message_id, record in list(pdata.get("panel_messages", {}).items()):
        channel_id = record.get("channel_id") if isinstance(record, dict) else None
        try:
            numeric_channel_id = int(channel_id) if channel_id else None
        except (TypeError, ValueError):
            errors.append(f"message {message_id}: invalid channel ID")
            continue
        channel = interaction.client.get_channel(numeric_channel_id) if numeric_channel_id else None
        if channel is None and channel_id:
            try:
                channel = await interaction.client.fetch_channel(numeric_channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                channel = None
        if channel is None:
            errors.append(f"message {message_id}: channel not found")
            continue
        ok, result = await refresh_panel_message(interaction, pdata, str(message_id), channel)
        if ok:
            refreshed += 1
        else:
            errors.append(result)
    return refreshed, errors


@role_bot.tree.command(name="ad", description="เพิ่มปุ่มลิงก์สั่งซื้อ/เปิดเว็บไซต์ เข้าไปในหน้าต่างควบคุม (เฉพาะ Bot/Admin)")
@app_commands.describe(
    button_label="ชื่อข้อความบนปุ่ม (เช่น 🛒 สั่งซื้อสคริปต์ VVIP)",
    url="ลิงก์เว็บไซต์สั่งซื้อ หรือหน้าเว็บที่ต้องการให้เปิด",
    emoji="อิโมจิบนปุ่ม (รองรับทั้ง Unicode และ Custom Emoji จากเซิร์ฟเวอร์ดิส)",
    project="เลือก Project ที่ต้องการเก็บปุ่มนี้"
)
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def ad_button(
    interaction: discord.Interaction,
    button_label: str,
    url: str,
    project: str,
    emoji: Optional[str] = None,
):
    _, pdata = resolve_project_input(project)
    if not pdata:
        await interaction.response.send_message("❌ ต้องเลือก Project ก่อนเพิ่มปุ่ม", ephemeral=True)
        return

    if len(pdata.get("custom_buttons", [])) >= 5:
        await interaction.response.send_message("This project already has 5 custom buttons. Remove one with `/button_remove` first.", ephemeral=True)
        return
    if not button_label.strip() or len(button_label.strip()) > 80 or not url.strip().startswith(("https://", "http://")):
        await interaction.response.send_message("Button labels must be 1-80 characters and URLs must start with http:// or https://.", ephemeral=True)
        return

    new_btn = {
        "label": button_label.strip(),
        "action": "link",
        "style": "link",
        "url": url.strip(),
        "emoji": emoji.strip() if emoji else "🛒"
    }
    pdata.setdefault("custom_buttons", []).append(new_btn)
    panel.upsert_project(pdata)
    await interaction.response.defer(ephemeral=True, thinking=True)
    refreshed, errors = await refresh_project_panels(interaction, pdata)

    await interaction.followup.send(
        f"✅ เพิ่มปุ่มลิงก์ **'{button_label}'** เข้า Project `{pdata.get('name')}` แล้ว\n"
        f"Updated {refreshed} installed panel(s)." + ("\n" + "; ".join(errors[:3]) if errors else ""),
        ephemeral=True
    )


@role_bot.tree.command(name="add_button", description="เพิ่มปุ่ม Action เสริม พร้อมกำหนดสีและอิโมจิได้ตามใจชอบ (เฉพาะ Bot/Admin)")
@app_commands.describe(
    label="ชื่อข้อความบนปุ่ม",
    action="หน้าที่การทำงานของปุ่ม",
    color="สีของปุ่ม",
    emoji="อิโมจิบนปุ่ม (Unicode หรือ Custom Discord Emoji)",
    url_or_message="ลิงก์ URL (หากเลือก action: link) หรือข้อความตอบกลับ (หากเลือก action: message)",
    project="เลือก Project ที่ต้องการเก็บปุ่มนี้"
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="Link — เปิดลิงก์เว็บไซต์", value="link"),
        app_commands.Choice(name="Message — ส่งข้อความตอบกลับส่วนตัว", value="message"),
        app_commands.Choice(name="Redeem — เปิดหน้าต่างแลกคีย์", value="redeem"),
        app_commands.Choice(name="Check Role — ตรวจสอบยศ", value="check_role"),
        app_commands.Choice(name="Get Script — รับสคริปต์", value="script"),
    ],
    color=[
        app_commands.Choice(name="Green (เขียว - Success)", value="green"),
        app_commands.Choice(name="Blue (น้ำเงิน/ฟ้า - Primary)", value="blue"),
        app_commands.Choice(name="Grey (เทา - Secondary)", value="grey"),
        app_commands.Choice(name="Red (แดง - Danger)", value="red"),
    ]
)
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def add_button(
    interaction: discord.Interaction,
    label: str,
    action: app_commands.Choice[str],
    color: app_commands.Choice[str],
    project: str,
    emoji: Optional[str] = None,
    url_or_message: Optional[str] = None,
):
    _, pdata = resolve_project_input(project)
    if not pdata:
        await interaction.response.send_message("❌ ต้องเลือก Project ก่อนเพิ่มปุ่ม", ephemeral=True)
        return

    if len(pdata.get("custom_buttons", [])) >= 5:
        await interaction.response.send_message("This project already has 5 custom buttons. Remove one with `/button_remove` first.", ephemeral=True)
        return
    if not label.strip() or len(label.strip()) > 80:
        await interaction.response.send_message("Button labels must be 1-80 characters.", ephemeral=True)
        return
    if action.value == "link" and (not url_or_message or not url_or_message.strip().startswith(("https://", "http://"))):
        await interaction.response.send_message("Link buttons require a URL starting with http:// or https://.", ephemeral=True)
        return

    btn_info = {
        "label": label.strip(),
        "action": action.value,
        "style": color.value if action.value != "link" else "link",
        "emoji": emoji.strip() if emoji else None,
        "url": url_or_message.strip() if (action.value == "link" and url_or_message) else None,
        "payload": url_or_message.strip() if (action.value == "message" and url_or_message) else None,
    }
    pdata.setdefault("custom_buttons", []).append(btn_info)
    panel.upsert_project(pdata)
    await interaction.response.defer(ephemeral=True, thinking=True)
    refreshed, errors = await refresh_project_panels(interaction, pdata)

    await interaction.followup.send(
        f"✅ เพิ่มปุ่ม **'{label}'** [Action: `{action.value}`, Color: `{color.value}`] เข้า Project `{pdata.get('name')}` แล้ว\n"
        f"Updated {refreshed} installed panel(s)." + ("\n" + "; ".join(errors[:3]) if errors else ""),
        ephemeral=True
    )


@role_bot.tree.command(name="button_list", description="ดูรายการปุ่มในโปรเจกต์")
@app_commands.describe(project="โปรเจกต์ที่ต้องการดูปุ่ม")
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def button_list(interaction: discord.Interaction, project: str):
    _, pdata = resolve_project_input(project)
    if not pdata:
        await interaction.response.send_message(f"ไม่พบโปรเจกต์ `{project}`", ephemeral=True)
        return

    lines = []
    if pdata.get("type") == "get_script_no_key":
        if pdata.get("map_mode") == "universal":
            if pdata.get("panel_buttons", {}).get("show_main_script", True):
                lines.append("`builtin:main_script` - Get Script (main button)")
        else:
            for index, map_data in enumerate(pdata.get("maps", [])):
                lines.append(f"`map:{index}` - Get {map_data.get('name', f'Map {index + 1}')}")
            if pdata.get("panel_buttons", {}).get("show_main_script", True):
                lines.append("`builtin:main_script` - Get Script (main button)")
            if pdata.get("panel_buttons", {}).get("show_check_maps", True):
                lines.append("`builtin:check_maps` - Check Maps")
    for index, button in enumerate(pdata.get("custom_buttons", [])):
        lines.append(f"`custom:{index}` - {button.get('label', 'Button')} ({button.get('action', 'message')})")
    if pdata.get("type") == "get_role":
        panel_buttons = pdata.get("panel_buttons", {})
        require_key = pdata.get("require_key", True)
        grant_mode = pdata.get("grant_mode", "key_role" if require_key else "free_role")
        if require_key and panel_buttons.get("show_redeem_key", True):
            lines.append("`builtin:redeem_key` - Redeem Key")
        elif not require_key and grant_mode == "free_role" and panel_buttons.get("show_claim_role", True):
            lines.append("`builtin:claim_role` - Claim Role")
        if pdata.get("role_id") and panel_buttons.get("show_check_role", True):
            lines.append("`builtin:check_role` - Check Role")
        if panel_buttons.get("show_main_script", True):
            lines.append("`builtin:main_script` - Get Script")

    body = "\n".join(lines) if lines else "This project has no buttons."
    await interaction.response.send_message(
        f"**ปุ่มของ {pdata.get('name', pdata.get('id'))}**\n{body}\n\n"
        f"💡 **คำแนะนำการใช้งาน:**\n"
        f"• แก้ปุ่ม `custom:N` ➔ ใช้ `/button_edit` (ใส่ `custom_index` เป็นลำดับ เช่น 1 สำหรับ `custom:0`)\n"
        f"• แก้โค้ดปุ่ม `builtin:main_script` (Get Script) ➔ ใช้ `/project_config project:{pdata.get('id')} new_script:...`\n"
        f"• ลบหรือเปิด/ปิดปุ่ม ➔ ใช้ `/button_remove` หรือ `/button_restore`",
        ephemeral=True,
    )


@role_bot.tree.command(name="button_remove", description="ลบปุ่มและอัปเดต Panel ที่ติดตั้งแล้ว")
@app_commands.describe(project="โปรเจกต์", button="เลือกปุ่มที่ต้องการลบ")
@app_commands.autocomplete(project=project_autocomplete, button=button_autocomplete)
@panel.staff_only()
async def button_remove(interaction: discord.Interaction, project: str, button: str):
    _, pdata = resolve_project_input(project)
    if not pdata:
        await interaction.response.send_message(f"ไม่พบโปรเจกต์ `{project}`", ephemeral=True)
        return

    button_type, _, raw_index = button.partition(":")
    changed_label = button
    if button_type == "custom" and raw_index.isdigit():
        index = int(raw_index)
        buttons = pdata.get("custom_buttons", [])
        if index >= len(buttons):
            await interaction.response.send_message("ไม่พบปุ่มนี้แล้ว ใช้ `/button_list` ดูรายการล่าสุด", ephemeral=True)
            return
        changed_label = buttons.pop(index).get("label", f"Custom #{index + 1}")
    elif button_type == "map" and raw_index.isdigit() and pdata.get("type") == "get_script_no_key":
        index = int(raw_index)
        maps = pdata.get("maps", [])
        if index >= len(maps):
            await interaction.response.send_message("ไม่พบปุ่มแมพนี้แล้ว ใช้ `/button_list` ดูรายการล่าสุด", ephemeral=True)
            return
        changed_label = f"Get {maps.pop(index).get('name', f'Map {index + 1}') }"
    elif button == "builtin:main_script" and pdata.get("type") == "get_script_no_key":
        pdata.setdefault("panel_buttons", {})["show_main_script"] = False
        changed_label = "Get Script"
    elif button == "builtin:check_maps" and pdata.get("type") == "get_script_no_key":
        pdata.setdefault("panel_buttons", {})["show_check_maps"] = False
        changed_label = "Check Maps"
    elif button.startswith("builtin:") and pdata.get("type") == "get_role":
        flag_by_button = {
            "builtin:redeem_key": "show_redeem_key",
            "builtin:claim_role": "show_claim_role",
            "builtin:check_role": "show_check_role",
            "builtin:main_script": "show_main_script",
        }
        flag = flag_by_button.get(button)
        if not flag:
            await interaction.response.send_message("ปุ่มมาตรฐานนี้ไม่รองรับการลบ", ephemeral=True)
            return
        pdata.setdefault("panel_buttons", {})[flag] = False
        changed_label = button.removeprefix("builtin:").replace("_", " ").title()
    else:
        await interaction.response.send_message("เลือกปุ่มจาก autocomplete หรือใช้ `/button_list` ดูรายการก่อน", ephemeral=True)
        return

    panel.upsert_project(pdata)
    await interaction.response.defer(ephemeral=True, thinking=True)
    refreshed, errors = await refresh_project_panels(interaction, pdata)
    message = f"ลบปุ่ม **{changed_label}** จาก `{pdata.get('name')}` และอัปเดต Panel {refreshed} ข้อความแล้ว"
    if errors:
        message += "\nอัปเดตบาง Panel ไม่สำเร็จ: " + "; ".join(errors[:3])
    if refreshed == 0 and not pdata.get("panel_messages"):
        message += "\nยังไม่มีข้อความ Panel ที่ติดตั้งไว้ ใช้ `/setup_panel` ก่อน"
    await interaction.followup.send(message, ephemeral=True)


@role_bot.tree.command(name="button_edit", description="แก้ชื่อ ลิงก์ ข้อความ Emoji หรือสีของปุ่ม custom")
@app_commands.describe(
    project="Project",
    custom_index="ลำดับปุ่ม custom จาก `/button_list` เริ่มที่ 1",
    label="ชื่อปุ่มใหม่ ไม่เกิน 80 ตัวอักษร",
    url_or_message="URL ใหม่ของ Link หรือข้อความตอบกลับของ Message",
    emoji="Emoji ใหม่",
    color="สีปุ่มใหม่",
)
@app_commands.choices(color=[
    app_commands.Choice(name="Green", value="green"),
    app_commands.Choice(name="Blue", value="blue"),
    app_commands.Choice(name="Grey", value="grey"),
    app_commands.Choice(name="Red", value="red"),
])
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def button_edit(
    interaction: discord.Interaction,
    project: str,
    custom_index: app_commands.Range[int, 1, 25],
    label: Optional[str] = None,
    url_or_message: Optional[str] = None,
    emoji: Optional[str] = None,
    color: Optional[app_commands.Choice[str]] = None,
):
    _, pdata = resolve_project_input(project)
    buttons = pdata.get("custom_buttons", []) if pdata else []
    index = custom_index - 1
    if not pdata or index >= len(buttons):
        custom_count = len(buttons)
        hint = f" (โปรเจกต์นี้มีปุ่ม custom ทั้งหมด {custom_count} ปุ่ม: ลำดับ 1 ถึง {custom_count})" if custom_count > 0 else " (โปรเจกต์นี้ยังไม่มีปุ่ม custom)"
        await interaction.response.send_message(
            f"❌ ไม่พบปุ่ม custom ลำดับที่ `{custom_index}`{hint}\n\n"
            f"💡 **หมายเหตุ:** ปุ่มมาตรฐานอย่าง **Get Script (`builtin:main_script`)** ไม่ใช่ปุ่ม custom จึงแก้ด้วยคำสั่งนี้ไม่ได้\n"
            f"• หากต้องการแก้โค้ด Loadstring ของปุ่ม **Get Script** ➔ ให้ใช้ `/project_config project:{project} new_script:<โค้ดใหม่>`\n"
            f"• ใช้ `/button_list` เพื่อตรวจสอบรายชื่อปุ่มทั้งหมด",
            ephemeral=True
        )
        return
    if not any(value is not None for value in (label, url_or_message, emoji, color)):
        await interaction.response.send_message("กรอกอย่างน้อยหนึ่งช่องที่ต้องการแก้", ephemeral=True)
        return

    button = buttons[index]
    if label is not None:
        if not label.strip() or len(label.strip()) > 80:
            await interaction.response.send_message("ชื่อปุ่มต้องมี 1–80 ตัวอักษร", ephemeral=True)
            return
        button["label"] = label.strip()
    if emoji is not None:
        button["emoji"] = emoji.strip() or None
    if color is not None and button.get("action") != "link":
        button["style"] = color.value
    if url_or_message is not None:
        if button.get("action") == "link":
            if not url_or_message.strip().startswith(("https://", "http://")):
                await interaction.response.send_message("URL ต้องขึ้นต้นด้วย http:// หรือ https://", ephemeral=True)
                return
            button["url"] = url_or_message.strip()
        elif button.get("action") == "message":
            button["payload"] = url_or_message.strip()
        else:
            await interaction.response.send_message("Action นี้ไม่มีช่อง URL หรือข้อความให้แก้", ephemeral=True)
            return

    panel.upsert_project(pdata)
    await interaction.response.defer(ephemeral=True, thinking=True)
    refreshed, errors = await refresh_project_panels(interaction, pdata)
    message = f"แก้ปุ่ม custom ลำดับ {custom_index} ใน `{pdata.get('name')}` และอัปเดต Panel {refreshed} ข้อความแล้ว"
    if errors:
        message += "\nอัปเดตบาง Panel ไม่สำเร็จ: " + "; ".join(errors[:3])
    await interaction.followup.send(message, ephemeral=True)


@role_bot.tree.command(name="button_restore", description="คืนปุ่ม Get Script และ Check Maps ที่ซ่อนไว้")
@app_commands.describe(project="โปรเจกต์ที่ต้องการคืนปุ่มมาตรฐาน")
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def button_restore(interaction: discord.Interaction, project: str):
    _, pdata = resolve_project_input(project)
    if not pdata:
        await interaction.response.send_message(f"ไม่พบโปรเจกต์ `{project}`", ephemeral=True)
        return
    panel_buttons = pdata.setdefault("panel_buttons", {})
    panel_buttons["show_main_script"] = True
    panel_buttons["show_check_maps"] = True
    panel_buttons["show_redeem_key"] = True
    panel_buttons["show_claim_role"] = True
    panel_buttons["show_check_role"] = True
    panel.upsert_project(pdata)
    await interaction.response.defer(ephemeral=True, thinking=True)
    refreshed, errors = await refresh_project_panels(interaction, pdata)
    message = f"คืนปุ่มมาตรฐานและอัปเดต Panel {refreshed} ข้อความแล้ว"
    if errors:
        message += "\nอัปเดตบาง Panel ไม่สำเร็จ: " + "; ".join(errors[:3])
    await interaction.followup.send(message, ephemeral=True)


# =========================================================================
# 7. 🔑 CHECK KEY & KEY STATS (คำสั่งตรวจสอบคีย์)
# =========================================================================
@role_bot.tree.command(name="check_key", description="ตรวจสอบสถานะของคีย์ VVIP (เฉพาะ Bot/Admin)")
@app_commands.describe(
    key="รหัสคีย์ที่ต้องการตรวจสอบ",
    project="เลือกโปรเจกต์ (เว้นว่างไว้จะตรวจสอบทั้งระบบ)"
)
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def check_key(interaction: discord.Interaction, key: str, project: Optional[str] = None):
    clean_key = key.strip()
    if clean_key == panel.SPECIAL_KEY:
        await interaction.response.send_message(
            f"💎 คีย์ `{clean_key}` เป็น **คีย์พิเศษ (SPECIAL VVIP)** สามารถใช้งานซ้ำได้ตลอดเวลา",
            ephemeral=True
        )
        return

    pid = project or "payomboyz-hub"
    pdata = panel.get_project(pid)
    proj_keys = pdata.get("keys", {}) if pdata else {}

    is_found = False
    is_active = False

    if clean_key in proj_keys:
        is_found = True
        is_active = proj_keys[clean_key]
    elif project is None and clean_key in panel.vvip_keys:
        is_found = True
        is_active = panel.vvip_keys[clean_key]

    if is_found:
        if is_active:
            await interaction.response.send_message(f"🟢 คีย์ `{clean_key}` **พร้อมใช้งาน** (ยังไม่ถูก Redeem)", ephemeral=True)
        else:
            await interaction.response.send_message(f"🔒 คีย์ `{clean_key}` **ถูกใช้งานไปแล้ว** (Redeemed)", ephemeral=True)
    else:
        p_label = f"ในโปรเจกต์ `{pdata.get('name', pid)}`" if project else "ในฐานข้อมูลระบบ"
        await interaction.response.send_message(f"❌ ไม่พบคีย์ `{clean_key}` {p_label}", ephemeral=True)


@role_bot.tree.command(name="key_stats", description="ดูสถิติคีย์ทั้งหมดของระบบ PAYOMBØYZ HUB (เฉพาะ Bot/Admin)")
@app_commands.describe(project="เลือกโปรเจกต์")
@app_commands.autocomplete(project=project_autocomplete)
@panel.staff_only()
async def key_stats(interaction: discord.Interaction, project: Optional[str] = None):
    pid = project or "payomboyz-hub"
    pdata = panel.get_project(pid)
    proj_keys = pdata.get("keys", {}) if pdata else {}

    total = len(proj_keys)
    available = sum(1 for v in proj_keys.values() if v is True)
    used = total - available

    embed = discord.Embed(
        title=f"📊 ข้อมูลสถิติคีย์: {pdata.get('name') if pdata else 'PAYOMBØYZ HUB'}",
        color=discord.Color.gold()
    )
    embed.add_field(name="📦 คีย์ทั้งหมด", value=f"`{total:,}` คีย์", inline=True)
    embed.add_field(name="✅ คีย์พร้อมใช้งาน", value=f"`{available:,}` คีย์", inline=True)
    embed.add_field(name="🔒 คีย์ที่ใช้แล้ว", value=f"`{used:,}` คีย์", inline=True)
    embed.add_field(name="💎 คีย์พิเศษ (ใช้ซ้ำได้)", value=f"`{panel.SPECIAL_KEY}`", inline=False)
    embed.set_footer(text=f"Requested by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# =========================================================================
# 🌐 SCRIPTCENTER SHOP & KEY SLASH COMMANDS
# =========================================================================
@role_bot.tree.command(name="panel", description="เปิดแผงควบคุมระบบคีย์ ScriptCenter (ผูกคีย์, วันหมดอายุ, รี HWID, รับโหลดเดอร์)")
async def cmd_panel(interaction: discord.Interaction):
    """คำสั่งเปิดแผงควบคุมคีย์ของร้าน (เหมือนบอทต้นฉบับ)"""
    await interaction.response.defer(ephemeral=False)
    embed, view = await panel.build_scriptcenter_panel_message()
    await interaction.followup.send(embed=embed, view=view)


@role_bot.tree.command(name="sc_panel", description="ติดตั้งแผงควบคุม ScriptCenter Key Panel ลงห้องที่เลือก (เฉพาะ Bot/Admin)")
@app_commands.describe(
    channel="เลือกห้อง Text Channel สำหรับส่งแผงควบคุม (เว้นว่างไว้จะส่งห้องปัจจุบัน)",
    role="เลือกบทบาท Discord ที่จะมอบเมื่อผู้ใช้ผูกคีย์สำเร็จ (ค่าเริ่มต้น: VVIP Role)"
)
@panel.staff_only()
async def cmd_sc_panel(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    role: Optional[discord.Role] = None
):
    target_channel = channel or interaction.channel
    target_role_id = role.id if role else panel.DEFAULT_VVIP_ROLE_ID
    embed, view = await panel.build_scriptcenter_panel_message(role_id=target_role_id)
    try:
        msg = await target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ ติดตั้งแผงควบคุม ScriptCenter ลงใน {target_channel.mention} เรียบร้อยแล้ว! (Message ID: `{msg.id}`)",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ ส่งข้อความไม่สำเร็จ: {e}", ephemeral=True)


@role_bot.tree.command(name="check_expiry", description="ตรวจสอบวันหมดอายุและสถานะคีย์ของคุณ (หรือของสมาชิกอื่นสำหรับแอดมิน)")
@app_commands.describe(user="เลือกผู้ใช้ที่ต้องการตรวจสอบ (เฉพาะ Admin)")
async def cmd_check_expiry(interaction: discord.Interaction, user: Optional[discord.User] = None):
    sc = get_sc_client()
    if not sc.is_configured():
        await interaction.response.send_message("❌ ยังไม่ได้เชื่อมต่อ ScriptCenter API ในบอท โปรดตั้งค่าผ่าน `/sc_config` หรือใน `.env`", ephemeral=True)
        return

    is_staff = panel.is_authorized_staff(interaction.user)
    target = user if (user and is_staff) else interaction.user

    await interaction.response.defer(ephemeral=True)
    res = await sc.check_expiry(str(target.id))
    if res.get("ok"):
        keys = res.get("keys", [])
        txt = sc.format_expiry_text(keys)
        embed = discord.Embed(
            title=f"⏳ ข้อมูลวันหมดอายุ: {target.display_name}",
            description=txt,
            color=discord.Color.green() if keys else discord.Color.gold()
        )
        embed.set_footer(text=f"User ID: {target.id}")
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(f"❌ {res.get('message', 'ไม่สามารถตรวจสอบวันหมดอายุได้')}", ephemeral=True)


@role_bot.tree.command(name="my_keys", description="ตรวจสอบรายการ License Key ทั้งหมดที่ผูกไว้กับบัญชี Discord ของคุณ")
async def cmd_my_keys(interaction: discord.Interaction):
    sc = get_sc_client()
    if not sc.is_configured():
        await interaction.response.send_message("❌ ยังไม่ได้เชื่อมต่อ ScriptCenter API ในบอท โปรดตั้งค่าผ่าน `/sc_config` หรือใน `.env`", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    res = await sc.get_my_keys(str(interaction.user.id))
    if res.get("ok"):
        keys = res.get("keys", [])
        if not keys:
            msg = res.get("message") or "ยังไม่มีคีย์ที่ผูกกับบัญชีนี้"
            embed = discord.Embed(
                title="📦 คีย์ของฉัน (My Keys)",
                description=f"⚠️ {msg}\n\n💡 กดปุ่ม **ผูกคีย์** หรือใช้แผงควบคุมเพื่อเชื่อมต่อ License Key",
                color=discord.Color.gold()
            )
        else:
            lines = [f"• `{k.get('key', k) if isinstance(k, dict) else k}`" for k in keys]
            embed = discord.Embed(
                title=f"📦 คีย์ของฉัน ({len(keys)} คีย์)",
                description="\n".join(lines),
                color=discord.Color.blue()
            )
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(f"❌ {res.get('message', 'ไม่สามารถดึงข้อมูลคีย์ได้')}", ephemeral=True)


@role_bot.tree.command(name="reset_hwid", description="รีเซ็ต HWID ของคีย์คุณ เพื่อเปลี่ยนเครื่องใช้งาน")
@app_commands.describe(key="กรอก License Key ที่ต้องการรีเซ็ต (เว้นว่างไว้เพื่อเปิดหน้าต่าง Popup)")
async def cmd_reset_hwid(interaction: discord.Interaction, key: Optional[str] = None):
    sc = get_sc_client()
    if not sc.is_configured():
        await interaction.response.send_message("❌ ยังไม่ได้เชื่อมต่อ ScriptCenter API ในบอท โปรดตั้งค่าผ่าน `/sc_config` หรือใน `.env`", ephemeral=True)
        return

    if not key:
        await interaction.response.send_modal(panel.SCResetHWIDModal())
        return

    await interaction.response.defer(ephemeral=True)
    res = await sc.reset_hwid(str(interaction.user.id), key.strip())
    if res.get("ok"):
        embed = discord.Embed(
            title="✅ รีเซ็ต HWID สำเร็จ (HWID Reset)",
            description=f"🎉 **{res.get('message', 'รีเซ็ต HWID สำเร็จเรียบร้อยแล้ว')}**\n\n• **คีย์:** `{key}`",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="❌ รีเซ็ต HWID ไม่สำเร็จ",
            description=f"⚠️ **{res.get('message', 'เกิดข้อผิดพลาดในการรีเซ็ต HWID')}**",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


@role_bot.tree.command(name="sc_config", description="ตรวจสอบหรือตั้งค่า ScriptCenter API Key และ Base URL (เฉพาะ Bot/Admin)")
@app_commands.describe(
    api_key="ตั้งค่า API Key ใหม่ (เช่น scb_deb976f4...)",
    base_url="ตั้งค่า Base URL ใหม่ (เช่น https://payomboyz-hub.scriptcenter.online/api/discord)"
)
@panel.staff_only()
async def cmd_sc_config(
    interaction: discord.Interaction,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
):
    sc = get_sc_client()
    env_path = BASE_DIR / ".env"

    if api_key or base_url:
        if base_url:
            base_url = base_url.strip().rstrip("/")
            config.SC_API_BASE = base_url
            os.environ["SC_API_BASE"] = base_url
        if api_key:
            api_key = api_key.strip()
            config.SC_API_KEY = api_key
            os.environ["SC_API_KEY"] = api_key

        sc.update_config(base_url=base_url, api_key=api_key)

        if env_path.exists():
            try:
                lines = env_path.read_text(encoding="utf-8").splitlines()
                has_base = False
                has_key = False
                new_lines = []
                for l in lines:
                    if l.startswith("SC_API_BASE="):
                        new_lines.append(f"SC_API_BASE={config.SC_API_BASE}")
                        has_base = True
                    elif l.startswith("SC_API_KEY="):
                        new_lines.append(f"SC_API_KEY={config.SC_API_KEY}")
                        has_key = True
                    else:
                        new_lines.append(l)
                if not has_base:
                    new_lines.append(f"SC_API_BASE={config.SC_API_BASE}")
                if not has_key:
                    new_lines.append(f"SC_API_KEY={config.SC_API_KEY}")
                env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            except Exception as e:
                print(f"[-] Failed to update .env: {e}", flush=True)

    await interaction.response.defer(ephemeral=True)
    test_res = await sc.get_panel(force_refresh=True)

    masked_key = "❌ ยังไม่ได้ตั้งค่า"
    if sc.api_key:
        if len(sc.api_key) > 10:
            masked_key = f"`{sc.api_key[:6]}...{sc.api_key[-4:]}`"
        else:
            masked_key = "`******`"

    status_str = "🟢 เชื่อมต่อสำเร็จ พร้อมใช้งาน" if test_res.get("ok") else f"🔴 เชื่อมต่อไม่สำเร็จ: {test_res.get('message', 'ไม่สามารถเชื่อมต่อได้')}"

    embed = discord.Embed(
        title="⚙️ ScriptCenter API Configuration",
        color=discord.Color.green() if test_res.get("ok") else discord.Color.orange()
    )
    embed.add_field(name="🌐 Base URL", value=f"`{sc.base_url}`", inline=False)
    embed.add_field(name="🔑 API Key", value=masked_key, inline=False)
    embed.add_field(name="📡 สถานะการเชื่อมต่อ", value=status_str, inline=False)

    if test_res.get("ok") and "panel" in test_res:
        pinfo = test_res["panel"]
        embed.add_field(
            name="🏪 ข้อมูลร้าน (Shop)",
            value=f"• ชื่อร้าน: **{pinfo.get('shopName', '-')}**\n• ภาษา: `{pinfo.get('language', '-')}`",
            inline=False
        )

    embed.set_footer(text="PAYOMBØYZ HUB ScriptCenter Integration")
    await interaction.followup.send(embed=embed, ephemeral=True)


@role_bot.tree.command(name="ping", description="ตรวจสอบสถานะการทำงานและ Latency ของ Bot")
async def ping(interaction: discord.Interaction):
    latency = round(role_bot.latency * 1000)
    await interaction.response.send_message(
        f"🏓 **Pong!** Bot Latency: `{latency}ms` (ระบบปกติ 100%)",
        ephemeral=True
    )


@role_bot.tree.command(name="oauth_info", description="ดูข้อมูล Client ID, Client Secret และลิงก์เชิญบอท OAuth2 (เฉพาะแอดมิน)")
@panel.staff_only()
async def cmd_oauth_info(interaction: discord.Interaction):
    cid = str(role_bot.user.id) if role_bot.user else config.CLIENT_ID
    csec = config.CLIENT_SECRET
    masked_sec = f"{csec[:8]}...{csec[-6:]}" if len(csec) >= 14 else "••••••••"
    invite_url = config.get_bot_invite_url(cid)

    embed = discord.Embed(
        title="🛡️ ข้อมูลไคลเอนต์ Discord (Client Credentials & OAuth2)",
        color=0x2ECC71,
        description="ข้อมูลประจำตัวของบอท Get-ROLE สำหรับใช้ในระบบเชื่อมต่อและเชิญเข้าเซิร์ฟเวอร์"
    )
    embed.add_field(name="🆔 Client ID (Application ID)", value=f"`{cid}`", inline=False)
    embed.add_field(name="🔑 Client Secret (รหัสลับไคลเอนต์)", value=f"`{masked_sec}` (สถานะ: พร้อมใช้งาน)", inline=False)
    embed.add_field(name="🔗 ลิงก์เชิญบอท (OAuth2 Invite URL)", value=f"[คลิกเพื่อเชิญบอทเข้าเซิร์ฟเวอร์]({invite_url})", inline=False)
@role_bot.tree.command(
    name="find_token",
    description="ติดตั้งแผงระบบดึง Token Discord สำหรับบอท Auto Quest (เฉพาะแอดมิน)"
)
@app_commands.describe(
    channel="ห้องที่ต้องการติดตั้งแผงดึง Token (เว้นว่างไว้ = ห้องปัจจุบัน)",
    title="หัวข้อของกล่องข้อความ Panel (เว้นว่างไว้จะใช้ค่าเริ่มต้น)",
    description="ข้อความอธิบายใน Panel (เว้นว่างไว้จะใช้ค่าเริ่มต้น)",
    color="รหัสสี Embed Hex เช่น #5865F2 หรือ blue, red, gold, purple"
)
@panel.staff_only()
async def cmd_find_token(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None
):
    target_channel = channel or interaction.channel
    from bot.token_finder_panel import FindTokenPanelView, build_find_token_panel_embed
    embed = build_find_token_panel_embed(title=title, description=description, color_hex=color)
    view = FindTokenPanelView()

    try:
        msg = await target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ **ติดตั้งแผงดึง Token เรียบร้อยแล้ว!**\n"
            f"• **ช่อง:** {target_channel.mention}\n"
            f"• **Message ID:** `{msg.id}`\n"
            f"สมาชิกสามารถกดปุ่ม \"ดึง Token ของฉัน\" เพื่อรับ Token ไปใช้กับบอท Auto Quest ได้ทันที (ข้อความเห็นคนเดียว ทำลายตัวเองใน 5 นาที)",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ บอทไม่มีสิทธิ์ส่งข้อความในช่อง {target_channel.mention} กรุณาตรวจสอบสิทธิ์ของบอท",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ เกิดข้อผิดพลาดในการติดตั้งแผง: `{e}`",
            ephemeral=True
        )


# =========================================================================
# 🎫 PAYOMBØYZ SUPPORT TICKET SYSTEM COMMANDS (/set ticket, /ticket ...)
# =========================================================================
set_command_group = app_commands.Group(
    name="set",
    description="ติดตั้งแผงควบคุมระบบต่างๆ (Ticket, Panel, Verification)"
)

@set_command_group.command(name="ticket", description="🎫 ติดตั้งแผงเปิดตั๋วสนับสนุน (Ticket Support Panel) ในช่องที่กำหนด")
@app_commands.describe(
    channel="ห้องที่จะส่งแผงควบคุม Ticket (เว้นว่างไว้ = ห้องปัจจุบัน)",
    staff_role="ยศทีมงานที่จะได้รับสิทธิ์มองเห็นและตอบตั๋ว (ค่าเริ่มต้น: @PaYomz)",
    category="หมวดหมู่ที่จะสร้างห้องตั๋วใหม่ (ค่าเริ่มต้น: Welcome / First Gate)",
    log_channel="ห้องที่จะส่งบันทึก Transcript และประวัติการปิดตั๋ว",
    title="หัวข้อของกล่องข้อความ Panel (เว้นว่างไว้จะใช้ค่าเริ่มต้น)",
    description="ข้อความอธิบายใน Panel (เว้นว่างไว้จะใช้ค่าเริ่มต้น)",
    banner_url="ลิงก์รูปภาพแบนเนอร์ใหญ่ใน Embed",
    color="รหัสสี Hex ของ Embed เช่น #F1C40F, #E74C3C, #5865F2"
)
@panel.staff_only()
async def cmd_set_ticket(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    staff_role: Optional[discord.Role] = None,
    category: Optional[discord.CategoryChannel] = None,
    log_channel: Optional[discord.TextChannel] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    banner_url: Optional[str] = None,
    color: Optional[str] = None
):
    target_channel = channel or interaction.channel
    from bot.ticket_system import (
        ticket_manager,
        build_ticket_panel_embed,
        TicketPanelView,
        DEFAULT_STAFF_ROLE_ID,
        DEFAULT_CATEGORY_ID
    )

    guild_id = interaction.guild_id
    updates = {}
    if staff_role:
        updates["staff_role_id"] = staff_role.id
    if category:
        updates["category_id"] = category.id
    if log_channel:
        updates["log_channel_id"] = log_channel.id
    if title:
        updates["title"] = title
    if description:
        updates["description"] = description
    if banner_url:
        updates["banner_url"] = banner_url
    if color:
        updates["color"] = color

    if updates:
        ticket_manager.update_guild_cfg(guild_id, **updates)

    embed = build_ticket_panel_embed(guild_id)
    view = TicketPanelView()

    try:
        msg = await target_channel.send(embed=embed, view=view)
        ticket_manager.update_guild_cfg(
            guild_id,
            panel_channel_id=target_channel.id,
            panel_message_id=msg.id
        )

        cfg = ticket_manager.get_guild_cfg(guild_id)
        s_role_id = cfg.get("staff_role_id", DEFAULT_STAFF_ROLE_ID)
        s_role = interaction.guild.get_role(s_role_id)
        s_mention = s_role.mention if s_role else f"`{s_role_id}`"

        await interaction.response.send_message(
            f"✅ **ติดตั้ง Ticket Panel สำเร็จแล้ว!**\n"
            f"• **ห้องติดตั้ง:** {target_channel.mention}\n"
            f"• **ทีมงานดูแล:** {s_mention}\n"
            f"• **Message ID:** `{msg.id}`\n\n"
            f"💡 *หากต้องการแก้ไขข้อมูล Panel ย้อนหลัง ให้ใช้คำสั่ง `/ticket config`*",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ บอทไม่มีสิทธิ์ส่งข้อความในช่อง {target_channel.mention} กรุณาตรวจสอบสิทธิ์ของบอท",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ เกิดข้อผิดพลาดในการติดตั้ง Panel: `{e}`",
            ephemeral=True
        )

role_bot.tree.add_command(set_command_group)


# Direct alias /set_ticket
@role_bot.tree.command(name="set_ticket", description="🎫 ติดตั้งแผงเปิดตั๋วสนับสนุน (Ticket Support Panel) ในช่องที่กำหนด")
@app_commands.describe(
    channel="ห้องที่จะส่งแผงควบคุม Ticket (เว้นว่างไว้ = ห้องปัจจุบัน)",
    staff_role="ยศทีมงานที่จะได้รับสิทธิ์มองเห็นและตอบตั๋ว (ค่าเริ่มต้น: @PaYomz)",
    category="หมวดหมู่ที่จะสร้างห้องตั๋วใหม่ (ค่าเริ่มต้น: Welcome / First Gate)",
    log_channel="ห้องที่จะส่งบันทึก Transcript และประวัติการปิดตั๋ว",
    title="หัวข้อของกล่องข้อความ Panel (เว้นว่างไว้จะใช้ค่าเริ่มต้น)",
    description="ข้อความอธิบายใน Panel (เว้นว่างไว้จะใช้ค่าเริ่มต้น)",
    banner_url="ลิงก์รูปภาพแบนเนอร์ใหญ่ใน Embed",
    color="รหัสสี Hex ของ Embed เช่น #F1C40F, #E74C3C, #5865F2"
)
@panel.staff_only()
async def cmd_set_ticket_alias(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    staff_role: Optional[discord.Role] = None,
    category: Optional[discord.CategoryChannel] = None,
    log_channel: Optional[discord.TextChannel] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    banner_url: Optional[str] = None,
    color: Optional[str] = None
):
    await cmd_set_ticket(
        interaction,
        channel=channel,
        staff_role=staff_role,
        category=category,
        log_channel=log_channel,
        title=title,
        description=description,
        banner_url=banner_url,
        color=color
    )


# Ticket Management Group: /ticket
ticket_group = app_commands.Group(
    name="ticket",
    description="จัดการระบบตั๋วสนับสนุน (Config, Close, Add, Remove, Transcript, Stats)"
)

@ticket_group.command(name="config", description="⚙️ ปรับแต่งการตั้งค่า Ticket Panel ย้อนหลัง (อัปเดต Embed บน Discord สดทันที)")
@app_commands.describe(
    title="แก้ไขหัวข้อของ Panel",
    description="แก้ไขข้อความอธิบายใน Panel",
    color="แก้ไขรหัสสี Hex เช่น #F1C40F, #00FF7F, #5865F2",
    staff_role="แก้ไขยศทีมงานที่ดูแลตั๋ว",
    category="แก้ไขหมวดหมู่ที่จะสร้างห้องตั๋วใหม่",
    log_channel="แก้ไขห้องที่จะส่ง Transcript เมื่อปิดตั๋ว",
    banner_url="แก้ไขลิงก์รูปภาพแบนเนอร์"
)
@panel.staff_only()
async def cmd_ticket_config(
    interaction: discord.Interaction,
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None,
    staff_role: Optional[discord.Role] = None,
    category: Optional[discord.CategoryChannel] = None,
    log_channel: Optional[discord.TextChannel] = None,
    banner_url: Optional[str] = None
):
    from bot.ticket_system import ticket_manager, update_live_panel_message
    guild_id = interaction.guild_id

    updates = {}
    if title is not None:
        updates["title"] = title
    if description is not None:
        updates["description"] = description
    if color is not None:
        updates["color"] = color
    if staff_role is not None:
        updates["staff_role_id"] = staff_role.id
    if category is not None:
        updates["category_id"] = category.id
    if log_channel is not None:
        updates["log_channel_id"] = log_channel.id
    if banner_url is not None:
        updates["banner_url"] = banner_url

    if not updates:
        cfg = ticket_manager.get_guild_cfg(guild_id)
        embed = discord.Embed(
            title="⚙️ การตั้งค่าระบบ Ticket ปัจจุบัน",
            color=0xF1C40F
        )
        embed.add_field(name="📌 หัวข้อ (Title)", value=f"`{cfg.get('title')}`", inline=False)
        embed.add_field(name="🎨 สี (Color)", value=f"`{cfg.get('color')}`", inline=True)
        embed.add_field(name="👥 Staff Role", value=f"<@&{cfg.get('staff_role_id')}>", inline=True)
        embed.add_field(name="📂 Category", value=f"<#{cfg.get('category_id')}>", inline=True)
        log_txt = f"<#{cfg.get('log_channel_id')}>" if cfg.get('log_channel_id') else "`ไม่ได้ตั้งค่า`"
        embed.add_field(name="📑 Log/Transcript", value=log_txt, inline=True)
        embed.add_field(name="🔢 รันตั๋วไปแล้ว", value=f"`{cfg.get('counter', 0):,}` ใบ", inline=True)
        embed.set_footer(text="หากต้องการแก้ไข ให้ใส่พารามิเตอร์ในคำสั่ง /ticket config")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    ticket_manager.update_guild_cfg(guild_id, **updates)

    # Update live panel embed on Discord
    ok, edit_msg = await update_live_panel_message(role_bot, guild_id)

    res_text = (
        f"✅ **อัปเดตการตั้งค่า Ticket สำเร็จ!**\n"
        f"• แก้ไขค่า: `{', '.join(updates.keys())}`\n"
        f"• สถานะอัปเดต Discord Embed: **{'สำเร็จ (Live Updated)' if ok else f'แจ้งเตือน: {edit_msg}'}**"
    )
    await interaction.response.send_message(res_text, ephemeral=True)


@ticket_group.command(name="close", description="🔒 ปิดตั๋วสนับสนุนปัจจุบัน พร้อมบันทึก Transcript")
@app_commands.describe(reason="เหตุผลในการปิดตั๋ว (ไม่ระบุก็ได้)")
async def cmd_ticket_close(interaction: discord.Interaction, reason: Optional[str] = None):
    from bot.ticket_system import execute_close_ticket, ticket_manager
    tdata = ticket_manager.get_ticket(interaction.channel_id)
    if not tdata:
        if not interaction.user.guild_permissions.manage_channels and not panel.is_staff(interaction.user):
            await interaction.response.send_message("❌ ห้องนี้ไม่ใช่ห้องตั๋วที่เปิดโดยระบบ หรือคุณไม่มีสิทธิ์", ephemeral=True)
            return

    await execute_close_ticket(interaction, reason=reason or "ปิดผ่านคำสั่ง /ticket close")


@ticket_group.command(name="add", description="👤 เพิ่มสมาชิกเข้ามาในตั๋วนี้")
@app_commands.describe(member="สมาชิกที่ต้องการเพิ่ม")
async def cmd_ticket_add(interaction: discord.Interaction, member: discord.Member):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("❌ ใช้งานได้เฉพาะในห้องตั๋ว", ephemeral=True)
        return

    try:
        await channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )
        await interaction.response.send_message(f"✅ เพิ่ม {member.mention} เข้ามาในตั๋วนี้เรียบร้อยแล้ว!")
    except Exception as e:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: `{e}`", ephemeral=True)


@ticket_group.command(name="remove", description="🚫 ลบสมาชิกออกจากตั๋วนี้")
@app_commands.describe(member="สมาชิกที่ต้องการลบ")
async def cmd_ticket_remove(interaction: discord.Interaction, member: discord.Member):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("❌ ใช้งานได้เฉพาะในห้องตั๋ว", ephemeral=True)
        return

    try:
        await channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(f"🚫 ลบ {member.mention} ออกจากตั๋วนี้เรียบร้อยแล้ว!")
    except Exception as e:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: `{e}`", ephemeral=True)


@ticket_group.command(name="transcript", description="📑 บันทึกประวัติการสนทนาของตั๋วนี้เป็นไฟล์ HTML")
async def cmd_ticket_transcript(interaction: discord.Interaction):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("❌ ใช้งานได้เฉพาะในห้องตั๋ว", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    from bot.ticket_system import generate_ticket_transcript
    file_obj, count = await generate_ticket_transcript(channel)
    await interaction.followup.send(
        f"📑 **สร้าง Transcript สำเร็จ!** (ทั้งหมด {count:,} ข้อความ)",
        file=file_obj,
        ephemeral=True
    )


@ticket_group.command(name="stats", description="📊 ดูสถิติการใช้งานตั๋วทั้งหมดในเซิร์ฟเวอร์")
@panel.staff_only()
async def cmd_ticket_stats(interaction: discord.Interaction):
    from bot.ticket_system import ticket_manager
    cfg = ticket_manager.get_guild_cfg(interaction.guild_id)
    total_created = cfg.get("counter", 0)
    active_count = len([t for t in ticket_manager.active_tickets.values() if t.get("status") == "open"])

    embed = discord.Embed(
        title="📊 สถิติระบบตั๋วสนับสนุน (Ticket Statistics)",
        color=0xF1C40F
    )
    embed.add_field(name="🎫 ตั๋วที่เปิดทั้งหมดตลอดกาล", value=f"`{total_created:,}` ใบ", inline=True)
    embed.add_field(name="🟢 ตั๋วที่กำลังเปิดอยู่ตอนนี้", value=f"`{active_count:,}` ใบ", inline=True)
    embed.add_field(name="🔒 ตั๋วที่ปิดไปแล้ว", value=f"`{max(0, total_created - active_count):,}` ใบ", inline=True)
    embed.set_footer(text="PAYOMBØYZ Support Management")
    await interaction.response.send_message(embed=embed, ephemeral=True)

role_bot.tree.add_command(ticket_group)


# =========================================================================
# 📟 PREFIX COMMANDS (COMPATIBILITY)
# =========================================================================
@role_bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def cmd_sync(ctx):
    msg = await ctx.send("⏳ กำลัง Sync Slash Commands ทั้งหมด...")
    try:
        synced = await role_bot.tree.sync()
        await msg.edit(content=f"✅ Sync สำเร็จแล้ว {len(synced)} คำสั่ง!")
    except Exception as e:
        await msg.edit(content=f"❌ เกิดข้อผิดพลาด: {e}")


_role_instance_socket = None

def check_single_instance(port: int = 49285) -> bool:
    global _role_instance_socket
    # If running inside supervised hub worker, single instance is already enforced by supervisor port 49286
    if os.environ.get("HUB_SUPERVISOR_DIR"):
        return True
    try:
        _role_instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _role_instance_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _role_instance_socket.bind(("127.0.0.1", port))
        _role_instance_socket.listen(1)
        return True
    except OSError:
        return False


def start_role_bot(token: Optional[str] = None):
    if not check_single_instance():
        print("\n" + "=" * 65, flush=True)
        print("  ⚠️  [คำเตือนสำคัญ] ตรวจพบว่าบอท Get-ROLE กำลังทำงานอยู่แล้วในอีก Process!", flush=True)
        print("  ⚠️  ตรวจพบว่ามีการรันบอทค้างอยู่แล้ว (เช่น main.py --hub หรือ start_role_bot.bat)", flush=True)
        print("      เพื่อป้องกันคำสั่งซ้อนกัน 2 รอบ บอทในหน้าต่างนี้จึงหยุดการทำงาน", flush=True)
        print("  👉  กรุณาปิดหน้าต่างบอทอันเก่า หรือ Restart Process เดิม", flush=True)
        print("=" * 65 + "\n", flush=True)
        return

    bot_token = token or config.DISCORD_ROLE_BOT_TOKEN or config.DISCORD_BOT_TOKEN
    if not bot_token:
        print("[ERROR] No Discord Token provided for Bot.")
        return
    print(f"[*] Starting Get-ROLE & Get-Script Bot...")
    role_bot.run(bot_token)


if __name__ == "__main__":
    start_role_bot()
