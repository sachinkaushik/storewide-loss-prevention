"""Seed kitchen food-safety violations into the SAD durable log.

Run once so the Hermes read tools (Get_all_activities, Get_activity_by_zone,
Get_all_zones) and notify_operator return real data during the demo:

    .venv/bin/python scripts/seed_demo.py

Writes to the same persistent log the running MCP server reads (see config.py).
Re-runs are idempotent because each event carries a stable ref_id.
"""

from __future__ import annotations

import queries
from tools import ingest_alert, svc

# zone, pose, severity, camera_id, object_id, description, ref_id
_EVENTS = [
    ("kitchen-prep", "item-drop-return", "high", "cam-3", "p-1001",
     "Object dropped on the floor and returned to the prep area", "seed-1"),
    ("kitchen-prep", "item-drop-return", "high", "cam-3", "p-1004",
     "Utensil dropped on the floor and placed back on the prep counter", "seed-2"),
    ("kitchen-prep", "reach-over", "medium", "cam-3", "p-1002",
     "Reach-over the sneeze guard near ready-to-eat food", "seed-3"),
    ("grill-station", "bare-hand-contact", "high", "cam-5", "p-1005",
     "Bare-hand contact with ready-to-eat food at the grill", "seed-4"),
    ("dish-return", "item-drop-return", "low", "cam-8", "p-1006",
     "Item dropped and returned near the dish return", "seed-5"),
]


def main() -> None:
    for zone, pose, severity, camera_id, object_id, description, ref_id in _EVENTS:
        ingest_alert(zone, pose, severity, camera_id, object_id, description, ref_id=ref_id)
    activities = queries.all_activities(svc.log)
    print(f"seeded {len(activities)} activities across zones {queries.all_zones(svc.log)}")


if __name__ == "__main__":
    main()
