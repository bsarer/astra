"""Zoho Mail provider using IMAP/SMTP.

Requires:
  pip install imapclient
"""

import os
import email
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

from .base import Email, EmailProvider


class ZohoEmailProvider(EmailProvider):
    """Zoho Mail provider using IMAP for reading, SMTP for sending."""

    def __init__(self, email_addr: str, password: str):
        self._email = email_addr
        self._password = password
        # Zoho Mail Europe servers
        self._imap_server = "imap.zoho.eu"
        self._imap_port = 993
        self._smtp_server = "smtp.zoho.eu"
        self._smtp_port = 465

    def _connect_imap(self):
        """Connect to Zoho IMAP server."""
        mail = imaplib.IMAP4_SSL(self._imap_server, self._imap_port)
        mail.login(self._email, self._password)
        return mail

    async def list_emails(self, limit: int = 20, label: str | None = None) -> list[Email]:
        """List recent emails from inbox."""
        try:
            mail = self._connect_imap()
            # Select inbox or specific folder
            folder = "INBOX"
            if label:
                # Map common labels to Zoho folders
                label_map = {"sent": "Sent", "drafts": "Drafts", "trash": "Trash"}
                folder = label_map.get(label.lower(), "INBOX")
            
            mail.select(folder)
            
            # Search for all emails, get most recent
            _, message_numbers = mail.search(None, "ALL")
            email_ids = message_numbers[0].split()
            
            # Get the last N emails
            recent_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
            recent_ids.reverse()  # Most recent first
            
            emails = []
            for email_id in recent_ids:
                _, msg_data = mail.fetch(email_id, "(RFC822)")
                email_body = msg_data[0][1]
                msg = email.message_from_bytes(email_body)
                
                # Parse email
                from_addr = msg.get("From", "")
                to_addr = msg.get("To", "")
                subject = msg.get("Subject", "")
                date_str = msg.get("Date", "")
                
                # Parse date
                try:
                    date_tuple = email.utils.parsedate_to_datetime(date_str)
                    date = date_tuple.replace(tzinfo=None) if date_tuple else datetime.now()
                except:
                    date = datetime.now()
                
                # Get body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                
                emails.append(Email(
                    id=email_id.decode(),
                    from_addr=from_addr,
                    to_addr=to_addr,
                    subject=subject,
                    body=body,
                    date=date,
                    labels=[folder.lower()],
                    read=True,  # IMAP doesn't easily expose unread status
                ))
            
            mail.close()
            mail.logout()
            return emails
            
        except Exception as e:
            raise Exception(f"Failed to fetch emails from Zoho: {e}")

    async def get_email(self, email_id: str) -> Email | None:
        """Get full email by ID."""
        try:
            mail = self._connect_imap()
            mail.select("INBOX")
            
            _, msg_data = mail.fetch(email_id.encode(), "(RFC822)")
            if not msg_data or not msg_data[0]:
                return None
                
            email_body = msg_data[0][1]
            msg = email.message_from_bytes(email_body)
            
            from_addr = msg.get("From", "")
            to_addr = msg.get("To", "")
            subject = msg.get("Subject", "")
            date_str = msg.get("Date", "")
            
            try:
                date_tuple = email.utils.parsedate_to_datetime(date_str)
                date = date_tuple.replace(tzinfo=None) if date_tuple else datetime.now()
            except:
                date = datetime.now()
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            
            mail.close()
            mail.logout()
            
            return Email(
                id=email_id,
                from_addr=from_addr,
                to_addr=to_addr,
                subject=subject,
                body=body,
                date=date,
                labels=["inbox"],
                read=True,
            )
            
        except Exception as e:
            raise Exception(f"Failed to get email {email_id}: {e}")

    async def send_email(self, to: str, subject: str, body: str, cc: list[str] | None = None) -> Email:
        """Send email via Zoho SMTP."""
        try:
            msg = MIMEMultipart()
            msg["From"] = self._email
            msg["To"] = to
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ", ".join(cc)
            
            msg.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP_SSL(self._smtp_server, self._smtp_port) as server:
                server.login(self._email, self._password)
                server.send_message(msg)
            
            return Email(
                id="sent-" + str(int(datetime.now().timestamp())),
                from_addr=self._email,
                to_addr=to,
                subject=subject,
                body=body,
                date=datetime.now(),
                labels=["sent"],
                read=True,
                cc=cc or [],
            )
            
        except Exception as e:
            raise Exception(f"Failed to send email: {e}")

    async def search_emails(self, query: str) -> list[Email]:
        """Search emails by keyword in subject or body."""
        # Simple implementation: fetch all and filter
        all_emails = await self.list_emails(limit=100)
        q = query.lower()
        return [
            e for e in all_emails
            if q in e.subject.lower() or q in e.body.lower()
            or q in e.from_addr.lower() or q in e.to_addr.lower()
        ]

    async def mark_read(self, email_id: str) -> bool:
        """Mark email as read (IMAP SEEN flag)."""
        try:
            mail = self._connect_imap()
            mail.select("INBOX")
            mail.store(email_id.encode(), "+FLAGS", "\\Seen")
            mail.close()
            mail.logout()
            return True
        except:
            return False
