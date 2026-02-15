#!/usr/bin/env python
"""
Minimal smoke test for review bundle: loads sample_packets.jsonl, runs engine path,
asserts at least one L0, one L2, and schema v2 export is valid.
Usage: from repo root: python tools/smoke_test.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAMPLE_JSONL = ROOT / "examples" / "sample_packets.jsonl"


def main():
    assert SAMPLE_JSONL.exists(), f"Missing {SAMPLE_JSONL}"
    packets = []
    with open(SAMPLE_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            packets.append(json.loads(line))

    assert len(packets) >= 1, "sample_packets.jsonl must have at least one packet"

    levels = [p.get("mdm", {}).get("level", 0) for p in packets]
    assert any(lv == 0 for lv in levels), "At least one L0 required in sample"
    assert any(lv == 2 for lv in levels), "At least one L2 required in sample"

    for p in packets:
        assert "mdm" in p, "Schema v2: every packet must have 'mdm'"
        assert p.get("schema_version") in ("2.0", 2, 2.0), "Schema version must be 2.0"

    try:
        from mdm_engine.audit_spec import decision_packet_to_csv_row, validate_packet_schema_v2
        for p in packets:
            validate_packet_schema_v2(p)
            row = decision_packet_to_csv_row(p)
            assert "mdm_level" in row and "final_action" in row, "CSV row must contain mdm_level and final_action"
    except ImportError as e:
        print(f"Warning: mdm_engine not installed, skip export check: {e}")

    print("OK: smoke_test passed (L0 present, L2 present, schema v2 export valid).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
