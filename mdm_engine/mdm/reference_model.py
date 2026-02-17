"""Reference MDM implementation: simple explainable scoring (logistic/linear)."""

from __future__ import annotations

import math
from typing import Any

from decision_schema.types import Action, Proposal as TradeProposal


def compute_proposal_reference(
    features: dict[str, Any],
    confidence_threshold: float = 0.5,
    imbalance_threshold: float = 0.1,
) -> TradeProposal:
    """
    Reference MDM: simple logistic scoring.
    
    This is a reference implementation. For production, use a private model hook
    (see decision_engine.py).
    
    Args:
        features: Market features (mid, spread, depth, imbalance, etc.)
        confidence_threshold: Minimum confidence to propose ACT (default: 0.5)
        imbalance_threshold: Minimum imbalance to propose ACT (default: 0.1)
    
    Returns:
        TradeProposal with action, confidence, reasons
    """
    mid = features.get("mid", 0.5)
    spread_bps = features.get("spread_bps", 0.0)
    depth = features.get("depth", 0.0)
    imbalance = features.get("imbalance", 0.0)
    
    # Simple scoring: depth and imbalance contribute to confidence
    depth_score = min(1.0, depth / 100.0)  # Normalize depth
    imbalance_score = abs(imbalance)
    spread_penalty = min(1.0, max(0.0, 1.0 - spread_bps / 1000.0))  # Penalize wide spreads
    
    # Logistic confidence
    raw_score = (depth_score * 0.4 + imbalance_score * 0.4 + spread_penalty * 0.2)
    confidence = 1.0 / (1.0 + math.exp(-5.0 * (raw_score - 0.5)))  # Logistic transform
    
    reasons = []
    if depth_score > 0.5:
        reasons.append("sufficient_depth")
    if abs(imbalance) > imbalance_threshold:
        reasons.append("imbalance")
    if spread_penalty > 0.7:
        reasons.append("tight_spread")
    
    # Decide action
    if confidence >= confidence_threshold and abs(imbalance) >= imbalance_threshold:
        action = Action.ACT
        # Simple quote: mid ± spread/4
        spread = features.get("spread", 0.02)
        bid_quote = mid - spread / 4.0
        ask_quote = mid + spread / 4.0
        size_usd = min(1.0, depth_score * 2.0)  # Size based on depth
        return TradeProposal(
            action=action,
            confidence=confidence,
            reasons=reasons,
            params={"bid_quote": bid_quote, "ask_quote": ask_quote, "size_usd": size_usd},
            features_summary={"depth_score": depth_score, "imbalance_score": imbalance_score},
        )
    
    return TradeProposal(action=Action.HOLD, confidence=confidence, reasons=reasons or ["low_confidence"])


def compute_proposal_private(features: dict[str, Any], **kwargs) -> TradeProposal | None:
    """
    Private model hook: import from mdm_engine.mdm._private.model if exists.
    
    Returns None if private model not available (falls back to reference).
    On runtime exception: fail-closed (returns safe HOLD proposal).
    """
    try:
        from mdm_engine.mdm._private.model import compute_proposal_private as _private_compute
        return _private_compute(features, **kwargs)
    except ImportError:
        # Private hook not available - silent fallback (expected)
        return None
    except Exception as e:
        # Private hook runtime error - fail-closed
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"🔒 Private MDM hook error, using reference: {type(e).__name__}")
        # Return safe HOLD proposal (fail-closed)
        from decision_schema.types import Action, Proposal as TradeProposal
        return TradeProposal(
            action=Action.HOLD,
            confidence=0.0,
            reasons=["private_hook_error"],
            features_summary={"error": type(e).__name__},
        )
