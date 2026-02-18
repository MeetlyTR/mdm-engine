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

## Core API (proposal generation)

`mdm-engine` produces a `decision_schema.types.Proposal` from a domain-agnostic state/context snapshot.

### Contract

- **Input**: `state: dict`, `context: dict`
- **Output**: `Proposal` (+ optional `PacketV2` emitted by the integration layer)

### Non-goals

- No execution, no adapters, no platform/service coupling in core.
- Any end-to-end loops live under `docs/examples/` (Example domain only).

## Components

### 1. Reference MDM (`mdm_engine/mdm/`)

- `decision_engine.py`: Glues features → proposal (uses private hook if available)
- `reference_model.py`: Simple logistic scoring (demonstration)

### 2. Features input (domain-free)

Core API accepts a **features dict** (e.g. generic keys: `signal_0`, `signal_1`, `state_scalar_*`). Build this in your adapter or pass state through; see `docs/INTEGRATION_GUIDE.md`.

### 3. Integration loop (example only)

Event loop and DMC integration: see `docs/examples/` for example integration (not part of core package).

### 4. Security (packaged: `mdm_engine/security/`)

- Audit, redaction, rate-limit, signing utilities (see `mdm_engine/security/`)

## Private MDM Hook

MDM Engine supports a private model hook:

1. Create `mdm_engine/mdm/_private/model.py` (gitignored)
2. Implement `compute_proposal_private(features: dict, **kwargs) -> Proposal`
3. `DecisionEngine` will use it if present; otherwise falls back to reference

This allows proprietary MDM models without exposing them in public code.

## Quick Start

```python
from mdm_engine.mdm.decision_engine import DecisionEngine
from decision_schema.types import Action

# Domain-free features dict (e.g. state snapshot or adapter output)
features = {
    "signal_0": 0.5,
    "signal_1": 0.0,
    "state_scalar_a": 120.0,
    "state_scalar_b": 10.0,
}

# MDM proposal
mdm = DecisionEngine(confidence_threshold=0.5)
proposal = mdm.propose(features)

print(f"Action: {proposal.action}, Confidence: {proposal.confidence}")
```

## Integration with Decision Schema

MDM Engine outputs `Proposal` (from `decision-schema` package). This is the **single source of truth** for type contracts.

**Schema Dependency**: MDM Engine depends **only** on `decision-schema>=0.2,<0.3` for type contracts. Compatibility check: `min_minor=2, max_minor=2`.

**Optional DMC Integration**: For risk-aware decision modulation, integrate `decision-modulation-core` (DMC) as an optional layer:

```python
from decision_schema.types import Proposal, Action, FinalDecision
from dmc_core.dmc.modulator import modulate
from dmc_core.dmc.policy import GuardPolicy

# features: dict from your adapter or state
proposal = mdm.propose(features)

# Optional: Apply guards via DMC (GuardPolicy)
final_decision, mismatch = modulate(proposal, GuardPolicy(), context)

if mismatch.flags:
    # Guards triggered - do not execute
    return

# Execute final_decision
```

**Without DMC**: Proposals can be executed directly (no risk guards). This is suitable for testing or when risk management is handled elsewhere.

See `decision-modulation-core` repository for DMC documentation.

## Documentation

- `docs/ARCHITECTURE.md`: System architecture and data flow
- `docs/TERMINOLOGY.md`: Key terms and concepts
- `docs/SAFETY_LIMITATIONS.md`: What MDM Engine does NOT guarantee
- `docs/PUBLIC_RELEASE_GUIDE.md`: Public release checklist
- `docs/examples/`: Example integration (content moderation, robotics, scheduling)

## Installation

```bash
pip install -e .
```

Or from git:
```bash
pip install git+https://github.com/MchtMzffr/mdm-engine.git
```

## Tests

```bash
pytest tests/
```

## License

[Add your license]
