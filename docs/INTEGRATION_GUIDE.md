# Integration Guide — mdm-engine

## Dependency

Pin schema version:
```toml
dependencies = ["decision-schema>=0.1,<0.2"]
```

## Usage

```python
from decision_schema.compat import is_compatible, get_current_version
from ami_engine.mdm.decision_engine import DecisionEngine
from ami_engine.features.feature_builder import build_features

# Compatibility gate (fail-closed)
v = get_current_version()
if not is_compatible(v, expected_major=0, min_minor=1, max_minor=1):
    raise RuntimeError("Incompatible decision-schema version (fail-closed).")

# Build features from generic event
event = {
    "value": 0.5,
    "timestamp_ms": 1000,
    "metadata": {"source": "sensor_1"},
}
features = build_features(event, history=[], ...)

# Generate proposal
mdm = DecisionEngine(confidence_threshold=0.5)
proposal = mdm.propose(features)

# proposal is a Proposal type from decision-schema
print(f"Action: {proposal.action}, Confidence: {proposal.confidence}")
```

## Adapter boundary

Adapters may transform domain inputs into `state`/`context`, but mdm-engine must remain domain-agnostic.

## Telemetry

All traces must be emitted as `PacketV2`. No parallel trace schemas in core paths.

## Integration with decision-modulation-core (optional)

```python
from decision_schema.types import Proposal, Action, FinalDecision
from dmc_core.dmc.modulator import modulate
from dmc_core.dmc.risk_policy import RiskPolicy

proposal = mdm.propose(features)

# Optional: Apply risk guards via DMC
final_action, mismatch = modulate(proposal, RiskPolicy(), context)

if mismatch.flags:
    # Guards triggered - do not execute
    return

# Execute final_action
```

## Private MDM Hook

For domain-specific models:

1. Create `ami_engine/mdm/_private/model.py` (gitignored)
2. Implement `compute_proposal_private(features: dict, **kwargs) -> Proposal`
3. `DecisionEngine` will use it if present; otherwise falls back to reference
