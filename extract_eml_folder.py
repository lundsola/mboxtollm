import email
import hashlib
import json
import logging
import os
from email.utils import parsedate_to_datetime

from email_reply_parser import EmailReplyParser
from tqdm import tqdm

logger = logging.getLogger(__name__)


def extract_eml_folder(eml_dir, output_jsonl="data/eml_output.jsonl"):
    messages = []

    filenames = [f for f in os.listdir(eml_dir) if f.lower().endswith(".eml")]
    for filename in tqdm(filenames, desc="Parsing EMLs"):
        path = os.path.join(eml_dir, filename)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            msg = email.message_from_file(f)

        try:
            body = _extract_body(msg)
            cleaned_body = EmailReplyParser.parse_reply(body)
            date_str = msg.get("Date")

            messages.append(
                {
                    "id": msg.get("Message-ID"),
                    "in_reply_to": msg.get("In-Reply-To"),
                    "references": msg.get_all("References", []),
                    "subject": msg.get("Subject"),
                    "from": msg.get("From"),
                    "to": msg.get("To"),
                    "date": str(parsedate_to_datetime(date_str))
                    if date_str
                    else None,
                    "cleaned_body": cleaned_body,
                    "body_hash": hashlib.sha256(
                        cleaned_body.encode()
                    ).hexdigest(),
                }
            )
        except (ValueError, TypeError) as e:
            logger.warning("Skipping %s: %s", filename, e)

    os.makedirs("data", exist_ok=True)
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    logger.info("Extracted %d messages to %s", len(messages), output_jsonl)


def _extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(errors="ignore")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(errors="ignore") if payload else ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    extract_eml_folder("data/eml_folder")
