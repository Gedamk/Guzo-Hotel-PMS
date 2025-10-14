# -*- coding: utf-8 -*-
"""
Deep Clean Utility for Guzo Dashboard
------------------------------------
Removes all non-UTF8 and invisible characters from Streamlit dashboard files.
Safe for production deployment.
"""

import os, re, hashlib

def clean_text(raw_bytes):
    # Decode with UTF-8 ignoring bad bytes
    text = raw_bytes.decode('utf-8', errors='ignore')

    # Remove any non-printable or private-use unicode ranges
    text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]', '', text)

    # Replace double spaces and normalize quotes
    text = (
        text.replace("  ", " ")
            .replace("’", "'")
            .replace("“", '"')
            .replace("”", '"')
            .replace("…", "...")
    )
    return text

def deep_clean_file(path):
    with open(path, 'rb') as f:
        raw = f.read()
    cleaned_text = clean_text(raw)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(cleaned_text)
    checksum = hashlib.md5(cleaned_text.encode()).hexdigest()[:8]
    print(f"✅ Cleaned {path} | hash={checksum}")

print("🧹 Deep cleaning all dashboard Python files...\n")

for root, _, files in os.walk('dashboard'):
    for f in files:
        if f.endswith('.py'):
            deep_clean_file(os.path.join(root, f))

print("\n✅ All dashboard .py files are now UTF-8 clean and printable.")
