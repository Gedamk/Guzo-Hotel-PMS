# -*- coding: utf-8 -*-
import os, chardet

path = "dashboard/pages/manager_center.py"

if not os.path.exists(path):
    print("‚ùå File not found.")
else:
    with open(path, "rb") as f:
        raw = f.read()
        enc = chardet.detect(raw)["encoding"]
        print(f"Ì¥ç Detected encoding:", enc)

        # Decode ignoring bad bytes, then re-encode clean UTF-8
        text = raw.decode(enc or "utf-8", errors="ignore")
        with open(path, "w", encoding="utf-8") as out:
            out.write(text)

        print(f"‚úÖ {path} converted and saved as clean UTF-8.")
