# Decision Packet Schema v2

All audit packets and CSV exports use **schema v2**. No legacy top-level key is allowed; the engine output is under **"mdm"** only.

## Top-level keys (packet)

- **schema_version** — Must be "2.0" (or compatible). Missing or lower version is rejected by dashboard and validators.
- **run_id**, **ts**, **source**, **entity_id**
- **input** — Domain input (e.g. title, user, revid, state_snapshot).
- **external** — External signal (e.g. ORES decision, p_damaging, p_goodfaith).
- **mdm** — **Required.** All engine-derived fields:
  - level, reason, soft_clamp, signals, explain, human_escalation
  - confidence*, constraint_margin, uncertainty, temporal_drift
  - escalation_driver, escalation_drivers, selection_reason
  - J, H, worst_H, worst_J, action, raw_action, …
- **final_action** — APPLY | APPLY_CLAMPED | HOLD_REVIEW.
- **final_action_reason** — Policy-facing reason string.
- **mismatch** — True if external decision and MDM level disagree in a defined way.
- **clamps** — List of applied clamps (type, strength, …).
- **review** — L2 review state (status, decision, category, note).
- Plus optional: latency_ms, mdm_latency_ms, config_profile, git_commit, host, session_id, adapter_version, source_event_id, mdm_input_risk, mdm_input_state_hash, ores_*.

Unknown top-level keys (e.g. legacy key) cause **validation error**. Use only the keys above or documented extensions.

## CSV columns (mdm_* only)

All engine/packet-derived columns use the **mdm_** prefix, e.g.:

- mdm_level, mdm_reason, mdm_human_escalation
- mdm_confidence, mdm_confidence_internal, mdm_confidence_used, mdm_confidence_source
- mdm_constraint_margin, mdm_H, mdm_J, mdm_worst_H, mdm_worst_J
- mdm_cus, mdm_cus_mean, mdm_divergence, mdm_drift_*, mdm_soft_clamp
- mdm_latency_ms, mdm_input_risk, mdm_input_state_hash

Config snapshot columns (cfg_*) and ORES columns (ores_*) are unchanged. No column name may use a legacy prefix.

## Validation

- **validate_packet_schema_v2(packet)** — Raises if "mdm" missing or legacy top-level key present.
- Dashboard and exporters reject packets with schema_version missing or less than 2.0.
