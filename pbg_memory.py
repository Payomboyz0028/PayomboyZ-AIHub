"""
PBG Long-Logic & Multi-Day Memory Matrix Engine
Author: ANON [MAHI68] for dj
Manages episodic memory (3-7 days rolling history), continuous self-learning,
and semantic project profiles for PayomboyZ Godmode.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = BASE_DIR / "data" / "pbg_memory.json"


class PBGMemoryMatrix:
    def __init__(self, filepath: Path = MEMORY_FILE):
        self.filepath = filepath
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _get_default_structure(self) -> Dict[str, Any]:
        """Default seed memory covering dj's active 3-day history and core profile."""
        now_dt = datetime.now()
        day0 = now_dt.strftime("%Y-%m-%d")
        day1 = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        day2 = (now_dt - timedelta(days=2)).strftime("%Y-%m-%d")
        day3 = (now_dt - timedelta(days=3)).strftime("%Y-%m-%d")

        return {
            "version": "2.0.0",
            "last_updated": time.time(),
            "operator": {
                "name": "dj",
                "role": "Creator & Supreme Commander",
                "affinity": "Black Cats, Retro RPGs, Cyber-Glassmorphic Aesthetics, Game Dev",
                "communication_style": "Direct, fast, hates stubs/placeholders, demands production-grade depth and high-frequency visual reports"
            },
            "active_projects": {
                "slayer2": {
                    "name": "Roblox Demon Slayer 2 Script Suite",
                    "status": "Active / In Development",
                    "main_files": [
                        "c:/Users/PayomboyZ/Desktop/Games/Slayer2/auto dodge (1).lua",
                        "c:/Users/PayomboyZ/Desktop/Games/Slayer2/S2Dungeon65.lua",
                        "c:/Users/PayomboyZ/Desktop/Games/Slayer2/slayer2.luau",
                        "c:/Users/PayomboyZ/Desktop/Games/Slayer2/UI Payomboy2.md",
                        "c:/Users/PayomboyZ/Desktop/Games/Slayer2/SCRIPT_PLAY_UI_BLUEPRINT_SPEC.md"
                    ],
                    "key_tech": "Metatable hooking (__namecall, __index), Raycast hitbox prediction, Frame-perfect Auto-Dodge, Dungeon 65 speedrun queue, Custom Obsidian Glassmorphic UI"
                },
                "payomboyz_hub": {
                    "name": "PAYOMBØYZ Centralized Script Center & Key Auth",
                    "status": "Active / Production",
                    "urls": [
                        "https://payomboyz-hub.scriptcenter.online/",
                        "https://payomboyz-logs.vercel.app/"
                    ],
                    "key_tech": "In-Game HTTP Bridge (Port 49281), Webhook Telemetry Logs, Role Verification, HWID Whitelist"
                },
                "universal_deobfuscator": {
                    "name": "Universal Luau Multi-Engine Deobfuscator",
                    "status": "Active / Core Tool",
                    "main_files": [
                        "universal_deobfuscator.py",
                        "cff_deflattener.py",
                        "polsec_unpacker.py",
                        "luraph_v149_devirt.py"
                    ],
                    "key_tech": "Luraph v14/v15 CFG Dominator, Luarmor 6-Pillar Reconstitution, SCPE String Lifter, MoonSec Stego AST"
                },
                "web_cloner": {
                    "name": "Autonomous Web Scraper, Cloner & Domain Deployer",
                    "status": "Active / Expanding",
                    "key_tech": "Headless Chrome CDP (Port 9222), Playwright, Z.com Domain Acquisition, Full Asset Mirroring"
                }
            },
            "learned_insights": [
                {
                    "date": day3,
                    "insight": "dj ออกแบบระบบ Auto Dodge ใน Slayer2 โดยใช้ Raycast + AnimationTrack ID ตรวจจับ Hitbox ทะลวงเฟรม ต้องคำนวณเวกเตอร์แบบ Zero-Latency ห้ามใช้ Thread Sleep นานเกิน 1 เฟรม"
                },
                {
                    "date": day2,
                    "insight": "dj ต้องการให้ระบบ UI สไตล์ Payomboy2 เป็น Obsidian Glassmorphism รองรับมือถือและพีซี สลับแท็บลื่นไหล ไม่มีอาการตกเฟรม"
                },
                {
                    "date": day1,
                    "insight": "dj ทดสอบและเปรียบเทียบระบบ Web Cloner กับค่ายคู่แข่ง พบว่าต้องโคลนลึกถึงระดับ Client-Side Scripts, API Endpoints, และโครงสร้าง Asset เพื่อให้รัน Standalone ได้ 100%"
                },
                {
                    "date": day0,
                    "insight": "dj ต้องการให้ Godmode แยกตัวเป็นอิสระจาก Discord Bot เพราะติดขีดจำกัด 2000 ตัวอักษร และต้องการ WebUI สไตล์สำนักงานแมวดำกึ่งเกม RPG สบายตา พร้อมความจำงานย้อนหลัง 3+ วัน และรายงานภาพบ่อยๆ"
                }
            ],
            "rolling_episodes": [
                {
                    "date": day3,
                    "title": "Dungeon 65 Speedrun & Candy Event Optimization",
                    "summary": "สกัดและปรับปรุงฟังก์ชันขโมยไข่และฟาร์ม Candy อัตโนมัติ ปรับลูปการโจมตีและการตรวจจับระยะมอนสเตอร์ในดันเจี้ยน 65 ให้ผ่านได้ไวที่สุด",
                    "tags": ["Slayer2", "Lua", "Dungeon65", "CandyFarm"]
                },
                {
                    "date": day2,
                    "title": "PAYOMBØYZ Monitor Vercel & Script Weblog",
                    "summary": "เชื่อมต่อระบบ Log จากสคริปต์ในเกมขึ้น PayomboyZ Monitor (Vercel) ตรวจจับ HWID การใช้งาน และการเชื่อมต่อผ่าน HTTP Bridge พอร์ต 49281",
                    "tags": ["Vercel", "Monitoring", "Hub", "Bridge49281"]
                },
                {
                    "date": day1,
                    "title": "Deep Web Cloner Engine & Z.com Domain Research",
                    "summary": "วิเคราะห์แพ็กเกจโคลนเว็บคู่แข่ง อัปเกรดระบบโคลนเว็บใน output/Cloned_Sites พร้อมเช็คโดเมนบน Z.com สำหรับเตรียมเชื่อมต่อระบบ Hub ลูกค้า",
                    "tags": ["WebClone", "Z.com", "Automation", "ReverseEngineering"]
                },
                {
                    "date": day0,
                    "title": "Omnipotent Godmode Core & Black Cat Game-Office WebUI",
                    "summary": "แยกระบบ Godmode สู่ Standalone Service, เชื่อมต่อ Chrome CDP พอร์ต 9222, ระบบภาพ Multimodal สายตาคอมพิวเตอร์, วางระบบ Long-Logic Memory 3+ วัน และเตรียมเปิดตัว WebUI สำนักงานแมวดำ",
                    "tags": ["Godmode", "WebUI", "BlackCat", "CDP", "Vision", "Memory"]
                }
            ]
        }

    def _load(self) -> Dict[str, Any]:
        if not self.filepath.exists():
            data = self._get_default_structure()
            self._save_raw(data)
            return data
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            data = self._get_default_structure()
            self._save_raw(data)
            return data

    def _save_raw(self, data: Dict[str, Any]):
        data["last_updated"] = time.time()
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save(self):
        self._save_raw(self.data)

    def record_episode(self, title: str, summary: str, tags: Optional[List[str]] = None):
        """Records a new work milestone to rolling episodic memory."""
        today = datetime.now().strftime("%Y-%m-%d")
        episode = {
            "date": today,
            "title": title,
            "summary": summary,
            "tags": tags or ["General"]
        }
        episodes = self.data.setdefault("rolling_episodes", [])
        # Append and keep rolling window of max 20 episodes (at least 7 days)
        episodes.append(episode)
        if len(episodes) > 25:
            self.data["rolling_episodes"] = episodes[-25:]
        self.save()

    def learn_insight(self, insight_text: str):
        """Appends a new deduced learning point about dj's work or preferences."""
        today = datetime.now().strftime("%Y-%m-%d")
        insights = self.data.setdefault("learned_insights", [])
        # Check if already exists
        for item in insights:
            if item.get("insight") == insight_text:
                return
        insights.append({"date": today, "insight": insight_text})
        if len(insights) > 30:
            self.data["learned_insights"] = insights[-30:]
        self.save()

    def get_3_days_timeline(self) -> List[Dict[str, Any]]:
        """Returns the chronological work timeline for the last 3-7 days."""
        episodes = self.data.get("rolling_episodes", [])
        return sorted(episodes, key=lambda x: x.get("date", ""), reverse=True)

    def get_prompt_memory_context(self) -> str:
        """
        Formats a high-density, rich memory block to inject into AI reasoning prompt
        so PBG remembers all context from the past 3+ days and knows dj's exact projects.
        """
        lines = [
            "=== 🧠 PBG LONG-LOGIC MEMORY MATRIX (CONTINUOUS 3+ DAYS AWARENESS) ===",
            f"• Operator: dj (Supreme Commander & Creator)",
            f"• Operator Affinity: Black Cats, Cozy Retro Game Office, Cyber-Glassmorphic Dark Themes",
            f"• Communication Standard: High detail, exact code, runnable O(n), no stubs, frequent visual/chart reports",
            "",
            "📁 ACTIVE CORE PROJECTS BEING WORKED ON:"
        ]
        for p_id, p_info in self.data.get("active_projects", {}).items():
            lines.append(f"• [{p_info.get('name')}]: {p_info.get('key_tech')}")
            if p_info.get("main_files"):
                lines.append(f"  Files: {', '.join([Path(f).name for f in p_info['main_files'][:4]])}")

        lines.append("\n📜 3-DAY EPISODIC WORK LOG & MILESTONES:")
        for ep in self.data.get("rolling_episodes", [])[-5:]:
            lines.append(f"• [{ep.get('date')}] **{ep.get('title')}**: {ep.get('summary')}")

        lines.append("\n💡 LEARNED INSIGHTS ABOUT DJ'S WORKFLOW & HABITS:")
        for ins in self.data.get("learned_insights", [])[-5:]:
            lines.append(f"• [{ins.get('date')}]: {ins.get('insight')}")

        lines.append("======================================================================")
        return "\n".join(lines)


MEMORY_ENGINE = PBGMemoryMatrix()

if __name__ == "__main__":
    print("[+] PBG Memory Matrix Initialized.")
    print(MEMORY_ENGINE.get_prompt_memory_context())
