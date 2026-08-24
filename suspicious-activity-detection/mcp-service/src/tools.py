"""Wires the ServiceServer: registers the event type, the read tools, and the
gated act tools. Domain query logic lives in tools.py; this file is the wiring.
"""

from __future__ import annotations

from typing import Annotated

from mcp_service_base import GateLevel, ServiceServer
from pydantic import Field

import queries
from config import get_settings
from events import EVENT_TYPE, SCHEMA
from events import ingest_alert as _ingest_alert
from models import Activity

_settings = get_settings()

svc = ServiceServer(service="suspicious_activity", store_id=_settings.store_id)
svc.register_event_type(EVENT_TYPE, schema=SCHEMA)


def ingest_alert(
    zone: str,
    pose: str,
    severity: str,
    camera_id: str,
    object_id: str,
    description: str,
    ref_id: str | None = None,
) -> None:
    """Pipeline hand-off: the SAD MQTT consumer calls this to publish a violation."""
    _ingest_alert(svc, zone, pose, severity, camera_id, object_id, description, ref_id)


# -- read tools -----------------------------------------------------------
# Descriptions come from the docstrings; parameter docs from Annotated Field.
@svc.read_tool("Get_all_activities")
def Get_all_activities() -> list[Activity]:
    """List every recorded suspicious-activity event, oldest first."""
    return queries.all_activities(svc.log)


@svc.read_tool("Get_activity_by_zone")
def Get_activity_by_zone(
    zone: Annotated[str, Field(description="Zone name, e.g. 'kitchen-prep'.")],
) -> list[Activity]:
    """List suspicious-activity events for a single zone."""
    return queries.activity_by_zone(svc.log, zone)


@svc.read_tool("Get_activity_by_zone_timestamp")
def Get_activity_by_zone_timestamp(
    zone: Annotated[str, Field(description="Zone name to filter by.")],
    start_ms: Annotated[
        int | None, Field(description="Inclusive lower bound, epoch milliseconds.")
    ] = None,
    end_ms: Annotated[
        int | None, Field(description="Inclusive upper bound, epoch milliseconds.")
    ] = None,
) -> list[Activity]:
    """List suspicious-activity events for a zone within an epoch-ms time range."""
    return queries.activity_by_zone_timestamp(svc.log, zone, start_ms, end_ms)


@svc.read_tool("Get_all_zones")
def Get_all_zones() -> list[str]:
    """List the distinct zones that have recorded any activity."""
    return queries.all_zones(svc.log)


# -- act tools (narrow, gated) --------------------------------------------
@svc.act_tool("notify_operator", level=GateLevel.AUTOMATIC, max_calls=10, per_seconds=60.0)
def notify_operator(
    zone: Annotated[str, Field(description="Zone the event occurred in.")],
    message: Annotated[str, Field(description="Operator-facing message.")],
) -> dict:
    """Surface a suspicious-activity / food-safety event to the store operator."""
    return {"notified": "operator", "zone": zone, "message": message}


@svc.act_tool("open_case", level=GateLevel.NEEDS_APPROVAL)
def open_case(
    zone: Annotated[str, Field(description="Zone the case concerns.")],
    object_id: Annotated[str, Field(description="SceneScape cross-camera person id.")],
    severity: Annotated[str, Field(description="low | medium | high.")],
) -> dict:
    """Open a loss-prevention investigation case. Requires human approval."""
    return {"case_opened": True, "zone": zone, "object_id": object_id, "severity": severity}
