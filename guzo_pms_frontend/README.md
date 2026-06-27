# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

## Guzo PMS Mobile / Tablet Visual QA

Run the responsive regression pass after frontend layout changes that touch PMS pages, tables, tabs, sidebars, topbars, filters, or action buttons.

Start the frontend first:

```bash
npm run dev -- --host 127.0.0.1 --port 5175
```

Then run the visual QA script in another terminal:

```bash
npm run responsive:qa
```

If the dev server is running on another port, pass the URL explicitly:

```bash
QA_BASE_URL=http://127.0.0.1:5173 npm run responsive:qa
```

The script saves screenshots and the JSON inspection report under:

```txt
screenshots/responsive-qa/
```

Tested viewport sizes:

- `390x844`
- `430x932`
- `768x1024`
- `1440x900`

Tested PMS routes:

- Dashboard
- Central Booking Hub
- Front Desk
- Reservations
- Housekeeping
- Finance
- Night Audit
- Reports
- Admin
- F&B Cost Control

The QA script checks for horizontal overflow, hidden/offscreen controls, clipped controls, and missing mobile table card labels from `DataTable` `data-label` values.

### Role-Based Mobile Workflow QA

`npm run responsive:qa` also runs a role workflow check at the mobile viewport. It signs in with each role, verifies allowed routes, verifies blocked routes redirect away, and checks key sensitive action buttons are visible or hidden.

Role scenarios:

- Admin
  - Visible routes: Dashboard, Central Booking Hub, Front Desk, Reservations, Housekeeping, Finance, Night Audit, Reports, Admin, F&B Cost Control.
  - Sensitive actions visible: booking conversion, deposit request, check-in/check-out, room status updates, payment posting, Night Audit controls, Admin user controls.

- Reservation Manager
  - Visible routes: Dashboard, Central Booking Hub, Front Desk, Reservations, Reports.
  - Blocked routes: Admin, Finance, Housekeeping, Night Audit, F&B Cost Control.
  - Sensitive actions visible: Booking Hub review, deposit request, reject, convert.
  - Sensitive actions blocked: check-in/check-out, room status updates, payment posting, Night Audit close, Admin user changes.

- Front Desk Agent
  - Visible routes: Dashboard, Front Desk, Reservations, Housekeeping, Finance, Reports.
  - Blocked routes: Admin, Central Booking Hub, Night Audit, F&B Cost Control.
  - Sensitive actions visible: room assignment, check-in, check-out, walk-in creation.
  - Sensitive actions blocked: booking conversion, room status updates, payment posting, Night Audit close, Admin user changes.
  - Finance is read-only for folio visibility unless the backend grants cashier permissions.

- Housekeeping
  - Visible routes: Dashboard, Housekeeping, Front Desk, Reports.
  - Blocked routes: Admin, Central Booking Hub, Finance, Night Audit, F&B Cost Control.
  - Sensitive actions visible: mark cleaned, mark inspected, room status override.
  - Sensitive actions blocked: booking conversion, check-in/check-out, payment posting, Night Audit close, Admin user changes.
  - Front Desk is read-only for arrivals/room-readiness coordination.

- Finance/Cashier
  - Visible routes: Dashboard, Finance, Reports, Night Audit, F&B Cost Control.
  - Blocked routes: Admin, Central Booking Hub, Front Desk, Housekeeping.
  - Sensitive actions visible: post charge and post payment.
  - Sensitive actions blocked: booking conversion, check-in/check-out, room status updates, Night Audit close, Admin user changes.
  - Night Audit is read-only unless the backend grants Night Audit close permissions.

- General Manager
  - Visible routes: Dashboard, Central Booking Hub, Front Desk, Reservations, Housekeeping, Finance, Night Audit, Reports, Admin, F&B Cost Control.
  - Sensitive actions visible: booking conversion, deposit request, check-in/check-out, room status updates, payment posting, Night Audit run/override, Admin user controls.

Backend enforcement remains the source of truth for sensitive actions. The frontend hides unauthorized buttons or shows read-only permission messages, while the backend records successful and blocked permission attempts in PMS audit logs.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
