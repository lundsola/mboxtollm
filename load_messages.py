import json
import logging
import os

from email_parser import parse_mbox

logger = logging.getLogger(__name__)


def load_messages(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"{filepath} not found.")

    if filepath.endswith(".mbox"):
        logger.info("Parsing mbox file: %s", filepath)
        return parse_mbox(filepath)

    if filepath.endswith(".jsonl"):
        logger.info("Loading JSONL file: %s", filepath)
        messages = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        return messages

    raise ValueError(f"Unsupported input format: {filepath}")
