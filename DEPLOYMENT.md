# Deployment Guide

The backend (FastAPI + Postgres) runs on **Render**, the frontend (Next.js) on **Vercel**.
Deploy the backend first, because the frontend needs its URL.

## 1. Backend on Render

1. Sign in at https://render.com with GitHub.
2. **New → Blueprint**, pick this repository. Render reads `render.yaml` from the repo
   root and creates:
   - `todo-backend`, a web service built from `backend/`
   - `todo-db`, a free Postgres database, wired in as `DATABASE_URL`
   - `SECRET_KEY`, generated automatically (signs login tokens)
3. When asked for `OPEN_ROUTER_API_KEY`, paste your OpenRouter key.
4. Wait for the deploy to finish, then open `https://<your-service>.onrender.com/health`.
   It should return `{"status": "healthy", ...}`. Copy this base URL.

Free-plan notes: the service sleeps after ~15 minutes idle, so the first request can
take about a minute. A free Render database expires after 30 days; for a lasting
database, create one at https://neon.tech and set its URL as `DATABASE_URL` instead.

## 2. Frontend on Vercel

1. Sign in at https://vercel.com with GitHub. **Add New → Project**, import this repository.
2. Set **Root Directory** to `frontend`. Framework preset: Next.js (detected).
3. Add the environment variable:

   | Name | Value |
   |------|-------|
   | `NEXT_PUBLIC_API_BASE_URL` | Your Render URL, e.g. `https://todo-backend-xxxx.onrender.com` (no trailing slash) |

4. Deploy. You'll get a URL like `https://<project>.vercel.app`.
5. To share it publicly: Project → Settings → Deployment Protection → turn off
   **Vercel Authentication**. Otherwise visitors must log in to Vercel.

`NEXT_PUBLIC_*` values are baked in at build time. After changing one, redeploy.

## Environment variables

### Backend (Render)
| Variable | Value | Set by |
|----------|-------|--------|
| `DATABASE_URL` | Postgres connection string | Blueprint (from `todo-db`) |
| `SECRET_KEY` | Random string | Blueprint (generated) |
| `OPEN_ROUTER_API_KEY` | Your OpenRouter key | You, in the Render dashboard |
| `OPEN_ROUTER_URL` | `https://openrouter.ai/api/v1` | Blueprint |
| `OPEN_ROUTER_MODEL` | Optional, default `openai/gpt-4o-mini` | You (optional) |

### Frontend (Vercel)
| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend base URL |

## Check after deploying

1. Open the Vercel URL, register an account and log in.
2. Add a task with a due date from the form; it shows a countdown.
3. In the assistant panel: `add a task pay rent on coming tuesday`, then
   `make it 9am`, then `delete the rent task`. The list updates each time,
   without duplicates.

## Troubleshooting

- **"Could not load your tasks" / network errors:** `NEXT_PUBLIC_API_BASE_URL` is
  missing or wrong, or the backend is still waking up. Check `/health` on Render,
  fix the variable in Vercel and redeploy.
- **Chat replies but never changes tasks:** `OPEN_ROUTER_API_KEY` is not set on
  Render, so the simple fallback parser is used. Check the Render logs.
- **Logged out after redeploying the backend:** expected if `SECRET_KEY` changed;
  log in again.
