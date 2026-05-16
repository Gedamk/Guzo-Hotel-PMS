**1. Current Structure**
The repo currently has several overlapping product generations:

- `guzo_backend/`: main FastAPI/backend package with `main.py`, `api/`, `routers/`, `core/`, `db/`, `modules/`, `services/`, `scripts/`, `templates/`, and tests.
- `guzo_pms_frontend/`: strongest current PMS React/Vite app, already organized by modules: `dashboard`, `reservations`, `frontdesk`, `housekeeping`, `finance`, `reports`, `admin`.
- `dashboard_ui/`: older React/CRA-style dashboard/front desk UI.
- `dashboard_frontend/`: Python/Streamlit-style dashboard plus React remnants.
- `guzo_dashboard/`, `website/`, `pms_frontend/`: separate frontend/prototype apps.
- `guzo_api/`: smaller FastAPI reporting API that overlaps with `guzo_backend`.
- `guzo_booking_bot/`: bot-specific package.
- Root-level scripts/tests/reports: many `.py`, `.bat`, `.sh`, generated daily reports, checks, and one-off utilities live directly in the repo root.
- Data/config/assets: `assets/`, `config/`, `migrations/`, `guzo_db/`, `email_templates/`, `logs/`, `reports_out/`, `tmp_reports/`.

**2. Problems And Risks**
The biggest issue is unclear ownership. There are multiple possible “real” frontends and APIs, so future changes can land in the wrong app.

Key risks:

- Duplicate backend API surfaces: [guzo_backend/main.py](</c:/Users/Gedan/Desktop/Guzo/guzo_backend/main.py>) and [guzo_api/main.py](</c:/Users/Gedan/Desktop/Guzo/guzo_api/main.py>) both expose reporting-style APIs.
- Backend route organization is split across `api/`, `routers/`, root files like `api_bookings.py`, and large `modules/`.
- `guzo_backend/modules/` is too broad: booking, payments, reports, messaging, integrations, Sheets, logging, and utilities are mixed together.
- PMS frontend says `finance`, but mission says `folio/cashier`; naming should be aligned before growth.
- No current `nightaudit` or `booking` module in `guzo_pms_frontend/src/modules`, even though they are mission-critical.
- Old backups and `.bak` files sit beside active code.
- Generated reports and operational files appear in the repo root.
- A real-looking service account file is tracked: `guzo_backend/credentials/guzo_service_account.json`. That is a serious secret-management risk.
- Root `package.json` has only router dependencies and may confuse install/build expectations.
- Frontend build may depend on exact import paths from [guzo_pms_frontend/src/App.tsx](</c:/Users/Gedan/Desktop/Guzo/guzo_pms_frontend/src/App.tsx>), so moving modules casually would break runtime.

**3. Proposed Clean Organization**
Recommended target shape:

```text
Guzo/
  apps/
    pms-web/                 # current guzo_pms_frontend
    marketing-site/          # current website, if still needed
    legacy-dashboard-ui/     # archived dashboard_ui, if still referenced
  backend/
    app/
      main.py
      api/
        dashboard/
        reservations/
        frontdesk/
        housekeeping/
        folio/
        reports/
        admin/
        nightaudit/
        booking/
        bots/
      services/
        reservations/
        frontdesk/
        housekeeping/
        folio/
        reports/
        nightaudit/
        notifications/
      db/
      core/
      schemas/
      integrations/
    tests/
    scripts/
  bots/
    booking-bot/
  packages/
    shared-types/            # optional later
  docs/
  config/
  migrations/
  assets/
  tools/
  tmp/                       # ignored
```

For the frontend PMS app:

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

**4. Step-By-Step Migration Plan**
1. Inventory active entry points: decide whether `guzo_backend` and `guzo_pms_frontend` are the official production apps.
2. Mark old apps as legacy in docs before moving anything.
3. Add/confirm ignore rules for generated reports, backups, local env, credentials, logs, and temp output.
4. Remove secrets from git history separately and rotate exposed credentials.
5. Rename only conceptually first: document `finance` as future `folio/cashier`, do not move it yet.
6. Add missing placeholder modules later: `nightaudit` and `booking`, with routes hidden or disabled until implemented.
7. Consolidate backend APIs by workflow area while preserving existing URL paths.
8. Move old dashboards into `legacy/` or `apps/legacy-*` only after import/build checks pass.
9. Move root scripts into `tools/` or `backend/scripts/` in small batches.
10. After each batch, run frontend build, backend import checks, and API smoke tests.

**5. Safe First Changes**
No-code or low-risk first steps:

- Create a written architecture map in `docs/`.
- Add comments/docs identifying official apps: `guzo_backend` and `guzo_pms_frontend`.
- Audit `.env.example` and remove any real values from tracked config.
- Add missing ignore patterns for credential JSONs and generated outputs.
- Move nothing yet; first produce a migration checklist.
- Add empty planning docs for PMS workflows: reservations, front desk, housekeeping, folio, night audit.
- Decide whether `dashboard_ui`, `dashboard_frontend`, `guzo_dashboard`, and `guzo_api` are active, legacy, or archival.

**6. Dangerous Changes**
These could break imports/runtime:

- Moving `guzo_backend/modules/*`; many files likely import from `guzo_backend.modules`.
- Moving `guzo_backend/api/*` without updating `main.py`.
- Renaming frontend module folders without updating [App.tsx](</c:/Users/Gedan/Desktop/Guzo/guzo_pms_frontend/src/App.tsx>) and service imports.
- Deleting `dashboard_ui`; `guzo_backend/main.py` currently serves `dashboard_ui/build` if present.
- Deleting `.bak` files without first confirming they are not referenced by scripts or recovery workflows.
- Changing route paths like `/frontdesk/bookings`, `/finance/*`, `/reports/*`, `/rooms/*`.
- Moving DB helpers from `guzo_backend/db` or `guzo_backend/core` without a full import search.
- Removing root scripts before checking scheduled tasks, `.bat` launchers, or local run habits.

**7. Recommended Checks Before Refactor**
Run these before any file movement:

```bash
git status --short
python -m pytest
python -m uvicorn guzo_backend.main:app --reload
cd guzo_pms_frontend && npm run build
cd guzo_pms_frontend && npm run lint
rg "guzo_backend.modules|guzo_backend.api|dashboard_ui|guzo_api|frontdesk/bookings|finance/" .
```

Also smoke test:

- `GET /health`
- `GET /frontdesk/bookings`
- room availability/status endpoints
- finance/folio endpoints
- reports endpoints
- PMS frontend routes: `/dashboard`, `/reservations`, `/frontdesk`, `/housekeeping`, `/finance`, `/reports`, `/admin`

Files changed: none.

Tests/checks run: read-only structure inspection using `Get-ChildItem`, `rg --files`, `git status --short`, `git ls-files`, and selected `Get-Content` reads. No builds or test suites were run because the request was structure review only.