# Formulas — mdm-engine

Let x_t be a state vector extracted from raw inputs at time t.

## Proposal scoring

```
s_t = f_theta(x_t, c_t)
```

Where:
- `s_t` is a real-valued score (or score vector)
- `c_t` is context (non-domain, operational metadata)
- `f_theta` is a deterministic function under a given profile

## Confidence

```
conf_t = sigma(s_t)   (e.g., sigmoid/softmax depending on action space)
```

## Invariants

- `conf_t ∈ [0, 1]`
- `propose(x_t, c_t)` is deterministic for fixed inputs and profile
- exceptions => fail-closed proposal (`Action.HOLD` or `Action.STOP`)

## Feature extraction (generic)

Features are extracted from event dictionaries:

```
x_t = extract_features(event_t, history_t)
```

Where:
- `event_t`: Generic event dictionary (timestamp, values, metadata)
- `history_t`: Historical events for rolling statistics
- `x_t`: Feature vector (numeric values)

## Latency metrics

```
latency_ms = now_ms - event_ts_ms
feature_latency_ms = feature_end_ts - event_ts_ms
mdm_latency_ms = mdm_end_ts - feature_end_ts
```

## Trace packet

```
PacketV2(
    run_id=run_id,
    step=step,
    input=event_dict,  # Redacted
    external=context_dict,  # Redacted
    mdm=proposal_dict,
    final_action=final_decision_dict,
    latency_ms=total_latency_ms,
    mismatch=mismatch_info_dict if any,
    schema_version="0.1.0",
)
```
