import json
import logging
import os

import spacy
from tqdm import tqdm

from config import INPUT_FILE

logger = logging.getLogger(__name__)

OUTPUT_FILE = "data/triplets_with_email.jsonl"


def _load_nlp():
    try:
        spacy.require_gpu()
        logger.info("spaCy will use GPU")
    except Exception:
        logger.info("spaCy falling back to CPU")
    return spacy.load("en_core_web_trf")


def extract_entities(nlp, text):
    doc = nlp(text)
    people = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    orgs = [ent.text for ent in doc.ents if ent.label_ in ("ORG", "PRODUCT")]

    triplets = []
    for person in people:
        for org in orgs:
            triplets.append((person, "mentioned", org))
        for date in dates:
            triplets.append((person, "mentioned_on", date))
    for org in orgs:
        for date in dates:
            triplets.append((org, "referenced_on", date))

    return triplets


def main():
    logging.basicConfig(level=logging.INFO)

    if not os.path.exists(INPUT_FILE):
        logger.error("Missing file: %s", INPUT_FILE)
        return

    nlp = _load_nlp()

    logger.info("Reading messages from %s", INPUT_FILE)
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    logger.info("Processing %d messages...", len(lines))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_file:
        for line in tqdm(lines):
            message = json.loads(line)
            body = message.get("cleaned_body") or message.get("body", "")
            email_id = message.get("id") or message.get("message_id")

            if not email_id or not body.strip():
                continue

            triplets = extract_entities(nlp, body)
            for subj, pred, obj in triplets:
                enriched = {
                    "subject": subj,
                    "predicate": pred,
                    "object": obj,
                    "email_id": email_id,
                }
                out_file.write(json.dumps(enriched) + "\n")

    logger.info("Done! Triplets written to %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
