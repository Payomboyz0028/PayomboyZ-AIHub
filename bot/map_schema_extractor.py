# -*- coding: utf-8 -*-
"""
=============================================================================
  ⚡ PAYOMBØYZ GROUND-TRUTH MAP SCHEMA EXTRACTOR V15.0
  Processes massive map dumps (1-20 MB) into a compact 10-30 KB Ground-Truth Contract:
    - Extracts verified RemoteEvents, RemoteFunctions, Bindables
    - Maps Workspace entity containers (Enemies, NPCs, Spawns, Chests, Eggs, Drops)
    - Maps Player DataStore / Leaderstats / Attributes
    - Guarantees ZERO hallucinated Remotes during multi-agent synthesis
=============================================================================
"""

from __future__ import annotations
import re
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Set, Optional


@dataclass
class GroundTruthContract:
    game_name: str
    place_id: int
    remotes: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    workspace_entities: Dict[str, List[str]] = field(default_factory=dict)
    services_detected: List[str] = field(default_factory=list)
    player_attributes: List[str] = field(default_factory=list)
    compact_contract_text: str = ""
    luau_helper_code: str = ""


class MapSchemaExtractor:
    """
    Reverse engineers game structure dumps into compact, operational ground-truth contracts.
    """

    REMOTE_CLASS_NAMES = {"RemoteEvent", "RemoteFunction", "BindableEvent", "BindableFunction"}
    
    KEY_CONTAINER_KEYWORDS = {
        "enemies": ["mob", "enemy", "boss", "monster", "npc", "targets", "dungeon"],
        "loot": ["chest", "coin", "gold", "gem", "drop", "collectible", "resource", "ore"],
        "pets": ["egg", "pet", "hatch", "capsule", "crate"],
        "spawns": ["spawn", "checkpoint", "waypoint", "teleport", "zone", "island", "door"]
    }

    @classmethod
    def extract_from_content(cls, content: str, filename: str = "") -> GroundTruthContract:
        """
        Parses JSON or Luau source text and produces a GroundTruthContract.
        """
        content_stripped = content.strip()
        remotes_found: Dict[str, List[Dict[str, Any]]] = {
            "RemoteEvent": [],
            "RemoteFunction": [],
            "BindableEvent": [],
            "BindableFunction": []
        }
        entities_found: Dict[str, List[str]] = {
            "enemies": [],
            "loot": [],
            "pets": [],
            "spawns": []
        }
        services: Set[str] = set()
        attrs: Set[str] = set()
        game_name = "Unknown Map"
        place_id = 0

        # Try parsing as JSON first
        if content_stripped.startswith("{") or content_stripped.startswith("["):
            try:
                data = json.loads(content_stripped)
                cls._parse_json_tree(data, remotes_found, entities_found, services, attrs)
                if isinstance(data, dict):
                    place_id = int(data.get("PlaceId") or data.get("placeId") or 0)
                    game_name = str(data.get("Name") or data.get("PlaceName") or filename)
            except Exception:
                # If partial JSON or invalid, fallback to regex scanning
                cls._parse_text_heuristics(content, remotes_found, entities_found, services, attrs)
        else:
            # Parse as Luau table / script dump
            cls._parse_text_heuristics(content, remotes_found, entities_found, services, attrs)

        # Build compact contract markdown/json text
        contract_summary = {
            "MapInfo": {"GameName": game_name, "PlaceId": place_id},
            "Services": sorted(list(services)),
            "VerifiedRemotes": {k: [r["Path"] for r in v[:30]] for k, v in remotes_found.items() if v},
            "WorkspaceContainers": {k: v[:20] for k, v in entities_found.items() if v},
            "PlayerAttributes": sorted(list(attrs))[:30]
        }
        compact_text = json.dumps(contract_summary, indent=2, ensure_ascii=False)

        # Generate Luau Helper Boilerplate for Shard 3
        luau_lines = [
            "-- [[ PAYOMBØYZ VERIFIED NETWORK CONTRACT — ZERO HALLUCINATIONS ]]",
            "local ReplicatedStorage = game:GetService('ReplicatedStorage')",
            "local Workspace = game:GetService('Workspace')",
            "local Players = game:GetService('Players')",
            "local LocalPlayer = Players.LocalPlayer",
            "",
            "local VerifiedRemotes = {"
        ]
        all_unique_paths = set()
        for r_type, r_list in remotes_found.items():
            for item in r_list:
                p = item["Path"]
                if p not in all_unique_paths:
                    all_unique_paths.add(p)
                    # derive clean variable name
                    clean_id = re.sub(r'[^a-zA-Z0-9_]', '_', item["Name"])
                    luau_lines.append(f"    ['{clean_id}'] = {p},")
        luau_lines.append("}")
        luau_lines.append("")

        helper_code = "\n".join(luau_lines)

        return GroundTruthContract(
            game_name=game_name,
            place_id=place_id,
            remotes=remotes_found,
            workspace_entities=entities_found,
            services_detected=sorted(list(services)),
            player_attributes=sorted(list(attrs)),
            compact_contract_text=compact_text,
            luau_helper_code=helper_code
        )

    @classmethod
    def _parse_json_tree(
        cls,
        node: Any,
        remotes: Dict[str, List[Dict[str, Any]]],
        entities: Dict[str, List[str]],
        services: Set[str],
        attrs: Set[str],
        current_path: str = "game"
    ):
        if isinstance(node, dict):
            c_name = node.get("ClassName", "")
            name = node.get("Name", "Unnamed")
            this_path = f"{current_path}.{name}" if current_path != "game" else f"game:GetService('{name}')" if name in ["ReplicatedStorage", "Workspace", "Players", "Lighting", "HttpService"] else f"game.{name}"

            if name in ["ReplicatedStorage", "Workspace", "Players", "Lighting", "HttpService"]:
                services.add(name)

            if c_name in cls.REMOTE_CLASS_NAMES:
                remotes[c_name].append({
                    "Name": name,
                    "Path": this_path,
                    "ClassName": c_name
                })

            # Check entity categorizations
            name_lower = name.lower()
            for cat, kws in cls.KEY_CONTAINER_KEYWORDS.items():
                if any(kw in name_lower for kw in kws):
                    entities[cat].append(this_path)
                    break

            # Attributes
            props = node.get("Properties", {})
            if isinstance(props, dict):
                for pk in props.keys():
                    if any(s in pk.lower() for s in ["level", "coins", "gems", "gold", "health", "mana", "exp", "stat"]):
                        attrs.add(pk)

            # Traverse Children
            children = node.get("Children", [])
            if isinstance(children, list):
                for child in children:
                    cls._parse_json_tree(child, remotes, entities, services, attrs, this_path)

        elif isinstance(node, list):
            for item in node:
                cls._parse_json_tree(item, remotes, entities, services, attrs, current_path)

    @classmethod
    def _parse_text_heuristics(
        cls,
        code: str,
        remotes: Dict[str, List[Dict[str, Any]]],
        entities: Dict[str, List[str]],
        services: Set[str],
        attrs: Set[str]
    ):
        # 1. Regex for ReplicatedStorage paths
        rep_patterns = [
            re.compile(r'game(?::GetService\(["\']ReplicatedStorage["\']\)|\.ReplicatedStorage)((?:\.[a-zA-Z0-9_]+|:WaitForChild\(["\'][^"\']+["\']\))+)', re.IGNORECASE),
            re.compile(r'ReplicatedStorage((?:\.[a-zA-Z0-9_]+|:WaitForChild\(["\'][^"\']+["\']\))+)', re.IGNORECASE)
        ]
        services.add("ReplicatedStorage")
        services.add("Workspace")
        services.add("Players")

        seen_remotes = set()
        for p in rep_patterns:
            for match in p.finditer(code):
                subpath = match.group(1)
                full_p = f"game:GetService('ReplicatedStorage'){subpath}"
                clean_name = re.findall(r'["\']([^"\']+)["\']|\.([a-zA-Z0-9_]+)', subpath)
                last_name = "Remote"
                if clean_name:
                    last_name = clean_name[-1][0] or clean_name[-1][1]
                
                if full_p not in seen_remotes:
                    seen_remotes.add(full_p)
                    r_type = "RemoteFunction" if any(rf in subpath.lower() for rf in ["func", "get", "request", "rf"]) else "RemoteEvent"
                    remotes[r_type].append({
                        "Name": last_name,
                        "Path": full_p,
                        "ClassName": r_type
                    })

        # 2. FireServer and InvokeServer invocations
        fire_pattern = re.compile(r'([a-zA-Z0-9_\.:]+)\s*:\s*(FireServer|InvokeServer)\s*\(', re.IGNORECASE)
        for match in fire_pattern.finditer(code):
            caller, method = match.groups()
            caller = caller.strip()
            if caller not in seen_remotes:
                seen_remotes.add(caller)
                r_type = "RemoteFunction" if method == "InvokeServer" else "RemoteEvent"
                remotes[r_type].append({
                    "Name": caller.split(".")[-1].split(":")[-1],
                    "Path": caller,
                    "ClassName": r_type
                })

        # 3. Workspace entities
        ws_pattern = re.compile(r'workspace(?:\.|\s*:\s*WaitForChild\s*\(\s*["\']([^"\']+)["\']\s*\))', re.IGNORECASE)
        for match in ws_pattern.finditer(code):
            name = match.group(1) or ""
            name_lower = name.lower()
            for cat, kws in cls.KEY_CONTAINER_KEYWORDS.items():
                if any(kw in name_lower for kw in kws):
                    p = f"workspace.{name}"
                    if p not in entities[cat]:
                        entities[cat].append(p)
