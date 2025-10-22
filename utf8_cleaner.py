# -*- coding: utf-8 -*-
"""
utf8_cleaner.py – Detect and auto-fix non-UTF-8 Python files
-------------------------------------------------------------
• Recursively scans the project for .py files
• Skips venv/ and encoding_backups/
• Converts bad encodings to UTF-8 safely
• Prints a clean summary report
"""

import os

def scan_and_fix(base_dir="."):
    repaired, failed = [], []
    for root, _, files in os.walk(base_dir):
        if "venv" in root or "encoding_backups" in root:
            continue
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    f.read()   # try reading as UTF-8
            except UnicodeDecodeError:
                try:
                    # Try common fallback encodings
                    with open(path, "rb") as f:
                        raw = f.read()
                    for enc in ("utf-8-sig", "latin-1", "windows-1252"):
                        try:
                            text = raw.decode(enc)
                            break
                        except Exception:
                            text = None
                    if text is None:
                        raise Exception("No valid decoding found")
                    # Rewrite as clean UTF-8
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    repaired.append(path)
                except Exception:
                    failed.append(path)
    return repaired, failed


if __name__ == "__main__":
    print("🔍 Scanning all .py files for encoding issues...\n")
    fixed, failed = scan_and_fix(".")
    if not fixed and not failed:
        print("✅ All .py files are already UTF-8 clean!")
    else:
        if fixed:
            print("🧩 Fixed files:")
            for f in fixed:
                print("   -", f)
        if failed:
            print("\n⚠️ Could not repair these files:")
            for f in failed:
                print("   -", f)
        print("\n✅ UTF-8 cleaning complete.")
