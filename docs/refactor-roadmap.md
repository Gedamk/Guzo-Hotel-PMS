# Guzo Refactor Roadmap

This roadmap turns the repository structure review into a cautious, step-by-step plan. It is documentation-only and does not move, delete, or rewrite files.

## Goals

- Make `guzo_backend/` the clear main backend.
- Make `guzo_pms_frontend/` the clear main PMS frontend.
- Organize code around hotel PMS workflows: dashboard, reservations, front desk, housekeeping, folio/cashier, reports, admin, night audit, and guest booking.
- Preserve existing API behavior while reducing duplicate apps, duplicate routes, and unclear ownership.

## Current Risks

- Multiple frontend generations exist in the repository, making it easy to edit the wrong app.
- Backend APIs are split across `api/`, `routers/`, root backend files, and broad `modules/` files.
- `finance` exists in the frontend, while the product mission refers to `folio/cashier`.
- `nightaudit` and guest `booking` are not yet first-class PMS frontend modules.
- Backup files, generated reports, scripts, and old prototypes are mixed with active source.
- Real credentials must not be committed or treated as normal source files.

## Proposed Target Shape

Long-term organization can move toward this shape after tests and import checks are in place:

```text
Guzo/
  apps/
    pms-web/
    marketing-site/
    legacy-dashboard-ui/
  backend/
    app/
      main.py
      api/
      services/
      db/
      core/
      schemas/
      integrations/
    tests/
    scripts/
  bots/
    booking-bot/
  docs/
  config/
  migrations/
  assets/
  tools/
```

For the PMS frontend:

```text
apps/pms-web/src/
  modules/
    dashboard/
    reservations/
    frontdesk/
    housekeeping/
    folio/
    reports/
    admin/
    nightaudit/
    booking/
  components/
  layout/
  services/
  context/
  types/
  config/
```

## Migration Plan

1. Confirm active apps.
   - Treat `guzo_backend/` as the main backend.
   - Treat `guzo_pms_frontend/` as the main PMS frontend.
   - Classify other app folders as active support, legacy, archival, or unknown.

2. Protect secrets and generated files.
   - Keep real credentials out of git.
   - Keep generated reports, logs, backups, and local temp output ignored.
   - Use `.env.example` only for sample variables.

3. Document current routing and launch commands.
   - Record backend entry points.
   - Record frontend dev/build commands.
   - Record known API paths used by the frontend.

4. Add missing PMS workflow placeholders only when needed.
   - Plan `nightaudit`.
   - Plan `booking`.
   - Decide whether `finance` should remain named `finance` internally or gradually become `folio`.

5. Consolidate backend code by workflow area.
   - Move only one workflow at a time.
   - Preserve public API paths.
   - Keep business logic in services and route files thin.

6. Archive or relocate legacy apps.
   - Do this only after confirming they are not served by the backend, launch scripts, scheduled jobs, or demos.
   - Avoid deleting files in the same step as moving or renaming.

7. Clean up root-level scripts and outputs.
   - Move reusable tools into `tools/` or backend scripts.
   - Leave generated reports out of source control.

## Safe First Changes

- Add documentation that identifies active apps.
- Add this roadmap.
- Add security notes for credentials and environment variables.
- Add tests or smoke-check documentation before moving source files.
- Update `.gitignore` only if needed and reviewed separately.

## Dangerous Changes

- Moving `guzo_backend/modules/*` without import checks.
- Moving `guzo_backend/api/*` without updating `guzo_backend/main.py`.
- Renaming frontend module folders without updating route imports.
- Deleting `dashboard_ui/`, because the backend currently knows how to serve its production build if present.
- Changing public endpoints such as `/frontdesk/bookings`, `/finance/*`, `/reports/*`, `/rooms/*`, or `/health`.
- Removing root scripts before checking scheduled tasks and local run commands.

## Checks Before Any Refactor

Run these before moving source files:

```bash
git status --short
python -m pytest
python -m uvicorn guzo_backend.main:app --reload
cd guzo_pms_frontend && npm run build
cd guzo_pms_frontend && npm run lint
rg "guzo_backend.modules|guzo_backend.api|dashboard_ui|guzo_api|frontdesk/bookings|finance/" .
```

Recommended smoke checks:

- `GET /health`
- `GET /frontdesk/bookings`
- room availability and room status endpoints
- finance or folio endpoints
- reports endpoints
- frontend routes: `/dashboard`, `/reservations`, `/frontdesk`, `/housekeeping`, `/finance`, `/reports`, `/admin`
