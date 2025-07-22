# extract_eml_folder.py

import os
import email
from email_reply_parser import EmailReplyParser
from email.utils import parsedate_to_datetime
import hashlib
import json
from tqdm import tqdm

def extract_eml_folder(eml_dir, output_jsonl="data/eml_output.jsonl"):
    messages = []

    for filename in tqdm(os.listdir(eml_dir), desc="Parsing EMLs"):
        if not filename.lower().endswith(".eml"):
            continue

        path = os.path.join(eml_dir, filename)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            msg = email.message_from_file(f)

            try:
                body = extract_body(msg)
                cleaned_body = EmailReplyParser.parse_reply(body)

                messages.append({
                    "id": msg.get("Message-ID"),
                    "in_reply_to": msg.get("In-Reply-To"),
                    "references": msg.get_all("References", []),
                    "subject": msg.get("Subject"),
                    "from": msg.get("From"),
                    "to": msg.get("To"),
                    "date": str(parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None),
                    "cleaned_body": cleaned_body,
                    "body_hash": hashlib.sha256(cleaned_body.encode()).hexdigest()
                })
            except Exception as e:
                print(f"Skipping {filename}: {e}")

    os.makedirs("data", exist_ok=True)
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    print(f"✅ Extracted {len(messages)} messages to {output_jsonl}")

def extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors='ignore')
    else:
        return msg.get_payload(decode=True).decode(errors='ignore')
    return ""

if __name__ == "__main__":
    extract_eml_folder("data/eml_folder")
