"""Decision Engine: glues features -> MDM proposal (reference or private hook)."""

from __future__ import annotations

from typing import Any

from decision_schema.types import Proposal as TradeProposal
from mdm_engine.mdm.reference_model import compute_proposal_reference, compute_proposal_private


class DecisionEngine:
    """
    MDM Decision Engine: generates proposals from features.
    
    Uses private model hook if available (mdm_engine.mdm._private.model.compute_proposal_private),
    otherwise falls back to reference implementation.
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.5,
        imbalance_threshold: float = 0.1,
        **kwargs,  # Passed to private model if available
    ):
        self.confidence_threshold = confidence_threshold
        self.imbalance_threshold = imbalance_threshold
        self._private_kwargs = kwargs
    
    def propose(self, features: dict[str, Any]) -> TradeProposal:
        """
        Generate proposal from features.
        
        Tries private model hook first, falls back to reference.
        On private hook error: fail-closed (safe HOLD).
        """
        # Try private model
        proposal = compute_proposal_private(features, **self._private_kwargs)
        if proposal is not None:
            # Check if it's a fail-closed HOLD from error
            if proposal.action.value == "HOLD" and "private_hook_error" in proposal.reasons:
                # Already fail-closed, return as-is
                return proposal
            return proposal
        
        # Fall back to reference (private hook not available - expected)
        return compute_proposal_reference(
            features,
            confidence_threshold=self.confidence_threshold,
            imbalance_threshold=self.imbalance_threshold,
        )
