# Trading Domain Example

**Note**: This is a domain-specific example. Trading terminology is kept here for reference only. The core MDM Engine is domain-agnostic.

## Use Case

A trading system that:
- Receives market data (prices, order book, trades)
- Generates trading proposals based on microstructure features
- Applies risk guards via DMC before executing trades

## Event Structure

```python
event = {
    "timestamp_ms": 1000000,
    "market_data": {
        "bid": 0.49,
        "ask": 0.51,
        "bid_depth": 100.0,
        "ask_depth": 100.0,
        "last_trade": 0.50,
    },
    "order_book": {
        "bids": [(0.49, 100), (0.48, 200)],
        "asks": [(0.51, 100), (0.52, 200)],
    },
}
```

## Feature Extraction

```python
from mdm_engine.features.feature_builder import build_features

features = build_features(event, mid_history=[], ...)

# Features include:
# - mid = (bid + ask) / 2
# - spread_bps = (ask - bid) / mid * 10000
# - depth = bid_depth + ask_depth
# - imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
# - Advanced: microprice, VWAP, pressure, sigma, etc.
```

## Proposal Generation

```python
from mdm_engine.mdm.decision_engine import DecisionEngine
from decision_schema.types import Action

mdm = DecisionEngine(confidence_threshold=0.5)

proposal = mdm.propose(features)

# Proposal example (using params dict, not direct fields):
# Proposal(
#     action=Action.ACT,  # Execute trade
#     confidence=0.75,
#     reasons=["imbalance", "alpha"],
#     params={
#         "bid_quote": 0.49,
#         "ask_quote": 0.51,
#         "size_usd": 1.0,
#         "post_only": True,
#     },
# )
```

## DMC Integration

```python
from decision_modulation_core.dmc.modulator import modulate
from decision_modulation_core.dmc.risk_policy import RiskPolicy

# Context from system state
context = {
    "now_ms": 1000000,
    "last_event_ts_ms": 999000,
    "depth": 100.0,
    "spread_bps": 400.0,
    "current_total_exposure_usd": 5.0,
    "abs_inventory": 2.0,
    "daily_realized_pnl_usd": -10.0,
    "ops_deny_actions": False,
}

policy = RiskPolicy(
    staleness_ms=1000,
    max_spread_bps=500.0,
    max_total_exposure_usd=10.0,
    daily_loss_stop_usd=-20.0,
    # ... other thresholds
)

final_action, mismatch = modulate(proposal, policy, context)

if mismatch.flags:
    print(f"Guards triggered: {mismatch.flags}")
    # Do not execute trade
else:
    # Execute trade
    execute_trade(final_action.params)
```

## Execution

```python
def execute_trade(params: dict):
    bid_quote = params.get("bid_quote")
    ask_quote = params.get("ask_quote")
    size_usd = params.get("size_usd")
    post_only = params.get("post_only", False)
    
    # Submit orders to exchange
    submit_order(bid_quote, ask_quote, size_usd, post_only)
```

## Notes

- This example uses trading-specific terminology (`bid`, `ask`, `spread`, `depth`) for illustration only
- The core MDM Engine is domain-agnostic and works with any event structure
- Domain-specific adapters and execution logic should be implemented separately
