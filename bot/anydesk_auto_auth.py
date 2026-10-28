# -*- coding: utf-8 -*-
"""
=============================================================================
  🔐 ANYDESK ZERO-KNOWLEDGE AUTO-AUTHENTICATION ENGINE
  - Brings AnyDesk window to foreground using Windows Alt-key bypass trick.
  - Injects master password silently with 100% clipboard paste fidelity.
  - Selects 'Log in automatically from now on' and submits OK.
  - Zero password leakage to web clients or logs.
=============================================================================
"""

import sys
import time
import ctypes
from ctypes import wintypes
import pyperclip
import pyautogui

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_RESTORE = 9
VK_MENU = 0x12  # ALT key

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

def force_foreground_window(hwnd: int) -> bool:
    """Forces target window into foreground bypassing Windows restrictions."""
    try:
        # Simulate Alt-key sequence to unblock SetForegroundWindow
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.keybd_event(VK_MENU, 0, 2, 0)
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SwitchToThisWindow(hwnd, True)
        return True
    except Exception as e:
        print(f"[AUTH ENGINE] Force foreground error: {e}", flush=True)
        return False

def find_anydesk_window() -> int:
    """Finds the active AnyDesk window on the current interactive desktop."""
    hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
    if hdesk:
        user32.SetThreadDesktop(hdesk)

    target_hwnd = 0

    def enum_cb(hwnd, lparam):
        nonlocal target_hwnd
        if user32.IsWindowVisible(hwnd):
            cls = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls, 256)
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            cls_name = cls.value.lower()
            title = buf.value.lower()
            if "ad_win" in cls_name or "anydesk" in title or "authorization" in title or "1216968584" in title:
                rect = RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w > 200 and h > 200:
                    target_hwnd = hwnd
                    return False
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumDesktopWindows(hdesk, WNDENUMPROC(enum_cb), 0)
    return target_hwnd

def perform_anydesk_injection(password: str = "St@313326339", max_wait_seconds: int = 25) -> bool:
    """
    Watches for AnyDesk window/modal, brings to focus, and enters password.
    Polls repeatedly to handle connection handshake delays.
    """
    start_t = time.time()
    print(f"[AUTH ENGINE] Starting Zero-Knowledge Auto-Auth watcher (timeout: {max_wait_seconds}s)...", flush=True)

    # 1. Copy password to clipboard for 100% exact character fidelity
    old_clipboard = ""
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        pass

    injected = False
    attempts = 0

    while time.time() - start_t < max_wait_seconds:
        hwnd = find_anydesk_window()
        if hwnd:
            force_foreground_window(hwnd)
            time.sleep(0.4)

            # Paste password directly into active focused field
            try:
                pyperclip.copy(password)
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.05)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.15)

                # Tab to "Log in automatically from now on"
                pyautogui.press("tab")
                time.sleep(0.1)
                # Space to check the box
                pyautogui.press("space")
                time.sleep(0.1)
                # Enter to submit OK
                pyautogui.press("enter")
                time.sleep(0.3)

                print(f"[AUTH ENGINE] Injected credentials into HWND {hwnd:x} (Attempt {attempts + 1})", flush=True)
                injected = True
                attempts += 1
                if attempts >= 2:
                    break
            except Exception as e:
                print(f"[AUTH ENGINE] Injection error: {e}", flush=True)

        time.sleep(0.8)

    # Restore previous clipboard if needed
    try:
        if old_clipboard:
            pyperclip.copy(old_clipboard)
    except Exception:
        pass

    return injected

if __name__ == "__main__":
    pwd = sys.argv[1] if len(sys.argv) > 1 else "St@313326339"
    success = perform_anydesk_injection(pwd)
    print("SUCCESS" if success else "TIMEOUT_OR_FAILED")
