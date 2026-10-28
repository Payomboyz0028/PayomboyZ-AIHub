# -*- coding: utf-8 -*-
"""
========================================================================================
🌐 DISCORD INTERACTIVE WEB CLONE PANEL & MODAL SYSTEM (ภาษาไทย + ครบเครื่องระดับปีศาจ)
- แผงควบคุม Web Clone แบบกดได้ทันทีโดยตรง (Dropdown 7 โหมด + ปุ่มลัด 6 ปุ่ม)
- รองรับการติดตั้งแบบถาวรในห้องด้วยคำสั่ง /setup panel (เลือก panel_type: clone) หรือ /setup clone
- เชื่อมต่อเครื่องมือโคลนระดับเทพ (SPA Hydration, Mock API, Source Maps, OWASP Audit)
========================================================================================
"""

from __future__ import annotations
import os
import sys
import io
import time
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

import discord
from discord import ui

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

CLONE_PANELS_FILE = ROOT_DIR / "data" / "clone_panels.json"
CLONE_PANELS_FILE.parent.mkdir(parents=True, exist_ok=True)

from bot.web_clone_engine import clone_site


def load_clone_panels() -> Dict[str, Any]:
    if not CLONE_PANELS_FILE.exists():
        return {}
    try:
        return json.loads(CLONE_PANELS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_clone_panel(panel_id: str, data: Dict[str, Any]):
    panels = load_clone_panels()
    panels[panel_id] = data
    CLONE_PANELS_FILE.write_text(json.dumps(panels, indent=2, ensure_ascii=False), encoding="utf-8")


def delete_clone_panel(panel_id: str):
    panels = load_clone_panels()
    if panel_id in panels:
        del panels[panel_id]
        CLONE_PANELS_FILE.write_text(json.dumps(panels, indent=2, ensure_ascii=False), encoding="utf-8")


def build_clone_panel_embed(cfg: Optional[Dict[str, Any]] = None) -> discord.Embed:
    """Creates the main Web Clone Tool panel embed."""
    cfg = cfg or {}
    title = cfg.get("title") or "🌐 Web Clone Tool — ศูนย์โจรกรรมและโคลนเว็บไซต์ระดับปีศาจ"
    embed = discord.Embed(
        title=title,
        description=(
            "**แผงควบคุมระบบโคลนเว็บไซต์และสแกนความปลอดภัยทางไซเบอร์**\n"
            "เลือกโหมดจาก Dropdown หรือคลิกปุ่มลัดด้านล่างเพื่อเริ่มดูดเว็บไซต์และรับไฟล์ ZIP ทาง DM ทันที:\n\n"
            "🔍 **1. เจาะลึกโครงสร้าง (Deep)** — HTML/CSS/JS + Assets ท้องถิ่น + สแกน Secret Keys\n"
            "🌐 **2. ทะลวงไฟร์วอลล์ (Bypass)** — ปลอม TLS Chrome 124 ข้าม Cloudflare / WAF + กวาด Subdomain\n"
            "💀 **3. ชำแหละเต็มสูบ (Full)** — ดึงไฟล์หลุด `.git` / `.env` + ตรวจสอบช่องโหว่ OWASP Top 10\n"
            "⚙️ **4. สกัด API เมทริกซ์ (API Full)** — แกะทุก REST/GraphQL Endpoint ภายใน JS Bundles\n"
            "🍪 **5. ทะลวงเซสชัน (Cookie Pass)** — จำลอง Cookie Auth + ถอดรหัสโครงสร้าง JWT อัตโนมัติ\n"
            "👻 **6. เงาล่องหน (Phantom)** — สปายไร้ร่องรอย + กวาด Form / Email / Phone + ปลอม JA3/JA4\n"
            "⚡ **7. ปีศาจกลืนกินโลก (Godmode)** — **โหมดสูงสุด!** Pre-render SPA (Next.js/React/Tailwind) + กู้ Source Code ฉบับแท้ TypeScript/JSX จาก Source Maps + ฝัง Mock API Interceptor + แถม `serve.py` และ `start.bat`"
        ),
        color=discord.Color.from_rgb(0, 168, 255)
    )
    if cfg.get("banner_url"):
        embed.set_image(url=cfg["banner_url"])
    if cfg.get("thumbnail_url"):
        embed.set_thumbnail(url=cfg["thumbnail_url"])
    embed.set_footer(text="PAYOMBØYZ High-Speed Web Recon & Cloner • ติดตั้งถาวร 24/7")
    return embed


class CloneUrlModal(ui.Modal):
    def __init__(self, mode: str, mode_label: str):
        safe_title = f"🌐 โคลนเว็บ — {mode_label}"[:45]
        super().__init__(title=safe_title)
        self.mode = mode
        self.mode_label = mode_label

        self.url_input = ui.TextInput(
            label="ใส่ URL หรือชื่อเว็บเป้าหมาย",
            placeholder="https://example.com หรือ target.com",
            required=True,
            max_length=500
        )
        self.add_item(self.url_input)

        self.cookie_input = ui.TextInput(
            label="Cookies / Headers เพิ่มเติม (เว้นว่างได้)",
            placeholder="session_id=xyz; auth_token=123...",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )
        self.add_item(self.cookie_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_url = self.url_input.value.strip()
            cookies = self.cookie_input.value.strip() or None

            if not target_url.startswith(("http://", "https://")):
                target_url = "https://" + target_url

            await interaction.response.defer(ephemeral=True, thinking=True)

            res = await asyncio.to_thread(clone_site, url=target_url, mode=self.mode, cookies=cookies)

            if not res or not res.get("success"):
                err_msg = res.get("error", "ไม่สามารถเชื่อมต่อเว็บไซต์หรือดาวน์โหลดโครงสร้างได้") if res else "Engine ไม่ส่งผลลัพธ์กลับมา"
                err_embed = discord.Embed(
                    title="❌ การโคลนเว็บไซต์ล้มเหลว",
                    description=f"**เป้าหมาย:** `{target_url}`\n**ข้อผิดพลาด:** `{err_msg}`\n\nโปรดตรวจสอบว่า URL ถูกต้อง หรือเว็บไซต์มี Cloudflare WAF บล็อกเข้มงวด",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=err_embed, ephemeral=True)
                return

            zip_path_str = res.get("zip_path", "")
            zip_path = Path(zip_path_str) if zip_path_str else None
            zip_size_kb = res.get("zip_size_bytes", 0) / 1024
            downloaded = res.get("downloaded_files", 0)
            apis_count = len(res.get("apis_found", []))
            secrets_count = len(res.get("secrets_found", []))
            sources_count = res.get("harvested_source_files", 0)
            elapsed = res.get("elapsed", 0.0)
            is_hydrated = res.get("is_spa_hydrated", False)
            stack_info = res.get("tech_stack", {})
            backend_fw = stack_info.get("backend_framework", "Native Enterprise Backend")
            frontend_fw = stack_info.get("frontend_framework", "HTML5 / SPA")
            confidence = int(stack_info.get("confidence", 0.95) * 100)
            contracts_count = res.get("api_contracts_count", apis_count)

            result_embed = discord.Embed(
                title=f"⚡ PAYOMBØYZ | โคลนเว็บไซต์สำเร็จ: {res.get('domain')}",
                description=(
                    f"**เป้าหมาย:** `{target_url}`\n"
                    f"**โหมดปฏิบัติการ:** `{self.mode_label}`\n"
                    f"**⚙️ เทคโนโลยี Backend ที่ตรวจจับได้:** `{backend_fw}` (`ความแม่นยำ {confidence}%`)\n"
                    f"**🎨 เทคโนโลยี Frontend:** `{frontend_fw}`\n"
                    f"**SPA DOM Hydration:** `{'✅ Pre-rendered (Chrome)' if is_hydrated else '⚡ Fast TLS'}`\n"
                    f"**ไฟล์ที่ดูดและทำ Localize:** `{downloaded:,} ไฟล์`\n"
                    f"**Source Code ที่กู้คืนได้ (TypeScript/JSX):** `{sources_count:,} ไฟล์`\n"
                    f"**API Contracts & DTOs ที่สกัดได้:** `{contracts_count:,} รายการ`\n"
                    f"**ความลับ/Secret Keys ที่พบ:** `{secrets_count:,} รายการ`\n"
                    f"**ขนาดไฟล์ ZIP:** `{zip_size_kb:.1f} KB` | **เวลา:** `{elapsed:.2f}s`\n\n"
                    f"📦 **สถาปัตยกรรมระดับเทพที่สร้างและแถมให้ใน ZIP:**\n"
                    f"• `backend-{stack_info.get('backend_tech', 'java')}/` — โปรเจกต์ Backend แท้ตาม Tech Stack ({backend_fw}) พร้อม Controller, DTOs, Service และ Dockerfile\n"
                    f"• `ARCHITECTURE.md` — เอกสารโครงสร้างระบบฉบับเต็ม พร้อม Mermaid Topology Diagram\n"
                    f"• `openapi.yaml` — สเปก API Contract มาตรฐาน OpenAPI 3.0.3 ครบทุก Endpoint\n"
                    f"• `docker-compose.yml` — ไฟล์คอนฟิกรัน Multi-Container (Frontend + Backend) 1 คำสั่งจบ\n"
                    f"• `server.py` & `start.bat` — ดับเบิ้ลคลิกเปิดเซิร์ฟเวอร์รันบน Localhost ได้ทันที!"
                ),
                color=discord.Color.from_rgb(0, 230, 150)
            )
            result_embed.set_footer(text="ไฟล์ .zip แนบมาด้านล่างแล้ว มีทั้งโค้ด Frontend, Native Backend, API และเอกสาร Architecture ครบ 100%")

            files_to_send = []
            if zip_path and zip_path.exists():
                try:
                    with open(zip_path, "rb") as zf:
                        zip_bytes = zf.read()
                    if len(zip_bytes) <= 24 * 1024 * 1024:
                        files_to_send.append(discord.File(io.BytesIO(zip_bytes), filename=zip_path.name))
                    else:
                        result_embed.add_field(
                            name="⚠️ ขนาดไฟล์เกินลิมิต Discord",
                            value=f"ไฟล์มีขนาด `{len(zip_bytes) / (1024*1024):.1f} MB` เกิน 25 MB เก็บไว้บนเซิร์ฟเวอร์ที่: `{zip_path}`",
                            inline=False
                        )
                except Exception as read_err:
                    print(f"[CLONE FILE READ ERROR] {read_err}", flush=True)

            # 1. Always send directly to user in their channel interaction
            await interaction.followup.send(embed=result_embed, files=files_to_send, ephemeral=True)

            # 2. Also attempt to DM a copy to user
            if files_to_send:
                try:
                    with open(zip_path, "rb") as zf:
                        dm_file = discord.File(zf, filename=zip_path.name)
                        await interaction.user.send(embed=result_embed, file=dm_file)
                except Exception:
                    pass

        except Exception as e:
            print(f"[CLONE MODAL ON_SUBMIT ERROR] {e}", flush=True)
            try:
                err_embed = discord.Embed(
                    title="❌ เกิดข้อผิดพลาดในระบบโคลนเว็บไซต์",
                    description=f"เกิดข้อผิดพลาดภายใน: `{str(e)[:400]}`",
                    color=discord.Color.red()
                )
                if interaction.response.is_done():
                    await interaction.followup.send(embed=err_embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=err_embed, ephemeral=True)
            except Exception:
                pass


class CloneModeDropdown(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="⚡ ปีศาจกลืนกินโลก (Godmode)",
                value="Godmode",
                description="กู้คืน Source Maps (TypeScript/JSX) + Pre-render SPA + Mock API",
                emoji="⚡"
            ),
            discord.SelectOption(
                label="🔍 เจาะลึกโครงสร้าง (Deep Recon)",
                value="Deep",
                description="HTML/CSS/JS + Asset Localizer + สแกน Secret Keys",
                emoji="🔍"
            ),
            discord.SelectOption(
                label="🌐 ทะลวงไฟร์วอลล์ (Bypass WAF/CF)",
                value="Bypass",
                description="ปลอมแปลง TLS Chrome 124 ทะลวง Cloudflare + สแกน Subdomain",
                emoji="🌐"
            ),
            discord.SelectOption(
                label="💀 ชำแหละเต็มสูบ (Full Apocalypse)",
                value="Full",
                description="ดึงไฟล์ซ่อน .git/.env + ตรวจสอบช่องโหว่ OWASP Top 10",
                emoji="💀"
            ),
            discord.SelectOption(
                label="⚙️ สกัด API เมทริกซ์ (API Matrix)",
                value="API Full",
                description="สกัดทุก REST/GraphQL Endpoint ภายใน JavaScript Chunks",
                emoji="⚙️"
            ),
            discord.SelectOption(
                label="🍪 ทะลวงเซสชัน (Cookie Pass)",
                value="Cookie Pass",
                description="ฝังเซสชันคุกกี้ + ถอดรหัสโครงสร้าง JSON Web Token (JWT)",
                emoji="🍪"
            ),
            discord.SelectOption(
                label="👻 เงาล่องหน (Phantom Spider)",
                value="Phantom",
                description="สปายไร้ร่องรอย + สกัด Form ล็อกอิน + อีเมลและเบอร์โทร",
                emoji="👻"
            ),
        ]
        super().__init__(
            placeholder="🎯 เลือกโหมดปฏิบัติการโคลนเว็บไซต์ (ทั้ง 7 โหมด)...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="select_clone_mode_dropdown",
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_mode = self.values[0]
            mode_labels = {
                "Godmode": "⚡ ปีศาจกลืนกินโลก (Godmode)",
                "Deep": "🔍 เจาะลึกโครงสร้าง (Deep)",
                "Bypass": "🌐 ทะลวงไฟร์วอลล์ (Bypass)",
                "Full": "💀 ชำแหละเต็มสูบ (Full)",
                "API Full": "⚙️ สกัด API เมทริกซ์ (API Full)",
                "Cookie Pass": "🍪 ทะลวงเซสชัน (Cookie Pass)",
                "Phantom": "👻 เงาล่องหน (Phantom)",
            }
            safe_label = mode_labels.get(selected_mode, selected_mode)
            await interaction.response.send_modal(
                CloneUrlModal(mode=selected_mode, mode_label=safe_label)
            )
        except Exception as e:
            print(f"[CLONE DROPDOWN ERROR] {e}", flush=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ ไม่สามารถเปิดหน้าต่างโคลนเว็บได้: `{e}`", ephemeral=True)
            except Exception:
                pass


class ClonePanelView(ui.View):
    """Persistent 24/7 Web Clone Control Panel View."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloneModeDropdown())

    # Row 1: Direct 1-Click Launch Buttons
    @ui.button(label="⚡ ปีศาจกลืนกินโลก (Godmode)", style=discord.ButtonStyle.success, emoji="⚡", custom_id="btn_clone_godmode_direct", row=1)
    async def btn_godmode(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_modal(CloneUrlModal(mode="Godmode", mode_label="ปีศาจกลืนกินโลก (Godmode)"))
        except Exception as e:
            print(f"[CLONE MODAL ERROR] {e}", flush=True)

    @ui.button(label="🌐 ทะลวง WAF (Bypass)", style=discord.ButtonStyle.primary, emoji="🌐", custom_id="btn_clone_bypass_direct", row=1)
    async def btn_bypass(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_modal(CloneUrlModal(mode="Bypass", mode_label="ทะลวงไฟร์วอลล์ (Bypass)"))
        except Exception as e:
            print(f"[CLONE MODAL ERROR] {e}", flush=True)

    @ui.button(label="💀 ชำแหละเต็มสูบ (Full)", style=discord.ButtonStyle.danger, emoji="💀", custom_id="btn_clone_full_direct", row=1)
    async def btn_full(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_modal(CloneUrlModal(mode="Full", mode_label="ชำแหละเต็มสูบ (Full)"))
        except Exception as e:
            print(f"[CLONE MODAL ERROR] {e}", flush=True)

    # Row 2: Secondary Tool Buttons
    @ui.button(label="⚙️ สกัด API (API Full)", style=discord.ButtonStyle.secondary, emoji="⚙️", custom_id="btn_clone_api_direct", row=2)
    async def btn_api_full(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_modal(CloneUrlModal(mode="API Full", mode_label="สกัด API เมทริกซ์ (API Full)"))
        except Exception as e:
            print(f"[CLONE MODAL ERROR] {e}", flush=True)

    @ui.button(label="🍪 ทะลวงเซสชัน (Cookie)", style=discord.ButtonStyle.secondary, emoji="🍪", custom_id="btn_clone_cookie_direct", row=2)
    async def btn_cookie_pass(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_modal(CloneUrlModal(mode="Cookie Pass", mode_label="ทะลวงเซสชัน (Cookie Pass)"))
        except Exception as e:
            print(f"[CLONE MODAL ERROR] {e}", flush=True)

    @ui.button(label="👻 เงาล่องหน (Phantom)", style=discord.ButtonStyle.secondary, emoji="👻", custom_id="btn_clone_phantom_direct", row=2)
    async def btn_phantom(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_modal(CloneUrlModal(mode="Phantom", mode_label="เงาล่องหน (Phantom)"))
        except Exception as e:
            print(f"[CLONE MODAL ERROR] {e}", flush=True)
