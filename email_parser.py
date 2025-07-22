import mailbox
from email_reply_parser import EmailReplyParser
from email.utils import parsedate_to_datetime
import hashlib

def parse_mbox(path):
    mbox = mailbox.mbox(path)
    messages = []
    for msg in mbox:
        try:
            message_id = msg['Message-ID']
            in_reply_to = msg['In-Reply-To']
            references = msg.get_all('References', [])
            subject = msg['Subject'] or ''
            sender = msg['From']
            date = parsedate_to_datetime(msg['Date']) if msg['Date'] else None
            body = get_clean_body(msg)
            body_hash = hashlib.sha256(body.encode()).hexdigest()

            messages.append({
                'id': message_id,
                'in_reply_to': in_reply_to,
                'references': references,
                'subject': subject,
                'from': sender,
                'date': date,
                'cleaned_body': body,
                'body_hash': body_hash
            })
        except Exception as e:
            print(f"Error parsing message: {e}")
    return messages

def get_clean_body(msg):
    payload = msg.get_payload(decode=True)
    if payload:
        text = payload.decode(errors='ignore')
        return EmailReplyParser.parse_reply(text)
    return ''
