# Guzo PMS Database Migrations

Guzo PMS uses Alembic for production database control. Runtime table creation can still protect MVP/demo environments, but production and pilot hotels should apply migrations before starting the backend.

## Configure Database

Set the existing Guzo database variables in `.env`:

```txt
GUZO_DB_NAME=guzo_db
GUZO_DB_USER=guzo_user
GUZO_DB_PASSWORD=your_password
GUZO_DB_HOST=localhost
GUZO_DB_PORT=5432
```

Alembic reads the same configuration used by `guzo_backend.core.postgres_db`.

## Run Migrations

From the project root:

```bash
venv\Scripts\alembic.exe upgrade head
```

Check current migration:

```bash
venv\Scripts\alembic.exe current
```

View migration history:

```bash
venv\Scripts\alembic.exe history
```

## First Production Migration

Revision `20260602_0001` creates and seeds the PMS control foundations:

```txt
rate_plans
room_type_rates
tax_service_rules
season_rules
deposit_policies
payment_requests
guest_notification_outbox
public_booking_requests
folios
audit_logs
pms_audit_logs
booking confirmation/rate/payment/source columns
```

Default seed data is inserted with conflict protection for property `DRE001`, so repeated migration runs do not duplicate rows.

## Guest Profile and Communication Migration

Revision `20260602_0014` adds the guest profile and guest communication schema:

```txt
guest_profiles
guest profile links on bookings, public booking requests, folios, and feedback
notification retry/profile tracking
manager_alerts
guest lookup, notification, and alert indexes
```

Run it with:

```bash
venv\Scripts\alembic.exe upgrade head
```

See `docs/guzo_guest_profile_communication_migration.md` for the detailed purpose and verification notes.

## Production Rule

For pilot or production hotels:

```txt
1. Backup database.
2. Pull latest code.
3. Run Alembic migrations.
4. Start backend.
5. Confirm Admin > Rates & Taxes contains expected rules.
6. Confirm Booking Hub quote shows applied rules.
```

Runtime `CREATE TABLE IF NOT EXISTS` guards can remain temporarily for demo resilience, but new schema changes should be added through Alembic migrations first.
