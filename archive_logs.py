import os
import zipfile
import datetime
from pathlib import Path

# ==========================================================
# GUZO - WEEKLY LOG ARCHIVER
# ==========================================================

# Define paths
base_dir = Path(__file__).parent
logs_dir = base_dir / "logs"
archive_dir = base_dir / "storage" / "archives"
archive_dir.mkdir(parents=True, exist_ok=True)

# Current week & date info
today = datetime.date.today()
year, week_num, _ = today.isocalendar()
archive_name = f"{year}-week{week_num}.zip"
archive_path = archive_dir / archive_name

def should_archive(file_path):
    """Return True if the file is older than 7 days."""
    file_date = datetime.date.fromtimestamp(file_path.stat().st_mtime)
    return (today - file_date).days > 7

def archive_logs():
    """Compress old logs and move to archives folder."""
    archived_files = []
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for log_file in logs_dir.glob("*.log"):
            if should_archive(log_file):
                zipf.write(log_file, log_file.name)
                archived_files.append(log_file.name)
                log_file.unlink()  # delete after zipping

    if archived_files:
        print(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Archived {len(archived_files)} log files ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {archive_name}")
    else:
        print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¹ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ No old logs found to archive.")

if __name__ == "__main__":
    print("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Starting Guzo Weekly Log Archiver...")
    archive_logs()
    print("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Done.")
