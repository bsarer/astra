"""Factory to create the right provider based on DATA_PROVIDER env var.

Usage:
    from providers.factory import get_email_provider, get_calendar_provider

    email = get_email_provider()
    calendar = get_calendar_provider()
"""

import os
from pathlib import Path

from .base import EmailProvider, CalendarProvider


# Resolve persona data directory — check env var first, then relative paths
def _find_data_root() -> Path:
    # Explicit override via env
    if os.getenv("PERSONA_DATA_DIR"):
        return Path(os.getenv("PERSONA_DATA_DIR"))
    # Inside Docker: data is copied to /app/data
    docker_path = Path("/app/data/personas/mike")
    if docker_path.exists():
        return docker_path
    # Local dev: relative to this file -> providers -> astra-poc-vc -> PoC -> repo root -> data
    local_path = Path(__file__).resolve().parent.parent.parent / "data" / "personas" / "mike"
    if local_path.exists():
        return local_path
    # Fallback
    return local_path

_ROOT = _find_data_root()


def get_email_provider() -> EmailProvider:
    provider = os.getenv("DATA_PROVIDER", "mock").lower()

    if provider == "google":
        from .google import GoogleEmailProvider
        email = os.environ["MIKE_EMAIL"]
        password = os.environ["MIKE_EMAIL_PASSWORD"]
        return GoogleEmailProvider(email=email, app_password=password)
    
    if provider == "zoho":
        from .zoho import ZohoEmailProvider
        email = os.environ["MIKE_EMAIL"]
        password = os.environ["MIKE_EMAIL_PASSWORD"]
        return ZohoEmailProvider(email_addr=email, password=password)

    # Default: mock
    from .mock import MockEmailProvider
    return MockEmailProvider(data_path=_ROOT / "emails.json")


def get_calendar_provider() -> CalendarProvider:
    provider = os.getenv("DATA_PROVIDER", "mock").lower()

    if provider == "google":
        from .google import GoogleCalendarProvider
        email = os.environ["MIKE_EMAIL"]
        password = os.environ["MIKE_EMAIL_PASSWORD"]
        return GoogleCalendarProvider(email=email, app_password=password)

    # Default: mock (Zoho doesn't have calendar API in this setup)
    from .mock import MockCalendarProvider
    return MockCalendarProvider(data_path=_ROOT / "calendar.json")
