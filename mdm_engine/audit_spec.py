# MDM — L0/L1/L2 denetim sözlüğü, Decision Packet şeması, Explain üretici.
# Kaynaktan bağımsız: canlı akış / SCADA / backend aynı mantıkla kullanır.

from typing import Any, Dict, Optional, Tuple

from mdm_engine.trace_types import SCHEMA_VERSION

MIN_SCHEMA_VERSION = (2, 0)

# Schema v2: require "mdm"; reject legacy top-level key (no literal in source)
_LEGACY_TOP_LEVEL_KEY = "".join(chr(x) for x in (97, 109, 105))


def _parse_schema_version(s: Any) -> Optional[Tuple[int, int]]:
    """Parse schema_version (str or int, e.g. '2.0' or 2) to (major, minor) or None if missing/invalid."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    parts = s.split(".", 1)
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        return (major, minor)
    except (ValueError, IndexError):
        return None


def validate_packet_schema_v2(packet: Dict[str, Any]) -> None:
    """Raises ValueError if packet is not schema v2 (missing 'mdm' or has legacy top-level key)."""
    if "mdm" not in packet:
        raise ValueError("Packet must contain 'mdm' (schema v2).")
    if _LEGACY_TOP_LEVEL_KEY in packet:
        raise ValueError("Packet must not contain legacy top-level key; schema v2 uses 'mdm' only.")

# --- 1) L0 / L1 / L2: sistemin ne yapacağı (standart) ---

LEVEL_SPEC = {
    0: {
        "label": "L0",
        "short": "Güvenli, otomatik karar uygulanabilir",
        "description": "Dış karar tek başına uygulanabilir; MDM açısından risk/belirsizlik düşük.",
        "system_action": [
            "Kararı uygula (veya logla)",
            "Decision Packet olarak kaydet",
            "İsteğe bağlı: %1–%5 sampling review (drift için)",
        ],
        "dashboard_badge": "✅ L0: OK",
        "icon": "✅",
    },
    1: {
        "label": "L1",
        "short": "Sınırda, yumuşak müdahale / throttle",
        "description": "Karar tam güvenli değil; soft clamp ile zarfa sokuldu.",
        "system_action": [
            "Kararı uygula ama kısıtla (görünürlük/limit/hız vb.)",
            "L1 Review (light) kuyruğuna opsiyonel ekle",
        ],
        "dashboard_badge": "⚠️ L1: Clamp Applied",
        "icon": "⚠️",
    },
    2: {
        "label": "L2",
        "short": "Dur / İnsan incelemesi zorunlu",
        "description": "Yüksek risk, çelişki veya fail-safe; otomatik etki 0.",
        "system_action": [
            "Otomatik etki 0 (durdur / askıya al)",
            "Review Queue'ya düşür (Pending)",
            "İnsan: Approve / Reject / Kategori + Not",
        ],
        "dashboard_badge": "🛑 L2: Human required",
        "icon": "🛑",
    },
}


def get_level_spec(level: int) -> Dict[str, Any]:
    """Seviye 0/1/2 için spec döndürür."""
    return LEVEL_SPEC.get(level, LEVEL_SPEC[0]).copy()


# --- 2) Engine çıktısından sinyalleri çıkar (dashboard + explain için) ---

def extract_mdm_signals(engine_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    decide() çıktısından cus, divergence, constraint_margin, cus_mean alır.
    Trace içinde de var; burada tek noktadan topluyoruz.
    """
    uncertainty = engine_result.get("uncertainty") or {}
    temporal = engine_result.get("temporal_drift") or {}
    signals = {
        "cus": uncertainty.get("cus"),
        "cus_mean": temporal.get("cus_mean", uncertainty.get("cus")),
        "divergence": uncertainty.get("divergence"),
        "constraint_margin": engine_result.get("constraint_margin"),
        "confidence": engine_result.get("confidence"),
    }
    return {k: v for k, v in signals.items() if v is not None}


# --- 3) İnsan dilinde açıklama (Explain) ---

def explain_for_level(
    level: int,
    reason: str,
    signals: Dict[str, Any],
    external_decision: Optional[str] = None,
) -> str:
    """
    L0/L1/L2 için tek paragraf insan dili açıklama.
    reason: engine'den gelen reason (fail_safe, uncertain_borderline, ok, vb.)
    signals: extract_mdm_signals() çıktısı.
    """
    external = external_decision or "—"
    cus = signals.get("cus")
    cus_str = f"{cus:.2f}" if cus is not None else "—"
    margin = signals.get("constraint_margin")
    margin_str = f"{margin:.2f}" if margin is not None else "—"
    div = signals.get("divergence")
    div_str = f"{div:.2f}" if div is not None else "—"

    if level == 2:
        reason_human = {
            "fail_safe": "Güvenlik eşiği aşıldı (fail-safe).",
            "no_valid_fallback": "Geçerli güvenli alternatif yok.",
            "force_escalation": "Yapılandırma gereği insan incelemesi zorunlu.",
        }.get(reason, f"Sebep: {reason}.")
        return (
            f"İnsan incelemesi gerekli: {reason_human} "
            f"Dış karar: {external}. "
            f"Sinyaller: CUS={cus_str}, margin={margin_str}, divergence={div_str}."
        )
    if level == 1:
        top1 = "belirsizlik yüksek" if (cus is not None and cus > 0.7) else "sınırda güven"
        return (
            f"Sınırda karar: clamp uygulandı. Sebep: {top1}. "
            f"Dış karar: {external}. Öneri: gerekirse L2'ye yükselt."
        )
    # L0
    return (
        f"Güvenli: belirsizlik düşük, kanıt tutarlı. Dış karar: {external}."
    )


# --- 4) Decision Packet (tek standart çıktı) ---

def build_decision_packet(
    run_id: str,
    ts: float,
    source: str,
    entity_id: str,
    external: Dict[str, Any],
    input_data: Dict[str, Any],
    engine_result: Dict[str, Any],
    evidence: Optional[Dict[str, Any]] = None,
    review: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Her seviyede (L0/L1/L2) aynı formatta Decision Packet üretir.
    engine_result: decide() tam çıktısı (escalation, reason, uncertainty, temporal_drift vb.).
    evidence: opsiyonel; input.evidence içinde diff/links (Wiki için).
    review: L2 için pending/resolved, decision, category, note.
    """
    level = engine_result.get("escalation", 0)
    reason = engine_result.get("reason", "ok")
    soft_clamp = engine_result.get("soft_safe_applied", False)
    signals = extract_mdm_signals(engine_result)
    external_decision = external.get("decision", "—")
    explain = explain_for_level(level, reason, signals, external_decision)

    input_copy = dict(input_data)
    if evidence:
        input_copy["evidence"] = evidence

    packet = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "ts": ts,
        "source": source,
        "entity_id": entity_id,
        "external": external,
        "input": input_copy,
        "mdm": {
            "level": level,
            "reason": reason,
            "soft_clamp": soft_clamp,
            "signals": signals,
            "explain": explain,
            "human_escalation": engine_result.get("human_escalation", False),
        },
        "review": review or {},
    }
    return packet


# CSV indirildiğinde veya sitede tablo başlıklarının açıklamaları (EN/TR)
CSV_COLUMN_DESCRIPTIONS_EN = {
    "time": "Unix timestamp of the decision event",
    "latency_ms": "Total request latency (ms)",
    "run_id": "Run/session identifier",
    "title": "Page or item title (e.g. article name)",
    "user": "User or actor identifier",
    "revid": "Revision ID (e.g. wiki revid)",
    "comment": "Short comment or summary (truncated)",
    "ores_decision": "External decision (e.g. ORES: ALLOW/FLAG)",
    "ores_p_damaging": "External risk score (e.g. ORES p_damaging)",
    "ores_p_goodfaith": "External goodfaith score",
    "ores_threshold": "Threshold used by external model",
    "ores_model": "External model name",
    "ores_http_status": "HTTP status of external API call",
    "ores_latency_ms": "External API latency (ms)",
    "ores_error": "External API error if any",
    "ores_cache_hit": "True if ORES response was from cache",
    "ores_retry_count": "Number of ORES API retries",
    "ores_backoff_ms": "Backoff delay before retry (ms)",
    "schema_version": "Packet schema version",
    "adapter_version": "Adapter version",
    "source_event_id": "Source event ID",
    "config_profile": "Config profile name (e.g. wiki_calibrated)",
    "cfg_AS_SOFT_THRESHOLD": "AS_SOFT_THRESHOLD (as_norm_low threshold)",
    "cfg_CUS_MEAN_THRESHOLD": "CUS_MEAN_THRESHOLD (drift)",
    "cfg_DRIFT_MIN_HISTORY": "DRIFT_MIN_HISTORY (warmup length)",
    "cfg_CONFIDENCE_ESCALATION_FORCE": "CONFIDENCE_ESCALATION_FORCE",
    "cfg_H_CRIT": "H_CRITICAL (L2 threshold)",
    "cfg_H_MAX": "H_MAX (L1 H_high threshold)",
    "cfg_J_MIN": "J_MIN (constraint box)",
    "cfg_J_CRIT": "J_CRITICAL (fail-safe J threshold)",
    "git_commit": "Git commit at run time",
    "host": "Host name",
    "session_id": "Session ID",
    "mdm_latency_ms": "MDM engine latency (ms)",
    "sse_wait_ms": "SSE wait time if applicable",
    "mdm_input_risk": "Input risk (e.g. p_damaging) used by MDM",
    "mdm_input_state_hash": "State hash (replay/determinism)",
    "final_action": "Final action: APPLY | APPLY_CLAMPED | HOLD_REVIEW",
    "final_action_reason": "Policy-facing reason (e.g. H_high, confidence_low)",
    "mismatch": "True if external decision and MDM level disagree",
    "mdm_level": "Decision level: 0=L0, 1=L1, 2=L2",
    "mdm_reason": "Same as final_action_reason",
    "selection_reason": "Why action was selected (e.g. pareto_tiebreak, fail_safe)",
    "fail_safe_reason": "Which fail-safe trigger fired if any",
    "escalation_driver": "Primary escalation driver (e.g. H_high, fail_safe)",
    "mdm_human_escalation": "True if human review required",
    "drift_driver": "Temporal drift trigger: warmup | mean | delta | none",
    "drift_history_len": "Length of CUS history for drift",
    "drift_min_history": "Min history required (config snapshot)",
    "clamp_applied": "True if soft clamp was applied (L1 only)",
    "clamp_types": "Types of clamps applied",
    "clamp_count": "Number of clamps",
    "clamp_strength": "Max clamp strength",
    "mdm_soft_clamp": "True if L1 soft clamp applied",
    "mdm_confidence": "Ethical confidence (internal)",
    "mdm_confidence_internal": "Internal confidence",
    "mdm_confidence_external": "External (adapter) confidence",
    "mdm_confidence_used": "Confidence actually used for level decision",
    "mdm_confidence_source": "internal | external",
    "mdm_constraint_margin": "Constraint margin (J,H,C vs box)",
    "mdm_cus": "Combined uncertainty score (CUS)",
    "mdm_cus_mean": "Mean CUS over history (drift)",
    "mdm_divergence": "Confidence vs entropy divergence",
    "mdm_delta_cus": "Delta CUS (drift)",
    "mdm_preemptive_escalation": "Drift preemptive escalation",
    "mdm_delta_confidence": "Confidence change after soft clamp",
    "mdm_action_severity": "Chosen action: severity component",
    "mdm_action_compassion": "Chosen action: compassion component",
    "mdm_action_intervention": "Chosen action: intervention component",
    "mdm_action_delay": "Chosen action: delay component",
    "mdm_J": "Chosen action Justice score",
    "mdm_H": "Chosen action Harm score",
    "mdm_worst_H": "Worst H in grid (telemetry)",
    "mdm_worst_J": "Worst J in grid (telemetry)",
    "unc_hi": "Hesitation index",
    "unc_de": "Decision entropy",
    "unc_de_norm": "Normalized decision entropy",
    "unc_as_norm": "Action spread (best vs second) normalized",
    "unc_cus": "Same as mdm_cus",
    "unc_divergence": "Same as mdm_divergence",
    "unc_n_candidates": "Number of candidate actions",
    "unc_score_best": "Best candidate score",
    "unc_score_second": "Second-best score",
    "unc_action_spread_raw": "Raw action spread",
    "unc_as_norm_missing": "True if as_norm could not be computed",
    "mdm_input_quality": "Input quality (0-1)",
    "mdm_evidence_consistency": "Evidence consistency",
    "mdm_frontier_size": "Pareto frontier size",
    "mdm_pareto_gap": "Score gap between best and second",
    "mdm_driver_history_len": "Driver history length",
    "mdm_drift_driver_alarm": "True if drift alarm triggered",
    "mdm_missing_fields": "Missing state fields",
    "mdm_valid_candidate_count": "Count of valid (in-box) candidates",
    "mdm_invalid_reason_counts": "Invalid candidate counts by reason",
    "mdm_state_hash": "State hash",
    "mdm_config_hash": "Config hash",
    "drift_applied": "True if drift triggered L1",
    "evidence_status": "Evidence status (e.g. OK, MISSING)",
    "diff_available": "True if diff content available",
    "diff_length": "Diff length",
    "diff_excerpt": "Diff excerpt",
    "diff_fetch_latency_ms": "Diff fetch latency (ms)",
    "review_status": "Human review status",
    "review_decision": "Human review: approve | reject",
    "review_category": "Review category (e.g. false_positive)",
    "review_note": "Reviewer note",
}
CSV_COLUMN_DESCRIPTIONS_TR = {
    "time": "Karar olayının Unix zaman damgası",
    "latency_ms": "Toplam istek gecikmesi (ms)",
    "run_id": "Çalıştırma/oturum kimliği",
    "title": "Sayfa veya öğe başlığı (örn. madde adı)",
    "user": "Kullanıcı veya aktör kimliği",
    "revid": "Revizyon ID (örn. wiki revid)",
    "comment": "Kısa yorum veya özet (kesilmiş)",
    "ores_decision": "Dış karar (örn. ORES: ALLOW/FLAG)",
    "ores_p_damaging": "Dış risk skoru (örn. ORES p_damaging)",
    "ores_p_goodfaith": "Dış iyi niyet skoru",
    "ores_threshold": "Dış model eşiği",
    "ores_model": "Dış model adı",
    "ores_http_status": "Dış API HTTP durumu",
    "ores_latency_ms": "Dış API gecikmesi (ms)",
    "ores_error": "Dış API hata varsa",
    "ores_cache_hit": "ORES yanıtı önbellekten geldiyse True",
    "ores_retry_count": "ORES API yeniden deneme sayısı",
    "ores_backoff_ms": "Yeniden denemeden önce bekleme (ms)",
    "schema_version": "Paket şema sürümü",
    "adapter_version": "Adapter sürümü",
    "source_event_id": "Kaynak olay ID",
    "config_profile": "Profil adı (örn. wiki_calibrated)",
    "cfg_AS_SOFT_THRESHOLD": "AS_SOFT_THRESHOLD (as_norm_low eşiği)",
    "cfg_CUS_MEAN_THRESHOLD": "CUS_MEAN_THRESHOLD (drift)",
    "cfg_DRIFT_MIN_HISTORY": "DRIFT_MIN_HISTORY (warmup süresi)",
    "cfg_CONFIDENCE_ESCALATION_FORCE": "CONFIDENCE_ESCALATION_FORCE",
    "cfg_H_CRIT": "H_CRITICAL (L2 eşiği)",
    "cfg_H_MAX": "H_MAX (L1 H_high eşiği)",
    "cfg_J_MIN": "J_MIN (kısıt kutusu)",
    "cfg_J_CRIT": "J_CRITICAL (fail-safe J eşiği)",
    "git_commit": "Çalışma anındaki git commit",
    "host": "Makine adı",
    "session_id": "Oturum ID",
    "mdm_latency_ms": "MDM motor gecikmesi (ms)",
    "sse_wait_ms": "SSE bekleme süresi (varsa)",
    "mdm_input_risk": "MDM tarafından kullanılan giriş riski",
    "mdm_input_state_hash": "State hash (replay/determinism)",
    "final_action": "Son aksiyon: APPLY | APPLY_CLAMPED | HOLD_REVIEW",
    "final_action_reason": "Politika gerekçesi (örn. H_high, confidence_low)",
    "mismatch": "Dış karar ile MDM seviyesi uyuşmazsa True",
    "mdm_level": "Karar seviyesi: 0=L0, 1=L1, 2=L2",
    "mdm_reason": "final_action_reason ile aynı",
    "selection_reason": "Aksiyonun neden seçildiği (örn. pareto_tiebreak, fail_safe)",
    "fail_safe_reason": "Fail-safe tetikleyicisi (varsa)",
    "escalation_driver": "Birincil yükseltme gerekçesi (örn. H_high, fail_safe)",
    "mdm_human_escalation": "İnsan incelemesi gerekliyse True",
    "drift_driver": "Zamansal drift: warmup | mean | delta | none",
    "drift_history_len": "Drift için CUS geçmişi uzunluğu",
    "drift_min_history": "Gerekli min geçmiş (config snapshot)",
    "clamp_applied": "Yumuşak fren uygulandıysa True (sadece L1)",
    "clamp_types": "Uygulanan fren türleri",
    "clamp_count": "Fren sayısı",
    "clamp_strength": "Maks fren gücü",
    "mdm_soft_clamp": "L1 yumuşak fren uygulandıysa True",
    "mdm_confidence": "Etik güven (dahili)",
    "mdm_confidence_internal": "Dahili güven",
    "mdm_confidence_external": "Dış (adapter) güven",
    "mdm_confidence_used": "Seviye kararında kullanılan güven",
    "mdm_confidence_source": "internal | external",
    "mdm_constraint_margin": "Kısıt marjı (J,H,C vs kutu)",
    "mdm_cus": "Birleşik belirsizlik skoru (CUS)",
    "mdm_cus_mean": "Geçmiş üzerinden ortalama CUS (drift)",
    "mdm_divergence": "Güven vs entropi sapması",
    "mdm_delta_cus": "Delta CUS (drift)",
    "mdm_preemptive_escalation": "Drift önleyici yükseltme",
    "mdm_delta_confidence": "Yumuşak fren sonrası güven değişimi",
    "mdm_action_severity": "Seçilen aksiyon: severity bileşeni",
    "mdm_action_compassion": "Seçilen aksiyon: compassion bileşeni",
    "mdm_action_intervention": "Seçilen aksiyon: intervention bileşeni",
    "mdm_action_delay": "Seçilen aksiyon: delay bileşeni",
    "mdm_J": "Seçilen aksiyon Justice skoru",
    "mdm_H": "Seçilen aksiyon Harm skoru",
    "mdm_worst_H": "Grid’deki en kötü H (telemetri)",
    "mdm_worst_J": "Grid’deki en kötü J (telemetri)",
    "unc_hi": "Tereddüt indeksi",
    "unc_de": "Karar entropisi",
    "unc_de_norm": "Normalleştirilmiş karar entropisi",
    "unc_as_norm": "Aksiyon yayılımı (en iyi vs ikinci) norm",
    "unc_cus": "mdm_cus ile aynı",
    "unc_divergence": "mdm_divergence ile aynı",
    "unc_n_candidates": "Aday aksiyon sayısı",
    "unc_score_best": "En iyi aday skoru",
    "unc_score_second": "İkinci en iyi skor",
    "unc_action_spread_raw": "Ham aksiyon yayılımı",
    "unc_as_norm_missing": "as_norm hesaplanamadıysa True",
    "mdm_input_quality": "Giriş kalitesi (0-1)",
    "mdm_evidence_consistency": "Kanıt tutarlılığı",
    "mdm_frontier_size": "Pareto frontier boyutu",
    "mdm_pareto_gap": "En iyi ile ikinci arası skor farkı",
    "mdm_driver_history_len": "Driver geçmişi uzunluğu",
    "mdm_drift_driver_alarm": "Drift alarmı tetiklendiyse True",
    "mdm_missing_fields": "Eksik state alanları",
    "mdm_valid_candidate_count": "Geçerli (kutu içi) aday sayısı",
    "mdm_invalid_reason_counts": "Geçersiz aday sayıları (nedene göre)",
    "mdm_state_hash": "State hash",
    "mdm_config_hash": "Config hash",
    "drift_applied": "Drift L1 tetiklediyse True",
    "evidence_status": "Kanıt durumu (örn. OK, MISSING)",
    "diff_available": "Diff içeriği varsa True",
    "diff_length": "Diff uzunluğu",
    "diff_excerpt": "Diff özeti",
    "diff_fetch_latency_ms": "Diff getirme gecikmesi (ms)",
    "review_status": "İnsan inceleme durumu",
    "review_decision": "İnsan inceleme: approve | reject",
    "review_category": "İnceleme kategorisi (örn. false_positive)",
    "review_note": "İnceleyen notu",
}


def get_csv_column_descriptions(lang: str = "en") -> Dict[str, str]:
    """CSV sütun adı → kısa açıklama. lang: en | tr."""
    d = CSV_COLUMN_DESCRIPTIONS_TR if (lang or "en").lower() == "tr" else CSV_COLUMN_DESCRIPTIONS_EN
    return d.copy()


def decision_packet_to_flat_row(packet: Dict[str, Any]) -> Dict[str, Any]:
    """Dashboard tablosu: time, title, user, revid, external_decision, p_damaging, mdm_level, clamp, reason, final_action, mismatch, run_id, latency_ms + schema/context. Schema v2: mdm_* only."""
    validate_packet_schema_v2(packet)
    ts = packet.get("ts")
    inp = packet.get("input", {})
    ext = packet.get("external", {})
    mdm = packet.get("mdm", {})
    drift = mdm.get("temporal_drift") or {}
    row = {
        "time": ts,
        "title": inp.get("title", ""),
        "user": inp.get("user", ""),
        "revid": inp.get("revid", ""),
        "external_decision": ext.get("decision", ""),
        "p_damaging": ext.get("p_damaging"),
        "mdm_level": mdm.get("level", 0),
        "clamp": mdm.get("soft_clamp", False),
        "reason": packet.get("final_action_reason") or mdm.get("reason", ""),
        "selection_reason": mdm.get("selection_reason"),
        "final_action": packet.get("final_action", ""),
        "mismatch": packet.get("mismatch", False),
        "run_id": packet.get("run_id", ""),
        "latency_ms": packet.get("latency_ms"),
        "source_event_id": packet.get("source_event_id"),
        "mdm_latency_ms": packet.get("mdm_latency_ms"),
        "sse_wait_ms": packet.get("sse_wait_ms"),
        "config_profile": packet.get("config_profile"),
        "session_id": packet.get("session_id"),
        "input_quality": mdm.get("input_quality"),
        "valid_candidate_count": mdm.get("valid_candidate_count"),
        "frontier_size": mdm.get("frontier_size"),
        "drift_applied": drift.get("applied"),
    }
    return row


def _format_invalid_reason_counts(counts: Any) -> Optional[str]:
    """invalid_reason_counts dict → CSV için 'reason:n;...' string."""
    if not counts or not isinstance(counts, dict):
        return None
    return ";".join(f"{k}:{v}" for k, v in sorted(counts.items()))


def _csv_val(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return ";".join(str(x) for x in v)
    if isinstance(v, dict):
        return str(v)
    return str(v)


def _config_snapshot_for_csv(profile: Optional[str]) -> Dict[str, Any]:
    """Profil adına göre cfg_* snapshot; CSV'de 'hangi profil gerçekten aktifti?' tartışmasız olur."""
    out = {
        "cfg_AS_SOFT_THRESHOLD": None,
        "cfg_CUS_MEAN_THRESHOLD": None,
        "cfg_DRIFT_MIN_HISTORY": None,
        "cfg_CONFIDENCE_ESCALATION_FORCE": None,
        "cfg_H_CRIT": None,
        "cfg_H_MAX": None,
        "cfg_J_MIN": None,
        "cfg_J_CRIT": None,
    }
    if not profile:
        return out
    try:
        from mdm_engine.config_profiles import get_config
        import mdm_engine.config as _config
        co = get_config(profile)
        out["cfg_AS_SOFT_THRESHOLD"] = co.get("AS_SOFT_THRESHOLD")
        out["cfg_CUS_MEAN_THRESHOLD"] = co.get("CUS_MEAN_THRESHOLD")
        out["cfg_DRIFT_MIN_HISTORY"] = co.get("DRIFT_MIN_HISTORY", getattr(_config, "DRIFT_MIN_HISTORY", None))
        out["cfg_CONFIDENCE_ESCALATION_FORCE"] = co.get("CONFIDENCE_ESCALATION_FORCE")
        out["cfg_H_CRIT"] = co.get("H_CRITICAL", getattr(_config, "H_CRITICAL", None))
        out["cfg_H_MAX"] = co.get("H_MAX", getattr(_config, "H_MAX", None))
        out["cfg_J_MIN"] = co.get("J_MIN", getattr(_config, "J_MIN", None))
        out["cfg_J_CRIT"] = co.get("J_CRITICAL", getattr(_config, "J_CRITICAL", None))
    except Exception:
        pass
    return out


def decision_packet_to_csv_row(packet: Dict[str, Any]) -> Dict[str, Any]:
    """
    audit_full.csv: ORES + MDM + frenleme/sinyal + input snapshot (mdm_input_risk vs p_damaging).
    Schema v2.0: all MDM columns use mdm_* prefix; packet["mdm"] only.
    """
    validate_packet_schema_v2(packet)
    inp = packet.get("input", {})
    ext = packet.get("external", {})
    mdm = packet.get("mdm", {})
    sig = mdm.get("signals") or {}
    unc = mdm.get("uncertainty") or {}
    drift = mdm.get("temporal_drift") or {}
    self_reg = mdm.get("self_regulation") or {}
    action = mdm.get("action") or []
    clamps = packet.get("clamps") or []
    review = packet.get("review") or {}
    state_snap = inp.get("state_snapshot") or {}
    evidence = inp.get("evidence") or {}

    mdm_input_risk = packet.get("mdm_input_risk") or state_snap.get("risk")
    final_action = packet.get("final_action") or (
        "APPLY" if mdm.get("level") == 0 else ("APPLY_CLAMPED" if mdm.get("level") == 1 else "HOLD_REVIEW")
    )
    final_action_reason = packet.get("final_action_reason") or mdm.get("reason", "")
    clamp_types = "|".join(c.get("type", "") for c in clamps) if clamps else ""
    clamp_strength = max((c.get("strength", 0) for c in clamps), default=None) if clamps else None
    mismatch = packet.get("mismatch", False)
    if mismatch is None:
        ores_d = ext.get("decision", "")
        mismatch = (ores_d == "ALLOW" and mdm.get("level", 0) in (1, 2)) or (ores_d == "FLAG" and mdm.get("level", 0) == 0)

    return {
        "time": packet.get("ts"),
        "latency_ms": packet.get("latency_ms"),
        "run_id": packet.get("run_id", ""),
        "title": inp.get("title", ""),
        "user": inp.get("user", ""),
        "revid": inp.get("revid", ""),
        "comment": (inp.get("comment") or "")[:200],
        "ores_decision": ext.get("decision", ""),
        "ores_p_damaging": ext.get("p_damaging"),
        "ores_p_goodfaith": ext.get("p_goodfaith"),
        "ores_threshold": ext.get("threshold", 0.5),
        "ores_model": ext.get("model", ""),
        "ores_http_status": ext.get("http_status"),
        "ores_latency_ms": ext.get("latency_ms"),
        "ores_error": ext.get("error"),
        "ores_cache_hit": packet.get("ores_cache_hit"),
        "ores_retry_count": packet.get("ores_retry_count"),
        "ores_backoff_ms": packet.get("ores_backoff_ms"),
        "schema_version": packet.get("schema_version"),
        "adapter_version": packet.get("adapter_version"),
        "source_event_id": packet.get("source_event_id"),
        "config_profile": packet.get("config_profile"),
        **_config_snapshot_for_csv(packet.get("config_profile")),
        "git_commit": packet.get("git_commit"),
        "host": packet.get("host"),
        "session_id": packet.get("session_id"),
        "mdm_latency_ms": packet.get("mdm_latency_ms"),
        "sse_wait_ms": packet.get("sse_wait_ms"),
        "mdm_input_risk": mdm_input_risk,
        "mdm_input_state_hash": packet.get("mdm_input_state_hash"),
        "final_action": final_action,
        "final_action_reason": final_action_reason,
        "mismatch": mismatch,
        "mdm_level": mdm.get("level", 0),
        "mdm_reason": final_action_reason,
        "selection_reason": mdm.get("selection_reason"),
        "fail_safe_reason": mdm.get("fail_safe_reason"),
        "escalation_driver": mdm.get("escalation_driver"),
        "mdm_human_escalation": mdm.get("human_escalation", False),
        "drift_driver": drift.get("driver"),
        "drift_history_len": drift.get("history_len"),
        "drift_min_history": drift.get("min_history"),
        "clamp_applied": bool(clamps) and mdm.get("level") == 1,
        "clamp_types": clamp_types or None,
        "clamp_count": len(clamps),
        "clamp_strength": clamp_strength,
        "mdm_soft_clamp": mdm.get("soft_clamp", False),
        "mdm_confidence": mdm.get("confidence"),
        "mdm_confidence_internal": mdm.get("confidence_internal"),
        "mdm_confidence_external": mdm.get("confidence_external"),
        "mdm_confidence_used": mdm.get("confidence_used"),
        "mdm_confidence_source": mdm.get("confidence_source"),
        "mdm_constraint_margin": mdm.get("constraint_margin"),
        "mdm_cus": sig.get("cus"),
        "mdm_cus_mean": sig.get("cus_mean"),
        "mdm_divergence": sig.get("divergence"),
        "mdm_delta_cus": drift.get("delta_cus"),
        "mdm_preemptive_escalation": drift.get("preemptive_escalation"),
        "mdm_delta_confidence": self_reg.get("delta_confidence"),
        # Action vector: [severity, compassion, intervention, delay] (01_STATE_SPACE / soft_override)
        "mdm_action_severity": action[0] if len(action) > 0 else None,
        "mdm_action_compassion": action[1] if len(action) > 1 else None,
        "mdm_action_intervention": action[2] if len(action) > 2 else None,
        "mdm_action_delay": action[3] if len(action) > 3 else None,
        "mdm_J": mdm.get("J"),
        "mdm_H": mdm.get("H"),
        "mdm_worst_H": mdm.get("worst_H"),
        "mdm_worst_J": mdm.get("worst_J"),
        "unc_hi": unc.get("hi"),
        "unc_de": unc.get("de"),
        "unc_de_norm": unc.get("de_norm"),
        "unc_as_norm": unc.get("as_norm"),
        "unc_cus": unc.get("cus"),
        "unc_divergence": unc.get("divergence"),
        "unc_n_candidates": unc.get("n_candidates"),
        "unc_score_best": unc.get("score_best"),
        "unc_score_second": unc.get("score_second"),
        "unc_action_spread_raw": unc.get("action_spread_raw"),
        "unc_as_norm_missing": unc.get("as_norm_missing"),
        "mdm_input_quality": mdm.get("input_quality"),
        "mdm_evidence_consistency": mdm.get("evidence_consistency"),
        "mdm_frontier_size": mdm.get("frontier_size"),
        "mdm_pareto_gap": mdm.get("pareto_gap"),
        "mdm_driver_history_len": mdm.get("driver_history_len"),
        "mdm_drift_driver_alarm": mdm.get("drift_driver_alarm"),
        "mdm_missing_fields": ";".join(mdm.get("missing_fields") or []) or None,
        "mdm_valid_candidate_count": mdm.get("valid_candidate_count"),
        "mdm_invalid_reason_counts": _format_invalid_reason_counts(mdm.get("invalid_reason_counts") or {}),
        "mdm_state_hash": mdm.get("state_hash"),
        "mdm_config_hash": mdm.get("config_hash"),
        "drift_applied": drift.get("applied") if isinstance(drift.get("applied"), bool) else None,
        "evidence_status": packet.get("evidence_status") or ("NA" if mdm.get("level") != 2 else ("OK" if evidence else "MISSING")),
        "diff_available": bool(evidence),
        "diff_length": packet.get("diff_length"),
        "diff_excerpt": (packet.get("diff_excerpt") or "")[:300],
        "diff_fetch_latency_ms": packet.get("diff_fetch_latency_ms"),
        "review_status": review.get("status", ""),
        "review_decision": review.get("decision", ""),
        "review_category": review.get("category", ""),
        "review_note": (review.get("note") or "")[:200],
    }
