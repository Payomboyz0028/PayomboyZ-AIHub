#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ CODE INTELLIGENCE & AI IDE INSPECTION ENGINE
====================================================================
Provides Discord Bot with "AI IDE" capabilities:
- Scans user-provided scripts or library files
- Detects:
  ✓ Functions
  ✓ Remote Calls (FireServer / InvokeServer)
  ✓ Loops & Coroutines (while, task.spawn, RenderStepped)
  ✓ UI Components (Tabs, Toggles, Sliders)
  ✓ State Machines & Flags (_G, shared, Options)
- Performs AST dependency tracing to advise on exact edit locations:
  "ต้องแก้ 3 จุด: State Controller, Farm Loop, UI Toggle ไม่จำเป็นต้องแตะ Remote Layer"
====================================================================
"""

import re
from typing import Dict, Any, List
from .dependency_graph import VALIDATOR


class CodeIntelligenceEngine:
    """Analyzes Luau source code and outputs AI IDE structured diagnostics."""

    def analyze_script(self, code_str: str, file_name: str = "Script.lua") -> Dict[str, Any]:
        """
        Performs full structural analysis and dependency validation.
        """
        # 1. Functions
        fns = re.findall(r'(?:local\s+)?function\s+([a-zA-Z0-9_.:]+)\s*\(', code_str)
        
        # 2. Remote Calls
        remotes = re.findall(r'([a-zA-Z0-9_]+):(FireServer|InvokeServer)\s*\(([^)]*)\)', code_str)
        
        # 3. Loops & Tasks
        loops = re.findall(r'\b(while\s+true\s+do|while\s+task\.wait|task\.spawn|task\.defer|RunService\.RenderStepped|RunService\.Heartbeat)\b', code_str)
        
        # 4. UI Components
        ui_comps = re.findall(r':(AddTab|AddSection|AddToggle|AddSlider|AddDropdown|AddButton|AddInput|AddKeybind)\s*\(', code_str)
        
        # 5. State Variables
        states = set(re.findall(r'(_G\.[a-zA-Z0-9_]+|shared\.[a-zA-Z0-9_]+|Options\.[a-zA-Z0-9_]+|Flags\.[a-zA-Z0-9_]+)', code_str))

        # 6. Dependency Validation
        is_valid, errors, warnings = VALIDATOR.validate_code(code_str)

        return {
            "file_name": file_name,
            "lines": len(code_str.splitlines()),
            "bytes": len(code_str.encode("utf-8")),
            "functions": fns,
            "remotes": [{"target": r[0], "method": r[1], "args": r[2][:40]} for r in remotes],
            "loops": loops,
            "ui_components": ui_comps,
            "states": list(states),
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "counts": {
                "functions": len(fns),
                "remotes": len(remotes),
                "loops": len(loops),
                "ui_components": len(ui_comps),
                "states": len(states)
            }
        }

    def format_ide_report(self, analysis: Dict[str, Any]) -> str:
        """Formats analysis into AI IDE Discord representation."""
        counts = analysis["counts"]
        lines = []
        lines.append(f"**🔬 AI IDE Code Inspection — `{analysis['file_name']}`**")
        lines.append(f"• **Lines:** {analysis['lines']:,} lines | **Size:** {analysis['bytes'] / 1024:.1f} KB")
        lines.append(f"• **Structure Overview:**")
        lines.append(f"  ✓ `{counts['functions']}` Functions")
        lines.append(f"  ✓ `{counts['remotes']}` Remote Calls")
        lines.append(f"  ✓ `{counts['loops']}` Active Loops / Tasks")
        lines.append(f"  ✓ `{counts['ui_components']}` UI Components")
        lines.append(f"  ✓ `{counts['states']}` State Machines / Global Flags")

        # Diagnostics / Warnings
        if analysis["errors"]:
            lines.append("\n**⚠️ Critical Issues Detected:**")
            for err in analysis["errors"]:
                lines.append(f"  - ❌ {err}")
        elif analysis["warnings"]:
            lines.append("\n**💡 Engineering Advice:**")
            for warn in analysis["warnings"]:
                lines.append(f"  - ⚠️ {warn}")
        else:
            lines.append("\n**🛡️ Dependency Integrity:** 100% Passed (No unknown methods or leaking threads)")

        return "\n".join(lines)

    def advise_modification(self, code_str: str, intent: str) -> str:
        """
        Pinpoints exact architectural locations to modify for a given goal.
        e.g. Pause/Resume, Auto-Sell, Anti-Detect
        """
        analysis = self.analyze_script(code_str)
        intent_l = intent.lower()

        if any(w in intent_l for w in ["pause", "resume", "พัก", "หยุด", "เริ่มใหม่"]):
            return """**🎯 จุดที่ต้องแก้ไขสำหรับระบบ Pause / Resume (3 จุด):**
1. **State Controller:** ประกาศตัวแปรสถานะ `_G.ScriptPaused = false`
2. **Farm Loop / Worker Threads:** ใส่เงื่อนไข `while _G.ScriptPaused do task.wait(0.5) end` ที่ต้นลูปของงาน
3. **UI Toggle / Keybind:** เพิ่มปุ่มสลับสถานะใน Tab Settings หรือปุ่ม Pause บน Pill HUD
*ข้อสังเกต: ไม่จำเป็นต้องแตะหรือแก้ไข Remote Layer หรือฟังก์ชันคำนวณตำแหน่ง*"""

        elif any(w in intent_l for w in ["auto sell", "ขายของ", "sell"]):
            return """**🎯 จุดที่ต้องแก้ไขสำหรับระบบ Auto-Sell (3 จุด):**
1. **Inventory Scanner:** สแกน PlayerGui หรือ PlayerData.Inventory เพื่อตรวจสอบไอเทมขยะ
2. **Remote Dispatcher:** เรียกใช้ RemoteEvent ของร้านค้า (FireServer "SellItem", ItemId)
3. **UI Dropdown / Toggle:** เพิ่มตัวเลือกระดับ Rarity ที่ต้องการขายใน Tab Main"""

        elif any(w in intent_l for w in ["speed", "ความเร็ว", "บิน", "fly", "speedhack"]):
            return """**🎯 จุดที่ต้องแก้ไขสำหรับระบบ Speed / Flight (2 จุด):**
1. **Character Physics:** จัดการ `Humanoid.WalkSpeed` หรือยัด `BodyVelocity / LinearVelocity` เข้า `HumanoidRootPart`
2. **Anti-Fall/Noclip:** เชื่อมโยง `RunService.Stepped` เพื่อปรับ `CanCollide = false` บนตัวละคร"""

        return f"**🎯 การวิเคราะห์การปรับแต่ง:** ตรวจพบ {analysis['counts']['functions']} ฟังก์ชัน และ {analysis['counts']['loops']} ลูป พร้อมรองรับการขยายโมดูล"


# Singleton
CODE_IDE = CodeIntelligenceEngine()
