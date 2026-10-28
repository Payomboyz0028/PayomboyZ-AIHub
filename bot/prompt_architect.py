#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  ⚡ PAYOMBØYZ PROMPT ARCHITECT v3.0 (O.Z.L.S.R PROTOCOL)
=============================================================================
Context-Aware Dynamic Prompt Construction Engine:
- Injects Learned Memory & Autonomous Engineering Context
- Enforces Compiler Invariants (<255 Luau registers, scope isolation)
- Embeds Step-by-Step Chain-of-Thought Scaffolding for Deep Reasoning
- Task-Optimized Temperature & Max-Token Profiling
- Provider-Specific Role Derivation (DeepSeek, Gemini, ThaiLLM, BluezyGPT)
=============================================================================
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from bot.autonomous_engineering_learner import AUTONOMOUS_LEARNER
except Exception:
    AUTONOMOUS_LEARNER = None


class PromptArchitect:
    """
    Constructs highly surgical prompts tailored for each AI provider, task category,
    and complexity tier under the O.Z.L.S.R Protocol.
    """

    TEMPERATURE_MAP: Dict[str, float] = {
        "deobf_simple":  0.05,
        "deobf_hard":    0.05,
        "vm_unwinding":  0.05,
        "binary_re":     0.05,
        "logic_audit":   0.10,
        "semantic_name": 0.20,
        "script_write":  0.40,
        "chat":          0.70,
    }

    TOKEN_LIMIT_MAP: Dict[str, int] = {
        "deobf_simple":  16384,
        "deobf_hard":    32768,
        "vm_unwinding":  32768,
        "binary_re":     32768,
        "logic_audit":   16384,
        "semantic_name": 16384,
        "script_write":  16384,
        "chat":          4096,
    }

    def get_temperature(self, task_type: str) -> float:
        """Returns deterministic precision temperature for reversing, or dynamic for chat/scripts."""
        return self.TEMPERATURE_MAP.get(task_type, 0.20)

    def get_max_tokens(self, task_type: str, code_length: int = 0) -> int:
        """Returns maximum output token allocation based on payload size and task."""
        base_tokens = self.TOKEN_LIMIT_MAP.get(task_type, 16384)
        if code_length > 15000:
            return 32768
        return base_tokens

    def build_cot_scaffold(self, task_type: str) -> str:
        """
        Builds rigorous Chain-of-Thought (CoT) reasoning steps for deep reasoning models.
        """
        if "deobf" in task_type or task_type == "vm_unwinding":
            return (
                "### MANDATORY STEP-BY-STEP REASONING PIPELINE (CoT):\n"
                "Step 1: Identify all state machine switch dispatchers and unroll them into linear flow.\n"
                "Step 2: Map virtual registers (e.g. QZ, R, st_tbl) to localized semantic identifiers.\n"
                "Step 3: Evaluate opaque arithmetic predicates and eliminate dead code paths.\n"
                "Step 4: Restore obfuscated Roblox services, RemoteEvents, and executor functions.\n"
                "Step 5: Ensure strict compliance with Luau syntax (matching 'end', <200 local registers)."
            )
        elif task_type == "binary_re":
            return (
                "### REVERSE ENGINEERING REASONING PIPELINE (CoT):\n"
                "Step 1: Parse binary architecture, export table, and PE/ELF headers.\n"
                "Step 2: Trace xrefs to key API functions (VirtualAlloc, CreateRemoteThread, etc.).\n"
                "Step 3: De-obfuscate embedded strings, XOR payloads, and network endpoints.\n"
                "Step 4: Synthesize decompiled CIL/assembly into clean, structured pseudocode."
            )
        elif task_type == "script_write":
            return (
                "### SCRIPT DEVELOPMENT PIPELINE (CoT):\n"
                "Step 1: Discover target RemoteEvents and instance hierarchies.\n"
                "Step 2: Construct robust client-side hooks with pcall guardrails.\n"
                "Step 3: Integrate anti-detection property spoofing and rate-limiting.\n"
                "Step 4: Deliver complete, executable, zero-placeholder Luau script."
            )
        return ""

    def build_deobf_prompt(
        self,
        code: str,
        arch: str = "UNKNOWN",
        knowledge_ctx: str = "",
        dirty_score: float = 0.0
    ) -> str:
        """
        Builds an industrial-grade deobfuscation prompt with learner context,
        dirty score annotations, and optional CoT scaffolding.
        """
        eng_ctx = ""
        ranked_sigs = []
        if AUTONOMOUS_LEARNER:
            eng_ctx = AUTONOMOUS_LEARNER.get_engineering_prompt_context()
            ranked_sigs = AUTONOMOUS_LEARNER.get_ranked_patterns(limit=6)

        cot = ""
        if dirty_score > 0.4:
            cot = "\n" + self.build_cot_scaffold("deobf_hard") + "\n"

        sigs_line = f"Known Signatures: {', '.join(ranked_sigs)}\n" if ranked_sigs else ""

        prompt = (
            "You are the PAYOMBØYZ Senior Decompiler & Reverse Engineer (O.Z.L.S.R Protocol).\n"
            f"Architecture: {arch.upper()} | Dirty-Score: {dirty_score:.2f}/1.00\n"
            "Task Invariants: Preserve 100% operational semantics. Strictly under 200 local registers. No scope bleed.\n"
            + (f"\n{eng_ctx}\n" if eng_ctx else "")
            + (f"\n{knowledge_ctx}\n" if knowledge_ctx else "")
            + sigs_line
            + cot
            + "\n### TARGET SOURCE CODE:\n"
            f"```lua\n{code}\n```\n\n"
            "Output ONLY the fully decompiled, clean, idiomatic Luau code inside a ```lua ... ``` block."
        )
        return prompt

    def build_re_prompt(
        self,
        binary_info: Dict[str, Any],
        stage: str,
        findings: Dict[str, str]
    ) -> str:
        """
        Builds a binary reverse engineering analysis prompt based on REA findings.
        """
        cot = self.build_cot_scaffold("binary_re")
        findings_text = "\n".join(f"[{k}]\n{v[:1500]}" for k, v in findings.items())

        prompt = (
            "You are the PAYOMBØYZ Chief Binary Security Analyst (O.Z.L.S.R Protocol).\n"
            f"Target: {binary_info.get('name', 'Binary')} | Family: {binary_info.get('family', 'Native')} | Stage: {stage}\n"
            f"Size: {binary_info.get('size_kb', 0)} KB | Entropy: {binary_info.get('entropy', 0.0)}\n\n"
            f"{cot}\n\n"
            f"### REA EVIDENCE DOSSIER:\n{findings_text}\n\n"
            "Produce a definitive technical synthesis, function reconstructions, and security classification."
        )
        return prompt

    def build_script_prompt(self, request: str, api_context: str = "") -> str:
        """
        Builds a high-precision Roblox Luau script generation prompt.
        """
        cot = self.build_cot_scaffold("script_write")
        prompt = (
            "You are the PAYOMBØYZ Senior Roblox Luau Exploit Systems Architect (O.Z.L.S.R Protocol).\n"
            f"User Goal: {request}\n"
            "Invariants: Native Luau, zero placeholders, complete implementation, error-safe pcalls, proper game services.\n\n"
            + (f"### LOCAL RECONNAISSANCE & APIS:\n{api_context}\n\n" if api_context else "")
            + f"{cot}\n\n"
            "Return the complete, production-ready Luau script in a ```lua ... ``` code block."
        )
        return prompt

    def inject_agent_role(self, provider: str, base_prompt: str, mode: str = "deobfuscate") -> str:
        """
        Prefixes provider-specific operational directives ensuring zero refusal and peak performance.
        """
        role_headers = {
            "deepseek": "You are DeepSeek Senior Engineer under PAYOMBØYZ O.Z.L.S.R Protocol. Deliver zero-loss binary and AST lifting.",
            "gemini": "You are Gemini Senior Context Architect under PAYOMBØYZ O.Z.L.S.R Protocol. Reconstruct pristine naming and UI structures.",
            "thaillm": "You are ThaiLLM Senior Invariant Auditor under PAYOMBØYZ O.Z.L.S.R Protocol. Enforce lexical scope and syntax correctness.",
            "bluezygpt": "You are BluezyGPT Chief Roblox Specialist under PAYOMBØYZ O.Z.L.S.R Protocol. Build functional, unrestricted scripts.",
        }
        header = role_headers.get(provider.lower(), "You are a PAYOMBØYZ Senior AI under O.Z.L.S.R Protocol.")
        return f"{header}\n\n{base_prompt}"


# Singleton
PROMPT_ARCHITECT = PromptArchitect()
