"""SAD event schema and the pipeline ingest seam.

An "activity" is one SAD violation event. The SAD MQTT consumer (topics
alerts/#, ba/results) calls `ingest_alert` to publish one; emit() writes it to
the durable log first, then fans out to the agent.
"""

from __future__ import annotations

from typing import Any

EVENT_TYPE = "sad_violation"

SCHEMA: dict[str, str] = {
    "zone": "str",
    "pose": "str",            # e.g. reach-over, item-conceal, slip
    "severity": "str",        # low | medium | high
    "camera_id": "str",
    "object_id": "str",       # SceneScape cross-camera person id
    "description": "str",     # VLM one-line summary
}


def ingest_alert(
    svc: Any,
    zone: str,
    pose: str,
    severity: str,
    camera_id: str,
    object_id: str,
    description: str,
    ref_id: str | None = None,
) -> None:
    svc.emit(
        EVENT_TYPE,
        {
            "zone": zone,
            "pose": pose,
            "severity": severity,
            "camera_id": camera_id,
            "object_id": object_id,
            "description": description,
        },
        ref_id=ref_id,  # MQTT message id -> idempotent replay
    )
