# Guest Profile and Communication Queue Migration

Migration `20260602_0014_guest_profile_communication_queue.py` moves the guest profile and guest communication schema from runtime compatibility guards into Alembic-managed database structure.

## Purpose

This migration adds production-tracked schema for:

- `guest_profiles`
- guest profile links on bookings, public booking requests, folios, and guest feedback
- notification outbox profile links and retry tracking
- manager alerts for VIP arrivals, failed guest messages, low feedback ratings, and missing deposits
- indexes for guest lookup, notification processing, and alert review

The migration is additive and preserves existing demo, development, and pilot records. It does not drop existing guest, booking, folio, feedback, notification, or alert data.

## Run Migration

From the project root:

```bash
venv\Scripts\alembic.exe upgrade head
```

Verify the current revision:

```bash
venv\Scripts\alembic.exe current
```

Expected head after this migration:

```text
20260602_0014 (head)
```

## Notes

Runtime schema guards remain only as compatibility protection for older local databases and isolated tests. Normal application startup should rely on Alembic-managed schema.
