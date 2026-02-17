# Robotics Control Example

This example shows how to use MDM Engine for robotics control systems.

## Use Case

A robotics control system that:
- Receives sensor readings (camera, lidar, IMU)
- Generates movement proposals based on sensor data
- Applies safety guards via DMC before sending commands to actuators

## Event Structure

```python
event = {
    "timestamp_ms": 1000000,
    "sensors": {
        "camera": {
            "obstacle_distance_m": 2.5,
            "obstacle_angle_deg": 45,
        },
        "lidar": {
            "front_distance_m": 2.3,
            "left_distance_m": 1.8,
            "right_distance_m": 2.1,
        },
        "imu": {
            "velocity_mps": 0.5,
            "acceleration_mps2": 0.1,
        },
    },
    "battery": {
        "level_percent": 75,
        "voltage_v": 12.5,
    },
    "target": {
        "x_m": 10.0,
        "y_m": 5.0,
        "distance_m": 11.2,
    },
}
```

## Feature Extraction

```python
from mdm_engine.features.feature_builder import build_features

features = build_features(event, history=[], ...)

# Features include:
# - sensors.camera.obstacle_distance_m
# - sensors.lidar.front_distance_m
# - sensors.imu.velocity_mps
# - battery.level_percent
# - target.distance_m
# - Derived features (collision risk, path clearance, etc.)
```

## Proposal Generation

```python
from mdm_engine.mdm.decision_engine import DecisionEngine
from decision_schema.types import Action

mdm = DecisionEngine(confidence_threshold=0.6)

proposal = mdm.propose(features)

# Proposal example:
# Proposal(
#     action=Action.ACT,  # Move forward
#     confidence=0.75,
#     reasons=["clear_path", "sufficient_battery"],
#     params={
#         "movement_type": "forward",
#         "speed_mps": 0.5,
#         "duration_ms": 1000,
#         "target_x": 10.0,
#         "target_y": 5.0,
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
    "battery_level_percent": 75,
    "error_count": 1,
    "latency_ms": 50,
    "current_total_exposure": 0.5,  # Current movement risk
    "ops_deny_actions": False,
}

policy = RiskPolicy(
    staleness_ms=1000,
    max_error_rate=0.05,
    max_total_exposure=1.0,  # Max movement risk
    max_latency_ms=100,
    # ... other thresholds
)

final_action, mismatch = modulate(proposal, policy, context)

if mismatch.flags:
    print(f"Guards triggered: {mismatch.flags}")
    # Emergency stop
    emergency_stop()
else:
    # Execute movement command
    execute_movement(final_action.params)
```

## Execution

```python
def execute_movement(params: dict):
    movement_type = params.get("movement_type")
    speed_mps = params.get("speed_mps", 0.0)
    duration_ms = params.get("duration_ms", 0)
    
    if movement_type == "forward":
        robot.move_forward(speed_mps, duration_ms)
    elif movement_type == "rotate":
        angle_deg = params.get("angle_deg", 0)
        robot.rotate(angle_deg)
    elif movement_type == "stop":
        robot.stop()
```
