# Webhook Processor Service (FastAPI + MongoDB + Redis/RQ)

## Overview

This service receives transaction webhooks from an external payment provider (e.g. Razorpay), acknowledges them immediately with HTTP 202, and processes them asynchronously in a background worker.

Why this matters:

- Payment gateways retry webhooks and expect a super-fast 2xx response.
- You _must not_ block that response while doing heavy work like settlement, reconciliation, downstream API calls, etc.
- You _must_ handle duplicate webhooks safely (idempotency).

This backend solves that.

---

## Features

### Endpoints

- `GET /`
  Health check. Returns `{ "status": "HEALTHY", "current_time": "<UTC_ISO8601>" }`
- `POST /v1/webhooks/transactions`
  Primary webhook receiver.

  - Validates and persists the transaction in MongoDB with status `"RECEIVED"`.
  - Enqueues a background job in Redis/RQ.
  - Returns **HTTP 202 Accepted** in under ~500ms.

- `GET /v1/transactions/{transaction_id}`
  Returns the live status:

  ```json
  {
    "transaction_id": "txn_abc123",
    "source_account": "acc_user_789",
    "destination_account": "acc_merchant_456",
    "amount": 1500,
    "currency": "INR",
    "status": "PROCESSED",
    "created_at": "2025-10-29T10:30:00Z",
    "processed_at": "2025-10-29T10:30:30Z"
  }
  ```

Possible `status` values:

- `"RECEIVED"` → saved, waiting to process
- `"PROCESSING"` → worker claimed it
- `"PROCESSED"` → finished successfully

### Background worker

- We run an RQ worker connected to Redis.
- The worker:

  1. Atomically flips status from `RECEIVED` → `PROCESSING` in MongoDB.
  2. Sleeps 30 seconds to simulate expensive external calls (like confirming with a payment gateway).
  3. Updates status to `PROCESSED` and sets `processed_at`.

### Idempotency

We guarantee that repeated webhooks with the same `transaction_id` do _not_ create duplicates or re-run the job:

1. **MongoDB unique index** on `transaction_id` means first insert wins, subsequent inserts with the same ID are ignored.
2. We enqueue the RQ job with `job_id = transaction_id`. RQ will refuse to enqueue a second job with the same ID.
3. The worker uses a conditional update (`status == "RECEIVED"`) to take ownership. If it’s already `"PROCESSING"` or `"PROCESSED"`, it no-ops.

This matches real-world payment gateway behavior (gateways often retry webhooks; you must handle duplicates safely).

---

## Tech Choices

- **FastAPI**: async-friendly, fast, great request validation + auto docs.
- **MongoDB Atlas (M0 Free Tier)**: persistent transaction store.
  Atlas’ M0 tier is “Free Forever,” ~512MB storage, shared RAM/CPU, meant for prototyping and dev, and runs in the cloud. (Refs: MongoDB Atlas “Free Forever” / M0 sandbox, ~512MB storage and shared compute, marketed for learning and prototyping.) [Sources: MongoDB pricing pages and docs as of Oct 29, 2025, which describe M0 as free forever with ~512MB storage and shared resources.]
- **Redis + RQ**: queue system for async processing.

  - Redis stores jobs
  - RQ worker pulls jobs and runs long-running work outside the request/response path

- **Render**: deployment target

  - Free web service tier with 750 free instance-hours/month per workspace, can spin down when idle and wake on traffic
  - Free/low-cost Redis-like service for queues
  - Background Worker service to run RQ in production
    (Sources: Render free tier docs as of Oct 29, 2025, which describe 750 free instance hours/month, automatic spin-down after 15 minutes idle, and a “Hobby/Free” style plan for personal projects.)

---

## Project Structure

```text
app/
  main.py                     # FastAPI app
  api/routes.py               # All routes (/, /v1/webhooks/transactions, /v1/transactions/{id})
  core/config.py              # Env config (Mongo URL, Redis URL, delay seconds)
  db/mongo.py                 # Mongo client + unique index on transaction_id
  repository/transactions.py  # DB logic (create/get/update with idempotency)
  queues/redis_conn.py        # Redis connection + RQ Queue
  queues/tasks.py             # enqueue helper (q.enqueue(...))
  workers/processor.py        # the background job (30s delay, status transitions)
  schemas/transaction.py      # Pydantic models

Dockerfile
docker-compose.yml
render.yaml
requirements.txt
.env.example
README.md
```

---

## How To Run Locally (Docker)

Requirements:

- Docker Desktop running

Then:

```bash
docker compose up --build
# or: docker-compose up --build
```

This will start 4 containers:

- `api` → FastAPI app on [http://localhost:8000](http://localhost:8000)
- `worker` → RQ background worker
- `mongo` → MongoDB
- `redis` → Redis

Environment values inside those containers are already configured so `api` talks to `mongo` and `redis`, and `worker` talks to both.

### Test locally

1. Health:

   ```bash
   curl http://localhost:8000/
   ```

2. Send a fake webhook:

   ```bash
   curl -X POST http://localhost:8000/v1/webhooks/transactions \
     -H "Content-Type: application/json" \
     -d '{
       "transaction_id": "txn_demo_123",
       "source_account": "acc_user_789",
       "destination_account": "acc_merchant_456",
       "amount": 1500,
       "currency": "INR"
     }'
   ```

   Expected `202 Accepted` and body like:

   ```json
   {
     "accepted": true,
     "transaction_id": "txn_demo_123",
     "status": "RECEIVED"
   }
   ```

3. Immediately check:

   ```bash
   curl http://localhost:8000/v1/transactions/txn_demo_123
   ```

   You’ll see `"status": "RECEIVED"`.

4. After ~30 seconds:

   ```bash
   curl http://localhost:8000/v1/transactions/txn_demo_123
   ```

   You’ll now see `"status": "PROCESSED"` and a `processed_at` timestamp.

5. Re-send the same webhook again (same `transaction_id`).
   You’ll still get 202, but DB and processing won’t duplicate, proving idempotency.

---

## How To Run Locally (manual / venv dev mode)

1. Create venv and install deps:

   ```bash
   python3.11 -m venv .venv
   source .venv/Scripts/activate # for windows
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. Run Redis + Mongo via Docker:

   ```bash
   docker run --name redis-local -p 6379:6379 -d redis:7
   docker run --name mongo-local -p 27017:27017 -d mongo:7
   ```

3. Export env vars:

   ```bash
   export MONGO_URL="mongodb://localhost:27017"
   export MONGO_DB="webhooks_db"
   export REDIS_URL="redis://localhost:6379/0"
   export PROCESS_DELAY_SECONDS=30
   ```

4. Run API:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. In a second terminal (same venv & env vars):

   ```bash
   rq worker -u redis://localhost:6379/0 transactions
   ```

---

## Deployment (Render)

### 1. Create a free MongoDB Atlas cluster

- Go to MongoDB Atlas → Create new cluster → choose **M0 (Free Forever)** tier.
- M0 gives ~512MB storage, shared RAM/CPU, and is designed for learning / prototypes at $0. (Source: MongoDB Atlas pricing info as of Oct 29, 2025.)
- Create a database user + password.
- Whitelist your IP(s).
- Copy your connection string, e.g.
  `mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/webhooks_db`

### 2. Push this repo to GitHub (public for the interview)

Include:

- all source code
- `Dockerfile`
- `docker-compose.yml`
- `render.yaml`
- `.env.example` (no secrets)
- this README.md

### 3. Render setup

1. Log into Render.

2. Create a new Redis / Key-Value service (free tier is allowed for personal/small projects; it's intended for hobby/testing workloads and counts against free hours).

3. Connect your GitHub repo as a “Blueprint deploy” using `render.yaml`.

4. For both the `webhook-api` service and the `webhook-worker` service in Render:

   - Add the following environment variables:

     - `MONGO_URL` = your Atlas URI
     - `MONGO_DB` = `webhooks_db`
     - `REDIS_URL` = the Redis URL Render shows you, e.g. `redis://:password@host:6379/0`
     - `PROCESS_DELAY_SECONDS` = `30`

   Render’s free web services get 750 free instance-hours/month and will spin down after 15 minutes idle, then spin back up when hit. (Source: Render free tier docs as of Oct 29, 2025.) The worker may or may not allow `plan: free`; if not, pick the lowest-cost Hobby worker.

5. Deploy.

### 4. After deploy

- You’ll get a public URL like `https://webhook-api-xxxx.onrender.com`.
- `GET /` should return `{ "status": "HEALTHY", ... }`.
- `GET /docs` should open FastAPI Swagger docs.
- You can `POST /v1/webhooks/transactions` to simulate Razorpay webhook calls.
- The background worker will be running in Render and will update MongoDB Atlas after ~30 seconds.

This URL is what you send to:

- Interviewer
- (Later) Razorpay’s “Webhook URL” field

---

## Razorpay-style webhook hookup

In Razorpay Dashboard:

- Go to Settings → Webhooks → Add New Webhook
- Webhook URL = `https://<your-render-url>/v1/webhooks/transactions`
- Secret = (random string you generate and store in an env var later for signature verification)
- Choose the events you want Razorpay to send

Razorpay will POST JSON to that URL; our service will:

- save it (`status="RECEIVED"`)
- enqueue it
- respond `202 Accepted`

---

## Environment Variables

In local `.env.example` we show how to configure:

```env
MONGO_URL=mongodb://mongo:27017
MONGO_DB=webhooks_db
REDIS_URL=redis://redis:6379/0
PROCESS_DELAY_SECONDS=30
```

In production (Render), you’ll override:

```text
MONGO_URL=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/webhooks_db
REDIS_URL=redis://:<password>@<render-redis-host>:6379/0
```

**Do not commit real credentials.** Add them in Render’s dashboard under Environment.

---

## What to show the interviewer

1. This README.md (so they understand architecture + how to run it).
2. The running Render URL (so they can curl it live).
3. The GitHub repo link with:

   - code
   - docker-compose.yml (local reproduction)
   - render.yaml (infra-as-code)
   - .env.example (so they know which env vars matter)

This proves:

- You designed for async processing and availability.
- You handled idempotency properly.
- You thought about real deployment (Redis queue, worker process, free-tier infra).
- You documented it well enough that someone else can spin it up quickly.

---

## Contact / Notes

If this is being reviewed:

- Please start with `docker compose up --build` and test `/v1/webhooks/transactions`.
- Then review `app/workers/processor.py` + `app/repository/transactions.py` to see the idempotency logic.
- Finally, open `render.yaml` to see how this ships to Render in a free/hobby-friendly way.
