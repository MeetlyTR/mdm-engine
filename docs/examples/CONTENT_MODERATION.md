# Content Moderation Example

This example shows how to use MDM Engine for content moderation pipelines.

## Use Case

A content moderation system that:
- Receives content submissions (text, images, videos)
- Uses ML models to score content
- Generates proposals to moderate/flag/approve
- Applies risk guards via DMC before executing moderation actions

## Event Structure

```python
event = {
    "content_id": "abc123",
    "content_type": "text",
    "text": "User-submitted content...",
    "user_id": "user_456",
    "timestamp_ms": 1000000,
    "ml_scores": {
        "toxicity": 0.8,
        "spam": 0.3,
        "hate_speech": 0.2,
    },
    "user_history": {
        "previous_flags": 2,
        "account_age_days": 30,
    },
}
```

## Feature Extraction

```python
from mdm_engine.features.feature_builder import build_features

features = build_features(event, history=[], ...)

# Features include:
# - ml_scores.toxicity
# - ml_scores.spam
# - ml_scores.hate_speech
# - user_history.previous_flags
# - user_history.account_age_days
# - Aggregated statistics (rolling averages, etc.)
```

## Proposal Generation

```python
from mdm_engine.mdm.decision_engine import DecisionEngine
from decision_schema.types import Action

mdm = DecisionEngine(confidence_threshold=0.7)

proposal = mdm.propose(features)

# Proposal example:
# Proposal(
#     action=Action.ACT,  # Moderate content
#     confidence=0.85,
#     reasons=["high_toxicity_score", "user_history_flags"],
#     params={
#         "moderation_action": "flag",
#         "severity": "high",
#         "content_id": "abc123",
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
    "moderation_rate_per_minute": 15,
    "error_count": 2,
    "ops_deny_actions": False,
}

policy = RiskPolicy(
    staleness_ms=5000,
    max_error_rate=0.1,
    # ... other thresholds
)

final_action, mismatch = modulate(proposal, policy, context)

if mismatch.flags:
    print(f"Guards triggered: {mismatch.flags}")
    # Hold moderation, queue for human review
else:
    # Execute moderation action
    execute_moderation(final_action.params)
```

## Execution

```python
def execute_moderation(params: dict):
    action = params.get("moderation_action")
    content_id = params.get("content_id")
    
    if action == "flag":
        flag_content(content_id)
    elif action == "remove":
        remove_content(content_id)
    elif action == "approve":
        approve_content(content_id)
```
