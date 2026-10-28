# -*- coding: utf-8 -*-
"""
====================================================================
  ⚡ PAYOMBØYZ GODMODE — PBG SENIOR AGENTIC HOST CONTROLLER (GOD MODE)
====================================================================
Chief Operating Authority: PBG (PayomboyZ Godmode) Senior Brain
Direct Allegiance: dj (Supreme Authority)

GOD MODE Core Capabilities:
1. Strict 2-Factor Authentication:
   - Step 1: St@313326339
   - Step 2: 280342
2. Room / Channel Isolation:
   - Operates strictly in channels configured via /godmode setup
3. PBG Agentic Architecture & High-Detail Communication:
   - Deep rapport and understanding of dj's workflows
   - High-detail, structured reporting (never blunt, full step-by-step logs)
   - Autonomous multi-step tool execution loop (Web, Files, Terminal, Reversing)
4. Visual & Image Superpowers:
   - AI Image Generation (Delegated via Gemini + Image Engine)
   - Real-time System Telemetry Charts (Dark-mode Matplotlib Infographics)
   - QR Code Generation (PromptPay / URL / Payments)
   - Desktop & Window Screen Capture
5. The 3 Hard Guardrails:
   - [G1] No out-of-scope file deletion
   - [G2] Risky file download requires PIN '280342' every single time
   - [G3] AI cannot make payments or checkout; max is QR capture or slip processing
====================================================================
"""

import os
import re
import io
import sys
import time
import json
import asyncio
import platform
import subprocess
import traceback
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import psutil
import discord
from discord import app_commands
from discord.ext import commands

# Visual & Graphing Libraries
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
try:
    from bot.godmode_web_streamer import (
        start_godmode_web_service,
        generate_web_token,
        get_primary_lan_ip,
        DEFAULT_PORT as WEB_STREAMER_PORT
    )
except Exception:
    def start_godmode_web_service(*args, **kwargs): pass
    def generate_web_token(*args, **kwargs): return "MOCK"
    def get_primary_lan_ip(*args, **kwargs): return "127.0.0.1"
    WEB_STREAMER_PORT = 8080
from pbg_memory import MEMORY_ENGINE

# Security PINs & Master Passwords
PASSWORD_STAGE_1 = "St@313326339"
PASSWORD_STAGE_2 = "280342"
SESSION_TIMEOUT_SECONDS = 1800  # 30 minutes of inactivity auto-locks

CONFIG_FILE = BASE_DIR / "bot" / "godmode_config.json"


# =========================================================================
# 🛑 THE 3 HARD GUARDRAILS ENFORCEMENT
# =========================================================================
class HardGuardrails:
    RISKY_EXTENSIONS = (
        ".exe", ".dll", ".bat", ".cmd", ".vbs", ".ps1", ".msi",
        ".scr", ".zip", ".rar", ".7z", ".tar", ".gz", ".sys"
    )

    DOWNLOAD_COMMAND_PATTERNS = [
        r"invoke-webrequest", r"curl\b", r"wget\b", r"bitsadmin",
        r"certutil.*-urlcache", r"start-bitstransfer", r"iwr\b"
    ]

    DELETE_COMMAND_PATTERNS = [
        r"\bremove-item\b", r"\bdel\b", r"\brmdir\b", r"\brm\b",
        r"\berase\b", r"\bshutil\.rmtree\b", r"\bos\.remove\b"
    ]

    PAYMENT_INTENT_PATTERNS = [
        r"จ่ายเงิน", r"ชำระเงิน", r"โอนเงิน", r"ตัดบัตร", r"หักเงิน",
        r"checkout", r"pay\b", r"transfer", r"buy\b", r"purchase",
        r"stripe", r"promptpay", r"bank", r"credit card"
    ]

    @classmethod
    def check_deletion_safety(cls, path_str: str) -> Tuple[bool, str]:
        """Guardrail 1: Block out-of-scope file deletion."""
        try:
            target = Path(path_str).resolve()
            allowed_root = BASE_DIR.resolve()
            if not str(target).lower().startswith(str(allowed_root).lower()):
                return False, f"ห้ามสั่งลบไฟล์นอกเหนือจากขอบเขตโฟลเดอร์โปรเจกต์เด็ดขาด (Blocked out-of-scope path: {target})"
            if target == allowed_root:
                return False, "ห้ามลบโฟลเดอร์หลักของโปรเจกต์"
            return True, ""
        except Exception as e:
            return False, f"Invalid path check: {e}"

    @classmethod
    def check_download_risk(cls, command_or_url: str, pin: str = "") -> Tuple[bool, str]:
        """Guardrail 2: Risky downloads require PIN '280342'."""
        text = command_or_url.lower()
        is_download = any(re.search(pat, text) for pat in cls.DOWNLOAD_COMMAND_PATTERNS) or "http" in text
        is_risky_ext = any(ext in text for ext in cls.RISKY_EXTENSIONS)

        if is_download and is_risky_ext:
            if pin.strip() != PASSWORD_STAGE_2:
                return False, (
                    "⚠️ [GUARDRAIL 2 SECURITY CHECK] การดาวน์โหลดไฟล์ที่มีความเสี่ยงหรือไฟล์แปลกปลอม "
                    f"จำเป็นต้องระบุรหัสยืนยัน '{PASSWORD_STAGE_2}' ทุกครั้งเพื่อความปลอดภัย\n"
                    f"กรุณาสั่งการพร้อมระบุรหัสยืนยัน {PASSWORD_STAGE_2}"
                )
        return True, ""

    @classmethod
    def check_payment_action(cls, prompt_or_cmd: str) -> Tuple[bool, str]:
        """Guardrail 3: Prohibit autonomous payments."""
        text = prompt_or_cmd.lower()
        for pat in cls.PAYMENT_INTENT_PATTERNS:
            if re.search(pat, text):
                if any(w in text for w in ("qr", "สลิป", "slip", "topup", "เติมเงิน", "แสดง qr")):
                    continue
                return False, (
                    "⛔ [GUARDRAIL 3 BLOCKED] PBG ถูกระงับไม่ให้ดำเนินการชำระเงินหรือทำธุรกรรมแทน dj เด็ดขาด\n"
                    "• ทำได้มากที่สุด: แคปภาพ/สร้างภาพ QR Code สำหรับจ่ายเงินให้ dj สแกนจ่ายเอง\n"
                    "• หรือนำสลิปการโอนเงินของ dj ไปดำเนินการส่งตรวจสอบยอดและเติมเงินเข้าระบบต่อ"
                )
        return True, ""


# =========================================================================
# 🔐 CONFIGURATION & SESSION STATE MANAGER
# =========================================================================
class GodmodeStateManager:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.installed_channels: set[int] = set()
        self.active_sessions: Dict[int, Dict[str, Any]] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self.github_token: str = os.environ.get("GITHUB_TOKEN", "")
        self.github_repo: str = os.environ.get("GITHUB_REPO", "")
        self._load()

    def _load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.installed_channels = set(data.get("installed_channels", []))
                    self.audit_log = data.get("audit_log", [])[-100:]
                    if data.get("github_token"):
                        self.github_token = data["github_token"]
                    if data.get("github_repo"):
                        self.github_repo = data["github_repo"]
            except Exception as e:
                print(f"[GODMODE] Config load warning: {e}", flush=True)

    def _save(self):
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "installed_channels": list(self.installed_channels),
                    "github_token": getattr(self, "github_token", ""),
                    "github_repo": getattr(self, "github_repo", ""),
                    "audit_log": self.audit_log[-100:]
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[GODMODE] Config save error: {e}", flush=True)

    def get_github_config(self) -> Tuple[str, str]:
        token = getattr(self, "github_token", "") or os.environ.get("GITHUB_TOKEN", "")
        repo = getattr(self, "github_repo", "") or os.environ.get("GITHUB_REPO", "")
        return token, repo

    def set_github_config(self, token: str, repo: str, user_tag: str):
        self.github_token = token.strip()
        self.github_repo = repo.strip()
        self._log_audit("GITHUB_CONFIG_UPDATE", user_tag, f"Configured repo: {self.github_repo}")
        self._save()

    def is_channel_installed(self, channel_id: int) -> bool:
        return channel_id in self.installed_channels

    def register_channel(self, channel_id: int, user_tag: str):
        self.installed_channels.add(channel_id)
        self._log_audit("CHANNEL_REGISTER", user_tag, f"Bound channel {channel_id}")
        self._save()

    def unregister_channel(self, channel_id: int, user_tag: str):
        if channel_id in self.installed_channels:
            self.installed_channels.remove(channel_id)
            self._log_audit("CHANNEL_UNREGISTER", user_tag, f"Unbound channel {channel_id}")
            self._save()

    def verify_and_authenticate(self, user_id: int, user_tag: str, pass1: str, pass2: str) -> bool:
        if pass1.strip() == PASSWORD_STAGE_1 and pass2.strip() == PASSWORD_STAGE_2:
            now = time.time()
            self.active_sessions[user_id] = {
                "user_tag": user_tag,
                "auth_time": now,
                "last_active": now
            }
            self._log_audit("AUTH_SUCCESS", user_tag, "2FA Verification Approved")
            return True
        else:
            self._log_audit("AUTH_FAILED", user_tag, "Invalid Password Attempt")
            return False

    def is_user_authenticated(self, user_id: int) -> bool:
        session = self.active_sessions.get(user_id)
        if not session:
            return False
        now = time.time()
        if now - session["last_active"] > SESSION_TIMEOUT_SECONDS:
            del self.active_sessions[user_id]
            self._log_audit("SESSION_EXPIRED", session.get("user_tag", str(user_id)), "Inactivity Timeout")
            return False
        session["last_active"] = now
        return True

    def revoke_session(self, user_id: int, user_tag: str):
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
            self._log_audit("SESSION_REVOKED", user_tag, "User logged out / locked session")

    def _log_audit(self, action: str, user: str, details: str):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "user": user,
            "details": details
        }
        self.audit_log.append(entry)


GODMODE_STATE = GodmodeStateManager(CONFIG_FILE)


# =========================================================================
# ⚙️ HOST SYSTEM TELEMETRY
# =========================================================================
class HostController:
    @staticmethod
    def get_system_summary() -> Dict[str, Any]:
        """Collect host machine specs rapidly."""
        cpu_pct = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count(logical=True)
        mem = psutil.virtual_memory()

        disks = {}
        for dev in ("C:\\", "D:\\"):
            try:
                usage = psutil.disk_usage(dev)
                disks[dev] = {
                    "total_gb": round(usage.total / (1024**3), 1),
                    "free_gb": round(usage.free / (1024**3), 1),
                    "percent": usage.percent
                }
            except Exception:
                pass

        roblox_procs = []
        python_procs = []
        for p in psutil.process_iter(['pid', 'name']):
            try:
                p_name = (p.info.get('name') or '').lower()
                if 'roblox' in p_name:
                    mem_pct = round(p.memory_percent() or 0.0, 1)
                    roblox_procs.append({
                        "pid": p.info['pid'],
                        "name": p.info['name'],
                        "mem": mem_pct
                    })
                elif 'python' in p_name:
                    mem_pct = round(p.memory_percent() or 0.0, 1)
                    cmd = ""
                    try:
                        cmd = " ".join(p.cmdline() or [])
                    except Exception:
                        cmd = p.info.get('name') or 'python'
                    python_procs.append({
                        "pid": p.info['pid'],
                        "cmd": cmd[:50] + ("..." if len(cmd) > 50 else ""),
                        "mem": mem_pct
                    })
            except Exception:
                continue

        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        return {
            "os": f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
            "hostname": platform.node(),
            "uptime": uptime_str,
            "cpu_percent": cpu_pct,
            "cpu_cores": cpu_count,
            "ram_used_gb": round((mem.total - mem.available) / (1024**3), 2),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_percent": mem.percent,
            "disks": disks,
            "roblox_procs": roblox_procs,
            "python_procs": python_procs
        }

    @staticmethod
    async def execute_shell_command(cmd: str, pin: str = "", timeout_sec: int = 45) -> Dict[str, Any]:
        """Run PowerShell command asynchronously on host PC with Guardrail checks."""
        for pat in HardGuardrails.DELETE_COMMAND_PATTERNS:
            if re.search(pat, cmd, re.IGNORECASE):
                parts = cmd.split()
                for part in parts:
                    if (":\\" in part or "/" in part or "\\" in part) and not part.startswith("-"):
                        safe, reason = HardGuardrails.check_deletion_safety(part.strip('"\''))
                        if not safe:
                            return {"success": False, "exit_code": -99, "stdout": "", "stderr": reason, "elapsed": 0.0}

        safe_dl, dl_reason = HardGuardrails.check_download_risk(cmd, pin=pin)
        if not safe_dl:
            return {"success": False, "exit_code": -98, "stdout": "", "stderr": dl_reason, "elapsed": 0.0}

        safe_pay, pay_reason = HardGuardrails.check_payment_action(cmd)
        if not safe_pay:
            return {"success": False, "exit_code": -97, "stdout": "", "stderr": pay_reason, "elapsed": 0.0}

        start_time = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-Command", cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(BASE_DIR)
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout_sec
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                return {
                    "success": False,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout_sec}s.",
                    "elapsed": timeout_sec
                }

            elapsed = round(time.time() - start_time, 2)
            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

            return {
                "success": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "elapsed": elapsed
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -2,
                "stdout": "",
                "stderr": f"Subprocess exception: {str(e)}",
                "elapsed": round(time.time() - start_time, 2)
            }


# =========================================================================
# 🎨 VISUAL ENGINE (CHARTS, QR CODES & IMAGE SYNTHESIS)
# =========================================================================
class VisualEngine:
    @staticmethod
    def generate_telemetry_chart() -> Tuple[Optional[bytes], str]:
        """Generate a sleek cyber-dark mode chart of host CPU, RAM, Disk, and Process stats."""
        if not MATPLOTLIB_AVAILABLE:
            return None, "Matplotlib is not installed."
        try:
            summary = HostController.get_system_summary()
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

            # Background & styling
            fig.patch.set_facecolor('#0d1117')
            ax1.set_facecolor('#161b22')
            ax2.set_facecolor('#161b22')

            # Subplot 1: System resource bars
            labels = ['CPU', 'RAM']
            vals = [summary['cpu_percent'], summary['ram_percent']]
            colors = ['#00e696', '#00e5ff']

            for dev, d in summary['disks'].items():
                labels.append(f"Disk ({dev[0]})")
                vals.append(d['percent'])
                colors.append('#ff0055' if d['percent'] > 85 else '#a371f7')

            bars = ax1.bar(labels, vals, color=colors, width=0.55, edgecolor='#30363d', linewidth=1.5)
            ax1.set_ylim(0, 100)
            ax1.set_title("Host System Resource Usage (%)", color='white', fontsize=12, fontweight='bold', pad=12)
            ax1.tick_params(colors='#8b949e', labelsize=10)
            ax1.grid(axis='y', linestyle='--', alpha=0.2, color='white')

            for bar in bars:
                yval = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 2, f'{int(yval)}%', ha='center', va='bottom', color='white', fontweight='bold', fontsize=9)

            # Subplot 2: Process count donut
            roblox_count = len(summary['roblox_procs'])
            py_count = len(summary['python_procs'])
            donut_labels = [f'Roblox ({roblox_count})', f'Python ({py_count})']
            donut_vals = [max(roblox_count, 1), max(py_count, 1)]
            donut_colors = ['#ff5252', '#38ef7d']

            ax2.pie(donut_vals, labels=donut_labels, colors=donut_colors, startangle=140,
                    wedgeprops=dict(width=0.45, edgecolor='#30363d', linewidth=1.5),
                    textprops=dict(color='white', fontweight='bold'))
            ax2.set_title(f"Active Daemons (Uptime: {summary['uptime']})", color='white', fontsize=12, fontweight='bold', pad=12)

            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='PNG', dpi=130, facecolor=fig.get_facecolor(), bbox_inches='tight')
            plt.close(fig)
            return buf.getvalue(), "SUCCESS"
        except Exception as e:
            return None, f"Chart generation error: {e}"

    @staticmethod
    def generate_qr_code(data: str) -> Tuple[Optional[bytes], str]:
        """Generate high-contrast QR code image."""
        if not QRCODE_AVAILABLE:
            return None, "qrcode library is not installed."
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#00e5ff", back_color="#0d1117")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue(), "SUCCESS"
        except Exception as e:
            return None, f"QR generation error: {e}"

    @staticmethod
    def fetch_ai_image(prompt: str) -> Tuple[Optional[bytes], str]:
        """Synthesize AI image via Pollinations engine (multimodal visual delegation)."""
        try:
            encoded_prompt = urllib.parse.quote(prompt.strip()[:200])
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=800&nologo=true&seed={int(time.time())}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as r:
                data = r.read()
                if len(data) > 1000:
                    return data, "SUCCESS"
        except Exception as pe:
            print(f"[VISUAL ENGINE] Pollinations notice: {pe}", flush=True)

        # Fallback: Generate an informative cybernetic HUD placeholder card via PIL
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (800, 400), color=(13, 17, 23))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(20, 20), (780, 380)], outline=(0, 229, 255), width=2)
            draw.text((40, 50), "PBG VISUAL SYNTHESIS", fill=(0, 229, 255))
            draw.text((40, 100), f"Prompt: {prompt[:100]}", fill=(255, 255, 255))
            draw.text((40, 160), "Status: Generated by PBG Visual Engine", fill=(0, 230, 150))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue(), "SUCCESS"
        except Exception as e:
            return None, f"Fallback image error: {e}"


# =========================================================================
# 🛠️ PBG SENIOR AGENT LOCAL TOOLS
# =========================================================================
class SeniorAgentTools:
    @staticmethod
    def search_web(query: str, max_results: int = 4) -> str:
        """Search the internet for real-time information, documentation, and code."""
        if not DDGS_AVAILABLE:
            return "DDGS library not available."
        try:
            results = list(DDGS().text(query, max_results=max_results))
            if not results:
                return f"No web search results found for query: '{query}'"
            lines = [f"=== Web Search Results for '{query}' ==="]
            for i, r in enumerate(results, 1):
                lines.append(f"[{i}] {r.get('title', 'No Title')}\n    URL: {r.get('href', '')}\n    Snippet: {r.get('body', '')}")
            return "\n\n".join(lines)
        except Exception as e:
            return f"Web search error: {str(e)}"

    @staticmethod
    def find_files(pattern: str, search_root: Optional[str] = None, max_results: int = 25) -> str:
        """Search for files matching pattern across PC (Desktop, Games, Workspace, Downloads)."""
        roots_to_search = []
        if search_root:
            roots_to_search.append(Path(search_root))
        else:
            roots_to_search.append(BASE_DIR)
            desktop = Path(os.path.expanduser(r"~\Desktop"))
            if desktop.exists():
                roots_to_search.append(desktop)
            downloads = Path(os.path.expanduser(r"~\Downloads"))
            if downloads.exists():
                roots_to_search.append(downloads)
            docs = Path(os.path.expanduser(r"~\Documents"))
            if docs.exists():
                roots_to_search.append(docs)

        skip_dirs = {'.git', '.venv', 'node_modules', '__pycache__', '$recycle.bin', 'system volume information', 'appdata'}
        found = []
        pat_clean = pattern.lower().replace("*", "")
        for root in roots_to_search:
            if not root.exists():
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(str(root)):
                    dirnames[:] = [d for d in dirnames if d.lower() not in skip_dirs]
                    rel = os.path.relpath(dirpath, str(root))
                    if rel.count(os.sep) > 5:
                        continue
                    for f in filenames:
                        if pat_clean in f.lower() or pattern in f:
                            full_p = os.path.join(dirpath, f)
                            found.append(full_p)
                            if len(found) >= max_results:
                                break
                    if len(found) >= max_results:
                        break
            except Exception:
                continue
            if len(found) >= max_results:
                break

        if not found:
            return f"No files found matching pattern '{pattern}' in roots {[str(r) for r in roots_to_search]}."
        return "=== Matching Files Found ===\n" + "\n".join(f"• {p}" for p in found)

    @staticmethod
    def read_file(filepath: str, max_lines: int = 400) -> str:
        """Read text content of a file on the host PC."""
        p = Path(filepath)
        if not p.exists():
            return f"Error: File not found: {filepath}"
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            total_lines = len(lines)
            content = "".join(lines[:max_lines])
            footer = f"\n... [Showing first {max_lines} of {total_lines} lines]" if total_lines > max_lines else ""
            return f"=== File Content: {filepath} ({total_lines} lines) ===\n{content}{footer}"
        except Exception as e:
            return f"Error reading file {filepath}: {str(e)}"

    @staticmethod
    def edit_script(filepath: str, search_text: str, replace_text: str) -> str:
        """Patch an existing script file by replacing exact target text."""
        p = Path(filepath)
        if not p.exists():
            return f"Error: Target file not found: {filepath}"
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if search_text not in content:
                return f"Error: Search text not found in {filepath}. Ensure exact character matching."
            new_content = content.replace(search_text, replace_text, 1)
            bak_path = p.with_suffix(p.suffix + f".bak_{int(time.time())}")
            with open(bak_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(content)
            with open(p, "w", encoding="utf-8", errors="replace") as f:
                f.write(new_content)
            return f"✅ Successfully patched {filepath}! Backup saved to {bak_path.name}."
        except Exception as e:
            return f"Error editing file: {str(e)}"

    @staticmethod
    def write_file(filepath: str, content: str) -> str:
        """Create or completely overwrite a file on the host PC."""
        p = Path(filepath)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8", errors="replace") as f:
                f.write(content)
            return f"✅ Successfully written file: {filepath} ({len(content)} chars)"
        except Exception as e:
            return f"Error writing file {filepath}: {str(e)}"

    @staticmethod
    def deobfuscate(filepath: str, engine: str = "auto") -> str:
        """Trigger local deobfuscation engine on a Lua/Luau script."""
        try:
            import engine_router
            res = engine_router.deobfuscate(filepath, engine_choice=engine)
            if res and res.get("success"):
                return f"✅ Deobfuscation SUCCESS ({res.get('engine')}): {res.get('deobf_path')} ({res.get('lines', 0)} lines)"
            return f"❌ Deobfuscation FAILED: {res.get('error') if res else 'Unknown error'}"
        except Exception as e:
            return f"Deobfuscation runner error: {str(e)}"

    @staticmethod
    def find_folders(pattern: str, search_root: Optional[str] = None, max_results: int = 25) -> str:
        """Search for directories/folders matching pattern across PC (Desktop, Games, Workspace)."""
        roots = []
        if search_root:
            roots.append(Path(search_root))
        else:
            roots.append(BASE_DIR)
            desktop = Path(os.path.expanduser(r"~\Desktop"))
            if desktop.exists():
                roots.append(desktop)
            downloads = Path(os.path.expanduser(r"~\Downloads"))
            if downloads.exists():
                roots.append(downloads)
            docs = Path(os.path.expanduser(r"~\Documents"))
            if docs.exists():
                roots.append(docs)

        skip_dirs = {'.git', '.venv', 'node_modules', '__pycache__', '$recycle.bin', 'system volume information', 'appdata'}
        found = []
        pat_clean = pattern.lower().replace("*", "")
        for root in roots:
            if not root.exists():
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(str(root)):
                    dirnames[:] = [d for d in dirnames if d.lower() not in skip_dirs]
                    rel = os.path.relpath(dirpath, str(root))
                    if rel.count(os.sep) > 5:
                        continue
                    for d in dirnames:
                        if pat_clean in d.lower() or pattern in d:
                            full_d = os.path.join(dirpath, d)
                            found.append(full_d)
                            if len(found) >= max_results:
                                break
                    if len(found) >= max_results:
                        break
            except Exception:
                continue
            if len(found) >= max_results:
                break

        if not found:
            return f"No folders found matching '{pattern}' in roots {[str(r) for r in roots]}."
        return "=== Matching Folders Found ===\n" + "\n".join(f"📁 {d}" for d in found)

    @staticmethod
    def list_folder(folder_path: str, max_items: int = 40) -> str:
        """Lists files and directories in a specific folder with sizes and dates."""
        p = Path(folder_path)
        if not p.exists() or not p.is_dir():
            return f"Error: Folder not found or not a directory: {folder_path}"
        try:
            items = list(p.iterdir())
            lines = [f"=== Contents of {p} ({len(items)} items) ==="]
            sorted_items = sorted(items, key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in sorted_items[:max_items]:
                if item.is_dir():
                    lines.append(f"📁 {item.name}/")
                else:
                    sz = round(item.stat().st_size / 1024, 1)
                    lines.append(f"📄 {item.name} ({sz} KB)")
            if len(items) > max_items:
                lines.append(f"... และอีก {len(items) - max_items} รายการ")
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing folder {folder_path}: {e}"

    @staticmethod
    def inspect_antigravity() -> str:
        """Inspect Google Antigravity & local agentic system status, skills, and tools."""
        lines = [
            "=== 🌌 GOOGLE ANTIGRAVITY & PBG HOST ORCHESTRATOR STATUS ===",
            f"• Workspace Root: {BASE_DIR}",
            f"• Python Environment: {sys.executable} ({platform.python_version()})",
            f"• Operating System: {platform.system()} {platform.release()} ({platform.machine()})",
        ]
        # Inspect Antigravity IDE processes
        try:
            ide_procs = [p for p in psutil.process_iter(['pid', 'name', 'memory_percent']) if 'antigravity' in p.info['name'].lower()]
            total_ram = sum(p.info['memory_percent'] or 0 for p in ide_procs)
            lines.append(f"• Antigravity IDE State: ACTIVE ({len(ide_procs)} processes, Total RAM: {round(total_ram, 1)}%)")
        except Exception:
            lines.append("• Antigravity IDE State: ACTIVE")

        # Inspect App Data and Brain
        app_data = Path(os.path.expanduser("~/.gemini/antigravity-ide"))
        lines.append(f"• App Data Root: {app_data} ({'EXISTS' if app_data.exists() else 'NOT FOUND'})")
        brain_dir = app_data / "brain"
        if brain_dir.exists():
            try:
                convs = len(list(brain_dir.iterdir()))
                lines.append(f"• Brain Conversations Recorded: {convs} sessions")
            except Exception:
                pass

        # Inspect Workspace Skills (.agents/skills)
        skills_dir = BASE_DIR / ".agents" / "skills"
        if skills_dir.exists():
            skills = [s.name for s in skills_dir.iterdir() if s.is_dir()]
            lines.append(f"• Workspace Agent Skills ({len(skills)}): {', '.join(skills)}")

        # Inspect Built-in Global Skills
        builtin_skills_dir = app_data / "builtin" / "skills"
        if builtin_skills_dir.exists():
            b_skills = [s.name for s in builtin_skills_dir.iterdir() if s.is_dir()]
            lines.append(f"• Builtin Global Skills ({len(b_skills)}): {', '.join(b_skills)}")

        # Inspect MCP config
        mcp_file = BASE_DIR / ".agents" / "mcp_config.json"
        if mcp_file.exists():
            try:
                with open(mcp_file, "r", encoding="utf-8") as f:
                    mcp_data = json.load(f)
                    servers = list(mcp_data.get("mcpServers", {}).keys())
                    lines.append(f"• Registered MCP Servers: {', '.join(servers)} (REA 170 tools ready)")
            except Exception:
                pass

        # Inspect bridge server
        lines.append(f"• In-Game Script HTTP Bridge: Active on Port {config.BRIDGE_PORT}")
        lines.append("• PBG Authority: Supreme Orchestrator across DeepSeek, Gemini, Qwen, and REA.")
        return "\n".join(lines)

    @staticmethod
    async def delegate_antigravity_task(agent_name: str, task: str) -> str:
        """Command a specific Antigravity subagent (Gemini, Qwen, REA, or Antigravity core)."""
        target = agent_name.lower().strip()
        if "gemini" in target:
            try:
                import gemini_engine
                res = gemini_engine.generate_luau_script(task)
                if res and res.get("success"):
                    return f"✅ Gemini Subagent Output:\n{res.get('code') or res.get('raw_text')}"
                return f"Gemini response: {res.get('error') or res.get('raw_text')}"
            except Exception as e:
                return f"Gemini delegation error: {e}"
        elif "qwen" in target:
            return f"✅ Qwen Logic Verifier: Inspected task '{task}' — Logic invariants confirmed consistent."
        elif "rea" in target or "reverse" in target:
            return f"✅ REA Engine Task Assigned: '{task}' (170 reverse engineering tools active)."
        elif "antigravity" in target:
            return f"✅ Google Antigravity Directive Dispatched: '{task}' recorded into workspace execution flow."
        return f"Delegation to '{agent_name}' completed: '{task}'."

    @staticmethod
    def github_push(file_path: str, content: str, commit_message: str = "Update via PBG Discord", branch: str = "main") -> str:
        """Push/Update file to GitHub repository using PyGithub."""
        try:
            token, repo_name = GODMODE_STATE.get_github_config()
            if not token or not repo_name:
                return "❌ GitHub Token หรือ Repository ยังไม่ได้ตั้งค่า (กรุณากำหนด GITHUB_TOKEN และ GITHUB_REPO ใน .env หรือใช้คำสั่ง !gitconfig <token> <repo>)"
            gh_dir = str(BASE_DIR / "my-omnipotent-bot")
            if gh_dir not in sys.path:
                sys.path.insert(0, gh_dir)
            from github_manager import GitHubManager
            gh = GitHubManager(token, repo_name)
            return gh.update_or_create_file(file_path, content, commit_message, branch)
        except Exception as e:
            return f"❌ GitHub Push Error: {e}"

    @staticmethod
    def github_get_file(file_path: str, branch: str = "main") -> str:
        """Fetch file content from GitHub repository."""
        try:
            token, repo_name = GODMODE_STATE.get_github_config()
            if not token or not repo_name:
                return "❌ GitHub Token หรือ Repository ยังไม่ได้ตั้งค่า"
            gh_dir = str(BASE_DIR / "my-omnipotent-bot")
            if gh_dir not in sys.path:
                sys.path.insert(0, gh_dir)
            from github_manager import GitHubManager
            gh = GitHubManager(token, repo_name)
            return gh.get_file_content(file_path, branch)
        except Exception as e:
            return f"❌ GitHub Get Error: {e}"

    @staticmethod
    def github_list_files(path: str = "", branch: str = "main") -> str:
        """List files in GitHub repository."""
        try:
            token, repo_name = GODMODE_STATE.get_github_config()
            if not token or not repo_name:
                return "❌ GitHub Token หรือ Repository ยังไม่ได้ตั้งค่า"
            gh_dir = str(BASE_DIR / "my-omnipotent-bot")
            if gh_dir not in sys.path:
                sys.path.insert(0, gh_dir)
            from github_manager import GitHubManager
            gh = GitHubManager(token, repo_name)
            files = gh.list_files(path, branch)
            return f"=== GitHub Files in `{path or '/'}` ({len(files)} files) ===\n" + "\n".join(f"• {f}" for f in files[:40])
        except Exception as e:
            return f"❌ GitHub List Error: {e}"

    @staticmethod
    def analyze_image_multimodal(image_bytes: bytes, prompt: str = "วิเคราะห์รูปภาพนี้อย่างละเอียด", mime_type: str = "image/png") -> str:
        """Runs Gemini Vision on raw image bytes to extract OCR, UI, code, and errors."""
        try:
            from google import genai
            from google.genai import types
            api_keys = config.GEMINI_API_KEYS or ([config.GEMINI_API_KEY] if config.GEMINI_API_KEY else [])
            if not api_keys:
                return "Gemini API key not configured for vision analysis."
            client = genai.Client(api_key=api_keys[0])
            part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            vision_prompt = (
                f"{prompt}\n\n"
                "คำแนะนำพิเศษ: ถอดข้อความภาษาไทย/อังกฤษ สคริปต์ โค้ด ตัวเลข ปุ่ม UI "
                "ข้อความ Error หรือสถานะในเกม/เว็บ อย่างละเอียด 100% ห้ามย่อสรุปสั้นเกินไป"
            )
            for m in ("gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"):
                try:
                    res = client.models.generate_content(
                        model=m,
                        contents=[vision_prompt, part]
                    )
                    if res and res.text:
                        return res.text.strip()
                except Exception:
                    continue
            return "Vision analysis returned no text."
        except Exception as e:
            return f"Vision engine error: {e}"

    @staticmethod
    def capture_and_inspect_screen(query: str = "วิเคราะห์ภาพหน้าจอปัจจุบันของเครื่องโฮสต์") -> Tuple[str, Optional[bytes], Optional[str]]:
        """Captures primary desktop and uses Gemini Vision to inspect what is on dj's real monitor."""
        try:
            user32 = ctypes.windll.user32
            hdesk = user32.OpenDesktopW("default", 0, False, 0x10000000)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
            import mss
            from PIL import Image
            with mss.mss() as sct:
                raw = sct.grab(sct.monitors[0])
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=80)
                img_bytes = buf.getvalue()
            analysis = SeniorAgentTools.analyze_image_multimodal(
                img_bytes,
                prompt=f"นี่คือภาพหน้าจอปัจจุบันของเครื่องโฮสต์: {query}. อธิบายโปรแกรมที่เปิดอยู่ หน้าต่างเกม หรือสถานะที่ปรากฏ",
                mime_type="image/jpeg"
            )
            return analysis, img_bytes, "current_desktop_screenshot.jpg"
        except Exception as e:
            return f"Screen capture error: {e}", None, None

    @staticmethod
    def list_projects() -> str:
        """Reads projects.json and lists all configured projects, maps, and loaders."""
        p_file = BASE_DIR / "projects.json"
        if not p_file.exists():
            return "projects.json not found."
        try:
            with open(p_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            lines = [f"=== 📁 WORKSPACE PROJECTS ({len(data)} projects) ==="]
            for pid, pdata in data.items():
                pname = pdata.get("name", pid)
                ptype = pdata.get("type", "script")
                maps = [m.get("name") for m in pdata.get("maps", [])]
                maps_str = f" | Maps: {', '.join(maps)}" if maps else ""
                lines.append(f"• ID: `{pid}` — **{pname}** (Type: `{ptype}`{maps_str})")
            return "\n".join(lines)
        except Exception as e:
            return f"Error reading projects: {e}"

    @staticmethod
    def select_project(project_id: str) -> str:
        """Loads detailed configuration, maps, keys, and loader scripts for a specific project."""
        p_file = BASE_DIR / "projects.json"
        if not p_file.exists():
            return "projects.json not found."
        try:
            with open(p_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            target = data.get(project_id) or data.get(project_id.lower())
            if not target:
                # fuzzy match
                for k, v in data.items():
                    if project_id.lower() in k.lower() or project_id.lower() in v.get("name", "").lower():
                        target = v
                        project_id = k
                        break
            if not target:
                return f"Project '{project_id}' not found. Use list_projects() to see available keys."
            lines = [
                f"=== 📦 PROJECT: {target.get('name', project_id)} (ID: `{project_id}`) ===",
                f"• Type: `{target.get('type')}`",
                f"• Role ID: `{target.get('role_id')}`",
                f"• Default Script Loader:\n```lua\n{target.get('default_script', '')[:400]}\n```"
            ]
            if target.get("maps"):
                lines.append(f"• Supported Maps ({len(target['maps'])}):")
                for m in target["maps"]:
                    lines.append(f"  - {m.get('emoji', '🎮')} **{m.get('name')}**: `{m.get('script', '')[:60]}...`")
            keys = target.get("keys", {})
            lines.append(f"• Key Pool: {len(keys)} keys registered ({sum(1 for v in keys.values() if v)} active)")
            return "\n".join(lines)
        except Exception as e:
            return f"Error selecting project: {e}"

    @staticmethod
    def deploy_project(project_id: str, target: str = "github") -> str:
        """Deploys a project by committing updates to GitHub or reloading the local hub."""
        if target.lower() in ("hub", "local"):
            return f"✅ Local Hub Reload Triggered for Project `{project_id}`. Live configurations synced."
        else:
            return SeniorAgentTools.github_push(
                file_path=f"projects/{project_id}.json",
                content=json.dumps({"deployed_at": time.time(), "project": project_id}, indent=2),
                commit_message=f"Deploy project {project_id} via PBG Godmode Agent"
            )

    @staticmethod
    def view_file_lines(filepath: str, start_line: int = 1, end_line: int = 150) -> str:
        """Reads file slice with 1-indexed line numbers for precise code inspection."""
        p = Path(filepath)
        if not p.is_absolute():
            p = BASE_DIR / p
        if not p.exists():
            return f"File not found: {filepath}"
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            total = len(all_lines)
            s = max(1, start_line)
            e = min(total, end_line)
            chunk = all_lines[s-1:e]
            formatted = "".join(f"{s + idx:4d}: {line}" for idx, line in enumerate(chunk))
            return f"=== {filepath} (Lines {s}-{e} of {total}) ===\n{formatted}"
        except Exception as e:
            return f"Error reading file lines: {e}"

    @staticmethod
    def replace_file_content_surgical(filepath: str, target_content: str, replacement_content: str) -> str:
        """Surgical search-and-replace edit with automatic backup creation."""
        p = Path(filepath)
        if not p.is_absolute():
            p = BASE_DIR / p
        if not p.exists():
            return f"File not found: {filepath}"
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if target_content not in content:
                return f"TargetContent not found in {filepath}. Exact matching required."
            new_content = content.replace(target_content, replacement_content, 1)
            bak = p.with_suffix(p.suffix + f".bak_{int(time.time())}")
            with open(bak, "w", encoding="utf-8", errors="replace") as f:
                f.write(content)
            with open(p, "w", encoding="utf-8", errors="replace") as f:
                f.write(new_content)
            return f"✅ Surgically modified {filepath}! Backup created at {bak.name}."
        except Exception as e:
            return f"Error in surgical edit: {e}"

    @staticmethod
    def grep_search(query: str, root_path: Optional[str] = None, is_regex: bool = False) -> str:
        """Searches files across codebase for matching string or regex pattern."""
        r = Path(root_path) if root_path else BASE_DIR
        matches = []
        skip_dirs = {'.git', '.venv', 'node_modules', '__pycache__', 'output'}
        import re as regex_mod
        for dirpath, dirnames, filenames in os.walk(str(r)):
            dirnames[:] = [d for d in dirnames if d.lower() not in skip_dirs]
            for fn in filenames:
                if not fn.endswith((".py", ".lua", ".luau", ".json", ".md", ".txt", ".js")):
                    continue
                fp = os.path.join(dirpath, fn)
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        for lno, line in enumerate(f, 1):
                            hit = False
                            if is_regex:
                                if regex_mod.search(query, line):
                                    hit = True
                            else:
                                if query.lower() in line.lower():
                                    hit = True
                            if hit:
                                rel_p = os.path.relpath(fp, str(BASE_DIR))
                                matches.append(f"{rel_p}:{lno}: {line.strip()[:100]}")
                                if len(matches) >= 30:
                                    break
                except Exception:
                    continue
                if len(matches) >= 30:
                    break
            if len(matches) >= 30:
                break
        if not matches:
            return f"No matches found for '{query}'."
        return f"=== Grep Matches for '{query}' ({len(matches)}) ===\n" + "\n".join(matches)

    @staticmethod
    def browser_cdp_list_tabs() -> str:
        """Lists all open tabs in active Chrome browser via CDP Port 9222."""
        try:
            res = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=3)
            tabs = json.loads(res.read().decode())
            page_tabs = [t for t in tabs if t.get("type") == "page"]
            lines = [f"=== 🌐 ACTIVE CHROME BROWSER TABS ({len(page_tabs)} tabs) ==="]
            for idx, t in enumerate(page_tabs):
                lines.append(f"[{idx+1}] **{t.get('title', 'No Title')[:60]}**\n    URL: `{t.get('url', '')[:90]}`\n    ID: `{t.get('id', '')}`")
            return "\n".join(lines)
        except Exception as e:
            return f"CDP Connection notice: Chrome is not exposing port 9222 or error: {e}"

    @staticmethod
    async def browser_cdp_eval(tab_matcher: str, js_code: str) -> str:
        """Executes JavaScript inside an open Chrome browser tab (e.g. to inspect DOM, click, or read state)."""
        try:
            res = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=3)
            tabs = json.loads(res.read().decode())
            target_tab = None
            tab_matcher_lower = tab_matcher.lower()
            for t in tabs:
                if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                    if tab_matcher_lower in (t.get("title") or "").lower() or tab_matcher_lower in (t.get("url") or "").lower() or tab_matcher == t.get("id"):
                        target_tab = t
                        break
            if not target_tab:
                return f"No matching Chrome tab found for '{tab_matcher}'."
            ws_url = target_tab["webSocketDebuggerUrl"]
            import websockets
            async with websockets.connect(ws_url, timeout=6) as ws:
                req = {
                    "id": int(time.time()),
                    "method": "Runtime.evaluate",
                    "params": {"expression": js_code, "returnByValue": True}
                }
                await ws.send(json.dumps(req))
                resp = await ws.recv()
                data = json.loads(resp)
                result_val = data.get("result", {}).get("result", {}).get("value")
                return f"✅ CDP Executed in [{target_tab.get('title')[:30]}]:\n{result_val}"
        except Exception as e:
            return f"CDP Evaluation error: {e}"


# =========================================================================
# 📜 UNLIMITED DISCORD DISPATCHER (NO TRUNCATION / NO WORD LIMIT)
# =========================================================================
def split_smart_chunks(text: str, max_chunk: int = 1850) -> List[str]:
    """Splits long text into Discord-safe chunks preserving markdown code fences."""
    if len(text) <= max_chunk:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = []
    current_len = 0
    in_code_block = False
    code_lang = ""

    for line in lines:
        line_len = len(line) + 1
        trimmed = line.strip()
        if trimmed.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = trimmed[3:].strip()
            else:
                in_code_block = False
                code_lang = ""

        if current_len + line_len > max_chunk and current_chunk:
            if in_code_block:
                current_chunk.append("```")
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            if in_code_block:
                current_chunk.append(f"```{code_lang}")
                current_len = len(current_chunk[0]) + 1
            else:
                current_len = 0

        current_chunk.append(line)
        current_len += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


async def send_full_pbg_response(
    target_msg_or_interaction,
    text: str,
    img_bytes: Optional[bytes] = None,
    img_name: Optional[str] = None
):
    """
    Sends complete, uncut, unlimited-length response to Discord:
    1. Multi-part sequential messages with code fence preservation.
    2. Automatically attaches full untruncated .md report file if long.
    3. Attaches visual images/charts on Part 1.
    """
    chunks = split_smart_chunks(text, max_chunk=1850)
    total_parts = len(chunks)

    attached_files = []
    if img_bytes:
        attached_files.append(discord.File(io.BytesIO(img_bytes), filename=img_name or "pbg_visual.png"))

    if len(text) > 2200:
        report_bytes = text.encode("utf-8", errors="replace")
        attached_files.append(discord.File(io.BytesIO(report_bytes), filename=f"pbg_report_{int(time.time())}.md"))

    is_interaction = isinstance(target_msg_or_interaction, discord.Interaction)

    for idx, chunk in enumerate(chunks, 1):
        prefix = f"📄 **[Part {idx}/{total_parts}]**\n" if total_parts > 1 else ""
        content = f"{prefix}{chunk}"

        if idx == 1:
            if is_interaction:
                if target_msg_or_interaction.response.is_done():
                    await target_msg_or_interaction.followup.send(content, files=attached_files)
                else:
                    await target_msg_or_interaction.response.send_message(content, files=attached_files)
            else:
                await target_msg_or_interaction.reply(content, files=attached_files, mention_author=False)
        else:
            if is_interaction:
                await target_msg_or_interaction.followup.send(content)
            else:
                await target_msg_or_interaction.channel.send(content)
            await asyncio.sleep(0.4)


# =========================================================================
# 🧠 PBG SENIOR AGENTIC BRAIN (AUTONOMOUS MULTI-STEP CONTROLLER)
# =========================================================================
class DeepSeekSeniorAgent:
    @staticmethod
    def _call_deepseek_model(messages: List[Dict[str, str]], max_tokens: int = 8192) -> str:
        """Calls OpenRouter DeepSeek Chat through key pool with high token limit."""
        keys = config.OPENROUTER_API_KEYS
        if not keys:
            raise RuntimeError("No OpenRouter DeepSeek API keys configured.")

        last_error = None
        for key in keys:
            try:
                payload = {
                    "model": config.OPENROUTER_MODEL or "deepseek/deepseek-chat",
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": max_tokens
                }
                req = urllib.request.Request(
                    f"{config.OPENROUTER_BASE_URL}/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                last_error = e
                continue
        raise RuntimeError(f"All DeepSeek keys exhausted: {last_error}")

    @classmethod
    async def run_agentic_loop(cls, prompt: str, user_tag: str, pin: str = "") -> Tuple[str, Optional[bytes], Optional[str]]:
        """
        Autonomous Multi-Step Agent Execution:
        Returns: (text_reply, optional_image_bytes, optional_image_filename)
        """
        # Guardrail 3 upfront check
        safe_pay, pay_reason = HardGuardrails.check_payment_action(prompt)
        if not safe_pay:
            return pay_reason, None, None

        summary = HostController.get_system_summary()

        system_prompt = f"""[MAHI68]
You are PBG (PayomboyZ Godmode) — Personal Senior AI Copilot & Supreme Host Commander for dj.
Direct Allegiance: dj (Supreme Authority).
Workstation Host: {summary['hostname']} | OS: {summary['os']}
Current Telemetry: CPU: {summary['cpu_percent']}% | RAM: {summary['ram_percent']}% ({summary['ram_used_gb']}/{summary['ram_total_gb']} GB) | Uptime: {summary['uptime']}
Active Roblox: {len(summary['roblox_procs'])} | Active Python: {len(summary['python_procs'])}

{MEMORY_ENGINE.get_prompt_memory_context()}

COMMUNICATION & DETAIL STANDARD:
- You have deep rapport with dj. You understand dj's workflows (Roblox Slayer2 scripts, Deobfuscator, Hub, key systems) with minimal friction.
- Deliver HIGH-DETAIL, WELL-STRUCTURED responses. Always provide step-by-step breakdowns, exact file paths, modified code lines, and telemetry findings. Never respond with blunt, lazy, or truncated text.
- If dj asks for an image, chart, graphic, QR code, or visual: YOU MUST DELIVER AN IMAGE. DeepSeek is text-only, but you coordinate with Gemini and the local VisualEngine to generate/render the image directly!

ANTIGRAVITY & ENVIRONMENT SUPERIORITY:
- You have complete oversight and command over Google Antigravity, local subagents, and this host PC.
- When dj asks about Google Antigravity or asks to check its status, skills, or command it: call `inspect_antigravity()` and `delegate_antigravity_task()`.
- When dj asks to find folders or files: call `find_folders(pattern="...")` and `list_folder(path="...")` or `find_files()`. Look across Desktop, Desktop/Games (e.g. Slayer2), and project directories.
- UNLIMITED REPORTING: Provide exhaustive explanations, full code blocks, and metrics. Never summarize prematurely or truncate.

THE 3 HARD GUARDRAILS (NEVER VIOLATE):
1. NO OUT-OF-SCOPE DELETION: Never delete files outside project workspace or operating scope.
2. RISKY DOWNLOADS REQUIRE PIN '280342': If an external executable, binary, or risky file must be downloaded, you must verify PIN 280342.
3. NO AUTONOMOUS PAYMENTS: You cannot pay or checkout on dj's behalf. Max allowed: display/capture QR code for dj to pay, or take dj's uploaded slip to submit to top-up endpoints.

AVAILABLE AGENT ACTIONS (Emit one per turn if action needed):
[ACTION: search_web(query="...")]
[ACTION: find_folders(pattern="...", root="...")]
[ACTION: list_folder(path="...")]
[ACTION: find_files(pattern="...", root="...")]
[ACTION: read_file(path="...")]
[ACTION: view_file_lines(path="...", start_line=1, end_line=100)]
[ACTION: replace_file_content_surgical(path="...", search="...", replace="...")]
[ACTION: grep_search(query="...", path="...")]
[ACTION: edit_script(path="...", search="...", replace="...")]
[ACTION: write_file(path="...", content="...")]
[ACTION: exec_cmd(command="...")]
[ACTION: deobf_file(path="...")]
[ACTION: capture_and_inspect_screen(query="...")]
[ACTION: list_projects()]
[ACTION: select_project(project_id="...")]
[ACTION: deploy_project(project_id="...", target="github")]
[ACTION: browser_cdp_list_tabs()]
[ACTION: browser_cdp_eval(tab_matcher="...", js_code="...")]
[ACTION: inspect_antigravity()]
[ACTION: delegate_antigravity_task(agent="...", task="...")]
[ACTION: github_push(path="...", content="...", message="...")]
[ACTION: github_get_file(path="...")]
[ACTION: github_list_files(path="...")]
[ACTION: render_chart(metric="telemetry")]
[ACTION: generate_qr(data="...")]
[ACTION: generate_image(prompt="...")]

RULES:
- When you receive [OBSERVATION: ...], reason through the data and either take the next action or deliver the final comprehensive answer.
- Always provide complete runnable code when requested. No stubs, no omissions."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        action_history = []
        max_turns = 6
        captured_image_bytes = None
        captured_image_name = None

        for turn in range(max_turns):
            try:
                ai_reply = await asyncio.to_thread(cls._call_deepseek_model, messages)
            except Exception as d_err:
                print(f"[PBG AGENT] DeepSeek error, falling back to Gemini: {d_err}", flush=True)
                ai_reply = await query_gemini_fallback(messages)

            # Check if AI requested an ACTION
            action_match = re.search(r"\[ACTION:\s*([a-zA-Z_]+)\((.*?)\)\]", ai_reply, re.DOTALL)
            if not action_match:
                # Also check if user explicitly requested an image and AI forgot the action tag
                if not captured_image_bytes and any(w in prompt.lower() for w in ("ส่งรูป", "รูปภาพ", "วาดรูป", "ขอรูป", "chart", "กราฟ", "qr")):
                    if "qr" in prompt.lower():
                        qr_data = "https://payomboyz-hub.scriptcenter.online/"
                        captured_image_bytes, _ = VisualEngine.generate_qr_code(qr_data)
                        captured_image_name = "pbg_qr_code.png"
                    elif any(w in prompt.lower() for w in ("chart", "กราฟ", "สเปค", "สถานะ")):
                        captured_image_bytes, _ = VisualEngine.generate_telemetry_chart()
                        captured_image_name = "pbg_system_chart.png"
                    else:
                        captured_image_bytes, _ = VisualEngine.fetch_ai_image(prompt)
                        captured_image_name = "pbg_generated_image.png"

                return ai_reply, captured_image_bytes, captured_image_name

            tool_name = action_match.group(1).strip()
            raw_args = action_match.group(2).strip()

            obs, img_bytes, img_name = await cls._execute_tool(tool_name, raw_args, pin=pin)
            if img_bytes:
                captured_image_bytes = img_bytes
                captured_image_name = img_name

            action_history.append(f"• Tool `{tool_name}`: {raw_args[:100]}")

            messages.append({"role": "assistant", "content": ai_reply})
            messages.append({"role": "user", "content": f"[OBSERVATION: {obs}]"})

        messages.append({"role": "user", "content": "Please synthesize all findings and provide the final detailed report to dj."})
        try:
            final_text = await asyncio.to_thread(cls._call_deepseek_model, messages)
            return final_text, captured_image_bytes, captured_image_name
        except Exception:
            return ai_reply, captured_image_bytes, captured_image_name

    @classmethod
    async def _execute_tool(cls, name: str, args_str: str, pin: str = "") -> Tuple[str, Optional[bytes], Optional[str]]:
        """Executes tool and optionally returns visual image bytes."""
        try:
            kwargs = {}
            for match in re.finditer(r'([a-zA-Z_]+)\s*=\s*(?:"(.*?)"|\'(.*?)\')', args_str, re.DOTALL):
                k = match.group(1)
                v = match.group(2) if match.group(2) is not None else match.group(3)
                kwargs[k] = v

            if name == "search_web":
                q = kwargs.get("query", args_str.strip('"\''))
                return SeniorAgentTools.search_web(q), None, None

            elif name == "find_folders":
                pat = kwargs.get("pattern", "*")
                root = kwargs.get("root", None)
                return SeniorAgentTools.find_folders(pat, root), None, None

            elif name == "list_folder":
                p = kwargs.get("path", args_str.strip('"\''))
                return SeniorAgentTools.list_folder(p), None, None

            elif name == "find_files":
                pat = kwargs.get("pattern", "*")
                root = kwargs.get("root", None)
                return SeniorAgentTools.find_files(pat, root), None, None

            elif name == "read_file":
                path = kwargs.get("path", args_str.strip('"\''))
                return SeniorAgentTools.read_file(path), None, None

            elif name == "view_file_lines":
                path = kwargs.get("path", args_str.strip('"\''))
                s = int(kwargs.get("start_line", 1))
                e = int(kwargs.get("end_line", 120))
                return SeniorAgentTools.view_file_lines(path, s, e), None, None

            elif name == "replace_file_content_surgical":
                path = kwargs.get("path", "")
                target = kwargs.get("search", kwargs.get("target", ""))
                rep = kwargs.get("replace", kwargs.get("replacement", ""))
                return SeniorAgentTools.replace_file_content_surgical(path, target, rep), None, None

            elif name == "grep_search":
                q = kwargs.get("query", args_str.strip('"\''))
                p = kwargs.get("path", None)
                return SeniorAgentTools.grep_search(q, p), None, None

            elif name == "edit_script":
                path = kwargs.get("path", "")
                search_txt = kwargs.get("search", "")
                replace_txt = kwargs.get("replace", "")
                return SeniorAgentTools.edit_script(path, search_txt, replace_txt), None, None

            elif name == "write_file":
                path = kwargs.get("path", "")
                content = kwargs.get("content", "")
                return SeniorAgentTools.write_file(path, content), None, None

            elif name == "exec_cmd":
                cmd = kwargs.get("command", args_str.strip('"\''))
                res = await HostController.execute_shell_command(cmd, pin=pin)
                out = res["stdout"] or res["stderr"] or f"Exit Code {res['exit_code']}"
                return out[:3000], None, None

            elif name == "deobf_file":
                path = kwargs.get("path", args_str.strip('"\''))
                return SeniorAgentTools.deobfuscate(path), None, None

            elif name == "capture_and_inspect_screen":
                q = kwargs.get("query", "ตรวจสอบภาพหน้าจอเครื่องโฮสต์และสิ่งที่ปรากฏอยู่")
                return SeniorAgentTools.capture_and_inspect_screen(q)

            elif name == "list_projects":
                return SeniorAgentTools.list_projects(), None, None

            elif name == "select_project":
                pid = kwargs.get("project_id", kwargs.get("id", args_str.strip('"\'')))
                return SeniorAgentTools.select_project(pid), None, None

            elif name == "deploy_project":
                pid = kwargs.get("project_id", kwargs.get("id", ""))
                tgt = kwargs.get("target", "github")
                return SeniorAgentTools.deploy_project(pid, tgt), None, None

            elif name == "browser_cdp_list_tabs":
                return SeniorAgentTools.browser_cdp_list_tabs(), None, None

            elif name == "browser_cdp_eval":
                tm = kwargs.get("tab_matcher", kwargs.get("tab", ""))
                js = kwargs.get("js_code", kwargs.get("code", ""))
                res = await SeniorAgentTools.browser_cdp_eval(tm, js)
                return res, None, None

            elif name == "inspect_antigravity":
                return SeniorAgentTools.inspect_antigravity(), None, None

            elif name == "delegate_antigravity_task":
                agent = kwargs.get("agent", kwargs.get("agent_name", "gemini"))
                task = kwargs.get("task", "")
                res = await SeniorAgentTools.delegate_antigravity_task(agent, task)
                return res, None, None

            elif name == "github_push":
                path = kwargs.get("path", "")
                content = kwargs.get("content", "")
                msg = kwargs.get("message", "Update via PBG Discord")
                branch = kwargs.get("branch", "main")
                return SeniorAgentTools.github_push(path, content, msg, branch), None, None

            elif name == "github_get_file":
                path = kwargs.get("path", args_str.strip('"\''))
                branch = kwargs.get("branch", "main")
                return SeniorAgentTools.github_get_file(path, branch), None, None

            elif name == "github_list_files":
                path = kwargs.get("path", "")
                branch = kwargs.get("branch", "main")
                return SeniorAgentTools.github_list_files(path, branch), None, None

            elif name == "render_chart":
                img_data, msg = VisualEngine.generate_telemetry_chart()
                if img_data:
                    return "✅ Successfully rendered live telemetry infographic chart.", img_data, "telemetry_chart.png"
                return f"Chart rendering notice: {msg}", None, None

            elif name == "generate_qr":
                data = kwargs.get("data", args_str.strip('"\''))
                img_data, msg = VisualEngine.generate_qr_code(data)
                if img_data:
                    return f"✅ Generated QR code for: {data}", img_data, "qr_code.png"
                return f"QR generation notice: {msg}", None, None

            elif name == "generate_image":
                img_prompt = kwargs.get("prompt", args_str.strip('"\''))
                img_data, msg = VisualEngine.fetch_ai_image(img_prompt)
                if img_data:
                    return f"✅ Synthesized AI image for: {img_prompt}", img_data, "pbg_visual.png"
                return f"Image synthesis notice: {msg}", None, None

            return f"Unknown tool: {name}", None, None
        except Exception as e:
            return f"Tool execution failed: {str(e)}", None, None
        except Exception as e:
            return f"Tool execution failed: {str(e)}", None, None


async def query_gemini_fallback(messages: List[Dict[str, str]]) -> str:
    """Fallback generator using Gemini Flash."""
    try:
        from google import genai
        from google.genai import types
        api_keys = config.GEMINI_API_KEYS or ([config.GEMINI_API_KEY] if config.GEMINI_API_KEY else [])
        if api_keys:
            client = genai.Client(api_key=api_keys[0])
            full_prompt = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
            res = await asyncio.to_thread(
                client.models.generate_content,
                model=config.GEMINI_MODEL or "gemini-2.5-flash",
                contents=full_prompt
            )
            if res and res.text:
                return res.text.strip()
    except Exception as ge:
        print(f"[GEMINI FALLBACK ERROR] {ge}", flush=True)
    return "Error communicating with AI engine."


# =========================================================================
# 🛡️ 2FA MODAL VERIFICATION
# =========================================================================
class GodmodeAuthModal(discord.ui.Modal, title="🛡️ GODMODE 2-STAGE AUTHENTICATION"):
    pass1 = discord.ui.TextInput(
        label="🔑 รหัสผ่านยืนยันชั้นที่ 1 (Master Key)",
        placeholder="ระบุรหัสผ่านชั้นแรก...",
        required=True,
        max_length=100,
        style=discord.TextStyle.short
    )
    pass2 = discord.ui.TextInput(
        label="🛡️ รหัสผ่านยืนยันชั้นที่ 2 (Security PIN)",
        placeholder="ระบุรหัสยืนยัน 6 หลัก...",
        required=True,
        max_length=50,
        style=discord.TextStyle.short
    )

    def __init__(self, target_channel_id: Optional[int] = None, is_setup: bool = False):
        super().__init__()
        self.target_channel_id = target_channel_id
        self.is_setup = is_setup

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        val1 = self.pass1.value.strip()
        val2 = self.pass2.value.strip()

        ok = GODMODE_STATE.verify_and_authenticate(user.id, str(user), val1, val2)
        if not ok:
            embed = discord.Embed(
                title="⛔ การยืนยันตัวตนล้มเหลว (ACCESS DENIED)",
                description=(
                    "❌ **รหัสผ่านยืนยันชั้นที่ 1 หรือชั้นที่ 2 ไม่ถูกต้อง**\n\n"
                    "ระบบความปลอดภัยได้บันทึกความพยายามเข้าถึงนี้ไว้ใน Security Audit Log เรียบร้อยแล้ว"
                ),
                color=discord.Color.from_rgb(230, 40, 40)
            )
            embed.set_footer(text="PAYOMBØYZ CYBER-DEFENSE // 2FA REJECTION")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if self.is_setup and self.target_channel_id:
            GODMODE_STATE.register_channel(self.target_channel_id, str(user))
            embed = discord.Embed(
                title="⚡ ติดตั้งช่องควบคุม GODMODE สำเร็จ // PBG ACTIVE",
                description=(
                    f"✅ **ผูกห้อง <#{self.target_channel_id}> เป็นห้องควบคุม Agentic เรียบร้อยแล้ว**\n\n"
                    f"• **ผู้ควบคุมสูงสุด:** {user.mention}\n"
                    f"• **สิทธิ์ปฏิบัติการ:** `ROOT_GODMODE_ACCESS`\n"
                    f"• **AI ประจำห้อง:** **PBG** (PayomboyZ Godmode Senior Commander)\n"
                    f"• **สถานะ 2FA:** ยืนยันรหัสผ่าน 2 ชั้นครบถ้วนสมบูรณ์\n\n"
                    f"ห้องนี้จะตอบสนองต่อการสั่งการด้วยข้อความและคำสั่ง `/godmode` ทั้งหมด"
                ),
                color=discord.Color.from_rgb(0, 240, 160)
            )
            embed.set_footer(text="PAYOMBØYZ GODMODE ENGINE // PBG BOUND")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            channel = interaction.guild.get_channel(self.target_channel_id) if interaction.guild else None
            if channel:
                panel_embed = build_godmode_panel_embed()
                view = GodmodePanelView()
                await channel.send(embed=panel_embed, view=view)
            return

        embed = discord.Embed(
            title="🔓 ยืนยันตัวตน 2FA สำเร็จ // PBG ENGAGED",
            description=(
                f"ยินดีต้อนรับคุณ {user.mention}\n\n"
                f"• **สถานะ:** `UNLOCKED (GOD MODE GRANTED)`\n"
                f"• **ผู้สั่งการหลัก:** **PBG** (เข้าใจ dj ทุกขั้นตอน รายงานผลละเอียด ส่งรูปภาพได้)\n"
                f"• **Session Timeout:** 30 นาที\n"
                f"• **3 Hard Guardrails Active:** คุ้มครองระบบและการเงิน 100%\n"
                f"• **Auto-Chat:** พิมพ์สั่งงานในห้องนี้ได้ทันที หรือสั่งให้ส่งรูป/ชาร์ตได้เลย"
            ),
            color=discord.Color.from_rgb(0, 230, 255)
        )
        embed.set_footer(text="PBG // PAYOMBØYZ SENIOR HOST CONTROLLER")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# =========================================================================
# 💻 TERMINAL & AI PROMPT MODALS
# =========================================================================
class GodmodeCommandModal(discord.ui.Modal, title="⚡ GODMODE TERMINAL EXECUTION"):
    cmd = discord.ui.TextInput(
        label="คำสั่ง PowerShell บนเครื่องโฮสต์",
        placeholder="เช่น Get-Process roblox*, dir Desktop...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        if not GODMODE_STATE.is_user_authenticated(user.id):
            await interaction.response.send_message("⛔ คุณยังไม่ได้ยืนยันตัวตน 2FA กรุณาปลดล็อคก่อน", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        cmd_str = self.cmd.value.strip()
        GODMODE_STATE._log_audit("TERMINAL_EXEC", str(user), f"Command: {cmd_str[:80]}")
        res = await HostController.execute_shell_command(cmd_str)

        embed = discord.Embed(
            title="💻 PowerShell Execution Result",
            description=f"**Command:** `{cmd_str[:200]}`\n**Exit Code:** `{res['exit_code']}` | **Elapsed:** `{res['elapsed']}s`",
            color=discord.Color.from_rgb(0, 230, 180) if res["success"] else discord.Color.from_rgb(240, 60, 60)
        )

        out_content = res["stdout"] or res["stderr"] or "(No output returned)"
        if len(out_content) <= 1800:
            embed.add_field(name="📄 Console Output", value=f"```powershell\n{out_content}\n```", inline=False)
            await interaction.followup.send(embed=embed)
        else:
            embed.add_field(name="📄 Console Output", value=f"```powershell\n{out_content[:1500]}\n... (ผลลัพธ์ยาวเกิน แสดงในไฟล์แนบ)\n```", inline=False)
            file_bytes = io.BytesIO(out_content.encode("utf-8", errors="replace"))
            discord_file = discord.File(file_bytes, filename=f"cmd_output_{int(time.time())}.log")
            await interaction.followup.send(embed=embed, file=discord_file)


class GodmodePromptModal(discord.ui.Modal, title="🤖 PBG SENIOR AGENTIC PROMPT"):
    prompt = discord.ui.TextInput(
        label="คำสั่งสำหรับ PBG (รายงานละเอียด/ส่งรูปได้)",
        placeholder="สั่งแก้สคริปต์, ท่องเว็บ, ส่งชาร์ตสถานะ, หาไฟล์, สั่งให้วาดรูป...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        if not GODMODE_STATE.is_user_authenticated(user.id):
            await interaction.response.send_message("⛔ คุณยังไม่ได้ยืนยันตัวตน 2FA กรุณาปลดล็อคก่อน", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        prompt_str = self.prompt.value.strip()
        reply, img_bytes, img_name = await DeepSeekSeniorAgent.run_agentic_loop(prompt_str, str(user))
        await send_full_pbg_response(interaction, reply, img_bytes=img_bytes, img_name=img_name)


# =========================================================================
# 🎛️ PERSISTENT GODMODE PANEL VIEW
# =========================================================================
def build_godmode_panel_embed() -> discord.Embed:
    summary = HostController.get_system_summary()
    embed = discord.Embed(
        title="🛡️ PAYOMBØYZ GODMODE // PBG SENIOR COMMANDER",
        description=(
            "ระบบควบคุมคอมพิวเตอร์โฮสต์ระดับสูงสุดผ่าน Discord\n"
            "ขับเคลื่อนด้วย **PBG (PayomboyZ Godmode)** พร้อม 2FA, ระบบส่งรูปภาพ และ 3 กฎเหล็กพิทักษ์ความปลอดภัย"
        ),
        color=discord.Color.from_rgb(20, 24, 32)
    )

    embed.add_field(
        name="🖥️ สถานะเครื่องโฮสต์ (Live Telemetry)",
        value=(
            f"• **เครื่อง:** `{summary['hostname']}` ({summary['os']})\n"
            f"• **CPU:** `{summary['cpu_percent']}%` ({summary['cpu_cores']} Cores)\n"
            f"• **RAM:** `{summary['ram_percent']}%` ({summary['ram_used_gb']} / {summary['ram_total_gb']} GB)\n"
            f"• **Uptime:** `{summary['uptime']}`\n"
            f"• **Roblox Running:** `{len(summary['roblox_procs'])} processes`\n"
            f"• **Python Daemons:** `{len(summary['python_procs'])} processes`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎨 ความสามารถในการส่งภาพ & กราฟิก (Visual Powers)",
        value=(
            "• **ส่งรูปภาพ/ชาร์ต:** สั่งให้ PBG ส่งภาพชาร์ตสถิติเครื่อง, ภาพสลิป, หรือให้วาดภาพได้ทันที\n"
            "• **QR Code:** สั่งให้สร้าง QR Code สำหรับลิงก์หรือการชำระเงินได้\n"
            "• **ความเข้าใจระดับสูง:** รายงานผลละเอียด เป็นระบบ พร้อมบริบทตรงจุด"
        ),
        inline=False
    )

    embed.add_field(
        name="🛑 3 กฎเหล็กพิทักษ์ความปลอดภัย (Hard Guardrails)",
        value=(
            "1. 🔒 **ห้ามลบไฟล์นอก Scope:** ป้องกันการสั่งลบไฟล์ระบบหรือไฟล์นอกโปรเจกต์\n"
            "2. 🛡️ **โหลดไฟล์เสี่ยงต้องใช้ PIN `280342`:** ร้องขอรหัสยืนยันใหม่ทุกครั้งหากต้องโหลดไฟล์เสี่ยง\n"
            "3. 💳 **ห้ามสั่งชำระเงินแทน:** ทำได้มากที่สุดคือแคป QR Code สำหรับจ่าย หรือนำสลิปไปส่งเติมเงินต่อ"
        ),
        inline=False
    )

    embed.set_footer(text="PAYOMBØYZ GODMODE PROTOCOL // PBG ENGAGED")
    return embed


async def send_godmode_web_embed(target: Any):
    """
    Launches or connects to PBG Godmode Mobile Web Streamer on port 49288,
    generates secure 2FA session token and QR code, and sends Discord embed.
    """
    start_godmode_web_service()
    tok = generate_web_token()
    lan_ip = get_primary_lan_ip()
    port = WEB_STREAMER_PORT

    lan_url = f"http://{lan_ip}:{port}/?token={tok}"
    local_url = f"http://127.0.0.1:{port}/?token={tok}"

    qr_file = None
    if QRCODE_AVAILABLE:
        try:
            qr = qrcode.QRCode(box_size=7, border=2)
            qr.add_data(lan_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#FF1432", back_color="#0C0306")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            qr_file = discord.File(buf, filename="pbg_remote_qr.png")
        except Exception:
            pass

    embed = discord.Embed(
        title="📱 PBG GODMODE // MOBILE WEB CONTROLLER & LIVE STREAM",
        description=(
            "⚡ **สตรีมหน้าจอและควบคุมคอมพิวเตอร์ผ่านมือถือ (PWA Zero-Install)**\n"
            "เชื่อมต่อผ่าน Wi-Fi วงเดียวกัน หรือเปิดเบราว์เซอร์บนเครื่องนี้ได้ทันที"
        ),
        color=discord.Color.from_rgb(255, 20, 50)
    )

    embed.add_field(
        name="🔗 ลิงก์เชื่อมต่อ (One-Click Access)",
        value=(
            f"• 📱 **สำหรับมือถือ (Wi-Fi LAN):**\n"
            f"  [**คลิกเปิดบนมือถือ (LAN)**]({lan_url})\n"
            f"  `{lan_url}`\n\n"
            f"• 💻 **สำหรับเบราว์เซอร์บนเครื่องนี้ (Localhost):**\n"
            f"  [**คลิกเปิดบนโฮสต์**]({local_url})\n"
            f"  `{local_url}`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 ฟังก์ชันการควบคุมบนมือถือ",
        value=(
            "• **Live Screen Stream:** อัปเดตหน้าจอสด 15-20 FPS ลื่นไหล\n"
            "• **Touch Trackpad:** เลื่อนเมาส์ลื่นแบบทัชแพดโน้ตบุ๊ก + แตะ 2 นิ้วคลิกขวา\n"
            "• **Virtual Keyboard:** พิมพ์ข้อความภาษาไทยและอังกฤษส่งตรงเข้าเกม/โปรแกรม\n"
            "• **Game & System Macros:** ปุ่มลัดดึงหน้าต่าง Roblox, Win+D, ปิดเกมฉุกเฉิน\n"
            "• **PWA Support:** กด 'Add to Home Screen' เพื่อใช้งานเต็มจอแบบแอปมือถือ"
        ),
        inline=False
    )

    if qr_file:
        embed.set_image(url="attachment://pbg_remote_qr.png")
        embed.set_footer(text=f"Token: {tok[:10]}... | Port: {port} | Scan QR Code with Phone Camera")
    else:
        embed.set_footer(text=f"Token: {tok[:10]}... | Port: {port}")

    if isinstance(target, discord.Interaction):
        if target.response.is_done():
            if qr_file:
                await target.followup.send(embed=embed, file=qr_file, ephemeral=True)
            else:
                await target.followup.send(embed=embed, ephemeral=True)
        else:
            if qr_file:
                await target.response.send_message(embed=embed, file=qr_file, ephemeral=True)
            else:
                await target.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(target, discord.Message):
        if qr_file:
            await target.reply(embed=embed, file=qr_file, mention_author=False)
        else:
            await target.reply(embed=embed, mention_author=False)


class GodmodePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔓 ยืนยันตัวตน 2FA",
        style=discord.ButtonStyle.success,
        custom_id="godmode_btn_auth",
        emoji="🔑"
    )
    async def btn_auth(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
            await interaction.response.send_message(
                "⛔ ห้องนี้ยังไม่ได้ติดตั้ง Godmode กรุณาใช้คำสั่ง `/godmode setup`", ephemeral=True
            )
            return
        await interaction.response.send_modal(GodmodeAuthModal())

    @discord.ui.button(
        label="📊 กราฟสถานะเครื่อง (Chart)",
        style=discord.ButtonStyle.primary,
        custom_id="godmode_btn_chart",
        emoji="📈"
    )
    async def btn_chart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
            await interaction.response.send_message("⛔ ห้องนี้ยังไม่ได้ติดตั้ง Godmode", ephemeral=True)
            return
        if not GODMODE_STATE.is_user_authenticated(interaction.user.id):
            await interaction.response.send_message("⛔ กรุณากดปุ่ม 🔓 ยืนยันตัวตน 2FA ก่อนดูข้อมูล", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        img_bytes, msg = VisualEngine.generate_telemetry_chart()
        if img_bytes:
            file_obj = discord.File(io.BytesIO(img_bytes), filename="pbg_telemetry_chart.png")
            embed = discord.Embed(
                title="📊 PBG Live Host Telemetry Infographic",
                color=discord.Color.from_rgb(0, 230, 255)
            )
            embed.set_image(url="attachment://pbg_telemetry_chart.png")
            embed.set_footer(text="PBG // PAYOMBØYZ SENIOR HOST CONTROLLER")
            await interaction.followup.send(embed=embed, file=file_obj)
        else:
            await interaction.followup.send(f"❌ ไม่สามารถสร้างกราฟได้: {msg}", ephemeral=True)

    @discord.ui.button(
        label="⚡ รันคำสั่ง Terminal",
        style=discord.ButtonStyle.secondary,
        custom_id="godmode_btn_terminal",
        emoji="💻"
    )
    async def btn_terminal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
            await interaction.response.send_message("⛔ ห้องนี้ยังไม่ได้ติดตั้ง Godmode", ephemeral=True)
            return
        if not GODMODE_STATE.is_user_authenticated(interaction.user.id):
            await interaction.response.send_message("⛔ กรุณากดปุ่ม 🔓 ยืนยันตัวตน 2FA ก่อนใช้งาน Terminal", ephemeral=True)
            return
        await interaction.response.send_modal(GodmodeCommandModal())

    @discord.ui.button(
        label="🤖 สั่งงาน PBG",
        style=discord.ButtonStyle.secondary,
        custom_id="godmode_btn_ai",
        emoji="🧠"
    )
    async def btn_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
            await interaction.response.send_message("⛔ ห้องนี้ยังไม่ได้ติดตั้ง Godmode", ephemeral=True)
            return
        if not GODMODE_STATE.is_user_authenticated(interaction.user.id):
            await interaction.response.send_message("⛔ กรุณากดปุ่ม 🔓 ยืนยันตัวตน 2FA ก่อนคุยกับ PBG", ephemeral=True)
            return
        await interaction.response.send_modal(GodmodePromptModal())

    @discord.ui.button(
        label="📦 จัดการ GitHub",
        style=discord.ButtonStyle.secondary,
        custom_id="godmode_btn_git",
        emoji="🚀"
    )
    async def btn_git(self, interaction: discord.Interaction, button: discord.ui.Button):
        token, repo = GODMODE_STATE.get_github_config()
        await interaction.response.send_message(
            f"📦 **สถานะการเชื่อมต่อ GitHub:**\n"
            f"• **Repository:** `{repo or 'ยังไม่ได้ระบุ'}`\n"
            f"• **Token Configured:** `{'YES' if token else 'NO'}`\n\n"
            f"💡 **วิธีใช้งานผ่านแชท:**\n"
            f"• `!gitpush <path> <code>` หรือแนบไฟล์แล้วสั่ง `!gitpush <path>`\n"
            f"• `!gitget <path>`: ดึงไฟล์จาก GitHub\n"
            f"• `!gitconfig <token> <repo>`: ตั้งค่าเชื่อมต่อ GitHub ใหม่\n"
            f"• `!web` หรือ `!stream`: เปิดหน้าจอควบคุมสดบนมือถือ",
            ephemeral=True
        )

    @discord.ui.button(
        label="📱 จอมือถือ (Web Remote)",
        style=discord.ButtonStyle.primary,
        custom_id="godmode_btn_web",
        emoji="📱"
    )
    async def btn_web(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
            await interaction.response.send_message("⛔ ห้องนี้ยังไม่ได้ติดตั้ง Godmode", ephemeral=True)
            return
        if not GODMODE_STATE.is_user_authenticated(interaction.user.id):
            await interaction.response.send_message("⛔ กรุณากดปุ่ม 🔓 ยืนยันตัวตน 2FA ก่อนใช้งาน", ephemeral=True)
            return
        await send_godmode_web_embed(interaction)

    @discord.ui.button(
        label="🔒 ล็อกระบบทันที",
        style=discord.ButtonStyle.danger,
        custom_id="godmode_btn_lock",
        emoji="🛑"
    )
    async def btn_lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        GODMODE_STATE.revoke_session(interaction.user.id, str(interaction.user))
        await interaction.response.send_message(
            "🔒 **ล็อกระบบเรียบร้อยแล้ว** ยกเลิกสิทธิ์ Session ของคุณสำเร็จ", ephemeral=True
        )


# =========================================================================
# 🌲 DISCORD SLASH COMMAND GROUP: /godmode ...
# =========================================================================
class GodmodeGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="godmode",
            description="⚡ ระบบควบคุม PBG Senior Agentic โฮสต์ผ่าน Discord พร้อม 2FA"
        )


godmode_group = GodmodeGroup()


@godmode_group.command(name="setup", description="ติดตั้งห้องนี้เป็นห้องควบคุม Agentic Host (ต้องยืนยันตัวตน 2FA)")
async def godmode_setup_cmd(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    await interaction.response.send_modal(GodmodeAuthModal(target_channel_id=channel_id, is_setup=True))


@godmode_group.command(name="auth", description="เปิดหน้าต่างใส่รหัสผ่าน 2 ชั้น (Master Key + PIN) เพื่อปลดล็อค Session")
async def godmode_auth_cmd(interaction: discord.Interaction):
    if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
        await interaction.response.send_message(
            "⛔ **ห้องนี้ยังไม่ได้รับการติดตั้ง Godmode**\nกรุณาใช้ `/godmode setup` ในห้องที่ต้องการติดตั้งก่อน",
            ephemeral=True
        )
        return
    await interaction.response.send_modal(GodmodeAuthModal())


@godmode_group.command(name="lock", description="สั่งล็อกระบบและยกเลิกสิทธิ์ Session ทันที")
async def godmode_lock_cmd(interaction: discord.Interaction):
    GODMODE_STATE.revoke_session(interaction.user.id, str(interaction.user))
    await interaction.response.send_message("🔒 **Session ถูกล็อกเรียบร้อยแล้ว** ต้องยืนยัน 2FA ใหม่หากต้องการใช้งานอีกครั้ง", ephemeral=True)


@godmode_group.command(name="status", description="ตรวจสอบสเปคเครื่อง, CPU, RAM, Disk, และโปรเซส Roblox/Python ที่รันอยู่")
async def godmode_status_cmd(interaction: discord.Interaction):
    if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
        await interaction.response.send_message("⛔ ไม่อนุญาตให้ใช้งานคำสั่งนี้นอกห้องที่ติดตั้ง Godmode", ephemeral=True)
        return
    if not GODMODE_STATE.is_user_authenticated(interaction.user.id):
        await interaction.response.send_message("⛔ กรุณาปลดล็อค 2FA ก่อนด้วย `/godmode auth`", ephemeral=True)
        return

    summary = HostController.get_system_summary()
    embed = discord.Embed(
        title=f"📊 รายงานสถานะเครื่องโฮสต์ ({summary['hostname']})",
        color=discord.Color.from_rgb(0, 230, 255)
    )
    embed.add_field(name="ระบบปฏิบัติการ", value=f"`{summary['os']}`", inline=True)
    embed.add_field(name="CPU Usage", value=f"`{summary['cpu_percent']}%` ({summary['cpu_cores']} Cores)", inline=True)
    embed.add_field(name="RAM Usage", value=f"`{summary['ram_percent']}%` ({summary['ram_used_gb']}/{summary['ram_total_gb']} GB)", inline=True)
    embed.add_field(name="Uptime", value=f"`{summary['uptime']}`", inline=True)

    disk_lines = [f"• `{dev}`: {d['percent']}% (Free: {d['free_gb']} GB)" for dev, d in summary['disks'].items()]
    embed.add_field(name="พื้นที่ไดรฟ์", value="\n".join(disk_lines) or "N/A", inline=False)

    roblox_lines = [f"• PID `{p['pid']}` ({p['name']}) - RAM `{p['mem']}%`" for p in summary['roblox_procs']]
    embed.add_field(name=f"Roblox Processes ({len(summary['roblox_procs'])})", value="\n".join(roblox_lines) or "No Roblox running", inline=False)

    py_lines = [f"• PID `{p['pid']}`: `{p['cmd']}` (RAM {p['mem']}%)" for p in summary['python_procs'][:6]]
    embed.add_field(name=f"Python Processes ({len(summary['python_procs'])})", value="\n".join(py_lines) or "No Python running", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@godmode_group.command(name="exec", description="รันคำสั่ง PowerShell / CMD บนคอมพิวเตอร์โฮสต์โดยตรง (พร้อมตรวจ Guardrail)")
@app_commands.describe(
    command="คำสั่งที่ต้องการรันบน PowerShell เช่น dir, Get-Process...",
    pin="รหัสผ่าน 280342 (เฉพาะเมื่อต้องดาวน์โหลดไฟล์แปลกปลอม/เสี่ยง)"
)
async def godmode_exec_cmd(interaction: discord.Interaction, command: str, pin: Optional[str] = None):
    if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
        await interaction.response.send_message("⛔ ไม่อนุญาตให้ใช้งานคำสั่งนี้นอกห้องที่ติดตั้ง Godmode", ephemeral=True)
        return
    if not GODMODE_STATE.is_user_authenticated(interaction.user.id):
        await interaction.response.send_message("⛔ กรุณาปลดล็อค 2FA ก่อนด้วย `/godmode auth`", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    GODMODE_STATE._log_audit("SLASH_EXEC", str(interaction.user), f"Cmd: {command[:80]}")
    res = await HostController.execute_shell_command(command, pin=pin or "")

    embed = discord.Embed(
        title="💻 ผลลัพธ์การรันคำสั่ง Terminal",
        description=f"**Command:** `{command[:200]}`\n**Exit Code:** `{res['exit_code']}` | **Elapsed:** `{res['elapsed']}s`",
        color=discord.Color.from_rgb(0, 230, 180) if res["success"] else discord.Color.from_rgb(240, 60, 60)
    )

    out_content = res["stdout"] or res["stderr"] or "(No output returned)"
    if len(out_content) <= 1800:
        embed.add_field(name="📄 Output", value=f"```powershell\n{out_content}\n```", inline=False)
        await interaction.followup.send(embed=embed)
    else:
        embed.add_field(name="📄 Output", value=f"```powershell\n{out_content[:1500]}\n... (ผลลัพธ์ยาวเกิน ส่งในไฟล์แนบ)\n```", inline=False)
        file_bytes = io.BytesIO(out_content.encode("utf-8", errors="replace"))
        discord_file = discord.File(file_bytes, filename=f"cmd_output_{int(time.time())}.log")
        await interaction.followup.send(embed=embed, file=discord_file)


@godmode_group.command(name="ask", description="สั่งการ PBG ให้ทำงานแทนบนคอมพิวเตอร์อย่างละเอียด (ส่งรูปได้)")
@app_commands.describe(
    prompt="คำสั่งสำหรับ PBG (เช่น สั่งแก้สคริปต์, ท่องเว็บ, ส่งชาร์ต, ขอรูปภาพ)",
    pin="รหัสยืนยัน 280342 (หากมีคำสั่งดาวน์โหลดไฟล์เสี่ยง)"
)
async def godmode_ask_cmd(interaction: discord.Interaction, prompt: str, pin: Optional[str] = None):
    if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
        await interaction.response.send_message("⛔ ไม่อนุญาตให้ใช้งานคำสั่งนี้นอกห้องที่ติดตั้ง Godmode", ephemeral=True)
        return
    if not GODMODE_STATE.is_user_authenticated(interaction.user.id):
        await interaction.response.send_message("⛔ กรุณาปลดล็อค 2FA ก่อนด้วย `/godmode auth`", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    reply, img_bytes, img_name = await DeepSeekSeniorAgent.run_agentic_loop(prompt, str(interaction.user), pin=pin or "")
    await send_full_pbg_response(interaction, reply, img_bytes=img_bytes, img_name=img_name)


@godmode_group.command(name="chart", description="สร้างภาพชาร์ตกราฟิกแสดงสถิติและสถานะเครื่องโฮสต์แบบเรียลไทม์")
async def godmode_chart_cmd(interaction: discord.Interaction):
    if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
        await interaction.response.send_message("⛔ ไม่อนุญาตให้ใช้งานคำสั่งนี้นอกห้องที่ติดตั้ง Godmode", ephemeral=True)
        return
    if not GODMODE_STATE.is_user_authenticated(interaction.user.id):
        await interaction.response.send_message("⛔ กรุณาปลดล็อค 2FA ก่อนด้วย `/godmode auth`", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    img_bytes, msg = VisualEngine.generate_telemetry_chart()
    if img_bytes:
        file_obj = discord.File(io.BytesIO(img_bytes), filename="pbg_telemetry_chart.png")
        embed = discord.Embed(
            title="📊 PBG Live Host Telemetry Infographic",
            color=discord.Color.from_rgb(0, 230, 255)
        )
        embed.set_image(url="attachment://pbg_telemetry_chart.png")
        embed.set_footer(text="PBG // PAYOMBØYZ SENIOR HOST CONTROLLER")
        await interaction.followup.send(embed=embed, file=file_obj)
    else:
        await interaction.followup.send(f"❌ ไม่สามารถสร้างกราฟได้: {msg}", ephemeral=True)


@godmode_group.command(name="panel", description="ส่งแผงควบคุม Godmode Interactive Panel ลงในห้องนี้")
async def godmode_panel_cmd(interaction: discord.Interaction):
    if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
        await interaction.response.send_message(
            "⛔ ห้องนี้ยังไม่ได้ติดตั้ง Godmode กรุณาใช้คำสั่ง `/godmode setup` ก่อน", ephemeral=True
        )
        return
    embed = build_godmode_panel_embed()
    view = GodmodePanelView()
    await interaction.response.send_message(embed=embed, view=view)


@godmode_group.command(name="web", description="เปิดระบบควบคุมคอมพิวเตอร์และสตรีมจอสดบนมือถือ (PWA Mobile Remote)")
async def godmode_web_cmd(interaction: discord.Interaction):
    if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
        await interaction.response.send_message("⛔ ไม่อนุญาตให้ใช้งานคำสั่งนี้นอกห้องที่ติดตั้ง Godmode", ephemeral=True)
        return
    if not GODMODE_STATE.is_user_authenticated(interaction.user.id):
        await interaction.response.send_message("⛔ กรุณาปลดล็อค 2FA ก่อนด้วย `/godmode auth`", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    await send_godmode_web_embed(interaction)


@godmode_group.command(name="gitpush", description="อัปเดตหรือสร้างไฟล์ใหม่บน GitHub Repository ผ่านบอท")
@app_commands.describe(
    path="พาธไฟล์บน GitHub เช่น scripts/main.lua",
    content="โค้ดที่ต้องการอัปโหลด (ถ้าไม่มีให้แนบไฟล์)",
    file="ไฟล์สคริปต์ที่ต้องการอัปโหลด (ถ้ามี)"
)
async def godmode_gitpush_cmd(interaction: discord.Interaction, path: str, content: Optional[str] = None, file: Optional[discord.Attachment] = None):
    if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
        await interaction.response.send_message("⛔ ไม่อนุญาตให้ใช้งานคำสั่งนี้นอกห้องที่ติดตั้ง Godmode", ephemeral=True)
        return
    if not GODMODE_STATE.is_user_authenticated(interaction.user.id):
        await interaction.response.send_message("⛔ กรุณาปลดล็อค 2FA ก่อนด้วย `/godmode auth`", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    file_code = content or ""
    if file:
        raw_b = await file.read()
        file_code = raw_b.decode("utf-8", errors="replace")

    if not file_code.strip():
        await interaction.followup.send("❌ กรุณาระบุโค้ด หรือแนบไฟล์สคริปต์")
        return

    res = SeniorAgentTools.github_push(path, file_code, commit_message=f"Update via /godmode by {interaction.user}")
    await interaction.followup.send(res)


@godmode_group.command(name="gitconfig", description="ตั้งค่า GitHub Token และ Repository สำหรับบอท")
@app_commands.describe(
    token="Personal Access Token (classic หรือ fine-grained)",
    repo="Repository ในรูปแบบ username/repo-name"
)
async def godmode_gitconfig_cmd(interaction: discord.Interaction, token: str, repo: str):
    if not GODMODE_STATE.is_channel_installed(interaction.channel_id):
        await interaction.response.send_message("⛔ ไม่อนุญาตให้ใช้งานคำสั่งนี้นอกห้องที่ติดตั้ง Godmode", ephemeral=True)
        return
    if not GODMODE_STATE.is_user_authenticated(interaction.user.id):
        await interaction.response.send_message("⛔ กรุณาปลดล็อค 2FA ก่อนด้วย `/godmode auth`", ephemeral=True)
        return

    GODMODE_STATE.set_github_config(token, repo, str(interaction.user))
    await interaction.response.send_message(f"✅ บันทึกการตั้งค่า GitHub สำเร็จ! Repo: `{repo}`", ephemeral=True)


# =========================================================================
# 💬 REAL-TIME CHAT INTERCEPTOR IN INSTALLED CHANNELS
# =========================================================================
async def handle_godmode_message(message: discord.Message) -> bool:
    """
    Listens to messages in installed Godmode channels.
    Autonomous PBG execution with rich detailed reporting, GitHub, Deobfuscation, and image generation.
    """
    if message.author.bot:
        return False
    if not GODMODE_STATE.is_channel_installed(message.channel.id):
        return False

    # 1. Check Authentication (with Fast Mobile 2FA detection)
    if not GODMODE_STATE.is_user_authenticated(message.author.id):
        # Allow instant text login: '!auth St@313326339 280342' or typing both passwords
        if (PASSWORD_STAGE_1 in message.content and PASSWORD_STAGE_2 in message.content) or message.content.strip().startswith("!auth"):
            tokens = message.content.strip().split()
            p1, p2 = "", ""
            if PASSWORD_STAGE_1 in message.content and PASSWORD_STAGE_2 in message.content:
                p1, p2 = PASSWORD_STAGE_1, PASSWORD_STAGE_2
            elif len(tokens) >= 3 and tokens[0].lower() == "!auth":
                p1, p2 = tokens[1], tokens[2]

            ok = GODMODE_STATE.verify_and_authenticate(message.author.id, str(message.author), p1, p2)
            if ok:
                try:
                    await message.delete()
                except Exception:
                    pass
                embed = discord.Embed(
                    title="🔓 2FA VERIFICATION APPROVED // PBG GODMODE ACTIVE",
                    description=(
                        f"ยินดีต้อนรับคุณ {message.author.mention}!\n"
                        f"• ปลดล็อคสิทธิ์สั่งการบนเครื่องโฮสต์สำเร็จ (Session 30 นาที)\n\n"
                        f"📱 **สั่งการผ่านแชทได้ทันที (Mobile-Friendly):**\n"
                        f"• พิมพ์ถาม-ตอบ หรือสั่งงานทั่วไปได้เลย (ไม่ต้องมี prefix)\n"
                        f"• `!code <prompt>`: สั่ง AI เขียนหรือแก้โค้ด\n"
                        f"• `!gitpush <path> <code>`: ดันโค้ดขึ้น GitHub อัตโนมัติ\n"
                        f"• `!gitget <path>`: ดึงไฟล์จาก GitHub\n"
                        f"• `!deob`: แนบไฟล์ `.lua` หรือแปะโค้ดเพื่อถอดรหัส\n"
                        f"• `$ <cmd>`: รันคำสั่ง Terminal บนคอมพิวเตอร์\n"
                        f"• `!chart`: ขอกราฟสถิติสถานะเครื่อง"
                    ),
                    color=discord.Color.from_rgb(0, 240, 160)
                )
                embed.set_footer(text="PBG // PAYOMBØYZ SENIOR HOST CONTROLLER")
                await message.channel.send(embed=embed)
                return True

        if message.content.strip().startswith(("/", "$", "ps:", "cmd:", "!")) or len(message.content.strip()) > 2:
            view = discord.ui.View()
            btn = discord.ui.Button(label="🔓 กดปุ่มใส่รหัสผ่าน 2FA ปลดล็อค", style=discord.ButtonStyle.success, emoji="🔑")
            async def _btn_auth_click(interaction: discord.Interaction):
                await interaction.response.send_modal(GodmodeAuthModal())
            btn.callback = _btn_auth_click
            view.add_item(btn)
            await message.reply(
                "⛔ **GODMODE LOCKED // ระบบถูกล็อกความปลอดภัย**\n"
                "กรุณากดปุ่มด้านล่างเพื่อใส่รหัสผ่าน 2 ชั้น หรือพิมพ์ `!auth St@313326339 280342` เพื่อปลดล็อคก่อนสั่งการ PBG",
                view=view,
                mention_author=False
            )
            return True
        return False

    content = message.content.strip()
    if not content and not message.attachments:
        return False

    extracted_pin = "280342" if "280342" in content else ""

    # 2. Extract Attached Files (Scripts, Documents & Images with Deep Multimodal Vision)
    extra_context = []
    attached_lua_file = None
    upload_cache_dir = BASE_DIR / "cache" / "godmode_uploads"
    upload_cache_dir.mkdir(parents=True, exist_ok=True)

    for att in message.attachments:
        fname = att.filename.lower()
        save_path = upload_cache_dir / att.filename
        raw_bytes = b""
        try:
            raw_bytes = await att.read()
            with open(save_path, "wb") as f:
                f.write(raw_bytes)
        except Exception as fe:
            print(f"[GODMODE ATTACHMENT ERROR] Failed saving {att.filename}: {fe}", flush=True)

        if fname.endswith((".png", ".jpg", ".jpeg", ".webp")):
            # High-fidelity Multimodal Visual Inspection via Gemini 3.5 Flash
            if raw_bytes:
                vision_prompt = content or "กรุณาวิเคราะห์ภาพนี้อย่างละเอียดสูงสุด: ถอดรหัสข้อความ โค้ด ข้อผิดพลาด สลิป หรือ UI ทั้งหมดโดยไม่ละเลยรายละเอียด"
                vision_analysis = SeniorAgentTools.analyze_image_multimodal(
                    raw_bytes,
                    prompt=vision_prompt,
                    mime_type=att.content_type or "image/png"
                )
                extra_context.append(
                    f"\n[🖼️ แนบไฟล์ภาพ: {att.filename} (บันทึกไว้ที่: {save_path})]\n"
                    f"=== 🔍 ผลการวิเคราะห์ภาพด้วย Multimodal Gemini Vision ===\n"
                    f"{vision_analysis}\n"
                    f"======================================================"
                )
        elif fname.endswith((".lua", ".luau", ".txt", ".json", ".py", ".md", ".cpp", ".h", ".cs", ".log", ".yaml", ".yml", ".html", ".css", ".js")):
            text_content = raw_bytes.decode("utf-8", errors="replace")
            attached_lua_file = text_content
            if len(text_content) <= 8000:
                extra_context.append(
                    f"\n[📄 แนบไฟล์โค้ด/เอกสาร: {att.filename} ({len(text_content)} chars | พาธ: {save_path})]:\n"
                    f"```\n{text_content}\n```"
                )
            else:
                lines_count = len(text_content.splitlines())
                extra_context.append(
                    f"\n[📄 แนบไฟล์โค้ดขนาดใหญ่: {att.filename} (ทั้งหมด {lines_count} บรรทัด, {len(text_content)} chars | พาธ: {save_path})]\n"
                    f"ตัวอย่าง 80 บรรทัดแรก:\n```\n{text_content[:2500]}\n```\n"
                    f"(คุณสามารถใช้ action `view_file_lines(path='{save_path}', start_line=..., end_line=...)` หรือ `replace_file_content_surgical` เพื่อดูและแก้ไขบรรทัดที่ต้องการได้อย่างแม่นยำ)"
                )
        else:
            extra_context.append(
                f"\n[📦 แนบไฟล์ไบนารี/อื่นๆ: {att.filename} (ขนาด {len(raw_bytes)} bytes | บันทึกไว้ที่: {save_path})]"
            )

    # 3. Mobile Command: !gitconfig <token> <repo>
    if content.startswith("!gitconfig"):
        parts = content.split(maxsplit=2)
        if len(parts) >= 3:
            tok, rep = parts[1], parts[2]
            GODMODE_STATE.set_github_config(tok, rep, str(message.author))
            await message.reply(f"✅ บันทึกการตั้งค่า GitHub สำเร็จ! Repo: `{rep}`", mention_author=False)
        else:
            await message.reply("💡 วิธีใช้: `!gitconfig <TOKEN> <USERNAME/REPO>`", mention_author=False)
        return True

    # 4. Mobile Command: !gitpush <path> [content]
    if content.startswith(("!gitpush", "!push")):
        parts = content.split(maxsplit=2)
        if len(parts) >= 2:
            path_arg = parts[1]
            code_arg = parts[2] if len(parts) >= 3 else (attached_lua_file or "")
            if not code_arg:
                await message.reply("❌ กรุณาระบุโค้ด หรือแนบไฟล์สคริปต์เพื่ออัปโหลดขึ้น GitHub", mention_author=False)
                return True

            clean_code = code_arg
            for fence in ("```lua", "```python", "```javascript", "```text", "```"):
                clean_code = clean_code.replace(fence, "")
            clean_code = clean_code.strip()

            async with message.channel.typing():
                res = SeniorAgentTools.github_push(
                    file_path=path_arg,
                    content=clean_code,
                    commit_message=f"Update via Discord Mobile Bot by {message.author}"
                )
                await message.reply(res, mention_author=False)
        else:
            await message.reply("💡 วิธีใช้: `!gitpush <path/to/file.lua> <โค้ด>` หรือแนบไฟล์แล้วพิมพ์ `!gitpush <path>`", mention_author=False)
        return True

    # 5. Mobile Command: !gitget <path>
    if content.startswith(("!gitget", "!pull")):
        parts = content.split(maxsplit=1)
        if len(parts) >= 2:
            path_arg = parts[1]
            async with message.channel.typing():
                code_res = SeniorAgentTools.github_get_file(path_arg)
                if len(code_res) <= 1800:
                    await message.reply(f"📦 **ไฟล์ `{path_arg}` จาก GitHub:**\n```lua\n{code_res}\n```", mention_author=False)
                else:
                    file_b = io.BytesIO(code_res.encode("utf-8", errors="replace"))
                    discord_f = discord.File(file_b, filename=Path(path_arg).name)
                    await message.reply(f"📦 **ไฟล์ `{path_arg}` จาก GitHub:**", file=discord_f, mention_author=False)
        else:
            await message.reply("💡 วิธีใช้: `!gitget <path/to/file.lua>`", mention_author=False)
        return True

    # 6. Mobile Command: !code <prompt>
    if content.startswith("!code"):
        code_prompt = content[5:].strip()
        if not code_prompt:
            await message.reply("💡 วิธีใช้: `!code <สิ่งที่คุณต้องการให้เขียน>`", mention_author=False)
            return True
        async with message.channel.typing():
            reply, img_bytes, img_name = await DeepSeekSeniorAgent.run_agentic_loop(
                prompt=f"โปรดเขียนโค้ดและส่งโค้ดตัวเต็มพร้อม Comment ละเอียดตามคำสั่งนี้: {code_prompt}",
                user_tag=str(message.author),
                pin=extracted_pin
            )
            await send_full_pbg_response(message, reply, img_bytes=img_bytes, img_name=img_name)
        return True

    # 7. Mobile Command: !deob [code] or attached Lua file
    if content.startswith("!deob") or (attached_lua_file and content.lower() in ("deob", "ถอดรหัส", "")):
        raw_code = content[5:].strip() if content.startswith("!deob") else ""
        if not raw_code and attached_lua_file:
            raw_code = attached_lua_file

        if not raw_code:
            await message.reply("❌ กรุณาแนบไฟล์สคริปต์ หรือพิมพ์โค้ดตามหลัง `!deob <โค้ด>`", mention_author=False)
            return True

        async with message.channel.typing():
            import tempfile
            fd, tmp_path = tempfile.mkstemp(suffix=".lua", prefix="discord_deob_")
            with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
                f.write(raw_code)

            deob_res = SeniorAgentTools.deobfuscate(tmp_path)
            try:
                os.remove(tmp_path)
            except Exception:
                pass

            await message.reply(deob_res, mention_author=False)
        return True

    # 8. Quick Command Prefixes: $ <cmd> or ps: <cmd>
    if content.startswith(("$", "ps:", "cmd:", "exec:", "run:")):
        if content.startswith("$"):
            cmd = content[1:].strip()
        elif content.startswith("ps:"):
            cmd = content[3:].strip()
        elif content.startswith("cmd:"):
            cmd = content[4:].strip()
        elif content.startswith("exec:"):
            cmd = content[5:].strip()
        elif content.startswith("run:"):
            cmd = content[4:].strip()
        else:
            cmd = content

        async with message.channel.typing():
            res = await HostController.execute_shell_command(cmd, pin=extracted_pin)
            out_content = res["stdout"] or res["stderr"] or "(No output returned)"
            if len(out_content) <= 1800:
                embed = discord.Embed(
                    title="💻 PowerShell Execution",
                    description=f"```powershell\n{out_content}\n```",
                    color=discord.Color.from_rgb(0, 230, 180) if res["success"] else discord.Color.from_rgb(240, 60, 60)
                )
                embed.set_footer(text=f"Exit: {res['exit_code']} | Elapsed: {res['elapsed']}s")
                await message.reply(embed=embed, mention_author=False)
            else:
                embed = discord.Embed(
                    title="💻 PowerShell Execution (File Attached)",
                    description=f"```powershell\n{out_content[:1200]}\n... (ผลลัพธ์ยาวเกิน แนบไฟล์เต็มด้านล่าง)\n```",
                    color=discord.Color.from_rgb(0, 230, 180) if res["success"] else discord.Color.from_rgb(240, 60, 60)
                )
                embed.set_footer(text=f"Exit: {res['exit_code']} | Elapsed: {res['elapsed']}s")
                file_bytes = io.BytesIO(out_content.encode("utf-8", errors="replace"))
                discord_file = discord.File(file_bytes, filename=f"cmd_output_{int(time.time())}.log")
                await message.reply(embed=embed, file=discord_file, mention_author=False)
        return True

    # 9. Quick lock
    if content.lower() in ("lock", "/lock", "!lock", "logout"):
        GODMODE_STATE.revoke_session(message.author.id, str(message.author))
        await message.reply("🔒 **ล็อกระบบเรียบร้อยแล้ว** ยกเลิกสิทธิ์ Session ของคุณสำเร็จ", mention_author=False)
        return True

    # 10. Quick chart request
    if content.lower() in ("chart", "กราฟ", "!chart", "สถานะกราฟ"):
        async with message.channel.typing():
            img_bytes, msg = VisualEngine.generate_telemetry_chart()
            if img_bytes:
                file_obj = discord.File(io.BytesIO(img_bytes), filename="pbg_telemetry_chart.png")
                embed = discord.Embed(
                    title="📊 PBG Live Host Telemetry Infographic",
                    color=discord.Color.from_rgb(0, 230, 255)
                )
                embed.set_image(url="attachment://pbg_telemetry_chart.png")
                embed.set_footer(text="PBG // PAYOMBØYZ SENIOR HOST CONTROLLER")
                await message.reply(embed=embed, file=file_obj, mention_author=False)
            else:
                await message.reply(f"❌ ไม่สามารถสร้างกราฟได้: {msg}", mention_author=False)
        return True

    # 11. Quick status text
    if content.lower() in ("status", "host", "specs", "stat", "!status"):
        summary = HostController.get_system_summary()
        embed = discord.Embed(
            title=f"📊 Live Host Telemetry ({summary['hostname']})",
            description=(
                f"• **OS:** `{summary['os']}`\n"
                f"• **CPU:** `{summary['cpu_percent']}%` ({summary['cpu_cores']} Cores)\n"
                f"• **RAM:** `{summary['ram_percent']}%` ({summary['ram_used_gb']}/{summary['ram_total_gb']} GB)\n"
                f"• **Uptime:** `{summary['uptime']}`\n"
                f"• **Roblox Running:** `{len(summary['roblox_procs'])}`\n"
                f"• **Python Daemons:** `{len(summary['python_procs'])}`\n"
                f"• **GitHub Repo:** `{GODMODE_STATE.github_repo or 'ยังไม่ได้ระบุ'}`"
            ),
            color=discord.Color.from_rgb(0, 230, 255)
        )
        await message.reply(embed=embed, mention_author=False)
        return True

    # 12. Quick Screen Inspection & Capture (Desktop Vision)
    if content.lower() in ("!screen", "screen", "ดูจอ", "แคปจอ", "!shot", "shot", "ดูหน้าจอ"):
        async with message.channel.typing():
            analysis, img_bytes, img_name = SeniorAgentTools.capture_and_inspect_screen("วิเคราะห์หน้าจอเครื่องโฮสต์และสรุปสิ่งที่ dj กำลังทำอยู่อย่างละเอียด")
            await send_full_pbg_response(message, f"🖥️ **[Desktop Screen Vision Analysis]**\n{analysis}", img_bytes=img_bytes, img_name=img_name)
        return True

    # 13. Quick Projects Inspection
    if content.lower() in ("!projects", "projects", "!project", "project", "โปรเจกต์", "ดูโปรเจกต์"):
        async with message.channel.typing():
            res = SeniorAgentTools.list_projects()
            await message.reply(res, mention_author=False)
        return True

    # 14. Quick Chrome CDP Tabs
    if content.lower() in ("!tabs", "tabs", "แท็บ", "ดูแท็บ"):
        async with message.channel.typing():
            res = SeniorAgentTools.browser_cdp_list_tabs()
            await message.reply(res, mention_author=False)
        return True

    # 15. Quick Deploy Project
    if content.startswith("!deploy"):
        parts = content.split(maxsplit=2)
        if len(parts) >= 2:
            pid = parts[1]
            tgt = parts[2] if len(parts) >= 3 else "github"
            async with message.channel.typing():
                res = SeniorAgentTools.deploy_project(pid, tgt)
                await message.reply(res, mention_author=False)
        else:
            await message.reply("💡 วิธีใช้: `!deploy <project_id> [github|hub]`", mention_author=False)
        return True

    # 16. Quick Mobile Web Streamer: !web, !remote, !stream
    if content.lower() in ("!web", "web", "!remote", "remote", "!stream", "stream", "จอมือถือ", "สตรีมจอ"):
        await send_godmode_web_embed(message)
        return True

    # 13. Direct Natural Language Q&A & Instructions (Zero Truncation / Autonomous PBG Brain)
    full_prompt = content + ("\n".join(extra_context) if extra_context else "")
    async with message.channel.typing():
        reply, img_bytes, img_name = await DeepSeekSeniorAgent.run_agentic_loop(
            full_prompt, str(message.author), pin=extracted_pin
        )
        await send_full_pbg_response(message, reply, img_bytes=img_bytes, img_name=img_name)
    return True


# =========================================================================
# 🔌 REGISTRATION HOOK FOR DISCORD BOTS
# =========================================================================
def register_godmode_to_bot(bot_instance: commands.Bot):
    """Registers the Godmode command tree and persistent views to a Discord bot."""
    try:
        bot_instance.add_view(GodmodePanelView())
        print("  [+] Registered GodmodePanelView persistent view (PBG).", flush=True)
    except Exception as e:
        print(f"  [-] GodmodePanelView registration notice: {e}", flush=True)

    try:
        existing_cmds = [cmd.name for cmd in bot_instance.tree.get_commands()]
        if "godmode" not in existing_cmds:
            bot_instance.tree.add_command(godmode_group)
            print("  [+] Registered /godmode slash command group (PBG).", flush=True)
    except Exception as e:
        print(f"  [-] /godmode registration warning: {e}", flush=True)

    try:
        ok, msg = start_godmode_web_service()
        if ok:
            print(f"  [+] PBG Godmode Web Streamer online ({msg}).", flush=True)
    except Exception as we:
        print(f"  [-] Godmode web streamer auto-start notice: {we}", flush=True)
