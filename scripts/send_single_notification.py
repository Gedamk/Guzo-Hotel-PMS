from guzo_booking_bot.modules.notifications import send_notification_prefer_channels

booking = {
    "Hotel name": "Sofi Hotel",
    "Guest Name": "Test Guest",
    "Contact": "testguest@example.com",
    "Source": "website"
}

hotel_contact = {
    "Hotel name": "Sofi Hotel",
    "email": "yourhotel@example.com",
    "phone": "+2519XXXXXXXX"
}

result = send_notification_prefer_channels(hotel_contact, booking)
print("Result:", result)
