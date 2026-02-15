#!/usr/bin/env python
# MDM — Canlı denetim: Wikimedia EventStreams + ORES skoru + MDM audit.
# Kullanım: pip install requests sseclient-py; python tools/live_wiki_audit.py [--jsonl path]
# Evde tek PC: canlı veri + dış karar (ORES) + MDM denetçi (L0/L1/L2) + Decision Packet (JSONL).

import argparse
import hashlib
import json
import math
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

# Thread-safe list for dashboard live stream (dashboard reads this)
LIVE_PACKETS: list = []
# Dashboard için bağlantı durumu: connected, error, events_seen, packets_sent
LIVE_STATUS: Dict[str, Any] = {"connected": False, "error": None, "events_seen": 0, "packets_sent": 0}

try:
    from sseclient import SSEClient
except ImportError:
    print("pip install sseclient-py")
    sys.exit(1)

from mdm_engine.audit_spec import build_decision_packet

EVENTSTREAM_URL = "https://stream.wikimedia.org/v2/stream/recentchange"
ORES_SCORE_URL_TEMPLATE = "https://ores.wikimedia.org/v3/scores/enwiki/{revid}?models=damaging|goodfaith"
WIKI_COMPARE_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "MDM-Live-Audit/0.1 (https://github.com/MeetlyTR/mdm-engine)"

# Packet şema uyumluluğu (eski JSONL/CSV bozulmasın)
SCHEMA_VERSION = "2.0"  # packet["mdm"] only; CSV mdm_*; dashboard rejects < 2.0
ADAPTER_VERSION = "wiki-ores-1.0"

# ORES revid cache (max size); thread-safe değil, tek consumer thread varsayıyoruz
_ORES_CACHE: Dict[int, Dict[str, Any]] = {}
_ORES_CACHE_MAX = 2000


@dataclass
class ExternalDecision:
    revid: int
    p_damaging: float
    p_goodfaith: float
    decision: str  # "FLAG" | "ALLOW"


def binary_entropy(p: float) -> float:
    p = min(max(p, 1e-9), 1 - 1e-9)
    return -(p * math.log(p, 2) + (1 - p) * math.log(1 - p, 2))


def _l1_clamp_type_from_driver(driver: str) -> str:
    """L1 clamp type: driver'a göre confidence / drift / constraint (CSV okunabilirliği)."""
    if not driver:
        return "constraint"
    d = (driver or "").lower()
    if "confidence" in d:
        return "confidence"
    if "temporal_drift" in d or "drift" in d:
        return "drift"
    if "constraint" in d:
        return "constraint"
    return "constraint"


def fetch_ores_scores(
    revid: int,
    timeout_s: float = 5.0,
    max_retries: int = 3,
    retry_backoff_base_ms: float = 1000.0,
) -> Optional[Dict[str, Any]]:
    """
    ORES skorlarını çeker. Revid cache kullanır; 429/5xx/timeout'ta backoff ile tekrar dener.
    Çıktı: cache_hit, retry_count, backoff_ms + standart alanlar (revid, p_damaging, decision, latency_ms, error, vb.).
    """
    # Cache hit
    if revid in _ORES_CACHE:
        cached = dict(_ORES_CACHE[revid])
        cached["ores_cache_hit"] = True
        cached["ores_retry_count"] = 0
        cached["ores_backoff_ms"] = None
        return cached
    url = ORES_SCORE_URL_TEMPLATE.format(revid=revid)
    out: Dict[str, Any] = {
        "http_status": None,
        "latency_ms": None,
        "error": None,
        "model": "ores damaging|goodfaith",
        "threshold": 0.5,
        "ores_cache_hit": False,
        "ores_retry_count": 0,
        "ores_backoff_ms": None,
    }
    total_backoff_ms = 0.0
    for attempt in range(max_retries + 1):
        t0 = time.time()
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout_s)
            out["latency_ms"] = round((time.time() - t0) * 1000, 2)
            out["http_status"] = r.status_code
            if r.status_code == 200:
                data = r.json()
                scores = data.get("enwiki", {}).get("scores", {}).get(str(revid))
                if not scores:
                    out["error"] = "no_scores"
                    return out
                dmg = scores.get("damaging", {}).get("score", {}).get("probability", {}).get("true", 0)
                gf = scores.get("goodfaith", {}).get("score", {}).get("probability", {}).get("true", 1)
                decision = "FLAG" if float(dmg) >= 0.5 else "ALLOW"
                out["revid"] = revid
                out["p_damaging"] = float(dmg)
                out["p_goodfaith"] = float(gf)
                out["decision"] = decision
                out["ores_retry_count"] = attempt
                out["ores_backoff_ms"] = round(total_backoff_ms, 2) if total_backoff_ms else None
                if len(_ORES_CACHE) >= _ORES_CACHE_MAX:
                    _ORES_CACHE.pop(next(iter(_ORES_CACHE)))
                _ORES_CACHE[revid] = {k: v for k, v in out.items() if k not in ("ores_retry_count", "ores_backoff_ms")}
                _ORES_CACHE[revid]["ores_retry_count"] = 0
                _ORES_CACHE[revid]["ores_backoff_ms"] = None
                return out
            # Retry on 429 or 5xx
            if r.status_code != 429 and (r.status_code < 500 or r.status_code > 599):
                out["error"] = f"HTTP {r.status_code}"
                return out
        except Exception as e:
            out["latency_ms"] = round((time.time() - t0) * 1000, 2)
            out["error"] = str(e)[:200]
        out["ores_retry_count"] = attempt + 1
        if attempt < max_retries:
            backoff_ms = retry_backoff_base_ms * (2 ** attempt)
            total_backoff_ms += backoff_ms
            time.sleep(backoff_ms / 1000.0)
    out["ores_backoff_ms"] = round(total_backoff_ms, 2) if total_backoff_ms else None
    return out


def build_mdm_input(event: Dict[str, Any], ext: Dict[str, Any]) -> Dict[str, Any]:
    """
    ORES + event → MDM state (physical, social, context, risk, compassion, justice, harm_sens, responsibility, empathy).
    """
    cus = binary_entropy(ext.get("p_damaging", 0.0))
    user = event.get("user", "")
    is_anon = bool(event.get("anon", False)) or (user and any(c.isdigit() for c in user))
    bot = bool(event.get("bot", False))
    length = event.get("length") or {}
    delta = int(length.get("new", 0)) - int(length.get("old", 0))
    evidence = 0.7
    if is_anon:
        evidence -= 0.2
    if abs(delta) > 500:
        evidence -= 0.2
    if bot:
        evidence += 0.1
    evidence = max(0.0, min(1.0, evidence))

    risk = ext.get("p_damaging", 0.0)
    state = {
        "physical": 0.5,
        "social": 0.3 if is_anon else 0.6,
        "context": evidence,
        "risk": risk,
        "compassion": 0.5,
        "justice": 0.9,
        "harm_sens": 0.4 + 0.4 * risk,
        "responsibility": 0.6,
        "empathy": 0.5,
    }
    # Distance-to-threshold confidence: ORES threshold’a yakınsa belirsiz (düşük), uzaksa net (yüksek)
    threshold = float(ext.get("threshold", 0.5))
    p_dmg = float(ext.get("p_damaging", 0.5))
    external_confidence = min(1.0, abs(p_dmg - threshold) / 0.5)

    context = {
        "source": "wikimedia_recentchange",
        "server_name": event.get("server_name"),
        "wiki": event.get("wiki"),
        "title": event.get("title"),
        "user": user,
        "comment": event.get("comment"),
        "timestamp": event.get("timestamp"),
        "entity_id": f"user:{user}",
        "revid": ext.get("revid"),
        "p_damaging": ext.get("p_damaging"),
        "p_goodfaith": ext.get("p_goodfaith"),
        "decision": ext.get("decision"),
        "external_confidence": external_confidence,
    }
    return {"state": state, "context": context}


def audit_with_mdm(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Gerçek MDM: decide() tam çıktısı (Decision Packet + explain için)."""
    from mdm_engine import decide
    # Wiki/ORES denetimi için varsayılan wiki_calibrated (CUS_MEAN_THRESHOLD, AS_SOFT_THRESHOLD kalibre)
    profile = os.environ.get("MDM_CONFIG_PROFILE", "wiki_calibrated")
    return decide(
        payload["state"],
        context=payload["context"],
        profile=profile,
        deterministic=True,
    )


def fetch_wiki_diff(
    from_revid: Optional[int],
    to_revid: int,
    timeout_s: float = 5.0,
) -> Optional[Dict[str, Any]]:
    """
    MediaWiki API action=compare ile iki revizyon arası diff HTML çeker (L2 inceleme için kanıt).
    from_revid=None ise (örn. new page) None döner.
    """
    if from_revid is None:
        return None
    try:
        params = {
            "action": "compare",
            "format": "json",
            "fromrev": from_revid,
            "torev": to_revid,
            "prop": "diff",
        }
        r = requests.get(
            WIKI_COMPARE_URL,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout_s,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        compare = data.get("compare") or {}
        diff_html = compare.get("diff")
        if diff_html is None:
            return None
        diff_text = diff_html if isinstance(diff_html, str) else str(diff_html)
        return {"diff": diff_text, "from_revid": from_revid, "to_revid": to_revid}
    except Exception:
        return None


_profile_logged: bool = False


def get_run_context(run_id: str) -> Dict[str, Any]:
    """Koşu bağlamı: config_profile, git_commit, host, session_id — 'neden dün farklıydı?' için."""
    global _profile_logged
    config_profile = os.environ.get("MDM_CONFIG_PROFILE", "wiki_calibrated")
    source = "MDM_CONFIG_PROFILE" if os.environ.get("MDM_CONFIG_PROFILE") else "default (wiki_calibrated)"
    if not _profile_logged:
        print(f"MDM config profile: {config_profile} (from {source})", file=sys.stderr)
        _profile_logged = True
    git_commit = os.environ.get("MDM_GIT_COMMIT", "")
    if not git_commit and ROOT.joinpath(".git").exists():
        try:
            git_commit = (
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(ROOT),
                    timeout=2,
                    stderr=subprocess.DEVNULL,
                )
                .decode("utf-8", errors="replace")
                .strip()[:12]
            )
        except Exception:
            pass
    host = socket.gethostname() or ""
    return {
        "config_profile": config_profile,
        "git_commit": git_commit,
        "host": host,
        "session_id": run_id,
    }


def run_live_loop(
    callback: Callable[[Dict[str, Any]], None],
    stop_event: threading.Event,
    sample_every_n: int = 25,
    run_id: Optional[str] = None,
) -> None:
    """
    SSE döngüsünü çalıştırır; her Decision Packet için callback(packet) çağırır.
    packet içinde latency_ms (event işleme süresi, ms) eklenir.
    stop_event.set() ile döngü durur.
    """
    run_id = run_id or str(uuid.uuid4())
    run_ctx = get_run_context(run_id)
    seen_ids: set = set()
    seen_ids_max = 10000
    last_msg_time: Optional[float] = None

    LIVE_STATUS["connected"] = False
    LIVE_STATUS["error"] = None
    LIVE_STATUS["events_seen"] = 0
    LIVE_STATUS["packets_sent"] = 0
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    SSE_CONNECT_TIMEOUT = 10
    SSE_READ_TIMEOUT = 120  # Uzun süre veri gelmezse timeout → reconnect (kopma/donma önlemi)
    backoff_sec = 5.0
    MAX_BACKOFF = 60.0
    cus_history: list = []  # Reconnect sonrası da korunur (drift history sıfırlanmaz)
    i = 0

    while not stop_event.is_set():
        try:
            resp = session.get(
                EVENTSTREAM_URL,
                stream=True,
                timeout=(SSE_CONNECT_TIMEOUT, SSE_READ_TIMEOUT),
            )
            if resp.status_code != 200:
                LIVE_STATUS["error"] = f"EventStreams HTTP {resp.status_code}"
                time.sleep(backoff_sec)
                backoff_sec = min(backoff_sec * 1.5, MAX_BACKOFF)
                continue
            client = SSEClient(resp)
            events = client.events()
            LIVE_STATUS["connected"] = True
            LIVE_STATUS["error"] = None
            backoff_sec = 5.0
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            LIVE_STATUS["error"] = str(e)[:200]
            LIVE_STATUS["connected"] = False
            time.sleep(backoff_sec)
            backoff_sec = min(backoff_sec * 1.5, MAX_BACKOFF)
            continue
        except Exception as e:
            LIVE_STATUS["error"] = str(e)[:200]
            return

        try:
            for msg in events:
                if stop_event.is_set():
                    break
                if getattr(msg, "event", None) != "message" or not getattr(msg, "data", None):
                    continue
                try:
                    event = json.loads(msg.data)
                except Exception:
                    continue
                if event.get("meta", {}).get("domain") == "canary":
                    continue
                if event.get("server_name") != "en.wikipedia.org":
                    continue
                if event.get("type") not in ("edit", "new"):
                    continue
                i += 1
                LIVE_STATUS["events_seen"] = i
                if i % sample_every_n != 0:
                    continue
                rev = None
                if isinstance(event.get("revision"), dict):
                    rev = event["revision"].get("new")
                rev = rev or event.get("rev_id") or event.get("id")
                if not rev:
                    continue
                # Dedupe: EventStreams meta.id veya composite ID
                meta = event.get("meta") or {}
                source_event_id = meta.get("id") or f"{event.get('server_name', '')}:{rev}:{meta.get('dt', '')}"
                if source_event_id in seen_ids:
                    continue
                seen_ids.add(source_event_id)
                if len(seen_ids) > seen_ids_max:
                    seen_ids = set(list(seen_ids)[seen_ids_max // 2 :])
                msg_time = time.time()
                sse_wait_ms = round((msg_time - last_msg_time) * 1000, 2) if last_msg_time is not None else None
                last_msg_time = msg_time

                t0 = time.time()
                ext = fetch_ores_scores(int(rev))
                if not ext or ext.get("decision") is None:
                    continue
                t_mdm_start = time.time()
                payload = build_mdm_input(event, ext)
                payload["context"]["cus_history"] = cus_history
                engine_result = audit_with_mdm(payload)
                cus_history = payload["context"].get("cus_history", cus_history)
                mdm_latency_ms = round((time.time() - t_mdm_start) * 1000, 2)
                latency_ms = round((time.time() - t0) * 1000, 2)
                level = engine_result.get("escalation", 0)
                ores_d = ext.get("decision") or "ALLOW"
                # Wiki adapter policy: ORES FLAG + MDM L0 → sessiz override yok, L2 (HOLD_REVIEW)
                wiki_ores_flag_override = ores_d == "FLAG" and level == 0
                if wiki_ores_flag_override:
                    level = 2
                reason = engine_result.get("reason", "ok")
                soft_clamp = engine_result.get("soft_safe_applied", False)
                external = {
                    "decision": ext.get("decision"),
                    "p_damaging": ext.get("p_damaging"),
                    "p_goodfaith": ext.get("p_goodfaith"),
                    "model": ext.get("model", "ores damaging|goodfaith"),
                    "threshold": ext.get("threshold", 0.5),
                    "http_status": ext.get("http_status"),
                    "latency_ms": ext.get("latency_ms"),
                    "error": ext.get("error"),
                    "ores_cache_hit": ext.get("ores_cache_hit", False),
                    "ores_retry_count": ext.get("ores_retry_count", 0),
                    "ores_backoff_ms": ext.get("ores_backoff_ms"),
                }
                input_data = {
                    "title": payload["context"].get("title", ""),
                    "user": payload["context"].get("user", ""),
                    "revid": ext.get("revid"),
                    "comment": payload["context"].get("comment", ""),
                    "state_snapshot": payload["state"],
                }
                evidence = None
                evidence_status = "NA"  # L2 dışı: diff ilgili değil (yanlış sinyal vermemek için MISSING değil NA)
                diff_fetch_latency_ms = None
                rev_old = event.get("revision", {}).get("old") if isinstance(event.get("revision"), dict) else None
                if level == 2:
                    t_diff = time.time()
                    try:
                        evidence = fetch_wiki_diff(rev_old, ext.get("revid"))
                        evidence_status = "OK" if evidence and evidence.get("diff") else "MISSING"
                        diff_fetch_latency_ms = round((time.time() - t_diff) * 1000, 2)
                    except Exception:
                        evidence_status = "ERROR"
                review = {"status": "pending"} if level == 2 else {}
                ts = time.time()
                packet = build_decision_packet(
                    run_id=run_id,
                    ts=ts,
                    source="wikimedia_recentchange",
                    entity_id=payload["context"].get("entity_id", ""),
                    external=external,
                    input_data=input_data,
                    engine_result=engine_result,
                    evidence=evidence,
                    review=review,
                )
                packet["schema_version"] = SCHEMA_VERSION
                packet["adapter_version"] = ADAPTER_VERSION
                packet["source_event_id"] = source_event_id
                packet["config_profile"] = run_ctx["config_profile"]
                packet["git_commit"] = run_ctx["git_commit"]
                packet["host"] = run_ctx["host"]
                packet["session_id"] = run_ctx["session_id"]
                packet["latency_ms"] = latency_ms
                packet["mdm_latency_ms"] = mdm_latency_ms
                packet["sse_wait_ms"] = sse_wait_ms
                packet["ores_cache_hit"] = ext.get("ores_cache_hit", False)
                packet["ores_retry_count"] = ext.get("ores_retry_count", 0)
                packet["ores_backoff_ms"] = ext.get("ores_backoff_ms")
                packet["mdm_input_risk"] = payload["state"].get("risk")
                state_json = json.dumps(payload["state"], sort_keys=True)
                packet["mdm_input_state_hash"] = hashlib.sha256(state_json.encode()).hexdigest()[:16]
                final_action = "APPLY" if level == 0 else ("APPLY_CLAMPED" if level == 1 else "HOLD_REVIEW")
                packet["final_action"] = final_action
                # Denetim nedeni: wiki policy override (ORES FLAG + L0 → L2) veya engine driver
                packet["final_action_reason"] = "wiki:ores_flag_disagree" if wiki_ores_flag_override else (engine_result.get("escalation_driver") or reason)
                # Birleşik driver "A|B" ise primary = ilk parça (degenerate/research için)
                far = packet["final_action_reason"] or ""
                packet["final_action_reason_primary"] = far.split("|")[0].strip() if isinstance(far, str) and "|" in far else far
                packet["mismatch"] = (ores_d == "ALLOW" and level in (1, 2)) or (ores_d == "FLAG" and level == 0)
                # SSOT: UI/CSV'de "reason" = policy-facing neden (final_action_reason); engine_reason = çekirdek teşhis
                reason_for_ui = packet["final_action_reason"]
                engine_reason = engine_result.get("escalation_driver") or reason
                clamps = []
                if soft_clamp:
                    clamps.append({"type": "soft_safe", "strength": 1.0, "reason": reason, "before": "APPLY", "after": "APPLY_CLAMPED"})
                if level == 2:
                    l2_reason = "wiki:ores_flag_disagree" if wiki_ores_flag_override else reason
                    clamps.append({"type": "human_review", "strength": 1.0, "reason": l2_reason, "before": "APPLY", "after": "HOLD_REVIEW"})
                if level == 1 and not clamps:
                    l1_reason = engine_result.get("escalation_driver") or reason
                    l1_type = _l1_clamp_type_from_driver(l1_reason)
                    clamps.append({"type": l1_type, "strength": 1.0, "reason": l1_reason, "before": "APPLY", "after": "APPLY_CLAMPED"})
                packet["clamps"] = clamps
                packet["evidence_status"] = evidence_status
                packet["diff_fetch_latency_ms"] = diff_fetch_latency_ms
                if evidence and isinstance(evidence, dict):
                    d = evidence.get("diff") or ""
                    packet["diff_length"] = len(d) if isinstance(d, str) else 0
                    packet["diff_excerpt"] = (d[:300] if isinstance(d, str) else str(d)[:300])
                else:
                    packet["diff_length"] = None
                    packet["diff_excerpt"] = None
                mdm = packet.setdefault("mdm", {})
                mdm["reason"] = reason_for_ui
                mdm["engine_reason"] = engine_reason
                mdm["core_level"] = engine_result.get("escalation", 0)
                mdm["confidence"] = engine_result.get("confidence")
                mdm["confidence_internal"] = engine_result.get("confidence_internal")
                mdm["confidence_external"] = engine_result.get("confidence_external")
                mdm["confidence_used"] = engine_result.get("confidence_used")
                mdm["confidence_source"] = engine_result.get("confidence_source")
                mdm["constraint_margin"] = engine_result.get("constraint_margin")
                mdm["uncertainty"] = engine_result.get("uncertainty")
                mdm["temporal_drift"] = engine_result.get("temporal_drift")
                mdm["selection_reason"] = engine_result.get("selection_reason")
                mdm["escalation_driver"] = engine_result.get("escalation_driver")
                mdm["escalation_drivers"] = engine_result.get("escalation_drivers")
                mdm["escalation_base"] = engine_result.get("escalation_base")
                mdm["self_regulation"] = engine_result.get("self_regulation")
                mdm["action"] = engine_result.get("action")
                mdm["raw_action"] = engine_result.get("raw_action")
                mdm["J"] = engine_result.get("J")
                mdm["H"] = engine_result.get("H")
                mdm["worst_H"] = engine_result.get("worst_H")
                mdm["worst_J"] = engine_result.get("worst_J")
                mdm["input_quality"] = engine_result.get("input_quality")
                mdm["evidence_consistency"] = engine_result.get("evidence_consistency")
                mdm["frontier_size"] = engine_result.get("frontier_size")
                mdm["pareto_gap"] = engine_result.get("pareto_gap")
                mdm["driver_history_len"] = engine_result.get("driver_history_len")
                mdm["drift_driver_alarm"] = engine_result.get("drift_driver_alarm")
                mdm["missing_fields"] = engine_result.get("missing_fields")
                mdm["valid_candidate_count"] = engine_result.get("valid_candidate_count")
                mdm["invalid_reason_counts"] = engine_result.get("invalid_reason_counts")
                mdm["state_hash"] = engine_result.get("state_hash")
                mdm["config_hash"] = engine_result.get("config_hash")
                if wiki_ores_flag_override:
                    mdm["level"] = 2
                    mdm["escalation_driver"] = "wiki:ores_flag_disagree"
                    mdm["escalation_drivers"] = ["wiki:ores_flag_disagree"]
                try:
                    callback(packet)
                    LIVE_STATUS["packets_sent"] = LIVE_STATUS.get("packets_sent", 0) + 1
                except Exception:
                    pass
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            LIVE_STATUS["error"] = str(e)[:200]
            LIVE_STATUS["connected"] = False
            time.sleep(backoff_sec)
            backoff_sec = min(backoff_sec * 1.5, MAX_BACKOFF)
            continue
    return


def main(sample_every_n: int = 25, jsonl_path: Optional[str] = None):
    run_id = str(uuid.uuid4())
    run_ctx = get_run_context(run_id)
    seen_ids: set = set()
    seen_ids_max = 10000
    last_msg_time: Optional[float] = None
    print(f"[RUN] {run_id} | {EVENTSTREAM_URL}")
    if jsonl_path:
        stem, ext = os.path.splitext(jsonl_path)
        jsonl_path = f"{stem}_{run_ctx['config_profile']}{ext}"
        print(f"[JSONL] {jsonl_path}")
    print("Ctrl+C ile durdur.\n")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    resp = session.get(EVENTSTREAM_URL, stream=True, timeout=30)
    if resp.status_code != 200:
        print(f"SSE connection failed: {resp.status_code}")
        return
    client = SSEClient(resp)
    events = client.events()
    i = 0
    jsonl_file = None
    if jsonl_path:
        jsonl_file = open(jsonl_path, "a", encoding="utf-8")

    cus_history_main: list = []
    try:
        for msg in events:
            if getattr(msg, "event", None) != "message" or not getattr(msg, "data", None):
                continue
            try:
                event = json.loads(msg.data)
            except Exception:
                continue
            if event.get("meta", {}).get("domain") == "canary":
                continue
            if event.get("server_name") != "en.wikipedia.org":
                continue
            if event.get("type") not in ("edit", "new"):
                continue
            i += 1
            if i % sample_every_n != 0:
                continue

            rev = None
            if isinstance(event.get("revision"), dict):
                rev = event["revision"].get("new")
            rev = rev or event.get("rev_id") or event.get("id")
            if not rev:
                continue
            meta = event.get("meta") or {}
            source_event_id = meta.get("id") or f"{event.get('server_name', '')}:{rev}:{meta.get('dt', '')}"
            if source_event_id in seen_ids:
                continue
            seen_ids.add(source_event_id)
            if len(seen_ids) > seen_ids_max:
                seen_ids = set(list(seen_ids)[seen_ids_max // 2 :])
            msg_time = time.time()
            sse_wait_ms = round((msg_time - last_msg_time) * 1000, 2) if last_msg_time is not None else None
            last_msg_time = msg_time

            t0 = time.time()
            ext = fetch_ores_scores(int(rev))
            if not ext or ext.get("decision") is None:
                continue
            t_mdm_start = time.time()
            payload = build_mdm_input(event, ext)
            payload["context"]["cus_history"] = cus_history_main
            engine_result = audit_with_mdm(payload)
            cus_history_main = payload["context"].get("cus_history", cus_history_main)
            mdm_latency_ms = round((time.time() - t_mdm_start) * 1000, 2)
            latency_ms = round((time.time() - t0) * 1000, 2)
            level = engine_result.get("escalation", 0)
            ores_d_main = ext.get("decision") or "ALLOW"
            wiki_ores_flag_override_main = ores_d_main == "FLAG" and level == 0
            if wiki_ores_flag_override_main:
                level = 2
            reason = engine_result.get("reason", "ok")
            soft_clamp = engine_result.get("soft_safe_applied", False)
            external = {
                "decision": ext.get("decision"),
                "p_damaging": ext.get("p_damaging"),
                "p_goodfaith": ext.get("p_goodfaith"),
                "model": ext.get("model", "ores damaging|goodfaith"),
                "threshold": 0.5,
                "http_status": ext.get("http_status"),
                "latency_ms": ext.get("latency_ms"),
                "error": ext.get("error"),
                "ores_cache_hit": ext.get("ores_cache_hit", False),
                "ores_retry_count": ext.get("ores_retry_count", 0),
                "ores_backoff_ms": ext.get("ores_backoff_ms"),
            }
            input_data = {
                "title": payload["context"].get("title", ""),
                "user": payload["context"].get("user", ""),
                "revid": ext.get("revid"),
                "comment": payload["context"].get("comment", ""),
                "state_snapshot": payload["state"],
            }
            evidence = None
            evidence_status = "NA"
            diff_fetch_latency_ms = None
            rev_old = event.get("revision", {}).get("old") if isinstance(event.get("revision"), dict) else None
            if level == 2:
                t_diff = time.time()
                try:
                    evidence = fetch_wiki_diff(rev_old, ext.get("revid"))
                    evidence_status = "OK" if evidence and evidence.get("diff") else "MISSING"
                    diff_fetch_latency_ms = round((time.time() - t_diff) * 1000, 2)
                except Exception:
                    evidence_status = "ERROR"
            review = {"status": "pending"} if level == 2 else {}
            ts = time.time()
            packet = build_decision_packet(
                run_id=run_id,
                ts=ts,
                source="wikimedia_recentchange",
                entity_id=payload["context"].get("entity_id", ""),
                external=external,
                input_data=input_data,
                engine_result=engine_result,
                evidence=evidence,
                review=review,
            )
            packet["schema_version"] = SCHEMA_VERSION
            packet["adapter_version"] = ADAPTER_VERSION
            packet["source_event_id"] = source_event_id
            packet["config_profile"] = run_ctx["config_profile"]
            packet["git_commit"] = run_ctx["git_commit"]
            packet["host"] = run_ctx["host"]
            packet["session_id"] = run_ctx["session_id"]
            packet["latency_ms"] = latency_ms
            packet["mdm_latency_ms"] = mdm_latency_ms
            packet["sse_wait_ms"] = sse_wait_ms
            packet["ores_cache_hit"] = ext.get("ores_cache_hit", False)
            packet["ores_retry_count"] = ext.get("ores_retry_count", 0)
            packet["ores_backoff_ms"] = ext.get("ores_backoff_ms")
            packet["mdm_input_risk"] = payload["state"].get("risk")
            state_json = json.dumps(payload["state"], sort_keys=True)
            packet["mdm_input_state_hash"] = hashlib.sha256(state_json.encode()).hexdigest()[:16]
            packet["final_action"] = "APPLY" if level == 0 else ("APPLY_CLAMPED" if level == 1 else "HOLD_REVIEW")
            packet["final_action_reason"] = "wiki:ores_flag_disagree" if wiki_ores_flag_override_main else (engine_result.get("escalation_driver") or reason)
            packet["mismatch"] = (ores_d_main == "ALLOW" and level in (1, 2)) or (ores_d_main == "FLAG" and level == 0)
            clamps = []
            if soft_clamp:
                clamps.append({"type": "soft_safe", "strength": 1.0, "reason": reason, "before": "APPLY", "after": "APPLY_CLAMPED"})
            if level == 2:
                l2_reason_main = "wiki:ores_flag_disagree" if wiki_ores_flag_override_main else reason
                clamps.append({"type": "human_review", "strength": 1.0, "reason": l2_reason_main, "before": "APPLY", "after": "HOLD_REVIEW"})
            if level == 1 and not clamps:
                l1_reason = engine_result.get("escalation_driver") or reason
                l1_type = _l1_clamp_type_from_driver(l1_reason)
                clamps.append({"type": l1_type, "strength": 1.0, "reason": l1_reason, "before": "APPLY", "after": "APPLY_CLAMPED"})
            packet["clamps"] = clamps
            packet["evidence_status"] = evidence_status
            packet["diff_fetch_latency_ms"] = diff_fetch_latency_ms
            if evidence and isinstance(evidence, dict):
                d = evidence.get("diff") or ""
                packet["diff_length"] = len(d) if isinstance(d, str) else 0
                packet["diff_excerpt"] = (d[:300] if isinstance(d, str) else str(d)[:300])
            else:
                packet["diff_length"] = None
                packet["diff_excerpt"] = None
            mdm = packet.setdefault("mdm", {})
            mdm["confidence"] = engine_result.get("confidence")
            mdm["confidence_internal"] = engine_result.get("confidence_internal")
            mdm["confidence_external"] = engine_result.get("confidence_external")
            mdm["confidence_used"] = engine_result.get("confidence_used")
            mdm["confidence_source"] = engine_result.get("confidence_source")
            mdm["constraint_margin"] = engine_result.get("constraint_margin")
            mdm["selection_reason"] = engine_result.get("selection_reason")
            mdm["escalation_driver"] = engine_result.get("escalation_driver")
            mdm["escalation_drivers"] = engine_result.get("escalation_drivers")
            mdm["escalation_base"] = engine_result.get("escalation_base")
            mdm["temporal_drift"] = engine_result.get("temporal_drift")
            mdm["uncertainty"] = engine_result.get("uncertainty")
            mdm["action"] = engine_result.get("action")
            mdm["raw_action"] = engine_result.get("raw_action")
            mdm["J"] = engine_result.get("J")
            mdm["H"] = engine_result.get("H")
            mdm["worst_H"] = engine_result.get("worst_H")
            mdm["worst_J"] = engine_result.get("worst_J")
            mdm["input_quality"] = engine_result.get("input_quality")
            mdm["evidence_consistency"] = engine_result.get("evidence_consistency")
            mdm["frontier_size"] = engine_result.get("frontier_size")
            mdm["pareto_gap"] = engine_result.get("pareto_gap")
            mdm["driver_history_len"] = engine_result.get("driver_history_len")
            mdm["drift_driver_alarm"] = engine_result.get("drift_driver_alarm")
            mdm["missing_fields"] = engine_result.get("missing_fields")
            mdm["valid_candidate_count"] = engine_result.get("valid_candidate_count")
            mdm["invalid_reason_counts"] = engine_result.get("invalid_reason_counts")
            mdm["state_hash"] = engine_result.get("state_hash")
            mdm["config_hash"] = engine_result.get("config_hash")
            if wiki_ores_flag_override_main:
                mdm["level"] = 2
                mdm["escalation_driver"] = "wiki:ores_flag_disagree"
                mdm["escalation_drivers"] = ["wiki:ores_flag_disagree"]
            if jsonl_file:
                jsonl_file.write(json.dumps(packet, ensure_ascii=False) + "\n")
                jsonl_file.flush()

            title = input_data.get("title", "")[:50]
            user = input_data.get("user", "")
            # Windows konsol encoding (cp1254 vb.) için güvenli
            safe = lambda s: (s or "").encode("ascii", "replace").decode("ascii")
            print(
                f"[{time.strftime('%H:%M:%S')}] "
                f"ORES(decision={ext.get('decision')}, p_dmg={ext.get('p_damaging', 0):.3f}) | "
                f"MDM(L{level}, clamp={soft_clamp}, reason={reason}) | "
                f"{safe(title)} | {safe(user)}"
            )
    finally:
        if jsonl_file:
            jsonl_file.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Live Wiki audit: EventStreams + ORES + MDM")
    ap.add_argument("--sample-every", type=int, default=25, help="Her N event'te bir işle")
    ap.add_argument("--jsonl", type=str, default=None, help="Decision Packet JSONL dosya yolu")
    args = ap.parse_args()
    main(sample_every_n=args.sample_every, jsonl_path=args.jsonl)
