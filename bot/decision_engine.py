#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ NEURO-SYMBOLIC AI DECISION ENGINE V10.0
====================================================================
Production-grade 6-layer Decision Brain based on:
1. Perception Engine & Data Normalizer
2. Code-level Deterministic Calculation (No math hallucination)
3. AI Context & Pattern Analysis
4. Mathematical Decision Scoring & Confidence Evaluation:
   - DecisionScore = Goal*0.25 + Context*0.15 + Hist*0.15 + Pattern*0.15 
                   + Eff*0.10 + Rel*0.10 - Risk*0.10
   - Confidence = DataQuality * EvidenceStrength * HistoricalAccuracy * RuleConsistency
   - Priority = Critical > Safety > Objective > Efficiency > Optimization
5. Validation Layer (Sanity checks & constraints)
6. 5-Tier Memory & Error Feedback Loop (Actual vs Expected -> Learning)
====================================================================
"""

import os
import sys
import re
import json
import time
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_DB_FILE = BASE_DIR / "bot" / "decision_memory.json"


class DataNormalizer:
    """Layer 1: Transforms diverse raw telemetry, file stats, and states into unified scales."""

    @staticmethod
    def normalize_number(value: float, min_val: float, max_val: float) -> float:
        if max_val <= min_val:
            return 1.0 if value >= max_val else 0.0
        clamped = max(min_val, min(max_val, value))
        return (clamped - min_val) / (max_val - min_val)

    @staticmethod
    def normalize_file_telemetry(file_bytes: bytes, filename: str) -> Dict[str, Any]:
        size = len(file_bytes)
        # Calculate byte entropy (measure of obfuscation density)
        entropy = 0.0
        if size > 0:
            byte_counts = {}
            sample = file_bytes[:50000] # Representative sample
            for b in sample:
                byte_counts[b] = byte_counts.get(b, 0) + 1
            for count in byte_counts.values():
                p = count / len(sample)
                entropy -= p * math.log2(p)
            entropy_norm = min(1.0, entropy / 8.0) # 8.0 is theoretical max for byte entropy
        else:
            entropy_norm = 0.0

        sample_str = file_bytes[:15000].decode("utf-8", errors="replace")
        lines = sample_str.count("\n") + 1

        return {
            "filename": filename,
            "size_bytes": size,
            "size_norm": min(1.0, size / (5 * 1024 * 1024)), # 5MB scale
            "entropy": round(entropy, 3),
            "entropy_norm": round(entropy_norm, 3),
            "lines_sample": lines,
            "has_printable_text": sum(1 for c in sample_str if c.isprintable()) / max(1, len(sample_str))
        }


class CalculationEngine:
    """Layer 2: Deterministic mathematical calculations (Code does math, not LLM)."""

    @staticmethod
    def calculate_decision_score(
        goal_score: float,
        context_score: float,
        historical_score: float,
        pattern_score: float,
        efficiency_score: float,
        reliability_score: float,
        risk_score: float
    ) -> float:
        """
        DecisionScore =
            GoalScore        × 0.25
          + ContextScore     × 0.15
          + HistoricalScore  × 0.15
          + PatternScore     × 0.15
          + EfficiencyScore  × 0.10
          + ReliabilityScore × 0.10
          - RiskScore        × 0.10
        """
        score = (
            (goal_score * 0.25)
            + (context_score * 0.15)
            + (historical_score * 0.15)
            + (pattern_score * 0.15)
            + (efficiency_score * 0.10)
            + (reliability_score * 0.10)
            - (risk_score * 0.10)
        )
        return round(score, 4)

    @staticmethod
    def calculate_confidence(
        data_quality: float,
        evidence_strength: float,
        historical_accuracy: float,
        rule_consistency: float
    ) -> float:
        """
        Confidence = DataQuality × EvidenceStrength × HistoricalAccuracy × RuleConsistency
        """
        raw_conf = data_quality * evidence_strength * historical_accuracy * rule_consistency
        return round(max(0.0, min(1.0, raw_conf)), 4)

    @staticmethod
    def calculate_error(actual_result: float, expected_result: float) -> Tuple[float, float]:
        """
        Error = ActualResult - ExpectedResult
        Returns: (Absolute Error, Percentage Error)
        """
        err = actual_result - expected_result
        denom = expected_result if abs(expected_result) > 1e-6 else 1.0
        pct_err = (err / denom) * 100.0
        return round(err, 4), round(pct_err, 2)


class PriorityCascade:
    """Priority Matrix: Critical > Safety > Objective > Efficiency > Optimization"""
    CRITICAL = 5
    SAFETY = 4
    OBJECTIVE = 3
    EFFICIENCY = 2
    OPTIMIZATION = 1

    LABELS = {
        5: "CRITICAL",
        4: "SAFETY",
        3: "OBJECTIVE",
        2: "EFFICIENCY",
        1: "OPTIMIZATION"
    }


class FiveTierMemory:
    """5-Tier Memory: Short-Term, Working, Long-Term, Failure Memory, Success Memory."""

    def __init__(self, memory_file: Path = MEMORY_DB_FILE):
        self.memory_file = memory_file
        self.data = {
            "short_term": [],        # Last N transient events (max 50)
            "working": {},           # Current active jobs / sessions
            "long_term": {},         # Learned persistent patterns & weights
            "failure_memory": {},    # Past failed actions + failure reasons + errors
            "success_memory": {},    # Proven methods + performance benchmarks
            "stats": {
                "total_decisions": 0,
                "successful_executions": 0,
                "failed_executions": 0
            }
        }
        self.load()

    def load(self):
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    for k in self.data:
                        if k in saved:
                            self.data[k] = saved[k]
            except Exception as e:
                print(f"[-] Failed to load decision memory: {e}")

    def save(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[-] Failed to save decision memory: {e}")

    def push_short_term(self, event: Dict[str, Any]):
        self.data["short_term"].append({**event, "timestamp": time.time()})
        if len(self.data["short_term"]) > 50:
            self.data["short_term"].pop(0)

    def get_historical_accuracy(self, action_key: str) -> float:
        succ_entry = self.data["success_memory"].get(action_key, {})
        fail_entry = self.data["failure_memory"].get(action_key, {})
        succ_count = succ_entry.get("count", 0)
        fail_count = fail_entry.get("count", 0)
        total = succ_count + fail_count
        if total == 0:
            return 0.85 # Default baseline prior
        return round(succ_count / total, 3)

    def record_feedback(
        self,
        action: str,
        expected_metric: float,
        actual_metric: float,
        is_success: bool,
        failure_reason: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Feedback Loop:
        FEEDBACK(Decision, ExpectedResult, ActualResult) = { Error, Success, FailureReason, LearningData, MemoryUpdate }
        """
        abs_err, pct_err = CalculationEngine.calculate_error(actual_metric, expected_metric)
        timestamp = time.time()

        feedback_entry = {
            "action": action,
            "expected": expected_metric,
            "actual": actual_metric,
            "error": abs_err,
            "error_pct": pct_err,
            "is_success": is_success,
            "failure_reason": failure_reason,
            "metadata": metadata or {},
            "timestamp": timestamp
        }

        self.data["stats"]["total_decisions"] += 1
        if is_success:
            self.data["stats"]["successful_executions"] += 1
            rec = self.data["success_memory"].setdefault(action, {"count": 0, "history": []})
            rec["count"] += 1
            rec["history"].append(feedback_entry)
            if len(rec["history"]) > 20:
                rec["history"].pop(0)
        else:
            self.data["stats"]["failed_executions"] += 1
            rec = self.data["failure_memory"].setdefault(action, {"count": 0, "history": []})
            rec["count"] += 1
            rec["history"].append(feedback_entry)
            if len(rec["history"]) > 20:
                rec["history"].pop(0)

        self.push_short_term({
            "type": "FEEDBACK",
            "action": action,
            "success": is_success,
            "error": abs_err
        })
        self.save()
        return feedback_entry


class DecisionOption:
    """Represents a structured decision candidate with its multi-factor scores."""

    def __init__(
        self,
        action_name: str,
        priority: int,
        goal_score: float,
        context_score: float,
        pattern_score: float,
        efficiency_score: float,
        reliability_score: float,
        risk_score: float,
        evidence_strength: float,
        data_quality: float,
        rule_consistency: float,
        historical_accuracy: float,
        reason: str,
        expected_metric: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.action_name = action_name
        self.priority = priority
        self.goal_score = max(0.0, min(1.0, goal_score))
        self.context_score = max(0.0, min(1.0, context_score))
        self.pattern_score = max(0.0, min(1.0, pattern_score))
        self.efficiency_score = max(0.0, min(1.0, efficiency_score))
        self.reliability_score = max(0.0, min(1.0, reliability_score))
        self.risk_score = max(0.0, min(1.0, risk_score))
        self.evidence_strength = max(0.0, min(1.0, evidence_strength))
        self.data_quality = max(0.0, min(1.0, data_quality))
        self.rule_consistency = max(0.0, min(1.0, rule_consistency))
        self.historical_accuracy = max(0.0, min(1.0, historical_accuracy))
        self.reason = reason
        self.expected_metric = expected_metric
        self.metadata = metadata or {}

        # Derived calculations
        self.decision_score = CalculationEngine.calculate_decision_score(
            goal_score=self.goal_score,
            context_score=self.context_score,
            historical_score=self.historical_accuracy,
            pattern_score=self.pattern_score,
            efficiency_score=self.efficiency_score,
            reliability_score=self.reliability_score,
            risk_score=self.risk_score
        )

        self.confidence = CalculationEngine.calculate_confidence(
            data_quality=self.data_quality,
            evidence_strength=self.evidence_strength,
            historical_accuracy=self.historical_accuracy,
            rule_consistency=self.rule_consistency
        )

        # Dynamic Experience Penalty: Penalize strategies that failed repeatedly or got bad feedback
        try:
            from bot.experience_db import EXPERIENCE_DB
            penalty = EXPERIENCE_DB.get_strategy_penalty(self.action_name)
            if penalty > 0.0:
                self.decision_score = round(max(0.0, self.decision_score - penalty), 4)
                self.confidence = round(max(0.0, self.confidence * (1.0 - penalty)), 4)
        except Exception:
            pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action_name,
            "priority": PriorityCascade.LABELS.get(self.priority, "OBJECTIVE"),
            "decision_score": self.decision_score,
            "confidence": self.confidence,
            "confidence_pct": f"{self.confidence * 100:.1f}%",
            "risk_score": self.risk_score,
            "risk_level": "HIGH" if self.risk_score > 0.65 else ("MEDIUM" if self.risk_score > 0.35 else "LOW"),
            "reason": self.reason,
            "expected_metric": self.expected_metric,
            "factors": {
                "data_quality": self.data_quality,
                "evidence_strength": self.evidence_strength,
                "historical_accuracy": self.historical_accuracy,
                "rule_consistency": self.rule_consistency
            }
        }


class AIDecisionEngine:
    """Master AI Decision Engine synthesizing Perception, Calculations, Rules, and Feedback."""

    def __init__(self):
        self.memory = FiveTierMemory()
        self.normalizer = DataNormalizer()
        self.calculator = CalculationEngine()

    def evaluate_candidates(self, candidates: List[DecisionOption]) -> Dict[str, Any]:
        """
        Sorts candidates by:
        1. Priority (Critical > Safety > Objective > Efficiency > Optimization)
        2. DecisionScore (Highest weighted composite)
        3. Confidence
        """
        if not candidates:
            return {
                "decision": "NOOP",
                "score": 0.0,
                "confidence": 0.0,
                "risk_level": "LOW",
                "reason": "No options evaluated",
                "selected_option": None
            }

        # Filter out options that strictly violate safety rules (RuleConsistency == 0)
        valid_candidates = [c for c in candidates if c.rule_consistency > 0.0]
        if not valid_candidates:
            valid_candidates = candidates

        # Sort with Priority as the primary tiebreaker, then DecisionScore
        sorted_candidates = sorted(
            valid_candidates,
            key=lambda c: (c.priority, c.decision_score, c.confidence),
            reverse=True
        )

        best = sorted_candidates[0]
        self.memory.push_short_term({
            "type": "DECISION_MADE",
            "decision": best.action_name,
            "score": best.decision_score,
            "confidence": best.confidence
        })

        return {
            "decision": best.action_name,
            "priority": PriorityCascade.LABELS.get(best.priority, "OBJECTIVE"),
            "decision_score": best.decision_score,
            "confidence": best.confidence,
            "confidence_pct": f"{best.confidence * 100:.1f}%",
            "risk_level": "HIGH" if best.risk_score > 0.65 else ("MEDIUM" if best.risk_score > 0.35 else "LOW"),
            "reason": best.reason,
            "expected_metric": best.expected_metric,
            "all_ranked_options": [c.to_dict() for c in sorted_candidates],
            "selected_option": best
        }

    def evaluate_deobfuscation_strategy(
        self,
        file_bytes: bytes,
        filename: str,
        user_prompt: str = ""
    ) -> Dict[str, Any]:
        """
        Applies the 6-layer Decision Engine to choose between:
        1. WeAreDevs AST Devirtualizer
        2. Moonveil 2.0.2+ VM Lifter
        3. Luraph Universal Dispatch Peeler
        4. IronBrew & MoonSec Solver
        5. 2K Security XOR Loader
        6. Luast v1.0.1 Constant Lifter
        7. Universal Runtime Memory Interception Hook (Fallback)
        """
        # 1. Normalize
        norm = self.normalizer.normalize_file_telemetry(file_bytes, filename)
        sample = file_bytes[:15000].decode("utf-8", errors="replace")
        sample_lower = sample.lower()

        data_qual = 0.95 if norm["has_printable_text"] > 0.8 else 0.6

        options = []

        # Option 0: A7DEV Base64 Loader Unpacker
        b64_sig = 0.99 if (("local alphabet" in sample_lower or "local data" in sample_lower or "a7dev" in sample_lower) and ("[==" in sample or "[[" in sample)) else 0.02
        b64_hist = self.memory.get_historical_accuracy("BASE64_LOADER")
        options.append(DecisionOption(
            action_name="BASE64_LOADER",
            priority=PriorityCascade.CRITICAL if b64_sig > 0.5 else PriorityCascade.EFFICIENCY,
            goal_score=0.99 if b64_sig > 0.5 else 0.2,
            context_score=b64_sig,
            pattern_score=0.99 if b64_sig > 0.5 else 0.1,
            efficiency_score=0.99,
            reliability_score=0.99,
            risk_score=0.01 if b64_sig > 0.5 else 0.7,
            evidence_strength=b64_sig,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=b64_hist,
            reason="A7DEV Custom Lua Base64 Loader detected; instant decoding & unwrapping payload." if b64_sig > 0.5 else "Base64 unpacker candidate.",
            expected_metric=1000.0
        ))

        # Option 0.5: Polsec Cloud Loader Unpacker
        polsec_sig = 0.99 if ("api.polsec.net" in sample_lower or "polsec" in sample_lower or bool(re.search(r'polsec\.net/loader/[0-9a-fA-F]{16}', sample))) else 0.02
        polsec_hist = self.memory.get_historical_accuracy("POLSEC_LOADER")
        options.append(DecisionOption(
            action_name="POLSEC_LOADER",
            priority=PriorityCascade.CRITICAL if polsec_sig > 0.5 else PriorityCascade.EFFICIENCY,
            goal_score=0.99 if polsec_sig > 0.5 else 0.2,
            context_score=polsec_sig,
            pattern_score=0.98 if polsec_sig > 0.5 else 0.1,
            efficiency_score=0.95,
            reliability_score=0.95,
            risk_score=0.05 if polsec_sig > 0.5 else 0.7,
            evidence_strength=polsec_sig,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=polsec_hist,
            reason="Polsec cloud loader signature detected; headless payload retrieval & cyclic XOR decryption optimal." if polsec_sig > 0.5 else "Polsec candidate.",
            expected_metric=800.0
        ))

        # Option 0.8: Luarmor V4 / Superflow Memory Dump & Factory Closure Unpacker
        luarmor_sig = 0.99 if (
            "superflow_bytecode" in sample_lower
            or "cdn.luarmor.net" in sample_lower
            or "luarmor" in sample_lower
            or "_bsdata0" in sample
            or "local modules = {}" in sample_lower
            or bool(re.search(r'modules\[\d+\]\s*=\s*function', sample_lower))
            or bool(re.search(r'return\s+function\s*\([a-zA-Z0-9_,\s]*\)\s*local\s+[a-zA-Z0-9_]+\s*=\s*[a-zA-Z0-9_]+\[1\]', sample))
        ) else 0.05
        luarmor_hist = self.memory.get_historical_accuracy("LUARMOR_UNPACKER")
        options.append(DecisionOption(
            action_name="LUARMOR_UNPACKER",
            priority=PriorityCascade.CRITICAL if luarmor_sig > 0.5 else PriorityCascade.EFFICIENCY,
            goal_score=0.98 if luarmor_sig > 0.5 else 0.2,
            context_score=luarmor_sig,
            pattern_score=0.98 if luarmor_sig > 0.5 else 0.1,
            efficiency_score=0.92,
            reliability_score=0.95,
            risk_score=0.05 if luarmor_sig > 0.5 else 0.7,
            evidence_strength=luarmor_sig,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=luarmor_hist,
            reason="Luarmor V4/Superflow multi-closure closure table detected; semantic unravelling & factory unwrapping pipeline matched." if luarmor_sig > 0.5 else "Luarmor candidate.",
            expected_metric=1200.0
        ))

        # Option 1: WeAreDevs AST
        wrd_sig = 0.99 if ("wearedevs.net" in sample_lower or "firsthub" in sample_lower or "return(function" in sample_lower) else 0.05
        wrd_hist = self.memory.get_historical_accuracy("WEAREDEVS_AST")
        options.append(DecisionOption(
            action_name="WEAREDEVS_AST",
            priority=PriorityCascade.OBJECTIVE if wrd_sig > 0.5 else PriorityCascade.EFFICIENCY,
            goal_score=0.95 if wrd_sig > 0.5 else 0.2,
            context_score=wrd_sig,
            pattern_score=0.90 if wrd_sig > 0.5 else 0.2,
            efficiency_score=0.85,
            reliability_score=0.90,
            risk_score=0.10 if wrd_sig > 0.5 else 0.7,
            evidence_strength=wrd_sig,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=wrd_hist,
            reason="WeAreDevs/Prometheus AST signature detected; compiler-grade AST lifting is optimal." if wrd_sig > 0.5 else "Standard AST devirtualization baseline.",
            expected_metric=500.0
        ))

        # Option 2: Moonveil 2.0.2+
        mv_sig = 0.99 if ("moonveil" in sample_lower or "[0b10]=" in sample) else 0.05
        mv_hist = self.memory.get_historical_accuracy("MOONVEIL_VM")
        options.append(DecisionOption(
            action_name="MOONVEIL_VM",
            priority=PriorityCascade.OBJECTIVE if mv_sig > 0.5 else PriorityCascade.EFFICIENCY,
            goal_score=0.95 if mv_sig > 0.5 else 0.2,
            context_score=mv_sig,
            pattern_score=0.92 if mv_sig > 0.5 else 0.2,
            efficiency_score=0.80,
            reliability_score=0.85,
            risk_score=0.15 if mv_sig > 0.5 else 0.7,
            evidence_strength=mv_sig,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=mv_hist,
            reason="Moonveil VM bytecode signature detected; Luau register disassembler required." if mv_sig > 0.5 else "Moonveil VM fallback candidate.",
            expected_metric=400.0
        ))

        # Option 3: Luraph Universal
        lph_sig = 0.99 if ("lph_" in sample_lower or "luraph" in sample_lower or "\\76\\117\\114" in sample or "lura.ph" in sample_lower) else 0.05
        lph_hist = self.memory.get_historical_accuracy("LURAPH_UNIVERSAL")
        options.append(DecisionOption(
            action_name="LURAPH_UNIVERSAL",
            priority=PriorityCascade.OBJECTIVE if lph_sig > 0.5 else PriorityCascade.EFFICIENCY,
            goal_score=0.95 if lph_sig > 0.5 else 0.2,
            context_score=lph_sig,
            pattern_score=0.90 if lph_sig > 0.5 else 0.2,
            efficiency_score=0.75,
            reliability_score=0.80,
            risk_score=0.20 if lph_sig > 0.5 else 0.7,
            evidence_strength=lph_sig,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=lph_hist,
            reason="Luraph Universal signature detected; instruction peeling & inner lifting pipeline matched." if lph_sig > 0.5 else "Luraph candidate.",
            expected_metric=450.0
        ))

        # Option 4: IronBrew / MoonSec
        ib_sig = 0.99 if ("ironbrew" in sample_lower or "moonsec" in sample_lower or "bit.bxor" in sample) else 0.05
        ib_hist = self.memory.get_historical_accuracy("IRONBREW_MOONSEC")
        options.append(DecisionOption(
            action_name="IRONBREW_MOONSEC",
            priority=PriorityCascade.OBJECTIVE if ib_sig > 0.5 else PriorityCascade.EFFICIENCY,
            goal_score=0.95 if ib_sig > 0.5 else 0.2,
            context_score=ib_sig,
            pattern_score=0.88 if ib_sig > 0.5 else 0.2,
            efficiency_score=0.80,
            reliability_score=0.85,
            risk_score=0.15 if ib_sig > 0.5 else 0.7,
            evidence_strength=ib_sig,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=ib_hist,
            reason="IronBrew/MoonSec control flow flattening detected." if ib_sig > 0.5 else "IronBrew candidate.",
            expected_metric=300.0
        ))

        # Option 5: 2K Security Loader
        twok_sig = 0.99 if ("2k protected" in sample_lower or "local _k1" in sample) else 0.05
        twok_hist = self.memory.get_historical_accuracy("TWOK_SECURITY")
        options.append(DecisionOption(
            action_name="TWOK_SECURITY",
            priority=PriorityCascade.OBJECTIVE if twok_sig > 0.5 else PriorityCascade.EFFICIENCY,
            goal_score=0.95 if twok_sig > 0.5 else 0.2,
            context_score=twok_sig,
            pattern_score=0.95 if twok_sig > 0.5 else 0.2,
            efficiency_score=0.95,
            reliability_score=0.95,
            risk_score=0.05 if twok_sig > 0.5 else 0.7,
            evidence_strength=twok_sig,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=twok_hist,
            reason="2K Security multi-layer XOR payload detected." if twok_sig > 0.5 else "2K Security candidate.",
            expected_metric=100.0
        ))

        # Option 6: Universal Multi-Stage Adaptive Pipeline (Highest priority when signatures are ambiguous)
        # Prevents selecting the wrong single tool and corrupting code variables
        max_detected_sig = max(b64_sig, polsec_sig, luarmor_sig, wrd_sig, mv_sig, lph_sig, ib_sig, twok_sig)
        universal_sig = 0.95 if max_detected_sig < 0.5 else 0.40
        options.append(DecisionOption(
            action_name="PAYOMBØYZ_UNIVERSAL_PIPELINE",
            priority=PriorityCascade.OBJECTIVE if max_detected_sig < 0.5 else PriorityCascade.EFFICIENCY,
            goal_score=0.95 if max_detected_sig < 0.5 else 0.5,
            context_score=universal_sig,
            pattern_score=0.95 if max_detected_sig < 0.5 else 0.5,
            efficiency_score=0.90,
            reliability_score=0.98,
            risk_score=0.05,
            evidence_strength=universal_sig,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=0.95,
            reason="Adaptive Multi-Stage Peeling & Semantic Synthesis Pipeline (Multi-Pass Unpacking, Deflattening & Scope Inlining)." if max_detected_sig < 0.5 else "Universal baseline pipeline.",
            expected_metric=500.0
        ))

        # Option 7: Dynamic Runtime Memory Interception Hook (Fallback)
        hook_hist = self.memory.get_historical_accuracy("RUNTIME_MEMORY_HOOK")
        options.append(DecisionOption(
            action_name="RUNTIME_MEMORY_HOOK",
            priority=PriorityCascade.EFFICIENCY,
            goal_score=0.85,
            context_score=0.60,
            pattern_score=0.65,
            efficiency_score=0.95,
            reliability_score=0.98,
            risk_score=0.10,
            evidence_strength=0.60,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=hook_hist,
            reason="Dynamic memory interception hook (loadstring / getgenv) for guaranteed execution capture in executor.",
            expected_metric=100.0
        ))

        return self.evaluate_candidates(options)

    def evaluate_obfuscation_strategy(
        self,
        file_bytes: bytes,
        filename: str,
        user_prompt: str = ""
    ) -> Dict[str, Any]:
        """
        Applies the 6-layer Neuro-Symbolic Decision Engine to select the optimal
        Obfuscation Architecture, preventing Double-VM performance collapse and GC lag:
        1. HYBRID_POLYMORPHIC_SEAL (Pre-VM / Pre-CFF detected — 0 FPS lag guarantee)
        2. TUNED_CLYDE_REGISTER_VM (Clean Lua/Luau script — 60 FPS JIT with cached globals)
        3. MAX_CFF_WITH_HARDENED_VM (Explicit CFF request on small cold scripts)
        4. PROMETHEUS_DOUBLE_VM (Two-tier instruction virtualizer fallback)
        5. MANGLED_MINIFY (Pure mangler + string encryption, 0 VM overhead)
        """
        norm = self.normalizer.normalize_file_telemetry(file_bytes, filename)
        sample = file_bytes[:30000].decode("utf-8", errors="replace")
        sample_lower = sample.lower()
        prompt_lower = (user_prompt or "").lower()

        data_qual = 0.95 if norm["has_printable_text"] > 0.8 else 0.6

        # Detect existing VM signatures
        vm_sigs = []
        if any(k in sample_lower for k in ("lph_", "luraph", "\\76\\117\\114", "lura.ph")):
            vm_sigs.append("Luraph")
        if any(k in sample_lower for k in ("superflow_bytecode", "cdn.luarmor.net", "luarmor.net", "_bsdata0")):
            vm_sigs.append("Luarmor")
        if any(k in sample_lower for k in ("moonsec", "\\u200b", "\\u200c")):
            vm_sigs.append("MoonSec")
        if any(k in sample_lower for k in ("ironbrew", "iron brew")):
            vm_sigs.append("IronBrew")
        if any(k in sample_lower for k in ("_clydedec_", "clyde protection", "clydeprotectionde.cloud", "_0_ilj")):
            vm_sigs.append("Clyde VM")
        if any(k in sample_lower for k in ("35184372088832", "27552854471197", "unpack or table[")):
            vm_sigs.append("Prometheus")
        if "moonveil" in sample_lower:
            vm_sigs.append("Moonveil")
        if bool(re.search(r'\{\s*(?:\d+\s*,\s*){80,}\d+\s*\}', sample)):
            vm_sigs.append("Packed Bytecode Table")
        if bool(re.search(r'(?:while\s+true\s+do|repeat)\s+.*?(?:ip\s*=|pc\s*=|opcode|instr|handlers\[)', sample, re.DOTALL)):
            vm_sigs.append("VM Dispatch Loop")

        has_existing_vm = len(vm_sigs) > 0

        # Detect existing CFF State Machines
        cff_matches = re.findall(r'while\s+([a-zA-Z0-9_]+)\s*(?:~=|>|<)\s*(?:0|0x0)\s+do', sample)
        has_existing_cff = len(cff_matches) > 0 or ("_cff_" in sample and "state ==" in sample)

        # Detect Hot Loops (60 FPS event loops in Roblox)
        hot_loop_matches = re.findall(r'(?:RenderStepped|Heartbeat|Stepped)\s*:\s*Connect', sample, re.IGNORECASE)
        hot_loop_matches += re.findall(r'while\s+(?:task\.)?wait\s*\([^)]*\)\s*do', sample)
        has_hot_loops = len(hot_loop_matches) > 0

        options = []

        # Option 1: HYBRID_POLYMORPHIC_SEAL
        # If script already has a VM, re-VMing creates a double-VM disaster causing severe FPS drops.
        seal_priority = PriorityCascade.CRITICAL if has_existing_vm else PriorityCascade.OBJECTIVE
        seal_goal = 0.99 if has_existing_vm else 0.70
        seal_context = 0.99 if has_existing_vm else 0.30
        seal_pattern = 0.95 if has_existing_vm else 0.40
        seal_eff = 0.99 # Instantaneous unpack (<2ms), zero in-game runtime overhead
        seal_rel = 0.99
        seal_risk = 0.01 if has_existing_vm else 0.20
        options.append(DecisionOption(
            action_name="HYBRID_POLYMORPHIC_SEAL",
            priority=seal_priority,
            goal_score=seal_goal,
            context_score=seal_context,
            pattern_score=seal_pattern,
            efficiency_score=seal_eff,
            reliability_score=seal_rel,
            risk_score=seal_risk,
            evidence_strength=0.95 if has_existing_vm else 0.30,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=self.memory.get_historical_accuracy("HYBRID_POLYMORPHIC_SEAL"),
            reason=(
                f"Existing VM structure detected ({', '.join(vm_sigs)}). Avoiding double-virtualization performance collapse. "
                "Polymorphic Keystream S-Box Seal guarantees 100% static protection with zero in-game GC lag."
                if has_existing_vm else "Polymorphic Keystream S-Box Seal candidate."
            ),
            expected_metric=60.0 # Target 60 FPS
        ))

        # Option 2: TUNED_CLYDE_REGISTER_VM
        # Optimal for clean scripts or scripts with hot loops
        clyde_priority = PriorityCascade.CRITICAL if (has_hot_loops and not has_existing_vm) else PriorityCascade.OBJECTIVE
        clyde_goal = 0.95
        clyde_context = 0.95 if not has_existing_vm else 0.10
        clyde_pattern = 0.95 if not has_existing_vm else 0.15
        clyde_eff = 0.92
        clyde_rel = 0.95
        clyde_risk = 0.05 if not has_existing_vm else 0.85 # High risk if already VM'd!
        options.append(DecisionOption(
            action_name="TUNED_CLYDE_REGISTER_VM",
            priority=clyde_priority,
            goal_score=clyde_goal,
            context_score=clyde_context,
            pattern_score=clyde_pattern,
            efficiency_score=clyde_eff,
            reliability_score=clyde_rel,
            risk_score=clyde_risk,
            evidence_strength=0.90 if not has_existing_vm else 0.10,
            data_quality=data_qual,
            rule_consistency=0.0 if has_existing_vm else 1.0, # Safety rule: NEVER double-VM!
            historical_accuracy=self.memory.get_historical_accuracy("TUNED_CLYDE_REGISTER_VM"),
            reason=(
                "Clean Luau code with 60 FPS event loops detected. Tuned Clyde Luau Register VM with cached globals and native operators is optimal."
                if (has_hot_loops and not has_existing_vm)
                else "Standard enterprise Luau register-based VM."
            ),
            expected_metric=60.0
        ))

        # Option 3: MAX_CFF_WITH_HARDENED_VM
        want_cff = any(k in prompt_lower for k in ("cff", "flatten", "state machine"))
        cff_risk = 0.80 if (has_existing_vm or has_existing_cff or has_hot_loops) else 0.20
        options.append(DecisionOption(
            action_name="MAX_CFF_WITH_HARDENED_VM",
            priority=PriorityCascade.OBJECTIVE if (want_cff and not has_existing_cff and not has_hot_loops) else PriorityCascade.OPTIMIZATION,
            goal_score=0.90 if want_cff else 0.60,
            context_score=0.85 if (want_cff and not has_existing_cff) else 0.20,
            pattern_score=0.80,
            efficiency_score=0.60, # CFF has state-dispatch overhead
            reliability_score=0.85,
            risk_score=cff_risk,
            evidence_strength=0.80 if want_cff else 0.30,
            data_quality=data_qual,
            rule_consistency=0.0 if (has_existing_cff or has_existing_vm) else 1.0, # Rule: do not nest CFF over CFF
            historical_accuracy=self.memory.get_historical_accuracy("MAX_CFF_WITH_HARDENED_VM"),
            reason="Control Flow Flattening requested for high-security cold logic without hot loops.",
            expected_metric=45.0
        ))

        # Option 4: PROMETHEUS_DOUBLE_VM
        options.append(DecisionOption(
            action_name="PROMETHEUS_DOUBLE_VM",
            priority=PriorityCascade.EFFICIENCY,
            goal_score=0.80,
            context_score=0.50 if not has_existing_vm else 0.10,
            pattern_score=0.70,
            efficiency_score=0.70,
            reliability_score=0.88,
            risk_score=0.30 if not has_existing_vm else 0.90,
            evidence_strength=0.50,
            data_quality=data_qual,
            rule_consistency=0.0 if has_existing_vm else 1.0,
            historical_accuracy=self.memory.get_historical_accuracy("PROMETHEUS_DOUBLE_VM"),
            reason="Prometheus two-tier instruction virtualizer fallback.",
            expected_metric=40.0
        ))

        # Option 5: MANGLED_MINIFY
        want_mini = any(k in prompt_lower for k in ("minify", "mini", "clean", "lightweight"))
        options.append(DecisionOption(
            action_name="MANGLED_MINIFY",
            priority=PriorityCascade.OBJECTIVE if want_mini else PriorityCascade.OPTIMIZATION,
            goal_score=0.95 if want_mini else 0.50,
            context_score=0.90 if want_mini else 0.40,
            pattern_score=0.85,
            efficiency_score=0.99, # 100% native speed
            reliability_score=0.99,
            risk_score=0.05,
            evidence_strength=0.85 if want_mini else 0.30,
            data_quality=data_qual,
            rule_consistency=1.0,
            historical_accuracy=self.memory.get_historical_accuracy("MANGLED_MINIFY"),
            reason="Zero-overhead identifier mangling and encrypted strings pass.",
            expected_metric=60.0
        ))

        return self.evaluate_candidates(options)


# Singleton
DECISION_ENGINE = AIDecisionEngine()

