"""
PAYOMBØYZ Support Ticket System — Industrial Grade.
Replaces Mahiru Ticket Bot with superior aesthetics, retroactive live config updates,
clean readable channel naming, and HTML transcript archival.
"""
import io
import os
import re
import time
import json
import asyncio
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import discord
from discord import app_commands

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "data" / "ticket_configs.json"
ACTIVE_TICKETS_FILE = BASE_DIR / "data" / "active_tickets.json"

DEFAULT_STAFF_ROLE_ID = 1549535328753164418  # @PaYomz
DEFAULT_CATEGORY_ID = 1549803476094029834    # First Gate / Welcome category
COLOR_PRIMARY_GOLD = 0xF1C40F
COLOR_EMBED_DARK = 0x1E1F22


# ─────────────────────────────────────────────────────────────
# 1. 📂 Persistent Configuration & Ticket State Manager
# ─────────────────────────────────────────────────────────────
class TicketConfigManager:
    def __init__(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.configs: Dict[str, Any] = self._load(CONFIG_FILE)
        self.active_tickets: Dict[str, Any] = self._load(ACTIVE_TICKETS_FILE)

    def _load(self, path: Path) -> dict:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_configs(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.configs, f, indent=2, ensure_ascii=False)

    def _save_active(self):
        with open(ACTIVE_TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.active_tickets, f, indent=2, ensure_ascii=False)

    def get_guild_cfg(self, guild_id: int) -> dict:
        return self.configs.setdefault(str(guild_id), {
            "staff_role_id": DEFAULT_STAFF_ROLE_ID,
            "category_id": DEFAULT_CATEGORY_ID,
            "log_channel_id": None,
            "panel_channel_id": None,
            "panel_message_id": None,
            "title": "👑 PAYOMBØYZ SUPPORT TICKETS",
            "description": None,
            "banner_url": None,
            "color": "#F1C40F",
            "counter": 0
        })

    def update_guild_cfg(self, guild_id: int, **kwargs):
        cfg = self.get_guild_cfg(guild_id)
        cfg.update(kwargs)
        self._save_configs()

    def get_next_counter(self, guild_id: int) -> int:
        cfg = self.get_guild_cfg(guild_id)
        cfg["counter"] = cfg.get("counter", 0) + 1
        self._save_configs()
        return cfg["counter"]

    def register_ticket(self, channel_id: int, ticket_data: dict):
        self.active_tickets[str(channel_id)] = ticket_data
        self._save_active()

    def get_ticket(self, channel_id: int) -> Optional[dict]:
        return self.active_tickets.get(str(channel_id))

    def close_ticket(self, channel_id: int):
        self.active_tickets.pop(str(channel_id), None)
        self._save_active()

    def find_user_open_ticket(self, guild: discord.Guild, user_id: int) -> Optional[discord.TextChannel]:
        """Check if user already has an open ticket in the guild."""
        for cid, data in self.active_tickets.items():
            if data.get("owner_id") == user_id and data.get("status") == "open":
                ch = guild.get_channel(int(cid))
                if ch:
                    return ch
        return None


ticket_manager = TicketConfigManager()


# ─────────────────────────────────────────────────────────────
# 2. 🎨 Premium Panel Embed Builder
# ─────────────────────────────────────────────────────────────
def build_ticket_panel_embed(guild_id: int) -> discord.Embed:
    cfg = ticket_manager.get_guild_cfg(guild_id)
    
    title = cfg.get("title") or "👑 PAYOMBØYZ SUPPORT TICKETS"
    
    custom_desc = cfg.get("description")
    if custom_desc:
        description = custom_desc
    else:
        description = (
            "**ยินดีต้อนรับสู่ศูนย์บริการลูกค้าและซัพพอร์ต PAYOMBØYZ HUB**\n"
            "กรุณาเลือกประเภทหัวข้อด้านล่าง หรือกดปุ่มด่วน เพื่อเปิดตั๋วสนทนาส่วนตัวกับทีมงาน\n\n"
            "📌 **หมวดหมู่บริการ (Select Service):**\n"
            "• 💬 **ปรึกษาทั่วไป (General Support)** — สอบถามข้อมูล แนะนำการใช้งาน\n"
            "• 🛠️ **ปัญหาสคริปต์ (Technical Support)** — แจ้งบั๊ก แก้ไขปัญหา รันสคริปต์ไม่ติด\n"
            "• 💰 **การชำระเงิน & ซื้อบริการ (Billing & Orders)** — ซื้อ SuperIP, จ้างทำสคริปต์, ตรวจสอบสลิป\n\n"
            "⚡ **ความเร็วในการให้บริการ:** ตอบกลับรวดเร็ว 5–15 นาที\n"
            "🔒 **ความปลอดภัย:** ห้องตั๋วเป็นแบบส่วนตัว (มีเพียงคุณและทีมงานเท่านั้นที่เข้าถึงได้)"
        )

    color_val = COLOR_PRIMARY_GOLD
    if cfg.get("color"):
        try:
            color_val = int(cfg["color"].lstrip("#"), 16)
        except Exception:
            pass

    embed = discord.Embed(
        title=title,
        description=description,
        color=color_val
    )

    if cfg.get("banner_url"):
        embed.set_image(url=cfg["banner_url"])

    embed.set_footer(text="PAYOMBØYZ SUPPORT • พร้อมดูแลตลอด 24 ชั่วโมง")
    return embed


# ─────────────────────────────────────────────────────────────
# 3. 🎫 In-Ticket Action Controls View (Inside Ticket Channel)
# ─────────────────────────────────────────────────────────────
class TicketCloseConfirmModal(discord.ui.Modal, title="ปิดตั๋วสนับสนุน (Close Ticket)"):
    reason_input = discord.ui.TextInput(
        label="เหตุผลในการปิดตั๋ว (ไม่บังคับ)",
        placeholder="เช่น แก้ไขปัญหาเสร็จสิ้น, ลูกค้าได้รับบริการแล้ว...",
        style=discord.TextStyle.short,
        required=False,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason_input.value.strip() or "ปิดโดยผู้ใช้/แอดมิน"
        await execute_close_ticket(interaction, reason=reason)


class TicketControlView(discord.ui.View):
    """Persistent controls displayed inside every ticket channel."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ปิดตั๋ว",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket:control:close"
    )
    async def btn_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketCloseConfirmModal())

    @discord.ui.button(
        label="บันทึกประวัติ (Transcript)",
        style=discord.ButtonStyle.secondary,
        emoji="📑",
        custom_id="ticket:control:transcript"
    )
    async def btn_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        file_obj, line_count = await generate_ticket_transcript(interaction.channel)
        await interaction.followup.send(
            f"📑 **สร้าง Transcript สำเร็จ!** (ทั้งหมด {line_count:,} ข้อความ)",
            file=file_obj,
            ephemeral=True
        )

    @discord.ui.button(
        label="สะกิดทีมงาน",
        style=discord.ButtonStyle.primary,
        emoji="🔔",
        custom_id="ticket:control:ping"
    )
    async def btn_ping(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = ticket_manager.get_guild_cfg(interaction.guild_id)
        staff_role_id = cfg.get("staff_role_id") or DEFAULT_STAFF_ROLE_ID
        role = interaction.guild.get_role(staff_role_id)
        mention_str = role.mention if role else "@Staff"
        await interaction.response.send_message(
            f"🔔 {mention_str} — มีการเรียกจาก {interaction.user.mention} ในตั๋วนี้!",
            ephemeral=False
        )


# ─────────────────────────────────────────────────────────────
# 4. 🗂️ Dropdown & Buttons for Main Ticket Panel
# ─────────────────────────────────────────────────────────────
CATEGORY_MAP = {
    "general": {
        "label": "ปรึกษาทั่วไป",
        "desc": "สอบถามข้อมูลทั่วไป แนะนำระบบ หรือเรื่องอื่นๆ",
        "emoji": "💬",
        "prefix": "💬・ทั่วไป"
    },
    "script": {
        "label": "ปัญหาสคริปต์",
        "desc": "แจ้งปัญหาสคริปต์ รันไม่ติด โดนเตะ หรือพบบั๊ก",
        "emoji": "🛠️",
        "prefix": "🛠️・สคริปต์"
    },
    "billing": {
        "label": "การชำระเงิน",
        "desc": "สั่งซื้อ SuperIP, จ้างทำสคริปต์, ส่งสลิป",
        "emoji": "💰",
        "prefix": "💰・ชำระเงิน"
    }
}


class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="💬 ปรึกษาทั่วไป (General Support)",
                value="general",
                description="สอบถามข้อมูลทั่วไป แนะนำระบบ หรือเรื่องอื่นๆ",
                emoji="💬"
            ),
            discord.SelectOption(
                label="🛠️ ปัญหาสคริปต์ (Technical Support)",
                value="script",
                description="แจ้งปัญหาสคริปต์ รันไม่ติด โดนเตะ หรือพบบั๊ก",
                emoji="🛠️"
            ),
            discord.SelectOption(
                label="💰 การชำระเงิน & สั่งซื้อ (Purchase & Billing)",
                value="billing",
                description="สั่งซื้อ SuperIP, จ้างทำสคริปต์, ส่งสลิป",
                emoji="💰"
            ),
        ]
        super().__init__(
            placeholder="เลือกหัวข้อที่ต้องการติดต่อ (Select Issue Type)...",
            min_values=1,
            max_values=1,
            custom_id="ticket:select:category",
            options=options,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        cat_key = self.values[0]
        await handle_ticket_create_request(interaction, cat_key)


class TicketPanelView(discord.ui.View):
    """Persistent View for the main ticket panel — survives restarts."""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())

    @discord.ui.button(
        label="ปรึกษาทั่วไป",
        style=discord.ButtonStyle.primary,
        emoji="💬",
        custom_id="ticket:btn:general",
        row=1
    )
    async def btn_general(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_ticket_create_request(interaction, "general")

    @discord.ui.button(
        label="ปัญหาสคริปต์",
        style=discord.ButtonStyle.success,
        emoji="🛠️",
        custom_id="ticket:btn:script",
        row=1
    )
    async def btn_script(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_ticket_create_request(interaction, "script")

    @discord.ui.button(
        label="การชำระเงิน",
        style=discord.ButtonStyle.secondary,
        emoji="💰",
        custom_id="ticket:btn:billing",
        row=1
    )
    async def btn_billing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_ticket_create_request(interaction, "billing")


# ─────────────────────────────────────────────────────────────
# 5. ⚙️ Ticket Creation Engine
# ─────────────────────────────────────────────────────────────
async def handle_ticket_create_request(interaction: discord.Interaction, cat_key: str):
    guild = interaction.guild
    user = interaction.user

    if not guild or not isinstance(user, discord.Member):
        await interaction.response.send_message("❌ คำสั่งนี้สามารถใช้งานได้เฉพาะในเซิร์ฟเวอร์", ephemeral=True)
        return

    # Check for existing open ticket
    existing_ticket = ticket_manager.find_user_open_ticket(guild, user.id)
    if existing_ticket:
        await interaction.response.send_message(
            f"⚠️ **คุณมีตั๋วที่เปิดค้างไว้อยู่แล้ว!**\nกรุณาใช้ตั๋วเดิมของคุณที่ช่อง {existing_ticket.mention}",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    cfg = ticket_manager.get_guild_cfg(guild.id)
    ticket_num = ticket_manager.get_next_counter(guild.id)
    cat_info = CATEGORY_MAP.get(cat_key, CATEGORY_MAP["general"])

    # Clean, human-readable channel name
    clean_user = re.sub(r'[^a-zA-Z0-9_\-\u0E00-\u0E7F]', '', user.name)[:12] or f"{ticket_num:04d}"
    channel_name = f"{cat_info['prefix']}-{clean_user}"

    # Category resolution
    target_category = None
    if cfg.get("category_id"):
        target_category = guild.get_channel(cfg["category_id"])
    if not isinstance(target_category, discord.CategoryChannel):
        target_category = interaction.channel.category

    # Staff role resolution
    staff_role = guild.get_role(cfg.get("staff_role_id", DEFAULT_STAFF_ROLE_ID))

    # Channel Overwrites
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True,
            attach_files=True,
            embed_links=True
        )
    }

    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )

    try:
        new_channel = await guild.create_text_channel(
            name=channel_name,
            category=target_category,
            overwrites=overwrites,
            topic=f"Ticket #{ticket_num:04d} | Owner: {user.name} ({user.id}) | Category: {cat_info['label']}",
            reason=f"PAYOMBØYZ Support Ticket #{ticket_num:04d} for {user.name}"
        )

        ticket_manager.register_ticket(new_channel.id, {
            "ticket_id": ticket_num,
            "owner_id": user.id,
            "owner_name": str(user),
            "category": cat_key,
            "created_at": time.time(),
            "status": "open"
        })

        # Welcome message inside the ticket
        staff_mention = staff_role.mention if staff_role else "@Staff"
        welcome_embed = discord.Embed(
            title=f"🎫 ตั๋วสนับสนุน #{ticket_num:04d} • {cat_info['label']}",
            description=(
                f"สวัสดีครับ {user.mention} 👋\n\n"
                f"ยินดีต้อนรับสู่ห้องสนับสนุนของ **PAYOMBØYZ HUB**\n"
                f"กรุณาพิมพ์รายละเอียดปัญหาหรือความต้องการของคุณไว้ได้เลยครับ\n"
                f"หากมีภาพหน้าจอ (Screenshot) หรือคลิปวิดีโอ สามารถแนบส่งมาได้เลย ทีมงานจะรีบเข้ามาตอบกลับครับ!\n\n"
                f"📌 **หมวดหมู่:** `{cat_info['label']}`\n"
                f"⏰ **เวลาที่เปิด:** <t:{int(time.time())}:F>\n"
                f"👤 **ผู้ดูแล:** {staff_mention}"
            ),
            color=COLOR_PRIMARY_GOLD
        )
        welcome_embed.set_footer(text="ใช้ปุ่มด้านล่างเพื่อจัดการตั๋ว หรือพิมพ์ข้อความพูดคุยได้ทันที")

        await new_channel.send(
            content=f"{user.mention} {staff_mention}",
            embed=welcome_embed,
            view=TicketControlView()
        )

        await interaction.followup.send(
            f"✅ **เปิดตั๋วสำเร็จแล้ว!** กรุณาคลิกไปที่ห้อง {new_channel.mention}",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ **บอทไม่มีสิทธิ์สร้างห้อง (Manage Channels)!** กรุณาตรวจสอบ Permission ของบอทในเซิร์ฟเวอร์",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"❌ เกิดข้อผิดพลาดในการสร้างตั๋ว: `{e}`",
            ephemeral=True
        )


# ─────────────────────────────────────────────────────────────
# 6. 📑 HTML Transcript Generator
# ─────────────────────────────────────────────────────────────
async def generate_ticket_transcript(channel: discord.TextChannel) -> Tuple[discord.File, int]:
    messages = []
    async for msg in channel.history(limit=500, oldest_first=True):
        messages.append(msg)

    html_content = [
        "<!DOCTYPE html>",
        "<html lang='th'>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>PAYOMBØYZ Ticket Transcript - {channel.name}</title>",
        "<style>",
        "body { background: #1e1f22; color: #dbdee1; font-family: 'Segoe UI', Tahoma, sans-serif; padding: 25px; margin: 0; }",
        ".header { border-bottom: 2px solid #35363c; padding-bottom: 15px; margin-bottom: 20px; }",
        ".header h1 { color: #f1c40f; margin: 0 0 5px 0; font-size: 24px; }",
        ".meta { color: #949ba4; font-size: 14px; }",
        ".msg { display: flex; margin-bottom: 16px; padding: 6px 12px; border-radius: 6px; }",
        ".msg:hover { background: #2b2d31; }",
        ".avatar { width: 42px; height: 42px; border-radius: 50%; margin-right: 15px; }",
        ".msg-body { flex: 1; }",
        ".author { font-weight: bold; color: #f2f3f5; margin-right: 8px; }",
        ".bot-tag { background: #5865f2; color: #fff; font-size: 10px; padding: 1px 4px; border-radius: 3px; font-weight: bold; }",
        ".time { font-size: 12px; color: #949ba4; }",
        ".content { margin-top: 4px; word-break: break-word; line-height: 1.4; }",
        ".embed { border-left: 4px solid #f1c40f; background: #2b2d31; padding: 10px 14px; margin-top: 8px; border-radius: 4px; }",
        "</style>",
        "</head>",
        "<body>",
        "<div class='header'>",
        f"<h1>👑 PAYOMBØYZ Support Transcript</h1>",
        f"<div class='meta'>ห้อง: <b>#{channel.name}</b> | วันที่บันทึก: {time.strftime('%Y-%m-%d %H:%M:%S')} | รวม {len(messages)} ข้อความ</div>",
        "</div>"
    ]

    for m in messages:
        avatar = m.author.display_avatar.url if m.author.display_avatar else ""
        time_str = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
        bot_badge = "<span class='bot-tag'>BOT</span>" if m.author.bot else ""
        
        escaped_content = m.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        
        embed_html = ""
        for emb in m.embeds:
            etitle = emb.title or ""
            edesc = (emb.description or "").replace("\n", "<br>")
            embed_html += f"<div class='embed'><b>{etitle}</b><br>{edesc}</div>"

        html_content.append(
            f"<div class='msg'>"
            f"<img class='avatar' src='{avatar}'>"
            f"<div class='msg-body'>"
            f"<div><span class='author'>{m.author.name}</span>{bot_badge} <span class='time'>{time_str}</span></div>"
            f"<div class='content'>{escaped_content}</div>"
            f"{embed_html}"
            f"</div></div>"
        )

    html_content.append("</body></html>")
    raw_html = "\n".join(html_content)

    file_bytes = io.BytesIO(raw_html.encode("utf-8"))
    safe_channel = re.sub(r'[^a-zA-Z0-9_\-]', '_', channel.name)
    discord_file = discord.File(file_bytes, filename=f"Transcript_{safe_channel}.html")
    return discord_file, len(messages)


# ─────────────────────────────────────────────────────────────
# 7. 🔒 Execute Close Ticket Routine
# ─────────────────────────────────────────────────────────────
async def execute_close_ticket(interaction: discord.Interaction, reason: str = "ปิดโดยผู้ใช้"):
    channel = interaction.channel
    guild = interaction.guild

    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("❌ คำสั่งนี้ใช้ได้เฉพาะในห้องตั๋ว", ephemeral=True)
        return

    tdata = ticket_manager.get_ticket(channel.id)

    await interaction.response.send_message(
        f"🔒 **กำลังปิดตั๋ว...**\n• **เหตุผล:** `{reason}`\n• บันทึก Transcript และห้องจะถูกลบใน **5 วินาที**",
        ephemeral=False
    )

    # 1. Generate Transcript
    transcript_file, msg_count = await generate_ticket_transcript(channel)

    # 2. Send Transcript to Log Channel if configured
    cfg = ticket_manager.get_guild_cfg(guild.id)
    log_ch_id = cfg.get("log_channel_id")
    if log_ch_id:
        log_ch = guild.get_channel(log_ch_id)
        if isinstance(log_ch, discord.TextChannel):
            log_embed = discord.Embed(
                title=f"📑 บันทึกการปิดตั๋ว #{channel.name}",
                description=(
                    f"👤 **ผู้เปิดตั๋ว:** <@{tdata.get('owner_id')}>\n"
                    f"🔒 **ผู้สั่งปิด:** {interaction.user.mention}\n"
                    f"📝 **เหตุผล:** `{reason}`\n"
                    f"💬 **จำนวนข้อความ:** `{msg_count:,}` ข้อความ"
                ),
                color=0xE74C3C
            )
            try:
                transcript_file.fp.seek(0)
                await log_ch.send(embed=log_embed, file=transcript_file)
            except Exception as e:
                print(f"[-] Failed to send transcript to log channel: {e}")

    # 3. DM Transcript to Ticket Owner
    if tdata and tdata.get("owner_id"):
        try:
            owner = guild.get_member(tdata["owner_id"]) or await guild.fetch_member(tdata["owner_id"])
            if owner:
                dm_embed = discord.Embed(
                    title=f"📑 สำเนาประวัติการสนทนา • #{channel.name}",
                    description=(
                        f"ตั๋วของคุณใน **{guild.name}** ถูกปิดเรียบร้อยแล้ว\n"
                        f"• **เหตุผล:** `{reason}`\n"
                        f"• สำเนาการสนทนาแนบมาด้านล่างแล้ว ขอบคุณที่ใช้บริการครับ 🙏"
                    ),
                    color=COLOR_PRIMARY_GOLD
                )
                transcript_file.fp.seek(0)
                await owner.send(embed=dm_embed, file=transcript_file)
        except Exception:
            pass

    # 4. Cleanup DB and delete channel
    ticket_manager.close_ticket(channel.id)
    await asyncio.sleep(5)
    try:
        await channel.delete(reason=f"Closed by {interaction.user.name}: {reason}")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 8. 🔄 Live Panel Message Updater (Retroactive Configuration)
# ─────────────────────────────────────────────────────────────
async def update_live_panel_message(bot: discord.Client, guild_id: int) -> Tuple[bool, str]:
    """Updates the existing panel message in Discord with current config values."""
    cfg = ticket_manager.get_guild_cfg(guild_id)
    ch_id = cfg.get("panel_channel_id")
    msg_id = cfg.get("panel_message_id")

    if not ch_id or not msg_id:
        return False, "ยังไม่มีการบันทึก Message ID ของ Panel ในเซิร์ฟเวอร์นี้"

    guild = bot.get_guild(guild_id)
    if not guild:
        return False, "ไม่พบกิลด์"

    channel = guild.get_channel(ch_id)
    if not isinstance(channel, discord.TextChannel):
        return False, "ไม่พบห้องข้อความของ Panel"

    try:
        msg = await channel.fetch_message(msg_id)
        new_embed = build_ticket_panel_embed(guild_id)
        await msg.edit(embed=new_embed, view=TicketPanelView())
        return True, "อัปเดต Panel บน Discord เรียบร้อยแล้ว!"
    except Exception as e:
        return False, f"ไม่สามารถแก้ไขข้อความเดิมได้: {e}"
