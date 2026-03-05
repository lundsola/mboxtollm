import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from storage import EmailStore

# Actually try to create a store to verify the model can be downloaded
try:
    import tempfile

    _test_store = EmailStore(persist_dir=tempfile.mkdtemp())
    del _test_store
    _model_available = True
except Exception:
    _model_available = False

requires_model = pytest.mark.skipif(
    not _model_available, reason="Embedding model not available"
)

SAMPLE_MESSAGES = [
    {
        "id": "msg1",
        "subject": "Project kickoff",
        "from": "alice@example.com",
        "to": "bob@example.com",
        "date": "2024-01-15",
        "cleaned_body": "Let's start the new project next Monday. I've prepared the requirements document.",
        "conversation_id": "conv1",
    },
    {
        "id": "msg2",
        "subject": "Re: Project kickoff",
        "from": "bob@example.com",
        "to": "alice@example.com",
        "date": "2024-01-16",
        "cleaned_body": "Sounds good! I'll review the requirements over the weekend.",
        "conversation_id": "conv1",
        "in_reply_to": "msg1",
    },
    {
        "id": "msg3",
        "subject": "Budget meeting",
        "from": "carol@example.com",
        "to": "team@example.com",
        "date": "2024-02-01",
        "cleaned_body": "Reminder: Q1 budget review meeting is on Friday at 2pm.",
        "conversation_id": "conv2",
    },
]


@pytest.fixture
def tmp_store(tmp_path):
    store = EmailStore(persist_dir=str(tmp_path / "chroma"))
    return store


@requires_model
def test_store_messages(tmp_store):
    count = tmp_store.store_messages(SAMPLE_MESSAGES)
    assert count == 3


@requires_model
def test_store_deduplicates(tmp_store):
    tmp_store.store_messages(SAMPLE_MESSAGES)
    count = tmp_store.store_messages(SAMPLE_MESSAGES)
    assert count == 0


@requires_model
def test_store_skips_empty_body(tmp_store):
    msgs = [{"id": "empty", "cleaned_body": ""}, {"id": "none"}]
    count = tmp_store.store_messages(msgs)
    assert count == 0


@requires_model
def test_search(tmp_store):
    tmp_store.store_messages(SAMPLE_MESSAGES)
    results = tmp_store.search("project requirements")
    assert len(results) > 0
    assert any("project" in r["cleaned_body"].lower() for r in results)


@requires_model
def test_search_empty_collection(tmp_store):
    results = tmp_store.search("anything")
    assert results == []


@requires_model
def test_search_with_k(tmp_store):
    tmp_store.store_messages(SAMPLE_MESSAGES)
    results = tmp_store.search("meeting", k=1)
    assert len(results) == 1


@requires_model
def test_collection_stats(tmp_store):
    tmp_store.store_messages(SAMPLE_MESSAGES)
    stats = tmp_store.collection_stats()
    assert stats["name"] == "emails"
    assert stats["count"] == 3


@requires_model
def test_get_message(tmp_store):
    tmp_store.store_messages(SAMPLE_MESSAGES)
    msg = tmp_store.get_message("msg1")
    assert msg is not None
    assert msg["id"] == "msg1"
    assert "project" in msg["cleaned_body"].lower()


@requires_model
def test_get_message_not_found(tmp_store):
    msg = tmp_store.get_message("nonexistent")
    assert msg is None


@requires_model
def test_get_thread(tmp_store):
    tmp_store.store_messages(SAMPLE_MESSAGES)
    thread = tmp_store.get_thread("conv1")
    assert len(thread) == 2
    assert thread[0]["date"] <= thread[1]["date"]


@requires_model
def test_list_collections(tmp_store):
    tmp_store.store_messages(SAMPLE_MESSAGES)
    tmp_store.store_messages(SAMPLE_MESSAGES, collection_name="archive")
    collections = tmp_store.list_collections()
    names = [c["name"] for c in collections]
    assert "emails" in names
    assert "archive" in names
