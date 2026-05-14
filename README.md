# Lyftr AI — Backend Assignment

This is a small FastAPI backend that receives WhatsApp-like messages via a webhook, saves them into SQLite, and exposes a few endpoints to list them, see stats, and check health.

## How to Run

Requirements:

- Docker and Docker Compose installed
- `make` available

Start the app:

```bash
make up
```

The API will be available at:

- http://localhost:8000

To stop it:

```bash
make down
```

## Endpoints (How to Hit Them)

- `POST /webhook`  
  Receives a message JSON body.  
  Requires `X-Signature` header with HMAC-SHA256 of the raw body using `WEBHOOK_SECRET`.  
  On success returns: `{"status": "ok"}`.

- `GET /messages`  
  Lists stored messages with pagination and basic filters.  
  Query params:
  - `limit` (default 50, max 100)
  - `offset` (default 0)
  - `from` (filter by sender)
  - `since` (timestamp filter)
  - `q` (search in `text`)

- `GET /stats`  
  Returns total messages, number of senders, messages per sender (top 10), and first/last message timestamps.

- `GET /health/live`  
  Simple liveness check.

- `GET /health/ready`  
  Readiness check that only returns 200 when DB is reachable and `WEBHOOK_SECRET` is set.

- `GET /metrics` (optional but implemented)  
  Returns Prometheus-style metrics text with HTTP request counters and webhook outcome counters.

## Design Decisions (Brief)

### HMAC Verification

For `/webhook`, the app reads the raw request body bytes and computes an HMAC-SHA256 hex digest using the `WEBHOOK_SECRET` environment variable. It compares this to the `X-Signature` header using `hmac.compare_digest`. If it does not match, it returns 401 and does not insert anything into the database.

### Pagination

`GET /messages` supports `limit` and `offset` query parameters. `limit` defaults to 50 and is capped at 100. `offset` defaults to 0. Messages are always ordered by `ts` ascending and then `message_id` ascending. The response includes `total`, which is the total number of rows that match the filters, not just the number in the current page.

### Stats and Metrics

The `/stats` endpoint uses simple SQL queries to compute total messages, number of unique senders, messages per sender (top 10), and the first/last message timestamps.  
The `/metrics` endpoint keeps in-memory counters (using Python dictionaries) that are updated on each request and then exposed in Prometheus text format, including a counter for total HTTP requests and a counter for webhook outcomes.

## Setup Used

Developed with VSCode and Docker. Claude AI assistant was used occasionally to understand FastAPI, Docker, and HMAC, but the code and logic were implemented and understood by me.
