# mdm-engine (Proposal Generation Runtime)

`mdm-engine` generates **domain-agnostic proposals**: given a state/context snapshot, it produces a `decision_schema.types.Proposal` plus an optional `PacketV2` trace.
This repository is part of the **multi-core decision ecosystem** (contract-first; cores depend only on `decision-schema`).

## What it does

- Computes a candidate action and confidence as a `Proposal`
- Emits trace telemetry via `PacketV2`
- Supports configurable profiles (thresholds/weights) without hard-coding external services

## What it does NOT do

- It does not encode domain policy. Domain semantics must live in an adapter layer.
- It does not require any specific external platform/service.

## Integration (contract-first)

- **Input**: `state: dict`, `context: dict`
- **Output**: `Proposal` (+ `PacketV2`)

See `docs/INTEGRATION_GUIDE.md`.

## Example domains (quarantined)

All platform-specific demos (e.g., any single-site or single-provider integrations) are documented under:
- `docs/examples/` (explicitly **Example domain only**)

## Core Components

### 1. Event Loop (`ami_engine/loop/run_loop.py`)

Main orchestration: event → features → MDM proposal → DMC modulation → execution → trace.

### 2. Feature Extraction (`ami_engine/features/feature_builder.py`)

Builds features from generic event dictionaries:
- Basic: numeric values, timestamps, counts
- Advanced: aggregations, rolling statistics, derived metrics

### 3. Reference MDM (`ami_engine/mdm/`)

- `reference_model.py`: Simple logistic scoring (demonstration)
- `decision_engine.py`: Glues features → proposal (uses private hook if available)
- `position_manager.py`: Reference exit policy (TP/SL/time stops) - **reference only, not production-ready**

### 4. Adapters (`ami_engine/adapters/`)

Generic interfaces:
- `DataSource`: Abstract interface for event streams
- `Broker`: Abstract interface for action execution

No domain-specific implementations (external adapters removed; use your own).

### 5. Trace/Audit (`ami_engine/trace/`, `ami_engine/security/`)

- `TraceLogger`: Writes PacketV2 to JSONL
- `AuditLogger`: Security audit logs
- `redaction`: Secret redaction utilities

## Private MDM Hook

MDM Engine supports a private model hook:

1. Create `ami_engine/mdm/_private/model.py` (gitignored)
2. Implement `compute_proposal_private(features: dict, **kwargs) -> Proposal`
3. `DecisionEngine` will use it if present; otherwise falls back to reference

This allows proprietary MDM models without exposing them in public code.

## Quick Start

```python
from ami_engine.mdm.decision_engine import DecisionEngine
from ami_engine.features.feature_builder import build_features
from decision_schema.types import Action

# Build features from generic event
event = {
    "value": 0.5,
    "timestamp_ms": 1000,
    "metadata": {"source": "sensor_1"},
}
features = build_features(event, history=[], ...)

# MDM proposal
mdm = DecisionEngine(confidence_threshold=0.5)
proposal = mdm.propose(features)

print(f"Action: {proposal.action}, Confidence: {proposal.confidence}")
```

## Integration with Decision Schema

MDM Engine outputs `Proposal` (from `decision-schema` package). This is the **single source of truth** for type contracts.

**Schema Dependency**: MDM Engine depends **only** on `decision-schema>=0.1,<0.2` for type contracts. This ensures compatibility across the multi-core ecosystem.

**Optional DMC Integration**: For risk-aware decision modulation, you can integrate `decision-modulation-core` (DMC) as an optional layer:

```python
from decision_schema.types import Proposal, Action, FinalDecision
from decision_modulation_core.dmc.modulator import modulate
from decision_modulation_core.dmc.risk_policy import RiskPolicy

proposal = mdm.propose(features)

# Optional: Apply risk guards via DMC
final_action, mismatch = modulate(proposal, RiskPolicy(), context)

if mismatch.flags:
    # Guards triggered - do not execute
    return

# Execute final_action
```

**Without DMC**: Proposals can be executed directly (no risk guards). This is suitable for testing or when risk management is handled elsewhere.

See `decision-modulation-core` repository for DMC documentation.

## Documentation

- `docs/ARCHITECTURE.md`: System architecture and data flow
- `docs/TERMINOLOGY.md`: Key terms and concepts
- `docs/SAFETY_LIMITATIONS.md`: What MDM Engine does NOT guarantee
- `docs/PUBLIC_RELEASE_GUIDE.md`: Public release checklist
- `docs/examples/`: Domain-specific examples (content moderation, robotics, trading)

## Installation

```bash
pip install -e .
```

Or from git:
```bash
pip install git+https://github.com/MeetlyTR/mdm-engine.git
```

## Tests

```bash
pytest tests/
```

## License

[Add your license]
