import sys
import os
import subprocess
import json
import re

CORE_DIR = r"d:\Deobfuscate\Lerning\Luraph\New\v15_tool_attempt_source\core"
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from obfuscators.luraph_v14 import vmmap as v14_vmmap
from obfuscators.luraph_v14 import devirt as v14_devirt
from obfuscators.base import Job
import harness

src_path = r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Key-obfuscated.lua"
with open(src_path, "r", encoding="latin-1") as f:
    source = f.read()

root = v14_vmmap.load_ast(src_path)
lines = source.split("\n")
edits = []

for l1, c1, pv in v14_vmmap.closure_entries(root):
    k = f"({pv} or __PID)"
    edits.append((l1, c1, f"if not __PID[{k}] then __PID.n=__PID.n+1;__PID[{k}]=__PID.n;end;"
                           f"__ENT.n=__ENT.n+1;__ENT[__ENT.n%64]=__PID[{k}];__PLAST[__PID[{k}]]=__ENT.n;"
                           f"if __SKIPP[__PID[{k}]] then return end;"))

tag = harness.chunk_key(source)
for info in v14_vmmap.maker_info(root):
    (l2, c2), var, pv = info["at"], info["var"], info["proto"]
    code = f" __PF[{var}]={info.get('pf_key', pv)} "
    cap = "".join(f"__PA[{pv}].{nm}={nm};" for nm in info["captures"])
    maker_str = f"{tag}@{l2},{c2}"
    code += (f"if __PA and not __PA[{pv}] then __PA[{pv}]={{}};__PA.n=__PA.n+1;__PA[{pv}].__seq=__PA.n;"
             f"__PA[{pv}].__maker=\"{maker_str}\";__PK[{info.get('pf_key', pv)}]={var};{cap} end ")
    edits.append((l2, c2, code))

for l, c, code in sorted(edits, reverse=True):
    lines[l] = lines[l][:c] + code + lines[l][c:]

patched = "\n".join(lines)
print(f"[*] Edits applied: {len(edits)}")

class Args:
    cfg = []
    keep_harness = False
    no_hooks = False
    no_devirt = False
    max_runs = 1
    raw = None
    input_text = None
    port = None
    budget = 10
    executor = "Wave"
    strings = False
    no_fold = False
    devirt_rounds = 200
    studio = False
    timeout = 60


args = Args()
job = Job(src_path, source, args, r"d:\Deobfuscate\test_trace.luau", False, "Luraph v14")
runner = harness.Runner(job)
runner.luau = r"d:\Deobfuscate\Lerning\Luraph\New\v15_tool_attempt_source\bin\luau.exe"
cfg = {"devirt": True, "time_budget": 10, "executor": "Wave"}
res = runner.run(patched, cfg, {})
runner.finish()
body = res[0] or ""
print(f"[*] Trace body length: {len(body)}")
m = re.search(re.escape(harness.mark("PROTOS ")) + r"([^\n]*)\n", body)
if m:
    protos_raw = m.group(1)
    print(f"[*] PROTOS raw length: {len(protos_raw)}")
    # Save raw protos first
    ppath = r"d:\Deobfuscate\test_v14_protos.json"
    with open(ppath, "w", encoding="utf-8") as f:
        f.write(protos_raw)
    print(f"[*] Saved raw protos to {ppath}")
    print("[*] Snippet around char 577:")
    print(protos_raw[max(0, 577-50):min(len(protos_raw), 577+50)])
    try:
        pj = json.loads(protos_raw)
        protos_dict = pj.get("protos", {})
        tables_dict = pj.get("tables", {})
        print(f"[+] Protos count: {len(protos_dict)}")
        print(f"[+] Tables count: {len(tables_dict)}")
    except Exception as je:
        print(f"[!] JSON parse error: {je}")

    
    # Try devirtualization step
    dpath = r"d:\Deobfuscate\test_v14_lifted.luau"
    print("[*] Testing lift_program with luraph_v14 devirt...")
    try:
        text, stats, reqs, bufs = v14_devirt.run_big_stack(
            v14_devirt.lift_program, src_path, ppath, [], None
        )
        print(f"[+] Lift success! Stats: {stats}")
        print(f"[+] Reqs count: {len(reqs)}: {list(reqs)[:20]}")
        print(f"[+] Bufs len: {len(bufs)}")
        with open(dpath, "w", encoding="utf-8") as f:
            f.write(v14_devirt.finish_text(text))
        print(f"[+] Output written to {dpath} ({len(text)} bytes)")

    except Exception as e:
        import traceback
        print(f"[!] Lift error: {e}")
        traceback.print_exc()
else:
    print("[!] No PROTOS found in trace!")
