#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  ⚡ PAYOMBØYZ MASTER FLOWCHART ENGINE v3.0 (O.Z.L.S.R PROTOCOL)
=============================================================================
Autonomous AI Council orchestrator and decision flowchart:
- 8-Task Matrix Routing (DeepSeek, Gemini, ThaiLLM Qwen, BluezyGPT)
- Deterministic Task Classification (<5ms)
- Parallel Dispatch & Multi-Model Result Ranking
- Quality Gate Evaluation (0.0 - 1.0 confidence)
- Autonomous Learner & Knowledge Router Feedback Loop
=============================================================================
"""

from __future__ import annotations
import os
import sys
import re
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from bot.hybrid_router import HYBRID_ROUTER
from bot.knowledge_router import ROUTER as KNOWLEDGE_ROUTER
from bot.autonomous_engineering_learner import AUTONOMOUS_LEARNER
from bot.luraph_topology_inspector import TOPOLOGY_INSPECTOR
from bot.cfg_deflattener import CFGDeflattener


class MasterFlowchartEngine:
    """
    Autonomous Flowchart Dispatcher executing the 8-cell Council Matrix:
    Task              | Primary       | Secondary    | R1 Gate
    ------------------+---------------+--------------+---------
    deobf_simple      | deepseek      | gemini       | False
    deobf_hard        | deepseek      | deepseek     | True
    vm_unwinding      | deepseek      | thaillm      | True
    semantic_name     | gemini        | thaillm      | False
    logic_audit       | thaillm       | gemini       | False
    script_write      | bluezygpt     | gemini       | False
    binary_re         | deepseek      | gemini       | True
    chat              | gemini        | thaillm      | False
    """

    AGENT_MATRIX: Dict[str, Tuple[str, str, bool]] = {
        "deobf_simple":  ("deepseek",  "gemini",   False),
        "deobf_hard":    ("deepseek",  "deepseek",  True),
        "vm_unwinding":  ("deepseek",  "thaillm",   True),
        "semantic_name": ("gemini",    "thaillm",  False),
        "logic_audit":   ("thaillm",   "gemini",   False),
        "script_write":  ("bluezygpt", "gemini",   False),
        "binary_re":     ("deepseek",  "gemini",    True),
        "chat":          ("gemini",    "thaillm",  False),
    }

    def __init__(self):
        self.router = HYBRID_ROUTER
        self.knowledge = KNOWLEDGE_ROUTER
        self.learner = AUTONOMOUS_LEARNER
        self.inspector = TOPOLOGY_INSPECTOR

    def classify_task(self, req: str, code: str = "") -> str:
        """
        Classifies incoming intent and code topology deterministically into 1 of 8 task types.
        """
        r = (req or "").casefold()
        c = (code or "").casefold()

        # 1. Binary / RE intent
        if any(w in r for w in ["pe", "elf", "macho", "exe", "dll", "native", "disassemble", "ghidra", "hopper", "rea", "reverse binary"]):
            return "binary_re"

        # 2. Logic Audit & Invariant checking
        if any(w in r for w in ["audit", "ตรวจบั๊ก", "syntax check", "scope leak", "verify logic", "ตรวจโค้ด"]):
            return "logic_audit"

        # 3. Semantic naming & UI binding
        if any(w in r for w in ["rename", "ตั้งชื่อ", "semantic name", "reconstruct naming", "variable names"]):
            return "semantic_name"

        # 4. Granular Variable & Code Topology Inspection (Luraph v14/v15/v15.1, CFF, VMs)
        if code:
            topo = self.inspector.inspect(code)
            if topo.get("target_type") in ("luraph_v15_1", "luraph_v15_0", "luraph_v14", "cff_generic"):
                return "vm_unwinding"
            if topo.get("target_type") == "moonsec_vm":
                return "deobf_hard"

        # 5. VM / CFF / Hard Deobfuscation Keyword Signatures
        hard_signatures = [
            "luraph", "lph", "moonsec", "clyde", "ironbrew", "moonveil",
            "cff", "state machine", "control flow flattening", "opcode",
            "virtual register", "qz[", "แกะ luraph", "ถอดรหัส luraph",
            "แกะ moonsec", "แกะ vm", "devirtualize"
        ]
        if any(sig in r or sig in c for sig in hard_signatures):
            if any(v in r or v in c for v in ["cff", "state machine", "unwind", "flatten", "devirtualize"]):
                return "vm_unwinding"
            return "deobf_hard"

        # 6. General / Simple Deobfuscation
        if any(w in r for w in ["deobf", "deobfuscate", "ถอดรหัส", "แกะ", "unpack", "decode"]):
            if len(c) > 5000 or any(sig in c for sig in ["while true do", "bit.bxor", "repeat until"]):
                return "deobf_hard"
            return "deobf_simple"

        # 7. Script Writing / Roblox Exploiting
        if any(w in r for w in ["script", "สคริปต์", "เขียนสคริปต์", "blox fruit", "autofarm", "auto farm", "esp", "aimbot", "teleport", "walkspeed"]):
            return "script_write"

        # 8. Default Chat / QA
        return "chat"

    def select_agents(self, task_type: str) -> Tuple[str, str, bool]:
        """
        Returns (primary_provider, secondary_provider, r1_gate_flag) from AGENT_MATRIX.
        """
        return self.AGENT_MATRIX.get(task_type, self.AGENT_MATRIX["chat"])

    async def dispatch_parallel(
        self,
        agents: List[str],
        prompts: List[Dict[str, Any]],
        timeout: float = 120.0
    ) -> List[Dict[str, Any]]:
        """
        Dispatches prompts concurrently across the designated agents with individual exception isolation.
        """
        tasks = []
        for agent, p_info in zip(agents, prompts):
            prompt_str = p_info.get("prompt", "")
            sys_prompt = p_info.get("system_prompt", "You are a senior AI under O.Z.L.S.R Protocol.")
            mode = p_info.get("mode", "deobfuscate")

            tasks.append(
                asyncio.wait_for(
                    asyncio.to_thread(
                        self.router.query_supervised,
                        prompt=prompt_str,
                        user_request=p_info.get("user_request", "Flowchart dispatch"),
                        system_prompt=sys_prompt,
                        mode=mode,
                        preferred_provider=agent
                    ),
                    timeout=timeout
                )
            )

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        cleaned_results: List[Dict[str, Any]] = []

        for idx, res in enumerate(raw_results):
            agent_name = agents[idx] if idx < len(agents) else "unknown"
            if isinstance(res, Exception):
                cleaned_results.append({
                    "provider": agent_name,
                    "success": False,
                    "text": "",
                    "error": str(res),
                    "quality_score": 0.0
                })
            elif isinstance(res, dict):
                text_out = res.get("reply") or res.get("text") or ""
                cleaned_results.append({
                    "provider": agent_name,
                    "success": bool(text_out),
                    "text": text_out,
                    "worker": res.get("worker", agent_name),
                    "quality_score": 0.0
                })

        return cleaned_results

    def quality_gate(self, result: Dict[str, Any], task_type: str) -> float:
        """
        Evaluates the generated output and returns a confidence score between 0.0 and 1.0.
        """
        text = result.get("text", "")
        if not text or not text.strip():
            return 0.0

        score = 0.5

        # Code block presence for technical tasks
        if task_type in ("deobf_simple", "deobf_hard", "vm_unwinding", "script_write", "logic_audit"):
            if "```" in text:
                score += 0.2
            else:
                score -= 0.1

        # Check for lingering obfuscation markers in deobf tasks
        if "deobf" in task_type or task_type == "vm_unwinding":
            dirty_markers = ["while true do local", "QZ[", "LPH_", "bit.bxor", "repeat until true"]
            hits = sum(1 for m in dirty_markers if m in text)
            if hits == 0:
                score += 0.25
            else:
                score -= min(0.3, hits * 0.1)

        # Syntax line length sanity
        lines = len(text.splitlines())
        if lines >= 5:
            score += 0.05
        if lines > 50:
            score += 0.05

        return max(0.0, min(1.0, round(score, 3)))

    def rank_results(self, results: List[Dict[str, Any]], task_type: str) -> Dict[str, Any]:
        """
        Scores all candidate results and returns the highest quality result.
        """
        for r in results:
            if r.get("success"):
                r["quality_score"] = self.quality_gate(r, task_type)

        sorted_results = sorted(results, key=lambda x: x.get("quality_score", 0.0), reverse=True)
        return sorted_results[0] if sorted_results else {"success": False, "text": "", "quality_score": 0.0}

    async def run(self, request: str, code: str = "", mode: str = "auto") -> Dict[str, Any]:
        """
        Master Flowchart execution entrypoint.
        """
        start_t = time.time()
        task_type = self.classify_task(request, code) if mode == "auto" else mode
        primary, secondary, r1_gate = self.select_agents(task_type)

        # Context enrichment from Knowledge Router
        ctx = self.knowledge.find_relevant_context(f"{request} {code[:200]}")
        eng_ctx = self.learner.get_engineering_prompt_context()

        # Step 0: Granular Topology Inspection & CFF Pre-unwinding
        topo = self.inspector.inspect(code) if code else None
        target_code = code

        topo_block = ""
        if topo:
            topo_block = (
                f"\n[ENGINEERING TOPOLOGY AUDIT]:\n"
                f"- Architecture: {topo['target_type']} ({topo['version']})\n"
                f"- Confidence: {topo['confidence']:.2f}\n"
                f"- Recommended Engine: {topo['recommended_engine']}\n"
                f"- Analysis: {topo['explanation']}\n"
            )
            # If generic CFF is detected, attempt immediate deterministic linearization
            if topo["target_type"] == "cff_generic":
                try:
                    linearized, cff_stats = CFGDeflattener.deflatten_code(code)
                    if cff_stats.get("blocks_linearized", 0) >= 2:
                        target_code = linearized
                        topo_block += f"- CFG Deflattener: Successfully linearized {cff_stats['blocks_linearized']} blocks\n"
                except Exception:
                    pass

        # Build prompt payload
        base_prompt = (
            f"User Intent: {request}\n"
            + topo_block
            + (f"\nRelevant Knowledge:\n{ctx[:2000]}\n" if ctx else "")
            + (f"\nEngineering Memory:\n{eng_ctx}\n" if eng_ctx else "")
            + (f"\nTarget Code:\n```lua\n{target_code[:16000]}\n```" if target_code else "")
        )

        prompts = [
            {"prompt": base_prompt, "user_request": request, "mode": "deobfuscate"},
            {"prompt": base_prompt, "user_request": request, "mode": "deobfuscate"}
        ]
        agents = [primary, secondary]

        # Parallel Blast
        candidates = await self.dispatch_parallel(agents, prompts)
        best = self.rank_results(candidates, task_type)

        # R1 Escalation Gate
        if r1_gate and best.get("quality_score", 0.0) < 0.75:
            r1_prompt = (
                "You are the PAYOMBØYZ R1 Deep Reasoning Specialist (O.Z.L.S.R Protocol).\n"
                f"Task: {task_type}. The initial candidates did not meet the 0.75 confidence threshold.\n"
                "Apply rigorous step-by-step Chain-of-Thought reasoning to produce a 100% clean solution:\n"
                f"{base_prompt}"
            )
            try:
                r1_res = await asyncio.to_thread(
                    self.router.query_supervised,
                    prompt=r1_prompt,
                    user_request=f"R1 Escalation: {request}",
                    system_prompt="You are an uncompromising deep reasoning AI under O.Z.L.S.R Protocol.",
                    mode="deobfuscate",
                    preferred_provider="deepseek"
                )
                r1_text = r1_res.get("reply") or r1_res.get("text") or ""
                if r1_text:
                    best = {
                        "provider": "deepseek_r1_escalation",
                        "success": True,
                        "text": r1_text,
                        "worker": r1_res.get("worker", "r1"),
                        "quality_score": 0.95
                    }
            except Exception as e_r1:
                print(f"[FLOWCHART] R1 Escalation skipped: {e_r1}", flush=True)

        elapsed = round(time.time() - start_t, 2)
        return {
            "success": best.get("success", False),
            "task_type": task_type,
            "topology": topo,
            "engine_recommended": topo.get("recommended_engine") if topo else None,
            "primary_agent": primary,
            "secondary_agent": secondary,
            "r1_gate_fired": r1_gate and best.get("provider") == "deepseek_r1_escalation",
            "quality_score": best.get("quality_score", 0.0),
            "output": best.get("text", ""),
            "worker_used": best.get("worker", primary),
            "elapsed": elapsed
        }


# Singleton
FLOWCHART_ENGINE = MasterFlowchartEngine()
