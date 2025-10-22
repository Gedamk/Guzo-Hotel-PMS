# ╔════════════════════════════════════════════╗
# ║  🚀 UTF-8 Cleaner and Git Commit Script     ║
# ╚════════════════════════════════════════════╝

# Ensure output encoding supports Unicode
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "🚀 Running UTF-8 Cleaner and Git Commit Tool" -ForegroundColor Yellow
Write-Host "============================================`n" -ForegroundColor Cyan

# Activate Python virtual environment
Write-Host "🔧 Activating Python virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\activate

# Run UTF-8 cleaner
Write-Host "`n🔍 Checking Python files for encoding issues..." -ForegroundColor Cyan
python utf8_cleaner.py

# Ask for commit message
$commit_msg = Read-Host "`n💬 Enter commit message"

# Add + commit + push
Write-Host "`n📦 Staging changes..." -ForegroundColor Yellow
git add .

Write-Host "📝 Committing changes..." -ForegroundColor Yellow
git commit -m "$commit_msg"

Write-Host "🚀 Pushing to GitHub..." -ForegroundColor Yellow
git push

Write-Host "`n✅ Done! UTF-8 cleaner and push complete." -ForegroundColor Green
pause
