import os
import glob
import json

base_dir = r"d:\Deobfuscate\Lerning\Luraph"

results = []
for root, dirs, files in os.walk(base_dir):
    for f in files:
        if f.endswith((".lua", ".luau", ".txt")):
            path = os.path.join(root, f)
            size = os.path.getsize(path)
            # check if Luraph protected
            try:
                with open(path, "r", encoding="latin-1") as fh:
                    head = fh.read(500)
                is_lph = "Luraph" in head or "lura.ph" in head
                v14 = "v14" in head
                v15 = "v15" in head
                results.append({
                    "path": path,
                    "rel": os.path.relpath(path, base_dir),
                    "size": size,
                    "is_lph": is_lph,
                    "v14": v14,
                    "v15": v15
                })
            except Exception:
                pass

print(f"Total files scanned: {len(results)}")
lph_files = [r for r in results if r["is_lph"]]
print(f"Total Luraph protected files: {len(lph_files)}")
print(f"Luraph v14: {len([r for r in lph_files if r['v14']])}")
print(f"Luraph v15: {len([r for r in lph_files if r['v15']])}")

print("\n--- Luraph Obfuscated Targets ---")
for r in sorted(lph_files, key=lambda x: x["size"]):
    print(f"[{'v14' if r['v14'] else 'v15' if r['v15'] else 'other'}] {r['size']:>8} bytes : {r['rel']}")
