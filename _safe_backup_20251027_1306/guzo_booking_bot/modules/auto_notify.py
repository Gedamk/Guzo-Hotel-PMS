import schedule
import time
from guzo_booking_bot.modules.guest_notifications import notify_hotels_about_new_bookings

def job():
    notify_hotels_about_new_bookings()

schedule.every(1).minutes.do(job)

print("Guzo Guest Assist Auto Notification started. Monitoring GuestAssist sheet...")

while True:
    schedule.run_pending()
    time.sleep(1)
