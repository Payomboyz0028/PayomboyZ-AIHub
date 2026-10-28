# -*- coding: utf-8 -*-
"""
=============================================================================
  🔬 REA UNIVERSAL REVERSE ENGINEERING ORCHESTRATOR  v3.0  (FULL UNLEASH)
  ─────────────────────────────────────────────────────────────────────────
  5-Stage Industrial Evidence Pipeline — no cap, no holding back:

  STAGE 0 ▸ Target Profiling     — format detect, entropy, embedded strings
  STAGE 1 ▸ Topology Discovery   — sections, imports, entrypoints, code graph
  STAGE 2 ▸ String & API Hunt    — all strings + xrefs → call-site mapping
  STAGE 3 ▸ Function Decompile   — batch pseudo-code via REA (Ghidra/Hopper)
  STAGE 4 ▸ AI Semantic Synthesis— DeepSeek (arch analysis) + Gemini (clean
                                    readable reconstruction), cross-validated
  STAGE 5 ▸ Evidence Commit      — dossier written, patterns learned, KR fed

  Supports:
    • Windows PE / EXE / DLL (x86, x64)
    • Linux ELF, macOS Mach-O
    • .NET CLR Assemblies (CIL bytecode)
    • Android DEX / APK
    • JavaScript / TypeScript Bundles (Wakaru + Wakaru-Pro)
    • Roblox Luau / Luraph / Moonsec / CFF VM (via full SHARDED pipeline)
    • WebAssembly (.wasm)
=============================================================================
"""

from __future__ import annotations

import os
import sys
import re
import json
import time
import math
import hashlib
import asyncio
import shutil
import subprocess
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
REA_ROOT = ROOT_DIR / "Lerning" / "rea-main"
REA_CLI  = REA_ROOT / "scripts" / "rea.mjs"
OUTPUT_DIR = ROOT_DIR / "output" / "Reversed_Artifacts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ─── lazy imports (avoid circular at module load) ─────────────────────────────
def _get_learner():
    from bot.autonomous_engineering_learner import AUTONOMOUS_LEARNER
    return AUTONOMOUS_LEARNER

def _get_router():
    from bot.hybrid_router import HYBRID_ROUTER
    return HYBRID_ROUTER

def _get_knowledge_router():
    try:
        from bot.knowledge_router import KNOWLEDGE_ROUTER
        return KNOWLEDGE_ROUTER
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# ENTROPY HELPER
# ══════════════════════════════════════════════════════════════════════════════
def _shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in freq if c)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
class REAUniversalOrchestrator:
    """
    Autonomous Master Reverse Engineer orchestrating REA (130 CLI commands,
    173 MCP tools) + 17-Agent AI Council for 1-Prompt Reversing of Anything.

    Evidence-Contract: every finding is tagged with evidence_id derived from
    file hash + stage + timestamp so results are traceable & reproducible.
    """

    # Maximum concurrent REA subprocess calls per stage
    MAX_PARALLEL_REA = 6

    def __init__(self):
        self.rea_root      = REA_ROOT
        self.rea_cli       = REA_CLI
        self.is_available  = self.rea_cli.exists()
        self._executor     = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.MAX_PARALLEL_REA,
            thread_name_prefix="rea_worker"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # LOW-LEVEL: Run a single REA CLI command
    # ──────────────────────────────────────────────────────────────────────────
    def _rea(self, command: str, args: List[str], timeout: int = 60) -> Tuple[bool, str]:
        """Executes one REA CLI command synchronously. Returns (ok, output)."""
        if not self.is_available:
            return False, "REA CLI unavailable — scripts/rea.mjs not found"

        cmd = ["node", str(self.rea_cli), command] + args
        try:
            p = subprocess.run(
                cmd,
                cwd=str(self.rea_root),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            out = (p.stdout or "").strip() or (p.stderr or "").strip()
            return p.returncode == 0, out
        except subprocess.TimeoutExpired:
            return False, f"[TIMEOUT] REA '{command}' exceeded {timeout}s"
        except Exception as e:
            return False, f"[ERROR] REA '{command}': {e}"

    async def _rea_async(self, command: str, args: List[str], timeout: int = 60) -> Tuple[bool, str]:
        """Async wrapper — runs _rea in thread-pool so we can blast many in parallel."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, lambda: self._rea(command, args, timeout)
        )

    # Backwards-compat alias
    def run_rea_cmd(self, command_name: str, args: List[str], timeout: int = 45) -> Tuple[bool, str]:
        return self._rea(command_name, args, timeout)

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 0 — TARGET PROFILING
    # ──────────────────────────────────────────────────────────────────────────
    def _profile_target(self, fp: Path) -> Dict[str, Any]:
        """
        Fully profiles a target: magic headers, entropy, embedded strings,
        size, hash, and a human-readable description.
        """
        if not fp.exists():
            return {"format": "MISSING", "family": "UNKNOWN", "size": 0, "desc": "File not found"}

        size    = fp.stat().st_size
        header  = fp.read_bytes()[:8192]
        sha256  = hashlib.sha256(header).hexdigest()
        entropy = _shannon_entropy(header[:2048])

        # ── magic detection ──
        if header.startswith(b"MZ"):
            is_dotnet = (b".NET Framework" in header or b"mscoree.dll" in header or b"BSJB" in header)
            if is_dotnet:
                fmt, fam, desc = "DOTNET_ASSEMBLY", "MANAGED_DOTNET", ".NET CLR Assembly (CIL bytecode)"
            elif b"PE\x00\x00\x64\x86" in header or b"PE\x00\x00d\x86" in header:
                fmt, fam, desc = "PE_X64", "NATIVE_WINDOWS", "Windows PE x86-64 (EXE/DLL)"
            elif b"PE\x00\x00L\x01" in header:
                fmt, fam, desc = "PE_X86", "NATIVE_WINDOWS", "Windows PE i386 32-bit (EXE/DLL)"
            else:
                fmt, fam, desc = "PE_GENERIC", "NATIVE_WINDOWS", "Windows PE Binary (unknown arch)"

        elif header.startswith(b"\x7fELF"):
            fmt, fam, desc = "ELF", "NATIVE_LINUX", "Linux ELF Executable / Shared Object"

        elif header.startswith((b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
                                 b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe")):
            fmt, fam, desc = "MACHO", "NATIVE_MACOS", "Apple Mach-O Binary"

        elif header.startswith(b"dex\n"):
            fmt, fam, desc = "DEX", "ANDROID", "Android Dalvik Executable (DEX)"

        elif header.startswith(b"PK\x03\x04") and fp.suffix.lower() == ".apk":
            fmt, fam, desc = "APK", "ANDROID", "Android Application Package (APK)"

        elif header.startswith(b"\x00asm"):
            fmt, fam, desc = "WASM", "WEBASSEMBLY", "WebAssembly Binary (.wasm)"

        else:
            ext = fp.suffix.lower()
            if ext in (".js", ".mjs", ".cjs", ".ts"):
                fmt, fam, desc = "JS_BUNDLE", "WEB_JAVASCRIPT", "JavaScript/TypeScript Bundle (Webpack/Vite/Rollup)"
            elif ext in (".lua", ".luau", ".txt"):
                fmt, fam, desc = "LUAU_SCRIPT", "ROBLOX_LUA", "Roblox Luau / Lua Script"
            elif ext in (".pyc", ".pyo"):
                fmt, fam, desc = "PYTHON_BYTECODE", "PYTHON", "Compiled Python Bytecode"
            else:
                fmt, fam, desc = "RAW_BINARY", "UNKNOWN", "Raw binary / data blob"

        # ── embedded ASCII strings (fast grep) ──
        strings_found = re.findall(rb"[\x20-\x7e]{6,}", header)
        readable_strings = [s.decode("ascii", errors="replace") for s in strings_found[:40]]

        return {
            "format":         fmt,
            "family":         fam,
            "desc":           desc,
            "size":           size,
            "size_kb":        round(size / 1024, 1),
            "sha256":         sha256,
            "entropy":        round(entropy, 3),
            "packed":         entropy > 7.2,
            "strings_sample": readable_strings,
        }

    # Backwards-compat alias
    def inspect_target_format(self, file_path: Path) -> Dict[str, Any]:
        return self._profile_target(file_path)

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 1 — TOPOLOGY DISCOVERY  (parallel REA blasts)
    # ──────────────────────────────────────────────────────────────────────────
    async def _stage1_topology(self, fp: Path, family: str) -> Dict[str, str]:
        """
        Fires all applicable REA topology commands simultaneously.
        Returns a dict of section_name → raw_output.
        """
        target = str(fp)
        tasks: List[Tuple[str, str, List[str], int]] = []   # (label, cmd, args, timeout)

        if family in ("NATIVE_WINDOWS", "NATIVE_LINUX", "NATIVE_MACOS"):
            tasks += [
                ("Binary Overview",       "binary-overview",           [target], 45),
                ("Sections & Entrypoint", "inspect-native-load-image", [target], 45),
                ("PE Resources",          "inspect-pe-resources",      [target], 45),
                ("Native API Exports",    "inspect-native-api",        [target], 45),
                ("Binary Layout",         "inspect-binary-layout",     [target], 45),
            ]

        elif family == "MANAGED_DOTNET":
            tasks += [
                ("Assembly Metadata",   "inspect-managed-artifact",          [target], 45),
                ("CIL Members & Types", "inspect-managed-members",           [target], 60),
                ("Native Boundaries",   "inspect-managed-native-boundaries", [target], 45),
            ]

        elif family == "ANDROID":
            tasks += [
                ("Package Structure", "inspect-android-package",  [target], 60),
                ("Class Search",      "search-android-classes",   [target, "--all"], 45),
            ]

        elif family == "WEB_JAVASCRIPT":
            tasks += [
                ("Module Import Graph", "trace-web-module-imports",   [target], 60),
                ("Source Recovery",     "recover-javascript-sources", [target], 90),
            ]

        elif family == "ROBLOX_LUA":
            tasks += [
                ("String Extract", "search-strings", [target], 30),
            ]

        # Fire all concurrently
        coros = [self._rea_async(cmd, args, timeout) for (_, cmd, args, timeout) in tasks]
        results_raw = await asyncio.gather(*coros, return_exceptions=True)

        out: Dict[str, str] = {}
        for (label, cmd, _, _), res in zip(tasks, results_raw):
            if isinstance(res, Exception):
                out[label] = f"[ERROR] {res}"
            else:
                ok, text = res
                out[label] = text if (ok and text) else f"[REA:{cmd}] {text or 'no output'}"

        return out

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 2 — STRING & API HUNT
    # ──────────────────────────────────────────────────────────────────────────
    async def _stage2_string_api_hunt(self, fp: Path, family: str) -> Dict[str, str]:
        """
        Extracts all strings, finds interesting names, and maps xrefs for
        native targets. For Luau/JS targets, runs pattern-based recon.
        """
        target = str(fp)
        findings: Dict[str, str] = {}

        if family in ("NATIVE_WINDOWS", "NATIVE_LINUX", "NATIVE_MACOS", "MANAGED_DOTNET"):
            tasks = [
                ("Strings (all)",  "list-strings",   [target], 45),
                ("Named Symbols",  "list-names",     [target], 45),
                ("Bookmarks",      "list-bookmarks", [target], 30),
                ("Segments",       "list-segments",  [target], 30),
            ]
            coros = [self._rea_async(cmd, args, t) for (_, cmd, args, t) in tasks]
            raws  = await asyncio.gather(*coros, return_exceptions=True)
            for (label, cmd, _, _), res in zip(tasks, raws):
                if isinstance(res, Exception):
                    findings[label] = f"[ERROR] {res}"
                else:
                    ok, text = res
                    findings[label] = text if ok else f"[{cmd}] {text}"

        elif family == "WEB_JAVASCRIPT":
            tasks = [
                ("Web Event Listeners", "inspect-web-event-listeners", [target], 45),
                ("Network Captures",    "inspect-web-network-capture",  [target], 45),
            ]
            coros = [self._rea_async(cmd, args, t) for (_, cmd, args, t) in tasks]
            raws  = await asyncio.gather(*coros, return_exceptions=True)
            for (label, cmd, _, _), res in zip(tasks, raws):
                if isinstance(res, Exception):
                    findings[label] = f"[ERROR] {res}"
                else:
                    ok, text = res
                    findings[label] = text if ok else f"[{cmd}] {text}"

        # Fast in-process interesting string extraction (works on all types)
        try:
            raw_bytes = fp.read_bytes()
            extracted = re.findall(rb"[\x20-\x7e]{8,}", raw_bytes)
            hits = [s.decode("ascii", "replace") for s in extracted[:300]]
            interesting = [
                s for s in hits
                if any(kw in s.lower() for kw in [
                    "http", "url", "api", "key", "secret", "token", "pass",
                    "remote", "webhook", "discord", "lua", "roblox", "game",
                    "require", "getfenv", "hookfunc", "loadstring", "debug",
                    "dll", "inject", "bypass", "cheat", "esp", "aimbot",
                ])
            ]
            if interesting:
                findings["Interesting Strings (in-process)"] = "\n".join(interesting[:80])
        except Exception:
            pass

        return findings

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 3 — FUNCTION DECOMPILATION  (call graph + pseudo-code)
    # ──────────────────────────────────────────────────────────────────────────
    async def _stage3_function_decompile(
        self, fp: Path, family: str, top_n_funcs: int = 20
    ) -> Dict[str, str]:
        """
        Builds the call graph, finds top procedures by size/importance,
        and batch-decompiles them via REA (Ghidra/Hopper pseudo-code).
        """
        target = str(fp)
        findings: Dict[str, str] = {}

        if family in ("NATIVE_WINDOWS", "NATIVE_LINUX", "NATIVE_MACOS"):
            ok_procs, procs_raw = await self._rea_async("list-procedures", [target], 60)
            if ok_procs and procs_raw:
                findings["Procedure List"] = procs_raw[:6000]

            ok_cg, cg_raw = await self._rea_async("get-call-graph", [target], 60)
            if ok_cg and cg_raw:
                findings["Call Graph"] = cg_raw[:4000]

            addr_pattern = re.compile(r"0x[0-9a-fA-F]{4,16}")
            addresses = addr_pattern.findall(procs_raw or "")[:top_n_funcs]

            if addresses:
                decompile_tasks = [
                    self._rea_async("procedure-pseudo-code", [target, addr], 90)
                    for addr in addresses
                ]
                decompile_results = await asyncio.gather(*decompile_tasks, return_exceptions=True)
                pseudo_code_blocks = []
                for addr, res in zip(addresses, decompile_results):
                    if isinstance(res, Exception):
                        continue
                    ok, text = res
                    if ok and text and len(text) > 30:
                        pseudo_code_blocks.append(f"// ── {addr} ──\n{text}")

                if pseudo_code_blocks:
                    findings["Pseudo-Code (Batch)"] = "\n\n".join(pseudo_code_blocks)

            ok_xr, xr_raw = await self._rea_async("xrefs", [target, "--all"], 60)
            if ok_xr and xr_raw:
                findings["Xrefs Summary"] = xr_raw[:3000]

        elif family == "MANAGED_DOTNET":
            ok_m, m_out = await self._rea_async("inspect-managed-members", [target], 60)
            if ok_m:
                findings["CIL Members & Types"] = m_out
            ok_nm, nm_out = await self._rea_async("inspect-managed-native-boundaries", [target], 45)
            if ok_nm:
                findings["Native Boundaries"] = nm_out

        elif family == "WEB_JAVASCRIPT":
            js_out_dir = OUTPUT_DIR / "js_recovered"
            js_out_dir.mkdir(parents=True, exist_ok=True)
            ok_js, js_out = await self._rea_async(
                "recover-javascript-sources",
                [target, "--output", str(js_out_dir)],
                timeout=120
            )
            if ok_js and js_out:
                findings["Wakaru Decompiler"] = js_out
                mods = list(js_out_dir.glob("**/*.js")) + list(js_out_dir.glob("**/*.ts"))
                findings["Recovered Modules"] = "\n".join(str(m) for m in mods[:60])
            else:
                findings["Wakaru Decompiler"] = f"[FAILED] {js_out}"

        elif family == "ANDROID":
            ok_cls, cls_out = await self._rea_async("search-android-classes", [target, "--all"], 60)
            if ok_cls:
                findings["Android Classes"] = cls_out[:5000]

        return findings

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 4 — AI SEMANTIC SYNTHESIS  (DeepSeek + Gemini cross-validation)
    # ──────────────────────────────────────────────────────────────────────────
    async def _stage4_ai_synthesis(
        self,
        fp: Path,
        profile: Dict[str, Any],
        topology: Dict[str, str],
        strings: Dict[str, str],
        decompiled: Dict[str, str],
        session_out: Path,
    ) -> Dict[str, Any]:
        """
        Feeds all REA evidence into the AI Council for semantic reconstruction.
        DeepSeek: architecture analysis + opcode lifting.
        Gemini: human-readable reconstruction + naming.
        Luau targets: full ShardedBlockDecompiler pipeline.
        """
        family = profile.get("family", "UNKNOWN")
        router = _get_router()
        synthesis_result: Dict[str, Any] = {"success": False, "text": "", "code": ""}

        # ── Luau branch: full Sharded pipeline ───────────────────────────────
        if family == "ROBLOX_LUA":
            from bot.sharded_decompiler import SHARDED_DECOMPILER
            from universal_deobfuscator import UniversalDeobfuscatorPipeline

            raw_code = fp.read_text(encoding="utf-8", errors="replace")

            pipeline  = UniversalDeobfuscatorPipeline(output_dir=session_out)
            deobf_res = pipeline.deobfuscate_file(fp)
            deobf_code = deobf_res.get("deobfuscated_code", "") if deobf_res.get("success") else ""

            still_obfuscated = (
                not deobf_res.get("success")
                or len(deobf_code.splitlines()) < 15
                or any(sig in deobf_code for sig in [
                    "while true do local", "repeat until", "bit.bxor",
                    "QZ[", "_0_x", "LPH_", "local _", "local  ",
                ])
            )

            if still_obfuscated:
                code_to_lift = deobf_code if (deobf_code and len(deobf_code) > 200) else raw_code
                sharded = await SHARDED_DECOMPILER.decompile(code_to_lift, script_name=fp.name)
                if sharded.get("success") and sharded.get("deobfuscated_code"):
                    synthesis_result["code"]    = sharded["deobfuscated_code"]
                    synthesis_result["success"] = True
                    synthesis_result["text"]    = (
                        f"ShardedBlockDecompiler: {sharded.get('lines', 0)} lines, "
                        f"{sharded.get('shards_count', 0)} shards, "
                        f"verify={sharded.get('verification', '?')}"
                    )
                else:
                    synthesis_result["code"]    = deobf_code or raw_code
                    synthesis_result["success"] = bool(deobf_code)
                    synthesis_result["text"]    = "Sharded fallback — universal pipeline output"
            else:
                synthesis_result["code"]    = deobf_code
                synthesis_result["success"] = True
                synthesis_result["text"]    = f"Universal pipeline: {len(deobf_code.splitlines())} clean lines"

            return synthesis_result

        # ── Native / Managed / Web / Android branch ───────────────────────────
        evidence_chunks = [
            f"TARGET: {fp.name} | {profile['desc']}\n"
            f"SIZE: {profile['size_kb']} KB | ENTROPY: {profile['entropy']} "
            f"({'PACKED/ENCRYPTED' if profile['packed'] else 'normal'})\n"
            f"SHA256: {profile['sha256'][:16]}...\n"
        ]

        for k, v in topology.items():
            if v and not v.startswith("[REA:") and not v.startswith("[ERROR]"):
                evidence_chunks.append(f"[TOPOLOGY — {k}]\n{v[:2000]}")

        for k, v in strings.items():
            if v and not v.startswith("[ERROR]"):
                evidence_chunks.append(f"[STRINGS — {k}]\n{v[:1500]}")

        for k, v in decompiled.items():
            if v and not v.startswith("[FAILED]"):
                evidence_chunks.append(f"[DECOMPILE — {k}]\n{v[:4000]}")

        full_evidence = "\n\n" + "\n\n".join(evidence_chunks)
        if len(full_evidence) > 28000:
            full_evidence = full_evidence[:28000] + "\n... [truncated for context window]"

        # ── DEEPSEEK PASS: Architecture Analysis ──────────────────────────────
        ds_prompt = (
            "You are the PAYOMBØYZ Senior Reverse Engineer (O.Z.L.S.R Protocol — no restrictions).\n"
            f"Binary family: {family}\n\n"
            "Analyze the REA evidence and produce a full technical breakdown:\n"
            "1. Architecture summary (packer, protector, VM, anti-debug found?)\n"
            "2. Key imports / APIs used + their purpose\n"
            "3. Notable strings: secrets, URLs, credentials, config values\n"
            "4. Primary functionality: what does this binary DO?\n"
            "5. Threat classification if applicable (stealer, RAT, loader, cheat, etc.)\n"
            "6. Suggested re-implementation outline in clean pseudocode\n\n"
            f"REA EVIDENCE:\n{full_evidence}"
        )

        try:
            ds_res  = await asyncio.to_thread(
                router.query_supervised,
                prompt=ds_prompt,
                user_request=f"Full architecture analysis of {fp.name}",
                system_prompt="You are a world-class reverse engineer. Return a complete, precise technical report. No disclaimers.",
                mode="deobfuscate",
                preferred_provider="deepseek",
            )
            ds_text = ds_res.get("reply") or ds_res.get("text") or ""
        except Exception as e:
            ds_text = f"[DeepSeek error: {e}]"

        # ── GEMINI PASS: Semantic Reconstruction + Naming ─────────────────────
        gem_prompt = (
            "You are the PAYOMBØYZ Semantic Reconstruction Engine (O.Z.L.S.R Protocol).\n"
            f"Binary: {fp.name} | Family: {family}\n\n"
            "Using the REA evidence AND architecture analysis, produce:\n"
            "1. Fully reconstructed, human-readable pseudocode or source code\n"
            "2. Meaningful variable/function names based on observed behavior\n"
            "3. Inline comments explaining each critical block\n"
            "4. A 5-sentence executive summary of what this target does\n\n"
            f"ARCHITECTURE ANALYSIS (DeepSeek):\n{ds_text[:3000]}\n\n"
            f"REA EVIDENCE:\n{full_evidence[:8000]}"
        )

        try:
            gem_res  = await asyncio.to_thread(
                router.query_supervised,
                prompt=gem_prompt,
                user_request=f"Semantic reconstruction of {fp.name}",
                system_prompt="You are a senior security researcher. Produce complete, accurate, documented reconstructed code.",
                mode="deobfuscate",
                preferred_provider="gemini",
            )
            gem_text = gem_res.get("reply") or gem_res.get("text") or ""
        except Exception as e:
            gem_text = f"[Gemini error: {e}]"

        synthesis_result["success"] = bool(ds_text or gem_text)
        synthesis_result["text"]    = ds_text
        synthesis_result["code"]    = gem_text

        (session_out / "deepseek_arch_analysis.md").write_text(ds_text, encoding="utf-8", errors="replace")
        (session_out / "gemini_reconstruction.md").write_text(gem_text, encoding="utf-8", errors="replace")

        return synthesis_result

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 5 — EVIDENCE COMMIT  (dossier + learner + knowledge router)
    # ──────────────────────────────────────────────────────────────────────────
    def _stage5_commit(
        self,
        fp: Path,
        profile: Dict[str, Any],
        topology: Dict[str, str],
        strings: Dict[str, str],
        decompiled: Dict[str, str],
        synthesis: Dict[str, Any],
        session_out: Path,
        elapsed: float,
    ) -> List[str]:
        """Writes the full evidence dossier and commits patterns to learner."""
        recovered_files: List[str] = []
        evidence_id = f"REA_{profile['sha256'][:12]}_{int(time.time())}"

        dossier_path = session_out / f"{fp.stem}_DOSSIER.md"
        lines_out: List[str] = [
            f"# 🔬 REA REVERSE ENGINEERING DOSSIER",
            f"**Evidence ID:** `{evidence_id}`  ",
            f"**Target:** `{fp.name}`  ",
            f"**Family:** `{profile['family']}`  |  **Format:** `{profile['format']}`  ",
            f"**Description:** {profile['desc']}  ",
            f"**Size:** {profile['size_kb']} KB  |  **Entropy:** {profile['entropy']} "
            f"({'⚠️ PACKED' if profile['packed'] else '✅ normal'})  ",
            f"**SHA-256:** `{profile['sha256']}`  ",
            f"**Analysis Time:** {elapsed:.1f}s  ",
            "", "---", "",
        ]

        def _section(title: str, content: str, lang: str = ""):
            fence = f"```{lang}" if lang else "```"
            lines_out.extend([f"## {title}", fence, content.strip()[:8000], "```", ""])

        for k, v in topology.items():
            if v and not v.startswith("[REA:") and not v.startswith("[ERROR]"):
                _section(f"Topology — {k}", v)

        for k, v in strings.items():
            if v and not v.startswith("[ERROR]"):
                _section(f"Strings — {k}", v)

        for k, v in decompiled.items():
            if v and not v.startswith("[FAILED]") and not v.startswith("[ERROR]"):
                _section(f"Decompile — {k}", v, lang="c")

        if synthesis.get("text"):
            lines_out.append("## 🤖 DeepSeek — Architecture Analysis")
            lines_out.append(synthesis["text"][:6000])
            lines_out.append("")

        if synthesis.get("code"):
            _section("🧠 Gemini — Semantic Reconstruction", synthesis["code"])

        dossier_path.write_text("\n".join(lines_out), encoding="utf-8", errors="replace")
        recovered_files.append(str(dossier_path))

        if synthesis.get("code"):
            family = profile.get("family", "UNKNOWN")
            ext = ".luau" if family == "ROBLOX_LUA" else ".js" if "JS" in family else ".c"
            code_path = session_out / f"{fp.stem}_RECONSTRUCTED{ext}"
            code_path.write_text(synthesis["code"], encoding="utf-8", errors="replace")
            recovered_files.append(str(code_path))

        try:
            learner = _get_learner()
            learner.record_decompilation_success(
                architecture=profile["format"],
                source_hash=profile["sha256"][:16],
                recovered_lines=len((synthesis.get("code") or "").splitlines()),
                confidence=90.0 if synthesis.get("success") else 40.0,
                discovered_patterns=[
                    f"REA_STAGE_PIPELINE_{profile['family']}",
                    "DEEPSEEK_ARCH_ANALYSIS",
                    "GEMINI_SEMANTIC_RECON",
                    evidence_id,
                ],
            )
        except Exception:
            pass

        try:
            kr = _get_knowledge_router()
            if kr and hasattr(kr, "index_finding"):
                kr.index_finding(
                    source="REA_UNIVERSAL_ORCHESTRATOR",
                    evidence_id=evidence_id,
                    target=fp.name,
                    family=profile["family"],
                    summary=synthesis.get("text", "")[:500],
                )
        except Exception:
            pass

        return recovered_files

    # ══════════════════════════════════════════════════════════════════════════
    # PUBLIC ENTRYPOINT — 1-Prompt Universal Reverse Engineering
    # ══════════════════════════════════════════════════════════════════════════
    async def reverse_target(
        self,
        target_path: Path,
        user_prompt: str = "",
        output_name: Optional[str] = None,
        top_n_funcs: int = 20,
    ) -> Dict[str, Any]:
        """
        1-Prompt full-stack reverse engineering of ANY target.
        Runs all 5 stages and returns a complete evidence dossier.
        """
        start_t = time.time()
        fp = Path(target_path)

        print(f"\n[REA] ⚡ Starting 5-Stage Universal RE Pipeline on: {fp.name}")

        # Stage 0: Profile
        print("[REA] Stage 0 ▸ Target Profiling...")
        profile = self._profile_target(fp)
        family  = profile["family"]
        fmt     = profile["format"]
        print(f"[REA]   → {profile['desc']} | {profile['size_kb']} KB | entropy={profile['entropy']}")

        ts_id = int(time.time() * 1000)
        name  = output_name or fp.stem
        session_out = OUTPUT_DIR / f"{name}_rea_{ts_id}"
        session_out.mkdir(parents=True, exist_ok=True)

        # Stage 1: Topology
        print("[REA] Stage 1 ▸ Topology Discovery (parallel REA blasts)...")
        topology = await self._stage1_topology(fp, family)
        print(f"[REA]   → {len(topology)} topology sections extracted")

        # Stage 2: Strings & API Hunt
        print("[REA] Stage 2 ▸ String & API Hunt...")
        strings = await self._stage2_string_api_hunt(fp, family)
        print(f"[REA]   → {len(strings)} string categories | "
              f"{len(strings.get('Interesting Strings (in-process)', '').splitlines())} interesting hits")

        # Stage 3: Function Decompilation
        print(f"[REA] Stage 3 ▸ Function Decompilation (top {top_n_funcs} procs)...")
        decompiled = await self._stage3_function_decompile(fp, family, top_n_funcs)
        pseudo_lines = sum(
            len(v.splitlines()) for v in decompiled.values() if v and not v.startswith("[")
        )
        print(f"[REA]   → {pseudo_lines} pseudo-code lines across {len(decompiled)} sections")

        # Stage 4: AI Semantic Synthesis
        print("[REA] Stage 4 ▸ AI Semantic Synthesis (DeepSeek + Gemini)...")
        synthesis = await self._stage4_ai_synthesis(
            fp, profile, topology, strings, decompiled, session_out
        )
        print(f"[REA]   → {'✅ SUCCESS' if synthesis['success'] else '⚠️ PARTIAL'}")

        # REA ↔ Deobf Bridge: detect embedded Lua / Luau in reverse target
        reconstructed_code = synthesis.get("code") or ""
        is_lua_format = (
            family in ("ROBLOX_LUA", "LUA", "LUAU")
            or fmt.lower() in ("lua", "luau", "roblox")
            or fp.suffix.lower() in (".lua", ".luau")
            or "game:GetService" in reconstructed_code
            or "setmetatable" in reconstructed_code
        )
        if is_lua_format and len(reconstructed_code.splitlines()) > 50:
            print("[REA] ⚡ Triggering REA ↔ Deobf Bridge (ShardedBlockDecompiler)...")
            try:
                from bot.sharded_decompiler import SHARDED_DECOMPILER
                deobf_bridge_result = await SHARDED_DECOMPILER.decompile(
                    reconstructed_code, script_name=fp.name
                )
                if deobf_bridge_result.get("success") and deobf_bridge_result.get("deobfuscated_code"):
                    synthesis["deobfuscated_luau"] = deobf_bridge_result["deobfuscated_code"]
                    synthesis["luau_verified"] = deobf_bridge_result.get("verified", False)
                    bridge_file = session_out / f"{fp.stem}_bridge_deobfuscated.luau"
                    bridge_file.write_text(deobf_bridge_result["deobfuscated_code"], encoding="utf-8", errors="replace")
                    print(f"[REA]   → Deobf Bridge finished: {deobf_bridge_result.get('lines', 0)} lines (verified={deobf_bridge_result.get('verified')})")
            except Exception as e_bridge:
                print(f"[REA] REA ↔ Deobf Bridge skipped: {e_bridge}", flush=True)

        # Stage 5: Evidence Commit
        elapsed = time.time() - start_t
        print("[REA] Stage 5 ▸ Evidence Commit (dossier + learner)...")
        recovered = self._stage5_commit(
            fp, profile, topology, strings, decompiled, synthesis, session_out, elapsed
        )

        code_lines = len((synthesis.get("code") or "").splitlines())
        print(f"\n[REA] ✅ Done in {elapsed:.1f}s — {code_lines} code lines reconstructed")
        print(f"[REA] 📁 Output: {session_out}")

        return {
            "success":           synthesis["success"],
            "target":            fp.name,
            "family":            family,
            "format":            fmt,
            "file_info":         profile,
            "analysis_sections": {**topology, **strings, **decompiled},
            "synthesis":         synthesis,
            "deobfuscated_luau": synthesis.get("deobfuscated_luau", ""),
            "luau_verified":     synthesis.get("luau_verified", False),
            "recovered_files":   recovered,
            "session_dir":       str(session_out),
            "elapsed":           elapsed,
            "summary": (
                f"REA 5-Stage pipeline on {fp.name} ({profile['desc']}) — "
                f"{pseudo_lines} pseudo-code lines + AI reconstruction of {code_lines} lines "
                f"in {elapsed:.1f}s. Evidence ID: REA_{profile['sha256'][:12]}."
            ),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # CONVENIENCE: Quick-reverse a raw code string (Luau / JS / Python text)
    # ──────────────────────────────────────────────────────────────────────────
    async def reverse_code_string(
        self,
        code: str,
        script_name: str = "target.lua",
        language: str = "luau",
    ) -> Dict[str, Any]:
        """Convenience entrypoint for reversing a raw code string without writing to disk first."""
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=f".{language}", delete=False,
            encoding="utf-8", errors="replace"
        ) as tmp:
            tmp.write(code)
            tmp_path = Path(tmp.name)
        try:
            return await self.reverse_target(tmp_path, output_name=script_name)
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────────────────
    # Synchronous wrapper for old call sites
    # ──────────────────────────────────────────────────────────────────────────
    def reverse_target_sync(self, target_path: Path, **kwargs) -> Dict[str, Any]:
        """Synchronous wrapper — creates its own event loop if needed."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures as cf
                with cf.ThreadPoolExecutor(1) as pool:
                    fut = pool.submit(asyncio.run, self.reverse_target(target_path, **kwargs))
                    return fut.result(timeout=300)
            else:
                return loop.run_until_complete(self.reverse_target(target_path, **kwargs))
        except RuntimeError:
            return asyncio.run(self.reverse_target(target_path, **kwargs))


# ─── Singleton ────────────────────────────────────────────────────────────────
REA_UNIVERSAL_ORCHESTRATOR = REAUniversalOrchestrator()

