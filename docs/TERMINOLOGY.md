# Terminology

## Core Concepts

### MDM (Model Decision Model / Decision Model)

A model that generates **action proposals** from features:
- Input: Features (numeric values, signals, state information, etc.)
- Output: `Proposal` (action, confidence, reasons, parameters)

MDM Engine provides a **reference implementation** (simple logistic scoring). Production MDMs should use the private hook.

### DMC (Decision Modulation Core)

A risk-aware decision layer that modulates MDM proposals:
- Input: `Proposal` + context + risk policy
- Output: `FinalDecision` + `MismatchInfo`

DMC applies guards (staleness, rate limits, exposure, etc.) and may override proposals to HOLD/EXIT/CANCEL/STOP.

See `decision-modulation-core` repository for DMC documentation.

### Proposal

MDM output: proposed action with confidence and reasons. May be modified by DMC.

### Final Action

Post-DMC action: what should actually be executed. May differ from proposal if guards triggered.

### Mismatch

When DMC overrides a proposal, it sets mismatch flags and reason codes explaining why.

### Features

Features extracted from event data (generic event dictionaries):
- Basic: numeric values, timestamps, counts
- Advanced: aggregations, rolling statistics, derived metrics

See `docs/examples/` for domain-specific feature extraction examples.

### Event

A data snapshot (timestamp, values, metadata, etc.) from `DataSource`.

### Trace

A `PacketV2` record written to `traces.jsonl` containing:
- Input event (redacted)
- External features (redacted)
- MDM proposal
- Final action
- Latency

### Audit

Security audit logs written to `security_audit.jsonl` containing:
- Order submissions
- Cancellations
- Errors
- Throttle events

## Action Types

- **ACT**: Execute action (domain-specific interpretation)
- **EXIT**: Exit current state/position
- **HOLD**: Do nothing
- **CANCEL**: Cancel pending actions
- **STOP**: Stop execution (emergency stop)

**Note**: Deprecated actions `QUOTE`, `FLATTEN`, `CANCEL_ALL` are aliases for generic actions. See `decision-schema` for details.

## Guard Types

See `decision-modulation-core/docs/GUARDS_AND_FORMULAS.md` for complete list.

Common guards:
- Staleness: Reject stale data
- Rate Limit: Throttle when rate exceeds limit
- Error Budget: Stop when error rate exceeds threshold
- Exposure: Limit total exposure/resource usage
- Cooldown: Enforce cooldown periods after failures
- Latency: Reject when latency exceeds threshold
- Daily Loss: Stop after loss threshold
- Drawdown: Stop when drawdown exceeds threshold

## Interfaces

### DataSource

Abstract interface for event streams:
- `next_event() -> dict | None`: Get next event or None if exhausted

### Executor

Abstract interface for action execution:
- `get_state() -> dict`: Get executor state (resources, positions, exposure)
- `execute_action(...) -> dict`: Execute action
- `cancel_action(action_id) -> bool`: Cancel action
- `cancel_all(resource_id) -> int`: Cancel all actions
- `process_results(now_ms) -> list[dict]`: Get execution results

**Note**: Domain-specific implementations (e.g., trading exchanges) should implement these interfaces. See `docs/examples/` for domain-specific adapter examples.

## Reference vs Private

- **Reference**: Public, explainable implementations (reference MDM, reference position manager)
- **Private**: Gitignored, proprietary implementations (private MDM hook, private execution logic)

Public tests must pass with reference implementations only.
