"""Idle-only, sampled private answer evaluation by the ThaiLLM supervisor."""

from __future__ import annotations

import asyncio
import json
import random
import re
import sqlite3
import time
from collections import deque
from pathlib import Path
from threading import Lock
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
EVALUATION_DB = BASE_DIR / "bot" / "answer_evaluations.sqlite3"


class IdleQualityMonitor:
    """Samples replies and evaluates them after the bot has been idle for a while."""

    SAMPLE_DENOMINATOR = 8  # approximately one in eight completed AI replies
    IDLE_SECONDS = 90
    MIN_REVIEW_INTERVAL = 300
    QUEUE_LIMIT = 32

    def __init__(self, database: Optional[Path] = None):
        self.database = Path(database) if database else EVALUATION_DB
        self._queue: deque[dict[str, Any]] = deque(maxlen=self.QUEUE_LIMIT)
        self._lock = Lock()
        self._last_activity = time.monotonic()
        self._last_review = 0.0
        self._task: Optional[asyncio.Task] = None

    @staticmethod
    def _redact(text: str, limit: int) -> str:
        value = str(text or "")
        value = re.sub(r"<@!?\d+>|<@&\d+>|<#\d+>", "[discord-reference]", value)
        value = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", "Bearer [redacted]", value)
        value = re.sub(r"(?i)\b(?:sk-[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{20,})\b", "[secret-redacted]", value)
        value = re.sub(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*[^\s,;]{8,}", r"\1=[redacted]", value)
        return value[:limit]

    def note_activity(self) -> None:
        with self._lock:
            self._last_activity = time.monotonic()

    def submit(self, question: str, answer: str, provider: str = "unknown", mode: str = "general_chat") -> bool:
        """Queue a sampled completed turn. This never sends a Discord message."""
        from bot.hybrid_router import HYBRID_ROUTER

        if random.randrange(self.SAMPLE_DENOMINATOR) != 0:
            return False
        if HYBRID_ROUTER._is_evasion_request(question) or HYBRID_ROUTER._is_sexual_request(question):
            return False
        item = {
            "question": self._redact(question, 3000),
            "answer": self._redact(answer, 6500),
            "provider": self._redact(provider, 120),
            "mode": self._redact(mode, 80),
            "queued_at": time.time(),
        }
        with self._lock:
            self._queue.append(item)
        return True

    def start(self) -> None:
        """Start exactly one background task, including across Discord reconnects."""
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self._run())

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(10)
            now = time.monotonic()
            with self._lock:
                if not self._queue:
                    continue
                if now - self._last_activity < self.IDLE_SECONDS:
                    continue
                if now - self._last_review < self.MIN_REVIEW_INTERVAL:
                    continue
                item = self._queue.popleft()
                self._last_review = now
            try:
                evaluation = await asyncio.to_thread(self._evaluate, item)
                if evaluation:
                    self._store(item, evaluation)
                    mean_score = round(
                        (evaluation["intent_match"] + evaluation["completeness"] + evaluation["grounding"]
                         + (6 - evaluation["hallucination_risk"])) / 4,
                        2,
                    )
                    print(
                        f"[AI QA] Stored idle evaluation: provider={item['provider']} "
                        f"mode={item['mode']} score={mean_score}/5",
                        flush=True,
                    )
            except Exception as exc:
                print(f"[AI QA] Background evaluation error: {type(exc).__name__}: {exc}", flush=True)

    @staticmethod
    def _evaluate(item: dict[str, Any]) -> Optional[dict[str, Any]]:
        # Search the existing local knowledge libraries while idle. Retrieved
        # text is supplied as evidence only; the evaluator cannot alter them.
        snippets: list[str] = []
        try:
            from bot.knowledge import RETRIEVER
            from bot.knowledge_router import ROUTER as KNOWLEDGE_ROUTER

            snippets.append(RETRIEVER.retrieve(item["question"], top_k=3))
            snippets.append(KNOWLEDGE_ROUTER.query_knowledge_base(item["question"]))
        except Exception as exc:
            print(f"[AI QA] Local knowledge search unavailable: {type(exc).__name__}", flush=True)
        knowledge = "\n\n".join(part for part in snippets if part).strip()[:5000]

        from bot.hybrid_router import HYBRID_ROUTER

        result = HYBRID_ROUTER.evaluate_answer_with_supervisor(
            item["question"], item["answer"], knowledge_context=knowledge
        )
        if result:
            result["knowledge_found"] = bool(knowledge)
        return result

    def _store(self, item: dict[str, Any], evaluation: dict[str, Any]) -> None:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.database), timeout=10.0) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS answer_evaluations ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, created_at REAL NOT NULL, "
                "provider TEXT NOT NULL, mode TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL, "
                "intent_match INTEGER NOT NULL, completeness INTEGER NOT NULL, grounding INTEGER NOT NULL, "
                "hallucination_risk INTEGER NOT NULL, issue TEXT NOT NULL, learning_query TEXT NOT NULL, "
                "knowledge_found INTEGER NOT NULL)"
            )
            db.execute(
                "INSERT INTO answer_evaluations (created_at, provider, mode, question, answer, "
                "intent_match, completeness, grounding, hallucination_risk, issue, learning_query, knowledge_found) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    time.time(), item["provider"], item["mode"], item["question"], item["answer"],
                    evaluation["intent_match"], evaluation["completeness"], evaluation["grounding"],
                    evaluation["hallucination_risk"], evaluation["issue"], evaluation["learning_query"],
                    int(bool(evaluation.get("knowledge_found"))),
                ),
            )
            db.commit()


QUALITY_MONITOR = IdleQualityMonitor()
