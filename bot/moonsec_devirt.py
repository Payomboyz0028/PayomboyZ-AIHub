"""
bot/moonsec_devirt.py
=====================
MoonSec V2, V3, V5 Unicode Steganography & Devirtualization Pipeline
"""
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parent.parent
PROMETHEUS_DIR = ROOT / "Prometheus-WeAre-Devs-Dumper-main"
if str(PROMETHEUS_DIR) not in sys.path:
    sys.path.insert(0, str(PROMETHEUS_DIR))

try:
    import moonsec_v5_engine
    import moonsec_v5_unpacker
except ImportError:
    moonsec_v5_engine = None
    moonsec_v5_unpacker = None


class MoonsecDevirt:
    def __init__(self):
        self.invisible_chars = {"\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u034f"}

    def count_invisible(self, text: str) -> int:
        return sum(1 for c in text if c in self.invisible_chars)

    def strip_invisible(self, text: str) -> str:
        for c in self.invisible_chars:
            text = text.replace(c, "")
        return text

    def devirt(self, target_text: str, version: str = "MOONSEC_V2") -> Dict[str, Any]:
        invisible_count = self.count_invisible(target_text)
        clean_seed = self.strip_invisible(target_text)

        # Write to temp file for engine processing
        with tempfile.NamedTemporaryFile(suffix=".lua", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(target_text)
            tmp_path = tmp.name

        try:
            if moonsec_v5_engine:
                res = moonsec_v5_engine.deobfuscate_moonsec_v5(tmp_path)
                if res.get("success"):
                    return {
                        "success": True,
                        "source_code": res.get("code", ""),
                        "invisible_count": invisible_count,
                        "method": res.get("method", "full_devirt")
                    }

            # Fallback: if stego string was extracted
            if clean_seed and clean_seed != target_text and len(clean_seed) > 50:
                return {
                    "success": True,
                    "source_code": clean_seed,
                    "invisible_count": invisible_count,
                    "method": "stego_strip"
                }

            return {
                "success": False,
                "error": "Failed to lift MoonSec bytecode payload",
                "invisible_count": invisible_count
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "invisible_count": invisible_count
            }
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
