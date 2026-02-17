# MDM Engine Integration Guide

## Installation

```bash
pip install mdm-engine
```

Or from source:
```bash
pip install -e .
```

## Basic Usage

### Running the Event Loop

```python
from ami_engine.loop.run_loop import run_loop
from ami_engine.adapters import MarketDataSource, Broker

# Implement your adapters
class MyMarketDataSource(MarketDataSource):
    def next_event(self):
        # Return event dict or None when exhausted
        return {"mid": 0.5, "bid": 0.49, "ask": 0.51, ...}

class MyBroker(Broker):
    def submit_order(self, order):
        # Submit order to exchange
        pass

# Run loop
summary = run_loop(
    source=MyMarketDataSource(),
    broker=MyBroker(),
    steps=100,
    dry_run=False,
)
```

### Using Private MDM Hook

Create `ami_engine/mdm/_private/model.py`:

```python
from decision_schema.types import Proposal, Action

def compute_proposal_private(features, **kwargs):
    # Your proprietary MDM logic
    confidence = compute_confidence(features)
    return Proposal(
        action=Action.ACT if confidence > 0.7 else Action.HOLD,
        confidence=confidence,
        reasons=["custom_model"],
        params={"value": features.get("mid")},
    )
```

The `DecisionEngine` will automatically use this if present.

### Feature Extraction

```python
from ami_engine.features.feature_builder import build_features

features = build_features(
    event={"mid": 0.5, "bid": 0.49, "ask": 0.51, ...},
    mid_history=[0.49, 0.50, 0.51],
    now_ms=1234567890,
)
# Returns: {"mid": 0.5, "spread_bps": 400, "depth": 100, ...}
```

### Integration with DMC

MDM Engine outputs `Proposal` (from `decision-schema`):

```python
from decision_schema.types import Proposal
proposal = Proposal(action=Action.ACT, confidence=0.8, ...)
```

DMC modulates this proposal:

```python
from dmc_core.dmc.modulator import modulate
from dmc_core.dmc.risk_policy import RiskPolicy

final_action, mismatch = modulate(proposal, RiskPolicy(), context)
```

## Trace/Audit

### PacketV2 Logging

```python
from ami_engine.trace.trace_logger import TraceLogger

logger = TraceLogger(run_id="run_123", output_dir="./traces")
logger.log_packet(packet_v2)
```

### Security Redaction

```python
from ami_engine.security.redaction import redact_secrets

safe_dict = redact_secrets({"api_key": "secret123", "mid": 0.5})
# Returns: {"api_key": "***REDACTED***", "mid": 0.5}
```

## Simulation (Testing)

```python
from ami_engine.sim.microstructure_sim import MicrostructureSim
from ami_engine.sim.synthetic_source import SyntheticSource
from ami_engine.sim.paper_broker import PaperBroker

sim = MicrostructureSim(mid=0.5, spread=0.01)
source = SyntheticSource(sim, num_events=100)
broker = PaperBroker()

summary = run_loop(source=source, broker=broker, steps=100)
```

## Configuration

MDM Engine uses `decision-schema` types. No domain-specific configuration is required.

For DMC integration, see `decision-modulation-core` documentation.
