# MDM Engine Architecture

## Overview

MDM Engine is a **runtime system** for Market Decision Models. It orchestrates the flow: market events → features → MDM proposal → DMC modulation → execution → trace.

## Data Flow

```
MarketDataSource → Event → Feature Builder → MDM → Proposal
                                                      ↓
                                              DMC Modulator
                                                      ↓
                                              Final Action
                                                      ↓
                                              Executor → Broker
                                                      ↓
                                              Trace/Audit
```

## Components

### 1. Event Loop (`ami_engine/loop/run_loop.py`)

**Main orchestration function**: `run_loop()`

Steps:
1. Get event from `MarketDataSource`
2. Build features from event
3. MDM generates proposal
4. DMC modulates proposal (applies guards)
5. Execute final action via `Broker`
6. Trace PacketV2
7. Repeat until source exhausted

Returns summary dict with action counts, latencies, PnL, etc.

### 2. Feature Extraction (`ami_engine/features/feature_builder.py`)

**Function**: `build_features(event, mid_history, ...) -> dict`

Extracts:
- **Basic**: mid, spread, depth, imbalance
- **Advanced**: microprice, VWAP, pressure, sigma, sigma_spike_z, cost_ticks
- **Regime**: 5-minute rolling statistics (sigma_5m, spread_med_5m, depth_p10_5m)

Features are generic (no exchange-specific logic).

### 3. MDM (`ami_engine/mdm/`)

**Reference Implementation**:
- `reference_model.py`: Simple logistic scoring
- `decision_engine.py`: Wrapper that tries private hook, falls back to reference
- `position_manager.py`: Reference TP/SL/time stops

**Private Hook**:
- `ami_engine/mdm/_private/model.py` (gitignored)
- `compute_proposal_private(features, **kwargs) -> TradeProposal`
- If present, `DecisionEngine` uses it; otherwise uses reference

### 4. Adapters (`ami_engine/adapters/`)

**Interfaces** (no implementations):
- `MarketDataSource`: `next_event() -> dict | None`
- `Broker`: `get_state()`, `submit_order()`, `cancel_order()`, `cancel_all()`, `process_fills()`

Users implement these for their exchange/data source.

### 5. Execution (`ami_engine/execution/`)

- `executor.py`: Thin wrapper around `execute()` function
- `order_manager.py`: Reference order lifecycle management (cancel/replace logic)

### 6. Trace/Audit (`ami_engine/trace/`, `ami_engine/security/`)

- `TraceLogger`: Writes `PacketV2` to `traces.jsonl`
- `AuditLogger`: Writes security audit logs to `security_audit.jsonl`
- `redaction`: Redacts secrets from dicts before logging

### 7. Simulation (`ami_engine/sim/`)

Reference implementations for testing:
- `MicrostructureSim`: Synthetic market simulator
- `SyntheticSource`: Generates events from simulator
- `PaperBroker`: Paper trading broker (no real orders)

## Integration Points

### MDM → DMC

MDM outputs `TradeProposal` (from `dmc_core.schema.types`):
- `action`: Proposed action (QUOTE/FLATTEN/HOLD/etc.)
- `confidence`: [0, 1] confidence score
- `reasons`: List of reason strings
- Action-specific fields (quotes, size) if action == QUOTE

DMC modulates proposal and returns `FinalAction` + `MismatchInfo`.

### Execution → Broker

Executor calls `Broker` interface methods:
- `submit_order()` for QUOTE
- `cancel_all()` for FLATTEN/CANCEL_ALL/STOP
- `process_fills()` to get fill events

Broker implementation is user-provided (not in MDM Engine).

## Design Principles

1. **Generic**: No exchange-specific or trading-specific logic
2. **Modular**: Clear interfaces (adapters, MDM hook)
3. **Traceable**: Every step logged (PacketV2)
4. **Secure**: Secrets redacted before logging
5. **Testable**: Reference implementations for testing

## Private Hook Pattern

Both MDM and execution support private hooks:

- **MDM**: `ami_engine/mdm/_private/model.py` → `compute_proposal_private()`
- **Execution**: User can override `Executor` behavior

Public tests must pass without `_private/` present.
