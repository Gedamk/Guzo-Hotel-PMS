@echo off
title Guzo Guest Assist - Daily Bot Launcher
echo ====================================================
echo Starting Daily Guzo Guest Assist Bot Process...
echo ====================================================

:: Step 1 - Kill old Python processes
echo Cleaning up previous bot instances...
taskkill /F /IM python.exe /T >nul 2>&1

:: Step 2 - Change to project directory
cd /d "C:\Users\Gedan\Desktop\Guzo"

:: Step 3 - Activate virtual environment
call venv\Scripts\activate

:: Step 4 - Run the bot
echo Launching new bot instance...
python guzo_booking_bot\main.py >> logs\bot_%date:~-4,4%-%date:~4,2%-%date:~7,2%.log 2>&1

echo ----------------------------------------------------
echo ✅ Guzo Guest Assist Bot started successfully!
echo Log file saved in the logs folder.
pause



