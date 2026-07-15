# Suspicious Activity Detection — Training Script

A simple, speakable script for presenting the Store-Wide Loss Prevention
**Suspicious Activity Detection** solution, plus a Q&A cheat-sheet.

---

## Script (~4 min + demo)

### 1. Intro & Overview (~1 min)
"Good morning everyone. I'll walk you through our **Suspicious Activity Detection**
solution — an edge-AI system for retail loss prevention. The problem it solves is
simple: today, store cameras are mostly used to *review* incidents after they
happen. Our system watches the cameras in **real time** and raises **explainable
alerts** the moment something suspicious happens — merchandise concealment, checkout
bypass, loitering, repeat visits, or entering a restricted area.

Under the hood it combines **real-time person tracking from SceneScape** with
**lightweight pose detection** and **Vision-Language-Model (VLM) confirmation**,
monitoring behavior across store zones. The architecture is **layered**: one
application-specific **Scene-Understanding Service** owns the session state and
business logic, while leveraging **generic, reusable services** —
BehavioralAnalysisService and AlertService — for analysis and alerting. And a core
design principle is **config-driven extensibility**: detection rules, session flags,
escalation services, pose patterns, and VLM prompts are all defined in **YAML/JSON**,
so new scenarios or zone types need **no code changes — only configuration**."

### 2. Where it runs (20 sec)
"Everything runs **on Intel hardware — CPU, GPU, or NPU — fully on-premise**. No
cloud. That means customer video never leaves the store, which is a big privacy
and compliance advantage."

### 3. Architecture (walk through SAD_Architecture.png — ~1.5 min)
"Let me walk you through the architecture, left to right:

- **Cameras → SceneScape:** The store cameras feed into **SceneScape**, which
  detects every person, re-identifies them so each shopper keeps a **consistent
  ID** across cameras, and tracks which **zone** they're in with enter/exit and
  dwell times.
- **SceneScape → MQTT → Scene-Understanding Service:** SceneScape publishes all of
  that on an **MQTT bus**. The **Scene-Understanding Service** — our single
  application-specific service — subscribes to those events (no direct camera
  dependency, so it stays decoupled and scalable). It **owns the session state and
  business logic**: a session per person, plus the **rule engine** that decides
  what's suspicious. Crucially, its **entire behavior is driven by one config file,
  `rules.yaml`** — the detection logic is *not* hard-coded. It leverages two
  **generic, reusable** services for the heavy lifting —
  **BehavioralAnalysisService** and **AlertService**.
- **Escalation → BehavioralAnalysisService:** When a rule needs a closer look, the
  Scene-Understanding Service escalates to the reusable **BehavioralAnalysisService** —
  the two-stage brain. A cheap **pose model** filters frames first, and only the
  suspicious ones go to the **Vision-Language Model, Qwen2.5-VL**, served on
  **OpenVINO Model Server**, which returns a confidence score and a **plain-English
  reason**.
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

### 4. What makes it different (30 sec)
"Three things set us apart:
- One — it's **explainable**, not a black-box risk score.
- Two — it's **fully edge and on-prem**, a privacy win over cloud competitors.
- Three — it's **config-driven**: detection rules, session flags, escalation
  services, pose patterns, and VLM prompts all live in YAML/JSON. New scenarios or
  zone types need no code change — only configuration."

### 5. Live demo
"Let me show you live:
1. Here's the **dashboard** with live camera feeds.
2. I'll walk a person through a high-value zone — watch the alert pop up with the
   **evidence frames and the VLM's explanation**.
3. Now checkout bypass — exit without paying → it escalates to **CRITICAL**.
4. And a restricted-zone entry → immediate **CRITICAL** alert."

### 6. Close (15 sec)
"So in short: real-time, explainable, privacy-preserving loss prevention that runs
at the edge on Intel hardware, built on SceneScape — and it adapts to each store
without re-engineering. Happy to take questions."

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
