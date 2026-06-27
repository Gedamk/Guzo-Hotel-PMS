# Guzo PMS Night Audit Posting Flow

Night Audit now posts operational revenue into guest folios and locks the business date.

## Close Flow

```txt
Run Night Audit
No-show candidates are marked no_show
No-show charge posts once per booking/date
Validation re-runs
In-house bookings receive room charge
Service charge posts from Admin rate rules
Tax posts from Admin rate rules
Folio totals refresh
Night Audit close package archives
Business date locks
```

## Duplicate Protection

`night_audit_postings` prevents duplicate postings for:

```txt
room_charge
service_charge
tax
no_show_charge
```

The unique key is:

```txt
property_code + business_date + booking_id + posting_type
```

## Production Tables

Alembic revision `20260602_0003` creates:

```txt
night_audit_postings
business_date_locks
report_archive
```

After migration, the database should report:

```txt
20260602_0003 (head)
```
