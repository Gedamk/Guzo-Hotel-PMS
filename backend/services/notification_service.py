# Notification business logic
def get_notifications():
    return [
        {'id': 1, 'type': 'Email', 'status': 'Sent'},
        {'id': 2, 'type': 'SMS', 'status': 'Pending'}
    ]

def send_notification(notification: dict):
    return {'message': 'Notification sent successfully', 'data': notification}

