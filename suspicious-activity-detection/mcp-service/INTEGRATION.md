# SAD MCP Service — Integration Guide

How the **Suspicious Activity Detection (SAD) MCP service** is built on the generic
`mcp-service-base` library, how it exposes tools to the Central QSR Agent, and how
events fan out from the SAD pipeline to the agent.

- **Service name:** `suspicious_activity`
- **Built on:** [`mcp-service-base`](https://github.com/sachinkaushik/mcp-service-base) (pinned `v0.1.3`)
- **MCP SDK:** official `mcp` (2.x, `MCPServer`)
- **Location:** `storewide-loss-prevention/suspicious-activity-detection/mcp-service`

---

## 1. What this service is

The SAD pipeline (YOLO-pose + VLM behavioral analysis) detects suspicious or
unsafe activity in camera zones. This MCP service makes those detections available
to the agent through the **uniform Service Contract**: the agent reads history and
acts, and it cannot tell this service apart from any other (real or simulated).

The service writes **only domain code** — its event schema, query helpers, and
tool declarations. Everything else (durable log, event delivery/fan-out, policy
gate, telemetry, MCP scaffolding) is inherited from `mcp-service-base`.

---

## 2. How it connects to the generic `mcp-service-base`

`mcp-service-base` is a **library**, not a running server. This service imports it,
creates one `ServiceServer`, registers its tools, and runs it — that instance *is*
the MCP server the agent connects to.

```mermaid
flowchart TB
    subgraph SAD["SAD MCP service (this repo)"]
        TOOLS["tools.py<br/>MCP tool declarations"]
        QUERIES["queries.py<br/>pure log queries"]
        EVENTS["events.py<br/>schema + ingest seam"]
        MODELS["models.py<br/>Activity type"]
        CONFIG["config.py<br/>env settings"]
        MAIN["main.py<br/>entrypoint"]
    end
    subgraph BASE["mcp-service-base (imported library)"]
        SS["ServiceServer"]
        LOG["SQLiteLog (durable log)"]
        DEL["Delivery (fan-out)"]
        POL["PolicyGate"]
        TEL["Telemetry"]
        MCP["MCP scaffolding<br/>describe/subscribe/read/act"]
    end
    AGENT["Central QSR Agent<br/>(Hermes — MCP client)"]

    TOOLS -->|register read and act tools| SS
    TOOLS --> QUERIES --> LOG
    EVENTS -->|svc.emit| SS
    MAIN -->|svc.run| SS
    SS --- LOG & DEL & POL & TEL & MCP
    MCP <-->|describe, subscribe, read| AGENT
    POL -->|gated act| AGENT
```

**Dependency wiring** (`pyproject.toml`):

```toml
dependencies = [
  "mcp-service-base[mcp] @ git+https://github.com/sachinkaushik/mcp-service-base.git@v0.1.3",
]
```

The `[mcp]` extra pulls in the official MCP SDK. The `@v0.1.3` pin keeps builds
reproducible.

---

## 3. Package structure

| File | Responsibility |
|---|---|
| `src/tools.py` | **The MCP tools** — creates `svc = ServiceServer(...)`, declares read/act tools, and `ingest_alert`. Edit this to add/change tools. |
| `src/queries.py` | Internal pure query logic over the durable log. Not exposed to the agent. |
| `src/events.py` | Event type name + payload schema + `ingest_alert` (the pipeline hand-off seam). |
| `src/models.py` | `Activity` `TypedDict` — structured output type. |
| `src/config.py` | Env-driven settings (store id, transport, host, port). |
| `src/main.py` | Entrypoint / console script (`sad-mcp`). |
| `scripts/demo_e2e.py` | End-to-end demo (no MCP client needed). |
| `tests/test_queries.py` | Unit tests for the query helpers. |

---

## 4. The Service Contract (what the agent sees)

Every service on `mcp-service-base` exposes the same four MCP capabilities:

| Capability | This service |
|---|---|
| **describe** | Advertises the `sad_violation` event schema + all read/act tools with descriptions. |
| **subscribe** | Agent registers interest (event + condition + callback). |
| **read tools** | `Get_all_activities`, `Get_activity_by_zone`, `Get_activity_by_zone_timestamp`, `Get_all_zones`. |
| **act tools** | `notify_operator` (auto), `open_case` (human approval). |

### Read tools

| Tool | Params | Returns |
|---|---|---|
| `Get_all_activities` | — | `list[Activity]` — every recorded activity |
| `Get_activity_by_zone` | `zone` | activities in that zone |
| `Get_activity_by_zone_timestamp` | `zone`, `start_ms?`, `end_ms?` | zone activities in an epoch-ms range |
| `Get_all_zones` | — | distinct zones with activity |

Descriptions come from the function **docstrings**; parameter docs from
`Annotated[..., Field(description=...)]` — the standard MCP convention.

### Act tools (gated by the Policy Gate)

| Tool | Gate | Guardrail |
|---|---|---|
| `notify_operator(zone, message)` | **automatic** | rate-limited 10/min |
| `open_case(zone, object_id, severity)` | **needs approval** | high-severity cases are human-in-the-loop |

An action off the allow-list (e.g. `lock_register`) is **blocked** and logged.

### The `Activity` shape

```python
class Activity(TypedDict):
    ref_id: str        # source event id (MQTT message id) — idempotent
    ts_ms: int         # epoch milliseconds
    zone: str
    pose: str          # reach-over, item-conceal, slip, ...
    severity: str      # low | medium | high
    camera_id: str
    object_id: str     # SceneScape cross-camera person id
    description: str    # VLM one-line summary
```

---

## 5. How events fan out (SAD pipeline → agent)

The SAD MQTT consumer publishes a violation by calling **one function**,
`ingest_alert(...)`. From there `mcp-service-base` does *emit-to-log-first, then
fan out*:

```mermaid
sequenceDiagram
    participant P as SAD pipeline (MQTT alerts, ba results)
    participant I as ingest_alert()
    participant SS as ServiceServer.emit()
    participant LOG as Durable log (SQLite)
    participant DEL as Delivery (fan-out)
    participant A as Agent inbox

    P->>I: violation (zone, pose, severity, ... , ref_id=mqtt_msg_id)
    I->>SS: emit("sad_violation", payload, ref_id)
    SS->>LOG: append (idempotent on ref_id)
    Note over LOG: written FIRST — nothing lost, replayable
    SS->>DEL: dispatch(event)
    DEL->>A: push to enabled sinks (with retries)
    Note over DEL: EventHub (default) / Webhook / Disabled
```

Key properties:

- **Log first.** The event is persisted to the service's own durable log *before*
  any delivery — so nothing is dropped and the whole run is replayable for
  benchmarking/debugging.
- **Idempotent.** `ref_id` = the MQTT message id; a redelivered message is stored
  once, never double-counted.
- **Fan-out sinks** (chosen by config in `mcp-service-base`):
  - **EventHub** (default) — de-dupes, fans out, retries; the agent inbox listens here.
  - **Webhook** — HTTP callback for partners / other agent frameworks.
  - **Disabled** — clean benchmark runs (log only, no delivery).
- **Bounded retries.** Failed deliveries are retried with backoff; nothing fails silently.

### Wiring the pipeline (the seam)

```python
from tools import ingest_alert   # from src/tools.py

ingest_alert(
    zone="kitchen-prep",
    pose="item-drop-return",
    severity="high",
    camera_id="cam-3",
    object_id="p-1001",
    description="Object dropped on floor and returned to prep area",
    ref_id=mqtt_message_id,     # -> idempotent replay
)
```

Drop this call into the SAD MQTT consumer (`behavioral-analysis/src`) wherever a
result/alert is produced.

---

## 6. How the agent reads and acts

```mermaid
sequenceDiagram
    participant A as Agent (Hermes)
    participant MCP as SAD MCP server
    participant PG as Policy Gate
    participant Q as queries.py + log

    A->>MCP: describe (on connect)
    A->>MCP: subscribe sad_violation
    A->>MCP: read Get_activity_by_zone("kitchen-prep")
    MCP->>Q: query durable log
    Q-->>A: list[Activity]
    A->>PG: act notify_operator(zone, message)
    alt allowed (automatic)
        PG->>MCP: execute
        MCP-->>A: result
    else needs approval / blocked
        PG-->>A: hold / refuse (logged)
    end
```

The agent connects as a standard MCP client. Because the contract is uniform,
onboarding this service needs **no agent code changes** — it discovers everything
via `describe`.

---

## 7. How it runs

The service runs as a **host process** (no container image to maintain), managed
by the Makefile and started/stopped with the main stack.

| Command | Effect |
|---|---|
| `make up` | Brings up the LP/SceneScape stack **and** starts the SAD MCP host process. |
| `make down` | Stops the stack **and** the MCP host process. |
| `make mcp-up` | Start just the MCP service (creates venv, `pip install -e`, launches). |
| `make mcp-down` | Stop just the MCP service. |

Details:

- **Transport:** `streamable-http` in deployment (so the agent can reach it over
  the network); `stdio` locally for CLI use.
- **Endpoint:** `http://localhost:9000/mcp` (override port with `MCP_PORT`).
- **Process:** `nohup` host process; PID in `/tmp/sad-mcp.pid`, logs in `/tmp/sad-mcp.log`.
- **Venv:** `mcp-service/.venv` (auto-created on first `make up`).

> **Networking note:** the agent reaches this at `http://<host>:9000/mcp`. If Hermes
> runs inside the compose network, use the host address (e.g. `host.docker.internal:9000`)
> rather than a compose service DNS name, since this is a host process, not a container.

---

## 8. Configuration (env vars)

| Var | Default | Meaning |
|---|---|---|
| `STORE_ID` | `store_001` | Store identity stamped on every event. |
| `MCP_TRANSPORT` | `stdio` | `stdio` \| `sse` \| `streamable-http`. Makefile sets `streamable-http`. |
| `MCP_HOST` | `0.0.0.0` | Bind host for HTTP transports. |
| `MCP_PORT` | `9000` | Bind port for HTTP transports. |

---

## 9. Develop & verify

```bash
cd mcp-service
python3 -m venv .venv
.venv/bin/pip install -e .        # installs mcp-service-base from GitHub + this package

# run the server
.venv/bin/sad-mcp                 # stdio; set MCP_TRANSPORT=streamable-http for HTTP

# tests + demo (no MCP client needed)
.venv/bin/python -m pytest -q tests/
.venv/bin/python scripts/demo_e2e.py
```

---

## 10. Versioning

- This service pins `mcp-service-base` to a **git tag** (`@v0.1.3`) for reproducible builds.
- `make mcp-up` runs `pip install -e` every start, so bumping the pin here is picked up automatically.
- When an internal package registry exists, swap the git URL for `mcp-service-base[mcp]==0.1.3`.

---

## 11. Summary

- The SAD service is a **thin instance** of the generic `mcp-service-base` contract.
- It writes only its **schema + query helpers + tool declarations**; the base
  provides the log, fan-out, policy gate, telemetry, and MCP scaffolding.
- Events flow **pipeline → `ingest_alert` → emit → durable log (first) → fan-out → agent**,
  idempotent on `ref_id` and fully replayable.
- The agent connects over MCP and discovers everything via `describe` — no agent
  changes needed to onboard this service.
