# Guzo PMS Deposit Payment Webhook Flow

The deposit request flow now supports payment completion and folio posting.

## Flow

```txt
Booking Hub requests deposit
payment_requests row is created
Guest receives /public/deposit/{token}
Payment provider confirms payment
Webhook posts to /public/deposit/webhook
payment_requests is marked paid/failed/expired
Converted booking gets payment_status = deposit_paid
Folio payment transaction is posted when booking exists
Guest receipt notification is queued
Audit log records completion
```

## Webhook Endpoint

```txt
POST /public/deposit/webhook
```

Header:

```txt
X-Payment-Webhook-Secret: <GUZO_PAYMENT_WEBHOOK_SECRET>
```

Body:

```json
{
  "token": "payment-request-token",
  "status": "paid",
  "amount_etb": 2500,
  "provider": "telebirr",
  "provider_reference": "PROVIDER-123",
  "paid_at": "2026-06-02T12:30:00"
}
```

Set `GUZO_PAYMENT_WEBHOOK_SECRET` or `PAYMENT_WEBHOOK_SECRET` in `.env` for provider validation. If a deposit is paid before a public request is converted, Guzo marks the request deposit as paid and posts it to the folio when Booking Hub converts the request.
