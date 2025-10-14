# -*- coding: utf-8 -*-
"""
Secure UTF-8 Cleaner for Dashboard
----------------------------------
Backs up, cleans, and re-encodes all .py files under dashboard/
"""

import os, chardet, hashlib, shutil

ROOT_DIR = "dashboard"
LOG_FILE = "dashboard_encoding_report.log"
BACKUP_DIR = "dashboard_backup"

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

        backup_path = os.path.join(BACKUP_DIR, os.path.relpath(path, ROOT_DIR))
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(path, backup_path)

        clean_text = raw.decode(enc, errors="ignore")
        with open(path, "w", encoding="utf-8") as f:
            f.write(clean_text)

        after_hash = hash_file(path)
        return f"✅ {path} | encoding={enc} | cleaned | hash={after_hash[:8]}"
    except Exception as e:
        return f"❌ {path} | error: {e}"

def main():
    print("🧹 Scanning and cleaning dashboard files securely...")
    os.makedirs(BACKUP_DIR, exist_ok=True)

    log_lines = []
    for root, _, files in os.walk(ROOT_DIR):
        for fname in files:
            if fname.endswith(".py"):
                path = os.path.join(root, fname)
                result = safe_clean_file(path)
                print(result)
                log_lines.append(result)

    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log.write("\n".join(log_lines))

    print("\n🧾 Cleaning complete. Report saved to", LOG_FILE)
    print("🔒 Backups saved under:", BACKUP_DIR)

if __name__ == "__main__":
    main()
