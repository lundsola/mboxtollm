import json
import logging
import os

from email_reply_parser import EmailReplyParser
from tqdm import tqdm

logger = logging.getLogger(__name__)

OUTPUT_FILE = "data/pst_output.jsonl"


def walk_folder(folder, messages):
    for item in folder.Items:
        if item.Class == 43:  # MailItem
            try:
                messages.append(
                    {
                        "id": item.EntryID,
                        "subject": item.Subject,
                        "from": item.SenderEmailAddress,
                        "to": item.To,
                        "date": str(item.SentOn),
                        "body": item.Body,
                        "cleaned_body": EmailReplyParser.parse_reply(item.Body),
                        "conversation_id": item.ConversationID,
                        "in_reply_to": None,
                        "references": [],
                    }
                )
            except AttributeError as e:
                logger.warning("Error reading mail item: %s", e)

    for subfolder in folder.Folders:
        walk_folder(subfolder, messages)


def extract_pst():
    # pywin32 is only available on Windows
    import win32com.client

    logging.basicConfig(level=logging.INFO)

    logger.info("Launching Outlook...")
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

    logger.info("Available PST stores:")
    for i in range(outlook.Folders.Count):
        folder = outlook.Folders.Item(i + 1)
        print(f"  {i + 1}: {folder.Name}")

    index = int(input("Enter the number of the PST store to extract from: ")) - 1
    root_folder = outlook.Folders.Item(index + 1)

    logger.info("Extracting from: %s", root_folder.Name)
    messages = []
    walk_folder(root_folder, messages)

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for msg in tqdm(messages, desc="Writing messages"):
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    logger.info("Done! %d messages written to %s", len(messages), OUTPUT_FILE)


if __name__ == "__main__":
    extract_pst()
