"""
Hugging Face Space entry point (Gradio SDK).

The Space runs `python app.py` on port 7860. This serves the FastAPI backend
unchanged (/api/..., /health) and mounts a small Gradio status page on /ui.
"""
import os

import gradio as gr
import uvicorn

from src.main import app as api

with gr.Blocks(title="Todo Backend") as status_page:
    gr.Markdown(
        "# Todo Backend\n"
        "The API is running. Health check: [`/health`](/health) · API docs: [`/docs`](/docs)\n\n"
        "Set `NEXT_PUBLIC_API_BASE_URL` in the frontend to this Space's URL."
    )

# ssr_mode=False: with SSR (on by default in Spaces) Gradio starts a Node server
# on the first free port from 7860 while mounting, which then blocks uvicorn
app = gr.mount_gradio_app(api, status_page, path="/ui", ssr_mode=False)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
