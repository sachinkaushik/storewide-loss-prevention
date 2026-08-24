"""Typed structures returned by the SAD tools (standard MCP structured output)."""

from __future__ import annotations

from typing import TypedDict


class Activity(TypedDict):
    """One suspicious-activity event, flattened for the agent."""

    ref_id: str
    ts_ms: int
    zone: str
    pose: str
    severity: str
    camera_id: str
    object_id: str
    description: str
