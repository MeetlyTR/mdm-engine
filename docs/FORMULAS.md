# MDM Engine Formulas

## Feature Extraction

### Basic Features

```
mid = (best_bid + best_ask) / 2
spread = ask - bid
spread_bps = 10000 * spread / max(mid, epsilon)
depth = sum(top_N_bids) + sum(top_N_asks)
imbalance = (sum(bids) - sum(asks)) / (sum(bids) + sum(asks))
```

### Advanced Features

```
microprice = (bid * sum(asks) + ask * sum(bids)) / (sum(bids) + sum(asks))
vwap = sum(price_i * qty_i) / sum(qty_i)  # Over top N levels
pressure = (bid_depth - ask_depth) / (bid_depth + ask_depth)
sigma = std(Δmid)  # Rolling window
sigma_spike_z = (sigma_current - sigma_mean) / sigma_std
cost_ticks = spread_ticks / 2  # Approximate cost
```

### Regime Features (5-minute rolling)

```
sigma_5m = std(Δmid) over 5-minute window
spread_med_5m = median(spread_bps) over 5-minute window
depth_p10_5m = 10th percentile(depth) over 5-minute window
```

## Reference MDM Scoring

### Logistic Confidence Score

```
signal = w1 * imbalance + w2 * pressure + w3 * (sigma_spike_z < threshold)
confidence = sigmoid(signal) = 1 / (1 + exp(-signal))
```

If `confidence >= min_confidence_to_quote` AND `imbalance >= imbalance_min_to_quote`:
- Action = `ACT`
- Size clamped to `max_per_market_usd`

Otherwise:
- Action = `HOLD`

### Reference Position Manager

```
if position_exists:
    if realized_pnl >= take_profit_ticks:
        action = EXIT
    elif realized_pnl <= -stop_loss_ticks:
        action = EXIT
    elif time_in_position_ms >= max_time_in_position_ms:
        action = EXIT
```

## Latency Metrics

```
latency_ms = now_ms - event_ts_ms
feature_latency_ms = feature_end_ts - event_ts_ms
mdm_latency_ms = mdm_end_ts - feature_end_ts
dmc_latency_ms = dmc_end_ts - mdm_end_ts
execution_latency_ms = execution_end_ts - dmc_end_ts
```

## Trace Packet

```
PacketV2(
    packet_version="2",
    schema_version="0.1.0",
    run_id=run_id,
    step=step,
    input=event_dict,
    external=context_dict,
    mdm=proposal_dict,
    final_action=final_decision_dict,
    latency_ms=total_latency_ms,
    mismatch=mismatch_info_dict if any,
)
```
