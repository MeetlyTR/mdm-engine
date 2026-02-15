# Calibration Guide (short)

Calibration = choosing **config profile** and (optionally) tuning thresholds so L0/L1/L2 and clamp behavior match your policy.

## Profiles

- **scenario_test** — General scenarios; moderate thresholds.
- **wiki_calibrated** — For Wiki/ORES: looser J_MIN, higher H_CRIT/CUS_MEAN so L0 can appear; AS_SOFT_THRESHOLD 0 so as_norm_low does not dominate.
- **production_safe** — Stricter for production.
- **high_critical** — Stricter H/J thresholds.

Set default via **MDM_CONFIG_PROFILE** (e.g. `wiki_calibrated` for live wiki audit).

## Key knobs

- **H_MAX, J_MIN, C_MIN, C_MAX** — Constraint box; actions outside trigger invalid or escalation.
- **H_CRITICAL** — Above this H → fail-safe (L2).
- **CONFIDENCE_ESCALATION_FORCE** — Below this confidence → L2 (or L1 per CONFIDENCE_LOW_ESCALATION_LEVEL).
- **CUS_MEAN_THRESHOLD, DELTA_CUS_THRESHOLD** — Temporal drift → optional L1.
- **AS_SOFT_THRESHOLD** — Action-space uncertainty; below → L1 (set 0 to disable in some profiles).

## Escalation vs. selected action

L1/L2 should be driven by the **selected action** (e.g. H_selected), not by worst_H over the whole grid. See docs/ESCALATION_H_HIGH_PLAN.md for the intended rule set (H_selected for H_high/H_critical; plausible-set worst only when uncertainty is high).

## Checking behavior

1. Run a batch (e.g. live_wiki_audit) and export CSV.
2. Inspect mdm_level, escalation_driver, mdm_H, mdm_confidence.
3. Adjust profile or thresholds and re-run.
