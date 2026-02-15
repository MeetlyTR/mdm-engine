# MDM Quickstart

## Install

```bash
pip install -e .   # from repo root
# or
pip install mdm-engine
```

Optional: dashboard (Streamlit + Plotly):

```bash
pip install -e ".[dashboard]"
```

## Run from Python

```python
from mdm_engine import decide

result = decide(
    {"risk": 0.5, "physical": 0.5, "social": 0.5, "context": 0.4,
     "compassion": 0.5, "justice": 0.9, "harm_sens": 0.5,
     "responsibility": 0.6, "empathy": 0.5},
    profile="scenario_test"
)
print(result["action"], result["escalation"])  # L0/L1/L2
```

## CLI

```bash
mdm --help
mdm dashboard          # Streamlit dashboard (proof / live audit)
mdm dashboard --full   # Advanced dashboard if available
mdm realtime           # Live test run
mdm tests              # Run pytest
```

## Wiki / ORES adapter (live audit)

```bash
export MDM_CONFIG_PROFILE=wiki_calibrated   # optional; default for wiki
python tools/live_wiki_audit.py --jsonl mdm_live.jsonl
```

Then open dashboard and load `mdm_live.jsonl` or start live stream.

## Export CSV

Packet list → CSV with only `mdm_*` columns (schema v2). Use `decision_packet_to_csv_row` from `mdm_engine.audit_spec` or export from the dashboard.

## Tests

```bash
pytest tests/ -v
```
