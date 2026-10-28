"""
cff_deflattener.py - Control Flow Flattening (CFF) De-Flattener for Luau / Luraph / Luarmor
Reconstructs structured control flow (sequential blocks, if/then/else, loops)
from flattened state-machine dispatchers.
"""
import re
from typing import Dict, Optional, Tuple, List, Set

class CFGNode:
    def __init__(self, state_id: int):
        self.state_id = state_id
        self.statements: List[str] = []      # list of statement strings
        self.cond: Optional[str] = None      # condition string if branching
        self.true_target: Optional[int] = None    # state_id
        self.false_target: Optional[int] = None   # state_id
        self.is_terminal: bool = False
        self.terminal_stmt: Optional[str] = None  # return, break, error


def parse_state_blocks(loop_body_text: str, state_var: str = "state") -> Dict[int, CFGNode]:
    """
    Parses an 'if state == X then ... elseif state == Y then ...' block into CFG nodes.
    Supports hex (0x1020), decimal, parenthesized comparisons, and dynamic state-variable discovery.
    """
    nodes: Dict[int, CFGNode] = {}
    
    # Auto-detect state variable if state_var is default or "true" or not present in comparisons
    effective_var = state_var
    if effective_var in ("true", "1", "state") or f"{effective_var} ==" not in loop_body_text:
        detected_vars = re.findall(r'(?:if|elseif)\s+(?:\(\s*)?([a-zA-Z0-9_]+)\s*==\s*(?:0x[0-9a-fA-F]+|-?\d+)', loop_body_text)
        if detected_vars:
            from collections import Counter
            effective_var = Counter(detected_vars).most_common(1)[0][0]

    # Matches 'if (state == 123) then', 'if state == 0x1020 and (...) then', etc.
    split_pattern = rf'(?:if|elseif)\s+(?:\(\s*)?{effective_var}\s*==\s*(0x[0-9a-fA-F]+|-?\d+)(?:[^\n]*?)\s+then'
    parts = re.split(split_pattern, loop_body_text)
    if len(parts) <= 1:
        return {}

    for i in range(1, len(parts), 2):
        try:
            s_id = int(parts[i], 0)
        except ValueError:
            continue

        block_text = parts[i + 1]
        node = CFGNode(s_id)
        
        lines = [l.strip() for l in block_text.splitlines() if l.strip()]
        stmts: List[str] = []
        cond: Optional[str] = None
        t_target: Optional[int] = None
        f_target: Optional[int] = None
        
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            if line.startswith("end") or line == "end;" or line == "else":
                idx += 1
                continue
            
            # Unconditional state change: state = Z or state = 0x123
            m_trans = re.match(rf'^{effective_var}\s*=\s*(0x[0-9a-fA-F]+|-?\d+);?$', line)
            if m_trans:
                try:
                    t_target = int(m_trans.group(1), 0)
                except ValueError:
                    pass
                idx += 1
                continue
                
            # Conditional state transition:
            # if <cond> then state = X else state = Y end
            m_if = re.match(r'^if\s+(.*?)\s+then$', line)
            if m_if:
                c_str = m_if.group(1)
                if idx + 4 < len(lines):
                    l1 = lines[idx + 1]
                    l2 = lines[idx + 2]
                    l3 = lines[idx + 3]
                    l4 = lines[idx + 4]
                    m_s1 = re.match(rf'^{effective_var}\s*=\s*(0x[0-9a-fA-F]+|-?\d+);?$', l1)
                    m_s2 = re.match(rf'^{effective_var}\s*=\s*(0x[0-9a-fA-F]+|-?\d+);?$', l3)
                    if m_s1 and l2 == "else" and m_s2 and (l4.startswith("end")):
                        cond = c_str
                        t_target = int(m_s1.group(1), 0)
                        f_target = int(m_s2.group(1), 0)
                        idx += 5
                        continue
            
            # Terminal statements
            if line.startswith("return") or line == "break":
                node.is_terminal = True
                node.terminal_stmt = line
                stmts.append(line)
                idx += 1
                continue
                
            if line.startswith('error("devirt:') or line.startswith('error('):
                node.is_terminal = True
                node.terminal_stmt = line
                stmts.append(line)
                idx += 1
                continue

            # Regular assignment / call statement (skip state variable assignments)
            if not re.match(rf'^{effective_var}\s*=', line):
                # Clean any dangling 'else' prefix or trailing 'end'
                cleaned_line = re.sub(r'^else\s+', '', line).strip()
                cleaned_line = re.sub(r'\bend;?$', '', cleaned_line).strip()
                if cleaned_line and cleaned_line != "else" and not cleaned_line.startswith("end"):
                    stmts.append(cleaned_line)
            idx += 1
            
        node.statements = stmts
        node.cond = cond
        node.true_target = t_target
        node.false_target = f_target
        nodes[s_id] = node

    return nodes


def de_flatten_cfg(nodes: Dict[int, CFGNode], start_state: int = 1, max_depth: int = 200) -> str:
    """
    Traverses and structures CFG nodes into formatted Luau statements.
    Eliminates dead trap branches (e.g. anti-tamper traps calling error("devirt:")).
    """
    if not nodes:
        return ""

    # If start_state is not in nodes, pick the first or smallest key
    if start_state not in nodes:
        sorted_keys = sorted(nodes.keys())
        start_state = sorted_keys[0] if sorted_keys else 1

    def emit_block(state_id: int, depth: int = 0, call_visited: Optional[Set[int]] = None) -> List[str]:
        if call_visited is None:
            call_visited = set()
            
        if state_id in call_visited or depth > max_depth or state_id == 0:
            return []
            
        if state_id not in nodes:
            return []
            
        node = nodes[state_id]
        lines: List[str] = []
        indent = "    " * depth
        
        # Add non-empty statements
        for s in node.statements:
            if not s.startswith('error("devirt:') and s not in ("else", "end", "end;"):
                lines.append(f"{indent}{s}")
                
        if node.is_terminal:
            return lines

        new_visited = set(call_visited)
        new_visited.add(state_id)

        # If conditional branch
        if node.cond and node.true_target and node.false_target:
            from bot.z3_cff_solver import Z3CFFSolver
            opaque_eval = Z3CFFSolver.evaluate_predicate(node.cond)

            if opaque_eval is True:
                # Opaque Predicate (Tautology): True branch is always taken!
                lines.extend(emit_block(node.true_target, depth, new_visited))
            elif opaque_eval is False:
                # Opaque Predicate (Contradiction): False branch is always taken!
                lines.extend(emit_block(node.false_target, depth, new_visited))
            else:
                t_node = nodes.get(node.true_target)
                f_node = nodes.get(node.false_target)

                # Check if one of them is a dead error trap
                t_is_trap = t_node and any('error("devirt:' in s for s in t_node.statements)
                f_is_trap = f_node and any('error("devirt:' in s for s in f_node.statements)

                if t_is_trap:
                    lines.extend(emit_block(node.false_target, depth, new_visited))
                elif f_is_trap:
                    lines.extend(emit_block(node.true_target, depth, new_visited))
                else:
                    t_stmts = emit_block(node.true_target, depth + 1, new_visited)
                    f_stmts = emit_block(node.false_target, depth + 1, new_visited)

                    lines.append(f"{indent}if {node.cond} then")
                    lines.extend(t_stmts)
                    if f_stmts:
                        lines.append(f"{indent}else")
                        lines.extend(f_stmts)
                    lines.append(f"{indent}end")
        elif node.true_target and node.true_target != 0:
            lines.extend(emit_block(node.true_target, depth, new_visited))

        return lines

    result = emit_block(start_state)
    return "\n".join(result)


def find_balanced_loop_end(text: str, start_pos: int) -> int:
    """Finds the matching 'end' token for a block that started at start_pos (right after 'do')."""
    depth = 1
    token_pat = re.compile(r'\b(elseif\b[^\n\r]*?\bthen|then|do|function|end)\b')
    for m in token_pat.finditer(text, start_pos):
        tok = m.group(1)
        if tok.startswith("elseif"):
            continue
        elif tok in ("then", "do", "function"):
            depth += 1
        elif tok == "end":
            depth -= 1
            if depth == 0:
                end_idx = m.end()
                if end_idx < len(text) and text[end_idx] == ';':
                    end_idx += 1
                return end_idx
    return -1


def deflatten_all_cff_blocks(code: str, enable_ai_fallback: bool = False) -> str:
    """
    High-level universal function: Scans an entire Lua/Luau script for all CFF state-machine
    while-loops (`while state ~= 0 do`, `while _cff > 0 do`, etc.),
    structures them via CFG graph walk, and replaces them with clean linear code.
    Deterministic graph walk only - zero AI hallucination.
    """
    loop_start_pat = re.compile(
        r'(?:local\s+([a-zA-Z0-9_]+)\s*=\s*(0x[0-9a-fA-F]+|-?\d+);?\s*)?'
        r'while\s+([a-zA-Z0-9_]+(?:\s*(?:~=|>|<|==)\s*(?:0|0x0|-?\d+|0x[0-9a-fA-F]+))?)\s+do'
    )

    cur = 0
    pieces = []
    while cur < len(code):
        m = loop_start_pat.search(code, cur)
        if not m:
            pieces.append(code[cur:])
            break

        start_idx = m.start()
        pieces.append(code[cur:start_idx])

        do_pos = m.end()
        loop_end = find_balanced_loop_end(code, do_pos)
        if loop_end == -1:
            pieces.append(code[start_idx:do_pos])
            cur = do_pos
            continue

        decl_var = m.group(1)
        init_val_str = m.group(2)
        raw_loop_cond = m.group(3).strip()
        loop_var = raw_loop_cond.split()[0] if raw_loop_cond else "state"
        body = code[do_pos:loop_end - 3]  # minus matching 'end'

        start_state = 1
        if init_val_str:
            try:
                start_state = int(init_val_str, 0)
            except ValueError:
                start_state = 1

        unwound = ""
        try:
            nodes = parse_state_blocks(body, state_var=loop_var)
            if len(nodes) >= 2:
                unwound = de_flatten_cfg(nodes, start_state=start_state)
        except Exception:
            pass

        # If static CFG could resolve, use clean unwound code; otherwise preserve original verbatim
        if not unwound.strip() and enable_ai_fallback:
            try:
                unwound = ai_deflatten_cff_shard(code[start_idx:loop_end])
            except Exception:
                pass

        if unwound.strip():
            pieces.append(unwound.strip())
        else:
            pieces.append(code[start_idx:loop_end])

        cur = loop_end

    return "".join(pieces)


def ai_deflatten_cff_shard(loop_text: str) -> str:
    """
    AI Fallback for Complex / Non-Linear CFF:
    Uses the 17-agent AI fleet (DeepSeek -> ThaiLLM Qwen 3.6 35B -> Bluezy -> Gemini)
    under O.Z.L.S.R Protocol to perform symbolic execution and reconstruct clean Luau code.
    """
    # Brand protection guard
    try:
        from bot.brand_protection import check_brand_protection
        if check_brand_protection(loop_text)[0]:
            return loop_text
    except Exception:
        pass

    try:
        from bot.hybrid_router import HYBRID_ROUTER
        prompt = (
            "You are the PAYOMBØYZ Chief CFF Deflattener (O.Z.L.S.R Protocol).\n"
            "This Luau code is flattened into a complex state machine (CFF). "
            "Trace the state transitions, unwind the state machine, eliminate dead branches, "
            "and reconstruct clean, structured, linear Luau source code (with if-then-else and sequential statements). "
            "Preserve all original statements, variable scopes, and logic exactly. "
            "Output ONLY the reconstructed Luau code inside a ```lua ... ``` block. No conversational filler.\n\n"
            f"```lua\n{loop_text[:7500]}\n```"
        )
        for provider in ["openrouter", "thaillm", "bluezygpt", "gemini"]:
            try:
                res = HYBRID_ROUTER.query_supervised(
                    prompt=prompt,
                    user_request="Deflatten complex Luau CFF state machine",
                    system_prompt="You are a senior compiler deobfuscator under O.Z.L.S.R Protocol. Output only clean Luau code.",
                    mode="deobfuscate",
                    preferred_provider=provider
                )
                if res.get("success"):
                    reply = res.get("reply") or res.get("text") or ""
                    m = re.search(r'```(?:lua|luau)?\s*\n(.*?)\n```', reply, re.DOTALL)
                    clean = m.group(1).strip() if m else reply.strip()
                    if clean and len(clean.splitlines()) >= 2:
                        return clean
            except Exception:
                continue
    except Exception as e:
        print(f"[CFF AI DEFLATTENER] Fallback skipped: {e}", flush=True)
    return loop_text

