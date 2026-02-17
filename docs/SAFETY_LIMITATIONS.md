# Safety Limitations

## What MDM Engine Does NOT Guarantee

MDM Engine is a **runtime system**, not a complete decision system. Important limitations:

### 1. No Guarantee of Positive Outcomes

MDM Engine does not guarantee positive outcomes. The reference MDM is for demonstration only. Production MDMs should use the private hook.

### 2. No Risk Management

MDM Engine generates proposals but does not manage risk. Risk management is provided by DMC (Decision Modulation Core). MDM Engine should be used with DMC for production systems.

### 3. No Domain Integration

MDM Engine provides **interfaces** (`DataSource`, `Executor`) but no implementations. Users must implement these for their domain/data source.

### 4. No State Management

The reference state management is basic. Production systems should use a proper state management system.

### 5. No Action Lifecycle Management

The reference action management is basic (cancel/replace logic). Production systems should use a proper action management system.

### 6. No Execution Guarantee

MDM Engine does not guarantee successful execution. Execution depends on:
- Executor implementation
- Domain-specific behavior
- Network latency
- System conditions

### 7. No Regime Detection

MDM Engine extracts features but does not detect system regime changes. Downstream systems should implement regime detection if needed.

### 8. Reference MDM Is Not Production-Ready

The reference MDM (`reference_model.py`) is a **demonstration**. It uses simple logistic scoring and is not optimized for any domain. Production MDMs should use the private hook.

## What MDM Engine DOES Provide

- **Event loop orchestration**: Coordinates MDM → DMC → execution flow
- **Feature extraction**: Generic features from event data
- **Reference implementations**: For testing and demonstration
- **Trace/audit**: Logging and security utilities
- **Private hook pattern**: Allows proprietary MDMs without exposing them

## Recommendations

1. **Use with DMC**: MDM Engine should be used with DMC for risk management
2. **Implement adapters**: Provide `DataSource` and `Executor` implementations for your domain
3. **Use private MDM hook**: Implement proprietary MDM in `ami_engine/mdm/_private/`
4. **Monitor traces**: Use `traces.jsonl` and `security_audit.jsonl` for debugging
5. **Test thoroughly**: Test with simulation before live execution

## When NOT to Use MDM Engine

- If you need domain-specific adapters (implement them yourself)
- If you need risk management (use DMC)
- If you need state management (use a state management system)
- If you need action lifecycle management (use an action management system)
- If you need regime detection (implement it separately)

MDM Engine is designed to be **one component** in a larger system, not a complete solution.
