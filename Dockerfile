# Enita: one image. FastAPI serves the API at /api and the Angular build at /.

# --- Stage 1: build the Angular frontend -------------------------------------
FROM node:24-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npx ng build

# --- Stage 2: Python backend --------------------------------------------------
FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/backend/.venv/bin:$PATH"

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/enita ./enita
RUN uv sync --frozen --no-dev

COPY content /app/content
COPY --from=frontend /app/frontend/dist/enita/browser /app/frontend/dist/enita/browser

RUN useradd --create-home enita && mkdir -p /app/backend/data && chown enita /app/backend/data
USER enita

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "enita.main:app", "--host", "0.0.0.0", "--port", "8000"]
