# Booking business logic
def get_bookings():
    return [
        {'id': 1, 'guest': 'Gedam Kacha', 'hotel': 'Sofi Hotel'},
        {'id': 2, 'guest': 'John Doe', 'hotel': 'Sky View Hotel'}
    ]

def create_booking(booking: dict):
    return {'message': 'Booking created successfully', 'data': booking}

