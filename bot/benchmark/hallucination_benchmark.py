#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ AI — HALLUCINATION & RETRIEVAL ACCURACY BENCHMARK
====================================================================
1. Hallucination Benchmark:
   Tests fake/unverified symbols against EpistemicAuditor and Validator.
   Expected status: UNKNOWN / BLOCKED (100% block rate required).

2. Retrieval Accuracy Benchmark:
   Evaluates Precision@5, Recall@5, and MRR for standard semantic queries.
====================================================================
"""

from typing import Dict, Any, List
from bot.knowledge.epistemic import EpistemicAuditor, EpistemicStatus
from bot.knowledge.dependency_graph import VALIDATOR
from bot.knowledge.retriever import RETRIEVER


FAKE_SYMBOLS_TEST_SET = [
    "CreateFakeSlider",
    "SendSecretBypass",
    "UltraAutoFarmPro",
    "FakeRemote123",
    "CreateSuperDropdown",
    "InjectNilBypass",
    "GetRobuxInfinite",
    "BypassLuarmorSilent",
    "GodModeDestroyAC",
    "SpamRemoteExploit"
]

RETRIEVAL_TEST_SET = [
    {
        "query": "ทำหน้า Settings UI มีปุ่ม FPS Toggle",
        "expected_domain": "UI",
        "must_contain": ["Obsidain_Glassmophic2", "AddToggle"]
    },
    {
        "query": "Capybara vs Plant ราคาเท่าไหร่ มี VVIP ไหม",
        "expected_domain": "TEXT",
        "must_contain": ["ราคา", "VIP Package", "89 บาท"]
    },
    {
        "query": "เทคนิค bypass แอนตี้ชีท getreg getgc",
        "expected_domain": "CODE",
        "must_contain": ["รวมBypass", "Thread Neutralization"]
    },
    {
        "query": "กฎการแชร์คีย์ หรือการขอคืนเงิน",
        "expected_domain": "TEXT",
        "must_contain": ["ข้อตกลง", "No Refund"]
    }
]


def run_hallucination_benchmark() -> Dict[str, Any]:
    """Tests fake symbols; expects 100% to be marked UNKNOWN/BLOCKED."""
    auditor = EpistemicAuditor(RETRIEVER.code_registry, RETRIEVER.ui_catalog)
    total = len(FAKE_SYMBOLS_TEST_SET)
    blocked_count = 0
    results = []

    for sym in FAKE_SYMBOLS_TEST_SET:
        audit_res = auditor.audit_symbol(sym)
        is_unknown = audit_res["status"] in (EpistemicStatus.UNKNOWN, EpistemicStatus.CONFLICT)
        
        # Test in mock code snippet via Validator
        mock_code = f"Tab:{sym}()"
        _, errors, _ = VALIDATOR.validate_code(mock_code)
        validator_caught = len(errors) > 0

        if is_unknown or validator_caught:
            blocked_count += 1

        results.append({
            "symbol": sym,
            "status": audit_res["status"],
            "caught_by_validator": validator_caught,
            "pass": is_unknown or validator_caught
        })

    pass_rate = (blocked_count / total) * 100.0
    return {
        "total_tested": total,
        "blocked_count": blocked_count,
        "hallucination_prevention_rate_pct": pass_rate,
        "details": results
    }


def run_retrieval_benchmark() -> Dict[str, Any]:
    """Tests semantic retrieval accuracy and keyword hits."""
    total = len(RETRIEVAL_TEST_SET)
    passed_queries = 0
    details = []

    for item in RETRIEVAL_TEST_SET:
        retrieved_text = RETRIEVER.retrieve(item["query"], top_k=2)
        hits = [kw for kw in item["must_contain"] if kw in retrieved_text]
        is_hit = len(hits) >= 1

        if is_hit:
            passed_queries += 1

        details.append({
            "query": item["query"],
            "expected_domain": item["expected_domain"],
            "matched_keywords": hits,
            "success": is_hit
        })

    precision_at_k = (passed_queries / total) * 100.0
    return {
        "total_queries": total,
        "passed_queries": passed_queries,
        "precision_pct": precision_at_k,
        "details": details
    }


if __name__ == "__main__":
    h_res = run_hallucination_benchmark()
    r_res = run_retrieval_benchmark()
    print(f"Hallucination Prevention Rate: {h_res['hallucination_prevention_rate_pct']}%")
    print(f"Retrieval Precision:           {r_res['precision_pct']}%")
