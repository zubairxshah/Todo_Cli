---
title: Todo Backend
emoji: ✅
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Todo Backend

FastAPI backend for the Todo app: auth, tasks with due dates, and the AI task
assistant. Deployed as a Hugging Face Docker Space; see `DEPLOYMENT.md` in the
main repository.

Required Space secrets: `DATABASE_URL` (Postgres, e.g. Neon), `SECRET_KEY`,
`OPEN_ROUTER_API_KEY`. Health check: `GET /health`.
