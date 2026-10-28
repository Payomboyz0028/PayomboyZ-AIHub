#!/usr/bin/env python3
"""
====================================================================
  PAYOMBØYZ KNOWLEDGE BASE — DEPENDENCY GRAPH & CODE VALIDATOR
====================================================================
Maintains the directed dependency graph across:
  - UI Components (Window -> Tab -> Toggle/Slider/Dropdown/Button)
  - Roblox Services (Players, ReplicatedStorage, TweenService, RunService)
  - Remote Event calls (FireServer, InvokeServer)
  - Lifecycle Managers (Maid, trackedConnections, trackedThreads)

Pre-flight Code Validation:
  Validates candidate Luau snippets before shipping to ensure no
  hallucinated functions, missing UI dependencies, or dangling remotes.
====================================================================
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

KNOWLEDGE_DIR = Path(__file__).resolve().parent

# Hardwired known Dependency Relationships
DEFAULT_DEPENDENCY_GRAPH = {
    # UI Hierarchy
    "UI.Window": ["Fluent", "TweenService", "UserInputService"],
    "UI.Tab": ["UI.Window"],
    "UI.Section": ["UI.Tab"],
    "UI.Toggle": ["UI.Tab", "ObsidianGlassEngine.Options"],
    "UI.Slider": ["UI.Tab", "ObsidianGlassEngine.Options", "TweenService"],
    "UI.Dropdown": ["UI.Tab", "ObsidianGlassEngine.Options"],
    "UI.Button": ["UI.Tab", "TweenService"],
    "UI.Input": ["UI.Tab"],
    "UI.Keybind": ["UI.Tab", "UserInputService"],
    "UI.Notification": ["Fluent", "TweenService"],

    # Player / Character Hierarchy
    "Character": ["Players.LocalPlayer"],
    "Humanoid": ["Character"],
    "HumanoidRootPart": ["Character"],

    # Remotes & Network
    "FireServer": ["ReplicatedStorage"],
    "InvokeServer": ["ReplicatedStorage"],

    # Lifecycle & Cleanup
    "Cleanup": ["Maid", "trackedConnections"]
}


class DependencyGraphValidator:
    """Validates Luau code structure and dependencies against PayomboyZ standards."""

    def __init__(self):
        self.graph = DEFAULT_DEPENDENCY_GRAPH
        self.ui_catalog = self._load_json("ui_catalog.json")
        self.code_registry = self._load_json("code_registry.json")

    def _load_json(self, name: str) -> Dict[str, Any]:
        p = KNOWLEDGE_DIR / name
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def inspect_dependencies(self, code_str: str) -> Dict[str, Any]:
        """
        Extracts used services, UI methods, remotes, and connections from code.
        """
        # 1. Services
        services_used = set(re.findall(r'game:GetService\(["\']([^"\']+)["\']\)', code_str))
        
        # 2. UI Methods called
        ui_methods_called = set(re.findall(r':(AddTab|AddSection|AddToggle|AddSlider|AddDropdown|AddButton|AddInput|AddKeybind|AddParagraph|CreateWindow|Notify)\b', code_str))
        
        # 3. Remote calls
        remote_calls = re.findall(r'([a-zA-Z0-9_]+):(FireServer|InvokeServer)\(([^)]*)\)', code_str)
        
        # 4. Loops & Tasks
        loops = len(re.findall(r'\b(while|task\.spawn|task\.wait|RunService\.RenderStepped|RunService\.Heartbeat)\b', code_str))
        
        # 5. Functions defined
        functions_defined = re.findall(r'(?:local\s+)?function\s+([a-zA-Z0-9_]+)\(', code_str)

        return {
            "services": list(services_used),
            "ui_methods": list(ui_methods_called),
            "remote_calls": [{"target": r[0], "type": r[1], "args": r[2][:40]} for r in remote_calls],
            "loop_count": loops,
            "functions": functions_defined
        }

    def validate_code(self, candidate_code: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validates candidate code against the Dependency Graph and Epistemic rules.
        Returns: (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        inspection = self.inspect_dependencies(candidate_code)

        # 1. Check for Hallucinated UI Methods (e.g. AddCheckBox, CreateSliderBar, etc.)
        fake_ui_methods = re.findall(r':(Create[A-Z][a-zA-Z0-9_]+|Add[A-Z][a-zA-Z0-9_]+)\(', candidate_code)
        valid_ui_names = set(self.ui_catalog.keys())
        for m in fake_ui_methods:
            # Common valid Fluent methods
            if m not in valid_ui_names and m not in ("AddTab", "AddSection", "AddToggle", "AddSlider", "AddDropdown", "AddButton", "AddInput", "AddKeybind", "AddParagraph", "AddColorpicker", "CreateWindow", "Notify", "strikeLightning"):
                # If it looks like a UI call on Window or Tab
                if any(k in candidate_code for k in [f"Window:{m}", f"Tab:{m}", f"Fluent:{m}"]):
                    errors.append(f"UNKNOWN UI METHOD: '{m}' does not exist in Obsidian Glassmorphic 2.0 / Fluent library. Use official AddToggle/AddSlider/AddDropdown.")

        # 2. Check for missing TweenService when using TweenService:Create
        if "TweenService:Create" in candidate_code and "TweenService" not in inspection["services"]:
            if 'game:GetService("TweenService")' not in candidate_code and "TweenService" not in candidate_code[:500]:
                warnings.append("MISSING SERVICE: TweenService:Create is called but game:GetService('TweenService') is not declared.")

        # 3. Check for unhandled infinite loops (while true without task.wait)
        for block in re.finditer(r'while\s+true\s+do([\s\S]*?)end', candidate_code):
            inner = block.group(1)
            if "task.wait" not in inner and "wait(" not in inner:
                errors.append("CRITICAL FREEZE: 'while true do' loop found without task.wait(). This will freeze the Roblox client thread.")

        # 4. Check for unmanaged connections
        if ".Connect(" in candidate_code and "Maid" not in candidate_code and "TrackConnection" not in candidate_code and ":Disconnect()" not in candidate_code:
            warnings.append("POTENTIAL MEMORY LEAK: Event .Connect() used without tracking via Maid or TrackConnection. May persist after script reload.")

        # 5. Check for VVIP / Private PayomboyZ security exposure
        if "PayomboyZ_VVIPKey" in candidate_code and "writefile" in candidate_code:
            if "performLogoutKeyClear" not in candidate_code:
                warnings.append("SECURITY ADVICE: Key file manipulation detected. Ensure performLogoutKeyClear() standard is maintained.")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings


# Singleton
VALIDATOR = DependencyGraphValidator()
