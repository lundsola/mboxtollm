import win32com.client
import json
from tqdm import tqdm
from email_reply_parser import EmailReplyParser
import os

OUTPUT_FILE = "data/pst_output.jsonl"

def walk_folder(folder, messages):
    for item in folder.Items:
        if item.Class == 43:  # MailItem
            try:
                messages.append({
                    "id": item.EntryID,
                    "subject": item.Subject,
                    "from": item.SenderEmailAddress,
                    "to": item.To,
                    "date": str(item.SentOn),
                    "body": item.Body,
                    "cleaned_body": EmailReplyParser.parse_reply(item.Body),
                    "conversation_id": item.ConversationID,
                    "in_reply_to": None,  # Not exposed via Outlook API easily
                    "references": []
                })
            except Exception as e:
                print(f"Error: {e}")

    for subfolder in folder.Folders:
        walk_folder(subfolder, messages)

def extract_pst():
    print("🟢 Launching Outlook...")
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

    print("📂 Selecting PST store...")
    for i in range(outlook.Folders.Count):
        folder = outlook.Folders.Item(i + 1)
        print(f"{i+1}: {folder.Name}")
    index = int(input("Enter the number of the PST store to extract from: ")) - 1
    root_folder = outlook.Folders.Item(index + 1)

    print(f"📤 Extracting from: {root_folder.Name}")
    messages = []
    walk_folder(root_folder, messages)

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for msg in tqdm(messages, desc="Writing messages"):
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    print(f"✅ Done! {len(messages)} messages written to {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_pst()
