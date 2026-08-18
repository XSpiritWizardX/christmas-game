# Build the React/Vite client once, then serve it from the Python web process.
FROM node:20-alpine AS client-build

WORKDIR /app/client
COPY client/package.json client/package-lock.json ./
RUN npm ci
COPY client/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r ./server/requirements.txt

COPY server/ ./server/
COPY web.py ./web.py
COPY --from=client-build /app/client/dist ./client/dist

# SQLite is only a local/fallback option. Production should set DATABASE_URL.
RUN mkdir -p /app/server/instance \
    && useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 10000

CMD ["sh", "-c", "exec gunicorn --worker-class eventlet --workers 1 --bind 0.0.0.0:${PORT:-10000} web:app"]
