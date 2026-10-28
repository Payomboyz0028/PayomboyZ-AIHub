import os
import sys
import glob
import json
import time
import subprocess
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


DEOB_DIR = r"d:\Deobfuscate\Lerning\Luraph\New\v15_tool_attempt_source"
LUAU_BIN = os.path.join(DEOB_DIR, "bin", "luau.exe")
OUTPUT_DIR = r"d:\Deobfuscate\benchmark_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define known benchmark pairs (obfuscated target -> original source)
PAIRS = [
    # Golden Luraph v15.1 samples
    {
        "name": "v15.1_Golden_2153b",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\New\v15_tool_attempt_source\samples_v15.1_deobfuscated\2153b779fa7a87f2_obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\New\v15_tool_attempt_source\samples_v15.1_deobfuscated\2153b779fa7a87f2_deobfuscated.luau",
        "version": "v15.1"
    },
    {
        "name": "v15.1_Golden_390ea",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\New\v15_tool_attempt_source\samples_v15.1_deobfuscated\390ea6acb88b8f9f_obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\New\v15_tool_attempt_source\samples_v15.1_deobfuscated\390ea6acb88b8f9f_deobfuscated.luau",
        "version": "v15.1"
    },
    {
        "name": "v15.1_Golden_cf96f",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\New\v15_tool_attempt_source\samples_v15.1_deobfuscated\cf96f658de290478_obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\New\v15_tool_attempt_source\samples_v15.1_deobfuscated\cf96f658de290478_deobfuscated.luau",
        "version": "v15.1"
    },
    {
        "name": "v15.1_Golden_e20f3",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\New\v15_tool_attempt_source\samples_v15.1_deobfuscated\e20f3887d419069f_obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\New\v15_tool_attempt_source\samples_v15.1_deobfuscated\e20f3887d419069f_deobfuscated.luau",
        "version": "v15.1"
    },
    # Production Payomboyz Targets
    {
        "name": "Key_Engine_v14",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Key-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Key.txt",
        "version": "v14.9"
    },
    {
        "name": "CapybaraVsPlant_v15",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\CapybaraVsPlant-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\CapybaraVsPlant.txt",
        "version": "v15.0"
    },
    {
        "name": "Master_Mystery_2_v15",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Master Mystery 2-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Master Mystery 2.txt",
        "version": "v15.0"
    },
    {
        "name": "Iron_Soul_Tower_v14",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Iron Soul Tower-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Iron Soul Tower.txt",
        "version": "v14.9"
    },
    {
        "name": "Iron_Soul_Boss_v15",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Iron Soul Boss-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Iron Soul Boss.txt",
        "version": "v15.0"
    },
    {
        "name": "DungeonLootr_v15",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\DungeonLootr-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\DungeonLootr.txt",
        "version": "v15.0"
    },
    {
        "name": "Aneme_Expredition_v14",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Aneme Expredition-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Aneme Expredition.txt",
        "version": "v14.9"
    },
    {
        "name": "Ride_a_pet_v15",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Ride a pet-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Ride a pet.txt",
        "version": "v15.0"
    },
    {
        "name": "FISCH_v15",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\FISCH-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\FISCH.txt",
        "version": "v15.0"
    },
    {
        "name": "Roll_a_Gnome_v15",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Roll a Gnome-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Roll a Gnome.txt",
        "version": "v15.0"
    },
    {
        "name": "99Night_v15",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\99Night-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\99Night.txt",
        "version": "v15.0"
    },
    {
        "name": "Grow_Chicken_Fighter_v15",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Grow a Chicken Fighter-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Grow a Chicken Fighter.txt",
        "version": "v15.0"
    },
    {
        "name": "Greedy_Grower_v15",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Greedy Grower-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Greedy Grower.txt",
        "version": "v15.0"
    },
    {
        "name": "Iron_Soul_Dungeon_v15",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Iron Soul-Dungeon-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Iron Soul-Dungeon.txt",
        "version": "v15.0"
    },
    {
        "name": "Gakurun_v14",
        "obf": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Gakurun-obfuscated.lua",
        "orig": r"d:\Deobfuscate\Lerning\Luraph\PAY-MB-YZ-HUB-main\Gakurun.txt",
        "version": "v14.9"
    },
]

def extract_strings(text):
    """Extract strings >= 3 chars from source."""
    return set(re.findall(r'["\']([^"\']{3,})["\']', text))

def extract_identifiers(text):
    """Extract identifiers from source."""
    return set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{3,})\b', text))

def validate_syntax(path):
    """Validate luau syntax with luau.exe -c."""
    if not os.path.exists(LUAU_BIN) or not os.path.exists(path):
        return False, "File or binary not found"
    r = subprocess.run([LUAU_BIN, "-c", path], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()

def run_benchmark():
    print("=" * 80)
    print("  🔥 PAYOMBØYZ LURAPH DEOBFUSCATION COMPREHENSIVE BENCHMARK SUITE")
    print("=" * 80)
    
    summary = []
    
    for item in PAIRS:
        name = item["name"]
        obf_path = item["obf"]
        orig_path = item["orig"]
        version = item["version"]
        
        print(f"\n[*] Target: {name} ({version})")
        print(f"    Obfuscated: {obf_path}")
        if not os.path.exists(obf_path):
            print("    [!] Obfuscated file not found, skipping.")
            continue
            
        out_path = os.path.join(OUTPUT_DIR, f"{name}.deobf.luau")
        t0 = time.time()
        
        cmd = ["node", "deob.js", obf_path, "-o", out_path, "--timeout", "120"]
        r = subprocess.run(cmd, cwd=DEOB_DIR, capture_output=True, text=True)
        elapsed = time.time() - t0
        
        success = os.path.exists(out_path) and os.path.getsize(out_path) > 100
        out_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        
        syntax_ok = False
        syntax_err = ""
        similarity = 0.0
        
        if success:
            syntax_ok, syntax_err = validate_syntax(out_path)
            with open(out_path, "r", encoding="utf-8", errors="replace") as fh:
                deob_text = fh.read()
            out_lines = len(deob_text.splitlines())
            
            # Compare with original if exists
            if os.path.exists(orig_path):
                with open(orig_path, "r", encoding="latin-1") as fh:
                    orig_text = fh.read()
                orig_lines = len(orig_text.splitlines())
                
                orig_strings = extract_strings(orig_text)
                deob_strings = extract_strings(deob_text)
                str_match = len(orig_strings & deob_strings)
                str_total = len(orig_strings) if orig_strings else 1
                
                orig_idents = extract_identifiers(orig_text)
                deob_idents = extract_identifiers(deob_text)
                ident_match = len(orig_idents & deob_idents)
                ident_total = len(orig_idents) if orig_idents else 1
                
                similarity = (str_match / str_total * 0.6 + ident_match / ident_total * 0.4) * 100
                print(f"    [+] Recovered: {out_lines} lines in {elapsed:.1f}s | String Match: {str_match}/{str_total} ({str_match/str_total*100:.1f}%) | Similarity: {similarity:.1f}%")
            else:
                orig_lines = 0
                print(f"    [+] Recovered: {out_lines} lines in {elapsed:.1f}s (No original file for comparison)")
        else:
            out_lines = 0
            orig_lines = 0
            print(f"    [-] Failed in {elapsed:.1f}s: {r.stderr[:200]}")
            
        summary.append({
            "name": name,
            "version": version,
            "success": success,
            "elapsed": round(elapsed, 1),
            "out_lines": out_lines,
            "orig_lines": orig_lines,
            "syntax_ok": syntax_ok,
            "similarity": round(similarity, 1)
        })
        
    print("\n" + "=" * 80)
    print("  📊 BENCHMARK SUMMARY REPORT")
    print("=" * 80)
    print(f"{'Target':<26} | {'Ver':<6} | {'Status':<7} | {'Time':<6} | {'Recov':<6} | {'Orig':<6} | {'Syntax':<6} | {'Fidelity':<8}")
    print("-" * 80)
    for s in summary:
        status = "PASS" if s["success"] else "FAIL"
        syn = "OK" if s["syntax_ok"] else "ERR"
        fid = f"{s['similarity']:.1f}%" if s['orig_lines'] > 0 else "N/A"
        print(f"{s['name']:<26} | {s['version']:<6} | {status:<7} | {s['elapsed']:>4.1f}s | {s['out_lines']:>6} | {s['orig_lines']:>6} | {syn:<6} | {fid:>8}")
    print("=" * 80)
    
    with open(r"d:\Deobfuscate\benchmark_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

if __name__ == "__main__":
    run_benchmark()
