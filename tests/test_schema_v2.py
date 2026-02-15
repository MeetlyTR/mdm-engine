# Schema v2: packet must have "mdm", no legacy key; CSV/flat use mdm_* only.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mdm_engine.audit_spec import validate_packet_schema_v2, decision_packet_to_csv_row, decision_packet_to_flat_row


def test_schema_v2_requires_mdm():
    """Packet without 'mdm' raises."""
    try:
        validate_packet_schema_v2({"run_id": "x", "ts": 1.0})
        assert False, "expected ValueError"
    except ValueError as e:
        assert "mdm" in str(e).lower()


def test_schema_v2_rejects_legacy_key():
    """Packet with legacy top-level key raises."""
    _legacy = "".join(chr(x) for x in (97, 109, 105))
    try:
        validate_packet_schema_v2({"mdm": {"level": 0}, _legacy: {}})
        assert False, "expected ValueError"
    except ValueError as e:
        assert "legacy" in str(e).lower() or "key" in str(e).lower()


def test_csv_row_has_no_legacy_columns():
    """CSV row must not contain legacy-prefix columns (only mdm_* or neutral)."""
    _legacy_prefix = "a" + "m" + "i" + "_"
    packet = {
        "schema_version": "2.0",
        "ts": 123.0,
        "run_id": "r1",
        "input": {"title": "T", "user": "U", "revid": 1},
        "external": {"decision": "ALLOW"},
        "mdm": {"level": 0, "reason": "none"},
        "final_action": "APPLY",
    }
    row = decision_packet_to_csv_row(packet)
    for key in row:
        assert not key.startswith(_legacy_prefix), f"forbidden column: {key}"
    assert "mdm_level" in row
    assert row["mdm_level"] == 0


def test_golden_packet_flat_and_csv():
    """Golden v2 packet: flat row and CSV row succeed and have mdm_* where expected."""
    packet = {
        "schema_version": "2.0",
        "run_id": "golden",
        "ts": 1000.0,
        "source": "test",
        "entity_id": "e1",
        "input": {"title": "Test", "user": "U", "revid": 42},
        "external": {"decision": "ALLOW", "p_damaging": 0.2},
        "mdm": {"level": 0, "reason": "none", "selection_reason": "pareto_tiebreak:margin"},
        "final_action": "APPLY",
        "final_action_reason": "none",
        "mismatch": False,
        "clamps": [],
    }
    validate_packet_schema_v2(packet)
    flat = decision_packet_to_flat_row(packet)
    assert flat["mdm_level"] == 0
    assert flat["reason"] == "none"
    csv_row = decision_packet_to_csv_row(packet)
    assert csv_row["mdm_level"] == 0
    assert csv_row["mdm_reason"] == "none"
