# -*- coding: utf-8 -*-
"""
check_utf8_integrity.py – UTF-8 Encoding Checker
Scans all .py files in the project for invalid encodings.
"""

import os


def check_utf8(path):
    errors = []
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith(".py"):
                full_path = os.path.join(root, f)
                try:
                    with open(full_path, "r", encoding="utf-8") as file:
                        file.read()
                except UnicodeDecodeError as e:
                    errors.append(f"[⚠️] Encoding issue in {full_path}: {e}")
    return errors


if __name__ == "__main__":
    print("🔍 Scanning for non-UTF-8 Python files...\n")
    results = check_utf8(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    if results:
        print("\n".join(results))
    else:
        print("✅ All Python files are UTF-8 clean!")
