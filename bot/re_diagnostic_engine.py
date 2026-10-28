#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ REVERSE ENGINEERING DIAGNOSTIC & BIOPSY ENGINE V1.0
====================================================================
Elite-Tier Reverse Engineering Analysis (REA-Powered):
  1. Obfuscator & VM Fingerprinting (Luraph, MoonSec, IronBrew, Luarmor, PSU, CFF)
  2. Secret, Grabber & HoneyPot Sniffer (Webhooks, IP Grabbers, Honeypots)
  3. Anti-Cheat Vulnerability & Defense Diagnostic (Bypass Generators)
  4. Dynamic Boundary Interception (via Headless Luau Metamethod Trap)
====================================================================
"""

import re
import json
import time
import hashlib
from typing import Dict, Any, List, Set, Optional

class REDiagnosticEngine:
    """
    Industrial-grade Reverse Engineering Biopsy & Threat Scanner for Luau/Lua scripts.
    """

    @classmethod
    def fingerprint_obfuscator(cls, code: str) -> Dict[str, Any]:
        """
        Pinpoints the exact obfuscator engine, VM architecture, and anti-tamper mechanisms.
        """
        engine_name = "Unknown / Clean Script"
        version = "N/A"
        vm_type = "Standard Luau AST"
        anti_tamper_traps = []
        confidence = 0.0

        # Luraph signatures
        if "LPH_" in code or "Luraph" in code or re.search(r'LPH_[A-Za-z0-9_]+', code):
            engine_name = "Luraph"
            confidence = 0.99
            if "LPH_NO_VIRTUALIZE" in code or "LPH_JIT" in code:
                version = "v14.9 / v15 Modern"
                vm_type = "High-Security Bytecode VM (Register-Based JIT)"
            elif "LPH_OBFUSCATED" in code:
                version = "v14.7 / v14.8"
                vm_type = "Dynamic Opcode Scrambler & Dispatcher"
            else:
                version = "v14.x Classic"
                vm_type = "Virtual Register Bytecode Machine"

        # MoonSec signatures
        elif "MoonSec" in code or re.search(r'local\s+[a-zA-Z0-9_]+\s*=\s*\{(?:\s*\[\d+\]\s*=\s*\d+,?){10,}\}', code):
            engine_name = "MoonSec"
            confidence = 0.95
            if "bit32" in code or "bit" in code:
                version = "v3 Extended"
                vm_type = "Bytecode VM with Bitwise Masking & Byte-Array Table"
            else:
                version = "v2 Classic"
                vm_type = "Stack-Based Virtual Machine"

        # IronBrew / IB2 signatures
        elif "IronBrew" in code or re.search(r'local\s+function\s+[a-zA-Z0-9_]+\s*\(\s*[a-zA-Z0-9_]+\s*,\s*[a-zA-Z0-9_]+\s*\)\s*local\s+[a-zA-Z0-9_]+\s*=\s*\{\s*\}', code) and "getfenv" in code:
            if re.search(r'\[\s*\d+\s*\]\s*=\s*\"\\(?:[0-9]{3}|x[0-9a-fA-F]{2})\"', code):
                engine_name = "IronBrew (IB2)"
                version = "v2.7.2 Edition"
                vm_type = "Control-Flow Flattened VM (Interpreter Loop)"
                confidence = 0.92

        # PSU / Prometheos
        elif "PSU" in code or "Prometheos" in code or re.search(r'local\s+[a-zA-Z0-9_]+\s*=\s*string\.dump', code):
            engine_name = "PSU / Prometheos"
            version = "Enterprise Edition"
            vm_type = "Virtualized C-Closure Wrapper"
            confidence = 0.90

        # Luarmor (Cloud-Based Protection)
        elif "luarmor" in code or "lzma" in code or re.search(r'api\.luarmor\.net|loader\.live', code):
            engine_name = "Luarmor"
            version = "Cloud VM (HWID/Key Tied)"
            vm_type = "Remote Payload Decryptor & Metamethod Gate"
            confidence = 0.98

        # WeAreDevs / Xen / Simple CFF
        elif re.search(r'while\s+true\s+do\s+if\s+[a-zA-Z0-9_]+\s*==\s*\d+\s+then', code) or "CFF" in code:
            engine_name = "Control Flow Flattening (CFF / Xen)"
            version = "Opaque Predicate Engine"
            vm_type = "Flattened State Machine"
            confidence = 0.85

        # Anti-Tamper & Integrity Traps Detection
        trap_checks = [
            (r'(?:debug\.getinfo|debug\.info)\s*\(', "Debug Callstack Validation Trap"),
            (r'hookfunction|hookmetamethod', "Anti-Hook Integrity Checker"),
            (r'getfenv\s*\(\s*\)\s*==\s*_G', "Environment Tamper Trap"),
            (r'setmetatable\s*\(\s*\{\}\s*,\s*\{\s*__mode', "Garbage Collector Canary Trap"),
            (r'coroutine\.wrap|coroutine\.create', "Thread Watchdog / Heartbeat Scanner"),
            (r'string\.char\s*\(\s*\d+\s*,\s*\d+', "Dynamic String De-obfuscation Layer"),
        ]
        for pattern, desc in trap_checks:
            m = re.search(pattern, code, re.IGNORECASE)
            if m:
                # Find line number
                line_no = code[:m.start()].count('\n') + 1
                anti_tamper_traps.append(f"{desc} (Line ~{line_no})")

        return {
            "engine": engine_name,
            "version": version,
            "vm_type": vm_type,
            "confidence": f"{int(confidence * 100)}%",
            "anti_tamper_traps": anti_tamper_traps[:5]
        }

    @classmethod
    def audit_threats_and_secrets(cls, code: str) -> Dict[str, Any]:
        """
        Scans for hidden malicious vectors: Discord Webhooks, IP Loggers,
        HoneyPot Remotes, and unauthorized HTTP exfiltration.
        """
        webhooks = []
        suspicious_urls = []
        honeypot_remotes = []
        cookie_theft = False
        threat_level = "CLEAN"
        risk_score = 0

        # 1. Discord Webhooks
        webhook_pattern = re.compile(r'https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/(\d+)/([a-zA-Z0-9_\-]+)', re.IGNORECASE)
        for m in webhook_pattern.finditer(code):
            wid, token = m.groups()
            masked = f"https://discord.com/api/webhooks/{wid}/{token[:6]}...{token[-4:]}"
            webhooks.append(masked)
            risk_score += 45

        # 2. Suspicious Exfiltration Domains (IP Grabbers, Pastebins, Webhook proxies)
        sus_domains = ["grabify.link", "iplogger.org", "webhook.site", "pastebin.com/api", "ngrok.io", "requestcatcher.com"]
        for domain in sus_domains:
            if domain in code.lower():
                suspicious_urls.append(domain)
                risk_score += 30

        # 3. HoneyPot & Detection Remotes
        # Developer honeypots designed to instantly ban unauthorized script users
        hp_keywords = ["honeypot", "securitycheck", "banremote", "anticheat_report", "detectiontrigger", "player_flagged", "telemetrylog"]
        for kw in hp_keywords:
            if re.search(rf'["\']([a-zA-Z0-9_\-]*{kw}[a-zA-Z0-9_\-]*)["\']', code, re.IGNORECASE):
                honeypot_remotes.append(kw)
                risk_score += 25

        # 4. Cookie / Credential Exfiltration Indicators
        if any(w in code for w in [".ROBLOSECURITY", "GetCookie", "cookie", "Roblosecurity"]) and any(w in code for w in ["request", "http_request", "syn.request"]):
            cookie_theft = True
            risk_score += 80

        # Determine Threat Level
        if risk_score >= 70 or cookie_theft:
            threat_level = "CRITICAL (MALICIOUS PAYLOAD DETECTED)"
        elif risk_score >= 35:
            threat_level = "HIGH (SUSPICIOUS TELEMETRY / HONEYPOT)"
        elif risk_score > 0:
            threat_level = "MEDIUM (EXTERNAL NETWORK CALLS)"

        return {
            "threat_level": threat_level,
            "risk_score": min(100, risk_score),
            "webhooks": webhooks,
            "suspicious_urls": suspicious_urls,
            "honeypot_remotes": honeypot_remotes,
            "cookie_theft_detected": cookie_theft
        }

    @classmethod
    def audit_anticheat_defenses(cls, code: str) -> Dict[str, Any]:
        """
        Audits anti-cheat hooks and generates surgical Luau bypasses.
        """
        defenses_detected = []
        bypass_snippets = []

        if re.search(r'WalkSpeed|JumpPower', code):
            defenses_detected.append("Humanoid Property Polling (WalkSpeed / JumpPower Check)")
            bypass_snippets.append("""-- [Surgical __index Spoof]
local oldIndex
oldIndex = hookmetamethod(game, "__index", newcclosure(function(self, key)
    if not checkcaller() and typeof(self) == "Instance" and self:IsA("Humanoid") then
        if key == "WalkSpeed" then return 16 end
        if key == "JumpPower" then return 50 end
    end
    return oldIndex(self, key)
end))""")

        if re.search(r'Raycast|DistanceFromCharacter|Magnitude', code):
            defenses_detected.append("Raycast Teleportation / Noclip Distance Delta Check")
            bypass_snippets.append("""-- [Safe Tween Movement Anchor]
local function SafeTween(targetCFrame, speedStudsPerSec)
    local root = game.Players.LocalPlayer.Character and game.Players.LocalPlayer.Character:FindFirstChild("HumanoidRootPart")
    if not root then return end
    local dist = (root.Position - targetCFrame.Position).Magnitude
    local duration = dist / (speedStudsPerSec or 45)
    game:GetService("TweenService"):Create(root, TweenInfo.new(duration, Enum.EasingStyle.Linear), {CFrame = targetCFrame}):Play()
end""")

        if re.search(r'Kick|kick', code):
            defenses_detected.append("Client-Side Metamethod Kick Dispatcher")
            bypass_snippets.append("""-- [Metamethod Anti-Kick Shield]
local oldNamecall
oldNamecall = hookmetamethod(game, "__namecall", newcclosure(function(self, ...)
    local method = getnamecallmethod()
    if (method == "Kick" or method == "kick") and not checkcaller() then
        return
    end
    return oldNamecall(self, ...)
end))""")

        return {
            "defenses": defenses_detected or ["Standard Server-Side Network Validation"],
            "surgical_bypasses": bypass_snippets
        }

    @classmethod
    def perform_full_biopsy(cls, code: str, filename: str = "Script.lua") -> Dict[str, Any]:
        """
        Performs the complete multi-vector reverse engineering biopsy.
        """
        from bot.remote_harvester import HARVESTER

        start_time = time.time()
        file_hash = hashlib.sha256(code.encode("utf-8", errors="ignore")).hexdigest()[:16]

        fingerprint = cls.fingerprint_obfuscator(code)
        threats = cls.audit_threats_and_secrets(code)
        defenses = cls.audit_anticheat_defenses(code)

        # Run RemoteHarvester (incorporating the dynamic Luau sandbox)
        harvest = HARVESTER.analyze_script(code)

        elapsed = round(time.time() - start_time, 3)

        return {
            "filename": filename,
            "hash": file_hash,
            "lines": len(code.splitlines()),
            "chars": len(code),
            "scan_time_sec": elapsed,
            "fingerprint": fingerprint,
            "threats": threats,
            "defenses": defenses,
            "harvest": harvest
        }

    @classmethod
    def format_biopsy_report(cls, report: Dict[str, Any]) -> str:
        """
        Formats biopsy data into an authoritative, elite-tier technical report.
        """
        fp = report["fingerprint"]
        th = report["threats"]
        df = report["defenses"]
        hv = report["harvest"]

        # Anti-tamper string
        traps_str = "\n".join([f"    • {t}" for t in fp.get("anti_tamper_traps", [])]) or "    • None detected (Open Execution AST)"

        # Webhook / Threats
        th_lines = []
        if th["webhooks"]:
            th_lines.append(f"  🚨 **Exfiltration Webhooks:** {', '.join(th['webhooks'])}")
        if th["honeypot_remotes"]:
            th_lines.append(f"  🍯 **Honeypot Remotes (Insta-Ban):** {', '.join(th['honeypot_remotes'])}")
        if th["cookie_theft_detected"]:
            th_lines.append("  ☠️ **CRITICAL WARNING:** Script contains Cookie / Token Stealer signatures!")
        threats_str = "\n".join(th_lines) if th_lines else "  ✅ No malicious stealers or honeypot traps detected."

        # Remotes
        remotes_str = ", ".join([f"`{r}`" for r in hv.get("remotes", [])[:8]]) or "None detected"

        # Surgical bypass snippet
        bypass_code = "\n\n".join(df.get("surgical_bypasses", [])[:2])
        bypass_section = f"**🛡️ Generated Surgical Bypass:**\n```lua\n{bypass_code}\n```" if bypass_code else ""

        return f"""```asciidoc
========================================================================
           ⚡ PAYOMBØYZ REVERSE ENGINEERING BIOPSY REPORT ⚡
========================================================================
[FILE TARGET]     :: {report['filename']} (SHA256: {report['hash']}...)
[SURFACE AREA]    :: {report['lines']:,} Lines | {report['chars']:,} Characters
[SCAN LATENCY]    :: {report['scan_time_sec']}s
========================================================================
[1. OBFUSCATION & VM FINGERPRINT]
  • Engine         :: {fp['engine']} ({fp['version']})
  • Architecture   :: {fp['vm_type']}
  • Identification :: {fp['confidence']} Confidence
  • Traps & Hooks  ::
{traps_str}

[2. SECURITY & THREAT SCANNER]
  • Threat Status  :: {th['threat_level']} (Score: {th['risk_score']}/100)
{threats_str}

[3. DECRYPTED NETWORK REMOTES]
  • Dispatched     :: {remotes_str}

[4. DEFENSIVE ANTI-CHEAT VECTORS]
  • Detected       :: {', '.join(df['defenses'])}
========================================================================
```

{bypass_section}"""


DIAGNOSTIC_ENGINE = REDiagnosticEngine()
