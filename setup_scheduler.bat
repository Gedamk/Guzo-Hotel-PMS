@echo off
REM ================================================
REM Guzo Project - Setup Windows Task Scheduler Jobs
REM ================================================
echo.
echo ============================================
echo   Guzo Project Task Scheduler Setup Script
echo ============================================
echo.

REM --- Step 1: Remove old tasks (if they exist) ---
echo Removing old scheduled tasks (ignore errors if not found)...
schtasks /Delete /TN "Guzo - System Health" /F >nul 2>&1
schtasks /Delete /TN "Guzo - Daily Summary" /F >nul 2>&1
schtasks /Delete /TN "Guzo - Weekly Summary" /F >nul 2>&1
schtasks /Delete /TN "Guzo - All Jobs" /F >nul 2>&1

REM --- Step 2: Create fresh tasks ---
echo Creating new scheduled tasks...

:: System Health - Daily 08:00 AM
schtasks /Create /TN "Guzo - System Health" ^
 /TR "C:\Users\Gedan\Desktop\Guzo\system_health.bat" ^
 /SC DAILY /ST 08:00 /RL HIGHEST /F /RU %USERNAME%

:: Daily Summary - Daily 08:00 PM
schtasks /Create /TN "Guzo - Daily Summary" ^
 /TR "C:\Users\Gedan\Desktop\Guzo\run_daily.bat" ^
 /SC DAILY /ST 20:00 /RL HIGHEST /F /RU %USERNAME%

:: Weekly Summary - Mondays 09:00 AM
schtasks /Create /TN "Guzo - Weekly Summary" ^
 /TR "C:\Users\Gedan\Desktop\Guzo\run_weekly.bat" ^
 /SC WEEKLY /D MON /ST 09:00 /RL HIGHEST /F /RU %USERNAME%

:: All Jobs - Daily 07:00 AM
schtasks /Create /TN "Guzo - All Jobs" ^
 /TR "C:\Users\Gedan\Desktop\Guzo\all_jobs.bat" ^
 /SC DAILY /ST 07:00 /RL HIGHEST /F /RU %USERNAME%

echo.
echo ============================================
echo   All tasks created successfully! 🎉
echo   You can verify with: schtasks /Query
echo ============================================
pause
