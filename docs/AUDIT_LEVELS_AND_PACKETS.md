# L0/L1/L2 Oversight and Decision Packet

This document defines **oversight levels** and the **Decision Packet** schema used by the engine regardless of the connected system.

## 1) L0 / L1 / L2: What the system does

| Level | Meaning | System action | Dashboard |
|-------|---------|---------------|-----------|
| **L0** | Safe; automatic decision applicable | Apply decision; record packet; optional 1–5% sampling review | L0: OK + explain + "Open details" |
| **L1** | Borderline; soft intervention | Apply but constrain (throttle/limit); optional L1 review queue | L1: Clamp Applied + reason + "Promote to L2" |
| **L2** | Stop; human review required | No automatic effect; send to Review Queue; Approve/Reject/Category+Note | L2: Human required + content/diff + actions |

Code: `mdm_engine.audit_spec.LEVEL_SPEC` and `get_level_spec(level)`.

## 2) Decision Packet (single standard output)

The same JSON structure is used at every level (L0/L1/L2). Source: live stream, simulation, or other adapter.

- **SSOT = Decision Packet JSONL** — Full evidence; live or export stored as JSONL.
- **CSV = audit_full (analytics)** — Flattened view for filtering and diagnostics.

### CSV export columns (audit_full)

| Group | Columns |
|-------|---------|
| Identity / latency | time, latency_ms, run_id, title, user, revid, comment |
| ORES | ores_decision, ores_p_damaging, ores_p_goodfaith, ores_threshold, ores_model |
| MDM input | mdm_input_risk (risk passed to MDM; compare with ores_p_damaging) |
| Final action | final_action: APPLY / APPLY_CLAMPED / HOLD_REVIEW |
| Clamp | clamp_applied, clamp_types, clamp_count, mdm_soft_clamp + confidence, cus, divergence, etc. |
| Action / scores | mdm_action_*, mdm_J, mdm_H |
| Uncertainty | unc_* |
| Evidence / review | diff_available, review_status, review_decision, review_category, review_note |

**ORES vs MDM:** ORES drives the external suggestion; MDM drives the applied action. Mismatch = ORES ALLOW but MDM L1/L2, or ORES FLAG but MDM L0 → mismatch=1.

## 3) Engine output signals

From `decide()`: escalation, reason, soft_safe_applied; uncertainty (cus, divergence); constraint_margin; temporal_drift (cus_mean). Dashboard "Explain + Top Signals" uses these. Extraction: `mdm_engine.audit_spec.extract_mdm_signals(engine_result)`.

## 4) Dashboard sections

- **Live Monitor:** Events/min, L0/L1/L2 ratio, last 200 events, filters (level, FLAG/ALLOW).
- **Decision Detail:** Selected packet: summary, explain, external decision, signals, content/diff; for L2: Approve/Reject + category + note.
- **Review Queue:** L2 only, status=pending. List, open detail, Approve/Reject.
- **Search & Audit:** Date/user/title/level filters, L0 sampling, open detail from results.
- **Quality:** review_log.jsonl: L2 override rate (Reject %), category distribution, reason→override.

## 5) Adapter contract (checklist)

For a new adapter, the packet must provide at least: external.*, input.*, mdm_input_risk + state_snapshot + mdm_input_state_hash, source_event_id, final_action, clamps, final_action_reason; for L2: evidence_status, diff/evidence; schema_version, adapter_version recommended.

## 6) Calibration and “system healthy” criteria

**Spine vs calibration:** Correct export/format, consistent run context, healthy ORES, correct mapping (mdm_input_risk == ores_p_damaging) → **telemetry/spine** is solid. That does not mean MDM behaviour is calibrated.

### Minimum two conditions for “system working correctly”

1. **L0 is produced** — At least some events are L0.
2. **L1 only in truly borderline band** — e.g. p_damaging in mid band (0.1–0.6); L0 at low risk, L2 occasionally at high risk.

If **all rows are L1**, that is **degenerate mode** (everything clamped); review thresholds/profile or drift warmup.

### Profile / calibration strategy (single rule)

- Per adapter: **default profile** + **calibrated profile** (e.g. scenario_test + wiki_calibrated).
- Calibration goal: L0 majority in low-risk band; L1 dense in mid band; L2 occasionally at high risk/drift/mismatch.
- Parameter change order: (1) AS_SOFT_THRESHOLD, (2) CUS_MEAN_THRESHOLD (drift), (3) DIVERGENCE_HARD_THRESHOLD / CONFIDENCE_ESCALATION_FORCE, (4) adapter drivers.

### Confidence: external vs internal

- **Internal confidence:** From engine (selected action scores); can stay low with wiki/ORES and push everything to L2 (confidence_low).
- **External confidence (adapter):** If context provides external_confidence, engine uses it for escalation. Wiki adapter sets distance-to-threshold so confidence_low does not blindly push to L2.
- **CONFIDENCE_LOW_ESCALATION_LEVEL:** If 1 in profile, confidence_low → L1 (default 2).

### Driver taxonomy (core contract)

| Driver | Meaning |
|--------|--------|
| none | No escalation (L0) |
| as_norm_low | AS_norm < AS_SOFT_THRESHOLD |
| constraint_violation | constraint_margin < 0 |
| confidence_low | confidence below threshold → L2 (or L1 if CONFIDENCE_LOW_ESCALATION_LEVEL=1) |
| H_critical | H > h_crit → L2 |
| divergence_high | divergence > DIVERGENCE_HARD_THRESHOLD → L2 |
| temporal_drift:mean | cus_mean > CUS_MEAN_THRESHOLD (after warmup) |
| temporal_drift:delta | delta_cus > DELTA_CUS_THRESHOLD |
| fail_safe | Fail-safe override |

Adapter-specific drivers can use their own namespace (e.g. wiki:ores_high).

### evidence_status for non-L2

For non-L2 rows, diff is not fetched; use evidence_status = **NA** (or empty). Only for L2 use OK/MISSING/ERROR.

---

**Summary:** Spine and export correct ✅. This file alone is not sufficient to claim “system working correctly”; L0/L1/L2 distribution, escalation reason, and warmup must be validated for **calibration**.
