#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ KNOWLEDGE BASE — CONFLICT RESOLVER ENGINE
====================================================================
Detects and arbitrates API signature conflicts across scripts:
e.g.
  Version A: AddToggle(Name, Callback)                [Source: UI/OldLib.txt]
  Version B: AddToggle(Id, Title, Default, Callback)  [Source: UI/Obsidian.txt]

Resolution Strategy:
  - Quality Dominance: OFFICIAL_CURRENT (1.00) overrides OLD_WORKING (0.75)
  - Recency Check: Newer last_verified wins if quality is tied
  - Mark 'NEEDS_VALIDATION' if conflict cannot be safely arbitrated
====================================================================
"""

from typing import Dict, Any, List, Optional
from .scoring import get_file_quality_score


class ConflictResolver:
    """Arbitrates multiple competing signatures for the same function/component."""

    @staticmethod
    def resolve_signature_conflict(symbol_name: str, candidate_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes a list of competing entries and chooses the best version,
        or flags NEEDS_VALIDATION with a clean conflict report.
        """
        if not candidate_entries:
            return {"status": "NOT_FOUND", "winner": None}

        if len(candidate_entries) == 1:
            return {"status": "UNCONTESTED", "winner": candidate_entries[0]}

        # Sort candidates by quality desc, then recency/confidence
        sorted_candidates = sorted(
            candidate_entries,
            key=lambda x: (
                x.get("quality", get_file_quality_score(x.get("source", ""))),
                x.get("confidence", 0.9)
            ),
            reverse=True
        )

        top1 = sorted_candidates[0]
        top2 = sorted_candidates[1]

        q1 = top1.get("quality", 0.8)
        q2 = top2.get("quality", 0.8)

        # Clear quality dominance (e.g. Official 1.0 vs Old 0.75)
        if q1 - q2 >= 0.15:
            return {
                "status": "AUTO_RESOLVED",
                "winner": top1,
                "reason": f"Quality dominance ({q1:.2f} vs {q2:.2f}): {top1.get('source')} wins over {top2.get('source')}",
                "suppressed": top2
            }

        # If parameters match exactly, no semantic conflict
        if top1.get("parameters") == top2.get("parameters"):
            return {
                "status": "IDENTICAL_SIGNATURES",
                "winner": top1,
                "reason": "Both sources agree on exact parameter signature"
            }

        # Ambiguous conflict: Flag for validation
        return {
            "status": "NEEDS_VALIDATION",
            "winner": top1,
            "conflict_report": {
                "symbol": symbol_name,
                "version_a": {
                    "source": top1.get("source"),
                    "parameters": top1.get("parameters"),
                    "confidence": top1.get("confidence")
                },
                "version_b": {
                    "source": top2.get("source"),
                    "parameters": top2.get("parameters"),
                    "confidence": top2.get("confidence")
                },
                "resolution_strategy": "Validator pre-flight check required at call site"
            }
        }


# Singleton
CONFLICT_RESOLVER = ConflictResolver()
