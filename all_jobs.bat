@echo off 
:: Guzo Guest Assist - All Automated Jobs Runner 
cd /d "C:\Users\Gedan\Desktop\Guzo" 
call venv\Scripts\activate 
echo ============================================== 
echo   Starting Guzo Guest Assist Automation Batch 
echo ============================================== 
echo [1/4] Running Daily Summary... 
if exist run_daily.bat (call run_daily.bat) else (echo ??  Daily job skipped) 
echo [2/4] Running Weekly Summary... 
if exist run_weekly.bat (call run_weekly.bat) else (echo ??  Weekly job skipped) 
echo [3/4] Running Monthly Performance... 
if exist run_monthly.bat (call run_monthly.bat) else (echo ??  Monthly job skipped) 
echo [4/4] Running System Health Check... 
if exist system_health.bat (call system_health.bat) else (echo ??  Health check skipped) 
echo ============================================== 
echo ? All Guzo jobs completed. 
echo ============================================== 
pause 
