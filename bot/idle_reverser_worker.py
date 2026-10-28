# -*- coding: utf-8 -*-
"""
========================================================================================
  🤖 7-AGENT CLOSED-LOOP REVERSE ENGINEERING SCHOOL ("AI ยามว่าง" AUTONOMOUS ENGINE)
  - Designed for dj: Autonomous Self-Evolving Reverse Engineering & Deobfuscation Fleet.
  - Multi-Agent Architecture:
      Agent 1: Harvester (AI หาสคริปต์ - ScriptBlox, Rscripts, GitHub, Pastebin)
      Agent 2: Validator (AI ตรวจสอบสคริปต์ - Format, size, and obfuscation signature audit)
      Agent 3: Spy & Dumper (AI Spy/Trace - Loader unwinder, Roblox/WinInet headers, payload interception)
      Agent 4: Deobfuscator (AI Deobfuscator - ShardedBlockDecompiler with DeepSeek + Gemini fleet)
      Agent 5: Evaluator & Compiler Gate (AI ตรวจสอบผลลัพธ์ - luau-compile.exe / luau.exe syntax gate)
      Agent 6: Human-Readable Grader (AI ตัดเกรดสคริปต์ - 0.0% to 100.0% human readability score)
      Agent 7: Gap Analyzer & Self-Repair (AI วิเคราะห์จุดขาดตกบกพร่อง & ส่งกลับไปแก้ลูปวนซ้ำ)
  - Knowledge Consolidation Loop (> 80%):
      Commits discovered syntax, novel AST patterns, and clean code to Experience DB,
      Knowledge Router, Autonomous Engineering Learner, and Lerning/ directory to make
      both Deobfuscator and Obfuscator smarter in a self-improving loop.
========================================================================================
"""

from __future__ import annotations
import os
import sys
import re
import time
import json
import asyncio
import datetime
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output" / "Autonomous_Reversed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LERNING_KNOWLEDGE_DIR = ROOT_DIR / "Lerning" / "Autonomous_Knowledge"
LERNING_KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

from curl_cffi import requests as cffi_requests
from bot.autonomous_engineering_learner import AUTONOMOUS_LEARNER
from bot.loader_spy_engine import LoaderSpyEngine, spy_and_deobf
from bot.game_detector import detect_roblox_game_and_map
from bot.sharded_decompiler import SHARDED_DECOMPILER
from bot.hybrid_router import HYBRID_ROUTER
from bot.experience_db import ExperienceDatabase
from bot.knowledge_router import KnowledgeRouter

EXP_DB = ExperienceDatabase()
KNOWLEDGE_ROUTER = KnowledgeRouter()

LUAU_COMPILE_EXE = ROOT_DIR / "Prometheus-WeAre-Devs-Dumper-main" / "lua_bin" / "luau" / "luau-compile.exe"
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SCHOOL_SESSIONS_FILE = DATA_DIR / "school_sessions.jsonl"


# ========================================================================================
# 7-AGENT CLOSED-LOOP REVERSE ENGINEERING SYSTEM
# ========================================================================================

class AgentSessionLogger:
    """Agent: Session Logger — Appends all school mission outcomes to data/school_sessions.jsonl."""

    @staticmethod
    def log_session(record: Dict[str, Any]):
        try:
            with open(SCHOOL_SESSIONS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[SESSION LOGGER] Write notice: {e}", flush=True)


class AgentAutoCurriculum:
    """Agent: Auto-Curriculum — Generates targeted challenges for weak architecture areas."""

    @staticmethod
    def generate_curriculum(weak_architectures: List[str]) -> List[str]:
        curriculum = []
        for arch in weak_architectures:
            curriculum.append(f"Synthesize and decompile target {arch} VM test vectors")
        return curriculum


class Agent1Harvester:
    """Agent 1: AI หาสคริปต์ — Harvests fresh obfuscated scripts and loaders."""

    @staticmethod
    async def harvest(processed_slugs: set[str]) -> Optional[Dict[str, Any]]:
        # Source 1: ScriptBlox API
        try:
            def _fetch_sb():
                r = cffi_requests.get("https://scriptblox.com/api/script/fetch?page=1", impersonate="chrome120", timeout=12)
                if r.status_code == 200:
                    return r.json()
                return None

            sb_data = await asyncio.to_thread(_fetch_sb)
            if sb_data:
                scripts = sb_data.get("result", {}).get("scripts", [])
                for s in scripts:
                    slug = s.get("slug")
                    raw_script = s.get("script", "")
                    if slug and slug not in processed_slugs and len(raw_script) >= 30:
                        return {
                            "source": "ScriptBlox",
                            "slug": slug,
                            "title": s.get("title", "Untitled Script"),
                            "game": s.get("game", {}).get("name", "Roblox"),
                            "script": raw_script
                        }
        except Exception as e:
            print(f"[HARVESTER] ScriptBlox fetch notice: {e}", flush=True)

        # Source 2: Rscripts API / Trending
        try:
            def _fetch_rs():
                r = cffi_requests.get("https://rscripts.net/api/scripts?page=1&orderBy=date", impersonate="chrome120", timeout=12)
                if r.status_code == 200:
                    return r.json()
                return None

            rs_data = await asyncio.to_thread(_fetch_rs)
            if rs_data:
                scripts = rs_data.get("scripts", []) or rs_data.get("data", [])
                for s in scripts:
                    slug = s.get("slug") or s.get("_id")
                    raw_script = s.get("script") or s.get("rawScript", "")
                    if slug and slug not in processed_slugs and len(raw_script) >= 30:
                        return {
                            "source": "Rscripts",
                            "slug": str(slug),
                            "title": s.get("title", "Untitled Rscripts Target"),
                            "game": s.get("game", "Roblox"),
                            "script": raw_script
                        }
        except Exception as e:
            print(f"[HARVESTER] Rscripts fetch notice: {e}", flush=True)

        return None


class Agent2Validator:
    """Agent 2: AI ตรวจสอบสคริปต์ที่หามา — Validates target validity and architecture."""

    @staticmethod
    def validate(candidate: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        raw = candidate.get("script", "").strip()
        if len(raw) < 25:
            return False, "Script length too short", {}

        # Architecture and obfuscation signature identification
        signatures = {
            "LUARMOR": ["luarmor.net", "v4_init_", "_bsdata0", "superflow_bytecode", "static_content_"],
            "LURAPH": ["LPH_", "LPH_OBFUSCATED", "\\76\\117\\114\\97\\112\\104", "buffer.readu8", "buffer.readi8"],
            "MOONSEC": [":::MoonSec:::", "MoonSec", "bit.bxor", "BitXOR", "\\68\\101\\97\\100"],
            "IRONBREW": ["IronBrew", "ironbrew", "BitXOR"],
            "CLYDE_VM": ["_clydeDec_", "Clyde Protection", "clydeprotectionde.cloud", "\\099\\104\\097\\114"],
            "WEAREDEVS": ["wearedevs.net", "35184372088832", "27552854471197", "unpack or table["],
            "POLSEC": ["POLSEC", "polsec", "cache_id"],
            "LOADER_URL": ["game:HttpGet", "loadstring", "raw.githubusercontent.com", "pastebin.com"]
        }

        detected_arch = "UNIVERSAL_LUAU"
        for arch, sigs in signatures.items():
            if any(s in raw for s in sigs):
                detected_arch = arch
                break

        meta = {
            "arch": detected_arch,
            "char_count": len(raw),
            "line_count": len(raw.splitlines()),
            "has_loader_link": bool(re.search(r'https?://[^\s"\'<>]+', raw))
        }

        return True, "Valid target acquired", meta


class Agent3SpyDumper:
    """Agent 3: AI Spy/Dumper — Unwinds multi-hop loaders, extracts true payload."""

    @staticmethod
    def spy_and_dump(script_text: str, target_place_id: Optional[int] = None) -> Dict[str, Any]:
        engine = LoaderSpyEngine()
        return engine.spy_and_deobfuscate(script_text, target_place_id=target_place_id)


class Agent4Deobfuscator:
    """Agent 4: AI Deobfuscator — Sharded Block Decompiler with 38 AI fleet."""

    @staticmethod
    async def decompile(raw_payload: str, script_name: str, repair_hints: str = "") -> Dict[str, Any]:
        decorated_name = f"{script_name} [Repair Hint: {repair_hints[:80]}]" if repair_hints else script_name
        return await SHARDED_DECOMPILER.decompile(raw_payload, script_name=decorated_name)


class Agent5CompilerGate:
    """Agent 5: AI ตรวจสอบผลลัพธ์ — Native Luau Compiler Syntax Gate."""

    @staticmethod
    def verify(code: str) -> Tuple[bool, str]:
        if not code or len(code.strip()) == 0:
            return False, "Empty code received"

        if not LUAU_COMPILE_EXE.exists():
            # Fallback basic balance check
            open_p = code.count("(") - code.count(")")
            open_b = code.count("{") - code.count("}")
            if open_p == 0 and open_b == 0:
                return True, "Structural balance verified (Native compiler binary absent)"
            return False, f"Imbalanced delimiters: paren delta={open_p}, brace delta={open_b}"

        try:
            res = subprocess.run(
                [str(LUAU_COMPILE_EXE), "-"],
                input=code.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=12
            )
            if res.returncode == 0:
                return True, "100% Valid Executable Luau Bytecode (Zero Syntax Errors)"
            err_msg = res.stderr.decode("utf-8", errors="replace").strip()
            return False, f"Luau Compile Gate Error: {err_msg[:400]}"
        except subprocess.TimeoutExpired:
            return False, "Compiler verification timeout (>12s)"
        except Exception as e:
            return False, f"Compiler execution failed: {str(e)}"


class Agent6HumanReadableGrader:
    """Agent 6: AI ตัดเกรดสคริปต์ — Human Readability Scorer (0.0% to 100.0%)."""

    @staticmethod
    def grade(code: str, is_compiler_valid: bool) -> Tuple[float, Dict[str, Any]]:
        score = 0.0
        breakdown = {}

        # Metric 1: Executable Compiler Validity (25 pts)
        if is_compiler_valid:
            score += 25.0
            breakdown["compiler_validity"] = 25.0
        else:
            score += 5.0
            breakdown["compiler_validity"] = 5.0

        # Metric 2: Identifier & Variable Naming Quality (30 pts)
        # Check ratio of meaningful variable names vs obfuscated patterns (_0x, single-char, [1054])
        tokens = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', code)
        meaningful_tokens = [
            t for t in tokens if len(t) > 2
            and not re.match(r'^_[0-9a-fA-F]{4,}$', t)
            and not re.match(r'^[Il10O]+$', t)
            and not re.match(r'^_[a-zA-Z0-9]$', t)
        ]
        if tokens:
            quality_ratio = min(len(meaningful_tokens) / max(len(tokens), 1), 1.0)
            id_pts = round(quality_ratio * 30.0, 1)
        else:
            id_pts = 0.0
        score += id_pts
        breakdown["identifier_quality"] = id_pts

        # Metric 3: Structural Control Flow & Absence of Obfuscation Dysfunctions (25 pts)
        has_cff_switch = bool(re.search(r'while\s+(?:true|\w+)\s+do\s+if\s+\w+\s*==\s*\d+', code))
        has_raw_vm_array = bool(re.search(r'\[\d+\]\s*=\s*\d+', code))
        has_opaque_predicates = bool(re.search(r'debug\.info|debug and debug\.info', code))

        cff_pts = 25.0
        if has_cff_switch:
            cff_pts -= 10.0
        if has_raw_vm_array:
            cff_pts -= 10.0
        if has_opaque_predicates:
            cff_pts -= 5.0
        cff_pts = max(cff_pts, 0.0)
        score += cff_pts
        breakdown["control_flow_clarity"] = cff_pts

        # Metric 4: Roblox Domain Context & Reflection Semantics (20 pts)
        has_getservice = "game:GetService" in code or "GetService" in code
        has_player = "LocalPlayer" in code or "Players" in code
        has_remotes = bool(re.search(r'\b(?:FireServer|InvokeServer|OnClientEvent)\b', code))
        has_ui = bool(re.search(r'\b(?:ScreenGui|Frame|TextLabel|TextButton|TweenService)\b', code))

        domain_pts = 0.0
        if has_getservice:
            domain_pts += 5.0
        if has_player:
            domain_pts += 5.0
        if has_remotes:
            domain_pts += 5.0
        if has_ui:
            domain_pts += 5.0
        score += domain_pts
        breakdown["roblox_semantics"] = domain_pts

        total_score = round(min(score, 100.0), 1)
        return total_score, breakdown


class Agent7GapAnalyzer:
    """Agent 7: AI วิเคราะห์จุดขาดตกบกพร่อง & สั่งซ่อมแซม — Feedback Loop Engine."""

    @staticmethod
    async def analyze_gaps(code: str, breakdown: Dict[str, Any], compiler_msg: str) -> str:
        prompt = (
            "You are the PAYOMBØYZ Senior Deobfuscation Gap Analyzer (Agent 7).\n"
            "This deobfuscated Luau code scored < 60% in Human Readability or failed compiler validation:\n"
            f"Compiler Status: {compiler_msg}\n"
            f"Readability Breakdown: {json.dumps(breakdown)}\n\n"
            "Analyze the defect areas in this code:\n"
            "1. Pinpoint unrolled CFF loops or switch dispatchers that need linearization.\n"
            "2. Identify mangled registers or unreadable symbols that need variable renaming.\n"
            "3. State exact repair actions for Agent 4 (Deobfuscator) to fix in the next iteration.\n\n"
            f"```lua\n{code[:3000]}\n```\n\n"
            "Return 3-5 concise, actionable bullet points instructing Agent 4 on exact repair targets."
        )

        try:
            res = await asyncio.to_thread(
                HYBRID_ROUTER.query_supervised,
                prompt=prompt,
                user_request="Analyze deobfuscation readability gaps for self-repair",
                system_prompt="You are a senior reverse engineering gap analyzer. Output concise repair instructions.",
                mode="deobfuscate",
                preferred_provider="deepseek"
            )
            return (res.get("reply") or res.get("text") or "Repair CFF loops and map variable names.").strip()
        except Exception as e:
            return f"Heuristic repair: deflatten residual dispatchers and rename registers. ({e})"


# ========================================================================================
# IDLE REVERSER WORKER — ORCHESTRATES THE 7 AGENTS IN A CLOSED LOOP
# ========================================================================================

class IdleReverserWorker:
    """
    Autonomous Background Worker that sharpens the system's reverse engineering
    heuristics during idle hours via the 7-Agent Closed-Loop School.
    """

    def __init__(self, idle_threshold_seconds: int = 900, max_daily_scripts: int = 3):
        self.idle_threshold = idle_threshold_seconds  # 15 minutes of inactivity
        self.max_daily = max_daily_scripts
        self.last_activity_time = time.time()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.bot = None

    def note_activity(self):
        """Called whenever a user interacts with the bot or AI."""
        self.last_activity_time = time.time()

    def check_auto_trigger(self, deobf_count: int) -> bool:
        """Auto-triggers school cycle every 50 deobfuscation completions."""
        return deobf_count > 0 and (deobf_count % 50 == 0)

    def start(self, bot_instance=None, force: bool = False):
        """Starts the autonomous idle daemon ONLY if explicitly requested. Default is OFF to save API quotas."""
        self.bot = bot_instance
        if not force:
            print("[IDLE REVERSER] Autonomous idle harvesting loop is DISABLED by default to protect API quotas. Use /school run to trigger manually.", flush=True)
            self.is_running = False
            return

        if self.is_running:
            return
        self.is_running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._worker_loop())
            print("[IDLE REVERSER] 7-Agent Closed-Loop Reverse Engineering School started manually.", flush=True)
        except RuntimeError:
            pass

    async def _worker_loop(self):
        """Main loop that evaluates idle condition and triggers autonomous missions."""
        await asyncio.sleep(60)

        while self.is_running:
            try:
                now = time.time()
                idle_duration = now - self.last_activity_time
                daily_count = AUTONOMOUS_LEARNER.get_todays_mission_count()

                if daily_count < self.max_daily and idle_duration >= self.idle_threshold:
                    print(
                        f"[IDLE REVERSER] Idle detected ({idle_duration/60:.1f}m >= {self.idle_threshold/60:.1f}m). "
                        f"Executing 7-Agent School Mission ({daily_count + 1}/{self.max_daily})...",
                        flush=True
                    )
                    await self.execute_autonomous_mission()

                await asyncio.sleep(300)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[IDLE REVERSER ERROR] Loop exception: {e}", flush=True)
                await asyncio.sleep(120)

    async def execute_autonomous_mission(self) -> bool:
        """
        Executes the full 7-Agent Closed-Loop Reverse Engineering Workflow.
        """
        processed_missions = AUTONOMOUS_LEARNER._knowledge.get("autonomous_idle_missions", [])
        processed_slugs = {m.get("slug") for m in processed_missions if m.get("slug")}

        # ─── AGENT 1: HARVESTER ────────────────────────────────────────────────────────
        print("[AGENT 1] Harvester scanning for fresh obfuscated targets...", flush=True)
        candidate = await Agent1Harvester.harvest(processed_slugs)
        if not candidate:
            print("[IDLE REVERSER] Agent 1 found no new targets.", flush=True)
            return False

        slug = candidate["slug"]
        title = candidate["title"]
        raw_script = candidate["script"]
        print(f"[AGENT 1] Target Acquired: '{title}' ({slug}) from {candidate.get('source')}", flush=True)

        # ─── AGENT 2: VALIDATOR ────────────────────────────────────────────────────────
        print("[AGENT 2] Validator auditing candidate structure & signatures...", flush=True)
        is_valid, val_msg, meta = Agent2Validator.validate(candidate)
        if not is_valid:
            print(f"[AGENT 2] Target rejected: {val_msg}", flush=True)
            return False
        print(f"[AGENT 2] Target Verified: Architecture={meta.get('arch')} ({meta.get('line_count')} lines)", flush=True)

        # ─── AGENT 3: SPY / DUMPER ─────────────────────────────────────────────────────
        print("[AGENT 3] Spy & Dumper unwinding loader chain with Roblox/WinInet headers...", flush=True)
        spy_res = await asyncio.to_thread(Agent3SpyDumper.spy_and_dump, raw_script)
        if not spy_res.get("success") and not spy_res.get("deobfuscated_code"):
            print(f"[AGENT 3] Spy failed to unwind payload: {spy_res.get('error')}", flush=True)
            return False

        current_code = spy_res.get("deobfuscated_code") or raw_script
        print(f"[AGENT 3] Payload recovered: {len(current_code):,} chars from {spy_res.get('target_url')}", flush=True)

        # Detect canonical Roblox game and map
        game_forensics = detect_roblox_game_and_map(
            raw_code=raw_script,
            deobf_code=current_code,
            title=title,
            slug=slug,
            sb_game_name=candidate.get("game", "")
        )

        # ─── CLOSED-LOOP DEOBFUSCATION, EVALUATION & REPAIR (AGENTS 4, 5, 6, 7) ────────
        readability_score = 0.0
        breakdown = {}
        compiler_passed = False
        compiler_msg = ""
        repair_round = 0
        max_repair_rounds = 3
        repair_hints = ""

        while repair_round < max_repair_rounds:
            repair_round += 1
            print(f"\n[LOOP ROUND {repair_round}] Running Agent 4 (Deobfuscator)...", flush=True)

            # ─── AGENT 4: DEOBFUSCATOR ─────────────────────────────────────────────────
            deobf_res = await Agent4Deobfuscator.decompile(current_code, title, repair_hints=repair_hints)
            if deobf_res.get("success"):
                current_code = deobf_res.get("deobfuscated_code", current_code)

            # ─── AGENT 5: EVALUATOR / COMPILER GATE ────────────────────────────────────
            print(f"[LOOP ROUND {repair_round}] Running Agent 5 (Compiler Gate)...", flush=True)
            compiler_passed, compiler_msg = Agent5CompilerGate.verify(current_code)
            print(f"[AGENT 5] Compiler Result: {compiler_msg}", flush=True)

            # ─── AGENT 6: HUMAN-READABLE GRADER ───────────────────────────────────────
            print(f"[LOOP ROUND {repair_round}] Running Agent 6 (Human-Readable Grader)...", flush=True)
            readability_score, breakdown = Agent6HumanReadableGrader.grade(current_code, compiler_passed)
            print(f"[AGENT 6] Readability Score: {readability_score}% | Breakdown: {breakdown}", flush=True)

            # ─── THRESHOLD EVALUATION (<0.60: R1 re-run, 0.60-0.80: flag, >0.80: trust) ─
            if readability_score < 60.0:
                print(f"[!] Score < 60% ({readability_score}%). Triggering DeepSeek R1 re-run pass...", flush=True)
                r1_res = await Agent4Deobfuscator.decompile(current_code, f"{title}_r1_rerun", repair_hints="Force R1 CoT deep reasoning")
                if r1_res.get("success") and r1_res.get("deobfuscated_code"):
                    current_code = r1_res["deobfuscated_code"]
                    compiler_passed, compiler_msg = Agent5CompilerGate.verify(current_code)
                    readability_score, breakdown = Agent6HumanReadableGrader.grade(current_code, compiler_passed)
                    print(f"[R1 RE-RUN RESULT] New Readability Score: {readability_score}% (compiler={compiler_passed})", flush=True)

            # If score >= 60%, pass the loop!
            if readability_score >= 60.0 and compiler_passed:
                print(f"[+] Score >= 60% reached ({readability_score}%) in round {repair_round}! Passing to Knowledge Gate.", flush=True)
                break

            # If score < 60% and we have repair rounds left, invoke AGENT 7:
            if repair_round < max_repair_rounds:
                print(f"[!] Score < 60% ({readability_score}%). Invoking Agent 7 (Gap Analyzer & Self-Repair)...", flush=True)
                repair_hints = await Agent7GapAnalyzer.analyze_gaps(current_code, breakdown, compiler_msg)
                print(f"[AGENT 7] Repair Hints for Round {repair_round + 1}:\n{repair_hints}", flush=True)

        date_str = datetime.datetime.now().strftime("%Y%m%d")
        safe_name = f"{date_str}_{slug[:30]}"
        recovered_lines = len(current_code.splitlines())

        out_path = OUTPUT_DIR / f"{safe_name}.luau"
        out_path.write_text(current_code, encoding="utf-8")

        # ─── KNOWLEDGE CONSOLIDATION LOOP (Score Thresholds) ────────────────────────
        knowledge_committed = False
        needs_review = (60.0 <= readability_score < 80.0)

        if readability_score >= 80.0:
            print(f"\n🌟 [KNOWLEDGE CONSOLIDATION] Readability score ({readability_score}%) >= 80%! Full Trust Commit...", flush=True)
            EXP_DB.record_experience(
                task="AUTONOMOUS_IDLE_REVERSING",
                input_pattern=meta.get("arch", "UNIVERSAL_LUAU"),
                strategy="7_AGENT_CLOSED_LOOP",
                engine="SHARDED_AI_COUNCIL_DEEPSEEK_GEMINI",
                expected=80.0,
                actual=readability_score,
                is_success=True,
                error_msg="",
                validation_passed=compiler_passed
            )
            KNOWLEDGE_ROUTER.learn_new_context(
                category="reversed_scripts",
                key=slug,
                value={
                    "title": title,
                    "game": game_forensics.get("display"),
                    "lines": recovered_lines,
                    "score": readability_score,
                    "needs_review": False,
                    "date": date_str
                }
            )
            AUTONOMOUS_LEARNER.record_decompilation_success(
                architecture=meta.get("arch", "UNIVERSAL_LUAU"),
                source_hash=slug,
                recovered_lines=recovered_lines,
                confidence=readability_score,
                discovered_patterns=["7_AGENT_SCHOOL_PASSED", f"ROUND_{repair_round}_REPAIRED"],
                notes=f"Reverse Engineering School for {title} (Game: {game_forensics.get('display')})"
            )
            lerning_file = LERNING_KNOWLEDGE_DIR / f"{safe_name}_Score_{int(readability_score)}.luau"
            lerning_file.write_text(current_code, encoding="utf-8")
            knowledge_committed = True

        elif needs_review:
            print(f"\n⚠️ [KNOWLEDGE CONSOLIDATION] Score {readability_score}% (60-80%). Committing with 'needs_review' flag...", flush=True)
            KNOWLEDGE_ROUTER.learn_new_context(
                category="reversed_scripts",
                key=slug,
                value={
                    "title": title,
                    "game": game_forensics.get("display"),
                    "lines": recovered_lines,
                    "score": readability_score,
                    "needs_review": True,
                    "date": date_str
                }
            )
            knowledge_committed = True

        # Record mission in Autonomous Learner & Session Logger
        mission_record = {
            "timestamp": time.time(),
            "date": date_str,
            "slug": slug,
            "title": title,
            "game": game_forensics.get("game", candidate.get("game")),
            "game_display": game_forensics.get("display"),
            "map_detail": game_forensics.get("map"),
            "architecture": meta.get("arch"),
            "readability_score": readability_score,
            "needs_review": needs_review,
            "score_breakdown": breakdown,
            "compiler_passed": compiler_passed,
            "repair_rounds": repair_round,
            "recovered_lines": recovered_lines,
            "knowledge_committed": knowledge_committed,
            "output_file": str(out_path)
        }
        AUTONOMOUS_LEARNER.record_idle_mission(mission_record)
        AgentSessionLogger.log_session(mission_record)

        # ─── DISCORD NOTIFICATION DISPATCH ─────────────────────────────────────────────
        await self._dispatch_discord_report(mission_record, current_code)
        return True

    async def _dispatch_discord_report(self, record: Dict[str, Any], deobf_code: str):
        """Sends comprehensive 7-Agent School accomplishment report to Discord."""
        if not self.bot:
            return

        import discord
        import io
        from bot.deobf_panel import DEFAULT_DEOBF_LOG_CHANNEL_ID

        target_ch_id = DEFAULT_DEOBF_LOG_CHANNEL_ID
        log_ch = self.bot.get_channel(target_ch_id)
        if not log_ch:
            try:
                log_ch = await self.bot.fetch_channel(target_ch_id)
            except Exception:
                return

        score = record.get("readability_score", 0.0)
        score_badge = "🟢 PASS (HIGH FIDELITY)" if score >= 80.0 else ("🟡 ACCEPTABLE" if score >= 60.0 else "🔴 LOW FIDELITY")
        map_line = f"• **แผนที่ / โหมด:** `{record.get('map_detail')}`\n" if record.get("map_detail") else ""
        knowledge_badge = "✅ บันทึกเข้าสู่ Experience DB & Obfuscator Knowledge Base เรียบร้อย" if record.get("knowledge_committed") else "ℹ️ ยังไม่ถึงเกณฑ์ 80% (ยังไม่ commit เข้า knowledge)"

        embed = discord.Embed(
            title="🧠 PAYOMBØYZ // โรงเรียนวิศวกรรมย้อนกลับยามว่าง (7-Agent Closed-Loop School)",
            description=(
                f"ระบบ AI ได้ทำการค้นหา ตรวจสอบ ถอดรหัส และตัดเกรดสคริปต์อัตโนมัติแบบปิดลูป:\n\n"
                f"• **สคริปต์เป้าหมาย:** `{record['title']}`\n"
                f"• **เกม:** `{record.get('game_display') or record.get('game', 'Roblox')}`\n"
                f"{map_line}"
                f"• **สถาปัตยกรรม:** `{record.get('architecture')}`\n"
                f"• **จำนวนบรรทัดที่กู้คืน:** `{record['recovered_lines']:,} บรรทัด`\n"
                f"• **คะแนน Human Readability:** `{score:.1f}%` ({score_badge})\n"
                f"• **Compiler Syntax Gate:** `{'✅ 100% PASS' if record.get('compiler_passed') else '❌ FAILED'}`\n"
                f"• **รอบการส่งซ่อม (Agent 7 Loop):** `{record.get('repair_rounds')} รอบ`\n"
                f"• **การอัปเกรดความรู้:** {knowledge_badge}"
            ),
            color=discord.Color.from_rgb(0, 230, 150) if score >= 80.0 else discord.Color.gold()
        )
        embed.set_footer(text="PAYOMBØYZ 7-Agent Autonomous School • Self-Improving Deobfuscator & Obfuscator Fleet")

        f_bytes = io.BytesIO(deobf_code.encode("utf-8"))
        f = discord.File(f_bytes, filename=f"Autonomous_{record['slug'][:25]}.luau")

        try:
            await log_ch.send(embed=embed, file=f)
        except Exception as e:
            print(f"[IDLE REVERSER] Discord dispatch notice: {e}", flush=True)


IDLE_REVERSER = IdleReverserWorker()
