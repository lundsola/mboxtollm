import json
import logging
import os

from email_parser import parse_mbox

logger = logging.getLogger(__name__)


def parse_pst(filepath):
    """Parse a .pst file using pypff and return a list of message dicts."""
    import hashlib

    import pypff
    from email_reply_parser import EmailReplyParser

    pst = pypff.file()
    pst.open(filepath)

    messages = []

    def _walk_folder(folder):
        for i in range(folder.number_of_sub_messages):
            msg = folder.get_sub_message(i)
            try:
                body = msg.plain_text_body
                if isinstance(body, bytes):
                    body = body.decode(errors="ignore")
                body = body or ""
                cleaned = EmailReplyParser.parse_reply(body)

                subject = msg.subject or ""
                sender = msg.sender_name or ""
                headers = msg.transport_headers or ""
                message_id = _extract_header(headers, "Message-ID")
                in_reply_to = _extract_header(headers, "In-Reply-To")
                date_str = _extract_header(headers, "Date")
                conversation_id = _extract_header(headers, "Thread-Index")

                entry_id = message_id or hashlib.sha256(
                    f"{subject}{sender}{date_str}{body[:200]}".encode()
                ).hexdigest()

                messages.append(
                    {
                        "id": entry_id,
                        "subject": subject,
                        "from": sender,
                        "to": getattr(msg, "display_to", "") or "",
                        "date": date_str,
                        "cleaned_body": cleaned,
                        "body_hash": hashlib.sha256(body.encode()).hexdigest(),
                        "conversation_id": conversation_id,
                        "in_reply_to": in_reply_to,
                        "references": [],
                    }
                )
            except Exception as e:
                logger.warning("Skipping PST message: %s", e)

        for j in range(folder.number_of_sub_folders):
            _walk_folder(folder.get_sub_folder(j))

    root = pst.get_root_folder()
    _walk_folder(root)
    pst.close()

    logger.info("Parsed %d messages from PST file", len(messages))
    return messages


def _extract_header(headers, name):
    """Extract a single header value from raw transport headers."""
    if not headers:
        return None
    for line in headers.splitlines():
        if line.lower().startswith(name.lower() + ":"):
            return line[len(name) + 1 :].strip()
    return None


def load_messages(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"{filepath} not found.")

    if filepath.endswith(".mbox"):
        logger.info("Parsing mbox file: %s", filepath)
        return parse_mbox(filepath)

    if filepath.endswith(".pst"):
        logger.info("Parsing PST file: %s", filepath)
        return parse_pst(filepath)

    if filepath.endswith(".jsonl"):
        logger.info("Loading JSONL file: %s", filepath)
        messages = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        return messages

    raise ValueError(f"Unsupported input format: {filepath}")
