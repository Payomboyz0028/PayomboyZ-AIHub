#!/usr/bin/env python3
"""
====================================================================
🔓 PAYOMBOYZ CFF (CONTROL FLOW FLATTENING) STATE DISPATCHER UNFLATTENER
Engineered by ANON [MAHI68] for dj.
====================================================================
Transforms obfuscated dispatcher state machines, binary search trees,
and scrambled execution arrays back into 100% natural, linear Luau code.
"""

import sys
import os
import json
import re
from typing import Dict, List, Tuple, Optional, Any, Set

HERE = os.path.dirname(os.path.abspath(__file__))
for rel_sub in [
    os.path.join(HERE, "Lerning", "Luraph", "Deobfuscator-Luraph-V15-master", "core"),
    os.path.join(HERE, "Lerning", "Luraph", "New", "v15_tool_attempt_source", "core"),
    os.path.join(HERE, "..", "Lerning", "Luraph", "Deobfuscator-Luraph-V15-master", "core"),
    os.path.join(HERE, "..", "Lerning", "Luraph", "New", "v15_tool_attempt_source", "core"),
    os.path.join(os.getcwd(), "Lerning", "Luraph", "Deobfuscator-Luraph-V15-master", "core"),
    os.path.join(os.getcwd(), "Lerning", "Luraph", "New", "v15_tool_attempt_source", "core"),
]:
    if os.path.exists(rel_sub) and rel_sub not in sys.path:
        sys.path.insert(0, rel_sub)

try:
    import luauast
    HAS_LUAU_AST = True
except ImportError:
    HAS_LUAU_AST = False


class CFFUnflattenerEngine:
    def __init__(self, code: str):
        self.raw_code = code
        self.stats = {
            "array_dispatchers": 0,
            "flat_dispatchers": 0,
            "bst_dispatchers": 0,
            "opaque_predicates": 0,
            "for_dispatchers": 0,
            "dual_hash_dispatchers": 0,
            "total_unflattened": 0
        }

    def run(self) -> Tuple[str, Dict[str, int]]:
        code = self.raw_code

        # Pass 0: Reduce algebraic MBA and parity gadget opaque predicates
        code = self._reduce_opaque_predicates(code)

        # Pass 1: Unflatten string.split / table array dispatchers (Fast regex pattern)
        code = self._unflatten_array_loops(code)

        # Pass 1.5: Unflatten sequential for-loop state-machine dispatchers (Prometheus / WeAreDevs / Luraph)
        code = self._unflatten_for_range_dispatchers(code)

        # Pass 1.8: Coupled Dual-Variable Hash Dispatchers & S-Box String Inliner (Level 2/3/Sentinel)
        code = self._decrypt_keystream_sbox(code)
        code = self._unflatten_dual_hash_dispatchers(code)

        # Pass 2: Unflatten Binary Search Tree dispatchers (Luast v1.0.1 / Prometheus)
        code = self._unflatten_bst_loops(code)

        # Pass 2.5: Unflatten Nested Binary Search Tree Dispatchers (Luraph v15.1 / v15 / v14)
        if HAS_LUAU_AST and ("while" in code or "repeat" in code) and any(op in code for op in ("<=", "<", ">=", ">", "==")):
            try:
                code = self._unflatten_nested_bst_dispatchers(code)
            except Exception as e:
                pass

        # Pass 3: AST-based While-Elseif Dispatcher Unflattener
        if HAS_LUAU_AST:
            try:
                code = self._unflatten_ast_loops(code)
            except Exception as e:
                pass

        self.stats["total_unflattened"] = (
            self.stats["array_dispatchers"] +
            self.stats["flat_dispatchers"] +
            self.stats["bst_dispatchers"] +
            self.stats["opaque_predicates"] +
            self.stats["for_dispatchers"] +
            self.stats["dual_hash_dispatchers"]
        )
        return code, self.stats

    # =========================================================================
    # PASS 0: ALGEBRAIC OPAQUE PREDICATES & PARITY GADGETS
    # =========================================================================
    def _reduce_opaque_predicates(self, code: str) -> str:
        """
        Reduces mathematical invariants and algebraic opaque predicates to constants:
        1. Parity gadgets: (x * (x - 1)) & 1 == 0 or (x * (x + 1)) % 2 == 0 -> true
        2. Bitwise invariants: x ~ x == 0, band(x, bnot(x)) == 0
        3. Folds if true then ... else ... end blocks
        """
        # Parity gadget: ((x * (x - 1)) % 2 == 0) or ((x * (x + 1)) % 2 == 0)
        p1 = re.compile(r'\(\s*\([a-zA-Z0-9_]+\s*\*\s*\([a-zA-Z0-9_]+\s*[-+]\s*1\)\)\s*[%&]\s*[12]\s*==\s*0\s*\)')
        code, n1 = p1.subn('true', code)
        self.stats["opaque_predicates"] += n1

        # Bitwise identity: x ~ x == 0
        p2 = re.compile(r'\b([a-zA-Z0-9_]+)\s*~\s*\1\s*==\s*0\b')
        code, n2 = p2.subn('true', code)
        self.stats["opaque_predicates"] += n2

        # bit32.band(x, bit32.bnot(x)) == 0
        p3 = re.compile(r'bit32\.band\s*\(\s*([a-zA-Z0-9_]+)\s*,\s*bit32\.bnot\s*\(\s*\1\s*\)\s*\)\s*==\s*0')
        code, n3 = p3.subn('true', code)
        self.stats["opaque_predicates"] += n3

        # Simplify dead if false blocks: if false then ... end
        code = re.sub(r'\bif\s+false\s+then[\s\S]*?\bend\s*;?', '', code)

        # ── Pass 0.2: Normalize hex and binary literals in expressions (e.g. 0x21 -> 33, 0B101 -> 5)
        def _norm_literal(m):
            raw = m.group(0).replace('_', '')
            try:
                if raw.lower().startswith('0x'):
                    return str(int(raw, 16))
                elif raw.lower().startswith('0b'):
                    return str(int(raw, 2))
                return str(int(raw))
            except Exception:
                return m.group(0)

        code = re.sub(r'\b0[xX][0-9a-fA-F_]+\b', _norm_literal, code)
        code = re.sub(r'\b0[bB][01_]+\b', _norm_literal, code)

        # ── Pass 0.3: Radix-85 polynomial digit folding: (d - offset) * 85^n
        # Luraph v14.9/v15.1: (d - 37) * 7225, (d - 33) * 85, etc.
        def _fold_radix_term(m):
            try:
                d = int(m.group(1))
                offset = int(m.group(2))
                power = int(m.group(3))
                return str((d - offset) * power)
            except Exception:
                return m.group(0)

        code = re.sub(r'\(\s*(\d+)\s*-\s*(37|33|32|35|0)\s*\)\s*\*\s*(\d+)', _fold_radix_term, code)

        # ── Pass 0.4: Constant arithmetic folding (Radix-85 digit polynomial reductions)
        def eval_bin(m):
            try:
                a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
                if op == '+': return str(a + b)
                if op == '-': return str(a - b)
                if op == '*': return str(a * b)
                if op == '//': return str(a // b) if b != 0 else m.group(0)
                if op == '%': return str(a % b) if b != 0 else m.group(0)
                if op == '^': return str(a ** b) if b >= 0 and b <= 16 else m.group(0)
            except Exception:
                pass
            return m.group(0)

        for _ in range(8):
            prev = code
            code = re.sub(r'\(\s*(-?\d+)\s*([-+*]|//|%|\^)\s*(-?\d+)\s*\)', eval_bin, code)
            code = re.sub(r'\b(\d+)\s*\*\s*1\b', r'\1', code)
            code = re.sub(r'\b1\s*\*\s*(\d+)\b', r'\1', code)
            code = re.sub(r'\b(\d+)\s*\+\s*0\b', r'\1', code)
            code = re.sub(r'\b0\s*\+\s*(\d+)\b', r'\1', code)
            code = re.sub(r'\(\s*\(([^()]+)\)\s*\)', r'(\1)', code)
            if code == prev:
                break

        # Clean redundant single-variable/number parenthesization: ((x)) -> x, but PROTECT function calls foo(bar)
        code = re.sub(r'(?<![a-zA-Z0-9_\]\)])\(\s*([a-zA-Z0-9_]+)\s*\)', r'\1', code)

        return code

    # =========================================================================
    # PASS 1.5: SEQUENTIAL FOR-LOOP STATE DISPATCHERS
    # =========================================================================
    def _unflatten_for_range_dispatchers(self, code: str) -> str:
        if "for " not in code or "==" not in code:
            return code
        pattern = re.compile(
            r'for\s+([a-zA-Z0-9_]+)\s*=\s*(\d+)\s*,\s*(\d+)\s+do\s*'
            r'if\s+\1\s*==\s*\2\s+then\s*'
            r'([\s\S]*?)'
            r'\bend\s*;?\s*end;?',
            re.MULTILINE
        )

        def replacer(m):
            var = m.group(1)
            start_idx = int(m.group(2))
            end_idx = int(m.group(3))
            body = m.group(4)

            # Extract branches: if var == X then ... elseif var == Y then ...
            branches = re.findall(
                rf'(?:if|elseif)\s+{re.escape(var)}\s*==\s*(\d+)\s+then([\s\S]*?)(?=(?:elseif|\belse\b|\bend\b))',
                f"if {var} == {start_idx} then" + body
            )

            branch_map = {}
            for s_idx, b_code in branches:
                branch_map[int(s_idx)] = b_code.strip()

            ordered = []
            for i in range(start_idx, end_idx + 1):
                if i in branch_map:
                    ordered.append(branch_map[i])

            if len(ordered) >= 2:
                self.stats["for_dispatchers"] += 1
                return f"-- [PAYOMBOYZ] Unflattened For-Loop Dispatcher ({len(ordered)} states)\n" + "\n".join(ordered)

            return m.group(0)

        return pattern.sub(replacer, code)

    # =========================================================================
    # PASS 1: ARRAY DISPATCHERS (string.split("1|3|2", "|") / { "1", "3", ... })
    # =========================================================================
    def _unflatten_array_loops(self, code: str) -> str:
        if ("string.split" not in code and "|" not in code) and ("{" not in code or "#" not in code):
            return code
        pattern = re.compile(
            r'(?:local\s+([a-zA-Z0-9_]+)\s*=\s*(?:string\.split\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\'][^"\']+["\']\s*\)|\{\s*([^}]+)\s*\}))\s*;?\s*'
            r'for\s+[a-zA-Z0-9_]+\s*=\s*1\s*,\s*#\1\s*(?:,\s*1)?\s*do\s*'
            r'(?:local\s+([a-zA-Z0-9_]+)\s*=\s*\1\[[a-zA-Z0-9_]+\])?\s*;?\s*'
            r'if\s+(?:\4|\1\[[a-zA-Z0-9_]+\])\s*==\s*["\']?([^"\'\n]+)["\']?\s*then\s*'
            r'([\s\S]*?)'
            r'\bend\s*;?\s*end',
            re.MULTILINE
        )

        def replacer(match):
            split_str = match.group(2)
            table_elems = match.group(3)
            loop_body = match.group(6)

            if split_str:
                order = [x.strip() for x in split_str.split("|") if x.strip()]
            elif table_elems:
                order = [re.sub(r'["\']', '', x.strip()) for x in table_elems.split(",") if x.strip()]
            else:
                return match.group(0)

            # Reconstruct branches
            branches = re.findall(
                r'(?:if|elseif)\s+[a-zA-Z0-9_\[\]]+\s*==\s*["\']?([^"\'\n]+)["\']?\s*then([\s\S]*?)(?=(?:elseif|\belse\b|\bend\b))',
                "if dummy == \"" + match.group(5) + "\" then" + loop_body
            )

            branch_map = {}
            for st_id, body in branches:
                st_id = st_id.strip()
                body = body.strip()
                body = re.sub(r'\bend$', '', body).strip()
                branch_map[st_id] = body

            ordered_stmts = []
            for st_id in order:
                if st_id in branch_map:
                    ordered_stmts.append(branch_map[st_id])

            if ordered_stmts:
                self.stats["array_dispatchers"] += 1
                return "-- [PAYOMBOYZ] Unflattened Array Dispatcher (" + str(len(ordered_stmts)) + " states)\n" + "\n".join(ordered_stmts)

            return match.group(0)

        return pattern.sub(replacer, code)


    # =========================================================================
    # PASS 1.8: S-BOX DECRYPTION & COUPLED DUAL-HASH CFF UNFLATTENER
    # =========================================================================
    def _decrypt_keystream_sbox(self, code: str) -> str:
        sbox_pattern = re.compile(
            r'local\s+_K\s*=\s*(\d+);\s*local\s+_R\s*=\s*(\d+);\s*local\s+_ST\s*=\s*\{([\s\S]*?)\};\s*local\s+_S\s*=\s*function\(idx\)[\s\S]*?end;?'
        )
        m = sbox_pattern.search(code)
        if not m:
            return code
        try:
            k_val = int(m.group(1))
            r_val = int(m.group(2))
            raw_table = m.group(3)
            items = re.findall(r'\{[\d,\s]+\}', raw_table)
            decrypted = []
            for idx, item in enumerate(items):
                nums = [int(x.strip()) for x in re.findall(r'\d+', item)]
                chars = []
                for j, b in enumerate(nums):
                    k = (k_val + (j * r_val) + idx) & 0xFF
                    chars.append(chr(b ^ k))
                decrypted.append("".join(chars))
            if decrypted:
                for i, s in enumerate(decrypted):
                    code = re.sub(rf'\b_S\({i + 1}\)', json.dumps(s), code)
                code = code.replace(m.group(0), '')
        except Exception:
            pass
        return code

    def _unflatten_dual_hash_dispatchers(self, code: str) -> str:
        dual_pattern = re.compile(
            r'local\s+_s1\s*=\s*(\d+);\s*local\s+_s2\s*=\s*(\d+);[\s\S]*?'
            r'while\s+true\s+do\s+local\s+_h\s*=\s*bit32\.bxor\(\(_s1\*(\d+)\)%(\d+),\(_s2\*(\d+)\+(\d+)\)%\d+\);'
            r'([\s\S]*?)\bend\s+end;?',
            re.IGNORECASE
        )
        def replacer(dm):
            try:
                s1 = int(dm.group(1))
                s2 = int(dm.group(2))
                multA = int(dm.group(3))
                modM = int(dm.group(4))
                multB = int(dm.group(5))
                offsetB = int(dm.group(6))
                body = dm.group(7)

                calc_hash = lambda a, b: ((a * multA) % modM) ^ ((b * multB + offsetB) % modM)
                branches = re.split(r'\b(?:elseif|if)\s+', body)
                state_map = {}

                for br in branches:
                    if not br.strip(): continue
                    cond_m = re.search(r'_h\s*==\s*(\d+)\s+and\s+\(\(_inv\*\(_inv\+1\)\)%2==(\d+)\)', br)
                    if not cond_m: continue
                    h_val = int(cond_m.group(1))
                    parity = int(cond_m.group(2))
                    if parity == 1:
                        continue # Prune mathematical decoy!
                    then_idx = br.find(' then ')
                    if then_idx == -1: continue
                    code_part = br[then_idx + 6:].strip()
                    is_exit = 'break;' in code_part

                    next_s1 = None
                    s1_div = re.search(r'_s1\s*=\s*math\.floor\((\d+)\/(\d+)\);?', code_part)
                    if s1_div:
                        next_s1 = int(s1_div.group(1)) // int(s1_div.group(2))
                    else:
                        s1_dir = re.search(r'_s1\s*=\s*(\d+);?', code_part)
                        if s1_dir: next_s1 = int(s1_dir.group(1))

                    next_s2 = None
                    s2_xor = re.search(r'_s2\s*=\s*bit32\.bxor\(bit32\.bxor\((\d+),\s*(\d+)\),\s*(\d+)\);?', code_part)
                    if s2_xor:
                        next_s2 = int(s2_xor.group(1))
                    else:
                        s2_dir = re.search(r'_s2\s*=\s*(\d+);?', code_part)
                        if s2_dir: next_s2 = int(s2_dir.group(1))

                    clean = re.sub(r'_s1\s*=\s*math\.floor\(\d+\/\d+\);?', '', code_part)
                    clean = re.sub(r'_s1\s*=\s*\d+;?', '', clean)
                    clean = re.sub(r'_s2\s*=\s*bit32\.bxor\(bit32\.bxor\(\d+,\s*\d+\),\s*\d+\);?', '', clean)
                    clean = re.sub(r'_s2\s*=\s*\d+;?', '', clean)
                    clean = re.sub(r'break;?', '', clean).strip()

                    state_map[h_val] = {"code": clean, "exit": is_exit, "s1": next_s1, "s2": next_s2}

                linear = []
                visited = set()
                for _ in range(200):
                    ch = calc_hash(s1, s2)
                    if ch not in state_map: break
                    st = state_map[ch]
                    if st["code"]: linear.append(st["code"])
                    if st["exit"] or st["s1"] is None: break
                    k = (st["s1"], st["s2"])
                    if k in visited: break
                    visited.add(k)
                    s1, s2 = st["s1"], st["s2"]

                if linear:
                    self.stats["dual_hash_dispatchers"] += 1
                    return "-- [PAYOMBOYZ] Unflattened Coupled Dual-Hash CFF\n" + "\n".join(linear)
            except Exception:
                pass
            return dm.group(0)

        return dual_pattern.sub(replacer, code)

    # =========================================================================
    # PASS 2: BINARY SEARCH TREE DISPATCHERS (Luast v1.0.1, Prometheus)
    # =========================================================================
    def _unflatten_bst_loops(self, code: str) -> str:
        if "while" not in code:
            return code
        pattern = re.compile(
            r'([a-zA-Z0-9_]+)\s*=\s*(\d+)\.?\s*;\s*'
            r'while\s+true\s+do\s*'
            r'\1\s*=\s*(\d+)\.?\s*-\s*\1\s*;\s*'
            r'do\s*(if\s+\1\s*<[\s\S]*?\bend\s*end\s*end\s*end)',
            re.MULTILINE
        )

        def replacer(match):
            var_name = match.group(1)
            init_val = int(match.group(2))
            affine_c = int(match.group(3))
            tree_body = match.group(4)

            # Extract leaf blocks with equality comparisons
            eq_blocks = re.findall(
                r'if\s+' + re.escape(var_name) + r'\s*==\s*(\d+)\.?\s*then\s*([\s\S]*?)(?:elseif|else|end)',
                tree_body
            )

            blocks = {}
            for raw_val, body in eq_blocks:
                val = int(raw_val)
                state_id = affine_c - val
                
                # Parse domain statements & transitions
                stmts = []
                next_st = None
                cond_br = None
                is_term = False

                for line in re.split(r';|\n', body):
                    line = line.strip()
                    if not line or line == "continue":
                        continue
                    if line == "break" or line.startswith("return"):
                        is_term = True
                        if line.startswith("return"):
                            stmts.append(line)
                        continue

                    # Ternary transition: var = if cond then S1 else S2
                    tm = re.search(r'\b' + re.escape(var_name) + r'\s*=\s*if\s+([\s\S]+?)\s+then\s*(\d+)\.?\s*else\s*(\d+)\.?', line)
                    if tm:
                        cond_br = (tm.group(1).strip(), int(tm.group(2)), int(tm.group(3)))
                        continue

                    # Direct transition: var = Next
                    dm = re.search(r'\b' + re.escape(var_name) + r'\s*=\s*(\d+)\.?', line)
                    if dm:
                        next_st = int(dm.group(1))
                        continue

                    stmts.append(line)

                blocks[state_id] = {
                    "stmts": stmts,
                    "next": next_st,
                    "cond_branch": cond_br,
                    "is_terminal": is_term
                }

            if blocks and init_val in blocks:
                self.stats["bst_dispatchers"] += 1
                unrolled = self._linearize_block_dict(blocks, init_val)
                return f"-- [PAYOMBOYZ] Unflattened BST State Dispatcher ({len(blocks)} states)\n" + unrolled

            return match.group(0)

        return pattern.sub(replacer, code)

    def _linearize_block_dict(self, blocks: Dict[int, Any], start_state: int, visited: Optional[Set[int]] = None, indent: int = 0) -> str:
        if visited is None:
            visited = set()

        pad = "  " * indent
        lines = []
        curr = start_state

        while curr is not None and curr in blocks and curr not in visited:
            visited.add(curr)
            b = blocks[curr]

            for s in b["stmts"]:
                lines.append(pad + s)

            if b["is_terminal"]:
                break

            if b["cond_branch"]:
                cond, s_then, s_else = b["cond_branch"]
                lines.append(pad + f"if {cond} then")
                lines.append(self._linearize_block_dict(blocks, s_then, set(visited), indent + 1))
                lines.append(pad + "else")
                lines.append(self._linearize_block_dict(blocks, s_else, set(visited), indent + 1))
                lines.append(pad + "end")
                break

            curr = b["next"]

        return "\n".join(lines)

    # =========================================================================
    # PASS 2.5: NESTED BINARY SEARCH TREE DISPATCHER UNFLATTENER (LURAPH V15 / V15.1)
    # =========================================================================
    @staticmethod
    def _get_ast_var_name(expr: Optional[Dict[str, Any]]) -> Optional[str]:
        if not expr or not isinstance(expr, dict):
            return None
        etype = expr.get("type")
        if etype == "AstExprLocal":
            return expr.get("local", {}).get("name") or expr.get("name")
        if etype == "AstExprGlobal":
            return expr.get("global")
        return None

    @staticmethod
    def _get_ast_number_val(expr: Optional[Dict[str, Any]]) -> Optional[int]:
        if not expr or not isinstance(expr, dict):
            return None
        etype = expr.get("type")
        if etype == "AstExprConstantNumber":
            try:
                return int(expr.get("value", 0))
            except Exception:
                return None
        if etype == "AstExprUnary" and expr.get("op") == "Minus":
            sub = CFFUnflattenerEngine._get_ast_number_val(expr.get("expr"))
            return -sub if sub is not None else None
        if etype == "AstExprGroup":
            return CFFUnflattenerEngine._get_ast_number_val(expr.get("expr"))
        return None

    def _extract_nested_bst_states(
        self,
        node: Optional[Dict[str, Any]],
        state_var: str,
        cur_min: int = 0,
        cur_max: int = 1000000
    ) -> Dict[int, List[Dict[str, Any]]]:
        if not node or not isinstance(node, dict):
            return {}
        ntype = node.get("type")
        if ntype == "AstStatBlock":
            body = node.get("body", [])
            if len(body) == 1 and body[0].get("type") == "AstStatIf":
                return self._extract_nested_bst_states(body[0], state_var, cur_min, cur_max)
            # Leaf block for interval [cur_min, cur_max]
            res: Dict[int, List[Dict[str, Any]]] = {}
            upper = min(cur_max, cur_min + 50) if cur_max >= 900000 else cur_max
            if cur_min <= upper:
                for s_id in range(cur_min, upper + 1):
                    res[s_id] = body
            res[cur_min] = body
            if not hasattr(self, "_bst_interval_map"):
                self._bst_interval_map = []
            self._bst_interval_map.append((cur_min, cur_max, body))
            return res

        if ntype == "AstStatIf":
            cond = node.get("condition", {})
            left_var = self._get_ast_var_name(cond.get("left")) if cond.get("type") == "AstExprBinary" else None
            right_var = self._get_ast_var_name(cond.get("right")) if cond.get("type") == "AstExprBinary" else None
            left_num = self._get_ast_number_val(cond.get("left")) if cond.get("type") == "AstExprBinary" else None
            right_num = self._get_ast_number_val(cond.get("right")) if cond.get("type") == "AstExprBinary" else None

            k = None
            effective_op = None
            if cond.get("type") == "AstExprBinary":
                op = cond.get("op")
                if left_var == state_var and right_num is not None:
                    k = right_num
                    effective_op = op
                elif right_var == state_var and left_num is not None:
                    k = left_num
                    flip_map = {
                        "CompareLe": "CompareGe",
                        "CompareLt": "CompareGt",
                        "CompareGe": "CompareLe",
                        "CompareGt": "CompareLt",
                        "CompareEq": "CompareEq",
                        "CompareNe": "CompareNe",
                    }
                    effective_op = flip_map.get(op)

            if k is not None and effective_op is not None:
                res: Dict[int, List[Dict[str, Any]]] = {}
                if effective_op == "CompareLe":
                    res.update(self._extract_nested_bst_states(node.get("thenbody"), state_var, cur_min, min(cur_max, k)))
                    res.update(self._extract_nested_bst_states(node.get("elsebody"), state_var, max(cur_min, k + 1), cur_max))
                elif effective_op == "CompareLt":
                    res.update(self._extract_nested_bst_states(node.get("thenbody"), state_var, cur_min, min(cur_max, k - 1)))
                    res.update(self._extract_nested_bst_states(node.get("elsebody"), state_var, max(cur_min, k), cur_max))
                elif effective_op == "CompareGe":
                    res.update(self._extract_nested_bst_states(node.get("thenbody"), state_var, max(cur_min, k), cur_max))
                    res.update(self._extract_nested_bst_states(node.get("elsebody"), state_var, cur_min, min(cur_max, k - 1)))
                elif effective_op == "CompareGt":
                    res.update(self._extract_nested_bst_states(node.get("thenbody"), state_var, max(cur_min, k + 1), cur_max))
                    res.update(self._extract_nested_bst_states(node.get("elsebody"), state_var, cur_min, min(cur_max, k)))
                elif effective_op == "CompareEq":
                    res.update(self._extract_nested_bst_states(node.get("thenbody"), state_var, k, k))
                    res.update(self._extract_nested_bst_states(node.get("elsebody"), state_var, cur_min, cur_max))
                elif effective_op == "CompareNe":
                    res.update(self._extract_nested_bst_states(node.get("thenbody"), state_var, cur_min, cur_max))
                    res.update(self._extract_nested_bst_states(node.get("elsebody"), state_var, k, k))
                return res
            else:
                # AstStatIf is regular domain code inside current state block
                res = {}
                upper = min(cur_max, cur_min + 50) if cur_max >= 900000 else cur_max
                if cur_min <= upper:
                    for s_id in range(cur_min, upper + 1):
                        res[s_id] = [node]
                res[cur_min] = [node]
                if not hasattr(self, "_bst_interval_map"):
                    self._bst_interval_map = []
                self._bst_interval_map.append((cur_min, cur_max, [node]))
                return res
        return {}

    def _parse_bst_state_transition(
        self,
        stmts: List[Dict[str, Any]],
        state_var: str
    ) -> Tuple[List[Dict[str, Any]], Optional[int], Optional[Tuple[Any, int, int]], bool]:
        domain_stmts = []
        next_st = None
        cond_br = None
        is_term = False

        for s in stmts:
            stype = s.get("type")
            if stype in ("AstStatReturn", "AstStatBreak"):
                is_term = True
                domain_stmts.append(s)
                continue

            if stype == "AstStatAssign":
                vars_list = s.get("vars", [])
                vals_list = s.get("values", [])
                matched_idx = -1
                for idx, v in enumerate(vars_list):
                    vname = self._get_ast_var_name(v)
                    if vname == state_var:
                        matched_idx = idx
                        break

                if matched_idx >= 0 and matched_idx < len(vals_list):
                    val_node = vals_list[matched_idx]
                    num_val = self._get_ast_number_val(val_node)
                    # Direct state assignment: state_var = Next
                    if num_val is not None:
                        next_st = num_val
                        rem_vars = [v for i, v in enumerate(vars_list) if i != matched_idx]
                        rem_vals = [vl for i, vl in enumerate(vals_list) if i != matched_idx]
                        if rem_vars:
                            s_copy = dict(s)
                            s_copy["vars"] = rem_vars
                            s_copy["values"] = rem_vals
                            domain_stmts.append(s_copy)
                        continue

                    # Idiomatic Luau ternary transition: (cond and StateA) or StateB
                    if val_node.get("type") == "AstExprBinary" and val_node.get("op") == "Or":
                        left_bin = val_node.get("left", {})
                        if left_bin.get("type") == "AstExprGroup":
                            left_bin = left_bin.get("expr", {})
                        if left_bin.get("type") == "AstExprBinary" and left_bin.get("op") == "And":
                            cond = left_bin.get("left")
                            t_num = self._get_ast_number_val(left_bin.get("right"))
                            f_num = self._get_ast_number_val(val_node.get("right"))
                            if t_num is not None and f_num is not None:
                                cond_br = (cond, t_num, f_num)
                                continue

                    # Luau IfElse expression: if cond then StateA else StateB
                    if val_node.get("type") == "AstExprIfElse":
                        cond = val_node.get("condition")
                        t_num = self._get_ast_number_val(val_node.get("trueExpr"))
                        f_num = self._get_ast_number_val(val_node.get("falseExpr"))
                        if t_num is not None and f_num is not None:
                            cond_br = (cond, t_num, f_num)
                            continue

            # Real statement if/then/else containing state transitions
            if stype == "AstStatIf":
                then_b = s.get("thenbody", {}).get("body", [])
                else_b = s.get("elsebody", {}).get("body", []) if s.get("elsebody") else []
                t_sub, t_nxt, _, _ = self._parse_bst_state_transition(then_b, state_var)
                f_sub, f_nxt, _, _ = self._parse_bst_state_transition(else_b, state_var)
                if t_nxt is not None and f_nxt is not None:
                    cond_br = (s.get("condition"), t_nxt, f_nxt)
                    if t_sub or f_sub:
                        s_copy = dict(s)
                        s_copy["thenbody"] = {"type": "AstStatBlock", "body": t_sub}
                        s_copy["elsebody"] = {"type": "AstStatBlock", "body": f_sub} if f_sub else None
                        domain_stmts.append(s_copy)
                    continue

            domain_stmts.append(s)

        return domain_stmts, next_st, cond_br, is_term

    def _find_bst_initial_state(self, parent_body: List[Dict[str, Any]], while_idx: int, state_var: str) -> Optional[int]:
        for i in range(while_idx - 1, -1, -1):
            prev = parent_body[i]
            ptype = prev.get("type")
            if ptype in ("AstStatLocal", "AstStatAssign"):
                vars_list = prev.get("vars", [])
                vals_list = prev.get("values", [])
                for idx, v in enumerate(vars_list):
                    if self._get_ast_var_name(v) == state_var:
                        if idx < len(vals_list):
                            num_val = self._get_ast_number_val(vals_list[idx])
                            if num_val is not None:
                                return num_val
        return None

    def _resolve_state_block(
        self,
        blocks: Dict[int, Tuple[List[Dict[str, Any]], Optional[int], Optional[Tuple[Any, int, int]], bool]],
        state_id: int
    ) -> Optional[Tuple[List[Dict[str, Any]], Optional[int], Optional[Tuple[Any, int, int]], bool]]:
        if state_id in blocks:
            return blocks[state_id]
        if hasattr(self, "_bst_interval_map"):
            for imin, imax, body in self._bst_interval_map:
                if imin <= state_id <= imax:
                    parsed = self._parse_bst_state_transition(body, "")
                    blocks[state_id] = parsed
                    return parsed
        return None

    def _can_reach_state(
        self,
        blocks: Dict[int, Tuple[List[Dict[str, Any]], Optional[int], Optional[Tuple[Any, int, int]], bool]],
        from_st: int,
        target_st: int,
        seen: Optional[Set[int]] = None
    ) -> bool:
        if seen is None:
            seen = set()
        if from_st == target_st:
            return True
        if from_st in seen:
            return False
        seen.add(from_st)
        blk = self._resolve_state_block(blocks, from_st)
        if not blk:
            return False
        dom, nxt, cbr, is_term = blk
        if is_term:
            return False
        if cbr:
            _, t_st, f_st = cbr
            return self._can_reach_state(blocks, t_st, target_st, seen) or self._can_reach_state(blocks, f_st, target_st, seen)
        if nxt is not None:
            return self._can_reach_state(blocks, nxt, target_st, seen)
        return False

    def _linearize_loop_body(
        self,
        blocks: Dict[int, Tuple[List[Dict[str, Any]], Optional[int], Optional[Tuple[Any, int, int]], bool]],
        start_state: int,
        loop_header: int,
        visited: Optional[Set[int]] = None
    ) -> List[Dict[str, Any]]:
        if visited is None:
            visited = set()
        if start_state == loop_header or start_state in visited:
            return []
        visited.add(start_state)
        blk = self._resolve_state_block(blocks, start_state)
        if not blk:
            return []
        dom, nxt, cbr, is_term = blk
        result = list(dom)
        if is_term or nxt == loop_header:
            return result
        if cbr:
            cond, t_st, f_st = cbr
            t_stmts = self._linearize_loop_body(blocks, t_st, loop_header, set(visited))
            f_stmts = self._linearize_loop_body(blocks, f_st, loop_header, set(visited))
            result.append({
                "type": "AstStatIf",
                "condition": cond,
                "thenbody": {"type": "AstStatBlock", "body": t_stmts},
                "elsebody": {"type": "AstStatBlock", "body": f_stmts} if f_stmts else None
            })
            return result
        if nxt is not None and nxt != loop_header:
            result.extend(self._linearize_loop_body(blocks, nxt, loop_header, visited))
        return result

    def _linearize_bst_cfg(
        self,
        blocks: Dict[int, Tuple[List[Dict[str, Any]], Optional[int], Optional[Tuple[Any, int, int]], bool]],
        start_state: Optional[int],
        visited: Optional[Set[int]] = None,
        path_stack: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        if visited is None:
            visited = set()
        if path_stack is None:
            path_stack = []

        if start_state is None:
            return []

        blk = self._resolve_state_block(blocks, start_state)
        if not blk:
            return []

        if start_state in path_stack:
            return []

        visited.add(start_state)
        path_stack.append(start_state)

        dom, nxt, cbr, is_term = blk
        result = list(dom)

        if is_term:
            path_stack.pop()
            return result

        if cbr:
            cond, s_then, s_else = cbr
            # Check for structured while-loop
            if self._can_reach_state(blocks, s_then, start_state):
                loop_body = self._linearize_loop_body(blocks, s_then, loop_header=start_state)
                result.append({
                    "type": "AstStatWhile",
                    "condition": cond,
                    "body": {"type": "AstStatBlock", "body": loop_body}
                })
                after_loop = self._linearize_bst_cfg(blocks, s_else, visited, list(path_stack))
                result.extend(after_loop)
                path_stack.pop()
                return result
            elif self._can_reach_state(blocks, s_else, start_state):
                loop_body = self._linearize_loop_body(blocks, s_else, loop_header=start_state)
                result.append({
                    "type": "AstStatWhile",
                    "condition": {"type": "AstExprUnary", "op": "Not", "expr": cond},
                    "body": {"type": "AstStatBlock", "body": loop_body}
                })
                after_loop = self._linearize_bst_cfg(blocks, s_then, visited, list(path_stack))
                result.extend(after_loop)
                path_stack.pop()
                return result

            then_stmts = self._linearize_bst_cfg(blocks, s_then, set(visited), list(path_stack))
            else_stmts = self._linearize_bst_cfg(blocks, s_else, set(visited), list(path_stack))
            result.append({
                "type": "AstStatIf",
                "condition": cond,
                "thenbody": {"type": "AstStatBlock", "body": then_stmts},
                "elsebody": {"type": "AstStatBlock", "body": else_stmts} if else_stmts else None
            })
            path_stack.pop()
            return result

        if nxt is not None:
            result.extend(self._linearize_bst_cfg(blocks, nxt, visited, path_stack))

        path_stack.pop()
        return result

    def _walk_and_unflatten_nested_bst(self, block_node: Optional[Dict[str, Any]]) -> int:
        if not block_node or block_node.get("type") != "AstStatBlock":
            return 0
        body = block_node.get("body", [])
        new_body = []
        transformed = 0
        i = 0

        while i < len(body):
            stmt = body[i]
            stype = stmt.get("type")

            # Recurse into nested structures
            if stype in ("AstStatFunction", "AstStatLocalFunction"):
                transformed += self._walk_and_unflatten_nested_bst(stmt.get("body"))
            elif stype == "AstStatIf":
                transformed += self._walk_and_unflatten_nested_bst(stmt.get("thenbody"))
                transformed += self._walk_and_unflatten_nested_bst(stmt.get("elsebody"))
            elif stype in ("AstStatWhile", "AstStatRepeat", "AstStatDo"):
                transformed += self._walk_and_unflatten_nested_bst(stmt.get("body"))

            # Check if this While/Repeat statement is a Nested BST Dispatcher
            if stype in ("AstStatWhile", "AstStatRepeat"):
                w_body = stmt.get("body", {}).get("body", [])
                if w_body:
                    for if_root_idx, if_candidate in enumerate(w_body):
                        if if_candidate.get("type") != "AstStatIf":
                            continue

                        cond = if_candidate.get("condition", {})
                        if cond.get("type") != "AstExprBinary":
                            continue

                        left_var = self._get_ast_var_name(cond.get("left"))
                        right_var = self._get_ast_var_name(cond.get("right"))
                        left_num = self._get_ast_number_val(cond.get("left"))
                        right_num = self._get_ast_number_val(cond.get("right"))

                        state_var = None
                        if left_var and right_num is not None:
                            state_var = left_var
                        elif right_var and left_num is not None:
                            state_var = right_var

                        if not state_var:
                            continue

                        raw_blocks = self._extract_nested_bst_states(if_candidate, state_var)
                        if len(raw_blocks) >= 2:
                            parsed_blocks = {}
                            for sid, stmts in raw_blocks.items():
                                parsed_blocks[sid] = self._parse_bst_state_transition(stmts, state_var)

                            init_state = self._find_bst_initial_state(body, i, state_var)
                            if init_state is None or init_state not in parsed_blocks:
                                init_state = min(parsed_blocks.keys())

                            linear_stmts = self._linearize_bst_cfg(parsed_blocks, init_state)
                            if linear_stmts:
                                # Preserve any meaningful statements before the if
                                prelude = [s for j, s in enumerate(w_body[:if_root_idx]) if s.get("type") != "AstStatLocal" or s.get("values")]
                                if prelude:
                                    new_body.extend(prelude)
                                new_body.extend(linear_stmts)
                                transformed += 1
                                i += 1
                                break
                    else:
                        new_body.append(stmt)
                        i += 1
                    continue

            new_body.append(stmt)
            i += 1

        block_node["body"] = new_body
        return transformed

    def _unflatten_nested_bst_dispatchers(self, code: str) -> str:
        if "while" not in code and "repeat" not in code:
            return code
        if "<=" not in code and "<" not in code and ">" not in code and ">=" not in code and "==" not in code:
            return code
        try:
            self._bst_interval_map = []
            ast = luauast.parse(code)
            count = self._walk_and_unflatten_nested_bst(ast)

            # Also inspect expression blocks (e.g. functions inside return tables)
            def walk_expressions(node):
                if not node or not isinstance(node, dict):
                    return 0
                cnt = 0
                for v in list(node.values()):
                    if isinstance(v, dict):
                        if v.get("type") == "AstStatBlock":
                            cnt += self._walk_and_unflatten_nested_bst(v)
                        cnt += walk_expressions(v)
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                if item.get("type") == "AstStatBlock":
                                    cnt += self._walk_and_unflatten_nested_bst(item)
                                cnt += walk_expressions(item)
                return cnt

            count += walk_expressions(ast)
            if count > 0:
                self.stats["bst_dispatchers"] += count
                return luauast.render(ast)
        except Exception:
            pass
        return code

    # =========================================================================
    # PASS 3: FULL AST WHILE-ELSEIF DISPATCHER UNFLATTENER
    # =========================================================================
    def _unflatten_ast_loops(self, code: str) -> str:
        if "while" not in code:
            return code
        try:
            ast = luauast.parse(code)
            self._walk_and_transform_block(ast)
            return luauast.render(ast)
        except Exception:
            return code

    def _walk_and_transform_block(self, block_node):
        if not block_node or block_node.get("type") != "AstStatBlock":
            return

        body = block_node.get("body", [])
        new_body = []
        i = 0

        while i < len(body):
            stmt = body[i]

            # Recurse into nested structures
            if stmt["type"] == "AstStatIf":
                self._walk_and_transform_block(stmt.get("thenbody"))
                self._walk_and_transform_block(stmt.get("elsebody"))
            elif stmt["type"] in ("AstStatFunction", "AstStatLocalFunction"):
                self._walk_and_transform_block(stmt.get("body"))
            elif stmt["type"] == "AstStatWhile":
                self._walk_and_transform_block(stmt.get("body"))
            elif stmt["type"] == "AstStatRepeat":
                self._walk_and_transform_block(stmt.get("body"))

            # Check if this While statement is a State Dispatcher
            if stmt["type"] == "AstStatWhile":
                transformed_stmts = self._try_transform_while_dispatcher(body, i)
                if transformed_stmts is not None:
                    # Pop declaration of state variable if it immediately preceded
                    if len(new_body) > 0 and self._is_state_decl(new_body[-1]):
                        new_body.pop()

                    self.stats["flat_dispatchers"] += 1
                    new_body.extend(transformed_stmts)
                    i += 1
                    continue

            new_body.append(stmt)
            i += 1

        block_node["body"] = new_body

    def _is_state_decl(self, stmt):
        return stmt["type"] in ("AstStatLocal", "AstStatAssign")

    def _try_transform_while_dispatcher(self, parent_stmts, while_idx):
        while_stmt = parent_stmts[while_idx]
        while_body_stmts = while_stmt.get("body", {}).get("body", [])
        if not while_body_stmts:
            return None

        # State variable check from previous statement
        var_name, init_val = self._find_state_var_init(parent_stmts, while_idx)
        if not var_name or init_val is None:
            return None

        first_stmt = while_body_stmts[0]
        if first_stmt.get("type") != "AstStatIf":
            return None

        # Collect blocks
        blocks = {}
        curr = first_stmt
        while curr and curr.get("type") == "AstStatIf":
            cond = curr.get("condition", {})
            if cond.get("type") == "AstExprBinary" and cond.get("op") == "CompareEq":
                left = cond.get("left", {})
                right = cond.get("right", {})
                left_name = left.get("name") or (left.get("local") and left["local"].get("name")) or left.get("global")
                if left_name == var_name and right.get("type") == "AstExprConstantNumber":
                    st_id = int(right["value"])
                    then_stmts = curr.get("thenbody", {}).get("body", [])
                    blocks[st_id] = self._process_ast_then_block(then_stmts, var_name)

            curr = curr.get("elsebody")

        if blocks and init_val in blocks:
            return self._trace_ast_cfg(blocks, init_val)

        return None

    def _find_state_var_init(self, stmts, while_idx):
        if while_idx <= 0:
            return None, None
        prev = stmts[while_idx - 1]

        if prev["type"] == "AstStatLocal":
            vars_list = prev.get("vars", [])
            values_list = prev.get("values", [])
            if vars_list and values_list:
                name = vars_list[0].get("name")
                if values_list[0].get("type") == "AstExprConstantNumber":
                    return name, int(values_list[0]["value"])

        elif prev["type"] == "AstStatAssign":
            vars_list = prev.get("vars", [])
            values_list = prev.get("values", [])
            if vars_list and values_list:
                first_var = vars_list[0]
                name = first_var.get("name") or (first_var.get("local") and first_var["local"].get("name")) or first_var.get("global")
                if values_list[0].get("type") == "AstExprConstantNumber":
                    return name, int(values_list[0]["value"])

        return None, None

    def _process_ast_then_block(self, stmts, state_var):
        domain_stmts = []
        next_state = None
        cond_branch = None
        is_terminal = False

        for stmt in stmts:
            if stmt["type"] == "AstStatReturn":
                is_terminal = True
                domain_stmts.append(stmt)
            elif stmt["type"] == "AstStatBreak":
                is_terminal = True
            elif stmt["type"] == "AstStatAssign":
                first_var = stmt.get("vars", [{}])[0]
                name = first_var.get("name") or (first_var.get("local") and first_var["local"].get("name")) or first_var.get("global")
                if name == state_var:
                    val_expr = stmt.get("values", [{}])[0]
                    if val_expr.get("type") == "AstExprConstantNumber":
                        next_state = int(val_expr["value"])
                    elif val_expr.get("type") == "AstExprIfElse":
                        cond = val_expr.get("condition")
                        true_val = val_expr.get("trueExpr", {}).get("value")
                        false_val = val_expr.get("falseExpr", {}).get("value")
                        if true_val is not None and false_val is not None:
                            cond_branch = (cond, int(true_val), int(false_val))
                else:
                    domain_stmts.append(stmt)
            else:
                domain_stmts.append(stmt)

        return {
            "stmts": domain_stmts,
            "next": next_state,
            "cond_branch": cond_branch,
            "is_terminal": is_terminal
        }

    def _trace_ast_cfg(self, blocks, curr_state, visited=None):
        if visited is None:
            visited = set()
        if curr_state is None or curr_state not in blocks or curr_state in visited:
            return []

        visited.add(curr_state)
        blk = blocks[curr_state]
        result = list(blk["stmts"])

        if blk["is_terminal"]:
            return result

        if blk["cond_branch"]:
            cond, s_then, s_else = blk["cond_branch"]
            then_stmts = self._trace_ast_cfg(blocks, s_then, set(visited))
            else_stmts = self._trace_ast_cfg(blocks, s_else, set(visited))

            if_node = {
                "type": "AstStatIf",
                "condition": cond,
                "thenbody": {"type": "AstStatBlock", "body": then_stmts},
                "elsebody": {"type": "AstStatBlock", "body": else_stmts} if else_stmts else None
            }
            result.append(if_node)
            return result

        if blk["next"] is not None:
            result.extend(self._trace_ast_cfg(blocks, blk["next"], visited))

        return result


def unflatten_cff_code(code: str) -> Tuple[str, Dict[str, int]]:
    engine = CFFUnflattenerEngine(code)
    return engine.run()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("🔓 PAYOMBOYZ CFF State Dispatcher Unflattener")
        print("Usage: python cff_unflattener.py <input.lua> [-o output.lua]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = None
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()

    print(f"[*] Reading {input_path} ({len(src)} bytes)...")
    result, stats = unflatten_cff_code(src)
    print(f"[+] Total CFF Dispatchers Unflattened: {stats['total_unflattened']}")
    print(f"    - Array/String-Split Loops: {stats['array_dispatchers']}")
    print(f"    - Flat While-If Loops:     {stats['flat_dispatchers']}")
    print(f"    - BST Affine State Loops:   {stats['bst_dispatchers']}")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[+] Clean source written to: {output_path}")
    else:
        print("\n--- PREVIEW (first 60 lines) ---")
        for line in result.splitlines()[:60]:
            print(line)
