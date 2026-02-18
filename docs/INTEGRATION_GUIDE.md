# Integration Guide — mdm-engine

## Dependency

Pin schema version:

```toml
dependencies = ["decision-schema>=0.2,<0.3"]
```

## Usage

Core API is domain-free: pass a **features dict** (e.g. state snapshot as generic keys) into `DecisionEngine.propose`. No bundled feature builder; use your adapter to build features or pass state through.

```python
from decision_schema.compat import is_compatible, get_current_version
from mdm_engine.mdm.decision_engine import DecisionEngine

# Compatibility gate (fail-closed)
v = get_current_version()
if not is_compatible(v, expected_major=0, min_minor=2, max_minor=2):
    raise RuntimeError("Incompatible decision-schema version (fail-closed).")

# State / context as features (passthrough; keys are domain-agnostic)
features = {
    "signal_0": 0.5,
    "signal_1": 0.0,
    "state_scalar_a": 120.0,
    "state_scalar_b": 10.0,
}
if "now_ms" in context:
    features["now_ms"] = context["now_ms"]

# Generate proposal
mdm = DecisionEngine(confidence_threshold=0.5)
proposal = mdm.propose(features)

# proposal is a Proposal type from decision-schema
print(f"Action: {proposal.action}, Confidence: {proposal.confidence}")
```

## Adapter boundary

Adapters may transform domain inputs into `state`/`context` and then into a features dict. mdm-engine core remains domain-agnostic.

## Telemetry

All traces must be emitted as `PacketV2`. No parallel trace schemas in core paths.

## Integration with decision-modulation-core (optional)

```python
from decision_schema.types import Proposal, Action, FinalDecision
from dmc_core.dmc.modulator import modulate
from dmc_core.dmc.policy import GuardPolicy

proposal = mdm.propose(features)

# Optional: Apply guards via DMC (GuardPolicy)
final_decision, mismatch = modulate(proposal, GuardPolicy(), context)

if mismatch.flags:
    # Guards triggered - do not execute
    return

# Execute final_decision
```

## Private MDM Hook

For domain-specific models:

1. Create `mdm_engine/mdm/_private/model.py` (gitignored)
2. Implement `compute_proposal_private(features: dict, **kwargs) -> Proposal`
3. `DecisionEngine` will use it if present; otherwise falls back to reference
