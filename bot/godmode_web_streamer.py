# -*- coding: utf-8 -*-
"""
====================================================================
  ⚡ PAYOMBØYZ GODMODE — MOBILE WEB CONTROLLER & LIVE STREAM SERVICE
====================================================================
Blueprint Spec:
  [📱 Mobile Phone / Remote Browser]
    ├── Glassmorphic Web App / PWA
    ├── Live Screen Canvas (15-20 FPS WebP / JPEG)
    └── ActionPad (Touch Trackpad + Virtual Keyboard + Macro Buttons)
  [⚡ Host Server / Port 49288]
    ├── FastAPI WebSocket Streamer
    ├── AuthGuard (PBG 2FA Auth & Session Token)
    └── ActionDispatcher (Event Pipeline -> Native Drivers)
  [💻 Native Core + PBG Engine]
    ├── Native Input Driver (ctypes user32 & pyautogui)
    ├── ScreenGrab (MSS / GDI Desktop Duplication)
    └── Godmode Worker Integration
====================================================================
"""

import os
import io
import sys
import time
import json
import base64
import socket
import asyncio
import secrets
import threading
from typing import Set, Dict, Any, Optional, Tuple
from pathlib import Path

import psutil
try:
    import mss
    MSS_AVAILABLE = True
except Exception:
    mss = None
    MSS_AVAILABLE = False
try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    Image = None
    PIL_AVAILABLE = False

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.005
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False

import ctypes
from ctypes import wintypes

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from fastapi.responses import HTMLResponse, Response, JSONResponse
import uvicorn

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# =========================================================================
# 🛡️ AUTHENTICATION & SESSION MANAGEMENT
# =========================================================================
DEFAULT_PORT = 49288
SESSION_TOKENS: Dict[str, float] = {}  # token -> creation timestamp
MASTER_PASSWORDS = {"St@313326339", "280342"}
TOKEN_TTL_SECONDS = 86400  # 24 hours per session


def generate_web_token() -> str:
    """Generates a cryptographically strong 32-char session token."""
    tok = secrets.token_urlsafe(24)
    SESSION_TOKENS[tok] = time.time()
    return tok


def is_token_valid(token: Optional[str]) -> bool:
    """Verifies provided token against active sessions or master passwords."""
    if not token:
        return False
    if token in MASTER_PASSWORDS:
        return True
    if token in SESSION_TOKENS:
        created = SESSION_TOKENS[token]
        if time.time() - created < TOKEN_TTL_SECONDS:
            return True
        else:
            del SESSION_TOKENS[token]
    return False


def get_primary_lan_ip() -> str:
    """Resolves the best LAN IP address for local network access."""
    # Priority list of prefixes for typical home/office Wi-Fi/LAN
    preferred_ips = []
    fallback_ips = []
    try:
        for nic, addrs in psutil.net_if_addrs().items():
            nic_lower = nic.lower()
            # Skip VMware, VirtualBox, WSL, Hyper-V, Loopback
            is_virtual = any(v in nic_lower for v in ("vmware", "virtualbox", "vbox", "wsl", "vethernet", "loopback"))
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    ip = addr.address
                    if is_virtual:
                        fallback_ips.append(ip)
                    else:
                        if ip.startswith(("192.168.1.", "192.168.0.", "10.0.", "172.16.")):
                            preferred_ips.insert(0, ip)
                        else:
                            preferred_ips.append(ip)
        if preferred_ips:
            return preferred_ips[0]
        if fallback_ips:
            return fallback_ips[0]
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# =========================================================================
# 🖱️ NATIVE INPUT DISPATCHER (CTYPES / USER32 + PYAUTOGUI)
# =========================================================================
class NativeInputDispatcher:
    """
    High-performance Windows user32 native input pipeline.
    Zero latency cursor dispatch, mouse clicks, wheel, keyboard, and macro hooks.
    """

    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_ABSOLUTE = 0x8000

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.sw = self.user32.GetSystemMetrics(0)
        self.sh = self.user32.GetSystemMetrics(1)
        self._ensure_default_desktop()

    def _ensure_default_desktop(self) -> bool:
        """Ensures the current thread is attached to the interactive user desktop."""
        try:
            hdesk = self.user32.OpenDesktopW("default", 0, False, 0x10000000)
            if hdesk:
                self.user32.SetThreadDesktop(hdesk)
                return True
        except Exception:
            pass
        return False

    def update_screen_metrics(self):
        self.sw = self.user32.GetSystemMetrics(0) or 1920
        self.sh = self.user32.GetSystemMetrics(1) or 1080

    def move_to_normalized(self, norm_x: float, norm_y: float):
        """Moves cursor to normalized screen coordinates [0.0 - 1.0]."""
        self._ensure_default_desktop()
        self.update_screen_metrics()
        target_x = max(0, min(self.sw - 1, int(norm_x * self.sw)))
        target_y = max(0, min(self.sh - 1, int(norm_y * self.sh)))
        self.user32.SetCursorPos(target_x, target_y)

    def move_relative(self, dx: float, dy: float, speed: float = 1.0):
        """Smooth relative movement for virtual trackpad."""
        self._ensure_default_desktop()
        self.update_screen_metrics()
        pt = wintypes.POINT()
        if self.user32.GetCursorPos(ctypes.byref(pt)):
            nx = max(0, min(self.sw - 1, int(pt.x + dx * speed)))
            ny = max(0, min(self.sh - 1, int(pt.y + dy * speed)))
            self.user32.SetCursorPos(nx, ny)

    def mouse_down(self, button: str = "left"):
        self._ensure_default_desktop()
        btn = button.lower()
        flag = self.MOUSEEVENTF_LEFTDOWN
        if btn == "right":
            flag = self.MOUSEEVENTF_RIGHTDOWN
        elif btn == "middle":
            flag = self.MOUSEEVENTF_MIDDLEDOWN
        self.user32.mouse_event(flag, 0, 0, 0, 0)

    def mouse_up(self, button: str = "left"):
        self._ensure_default_desktop()
        btn = button.lower()
        flag = self.MOUSEEVENTF_LEFTUP
        if btn == "right":
            flag = self.MOUSEEVENTF_RIGHTUP
        elif btn == "middle":
            flag = self.MOUSEEVENTF_MIDDLEUP
        self.user32.mouse_event(flag, 0, 0, 0, 0)

    def click(self, button: str = "left", double: bool = False):
        self._ensure_default_desktop()
        btn = button.lower()
        if btn == "right":
            self.user32.mouse_event(self.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(0.01)
            self.user32.mouse_event(self.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        elif btn == "middle":
            self.user32.mouse_event(self.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
            time.sleep(0.01)
            self.user32.mouse_event(self.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
        else:
            self.user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.01)
            self.user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            if double:
                time.sleep(0.06)
                self.user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.01)
                self.user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def wheel(self, delta_y: int):
        self._ensure_default_desktop()
        self.user32.mouse_event(self.MOUSEEVENTF_WHEEL, 0, 0, int(delta_y), 0)

    def type_unicode(self, text: str):
        """Types unicode string (including Thai characters) via clipboard or pyautogui."""
        self._ensure_default_desktop()
        if not text:
            return
        if PYAUTOGUI_AVAILABLE:
            try:
                import pyperclip
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                return
            except Exception:
                try:
                    pyautogui.write(text, interval=0.01)
                    return
                except Exception:
                    pass

    def press_key(self, key_name: str):
        """Presses a single key (e.g. 'enter', 'esc', 'backspace', 'tab')."""
        self._ensure_default_desktop()
        if PYAUTOGUI_AVAILABLE:
            try:
                key_map = {
                    "enter": "enter", "return": "enter",
                    "esc": "esc", "escape": "esc",
                    "backspace": "backspace", "tab": "tab",
                    "space": "space", "up": "up", "down": "down",
                    "left": "left", "right": "right",
                    "delete": "delete", "home": "home", "end": "end"
                }
                k = key_map.get(key_name.lower(), key_name.lower())
                pyautogui.press(k)
            except Exception:
                pass

    def hotkey(self, *keys: str):
        """Presses hotkey combination."""
        self._ensure_default_desktop()
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey(*keys)
            except Exception:
                pass

    def run_macro(self, macro_name: str) -> str:
        """Executes designated quick macros."""
        self._ensure_default_desktop()
        m = macro_name.lower()
        if m in ("roblox_focus", "focus_roblox"):
            return self._focus_window_by_title("roblox")
        elif m in ("discord_focus", "focus_discord"):
            return self._focus_window_by_title("discord")
        elif m in ("win_d", "show_desktop", "desktop"):
            self.hotkey("win", "d")
            return "Executed Win+D (Show Desktop)"
        elif m in ("alt_tab", "switch_window"):
            self.hotkey("alt", "tab")
            return "Executed Alt+Tab"
        elif m in ("taskmgr", "task_manager"):
            os.system("start taskmgr.exe")
            return "Launched Task Manager"
        elif m in ("kill_roblox", "kill_all_roblox"):
            os.system("taskkill /F /IM RobloxPlayerBeta.exe /T 2>nul")
            return "Terminated Roblox processes"
        elif m in ("esc", "escape"):
            self.press_key("esc")
            return "Pressed ESC"
        elif m in ("enter", "return"):
            self.press_key("enter")
            return "Pressed Enter"
        return f"Unknown macro: {macro_name}"

    def _focus_window_by_title(self, keyword: str) -> str:
        """Finds top-level window containing keyword and brings it to the foreground."""
        target_hwnd = None

        def enum_cb(hwnd, lparam):
            nonlocal target_hwnd
            if self.user32.IsWindowVisible(hwnd):
                length = self.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    self.user32.GetWindowTextW(hwnd, buf, length + 1)
                    if keyword in buf.value.lower():
                        target_hwnd = hwnd
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        self.user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

        if target_hwnd:
            SW_RESTORE = 9
            self.user32.ShowWindow(target_hwnd, SW_RESTORE)
            self.user32.SetForegroundWindow(target_hwnd)
            return f"Focused window HWND: {hex(target_hwnd)}"
        return f"Window containing '{keyword}' not found"


INPUT_DRIVER = NativeInputDispatcher()


# =========================================================================
# 📺 SCREEN GRABBER & BROADCAST ENGINE (MSS / GDI)
# =========================================================================
class ScreenStreamEngine:
    """
    Ultra low-latency desktop screen grabber.
    Captures primary screen, resizes dynamically, encodes to JPEG/WebP,
    and broadcasts to connected WebSockets at 15-20 FPS.
    """

    def __init__(self):
        self.clients: Set[WebSocket] = set()
        self.target_fps = 15
        self.quality = 65
        self.scale = 0.5  # Default 960x540 for mobile Wi-Fi
        self.codec = "jpeg"  # 'jpeg' or 'webp'
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.current_fps = 0.0
        self.last_frame_bytes: bytes = b""
        self.lock = threading.Lock()

    def _ensure_desktop(self):
        try:
            user32 = ctypes.windll.user32
            hdesk = user32.OpenDesktopW("default", 0, False, 0x10000000)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="PBGScreenStreamLoop")
        self._thread.start()

    def stop(self):
        self.running = False

    def update_config(self, fps: Optional[int] = None, quality: Optional[int] = None, scale: Optional[float] = None, codec: Optional[str] = None):
        with self.lock:
            if fps is not None:
                self.target_fps = max(5, min(30, fps))
            if quality is not None:
                self.quality = max(25, min(95, quality))
            if scale is not None:
                self.scale = max(0.3, min(1.0, scale))
            if codec is not None and codec.lower() in ("jpeg", "webp"):
                self.codec = codec.lower()

    def _capture_loop(self):
        """Continuous screen grab loop executed in a dedicated daemon thread."""
        self._ensure_desktop()
        frames_counted = 0
        fps_start = time.time()

        with mss.mss() as sct:
            mon = sct.monitors[0]
            while self.running:
                loop_start = time.time()
                try:
                    # Capture screen
                    raw = sct.grab(mon)
                    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

                    # Resize according to scale
                    if self.scale < 0.98:
                        nw = max(320, int(img.width * self.scale))
                        nh = max(180, int(img.height * self.scale))
                        img = img.resize((nw, nh), Image.Resampling.NEAREST)

                    # Encode
                    buf = io.BytesIO()
                    if self.codec == "webp":
                        img.save(buf, format="WEBP", quality=self.quality, method=0)
                    else:
                        img.save(buf, format="JPEG", quality=self.quality, optimize=False)
                    frame_data = buf.getvalue()

                    with self.lock:
                        self.last_frame_bytes = frame_data

                    # Broadcast to clients via async event loop
                    if self.clients:
                        asyncio.run(self._broadcast_frame(frame_data))

                    frames_counted += 1
                    now = time.time()
                    if now - fps_start >= 1.0:
                        self.current_fps = frames_counted / (now - fps_start)
                        frames_counted = 0
                        fps_start = now

                    # Maintain target frame rate
                    target_delay = 1.0 / self.target_fps
                    elapsed = time.time() - loop_start
                    delay = max(0.001, target_delay - elapsed)
                    time.sleep(delay)

                except Exception as e:
                    time.sleep(0.05)

    async def _broadcast_frame(self, frame_data: bytes):
        """Asynchronously sends frame to all connected WebSockets."""
        dead_clients = []
        for ws in list(self.clients):
            try:
                await ws.send_bytes(frame_data)
            except Exception:
                dead_clients.append(ws)
        for dc in dead_clients:
            self.clients.discard(dc)


STREAM_ENGINE = ScreenStreamEngine()


# =========================================================================
# 📱 GLASSMORPHIC PWA FRONTEND (HTML / CSS / JAVASCRIPT BUNDLE)
# =========================================================================
def render_mobile_pwa_html(token: str) -> str:
    """Returns the standalone, high-performance Glassmorphic Mobile Web App."""
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="theme-color" content="#0C0306">
  <title>PBG Godmode // Mobile Remote</title>
  <link rel="manifest" href="/manifest.json?token={token}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-dark: #0A0205;
      --card-bg: rgba(22, 6, 14, 0.75);
      --card-border: rgba(255, 20, 50, 0.25);
      --crimson: #FF1432;
      --crimson-glow: rgba(255, 20, 50, 0.45);
      --emerald: #00E696;
      --emerald-glow: rgba(0, 230, 150, 0.35);
      --cyan: #00E5FF;
      --text: #F3F4F6;
      --text-dim: #9CA3AF;
      --trackpad-bg: rgba(18, 5, 12, 0.85);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
    }}

    body {{
      background: var(--bg-dark);
      color: var(--text);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      overflow: hidden;
      height: 100vh;
      width: 100vw;
      display: flex;
      flex-direction: column;
      position: fixed;
      touch-action: none;
    }}

    /* HEADER BAR */
    header {{
      height: 48px;
      padding: 0 12px;
      background: rgba(12, 3, 6, 0.85);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 100;
    }}

    .logo-badge {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      font-weight: 800;
      letter-spacing: 0.5px;
    }}

    .logo-badge span.dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--crimson);
      box-shadow: 0 0 8px var(--crimson);
    }}

    .logo-badge span.online {{
      background: var(--emerald);
      box-shadow: 0 0 8px var(--emerald);
    }}

    .telemetry-pills {{
      display: flex;
      gap: 6px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }}

    .pill {{
      padding: 2px 7px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      display: flex;
      align-items: center;
      gap: 4px;
    }}

    .pill.active {{
      border-color: var(--emerald);
      color: var(--emerald);
    }}

    /* VIEWPORT / CANVAS */
    #viewport-container {{
      flex: 1;
      position: relative;
      background: #000;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}

    #screenCanvas {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      box-shadow: 0 0 20px rgba(0,0,0,0.8);
      display: block;
    }}

    /* VIRTUAL TRACKPAD OVERLAY */
    #trackpad-overlay {{
      display: none;
      position: absolute;
      inset: 0;
      background: var(--trackpad-bg);
      backdrop-filter: blur(8px);
      z-index: 20;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }}

    .trackpad-hint {{
      color: var(--text-dim);
      font-size: 12px;
      margin-bottom: 8px;
      letter-spacing: 0.5px;
    }}

    .trackpad-zone {{
      width: 90%;
      height: 70%;
      border-radius: 16px;
      border: 2px dashed rgba(255, 20, 50, 0.4);
      background: rgba(255, 20, 50, 0.03);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.3);
      touch-action: none;
    }}

    /* FLOATING ACTION PAD DOCK */
    #action-dock {{
      position: absolute;
      bottom: 12px;
      left: 10px;
      right: 10px;
      background: var(--card-bg);
      backdrop-filter: blur(20px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
      z-index: 50;
      transition: transform 0.25s ease;
    }}

    .dock-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
    }}

    .btn {{
      flex: 1;
      height: 38px;
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      background: rgba(255, 255, 255, 0.05);
      color: var(--text);
      font-weight: 600;
      font-size: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      cursor: pointer;
      transition: all 0.12s ease;
    }}

    .btn:active {{
      transform: scale(0.95);
      background: rgba(255, 20, 50, 0.25);
      border-color: var(--crimson);
    }}

    .btn.primary {{
      background: linear-gradient(135deg, rgba(255, 20, 50, 0.3), rgba(255, 20, 50, 0.15));
      border-color: var(--crimson);
      box-shadow: 0 0 10px rgba(255, 20, 50, 0.2);
    }}

    .btn.emerald {{
      background: linear-gradient(135deg, rgba(0, 230, 150, 0.25), rgba(0, 230, 150, 0.1));
      border-color: var(--emerald);
      color: var(--emerald);
    }}

    .btn.danger {{
      background: rgba(255, 30, 50, 0.2);
      border-color: rgba(255, 30, 50, 0.5);
      color: #FFA0A0;
    }}

    /* KEYBOARD & TEXT SENDER MODAL */
    #text-modal {{
      display: none;
      position: absolute;
      top: 54px;
      left: 12px;
      right: 12px;
      background: var(--card-bg);
      backdrop-filter: blur(24px);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 12px;
      z-index: 120;
      box-shadow: 0 12px 35px rgba(0,0,0,0.8);
    }}

    .input-row {{
      display: flex;
      gap: 8px;
    }}

    #text-input {{
      flex: 1;
      height: 40px;
      border-radius: 8px;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: rgba(0, 0, 0, 0.5);
      color: #fff;
      padding: 0 10px;
      font-size: 14px;
      outline: none;
    }}

    #text-input:focus {{
      border-color: var(--crimson);
      box-shadow: 0 0 8px var(--crimson-glow);
    }}

    /* SETTINGS MODAL */
    #settings-modal {{
      display: none;
      position: absolute;
      inset: 16px;
      background: rgba(14, 4, 10, 0.94);
      backdrop-filter: blur(28px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px;
      z-index: 150;
      overflow-y: auto;
    }}

    .setting-group {{
      margin-bottom: 14px;
    }}

    .setting-label {{
      font-size: 12px;
      font-weight: 700;
      color: var(--text-dim);
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .chips {{
      display: flex;
      gap: 6px;
    }}

    .chip {{
      flex: 1;
      padding: 8px 4px;
      text-align: center;
      border-radius: 8px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      background: rgba(255, 255, 255, 0.04);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }}

    .chip.selected {{
      border-color: var(--crimson);
      background: rgba(255, 20, 50, 0.2);
      color: #fff;
    }}
  </style>
</head>
<body>
  <!-- HEADER -->
  <header>
    <div class="logo-badge">
      <span class="dot" id="status-dot"></span>
      <span>PBG GODMODE</span>
    </div>
    <div class="telemetry-pills">
      <div class="pill active" id="fps-pill">⚡ 0 FPS</div>
      <div class="pill" id="ping-pill">📶 0ms</div>
      <div class="pill" id="settings-btn" style="cursor: pointer;">⚙️</div>
    </div>
  </header>

  <!-- SCREEN VIEWPORT -->
  <div id="viewport-container">
    <canvas id="screenCanvas"></canvas>

    <!-- VIRTUAL TRACKPAD OVERLAY -->
    <div id="trackpad-overlay">
      <div class="trackpad-hint">แตะลากเพื่อเลื่อนเมาส์ / แตะ 1 นิ้วคลิกซ้าย / 2 นิ้วคลิกขวา</div>
      <div class="trackpad-zone" id="trackpad-touch-zone">
        🖱️ พื้นที่ควบคุม Touch Trackpad
      </div>
    </div>
  </div>

  <!-- FLOATING QUICK DOCK -->
  <div id="action-dock">
    <!-- Row 1: Mode Switch & Essential Clicks -->
    <div class="dock-row">
      <button class="btn primary" id="btn-mode-toggle">👆 สลับ Trackpad</button>
      <button class="btn" id="btn-click-left">🖱️ L-Click</button>
      <button class="btn" id="btn-click-right">🖱️ R-Click</button>
      <button class="btn" id="btn-click-double">⚡ 2x Click</button>
    </div>

    <!-- Row 2: In-Game / System Macros -->
    <div class="dock-row">
      <button class="btn emerald" id="btn-focus-roblox">🎮 Roblox</button>
      <button class="btn" id="btn-keyboard-toggle">⌨️ แป้นพิมพ์</button>
      <button class="btn" id="btn-macro-desktop">🖥️ Win+D</button>
      <button class="btn" id="btn-macro-esc">ESC</button>
      <button class="btn danger" id="btn-kill-roblox">🛑 ปิดเกม</button>
    </div>
  </div>

  <!-- TEXT INPUT MODAL -->
  <div id="text-modal">
    <div class="input-row">
      <input type="text" id="text-input" placeholder="พิมพ์ข้อความ (รองรับภาษาไทย) แล้วกดส่ง..." />
      <button class="btn primary" style="width: 70px;" id="btn-send-text">ส่ง</button>
      <button class="btn" style="width: 40px;" id="btn-close-text">✕</button>
    </div>
  </div>

  <!-- SETTINGS MODAL -->
  <div id="settings-modal">
    <h3 style="margin-bottom: 14px; font-size: 15px; color: var(--crimson);">⚙️ ตั้งค่าสตรีมและประสิทธิภาพ</h3>

    <div class="setting-group">
      <div class="setting-label">เป้าหมายเฟรมเรต (FPS)</div>
      <div class="chips" id="fps-chips">
        <div class="chip" data-val="10">10 FPS</div>
        <div class="chip selected" data-val="15">15 FPS</div>
        <div class="chip" data-val="20">20 FPS</div>
        <div class="chip" data-val="25">25 FPS</div>
      </div>
    </div>

    <div class="setting-group">
      <div class="setting-label">สเกลภาพ (Resolution Scale)</div>
      <div class="chips" id="scale-chips">
        <div class="chip" data-val="0.4">40% (ประหยัดเน็ต)</div>
        <div class="chip selected" data-val="0.5">50% (แนะนำ)</div>
        <div class="chip" data-val="0.75">75% (คมชัด)</div>
      </div>
    </div>

    <div class="setting-group">
      <div class="setting-label">ตัวถอดรหัส (Codec)</div>
      <div class="chips" id="codec-chips">
        <div class="chip selected" data-val="jpeg">JPEG (ลื่นสุด)</div>
        <div class="chip" data-val="webp">WebP (ประหยัดเน็ต)</div>
      </div>
    </div>

    <button class="btn primary" id="btn-close-settings" style="width: 100%; height: 44px; margin-top: 10px;">บันทึกและปิด</button>
  </div>

  <script>
    const TOKEN = "{token}";
    const canvas = document.getElementById("screenCanvas");
    const ctx = canvas.getContext("2d");
    const statusDot = document.getElementById("status-dot");
    const fpsPill = document.getElementById("fps-pill");
    const pingPill = document.getElementById("ping-pill");

    let ws = null;
    let isConnected = false;
    let trackpadMode = false;
    let currentFps = 0;
    let frameCount = 0;
    let lastFpsTime = Date.now();
    let pingStartTime = 0;

    // Connect WebSocket
    function connectStream() {{
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${{proto}}//${{window.location.host}}/ws/stream?token=${{TOKEN}}`;

      ws = new WebSocket(wsUrl);
      ws.binaryType = "blob";

      ws.onopen = () => {{
        isConnected = true;
        statusDot.classList.add("online");
        fpsPill.classList.add("active");
        sendPing();
      }};

      ws.onclose = () => {{
        isConnected = false;
        statusDot.classList.remove("online");
        fpsPill.classList.remove("active");
        setTimeout(connectStream, 1500);
      }};

      ws.onerror = () => {{
        ws.close();
      }};

      ws.onmessage = async (evt) => {{
        if (typeof evt.data === "string") {{
          try {{
            const msg = JSON.parse(evt.data);
            if (msg.type === "pong") {{
              const rtt = Math.round(performance.now() - pingStartTime);
              pingPill.textContent = `📶 ${{rtt}}ms`;
              setTimeout(sendPing, 2000);
            }}
          }} catch (e) {{}}
          return;
        }}

        // Binary image blob
        const blob = evt.data;
        const bitmap = await createImageBitmap(blob);
        if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {{
          canvas.width = bitmap.width;
          canvas.height = bitmap.height;
        }}
        ctx.drawImage(bitmap, 0, 0);

        frameCount++;
        const now = Date.now();
        if (now - lastFpsTime >= 1000) {{
          currentFps = Math.round((frameCount * 1000) / (now - lastFpsTime));
          fpsPill.textContent = `⚡ ${{currentFps}} FPS`;
          frameCount = 0;
          lastFpsTime = now;
        }}
      }};
    }}

    function sendPing() {{
      if (isConnected && ws) {{
        pingStartTime = performance.now();
        ws.send(JSON.stringify({{ type: "ping" }}));
      }}
    }}

    function sendCmd(cmd) {{
      if (isConnected && ws && ws.readyState === WebSocket.OPEN) {{
        ws.send(JSON.stringify(cmd));
      }}
    }}

    // --- DIRECT TOUCH INTERACTION ON CANVAS ---
    canvas.addEventListener("touchstart", (e) => {{
      if (trackpadMode) return;
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const touch = e.touches[0];
      const nx = (touch.clientX - rect.left) / rect.width;
      const ny = (touch.clientY - rect.top) / rect.height;
      if (nx >= 0 && nx <= 1 && ny >= 0 && ny <= 1) {{
        sendCmd({{ type: "move", x: nx, y: ny }});
        sendCmd({{ type: "click", btn: "left" }});
      }}
    }}, {{ passive: false }});

    // --- TRACKPAD TOUCH ZONE GESTURES ---
    const trackZone = document.getElementById("trackpad-touch-zone");
    let tpStartX = 0, tpStartY = 0;
    let tpLastX = 0, tpLastY = 0;
    let isTracking = false;

    trackZone.addEventListener("touchstart", (e) => {{
      e.preventDefault();
      if (e.touches.length === 1) {{
        tpStartX = e.touches[0].clientX;
        tpStartY = e.touches[0].clientY;
        tpLastX = tpStartX;
        tpLastY = tpStartY;
        isTracking = true;
      }} else if (e.touches.length === 2) {{
        sendCmd({{ type: "click", btn: "right" }});
      }}
    }}, {{ passive: false }});

    trackZone.addEventListener("touchmove", (e) => {{
      e.preventDefault();
      if (isTracking && e.touches.length === 1) {{
        const cx = e.touches[0].clientX;
        const cy = e.touches[0].clientY;
        const dx = (cx - tpLastX) * 1.6;
        const dy = (cy - tpLastY) * 1.6;
        tpLastX = cx;
        tpLastY = cy;
        sendCmd({{ type: "delta", dx: dx, dy: dy }});
      }} else if (e.touches.length === 2) {{
        // Two-finger scroll
        const dy = (e.touches[0].clientY - tpStartY) * 2;
        sendCmd({{ type: "wheel", dy: -dy }});
      }}
    }}, {{ passive: false }});

    trackZone.addEventListener("touchend", (e) => {{
      e.preventDefault();
      if (isTracking) {{
        const dist = Math.hypot(tpLastX - tpStartX, tpLastY - tpStartY);
        if (dist < 8) {{
          // Quick tap -> left click
          sendCmd({{ type: "click", btn: "left" }});
        }}
        isTracking = false;
      }}
    }}, {{ passive: false }});

    // --- BUTTON CONTROLS ---
    const btnModeToggle = document.getElementById("btn-mode-toggle");
    const trackpadOverlay = document.getElementById("trackpad-overlay");

    btnModeToggle.onclick = () => {{
      trackpadMode = !trackpadMode;
      trackpadOverlay.style.display = trackpadMode ? "flex" : "none";
      btnModeToggle.textContent = trackpadMode ? "🖱️ สลับ Direct Touch" : "👆 สลับ Trackpad";
    }};

    document.getElementById("btn-click-left").onclick = () => sendCmd({{ type: "click", btn: "left" }});
    document.getElementById("btn-click-right").onclick = () => sendCmd({{ type: "click", btn: "right" }});
    document.getElementById("btn-click-double").onclick = () => sendCmd({{ type: "click", btn: "left", double: true }});

    // --- MACROS ---
    document.getElementById("btn-focus-roblox").onclick = () => sendCmd({{ type: "macro", name: "roblox_focus" }});
    document.getElementById("btn-macro-desktop").onclick = () => sendCmd({{ type: "macro", name: "win_d" }});
    document.getElementById("btn-macro-esc").onclick = () => sendCmd({{ type: "macro", name: "esc" }});
    document.getElementById("btn-kill-roblox").onclick = () => {{
      if (confirm("ยืนยันสั่งปิดโปรเซส Roblox ทั้งหมดทันที?")) {{
        sendCmd({{ type: "macro", name: "kill_all_roblox" }});
      }}
    }};

    // --- KEYBOARD MODAL ---
    const textModal = document.getElementById("text-modal");
    const textInput = document.getElementById("text-input");

    document.getElementById("btn-keyboard-toggle").onclick = () => {{
      textModal.style.display = textModal.style.display === "block" ? "none" : "block";
      if (textModal.style.display === "block") textInput.focus();
    }};

    document.getElementById("btn-close-text").onclick = () => textModal.style.display = "none";

    document.getElementById("btn-send-text").onclick = sendText;
    textInput.addEventListener("keydown", (e) => {{
      if (e.key === "Enter") sendText();
    }});

    function sendText() {{
      const val = textInput.value;
      if (val) {{
        sendCmd({{ type: "type", text: val }});
        textInput.value = "";
      }}
    }}

    // --- SETTINGS MODAL ---
    const settingsModal = document.getElementById("settings-modal");
    document.getElementById("settings-btn").onclick = () => settingsModal.style.display = "block";
    document.getElementById("btn-close-settings").onclick = () => settingsModal.style.display = "none";

    function setupChips(containerId, configKey, parser) {{
      const container = document.getElementById(containerId);
      container.querySelectorAll(".chip").forEach(chip => {{
        chip.onclick = () => {{
          container.querySelectorAll(".chip").forEach(c => c.classList.remove("selected"));
          chip.classList.add("selected");
          const val = parser(chip.dataset.val);
          const payload = {{ type: "config" }};
          payload[configKey] = val;
          sendCmd(payload);
        }};
      }});
    }}

    setupChips("fps-chips", "fps", parseInt);
    setupChips("scale-chips", "scale", parseFloat);
    setupChips("codec-chips", "codec", (v) => v);

    // Initial boot
    connectStream();
  </script>
</body>
</html>
"""


# =========================================================================
# 🚀 FASTAPI SERVICE DEFINITION (PORT 49288)
# =========================================================================
app = FastAPI(title="PBG Godmode Web Controller", docs_url=None, redoc_url=None)


@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "service": "PBG Godmode Web Controller & Live Streamer",
        "port": DEFAULT_PORT,
        "timestamp": time.time()
    }


@app.get("/", response_class=HTMLResponse)
async def get_index(token: Optional[str] = Query(None)):
    """Serves the Glassmorphic Mobile Web App."""
    if not is_token_valid(token):
        return HTMLResponse(
            """<html><body style="background:#0C0306;color:#FF1432;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;">
            <h2>⛔ PBG 2FA AUTH REQUIRED // INVALID OR EXPIRED TOKEN</h2></body></html>""",
            status_code=403
        )
    return HTMLResponse(render_mobile_pwa_html(token))


@app.get("/manifest.json")
async def get_manifest(token: Optional[str] = Query(None)):
    """PWA Web App Manifest for mobile home screen installation."""
    manifest = {
        "name": "PBG Godmode Remote Controller",
        "short_name": "PBG Remote",
        "start_url": f"/?token={token or ''}",
        "display": "standalone",
        "background_color": "#0A0205",
        "theme_color": "#FF1432",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>",
                "sizes": "192x192",
                "type": "image/svg+xml"
            }
        ]
    }
    return JSONResponse(manifest)


@app.get("/api/qr")
async def get_qr_code(token: Optional[str] = Query(None)):
    """Generates a QR Code image pointing directly to the mobile access URL."""
    if not is_token_valid(token):
        raise HTTPException(status_code=403, detail="Invalid token")

    lan_ip = get_primary_lan_ip()
    target_url = f"http://{lan_ip}:{DEFAULT_PORT}/?token={token}"

    if QRCODE_AVAILABLE:
        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(target_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#FF1432", back_color="#0C0306")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
    else:
        raise HTTPException(status_code=500, detail="QRCode library not installed")


@app.get("/api/status")
async def get_status(token: Optional[str] = Query(None)):
    """Live telemetry payload."""
    if not is_token_valid(token):
        raise HTTPException(status_code=403, detail="Invalid token")

    return {
        "status": "online",
        "current_fps": round(STREAM_ENGINE.current_fps, 1),
        "target_fps": STREAM_ENGINE.target_fps,
        "quality": STREAM_ENGINE.quality,
        "scale": STREAM_ENGINE.scale,
        "codec": STREAM_ENGINE.codec,
        "active_clients": len(STREAM_ENGINE.clients),
        "lan_ip": get_primary_lan_ip(),
        "cpu_percent": psutil.cpu_percent(),
        "ram_percent": psutil.virtual_memory().percent
    }


@app.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    WebSocket endpoint handling:
    - High speed binary image frame streaming to phone
    - Inbound touch gestures, cursor movements, clicks, and text commands
    """
    if not is_token_valid(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    STREAM_ENGINE.clients.add(websocket)
    STREAM_ENGINE.start()

    # Send current frame immediately if available
    with STREAM_ENGINE.lock:
        if STREAM_ENGINE.last_frame_bytes:
            try:
                await websocket.send_bytes(STREAM_ENGINE.last_frame_bytes)
            except Exception:
                pass

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
                mtype = data.get("type")

                if mtype == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

                elif mtype == "move":
                    x = float(data.get("x", 0.0))
                    y = float(data.get("y", 0.0))
                    INPUT_DRIVER.move_to_normalized(x, y)

                elif mtype == "delta":
                    dx = float(data.get("dx", 0.0))
                    dy = float(data.get("dy", 0.0))
                    INPUT_DRIVER.move_relative(dx, dy)

                elif mtype == "click":
                    btn = data.get("btn", "left")
                    double = bool(data.get("double", False))
                    INPUT_DRIVER.click(button=btn, double=double)

                elif mtype == "down":
                    btn = data.get("btn", "left")
                    INPUT_DRIVER.mouse_down(button=btn)

                elif mtype == "up":
                    btn = data.get("btn", "left")
                    INPUT_DRIVER.mouse_up(button=btn)

                elif mtype == "wheel":
                    dy = int(data.get("dy", 0))
                    INPUT_DRIVER.wheel(dy)

                elif mtype == "type":
                    txt = data.get("text", "")
                    INPUT_DRIVER.type_unicode(txt)

                elif mtype == "macro":
                    mname = data.get("name", "")
                    INPUT_DRIVER.run_macro(mname)

                elif mtype == "config":
                    STREAM_ENGINE.update_config(
                        fps=data.get("fps"),
                        quality=data.get("quality"),
                        scale=data.get("scale"),
                        codec=data.get("codec")
                    )

            except Exception:
                pass

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        STREAM_ENGINE.clients.discard(websocket)


# =========================================================================
# 🌐 BACKGROUND SERVICE CONTROLLER
# =========================================================================
_SERVER_THREAD: Optional[threading.Thread] = None
_SERVER_RUNNING = False


def start_godmode_web_service(port: int = DEFAULT_PORT, host: str = "0.0.0.0") -> Tuple[bool, str]:
    """Starts the FastAPI Web Streamer service on a background daemon thread."""
    global _SERVER_THREAD, _SERVER_RUNNING

    if _SERVER_RUNNING:
        return True, f"Service already running on port {port}"

    def run_uvicorn():
        global _SERVER_RUNNING
        _SERVER_RUNNING = True
        try:
            uvicorn.run(app, host=host, port=port, log_level="warning")
        except Exception as e:
            print(f"[GODMODE WEB STREAMER] Error: {e}", flush=True)
        finally:
            _SERVER_RUNNING = False

    _SERVER_THREAD = threading.Thread(target=run_uvicorn, daemon=True, name="PBGWebStreamerThread")
    _SERVER_THREAD.start()

    time.sleep(0.5)
    return True, f"Started on http://{get_primary_lan_ip()}:{port}"


if __name__ == "__main__":
    print(f"[*] Starting PBG Godmode Mobile Web Streamer on port {DEFAULT_PORT}...")
    start_godmode_web_service()
    tok = generate_web_token()
    print(f"[+] Access URL: http://{get_primary_lan_ip()}:{DEFAULT_PORT}/?token={tok}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[!] Stopping...")
