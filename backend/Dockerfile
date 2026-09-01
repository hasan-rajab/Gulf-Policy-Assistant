FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system nexus \
    && useradd --system --gid nexus --create-home nexus

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=nexus:nexus app ./app
COPY --chown=nexus:nexus scripts ./scripts
COPY --chown=nexus:nexus tests ./tests
RUN mkdir -p /app/data && chown -R nexus:nexus /app/data

USER nexus
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl --fail http://127.0.0.1:8080/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
