import json


BODY = {
    "message_id": "m1",
    "from": "+919876543210",
    "to": "+14155550100",
    "ts": "2025-01-15T10:00:00Z",
    "text": "Hello",
}


def test_valid_message(signed_post, client):
    r = signed_post(BODY)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert client.get("/messages").json()["total"] == 1


def test_duplicate_is_idempotent(signed_post, client):
    assert signed_post(BODY).status_code == 200
    assert signed_post(BODY).status_code == 200
    assert client.get("/messages").json()["total"] == 1


def test_wrong_signature(client):
    r = client.post("/webhook", content=json.dumps(BODY).encode(), headers={"X-Signature": "wrong"})
    assert r.status_code == 401
    assert client.get("/messages").json()["total"] == 0


def test_missing_signature(client):
    r = client.post("/webhook", content=json.dumps(BODY).encode())
    assert r.status_code == 401


def test_invalid_phone(signed_post):
    bad = {**BODY, "from": "919876543210"}
    assert signed_post(bad).status_code == 422


def test_missing_field(signed_post):
    bad = {k: v for k, v in BODY.items() if k != "to"}
    assert signed_post(bad).status_code == 422
