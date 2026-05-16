# Guzo PMS Frontend Structure Review

This review covers the current `guzo_pms_frontend/src` structure only. It is documentation-only and does not change routes, source code, package files, or runtime behavior.

## Current Frontend Structure

`guzo_pms_frontend` is the active React, TypeScript, and Vite PMS frontend.

Important areas:

- `src/App.tsx` defines the active application routes.
- `src/layout/` contains the PMS application shell.
- `src/modules/` contains workflow-specific PMS pages.
- `src/services/` contains API client helpers and workflow actions.
- `src/context/` contains shared PMS state for property and business date.
- `src/types/` contains shared frontend data types.

Supporting areas also exist under `src/`, including `auth/`, `components/`, and `config/`.

## Active Routes

Current routes from `src/App.tsx`:

- `/` redirects to `/dashboard`
- `/login` renders `LoginPage`
- `/dashboard` renders `DashboardPage`
- `/reservations` renders `ReservationsPage`
- `/frontdesk` renders `FrontDeskPage`
- `/housekeeping` renders `HousekeepingPage`
- `/finance` renders `FinanceDashboard`
- `/reports` renders `ReportsPage`
- `/admin` renders `AdminPage`

## Current PMS Modules

Current module folders under `src/modules/`:

- `dashboard`
- `reservations`
- `frontdesk`
- `housekeeping`
- `finance`
- `reports`
- `admin`

The current `finance` module includes folio-style workflows such as folio lookup, charges, payments, transaction history, and checkout validation.

## Finance, Folio, And Cashier Naming

`finance` is the current technical frontend route and module name. Keep `/finance` unchanged for now because the existing route, navigation item, module import, and service calls are already wired around that name.

`folio` or `cashier` is the future PMS naming direction. A future `/folio` or `/cashier` route can be added as an alias to the existing finance screen before any folder or component rename is attempted.

Backend endpoints currently use `/finance/*`, including folio, charge, payment, and checkout validation calls. Route and API naming should not be changed in this PR. Any future rename should be phased and verified with `npm run build`.

## Missing Future Modules

Based on the Guzo PMS mission, these modules should be planned before major frontend refactors:

- `folio` or `cashier`
  - Current behavior lives under `finance`.
  - Do not rename `finance` yet without route aliases, import checks, and backend endpoint planning.
- `nightaudit`
  - No first-class `src/modules/nightaudit` folder or route exists yet.
  - Future scope should include business date close, arrivals/departures validation, open folio checks, housekeeping readiness, and manager reporting.
- `booking`
  - No first-class guest booking module exists in this frontend yet.
  - Future scope should clarify whether guest booking belongs in the PMS web app, a public booking app, or the existing bot flow.

## Duplicate Or Confusing Files

Files to review later, without deleting in this documentation-only change:

- `src/App.tsx.bak`
- `src/layout/PmsShell.tsx.bak`
- module-level `*.tsx.bak` files
- `src/services/financeService.ts.rolefix.bak`
- `src/modules/reports/ReportsDashboard.tsx`, which currently appears empty and is not routed

Naming confusion:

- Product language says `folio/cashier`, while the current route and folder are named `finance`.
- `NAV_ITEMS` uses `/` for Dashboard while `App.tsx` redirects `/` to `/dashboard`; this should be checked before navigation refactors.

## Import Risks Before Refactor

Be careful with these areas before moving or renaming frontend files:

- `src/App.tsx` imports routed pages directly from module folders.
- Module pages import shared code with relative paths such as `../../services/...`, `../../context/...`, and `../../types/...`.
- API endpoint paths are hardcoded in service files, including `/frontdesk/*`, `/rooms/*`, `/finance/*`, `/reports/*`, `/kpi/*`, and `/health`.
- `financeService.ts` uses a local `fetch` helper and authorization header, while other services use the shared Axios `http` client.
- `src/types/pms.ts` includes a `finance` role but no `cashier` or `nightaudit` role yet.
- Renaming `finance` to `folio` without route aliases would break `/finance` links and imports.

## Safe Phased Frontend Refactor Plan

1. Confirm the active app.
   - Treat `guzo_pms_frontend` as the main PMS frontend.
   - Avoid changing older frontend folders in the same PR.

2. Stabilize route documentation.
   - Keep existing routes unchanged.
   - Document any planned aliases before adding them.

3. Plan naming before moving files.
   - Decide whether `finance` remains the technical module name or gradually becomes `folio` or `cashier`.
   - Preserve `/finance` until users and backend integrations are ready for a change.

4. Add missing modules only when scoped.
   - Add `nightaudit` and `booking` only after defining required backend endpoints and UI workflows.
   - Start with small routed pages or placeholders in a separate source-code PR.

5. Reduce import fragility.
   - Consider path aliases later if the project wants deeper module organization.
   - Avoid moving multiple modules in one change.

6. Normalize API services later.
   - Keep current service behavior unchanged first.
   - Later, consider moving `financeService` to the shared `http` client pattern.

7. Clean backups separately.
   - Review `.bak` and empty files in a dedicated cleanup PR.
   - Do not delete backup files during feature or route work.

## Checks Before Frontend Refactors

Before changing frontend source files:

```bash
cd guzo_pms_frontend
npm run build
npm run lint
```

There is no dedicated `typecheck` script in `guzo_pms_frontend/package.json` at the time of this review. Adding one would be a separate package-file change.
