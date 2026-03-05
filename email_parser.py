import hashlib
import logging
import mailbox
from email.utils import parsedate_to_datetime

from email_reply_parser import EmailReplyParser

logger = logging.getLogger(__name__)


def parse_mbox(path):
    mbox = mailbox.mbox(path)
    messages = []
    skipped = 0

    for msg in mbox:
        try:
            message_id = msg["Message-ID"]
            in_reply_to = msg["In-Reply-To"]
            references = msg.get_all("References", [])
            subject = msg["Subject"] or ""
            sender = msg["From"]
            date_str = msg["Date"]
            date = parsedate_to_datetime(date_str) if date_str else None

            body = _get_clean_body(msg)
            body_hash = hashlib.sha256(body.encode()).hexdigest()

            messages.append(
                {
                    "id": message_id,
                    "in_reply_to": in_reply_to,
                    "references": references,
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "cleaned_body": body,
                    "body_hash": body_hash,
                }
            )
        except (ValueError, TypeError, KeyError) as e:
            skipped += 1
            logger.warning("Skipping message: %s", e)

    if skipped:
        logger.info("Skipped %d unparseable messages", skipped)
    return messages


def _get_clean_body(msg):
    """Extract the plain-text body from a (possibly multipart) email."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    text = payload.decode(errors="ignore")
                    return EmailReplyParser.parse_reply(text)
        return ""

    payload = msg.get_payload(decode=True)
    if payload:
        text = payload.decode(errors="ignore")
        return EmailReplyParser.parse_reply(text)
    return ""
