# -*- coding: utf-8 -*-
<#
setup_guzo_tasks.ps1 – Fixed v2
Registers two tasks:
• Daily Summary → 07:00 AM
• Weekly Report → Sunday 08:00 AM
#>

Write-Host "`n🚀 Setting up Guzo Guest Assist scheduled tasks..." -ForegroundColor Cyan

# Paths
$projectPath = "C:\Users\Gedan\Desktop\Guzo"
$dailyBat = "$projectPath\run_daily_summary.bat"
$weeklyBat = "$projectPath\run_weekly_report.bat"
$dailyLog = "$projectPath\logs\daily\task_output.log"
$weeklyLog = "$projectPath\logs\weekly\task_output.log"

# Ensure log folders
New-Item -ItemType Directory -Force -Path (Split-Path $dailyLog) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $weeklyLog) | Out-Null

# Properly quoted task commands for Windows Task Scheduler
$dailyCommand  = "cmd.exe /c `"`"$dailyBat`" ^>^> `"$dailyLog`" 2^>^&1`""
$weeklyCommand = "cmd.exe /c `"`"$weeklyBat`" ^>^> `"$weeklyLog`" 2^>^&1`""

# --- Register tasks ---
schtasks /create /tn "Guzo_Daily_Summary" /tr $dailyCommand /sc daily /st 07:00 /f | Out-Null
Write-Host "✅ Scheduled daily summary at 07:00 AM" -ForegroundColor Green

schtasks /create /tn "Guzo_Weekly_Report" /tr $weeklyCommand /sc weekly /d SUN /st 08:00 /f | Out-Null
Write-Host "✅ Scheduled weekly report every Sunday at 08:00 AM" -ForegroundColor Green

# --- Verify ---
Write-Host "`n🧾 Confirming registered tasks..." -ForegroundColor Yellow
schtasks /query | Select-String "Guzo"

Write-Host "`n🎉 Setup complete! Both tasks are ready." -ForegroundColor Cyan
Write-Host "Logs will be saved to:" -ForegroundColor DarkCyan
Write-Host "  → $dailyLog" -ForegroundColor Gray
Write-Host "  → $weeklyLog" -ForegroundColor Gray

