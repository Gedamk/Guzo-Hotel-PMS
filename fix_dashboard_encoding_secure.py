# -*- coding: utf-8 -*-
"""
Secure UTF-8 Cleaner for Dashboard and Project
----------------------------------------------
Backs up, cleans, and re-encodes all .py files safely to UTF-8.
"""

import os, chardet, hashlib, shutil

# You can change this later to include other folders like backend/, guzo_booking_bot/
TARGET_DIRS = ["dashboard"]
LOG_FILE = "encoding_secure_report.log"
BACKUP_DIR = "encoding_backups"

def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def safe_clean_file(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()

        enc = chardet.detect(raw)["encoding"] or "utf-8"
        before_hash = hash_file(path)

        backup_path = os.path.join(BACKUP_DIR, path)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(path, backup_path)

        clean_text = raw.decode(enc, errors="ignore")
        with open(path, "w", encoding="utf-8") as f:
            f.write(clean_text)

        after_hash = hash_file(path)
        return f"✅ {path} | {enc} → utf-8 | hash={after_hash[:8]}"
    except Exception as e:
        return f"❌ {path} | error: {e}"

def main():
    print("🧹 Secure UTF-8 Cleaner starting...")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    log = []

    for root_dir in TARGET_DIRS:
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    result = safe_clean_file(path)
                    print(result)
                    log.append(result)

    with open(LOG_FILE, "w", encoding="utf-8") as lf:
        lf.write("\n".join(log))

    print("\n✅ All done. Details saved to", LOG_FILE)
    print("🔒 Backups stored under:", BACKUP_DIR)

if __name__ == "__main__":
    main()
