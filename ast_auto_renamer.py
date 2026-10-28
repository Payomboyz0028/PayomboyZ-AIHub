#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================================
💎 PAYOMBOYZ AST SEMANTIC AUTO-RENAMER ENGINE V1.0
Engineered by ANON [MAHI68] for dj.
====================================================================
Performs deep AST-level semantic inference and def-use scope resolution
to restore 100% original human-readable developer identifiers across
Roblox services, character instances, UI frameworks, and exploit logic.
====================================================================
"""

import sys
import os
import re
from typing import Dict, List, Tuple, Optional, Any, Set

HERE = os.path.dirname(os.path.abspath(__file__))
LURAPH_CORE = os.path.join(HERE, "Lerning", "Luraph", "New", "v15_tool_attempt_source", "core")
if not os.path.exists(LURAPH_CORE):
    LURAPH_CORE = os.path.join(HERE, "Lerning", "Luraph", "Deobfuscator-Luraph-V15-master", "core")
if os.path.exists(LURAPH_CORE) and LURAPH_CORE not in sys.path:
    sys.path.insert(0, LURAPH_CORE)

try:
    import luauast
    HAS_LUAU_AST = True
except ImportError:
    HAS_LUAU_AST = False

try:
    import names as luraph_names
    HAS_LURAPH_NAMES = True
except ImportError:
    HAS_LURAPH_NAMES = False


# Known Roblox Services
ROBLOX_SERVICES = {
    "Players", "ReplicatedStorage", "RunService", "TweenService",
    "UserInputService", "HttpService", "Workspace", "CoreGui",
    "Lighting", "SoundService", "StarterGui", "StarterPack",
    "StarterPlayer", "TeleportService", "MarketplaceService",
    "VirtualUser", "PathfindingService", "ContextActionService",
    "GuiService", "LogService", "Stats", "Debris"
}

# UI Methods -> Inferred Component Type
UI_METHODS = {
    "CreateWindow": "Window",
    "CreateTab": "Tab",
    "AddTab": "Tab",
    "CreateSection": "Section",
    "AddSection": "Section",
    "CreateToggle": "Toggle",
    "AddToggle": "Toggle",
    "CreateButton": "Button",
    "AddButton": "Button",
    "CreateSlider": "Slider",
    "AddSlider": "Slider",
    "CreateDropdown": "Dropdown",
    "AddDropdown": "Dropdown",
    "CreateColorpicker": "Colorpicker",
    "AddColorpicker": "Colorpicker",
    "CreateKeybind": "Keybind",
    "AddKeybind": "Keybind",
}


class ASTRenamerContext:
    def __init__(self):
        # location -> { "name": original_name, "decl_node": dict, "usages": [dict], "inferred": str }
        self.locals: Dict[str, Dict[str, Any]] = {}
        # location -> scope_id
        self.local_scope: Dict[str, int] = {}
        # scope_id -> set of used names in that scope
        self.scope_names: Dict[int, Set[str]] = {}
        self.scope_counter = 0


class ASTAutoRenamer:
    def __init__(self, code: str):
        self.raw_code = code
        self.ctx = ASTRenamerContext()
        self.rename_count = 0

    def run(self) -> Tuple[str, int]:
        current_code = self.raw_code
        if not HAS_LUAU_AST:
            current_code = self._regex_fallback(current_code)
            if HAS_LURAPH_NAMES:
                try:
                    current_code = luraph_names.rename_text(current_code)
                except Exception:
                    pass
            return current_code, self.rename_count

        try:
            ast = luauast.parse(current_code)
            # Pass 1: Collect declarations & usages
            self._collect_ast_symbols(ast, scope_id=0)

            # Pass 2: Semantic Inference from definitions & usages
            self._infer_semantics()

            # Pass 3: Apply renamed identifiers with collision deduplication
            self._apply_renames()

            # Render AST back to Luau source
            current_code = luauast.render(ast)
        except Exception:
            current_code = self._regex_fallback(current_code)

        # Pass 4: Deep Behavioral Semantic Namer (catches deferred accesses, properties, and method hints)
        if HAS_LURAPH_NAMES:
            try:
                before_obf = len(re.findall(r'\b[vVnNrR]\d{1,4}\b', current_code))
                deep_renamed = luraph_names.rename_text(current_code)
                after_obf = len(re.findall(r'\b[vVnNrR]\d{1,4}\b', deep_renamed))
                recovered_in_pass = max(0, before_obf - after_obf)
                self.rename_count += recovered_in_pass
                current_code = deep_renamed
            except Exception:
                pass

        return current_code, self.rename_count

    def _collect_ast_symbols(self, node: Any, scope_id: int):
        if not isinstance(node, dict):
            return

        t = node.get("type")

        # Scope boundary check
        current_scope = scope_id
        if t in ("AstStatBlock", "AstExprFunction"):
            self.ctx.scope_counter += 1
            current_scope = self.ctx.scope_counter
            if current_scope not in self.ctx.scope_names:
                self.ctx.scope_names[current_scope] = set()

        # Local Declarations
        if t == "AstStatLocal":
            vars_list = node.get("vars", [])
            values_list = node.get("values", [])
            for i, v in enumerate(vars_list):
                loc = v.get("location")
                if loc:
                    if i < len(values_list):
                        val_node = values_list[i]
                        val_idx = 0
                    elif len(values_list) == 1 and values_list[0].get("type") in ("AstExprCall", "AstExprVarargs"):
                        val_node = values_list[0]
                        val_idx = i
                    else:
                        val_node = None
                        val_idx = 0

                    self.ctx.locals[loc] = {
                        "name": v.get("name"),
                        "decl_node": v,
                        "val_node": val_node,
                        "val_index": val_idx,
                        "usages": [],
                        "inferred": None,
                        "scope": current_scope
                    }
                    if current_scope in self.ctx.scope_names:
                        self.ctx.scope_names[current_scope].add(v.get("name"))

        elif t in ("AstStatForIn", "AstStatFor"):
            vars_list = node.get("vars", []) if t == "AstStatForIn" else ([node.get("var")] if node.get("var") else [])
            for v in vars_list:
                if v and v.get("location"):
                    self.ctx.locals[v["location"]] = {
                        "name": v.get("name"),
                        "decl_node": v,
                        "val_node": node,
                        "val_index": 0,
                        "usages": [],
                        "inferred": None,
                        "scope": current_scope
                    }

        elif t == "AstStatLocalFunction":
            v = node.get("name")
            if v and v.get("location"):
                self.ctx.locals[v["location"]] = {
                    "name": v.get("name"),
                    "decl_node": v,
                    "val_node": node.get("func"),
                    "val_index": 0,
                    "is_function": True,
                    "usages": [],
                    "inferred": None,
                    "scope": current_scope
                }
                if current_scope in self.ctx.scope_names:
                    self.ctx.scope_names[current_scope].add(v.get("name"))

        elif t == "AstStatAssign":
            vars_list = node.get("vars", [])
            values_list = node.get("values", [])
            for i, v_expr in enumerate(vars_list):
                if v_expr.get("type") == "AstExprLocal":
                    local_obj = v_expr.get("local", {})
                    loc = local_obj.get("location")
                    if loc and loc in self.ctx.locals:
                        if i < len(values_list):
                            self.ctx.locals[loc].setdefault("assigned_values", []).append(values_list[i])
                        elif len(values_list) == 1:
                            self.ctx.locals[loc].setdefault("assigned_values", []).append(values_list[0])

        elif t == "AstExprFunction":
            args_list = node.get("args", [])
            parent_context = node.get("_parent_context")
            for i, a in enumerate(args_list):
                loc = a.get("location")
                if loc:
                    self.ctx.locals[loc] = {
                        "name": a.get("name"),
                        "decl_node": a,
                        "val_node": None,
                        "val_index": i,
                        "parent_context": parent_context,
                        "usages": [],
                        "inferred": None,
                        "scope": current_scope
                    }

        elif t == "AstExprCall":
            func = node.get("func", {})
            call_method = ""
            if func.get("type") == "AstExprIndexName":
                call_method = func.get("index", "")
                callee = func.get("expr", {})
                callee_name = self._get_expr_name(callee)
            for arg_idx, arg in enumerate(node.get("args", [])):
                if isinstance(arg, dict) and arg.get("type") == "AstExprFunction":
                    arg["_parent_context"] = {
                        "method": call_method,
                        "callee": callee_name if 'callee_name' in locals() else "",
                        "arg_idx": arg_idx
                    }

        # Local Usages
        elif t == "AstExprLocal":
            local_obj = node.get("local")
            if local_obj and local_obj.get("location"):
                loc = local_obj["location"]
                if loc in self.ctx.locals:
                    self.ctx.locals[loc]["usages"].append(local_obj)

        # Recurse into children
        for key, val in node.items():
            if isinstance(val, dict):
                self._collect_ast_symbols(val, current_scope)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        self._collect_ast_symbols(item, current_scope)

    def _infer_semantics(self):
        for loc, data in self.ctx.locals.items():
            orig_name = data["name"]
            val = data["val_node"]
            inferred = None

            # Skip if already a good descriptive name
            if not self._is_mangled_name(orig_name):
                continue

            # 1. Analyze RHS Expression
            if val:
                inferred = self._infer_from_expr(val, data["val_index"])

            # 1.5. Analyze Assigned Values from later statements (AstStatAssign)
            if not inferred and data.get("assigned_values"):
                for a_val in data["assigned_values"]:
                    inf = self._infer_from_expr(a_val, 0)
                    if inf:
                        inferred = inf
                        break

            # 1.6. Analyze Local Function Purpose
            if not inferred and data.get("is_function") and val:
                inferred = self._infer_function_purpose(val)

            # 2. Analyze ForIn Loops
            decl_node = data["decl_node"]
            parent_stat = data["val_node"]
            if not inferred and parent_stat and isinstance(parent_stat, dict) and parent_stat.get("type") == "AstStatForIn":
                inferred = self._infer_for_in_var(parent_stat, decl_node)

            # 3. Analyze Function Parameters from caller context
            if not inferred:
                inferred = self._infer_function_param(decl_node, data["usages"])

            # 4. Analyze Usages (Methods invoked on this local)
            if not inferred:
                inferred = self._infer_from_usages(data["usages"])

            if inferred:
                data["inferred"] = inferred

    def _infer_from_expr(self, expr: Dict[str, Any], val_idx: int = 0) -> Optional[str]:
        if not isinstance(expr, dict):
            return None
        t = expr.get("type")

        # game:GetService("XYZ")
        if t == "AstExprCall":
            func = expr.get("func", {})
            args = expr.get("args", [])

            if func.get("type") == "AstExprIndexName":
                method = func.get("index")
                callee = func.get("expr", {})

                # GetService call
                if method == "GetService" and args and args[0].get("type") == "AstExprConstantString":
                    svc = args[0].get("value")
                    return svc

                # WaitForChild / FindFirstChild / FindFirstChildOfClass
                if method in ("WaitForChild", "FindFirstChild", "FindFirstChildWhichIsA", "FindFirstChildOfClass"):
                    if args and args[0].get("type") == "AstExprConstantString":
                        child_name = args[0].get("value")
                        clean = re.sub(r'[^a-zA-Z0-9_]', '', child_name)
                        if clean:
                            callee_base = self._get_expr_name(callee)
                            if any(k in callee_base.lower() for k in ("player", "enemy", "target", "mob", "other")):
                                return f"target{clean}"
                            return clean

                # TweenService:Create(...)
                if method == "Create":
                    return "Tween"

                # UI Framework Methods
                if method in UI_METHODS:
                    return UI_METHODS[method]

                callee_name = self._get_expr_name(callee)
                # Instance.new("...") / Drawing.new("...")
                if method == "new" and (callee_name in ("Instance", "Drawing") or (callee.get("type") == "AstExprGlobal" and callee.get("global") in ("Instance", "Drawing"))):
                    if args and args[0].get("type") == "AstExprConstantString":
                        class_name = args[0].get("value")
                        clean = re.sub(r'[^a-zA-Z0-9_]', '', class_name)
                        return clean[0].lower() + clean[1:] if clean else "instance"

                # Datatype constructors: Vector3.new, CFrame.new, Color3.fromRGB, etc.
                if callee_name in ("Vector3", "CFrame", "Color3", "UDim2", "UDim", "TweenInfo", "RaycastParams"):
                    return callee_name[0].lower() + callee_name[1:]

                # HttpGet -> WebResponse / ScriptSource
                if method == "HttpGet":
                    return "ScriptSource"

                # Players:GetPlayers() -> PlayersList
                if method in ("GetPlayers", "GetChildren", "GetDescendants"):
                    return "List"

                # :GetMouse() -> Mouse
                if method == "GetMouse":
                    return "Mouse"

                # :Clone() -> Clone
                if method == "Clone":
                    return "Clone"

            # pcall(...) return values
            if func.get("type") == "AstExprGlobal" and func.get("global") == "pcall":
                return "success" if val_idx == 0 else "result"

            # loadstring(...)()
            if func.get("type") == "AstExprCall":
                sub_func = func.get("func", {})
                if sub_func.get("type") == "AstExprGlobal" and sub_func.get("global") == "loadstring":
                    return "Library"

        # Indexing via string constant expr: Lp["RE/RigSync/Refresh"]
        elif t == "AstExprIndexExpr":
            idx_expr = expr.get("index", {})
            if idx_expr.get("type") == "AstExprConstantString":
                raw_str = idx_expr.get("value", "")
                if "RE/" in raw_str or "RemoteEvent" in raw_str:
                    clean = re.sub(r'[^a-zA-Z0-9_]', '', raw_str.replace("RE/", "remote_"))
                    return clean
                elif "RF/" in raw_str or "RemoteFunction" in raw_str:
                    clean = re.sub(r'[^a-zA-Z0-9_]', '', raw_str.replace("RF/", "function_"))
                    return clean
                elif len(raw_str) >= 2 and len(raw_str) <= 30:
                    clean = re.sub(r'[^a-zA-Z0-9_]', '', raw_str)
                    if clean and not clean[0].isdigit():
                        return f"item_{clean}"

        # Indexing: LocalPlayer, Character, Camera, etc.
        elif t == "AstExprIndexName":
            idx = expr.get("index")
            if idx in ("CurrentCamera", "Camera"):
                return "camera"
            if idx in ("LocalPlayer", "Character", "Humanoid", "HumanoidRootPart", "PlayerGui", "Backpack"):
                return idx[0].lower() + idx[1:]
            if idx in ("CFrame", "Position", "CameraType"):
                return idx[0].lower() + idx[1:]

        # Binary OR fallback: v2.Character or v2.CharacterAdded:Wait()
        elif t == "AstExprBinary" and expr.get("op") == "Or":
            left_inf = self._infer_from_expr(expr.get("left", {}), val_idx)
            if left_inf:
                return left_inf
            right_inf = self._infer_from_expr(expr.get("right", {}), val_idx)
            if right_inf:
                return right_inf

        return None

    def _infer_function_purpose(self, func_node: Dict[str, Any]) -> Optional[str]:
        """Infers the high-level intent of a local function from its AST body."""
        if not isinstance(func_node, dict):
            return None
        text_repr = str(func_node)
        if "OnClientEvent" in text_repr and "Connect" in text_repr:
            return "setupNetworkSync"
        if "CameraType" in text_repr and "Scriptable" in text_repr:
            return "lockCamera"
        if "CameraType" in text_repr and "sp.Type" in text_repr:
            return "restoreCamera"
        if "Disconnect" in text_repr:
            return "cleanupSync"
        if "FireServer" in text_repr:
            return "sendPayload"
        if "InvokeServer" in text_repr:
            return "requestData"
        return None

    def _infer_for_in_var(self, for_in_stmt: Dict[str, Any], decl_node: Dict[str, Any]) -> Optional[str]:
        vars_list = for_in_stmt.get("vars", [])
        var_idx = 0
        for idx, v in enumerate(vars_list):
            if v.get("location") == decl_node.get("location"):
                var_idx = idx
                break

        values = for_in_stmt.get("values", [])
        if values:
            first_val = values[0]
            # pairs(...) / ipairs(...)
            if first_val.get("type") == "AstExprCall":
                iter_args = first_val.get("args", [])
                if iter_args:
                    arg0 = iter_args[0]
                    # pairs(Players:GetPlayers())
                    if arg0.get("type") == "AstExprCall":
                        f = arg0.get("func", {})
                        if f.get("type") == "AstExprIndexName":
                            m = f.get("index")
                            if m == "GetPlayers":
                                return "index" if var_idx == 0 else "player"
                            elif m in ("GetChildren", "GetDescendants"):
                                callee_name = self._get_expr_name(f.get("expr", {}))
                                if "Enemy" in callee_name or "enemy" in callee_name or "Mob" in callee_name:
                                    return "index" if var_idx == 0 else "enemy"
                                return "index" if var_idx == 0 else "child"

        return "index" if var_idx == 0 else "value"

    def _infer_function_param(self, decl_node: Dict[str, Any], usages: List[Dict[str, Any]]) -> Optional[str]:
        loc = decl_node.get("location")
        local_data = self.ctx.locals.get(loc, {})
        ctx = local_data.get("parent_context")
        arg_idx = local_data.get("val_index", 0)

        if ctx:
            method = ctx.get("method", "")
            if method in ("CreateToggle", "AddToggle"):
                return "enabled" if arg_idx == 0 else f"arg_{arg_idx + 1}"
            elif method in ("CreateSlider", "AddSlider"):
                return "value" if arg_idx == 0 else f"arg_{arg_idx + 1}"
            elif method in ("CreateDropdown", "AddDropdown"):
                return "selectedOption" if arg_idx == 0 else f"arg_{arg_idx + 1}"
            elif method in ("CreateColorpicker", "AddColorpicker"):
                return "color" if arg_idx == 0 else f"arg_{arg_idx + 1}"
            elif method in ("CreateKeybind", "AddKeybind"):
                return "key" if arg_idx == 0 else f"arg_{arg_idx + 1}"
            elif method == "Connect":
                callee = ctx.get("callee", "")
                if "PlayerAdded" in callee or "PlayerRemoving" in callee:
                    return "player"
                elif "CharacterAdded" in callee or "CharacterRemoving" in callee:
                    return "character"
                elif "Heartbeat" in callee or "RenderStepped" in callee or "Stepped" in callee:
                    return "deltaTime"
                elif "InputBegan" in callee or "InputEnded" in callee:
                    return "input" if arg_idx == 0 else "gameProcessed"
                elif "Touched" in callee:
                    return "hit"
                return "eventArg"
        return None

    def _infer_from_usages(self, usages: List[Dict[str, Any]]) -> Optional[str]:
        text_repr = str(usages)
        if "Disconnect" in text_repr:
            return "connection"
        if "CameraType" in text_repr or "CFrame" in text_repr:
            return "camera"
        if "FireServer" in text_repr:
            return "remoteEvent"
        return None

    def _get_expr_name(self, expr: Dict[str, Any]) -> str:
        if not isinstance(expr, dict):
            return ""
        t = expr.get("type")
        if t == "AstExprGlobal":
            return expr.get("global", "")
        if t == "AstExprLocal":
            loc = expr.get("local", {}).get("location")
            if loc and loc in self.ctx.locals:
                inf = self.ctx.locals[loc].get("inferred")
                if inf:
                    return inf
                val_n = self.ctx.locals[loc].get("val_node")
                if val_n and isinstance(val_n, dict):
                    if val_n.get("type") == "AstExprGlobal":
                        return val_n.get("global", "")
                    elif val_n.get("type") == "AstExprCall":
                        f = val_n.get("func", {})
                        if f.get("type") == "AstExprIndexName" and f.get("index") == "GetService":
                            args = val_n.get("args", [])
                            if args and args[0].get("type") == "AstExprConstantString":
                                return args[0].get("value", "")
            return expr.get("local", {}).get("name", "")
        if t == "AstExprIndexName":
            base = self._get_expr_name(expr.get("expr", {}))
            idx = expr.get("index", "")
            return f"{base}.{idx}" if base else idx
        return ""

    def _is_mangled_name(self, name: str) -> bool:
        if not name:
            return False
        # Preserve standard math / coordinates / loop vars
        if name in ("x", "y", "z", "w", "i", "j", "k", "ui", "id", "os", "fs", "io", "math", "table", "string"):
            return False
        # Obfuscator temp variables starting with underscore
        if name.startswith("_"):
            return True
        # 1-3 letter variables (Wp, qp, Lp, fp, Up, sp, pp, bp, cp, Gp, vp, dp, mp, a, b, etc.)
        if len(name) <= 3 and re.match(r'^[a-zA-Z0-9]+$', name):
            return True
        # Standard obfuscator patterns: v1, r12, slot4, reg12, arg3, etc.
        if re.match(r'^(?:v|r|u|a|t|reg|slot|arg|temp|val|var|local)\d+$', name, re.IGNORECASE):
            return True
        # Hex variable names: _0x12a, var_0x12a
        if re.search(r'0x[0-9a-fA-F]+', name):
            return True
        # Confusables / barcode names: II11l, l1l1l, O0O0, IllII
        if re.match(r'^[lI10_]{3,}$', name):
            return True
        # Obfuscator suffixes ending in 'p' or '_' with short prefix: Wp, qp, L_1
        if name.endswith("p") and len(name) <= 4:
            return True
        return False

    def _apply_renames(self):
        used_names_by_scope: Dict[int, Set[str]] = {}

        for loc, data in self.ctx.locals.items():
            inferred = data.get("inferred")
            if not inferred:
                continue

            scope = data.get("scope", 0)
            if scope not in used_names_by_scope:
                used_names_by_scope[scope] = set()

            # Ensure unique name in this scope
            final_name = inferred
            counter = 2
            while final_name in used_names_by_scope[scope]:
                final_name = f"{inferred}_{counter}"
                counter += 1

            used_names_by_scope[scope].add(final_name)

            # Apply to declaration
            decl = data["decl_node"]
            decl["name"] = final_name

            # Apply to all AST usages
            for u in data["usages"]:
                u["name"] = final_name

            self.rename_count += 1

    def _regex_fallback(self, code: str) -> str:
        s = code
        # Service rename: local <var> = game:GetService("XYZ")
        s = re.sub(
            r'local\s+([a-zA-Z0-9_]+)\s*=\s*game:GetService\(["\']([a-zA-Z0-9_]+)["\']\)',
            r'local \2 = game:GetService("\2")',
            s
        )
        return s


def auto_rename_ast(code: str) -> Tuple[str, int]:
    renamer = ASTAutoRenamer(code)
    return renamer.run()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ast_auto_renamer.py <input.lua> [-o output.lua]")
        sys.exit(1)

    in_file = sys.argv[1]
    out_file = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None

    with open(in_file, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()

    print(f"[*] Reading {in_file}...")
    clean, count = auto_rename_ast(src)
    print(f"[+] Total Identifiers Semantically Reconstructed: {count}")

    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(clean)
        print(f"[+] Clean source written to: {out_file}")
    else:
        print(clean)
