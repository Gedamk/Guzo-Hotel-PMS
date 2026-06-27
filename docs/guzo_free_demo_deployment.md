# Guzo Hotel PMS Free/Demo Deployment

This guide deploys Guzo Hotel PMS with a low-cost demo stack:

- Frontend: Vercel Hobby
- Backend: Render free Web Service
- Database: Render PostgreSQL free/demo
- Repository: https://github.com/Gedamk/Guzo-Hotel-PMS

Do not commit real credentials, `.env` files, service-account JSON files, local backup folders, screenshots, or generated build output.

## Deployment Shape

| Service | Platform | Root / Start |
|---|---|---|
| Frontend | Vercel Hobby | Root: `guzo_pms_frontend`; Build: `npm run build`; Output: `dist` |
| Backend | Render Web Service | Start: `uvicorn guzo_backend.main:app --host 0.0.0.0 --port $PORT` |
| Database | Render PostgreSQL | Use Render's internal database URL as `DATABASE_URL` |

## Render PostgreSQL

1. In Render, create a PostgreSQL database.
2. Use the free/demo plan if available for the environment.
3. Copy the internal database URL.
4. Add it to the backend Render Web Service as `DATABASE_URL`.
5. Do not paste database credentials into GitHub, docs, screenshots, issue comments, or committed files.

The repo also includes a safe `render.yaml` blueprint. It can create the demo PostgreSQL database and backend Web Service without storing secret values in Git. Any `sync: false` value must still be entered directly in Render.

## Render Backend Web Service

Create a Render Web Service from the GitHub repo.

Recommended settings:

| Setting | Value |
|---|---|
| Repository | `https://github.com/Gedamk/Guzo-Hotel-PMS` |
| Branch | `main` |
| Runtime | Python |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn guzo_backend.main:app --host 0.0.0.0 --port $PORT` |

After the backend deploys, run database migrations from a safe one-off Render shell or job:

```bash
alembic upgrade head
```

If Render's shell does not automatically expose the same environment as the service, confirm `DATABASE_URL` is present before running migrations.

## Backend Environment Variables

Required for the Render backend:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | Render PostgreSQL internal URL. Keep secret. |
| `SECRET_KEY` | Yes | Strong random app secret for production/demo platform config. Keep secret. |
| `ADMIN_TOKEN` | Yes for admin/demo automation | Strong random admin token. Keep secret. |
| `GUZO_JWT_SECRET` | Yes | Generate a strong random value. Keep secret. |
| `GUZO_DEFAULT_ADMIN_PASSWORD` | Yes for initial demo login | Use a temporary strong password, then change it. |
| `ENVIRONMENT` | Recommended | Use `production`. |
| `ADMIN_API_TOKEN` | Optional legacy endpoints | Strong random token if legacy admin endpoints are used. |
| `GUZO_SIMPLE_ADMIN_TOKEN` | Optional legacy endpoints | Strong random token if simple-token endpoints are used. |
| `GUZO_API_ADMIN_TOKEN` | Optional legacy endpoints | Strong random token if legacy API auth is used. |
| `GUZO_REPORTS_ADMIN_TOKEN` | Optional reports router | Strong random token if reports router is used. |
| `REPORTS_API_TOKEN` | Optional reports API | Strong random token if reports API is used. |

Optional integrations:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | AI/assistant features |
| `SENDGRID_API_KEY` | Email delivery |
| `DEFAULT_SENDER_EMAIL` | Email sender |
| `REPLY_TO_EMAIL` | Email replies |
| `TELEGRAM_BOT_TOKEN` | Telegram bot |
| `TELEGRAM_CHAT_ID` | Telegram alerts |
| `TWILIO_ACCOUNT_SID` | SMS/WhatsApp |
| `TWILIO_AUTH_TOKEN` | SMS/WhatsApp |
| `TWILIO_PHONE_NUMBER` | SMS/WhatsApp |
| `CHAPA_PUBLIC_KEY` | Payments |
| `CHAPA_SECRET_KEY` | Payments |
| `CHAPA_WEBHOOK_SECRET` | Payment webhooks |
| `STRIPE_API_KEY` | Payments |
| `STRIPE_WEBHOOK_SECRET` | Payment webhooks |
| `OPENWEATHER_API_KEY` | Weather integration |

For demo deployment, leave optional integrations unset unless you are actively testing them.

## Vercel Frontend

Create a Vercel project from the same GitHub repo.

Required Vercel settings:

| Setting | Value |
|---|---|
| Framework Preset | Vite |
| Root Directory | `guzo_pms_frontend` |
| Install Command | default |
| Build Command | `npm run build` |
| Output Directory | `dist` |

Frontend environment variables:

| Variable | Required | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | Yes | Render backend URL, for example `https://your-render-service.onrender.com`. |
| `VITE_DEV_AUTH_FALLBACK` | Demo only | Use `false` for production-like demos. |
| `VITE_PROPERTY_CODE` | Recommended | Demo default: `DRE001`. |
| `VITE_PROPERTY_NAME` | Recommended | Demo property display name. |
| `VITE_PMS_USER_EMAIL` | Demo only | Demo user email if dev fallback is enabled. |
| `VITE_AUTH_TOKEN` | Legacy only | Leave unset unless old token-based endpoints are required. |

Do not put server-only secrets into Vercel `VITE_*` variables. Anything prefixed with `VITE_` is visible in the browser bundle.

## CORS And URLs

After Vercel deploys, copy the Vercel production URL and allow it in backend CORS settings if the backend enforces explicit origins.

Expected URL flow:

1. Browser opens Vercel frontend.
2. Frontend calls `VITE_API_BASE_URL`.
3. Render backend connects to Render PostgreSQL using `DATABASE_URL`.

## Post-Deploy Smoke Test Checklist

Run these checks after each deployment:

1. Backend health:
   - Open `https://your-render-service.onrender.com/health`.
   - Expect HTTP 200 and a healthy JSON response.
2. Login:
   - Open the Vercel frontend.
   - Log in with the demo admin account.
   - Change any temporary default password before sharing the demo.
3. Dashboard:
   - Confirm dashboard KPIs load.
   - Confirm selected property and business date display.
4. Reservations:
   - Open Reservations.
   - Create or review a demo reservation.
   - Confirm guest profile links are visible.
5. Front Desk:
   - Confirm arrivals/in-house/departures load.
   - Test room assignment or check-in on demo data.
6. Housekeeping:
   - Confirm room board loads.
   - Mark a demo room clean/inspected/dirty.
7. Finance / Folio:
   - Open folio.
   - Post a demo charge/payment only on demo data.
8. Night Audit:
   - Run validation first.
   - Confirm open folio, departure, and cashier exceptions are understandable.
   - Do not hard-close a live property date unless authorized.
9. Reports:
   - Confirm manager reports load.
   - Confirm exported files do not contain test secrets.

## Security Checklist Before Sharing Demo

- Rotate/revoke any previously exposed OpenAI, Google, Gmail, and demo bearer credentials.
- Confirm GitHub does not contain `.env`, credentials, backups, or local backup folders.
- Confirm Render and Vercel environment variables contain real secrets only in their dashboards.
- Confirm `.env.example` contains placeholders only.
- Confirm database contains demo or approved data only.
- Confirm the local `_local_backup/secret_history_cleanup` folder is never uploaded.

## Safe Update Workflow

Before pushing deployment changes:

```bash
git status
git ls-files | grep -i "_local_backup\|secret_history_cleanup\|credentials\|service_account\|backups\|\.env"
```

Only `.env.example` should appear from that grep.

Then run:

```bash
venv\Scripts\python.exe -m pytest tests -q
cd guzo_pms_frontend
npm run typecheck
npm run build
```

Push only after the history/current-tree secret scans and tests pass.
