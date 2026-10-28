#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ MEMORY BRAIN — EXPERIENCE DATABASE & FEEDBACK ENGINE
====================================================================
Transforms Memory Brain from a simple log into an Experience Database:
  - Records multi-dimensional task experiences
  - Tracks user feedback (/feedback good, /feedback bad)
  - Computes dynamic strategy penalties based on past failures
====================================================================
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
EXP_DB_FILE = BASE_DIR / "bot" / "experience_db.json"


class ExperienceDatabase:
    """Persistent experience learning storage for the Memory Brain."""

    def __init__(self, db_file: Optional[Path | str] = None):
        self.db_file = Path(db_file) if db_file is not None else EXP_DB_FILE
        self.experiences: List[Dict[str, Any]] = self._load_db()
        self.tag_index: Dict[str, List[str]] = {}
        self.dedup_by_hash()
        self.rebuild_index()

    @staticmethod
    def _compute_hash(text: str) -> str:
        norm = " ".join((text or "").strip().lower().split())
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def _load_db(self) -> List[Dict[str, Any]]:
        if self.db_file.exists():
            try:
                with open(self.db_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_db(self):
        try:
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(self.experiences[-500:], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[-] Failed to save experience db: {e}")

    def dedup_by_hash(self) -> int:
        """Removes exact duplicate entries by embedding_hash, keeping the newest entry."""
        seen_hashes = set()
        deduped = []
        removed = 0
        for exp in reversed(self.experiences):
            h = exp.get("embedding_hash")
            if not h:
                h = self._compute_hash(exp.get("pattern", "") or exp.get("task", ""))
                exp["embedding_hash"] = h
            if h in seen_hashes:
                removed += 1
                continue
            seen_hashes.add(h)
            deduped.append(exp)

        deduped.reverse()
        if removed > 0:
            self.experiences = deduped
            self._save_db()
        return removed

    def rebuild_index(self):
        """Regenerates tag index mapping tags to experience IDs."""
        self.tag_index.clear()
        for exp in self.experiences:
            exp_id = exp.get("id", "")
            tags = exp.get("context_tags") or exp.get("tags") or []
            for tag in tags:
                t_clean = tag.strip().lower()
                self.tag_index.setdefault(t_clean, []).append(exp_id)

    def get_by_tags(self, tags: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Filtered retrieval of experiences by matching context tags."""
        query_tags = {t.strip().lower() for t in tags if t.strip()}
        if not query_tags:
            return self.experiences[-limit:]

        matched: List[Tuple[int, Dict[str, Any]]] = []
        for exp in reversed(self.experiences):
            exp_tags = {t.strip().lower() for t in (exp.get("context_tags") or exp.get("tags") or [])}
            overlap = len(query_tags & exp_tags)
            if overlap > 0:
                matched.append((overlap, exp))

        matched.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in matched[:limit]]

    def record_experience(
        self,
        task: str,
        input_pattern: str,
        strategy: str,
        engine: str,
        expected: float,
        actual: float,
        is_success: bool,
        error_msg: str = "",
        validation_passed: bool = True,
        user_feedback: Optional[str] = None,
        context_tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Records a new execution experience."""
        err_delta = actual - expected
        h = self._compute_hash(f"{input_pattern} {strategy} {task}")
        tags = list(context_tags or [])
        if not tags:
            inferred = re.findall(r"[A-Za-z0-9_]{3,}", f"{task} {input_pattern} {strategy}".lower())
            tags = list(dict.fromkeys(inferred))[:8]

        exp = {
            "id": f"EXP_{len(self.experiences) + 1:04d}",
            "task": task,
            "pattern": input_pattern,
            "strategy": strategy,
            "engine": engine,
            "embedding_hash": h,
            "context_tags": tags,
            "confidence_score": round(max(0.0, min(1.0, actual / 100.0 if actual > 1.0 else actual)), 3),
            "recovery_rate": 1.0 if is_success else 0.0,
            "expected_result": expected,
            "actual_result": actual,
            "error_delta": round(err_delta, 2),
            "is_success": is_success,
            "error_msg": error_msg,
            "validation_passed": validation_passed,
            "user_feedback": user_feedback or "UNSPECIFIED",
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.experiences.append(exp)
        for t in tags:
            self.tag_index.setdefault(t.lower(), []).append(exp["id"])
        self._save_db()
        return exp

    def record_user_feedback(self, task_or_id: str, feedback: str) -> bool:
        """Records user feedback ('good', 'bad', 'correct', 'wrong')."""
        fb_normalized = feedback.strip().lower()
        if not self.experiences:
            return False

        # Apply to last matching experience or latest
        target = self.experiences[-1]
        for exp in reversed(self.experiences):
            if exp.get("id") == task_or_id or exp.get("strategy") == task_or_id:
                target = exp
                break

        target["user_feedback"] = fb_normalized
        self._save_db()
        return True

    def record_answer_evaluation(
        self,
        task: str,
        prompt: str,
        response: str,
        pass_status: bool,
        score: float = 0.0,
        evidence: str = "",
        tags: Optional[List[str]] = None,
        engine: str = "gemini",
    ) -> Dict[str, Any]:
        """Persist an AI answer evaluation as an experience record with pass/fail metadata."""
        record = {
            "id": f"ANS_{len(self.experiences) + 1:04d}",
            "task": task,
            "pattern": prompt[:160],
            "strategy": "AI_EVALUATION",
            "engine": engine,
            "expected_result": 1.0,
            "actual_result": float(score),
            "error_delta": round(float(score) - 1.0, 3),
            "is_success": bool(pass_status),
            "error_msg": "" if pass_status else evidence or "Answer did not pass validation.",
            "validation_passed": bool(pass_status),
            "user_feedback": "good" if pass_status else "bad",
            "pass_status": bool(pass_status),
            "score": float(score),
            "evidence": evidence,
            "tags": list(tags or []),
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.experiences.append(record)
        self._save_db()
        return record

    def get_strategy_penalty(self, strategy: str, pattern: str = "") -> float:
        """
        Computes dynamic penalty (0.0 to 0.4) if this strategy recently failed repeatedly.
        """
        recent = [
            e for e in self.experiences[-20:]
            if e.get("strategy") == strategy or e.get("engine") == strategy
        ]
        if not recent:
            return 0.0

        consecutive_fails = 0
        for e in reversed(recent):
            if not e.get("is_success") or e.get("user_feedback") in ("bad", "wrong"):
                consecutive_fails += 1
            else:
                break

        if consecutive_fails >= 3:
            return 0.35
        elif consecutive_fails == 2:
            return 0.20
        elif consecutive_fails == 1:
            return 0.10

        return 0.0

    # ==========================================================================
    # Self-Learning Bypass & Architecture Feedback Engine
    # ==========================================================================
    def record_bypass_feedback(
        self,
        technique_id: str,
        is_success: bool,
        executor: str = "general",
        note: str = ""
    ) -> Dict[str, Any]:
        """
        Records the real-world outcome of a bypass/script technique in an executor.
        Allows the system to continuously learn which techniques get detected.
        """
        return self.record_experience(
            task="bypass_execution",
            input_pattern=f"{technique_id}@{executor.lower()}",
            strategy=technique_id,
            engine=executor.lower(),
            expected=1.0,
            actual=1.0 if is_success else 0.0,
            is_success=is_success,
            error_msg=note,
            validation_passed=is_success,
            user_feedback="good" if is_success else "bad"
        )

    def get_bypass_effectiveness(self, technique_id: str) -> Dict[str, Any]:
        """
        Calculates adaptive effectiveness and confidence for a bypass technique:
        AdaptiveScore = BaseSuccessRate * (1 - ConsecutiveFailPenalty) * RecencyBoost
        """
        now = time.time()
        relevant = [
            e for e in self.experiences
            if e.get("strategy") == technique_id or e.get("pattern", "").startswith(technique_id)
        ]

        if not relevant:
            return {
                "technique": technique_id,
                "total_runs": 0,
                "success_rate": 0.85,  # Optimistic default for standard documented techniques
                "consecutive_fails": 0,
                "adaptive_score": 0.85,
                "is_active": True,
                "status": "DEFAULT_TRUSTED"
            }

        total = len(relevant)
        successes = sum(1 for e in relevant if e.get("is_success") and e.get("user_feedback") not in ("bad", "wrong"))
        base_rate = successes / total

        # Consecutive fails from the end
        consecutive_fails = 0
        last_success_ts = 0.0
        for e in reversed(relevant):
            if e.get("is_success") and e.get("user_feedback") not in ("bad", "wrong"):
                if last_success_ts == 0.0:
                    last_success_ts = e.get("timestamp", 0.0)
                break
            else:
                consecutive_fails += 1

        # Penalty
        penalty = 0.0
        if consecutive_fails >= 3:
            penalty = 0.50
        elif consecutive_fails == 2:
            penalty = 0.25
        elif consecutive_fails == 1:
            penalty = 0.10

        # Recency Boost
        recency_boost = 1.0
        if last_success_ts > 0:
            age_hours = (now - last_success_ts) / 3600.0
            if age_hours <= 1.0:
                recency_boost = 1.20
            elif age_hours <= 24.0:
                recency_boost = 1.05
            elif age_hours > 72.0:
                recency_boost = 0.90
        else:
            recency_boost = 0.70

        adaptive_score = min(1.0, max(0.0, base_rate * (1.0 - penalty) * recency_boost))

        status = "RECOMMENDED"
        if adaptive_score < 0.40:
            status = "OBSOLETE_OR_DETECTED"
        elif adaptive_score < 0.70:
            status = "PROCEED_WITH_CAUTION"

        return {
            "technique": technique_id,
            "total_runs": total,
            "success_rate": round(base_rate, 2),
            "consecutive_fails": consecutive_fails,
            "adaptive_score": round(adaptive_score, 2),
            "is_active": adaptive_score >= 0.40,
            "status": status,
            "last_success_ts": last_success_ts
        }

    def get_learning_summary(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Summarizes recent self-learning observations and adjustments."""
        summary = []
        for e in reversed(self.experiences[-top_n:]):
            summary.append({
                "id": e.get("id"),
                "task": e.get("task"),
                "pattern": e.get("pattern"),
                "strategy": e.get("strategy"),
                "success": e.get("is_success") or e.get("pass_status"),
                "feedback": e.get("user_feedback"),
                "score": e.get("score"),
                "tags": e.get("tags", []),
                "date": e.get("date")
            })
        return summary


# Singleton
EXPERIENCE_DB = ExperienceDatabase()

