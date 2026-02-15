# MDM Terminology

**Model Denetim Motoru (MDM) / Model Oversight Engine** — L0/L1/L2 oversight, clamps, human review, audit telemetry.

## Levels (L0 / L1 / L2)

| Level | Meaning | System action |
|-------|--------|----------------|
| **L0** | Safe; automatic decision applicable | Apply decision, log packet, optional light sampling |
| **L1** | At margin; soft intervention | Apply with soft clamp (throttle/visibility), optional light review |
| **L2** | Stop; human review required | No automatic effect; put in Review Queue (Pending) |

## Core terms

- **State** — Encoded input: physical, social, context, risk + compassion, justice, harm_sens, responsibility, empathy (all [0,1]).
- **Action** — Vector [severity, compassion, intervention, delay]. Grid of candidates is scored.
- **W / J / H / C** — Wellbeing, Justice, Harm, Compassion (moral scores per action).
- **Fail-safe** — If no candidate passes constraints (e.g. J below J_MIN or H above H_CRIT), override to safe action and L2.
- **Soft clamp** — At L1, raw action is moved toward a safe envelope (CUS/uncertainty–weighted).
- **Escalation driver** — Reason for level: e.g. none, H_high, confidence_low, fail_safe, as_norm_low, temporal_drift.
- **Decision packet** — Schema v2 object: schema_version, run_id, input, external, mdm (level, reason, signals), final_action, clamps, review.
- **Adapter** — Domain layer that builds state and (optionally) external signal (e.g. ORES for Wiki); calls decide() and builds the packet.

## Env / CLI

- **MDM_CONFIG_PROFILE** — Config profile name (e.g. wiki_calibrated, scenario_test).
- **MDM_REVIEW_LOG** — Path to review log JSONL (L2 human decisions).
- **CLI** — Single entry: mdm (e.g. mdm dashboard, mdm realtime).

## Audit / CSV

- **mdm_*** — All engine/packet-derived columns in CSV (e.g. mdm_level, mdm_reason, mdm_H, mdm_confidence).
- **schema_version** — Packet and CSV use schema v2.0; only "mdm" key at top level for engine output.
