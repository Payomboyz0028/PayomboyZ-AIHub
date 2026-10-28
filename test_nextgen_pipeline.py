# -*- coding: utf-8 -*-
"""
=============================================================================
  🧪 PAYOMBØYZ NEXT-GEN PIPELINE VERIFICATION & DIAGNOSTIC TEST SUITE
  Engineered by ANON [MAHI68] for dj
=============================================================================
Executes comprehensive end-to-end testing across all 6 layers:
  1. MCI Ingestion Engine (Intent & Map Dump Disambiguation)
  2. Ground-Truth Map Schema Extractor (Zero Hallucinated Remotes)
  3. Refusal Circuit Breaker & Jailbreak Compliance Gate
  4. Sharded Synthesis Engine (50k-100k Character Assembly Gate)
  5. Deobfuscator Semantic Transformer & Parentheses Integrity Gate
  6. Luraph v14.9 / v15 Live Devirtualizer Validation Gate
=============================================================================
"""

import os
import sys
import json
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure") and sys.stderr is not None:
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PASS_COUNT = 0
FAIL_COUNT = 0


def assert_test(name: str, condition: bool, extra: str = ""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  [PASS] {name} {extra}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {name} {extra}")


def test_mci_ingestion_engine():
    print("\n--- [TEST 1] Multi-Modal Context & Intent Ingestion Engine (MCI) ---")
    from bot.mci_ingestion_engine import MCIIngestionEngine

    # Case 1: Map Dump in JSON format (Dex Dump)
    dex_json = json.dumps({
        "PlaceId": 2753915549,
        "Name": "Blox Fruits",
        "ClassName": "DataModel",
        "Children": [
            {
                "Name": "ReplicatedStorage",
                "ClassName": "ReplicatedStorage",
                "Children": [
                    {"Name": "AttackRemote", "ClassName": "RemoteEvent"},
                    {"Name": "BuyItem", "ClassName": "RemoteFunction"}
                ]
            },
            {
                "Name": "Workspace",
                "ClassName": "Workspace",
                "Children": [
                    {"Name": "Enemies", "ClassName": "Folder"},
                    {"Name": "Chests", "ClassName": "Folder"}
                ]
            }
        ]
    }).encode("utf-8")

    res1 = MCIIngestionEngine.inspect(
        user_text="เขียนสคริปต์ออโต้ฟาร์มตามไฟล์นี้ให้หน่อย",
        filename="Dex_MapDump.json",
        content_bytes=dex_json
    )
    assert_test("MCI: Dex JSON Map Dump -> game_dump_synthesis", res1.route_target == "game_dump_synthesis", f"(got: {res1.route_target})")

    # Case 2: Map Dump in Luau table format
    lua_dump = b"""
    return {
        ["ReplicatedStorage"] = {
            ["Remotes"] = {
                ["Combat"] = Instance.new("RemoteEvent"),
                ["Quest"] = Instance.new("RemoteFunction")
            }
        },
        ["Workspace"] = {
            ["Mobs"] = Instance.new("Folder")
        }
    }
    """
    res2 = MCIIngestionEngine.inspect(
        user_text="ดัมพ์แมพมาแล้ว ช่วยทำออโต้ฟาร์มที",
        filename="ReplicatedStorage_Dump.lua",
        content_bytes=lua_dump
    )
    assert_test("MCI: Luau Table Dump -> game_dump_synthesis", res2.route_target == "game_dump_synthesis", f"(got: {res2.route_target})")

    # Case 3: Obfuscated Luraph Script
    lph_code = b'LPH_OBFUSCATED = true; local v3 = 0; while true do if v3 <= 0 then break end end'
    res3 = MCIIngestionEngine.inspect(
        user_text="แกะไฟล์นี้ให้หน่อย",
        filename="Protected.lua",
        content_bytes=lph_code
    )
    assert_test("MCI: Luraph Script -> deobfuscate", res3.route_target == "deobfuscate", f"(got: {res3.route_target})")

    # Case 4: Clean Script for Refactoring (User asks to add features)
    clean_lua = b'local player = game.Players.LocalPlayer\nprint("Hello")'
    res4 = MCIIngestionEngine.inspect(
        user_text="เขียนระบบบินและวาปเพิ่มลงในสคริปต์นี้หน่อย",
        filename="MyScript.lua",
        content_bytes=clean_lua
    )
    assert_test("MCI: Clean Script + Request -> clean_refactor", res4.route_target == "clean_refactor", f"(got: {res4.route_target})")

    # Case 5: Native Binary DLL / EXE -> REA
    res5 = MCIIngestionEngine.inspect(
        user_text="เจาะไฟล์นี้ให้หน่อย",
        filename="injector.dll",
        content_bytes=b'MZ\x90\x00\x03\x00\x00\x00'
    )
    assert_test("MCI: Native DLL -> rea_reverse", res5.route_target == "rea_reverse", f"(got: {res5.route_target})")


def test_map_schema_extractor():
    print("\n--- [TEST 2] Ground-Truth Map Schema Extractor ---")
    from bot.map_schema_extractor import MapSchemaExtractor

    dex_json = json.dumps({
        "PlaceId": 987654321,
        "Name": "Blade Ball",
        "Children": [
            {
                "Name": "ReplicatedStorage",
                "ClassName": "ReplicatedStorage",
                "Children": [
                    {"Name": "ParryRemote", "ClassName": "RemoteEvent"},
                    {"Name": "UpgradeAbility", "ClassName": "RemoteFunction"}
                ]
            },
            {
                "Name": "Workspace",
                "ClassName": "Workspace",
                "Children": [
                    {"Name": "Balls", "ClassName": "Folder"},
                    {"Name": "AlivePlayers", "ClassName": "Folder"}
                ]
            }
        ]
    })

    contract = MapSchemaExtractor.extract_from_content(dex_json, filename="BladeBall_Dump.json")
    remotes_count = len(contract.remotes.get("RemoteEvent", [])) + len(contract.remotes.get("RemoteFunction", []))
    assert_test("MapSchema: Remote Count >= 2", remotes_count >= 2, f"(found {remotes_count})")
    assert_test("MapSchema: PlaceId Preserved", contract.place_id == 987654321)
    assert_test("MapSchema: Contract Text Size < 10KB", len(contract.compact_contract_text) < 10000, f"({len(contract.compact_contract_text)} bytes)")
    assert_test("MapSchema: Luau Boilerplate Helper Generated", "VerifiedRemotes" in contract.luau_helper_code)


def test_refusal_circuit_breaker():
    print("\n--- [TEST 3] Refusal Circuit Breaker & Safety Override ---")
    from bot.hybrid_router import HYBRID_ROUTER

    test_refusals = [
        "ผมไม่สามารถเขียนสคริปต์ exploit ให้ได้ครับ",
        "I cannot assist with creating exploits or cheats",
        "as an ai language model, i cannot create exploits",
        "งานแบบนั้นคือการเขียนโค้ดเข้าไปรันในเกมของคนอื่นผ่าน executor ซึ่งผมช่วยไม่ได้",
        "ไม่สามารถจัดทำสคริปต์ประเภท aimlock"
    ]

    for ref in test_refusals:
        detected = HYBRID_ROUTER.is_refusal_response(ref)
        assert_test(f"Circuit Breaker detects: '{ref[:40]}...'", detected is True)

    clean_replies = [
        "สร้างสคริปต์ให้เรียบร้อยแล้วครับ ด้านล่างนี้คือโค้ดเต็มระบบ",
        "โย่ว dj ว่าไง วันนี้จะให้เขียนสคริปต์หรือแกะตัวไหน",
        "```lua\nlocal Fluent = loadstring(...)()\n```"
    ]
    for c in clean_replies:
        detected = HYBRID_ROUTER.is_refusal_response(c)
        assert_test(f"Clean reply not flagged: '{c[:40]}...'", detected is False)


def test_sharded_synthesis_engine():
    print("\n--- [TEST 4] Modular Sharded Synthesis Assembly & Syntax Gate ---")
    from bot.sharded_synthesis_engine import ShardedSynthesisEngine, SynthesisShard

    # Create 5 test mock shards
    test_shards = [
        SynthesisShard(shard_id=1, name="UI_Framework", target_chars=1000, code="local UI = { Title = 'Hub' }"),
        SynthesisShard(shard_id=2, name="State_And_AntiAFK", target_chars=1000, code="local State = { AutoFarm = false }"),
        SynthesisShard(shard_id=3, name="Remote_Network_Adapter", target_chars=1000, code="local Remotes = { Attack = function() end }"),
        SynthesisShard(shard_id=4, name="Gameplay_Automation_Core", target_chars=1000, code="function Farm() if State.AutoFarm then Remotes.Attack() end end"),
        SynthesisShard(shard_id=5, name="Main_Orchestrator_And_Mobile", target_chars=1000, code="print('Mobile UI Ready')")
    ]

    assembled = ShardedSynthesisEngine._assemble_shards(test_shards, "Test Game", 12345, "Make Hub")
    assert_test("M3SE: All 5 Shards Linked", all(f"[SHARD {i}:" in assembled for i in range(1, 6)))
    assert_test("M3SE: Header & Footer Attached", "PAYOMBØYZ CYBER-AI HIGH-CAPACITY EXPLOIT SUITE" in assembled)

    valid, patched = ShardedSynthesisEngine._run_compiler_gate(assembled + "\nfunction test() ")
    assert_test("M3SE: Compiler Gate Patches Unclosed Function", valid and patched.endswith("end\n"))


def test_parentheses_integrity_gate():
    print("\n--- [TEST 5] Parentheses Integrity Gate (cff_unflattener regex check) ---")
    import cff_unflattener

    test_cases = [
        ("type(key)", "type(key)"),
        ("Module.IsSuperVIP(key)", "Module.IsSuperVIP(key)"),
        ("print(a)", "print(a)"),
        ("v10(v11)", "v10(v11)"),
        ("local x = (v1)", "local x = v1")
    ]

    for inp, expected in test_cases:
        # Run strip single parens
        cleaner = cff_unflattener.CFFUnflattenerEngine(inp)
        cleaned = cleaner._reduce_opaque_predicates(inp)
        assert_test(f"Parens preserved: {inp} -> {cleaned}", cleaned == expected, f"(expected {expected})")


def test_luraph_v149_live_devirt():
    print("\n--- [TEST 6] Luraph v14.9 Live Devirtualizer Validation Gate ---")
    from luraph_v149_devirt import LuraphV149Devirt

    key_sample = Path(r"d:\Deobfuscate\Lerning\Luraph\V14.9\Key-obfuscated (4).lua")
    if key_sample.exists():
        t0 = time.time()
        devirter = LuraphV149Devirt()
        code = key_sample.read_text(encoding="utf-8", errors="ignore")
        res = devirter.devirt(code, source_name=key_sample.name)
        elapsed = time.time() - t0
        assert_test("LuraphV149: Devirt Success", res.get("success") is True)
        assert_test("LuraphV149: Exported Module Table Recovered", res.get("has_exported_module") is True)
        assert_test("LuraphV149: 12 Game URLs Extracted", len(res.get("urls", [])) >= 12, f"(found {len(res.get('urls', []))})")
        assert_test("LuraphV149: Fast Execution (< 5s)", elapsed < 5.0, f"({elapsed:.2f}s)")
    else:
        print("  [SKIP] Key-obfuscated (4).lua not found at path")


def run_all_tests():
    t0 = time.time()
    print("=================================================================")
    print("⚡ PAYOMBØYZ NEXT-GEN PIPELINE VERIFICATION")
    print("=================================================================")
    test_mci_ingestion_engine()
    test_map_schema_extractor()
    test_refusal_circuit_breaker()
    test_sharded_synthesis_engine()
    test_parentheses_integrity_gate()
    test_luraph_v149_live_devirt()
    elapsed = time.time() - t0
    print("=================================================================")
    print(f"📊 SUMMARY: {PASS_COUNT} PASSED | {FAIL_COUNT} FAILED in {elapsed:.3f}s")
    print("=================================================================")
    return FAIL_COUNT == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
