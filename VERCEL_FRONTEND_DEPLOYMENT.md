# Guzo PMS Vercel Frontend Deployment

Deploy only the React/Vite frontend on Vercel. The FastAPI backend is already deployed on Render.

## Vercel Project Settings

| Setting | Value |
|---|---|
| Root Directory | `guzo_pms_frontend` |
| Framework Preset | `Vite` |
| Install Command | `npm install` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

## Environment Variables

Set this in the Vercel dashboard:

```text
VITE_API_BASE_URL=https://guzo-hotel-pms-api.onrender.com
```

Do not add backend secrets, database URLs, admin tokens, `.env` files, credentials, backups, generated `dist`, or local backup folders to Vercel or GitHub.

## Existing Frontend Routing

`guzo_pms_frontend/vercel.json` contains the SPA fallback needed for React routes:

```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```
