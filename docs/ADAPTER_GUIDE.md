# How to Add a New Adapter

An **adapter** turns your domain data into **state** and (optionally) **context**, calls the MDM engine, and builds a **decision packet** (schema v2).

## Steps

1. **Build state**  
   Map your domain input to a dict with keys: physical, social, context, risk, compassion, justice, harm_sens, responsibility, empathy. Values in [0,1]. Missing keys are filled with a default (e.g. 0.5) by the state encoder.

2. **Build context (optional)**  
   For confidence/quality: e.g. external_confidence, cus_history. Pass to `decide(state, context=context, profile=...)`.

3. **Call engine**  
   `from mdm_engine import decide`  
   `result = decide(state, context=context, profile="your_profile")`  
   Result contains: action, escalation, reason, confidence, uncertainty, temporal_drift, trace, etc.

4. **Build packet (schema v2)**  
   Use `build_decision_packet` from `mdm_engine.audit_spec`:
   - run_id, ts, source, entity_id, external (dict), input (dict), **engine_result** (the `decide()` output), evidence, review.
   - Packet must have **"mdm"** and must **not** have the legacy top-level key. Use only the keys listed in PACKET_SCHEMA_V2.md.

5. **Export**  
   Append packet as one JSON line to a JSONL file. For CSV, use `decision_packet_to_csv_row(packet)` (all mdm_* columns).

## Example: Wiki adapter

See **tools/live_wiki_audit.py**:

- EventStreams event + ORES response → state (risk = p_damaging, etc.) and context (external_confidence, title, revid).
- `decide(payload["state"], context=payload["context"], profile="wiki_calibrated")` → engine_result.
- `build_decision_packet(..., engine_result=engine_result)` → packet with "mdm" only.
- Optional policy: if ORES says FLAG and MDM says L0, force L2 (human review). Then set packet["final_action"], packet["final_action_reason"], packet["mdm"]["level"] accordingly.
- Write packet to JSONL; CSV export via dashboard or tools.

## Config profile

Create or reuse a profile in **config_profiles/** (e.g. wiki_calibrated.py). Set thresholds (H_MAX, J_MIN, CUS_MEAN_THRESHOLD, etc.) and pass the profile name to `decide(..., profile="name")`. Set **MDM_CONFIG_PROFILE** in the environment if you want that profile as default.
