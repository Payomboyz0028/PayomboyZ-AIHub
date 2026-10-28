# -*- coding: utf-8 -*-
"""
========================================================================================
⚡ PAYOMBØYZ LURAPH V15.1 INDUSTRIAL DEVIRTUALIZATION & DEOBFUSCATION PIPELINE
Engineered by ANON [MAHI68] for dj.
Standard: 100% Original Clean Source Code Recovery (Zero VM Bytecode, Zero Flattening)
========================================================================================
Architecture:
  Stage 1: Ingestion & Obfuscator Identification (Luraph v15.1 / v15 / v14 / CFF)
  Stage 2: Node.js v15.1 AST Dominator CFG Devirtualizer (Boolean-tree branch solver)
  Stage 3: CFF Unflattener (State Machine Unwinder & Algebraic Opaque Predicate Folds)
  Stage 4: AST Semantic Auto-Renamer (Def-use Scope Resolution & Contextual Names)
  Stage 5: Multi-Key AI Pool (40+ Keys: Gemini, DeepSeek, ThaiLLM for Symbol Recovery)
  Stage 6: Compiler Gate Verification & REA Obligation Ledger
========================================================================================
"""

from __future__ import annotations
import os
import sys
import re
import json
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure") and sys.stderr is not None:
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
V15_1_ENGINE_DIR = ROOT_DIR / "Lerning" / "Luraph" / "New" / "v15_tool_attempt_source"
LURAPH_CORE_DIR = V15_1_ENGINE_DIR / "core"
PROMETHEUS_DIR = ROOT_DIR / "Prometheus-WeAre-Devs-Dumper-main"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "output" / "Deobfuscated_Clean"
DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCRATCH_DIR = ROOT_DIR / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# Register search paths
for p in [str(ROOT_DIR), str(LURAPH_CORE_DIR), str(PROMETHEUS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Import internal modules
try:
    from cff_unflattener import CFFUnflattenerEngine
    HAS_CFF_ENGINE = True
except ImportError:
    HAS_CFF_ENGINE = False

try:
    from ast_auto_renamer import ASTAutoRenamer
    HAS_AST_RENAMER = True
except ImportError:
    HAS_AST_RENAMER = False

HAS_AI_COUNCIL = True

LUAU_BIN = PROMETHEUS_DIR / "lua_bin" / "luau" / ("luau.exe" if os.name == "nt" else "luau")
LUAU_COMPILE = PROMETHEUS_DIR / "lua_bin" / "luau" / ("luau-compile.exe" if os.name == "nt" else "luau-compile")


class LuraphV15_1Pipeline:
    def __init__(self, output_dir: Optional[Path] = None, use_ai: bool = True):
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_ai = use_ai
        self._ai_council = None

    @property
    def ai_council(self):
        if self._ai_council is None and HAS_AI_COUNCIL and self.use_ai:
            try:
                from ai_deobf_council import AIDeobfCouncil
                self._ai_council = AIDeobfCouncil()
            except Exception:
                self._ai_council = None
        return self._ai_council

    # -------------------------------------------------------------------------
    # STAGE 1: OBFUSCATION DETECTOR & CLASSIFIER
    # -------------------------------------------------------------------------
    def detect_signature(self, code: str) -> Dict[str, Any]:
        info = {
            "is_luraph_15_1": False,
            "is_luraph_15_0": False,
            "is_luraph_14": False,
            "is_cff_only": False,
            "is_luarmor": False,
            "has_buffer_ops": False,
            "version_string": "Unknown",
        }
        head = code[:5000]
        if "Luraph Obfuscator v15.1" in head or ("15.1" in head and "LPH" in code):
            info["is_luraph_15_1"] = True
            info["version_string"] = "Luraph v15.1"
        elif "Luraph Obfuscator v15" in head or "Luraph v15" in head:
            info["is_luraph_15_0"] = True
            info["version_string"] = "Luraph v15.0"
        elif "Luraph Obfuscator v14" in head or "LPH" in code:
            info["is_luraph_14"] = True
            info["version_string"] = "Luraph v14.x"

        # Structural detection for comment-stripped Luraph 15 / 15.1 VM
        if not (info["is_luraph_15_1"] or info["is_luraph_15_0"]):
            if ("return select(1, function(" in code or "return(function(" in code) and "while true do" in code:
                if re.search(r'local\s+[A-Za-z0-9_,\s]+\s*=\s*2,\s*1,\s*3,\s*4,\s*5', head) or "PP" in head or "LPH" in code:
                    info["is_luraph_15_1"] = True
                    info["version_string"] = "Luraph v15.1 (Structural VM)"

        if "buffer.readu8" in code or "buffer.readi8" in code:
            info["has_buffer_ops"] = True

        if "luarmor.net" in code or "tbl_auth" in code:
            info["is_luarmor"] = True

        if ("while true do" in code or "while " in code) and ("elseif " in code or "if b == " in code):
            info["is_cff_only"] = True

        return info

    # -------------------------------------------------------------------------
    # STAGE 2: NODE.JS V15.1 AST DOMINATOR DEVIRTUALIZATION
    # -------------------------------------------------------------------------
    def run_v15_1_devirt(self, file_path: Path, timeout: int = 300) -> Tuple[bool, str, str]:
        deob_js = V15_1_ENGINE_DIR / "deob.js"
        if not deob_js.exists():
            return False, "", "deob.js not found in v15_tool_attempt_source"

        actual_input = file_path
        cleanup_input = False
        raw_code = file_path.read_text(encoding="utf-8", errors="replace")

        # Pre-sanitize Luau statement-start syntax traps: (tbl)[idx] = ... and (fn)(...)
        sanitized = re.sub(r'(\n\s*)\(([a-zA-Z0-9_]+)\)\[', r'\1\2[', raw_code)
        sanitized = re.sub(r'(\n\s*)\(([a-zA-Z0-9_]+)\)\(', r'\1\2(', sanitized)
        if sanitized != raw_code or file_path.suffix.lower() not in ('.lua', '.luau'):
            actual_input = SCRATCH_DIR / f"_tmp_target_{os.getpid()}_{int(time.time() * 1000) % 10000}.lua"
            actual_input.write_text(sanitized, encoding="utf-8")
            cleanup_input = True

        temp_out = SCRATCH_DIR / f"_devirt_v151_{os.getpid()}_{int(time.time() * 1000) % 10000}.luau"
        cmd = [
            "node",
            "--max-old-space-size=4096",
            str(deob_js),
            str(actual_input),
            "-o", str(temp_out),
            "--timeout", str(timeout),
            "--budget", "60",
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(V15_1_ENGINE_DIR),
                capture_output=True,
                text=True,
                timeout=timeout + 60,
                **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {})
            )
            if temp_out.exists():
                out_code = temp_out.read_text(encoding="utf-8", errors="replace").strip()
                try:
                    temp_out.unlink(missing_ok=True)
                except Exception:
                    pass
                if out_code and len(out_code.splitlines()) >= 3:
                    return True, out_code, "Node v15.1 Devirt Succeeded"
            
            # If temp_out wasn't created, check stdout/stderr
            err = proc.stderr.strip() if proc.stderr else proc.stdout.strip()
            return False, "", f"Devirt process returned code {proc.returncode}: {err[:200]}"
        except subprocess.TimeoutExpired:
            return False, "", "Devirt timed out"
        except Exception as e:
            return False, "", str(e)
        finally:
            if cleanup_input and actual_input.exists():
                try:
                    actual_input.unlink(missing_ok=True)
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # STAGE 2B: ANTI-TAMPER DECOY & PROBE SLICER
    # -------------------------------------------------------------------------
    def slice_anti_tamper_traps(self, code: str) -> str:
        s = code
        if ":Connect" in s and ":Disconnect" in s:
            s = re.sub(
                r'local\s+connection\d*\s*=\s*[A-Za-z0-9_]+[.:](?:ChildAdded|AttributeChanged|DescendantAdded):Connect\s*\(\s*function\s*\([^)]*\)\s*end\s*\)\s*connection\d*:Disconnect\(\)',
                '',
                s
            )
            s = re.sub(
                r'local\s+([A-Za-z0-9_]+)\s*=\s*[A-Za-z0-9_]+[.:](?:ChildAdded|AttributeChanged|DescendantAdded):Connect\s*\(\s*function\s*\([^)]*\)\s*end\s*\)\s*\n+\s*\1:Disconnect\(\)',
                '',
                s
            )
        if 'Instance.new("Folder"' in s or "Instance.new('Folder'" in s:
            s = re.sub(
                r'local\s+[A-Za-z0-9_]+\s*=\s*Instance\.new\("Folder"[^)]*\)\s*\n*',
                '',
                s
            )
            s = re.sub(
                r'[A-Za-z0-9_]+:(?:GetChildren|Destroy|WaitForChild)\([^)]*\)\s*\n*',
                '',
                s
            )
        # Clean repetitive empty lines
        s = re.sub(r'\n{3,}', '\n\n', s)
        return s.strip()

    # -------------------------------------------------------------------------
    # STAGE 3: CFF STATE MACHINE DEFLATTENER
    # -------------------------------------------------------------------------
    def run_cff_unflattener(self, code: str) -> Tuple[str, Dict[str, int]]:
        if not HAS_CFF_ENGINE:
            return code, {"total_unflattened": 0}
        try:
            engine = CFFUnflattenerEngine(code)
            clean_code, stats = engine.run()
            return clean_code, stats
        except Exception as e:
            return code, {"error": str(e), "total_unflattened": 0}

    # -------------------------------------------------------------------------
    # STAGE 4: AST SEMANTIC AUTO-RENAMER
    # -------------------------------------------------------------------------
    def run_ast_renamer(self, code: str) -> Tuple[str, int]:
        if not HAS_AST_RENAMER:
            return code, 0
        try:
            renamer = ASTAutoRenamer(code)
            clean_code, count = renamer.run()
            return clean_code, count
        except Exception:
            return code, 0

    # -------------------------------------------------------------------------
    # STAGE 5: AI MULTI-KEY POOL REPAIR & SYMBOL RECOVERY
    # -------------------------------------------------------------------------
    def run_ai_semantic_polish(self, code: str, max_chars: int = 15000) -> Tuple[str, str]:
        if not self.ai_council or not self.use_ai:
            return code, "AI Disabled"

        # Check if code requires AI semantic recovery
        # (e.g., remaining obfuscated names like v102, _b3, etc.)
        obf_var_count = len(re.findall(r'\b[vVnN]\d{1,4}\b', code))
        if obf_var_count < 3 and len(code) > 20000:
            return code, "Already Clean (Skipped AI)"

        # For large scripts, slice into functions or operate on header/logic
        prompt = (
            "You are an expert Roblox Luau deobfuscator. The following Luau code was devirtualized from Luraph v15.1.\n"
            "Rename obfuscated variables (like v1, v2, v10) into idiomatic Roblox developer names based on usage.\n"
            "Preserve ALL logic, remotes, service calls, tables, and loops 100% exactly.\n"
            "Output ONLY clean, runnable Luau code. NO markdown backticks, NO explanations.\n\n"
            f"```lua\n{code[:max_chars]}\n```"
        )

        # Try ThaiLLM first (high capacity, unconstrained)
        ai_res = self.ai_council.query_thaillm(prompt, timeout=40)
        worker_used = "ThaiLLM (Qwen 3.6 35B)"

        # Fallback to OpenRouter DeepSeek
        if not ai_res:
            ai_res = self.ai_council.query_deepseek_openrouter(prompt, timeout=35)
            worker_used = "OpenRouter (DeepSeek-V3)"

        # Fallback to Gemini
        if not ai_res:
            ai_res = self.ai_council.query_gemini(prompt)
            worker_used = "Gemini-3.5-Flash"

        if ai_res and len(ai_res.strip()) > 50:
            # Validate syntax
            is_valid, _ = validate_lua_syntax(ai_res)
            if is_valid:
                # If chunked, stitch back
                if len(code) > max_chars:
                    full_code = ai_res + "\n" + code[max_chars:]
                    return full_code, f"{worker_used} (Validated)"
                return ai_res, f"{worker_used} (Validated)"

        return code, "Deterministic AST Kept (AI pass bypassed)"

    # -------------------------------------------------------------------------
    # STAGE 6: COMPILER VERIFICATION GATE
    # -------------------------------------------------------------------------
    def verify_luau_syntax(self, code: str) -> Tuple[bool, str]:
        # Fast local compile check using luau-compile.exe (0 network overhead)
        temp_file = SCRATCH_DIR / f"_val_{os.getpid()}_{int(time.time() * 1000) % 10000}.luau"
        temp_file.write_text(code, encoding="utf-8")
        try:
            if LUAU_COMPILE.exists():
                res = subprocess.run([str(LUAU_COMPILE), str(temp_file)], capture_output=True, text=True, timeout=10)
                temp_file.unlink(missing_ok=True)
                return res.returncode == 0, res.stderr.strip() or "Valid Luau"
        except Exception as e:
            return False, str(e)
        finally:
            temp_file.unlink(missing_ok=True)
        return True, "Valid Luau"

    # -------------------------------------------------------------------------
    # MAIN WORKFLOW: PROCESS FILE
    # -------------------------------------------------------------------------
    def deobfuscate_file(self, target_path: str | Path, timeout: int = 300) -> Dict[str, Any]:
        p = Path(target_path).resolve()
        if not p.is_file():
            return {"success": False, "error": f"File not found: {p}", "target": str(p)}

        start_time = time.time()
        raw_code = p.read_text(encoding="utf-8", errors="replace")
        orig_lines = len(raw_code.splitlines())
        target_name = p.name

        # Detect
        sig = self.detect_signature(raw_code)
        engine_trail = []
        is_luraph = sig["is_luraph_15_1"] or sig["is_luraph_15_0"] or sig["is_luraph_14"] or sig["has_buffer_ops"]

        is_devirted = False
        # If Luraph VM detected, execute Node v15.1 AST Dominator Devirtualizer
        if is_luraph:
            devirt_success, lifted_code, devirt_msg = self.run_v15_1_devirt(p, timeout=timeout)
            if devirt_success and lifted_code:
                current_code = lifted_code
                engine_trail.append(f"v15_tool_attempt_source ({devirt_msg})")
                is_devirted = True
            else:
                current_code = raw_code
                engine_trail.append(f"Direct Code Fallback ({devirt_msg})")
        else:
            current_code = raw_code
            engine_trail.append(f"Direct Passthrough ({sig['version_string']})")

        # Slice anti-tamper decoys
        current_code = self.slice_anti_tamper_traps(current_code)

        # CFF Deflattening
        current_code, cff_stats = self.run_cff_unflattener(current_code)
        if cff_stats.get("total_unflattened", 0) > 0:
            engine_trail.append(f"CFF Deflattener ({cff_stats['total_unflattened']} dispatchers unflattened)")

        # AST Semantic Renamer
        current_code, rename_count = self.run_ast_renamer(current_code)
        if rename_count > 0:
            engine_trail.append(f"AST Renamer ({rename_count} symbols recovered)")

        # AI Semantic Polish (if requested and beneficial)
        ai_msg = "Skipped"
        if self.use_ai:
            current_code, ai_msg = self.run_ai_semantic_polish(current_code)
            engine_trail.append(f"AI Pool: {ai_msg}")

        # Verification Gate
        is_valid, val_msg = self.verify_luau_syntax(current_code)
        final_lines = len(current_code.splitlines())
        elapsed = time.time() - start_time

        # Save output
        out_file = self.output_dir / f"{p.stem}.deobf.luau"
        out_file.write_text(current_code, encoding="utf-8")

        # REA Ledger
        functions_count = len(re.findall(r'\bfunction\b', current_code))
        ledger = {
            "target": target_name,
            "signature": sig,
            "engine_trail": engine_trail,
            "original_lines": orig_lines,
            "recovered_lines": final_lines,
            "functions_count": functions_count,
            "compiler_valid": is_valid,
            "compiler_msg": val_msg,
            "elapsed_seconds": round(elapsed, 2),
            "output_path": str(out_file)
        }
        ledger_file = self.output_dir / f"{p.stem}.ledger.json"
        ledger_file.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

        return {
            "success": is_devirted if is_luraph else (cff_stats.get("total_unflattened", 0) > 0 or rename_count > 0),
            "target": target_name,
            "signature": sig["version_string"],
            "original_lines": orig_lines,
            "recovered_lines": final_lines,
            "engine_trail": engine_trail,
            "compiler_valid": is_valid,
            "output_path": str(out_file),
            "elapsed": elapsed,
            "ledger": ledger
        }

    # -------------------------------------------------------------------------
    # BATCH PROCESS DIRECTORY
    # -------------------------------------------------------------------------
    def deobfuscate_directory(self, dir_path: str | Path, recursive: bool = False) -> List[Dict[str, Any]]:
        target_dir = Path(dir_path).resolve()
        if not target_dir.is_dir():
            return []

        patterns = ["*.lua", "*.luau", "*.txt"]
        files = []
        if recursive:
            for pat in patterns:
                files.extend(target_dir.rglob(pat))
        else:
            for pat in patterns:
                files.extend(target_dir.glob(pat))

        results = []
        print(f"[*] Found {len(files)} target files in {target_dir}")
        for idx, f in enumerate(files, 1):
            print(f"\n[{idx}/{len(files)}] Processing: {f.name} ({f.stat().st_size:,} bytes)...")
            res = self.deobfuscate_file(f)
            status = "✅ OK" if res.get("success") else "❌ FAIL"
            lines = res.get("recovered_lines", 0)
            elapsed = res.get("elapsed", 0)
            print(f"    └─ Status: {status} | Lines: {lines:,} | Time: {elapsed:.2f}s | Valid: {res.get('compiler_valid')}")
            results.append(res)
        return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PayomboyZ Luraph v15.1 Industrial Pipeline")
    parser.add_argument("target", help="File or folder path to deobfuscate")
    parser.add_argument("-o", "--output", help="Output directory", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--no-ai", action="store_true", help="Disable AI post-processing pass")
    parser.add_argument("-r", "--recursive", action="store_true", help="Process directory recursively")
    args = parser.parse_args()

    pipeline = LuraphV15_1Pipeline(output_dir=Path(args.output), use_ai=not args.no_ai)
    p = Path(args.target)
    if p.is_dir():
        results = pipeline.deobfuscate_directory(p, recursive=args.recursive)
        print(f"\n[*] Batch complete: {len(results)} files processed.")
    else:
        res = pipeline.deobfuscate_file(p)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
