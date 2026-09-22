"""Unit tests for alert MQTT payload normalization."""

from __future__ import annotations

from mqtt_ingest import normalize_alert


def test_normalize_kitchen_food_safety_alert():
    event = normalize_alert(
        "alerts/food_safety_violation",
        {
            "alert_id": "alert-1",
            "alert_type": "FOOD_SAFETY_VIOLATION",
            "alert_level": "CRITICAL",
            "metadata": {
                "person_id": "p-1001",
                "zone_id": "kitchen-prep",
                "zone_name": "kitchen-prep",
                "severity": "CRITICAL",
            },
            "payload": {
                "event_type": "food_safety_violation",
                "description": "Item picked from floor and placed back in food area",
                "frames_analyzed": 8,
            },
        },
        use_case="kitchen",
    )

    assert event == {
        "zone": "kitchen-prep",
        "pose": "food_safety_violation",
        "severity": "critical",
        "camera_id": "unknown",
        "object_id": "p-1001",
        "description": "Item picked from floor and placed back in food area",
        "ref_id": "alert-1",
        "event_name": "food_safety_violation",
        "use_case": "kitchen",
        "frame": "",
        "station": "kitchen-prep",
        "shift": "unknown",
    }


def test_normalize_retail_alert_without_alert_id_gets_stable_ref():
    alert = {
        "alert_type": "LOITERING",
        "metadata": {"person_id": "p-2001", "zone_id": "aisle1"},
        "payload": {"dwell_seconds": 60},
    }

    event = normalize_alert("alerts/loitering", alert, use_case="retail")

    assert event["zone"] == "aisle1"
    assert event["object_id"] == "p-2001"
    assert event["event_name"] == "loitering"
    assert event["use_case"] == "retail"
    assert event["ref_id"].startswith("mqtt-")
    assert event["ref_id"] == normalize_alert("alerts/loitering", alert, use_case="retail")["ref_id"]