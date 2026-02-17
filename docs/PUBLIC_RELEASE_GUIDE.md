# Public Release Guide

Checklist for making MDM Engine public-safe.

## Pre-Release Checklist

### Code Cleanup

- [ ] Remove all exchange-specific adapters (external exchange integrations)
- [ ] Remove all trading/bot artifacts (dashboards, scripts, configs)
- [ ] Remove external integration tests and references
- [ ] Verify `git grep -i exchange` returns only generic terms
- [ ] Verify no external service names appear in code
- [ ] Verify `git grep -i trading` returns nothing (except generic terms)

### Secrets and Security

- [ ] Verify `.gitignore` includes: `.env*`, `*.local`, `*.secrets*`, `runs/`, `traces/`, `*.log`
- [ ] Verify `mdm_engine/mdm/_private/` is gitignored
- [ ] Check git history for secrets (see `SECURITY.md`)
- [ ] Add `SECURITY.md` with warnings if history contains secrets
- [ ] Verify no API keys, private keys, or credentials in code
- [ ] Verify redaction utilities work (`tests/test_security_redaction.py`)

### Documentation

- [ ] `README.md` explains what MDM Engine is and is NOT
- [ ] `SECURITY.md` documents security policy
- [ ] `docs/ARCHITECTURE.md` describes system architecture
- [ ] `docs/TERMINOLOGY.md` defines key terms
- [ ] `docs/SAFETY_LIMITATIONS.md` documents limitations
- [ ] `docs/PUBLIC_RELEASE_GUIDE.md` (this file)

### Tests

- [ ] All tests pass: `pytest tests/`
- [ ] No network tests (all unit tests)
- [ ] Tests cover reference MDM behavior
- [ ] Tests cover private hook optional behavior
- [ ] Tests cover redaction
- [ ] Tests pass without `_private/` present

### Reference MDM

- [ ] `mdm_engine/mdm/reference_model.py` is simple and explainable
- [ ] `mdm_engine/mdm/decision_engine.py` uses private hook if available
- [ ] `mdm_engine/mdm/position_manager.py` is reference only (basic TP/SL)

### Package Structure

- [ ] `pyproject.toml` has correct name and description
- [ ] Package structure matches target:
  ```
  mdm_engine/
    loop/
      run_loop.py
    adapters/
      base.py (interfaces only)
    features/
      feature_builder.py
    mdm/
      reference_model.py
      decision_engine.py
      position_manager.py
    execution/
      executor.py
      order_manager.py (reference)
    trace/
      trace_logger.py
    security/
      redaction.py
      audit.py
    sim/
      microstructure_sim.py (for testing)
      synthetic_source.py
      paper_broker.py
  ```

## Post-Release

- [ ] Monitor issues for secret leaks
- [ ] Monitor issues for missing documentation
- [ ] Update `CHANGELOG.md` (if present) with release notes

## Notes

- MDM Engine is designed to be **generic** and work with any exchange (via adapters)
- Keep public code **explainable** (reference MDM uses simple formulas)
- Private hook allows **proprietary MDMs** without exposing them
- All components should be **testable** with simulation
