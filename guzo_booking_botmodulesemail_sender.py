@echo off
chcp 65001 > nul
cd /d "C:\Users\Gedan\Desktop\Guzo"
call venv\Scripts\activate.bat
python -m guzo_booking_bot.modules.daily_summary
echo [%date% %time%] ✅ Daily Summary finished successfully >> logs\daily\daily_summary_%date:~-4%-%date:~4,2%-%date:~7,2%.log
exit
