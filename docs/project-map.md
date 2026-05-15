# Guzo Project Map

This map identifies the current active applications in the Guzo PMS repository. It is documentation-only and does not change runtime behavior.

## Active Applications

### Main Backend: `guzo_backend/`

`guzo_backend` is the main backend application for Guzo Guest Assist PMS.

Current role:

- FastAPI application entry point: `guzo_backend/main.py`
- PMS API routing for front desk, rooms, bookings, reports, finance, availability, KPI, housekeeping, and bot-related workflows
- Backend business and integration code in `api/`, `routers/`, `core/`, `db/`, `modules/`, `services/`, and `scripts/`
- Database access helpers and migrations support for bookings, rooms, payments, reporting, and housekeeping workflows

Important note: some backend functionality is still split across multiple folders and naming styles. Future refactors should preserve existing endpoints while gradually organizing code by PMS workflow area.

### Main PMS Frontend: `guzo_pms_frontend/`

`guzo_pms_frontend` is the main React/Vite PMS frontend.

Current role:

- React, TypeScript, Vite frontend for the PMS operator experience
- Main app routes in `guzo_pms_frontend/src/App.tsx`
- PMS shell and shared layout in `src/layout/`
- PMS modules in `src/modules/`
- API client code in `src/services/`
- Shared types in `src/types/`

Current PMS modules:

- `dashboard`
- `reservations`
- `frontdesk`
- `housekeeping`
- `finance`
- `reports`
- `admin`

Future modules expected by the product mission:

- `folio` or `cashier`, likely evolving from the current `finance` area
- `nightaudit`
- `booking`, for guest booking flows if this becomes part of the PMS web app

## Supporting Or Legacy Areas

These folders appear to contain earlier apps, prototypes, dashboards, or supporting tools. Treat them carefully until they are explicitly classified as active, legacy, archival, or removable.

- `dashboard_ui/`
- `dashboard_frontend/`
- `guzo_dashboard/`
- `guzo_api/`
- `website/`
- `pms_frontend/`
- `guzo_booking_bot/`
- root-level scripts and report files

## Refactor Rule

Before moving or renaming any folder, first confirm whether it is imported, served, launched by scripts, referenced by scheduled jobs, or used in local demos.
