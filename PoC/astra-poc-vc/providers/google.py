"""Google providers (Gmail + Calendar) — real API implementation.

Requires:
  pip install google-api-python-client google-auth-oauthlib

Set DATA_PROVIDER=google and provide credentials in .env to use.
This is a stub — implement methods when ready to connect to real Google APIs.
"""

from datetime import datetime
from .base import Email, EmailProvider, CalendarEvent, CalendarProvider


class GoogleEmailProvider(EmailProvider):
    """Gmail API provider."""

    def __init__(self, email: str, app_password: str):
        self._email = email
        self._app_password = app_password
        # TODO: Initialize Gmail API client
        # from google.oauth2.credentials import Credentials
        # from googleapiclient.discovery import build

    async def list_emails(self, limit: int = 20, label: str | None = None) -> list[Email]:
        raise NotImplementedError("Google Gmail provider not yet implemented")

    async def get_email(self, email_id: str) -> Email | None:
        raise NotImplementedError("Google Gmail provider not yet implemented")

    async def send_email(self, to: str, subject: str, body: str, cc: list[str] | None = None) -> Email:
        raise NotImplementedError("Google Gmail provider not yet implemented")

    async def search_emails(self, query: str) -> list[Email]:
        raise NotImplementedError("Google Gmail provider not yet implemented")

    async def mark_read(self, email_id: str) -> bool:
        raise NotImplementedError("Google Gmail provider not yet implemented")

    async def download_attachment(self, email_id: str, attachment_name: str) -> tuple[str, bytes]:
        raise NotImplementedError("Google Gmail provider not yet implemented")


class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar API provider."""

    def __init__(self, email: str, app_password: str, calendar_id: str = "primary"):
        self._email = email
        self._app_password = app_password
        self._calendar_id = calendar_id
        # TODO: Initialize Calendar API client

    async def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        raise NotImplementedError("Google Calendar provider not yet implemented")

    async def get_event(self, event_id: str) -> CalendarEvent | None:
        raise NotImplementedError("Google Calendar provider not yet implemented")

    async def create_event(
        self, title: str, start: datetime, end: datetime,
        location: str = "", description: str = "",
        attendees: list[str] | None = None,
    ) -> CalendarEvent:
        raise NotImplementedError("Google Calendar provider not yet implemented")

    async def delete_event(self, event_id: str) -> bool:
        raise NotImplementedError("Google Calendar provider not yet implemented")
