"""End-to-end demo of the four SAD tools (no MCP client needed).

    python scripts/demo_e2e.py     # after `pip install -e .`
"""

from __future__ import annotations

from tools import ingest_alert, svc


def main() -> None:
    # SAD pipeline publishes activities (the MQTT hand-off seam).
    ingest_alert("kitchen-prep", "item-drop-return", "high", "cam-3", "p-1001",
                 "Object dropped on floor and returned to prep area", ref_id="mqtt-1")
    ingest_alert("kitchen-prep", "reach-over", "medium", "cam-3", "p-1002",
                 "Reach-over sneeze guard", ref_id="mqtt-2")
    ingest_alert("checkout-2", "item-conceal", "high", "cam-7", "p-1003",
                 "Possible concealment at self-checkout", ref_id="mqtt-3")
    ingest_alert("checkout-2", "item-conceal", "high", "cam-7", "p-1003",
                 "Duplicate MQTT redelivery", ref_id="mqtt-3")  # idempotent

    print("Get_all_activities:", len(svc._read_tools["Get_all_activities"].fn()), "(idempotent = 3)")
    print("Get_all_zones:", svc._read_tools["Get_all_zones"].fn())
    print("Get_activity_by_zone(kitchen-prep):",
          len(svc._read_tools["Get_activity_by_zone"].fn("kitchen-prep")))

    acts = svc._read_tools["Get_all_activities"].fn()
    lo = min(a["ts_ms"] for a in acts)
    print("Get_activity_by_zone_timestamp(kitchen-prep, from lo):",
          len(svc._read_tools["Get_activity_by_zone_timestamp"].fn("kitchen-prep", start_ms=lo)))

    # gated actions
    print("notify_operator (auto):",
          svc.call_action("notify_operator", zone="kitchen-prep", message="High-severity SAD event")["executed"])
    print("open_case (needs approval):",
          svc.call_action("open_case", zone="checkout-2", object_id="p-1003", severity="high")["reason"])

    d = svc.describe()
    print("describe read tools:", list(d["read_tools"]))
    print("describe act tools:", {k: v["gate"] for k, v in d["act_tools"].items()})
    print("\nOK — SAD MCP (standard package) works end-to-end.")


if __name__ == "__main__":
    main()
