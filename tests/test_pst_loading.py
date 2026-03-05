"""Tests for PST file parsing via load_messages."""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from load_messages import load_messages, parse_pst, _extract_header


class FakeMessage:
    def __init__(self, subject, sender, body, headers=""):
        self.subject = subject
        self.sender_name = sender
        self.plain_text_body = body
        self.transport_headers = headers
        self.display_to = "recipient@example.com"


class FakeFolder:
    def __init__(self, messages=None, subfolders=None):
        self._messages = messages or []
        self._subfolders = subfolders or []

    @property
    def number_of_sub_messages(self):
        return len(self._messages)

    def get_sub_message(self, i):
        return self._messages[i]

    @property
    def number_of_sub_folders(self):
        return len(self._subfolders)

    def get_sub_folder(self, i):
        return self._subfolders[i]


class FakePstFile:
    def __init__(self, root_folder):
        self._root = root_folder

    def open(self, path):
        pass

    def get_root_folder(self):
        return self._root

    def close(self):
        pass


def test_extract_header():
    headers = "Message-ID: <abc@example.com>\r\nDate: Mon, 1 Jan 2024\r\nFrom: test@example.com"
    assert _extract_header(headers, "Message-ID") == "<abc@example.com>"
    assert _extract_header(headers, "Date") == "Mon, 1 Jan 2024"
    assert _extract_header(headers, "Subject") is None
    assert _extract_header(None, "Message-ID") is None
    assert _extract_header("", "Message-ID") is None


def test_parse_pst_with_mock():
    msg1 = FakeMessage(
        subject="Test Subject",
        sender="sender@example.com",
        body="Hello, this is a test email body.",
        headers="Message-ID: <msg1@example.com>\r\nDate: 2024-01-15",
    )
    msg2 = FakeMessage(
        subject="Another Subject",
        sender="other@example.com",
        body="Second email body.",
        headers="Message-ID: <msg2@example.com>\r\nIn-Reply-To: <msg1@example.com>",
    )

    subfolder = FakeFolder(messages=[msg2])
    root = FakeFolder(messages=[msg1], subfolders=[subfolder])
    fake_pst = FakePstFile(root)

    mock_pypff = MagicMock()
    mock_pypff.file.return_value = fake_pst

    with patch.dict("sys.modules", {"pypff": mock_pypff}):
        messages = parse_pst("/fake/path.pst")

    assert len(messages) == 2
    assert messages[0]["id"] == "<msg1@example.com>"
    assert messages[0]["subject"] == "Test Subject"
    assert messages[0]["from"] == "sender@example.com"
    assert messages[1]["in_reply_to"] == "<msg1@example.com>"


def test_parse_pst_bytes_body():
    msg = FakeMessage(
        subject="Bytes test",
        sender="test@example.com",
        body=b"Body as bytes",
        headers="Message-ID: <bytes@example.com>",
    )
    root = FakeFolder(messages=[msg])
    fake_pst = FakePstFile(root)

    mock_pypff = MagicMock()
    mock_pypff.file.return_value = fake_pst

    with patch.dict("sys.modules", {"pypff": mock_pypff}):
        messages = parse_pst("/fake/path.pst")

    assert len(messages) == 1
    assert "bytes" not in messages[0]["cleaned_body"] or "Body as bytes" in messages[0]["cleaned_body"]


def test_parse_pst_generates_id_without_message_id():
    msg = FakeMessage(
        subject="No ID",
        sender="test@example.com",
        body="No message ID in headers.",
        headers="Date: 2024-01-15",
    )
    root = FakeFolder(messages=[msg])
    fake_pst = FakePstFile(root)

    mock_pypff = MagicMock()
    mock_pypff.file.return_value = fake_pst

    with patch.dict("sys.modules", {"pypff": mock_pypff}):
        messages = parse_pst("/fake/path.pst")

    assert len(messages) == 1
    assert messages[0]["id"]  # should have a generated hash ID


def test_load_messages_pst_suffix():
    """load_messages dispatches .pst files to parse_pst."""
    with tempfile.NamedTemporaryFile(suffix=".pst", delete=False) as f:
        f.write(b"fake")
        path = f.name

    try:
        with patch("load_messages.parse_pst", return_value=[{"id": "1"}]) as mock:
            result = load_messages(path)
            mock.assert_called_once_with(path)
            assert result == [{"id": "1"}]
    finally:
        os.unlink(path)
