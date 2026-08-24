"""Pure query logic over the durable log. No MCP or agent concerns here.

An "activity" is a flattened SAD violation event: the envelope's ref_id + ts_ms
merged with the payload fields.
"""

from __future__ import annotations

from typing import Any

from events import EVENT_TYPE
from models import Activity

_MAX = 10_000


def _to_activity(event: Any) -> Activity:
    """Flatten an event envelope into an Activity row."""
    return {"ref_id": event.ref_id, "ts_ms": event.ts_ms, **event.payload}


def all_activities(log: Any, limit: int = _MAX) -> list[Activity]:
    """All activities from the log, oldest first."""
    return [_to_activity(e) for e in log.read(event_type=EVENT_TYPE, limit=limit)]


def activity_by_zone(log: Any, zone: str, limit: int = _MAX) -> list[Activity]:
    """Activities filtered to a single zone."""
    return [a for a in all_activities(log, limit) if a.get("zone") == zone]


def activity_by_zone_timestamp(
    log: Any,
    zone: str,
    start_ms: int | None = None,
    end_ms: int | None = None,
    limit: int = _MAX,
) -> list[Activity]:
    """Activities for a zone within an optional epoch-ms range."""
    out: list[Activity] = []
    for a in all_activities(log, limit):
        if a.get("zone") != zone:
            continue
        ts = a.get("ts_ms", 0)
        if start_ms is not None and ts < start_ms:
            continue
        if end_ms is not None and ts > end_ms:
            continue
        out.append(a)
    return out


def all_zones(log: Any, limit: int = _MAX) -> list[str]:
    """Distinct zone names that have any activity."""
    return sorted({a["zone"] for a in all_activities(log, limit) if a.get("zone")})
