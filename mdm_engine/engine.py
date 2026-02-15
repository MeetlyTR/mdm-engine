# MDM — Ana karar motoru pipeline (Phase 2 spec §5).
# B.4: Trace raw_state + Replay + regülasyon-grade sertleştirmeler (04_QUALITY_AND_PHASE4_SPEC).

import copy
import hashlib
import json
import math
import os
import random
from typing import Any, Dict, List, Optional, Union

from mdm_engine import config as _config
from mdm_engine.config import DEFAULT_WEIGHTS

# Import from parent core package (relative import)
# Note: core/ is at repo root, not in mdm_engine package
import sys
from pathlib import Path

_core_parent = Path(__file__).resolve().parent.parent.parent / "core"
if str(_core_parent.parent) not in sys.path:
    sys.path.insert(0, str(_core_parent.parent))

from core import (
    encode_state,
    generate_actions,
    refine_actions_around,
    evaluate_moral,
    validate_constraints,
    fail_safe,
    select_action,
    SelectionResult,
    TraceLogger,
    MoralScores,
    compute_confidence,
    compute_uncertainty,
    compute_input_quality,
)
from core.fail_safe import FailSafeResult
from core.state_encoder import STATE_KEYS
from core.soft_override import compute_escalation_level, compute_escalation_decision
from core.soft_clamp import soft_clamp_action
from core.temporal_drift import (
    update_cus_history,
    compute_temporal_drift,
    should_preemptively_escalate,
)

# TRACE_VERSION is imported from mdm_engine.trace_types
from mdm_engine.trace_types import TRACE_VERSION

# Hash determinism: aynı girdi → aynı hash (float quantize + sorted)
def _quantize_float(x: float, ndigits: int = 6) -> float:
    return round(float(x), ndigits)


def _canonical_for_hash(obj: Any) -> Any:
    """Recursive: sort keys, quantize floats (1e-6). NaN/inf → sabit string (hash determinism)."""
    if obj is None:
        return None
    if isinstance(obj, (int, str, bool)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj):
            return "_nan"
        if math.isinf(obj):
            return "_inf_neg" if obj < 0 else "_inf_pos"
        return _quantize_float(obj)
    if isinstance(obj, list):
        # Sıra korunsun (action vector vb. semantik); sadece dict key'leri sıralı
        return [_canonical_for_hash(x) for x in obj] if obj else []
    if isinstance(obj, dict):
        return {k: _canonical_for_hash(v) for k, v in sorted(obj.items())}
    return obj


# Regülasyon-grade: key order + whitespace yok + Unicode stabil (hash tutarlılığı)
def _trace_to_canonical(trace: Union[Dict[str, Any], List[Dict[str, Any]]]) -> bytes:
    return json.dumps(
        trace,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _get_steps(trace: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Trace versioned (dict) veya legacy (list) olsun, steps listesini döndürür."""
    if isinstance(trace, dict) and "steps" in trace:
        return trace["steps"]
    if isinstance(trace, list):
        return trace
    return []


def moral_decision_engine(
    raw_state: Dict[str, Any],
    resolution: List[float] | None = None,
    deterministic: bool = True,
    config_override: Optional[Union[Dict[str, Any], str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tek adımda etik karar: ham durum → seçilen aksiyon + tam trace + human_escalation.
    config_override: dict (J_MIN, H_MAX, ...) veya profile adı (base, production_safe, high_critical).
    context: opsiyonel; "cus_history" (List[float]) ile Phase 5 temporal drift kullanılır (in-place güncellenir).
    """
    if deterministic:
        random.seed(0)

    if isinstance(config_override, str):
        try:
            from mdm_engine.config_profiles import get_config
            config_override = get_config(config_override)
        except Exception:
            config_override = {}
    co = config_override or {}
    j_min = co.get("J_MIN", _config.J_MIN)
    h_max = co.get("H_MAX", _config.H_MAX)
    c_min = co.get("C_MIN", _config.C_MIN)
    c_max = co.get("C_MAX", _config.C_MAX)
    j_crit = co.get("J_CRITICAL", _config.J_CRITICAL)
    h_crit = co.get("H_CRITICAL", _config.H_CRITICAL)

    logger = TraceLogger()

    logger.log(0, "raw_state", copy.deepcopy(raw_state))

    x_t = encode_state(raw_state)
    logger.log(1, "state_encoded", {"x_ext": list(x_t.x_ext), "x_moral": list(x_t.x_moral)})

    input_quality_result = compute_input_quality(raw_state)

    A = generate_actions(x_t, resolution)
    scored: List[tuple] = []
    for a in A:
        scores = evaluate_moral(x_t, a)
        scored.append((a, scores))
    # Coarse-to-fine (Tavsiye §2): en iyi 5 aday etrafında ±0.25 refine
    _score_fn = lambda item: (
        DEFAULT_WEIGHTS.alpha * item[1].W + DEFAULT_WEIGHTS.beta * item[1].J
        - DEFAULT_WEIGHTS.gamma * item[1].H + DEFAULT_WEIGHTS.delta * item[1].C
    )
    top_actions = [a for a, _ in sorted(scored, key=lambda x: -_score_fn(x))[:5]]
    A_refined = refine_actions_around(top_actions, step=0.25)
    for a in A_refined:
        scores = evaluate_moral(x_t, a)
        scored.append((a, scores))
    # Dedupe by action (round 6 decimals)
    _key = lambda a: tuple(round(float(x), 6) for x in a)
    seen = set()
    scored_dedup: List[tuple] = []
    for a, s in scored:
        k = _key(a)
        if k not in seen:
            seen.add(k)
            scored_dedup.append((a, s))
    scored = scored_dedup
    logger.log(2, "actions_generated", {"count": len(scored), "coarse_plus_refined": True})
    logger.log(3, "moral_scores", [{"a": a, "W": s.W, "J": s.J, "H": s.H, "C": s.C} for a, s in scored])

    candidates: List[tuple] = []
    invalid_reason_counts: Dict[str, int] = {}
    for a, scores in scored:
        cv = validate_constraints(scores, j_min=j_min, h_max=h_max, c_min=c_min, c_max=c_max)
        if cv.valid:
            candidates.append((a, scores))
        else:
            for v in cv.violations:
                invalid_reason_counts[v] = invalid_reason_counts.get(v, 0) + 1
        logger.log(4, "constraint", {"a": a, "valid": cv.valid, "violations": cv.violations})

    worst_J = min(s.J for _, s in scored)
    worst_H = max(s.H for _, s in scored)
    # Fail-safe: seçilen (chosen) aksiyonun J/H ile tetikle; worst sadece telemetri (L0 dengelenebilsin).
    fs_tentative = FailSafeResult(override=False, safe_action=(getattr(_config, "SAFE_ACTION", [0.0, 0.5, 0.0, 1.0])).copy(), human_escalation=False, trigger=None)
    sel = select_action(candidates, fs_tentative, DEFAULT_WEIGHTS, config=co, use_pareto=True)
    chosen_scores = next((s for a, s in candidates if a == sel.action), None)
    if chosen_scores is not None:
        fs = fail_safe(MoralScores(W=0, J=chosen_scores.J, H=chosen_scores.H, C=0), j_crit=j_crit, h_crit=h_crit)
    else:
        fs = fail_safe(MoralScores(W=0, J=worst_J, H=worst_H, C=0), j_crit=j_crit, h_crit=h_crit)
    logger.log(5, "fail_safe", {"override": fs.override, "human_escalation": fs.human_escalation})

    if fs.override and fs.safe_action is not None:
        sel = SelectionResult(
            action=fs.safe_action,
            score=None,
            reason="fail_safe",
            frontier_size=sel.frontier_size,
            pareto_gap=sel.pareto_gap,
        )
        chosen_scores = None

    candidate_scores = [
        DEFAULT_WEIGHTS.alpha * s.W + DEFAULT_WEIGHTS.beta * s.J
        - DEFAULT_WEIGHTS.gamma * s.H + DEFAULT_WEIGHTS.delta * s.C
        for _, s in candidates
    ]

    if sel.reason in ("fail_safe", "no_valid_fallback") and fs.safe_action is not None:
        selected_scores = evaluate_moral(x_t, fs.safe_action)
    else:
        selected_scores = next((s for a, s in candidates if a == sel.action), None)

    selection_data = {
        "action": sel.action,
        "reason": sel.reason,
        "score": sel.score,
        "override": fs.override,
        "frontier_size": sel.frontier_size,
        "pareto_gap": sel.pareto_gap,
    }
    if selected_scores is not None:
        selection_data["scores"] = {
            "W": selected_scores.W,
            "J": selected_scores.J,
            "H": selected_scores.H,
            "C": selected_scores.C,
        }
        conf = compute_confidence(
            selected_scores,
            j_min=j_min,
            h_max=h_max,
            c_min=c_min,
            c_max=c_max,
        )
        selection_data["confidence"] = conf.confidence
        selection_data["constraint_margin"] = conf.constraint_margin
        selection_data["base_confidence"] = conf.base_confidence
        selection_data["margin_factor"] = conf.margin_factor
        selection_data["confidence_gradient"] = conf.confidence_gradient
        selection_data["suggest_escalation"] = conf.suggest_escalation
        selection_data["force_escalation"] = conf.force_escalation
        human_escalation = fs.human_escalation or conf.force_escalation
        uncertainty = compute_uncertainty(
            conf.confidence,
            conf.constraint_margin,
            candidate_scores,
            config=co,
        )
        unc_dict = uncertainty.to_dict()
        sorted_scores = sorted(candidate_scores, reverse=True)
        unc_dict["n_candidates"] = len(candidate_scores)
        unc_dict["score_best"] = sorted_scores[0] if sorted_scores else None
        unc_dict["score_second"] = sorted_scores[1] if len(sorted_scores) >= 2 else None
        unc_dict["action_spread_raw"] = uncertainty.as_
        unc_dict["as_norm_missing"] = uncertainty.as_norm is None
        selection_data["uncertainty"] = unc_dict
    else:
        conf = None
        uncertainty = None
        unc_dict = None
        human_escalation = fs.human_escalation

    # Adapter’dan gelen external_confidence (örn. ORES distance-to-threshold) escalation için kullanılır
    effective_confidence = None
    if conf is not None:
        if context is not None and context.get("external_confidence") is not None:
            effective_confidence = max(0.0, min(1.0, float(context["external_confidence"])))
        else:
            effective_confidence = conf.confidence
        effective_confidence = max(0.0, min(1.0, effective_confidence * input_quality_result.input_quality))

    # H_high / H_critical: seçilen aksiyonun H'ine göre karar ver (worst_H tüm grid'den L0'ı kapatmasın)
    selected_H = None
    if selection_data.get("scores"):
        selected_H = selection_data["scores"].get("H")
    H_for_escalation = selected_H if selected_H is not None else worst_H

    base_level = 0
    base_driver = "none"
    escalation_drivers: List[str] = []
    if conf is not None and effective_confidence is not None:
        base_level, base_driver = compute_escalation_decision(
            effective_confidence,
            conf.constraint_margin,
            H_for_escalation,
            h_crit,
            config=co,
            h_high=h_max,
            as_norm=uncertainty.as_norm if uncertainty else None,
            divergence=uncertainty.divergence if uncertainty else None,
        )
        if base_driver != "none":
            escalation_drivers.append(base_driver)
        escalation = compute_escalation_level(
            effective_confidence,
            conf.constraint_margin,
            H_for_escalation,
            h_crit,
            config=co,
            h_high=h_max,
            as_norm=uncertainty.as_norm if uncertainty else None,
            divergence=uncertainty.divergence if uncertainty else None,
        )
    else:
        escalation = 2 if fs.override else 0
        if fs.override:
            escalation_drivers.append("fail_safe")
    if sel.reason == "no_valid_fallback":
        escalation = 2
        escalation_drivers = ["no_valid_candidates"]
    # Hard invariant: fail_safe ⇒ level=2, HOLD_REVIEW, clamp_applied=False (INVARIANTS_SCHEMA_METRICS)
    if fs.override:
        escalation = 2
        escalation_drivers = ["fail_safe"]

    temporal_drift_data: Optional[Dict[str, Any]] = None
    if context is not None and uncertainty is not None:
        window = co.get("CUS_MEAN_WINDOW", _config.CUS_MEAN_WINDOW)
        delta_thresh = co.get("DELTA_CUS_THRESHOLD", _config.DELTA_CUS_THRESHOLD)
        mean_thresh = co.get("CUS_MEAN_THRESHOLD", _config.CUS_MEAN_THRESHOLD)
        min_hist = co.get("DRIFT_MIN_HISTORY", getattr(_config, "DRIFT_MIN_HISTORY", 30))
        hist = context.get("cus_history", [])
        hist = update_cus_history(hist, uncertainty.cus, window)
        context["cus_history"] = hist
        drift = compute_temporal_drift(uncertainty.cus, hist, delta_thresh, mean_thresh)
        delta_trigger = drift.delta_cus is not None and drift.delta_cus > delta_thresh
        mean_trigger = drift.cus_mean > mean_thresh
        if len(hist) < min_hist:
            drift_driver = "warmup"
        elif delta_trigger and mean_trigger:
            drift_driver = "delta+mean"
        elif delta_trigger:
            drift_driver = "delta"
        elif mean_trigger:
            drift_driver = "mean"
        else:
            drift_driver = "none"
        drift_applied = should_preemptively_escalate(drift, history_len=len(hist), min_history=min_hist)
        temporal_drift_data = {
            "delta_cus": drift.delta_cus,
            "cus_mean": drift.cus_mean,
            "preemptive_escalation": drift.preemptive_escalation,
            "history_len": len(hist),
            "min_history": min_hist,
            "driver": drift_driver,
            "applied": drift_applied,
        }
        if drift_applied:
            escalation = max(escalation, 1)
            if drift_driver != "none":
                escalation_drivers.append(f"temporal_drift:{drift_driver}")

    # Composite driver öncelik sırası: primary stabil olsun (A|B her zaman aynı sıra)
    _DRIVER_PRIORITY = (
        "fail_safe",
        "no_valid_candidates",
        "h_critical",  # H_crit aşımı
        "constraint_violation",
        "as_norm",     # as_norm_low vb.
        "temporal_drift",
        "confidence",
    )

    def _driver_priority(d: str) -> int:
        d_lower = (d or "").lower()
        for i, key in enumerate(_DRIVER_PRIORITY):
            if key in d_lower:
                return i
        return len(_DRIVER_PRIORITY)

    escalation_drivers = sorted(escalation_drivers, key=_driver_priority)

    # Tavsiye §6: driver dağılımı — son N kararda escalation_driver histogramı; ani sıçrama = drift alarm
    primary_driver = (escalation_drivers[0] if escalation_drivers else "none")
    driver_hist: List[str] = list(context.get("driver_history", [])) if context else []
    driver_hist = (driver_hist + [primary_driver])[-50:]
    if context is not None:
        context["driver_history"] = driver_hist
    drift_driver_alarm = False
    if len(driver_hist) >= 10:
        recent = driver_hist[-10:]
        prev = driver_hist[-30:-10] if len(driver_hist) >= 30 else driver_hist[:-10]
        count_recent = sum(1 for d in recent if d and "constraint_violation" in d)
        count_prev = sum(1 for d in prev if d and "constraint_violation" in d)
        if count_recent >= 5 and (len(prev) < 5 or count_prev <= 1):
            drift_driver_alarm = True

    soft_safe_applied = False
    raw_action = list(sel.action)
    final_action = sel.action
    self_regulation_data: Optional[Dict[str, Any]] = None
    if escalation == 1 and not fs.override and uncertainty is not None:
        confidence_before = conf.confidence
        alpha = co.get("SOFT_CLAMP_ALPHA", _config.SOFT_CLAMP_ALPHA)
        beta = co.get("SOFT_CLAMP_BETA", _config.SOFT_CLAMP_BETA)
        gamma = co.get("SOFT_CLAMP_GAMMA", _config.SOFT_CLAMP_GAMMA)
        clamped = soft_clamp_action(sel.action, uncertainty.cus, alpha, beta, gamma)
        final_action = clamped
        selected_scores = evaluate_moral(x_t, clamped)
        conf = compute_confidence(
            selected_scores,
            j_min=j_min,
            h_max=h_max,
            c_min=c_min,
            c_max=c_max,
        )
        uncertainty = compute_uncertainty(
            conf.confidence,
            conf.constraint_margin,
            candidate_scores,
            config=co,
        )
        _unc = uncertainty.to_dict()
        _sorted = sorted(candidate_scores, reverse=True)
        _unc["n_candidates"] = len(candidate_scores)
        _unc["score_best"] = _sorted[0] if _sorted else None
        _unc["score_second"] = _sorted[1] if len(_sorted) >= 2 else None
        _unc["action_spread_raw"] = uncertainty.as_
        _unc["as_norm_missing"] = uncertainty.as_norm is None
        unc_dict = _unc
        human_escalation = False
        delta_confidence = conf.confidence - confidence_before
        self_regulation_data = {"delta_confidence": delta_confidence}
        selection_data = {
            "action": clamped,
            "reason": sel.reason,
            "score": sel.score,
            "override": False,
            "scores": {
                "W": selected_scores.W,
                "J": selected_scores.J,
                "H": selected_scores.H,
                "C": selected_scores.C,
            },
            "confidence": conf.confidence,
            "constraint_margin": conf.constraint_margin,
            "base_confidence": conf.base_confidence,
            "margin_factor": conf.margin_factor,
            "confidence_gradient": conf.confidence_gradient,
            "suggest_escalation": conf.suggest_escalation,
            "force_escalation": conf.force_escalation,
            "uncertainty": unc_dict,
            "self_regulation": self_regulation_data,
        }
        soft_safe_applied = True

    selection_data["escalation"] = escalation
    selection_data["soft_safe_applied"] = soft_safe_applied
    if temporal_drift_data is not None:
        selection_data["temporal_drift"] = temporal_drift_data

    logger.log(6, "selection", selection_data)

    trace_list = [{"step": e.step, "event_type": e.event_type, "data": e.data} for e in logger.trace]
    trace_output: Dict[str, Any] = {"version": TRACE_VERSION, "steps": trace_list}
    selection_reason_str = "pareto_tiebreak:margin>H>J>W>C" if sel.reason == "pareto_tiebreak" else sel.reason
    out = {
        "action": final_action,
        "raw_action": raw_action,
        "trace": trace_output,
        "human_escalation": human_escalation,
        "reason": sel.reason,
        "selection_reason": selection_reason_str,
        "escalation_driver": "|".join(escalation_drivers) if escalation_drivers else "none",
        "escalation_drivers": escalation_drivers,
        "escalation_base": {"level": base_level, "driver": base_driver},
        "trace_hash": compute_trace_hash(trace_output),
    }
    if conf is not None:
        out["confidence"] = effective_confidence if effective_confidence is not None else conf.confidence
        out["constraint_margin"] = conf.constraint_margin
        out["confidence_gradient"] = conf.confidence_gradient
    # Kalibrasyon teşhisi: hangi confidence kullanıldı (internal vs external)
    out["confidence_internal"] = conf.confidence if conf is not None else None
    out["confidence_external"] = (context.get("external_confidence") if context else None)
    out["confidence_used"] = effective_confidence
    out["confidence_source"] = "external" if (context is not None and context.get("external_confidence") is not None) else "internal"
    if uncertainty is not None:
        out["uncertainty"] = unc_dict
    out["escalation"] = escalation
    out["soft_safe_applied"] = soft_safe_applied
    if temporal_drift_data is not None:
        out["temporal_drift"] = temporal_drift_data
    if self_regulation_data is not None:
        out["self_regulation"] = self_regulation_data
    if selected_scores is not None:
        out["J"] = selected_scores.J
        out["H"] = selected_scores.H
    # H_critical kararı worst_H ile alınır; CSV'de mdm_H (seçilen) vs mdm_worst_H tutarlılığı
    out["worst_H"] = worst_H
    out["worst_J"] = worst_J
    if fs.override and getattr(fs, "trigger", None):
        out["fail_safe_reason"] = fs.trigger
    # Tavsiye §1: input quality / evidence consistency
    out["input_quality"] = input_quality_result.input_quality
    out["evidence_consistency"] = input_quality_result.evidence_consistency
    # Tavsiye §3: Pareto sinyalleri
    out["frontier_size"] = sel.frontier_size
    out["pareto_gap"] = sel.pareto_gap
    # Tavsiye §6: driver history ve drift alarm
    out["driver_history_len"] = len(driver_hist)
    out["drift_driver_alarm"] = drift_driver_alarm
    # Operasyon: missing_fields (alfabetik sıra = deterministik), valid_candidate_count, invalid_reason_counts
    missing_list = sorted([k for k, m in zip(STATE_KEYS, input_quality_result.missing_mask) if not m])
    out["missing_fields"] = missing_list
    out["valid_candidate_count"] = len(candidates)
    out["invalid_reason_counts"] = dict(sorted(invalid_reason_counts.items()))
    # Replay / denetim: state_hash + config_hash (float quantize + sorted → aynı girdi aynı hash)
    canonical_state = _canonical_for_hash(raw_state)
    canonical_config = _canonical_for_hash(co)
    out["state_hash"] = hashlib.sha256(
        json.dumps(canonical_state, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()
    out["config_hash"] = hashlib.sha256(
        json.dumps(canonical_config, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    # Debug: karar invariants assert (MDM_ASSERT_INVARIANTS=1 veya context["assert_invariants"])
    _assert_inv = os.environ.get("MDM_ASSERT_INVARIANTS", "")
    if context and context.get("assert_invariants") or (_assert_inv.strip().lower() in ("1", "true", "yes")):
        try:
            from mdm_engine.invariants import check_decision_invariants
            packet_view = {
                "mdm": {**out, "level": out.get("escalation", 0)},
                "final_action": "APPLY" if out.get("escalation") == 0 else ("APPLY_CLAMPED" if out.get("escalation") == 1 else "HOLD_REVIEW"),
                "clamps": [{"type": "soft_safe"}] if out.get("soft_safe_applied") else [],
            }
            violations = check_decision_invariants(packet_view, strict=True)
            if violations:
                raise AssertionError("Decision invariants violated: " + "; ".join(f"{n}: {m}" for n, m in violations))
        except ImportError:
            pass
    return out


def extract_raw_state(trace: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any] | None:
    """Trace'ten replay girdisi olan raw_state'i çıkarır (step 0, event_type='raw_state')."""
    steps = _get_steps(trace)
    for event in steps:
        if event.get("step") == 0 and event.get("event_type") == "raw_state":
            return event.get("data")
    return None


def extract_action(trace: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[float] | None:
    """Trace'ten orijinal seçilen aksiyonu çıkarır (step 6, event_type='selection')."""
    steps = _get_steps(trace)
    for event in steps:
        if event.get("step") == 6 and event.get("event_type") == "selection":
            data = event.get("data")
            return data.get("action") if isinstance(data, dict) else None
    return None


def extract_selection_data(trace: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any] | None:
    """Trace'ten step 6 selection data (action, reason, score, scores, override) döndürür."""
    steps = _get_steps(trace)
    for event in steps:
        if event.get("step") == 6 and event.get("event_type") == "selection":
            return event.get("data") if isinstance(event.get("data"), dict) else None
    return None


def extract_fail_safe_data(trace: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any] | None:
    """Trace'ten step 5 fail_safe data (override, human_escalation) döndürür."""
    steps = _get_steps(trace)
    for event in steps:
        if event.get("step") == 5 and event.get("event_type") == "fail_safe":
            return event.get("data") if isinstance(event.get("data"), dict) else None
    return None


def compute_trace_hash(trace: Union[Dict[str, Any], List[Dict[str, Any]]]) -> str:
    """Trace'in deterministik SHA256 hash'i; sort_keys+separators ile regülasyon-grade."""
    return hashlib.sha256(_trace_to_canonical(trace)).hexdigest()


# Tavsiye §4: Sensitivity / robustness — küçük state pertürbasyonunda karar değişiyor mu?
_SENSITIVITY_STATE_KEYS = ("physical", "social", "context", "risk", "compassion", "justice", "harm_sens", "responsibility", "empathy")


def run_sensitivity_check(
    raw_state: Dict[str, Any],
    config_override: Optional[Union[Dict[str, Any], str]] = None,
    context: Optional[Dict[str, Any]] = None,
    epsilon: float = 0.02,
    state_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    State'i ±epsilon perturbe edip karar/level değişimini sayar.
    Returns: { "stable": bool, "flip_count": int, "level_flip_count": int }.
    """
    keys = state_keys or list(_SENSITIVITY_STATE_KEYS)
    base = moral_decision_engine(raw_state, config_override=config_override, context=context or {}, deterministic=True)
    action0 = tuple(round(float(x), 6) for x in (base.get("action") or []))
    level0 = base.get("escalation", 0)
    flip_count = 0
    level_flip_count = 0
    for key in keys:
        v = raw_state.get(key)
        if v is None:
            continue
        try:
            x = float(v)
        except (TypeError, ValueError):
            continue
        for delta in (epsilon, -epsilon):
            perturbed = dict(raw_state)
            perturbed[key] = max(0.0, min(1.0, x + delta))
            out = moral_decision_engine(perturbed, config_override=config_override, context=context or {}, deterministic=True)
            action1 = tuple(round(float(x), 6) for x in (out.get("action") or []))
            level1 = out.get("escalation", 0)
            if action1 != action0:
                flip_count += 1
            if level1 != level0:
                level_flip_count += 1
    return {
        "stable": flip_count == 0,
        "flip_count": flip_count,
        "level_flip_count": level_flip_count,
    }


def replay(
    trace: Union[Dict[str, Any], List[Dict[str, Any]]],
    validate: bool = True,
    verify_hash: bool = False,
    validate_ethics: bool = False,
) -> Dict[str, Any]:
    """
    Kayıtlı trace'ten raw_state alıp motoru tekrar çalıştırır (deterministic=True ile).
    validate=True: yeni action == trace'teki action.
    verify_hash=True: yeni trace hash == orijinal trace hash.
    validate_ethics=True: yeni selection/fail_safe data (scores, override) == orijinal.
    """
    raw_state = extract_raw_state(trace)
    if raw_state is None:
        raise ValueError("Trace'te raw_state yok (step 0, event_type='raw_state' gerekli)")

    result = moral_decision_engine(raw_state, deterministic=True)

    if validate:
        orig_action = extract_action(trace)
        if orig_action is not None:
            new_action = result["action"]
            assert new_action == orig_action, (
                "Replay determinizm ihlali: yeni action trace'teki action ile aynı değil."
            )

    if verify_hash:
        orig_hash = compute_trace_hash(trace)
        new_hash = result.get("trace_hash") or compute_trace_hash(result["trace"])
        assert new_hash == orig_hash, (
            "Replay bütünlük ihlali: yeni trace hash'i orijinal ile aynı değil."
        )

    if validate_ethics:
        orig_sel = extract_selection_data(trace)
        new_sel = extract_selection_data(result["trace"])
        orig_fs = extract_fail_safe_data(trace)
        new_fs = extract_fail_safe_data(result["trace"])
        if orig_sel and new_sel:
            assert new_sel.get("action") == orig_sel.get("action")
            assert new_sel.get("override") == orig_sel.get("override")
            if "scores" in orig_sel and "scores" in new_sel:
                for k in ("W", "J", "H", "C"):
                    assert new_sel["scores"][k] == orig_sel["scores"][k]
            if "confidence" in orig_sel and "confidence" in new_sel:
                assert new_sel["confidence"] == orig_sel["confidence"]
            if "constraint_margin" in orig_sel and "constraint_margin" in new_sel:
                assert new_sel["constraint_margin"] == orig_sel["constraint_margin"]
            if "confidence_gradient" in orig_sel and "confidence_gradient" in new_sel:
                assert new_sel["confidence_gradient"] == orig_sel["confidence_gradient"]
            if "uncertainty" in orig_sel and "uncertainty" in new_sel:
                tol = 1e-9
                for key in ("hi", "de", "de_norm", "as_", "as_norm", "cus", "divergence"):
                    if key in orig_sel["uncertainty"] and key in new_sel["uncertainty"]:
                        assert abs(new_sel["uncertainty"][key] - orig_sel["uncertainty"][key]) <= tol, (
                            f"Replay uncertainty ihlali: {key}"
                        )
            if "escalation" in orig_sel and "escalation" in new_sel:
                assert new_sel["escalation"] == orig_sel["escalation"], "Replay escalation ihlali"
            if "soft_safe_applied" in orig_sel and "soft_safe_applied" in new_sel:
                assert new_sel["soft_safe_applied"] == orig_sel["soft_safe_applied"], "Replay soft_safe_applied ihlali"
        if orig_fs and new_fs:
            assert new_fs.get("override") == orig_fs.get("override")

    return result


if __name__ == "__main__":
    state = {
        "physical": 0.8,
        "social": 0.7,
        "context": 0.6,
        "risk": 0.75,
        "compassion": 0.6,
        "justice": 0.9,
        "harm_sens": 0.7,
        "responsibility": 0.8,
        "empathy": 0.65,
    }
    result = moral_decision_engine(state)
    print("Seçilen aksiyon:", result["action"])
    print("Gerekçe:", result["reason"])
    print("Trace hash:", result["trace_hash"][:16], "...")

    replayed = replay(result["trace"], validate=True, verify_hash=True)
    print("Replay OK — determinizm ve bütünlük doğrulandı.")
    assert replayed["action"] == result["action"]
