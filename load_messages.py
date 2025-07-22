# load_messages.py

import os
import json
from email_parser import parse_mbox

def load_messages(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"{filepath} not found.")

    if filepath.endswith(".mbox"):
        return parse_mbox(filepath)

    elif filepath.endswith(".jsonl"):
        messages = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                msg = json.loads(line)
                messages.append(msg)
        return messages

    else:
        raise ValueError(f"Unsupported input format: {filepath}")

