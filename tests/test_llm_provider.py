import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm_provider import _format_thread


def test_format_thread_basic():
    messages = [
        {
            "from": "alice@example.com",
            "date": "2024-01-15",
            "subject": "Hello",
            "cleaned_body": "Hi there!",
        },
        {
            "from": "bob@example.com",
            "date": "2024-01-16",
            "subject": "Re: Hello",
            "cleaned_body": "Hey Alice!",
        },
    ]
    result = _format_thread(messages)
    assert "alice@example.com" in result
    assert "bob@example.com" in result
    assert "Hi there!" in result
    assert "Hey Alice!" in result
    assert "---" in result  # separator


def test_format_thread_truncates_long_body():
    messages = [
        {
            "from": "test@test.com",
            "date": "2024-01-01",
            "subject": "Long email",
            "cleaned_body": "x" * 5000,
        }
    ]
    result = _format_thread(messages)
    assert "...[truncated]" in result
    assert len(result) < 5000


def test_format_thread_handles_missing_fields():
    messages = [{}]
    result = _format_thread(messages)
    assert "unknown" in result


def test_format_empty_thread():
    result = _format_thread([])
    assert result == ""
