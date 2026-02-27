import json
import os
import tempfile

import pytest

# Ensure project root is importable
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from load_messages import load_messages


def _write_jsonl(path, records):
    with open(path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def test_load_jsonl():
    records = [
        {"id": "1", "subject": "Hello", "cleaned_body": "Hi there"},
        {"id": "2", "subject": "Re: Hello", "cleaned_body": "Hey"},
    ]
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
        path = f.name

    try:
        messages = load_messages(path)
        assert len(messages) == 2
        assert messages[0]["id"] == "1"
        assert messages[1]["subject"] == "Re: Hello"
    finally:
        os.unlink(path)


def test_load_missing_file():
    with pytest.raises(FileNotFoundError):
        load_messages("/nonexistent/path.jsonl")


def test_load_unsupported_format():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        f.write(b"a,b\n1,2\n")
        path = f.name

    try:
        with pytest.raises(ValueError, match="Unsupported"):
            load_messages(path)
    finally:
        os.unlink(path)
