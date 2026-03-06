"""Typed JSON Message Protocol for WebSocket communication.

Defines all server→client and client→server message types,
discriminated union types, and serialization/parsing helpers.
"""

import json
from typing import Literal, TypedDict, Union


# --- Grid Options ---

class GridOptions(TypedDict, total=False):
    w: int  # Grid columns (1-12)
    h: int  # Grid rows (height in 10px cells)
    x: int  # Column position
    y: int  # Row position


# --- Server → Client Messages ---

class TokenMessage(TypedDict):
    type: Literal["token"]
    content: str


class WidgetMessage(TypedDict):
    type: Literal["widget"]
    id: str
    html: str
    grid: GridOptions


class DoneMessage(TypedDict):
    type: Literal["done"]


class ErrorMessage(TypedDict):
    type: Literal["error"]
    content: str


class SessionInitMessage(TypedDict):
    type: Literal["session_init"]
    session_id: str


# --- Client → Server Messages ---

class UserMessage(TypedDict):
    type: Literal["user_message"]
    content: str


class WidgetEventMessage(TypedDict):
    type: Literal["widget_event"]
    event_name: str
    payload: dict


# --- Union Types ---

ServerMessage = Union[
    TokenMessage, WidgetMessage, DoneMessage, ErrorMessage, SessionInitMessage
]
ClientMessage = Union[UserMessage, WidgetEventMessage]


# --- Health Check ---

class HealthResponse(TypedDict):
    status: Literal["ok"]


# --- Valid client message type values ---

_CLIENT_MESSAGE_TYPES = {"user_message", "widget_event"}


def parse_client_message(raw: str) -> ClientMessage:
    """Parse a raw JSON string into a validated ClientMessage.

    Args:
        raw: JSON string representing a client message.

    Returns:
        A ClientMessage (UserMessage or WidgetEventMessage).

    Raises:
        ValueError: If the string is not valid JSON or has an unknown/missing type field.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    msg_type = data.get("type")
    if msg_type not in _CLIENT_MESSAGE_TYPES:
        raise ValueError(f"Unknown message type: {msg_type!r}")

    return data  # type: ignore[return-value]


def serialize_server_message(msg: ServerMessage) -> str:
    """Serialize a ServerMessage dict to a JSON string.

    Args:
        msg: A ServerMessage typed dict.

    Returns:
        JSON string representation of the message.
    """
    return json.dumps(msg)
