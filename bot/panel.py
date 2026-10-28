import json

import io

import os

import re

import time

from pathlib import Path

from typing import Dict, List, Optional, Tuple, Union

import discord

from discord import app_commands

from bot.scriptcenter_client import get_sc_client, WORDS as SC_WORDS

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================================================================

# 🛡️ ROLE PERMISSIONS CONFIG

# Role ที่มีสิทธิ์ออกคำสั่งกับบอท:

# 1549786080595804251 (Bot)

# 1549535328753164418 (Admin)

# =========================================================================

BOT_ROLE_ID = 1549786080595804251

ADMIN_ROLE_ID = 1549535328753164418

# Role เริ่มต้นที่จะแจกให้ผู้ใช้เมื่อกรอกคีย์ผ่าน (VVIP Role)
DEFAULT_VVIP_ROLE_ID = int(os.environ.get("ROLE_ID", "1549785782330593330"))

ALLOWED_COMMAND_ROLES = {BOT_ROLE_ID, ADMIN_ROLE_ID, DEFAULT_VVIP_ROLE_ID}

# คีย์พิเศษที่สามารถใช้ได้หลายครั้งโดยไม่โดนลบ

SPECIAL_KEY = "PAYOMVVIP280342PBGZ19"

# ไฟล์จัดเก็บข้อมูล

DB_FILE = BASE_DIR / "vvip_keys.json"

PANELS_FILE = BASE_DIR / "panels_config.json"

PROJECTS_FILE = BASE_DIR / "projects.json"

# สคริปต์เริ่มต้นสำหรับปุ่ม Get Script

DEFAULT_SCRIPT = "loadstring(game:HttpGet('https://raw.githubusercontent.com/PayomboyZ/Hub/main/loader.lua'))()"

# =========================================================================

# 👑 PAYOMBØYZ HUB CUSTOM SERVER EMOJIS

# =========================================================================

EMOJI_PAYOMBOYZ = "<:payomboyz:1551064225974325318>"

EMOJI_KING = "<:pbg_king:1551063202002108446>"

EMOJI_CHICKEN_KING = "<:pbg_chicken_king:1551064110970441818>"

EMOJI_SUKUNA = "<a:Sukuna:1551069997999067228>"

EMOJI_FIRE = "<a:anime_fire:1551069928105447485>"

EMOJI_SNIPER = "<:pbg_sniper:1551054607986458734>"

EMOJI_DARK = "<:pbg_dark:1551054748268888094>"

EMOJI_NIGHT = "<:pbg_night:1551062377519259648>"

EMOJI_COME = "<:pbg_come:1551063846276563074>"

EMOJI_ZA = "<:pbg_za:1551063500351213700>"

EMOJI_CHILL = "<:pbg_chill:1551064392139804702>"

EMOJI_WAIT = "<:pbg_wait:1551063140349780068>"

EMOJI_SLEEP = "<:pbg_sleep:1551064016804253787>"

EMOJI_ANGRY = "<:pbg_angry:1551063284868714657>"

EMOJI_QUESTION = "<:pbg_question:1551063774251851806>"

EMOJI_GOJO = "<:pbg_gojo:1551063918020005949>"

EMOJI_SPIN = "<a:spin:1551027090025877536>"

EMOJI_RUN = "<:pbg_run:1551532010932273203>"

# =========================================================================

# 🎨 COLOR, EMOJI & BUTTON STYLE HELPERS

# =========================================================================

COLOR_PRESETS = {

    "red": discord.Color.red(),

    "crimson": discord.Color.from_rgb(220, 20, 60),

    "green": discord.Color.green(),

    "emerald": discord.Color.from_rgb(46, 204, 113),

    "blue": discord.Color.blue(),

    "blurple": discord.Color.blurple(),

    "gold": discord.Color.gold(),

    "yellow": discord.Color.yellow(),

    "purple": discord.Color.purple(),

    "magenta": discord.Color.magenta(),

    "orange": discord.Color.orange(),

    "dark": discord.Color.dark_theme(),

    "black": discord.Color.from_rgb(15, 15, 15),

    "white": discord.Color.from_rgb(255, 255, 255),

}

def parse_color(color_val: Optional[str]) -> discord.Color:

    """แปลงสตริงสีเป็น discord.Color (รองรับชื่อสี, HEX เช่น #FF0000 หรือ 0xFF0000)"""

    if not color_val:

        return discord.Color.from_rgb(255, 0, 0)

    val = color_val.strip().lower()

    if val in COLOR_PRESETS:

        return COLOR_PRESETS[val]

    # ลบ # หรือ 0x ออก

    cleaned = val.lstrip("#").replace("0x", "")

    try:

        if len(cleaned) == 6:

            r = int(cleaned[0:2], 16)

            g = int(cleaned[2:4], 16)

            b = int(cleaned[4:6], 16)

            return discord.Color.from_rgb(r, g, b)

        elif len(cleaned) == 3:

            r = int(cleaned[0] * 2, 16)

            g = int(cleaned[1] * 2, 16)

            b = int(cleaned[2] * 2, 16)

            return discord.Color.from_rgb(r, g, b)

    except Exception:

        pass

    return discord.Color.from_rgb(255, 0, 0)

def parse_emoji(emoji_str: Optional[str]) -> Optional[Union[discord.PartialEmoji, str]]:

    """

    แยกวิเคราะห์อิโมจิ รองรับทั้ง:

    - Standard Unicode emoji (เช่น 🔑, 📜, 🛒)

    - Custom Discord server emoji (เช่น <:pepe:123456789> หรือ <a:spin:123456789>)

    """

    if not emoji_str:

        return None

    s = emoji_str.strip()

    if not s:

        return None

    try:

        # ลองใช้ PartialEmoji.from_str ถ้าเป็น custom emoji ของดิสคอร์ด

        if s.startswith("<") and s.endswith(">") and ":" in s:

            pe = discord.PartialEmoji.from_str(s)

            if pe:

                return pe

        # ถ้ามีรูปแบบ name:id

        if ":" in s and not s.startswith("http"):

            parts = s.split(":")

            if len(parts) == 2 and parts[1].isdigit():

                return discord.PartialEmoji(name=parts[0], id=int(parts[1]))

    except Exception:

        pass

    return s

def parse_button_style(style_str: Optional[str]) -> discord.ButtonStyle:

    """แปลงข้อความสไตล์ปุ่มเป็น discord.ButtonStyle"""

    if not style_str:

        return discord.ButtonStyle.primary

    s = style_str.strip().lower()

    if s in ("green", "success", "เขียว"):

        return discord.ButtonStyle.success

    elif s in ("blue", "blurple", "primary", "น้ำเงิน", "ฟ้า"):

        return discord.ButtonStyle.primary

    elif s in ("grey", "gray", "secondary", "เทา"):

        return discord.ButtonStyle.secondary

    elif s in ("red", "danger", "destructive", "แดง"):

        return discord.ButtonStyle.danger

    elif s in ("link", "url", "เว็บ"):

        return discord.ButtonStyle.link

    return discord.ButtonStyle.primary

def parse_bulk_keys(text: str) -> List[str]:

    """

    แยกวิเคราะห์คีย์จำนวนมาก คั่นด้วยเครื่องหมายจุลภาค (,) หรือการเคาะ Enter (

)

    ตัดช่องว่าง และกรองคีย์ที่ว่างเปล่าออก

    """

    if not text:

        return []

    # แทนที่การขึ้นบรรทัดใหม่ด้วยจุลภาค

    normalized = text.replace("\r\n", ",").replace("\n", ",").replace("\r", ",")

    tokens = normalized.split(",")

    keys = []

    seen = set()

    for token in tokens:

        cleaned = token.strip().strip('"').strip("'")

        if cleaned and cleaned not in seen:

            seen.add(cleaned)

            keys.append(cleaned)

    return keys

# =========================================================================

# 🗄️ PROJECT & KEY DATA STORAGE

# =========================================================================

def load_keys() -> dict:

    if DB_FILE.exists():

        try:

            with open(DB_FILE, "r", encoding="utf-8") as f:

                return json.load(f)

        except Exception:

            pass

    return {}

def save_keys(keys_data: dict):

    try:

        with open(DB_FILE, "w", encoding="utf-8") as f:

            json.dump(keys_data, f, indent=2, ensure_ascii=False)

    except Exception as e:

        print(f"[!] Failed to save keys: {e}", flush=True)

vvip_keys = load_keys()

def load_panel_configs() -> dict:

    if PANELS_FILE.exists():

        try:

            with open(PANELS_FILE, "r", encoding="utf-8") as f:

                return json.load(f)

        except Exception:

            pass

    return {

        str(DEFAULT_VVIP_ROLE_ID): {

            "role_id": DEFAULT_VVIP_ROLE_ID,

            "title": "PAYOMBØYZ GET-Script",

            "description": (

                "แผงควบคุมนี้สำหรับโปรเจกต์: **PAYOMBØYZ HUB**\n"

                "หากคุณเป็นผู้ซื้อหรือสมาชิกระดับ VVIP คลิกที่ปุ่มด้านล่างเพื่อยืนยันคีย์รับยศ (Redeem Key), "

                "รับสคริปต์ (Get Script) หรือรับบทบาทของคุณ (Get Role)"

            ),

            "script_text": DEFAULT_SCRIPT,

        }

    }

def save_panel_config(role_id: int, title: str, description: str, script_text: str):

    configs = load_panel_configs()

    configs[str(role_id)] = {

        "role_id": role_id,

        "title": title,

        "description": description,

        "script_text": script_text,

    }

    try:

        with open(PANELS_FILE, "w", encoding="utf-8") as f:

            json.dump(configs, f, indent=2, ensure_ascii=False)

    except Exception as e:

        print(f"[!] Failed to save panel config: {e}", flush=True)

def load_projects() -> Dict[str, dict]:
    """โหลดข้อมูล Projects ทั้งหมด พร้อม Migration ข้อมูลเก่าอัตโนมัติ และระบบกู้คืนไฟล์"""
    projects = {}
    should_seed_default = not PROJECTS_FILE.exists()
    if PROJECTS_FILE.exists():
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                projects = json.load(f)
        except Exception as e:
            print(f"[!] Failed to load projects from {PROJECTS_FILE}: {type(e).__name__}: {e}", flush=True)
            # Try reading auto backup if main file failed to parse
            bak_file = PROJECTS_FILE.with_suffix(".json.bak_auto")
            if bak_file.exists():
                try:
                    with open(bak_file, "r", encoding="utf-8") as bf:
                        projects = json.load(bf)
                        print(f"[+] Recovered projects from {bak_file}", flush=True)
                except Exception:
                    pass

    if not isinstance(projects, dict):
        print(f"[!] Invalid projects file format at {PROJECTS_FILE}: expected an object, got {type(projects).__name__}", flush=True)
        projects = {}

    default_id = "payomboyz-hub"
    if should_seed_default and default_id not in projects:
        legacy_panels = load_panel_configs()
        legacy_cfg = legacy_panels.get(str(DEFAULT_VVIP_ROLE_ID), {})
        projects[default_id] = {
            "id": default_id,
            "name": "PAYOMBØYZ HUB",
            "type": "get_role",
            "role_id": DEFAULT_VVIP_ROLE_ID,
            "default_script": legacy_cfg.get("script_text", DEFAULT_SCRIPT),
            "maps": [
                {
                    "name": "Blox Fruits",
                    "script": "loadstring(game:HttpGet('https://raw.githubusercontent.com/PayomboyZ/Hub/main/loader.lua'))()",
                    "emoji": "🍇",
                },
                {
                    "name": "King Legacy",
                    "script": "loadstring(game:HttpGet('https://raw.githubusercontent.com/PayomboyZ/Hub/main/loader.lua'))()",
                    "emoji": "👑",
                },
                {
                    "name": "Fisch",
                    "script": "loadstring(game:HttpGet('https://raw.githubusercontent.com/PayomboyZ/Hub/main/loader.lua'))()",
                    "emoji": "🐟",
                },
            ],
            "keys": dict(vvip_keys),
            "custom_buttons": [],
            "panel_config": {
                "title": legacy_cfg.get("title", "PAYOMBØYZ GET-Script"),
                "description": legacy_cfg.get(
                    "description",
                    "แผงควบคุมนี้สำหรับโปรเจกต์: **PAYOMBØYZ HUB**\n"
                    "หากคุณเป็นผู้ซื้อหรือสมาชิกระดับ VVIP คลิกที่ปุ่มด้านล่างเพื่อยืนยันคีย์รับยศ (Redeem Key), "
                    "ตรวจสอบยศ (Check Role) หรือรับสคริปต์ (Get Script)",
                ),
                "color": "#FF0000",
                "image_url": None,
                "thumbnail_url": None,
                "footer": "PAYOMBØYZ HUB",
            },
        }
        save_projects(projects)

    for pdata in projects.values():
        if isinstance(pdata, dict) and "require_key" not in pdata:
            pdata["require_key"] = True

    return projects

def save_projects(projects: Dict[str, dict]):
    """บันทึก Projects แบบ Atomic Write พร้อม Auto Backup ป้องกันไฟล์ถูกเขียนทับว่างเปล่า"""
    if not isinstance(projects, dict) or not projects:
        if PROJECTS_FILE.exists() and PROJECTS_FILE.stat().st_size > 100:
            print("[!] Refusing to save empty projects dict over existing populated file!", flush=True)
            return

    try:
        import shutil
        bak_file = PROJECTS_FILE.with_suffix(".json.bak_auto")
        if PROJECTS_FILE.exists():
            try:
                shutil.copy2(PROJECTS_FILE, bak_file)
            except Exception:
                pass

        tmp_file = PROJECTS_FILE.with_suffix(".json.tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(projects, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, PROJECTS_FILE)
    except Exception as e:
        print(f"[!] Failed to save projects: {e}", flush=True)

def get_project(project_id: str) -> Optional[dict]:

    if not isinstance(project_id, str) or not project_id.strip():

        return None

    projects = load_projects()

    p_lower = project_id.lower().strip()

    for pid, pdata in projects.items():

        if str(pid).lower() == p_lower or str(pdata.get("id", "")).lower() == p_lower or str(pdata.get("name", "")).lower() == p_lower:

            return pdata

    return None

def upsert_project(project_data: dict):

    projects = load_projects()

    pid = project_data.get("id")

    if not pid:

        name = project_data.get("name", "project")

        pid = re.sub(r"[^a-zA-Z0-9_\-]", "_", name).lower()

        project_data["id"] = pid

    projects[pid] = project_data

    save_projects(projects)

    return project_data

def remove_project(project_id: str) -> Optional[dict]:

    """Remove one configured project and return its previous data."""

    projects = load_projects()

    if not isinstance(project_id, str) or not project_id.strip():

        return None

    query = project_id.strip().casefold()

    target_key = next((

        key for key, item in projects.items()

        if str(key).casefold() == query

        or str(item.get("id", "")).casefold() == query

        or str(item.get("name", "")).casefold() == query

    ), None)

    if target_key is None:

        return None

    removed = projects.pop(target_key)

    save_projects(projects)

    # Confirm persistence before reporting success to the command handler.

    try:

        persisted = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))

        if target_key in persisted:

            return None

    except Exception:

        return None

    return removed

def add_map_to_project(

    project_id: str,

    name: str,

    script: str,

    emoji: Optional[str] = None,

    description: Optional[str] = None

) -> Tuple[bool, str, dict]:

    """เพิ่มหรืออัปเดตแมพในโปรเจกต์"""

    project = get_project(project_id)

    if not project:

        return False, f"ไม่พบโปรเจกต์ `{project_id}`", {}

    maps = project.setdefault("maps", [])

    found = False

    clean_name = name.strip()

    clean_emoji = emoji.strip() if emoji and emoji.strip() else "🗺️"

    clean_desc = description.strip() if description and description.strip() else "พร้อมใช้งาน (Active)"

    for m in maps:

        if m.get("name", "").lower() == clean_name.lower():

            m["name"] = clean_name

            m["script"] = script.strip()

            m["emoji"] = clean_emoji

            m["description"] = clean_desc

            found = True

            break

    if not found:

        maps.append({

            "name": clean_name,

            "script": script.strip(),

            "emoji": clean_emoji,

            "description": clean_desc

        })

    upsert_project(project)

    msg = f"อัปเดตข้อมูลแมพ **{clean_name}** เรียบร้อยแล้ว" if found else f"เพิ่มแมพ **{clean_name}** สำเร็จ"

    return True, msg, project

def edit_map_in_project(

    project_id: str,

    old_map_name: str,

    new_name: str,

    script: str,

    emoji: Optional[str] = None,

    description: Optional[str] = None

) -> Tuple[bool, str, dict]:

    """แก้ไขข้อมูลแมพเดิมในโปรเจกต์"""

    project = get_project(project_id)

    if not project:

        return False, f"ไม่พบโปรเจกต์ `{project_id}`", {}

    maps = project.get("maps", [])

    target = None

    for m in maps:

        if m.get("name", "").lower() == old_map_name.strip().lower():

            target = m

            break

    if not target:

        return False, f"ไม่พบแมพชื่อ `{old_map_name}` ในโปรเจกต์นี้", project

    target["name"] = new_name.strip()

    target["script"] = script.strip()

    if emoji and emoji.strip():

        target["emoji"] = emoji.strip()

    if description is not None:

        target["description"] = description.strip() or "พร้อมใช้งาน (Active)"

    upsert_project(project)

    return True, f"แก้ไขแมพ **{new_name.strip()}** เรียบร้อยแล้ว", project

def remove_map_from_project(project_id: str, target_map_name: str) -> Tuple[bool, str, dict]:

    """ลบแมพออกจากโปรเจกต์"""

    project = get_project(project_id)

    if not project:

        return False, f"ไม่พบโปรเจกต์ `{project_id}`", {}

    maps = project.get("maps", [])

    initial_len = len(maps)

    project["maps"] = [m for m in maps if m.get("name", "").lower() != target_map_name.strip().lower()]

    if len(project["maps"]) < initial_len:

        upsert_project(project)

        return True, f"ลบแมพ **{target_map_name}** เรียบร้อยแล้ว", project

    else:

        return False, f"ไม่พบแมพชื่อ `{target_map_name}` ในโปรเจกต์นี้", project

# =========================================================================

# 🔒 STRICT ROLE AUTHORIZATION CHECK

# =========================================================================

def is_authorized_staff(user: Union[discord.Member, discord.User]) -> bool:

    if not hasattr(user, "roles"):

        return False

    user_roles_ids = {r.id for r in user.roles}

    if user_roles_ids & ALLOWED_COMMAND_ROLES or (DEFAULT_VVIP_ROLE_ID and DEFAULT_VVIP_ROLE_ID in user_roles_ids):

        return True

    for r in user.roles:

        r_lower = r.name.lower()

        if any(k in r_lower for k in ["bot", "admin", "staff", "mod", "vip", "vvip", "member", "customer"]):

            return True

    if hasattr(user, "guild_permissions") and user.guild_permissions.administrator:

        return True

    if hasattr(user, "guild") and user.guild and user.guild.owner_id == user.id:

        return True

    return False

async def check_command_permission(interaction: discord.Interaction) -> bool:

    if not interaction.guild:

        await interaction.response.send_message("❌ คำสั่งนี้สามารถใช้งานได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)

        return False

    user = interaction.user

    if not isinstance(user, discord.Member) or not is_authorized_staff(user):

        await interaction.response.send_message(

            "❌ **คุณไม่มีสิทธิ์ออกคำสั่งกับบอทนี้!**\n"

            "คำสั่งนี้จำกัดสิทธิ์เฉพาะผู้ที่มีบทบาทต่อไปนี้เท่านั้น:\n"

            f"• 🤖 **Bot Role:** `<@&{BOT_ROLE_ID}>` (`{BOT_ROLE_ID}`)\n"

            f"• 👑 **Admin Role:** `<@&{ADMIN_ROLE_ID}>` (`{ADMIN_ROLE_ID}`)",

            ephemeral=True,

        )

        return False

    return True

def staff_only():

    return app_commands.check(check_command_permission)

# =========================================================================

# 📝 POPUPS & MODALS

# =========================================================================

class BulkAddKeyModal(discord.ui.Modal, title="Add Keys to Project"):

    """Popup สำหรับให้แอดมินใส่คีย์หลายๆ คีย์พร้อมกันด้วย Enter หรือ Comma"""

    keys_input = discord.ui.TextInput(

        label="ใส่รายการคีย์ (คั่นด้วย Enter หรือจุลภาค ,)",

        placeholder="KEY-ABC123\nKEY-XYZ789\nKEY-111, KEY-222",

        style=discord.TextStyle.paragraph,

        required=True,

        max_length=4000,

    )

    def __init__(self, project_id: str):

        super().__init__()

        self.project_id = project_id

    async def on_submit(self, interaction: discord.Interaction):

        project = get_project(self.project_id)

        if not project:

            await interaction.response.send_message(f"❌ ไม่พบโปรเจกต์ ID `{self.project_id}`", ephemeral=True)

            return

        raw_text = self.keys_input.value

        parsed_keys = parse_bulk_keys(raw_text)

        if not parsed_keys:

            await interaction.response.send_message("⚠️ ไม่พบคีย์ที่ถูกต้องในข้อความที่กรอก กรุณาลองใหม่อีกครั้ง", ephemeral=True)

            return

        project_keys = project.setdefault("keys", {})

        added_count = 0

        duplicate_count = 0

        for k in parsed_keys:
            if k in project_keys:
                duplicate_count += 1
            else:
                project_keys[k] = True
                added_count += 1

        upsert_project(project)

        embed = discord.Embed(

            title=f"🔑 เพิ่มคีย์เข้าระบบสำเร็จ: {project.get('name')}",

            color=discord.Color.green(),

        )

        embed.add_field(name="✅ เพิ่มสำเร็จ", value=f"`{added_count:,}` คีย์", inline=True)

        embed.add_field(name="⚠️ คีย์ซ้ำเดิม (ข้าม)", value=f"`{duplicate_count:,}` คีย์", inline=True)

        embed.add_field(name="📦 คีย์ทั้งหมดในโปรเจกต์", value=f"`{len(project_keys):,}` คีย์", inline=True)

        if parsed_keys:

            preview = "\n".join([f"• `{k[:24]}...`" if len(k) > 24 else f"• `{k}`" for k in parsed_keys[:5]])

            if len(parsed_keys) > 5:

                preview += f"\n*...และอีก {len(parsed_keys) - 5} คีย์*"

            embed.add_field(name="ตัวอย่างคีย์ที่บันทึก", value=preview, inline=False)

        embed.set_footer(text=f"Added by {interaction.user.name}")

        await interaction.response.send_message(embed=embed, ephemeral=True)


class BulkAddSuperIPModal(discord.ui.Modal, title="⚡ Add SuperIP Keys to ALL Projects"):
    """Popup สำหรับให้แอดมินใส่คีย์ที่จะเพิ่มเข้าไปในทุกโปรเจกต์พร้อมกันในครั้งเดียว"""
    keys_input = discord.ui.TextInput(
        label="ใส่รายการ Super Key (คั่นด้วย Enter หรือ ,)",
        placeholder="SUPER-KEY-111\nSUPER-KEY-222\nPAYOMBOYZHUB-ALL-XXXX",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        projects = load_projects()
        if not projects:
            await interaction.response.send_message("❌ ไม่พบโปรเจกต์ในระบบ", ephemeral=True)
            return

        raw_text = self.keys_input.value
        parsed_keys = parse_bulk_keys(raw_text)
        if not parsed_keys:
            await interaction.response.send_message("⚠️ ไม่พบคีย์ที่ถูกต้องในข้อความที่กรอก", ephemeral=True)
            return

        total_projects = 0
        for pid, pdata in projects.items():
            if isinstance(pdata, dict):
                proj_keys = pdata.setdefault("keys", {})
                for k in parsed_keys:
                    proj_keys[k] = True
                total_projects += 1

        save_projects(projects)

        embed = discord.Embed(
            title="⚡ เพิ่ม SuperIP Keys ในทุกโปรเจกต์สำเร็จ!",
            description=(
                f"• **จำนวนคีย์:** `{len(parsed_keys):,}` คีย์\n"
                f"• **กระจายไปยัง:** `{total_projects}` โปรเจกต์พร้อมกันในระบบ\n\n"
                f"✅ สมาชิกที่มีคีย์ชุดนี้ สามารถนำไป Redeem ได้ในแผงควบคุมของทุกโปรเจกต์ทันที"
            ),
            color=discord.Color.gold(),
        )
        preview = "\n".join([f"• `{k[:28]}...`" if len(k) > 28 else f"• `{k}`" for k in parsed_keys[:5]])
        if len(parsed_keys) > 5:
            preview += f"\n*...และอีก {len(parsed_keys) - 5} คีย์*"
        embed.add_field(name="ตัวอย่างคีย์ที่บันทึก", value=preview, inline=False)
        embed.set_footer(text=f"Added SuperIP by {interaction.user.name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class CreateProjectModal(discord.ui.Modal, title="สร้างโปรเจกต์ใหม่ / Create Project"):

    """Modal สำหรับใส่ชื่อโปรเจกต์และ Loadstring"""

    name_input = discord.ui.TextInput(

        label="ชื่อโปรเจกต์ (Project Name)",

        placeholder="PAYOMBØYZ HUB V2",

        style=discord.TextStyle.short,

        required=True,

        max_length=100,

    )

    desc_input = discord.ui.TextInput(

        label="คำอธิบายโปรเจกต์ (Description)",

        placeholder="ระบบแจกสคริปต์อัตโนมัติ สคริปต์อัปเดตรวดเร็ว ปลอดภัย",

        style=discord.TextStyle.paragraph,

        required=False,

        max_length=500,

    )

    script_input = discord.ui.TextInput(

        label="โค้ดสคริปต์ (Loadstring / Script)",

        placeholder="loadstring(game:HttpGet('https://...'))()",

        style=discord.TextStyle.paragraph,

        required=True,

        max_length=4000,

    )

    def __init__(

        self,

        project_type: str,

        map_mode: str = "multi",

        role_id: Optional[int] = None,

        require_key: bool = True,

        grant_mode: str = "key_role",

    ):

        super().__init__()

        self.project_type = project_type

        self.map_mode = map_mode if project_type == "get_script_no_key" else "single"

        self.grant_mode = grant_mode

        self.role_id = role_id

        self.require_key = grant_mode in {"key_role", "key_only"} if grant_mode else require_key

    async def on_submit(self, interaction: discord.Interaction):

        name = self.name_input.value.strip()

        pid = re.sub(r"[^a-zA-Z0-9_\-]", "_", name).lower()

        desc = self.desc_input.value.strip() or f"แผงควบคุมสคริปต์สำหรับโปรเจกต์: **{name}**"

        script = self.script_input.value.strip()

        project_data = {

            "id": pid,

            "name": name,

            "type": self.project_type,

            "map_mode": self.map_mode,

            "role_id": self.role_id,

            "require_key": self.require_key,

            "grant_mode": self.grant_mode,

            "default_script": script,

            "maps": [] if self.map_mode == "universal" else [

                {

                    "name": "Main Map",

                    "script": script,

                    "emoji": "📜",

                    "description": "สคริปต์หลักของระบบ"

                }

            ],

            "keys": {},

            "custom_buttons": [],

            "panel_config": {

                "title": f"{name} Panel",

                "description": desc,

                "color": "#FF0000",

                "image_url": None,

                "thumbnail_url": None,

                "footer": name,

            },

        }

        upsert_project(project_data)

        role_mode_str = {

            "key_role": "ใช้คีย์เพื่อรับยศ",

            "key_only": "ใช้คีย์โดยไม่รับยศ",

            "free_role": "รับยศฟรี",

            "free_open": "ฟรี ไม่ใช้คีย์และไม่ใช้ยศ",

        }.get(self.grant_mode, "ใช้คีย์" if self.require_key else "ไม่ใช้คีย์")

        role_line = f"• **บทบาทเชื่อมโยง:** <@&{self.role_id}>\n" if self.role_id else "• **บทบาทเชื่อมโยง:** ไม่ใช้ Role\n"

        embed = discord.Embed(

            title=f"✅ สร้างโปรเจกต์ '{name}' สำเร็จ!",

            description=f"• **Project ID:** `{pid}`\n"

                        f"• **ประเภท:** `{self.project_type}`\n"

                        f"• **โหมดสคริปต์:** `{ {'single': 'แมพเดียว', 'multi': 'หลายแมพ', 'universal': 'ใช้ได้ทุกแมพ'} .get(self.map_mode, self.map_mode) }`\n"

                        f"• **โหมดรับยศ:** `{role_mode_str}`\n"

                        f"{role_line}\n"

                        f"💡 **ขั้นตอนต่อไป:**\n"

                        f"• หากต้องการเพิ่มคีย์ ให้ใช้คำสั่ง `/add_key`\n"

                        f"• หากต้องการเพิ่มแมพแยก ให้ใช้คำสั่ง `/map add` (มี Popup)\n"

                        f"• หากต้องการติดตั้งแผง ให้ใช้ `/setup_panel`",

            color=discord.Color.green(),

        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

class MapAddModal(discord.ui.Modal, title="เพิ่มแมพใหม่ / Add Map"):
    """Popup Modal สำหรับเพิ่มแมพและวางโค้ด Loadstring ขนาดใหญ่"""
    map_name = discord.ui.TextInput(
        label="ชื่อเกม / แมพ (Map Name)",
        placeholder="เช่น Blox Fruits, King Legacy, Fisch, Brookhaven",
        style=discord.TextStyle.short,
        required=True,
        max_length=100,
    )
    emoji_input = discord.ui.TextInput(
        label="อิโมจิประจำแมพ (Emoji)",
        placeholder="เช่น 🍇, 👑, 🐟 หรือ <:name:id> (เว้นว่างไว้จะเป็น 🗺️)",
        style=discord.TextStyle.short,
        required=False,
        max_length=100,
    )
    desc_input = discord.ui.TextInput(
        label="คำอธิบายแมพสั้นๆ (Description)",
        placeholder="เช่น อัปเดตล่าสุด / ฟาร์มไว / No-Key VVIP",
        style=discord.TextStyle.short,
        required=False,
        max_length=200,
    )
    script_input = discord.ui.TextInput(
        label="โค้ดสคริปต์ (Loadstring / Script)",
        placeholder="loadstring(game:HttpGet('https://...'))()",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000,
    )

    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id

    async def on_submit(self, interaction: discord.Interaction):
        name = self.map_name.value.strip()
        emoji = self.emoji_input.value.strip() or "🗺️"
        desc = self.desc_input.value.strip() or "พร้อมใช้งาน (Active)"
        script = self.script_input.value.strip()

        ok, msg, pdata = add_map_to_project(self.project_id, name, script, emoji, desc)
        if not ok:
            await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"✅ {msg}",
            description=f"• **โปรเจกต์:** `{pdata.get('name')}`\n"
                        f"• **ชื่อแมพ:** {emoji} **{name}**\n"
                        f"• **คำอธิบาย:** {desc}\n"
                        f"• **จำนวนแมพทั้งหมด:** `{len(pdata.get('maps', []))}` แมพ",
            color=discord.Color.green(),
        )
        preview_text = script[:120] + "..." if len(script) > 120 else script
        embed.add_field(name="ตัวอย่างโค้ด Loadstring", value=f"```lua\n{preview_text}\n```", inline=False)
        embed.set_footer(text="💡 สมาชิกสามารถเลือกแมพนี้ได้ทันทีจาก buttons หรือกดปุ่ม Check Maps ในหน้าต่าง No-Key")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class MapEditModal(discord.ui.Modal, title="แก้ไขข้อมูลแมพ / Edit Map"):
    """Popup Modal สำหรับแก้ไขแมพเดิมที่เคยบันทึกไว้"""
    map_name = discord.ui.TextInput(
        label="ชื่อเกม / แมพ (Map Name)",
        style=discord.TextStyle.short,
        required=True,
        max_length=100,
    )
    emoji_input = discord.ui.TextInput(
        label="อิโมจิประจำแมพ (Emoji)",
        style=discord.TextStyle.short,
        required=False,
        max_length=100,
    )
    desc_input = discord.ui.TextInput(
        label="คำอธิบายแมพสั้นๆ (Description)",
        style=discord.TextStyle.short,
        required=False,
        max_length=200,
    )
    script_input = discord.ui.TextInput(
        label="โค้ดสคริปต์ (Loadstring / Script)",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000,
    )

    def __init__(self, project_id: str, old_map_name: str, current_data: dict):
        super().__init__()
        self.project_id = project_id
        self.old_map_name = old_map_name
        self.map_name.default = current_data.get("name", old_map_name)
        self.emoji_input.default = current_data.get("emoji", "🗺️")
        self.desc_input.default = current_data.get("description", "")
        self.script_input.default = current_data.get("script", "")

    async def on_submit(self, interaction: discord.Interaction):
        new_name = self.map_name.value.strip()
        emoji = self.emoji_input.value.strip() or "🗺️"
        desc = self.desc_input.value.strip() or "พร้อมใช้งาน (Active)"
        script = self.script_input.value.strip()

        ok, msg, pdata = edit_map_in_project(self.project_id, self.old_map_name, new_name, script, emoji, desc)
        if not ok:
            await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"✅ {msg}",
            description=f"• **โปรเจกต์:** `{pdata.get('name')}`\n"
                        f"• **ชื่อเดิม:** `{self.old_map_name}` ➔ **{new_name}** ({emoji})\n"
                        f"• **คำอธิบาย:** {desc}\n"
                        f"• **จำนวนแมพทั้งหมด:** `{len(pdata.get('maps', []))}` แมพ",
            color=discord.Color.green(),
        )
        preview_text = script[:120] + "..." if len(script) > 120 else script
        embed.add_field(name="ตัวอย่างโค้ดที่อัปเดต", value=f"```lua\n{preview_text}\n```", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RedeemKeyModal(discord.ui.Modal, title="Redeem a key"):
    """หน้าต่างสำหรับผู้ใช้กรอกคีย์เพื่อรับยศ"""
    key_input = discord.ui.TextInput(
        label="Enter script key below: *",
        placeholder="VZegGvaxErVhZfVBLUqGqYHuVxTmfOhDm",
        required=True,
        max_length=100,
        style=discord.TextStyle.short,
    )

    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        if not isinstance(member, discord.Member):
            try:
                member = await guild.fetch_member(interaction.user.id)
            except discord.HTTPException:
                await interaction.followup.send("❌ ดึงข้อมูลสมาชิกไม่สำเร็จ ลองใหม่อีกครั้ง", ephemeral=True)
                return

        project = get_project(self.project_id)
        require_key = project.get("require_key", True) if project else True
        grant_mode = project.get("grant_mode", "key_role" if require_key else "free_role") if project else "key_role"
        key_only = grant_mode == "key_only" or (project and project.get("require_key") and not project.get("role_id"))
        target_role_id = project.get("role_id") if project else DEFAULT_VVIP_ROLE_ID
        role = guild.get_role(target_role_id) if target_role_id else None

        if not key_only and not role:
            await interaction.followup.send(
                f"❌ ระบบขัดข้อง: ไม่พบบทบาท ID `{target_role_id}` ในเซิร์ฟเวอร์ โปรดแจ้งแอดมิน",
                ephemeral=True,
            )
            return

        # 1. คีย์พิเศษ (ใช้ซ้ำได้)
        if key == SPECIAL_KEY:
            if key_only:
                project.setdefault("authorized_users", {})[f"{guild.id}:{member.id}"] = True
                upsert_project(project)
                await interaction.followup.send(f"{EMOJI_CHILL} **ยืนยันคีย์สำเร็จแล้ว!** กด Get Script เพื่อรับสคริปต์ได้เลย (ไม่มีการมอบยศ)", ephemeral=True)
                return
            if role in member.roles:
                await interaction.followup.send(f"{EMOJI_CHILL} คุณมีบทบาทนี้อยู่แล้ว ไม่จำเป็นต้องรับซ้ำ!", ephemeral=True)
                return
            try:
                await member.add_roles(role, reason=f"Redeemed SPECIAL VVIP Key ({project.get('name') if project else 'PAYOMBØYZ'})")
                embed = discord.Embed(
                    title=f"{EMOJI_KING} PAYOMBØYZ HUB | ยืนยันคีย์พิเศษสำเร็จ",
                    description=f"{EMOJI_FIRE} ยินดีด้วย! คุณได้รับบทบาท **{role.name}** เรียบร้อยแล้ว\n\n"
                                f"{EMOJI_SUKUNA} *กดปุ่ม **Get Script** บนหน้าต่างเพื่อรับสคริปต์ไปรันได้ทันที*",
                    color=0x1a1a1a,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send(
                    f"{EMOJI_ANGRY} บอทไม่มีสิทธิ์มอบบทบาทนี้ โปรดแจ้งแอดมินให้เลื่อนตำแหน่ง Role บอทให้อยู่สูงกว่าบทบาทนี้",
                    ephemeral=True,
                )
            return

        # 2. ตรวจสอบผ่าน ScriptCenter API (เฉพาะโปรเจกต์ที่เชื่อมโยงระบบ ScriptCenter เท่านั้น)
        use_sc = project.get("use_scriptcenter", False) if project else False
        if use_sc:
            sc = get_sc_client()
            sc_error_msg = None
            if sc.is_configured():
                try:
                    sc_res = await sc.link_key(str(member.id), member.name, key)
                    if sc_res.get("ok"):
                        if key_only:
                            project.setdefault("authorized_users", {})[f"{guild.id}:{member.id}"] = True
                            upsert_project(project)
                            await interaction.followup.send(
                                f"{EMOJI_CHILL} {sc_res.get('message', 'ผูกคีย์สำเร็จ')} (กด Get Script เพื่อรับสคริปต์)",
                                ephemeral=True,
                            )
                            return

                        exp_text = ""
                        try:
                            exp_res = await sc.check_expiry(str(member.id))
                            if exp_res.get("ok"):
                                exp_text = sc.format_expiry_text(exp_res.get("keys", []))
                        except Exception:
                            pass

                        if role in member.roles:
                            embed = discord.Embed(
                                title=f"{EMOJI_KING} PAYOMBØYZ HUB | ผูกคีย์สำเร็จ",
                                description=(
                                    f"{EMOJI_FIRE} **คุณมีบทบาท {role.mention} อยู่แล้ว** และได้ทำการผูกคีย์กับบัญชีเรียบร้อย!\n\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    + (f"{EMOJI_SNIPER} **ข้อมูลวันหมดอายุ (LICENSE STATUS):**\n{exp_text}\n\n" if exp_text else "")
                                    + f"{EMOJI_CHILL} สถานะ: `{sc_res.get('message', 'สำเร็จ')}`\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"{EMOJI_SUKUNA} *ระบบพร้อมใช้งาน รันสคริปต์ได้ทันที*"
                                ),
                                color=0x1a1a1a,
                            )
                            await interaction.followup.send(embed=embed, ephemeral=True)
                            return

                        try:
                            await member.add_roles(role, reason=f"Redeemed ScriptCenter Key ({project.get('name') if project else 'PAYOMBØYZ'})")
                            embed = discord.Embed(
                                title=f"{EMOJI_KING} PAYOMBØYZ HUB | ยืนยันและผูกคีย์สำเร็จ",
                                description=(
                                    f"{EMOJI_FIRE} **ยืนยันคีย์สำเร็จผ่านระบบ ScriptCenter API!**\n\n"
                                    f"{EMOJI_PAYOMBOYZ} **บทบาทที่ได้รับ:** {role.mention}\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    + (f"{EMOJI_SNIPER} **ข้อมูลวันหมดอายุ:**\n{exp_text}\n" if exp_text else "")
                                    + f"{EMOJI_CHILL} **สถานะ:** `{sc_res.get('message', 'สำเร็จ')}`\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"{EMOJI_SUKUNA} *กดปุ่ม **Get Script** บนหน้าต่างเพื่อรับสคริปต์ไปรันได้เลย*"
                                ),
                                color=0x1a1a1a,
                            )
                            await interaction.followup.send(embed=embed, ephemeral=True)
                        except discord.Forbidden:
                            await interaction.followup.send(
                                f"{EMOJI_ANGRY} **บอทไม่มีสิทธิ์มอบบทบาทนี้!** โปรดแจ้งแอดมินให้เลื่อนตำแหน่ง Role บอทให้อยู่สูงกว่าบทบาทนี้",
                                ephemeral=True,
                            )
                        return
                    else:
                        sc_error_msg = sc_res.get("message")
                except Exception as e:
                    sc_error_msg = str(e)
            await interaction.followup.send(
                f"{EMOJI_ANGRY} **{sc_error_msg or 'คีย์ไม่ถูกต้อง หรือถูกผูกไปแล้ว!'}**",
                ephemeral=True,
            )
            return

        # 3. โหมดคลังคีย์แยกประจำโปรเจกต์ (Project Key Pool Isolation)
        proj_keys = project.get("keys", {}) if project else {}
        pname = project.get("name", "PAYOMBØYZ HUB") if project else "PAYOMBØYZ HUB"

        if key in proj_keys and proj_keys[key] is True:
            is_master_key = key.startswith("PAYOMBOYZHUB-ALL-")
            if key_only:
                project.setdefault("authorized_users", {})[f"{guild.id}:{member.id}"] = True
                if not is_master_key:
                    proj_keys[key] = False
                project.setdefault("redeemed_users", {})[key] = {
                    "user_id": member.id,
                    "user_name": member.name,
                    "time": int(time.time()),
                }
                upsert_project(project)
                await interaction.followup.send(f"{EMOJI_CHILL} **ยืนยันคีย์สำเร็จ!** กดปุ่ม Get Script เพื่อรับสคริปต์ได้เลย", ephemeral=True)
                return

            if role in member.roles:
                await interaction.followup.send(f"{EMOJI_CHILL} คุณมีบทบาท **{role.name}** อยู่แล้ว ไม่จำเป็นต้องรับซ้ำ!", ephemeral=True)
                return

            try:
                await member.add_roles(role, reason=f"Redeemed Key for {pname}")
                if not is_master_key:
                    proj_keys[key] = False
                project.setdefault("redeemed_users", {})[key] = {
                    "user_id": member.id,
                    "user_name": member.name,
                    "time": int(time.time()),
                }
                upsert_project(project)
                embed = discord.Embed(
                    title=f"{EMOJI_KING} {pname} | ยืนยันคีย์สำเร็จ",
                    description=(
                        f"{EMOJI_FIRE} **ยืนยันคีย์ถูกต้องสำหรับ {pname}!**\n"
                        f"{EMOJI_PAYOMBOYZ} **บทบาทที่ได้รับ:** {role.mention}\n\n"
                        f"{EMOJI_SUKUNA} *กดปุ่ม **Get Script** ด้านล่างเพื่อรับสคริปต์ไปใช้งานได้ทันที*"
                    ),
                    color=0x1a1a1a,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send(
                    f"{EMOJI_ANGRY} บอทไม่มีสิทธิ์มอบบทบาทนี้ โปรดแจ้งแอดมินให้เลื่อนตำแหน่ง Role บอทให้อยู่สูงกว่าบทบาทนี้",
                    ephemeral=True,
                )
        elif key in proj_keys and proj_keys[key] is False:
            await interaction.followup.send(
                f"{EMOJI_ANGRY} **คีย์นี้ถูกใช้งานไปแล้ว!** กรุณาใช้คีย์ใหม่ที่ยังไม่เคยถูก Redeem",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"{EMOJI_ANGRY} **ไม่พบคีย์นี้ในระบบของโปรเจกต์ {pname}!** โปรดตรวจสอบรหัสคีย์ของคุณใหม่อีกครั้ง",
                ephemeral=True,
            )

# =========================================================================

# 🌐 SCRIPTCENTER SHOP API MODALS & PANELS

# =========================================================================

class SCResetHWIDModal(discord.ui.Modal, title="รีเซ็ต HWID (Device Reset)"):
    """หน้าต่างสำหรับผู้ใช้กรอกคีย์เพื่อรีเซ็ต HWID ผ่าน ScriptCenter API"""
    key_input = discord.ui.TextInput(
        label="License Key *",
        placeholder="กรอก License Key ที่ต้องการรีเซ็ต HWID",
        required=True,
        max_length=100,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        sc = get_sc_client()
        key = self.key_input.value.strip()
        uid = str(interaction.user.id)
        res = await sc.reset_hwid(uid, key)
        if res.get("ok"):
            embed = discord.Embed(
                title=f"{EMOJI_SUKUNA} PAYOMBØYZ | รีเซ็ต HWID สำเร็จ",
                description=(
                    f"{EMOJI_ZA} **{res.get('message', 'รีเซ็ต HWID สำเร็จเรียบร้อยแล้ว')}**\n\n"
                    f"• **คีย์:** `{key}`\n"
                    f"{EMOJI_FIRE} **สถานะ:** ปลดล็อกอุปกรณ์เรียบร้อยแล้ว นำไปรันบนเครื่องใหม่ได้ทันที"
                ),
                color=0x1a1a1a,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title=f"{EMOJI_ANGRY} PAYOMBØYZ | รีเซ็ต HWID ไม่สำเร็จ",
                description=(
                    f"⚠️ **{res.get('message', 'เกิดข้อผิดพลาดในการรีเซ็ต HWID')}**\n\n"
                    f"• ตรวจสอบว่าคีย์ถูกต้อง และผูกไว้กับบัญชีของคุณ หรือยังไม่เกินโควตารีเซ็ต"
                ),
                color=0x8b0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class SCLinkKeyModal(discord.ui.Modal, title="ผูกคีย์ (Link License Key)"):
    """หน้าต่างผูกคีย์ ScriptCenter พร้อมมอบยศอัตโนมัติ"""
    key_input = discord.ui.TextInput(
        label="License Key *",
        placeholder="กรอก License Key ของคุณ",
        required=True,
        max_length=100,
        style=discord.TextStyle.short,
    )

    def __init__(self, role_id: Optional[int] = None):
        super().__init__()
        self.role_id = role_id or DEFAULT_VVIP_ROLE_ID

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        sc = get_sc_client()
        key = self.key_input.value.strip()
        uid = str(interaction.user.id)
        uname = interaction.user.name

        res = await sc.link_key(uid, uname, key)
        if res.get("ok"):
            guild = interaction.guild
            role_line = ""
            if guild and self.role_id:
                member = interaction.user
                if not isinstance(member, discord.Member):
                    try:
                        member = await guild.fetch_member(interaction.user.id)
                    except Exception:
                        member = None
                if member:
                    role = guild.get_role(self.role_id)
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role, reason="Linked ScriptCenter Key")
                            role_line = f"\n{EMOJI_PAYOMBOYZ} **ได้รับบทบาท:** {role.mention}"
                        except Exception:
                            pass
                    elif role:
                        role_line = f"\n{EMOJI_PAYOMBOYZ} **คุณมีบทบาท:** {role.mention} อยู่แล้ว"

            exp_res = await sc.check_expiry(uid)
            exp_text = sc.format_expiry_text(exp_res.get("keys", [])) if exp_res.get("ok") else ""
            embed = discord.Embed(
                title=f"{EMOJI_KING} PAYOMBØYZ HUB | ผูกคีย์สำเร็จ (KEY LINKED)",
                description=(
                    f"{EMOJI_FIRE} **{res.get('message', 'ผูกคีย์กับ Discord สำเร็จ')}**{role_line}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    + (f"{EMOJI_SNIPER} **ข้อมูลวันหมดอายุ (LICENSE STATUS):**\n{exp_text}\n" if exp_text else "")
                    + f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{EMOJI_SUKUNA} *สถานะสิทธิ์พร้อมใช้งาน รันผ่าน Loader ได้ทันที*"
                ),
                color=0x1a1a1a,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title=f"{EMOJI_ANGRY} PAYOMBØYZ | ผูกคีย์ไม่สำเร็จ",
                description=f"⚠️ **{res.get('message', 'คีย์ไม่ถูกต้อง หรือถูกผูกไปแล้ว')}**\n\n💡 กรุณาตรวจสอบรหัสคีย์ของคุณใหม่อีกครั้ง",
                color=0x8b0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class ScriptCenterPanelView(discord.ui.View):
    """
    แผงควบคุมระบบ ScriptCenter API:
    - 👑 ผูกคีย์ (Link Key) [Primary] -> custom_id: sc_link
    - 🎯 คีย์ของฉัน (My Keys) [Secondary] -> custom_id: sc_keys
    - 🕶️ เช็ควันหมดอายุ (Check Expiry) [Secondary] -> custom_id: sc_exp
    - 🔥 รับโหลดเดอร์ (Get Loader) [Success] -> custom_id: sc_loader
    - ⚡ รี HWID (Reset HWID) [Danger] -> custom_id: sc_reset
    """
    def __init__(self, role_id: Optional[int] = None):
        super().__init__(timeout=None)
        self.role_id = role_id or DEFAULT_VVIP_ROLE_ID

    @discord.ui.button(
        label="ผูกคีย์",
        style=discord.ButtonStyle.primary,
        emoji=discord.PartialEmoji.from_str("<:payomboyz:1551064225974325318>"),
        custom_id="sc_link",
        row=0
    )
    async def btn_link(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SCLinkKeyModal(self.role_id))

    @discord.ui.button(
        label="คีย์ของฉัน",
        style=discord.ButtonStyle.secondary,
        emoji=discord.PartialEmoji.from_str("<:pbg_sniper:1551054607986458734>"),
        custom_id="sc_keys",
        row=0
    )
    async def btn_my_keys(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        sc = get_sc_client()
        uid = str(interaction.user.id)
        res = await sc.get_my_keys(uid)
        if res.get("ok"):
            keys = res.get("keys", [])
            if not keys:
                msg = res.get("message") or "ยังไม่มีคีย์ที่ผูกกับบัญชีนี้"
                embed = discord.Embed(
                    title=f"{EMOJI_WAIT} PAYOMBØYZ | ไม่พบคีย์ที่ผูกไว้",
                    description=f"{EMOJI_QUESTION} {msg}\n\n💡 กดปุ่ม **ผูกคีย์** `{EMOJI_PAYOMBOYZ}` เพื่อลงทะเบียนคีย์เข้ากับบัญชีของคุณ",
                    color=0x2b2d42,
                )
            else:
                lines = [f"• `{k.get('key', k) if isinstance(k, dict) else k}` ➔ {EMOJI_CHILL} Active" for k in keys]
                embed = discord.Embed(
                    title=f"{EMOJI_SNIPER} PAYOMBØYZ | คีย์ของคุณ ({len(keys)} รายการ)",
                    description=(
                        f"{EMOJI_KING} **รายการ License Key ที่ลงทะเบียนในระบบ:**\n\n"
                        + "\n".join(lines)
                        + f"\n\n{EMOJI_FIRE} *สามารถนำไปรันผ่านสคริปต์ได้ทันที*"
                    ),
                    color=0x1a1a1a,
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"{EMOJI_ANGRY} **เกิดข้อผิดพลาด:** {res.get('message', 'ดึงข้อมูลคีย์ไม่สำเร็จ')}", ephemeral=True)

    @discord.ui.button(
        label="เช็ควันหมดอายุ",
        style=discord.ButtonStyle.secondary,
        emoji=discord.PartialEmoji.from_str("<:pbg_chill:1551064392139804702>"),
        custom_id="sc_exp",
        row=0
    )
    async def btn_check_expiry(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        sc = get_sc_client()
        uid = str(interaction.user.id)
        res = await sc.check_expiry(uid)
        if res.get("ok"):
            keys = res.get("keys", [])
            txt = sc.format_expiry_text(keys)

            role_note = ""
            guild = interaction.guild
            if guild and self.role_id and keys:
                member = interaction.user
                if not isinstance(member, discord.Member):
                    try:
                        member = await guild.fetch_member(interaction.user.id)
                    except Exception:
                        member = None
                if member:
                    role = guild.get_role(self.role_id)
                    if role and role not in member.roles:
                        has_active = any(k.get("isLifetime") or k.get("firstUse") or (k.get("daysRemaining", 0) > 0) for k in keys)
                        if has_active:
                            try:
                                await member.add_roles(role, reason="Auto-grant from active ScriptCenter key check")
                                role_note = f"\n\n{EMOJI_FIRE} **ได้รับบทบาท {role.mention} เรียบร้อยแล้ว!**"
                            except Exception:
                                pass
            embed = discord.Embed(
                title=f"{EMOJI_CHILL} PAYOMBØYZ | สถานะวันหมดอายุ (EXPIRY STATUS)",
                description=f"{EMOJI_SNIPER} **ข้อมูลคีย์ที่ตรวจพบ:**\n{txt}{role_note}",
                color=0x1a1a1a if keys else 0x2b2d42,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"{EMOJI_ANGRY} **เกิดข้อผิดพลาด:** {res.get('message', 'ตรวจสอบวันหมดอายุไม่สำเร็จ')}", ephemeral=True)

    @discord.ui.button(
        label="รับโหลดเดอร์",
        style=discord.ButtonStyle.success,
        emoji=discord.PartialEmoji.from_str("<a:anime_fire:1551069928105447485>"),
        custom_id="sc_loader",
        row=1
    )
    async def btn_loader(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        sc = get_sc_client()
        uid = str(interaction.user.id)
        res = await sc.get_loader(uid)
        if res.get("ok"):
            loader_code = res.get("loader", "")
            if not loader_code:
                await interaction.followup.send(f"{EMOJI_WAIT} ไม่พบโค้ดโหลดเดอร์ในระบบ", ephemeral=True)
                return
            if len(loader_code) < 1900:
                await interaction.followup.send(
                    f"{EMOJI_FIRE} **PAYOMBØYZ LUA LOADER:**\n```lua\n{loader_code}\n```",
                    ephemeral=True
                )
            else:
                file = discord.File(io.BytesIO(loader_code.encode("utf-8")), filename="payomboyz_loader.lua")
                await interaction.followup.send(f"{EMOJI_FIRE} **โค้ดโหลดเดอร์ของคุณ:**", file=file, ephemeral=True)
        else:
            await interaction.followup.send(f"{EMOJI_ANGRY} {res.get('message', 'ไม่พบคีย์ที่ผูกไว้ หรือยังไม่ได้รับสิทธิ์')}", ephemeral=True)

    @discord.ui.button(
        label="รี HWID",
        style=discord.ButtonStyle.danger,
        emoji=discord.PartialEmoji.from_str("<a:Sukuna:1551069997999067228>"),
        custom_id="sc_reset",
        row=1
    )
    async def btn_reset_hwid(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SCResetHWIDModal())

async def build_scriptcenter_panel_message(role_id: Optional[int] = None) -> Tuple[discord.Embed, ScriptCenterPanelView]:
    """สร้าง Embed และ View สำหรับ ScriptCenter Shop Panel ด้วยธีมพรีเมียม PAYOMBØYZ"""
    sc = get_sc_client()
    panel_res = await sc.get_panel()
    pdata = panel_res.get("panel", {}) if panel_res.get("ok") else {}

    shop_name = pdata.get("shopName", "PAYOMBØYZ HUB")
    desc = pdata.get("description") or (
        f"{EMOJI_FIRE} **ระบบจัดการและยืนยันสิทธิ์สคริปต์ระดับพรีเมียม (ScriptCenter API)**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI_KING} **ผูกคีย์ (Link Key)**\n"
        f"↳ เชื่อมต่อ License Key เข้ากับบัญชี Discord เพื่อรับยศทันที\n\n"
        f"{EMOJI_SNIPER} **คีย์ของฉัน (My Keys)**\n"
        f"↳ ตรวจสอบรายชื่อคีย์ทั้งหมดที่คุณครอบครอง\n\n"
        f"{EMOJI_CHILL} **เช็ควันหมดอายุ (Check Expiry)**\n"
        f"↳ ดูระยะเวลาคงเหลือของคีย์ทุกตัว หรือสถานะตลอดชีพ (Lifetime)\n\n"
        f"{EMOJI_FIRE} **รับโหลดเดอร์ (Get Loader)**\n"
        f"↳ รับโค้ด Lua Loader สำหรับนำไปรันใน Executor ทันที\n\n"
        f"{EMOJI_SUKUNA} **รี HWID (Reset HWID)**\n"
        f"↳ รีเซ็ตอุปกรณ์เพื่อปลดล็อกและเปลี่ยนเครื่องใช้งาน\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    logo_url = pdata.get("logoUrl")

    embed = discord.Embed(
        title=f"{EMOJI_PAYOMBOYZ} {shop_name.upper()} | KEY MANAGEMENT SYSTEM",
        description=desc,
        color=0x111111,
    )
    if logo_url:
        embed.set_thumbnail(url=logo_url)
    embed.set_footer(text=f"{shop_name} • Premium Script System • Powered by ScriptCenter")
    view = ScriptCenterPanelView(role_id=role_id)
    return embed, view

class EmbedCreateModal(discord.ui.Modal, title="สร้างข้อความ Embed"):

    """Modal สำหรับสร้างกล่องข้อความ Embed แบบอิสระ"""

    embed_title = discord.ui.TextInput(

        label="หัวข้อ (Embed Title)",

        placeholder="ประกาศอัปเดตสคริปต์ใหม่",

        required=True,

        max_length=256,

    )

    embed_desc = discord.ui.TextInput(

        label="เนื้อหา (Description)",

        placeholder="รายละเอียดการอัปเดต หรือข้อความที่ต้องการสื่อสาร...",

        style=discord.TextStyle.paragraph,

        required=True,

        max_length=4000,

    )

    embed_color = discord.ui.TextInput(

        label="รหัสสี (Hex เช่น #FF0000 หรือชื่อสี red/green)",

        placeholder="#FF0000",

        required=False,

        default="#FF0000",

        max_length=20,

    )

    embed_image = discord.ui.TextInput(

        label="ลิงก์รูปภาพใหญ่ (Image URL)",

        placeholder="https://example.com/banner.png",

        required=False,

        max_length=500,

    )

    embed_footer = discord.ui.TextInput(

        label="ข้อความท้าย (Footer Text)",

        placeholder="PAYOMBØYZ Official",

        required=False,

        max_length=150,

    )

    def __init__(self, channel: discord.TextChannel):

        super().__init__()

        self.target_channel = channel

    async def on_submit(self, interaction: discord.Interaction):

        color = parse_color(self.embed_color.value)

        embed = discord.Embed(

            title=self.embed_title.value.strip(),

            description=self.embed_desc.value.strip(),

            color=color,

        )

        if self.embed_image.value.strip():

            embed.set_image(url=self.embed_image.value.strip())

        if self.embed_footer.value.strip():

            embed.set_footer(text=self.embed_footer.value.strip())

        try:

            msg = await self.target_channel.send(embed=embed)

            await interaction.response.send_message(

                f"✅ ส่ง Embed ไปยัง {self.target_channel.mention} เรียบร้อยแล้ว! (Message ID: `{msg.id}`)",

                ephemeral=True,

            )

        except Exception as e:

            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการส่งข้อความ: {e}", ephemeral=True)

class EmbedEditModal(discord.ui.Modal, title="แก้ไขข้อความ Embed"):

    """Modal สำหรับแก้ไขกล่องข้อความ Embed เดิม"""

    embed_title = discord.ui.TextInput(label="หัวข้อ (Embed Title)", required=True, max_length=256)

    embed_desc = discord.ui.TextInput(label="เนื้อหา (Description)", style=discord.TextStyle.paragraph, required=True, max_length=4000)

    embed_color = discord.ui.TextInput(label="รหัสสี (Hex เช่น #FF0000)", required=False, max_length=20)

    embed_image = discord.ui.TextInput(label="ลิงก์รูปภาพใหญ่ (Image URL)", required=False, max_length=500)

    embed_footer = discord.ui.TextInput(label="ข้อความท้าย (Footer Text)", required=False, max_length=150)

    def __init__(self, message: discord.Message, initial_title: str, initial_desc: str, initial_color: str, initial_image: str, initial_footer: str):

        super().__init__()

        self.target_message = message

        self.embed_title.default = initial_title[:256]

        self.embed_desc.default = initial_desc[:4000]

        self.embed_color.default = initial_color or "#FF0000"

        self.embed_image.default = initial_image or ""

        self.embed_footer.default = initial_footer or ""

    async def on_submit(self, interaction: discord.Interaction):

        color = parse_color(self.embed_color.value)

        embed = discord.Embed(

            title=self.embed_title.value.strip(),

            description=self.embed_desc.value.strip(),

            color=color,

        )

        if self.embed_image.value.strip():

            embed.set_image(url=self.embed_image.value.strip())

        if self.embed_footer.value.strip():

            embed.set_footer(text=self.embed_footer.value.strip())

        try:

            await self.target_message.edit(embed=embed)

            await interaction.response.send_message(

                f"✅ แก้ไข Embed (ID: `{self.target_message.id}`) เรียบร้อยแล้ว!",

                ephemeral=True,

            )

        except Exception as e:

            await interaction.response.send_message(f"❌ ไม่สามารถแก้ไขข้อความได้: {e}", ephemeral=True)

# =========================================================================

# 🗺️ SELECT MENU: Map Selector for Get-Script-No-Key

# =========================================================================

class GetRolePanelView(discord.ui.View):

    """

    แผงควบคุมระบบ Get-Role:

    - 🔑 Redeem Key (Success/Green) -> เปิด Modal แลกคีย์ (เมื่อ require_key=True)

    - 🎖️ Claim Role (Success/Green) -> รับยศฟรีทันทีไม่ต้องใช้คีย์ (เมื่อ require_key=False)

    - 👤 Check Role (Primary/Blurple) -> ตรวจสอบว่ามียศแล้วหรือยัง

    - 📜 Get Script (Primary/Blurple) -> แสดงสคริปต์ (ตรวจสอบสิทธิ์ยศ)

    - Custom Buttons (เช่น ปุ่มสั่งซื้อ /ad หรือปุ่มลิงก์/แอคชั่นที่แอดมินเพิ่ม)

    """

    def __init__(self, project_id: str, script_text: Optional[str] = None, custom_buttons: Optional[list[dict]] = None):

        super().__init__(timeout=None)

        self.project_id = project_id

        self.script_text = script_text or DEFAULT_SCRIPT

        project = get_project(self.project_id)

        require_key = project.get("require_key", True) if project else True

        grant_mode = project.get("grant_mode", "key_role" if require_key else "free_role") if project else "key_role"

        panel_buttons = project.get("panel_buttons", {}) if project else {}

        # 1. Action Button: Redeem Key หรือ Claim Role

        if require_key and panel_buttons.get("show_redeem_key", True):

            btn_key = discord.ui.Button(

                label="Redeem Key",

                style=discord.ButtonStyle.success,

                emoji=discord.PartialEmoji.from_str("<:payomboyz:1551064225974325318>"),
                custom_id=f"payom_redeem_{project_id}",

                row=0,

            )

            btn_key.callback = self._redeem_callback

            self.add_item(btn_key)

        elif grant_mode == "free_role" and panel_buttons.get("show_claim_role", True):

            btn_claim = discord.ui.Button(

                label="Claim Role (รับยศฟรี)",

                style=discord.ButtonStyle.success,

                emoji=discord.PartialEmoji.from_str("<:pbg_king:1551063202002108446>"),
                custom_id=f"payom_claimrole_{project_id}",

                row=0,

            )

            btn_claim.callback = self._claim_role_callback

            self.add_item(btn_claim)

        if project and project.get("role_id") and panel_buttons.get("show_check_role", True):

            btn_check = discord.ui.Button(

                label="Check Role",

                style=discord.ButtonStyle.primary,

                emoji=discord.PartialEmoji.from_str("<:pbg_chill:1551064392139804702>"),
                custom_id=f"payom_checkrole_{project_id}",

                row=0,

            )

            btn_check.callback = self._check_role_callback

            self.add_item(btn_check)

        # 3. Get Script

        if panel_buttons.get("show_main_script", True):

            btn_script = discord.ui.Button(

                label="Get Script",

                style=discord.ButtonStyle.primary,

                emoji="📜",

                custom_id=f"payom_script_{project_id}",

                row=0,

            )

            btn_script.callback = self._script_callback

            self.add_item(btn_script)

        # 4. แนบปุ่มเพิ่มเติมจาก config ของโปรเจกต์

        self._attach_custom_buttons(project, custom_buttons)

    def _attach_custom_buttons(self, project: Optional[dict], custom_buttons: Optional[list[dict]] = None):

        if not project:

            return

        custom_buttons = project.get("custom_buttons", []) if custom_buttons is None else custom_buttons

        for i, btn in enumerate(custom_buttons[:5]):

            label = btn.get("label", "Button")

            emoji = parse_emoji(btn.get("emoji"))

            action = btn.get("action", "link")

            style = parse_button_style(btn.get("style", "link" if action == "link" else "primary"))

            url = btn.get("url")

            if action == "link" and url:

                self.add_item(

                    discord.ui.Button(

                        label=label,

                        style=discord.ButtonStyle.link,

                        url=url,

                        emoji=emoji,

                        row=1,

                    )

                )

            else:

                custom_id = f"payom_btn_{self.project_id}_{i}"

                b = discord.ui.Button(

                    label=label,

                    style=style,

                    emoji=emoji,

                    custom_id=custom_id,

                    row=1,

                )

                b.callback = self._make_custom_callback(btn)

                self.add_item(b)

    def _make_custom_callback(self, btn_info: dict):

        async def callback(interaction: discord.Interaction):

            action = btn_info.get("action", "message")

            if action == "message":

                text = btn_info.get("payload", "ขอขอบคุณที่ใช้บริการ!")

                embed = discord.Embed(title=btn_info.get("label", "ข้อมูล"), description=text, color=discord.Color.blue())

                await interaction.response.send_message(embed=embed, ephemeral=True)

            elif action == "redeem":

                await interaction.response.send_modal(RedeemKeyModal(self.project_id))

            elif action == "script":

                await self._script_callback(interaction)

            elif action == "check_role":

                await self._check_role_callback(interaction)

        return callback

    async def _send_reply(self, interaction: discord.Interaction, content: Optional[str] = None, embed: Optional[discord.Embed] = None):

        try:

            if interaction.response.is_done():

                if embed:

                    await interaction.followup.send(embed=embed, ephemeral=True)

                else:

                    await interaction.followup.send(content=content, ephemeral=True)

            else:

                if embed:

                    await interaction.response.send_message(embed=embed, ephemeral=True)

                else:

                    await interaction.response.send_message(content=content, ephemeral=True)

        except Exception as e:

            print(f"[-] Failed to send interaction reply: {e}", flush=True)

    async def _redeem_callback(self, interaction: discord.Interaction):

        await interaction.response.send_modal(RedeemKeyModal(self.project_id))

    async def _claim_role_callback(self, interaction: discord.Interaction):

        try:

            if not interaction.response.is_done():

                await interaction.response.defer(ephemeral=True)

        except Exception:

            pass

        guild = interaction.guild

        if not guild:

            await self._send_reply(interaction, content="❌ ใช้งานได้เฉพาะในเซิร์ฟเวอร์")

            return

        member = interaction.user

        if not isinstance(member, discord.Member):

            try:

                member = await guild.fetch_member(interaction.user.id)

            except discord.HTTPException:

                await self._send_reply(interaction, content="❌ ดึงข้อมูลสมาชิกไม่สำเร็จ ลองใหม่อีกครั้ง")

                return

        project = get_project(self.project_id)

        target_role_id = project.get("role_id") if project else DEFAULT_VVIP_ROLE_ID

        role = guild.get_role(target_role_id) if target_role_id else None

        if project and project.get("require_key") and not role:

            authorized = project.get("authorized_users", {}).get(f"{guild.id}:{member.id}", False)

            text = "✅ ยืนยันคีย์แล้ว รับสคริปต์ได้" if authorized else "❌ ยังไม่ได้ Redeem Key"

            await self._send_reply(interaction, content=text)

            return

        if not role:

            await self._send_reply(

                interaction, content=f"❌ ไม่พบบทบาท ID `{target_role_id}` ในเซิร์ฟเวอร์ โปรดแจ้งแอดมิน"

            )

            return

        if role in member.roles:

            embed = discord.Embed(

                title="PAYOMBØYZ HUB | 🎖️ รับบทบาท",

                description=f"⚠️ คุณมีบทบาท {role.mention} อยู่แล้ว ไม่จำเป็นต้องรับซ้ำ!\n"

                            f"สามารถกดปุ่ม **Get Script** เพื่อรับสคริปต์ได้ทันที",

                color=discord.Color.yellow(),

            )

            await self._send_reply(interaction, embed=embed)

            return

        try:

            pname = project.get('name') if project else 'PAYOMBØYZ'

            await member.add_roles(role, reason=f"Claimed Free Role for {pname}")

            embed = discord.Embed(

                title="PAYOMBØYZ HUB | 🎉 รับบทบาทสำเร็จ",

                description=f"✅ **ยินดีต้อนรับ!** คุณได้รับบทบาท {role.mention} เรียบร้อยแล้ว (โหมดรับยศฟรี)\n\n"

                            f"💡 คุณสามารถกดปุ่ม **Get Script** ด้านล่างเพื่อรับสคริปต์ไปรันได้เลย",

                color=discord.Color.green(),

            )

            await self._send_reply(interaction, embed=embed)

        except discord.Forbidden:

            await self._send_reply(

                interaction,

                content="❌ บอทไม่มีสิทธิ์มอบบทบาทนี้ โปรดแจ้งแอดมินให้เลื่อนตำแหน่งยศบอทให้อยู่สูงกว่าบทบาทนี้",

            )

        except Exception as e:

            await self._send_reply(

                interaction,

                content=f"❌ เกิดข้อผิดพลาดในการมอบบทบาท: {e}",

            )

    async def _check_role_callback(self, interaction: discord.Interaction):

        try:

            if not interaction.response.is_done():

                await interaction.response.defer(ephemeral=True)

        except Exception:

            pass

        guild = interaction.guild

        if not guild:

            await self._send_reply(interaction, content="❌ ใช้งานได้เฉพาะในเซิร์ฟเวอร์")

            return

        member = interaction.user

        if not isinstance(member, discord.Member):

            try:

                member = await guild.fetch_member(interaction.user.id)

            except discord.HTTPException:

                await self._send_reply(interaction, content="❌ ดึงข้อมูลสมาชิกไม่สำเร็จ ลองใหม่อีกครั้ง")

                return

        project = get_project(self.project_id)

        target_role_id = project.get("role_id") if project else DEFAULT_VVIP_ROLE_ID

        if project and project.get("require_key") and not target_role_id:

            authorized_users = project.get("authorized_users", [])

            authorized = f"{guild.id}:{interaction.user.id}" in authorized_users

            await self._send_reply(

                interaction,

                content="✅ ยืนยันคีย์แล้ว สามารถใช้ Get Script ได้" if authorized else "❌ ต้อง Redeem Key ก่อน"

            )

            return

        role = guild.get_role(target_role_id) if target_role_id else None

        if not role:

            await self._send_reply(

                interaction, content=f"❌ ไม่พบบทบาท ID `{target_role_id}` ในเซิร์ฟเวอร์"

            )

            return

        use_sc = project.get("use_scriptcenter", False) if project else False
        sc = get_sc_client()
        pname = project.get("name", "PAYOMBØYZ HUB") if project else "PAYOMBØYZ HUB"

        if role in member.roles:
            extra_exp = ""
            if use_sc and sc.is_configured():
                try:
                    exp_res = await sc.check_expiry(str(member.id))
                    if exp_res.get("ok") and exp_res.get("keys"):
                        extra_exp = f"\n\n**📅 ข้อมูลวันหมดอายุ (ScriptCenter):**\n{sc.format_expiry_text(exp_res.get('keys', []))}"
                except Exception:
                    pass

            embed = discord.Embed(
                title=f"{EMOJI_KING} {pname} | สถานะสิทธิ์ของคุณ",
                description=(
                    f"{EMOJI_FIRE} **คุณมีบทบาท {role.mention} เรียบร้อยแล้ว!**\n\n"
                    f"{EMOJI_PAYOMBOYZ} **สถานะ:** ได้รับสิทธิ์ใช้งาน VIP เรียบร้อยแล้ว{extra_exp}\n\n"
                    f"{EMOJI_SUKUNA} *สามารถกดปุ่ม **Get Script** ด้านล่างเพื่อรับสคริปต์ได้ทันที*"
                ),
                color=0x1a1a1a,
            )
            await self._send_reply(interaction, embed=embed)
            return
        else:
            if use_sc and sc.is_configured():
                try:
                    exp_res = await sc.check_expiry(str(member.id))
                    if exp_res.get("ok") and exp_res.get("keys"):
                        keys = exp_res.get("keys", [])
                        has_active = any(k.get("isLifetime") or k.get("firstUse") or (k.get("daysRemaining", 0) > 0) for k in keys)
                        if has_active:
                            try:
                                await member.add_roles(role, reason="Auto-restored role from active ScriptCenter key check")
                                embed = discord.Embed(
                                    title=f"{EMOJI_KING} {pname} | กู้คืนสิทธิ์สำเร็จ",
                                    description=(
                                        f"{EMOJI_FIRE} **พบคีย์ของคุณในระบบ ScriptCenter!** จึงได้มอบบทบาท {role.mention} คืนให้อัตโนมัติ\n\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"{EMOJI_SNIPER} **ข้อมูลวันหมดอายุ:**\n{sc.format_expiry_text(keys)}\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                        f"{EMOJI_SUKUNA} *กดปุ่ม **Get Script** เพื่อรับสคริปต์ได้ทันที*"
                                    ),
                                    color=0x1a1a1a,
                                )
                                await self._send_reply(interaction, embed=embed)
                                return
                            except Exception:
                                pass
                except Exception:
                    pass

            r_key = project.get("require_key", True) if project else True
            hint = "กรุณากดปุ่ม **Redeem Key** เพื่อกรอกคีย์ของคุณ" if r_key else "กรุณากดปุ่ม **Claim Role** เพื่อรับยศฟรี"
            embed = discord.Embed(
                title=f"{EMOJI_PAYOMBOYZ} {pname} | ตรวจสอบสถานะบทบาท",
                description=f"❌ **คุณยังไม่มีบทบาท {role.mention}**\n\n"
                            f"💡 {hint} หรือติดต่อแอดมิน",
                color=discord.Color.red(),
            )
            await self._send_reply(interaction, embed=embed)

    async def _script_callback(self, interaction: discord.Interaction):

        try:

            if not interaction.response.is_done():

                await interaction.response.defer(ephemeral=True)

        except Exception:

            pass

        project = get_project(self.project_id)

        script = project.get("default_script", self.script_text) if project else self.script_text

        # ตรวจสอบว่าผู้ใช้มีบทบาทก่อนหรือไม่ (เพื่อความปลอดภัย)

        target_role_id = project.get("role_id") if project else DEFAULT_VVIP_ROLE_ID

        guild = interaction.guild

        if guild:

            member = interaction.user

            if not isinstance(member, discord.Member):

                try:

                    member = await guild.fetch_member(interaction.user.id)

                except discord.HTTPException:

                    await self._send_reply(interaction, content="❌ ดึงข้อมูลสมาชิกไม่สำเร็จ ลองใหม่อีกครั้ง")

                    return

            role = guild.get_role(target_role_id) if target_role_id else None

            authorized_users = project.get("authorized_users", {}) if project else {}

            authorized_by_key = authorized_users.get(f"{guild.id}:{member.id}", False)

            if project and project.get("require_key") and not role and not authorized_by_key:

                await self._send_reply(interaction, content="🔒 ต้อง Redeem Key ก่อน จึงจะรับสคริปต์ได้")

                return

            if role and role not in member.roles:

                r_key = project.get("require_key", True) if project else True

                action_text = "Redeem Key เพื่อยืนยันคีย์" if r_key else "Claim Role เพื่อรับยศ"

                embed = discord.Embed(

                    title="🔒 สิทธิ์การเข้าถึงสคริปต์",

                    description=f"❌ คุณต้องมีบทบาท {role.mention} ก่อน จึงจะสามารถรับสคริปต์ได้!\n\n"

                                f"💡 กรุณากดปุ่ม **{action_text}** ที่หน้าต่างควบคุมก่อน",

                    color=discord.Color.red(),

                )

                await self._send_reply(interaction, embed=embed)

                return

        embed = discord.Embed(

            title="PAYOMBØYZ HUB | 📜 สคริปต์สำหรับรัน",

            description="คัดลอกโค้ดด้านล่างนี้ไปวางใน Executor ของคุณได้ทันที:",

            color=discord.Color.blue(),

        )

        embed.add_field(

            name="Lua Loader Script",

            value=f"```lua\n{script}\n```",

            inline=False,

        )

        embed.set_footer(text="PAYOMBØYZ HUB • ปลอดภัย อัปเดตล่าสุด ห้ามส่งต่อบุคคลภายนอก")

        await self._send_reply(interaction, embed=embed)

class NoKeyPanelView(discord.ui.View):

    """

    แผงควบคุมระบบ Get-Script-No-Key:

    - ไม่ต้องใช้คีย์ ไม่ต้องมีปุ่ม Redeem Key

    - มี buttons ให้เลือกแมพ (Map Selector) เพื่อรับสคริปต์เฉพาะแมพนั้นๆ

    - ปุ่ม Get Script ทั่วไป (สคริปต์หลัก)

    - ปุ่ม Check Maps (ตรวจสอบรายชื่อแมพที่รองรับ)

    - ปุ่ม Link (เช่น ปุ่ม /ad สำหรับลิงก์สั่งซื้อ) และปุ่ม Action เสริม

    """

    def __init__(self, project_id: str, custom_buttons: Optional[list[dict]] = None):

        super().__init__(timeout=None)

        self.project_id = project_id

        project = get_project(project_id)

        maps = project.get("maps", []) if project else []

        map_mode = project.get("map_mode", "multi") if project else "multi"

        # Each configured game map gets its own button. Universal scripts do not

        # represent a specific game and therefore have no map buttons.

        if map_mode != "universal":

            map_button_limit = 15

            for index, map_data in enumerate(maps[:map_button_limit]):

                map_name = str(map_data.get("name", f"Map {index + 1}"))

                button = discord.ui.Button(

                    label=f"Get {map_name}"[:80],

                    style=discord.ButtonStyle.secondary,

                    emoji=parse_emoji(map_data.get("emoji")) or "🗺️",

                    custom_id=f"payom_nokey_map_{project_id}_{index}",

                    row=min(1 + index // 5, 4),

                )

                button.callback = self._make_map_callback(index)

                self.add_item(button)

        custom_buttons = (project.get("custom_buttons", []) if project else []) if custom_buttons is None else custom_buttons

        panel_buttons = project.get("panel_buttons", {}) if project else {}

        if panel_buttons.get("show_main_script", True):

            btn_script = discord.ui.Button(

                label="Get Script (สคริปต์หลัก)",

                style=discord.ButtonStyle.primary,

                emoji="📜",

                custom_id=f"payom_nokey_main_{project_id}",

                row=0,

            )

            btn_script.callback = self._main_script_callback

            self.add_item(btn_script)

        if map_mode != "universal" and panel_buttons.get("show_check_maps", True):

            btn_check_map = discord.ui.Button(

                label="Check Maps (ตรวจสอบแมพ)",

                style=discord.ButtonStyle.secondary,

                emoji="🗺️",

                custom_id=f"payom_nokey_checkmap_{project_id}",

                row=0,

            )

            btn_check_map.callback = self._check_maps_callback

            self.add_item(btn_check_map)

        # Custom buttons are persisted on the project and can be managed by slash commands.

        self._attach_custom_buttons(project, custom_buttons[:5])

    def _attach_custom_buttons(self, project: Optional[dict], custom_buttons: Optional[list[dict]] = None):

        if not project:

            return

        custom_buttons = project.get("custom_buttons", []) if custom_buttons is None else custom_buttons

        for i, btn in enumerate(custom_buttons):

            label = btn.get("label", "Button")

            emoji = parse_emoji(btn.get("emoji"))

            action = btn.get("action", "link")

            style = parse_button_style(btn.get("style", "link" if action == "link" else "primary"))

            url = btn.get("url")

            if action == "link" and url:

                self.add_item(

                    discord.ui.Button(

                        label=label,

                        style=discord.ButtonStyle.link,

                        url=url,

                        emoji=emoji,

                        row=4,

                    )

                )

            else:

                custom_id = f"payom_nokey_btn_{self.project_id}_{i}"

                b = discord.ui.Button(

                    label=label,

                    style=style,

                    emoji=emoji,

                    custom_id=custom_id,

                    row=4,

                )

                b.callback = self._make_custom_callback(btn)

                self.add_item(b)

    def _make_custom_callback(self, btn_info: dict):

        async def callback(interaction: discord.Interaction):

            text = btn_info.get("payload", "ขอขอบคุณที่ใช้บริการ!")

            embed = discord.Embed(title=btn_info.get("label", "ข้อมูล"), description=text, color=discord.Color.blue())

            await interaction.response.send_message(embed=embed, ephemeral=True)

        return callback

    def _make_map_callback(self, index: int):

        async def callback(interaction: discord.Interaction):

            project = get_project(self.project_id)

            maps = project.get("maps", []) if project else []

            if index >= len(maps):

                await interaction.response.send_message("❌ ไม่พบข้อมูลแมพนี้แล้ว โปรดติดตั้งแผงใหม่", ephemeral=True)

                return

            map_data = maps[index]

            script = map_data.get("script", DEFAULT_SCRIPT)

            map_name = map_data.get("name", "สคริปต์")

            embed = discord.Embed(

                title=f"📜 สคริปต์สำหรับแมพ: {map_name}",

                description="ดาวน์โหลดไฟล์สคริปต์แนบด้านล่าง:",

                color=discord.Color.teal(),

            )

            filename = re.sub(r"[^a-zA-Z0-9_-]+", "_", map_name).strip("_") or "map_script"

            file = discord.File(io.BytesIO(script.encode("utf-8")), filename=f"{filename}.lua")

            await interaction.response.send_message(embed=embed, file=file, ephemeral=True)

        return callback

    async def _main_script_callback(self, interaction: discord.Interaction):

        project = get_project(self.project_id)

        script = project.get("default_script", DEFAULT_SCRIPT) if project else DEFAULT_SCRIPT

        embed = discord.Embed(

            title="PAYOMBØYZ HUB | 📜 สคริปต์หลัก (No Key)",

            description="คัดลอกโค้ดด้านล่างนี้ไปวางใน Executor ของคุณได้ทันที:",

            color=discord.Color.green(),

        )

        embed.add_field(

            name="Lua Loader Script",

            value=f"```lua\n{script}\n```",

            inline=False,

        )

        embed.set_footer(text="PAYOMBØYZ HUB No-Key System • ฟรี อัปเดตตลอดเวลา")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _check_maps_callback(self, interaction: discord.Interaction):

        project = get_project(self.project_id)

        if not project:

            await interaction.response.send_message("❌ ไม่พบข้อมูลโปรเจกต์นี้ในระบบ", ephemeral=True)

            return

        maps = project.get("maps", [])

        pname = project.get("name", self.project_id)

        embed = discord.Embed(

            title=f"🗺️ รายการแมพที่รองรับ: {pname}",

            color=discord.Color.teal(),

        )

        if not maps:

            embed.description = "⚠️ ขณะนี้ยังไม่มีการเพิ่มแมพใดๆ ในโปรเจกต์นี้\nโปรดติดต่อแอดมินเพื่อเพิ่มแมพผ่านคำสั่ง `/map add`"

        else:

            embed.description = (

                f"โปรเจกต์ **{pname}** รองรับเกมและแมพทั้งหมด **{len(maps)}** แมพ:\n"

                f"👇 *เลือกแมพจากเมนู buttons ด้านบน เพื่อคัดลอกสคริปต์ไปวางใน Executor ได้ทันที*\n"

            )

            for i, m in enumerate(maps, 1):

                e = m.get("emoji", "🗺️")

                m_name = m.get("name", "Unknown Map")

                m_desc = m.get("description", "พร้อมใช้งาน (Active)")

                embed.add_field(

                    name=f"{i}. {e} {m_name}",

                    value=f"• สถานะ: `🟢 พร้อมใช้งาน`\n• รายละเอียด: {m_desc}",

                    inline=False,

                )

        embed.set_footer(text=f"PAYOMBØYZ HUB No-Key System • ตรวจสอบล่าสุดเมื่อเวลา {time.strftime('%H:%M')}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

class PersistentFallbackRoleView(discord.ui.View):

    """View เสริมสำหรับลงทะเบียน Custom ID ทั้งหมดเพื่อป้องกัน Interaction Failed บนข้อความเดิม"""

    def __init__(self, project_id: str):

        super().__init__(timeout=None)

        self.project_id = project_id

        # Register all button IDs for fallback

        b_redeem = discord.ui.Button(custom_id=f"payom_redeem_{project_id}")

        b_redeem.callback = self._redeem_cb

        self.add_item(b_redeem)

        b_claim = discord.ui.Button(custom_id=f"payom_claimrole_{project_id}")

        b_claim.callback = self._claim_cb

        self.add_item(b_claim)

        b_check = discord.ui.Button(custom_id=f"payom_checkrole_{project_id}")

        b_check.callback = self._check_cb

        self.add_item(b_check)

        b_script = discord.ui.Button(custom_id=f"payom_script_{project_id}")

        b_script.callback = self._script_cb

        self.add_item(b_script)

    async def _redeem_cb(self, interaction: discord.Interaction):

        await interaction.response.send_modal(RedeemKeyModal(self.project_id))

    async def _claim_cb(self, interaction: discord.Interaction):

        temp_view = GetRolePanelView(self.project_id)

        await temp_view._claim_role_callback(interaction)

    async def _check_cb(self, interaction: discord.Interaction):

        temp_view = GetRolePanelView(self.project_id)

        await temp_view._check_role_callback(interaction)

    async def _script_cb(self, interaction: discord.Interaction):

        temp_view = GetRolePanelView(self.project_id)

        await temp_view._script_callback(interaction)

# =========================================================================

# 🔄 REGISTER ALL VIEWS INTO BOT

# =========================================================================

def register_all_panel_views(bot: discord.Client):

    """ลงทะเบียน Persistent Views ทั้งหมดเพื่อให้ปุ่มและ buttons ทำงานได้ตลอดเวลาหลังรีสตาร์ท"""

    projects = load_projects()

    registered_count = 0

    for pid, pdata in projects.items():

        ptype = pdata.get("type", "get_role")

        if ptype == "get_script_no_key":

            bot.add_view(NoKeyPanelView(pid))

            registered_count += 1

        else:

            bot.add_view(GetRolePanelView(pid, pdata.get("default_script", DEFAULT_SCRIPT)))

            # ลงทะเบียน fallback เพื่อรองรับทั้งโหมดมีคีย์และไม่มีคีย์

            bot.add_view(PersistentFallbackRoleView(pid))

            registered_count += 2

    # ลงทะเบียน legacy panels เพื่อรองรับข้อความเดิมในห้องแชท

    legacy_panels = load_panel_configs()

    for role_id_str, cfg in legacy_panels.items():

        try:

            r_id = int(role_id_str)

            bot.add_view(GetRolePanelView(str(r_id), cfg.get("script_text", DEFAULT_SCRIPT)))

            registered_count += 1

        except Exception:

            pass

    # ลงทะเบียน ScriptCenter Shop Panel Persistent View
    try:
        bot.add_view(ScriptCenterPanelView())
        registered_count += 1
    except Exception as e:
        print(f"[-] Failed to register ScriptCenterPanelView: {e}", flush=True)

    # ลงทะเบียน FindTokenPanelView (Auto Quest Token Extractor)
    try:
        from bot.token_finder_panel import FindTokenPanelView
        bot.add_view(FindTokenPanelView())
        registered_count += 1
    except Exception as e:
        print(f"[-] Failed to register FindTokenPanelView: {e}", flush=True)

    # ลงทะเบียน TicketPanelView และ TicketControlView (Support Ticket Engine)
    try:
        from bot.ticket_system import TicketPanelView, TicketControlView
        bot.add_view(TicketPanelView())
        bot.add_view(TicketControlView())
        registered_count += 2
    except Exception as e:
        print(f"[-] Failed to register Ticket views: {e}", flush=True)

    print(f"  [+] Registered {registered_count} persistent panel views into Bot.", flush=True)
