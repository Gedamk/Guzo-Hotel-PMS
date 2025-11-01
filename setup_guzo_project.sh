#!/usr/bin/env bash
# ======================================================
# setup_guzo_project.sh
# ------------------------------------------------------
# Guzo Guest Assist ‚Äì Auto Setup & Structure Validator
# Creates missing folders, fixes misplaced files,
# verifies dependencies, and confirms readiness.
# ======================================================

echo "Ì∫Ä Starting Guzo Guest Assist Project Setup..."
sleep 1

# Root check
ROOT_DIR="$HOME/Desktop/Guzo"
if [ ! -d "$ROOT_DIR" ]; then
  echo "‚ùå ERROR: Guzo project folder not found at $ROOT_DIR"
  exit 1
fi

cd "$ROOT_DIR" || exit 1

# ======================================================
# Ì≥Å Create required folders
# ======================================================
echo "Ì≥¶ Creating required directories..."
mkdir -p dashboard/{assets,components,pages,storage/{logs,temp}}
mkdir -p guzo_booking_bot/{modules,credentials}
mkdir -p scripts reports/{weekly_reports,logs} assets .streamlit

# ======================================================
# Ì∑π Move misplaced or duplicate files
# ======================================================
echo "Ì∑© Organizing misplaced files..."
mv -f hotel_manager_dashboard.py dashboard/ 2>/dev/null
mv -f app_launcher.py dashboard/ 2>/dev/null
mv -f sidebar.py dashboard/ 2>/dev/null
mv -f login.py dashboard/pages/ 2>/dev/null

mv -f google_sheets.py guzo_booking_bot/modules/ 2>/dev/null
mv -f email_sender.py guzo_booking_bot/modules/ 2>/dev/null
mv -f log_helper.py guzo_booking_bot/modules/ 2>/dev/null
mv -f message_router.py guzo_booking_bot/modules/ 2>/dev/null
mv -f system_check.py guzo_booking_bot/modules/ 2>/dev/null

mv -f service_account.json guzo_booking_bot/credentials/ 2>/dev/null
mv -f credentials.json guzo_booking_bot/credentials/ 2>/dev/null

mv -f logo.png dashboard/assets/ 2>/dev/null

# ======================================================
# Ì¥ß Ensure .env and venv exist
# ======================================================
if [ ! -f ".env" ]; then
  echo "‚ö†Ô∏è  .env file missing ‚Äî creating template..."
  cat <<EOT > .env
GOOGLE_SERVICE_ACCOUNT_JSON=guzo_booking_bot/credentials/credentials.json
HOTEL_CONTACTS_SHEET_ID=13WD4nSsNLmYBnf...
NOTIFICATIONS_LOG_SHEET_ID=13WD4nSsNLmYBnf...
SENDGRID_API_KEY=YOUR_SENDGRID_API_KEY
EOT
fi

if [ ! -d "venv" ]; then
  echo "‚öôÔ∏è  Creating Python virtual environment..."
  python -m venv venv
  source venv/Scripts/activate
  pip install --upgrade pip
fi

# ======================================================
# Ì≥¶ Install dependencies if requirements.txt exists
# ======================================================
if [ -f "requirements.txt" ]; then
  echo "Ì≥¶ Installing project dependencies..."
  source venv/Scripts/activate
  pip install -r requirements.txt
else
  echo "‚ö†Ô∏è  requirements.txt missing ‚Äî creating default..."
  cat <<EOT > requirements.txt
streamlit>=1.40.0
pandas
python-dotenv
pyarrow
gspread
oauth2client
sendgrid
reportlab
plotly
EOT
  source venv/Scripts/activate
  pip install -r requirements.txt
fi

# ======================================================
# Ìæ® Ensure Streamlit theme config exists
# ======================================================
if [ ! -f ".streamlit/config.toml" ]; then
  echo "Ìæ® Creating Streamlit theme config..."
  cat <<EOT > .streamlit/config.toml
[theme]
base = "light"
primaryColor = "#184E77"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F6F9FC"
textColor = "#1C1C1E"
font = "sans serif"
EOT
fi

# ======================================================
# Ì∑† Final summary
# ======================================================
echo ""
echo "‚úÖ Guzo Guest Assist structure verified!"
echo "Ì≥Ç Project root: $ROOT_DIR"
echo "Ì≥ä Key Folders:"
echo "  - dashboard/              ‚Üí Streamlit dashboards"
echo "  - guzo_booking_bot/       ‚Üí Core backend modules"
echo "  - scripts/                ‚Üí Automation scripts"
echo "  - reports/                ‚Üí PDF & logs output"
echo ""
echo "ÌæØ Next steps:"
echo "  1Ô∏è‚É£ source venv/Scripts/activate"
echo "  2Ô∏è‚É£ streamlit run dashboard/hotel_manager_dashboard.py"
echo "  3Ô∏è‚É£ python scripts/daily_check.py"
echo ""
echo "Ì≤´ Setup completed successfully!"
