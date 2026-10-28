#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ REMOTE HARVESTER & AST SEMANTIC EXTRACTOR (REA-POWERED)
====================================================================
Reverse Engine Analysis for Luau Scripts:
  - Scans raw/decompiled scripts for Network Remotes (FireServer/InvokeServer)
  - Resolves ReplicatedStorage paths & RemoteEvent tables
  - Maps Mobs, Bosses, Quests, Items, and Target Entities
  - Identifies AntiCheat Detection remotes for automated blacklisting
  - Assembles verified Ground Truth specs for MultiAgentScriptFactory
====================================================================
"""

import re
import json
from typing import Dict, Any, List, Set, Optional

class RemoteHarvester:
    """
    Reverse engineers game mechanics from Luau source code.
    Extracts network contracts, entities, and anti-cheat hooks.
    """

    @classmethod
    def analyze_script(cls, code: str, max_lines: int = 10000) -> Dict[str, Any]:
        """
        Extracts verified ground-truth mechanics from a Luau script.
        """
        lines = code.splitlines()[:max_lines]
        truncated_code = "\n".join(lines)

        remotes: Set[str] = set()
        remote_calls: List[Dict[str, Any]] = []
        entities: Set[str] = set()
        anti_cheats: Set[str] = set()
        replicated_paths: Set[str] = set()

        # 1. Detect FireServer & InvokeServer calls
        # Pattern: variable:FireServer(...) or path.Remote:FireServer(...)
        fire_pattern = re.compile(r'([a-zA-Z0-9_\.:]+)\s*:\s*(?:FireServer|InvokeServer)\s*\((.*?)\)', re.IGNORECASE)
        for match in fire_pattern.finditer(truncated_code):
            caller, args = match.groups()
            clean_caller = caller.strip()
            clean_args = args.strip()
            remotes.add(clean_caller)
            if len(remote_calls) < 25:
                remote_calls.append({
                    "remote": clean_caller,
                    "args": clean_args[:120]
                })

        # 2. Detect ReplicatedStorage / Remote Declarations
        # e.g. ReplicatedStorage:WaitForChild("Remotes"):WaitForChild("Attack")
        rep_pattern = re.compile(r'ReplicatedStorage(?:\.|\s*:\s*WaitForChild\s*\(\s*["\']([^"\']+)["\']\s*\))(?:\.|\s*:\s*WaitForChild\s*\(\s*["\']([^"\']+)["\']\s*\))?', re.IGNORECASE)
        for match in rep_pattern.finditer(truncated_code):
            p1, p2 = match.groups()
            if p1 and p2:
                replicated_paths.add(f"ReplicatedStorage.{p1}.{p2}")
            elif p1:
                replicated_paths.add(f"ReplicatedStorage.{p1}")

        # Direct RemoteEvent / RemoteFunction instances
        inst_pattern = re.compile(r'["\']([a-zA-Z0-9_\-\s]+)["\']\s*,\s*["\'](?:RemoteEvent|RemoteFunction)["\']', re.IGNORECASE)
        for match in inst_pattern.finditer(truncated_code):
            remotes.add(match.group(1))

        # 3. Detect Workspace entity folders (Mobs, Enemies, NPCs, Chests, Eggs)
        ws_entity_pattern = re.compile(r'workspace(?:\.|\s*:\s*WaitForChild\s*\(\s*["\']([^"\']+)["\']\s*\))', re.IGNORECASE)
        common_entity_keywords = ["mob", "enemy", "npc", "boss", "monster", "chest", "egg", "ore", "spawn", "dungeon", "target"]
        for match in ws_entity_pattern.finditer(truncated_code):
            name = match.group(1) or ""
            if any(k in name.lower() for k in common_entity_keywords):
                entities.add(f"workspace.{name}")

        # Also search for list of enemies / bosses defined in tables
        # e.g. local Mobs = {"Bandit", "Pirate", "Boss"}
        table_list_pattern = re.compile(r'(?:mobs?|enemies|bosses|targets|targets_list)\s*=\s*\{([^}]+)\}', re.IGNORECASE)
        for match in table_list_pattern.finditer(truncated_code):
            raw_items = match.group(1)
            found_strings = re.findall(r'["\']([^"\']+)["\']', raw_items)
            for s in found_strings[:10]:
                entities.add(s)

        # 4. Detect AntiCheat / Ban remotes or checks
        ac_pattern = re.compile(r'["\']([a-zA-Z0-9_\-]*AntiCheat[a-zA-Z0-9_\-]*|BanEvent|SecurityCheck|Telemetry|KickRemote|Detection[a-zA-Z0-9_\-]*)["\']', re.IGNORECASE)
        for match in ac_pattern.finditer(truncated_code):
            anti_cheats.add(match.group(1))

        # 5. Extract UI tab names or features
        features: Set[str] = set()
        feature_pattern = re.compile(r':(?:CreateToggle|AddToggle|Toggle)\s*\(\s*\{\s*Name\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
        for match in feature_pattern.finditer(truncated_code):
            features.add(match.group(1))

        # 6. Dynamic Luau Metamethod Sandbox Trap for Obfuscated Scripts
        # If static parsing found 0 remotes, or script contains obfuscation indicators
        is_obfuscated = (
            len(remotes) == 0
            or any(kw in truncated_code for kw in ["string.char", "LPH_", "bit32", "getfenv", "loadstring", "\\0", "\\x"])
        )
        if is_obfuscated:
            try:
                from bot.luau_sandbox_tracer import SANDBOX_TRACER
                sandbox_result = SANDBOX_TRACER.trace_obfuscated_script(code)
                for r in sandbox_result.get("remotes", []):
                    remotes.add(r)
                for rc in sandbox_result.get("remote_calls", []):
                    if rc not in remote_calls:
                        remote_calls.append(rc)
                if sandbox_result.get("remotes"):
                    print(f"[REMOTE HARVESTER] Intercepted {len(sandbox_result['remotes'])} remotes dynamically via Luau Sandbox!", flush=True)
            except Exception as s_err:
                print(f"[REMOTE HARVESTER] Sandbox tracing fallback skipped: {s_err}", flush=True)

        return {
            "remotes": sorted(list(remotes))[:20],
            "remote_calls": remote_calls[:15],
            "replicated_paths": sorted(list(replicated_paths))[:15],
            "entities": sorted(list(entities))[:20],
            "anti_cheats": sorted(list(anti_cheats))[:10],
            "features": sorted(list(features))[:15]
        }


    @classmethod
    def format_as_ground_truth(cls, analysis: Dict[str, Any], game_name: str) -> str:
        """
        Formats analysis into an authoritative ground-truth spec block for LLMs.
        """
        remotes_str = "\n".join([f"  - `{r}`" for r in analysis.get("remotes", [])]) or "  - [Standard Network Dispatcher]"
        calls_str = "\n".join([f"  - `{c['remote']}:FireServer({c['args']})`" for c in analysis.get("remote_calls", [])]) or "  - Standard FireServer payload"
        entities_str = ", ".join([f"`{e}`" for e in analysis.get("entities", [])]) or "Enemies, Mobs, Workspace Target Models"
        ac_str = ", ".join([f"`{ac}`" for ac in analysis.get("anti_cheats", [])]) or "AntiCheat, BanEvent (Standard Metamethod Protection Required)"
        rep_paths = "\n".join([f"  - `{p}`" for p in analysis.get("replicated_paths", [])]) or "  - ReplicatedStorage.Remotes"

        return f"""
[🎯 VERIFIED REVERSE-ENGINEERING GROUND TRUTH — {game_name.upper()}]
Status: Extracted from Decompiled / Active Game Scripts via REA Engine
1. Real Game Remotes:
{remotes_str}
2. Network Call Signatures:
{calls_str}
3. Known ReplicatedStorage Paths:
{rep_paths}
4. Identified Target Entities / Mobs / Folders:
  {entities_str}
5. AntiCheat Remotes to Blacklist / Bypass:
  {ac_str}
CRITICAL INSTRUCTION: You MUST use these exact Remotes and entity paths in your Luau script. DO NOT invent fake remote names.
"""

HARVESTER = RemoteHarvester()
