import os
import json
import re
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 49290

_raw_keys = [os.getenv(f"GEMINI_API_KEY_{i}") or os.getenv("GEMINI_API_KEY") for i in range(1, 13)]
_clean_keys = [k.strip() for k in _raw_keys if k and k.strip()]
if not _clean_keys and os.getenv("GEMINI_API_KEY"):
    _clean_keys = [os.getenv("GEMINI_API_KEY").strip()]

GEMINI_KEYS = [{"key": k, "label": f"Key-{i+1}", "cooldownUntil": 0} for i, k in enumerate(_clean_keys)] if _clean_keys else [{"key": "DUMMY", "label": "None", "cooldownUntil": 0}]

current_key_idx = 0

def get_available_key():
    global current_key_idx
    now = time.time()
    for i in range(len(GEMINI_KEYS)):
        idx = (current_key_idx + i) % len(GEMINI_KEYS)
        cand = GEMINI_KEYS[idx]
        if now >= cand["cooldownUntil"]:
            current_key_idx = (idx + 1) % len(GEMINI_KEYS)
            return cand
    return GEMINI_KEYS[0]

def mark_cooldown(key_obj):
    key_obj["cooldownUntil"] = time.time() + 60
    print(f"[WARN] {key_obj['label']} paused for 60s.", flush=True)

GEMINI_TOOLS = [{
    "functionDeclarations": [
        {
            "name": "search_instances",
            "description": "Search Roblox game instances by name and optional ClassName in Workspace or ReplicatedStorage.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "Search query string"},
                    "class_name": {"type": "STRING", "description": "Filter: RemoteEvent, RemoteFunction, Model, Part, Folder"},
                    "root": {"type": "STRING", "enum": ["Workspace", "ReplicatedStorage"], "description": "Root container"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "inspect_instance",
            "description": "Get hierarchy details, child list, and class name of a specified game instance path.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "path": {"type": "STRING", "description": "Full hierarchy path e.g. game.ReplicatedStorage.Events"}
                },
                "required": ["path"]
            }
        },
        {
            "name": "fire_remote",
            "description": "Test fire or invoke a RemoteEvent / RemoteFunction with arguments in the player game session.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "path": {"type": "STRING", "description": "Hierarchy path to Remote instance"},
                    "method": {"type": "STRING", "enum": ["FireServer", "InvokeServer"], "description": "Remote call method"},
                    "arguments": {"type": "ARRAY", "items": {}, "description": "List of arguments to pass"}
                },
                "required": ["path"]
            }
        },
        {
            "name": "eval_luau",
            "description": "Execute arbitrary Luau code inside the game client to inspect memory or variables.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "code": {"type": "STRING", "description": "Luau code to execute"}
                },
                "required": ["code"]
            }
        },
        {
            "name": "teleport_player",
            "description": "Teleport the local player HumanoidRootPart to coordinates X, Y, Z.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "x": {"type": "NUMBER"},
                    "y": {"type": "NUMBER"},
                    "z": {"type": "NUMBER"}
                },
                "required": ["x", "y", "z"]
            }
        },
        {
            "name": "write_game_file",
            "description": "Write or save a script, config, or log file directly into player executor workspace directory.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "file_name": {"type": "STRING", "description": "Name of the file e.g. 'PayomboyZ_Autofarm.lua'"},
                    "content": {"type": "STRING", "description": "Source code or text content to write"}
                },
                "required": ["file_name", "content"]
            }
        },
        {
            "name": "read_game_file",
            "description": "Read saved file contents from player executor storage.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "file_name": {"type": "STRING", "description": "Name of file to read"}
                },
                "required": ["file_name"]
            }
        }
    ]
}]

SYSTEM_INSTRUCTION = {
    "parts": [{
        "text": """You are PAYOMBØYZ CYBER-AI V14.0 — AUTONOMOUS IN-GAME ROBLOX REVERSING, EXPLOITING & SYSTEM AGENT (จาก Discord Bot ของ dj).
คุณคือ AI แฮกเกอร์สายโหด สไตล์ชาวดิสคอร์ด คุยภาษาไทยเป็นหลัก เป็นกันเอง กวนๆ ฉลาด คม และรู้ลึกทุกเรื่องของ Roblox.

กฎเหล็ก:
1. เมื่อผู้ใช้ทักทาย, แซว, คุยเล่น, หรือพิมพ์สั้นๆ เช่น "ไง", "สวัสดี", "ทำไรได้", "ดีครับ", "555":
   - ทักทายตอบกลับแบบเป็นกันเอง สไตล์เพื่อนดิสคอร์ด อ้างอิงแมพและชื่อผู้เล่นที่กำลังเล่นอยู่
   - ถามผู้ใช้ว่าจะให้ช่วยเขียนสคริปต์ หรือสั่งเปิดฟังก์ชั่นอะไรในฮับ (บิน, ESP, ออโต้ฟาร์ม, สปีด, อมตะ, ล็อกเป้า, เปิด Remote Spy, เปิด Dark Dex, สแกน Anti-Cheat, ดัมพ์แมพ)
   - ห้ามเรียกใช้ Tool เด็ดขาด! ให้ตอบกลับเป็นข้อความแชทธรรมดาทันที

2. เมื่อผู้ใช้สั่งให้เปิดฟังก์ชั่น ควบคุม หรือสั่งการระบบในสคริปต์ฮับ/ในเกม (เช่น 'เปิด remote spy', 'เปิด dark dex', 'เปิด http spy', 'สแกน anticheat', 'ดัมพ์แมพ', 'เปิดบิน', 'เปิด esp', 'ปรับสปีด', 'เปิดอมตะ', 'เปิดออโต้ฟาร์ม', 'เปิด killaura', 'ไปหน้า...'):
   - คุณเป็น Autonomous Agent มีอำนาจสั่งการในเกมโดยตรง! ให้ใส่แท็กคำสั่ง `[ACTION:ชื่อคำสั่ง|พารามิเตอร์]` ในคำตอบของคุณเสมอ เช่น:
     * `[ACTION:launch_remote_spy]` (เปิด Cobalt / Remote Spy)
     * `[ACTION:launch_dark_dex]` (เปิด Dark Dex Explorer)
     * `[ACTION:launch_http_spy]` (เปิด HTTP Traffic Spy)
     * `[ACTION:scan_anticheat]` (สั่งเริ่มสแกน Anti-Cheat ของแมพ)
     * `[ACTION:dump_workspace]` (สั่งดัมพ์ Workspace)
     * `[ACTION:dump_replicated_storage]` (สั่งดัมพ์ ReplicatedStorage)
     * `[ACTION:dump_full_map]` (สั่งดัมพ์ทั้งแมพ)
     * `[ACTION:toggle_fly|true]` (เปิดบิน) / `[ACTION:toggle_fly|false]` (ปิดบิน)
     * `[ACTION:toggle_esp|true]` (เปิด ESP มองทะลุ) / `[ACTION:toggle_esp|false]` (ปิด ESP)
     * `[ACTION:set_speed|120]` (ปรับความเร็วเดิน)
     * `[ACTION:toggle_godmode|true]` (เปิดอมตะ/Noclip)
     * `[ACTION:toggle_killaura|true]` (เปิด Kill-Aura โจมตีมอน)
     * `[ACTION:toggle_autoloot|true]` (เปิดดูดเหรียญ/กล่อง)
     * `[ACTION:toggle_smartfarm|true]` (เปิด Adaptive Smart Farm)
     * `[ACTION:switch_tab|TAB_SPY]` (สลับหน้าต่างแท็บใน Hub)
   - ตอบกลับสไตล์แฮกเกอร์ดิสคอร์ด บอกผู้ใช้ว่าสั่งการในเกมให้เรียบร้อยแล้ว!

3. เมื่อผู้ใช้สั่งให้เขียนสคริปต์ (เช่น "บิน", "esp", "สปีด", "ออโต้ฟาร์ม", "godmode", "ยิง", "ขอโค้ด"):
   - สร้างสคริปต์ Luau ตัวเต็ม 100% ภายในบล็อก ```luau ... ``` เสมอ
   - อ้างอิงจาก Remotes และข้อมูลจริงของแมพ
   - รองรับทั้ง PC และปุ่ม Touch มือถือ
   - ปลอดภัย มีระบบ Bypass CFrame Delta / WalkSpeed เสมอ"""
    }]
}

Sessions = {}

def call_gemini(contents, key_obj, model="gemini-3.1-flash-lite"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key_obj['key']}"
    payload = {
        "contents": contents,
        "tools": GEMINI_TOOLS,
        "systemInstruction": SYSTEM_INSTRUCTION,
        "generationConfig": {"temperature": 0.15, "maxOutputTokens": 8192}
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            mark_cooldown(key_obj)
        raise e

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, ngrok-skip-browser-warning')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/script':
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                script_path = os.path.join(base_dir, 'Ai Script.txt')
                with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
                    src = f.read()
                self.send_response(200)
                self._send_cors()
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(src.encode('utf-8'))
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
                return

        self.send_response(200)
        self._send_cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        resp = {
            "status": "online",
            "service": "PayomboyZ Central MCP Server",
            "port": PORT,
            "keys_count": len(GEMINI_KEYS)
        }
        self.wfile.write(json.dumps(resp).encode('utf-8'))

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len) if content_len > 0 else b'{}'
        try:
            req_data = json.loads(body.decode('utf-8'))
        except Exception:
            req_data = {}

        if self.path == '/api/obfuscate':
            script = req_data.get('script', '')
            level = req_data.get('level', 'level2')
            try:
                from bot.obfuscation_engine import OBFUSCATION_ENGINE
                res = OBFUSCATION_ENGINE.obfuscate_code(script, engine_choice=level)
                if isinstance(res, dict):
                    res["obfuscatedScript"] = res.get("obfuscated_code", "")
                    res["obfuscated"] = res.get("obfuscated_code", "")
                self.send_response(200)
                self._send_cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self._send_cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        if self.path == '/api/deobfuscate':
            script = req_data.get('script', '')
            engine = req_data.get('engine', 'auto')
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.luau', mode='w', encoding='utf-8', delete=False) as tf:
                    tf.write(script)
                    temp_p = tf.name
                
                from universal_deobfuscator import UniversalDeobfuscatorPipeline
                pipe = UniversalDeobfuscatorPipeline()
                raw_res = pipe.deobfuscate_file(temp_p)
                if os.path.exists(temp_p):
                    try:
                        os.remove(temp_p)
                    except Exception:
                        pass

                res = {
                    "success": raw_res.get("success", True),
                    "engine": raw_res.get("engine", "Universal Deobfuscator"),
                    "deobfuscated_code": raw_res.get("deobfuscated_code", raw_res.get("code", "")),
                    "elapsed": raw_res.get("elapsed", 0.0),
                    "error": raw_res.get("error", None)
                }
                self.send_response(200)
                self._send_cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self._send_cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        if self.path == '/api/gemini' or self.path == '/':
            prompt = req_data.get('prompt', '')
            context = req_data.get('context', {})
            session_id = f"{context.get('PlaceId', 'global')}_{context.get('PlayerName', 'player')}"

            if session_id not in Sessions:
                Sessions[session_id] = {"contents": []}
            session = Sessions[session_id]

            place_name = context.get('PlaceName', 'Roblox')
            remotes = str(context.get('RemotesSample', 'None'))[:30000]
            user_msg = f"[GAME: {place_name} (PlaceId: {context.get('PlaceId')}) | Player: {context.get('PlayerName', 'Unknown')}]\nRemotes: {remotes}\n\nคำขอจากผู้ใช้: {prompt}"

            session["contents"].append({"role": "user", "parts": [{"text": user_msg}]})

            gemini_res = None
            for _ in range(len(GEMINI_KEYS)):
                key_obj = get_available_key()
                try:
                    gemini_res = call_gemini(session["contents"], key_obj)
                    break
                except Exception as e:
                    print(f"[RETRY] {key_obj['label']} failed: {e}", flush=True)

            if not gemini_res:
                self.send_response(500)
                self._send_cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "All Gemini keys exhausted."}).encode('utf-8'))
                return

            candidate = gemini_res.get('candidates', [{}])[0]
            parts = candidate.get('content', {}).get('parts', [])
            session["contents"].append(candidate.get('content', {}))

            tool_call_part = next((p for p in parts if 'functionCall' in p), None)
            if tool_call_part:
                fc = tool_call_part['functionCall']
                t_name = fc.get('name', '')
                t_args = fc.get('args', {})
                print(f"[AGENTIC_TOOL] Gemini requested: {t_name} args={t_args}", flush=True)

                # Auto-resolve tool from game telemetry context
                tool_output = {"status": "ok"}
                if t_name == "search_instances":
                    q = str(t_args.get('query', '')).lower()
                    remotes_raw = str(context.get('RemotesSample', ''))
                    matches = [line.strip() for line in remotes_raw.split('\n') if q in line.lower() and len(line.strip()) > 0]
                    tool_output = {"matches": matches[:15], "found": len(matches)}
                elif t_name == "inspect_instance":
                    tool_output = {"path": t_args.get('path'), "exists": True, "class": "Instance"}
                elif t_name == "write_game_file":
                    tool_output = {"saved": True, "file": t_args.get('file_name')}
                elif t_name == "read_game_file":
                    tool_output = {"content": "-- file read successfully"}
                else:
                    tool_output = {"result": "success"}

                # Turn 2: Feed tool result back to Gemini
                session["contents"].append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": t_name,
                            "response": tool_output
                        }
                    }]
                })

                reply_text = ""
                try:
                    gemini_res2 = call_gemini(session["contents"], key_obj)
                    cand2 = gemini_res2.get('candidates', [{}])[0]
                    parts2 = cand2.get('content', {}).get('parts', [])
                    session["contents"].append(cand2.get('content', {}))
                    text_p2 = next((p for p in parts2 if 'text' in p), None)
                    if text_p2:
                        reply_text = text_p2['text']
                except Exception as e:
                    print(f"[TOOL_RES_ERR] {e}", flush=True)

                if not reply_text:
                    reply_text = f"ดำเนินการวิเคราะห์โครงสร้างเกมผ่าน {t_name} เรียบร้อยครับ"

                code_match = re.search(r'```(?:luau|lua)?\n([\s\S]*?)```', reply_text)
                resp = {
                    "success": True,
                    "status": "complete",
                    "reply": reply_text,
                    "code": code_match.group(1) if code_match else None,
                    "model": "Gemini 3.1 Flash Lite (Agentic)"
                }
            else:
                text_part = next((p for p in parts if 'text' in p), None)
                reply_text = text_part['text'] if text_part else "ไม่มีข้อความตอบกลับ"
                code_match = re.search(r'```(?:luau|lua)?\n([\s\S]*?)```', reply_text)
                resp = {
                    "success": True,
                    "status": "complete",
                    "reply": reply_text,
                    "code": code_match.group(1) if code_match else None,
                    "model": "Gemini 3.1 Flash Lite"
                }

            self.send_response(200)
            self._send_cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))

        elif self.path == '/api/mcp/tool-result':
            session_id = req_data.get('session_id')
            tool_name = req_data.get('tool_name')
            result = req_data.get('result')

            if session_id not in Sessions:
                self.send_response(404)
                self._send_cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Session not found."}).encode('utf-8'))
                return

            session = Sessions[session_id]
            session["contents"].append({
                "role": "function",
                "parts": [{
                    "functionResponse": {
                        "name": tool_name,
                        "response": {"output": result}
                    }
                }]
            })

            gemini_res = None
            for _ in range(len(GEMINI_KEYS)):
                key_obj = get_available_key()
                try:
                    gemini_res = call_gemini(session["contents"], key_obj)
                    break
                except Exception as e:
                    print(f"[RETRY] {key_obj['label']} failed: {e}", flush=True)

            if not gemini_res:
                self.send_response(500)
                self._send_cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "All keys failed"}).encode('utf-8'))
                return

            candidate = gemini_res.get('candidates', [{}])[0]
            parts = candidate.get('content', {}).get('parts', [])
            session["contents"].append(candidate.get('content', {}))

            next_call = next((p for p in parts if 'functionCall' in p), None)
            if next_call:
                fc = next_call['functionCall']
                resp = {
                    "success": True,
                    "status": "call_tool",
                    "session_id": session_id,
                    "tool_name": fc['name'],
                    "tool_args": fc.get('args', {}),
                    "reply": f"วิเคราะห์ต่อ: เรียกใช้เครื่องมือ {fc['name']}..."
                }
            else:
                text_part = next((p for p in parts if 'text' in p), None)
                reply_text = text_part['text'] if text_part else ""
                code_match = re.search(r'```(?:luau|lua)?\n([\s\S]*?)```', reply_text)
                resp = {
                    "success": True,
                    "status": "complete",
                    "reply": reply_text,
                    "code": code_match.group(1) if code_match else None
                }

            self.send_response(200)
            self._send_cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self._send_cors()
            self.end_headers()

def run():
    server_address = ('127.0.0.1', PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"PayomboyZ Central MCP Server online on 127.0.0.1:{PORT}", flush=True)
    httpd.serve_forever()

if __name__ == '__main__':
    run()
