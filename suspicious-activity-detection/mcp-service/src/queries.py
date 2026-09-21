"""Pure query logic over the durable log. No MCP or agent concerns here.

An "activity" is a flattened SAD violation event: the envelope's ref_id + ts_ms
merged with the payload fields.
"""

from __future__ import annotations

from typing import Any

from events import EVENT_TYPE
from models import Activity, TrendCount

_MAX = 10_000


def _to_activity(event: Any) -> Activity:
    """Flatten an event envelope into an Activity row."""
    return {"ref_id": event.ref_id, "ts_ms": event.ts_ms, **event.payload}


def _matches_time(activity: Activity, start_ms: int | None, end_ms: int | None) -> bool:
    ts = activity.get("ts_ms", 0)
    if start_ms is not None and ts < start_ms:
        return False
    if end_ms is not None and ts > end_ms:
        return False
    return True


def _matches_text(activity: Activity, query: str | None) -> bool:
    if not query:
        return True
    needle = query.lower()
    fields = (
        activity.get("event_name", ""),
        activity.get("zone", ""),
        activity.get("pose", ""),
        activity.get("description", ""),
        activity.get("frame", ""),
    )
    return any(needle in str(field).lower() for field in fields)


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
        if not _matches_time(a, start_ms, end_ms):
            continue
        out.append(a)
    return out


def retrospective_frame_search(
    log: Any,
    query: str | None = None,
    start_ms: int | None = None,
    end_ms: int | None = None,
    zone: str | None = None,
    event_name: str | None = None,
    use_case: str | None = None,
    limit: int = _MAX,
) -> list[Activity]:
    """Search logged SAD events with frame references for retrospective review."""
    out: list[Activity] = []
    for a in all_activities(log, limit):
        if zone and a.get("zone") != zone:
            continue
        if event_name and a.get("event_name") != event_name:
            continue
        if use_case and a.get("use_case") != use_case:
            continue
        if not _matches_time(a, start_ms, end_ms):
            continue
        if not _matches_text(a, query):
            continue
        out.append(a)
    return out


def trend_counts(
    log: Any,
    start_ms: int | None = None,
    end_ms: int | None = None,
    event_name: str | None = None,
    use_case: str | None = None,
    limit: int = _MAX,
) -> list[TrendCount]:
    """Count matching events by station and shift."""
    buckets: dict[tuple[str, str], int] = {}
    for a in all_activities(log, limit):
        if event_name and a.get("event_name") != event_name:
            continue
        if use_case and a.get("use_case") != use_case:
            continue
        if not _matches_time(a, start_ms, end_ms):
            continue
        key = (a.get("station") or a.get("zone") or "unknown", a.get("shift") or "unknown")
        buckets[key] = buckets.get(key, 0) + 1
    return [
        {"station": station, "shift": shift, "count": count}
        for (station, shift), count in sorted(buckets.items())
    ]


def all_zones(log: Any, limit: int = _MAX) -> list[str]:
    """Distinct zone names that have any activity."""
    return sorted({a["zone"] for a in all_activities(log, limit) if a.get("zone")})
