import importlib
import platform
import sys
from pathlib import Path
from typing import List, Dict, Any


class RuntimeGuard:
    """Checks local Python compatibility and long-text handling rules."""

    @staticmethod
    def python_version_info() -> Dict[str, Any]:
        return {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
            "major": sys.version_info.major,
            "minor": sys.version_info.minor,
            "patch": sys.version_info.micro,
        }

    @staticmethod
    def check_audioop() -> Dict[str, Any]:
        result = {"available": False, "error": None, "module": "audioop"}
        try:
            import audioop  # type: ignore
            result["available"] = True
            result["details"] = "audioop import succeeded"
            return result
        except Exception as exc:  # pragma: no cover - environment dependent
            result["error"] = str(exc)
            result["details"] = "audioop import failed"
            return result

    @staticmethod
    def check_runtime() -> Dict[str, Any]:
        info = RuntimeGuard.python_version_info()
        audioop = RuntimeGuard.check_audioop()
        compat = True
        if info["major"] >= 3 and info["minor"] >= 13:
            compat = audioop["available"]
        return {
            "python": info,
            "audioop": audioop,
            "discord_compatible": compat,
            "recommendation": (
                "Python runtime is compatible with Discord.py and audioop" if compat else
                "Use Python 3.12.x or install audioop-lts for Python 3.13+ to restore discord audio support"
            ),
        }

    @staticmethod
    def chunk_text(text: str, max_chars: int = 1800, split_on: str = "\n") -> List[str]:
        payload = (text or "").strip()
        if not payload:
            return []
        if len(payload) <= max_chars:
            return [payload]

        parts: List[str] = []
        buffer: List[str] = []
        current_len = 0
        for line in payload.split(split_on):
            nxt = f"{line}{split_on}"
            if current_len + len(nxt) > max_chars and buffer:
                parts.append("".join(buffer).rstrip())
                buffer = [line]
                current_len = len(line) + 1
            else:
                buffer.append(nxt)
                current_len += len(nxt)
        if buffer:
            parts.append("".join(buffer).rstrip())
        return [p for p in parts if p.strip()]

    @staticmethod
    def chunk_long_script(script_text: str, max_lines: int = 1800) -> List[str]:
        text = (script_text or "").strip()
        if not text:
            return []
        lines = text.splitlines()
        if len(lines) <= max_lines:
            return [text]

        chunks: List[str] = []
        for idx in range(0, len(lines), max_lines):
            chunks.append("\n".join(lines[idx:idx + max_lines]))
        return chunks


runtime_guard = RuntimeGuard()
