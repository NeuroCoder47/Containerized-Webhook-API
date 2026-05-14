import pytest
from app.storage import insert_message


@pytest.fixture
def seeded():
    insert_message("m1", "+911111111111", "+14155550100", "2025-01-15T09:00:00Z", "Hi")
    insert_message("m2", "+911111111111", "+14155550100", "2025-01-15T10:00:00Z", "Hi")
    insert_message("m3", "+922222222222", "+14155550100", "2025-01-15T11:00:00Z", "Hi")


def test_empty_stats(client):
    data = client.get("/stats").json()
    assert data["total_messages"] == 0
    assert data["senders_count"] == 0
    assert data["messages_per_sender"] == []
    assert data["first_message_ts"] is None
    assert data["last_message_ts"] is None


def test_total_messages(client, seeded):
    assert client.get("/stats").json()["total_messages"] == 3


def test_senders_count(client, seeded):
    assert client.get("/stats").json()["senders_count"] == 2


def test_messages_per_sender(client, seeded):
    senders = client.get("/stats").json()["messages_per_sender"]
    counts = {s["from"]: s["count"] for s in senders}
    assert counts == {"+911111111111": 2, "+922222222222": 1}
    assert senders[0]["from"] == "+911111111111"


def test_first_and_last_ts(client, seeded):
    data = client.get("/stats").json()
    assert data["first_message_ts"] == "2025-01-15T09:00:00Z"
    assert data["last_message_ts"] == "2025-01-15T11:00:00Z"


def test_counts_sum_to_total(client, seeded):
    data = client.get("/stats").json()
    total = sum(s["count"] for s in data["messages_per_sender"])
    assert total == data["total_messages"]
