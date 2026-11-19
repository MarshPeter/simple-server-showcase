# ---- Stage 1: build the React frontend into static files ----
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime that serves the API and the static files ----
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
COPY --from=frontend /frontend/dist ./static

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
# 2 workers x 4 threads is far more than a classroom needs.
# Our own app logs each request, so gunicorn's access log is left off.
CMD ["sh", "-c", "exec gunicorn --workers 2 --threads 4 --bind 0.0.0.0:${PORT} --timeout 60 app:app"]
