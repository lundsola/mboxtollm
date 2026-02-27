import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from graph_builder import build_thread_graph


def test_empty_messages():
    g = build_thread_graph([])
    assert g.number_of_nodes() == 0
    assert g.number_of_edges() == 0


def test_single_message():
    msgs = [{"id": "msg1", "subject": "Hi", "date": "2024-01-01"}]
    g = build_thread_graph(msgs)
    assert g.number_of_nodes() == 1
    assert g.number_of_edges() == 0


def test_reply_to_edges():
    msgs = [
        {"id": "msg1", "subject": "Hi", "date": "2024-01-01"},
        {"id": "msg2", "subject": "Re: Hi", "date": "2024-01-02", "in_reply_to": "msg1"},
    ]
    g = build_thread_graph(msgs)
    assert g.number_of_nodes() == 2
    assert g.has_edge("msg1", "msg2")


def test_conversation_id_threading():
    msgs = [
        {"id": "a", "subject": "Thread", "date": "2024-01-01", "conversation_id": "conv1"},
        {"id": "b", "subject": "Re: Thread", "date": "2024-01-02", "conversation_id": "conv1"},
        {"id": "c", "subject": "Re: Re: Thread", "date": "2024-01-03", "conversation_id": "conv1"},
    ]
    g = build_thread_graph(msgs)
    assert g.number_of_nodes() == 3
    assert g.has_edge("a", "b")
    assert g.has_edge("b", "c")


def test_skips_messages_without_id():
    msgs = [
        {"subject": "No ID"},
        {"id": "msg1", "subject": "Has ID"},
    ]
    g = build_thread_graph(msgs)
    assert g.number_of_nodes() == 1


def test_reply_to_takes_precedence():
    """When in_reply_to is present, it should create the edge even without conversation_id."""
    msgs = [
        {"id": "parent", "subject": "Original", "date": "2024-01-01"},
        {"id": "child", "subject": "Reply", "date": "2024-01-02", "in_reply_to": "parent"},
    ]
    g = build_thread_graph(msgs)
    assert g.has_edge("parent", "child")
    assert g.number_of_edges() == 1
