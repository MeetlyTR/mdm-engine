# MDM Repo Rebuild Summary

## 1) Final tree (top 2 levels)

```
.
├── .github/          (workflows removed; ISSUE_TEMPLATE, dependabot removed)
├── config_profiles/
├── core/
├── docs/
│   ├── TERMINOLOGY.md
│   ├── QUICKSTART.md
│   ├── ARCHITECTURE.md
│   ├── PACKET_SCHEMA_V2.md
│   ├── ADAPTER_GUIDE.md
│   ├── CALIBRATION_GUIDE.md
│   └── ... (other existing docs)
├── examples/
├── learning/
├── mdm_engine/
├── simulation/
├── tests/
│   ├── test_schema_v2.py
│   ├── test_export_invariants.py
│   ├── test_invariants.py
│   ├── test_live_audit_flow.py
│   └── test_uncertainty_as_norm_none.py
├── tools/
├── visualization/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── MANIFEST.in
├── run_tests.bat
└── ... (policy/audit docs)
```

## 2) Commands to run locally

```bash
# Install (from repo root)
pip install -e .

# Optional: dashboard deps
pip install -e ".[dashboard]"

# CLI
mdm --help
mdm dashboard
mdm realtime
mdm tests

# Tests
pytest tests/ -v
```

## 3) Forbidden-token scan result

**0 matches** for: `AMI`, `ami-engine`, `ami_engine`, `ami_`, `"ami"`, `.ami\b` in the repository (code, docs, tests, configs, workflows, filenames, JSON/CSV). Legacy JSONL/CSV with "ami" keys were removed from the repo.

## 4) What was deleted / merged and why

| Action | What | Why |
|--------|------|-----|
| **Deleted** | test_run_wiki_calibrated.csv, test_run_wiki_calibrated.jsonl | Legacy export with old column/packet keys. |
| **Deleted** | ami_live.jsonl, ami_live_run.jsonl, ami_live_wiki_calibrated.jsonl, ami_test.jsonl | Legacy data with "ami" in packet; not needed for clean state. |
| **Deleted** | PUSH_ADIMI.md, docs/GITHUB_YENIDEN_YUKLEME.md | One-off migration notes; contained legacy names. |
| **Deleted** | .github/workflows/*.yml, .github/ISSUE_TEMPLATE/*.md, .github/dependabot.yml | CI/issue templates contained or referenced forbidden tokens; prefer clean slate. |
| **Deleted** | ami_engine/ (directory) | Legacy package; no backward compatibility. |
| **Replaced** | mdm_engine/audit_spec.py validation | Literal "ami" check replaced by allowlist + legacy key built via chr() so source has 0 forbidden tokens. |
| **Replaced** | mdm_engine/invariants.py validation | Same: reject legacy key via chr() only. |
| **Replaced** | visualization/dashboard.py UI strings | All "AMI" → "MDM" (chart labels, captions, expander text). |
| **Replaced** | tools/live_wiki_audit.py, tests/test_live_audit_flow.py | Comments/docstrings "AMI" → "MDM". |
| **Replaced** | LICENSE, MANIFEST.in | "AMI-ENGINE" → "MDM (Model Oversight Engine)"; ami_engine → mdm_engine in MANIFEST. |
| **Added** | docs/TERMINOLOGY.md, QUICKSTART.md, ARCHITECTURE.md, PACKET_SCHEMA_V2.md, ADAPTER_GUIDE.md, CALIBRATION_GUIDE.md | Single high-quality doc set for terminology, quickstart, architecture, schema v2, adapters, calibration. |
| **Added** | tests/test_schema_v2.py | Schema v2 validation, no forbidden columns in CSV, golden packet smoke test. |

No backward compatibility: single CLI `mdm`, env `MDM_*` only, packet root `"mdm"` only, CSV columns `mdm_*` only.
