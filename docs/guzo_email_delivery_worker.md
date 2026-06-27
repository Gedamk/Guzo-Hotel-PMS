# Guzo PMS Email Delivery Worker

Guzo PMS processes guest email messages from `guest_notification_outbox`.

## Supported Notification Actions

- `reservation_confirmation`
- `pre_arrival_reminder`
- `checkout_receipt`
- `feedback_request`
- `guest_feedback_request`
- `booking_cancellation`
- `failed_message_manager_alert`

## Environment Variables

```env
GUZO_EMAIL_PROVIDER=smtp
GUZO_SMTP_HOST=smtp.example.com
GUZO_SMTP_PORT=587
GUZO_SMTP_USERNAME=your-smtp-user
GUZO_SMTP_PASSWORD=your-smtp-password
GUZO_SMTP_USE_TLS=true
GUZO_EMAIL_FROM=reservations@example.com
GUZO_EMAIL_MAX_RETRIES=3
```

For local development without sending real messages:

```env
GUZO_EMAIL_PROVIDER=disabled
```

Do not commit real SMTP credentials. Keep them in `.env`, deployment secrets, or a managed secret store.

## Admin Operations

View notification queue:

```http
GET /notifications/outbox?property_code=DRE001
```

Process queued/failed email notifications:

```http
POST /notifications/process-email-outbox?property_code=DRE001
```

Retry a failed notification:

```http
POST /notifications/outbox/{notification_id}/retry?property_code=DRE001
```

Only Admin and General Manager roles can view and retry the queue.
