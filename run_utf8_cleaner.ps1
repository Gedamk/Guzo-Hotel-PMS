# 🚀 UTF-8 Cleaner and Git Commit Script
# -------------------------------------
# Ensures all Python files are UTF-8 clean before committing to GitHub.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🚀 Running UTF-8 Cleaner and Git Commit Tool" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan

# Use current directory instead of $PSScriptRoot for compatibility
$projectRoot = Get-Location

# Step 1: Activate virtual environment
Write-Host "`n🔧 Activating Python virtual environment..." -ForegroundColor Cyan
$activatePath = "$projectRoot\venv\Scripts\Activate.ps1"
if (Test-Path $activatePath) {
    & $activatePath
    Write-Host "✅ Virtual environment activated." -ForegroundColor Green
} else {
    Write-Host "⚠️ Virtual environment not found at $activatePath" -ForegroundColor Red
}

# Step 2: Run UTF-8 Cleaner
Write-Host "`n🔍 Checking Python files for encoding issues..." -ForegroundColor Cyan
python utf8_cleaner.py

# Step 3: Ask for commit message
$commit_msg = Read-Host "`n💬 Enter commit message"

# Step 4: Git add, commit, and push
Write-Host "`n📦 Staging changes..." -ForegroundColor Yellow
git add .

Write-Host "📝 Committing changes..." -ForegroundColor Yellow
git commit -m "$commit_msg"

Write-Host "🚀 Pushing to GitHub..." -ForegroundColor Yellow
git push

Write-Host "`n✅ Done! UTF-8 cleaner and push complete." -ForegroundColor Green
Pause
