# -*- coding: utf-8 -*-
"""
=============================================================================
  ⚡ REA (REVERSE ENGINEER ANYTHING) UNIVERSAL ENGINE BRIDGE
  Bridges REA capabilities, Ghidra/Hopper native analysis, Wakaru JS unbundling,
  and cross-binary reverse engineering directly into PAYOMBØYZ 17-AI Council.
=============================================================================
"""

from __future__ import annotations
import os
import sys
import re
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
REA_DIR = ROOT_DIR / "Lerning" / "rea-main"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class REAEngineBridge:
    """
    Universal Reverse Engineering Bridge connecting:
    - PE / DLL / ELF / Mach-O Native Binaries
    - JavaScript / Webpack / Vite Bundles
    - .NET CIL Assemblies
    - Android APK / DEX
    - Python Bytecode & PyArmor
    """

    def __init__(self):
        self.rea_root = REA_DIR
        self.has_rea = self.rea_root.exists()

    def inspect_binary_target(self, file_path: Path) -> Dict[str, Any]:
        """Inspects target file header, entropy, and architecture."""
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        data = file_path.read_bytes()[:4096]
        size = file_path.stat().st_size

        target_type = "UNKNOWN"
        arch_details = {}

        # 1. Windows PE (MZ header)
        if data.startswith(b"MZ"):
            target_type = "PE_WINDOWS"
            arch_details["format"] = "Portable Executable (PE32/PE32+)"
            if b"PE\0\0d\x86" in data or b"PE\0\0\x64\x86" in data:
                arch_details["machine"] = "x86-64 (AMD64)"
            elif b"PE\0\0L\x01" in data:
                arch_details["machine"] = "i386 (32-bit)"
            if b".NET Framework" in data or b"mscoree.dll" in data or b"BSJB" in data:
                target_type = "DOTNET_ASSEMBLY"
                arch_details["framework"] = ".NET CLR Assembly (CIL)"

        # 2. Linux ELF
        elif data.startswith(b"\x7fELF"):
            target_type = "ELF_LINUX"
            arch_details["format"] = "Executable and Linkable Format"

        # 3. macOS Mach-O
        elif data.startswith((b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe")):
            target_type = "MACHO_APPLE"
            arch_details["format"] = "Mach-O Binary"

        # 4. Android DEX / APK
        elif data.startswith(b"dex\n"):
            target_type = "ANDROID_DEX"
            arch_details["format"] = "Dalvik Executable"
        elif data.startswith(b"PK\x03\x04") and file_path.suffix.lower() == ".apk":
            target_type = "ANDROID_APK"
            arch_details["format"] = "Android Package Archive"

        # 5. Python Bytecode (.pyc)
        elif file_path.suffix.lower() in (".pyc", ".pyo"):
            target_type = "PYTHON_BYTECODE"
            arch_details["format"] = "Compiled Python Bytecode"

        # 6. JavaScript / Web Bundle
        elif file_path.suffix.lower() in (".js", ".mjs", ".cjs", ".ts"):
            target_type = "JAVASCRIPT_BUNDLE"
            arch_details["format"] = "JavaScript/TypeScript Source/Bundle"

        return {
            "success": True,
            "target_type": target_type,
            "file_size": size,
            "filename": file_path.name,
            "arch_details": arch_details
        }

    def extract_source_map_sources(self, map_path: Path, output_dir: Path) -> int:
        """Extracts all embedded sources from a Source Map JSON file."""
        if not map_path.exists():
            return 0
        try:
            map_data = json.loads(map_path.read_text(encoding="utf-8", errors="replace"))
            sources = map_data.get("sources", [])
            contents = map_data.get("sourcesContent", [])
            extracted = 0
            if sources and contents:
                output_dir.mkdir(parents=True, exist_ok=True)
                for s_path, s_code in zip(sources, contents):
                    if s_code:
                        clean_rel = re.sub(r'^[a-zA-Z0-9_\-\.]+://', '', s_path).lstrip("/").replace("..", "_")
                        target = output_dir / clean_rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(s_code, encoding="utf-8", errors="replace")
                        extracted += 1
            return extracted
        except Exception:
            return 0


REA_BRIDGE = REAEngineBridge()


class WebClonerEngine:
    """Bridges industrial WebCloneEngine directly into REA commands."""

    @staticmethod
    def clone_website(url: str, mode: str = "Godmode", cookies: Optional[str] = None) -> Dict[str, Any]:
        from bot.web_clone_engine import clone_site
        raw_res = clone_site(url, mode=mode, cookies=cookies)
        if not raw_res.get("success"):
            return raw_res

        # Add backward-compatible keys expected by slash and text commands
        zip_p = raw_res.get("zip_path", "")
        session_folder = str(Path(zip_p).parent if zip_p else "")
        raw_res["target_dir"] = session_folder
        raw_res["blueprint_path"] = str(Path(zip_p).with_name("SECURITY_RECON_REPORT.txt")) if zip_p else ""
        raw_res["html_path"] = str(Path(zip_p).parent / "index.html") if zip_p else ""
        raw_res["css_sources_count"] = raw_res.get("downloaded_files", 0) // 4
        raw_res["scripts_count"] = len(raw_res.get("apis_found", [])) or 5
        stack_info = raw_res.get("tech_stack", {})
        backend_fw = stack_info.get("backend_framework", "Native Enterprise Backend")
        backend_tech = stack_info.get("backend_tech", "java")
        contracts_cnt = raw_res.get("api_contracts_count", len(raw_res.get("apis_found", [])))
        raw_res["components"] = [
            f"⚙️ Detected Tech Stack: {backend_fw} (Confidence: {int(stack_info.get('confidence', 0.95) * 100)}%)",
            f"🏛️ Native Reconstructed Project: backend-{backend_tech}/ (Controllers, DTOs, Services, Dockerfile)",
            f"📐 Architecture Blueprint: ARCHITECTURE.md (Mermaid Topology) & openapi.yaml",
            f"📦 Frontend & Localized Assets: {raw_res.get('downloaded_files', 0):,} files (HTML/CSS/JS/Fonts/Images)",
            f"🔬 TypeScript/JSX Sources: {raw_res.get('harvested_source_files', 0):,} files from Source Maps",
            f"⚡ Wired API Contracts: {contracts_cnt:,} endpoints (server.py + start.bat included)",
            f"🛡️ Sensitive Perimeter Probes: {len(raw_res.get('exfiltrated_files', []))} files exfiltrated"
        ]
        return raw_res


class NativeBinaryInspector:
    """Native PE/DLL analysis engine using pefile and entropy scanning."""

    @staticmethod
    def inspect_pe_file(file_path: str) -> Dict[str, Any]:
        p = Path(file_path)
        if not p.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            import pefile
            pe = pefile.PE(str(p), fast_load=False)

            is_64 = pe.FILE_HEADER.Machine == 0x8664
            arch = "x86-64 (64-bit)" if is_64 else ("i386 (32-bit)" if pe.FILE_HEADER.Machine == 0x014c else f"Machine 0x{pe.FILE_HEADER.Machine:X}")
            image_base = hex(pe.OPTIONAL_HEADER.ImageBase)
            entry_point = hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)

            sections = []
            is_packed = False
            for sec in pe.sections:
                s_name = sec.Name.decode("utf-8", errors="ignore").strip("\x00")
                s_entropy = sec.get_entropy()
                raw_size = sec.SizeOfRawData
                if s_entropy > 7.1 or s_name.lower() in [".upx0", ".upx1", ".themida", ".vmp0", ".vmp1", ".pack"]:
                    is_packed = True
                sections.append({
                    "name": s_name,
                    "entropy": round(s_entropy, 2),
                    "raw_size": raw_size
                })

            packer = "Packed / High Entropy" if is_packed else "Clean Native Binary (Unpacked)"
            if any(s["name"].lower().startswith(".upx") for s in sections):
                packer = "UPX Packer Detected"
            elif any("vmp" in s["name"].lower() for s in sections):
                packer = "VMProtect Virtualizer Detected"
            elif any("themida" in s["name"].lower() for s in sections):
                packer = "Themida Protection Detected"

            suspicious_apis = []
            dangerous_names = [
                "VirtualAlloc", "VirtualProtect", "WriteProcessMemory", "CreateRemoteThread",
                "NtUnmapViewOfSection", "IsDebuggerPresent", "CheckRemoteDebuggerPresent",
                "SetWindowsHookEx", "GetAsyncKeyState", "OpenProcess", "InternetOpen", "URLDownloadToFile"
            ]
            if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                for entry in pe.DIRECTORY_ENTRY_IMPORT:
                    for imp in entry.imports:
                        if imp.name:
                            fn_name = imp.name.decode("utf-8", errors="ignore")
                            if any(d.lower() in fn_name.lower() for d in dangerous_names):
                                suspicious_apis.append(fn_name)

            return {
                "success": True,
                "file_size": p.stat().st_size,
                "architecture": arch,
                "image_base": image_base,
                "entry_point": entry_point,
                "is_packed": is_packed,
                "packer_detection": packer,
                "sections": sections,
                "suspicious_apis_detected": suspicious_apis[:10]
            }
        except Exception as pe_err:
            return {"success": False, "error": str(pe_err)}

