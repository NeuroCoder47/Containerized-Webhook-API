# Lyftr AI — Backend Thingy I Somehow Got Working

So… this is my very serious, totally professional backend API for the Lyftr assignment.  
In normal words: it’s a tiny inbox where “WhatsApp-ish” messages come in, I check if they’re fake using a secret, and if they pass, I save them into a SQLite database and then pretend this is “production-grade infrastructure”. [file:1]

It runs inside Docker so you don’t even need Python installed, just nerves of steel and Docker Desktop. [file:1]

---

## How to Run This Without Crying

**Prerequisites:**

- Docker Desktop running
- `make` installed
- Basic faith in copy–paste

**Start the app:**

```bash
make up
```

If nothing explodes, the API should be available at:

- http://localhost:8000

**Shut it down:**

```bash
make down
```

**See what it’s doing (or breaking):**

```bash
make logs
```

**Run tests (they passed on my machine, which is legally binding):**

```bash
make test
```

---

## What This Backend Actually Does

Think of it as a filtered message inbox:

1. Messages arrive at a `/webhook` endpoint. [file:1]  
2. Each message has a signature header (`X-Signature`) that is validated using HMAC-SHA256 and a secret (`WEBHOOK_SECRET`). [file:1]  
3. If the signature is valid and the payload is correct, the message is stored in SQLite. [file:1]  
4. You can then:
   - List messages with filters and pagination via `/messages`. [file:1]
   - Get simple stats via `/stats`. [file:1]
   - Check health with `/health/live` and `/health/ready`. [file:1]
   - Scrape metrics for Prometheus via `/metrics`. [file:1]

All of this is wrapped in FastAPI and containerized with Docker Compose. [file:1]

---

## Main Endpoints (Human-Level Summary)

### 1. `POST /webhook` — Messages Enter Here

- Accepts JSON with fields like:
  - `message_id`
  - `from`
  - `to`
  - `ts` (ISO-8601 UTC)
  - `text` (optional) [file:1]
- Requires:
  - Header `X-Signature`: HMAC-SHA256 of the **raw** request body using `WEBHOOK_SECRET`. [file:1]
- Behavior:
  - If signature is missing or invalid → returns `401` and does **not** save anything. [file:1]
  - If payload is invalid → returns `422`, no DB insert. [file:1]
  - If valid and new `message_id` → inserts into DB and returns `{"status": "ok"}`. [file:1]
  - If valid but `message_id` already exists → returns `{"status": "ok"}` but does not insert again (idempotent). [file:1]

In short: “Only real, well-formed messages get in, and only once.”

---

### 2. `GET /messages` — Browse Stored Messages

- Supports:
  - `limit` (default 50, max 100)
  - `offset` (default 0)
  - `from` (filter by sender)
  - `since` (only messages after a timestamp)
  - `q` (simple substring search in `text`) [file:1]
- Always ordered by:
  - `ts` ascending
  - `message_id` ascending [file:1]
- Response contains:
  - `data`: list of messages
  - `total`: total matching rows for the filters (ignores pagination)
  - `limit`
  - `offset` [file:1]

So you can paginate and still know how many total messages match your filters.

---

### 3. `GET /stats` — Simple Message Analytics

Returns a JSON summary like: [file:1]

- `total_messages`: total number of messages
- `senders_count`: number of unique senders
- `messages_per_sender`: up to top 10 senders with counts
- `first_message_ts`: earliest message timestamp or `null`
- `last_message_ts`: latest message timestamp or `null` [file:1]

These are computed with a few SQL queries over the `messages` table. [file:1]

---

### 4. Health Checks

- `GET /health/live`  
  - Just confirms the app is running and able to respond. Always returns 200 once the app is up. [file:1]

- `GET /health/ready`  
  - Returns 200 **only if**:
    - The database is reachable and schema is applied
    - `WEBHOOK_SECRET` is set  
  - Otherwise returns 503. [file:1]

This lets something like Kubernetes know when the app is actually ready and not just “technically alive”.

---

### 5. `GET /metrics` — Prometheus Metrics

- Exposes text-based metrics in Prometheus exposition format. [file:1]
- Includes:
  - A counter for total HTTP requests with labels like `path` and `status`
  - A counter for webhook outcomes (`created`, `duplicate`, `invalid_signature`, etc.)
  - Some latency bucket metrics [file:1]
- Metrics are tracked in memory using Python dictionaries and updated by middleware on each request. [file:1]

---

## Design Decisions (Yes, There Was Some Thought)

### HMAC Signature Verification

- Reads the raw request body bytes.  
- Uses Python’s `hmac` library with `WEBHOOK_SECRET` to compute an HMAC-SHA256 hex digest. [file:1]  
- Compares it to `X-Signature` using `hmac.compare_digest` for constant-time comparison. [file:1]  
- If they differ → 401, no DB insert, error log entry. [file:1]

This ensures only callers with the shared secret can successfully post messages.

### Pagination Contract

- `limit`: default 50, max 100, minimum 1  
- `offset`: default 0, minimum 0 [file:1]  
- `total` in the response always refers to *all* matching rows for that filter, not just the current page. [file:1]  
- Messages are always ordered by `ts` then `message_id` for deterministic results. [file:1]

### Stats Implementation

- Uses a small set of SQL queries:
  - Count all messages
  - Count distinct senders
  - Group by sender and sort by count (top 10)
  - Get MIN and MAX timestamps [file:1]
- If no messages exist, first and last timestamps are `null`. [file:1]

### Metrics Implementation

- Uses in-memory `defaultdict(int)` to track counters. [file:1]  
- Middleware wraps each request to record:
  - Request counts
  - Status codes
  - Webhook outcome labels
  - Latency buckets [file:1]
- `/metrics` formats these into Prometheus-style lines. [file:1]

---

## Configuration via Environment Variables

The app is configured using environment variables (12-factor style): [file:1]

- `WEBHOOK_SECRET`  
  - Required  
  - Used for HMAC validation  
  - If not set, the app will never be “ready” (health/ready fails). [file:1]

- `DATABASE_URL`  
  - Default: `sqlite:////data/app.db`  
  - Points to the SQLite DB file (mounted via Docker volume). [file:1]

- `LOG_LEVEL`  
  - Default: `INFO`  
  - Controls logging verbosity. [file:1]

---

## Project Structure

```text
├── app/
│   ├── main.py          # FastAPI app, routes, middleware
│   ├── models.py        # SQLite table definitions
│   ├── storage.py       # DB read/write helpers
│   ├── config.py        # Environment variable loading
│   ├── logging_utils.py # JSON logging helpers
│   └── metrics.py       # Metrics helpers
├── tests/
│   ├── conftest.py
│   ├── test_webhook.py
│   ├── test_messages.py
│   └── test_stats.py
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── README.md
```

This matches the deliverables expected in the assignment description. [file:1]

---

## Tech Stack & Tools Used

- **Language:** Python (3.11+) [file:1]  
- **Framework:** FastAPI (async, modern, mildly intimidating at first) [file:1]  
- **Database:** SQLite (file-based, stored in a Docker volume) [file:1]  
- **Containerization:** Docker & Docker Compose [file:1]  
- **Config:** Environment variables (`WEBHOOK_SECRET`, `DATABASE_URL`, `LOG_LEVEL`) [file:1]  
- **Logging:** Structured JSON logs, one line per request, including fields like `ts`, `level`, `request_id`, `method`, `path`, `status`, `latency_ms`, and for webhooks, `message_id`, `dup`, and `result`. [file:1]

For development, a code editor (VSCode) and an AI assistant were used to better understand FastAPI, Docker, and HMAC, but all logic and structure were implemented and understood by the developer. [file:1]

---

If you were a hiring manager reading this README, what part would you say still feels *too* senior/over-polished for an “entry-level” voice and should be simplified or made more naive?
</div>
