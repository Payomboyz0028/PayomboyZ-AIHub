# -*- coding: utf-8 -*-
"""
Two-tier CFF De-flattener for Luraph v14
Reconstructs linear flow and application control flow from 
nested state machine dispatch trees (state + r10 registers).
"""

import re
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def deflatten_v14_cff(code: str) -> str:
    lines = code.splitlines()
    
    # Extract blocks
    blocks = {}
    current_state = None
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("if state == ") or stripped.startswith("elseif state == "):
            if current_state is not None:
                blocks[current_state] = current_lines
            s_id = int(stripped.split("==")[1].split("then")[0].strip())
            current_state = s_id
            current_lines = []
        elif current_state is not None:
            if stripped != "end":
                current_lines.append(stripped)

    if current_state is not None:
        blocks[current_state] = current_lines

    print(f"[*] Parsed {len(blocks)} total states.")

    # Classify blocks
    dispatch_blocks = {}
    inst_blocks = {}

    for s_id, blk in blocks.items():
        blk_text = "\n".join(blk).strip()
        m_disp = re.match(r"^if\s+([a-zA-Z0-9_]+)\s*(>|<|>=|<=|==|~=|!=)\s*([0-9]+)\s+then\s*state\s*=\s*(\d+)\s*else\s*state\s*=\s*(\d+)$", blk_text)
        if m_disp and ("r10" in m_disp.group(1) or "r158" in m_disp.group(1)):
            dispatch_blocks[s_id] = (m_disp.group(1), m_disp.group(2), int(m_disp.group(3)), int(m_disp.group(4)), int(m_disp.group(5)))
        else:
            inst_blocks[s_id] = blk

    print(f"[*] Dispatch nodes: {len(dispatch_blocks)} | Instruction nodes: {len(inst_blocks)}")

    def resolve_next(state, regs):
        visited = set()
        curr = state
        while curr in dispatch_blocks and curr not in visited:
            visited.add(curr)
            var, op, val, s_then, s_else = dispatch_blocks[curr]
            v = regs.get(var, 0)
            cond = False
            if op == ">": cond = (v > val)
            elif op == "<": cond = (v < val)
            elif op == ">=": cond = (v >= val)
            elif op == "<=": cond = (v <= val)
            elif op == "==": cond = (v == val)
            elif op in ("~=", "!="): cond = (v != val)
            curr = s_then if cond else s_else
        return curr

    # Build CFG among instruction blocks
    # Trace linear sequence starting from state 1
    output_statements = []
    visited_states = set()
    regs = {}
    curr_state = 1

    while curr_state and curr_state not in visited_states and curr_state in inst_blocks:
        visited_states.add(curr_state)
        blk = inst_blocks[curr_state]

        # Process statements in blk
        clean_stmt = []
        next_state_candidates = []

        i = 0
        while i < len(blk):
            l = blk[i]
            # State assignment
            m_st = re.match(r"^state\s*=\s*(\d+)$", l)
            m_rg = re.match(r"^([a-zA-Z0-9_]+)\s*=\s*([0-9]+)$", l)
            
            # Check for conditional branch at block end:
            # if cond then state = A else state = B
            m_branch = re.match(r"^if\s+(.*?)\s+then$", l)
            if m_branch:
                cond_expr = m_branch.group(1)
                # peek next lines
                # line i+1: state = X
                # line i+2: else
                # line i+3: state = Y
                if i + 3 < len(blk):
                    m_s1 = re.match(r"^state\s*=\s*(\d+)$", blk[i+1])
                    m_el = blk[i+2] == "else"
                    m_s2 = re.match(r"^state\s*=\s*(\d+)$", blk[i+3])
                    if m_s1 and m_el and m_s2:
                        s1 = int(m_s1.group(1))
                        s2 = int(m_s2.group(1))
                        # Resolve both targets through dispatch
                        t1 = resolve_next(s1, regs)
                        t2 = resolve_next(s2, regs)
                        clean_stmt.append(f"if {cond_expr} then --[[ target: state {t1} ]]")
                        clean_stmt.append(f"else --[[ target: state {t2} ]]")
                        clean_stmt.append("end")
                        i += 4
                        continue
            
            if m_st:
                next_st = int(m_st.group(1))
                resolved = resolve_next(next_st, regs)
                next_state_candidates.append(resolved)
            else:
                if m_rg and m_rg.group(1).startswith("r10"):
                    regs[m_rg.group(1)] = int(m_rg.group(2))
                else:
                    clean_stmt.append(l)
            i += 1

        output_statements.extend(clean_stmt)
        if next_state_candidates:
            curr_state = next_state_candidates[0]
        else:
            break

    print(f"[*] Linearized {len(visited_states)} instruction blocks into {len(output_statements)} statements.")
    return "\n".join(output_statements)

if __name__ == "__main__":
    src_file = r"d:\Deobfuscate\test_key_v14_direct.luau"
    if os.path.exists(src_file):
        with open(src_file, "r", encoding="utf-8") as f:
            code = f.read()
        res = deflatten_v14_cff(code)
        out_file = r"d:\Deobfuscate\test_key_v14_deflatted.luau"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(res)
        print(f"[+] Written to {out_file} ({len(res.splitlines())} lines)")
