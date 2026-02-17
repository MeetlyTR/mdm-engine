# MDM Engine

**MDM Engine** is a runtime system for Market Decision Models (MDM). It provides event loop orchestration, feature extraction, reference MDM implementation, and trace/audit capabilities.

## What MDM Engine Does

MDM Engine provides:
- **Event Loop**: Orchestrates MDM → DMC → execution flow
- **Feature Extraction**: Builds market microstructure features from order book snapshots
- **Reference MDM**: Simple explainable scoring model (logistic/linear)
- **Adapters**: Generic interfaces for market data sources and brokers
- **Trace/Audit**: Logging and security utilities (redaction)

## What MDM Engine Is NOT

- **Not DMC**: MDM Engine generates proposals; DMC modulates them (see `decision-modulation-core`)
- **Not exchange-specific**: No third-party exchange, crypto, or exchange-specific adapters
- **Not a trading bot**: No order management, position management, or execution logic beyond interfaces
- **Not a strategy**: Reference MDM is for demonstration; use private hook for production models

## Core Components

### 1. Event Loop (`ami_engine/loop/run_loop.py`)

Main orchestration: event → features → MDM proposal → DMC modulation → execution → trace.

### 2. Feature Extraction (`ami_engine/features/feature_builder.py`)

Builds market microstructure features:
- Basic: mid, spread, depth, imbalance
- Advanced: microprice, VWAP, pressure, sigma, sigma_spike_z, cost_ticks

### 3. Reference MDM (`ami_engine/mdm/`)

- `reference_model.py`: Simple logistic scoring (demonstration)
- `decision_engine.py`: Glues features → proposal (uses private hook if available)
- `position_manager.py`: Reference exit policy (TP/SL/time stops) - **reference only, not production-ready**

### 4. Adapters (`ami_engine/adapters/`)

Generic interfaces:
- `MarketDataSource`: Abstract interface for market events
- `Broker`: Abstract interface for order submission/cancellation

No exchange-specific implementations (external adapters removed; use your own).

### 5. Trace/Audit (`ami_engine/trace/`, `ami_engine/security/`)

- `TraceLogger`: Writes PacketV2 to JSONL
- `AuditLogger`: Security audit logs
- `redaction`: Secret redaction utilities

## Private MDM Hook

MDM Engine supports a private model hook:

1. Create `ami_engine/mdm/_private/model.py` (gitignored)
2. Implement `compute_proposal_private(features: dict, **kwargs) -> TradeProposal`
3. `DecisionEngine` will use it if present; otherwise falls back to reference

This allows proprietary MDM models without exposing them in public code.

## Quick Start

```python
from ami_engine.mdm.decision_engine import DecisionEngine
from ami_engine.features.feature_builder import build_features
from dmc_core.schema.types import Action

# Build features from market event
event = {"bid": 0.49, "ask": 0.51, "bid_depth": 100.0, "ask_depth": 100.0}
features = build_features(event, mid_history=[], ...)

# MDM proposal
mdm = DecisionEngine(confidence_threshold=0.5)
proposal = mdm.propose(features)

print(f"Action: {proposal.action}, Confidence: {proposal.confidence}")
```

## Integration with Decision Schema

MDM Engine outputs `Proposal` (from `decision-schema` package). **DMC is optional but highly recommended** for risk management.

**Schema Dependency**: MDM Engine depends on `decision-schema>=0.1,<0.2` for type contracts. This ensures compatibility across the multi-core ecosystem.

**Without DMC**: Proposals are executed directly (no risk guards).

**With DMC**: Proposals are modulated by guards before execution:

```python
from dmc_core.dmc.modulator import modulate
from dmc_core.dmc.risk_policy import RiskPolicy

proposal = mdm.propose(features)
final_action, mismatch = modulate(proposal, RiskPolicy(), context)

if mismatch.flags:
    # Guards triggered - do not execute
    return

# Execute final_action
```

See `decision-modulation-core` repository for DMC documentation.

## Documentation

- `docs/ARCHITECTURE.md`: System architecture and data flow
- `docs/TERMINOLOGY.md`: Key terms and concepts
- `docs/SAFETY_LIMITATIONS.md`: What MDM Engine does NOT guarantee
- `docs/PUBLIC_RELEASE_GUIDE.md`: Public release checklist

## Installation

```bash
pip install -e .
```

Requires `dmc-core` (Decision Modulation Core).

## Tests

```bash
pytest tests/
```

## License

[Add your license]
