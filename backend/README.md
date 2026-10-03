---
title: Todo Backend
emoji: ✅
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 6.29.1
python_version: "3.12"
app_file: app.py
pinned: false
---

# Todo Backend

FastAPI backend for the Todo app: auth, tasks with due dates, and the AI task
assistant. Runs as a Hugging Face Gradio Space: `app.py` serves the API and a
status page on `/ui`. See `DEPLOYMENT.md` in the main repository.

Required Space secrets: `DATABASE_URL` (Postgres, e.g. Neon), `SECRET_KEY`,
`OPEN_ROUTER_API_KEY`. Health check: `GET /health`.
