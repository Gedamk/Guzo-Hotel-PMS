from guzo_backend.modules.notifications import send_notification_prefer_channels
from guzo_backend import config

booking = {
    "Hotel name": "Sofi Hotel",
    "Guest Name": "Test Guest",
    "Contact": "nahom2natanim@gmail.com",   # guest email or phone
    "Source": "website"
}

hotel_contact = {
    "Hotel name": "Sofi Hotel",
    "email": "sophiadefar17@gmail.com",
    "phone": "+2519XXXXXXXX"
}

result = send_notification_prefer_channels(hotel_contact, booking)
print("Result:", result)
