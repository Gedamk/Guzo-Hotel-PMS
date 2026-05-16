# AGENTS.md — Guzo PMS Instructions for Codex

## Project Mission
Guzo Guest Assist PMS is a production-grade hotel property management system inspired by global hotel PMS workflows. The system supports dashboard, reservations, front desk, housekeeping, folio/cashier, reports, admin, night audit, and guest booking flows.

## Safety Rules
- Do not delete files unless explicitly requested.
- Do not rewrite the whole project in one task.
- Do not commit secrets, API keys, tokens, database passwords, or real credentials.
- Use `.env.example` for sample environment variables.
- Prefer small pull requests.
- Preserve existing API behavior unless the task says otherwise.
- Explain every file changed.
- Run safe checks when possible.

## Backend
- Backend uses Python/FastAPI.
- Keep routes organized by hotel workflow area.
- Keep business logic in services, not directly inside route files.
- Keep database access clear and documented.
- Preserve existing endpoints unless specifically asked to refactor them.

## Frontend
- Frontend uses React, TypeScript, Vite, and TailwindCSS.
- Keep PMS modules organized by workflow:
  - dashboard
  - reservations
  - frontdesk
  - housekeeping
  - folio
  - reports
  - nightaudit
  - admin
  - booking
- Keep reusable UI components separate from page modules.
- Preserve imports and routes when moving files.
- Run `npm run build` or `npm run typecheck` when possible.

## Guzo PMS Workflow Priorities
- Arrivals
- Departures
- In-house guests
- No-shows
- Room assignment
- Check-in/check-out
- Folio charges/payments
- Housekeeping status
- Night audit
- Daily manager reporting
- Property-aware configuration
- Role-based access

## Expected Response
For each task, provide:
1. Summary of what changed
2. Files changed
3. Tests/checks run
4. Risks or follow-up work