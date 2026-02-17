# Architecture — mdm-engine

## Role in the ecosystem

mdm-engine is the **proposal generation** core.

## Data flow

```
(state, context) -> propose() -> Proposal -> PacketV2
Proposal -> decision-modulation-core -> FinalDecision -> PacketV2
```

## Contracts

- Output types come from `decision-schema`
- Compatibility gate: reject incompatible schema versions (fail-closed)

## Safety invariants

- Fail-closed on exceptions
- No hard-coded external services in core logic
- Secrets must never be logged; redact sensitive keys from context

## Components

### 1. Proposal Generation (`mdm_engine/mdm/decision_engine.py`)

**Function**: `propose(features: dict, context: dict) -> Proposal`

- Takes generic feature dictionary
- Computes confidence score
- Returns `Proposal` conforming to `decision-schema`

### 2. Feature Extraction (`mdm_engine/features/feature_builder.py`)

**Function**: `build_features(event: dict, history: list, ...) -> dict`

- Extracts numeric features from event dictionaries
- Computes aggregations and rolling statistics
- Domain-agnostic feature extraction

### 3. Event Loop (`mdm_engine/loop/run_loop.py`)

**Function**: `run_loop(source, executor, ...) -> dict`

- Orchestrates: event → features → proposal → (optional modulation) → execution → trace
- Emits `PacketV2` traces
- Returns summary statistics

### 4. Adapters (`mdm_engine/adapters/`)

Generic interfaces:
- `DataSource`: Abstract interface for event streams
- `Executor`: Abstract interface for action execution

Domain-specific implementations must be provided by users.

### 5. Trace/Audit (`mdm_engine/trace/`, `mdm_engine/security/`)

- `TraceLogger`: Writes PacketV2 to JSONL
- `AuditLogger`: Security audit logs
- `redaction`: Secret redaction utilities

## Private Hook Pattern

Domain-specific models can be implemented via private hook:
- Create `mdm_engine/mdm/_private/model.py` (gitignored)
- Implement `compute_proposal_private(features: dict, **kwargs) -> Proposal`
- `DecisionEngine` will use it if present; otherwise falls back to reference
