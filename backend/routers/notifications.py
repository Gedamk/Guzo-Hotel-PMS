from fastapi import APIRouter
from backend.services import notification_service

router = APIRouter()

@router.get('/')
def list_notifications():
    return notification_service.get_notifications()

@router.post('/')
def send_notification(notification: dict):
    return notification_service.send_notification(notification)

