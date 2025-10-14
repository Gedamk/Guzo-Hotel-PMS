# -*- coding: utf-8 -*-
import os, chardet

path = "dashboard/pages/manager_center.py"

if not os.path.exists(path):
    print("‚ùå File not found.")
else:
    with open(path, "rb") as f:
        raw = f.read()
    enc_info = chardet.detect(raw)
    enc = enc_info.get("encoding", "latin1")  # fallback to latin1
    print(f"Ì¥ç Detected encoding: {enc}")

    try:
        # decode with fallback if utf-8 fails
        try:
            text = raw.decode(enc or "utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin1", errors="ignore")

        # rewrite clean UTF-8
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"‚úÖ Cleaned and saved {path} as UTF-8.")
    except Exception as e:
        print("‚ùå Error cleaning file:", e)

