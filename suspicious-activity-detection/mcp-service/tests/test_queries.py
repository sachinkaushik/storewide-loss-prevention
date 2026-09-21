"""Unit tests for the SAD query helpers (pure log queries)."""

from __future__ import annotations

from mcp_service_sdk import SQLiteLog

import events
import queries


def _seed(log: SQLiteLog) -> None:
    def ev(zone: str, ref: str, ts: int):
        from mcp_service_sdk.envelope import EventEnvelope

        return EventEnvelope(
            event_type=events.EVENT_TYPE,
            service="suspicious_activity",
            store_id="store_001",
            payload={
                "event_name": "food_safety_violation" if zone == "kitchen-prep" else "loitering",
                "use_case": "kitchen" if zone == "kitchen-prep" else "retail",
                "zone": zone,
                "pose": "floor_to_food_area" if zone == "kitchen-prep" else "loiter",
                "severity": "high",
                "camera_id": "lp-camera1",
                "object_id": ref,
                "description": "item picked from floor and placed back in the food area",
                "frame": f"s3://behavioral-frames/{ref}.jpg",
                "station": "prep" if zone == "kitchen-prep" else "checkout",
                "shift": "lunch",
            },
            ref_id=ref,
            ts_ms=ts,
        )

    log.append(ev("kitchen-prep", "a", 100))
    log.append(ev("kitchen-prep", "b", 200))
    log.append(ev("checkout-2", "c", 300))
    log.append(ev("kitchen-prep", "a", 100))  # idempotent duplicate


def test_all_activities_idempotent():
    log = SQLiteLog(service="t")
    _seed(log)
    assert len(queries.all_activities(log)) == 3


def test_activity_by_zone():
    log = SQLiteLog(service="t")
    _seed(log)
    assert len(queries.activity_by_zone(log, "kitchen-prep")) == 2
    assert len(queries.activity_by_zone(log, "checkout-2")) == 1


def test_activity_by_zone_timestamp():
    log = SQLiteLog(service="t")
    _seed(log)
    assert len(queries.activity_by_zone_timestamp(log, "kitchen-prep", start_ms=150)) == 1
    assert len(queries.activity_by_zone_timestamp(log, "kitchen-prep", end_ms=150)) == 1


def test_all_zones():
    log = SQLiteLog(service="t")
    _seed(log)
    assert queries.all_zones(log) == ["checkout-2", "kitchen-prep"]


def test_retrospective_frame_search():
    log = SQLiteLog(service="t")
    _seed(log)
    results = queries.retrospective_frame_search(
        log,
        query="floor",
        use_case="kitchen",
        event_name="food_safety_violation",
        start_ms=50,
        end_ms=250,
    )
    assert [r["ref_id"] for r in results] == ["a", "b"]


def test_trend_counts():
    log = SQLiteLog(service="t")
    _seed(log)
    assert queries.trend_counts(log, use_case="kitchen") == [
        {"station": "prep", "shift": "lunch", "count": 2}
    ]
