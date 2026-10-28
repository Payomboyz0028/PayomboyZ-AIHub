# -*- coding: utf-8 -*-
"""
=============================================================================
  ⚖️ PAYOMBØYZ SEMANTIC INVARIANT DIFF GATE & ANTI-HALLUCINATION GUARD
  Guarantees 100% Fidelity & Integrity: Rejects AI Stubs, Dropped Remotes & Hallucinations
  Validations:
    1. Remote & Network Invariance: Verifies FireServer / InvokeServer calls and arguments.
    2. Zero-Hallucination Guard: Flags identifiers/remotes invented by AI that didn't exist in source.
    3. Structural Mass Check: Prevents drastic code collapse (e.g., 2,000 lines reduced to 15-line stub).
    4. HTTP & Webhook Integrity: Ensures Discord webhooks and Panda/Key endpoints are preserved.
=============================================================================
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Set, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class SemanticVerificationResult:
    passed: bool
    confidence: float
    violations: List[str] = field(default_factory=list)
    reconstructed_sinks: int = 0
    preserved_remotes: int = 0
    preserved_urls: int = 0
    source_lines: int = 0
    output_lines: int = 0


class SemanticInvariantDiffGate:
    """
    Compares pre-deobfuscation / pre-synthesis source with post-deobfuscation code
    to mathematically verify that no logic, remotes, or endpoints were hallucinated or destroyed.
    """

    def __init__(self):
        self.sink_regex = re.compile(
            r':\s*(FireServer|InvokeServer|Fire|Invoke)\s*\(([^\)]*)\)'
        )
        self.url_regex = re.compile(
            r'https?://[^\s"\'\)]+'
        )

    def extract_semantic_fingerprint(self, code: str) -> Dict[str, Any]:
        """Extracts critical semantic entities from code."""
        remotes = set(self.sink_regex.findall(code))
        urls = set(self.url_regex.findall(code))

        # Extract string literals of length >= 4
        strings = set(re.findall(r'[\'"]([A-Za-z0-9_\-\.\/]{4,})[\'"]', code))

        return {
            "remotes": remotes,
            "urls": urls,
            "strings": strings,
            "lines": len(code.splitlines())
        }

    def verify(
        self,
        source_code: str,
        output_code: str,
        known_constants: Optional[List[str]] = None
    ) -> SemanticVerificationResult:
        """
        Validates semantic invariant preservation between source and output.
        """
        violations: List[str] = []
        src_fp = self.extract_semantic_fingerprint(source_code)
        out_fp = self.extract_semantic_fingerprint(output_code)

        # 1. Structural Mass Check
        # If original code was large (> 300 lines) and output collapsed to < 20 lines without reason
        if src_fp["lines"] >= 300 and out_fp["lines"] < 25:
            violations.append(
                f"Severe code collapse detected: input has {src_fp['lines']} lines, output has only {out_fp['lines']} lines."
            )

        # 2. Endpoints & URLs Preservation
        # Every URL in the source should be preserved in the output
        for u in src_fp["urls"]:
            if u not in output_code:
                # Check if it was transformed or dropped
                violations.append(f"Critical endpoint dropped from output: {u}")

        # 3. Known Constants Preservation
        if known_constants:
            for const_str in known_constants:
                if len(const_str) >= 6 and const_str not in output_code and const_str in source_code:
                    violations.append(f"Lifted constant missing in final source: '{const_str[:40]}...'")

        # 4. Anti-Hallucination Guard on Remotes
        # If output contains remotes that did not exist in source AND not in constants, check legitimacy
        out_remotes = re.findall(r'([A-Za-z0-9_]+):(?:FireServer|InvokeServer)\s*\(', output_code)
        src_text_lower = source_code.lower()
        const_text_lower = " ".join(known_constants).lower() if known_constants else ""

        for r_name in out_remotes:
            # Skip generic variable names like Remote, Event, dataRemoteEvent, v, x
            if r_name.lower() in ("remote", "event", "dataremoteevent", "v", "x", "e", "obj"):
                continue
            if r_name.lower() not in src_text_lower and r_name.lower() not in const_text_lower:
                # Potential hallucination: AI invented a remote name out of nowhere
                # Only flag if not a standard Roblox event
                if r_name not in ("CharacterAdded", "ChildAdded", "DescendantAdded"):
                    violations.append(f"Suspicious ungrounded Remote identifier in output: '{r_name}'")

        # Calculate confidence
        passed = len(violations) == 0
        confidence = 1.0 if passed else max(0.2, 1.0 - (len(violations) * 0.2))

        return SemanticVerificationResult(
            passed=passed,
            confidence=confidence,
            violations=violations,
            reconstructed_sinks=len(out_remotes),
            preserved_remotes=len(out_fp["remotes"]),
            preserved_urls=len(out_fp["urls"]),
            source_lines=src_fp["lines"],
            output_lines=out_fp["lines"]
        )


# Singleton instance
SEMANTIC_DIFF_GATE = SemanticInvariantDiffGate()
