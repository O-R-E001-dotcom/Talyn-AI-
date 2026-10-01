# Talyn AI coach — FastAPI wrapper around the Anthropic API.
#
# Holds ANTHROPIC_API_KEY and TALYN_BACKEND_URL. The browser never talks to
# this service with anything but a backend JWT.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /wheels
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /usr/sbin/nologin --uid 10002 app

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY --chown=app:app app ./app

USER app

EXPOSE 8001

# Honors $PORT (Render and friends inject it; default 8001 keeps the local
# compose setup working unchanged).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT:-8001}/health || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app \
      --host 0.0.0.0 --port ${PORT:-8001} \
      --proxy-headers --forwarded-allow-ips '*' \
      --no-server-header"]
