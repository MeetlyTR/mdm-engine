# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""
Domain-free reference MDM: generic feature keys (signal_0, signal_1, state_scalar_a/b).

INVARIANT 0: No domain vocabulary. Use params for domain-specific data only with namespaced keys.
"""

from __future__ import annotations

import math
from typing import Any

from decision_schema.types import Action, Proposal


def compute_proposal_reference(
    features: dict[str, Any],
    confidence_threshold: float = 0.5,
    signal_threshold: float = 0.1,
) -> Proposal:
    """
    Reference MDM: simple scoring from generic signals.

    Formulas: raw_score = 0.4·scale_score + 0.4·signal_score + 0.2·width_penalty;
    confidence = σ(5·(raw_score − 0.5)). Full equations in docs/FORMULAS.md
    (Reference implementation: generic numeric scorer).

    Args:
        features: Generic keys signal_0, signal_1, state_scalar_a, state_scalar_b (optional)
        confidence_threshold: Minimum confidence to propose ACT
        signal_threshold: Minimum |signal_1| to propose ACT

    Returns:
        Proposal with action, confidence, reasons
    """
    _s0 = features.get("signal_0", 0.5)  # reserved for future use
    s1 = features.get("signal_1", 0.0)
    scale_a = features.get("state_scalar_a", 0.0)
    scale_b = features.get("state_scalar_b", 0.0)

    scale_score = min(1.0, scale_a / 100.0) if scale_a else 0.0
    signal_score = abs(s1)
    width_penalty = min(1.0, max(0.0, 1.0 - (scale_b or 0) / 1000.0))

    raw_score = scale_score * 0.4 + signal_score * 0.4 + width_penalty * 0.2
    confidence = 1.0 / (1.0 + math.exp(-5.0 * (raw_score - 0.5)))

    reasons = []
    if scale_score > 0.5:
        reasons.append("sufficient_scale")
    if abs(s1) > signal_threshold:
        reasons.append("signal_above_threshold")
    if width_penalty > 0.7:
        reasons.append("tight_penalty")

    if confidence >= confidence_threshold and abs(s1) >= signal_threshold:
        return Proposal(
            action=Action.ACT,
            confidence=confidence,
            reasons=reasons,
            params={
                "score_components": {
                    "scale_score": scale_score,
                    "signal_score": signal_score,
                }
            },
            features_summary={"scale_score": scale_score, "signal_score": signal_score},
        )
    return Proposal(
        action=Action.HOLD, confidence=confidence, reasons=reasons or ["low_confidence"]
    )


def compute_proposal_private(
    features: dict[str, Any], **kwargs: Any
) -> Proposal | None:
    """
    Private model hook: import from mdm_engine.mdm._private.model if exists.

    Returns None if not available. On exception: fail-closed (safe HOLD).
    """
    try:
        from mdm_engine.mdm._private.model import (
            compute_proposal_private as _private_compute,
        )

        return _private_compute(features, **kwargs)
    except ImportError:
        return None
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(
            "Private MDM hook error, using reference: %s", type(e).__name__
        )
        return Proposal(
            action=Action.HOLD,
            confidence=0.0,
            reasons=["private_hook_error"],
            features_summary={"error": type(e).__name__},
        )
