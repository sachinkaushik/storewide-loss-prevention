"""Unit tests for the SAD query helpers (pure log queries)."""

from __future__ import annotations

from mcp_service_base import SQLiteLog

import events
import queries


def _seed(log: SQLiteLog) -> None:
    def ev(zone: str, ref: str, ts: int):
        from mcp_service_base.envelope import EventEnvelope

        return EventEnvelope(
            event_type=events.EVENT_TYPE,
            service="suspicious_activity",
            store_id="store_001",
            payload={"zone": zone, "severity": "high"},
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
