from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, ValidationError, validator
import hmac
import hashlib
import uuid
import time
import json
import re

from app.config import WEBHOOK_SECRET
from app.models import init_db
from app.storage import (
    message_exists,
    insert_message,
    get_messages,
    get_stats,
    get_connection,
)
from app.logging_utils import logger
from app.metrics import record_request, record_webhook_result, generate_metrics_text

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()


PHONE_REGEX = re.compile(r"^\+\d+$")
TS_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


class WebhookMessage(BaseModel):
    message_id: str
    from_msisdn: str = Field(alias="from")
    to_msisdn: str = Field(alias="to")
    ts: str
    text: str = None

    class Config:
        populate_by_name = True

    @validator("message_id")
    def message_id_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("message_id must not be empty")
        return v

    @validator("from_msisdn", "to_msisdn")
    def phone_must_be_valid(cls, v):
        if not PHONE_REGEX.match(v):
            raise ValueError("phone must start with + followed by digits")
        return v

    @validator("ts")
    def ts_must_be_iso_z(cls, v):
        if not TS_REGEX.match(v):
            raise ValueError("ts must be ISO-8601 UTC ending with Z")
        return v

    @validator("text")
    def text_max_length(cls, v):
        if v is not None and len(v) > 4096:
            raise ValueError("text too long")
        return v


@app.middleware("http")
async def log_and_metrics_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.message_id = None
    request.state.dup = None
    request.state.result = None

    start = time.time()
    response = await call_next(request)
    latency_ms = int((time.time() - start) * 1000)

    log_fields = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "latency_ms": latency_ms,
    }

    if request.url.path == "/webhook":
        if request.state.message_id is not None:
            log_fields["message_id"] = request.state.message_id
        if request.state.dup is not None:
            log_fields["dup"] = request.state.dup
        if request.state.result is not None:
            log_fields["result"] = request.state.result

    logger.info("request", extra={"extra_fields": log_fields})
    record_request(request.url.path, response.status_code, latency_ms)

    return response


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    if not WEBHOOK_SECRET:
        return JSONResponse(status_code=503, content={"status": "not ready"})

    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM messages LIMIT 1")
        cursor.fetchone()
        connection.close()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not ready"})

    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_metrics_text())


@app.get("/stats")
def stats():
    return get_stats()


@app.get("/messages")
def list_messages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_: str = Query(None, alias="from"),
    since: str = Query(None),
    q: str = Query(None),
):
    if from_:
        from_ = from_.replace(" ", "+")
    data, total = get_messages(limit=limit, offset=offset, from_=from_, since=since, q=q)
    return {
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.post("/webhook")
async def webhook(request: Request):
    raw_body = await request.body()

    received_signature = request.headers.get("X-Signature", "")
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(received_signature, expected_signature):
        request.state.result = "invalid_signature"
        record_webhook_result("invalid_signature")
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        body_dict = json.loads(raw_body)
    except json.JSONDecodeError:
        request.state.result = "validation_error"
        record_webhook_result("validation_error")
        return JSONResponse(status_code=422, content={"detail": "invalid JSON"})

    try:
        msg = WebhookMessage(**body_dict)
    except ValidationError as e:
        request.state.result = "validation_error"
        record_webhook_result("validation_error")
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(e.errors())})

    request.state.message_id = msg.message_id

    if message_exists(msg.message_id):
        request.state.dup = True
        request.state.result = "duplicate"
        record_webhook_result("duplicate")
        return {"status": "ok"}

    insert_message(
        message_id=msg.message_id,
        from_msisdn=msg.from_msisdn,
        to_msisdn=msg.to_msisdn,
        ts=msg.ts,
        text=msg.text,
    )
    request.state.dup = False
    request.state.result = "created"
    record_webhook_result("created")
    return {"status": "ok"}