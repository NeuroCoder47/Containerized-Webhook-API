import json
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import WEBHOOK_SECRET
from app.storage import get_connection


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    conn = get_connection()
    conn.execute("DELETE FROM messages")
    conn.commit()
    conn.close()


@pytest.fixture
def signed_post(client):
    def _post(body):
        body_bytes = json.dumps(body).encode()
        sig = hmac.new(WEBHOOK_SECRET.encode(), body_bytes, hashlib.sha256).hexdigest()
        return client.post("/webhook", content=body_bytes, headers={"X-Signature": sig})
    return _post
