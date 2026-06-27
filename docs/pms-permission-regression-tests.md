# Guzo PMS Permission Regression Tests

Run backend API-level permission regression tests for sensitive PMS actions.

These tests are intentionally isolated from pilot, demo, and development
business data. The test process refuses to start unless `TEST_DATABASE_URL` is
set. During a run, pytest creates a temporary PostgreSQL schema named like
`pms_permission_qa_<id>`, seeds only QA records inside that schema, overrides
FastAPI database dependencies to use that schema, and drops the schema at the
end of the test session.

## Setup

Create a dedicated test database, or use a dedicated test user/database where
temporary schemas are allowed. Do not point `TEST_DATABASE_URL` at a production
database.

PowerShell example:

```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg2://guzo_test_user:CHANGE_ME@localhost:5432/guzo_test_db"
python -m pytest tests/test_pms_permissions.py
```

Git Bash example:

```bash
export TEST_DATABASE_URL="postgresql+psycopg2://guzo_test_user:CHANGE_ME@localhost:5432/guzo_test_db"
python -m pytest tests/test_pms_permissions.py
```

If `TEST_DATABASE_URL` is missing, the suite fails safely with a clear message
instead of falling back to the normal app database.

## Command

```bash
python -m pytest tests/test_pms_permissions.py
```

The suite intentionally calls protected endpoints with unauthorized PMS user headers and verifies:

- `HTTP 403`
- clear permission error detail
- denied-attempt audit rows in `pms_audit_logs`
- authorized roles reach the normal validation/action path

Covered actions:

- Public booking request conversion
- Front Desk check-in
- Front Desk check-out
- Walk-in booking creation
- Housekeeping room status update
- Finance payment posting
- Finance charge posting
- Night Audit run
- Night Audit override
- Admin user create, update, disable, and reset password

The tests keep the existing development fallback user behavior unchanged. Requests without an explicit `X-PMS-User-Email` header still use the existing backend fallback identity.
