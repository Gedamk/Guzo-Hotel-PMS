#!/usr/bin/env bash
set -e
echo "í·¹ Starting full Guzo Guest Assist reorganization..."

ROOT="$HOME/Desktop/Guzo"
ARCHIVE="$ROOT/_archive_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ARCHIVE"

echo "í³¦ Archiving non-essential or duplicate folders..."
for dir in dashboard_backup dashboard_clean_backup encoding_backups guzo_booking_bot/venv guzo_booking_bot/logs dashboard/node_modules node_modules; do
  if [ -d "$ROOT/$dir" ]; then
    mv "$ROOT/$dir" "$ARCHIVE/"
    echo "  âžœ Moved $dir â†’ $ARCHIVE/"
  fi
done

echo "í³ Re-creating essential structure..."
mkdir -p "$ROOT"/{dashboard/{assets,components,pages,storage/{logs,temp}},guzo_booking_bot/{modules/{integrations},credentials,reports,templates,utils},scripts,reports/{weekly_reports,logs,assets},logs/{daily,weekly,webhooks/{failed,recovered},archive},.streamlit,venv}

for f in .env requirements.txt setup_guzo_project.sh run_daily.bat run_weekly.bat; do
  if [ ! -f "$ROOT/$f" ]; then
    touch "$ROOT/$f"
    echo "  âžœ Created placeholder $f"
  fi
done

LOGO="$ROOT/dashboard/assets/logo.png"
if [ ! -f "$LOGO" ]; then
  echo "í¿¨ Creating placeholder logo..."
  convert -size 200x200 xc:white -gravity center -pointsize 40 -annotate 0 "GUZO" "$LOGO" 2>/dev/null || echo "   (placeholder text logo)"
fi

echo "âœ… Folder reorganization complete!"
echo "í³‚ Backup archive: $ARCHIVE"
