# Suspicious Activity Detection — Training Script

A simple, speakable script for presenting the Store-Wide Loss Prevention
**Suspicious Activity Detection** solution, plus a Q&A cheat-sheet.

---

## Script (~4 min + demo)

###  Intro & Overview (~1 min)
"Hi everyone. I'll walk you through **Suspicious Activity Detection**
solution — an edge-AI system for retail loss prevention. The problem it solves is
simple: today, store cameras are mostly used to *review* incidents after they
happen. This system watches the cameras in **real time** and raises **explainable
alerts** the moment something suspicious happens — concealment, checkout
bypass, loitering, repeat visits, or entering a restricted area.

Under the hood it combines **real-time person tracking from SceneScape** with
**lightweight pose detection** and **Vision-Language-Model (VLM) confirmation**,
monitoring behavior across store zones. **Scene-Understanding Service** owns the session state and
business logic, while leveraging **generic, reusable services** —
BehavioralAnalysisService and AlertService — for analysis and alerting. And a core
design principle is **config-driven extensibility**: detection rules, session flags,
escalation services, pose patterns, and VLM prompts are all defined in **YAML/JSON**,
so new scenarios or zone types need **no code changes — only configuration**."

###  Architecture (walk through SAD_Architecture.png — ~1.5 min)
"Let me walk you through the architecture, left to right:

- **Cameras → SceneScape:** The store cameras feed into **SceneScape**, which
  detects every person, re-identifies them so each shopper keeps a **consistent
  ID** across cameras, and tracks which **zone** they're in with enter/exit and
  dwell times.

- **SceneScape → MQTT → Scene-Understanding Service:** SceneScape publishes every
  person and zone event on an **MQTT bus**, and the **Scene-Understanding Service**
  subscribes to them. This is the **decision-making core** of the app: it keeps a
  **session per person** — tracking which zones they entered, how long they stayed,
  and per-person flags — and runs a **rule engine** driven by `rules.yaml`. For each
  incoming event it evaluates the configured rules; when a rule's **trigger and
  conditions** match, it fires that rule's **actions** — either raise an **alert**
  or **escalate** to behavioral analysis. Every rule lives in `rules.yaml`, so we
  can add, tune, or enable/disable any rule at any time — no rebuild, no code change.

- **Escalation → BehavioralAnalysisService:** We define a `behavioral_analysis`
  rule that calls this **external service**. When a person enters a **high-value
  zone**, the rule triggers: the Scene-Understanding Service **captures frames,
  stores them in SeaweedFS**, and **publishes a request to MQTT**. The reusable
  **BehavioralAnalysisService** consumes that message from the queue and runs a
  **two-stage analysis** — first a lightweight **pose analyzer** checks for
  suspicious activity; only if it **confirms** something suspicious are the frames
  sent to the **Vision-Language Model (Qwen2.5-VL, on OpenVINO Model Server)** for
  deeper analysis, which returns a confidence score and a **plain-English reason**.

- **Frame storage:** Evidence frames for people in high-value zones are saved to
  an **on-prem object store** — this backs each alert and never leaves the store.

- **Alerts → AlertService → Dashboard:** Confirmed behavior becomes an **alert**.
  The reusable **AlertService** deduplicates and routes it, and it appears on the
  **operator dashboard** with severity, person, zone, and evidence.

The core design principle is **config-driven extensibility**: detection rules,
session flags, escalation services, pose patterns, and VLM prompts are all defined
declaratively in **YAML/JSON**. Adding a new detection scenario, zone type, or
analysis service needs **no code change — only configuration**. And it all runs at
the **edge on Intel CPU/GPU/NPU**."

**The Scene-Understanding Service is driven entirely by `rules.yaml`** — five sections,
all extensible without touching code:

| Section | What it controls |
|---------|------------------|
| `settings` | Session timeout and frame-capture cadence. |
| `variables` | Tunable thresholds reused across rules (e.g. loiter time, repeat-visit count). |
| `session_flags` | Boolean flags auto-set per person (e.g. `visited_high_value`, `visited_checkout`, `concealment_suspected`). Add a flag → picked up automatically. |
| `services` | Named escalation services a rule can invoke (e.g. `behavioral_analysis`). |
| `rules` | Each rule = a **trigger** (zone entry / loiter / exit), **conditions**, and **actions** — raise an *alert* or *escalate* to behavioral analysis — with severity and de-duplication scope. |

"So to add a new suspicious behavior, change a threshold, or wire in a new analysis
service, we edit `rules.yaml` — no rebuild, no code release."



---

## Architecture box reference (SAD_Architecture.png)

| Box | Role |
|-----|------|
| **Cameras** | Live RTSP feeds |
| **SceneScape** | Person detection + re-ID + multi-camera tracking |
| **MQTT bus** | Event backbone |
| **Scene-Understanding Service** | App-specific: per-person sessions + rule engine + business logic |
| **BehavioralAnalysisService** | Generic/reusable: pose pre-filter + VLM reasoning |
| **OVMS (VLM)** | Qwen2.5-VL inference |
| **SeaweedFS / MinIO** | Evidence frame storage |
| **AlertService** | Generic/reusable: dedup + routing |
| **Dashboard (Gradio)** | Operator view |

---

## Detected activities

| Activity | Trigger | Severity |
|----------|---------|----------|
| Merchandise Concealment | Behavioral Analysis returns "suspicious" | WARNING |
| Checkout Bypass | Visited high-value zone, exits without checkout | WARNING / CRITICAL* |
| Loitering | Dwell time over threshold in a zone | WARNING |
| Repeated Visits | Re-enters same high-value zone ≥ threshold | WARNING |
| Restricted Zone Violation | Enters a restricted zone | CRITICAL |

\* Escalates to CRITICAL when concealment is already suspected.

---

## Q&A cheat-sheet

**Q: How accurate is it? / What's the false-positive rate?**
"The pose-plus-VLM two-stage design is built to reduce false positives — the pose
filter removes obvious non-events, and the VLM adds context before we alert.
Thresholds are tunable per store in YAML, so a site can dial sensitivity to its own
tolerance. Formal precision/recall benchmarking on real store footage is on the
roadmap."

**Q: Why a VLM instead of a trained shoplifting classifier?**
"A supervised classifier needs large, labeled shoplifting datasets, which are
scarce and biased. The VLM works zero-shot and, crucially, gives a **human-readable
reason** — staff need a defensible explanation before approaching a customer."

**Q: Does it run on the edge or in the cloud?**
"Fully on the edge, on Intel CPU/GPU/NPU. No video leaves the store — a privacy and
bandwidth advantage over cloud-first competitors."

**Q: How do you add a new rule or change a threshold?**
"It's config-driven — edit `rules.yaml`. New rule, severity, or threshold, no code
change or redeploy of the logic."

**Q: How does it track the same person across cameras?**
"SceneScape does person re-identification, giving each shopper a persistent ID.
That's what powers repeat-visit and cross-camera detection."

**Q: What if the VLM is unsure?**
"It returns a confidence score. Low-confidence cases can be suppressed or flagged
for human review — we keep a human in the loop for anything that would confront a
customer."

**Q: What are the roadmap / improvement areas?**
"Published accuracy benchmarks, multi-store fleet management, and a GUI rule-tuner
so non-technical staff can adjust detections without editing YAML."
