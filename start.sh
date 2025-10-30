#!/usr/bin/env bash
set -e
# 1) start the RQ worker in the background
rq worker -u "$REDIS_URL" transactions &
# 2) start FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
