# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""Contract smoke test: verify MDM Engine can import and use DMC schema/types."""

from __future__ import annotations

import pytest


def test_dmc_schema_imports() -> None:
    """Verify decision_schema types can be imported."""
    from decision_schema.types import Action, Proposal, FinalDecision, MismatchInfo
    from decision_schema.packet_v2 import PacketV2

    assert Action is not None and Proposal is not None
    assert (
        FinalDecision is not None and MismatchInfo is not None and PacketV2 is not None
    )


def test_dmc_modulator_imports() -> None:
    """Verify DMC modulator and GuardPolicy can be imported (optional dep)."""
    pytest.importorskip("dmc_core")
    from dmc_core.dmc.modulator import modulate
    from dmc_core.dmc.policy import GuardPolicy

    assert modulate is not None and GuardPolicy is not None


def test_dmc_contract_smoke() -> None:
    """Smoke test: Proposal passes through DMC modulator (GuardPolicy)."""
    pytest.importorskip("dmc_core")
    from decision_schema.types import Action, Proposal
    from dmc_core.dmc.modulator import modulate
    from dmc_core.dmc.policy import GuardPolicy

    proposal = Proposal(action=Action.ACT, confidence=0.8, reasons=["test"])
    context = {
        "now_ms": 1000,
        "last_event_ts_ms": 950,
        "errors_in_window": 0,
        "steps_in_window": 10,
        "rate_limit_events": 0,
        "recent_failures": 0,
    }
    policy = GuardPolicy()
    final_decision, mismatch = modulate(proposal, policy, context)
    assert final_decision is not None and mismatch is not None
    assert final_decision.action in (Action.ACT, Action.HOLD, Action.STOP)


def test_dmc_schema_fields_present() -> None:
    """Verify Proposal has expected fields (0.2 contract)."""
    from decision_schema.types import Proposal, Action

    proposal = Proposal(action=Action.HOLD, confidence=0.5, reasons=["test"])
    assert hasattr(proposal, "action") and hasattr(proposal, "confidence")
    assert hasattr(proposal, "reasons") and hasattr(proposal, "params")
