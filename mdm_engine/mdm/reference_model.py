"""Re-export domain-free reference implementation. Legacy mapping lives in docs/examples."""

from mdm_engine.mdm.reference_model_generic import (
    compute_proposal_private,
    compute_proposal_reference,
)

__all__ = ["compute_proposal_reference", "compute_proposal_private"]
