"""A2UI v0.8 message models for the declarative UI protocol.

Pydantic v2 models for A2UI message types: SurfaceUpdate, BeginRendering,
DeleteSurface, DataModelUpdate, and the A2UIComponent adjacency list model.
"""

from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel


class A2UIComponent(BaseModel):
    """A single component in the A2UI adjacency list model.

    Components are stored flat — layout components reference children by ID.
    """

    id: str
    type: str  # "Text", "Button", "Card", "Row", "Column", "StockTicker", etc.
    props: dict[str, Any] = {}
    children: list[str] = []  # Child component IDs (adjacency list)


class SurfaceUpdate(BaseModel):
    """Defines or updates UI components on a named surface."""

    message_type: Literal["surfaceUpdate"] = "surfaceUpdate"
    surface_id: str
    components: list[A2UIComponent]


class BeginRendering(BaseModel):
    """Signals the client to render a surface from a root component."""

    message_type: Literal["beginRendering"] = "beginRendering"
    surface_id: str
    root: str  # Root component ID


class DeleteSurface(BaseModel):
    """Removes a previously rendered surface."""

    message_type: Literal["deleteSurface"] = "deleteSurface"
    surface_id: str


class DataModelUpdate(BaseModel):
    """Updates application state bound to UI components (Phase 2 stub)."""

    message_type: Literal["dataModelUpdate"] = "dataModelUpdate"
    surface_id: str
    contents: list[dict] = []  # [{"path": "/stocks/AAPL/price", "value": 189.50}]


A2UIMessage = Union[SurfaceUpdate, BeginRendering, DeleteSurface, DataModelUpdate]
