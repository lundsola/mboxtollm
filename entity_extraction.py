import json
import os
import spacy
from tqdm import tqdm

# Enable GPU if available
try:
    spacy.require_gpu()
    print("✅ spaCy will use GPU")
except Exception:
    print("⚠️  spaCy is falling back to CPU")

nlp = spacy.load("en_core_web_trf")

INPUT_FILE = "data/pst_output.jsonl"
OUTPUT_FILE = "data/triplets_with_email.jsonl"


def extract_entities(text):
    doc = nlp(text)
    people = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    orgs = [ent.text for ent in doc.ents if ent.label_ in ["ORG", "PRODUCT"]]

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
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Missing file: {INPUT_FILE}")
        return

    print(f"📥 Reading messages from {INPUT_FILE}")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total = len(lines)
    print(f"⚙️ Processing {total} messages with GPU-backed spaCy pipeline...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_file:
        for line in tqdm(lines):
            message = json.loads(line)
            body = message.get("cleaned_body") or message.get("body", "")
            email_id = message.get("id") or message.get("message_id")

            if not email_id or not body.strip():
                continue

            triplets = extract_entities(body)
            for subj, pred, obj in triplets:
                enriched = {
                    "subject": subj,
                    "predicate": pred,
                    "object": obj,
                    "email_id": email_id
                }
                out_file.write(json.dumps(enriched) + "\n")

    print(f"✅ Done! Triplets written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
