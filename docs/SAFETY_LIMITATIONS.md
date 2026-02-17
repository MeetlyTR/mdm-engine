# Safety Limitations

## What MDM Engine Does NOT Guarantee

MDM Engine is a **runtime system**, not a complete trading system. Important limitations:

### 1. No Guarantee of Profitability

MDM Engine does not guarantee profitable trading. The reference MDM is for demonstration only. Production MDMs should use the private hook.

### 2. No Risk Management

MDM Engine generates proposals but does not manage risk. Risk management is provided by DMC (Decision Modulation Core). MDM Engine must be used with DMC.

### 3. No Exchange Integration

MDM Engine provides **interfaces** (`MarketDataSource`, `Broker`) but no implementations. Users must implement these for their exchange/data source.

### 4. No Position Management

The reference `PositionManager` is basic (TP/SL/time stops). Production systems should use a proper position management system.

### 5. No Order Lifecycle Management

The reference `OrderManager` is basic (cancel/replace logic). Production systems should use a proper order management system.

### 6. No Fill Guarantee

MDM Engine does not guarantee fills. Execution depends on:
- Broker implementation
- Exchange behavior
- Network latency
- Market conditions

### 7. No Market Regime Detection

MDM Engine extracts features but does not detect market regime changes. Downstream systems should implement regime detection.

### 8. Reference MDM Is Not Production-Ready

The reference MDM (`reference_model.py`) is a **demonstration**. It uses simple logistic scoring and is not optimized for any market. Production MDMs should use the private hook.

## What MDM Engine DOES Provide

- **Event loop orchestration**: Coordinates MDM → DMC → execution flow
- **Feature extraction**: Generic market microstructure features
- **Reference implementations**: For testing and demonstration
- **Trace/audit**: Logging and security utilities
- **Private hook pattern**: Allows proprietary MDMs without exposing them

## Recommendations

1. **Use with DMC**: MDM Engine must be used with DMC for risk management
2. **Implement adapters**: Provide `MarketDataSource` and `Broker` implementations for your exchange
3. **Use private MDM hook**: Implement proprietary MDM in `ami_engine/mdm/_private/`
4. **Monitor traces**: Use `traces.jsonl` and `security_audit.jsonl` for debugging
5. **Test thoroughly**: Test with simulation before live trading

## When NOT to Use MDM Engine

- If you need exchange-specific adapters (implement them yourself)
- If you need risk management (use DMC)
- If you need position management (use a position management system)
- If you need order lifecycle management (use an order management system)
- If you need market regime detection (implement it separately)

MDM Engine is designed to be **one component** in a larger system, not a complete solution.
