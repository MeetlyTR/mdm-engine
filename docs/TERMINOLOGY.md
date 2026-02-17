# Terminology

## Core Concepts

### MDM (Market Decision Model)

A model that generates **action proposals** from market features:
- Input: Market features (mid, spread, depth, imbalance, etc.)
- Output: `TradeProposal` (action, confidence, reasons, quotes, size)

MDM Engine provides a **reference implementation** (simple logistic scoring). Production MDMs should use the private hook.

### DMC (Decision Modulation Core)

A risk-aware decision layer that modulates MDM proposals:
- Input: `TradeProposal` + context + risk policy
- Output: `FinalAction` + `MismatchInfo`

DMC applies guards (staleness, liquidity, exposure, etc.) and may override proposals to HOLD/FLATTEN/CANCEL_ALL/STOP.

See `decision-modulation-core` repository for DMC documentation.

### Proposal

MDM output: proposed action with confidence and reasons. May be modified by DMC.

### Final Action

Post-DMC action: what should actually be executed. May differ from proposal if guards triggered.

### Mismatch

When DMC overrides a proposal, it sets mismatch flags and reason codes explaining why.

### Features

Market microstructure features extracted from order book snapshots:
- Basic: mid, spread, depth, imbalance
- Advanced: microprice, VWAP, pressure, sigma, sigma_spike_z

### Event

A market data snapshot (order book, timestamp, etc.) from `MarketDataSource`.

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

- **QUOTE**: Submit bid/ask quotes
- **FLATTEN**: Close position (cancel orders + close)
- **HOLD**: Do nothing
- **CANCEL_ALL**: Cancel all orders
- **STOP**: Stop trading (cancel all + stop)

## Guard Types

See `decision-modulation-core/docs/GUARDS_AND_FORMULAS.md` for complete list.

Common guards:
- Staleness: Reject stale data
- Liquidity: Require minimum depth
- Spread: Reject wide spreads
- Exposure: Limit total USD exposure
- Inventory: Limit absolute inventory
- Cancel Rate: Throttle on high cancel rate
- Daily Loss: Stop after loss threshold
- Adverse Selection: Monitor fill quality

## Interfaces

### MarketDataSource

Abstract interface for market events:
- `next_event() -> dict | None`: Get next event or None if exhausted

### Broker

Abstract interface for order execution:
- `get_state() -> dict`: Get broker state (cash, positions, exposure)
- `submit_order(...) -> dict`: Submit order
- `cancel_order(order_id) -> bool`: Cancel order
- `cancel_all(market_id) -> int`: Cancel all orders
- `process_fills(now_ms) -> list[dict]`: Get fill events

## Reference vs Private

- **Reference**: Public, explainable implementations (reference MDM, reference position manager)
- **Private**: Gitignored, proprietary implementations (private MDM hook, private execution logic)

Public tests must pass with reference implementations only.
