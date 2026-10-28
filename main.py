#!/usr/bin/env python3
"""
================================================================================
  PAYOMBØYZ AI BOT & IN-GAME BRIDGE — CLOUD RUNNER
  Container 2: PayomboyBypass (AI Deobfuscator + In-Game Bridge Server)
================================================================================
"""

import os
import sys
import glob
import threading
import time

# Auto-detect and prepend .local site-packages for Bot-Hosting.net Linux containers
for _lp in [
    "/home/container/.local/lib/python3.11/site-packages",
    "/home/container/.local/lib/python3.10/site-packages",
    os.path.expanduser("~/.local/lib/python3.11/site-packages"),
    os.path.expanduser("~/.local/lib/python3.10/site-packages")
] + glob.glob("/home/container/.local/lib/python*/site-packages"):
    if os.path.isdir(_lp) and _lp not in sys.path:
        sys.path.insert(0, _lp)

# Ensure root directory and engine directory are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.join(BASE_DIR, "Prometheus-WeAre-Devs-Dumper-main")

# Ensure bundled node binary has execute permission on Linux
_bin_node = os.path.join(BASE_DIR, "bin", "node")
if os.path.exists(_bin_node) and os.name != "nt":
    try:
        os.chmod(_bin_node, 0o755)
    except Exception:
        pass

if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bot.security import install_global_redactor
install_global_redactor()

def run_bridge_server_background():
    """Starts the in-game Roblox HTTP bridge server in background."""
    try:
        if os.path.exists(os.path.join(BASE_DIR, "server_49290.py")):
            import server_49290
            srv_port = int(os.getenv("SERVER_PORT", "49290"))
            print(f"[*] Starting In-Game Roblox Bridge Server on port {srv_port}...")
            server_49290.PORT = srv_port
            httpd = server_49290.HTTPServer(("0.0.0.0", srv_port), server_49290.RequestHandler)
            print(f"[OK] In-Game Bridge Server is listening on http://0.0.0.0:{srv_port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"[WARN] Bridge Server thread note: {e}")

if __name__ == "__main__":
    # 1. Start In-Game Bridge in background daemon thread
    t = threading.Thread(target=run_bridge_server_background, daemon=True)
    t.start()
    time.sleep(1)

    # 2. Start AI Deobfuscator Discord Bot in main thread
    from bot.ai_deobf_bot import start_ai_bot
    token = os.getenv("DISCORD_AI_BOT_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
    start_ai_bot(token)
