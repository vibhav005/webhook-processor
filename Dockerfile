# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps (optional: useful for pymongo SSL etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY .env.example ./.env.example

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command is the API server.
# Worker will override this in docker-compose / render.yaml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]
