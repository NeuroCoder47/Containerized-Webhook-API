import pytest
from app.storage import insert_message


@pytest.fixture
def seeded():
    insert_message("m1", "+911111111111", "+14155550100", "2025-01-15T09:00:00Z", "Hello world")
    insert_message("m2", "+911111111111", "+14155550100", "2025-01-15T10:00:00Z", "Hello again")
    insert_message("m3", "+922222222222", "+14155550100", "2025-01-15T11:00:00Z", "Different sender")
    insert_message("m4", "+922222222222", "+14155550100", "2025-01-15T12:00:00Z", "Another one")


def test_basic_list(client, seeded):
    data = client.get("/messages").json()
    assert data["total"] == 4
    assert len(data["data"]) == 4
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_limit(client, seeded):
    data = client.get("/messages?limit=2").json()
    assert len(data["data"]) == 2
    assert data["total"] == 4


def test_offset(client, seeded):
    data = client.get("/messages?limit=2&offset=2").json()
    assert [m["message_id"] for m in data["data"]] == ["m3", "m4"]


def test_filter_by_from(client, seeded):
    data = client.get("/messages?from=+911111111111").json()
    assert data["total"] == 2
    assert all(m["from"] == "+911111111111" for m in data["data"])


def test_filter_by_since(client, seeded):
    data = client.get("/messages?since=2025-01-15T10:30:00Z").json()
    assert data["total"] == 2
    assert all(m["ts"] >= "2025-01-15T10:30:00Z" for m in data["data"])


def test_filter_by_q(client, seeded):
    data = client.get("/messages?q=Hello").json()
    assert data["total"] == 2


def test_ordering(client, seeded):
    data = client.get("/messages").json()
    timestamps = [m["ts"] for m in data["data"]]
    assert timestamps == sorted(timestamps)
