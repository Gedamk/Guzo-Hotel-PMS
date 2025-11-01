# -*- coding: utf-8 -*-
"""
check_utf8.py – Validate all .py files in project are proper UTF-8
---------------------------------------------------------------
Scans recursively from the current folder and reports
any files that fail to decode as UTF-8.
"""

import os

def check_utf8_files(base_dir="."):
    bad_files = []
    for root, _, files in os.walk(base_dir):
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(root, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        f.read()
                except UnicodeDecodeError:
                    bad_files.append(path)
    return bad_files

if __name__ == "__main__":
    print("🔍 Checking all .py files for UTF-8 encoding...\n")
    errors = check_utf8_files(".")
    if errors:
        print("❌ Found non-UTF8 files:")
        for path in errors:
            print("   -", path)
    else:
        print("✅ All .py files are valid UTF-8!")
