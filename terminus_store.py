"""Opt-in, bounded-write MBOX pilot. Does not change the legacy EmailStore."""
import argparse
import hashlib
import json
import mailbox
import os
import re
from email import policy
from email.parser import BytesParser


SCHEMA = {
    "@type": "Class", "@id": "Email",
    "archive": "xsd:string", "message_id": "xsd:string",
    "subject": "xsd:string", "sender": "xsd:string",
    "recipients": "xsd:string", "date_header": "xsd:string",
    "body": "xsd:string", "source_sha256": "xsd:string",
    "references": {"@type": "Set", "@class": "xsd:string"},
}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def iter_documents(path, archive):
    """Stream mail; retain full text (including quotes), not attachments.

    ID collisions with different content are kept as separate source variants.
    Raw archive retention remains the caller's responsibility.
    """
    if not archive.strip():
        raise ValueError("archive must not be empty")
    box = mailbox.mbox(path, create=False)
    try:
        for key in box.iterkeys():
            raw = box.get_bytes(key)
            source_hash = digest(raw)
            msg = BytesParser(policy=policy.default).parsebytes(raw)
            mid = str(msg.get("Message-ID", "")).strip() or "sha256:" + source_hash
            parts = []
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    continue
                if part.get_content_type() == "text/plain":
                    try:
                        parts.append(part.get_content())
                    except LookupError:
                        parts.append(part.get_payload(decode=True).decode("utf-8", "replace"))
            # Preserve HTML-only mail as text source; sanitization belongs to UI.
            if not parts:
                for part in msg.walk():
                    if part.get_content_type() == "text/html" and part.get_content_disposition() != "attachment":
                        parts.append(part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace"))
            refs = re.findall(r"<[^<>\s]+>", " ".join(
                str(v) for name in ("References", "In-Reply-To") for v in msg.get_all(name, [])
            ))
            yield {
                "@type": "Email",
                "@id": "Email/" + digest(json.dumps([archive, mid, source_hash]).encode()),
                "archive": archive, "message_id": mid,
                "subject": str(msg.get("Subject", "")),
                "sender": str(msg.get("From", "")),
                "recipients": str(msg.get("To", "")),
                "date_header": str(msg.get("Date", "")),
                "body": "\n".join(parts), "source_sha256": source_hash,
                "references": sorted(set(refs)),
            }
    finally:
        box.close()


class TerminusEmailStore:
    def __init__(self, client):
        self.client = client

    def install_schema(self):
        # Explicit opt-in; never replace the entire schema graph.
        self.client.insert_document(SCHEMA, graph_type="schema")

    def import_mbox(self, path, archive, batch_size=100):
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        batch, processed = {}, 0
        for doc in iter_documents(path, archive):
            batch[doc["@id"]] = doc
            processed += 1
            if len(batch) >= batch_size:
                self.client.replace_document(list(batch.values()), create=True)
                batch.clear()
        if batch:
            self.client.replace_document(list(batch.values()), create=True)
        return processed  # source records processed, NOT newly inserted count

    def get_thread(self, archive, message_id):
        # Pilot only: scans ONE archive. Replace with server-side graph traversal
        # before using multi-million-message archives.
        docs = list(self.client.query_document({"@type": "Email", "archive": archive}))
        if not any(d["message_id"] == message_id for d in docs):
            return []
        connected = {message_id}
        changed = True
        while changed:
            changed = False
            for doc in docs:
                ids = {doc["message_id"], *doc.get("references", [])}
                if connected & ids and not ids <= connected:
                    connected.update(ids)
                    changed = True
        return sorted((d for d in docs if d["message_id"] in connected), key=lambda d: d["@id"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--mbox")
    parser.add_argument("--thread", help="Message-ID of any message in the thread")
    parser.add_argument("--init-schema", action="store_true", help="Only on a new, dedicated database")
    args = parser.parse_args()
    from terminusdb_client import Client
    client = Client(os.environ.get("TERMINUSDB_URL", "http://localhost:6363"))
    client.connect(db=os.environ["TERMINUSDB_DATABASE"],
                   team=os.environ.get("TERMINUSDB_TEAM", "admin"),
                   user=os.environ.get("TERMINUSDB_USER", "admin"),
                   key=os.environ["TERMINUSDB_KEY"])
    store = TerminusEmailStore(client)
    if args.init_schema:
        store.install_schema()
    if args.mbox:
        print(json.dumps({"processed": store.import_mbox(args.mbox, args.archive)}))
    if args.thread:
        print(json.dumps(store.get_thread(args.archive, args.thread), ensure_ascii=False))


if __name__ == "__main__":
    main()
