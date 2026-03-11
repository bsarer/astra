"""LangChain tools for email and calendar — backed by the provider layer."""

import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from langchain_core.tools import tool

from providers.factory import get_email_provider, get_calendar_provider


@tool
async def list_emails(limit: int = 10, label: Optional[str] = None) -> str:
    """List recent emails from the inbox. Optionally filter by label (e.g. 'work', 'travel', 'clients').
    Returns a JSON array of email summaries."""
    provider = get_email_provider()
    emails = await provider.list_emails(limit=limit, label=label)
    return json.dumps([
        {
            "id": e.id, "from": e.from_addr, "to": e.to_addr,
            "subject": e.subject, "date": e.date.isoformat(),
            "read": e.read, "labels": e.labels,
            "preview": e.body[:120] + "..." if len(e.body) > 120 else e.body,
        }
        for e in emails
    ], indent=2)


@tool
async def get_email(email_id: str) -> str:
    """Get the full content of a specific email by its ID."""
    provider = get_email_provider()
    email = await provider.get_email(email_id)
    if not email:
        return f"Email {email_id} not found."
    return json.dumps({
        "id": email.id, "from": email.from_addr, "to": email.to_addr,
        "subject": email.subject, "body": email.body,
        "date": email.date.isoformat(), "labels": email.labels, "read": email.read,
    }, indent=2)


@tool
async def search_emails(query: str) -> str:
    """Search emails by keyword. Searches subject, body, from, and to fields."""
    provider = get_email_provider()
    results = await provider.search_emails(query)
    return json.dumps([
        {
            "id": e.id, "from": e.from_addr, "subject": e.subject,
            "date": e.date.isoformat(), "preview": e.body[:100],
        }
        for e in results[:10]
    ], indent=2)


@tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email. Returns confirmation with the sent email details."""
    provider = get_email_provider()
    email = await provider.send_email(to=to, subject=subject, body=body)
    return f"Email sent successfully. ID: {email.id}, To: {email.to_addr}, Subject: {email.subject}"


@tool
async def list_calendar_events(days_ahead: int = 7) -> str:
    """List upcoming calendar events for the next N days (default 7).
    Returns a JSON array of events with title, time, location, and attendees."""
    provider = get_calendar_provider()
    now = datetime.now()
    end = now + timedelta(days=days_ahead)
    events = await provider.list_events(start=now, end=end)
    return json.dumps([
        {
            "id": e.id, "title": e.title,
            "start": e.start.isoformat(), "end": e.end.isoformat(),
            "location": e.location, "attendees": e.attendees,
            "description": e.description, "status": e.status,
        }
        for e in events
    ], indent=2)


@tool
async def get_calendar_event(event_id: str) -> str:
    """Get full details of a specific calendar event by ID."""
    provider = get_calendar_provider()
    event = await provider.get_event(event_id)
    if not event:
        return f"Event {event_id} not found."
    return json.dumps({
        "id": event.id, "title": event.title,
        "start": event.start.isoformat(), "end": event.end.isoformat(),
        "location": event.location, "description": event.description,
        "attendees": event.attendees, "status": event.status,
    }, indent=2)


@tool
async def create_calendar_event(
    title: str, start: str, end: str,
    location: str = "", description: str = "",
    attendees: Optional[List[str]] = None,
) -> str:
    """Create a new calendar event. Start and end should be ISO datetime strings.
    Example: start='2026-03-15T10:00:00', end='2026-03-15T11:00:00'"""
    provider = get_calendar_provider()
    event = await provider.create_event(
        title=title,
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
        location=location,
        description=description,
        attendees=attendees,
    )
    return f"Event created: {event.title} on {event.start.isoformat()} (ID: {event.id})"


# All email/calendar tools for easy import
email_calendar_tools = [
    list_emails, get_email, search_emails, send_email,
    list_calendar_events, get_calendar_event, create_calendar_event,
]
