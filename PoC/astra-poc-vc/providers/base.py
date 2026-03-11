"""Abstract base classes for email and calendar providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Email:
    id: str
    from_addr: str
    to_addr: str
    subject: str
    body: str
    date: datetime
    labels: list[str] = field(default_factory=list)
    read: bool = False
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)


@dataclass
class CalendarEvent:
    id: str
    title: str
    start: datetime
    end: datetime
    location: str = ""
    description: str = ""
    attendees: list[str] = field(default_factory=list)
    recurring: Optional[str] = None
    status: str = "confirmed"
    color: str = "#3b82f6"


class EmailProvider(ABC):
    """Interface for email services."""

    @abstractmethod
    async def list_emails(self, limit: int = 20, label: str | None = None) -> list[Email]:
        ...

    @abstractmethod
    async def get_email(self, email_id: str) -> Email | None:
        ...

    @abstractmethod
    async def send_email(self, to: str, subject: str, body: str, cc: list[str] | None = None) -> Email:
        ...

    @abstractmethod
    async def search_emails(self, query: str) -> list[Email]:
        ...

    @abstractmethod
    async def mark_read(self, email_id: str) -> bool:
        ...


class CalendarProvider(ABC):
    """Interface for calendar services."""

    @abstractmethod
    async def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        ...

    @abstractmethod
    async def get_event(self, event_id: str) -> CalendarEvent | None:
        ...

    @abstractmethod
    async def create_event(
        self, title: str, start: datetime, end: datetime,
        location: str = "", description: str = "",
        attendees: list[str] | None = None,
    ) -> CalendarEvent:
        ...

    @abstractmethod
    async def delete_event(self, event_id: str) -> bool:
        ...
