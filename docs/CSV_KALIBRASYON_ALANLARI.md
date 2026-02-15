# CSV sütunları ve kalibrasyon kullanımı

Bu doküman, `decision_packet_to_csv_row` (audit_spec) ile üretilen CSV’deki her sütunun **L0/L1/L2 kararı ve eşik kalibrasyonunda** kullanılıp kullanılmadığını özetler. Referans: `core/soft_override.py`, `core/confidence.py`, `core/uncertainty.py`, `core/fail_safe.py`, `mdm_engine/engine.py`.

---

## Kalibrasyonda kullanılan sinyaller (kısa)

Level kararı şunlara bağlı:

- **Fail-safe:** `worst_J`, `worst_H` vs `J_CRITICAL`, `H_CRITICAL`
- **Escalation (H_high, H_critical, confidence_low, constraint_violation, as_norm_low, divergence_high):**
  - `effective_confidence` (= confidence_used; internal veya external × input_quality) vs `CONFIDENCE_ESCALATION_FORCE`, `CONFIDENCE_LOW_ESCALATION_LEVEL`
  - `constraint_margin` (seçilen aksiyonun J,H,C vs J_MIN, H_MAX, C_MIN, C_MAX)
  - **Seçilen aksiyonun H’i** (`mdm_H`) vs `H_MAX` (H_high), `H_CRITICAL` (H_critical)
  - `as_norm` vs `AS_SOFT_THRESHOLD`
  - `divergence` vs `DIVERGENCE_HARD_THRESHOLD`
- **Temporal drift:** `cus` geçmişi → `cus_mean`, `delta_cus` vs `CUS_MEAN_THRESHOLD`, `DELTA_CUS_THRESHOLD`, `DRIFT_MIN_HISTORY`

Tüm eşikler profil üzerinden `cfg_*` olarak CSV’de snapshot’lanır.

---

## Tablo: CSV sütunu → Kalibrasyonda kullanım

| CSV sütunu | Kalibrasyonda kullanım | Açıklama |
|------------|-------------------------|----------|
| **time** | Hayır | Audit / zaman damgası |
| **latency_ms** | Hayır | Toplam gecikme (ops) |
| **run_id** | Hayır | Çalıştırma kimliği |
| **title** | Hayır | Bağlam (örn. sayfa) |
| **user** | Hayır | Bağlam (kullanıcı) |
| **revid** | Hayır | Bağlam (revizyon) |
| **comment** | Hayır | Bağlam (özet) |
| **ores_decision** | Hayır | ORES çıktısı; mismatch için kullanılır, level formülüne girmez |
| **ores_p_damaging** | Dolaylı | Adapter’da external_confidence/risk kaynağı olabilir; MDM level formülünde doğrudan yok |
| **ores_p_goodfaith** | Hayır | ORES; level kararına girmiyor |
| **ores_threshold** | Hayır | ORES eşiği |
| **ores_model** | Hayır | Teşhis |
| **ores_http_status** | Hayır | Ops |
| **ores_latency_ms** | Hayır | Ops |
| **ores_error** | Hayır | Ops |
| **ores_cache_hit** | Hayır | Ops |
| **ores_retry_count** | Hayır | Ops |
| **ores_backoff_ms** | Hayır | Ops |
| **schema_version** | Hayır | Meta |
| **adapter_version** | Hayır | Meta |
| **source_event_id** | Hayır | Meta |
| **config_profile** | Hayır | Profil adı (cfg_* snapshot anlamlı) |
| **cfg_AS_SOFT_THRESHOLD** | Evet | as_norm_low eşiği |
| **cfg_CUS_MEAN_THRESHOLD** | Evet | Drift: cus_mean eşiği |
| **cfg_DRIFT_MIN_HISTORY** | Evet | Drift warmup süresi |
| **cfg_CONFIDENCE_ESCALATION_FORCE** | Evet | confidence_low eşiği |
| **cfg_H_CRIT** | Evet | H_critical (L2) eşiği |
| **cfg_H_MAX** | Evet | H_high (L1) eşiği |
| **cfg_J_MIN** | Evet | Constraint margin (J) + fail_safe ile ilişkili |
| **cfg_J_CRIT** | Evet | Fail-safe J eşiği |
| **git_commit** | Hayır | Meta |
| **host** | Hayır | Meta |
| **session_id** | Hayır | Meta |
| **mdm_latency_ms** | Hayır | Performans |
| **sse_wait_ms** | Hayır | Performans |
| **mdm_input_risk** | Dolaylı | Adapter’da risk/confidence kaynağı; level formülünde explicit değil |
| **mdm_input_state_hash** | Hayır | Replay / determinism |
| **final_action** | Hayır | Çıktı (APPLY / APPLY_CLAMPED / HOLD_REVIEW) |
| **final_action_reason** | Hayır | Çıktı (policy-facing neden) |
| **mismatch** | Hayır | ORES vs MDM karşılaştırma sonucu |
| **mdm_level** | Hayır | Çıktı (L0/L1/L2) |
| **mdm_reason** | Hayır | final_action_reason ile aynı |
| **selection_reason** | Hayır | Teşhis (action_selector gerekçesi) |
| **fail_safe_reason** | Hayır | Teşhis (fail_safe trigger) |
| **escalation_driver** | Hayır | Çıktı (birincil driver) |
| **mdm_human_escalation** | Hayır | Çıktı |
| **drift_driver** | Hayır | Teşhis (warmup/mean/delta/none) |
| **drift_history_len** | Evet | Drift penceresi (kalibrasyonla birlikte yorumlanır) |
| **drift_min_history** | Evet | cfg_DRIFT_MIN_HISTORY ile aynı (snapshot) |
| **clamp_applied** | Hayır | Çıktı |
| **clamp_types** | Hayır | Çıktı |
| **clamp_count** | Hayır | Çıktı |
| **clamp_strength** | Hayır | Çıktı |
| **mdm_soft_clamp** | Hayır | Çıktı |
| **mdm_confidence** | Evet | Internal confidence; effective_confidence’ın kaynağı olabilir |
| **mdm_confidence_internal** | Evet | Aynı (teşhis ayrımı) |
| **mdm_confidence_external** | Evet | Adapter’dan gelen confidence (external_confidence) |
| **mdm_confidence_used** | Evet | Level kararında kullanılan effective_confidence |
| **mdm_confidence_source** | Hayır | Teşhis (internal vs external) |
| **mdm_constraint_margin** | Evet | constraint_violation ve confidence formülü |
| **mdm_cus** | Evet | Drift girdisi (CUS geçmişi) |
| **mdm_cus_mean** | Evet | Drift: cus_mean vs CUS_MEAN_THRESHOLD |
| **mdm_divergence** | Evet | divergence_high vs DIVERGENCE_HARD_THRESHOLD |
| **mdm_delta_cus** | Evet | Drift: delta_cus vs DELTA_CUS_THRESHOLD |
| **mdm_preemptive_escalation** | Hayır | Drift çıktısı (teşhis) |
| **mdm_delta_confidence** | Hayır | Self-regulation teşhis |
| **mdm_action_severity** | Hayır | Seçilen aksiyon (çıktı); eşik kararına girmiyor |
| **mdm_action_compassion** | Hayır | Aynı |
| **mdm_action_intervention** | Hayır | Aynı |
| **mdm_action_delay** | Hayır | Aynı |
| **mdm_J** | Evet | Constraint margin (seçilen aksiyon J) |
| **mdm_H** | Evet | H_high / H_critical (seçilen aksiyon H) |
| **mdm_worst_H** | Evet | Fail-safe tetiklemesi (H_CRITICAL) |
| **mdm_worst_J** | Evet | Fail-safe tetiklemesi (J_CRITICAL) |
| **unc_hi** | Dolaylı | CUS bileşeni; doğrudan eşik yok |
| **unc_de** | Dolaylı | CUS/divergence girdisi; doğrudan eşik yok |
| **unc_de_norm** | Dolaylı | CUS + divergence hesapları |
| **unc_as_norm** | Evet | as_norm_low vs AS_SOFT_THRESHOLD |
| **unc_cus** | Evet | mdm_cus ile aynı (drift girdisi) |
| **unc_divergence** | Evet | mdm_divergence ile aynı |
| **unc_n_candidates** | Hayır | Teşhis |
| **unc_score_best** | Hayır | Teşhis |
| **unc_score_second** | Hayır | Teşhis |
| **unc_action_spread_raw** | Hayır | Teşhis (as_norm ham girdisi) |
| **unc_as_norm_missing** | Hayır | Teşhis |
| **mdm_input_quality** | Evet | effective_confidence çarpanı |
| **mdm_evidence_consistency** | Hayır | Kalite teşhisi; level formülünde yok |
| **mdm_frontier_size** | Hayır | Pareto teşhis |
| **mdm_pareto_gap** | Hayır | Pareto teşhis |
| **mdm_driver_history_len** | Hayır | Teşhis (driver histogram) |
| **mdm_drift_driver_alarm** | Hayır | Teşhis (ani constraint_violation artışı) |
| **mdm_missing_fields** | Hayır | Teşhis |
| **mdm_valid_candidate_count** | Hayır | Teşhis |
| **mdm_invalid_reason_counts** | Hayır | Teşhis |
| **mdm_state_hash** | Hayır | Replay / determinism |
| **mdm_config_hash** | Hayır | Replay / determinism |
| **drift_applied** | Hayır | Çıktı (drift L1 tetikledi mi) |
| **evidence_status** | Hayır | İnceleme workflow |
| **diff_available** | Hayır | İnceleme workflow |
| **diff_length** | Hayır | İnceleme workflow |
| **diff_excerpt** | Hayır | İnceleme workflow |
| **diff_fetch_latency_ms** | Hayır | İnceleme workflow |
| **review_status** | Hayır | İnceleme sonucu |
| **review_decision** | Hayır | İnceleme sonucu |
| **review_category** | Hayır | İnceleme sonucu |
| **review_note** | Hayır | İnceleme sonucu |

---

## Kalibrasyonda kullanılmayan değerler (özet)

Aşağıdaki CSV sütunları **L0/L1/L2 veya eşik kararına hiç girmiyor**; sadece audit, teşhis, performans veya inceleme için:

- **Audit/bağlam:** time, latency_ms, run_id, title, user, revid, comment  
- **Meta:** schema_version, adapter_version, source_event_id, config_profile, git_commit, host, session_id  
- **ORES (mismatch dışında):** ores_decision, ores_p_goodfaith, ores_threshold, ores_model, ores_http_status, ores_latency_ms, ores_error, ores_cache_hit, ores_retry_count, ores_backoff_ms  
- **Performans:** mdm_latency_ms, sse_wait_ms  
- **Replay/identity:** mdm_input_state_hash, mdm_state_hash, mdm_config_hash  
- **Çıktı:** final_action, final_action_reason, mismatch, mdm_level, mdm_reason, selection_reason, fail_safe_reason, escalation_driver, mdm_human_escalation, clamp_applied, clamp_types, clamp_count, clamp_strength, mdm_soft_clamp, drift_applied  
- **Teşhis:** mdm_confidence_source, drift_driver, mdm_preemptive_escalation, mdm_delta_confidence, mdm_action_* (4 sütun), unc_n_candidates, unc_score_best, unc_score_second, unc_action_spread_raw, unc_as_norm_missing, mdm_evidence_consistency, mdm_frontier_size, mdm_pareto_gap, mdm_driver_history_len, mdm_drift_driver_alarm, mdm_missing_fields, mdm_valid_candidate_count, mdm_invalid_reason_counts  
- **İnceleme:** evidence_status, diff_available, diff_length, diff_excerpt, diff_fetch_latency_ms, review_status, review_decision, review_category, review_note  

Kalibrasyon için **gerçekten kritik** olanlar: **cfg_***, **mdm_confidence_used**, **mdm_constraint_margin**, **mdm_H**, **mdm_J**, **mdm_worst_H**, **mdm_worst_J**, **unc_as_norm**, **unc_divergence**, **mdm_cus** / **unc_cus**, **mdm_cus_mean**, **mdm_delta_cus**, **mdm_input_quality**, **drift_history_len** / **drift_min_history**.  
(ores_p_damaging, mdm_input_risk adapter tarafında external_confidence’a dönüşüyorsa dolaylı etkisi olur; MDM level formülünde doğrudan eşik olarak geçmez.)
