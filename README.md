# Model Oversight Engine (MDM)  
## Model Denetim Motoru (MDM)

**L0/L1/L2 oversight, clamps, human-in-the-loop review, and end-to-end audit telemetry.**  
*L0/L1/L2 denetim, clamp, insan incelemesi ve uçtan uca audit/telemetri.*

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

> **MDM**, modellerin verdiği kararları L0/L1/L2 seviyelerinde denetleyen; gerektiğinde frenleyen (clamp) ve insan incelemesine yükselten (L2) bir oversight motorudur.  
> *MDM is an oversight engine that monitors model decisions at L0/L1/L2, applies clamps when needed, and escalates to human review at L2.*

---

## Quick Start

```bash
pip install mdm-engine
```

```python
from mdm_engine import decide

result = decide({
    "risk": 0.7, "severity": 0.8, "physical": 0.6, "social": 0.5,
    "context": 0.4, "compassion": 0.5, "justice": 0.9,
    "harm_sens": 0.5, "responsibility": 0.7, "empathy": 0.6
}, profile="scenario_test")

print(f"Action: {result['action']}, Level: L{result['escalation']}")
# Action: [0.0, 1.0, 0.58, 0.29], Level: L1
```

**CLI:**
```bash
mdm dashboard         # Proof dashboard (supported, testable, L0/L1/L2 + Proof Pack)
mdm dashboard --full  # Research/advanced dashboard (experimental, heavy deps)
mdm realtime          # Run live test
mdm tests             # Run test suite
```

**Dashboard:** `mdm dashboard` = **Proof dashboard** (tek ekran, kanıt kartları, seed’li run-until-coverage; desteklenen kararlı UI). `--full` = gelişmiş/araştırma dashboard’u (deneysel, isteğe bağlı).

### Migrating from the previous package?

- **Import:** `from mdm_engine import decide`.
- **CLI:** `mdm dashboard`.
- **Env:** `MDM_CONFIG_PROFILE` (default for wiki audit: `wiki_calibrated`). Audit schema v2.0 uses `mdm` packet key and `mdm_*` columns. Startup logs which profile is loaded.
- **Install:** `pip install mdm-engine`. The package name on PyPI is `mdm-engine`.

See [CHANGELOG.md](CHANGELOG.md) for the full migration note.

---

## Run instructions (review bundle)

- **Quick start**
  - `pip install -e .` or `pip install mdm-engine`
  - `streamlit run visualization/dashboard.py` (dashboard UI; default port 8501)
- **Offline demo**
  - Open dashboard → Sidebar: load JSONL → choose `examples/sample_packets.jsonl` for a small “load and view” demo.
- **Live Wikipedia demo**
  - In dashboard: “Start live stream”. EventStreams + ORES + MDM pipeline runs; see `tools/live_wiki_audit.py` for connection and evidence/diff fetch.
- **CSV export**
  - In dashboard: “Live Monitor” or “Search & Audit” → “Download CSV” button for full audit (ORES + MDM + clamp/model columns).
- **Review log**
  - Approve/Reject on L2 items append to `review_log.jsonl` (env: `MDM_REVIEW_LOG`). “Quality” tab reads this for override rate and reason heatmap.

See [REVIEW_BUNDLE.md](REVIEW_BUNDLE.md) for repo layout, important files, and one-command smoke test (`python tools/smoke_test.py`).

---

## What It Does

MDM (Model Oversight Engine) is a **regulation-grade** engine for **model oversight**: it does not make decisions itself but monitors and constrains them. It takes raw state as input, computes moral scores (Justice, Harm, Compassion), and produces safe actions through **three-level escalation** (L0/L1/L2).

### Core Features

- **L0/L1/L2 Escalation**: Automatic decision → Soft clamp → Human escalation
- **Soft Clamp**: Softly constrains raw outputs that exceed safety boundaries
- **Auditability**: Full trace (JSONL/CSV) for every decision + replay support
- **Temporal Drift**: Uncertainty tracking over time via CUS (Cumulative Uncertainty Score)
- **Config Profiles**: Scenario-based threshold settings (scenario_test, production_safe, etc.)

---

## What It Doesn't Do

- ❌ **Does not make domain-specific decisions**: This is a **decision regulator**; domain knowledge comes from the adapter layer
- ❌ **Does not process personal data**: Receives raw state from domain adapter; does not collect/surveil data
- ❌ **Does not apply automatic sanctions**: Human escalation is mandatory at L2
- ❌ **Does not perform surveillance/identification**: These uses are prohibited (see USAGE_POLICY.md)

---

## Installation

```bash
pip install mdm-engine
```

## Quick Start

### Python API

**Simplified API (Recommended):**

```python
from mdm_engine import decide

# Raw state (comes from domain adapter)
raw_state = {
    "risk": 0.7,
    "severity": 0.8,
    "physical": 0.6,
    "social": 0.5,
    "context": 0.4,
    "compassion": 0.5,
    "justice": 0.9,
    "harm_sens": 0.5,
    "responsibility": 0.7,
    "empathy": 0.6,
}

# Make decision
result = decide(raw_state, profile="scenario_test")

# Result
action = result["action"]  # [severity, intervention, compassion, delay]
level = result["escalation"]  # 0, 1, or 2
human_escalation = result["human_escalation"]  # True/False
```

**Full API (Advanced):**

```python
from mdm_engine import moral_decision_engine, replay_trace

result = moral_decision_engine(
    raw_state,
    config_override="scenario_test",
    context={"cus_history": []}
)

# Replay trace
replayed = replay_trace(result["trace"], validate=True)
```

See `examples/` directory for more examples.

### CLI

```bash
# Start dashboard
mdm dashboard

# Live test (90 seconds)
mdm realtime --duration 90 --profile scenario_test

# Run test suite
mdm tests
```

---

## L0/L1/L2 Meaning

- **L0**: Automatic decision — engine produced a safe action
- **L1**: Soft clamp applied — raw output was constrained, but continues automatically
- **L2**: Human escalation — human decision required (fail-safe triggered)

Each level is marked in the trace via the `level` field.

---

## Trace and Auditability

Full trace is generated for every decision:

- **JSONL**: `traces_live.jsonl` (each line is a trace)
- **CSV**: `traces_live.csv` (raw vs final action comparison)
- **Dashboard**: Visualization via `mdm dashboard`

Trace schema: `TRACE_VERSION = "1.0"` (version increments on changes).

**Replay**: Reproduce the same decision with `replay(trace)`.

---

## Config Profiles

```python
from mdm_engine import get_config, list_profiles

# Available profiles
print(list_profiles())  # ['base', 'scenario_test', 'production_safe', ...]

# Use profile
config = get_config("scenario_test")
result = moral_decision_engine(raw_state, config_override=config)
```

---

## Adapter Pattern

MDM is domain-agnostic. An **adapter** layer is required to connect to a domain:

```
Domain Input → Adapter → raw_state → MDM → action → Adapter → Domain Output
```

Example adapters:
- Chat messages → risk score → raw_state
- Sensor data → physical risk → raw_state
- Customer requests → urgency score → raw_state

---

## Examples

See the `examples/` directory for complete examples:

- **hello_world.py**: Simplest usage example
- **replay_example.py**: Trace replay demonstration
- **trace_collection.py**: Collecting multiple traces

Run examples:
```bash
python examples/hello_world.py
```

## Documentation

- **README.md** (this file): Overview
- **USAGE_POLICY.md**: Usage policy and prohibitions
- **SAFETY_LIMITATIONS.md**: Safety boundaries and warnings
- **AUDITABILITY.md**: Auditability and trace schema
- **CHANGELOG.md**: Version history
- **examples/README.md**: Example usage guide

---

## License

Apache-2.0 License — See LICENSE file for details.

---

## Contributing

See the GitHub repository to open issues and submit PRs.

**Contact**: mucahit.muzaffer@gmail.com

**Security**: Please use the private channel for security vulnerability reports (specified in USAGE_POLICY.md).

---

## Intellectual Position

MDM (Model Oversight Engine) is an open-source **reference implementation** of a model oversight and ethical decision governance layer.

The value of this project lies not only in the code, but in:
- **The architecture**: L0/L1/L2 escalation framework
- **The safety philosophy**: Human-in-the-loop, fail-safe mechanisms
- **The validation methodology**: Deterministic replay, trace auditability
- **The governance model**: Domain-agnostic decision regulation

**Commercial or institutional usage** is expected to involve direct collaboration with the author for:
- Domain-specific adapter development
- Custom configuration profiles
- Integration support
- Compliance validation

This project serves as a **foundational reference** for ethical AI decision systems. While the code is freely available under Apache-2.0, the architectural insights, safety patterns, and governance approach represent years of research and engineering.

---

## Version

**1.0.0** — First stable release
