#!/usr/bin/env bash
echo "Ì∑π Reorganizing Guzo Guest Assist project structure safely..."

ROOT="$HOME/Desktop/Guzo"
BACKUP_DIR="$ROOT/_archive_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Move all old backups to archive
for dir in dashboard_backup dashboard_clean_backup encoding_backups; do
  if [ -d "$ROOT/$dir" ]; then
    mv "$ROOT/$dir" "$BACKUP_DIR/"
    echo "Ì≥¶ Moved old backup: $dir ‚Üí $BACKUP_DIR/"
  fi
done

# Remove redundant venv inside guzo_booking_bot
if [ -d "$ROOT/guzo_booking_bot/venv" ]; then
  rm -rf "$ROOT/guzo_booking_bot/venv"
  echo "Ì∑© Removed duplicate venv from guzo_booking_bot/"
fi

# Move nested logs into main /logs
mkdir -p "$ROOT/logs"
if [ -d "$ROOT/guzo_booking_bot/logs" ]; then
  mv "$ROOT/guzo_booking_bot/logs"/* "$ROOT/logs/" 2>/dev/null
  rm -rf "$ROOT/guzo_booking_bot/logs"
  echo "Ì≥Å Merged guzo_booking_bot/logs ‚Üí /logs/"
fi

# Move dashboard node_modules to archive
if [ -d "$ROOT/dashboard/node_modules" ]; then
  mv "$ROOT/dashboard/node_modules" "$BACKUP_DIR/dashboard_node_modules_backup"
  echo "Ì≥¶ Archived dashboard/node_modules"
fi

echo "‚úÖ Reorganization complete!"
echo "Ì≥Ç Backup created at: $BACKUP_DIR"
