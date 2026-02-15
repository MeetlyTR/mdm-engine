# MDM Architecture

## Overview

MDM is a **decision regulator**: it does not make domain decisions but monitors and constrains them. Input: **raw state** (from an adapter). Output: **action** (safe vector), **escalation level** (L0/L1/L2), and full **audit packet** (trace, confidence, drift, clamps).

## Core mathematical flow

1. **State encoding**  
   Raw state (physical, social, context, risk, compassion, justice, harm_sens, responsibility, empathy) → clamped [0,1] vectors `x_ext`, `x_moral`.

2. **Action grid**  
   Generator builds candidate actions (e.g. [severity, compassion, intervention, delay] over a grid). Each action is scored.

3. **Moral scores (W, J, H, C)**  
   For each (state, action), compute Wellbeing, Justice, Harm, Compassion. Constraints: J ≥ J_MIN, H ≤ H_MAX, C in [C_MIN, C_MAX]. Invalid candidates are dropped.

4. **Fail-safe**  
   If no candidate is valid, or worst-case (min J, max H) exceeds critical thresholds (J_CRIT, H_CRIT), the engine overrides to a **safe action** and sets level to L2.

5. **Selection**  
   Among valid candidates, select by score (e.g. weighted sum) and tie-breaking (e.g. Pareto, margin). Output: chosen action + selection reason.

6. **Confidence & uncertainty**  
   From the chosen action’s scores and constraint margin, compute **confidence**. From candidate spread and action-space coverage, compute **uncertainty** (e.g. CUS, as_norm, divergence).

7. **Escalation**  
   Level 0/1/2 from rules: e.g. confidence_low → L2; H_selected &gt; H_high → L1; constraint_margin &lt; 0 → L1; drift/uncertainty thresholds can add L1.

8. **Temporal drift**  
   CUS history over time; if delta or mean exceeds thresholds, optional preemptive L1.

9. **Soft clamp (L1)**  
   If level is L1, the raw action can be softly moved toward a safe envelope (CUS-weighted).

10. **Output**  
    Action, escalation, reason, trace, confidence, uncertainty, drift, clamps → **decision packet** (schema v2: root key `"mdm"`).

## Components

- **core/** — State encoder, action generator, moral evaluator, constraint validator, fail-safe, soft override, confidence, uncertainty, temporal drift, trace logger.
- **mdm_engine/** — Engine orchestration, API, CLI, audit_spec (packet build, CSV/flat row, schema v2 validation), invariants.
- **config_profiles/** — Named configs (scenario_test, wiki_calibrated, production_safe, …).
- **tools/** — Live wiki audit (EventStreams + ORES + decide → JSONL/CSV), exporters.
- **visualization/** — Streamlit dashboard (load JSONL, live stream, review queue, CSV export).

## Data flow (Wiki adapter)

1. EventStreams → edit event.
2. ORES → `p_damaging`, `p_goodfaith`, decision (ALLOW/FLAG).
3. Adapter builds **state** from event + ORES (risk = p_damaging, etc.).
4. `decide(state, context, profile=wiki_calibrated)` → engine result.
5. `build_decision_packet(..., engine_result)` → packet with `"mdm"` only (schema v2).
6. Append to JSONL; CSV export uses `decision_packet_to_csv_row` (all columns `mdm_*` or neutral).
