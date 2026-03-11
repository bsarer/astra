"""Mock providers that read from persona JSON files."""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import Email, EmailProvider, CalendarEvent, CalendarProvider


def _parse_dt(s: str) -> datetime:
    """Parse ISO datetime, stripping timezone for simplicity."""
    # Handle timezone offset: +HH:MM or -HH:MM at the end
    # Also handle Z suffix
    if s.endswith("Z"):
        s = s[:-1]
    # Check for timezone offset (e.g., +02:00 or -06:00)
    # Only strip if there's a + or - after the time portion
    if "T" in s:
        time_part = s.split("T")[1]
        # Look for +/- in the time part (not the date part)
        for sep in ["+", "-"]:
            if sep in time_part:
                # Find the position in the full string
                idx = s.rindex(sep)
                # Make sure it's a timezone offset (has : after it or is at least 5 chars from end)
                remaining = s[idx+1:]
                if ":" in remaining or len(remaining) in [2, 4, 5]:
                    s = s[:idx]
                    break
    try:
        return datetime.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"Cannot parse datetime '{s}': {e}")


class MockEmailProvider(EmailProvider):
    """Serves emails from a JSON file. Supports send (appends to file)."""

    def __init__(self, data_path: str | Path):
        self._path = Path(data_path)
        self._emails = self._load()

    def _load(self) -> list[Email]:
        if not self._path.exists():
            return []
        raw = json.loads(self._path.read_text())
        emails = []
        for e in raw:
            emails.append(Email(
                id=str(e["id"]),
                from_addr=e["from"],
                to_addr=e["to"],
                subject=e["subject"],
                body=e["body"],
                date=_parse_dt(e["date"]),
                labels=e.get("labels", []),
                read=e.get("read", False),
            ))
        return sorted(emails, key=lambda x: x.date, reverse=True)

    def _save(self):
        data = []
        for e in self._emails:
            data.append({
                "id": e.id, "from": e.from_addr, "to": e.to_addr,
                "subject": e.subject, "body": e.body,
                "date": e.date.isoformat(), "labels": e.labels, "read": e.read,
            })
        self._path.write_text(json.dumps(data, indent=2))

    async def list_emails(self, limit: int = 20, label: str | None = None) -> list[Email]:
        result = self._emails
        if label:
            result = [e for e in result if label in e.labels]
        return result[:limit]

    async def get_email(self, email_id: str) -> Email | None:
        return next((e for e in self._emails if e.id == email_id), None)

    async def send_email(self, to: str, subject: str, body: str, cc: list[str] | None = None) -> Email:
        email = Email(
            id=str(len(self._emails) + 1),
            from_addr=os.getenv("MIKE_GOOGLE_EMAIL", "mike.astraos@gmail.com"),
            to_addr=to,
            subject=subject,
            body=body,
            date=datetime.now(),
            labels=["sent"],
            read=True,
            cc=cc or [],
        )
        self._emails.insert(0, email)
        self._save()
        return email

    async def search_emails(self, query: str) -> list[Email]:
        q = query.lower()
        return [
            e for e in self._emails
            if q in e.subject.lower() or q in e.body.lower()
            or q in e.from_addr.lower() or q in e.to_addr.lower()
        ]

    async def mark_read(self, email_id: str) -> bool:
        email = await self.get_email(email_id)
        if email:
            email.read = True
            self._save()
            return True
        return False


class MockCalendarProvider(CalendarProvider):
    """Serves calendar events from a JSON file."""

    def __init__(self, data_path: str | Path):
        self._path = Path(data_path)
        self._events = self._load()

    def _load(self) -> list[CalendarEvent]:
        if not self._path.exists():
            return []
        raw = json.loads(self._path.read_text())
        events = []
        for e in raw:
            events.append(CalendarEvent(
                id=e["id"],
                title=e["title"],
                start=_parse_dt(e["start"]),
                end=_parse_dt(e["end"]),
                location=e.get("location", ""),
                description=e.get("description", ""),
                attendees=e.get("attendees", []),
                recurring=e.get("recurring"),
                status=e.get("status", "confirmed"),
                color=e.get("color", "#3b82f6"),
            ))
        return sorted(events, key=lambda x: x.start)

    def _save(self):
        data = []
        for e in self._events:
            d = {
                "id": e.id, "title": e.title,
                "start": e.start.isoformat(), "end": e.end.isoformat(),
                "location": e.location, "description": e.description,
                "attendees": e.attendees, "color": e.color,
            }
            if e.recurring:
                d["recurring"] = e.recurring
            if e.status != "confirmed":
                d["status"] = e.status
            data.append(d)
        self._path.write_text(json.dumps(data, indent=2))

    async def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return [e for e in self._events if e.start >= start and e.start <= end]

    async def get_event(self, event_id: str) -> CalendarEvent | None:
        return next((e for e in self._events if e.id == event_id), None)

    async def create_event(
        self, title: str, start: datetime, end: datetime,
        location: str = "", description: str = "",
        attendees: list[str] | None = None,
    ) -> CalendarEvent:
        event = CalendarEvent(
            id=f"cal-{uuid.uuid4().hex[:6]}",
            title=title, start=start, end=end,
            location=location, description=description,
            attendees=attendees or [],
        )
        self._events.append(event)
        self._events.sort(key=lambda x: x.start)
        self._save()
        return event

    async def delete_event(self, event_id: str) -> bool:
        before = len(self._events)
        self._events = [e for e in self._events if e.id != event_id]
        if len(self._events) < before:
            self._save()
            return True
        return False
