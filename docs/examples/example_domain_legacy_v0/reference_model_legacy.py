# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""
LEGACY: Example-domain reference model (mid, spread, depth, imbalance, bid_quote, ask_quote).

Quarantined under docs/examples. Core uses mdm_engine.mdm.reference_model_generic only.
Do not import this from production code; for migration see README in this folder.
"""

from __future__ import annotations

import math
from typing import Any

from decision_schema.types import Action, Proposal


def compute_proposal_reference(
    features: dict[str, Any],
    confidence_threshold: float = 0.5,
    imbalance_threshold: float = 0.1,
) -> Proposal:
    """Legacy: market-style features (mid, spread, depth, imbalance). Use reference_model_generic in core."""
    mid = features.get("mid", 0.5)
    spread_bps = features.get("spread_bps", 0.0)
    depth = features.get("depth", 0.0)
    imbalance = features.get("imbalance", 0.0)

    depth_score = min(1.0, depth / 100.0)
    imbalance_score = abs(imbalance)
    spread_penalty = min(1.0, max(0.0, 1.0 - spread_bps / 1000.0))
    raw_score = depth_score * 0.4 + imbalance_score * 0.4 + spread_penalty * 0.2
    confidence = 1.0 / (1.0 + math.exp(-5.0 * (raw_score - 0.5)))

    reasons = []
    if depth_score > 0.5:
        reasons.append("sufficient_depth")
    if abs(imbalance) > imbalance_threshold:
        reasons.append("imbalance")
    if spread_penalty > 0.7:
        reasons.append("tight_spread")

    if confidence >= confidence_threshold and abs(imbalance) >= imbalance_threshold:
        spread = features.get("spread", 0.02)
        return Proposal(
            action=Action.ACT,
            confidence=confidence,
            reasons=reasons,
            params={
                "bid_quote": mid - spread / 4.0,
                "ask_quote": mid + spread / 4.0,
                "size_usd": min(1.0, depth_score * 2.0),
            },
            features_summary={
                "depth_score": depth_score,
                "imbalance_score": imbalance_score,
            },
        )
    return Proposal(
        action=Action.HOLD, confidence=confidence, reasons=reasons or ["low_confidence"]
    )
