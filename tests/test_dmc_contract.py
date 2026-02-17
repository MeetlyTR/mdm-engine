"""Contract smoke test: verify MDM Engine can import and use DMC schema/types."""

from __future__ import annotations

import pytest


def test_dmc_schema_imports() -> None:
    """Verify DMC schema types can be imported."""
    from decision_schema.types import Action, Proposal as TradeProposal, FinalDecision as FinalAction, MismatchInfo
    from decision_schema.packet_v2 import PacketV2
    
    # Verify types exist
    assert Action is not None
    assert TradeProposal is not None
    assert FinalAction is not None
    assert MismatchInfo is not None
    assert PacketV2 is not None


def test_dmc_modulator_imports() -> None:
    """Verify DMC modulator can be imported."""
    from dmc_core.dmc.modulator import modulate
    from dmc_core.dmc.risk_policy import RiskPolicy
    
    assert modulate is not None
    assert RiskPolicy is not None


def test_dmc_contract_smoke() -> None:
    """Smoke test: dummy proposal passes through DMC modulator."""
    from decision_schema.types import Action, Proposal as TradeProposal
    from dmc_core.dmc.modulator import modulate
    from dmc_core.dmc.risk_policy import RiskPolicy
    
    # Create dummy proposal
    proposal = TradeProposal(
        action=Action.QUOTE,
        confidence=0.8,
        reasons=["test"],
        params={"bid_quote": 0.49, "ask_quote": 0.51, "size_usd": 1.0},
    )
    
    # Create context (minimal required fields)
    context = {
        "now_ms": 1000,
        "last_event_ts_ms": 950,
        "depth": 100.0,
        "spread_bps": 400.0,
        "current_total_exposure_usd": 5.0,
        "abs_inventory": 2.0,
    }
    
    # Create policy (defaults)
    policy = RiskPolicy()
    
    # Modulate (should not crash)
    final_action, mismatch = modulate(proposal, policy, context)
    
    # Verify return types
    assert final_action is not None
    assert mismatch is not None
    assert final_action.action in [Action.QUOTE, Action.HOLD]  # May be overridden to HOLD by guards


def test_dmc_schema_fields_present() -> None:
    """Verify TradeProposal has expected fields."""
    from decision_schema.types import Proposal as TradeProposal, Action
    
    proposal = TradeProposal(
        action=Action.HOLD,
        confidence=0.5,
        reasons=["test"],
    )
    
    # Verify required fields
    assert hasattr(proposal, "action")
    assert hasattr(proposal, "confidence")
    assert hasattr(proposal, "reasons")
    assert hasattr(proposal, "params")  # params dict contains bid_quote, ask_quote, size_usd
