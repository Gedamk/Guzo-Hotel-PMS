# -*- coding: utf-8 -*-
import os, chardet

path = r"dashboard/pages/manager_center.py"

if not os.path.exists(path):
    print("❌ manager_center.py not found.")
else:
    with open(path, "rb") as f:
        raw = f.read()

    enc = chardet.detect(raw)["encoding"]
    print(f"🔍 Detected encoding: {enc}")

    try:
        text = raw.decode(enc or "latin-1", errors="ignore")
    except Exception as e:
        print(f"⚠️ Decode error with {enc}: {e}")
        text = raw.decode("latin-1", errors="ignore")

    with open(path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(text)

    print(f"✅ Successfully cleaned and saved {path} as UTF-8.")
