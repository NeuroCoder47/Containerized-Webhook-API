<div align="center">

# 🔗 Lyftr AI — Containerized Webhook API

<img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
<img src="https://img.shields.io/badge/FastAPI-0.136+-green.svg" alt="FastAPI">
<img src="https://img.shields.io/badge/Docker-Compose-2496ED.svg" alt="Docker">
<img src="https://img.shields.io/badge/SQLite-Database-003B57.svg" alt="SQLite">
<img src="https://img.shields.io/badge/Tests-19%20Passing-success.svg" alt="Tests">

### *Production-style WhatsApp-like Message Inbox API*

[Overview](#-overview) •
[Quick Start](#-quick-start) •
[Endpoints](#-endpoints) •
[Design Decisions](#-design-decisions) •
[Setup Used](#-setup-used)

---

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=18&duration=3000&pause=1000&color=2E9EF7&center=true&vCenter=true&width=600&lines=Receive+Messages+via+Webhook;HMAC+Signature+Verification;Paginated+%2B+Filterable+API;Prometheus+Metrics+%2B+JSON+Logs;Runs+in+Docker+Compose" alt="Typing SVG" />

</div>

---

## 📖 Overview

A production-style FastAPI service that ingests inbound WhatsApp-like messages exactly once, validates HMAC-based signatures, stores them in SQLite, and exposes paginated search, analytics, Prometheus metrics, and structured JSON logs — all running inside Docker Compose.


## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running

### Run the app

```bash
make up
```

The API is now live at **http://localhost:8000**

### Stop the app

```bash
make down
```

### View live logs

```bash
make logs
```

### Run tests

```bash
make test
```

---

## 🔌 Endpoints

### POST /webhook — Receive a message

```bash
# Compute signature first
BODY='{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "testsecret" | awk '{print $2}')

curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIG" \
  -d "$BODY"
```

Response:
```json
{"status": "ok"}
```

---

### GET /messages — List messages

```bash
# Basic list
curl -s "http://localhost:8000/messages"

# With pagination
curl -s "http://localhost:8000/messages?limit=2&offset=0"

# Filter by sender
curl -s "http://localhost:8000/messages?from=%2B919876543210"

# Filter by date
curl -s "http://localhost:8000/messages?since=2025-01-15T09:30:00Z"

# Search by keyword
curl -s "http://localhost:8000/messages?q=Hello"
```

Response:
```json
{
  "data": [{"message_id": "m1", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T10:00:00Z", "text": "Hello"}],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### GET /stats — Analytics

```bash
curl -s "http://localhost:8000/stats"
```

Response:
```json
{
  "total_messages": 5,
  "senders_count": 2,
  "messages_per_sender": [{"from": "+919876543210", "count": 3}],
  "first_message_ts": "2025-01-15T09:00:00Z",
  "last_message_ts": "2025-01-15T12:00:00Z"
}
```

---

### GET /health/live — Liveness probe

```bash
curl -s "http://localhost:8000/health/live"
# {"status": "ok"}
```

---

### GET /health/ready — Readiness probe

```bash
curl -s "http://localhost:8000/health/ready"
# {"status": "ok"}  if DB connected and secret is set
# 503               otherwise
```

---

### GET /metrics — Prometheus metrics

```bash
curl -s "http://localhost:8000/metrics"
```

Response (plain text):
```
http_requests_total{path="/webhook",status="200"} 5
webhook_requests_total{result="created"} 3
webhook_requests_total{result="duplicate"} 2
request_latency_ms_bucket{le="100"} 5
```

---

## 🏗️ Design Decisions

### HMAC Signature Verification

Every incoming webhook request must include an `X-Signature` header containing `hex(HMAC_SHA256(WEBHOOK_SECRET, raw_body_bytes))`.

The server reads the raw request body bytes before any JSON parsing, computes its own HMAC using the same secret, and compares the two using `hmac.compare_digest()` — a constant-time comparison that prevents timing attacks. If they don't match, the request is rejected with 401 and nothing is written to the database.

### Pagination

`GET /messages` uses `limit` and `offset` query parameters. `limit` defaults to 50, min 1, max 100. `offset` defaults to 0. The `total` field in the response always reflects the full count of matching records for the given filters — not just the number returned on the current page. Ordering is always `ts ASC, message_id ASC` for deterministic results.

### Idempotency

The `messages` table uses `message_id` as a `PRIMARY KEY`. Before inserting, the app checks if that `message_id` already exists. If it does, it returns `200 {"status": "ok"}` without inserting a second row. This means sending the same message 10 times is identical to sending it once.

### Stats

`GET /stats` runs four SQL queries: `COUNT(*)` for total messages, `COUNT(DISTINCT from_msisdn)` for unique senders, `GROUP BY from_msisdn ORDER BY count DESC LIMIT 10` for top senders, and `MIN(ts) / MAX(ts)` for first and last timestamps. Returns nulls when no messages exist.

### Metrics

Counters are stored in Python `defaultdict(int)` in memory. Three counters are tracked: HTTP requests by path and status code, webhook outcomes by result type, and request latency buckets (100ms, 500ms, +Inf). These are formatted as Prometheus exposition text at `GET /metrics`.

### Structured JSON Logs

Every request produces one JSON log line with fields: `ts`, `level`, `request_id`, `method`, `path`, `status`, `latency_ms`. Webhook requests additionally include `message_id`, `dup`, and `result`. Logging is handled via Python's built-in `logging` module with a custom `JSONFormatter`.

---

## ⚙️ Environment Variables

| Variable | Description | Default |
|---|---|---|
| `WEBHOOK_SECRET` | HMAC signing secret — **required** | none |
| `DATABASE_URL` | SQLite file path | `sqlite:////data/app.db` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

## 📁 Project Structure

```
├── app/
│   ├── main.py          # FastAPI app, middleware, all routes
│   ├── models.py        # SQLite table initialisation
│   ├── storage.py       # All database operations
│   ├── config.py        # Environment variable loading
│   ├── logging_utils.py # JSON log formatter
│   └── metrics.py       # Prometheus counter helpers
├── tests/
│   ├── conftest.py      # Shared pytest fixtures
│   ├── test_webhook.py  # Webhook endpoint tests
│   ├── test_messages.py # Messages pagination + filter tests
│   └── test_stats.py    # Stats correctness tests
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── README.md
```

---

## 🛠️ Setup Used

Built using **VSCode** with **Claude (Anthropic)** as an AI coding assistant for guidance on FastAPI patterns, Docker configuration, and debugging. All code was written, reviewed, and understood by the author.

---

<div align="center">

**Built for Lyftr AI Backend Assignment 🚀**

</div>
