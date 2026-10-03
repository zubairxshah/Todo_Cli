# Backend image. Works on Hugging Face Spaces (Docker SDK, port 7860, uid 1000)
# and anywhere else that sets $PORT.
FROM python:3.12-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user src/ ./src/

EXPOSE 7860

# Shell form so $PORT is expanded
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT}
