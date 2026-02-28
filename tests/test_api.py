"""API endpoint tests. Requires the embedding model to be downloadable."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# The API app loads an EmailStore on startup, which downloads the embedding model.
# Skip the entire module if the model can't be loaded.
try:
    os.environ.setdefault("CHROMA_PERSIST_DIR", tempfile.mkdtemp())
    from storage import EmailStore

    _tmp = EmailStore(persist_dir=tempfile.mkdtemp())
    del _tmp
except Exception:
    pytest.skip("Embedding model not available", allow_module_level=True)

from fastapi.testclient import TestClient

from api import app


@pytest.fixture
def client():
    """Create a test client with the lifespan properly initialized."""
    with TestClient(app) as c:
        yield c


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_upload_unsupported_format(client):
    response = client.post(
        "/upload",
        files={"file": ("test.txt", b"some content", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_collections(client):
    response = client.get("/collections")
    assert response.status_code == 200


def test_search_empty(client):
    response = client.post(
        "/search", json={"query": "test", "collection": "test_empty"}
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_upload_and_search(client):
    messages = [
        {
            "id": "test1",
            "subject": "Quarterly review",
            "from": "boss@company.com",
            "date": "2024-03-01",
            "cleaned_body": "Please prepare the quarterly financial review for the board meeting.",
            "conversation_id": "conv_test",
        },
        {
            "id": "test2",
            "subject": "Re: Quarterly review",
            "from": "analyst@company.com",
            "date": "2024-03-02",
            "cleaned_body": "I have the financial data ready. Revenue is up 15% year over year.",
            "conversation_id": "conv_test",
            "in_reply_to": "test1",
        },
    ]
    content = "\n".join(json.dumps(m) for m in messages)

    response = client.post(
        "/upload",
        files={"file": ("test.jsonl", content.encode(), "application/octet-stream")},
        data={"collection": "test_search"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processing"

    response = client.post(
        "/search",
        json={"query": "financial revenue", "collection": "test_search"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0


def test_storyline_no_api_key(client):
    """Storyline should fail gracefully when no API key is configured."""
    response = client.post(
        "/storyline",
        json={"topic": "test topic", "collection": "nonexistent"},
    )
    assert response.status_code in (503, 404)


def test_summarize_missing_params(client):
    response = client.post("/summarize", json={"collection": "emails"})
    assert response.status_code == 400
