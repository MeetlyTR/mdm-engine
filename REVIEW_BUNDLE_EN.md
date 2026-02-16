# MDM Review Bundle

Structure and run instructions for external review. Only **required** files are included in the bundle zip (see list below).

---

## Repo structure

```
mdm-engine/
├── README.md
├── pyproject.toml
├── REVIEW_BUNDLE_EN.md       # This file
├── CHANGELOG.md
├── mdm_engine/               # Engine, schema, audit
├── core/                     # Fail-safe, soft override, confidence, uncertainty
├── config_profiles/          # wiki_calibrated, scenario_test, etc.
├── tools/                    # live_wiki_audit, smoke_test, make_review_bundle, csv_export
├── visualization/            # Streamlit dashboard
├── docs/                     # Schema, L2 case studies, specs (EN only in repo)
├── examples/                 # sample_packets.jsonl, sample_mdm_audit.csv
└── tests/
```

---

## Key files

| File | Purpose |
|------|---------|
| **mdm_engine/engine.py** | Main flow: raw_state → moral scores → action grid → selection → fail-safe → escalation → final_action (APPLY / APPLY_CLAMPED / HOLD_REVIEW). |
| **core/fail_safe.py** | Fail-safe (J/H thresholds), override ⇒ L2. |
| **core/soft_override.py** | Soft clamp. |
| **mdm_engine/audit_spec.py** | Schema v2, CSV/JSONL export. |
| **visualization/dashboard.py** | Streamlit: Review Queue, Live Monitor, Quality; Approve/Reject → review_log. |
| **tools/live_wiki_audit.py** | EventStreams + ORES + MDM pipeline, evidence/diff fetch. |
| **docs/L2_CASE_STUDIES.md** | L2 content examples (Suhrawardy, Pastoral); images in docs/images/. |

---

## Run commands

- **Install:** `pip install -e .`
- **Dashboard:** `streamlit run visualization/dashboard.py`
- **Offline demo:** Load `examples/sample_packets.jsonl` from the dashboard.
- **Live Wikipedia:** Dashboard → Start live stream (EventStreams + ORES + MDM).
- **CSV export:** From Live Monitor or Search & Audit in the dashboard.
- **Smoke test:** `python tools/smoke_test.py`
- **Review bundle zip:** `python tools/make_review_bundle.py` → writes only the required file set to Desktop.

---

## Included in bundle zip (required only)

Root: README.md, REVIEW_BUNDLE_EN.md, CHANGELOG.md, pyproject.toml, SECURITY.md, USAGE_POLICY.md, CONTRIBUTING.md, AUDITABILITY.md, SAFETY_LIMITATIONS.md.  
Code: mdm_engine/, core/, config_profiles/, visualization/, tests/.  
Tools: smoke_test.py, make_review_bundle.py, live_wiki_audit.py, quick_wiki_test.py, csv_export.py.  
Examples: examples/.  
Docs: L2_CASE_STUDIES.md, images/, PACKET_SCHEMA_V2.md, QUICKSTART.md, README.md, AUDIT_LEVELS_AND_PACKETS.md.

Internal and Turkish docs are **not** included in the zip.

---

## Security checklist (before share)

- [x] No API keys
- [x] No cookies/sessions
- [x] No personal data
- [x] Sample data small (10–30 rows)
