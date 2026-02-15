# MDM — Canlı Akış Denetim Dashboard / Live Audit Dashboard
# Veriler canlı akar; grafikler karar dağılımı ve gecikmeyi gösterir. EN/TR.

import importlib.util
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from mdm_engine.audit_spec import get_level_spec, decision_packet_to_flat_row, decision_packet_to_csv_row
except ImportError:
    try:
        from ami_engine.audit_spec import get_level_spec, decision_packet_to_flat_row, decision_packet_to_csv_row
    except ImportError:
        def get_level_spec(level: int) -> Dict:
            return {"label": f"L{level}", "short": "", "dashboard_badge": f"L{level}"}
        def decision_packet_to_flat_row(packet: Dict) -> Dict:
            inp = packet.get("input", {}); ext = packet.get("external", {}); mdm = packet.get("mdm", {})
            return {
                "time": packet.get("ts"), "title": inp.get("title", ""), "user": inp.get("user", ""),
                "revid": inp.get("revid", ""), "external_decision": ext.get("decision", ""),
                "p_damaging": ext.get("p_damaging"), "mdm_level": mdm.get("level", 0),
                "clamp": mdm.get("soft_clamp", False), "reason": mdm.get("reason", ""),
                "final_action": packet.get("final_action", ""), "mismatch": packet.get("mismatch", False),
                "run_id": packet.get("run_id", ""), "latency_ms": packet.get("latency_ms"),
            }
        def decision_packet_to_csv_row(packet: Dict) -> Dict:
            return decision_packet_to_flat_row(packet)

# Bilingual strings / Çift dilli metinler (tüm arayüz metinleri)
TEXTS = {
    "en": {
        "title": "MDM",
        "title_full": "Model Oversight Engine",
        "badge": "Live audit",
        "sidebar_data": "Data",
        "sidebar_section": "Section",
        "start_live": "Start live stream",
        "stop_live": "Stop live stream",
        "live_running": "Live stream running",
        "live_stopped": "Stopped",
        "upload_jsonl": "Or load JSONL file",
        "events": "Events",
        "external": "FLAG / ALLOW",
        "avg_latency": "Avg latency (ms)",
        "last_latency": "Last (ms)",
        "tab_monitor": "Live Monitor",
        "tab_detail": "Decision Detail",
        "tab_review": "Review Queue",
        "tab_search": "Search & Audit",
        "no_data": "No data yet. Click **Start live stream** to connect to Wikipedia EventStreams + ORES + MDM.",
        "chart_levels": "Decision levels (L0 auto, L1 soft clamp, L2 human review)",
        "chart_events": "Level of last 50 decisions over time",
        "chart_latency": "Response time per decision (ms)",
        "chart_mismatch": "Wikipedia risk (FLAG/ALLOW) vs our level (L0/L1/L2)",
        "chart_pdamage_level": "Risk score vs level (calibration)",
        "chart_reason_breakdown": "Why decisions went to human review (L1/L2)",
        "chart_as_norm_histogram": "as_norm (internal calibration)",
        "chart_drift_driver": "Drift trigger (internal)",
        "calibration_section": "Calibration (escalation_driver, as_norm, drift_driver)",
        "filter_mismatch": "Only mismatches (ORES≠MDM)",
        "detail_select": "Select a row in **Live Monitor** or **Search** to see details.",
        "review_pending": "Pending L2",
        "review_none": "No pending L2.",
        "review_why_here": "**Why you're here:** A change was marked for human review (e.g. Wikipedia flagged it as suspicious, or our system asked for a second opinion). Your job is to look at what was changed and decide: **Approve** if it's fine, **Reject** if it's harmful or should be reverted.",
        "review_what_to_do": "Your decision",
        "review_approve_means": "**Approve** — The change is OK; no action needed. We will not revert it.",
        "review_reject_means": "**Reject** — The change is harmful, vandalism, or should be reverted. We treat it as needing human or automated revert.",
        "review_change_label": "What changed (diff)",
        "review_diff_unavailable": "Diff not available. Open the Wikipedia link above to see the change, then Approve or Reject.",
        "review_diff_legend": "(−) removed or changed  ·  (+) added",
        "review_open_wiki": "Open on Wikipedia",
        "review_edit_summary": "Edit summary",
        "review_item_ores": "Wikipedia (ORES) flagged this edit as suspicious. We send it to you so a human can confirm: real problem (Reject) or false alarm (Approve).",
        "review_item_mdm": "Our system asked for human review (e.g. low confidence or safety threshold). Check the change and Approve or Reject.",
        "filter_level": "Level",
        "filter_ext": "External decision",
        "filter_profile": "Config profile",
        "search_result": "Result",
        "search_sample_l0": "L0 sampling (1 per 100)",
        "download_csv": "Download CSV (full: ORES + MDM + clamp/model)",
        "language": "Language",
        "sample_every": "Sample every N events",
        "open_detail": "Open detail",
        "approve": "Approve",
        "reject": "Reject",
        "approve_tr": "Approve",
        "reject_tr": "Reject",
        "saved": "Saved",
        "category": "Category",
        "note": "Note",
        "see_detail_tab": "See **Decision Detail** for full view.",
        "packets_label": "packets",
        "detail_explain": "Explain",
        "detail_external": "External decision",
        "detail_signals": "Signals",
        "detail_content": "Content",
        "detail_actions": "Actions",
        "detail_l2_resolve_in_review": "Use the **Review Queue** tab to Approve or Reject this item. (Only one set of buttons to avoid confusion.)",
        "tab_quality": "Quality",
        "quality_override_rate": "L2 override rate (Reject %)",
        "quality_category_dist": "Category distribution",
        "quality_reason_heatmap": "Reason → Override (which mdm_reason leads to Reject)",
        "quality_no_reviews": "No review log yet. Resolve L2 items (Approve/Reject) to see metrics.",
        "core_signals": "Core / Quality signals",
        "core_missing_fields": "Missing fields",
        "core_valid_candidates": "Valid candidates",
        "core_invalid_reasons": "Invalid reason counts",
        "core_input_quality": "Input quality",
        "core_evidence_consistency": "Evidence consistency",
        "core_frontier_size": "Pareto frontier size",
        "core_pareto_gap": "Pareto gap",
        "core_drift_applied": "Drift applied",
        "core_selection_reason": "Selection reason",
        "core_state_hash": "State hash",
        "core_config_hash": "Config hash",
        "engine_reason": "Engine reason",
        "evidence_status": "Evidence status",
        "compare_link": "Compare on Wikipedia",
        "chart_guide_levels": "How many decisions were automatic (L0), soft-limited (L1), or sent to human review (L2). Use this to see if too many or too few go to review.",
        "chart_guide_events": "How the last 50 decisions were classified. Lets you see if there are sudden spikes in human review or if the flow is stable.",
        "chart_guide_latency": "How many milliseconds each decision took. If this goes up a lot, the system or network may be under load.",
        "chart_guide_mismatch": "Compares Wikipedia’s risk label (FLAG = risky, ALLOW = ok) with our level. Helps you see when we agree or disagree with Wikipedia.",
        "chart_guide_pdamage": "Technical: how risk score maps to L0/L1/L2. For tuning calibration.",
        "chart_guide_reason": "For decisions that needed human review: which reason triggered it (e.g. low confidence, rule hit). Helps improve rules.",
        "chart_guide_as_norm": "Distribution of as_norm (action selector soft-threshold). Helps tune AS_SOFT_THRESHOLD and diagnose L1 soft clamps.",
        "chart_guide_drift": "How often temporal drift was driven by warmup vs mean/delta. Useful to see early or unstable drift triggers.",
        "chart_guide_quality_cat": "How reviewers categorized L2 decisions (e.g. false positive, correct escalation). Informs policy and calibration.",
        "chart_guide_quality_heatmap": "For each mdm_reason, how many L2 items were Approved vs Rejected. Shows which reasons lead to overrides.",
        "advanced_calibration_expander": "Advanced: Calibration & diagnostics",
        "advanced_calibration_details": "Details",
        "advanced_calibration_caption": "For experts: as_norm, drift_driver, and risk-score vs level. Used to tune thresholds.",
        "search_audit_explanation": "**Search & Audit:** Search and filter decision packets by level (L0/L1/L2), user, or title. Select a row to open it in Decision Detail. Use this to inspect past decisions or find specific edits.",
        "metric_l2_ratio": "Human review %",
        "info_meaning": "Meaning",
        "info_purpose": "Why you look at it",
        "info_example": "Example",
        "info_levels_meaning": "This chart shows how the last 50 decisions were classified: L0 (fully automatic), L1 (system applied a soft limit but no human needed), or L2 (sent to a human for review).",
        "info_levels_purpose": "You look at it to see whether most decisions are automatic or whether too many are going to human review. A healthy balance depends on your policy: e.g. you might want most as L0 with a small share of L2.",
        "info_levels_example": "Example: if the pie is mostly L2, almost every decision is waiting for a human — you may want to relax thresholds or add capacity. If it’s almost all L0, the system is very permissive.",
        "info_events_meaning": "Each point is one of the last 50 decisions; the height shows its level (0, 1, or 2). So you see the sequence of levels over time.",
        "info_events_purpose": "You look at it to spot patterns: e.g. a sudden run of L2s, or a switch from mostly L0 to L1. It helps you see if the stream is stable or if something changed.",
        "info_events_example": "Example: if the line is flat at 0 and then jumps to 2 for several points, a burst of edits may have triggered more human review; you can then check those events in the table.",
        "info_latency_meaning": "This chart shows how many milliseconds the system took to produce each of the last 50 decisions. One point per decision.",
        "info_latency_purpose": "You look at it to see if the system is fast enough. If latency grows or stays high, the service or network might be overloaded and users will wait longer.",
        "info_latency_example": "Example: if values are usually under 500 ms and suddenly go above 2000 ms, something may be wrong (e.g. backend slow or network issue).",
        "info_mismatch_meaning": "Wikipedia’s tool (ORES) labels each edit as ALLOW (low risk) or FLAG (needs attention). We then assign a level L0, L1, or L2. This table counts how many times each combination happened.",
        "info_mismatch_purpose": "You look at it to see when we agree or disagree with Wikipedia. E.g. many FLAG + L0 means we often treat “risky” edits as automatic; many ALLOW + L2 means we escalate even when Wikipedia said low risk.",
        "info_mismatch_example": "Example: if most FLAG edits are in the L2 column, we are aligning with Wikipedia. If most FLAG are L0, we might be too permissive and could tighten calibration.",
        "info_reason_meaning": "For decisions that went to L1 or L2, the system recorded a reason (e.g. low confidence, rule triggered). This chart shows how often each reason occurred.",
        "info_reason_purpose": "You look at it to understand why decisions need human review. That helps you improve rules or thresholds so that the right cases are escalated and others stay automatic.",
        "info_reason_example": "Example: if ‘low_confidence’ is the top reason, you might adjust the confidence threshold or improve input quality so that fewer decisions are escalated for that reason.",
        "info_as_norm_meaning": "as_norm is an internal signal: how clearly the best action outscored the second (action selector). Values near 0 mean the model could not pick a clear winner.",
        "info_as_norm_purpose": "You look at it to tune AS_SOFT_THRESHOLD and to see why L1 soft clamps trigger. If as_norm is always near 0, the system often hesitates between actions.",
        "info_as_norm_example": "Example: if the histogram is mostly in the 0.3–0.5 range, the selector is fairly decisive; if it is piled near 0, consider relaxing AS_SOFT_THRESHOLD or improving inputs.",
        "info_drift_meaning": "Each bar is how often temporal drift was triggered by that driver: warmup (not enough history yet), mean (CUS mean high), delta (CUS change high), or none.",
        "info_drift_purpose": "You look at it to see if drift is firing too often (e.g. always warmup) or too little. Helps set CUS_MEAN_THRESHOLD and DRIFT_MIN_HISTORY.",
        "info_drift_example": "Example: if almost all bars are 'warmup', history might be too short; if 'mean' dominates, CUS_MEAN_THRESHOLD may be too low.",
        "info_pdamage_meaning": "Each point is one decision: x = ORES risk score (p_damaging), y = MDM level (L0/L1/L2). Shows how risk score maps to your levels.",
        "info_pdamage_purpose": "You look at it to check calibration: e.g. low risk scores should often be L0; high risk may be L1 or L2. If everything is L1, thresholds may need tuning.",
        "info_pdamage_example": "Example: if points with p_damaging < 0.2 are all L1, the engine may be too cautious; consider relaxing H_MAX or confidence thresholds.",
        "info_quality_cat_meaning": "After human review, each L2 decision can be given a category (e.g. false_positive, true_positive). This chart shows how many fall into each category.",
        "info_quality_cat_purpose": "You look at it to see whether most L2s are false alarms or correct escalations. That informs policy and whether to relax or tighten thresholds.",
        "info_quality_cat_example": "Example: if most are false_positive, the system may be over-escalating; if most are true_positive, escalation is doing its job.",
        "info_quality_heatmap_meaning": "For each mdm_reason (why the item went to L2), the chart shows how many reviewers Approved vs Rejected. So you see which reasons lead to overrides.",
        "info_quality_heatmap_purpose": "You look at it to see which escalation reasons reviewers often reject (override) vs accept. That helps you adjust rules or thresholds for those reasons.",
        "info_quality_heatmap_example": "Example: if one reason has many Rejects, that driver may be too aggressive; consider tuning that rule or threshold.",
    },
    "tr": {
        "title": "MDM",
        "title_full": "Model Denetim Motoru",
        "badge": "Canlı denetim",
        "sidebar_data": "Veri",
        "sidebar_section": "Bölüm",
        "start_live": "Canlı akışı başlat",
        "stop_live": "Canlı akışı durdur",
        "live_running": "Canlı akış açık",
        "live_stopped": "Durduruldu",
        "upload_jsonl": "Veya JSONL dosyası yükle",
        "events": "Olay",
        "external": "FLAG / ALLOW",
        "avg_latency": "Ort. gecikme (ms)",
        "last_latency": "Son (ms)",
        "tab_monitor": "Canlı İzleme",
        "tab_detail": "Karar Detayı",
        "tab_review": "İnceleme Kuyruğu",
        "tab_search": "Ara & Denetle",
        "no_data": "Henüz veri yok. **Canlı akışı başlat** ile Wikipedia EventStreams + ORES + MDM bağlanır.",
        "chart_levels": "Karar seviyeleri (L0 otomatik, L1 yumuşak fren, L2 insan incelemesi)",
        "chart_events": "Son 50 kararın seviyesi (zamana göre)",
        "chart_latency": "Her kararın yanıt süresi (ms)",
        "chart_mismatch": "Wikipedia riski (FLAG/ALLOW) ile bizim seviyemiz (L0/L1/L2)",
        "chart_pdamage_level": "Risk skoru vs seviye (kalibrasyon)",
        "chart_reason_breakdown": "İnsan incelemesine giden kararların gerekçeleri (L1/L2)",
        "chart_as_norm_histogram": "as_norm (dahili kalibrasyon)",
        "chart_drift_driver": "Drift tetikleyici (dahili)",
        "calibration_section": "Kalibrasyon (escalation_driver, as_norm, drift_driver)",
        "filter_mismatch": "Sadece uyumsuzlar (ORES≠MDM)",
        "detail_select": "Detay için **Canlı İzleme** veya **Ara** tablosunda bir satır seçin.",
        "review_pending": "Bekleyen L2",
        "review_none": "Bekleyen L2 yok.",
        "review_why_here": "**Neden buradasınız?** Bir değişiklik insan incelemesine alındı (ör. Wikipedia şüpheli buldu veya sistem ikinci görüş istedi). Sizin işiniz: ne değiştiğine bakıp **Onayla** (sorun yok) veya **Red** (zararlı / geri alınsın) demek.",
        "review_what_to_do": "Kararınız",
        "review_approve_means": "**Onayla** — Değişiklik uygun; işlem gerekmez. Geri alınmayacak.",
        "review_reject_means": "**Red** — Değişiklik zararlı, vandalizm veya geri alınmalı. İnsan veya otomatik geri alma gerektiği kabul edilir.",
        "review_change_label": "Ne değişti (diff)",
        "review_diff_unavailable": "Diff yok. Değişikliği görmek için yukarıdaki Wikipedia linkini açın, sonra Onayla veya Red deyin.",
        "review_diff_legend": "(−) kaldırılan/değişen  ·  (+) eklenen",
        "review_open_wiki": "Wikipedia'da aç",
        "review_edit_summary": "Edit özeti",
        "review_item_ores": "Wikipedia (ORES) bu düzenlemeyi şüpheli buldu. İnsan gözü onaylasın diye size gönderiyoruz: gerçekten sorun mu (Red) yoksa yanlış alarm mı (Onayla).",
        "review_item_mdm": "Sistemimiz insan incelemesi istedi (örn. düşük güven veya güvenlik eşiği). Değişikliğe bakıp Onayla veya Red deyin.",
        "filter_level": "Seviye",
        "filter_ext": "Dış karar",
        "filter_profile": "Profil",
        "search_result": "Sonuç",
        "search_sample_l0": "L0 örnekleme (100'de 1)",
        "download_csv": "CSV indir (tam: ORES + MDM + frenleme/model)",
        "language": "Dil",
        "sample_every": "Her N olayda örnekle",
        "open_detail": "Detay aç",
        "approve": "Onayla",
        "reject": "Red",
        "approve_tr": "Onayla",
        "reject_tr": "Red",
        "saved": "Kaydedildi",
        "category": "Kategori",
        "note": "Not",
        "see_detail_tab": "Detay için **Karar Detayı** sekmesine geçin.",
        "packets_label": "paket",
        "detail_explain": "Açıklama",
        "detail_external": "Dış karar",
        "detail_signals": "Sinyaller",
        "detail_content": "İçerik",
        "detail_actions": "Aksiyonlar",
        "detail_l2_resolve_in_review": "Onayla/Red kararını **Review Queue** sekmesinden verin. (Tek yerde buton, karışıklık olmasın.)",
        "tab_quality": "Kalite",
        "quality_override_rate": "L2 override oranı (Red %)",
        "quality_category_dist": "Kategori dağılımı",
        "quality_reason_heatmap": "Gerekçe → Red (hangi mdm_reason Red üretiyor)",
        "quality_no_reviews": "Henüz inceleme kaydı yok. L2 kararlarını verin (Onayla/Red) metrikleri görmek için.",
        "core_signals": "Çekirdek / Kalite sinyalleri",
        "core_missing_fields": "Eksik alanlar",
        "core_valid_candidates": "Geçerli aday sayısı",
        "core_invalid_reasons": "Geçersiz neden sayıları",
        "core_input_quality": "Giriş kalitesi",
        "core_evidence_consistency": "Kanıt tutarlılığı",
        "core_frontier_size": "Pareto frontier boyutu",
        "core_pareto_gap": "Pareto gap",
        "core_drift_applied": "Drift uygulandı",
        "core_selection_reason": "Seçim gerekçesi",
        "core_state_hash": "State hash",
        "core_config_hash": "Config hash",
        "engine_reason": "Motor gerekçesi",
        "evidence_status": "Kanıt durumu",
        "compare_link": "Wikipedia'da karşılaştır",
        "chart_guide_levels": "Kaç kararın otomatik (L0), yumuşak frenli (L1) veya insan incelemesine gittiğini (L2) gösterir. İncelemeye giden oranın çok mu az mı olduğunu anlamak için kullanın.",
        "chart_guide_events": "Son 50 kararın nasıl sınıflandığı. İnsan incelemesinde ani artış var mı, akış kararlı mı görebilirsiniz.",
        "chart_guide_latency": "Her karar kaç milisaniye sürdü. Bu değer çok yükselirse sistem veya ağ yük altında olabilir.",
        "chart_guide_mismatch": "Wikipedia’nın risk etiketi (FLAG = riskli, ALLOW = sorunsuz) ile bizim seviyemizi karşılaştırır. Ne zaman aynı fikirde olduğumuzu, ne zaman farklı karar verdiğimizi gösterir.",
        "chart_guide_pdamage": "Teknik: risk skorunun L0/L1/L2’ye nasıl eşlendiği. Kalibrasyon ayarı için.",
        "chart_guide_reason": "İnsan incelemesine giden kararlarda: hangi gerekçe tetikledi (örn. düşük güven, kural tetiklemesi). Kuralları iyileştirmek için kullanın.",
        "chart_guide_as_norm": "as_norm (aksiyon seçici yumuşak eşik) dağılımı. AS_SOFT_THRESHOLD ayarı ve L1 yumuşak fren teşhisi için faydalıdır.",
        "chart_guide_drift": "Zamansal drift'in ne sıklıkla warmup vs mean/delta ile tetiklendiği. Erken veya kararsız drift tetikleyicilerini görmek için kullanın.",
        "chart_guide_quality_cat": "İnceleyicilerin L2 kararları nasıl kategorize ettiği (örn. yanlış pozitif, doğru yükseltme). Politika ve kalibrasyonu bilgilendirir.",
        "chart_guide_quality_heatmap": "Her mdm_reason için kaç L2 öğesinin Onaylandığı / Reddedildiği. Hangi gerekçelerin override'a yol açtığını gösterir.",
        "advanced_calibration_expander": "Gelişmiş: Kalibrasyon ve teşhis",
        "advanced_calibration_details": "Detaylar",
        "advanced_calibration_caption": "Uzmanlar için: as_norm, drift_driver ve risk skoru–seviye grafikleri. Eşik ayarlamada kullanılır.",
        "search_audit_explanation": "**Ara & Denetle:** Karar paketlerini seviye (L0/L1/L2), kullanıcı veya başlığa göre arayıp filtreleyin. Bir satır seçerek Karar Detayı'nda açın. Geçmiş kararları incelemek veya belirli düzenlemeleri bulmak için kullanın.",
        "metric_l2_ratio": "İnsan incelemesi %",
        "info_meaning": "Anlam",
        "info_purpose": "Görev (Neden inceliyorsun)",
        "info_example": "Örnek",
        "info_levels_meaning": "Bu grafik son 50 kararın nasıl sınıflandığını gösterir: L0 (tam otomatik), L1 (sistem yumuşak fren uyguladı ama insan gerekmedi), L2 (insan incelemesine gönderildi).",
        "info_levels_purpose": "Çoğu kararın otomatik mi gittiğini yoksa çok fazlasının insan incelemesine mi gittiğini görmek için bakarsın. Sağlıklı denge politikanıza bağlıdır: örn. çoğunun L0, az bir kısmının L2 olmasını isteyebilirsiniz.",
        "info_levels_example": "Örnek: Pasta çoğunlukla L2 ise neredeyse her karar insan bekliyor demektir — eşikleri yumuşatabilir veya inceleme kapasitesi ekleyebilirsiniz. Neredeyse hepsi L0 ise sistem çok serbest davranıyor demektir.",
        "info_events_meaning": "Her nokta son 50 karardan biridir; yükseklik o kararın seviyesini (0, 1 veya 2) gösterir. Böylece zamana göre seviye sırasını görürsünüz.",
        "info_events_purpose": "Örüntüleri fark etmek için bakarsınız: örn. aniden peş peşe L2’ler veya çoğunlukla L0’dan L1’e geçiş. Akışın kararlı mı yoksa bir şeyin değiştiği mi anlaşılır.",
        "info_events_example": "Örnek: Çizgi 0’da düz gidip birkaç nokta 2’ye sıçrarsa, bir düzenleme patlaması daha fazla insan incelemesi tetiklemiş olabilir; tablodan o olayları inceleyebilirsiniz.",
        "info_latency_meaning": "Bu grafik son 50 kararın her biri için sistemin kaç milisaniye sürdüğünü gösterir. Karar başına bir nokta.",
        "info_latency_purpose": "Sistemin yeterince hızlı olup olmadığını görmek için bakarsınız. Gecikme artıyorsa veya sürekli yüksekse servis veya ağ yük altında olabilir, kullanıcılar daha uzun bekler.",
        "info_latency_example": "Örnek: Değerler genelde 500 ms altındayken aniden 2000 ms üstüne çıkarsa bir sorun olabilir (örn. arka uç yavaş veya ağ problemi).",
        "info_mismatch_meaning": "Wikipedia’nın aracı (ORES) her düzenlemeyi ALLOW (düşük risk) veya FLAG (dikkat gerekir) olarak etiketler. Biz de L0, L1 veya L2 seviyesi veriyoruz. Bu tablo her kombinasyonun kaç kez oluştuğunu sayar.",
        "info_mismatch_purpose": "Wikipedia ile ne zaman aynı fikirde olduğumuzu, ne zaman farklı karar verdiğimizi görmek için bakarsınız. Örn. çok FLAG + L0, “riskli” düzenlemeleri sık sık otomatik geçtiğimiz anlamına gelir; çok ALLOW + L2, Wikipedia düşük risk dediğinde bile yükselttiğimiz anlamına gelir.",
        "info_mismatch_example": "Örnek: FLAG’li düzenlemelerin çoğu L2 sütunundaysa Wikipedia ile uyumluyuz. FLAG’lerin çoğu L0’daysa fazla serbest kalıyor olabiliriz, kalibrasyonu sıkılaştırabiliriz.",
        "info_reason_meaning": "L1 veya L2’ye giden kararlar için sistem bir gerekçe kaydetti (örn. düşük güven, kural tetiklendi). Bu grafik her gerekçenin ne sıklıkta görüldüğünü gösterir.",
        "info_reason_purpose": "Kararların neden insan incelemesine gittiğini anlamak için bakarsınız. Böylece kuralları veya eşikleri iyileştirir, doğru vakalar yükselir, diğerleri otomatik kalır.",
        "info_reason_example": "Örnek: En sık gerekçe ‘düşük_güven’ ise güven eşiğini ayarlayabilir veya giriş kalitesini artırarak bu nedenle yükselen karar sayısını azaltabilirsiniz.",
        "info_as_norm_meaning": "as_norm dahili bir sinyal: en iyi aksiyonun ikinciden ne kadar net önde olduğu (aksiyon seçici). 0'a yakın değerler modelin net kazanan seçemediği anlamına gelir.",
        "info_as_norm_purpose": "AS_SOFT_THRESHOLD ayarını ve L1 yumuşak frenin neden tetiklendiğini görmek için bakarsınız. as_norm sürekli 0'a yakınsa sistem sık sık iki aksiyon arasında kalıyor demektir.",
        "info_as_norm_example": "Örnek: Histogram çoğunlukla 0,3–0,5 aralığındaysa seçici nispeten kararlı; 0'a yığılmışsa AS_SOFT_THRESHOLD'u gevşetmeyi veya girişleri iyileştirmeyi düşünün.",
        "info_drift_meaning": "Her çubuk, zamansal drift'in o tetikleyiciyle (warmup, mean, delta veya none) ne sıklıkla tetiklendiğini gösterir.",
        "info_drift_purpose": "Drift'in çok sık (örn. hep warmup) veya çok az tetiklenip tetiklenmediğini görmek için bakarsınız. CUS_MEAN_THRESHOLD ve DRIFT_MIN_HISTORY ayarına yardımcı olur.",
        "info_drift_example": "Örnek: Neredeyse tüm çubuklar 'warmup' ise geçmiş çok kısa olabilir; 'mean' baskınsa CUS_MEAN_THRESHOLD düşük kalıyor olabilir.",
        "info_pdamage_meaning": "Her nokta bir karar: x = ORES risk skoru (p_damaging), y = MDM seviyesi (L0/L1/L2). Risk skorunun seviyelere nasıl eşlendiğini gösterir.",
        "info_pdamage_purpose": "Kalibrasyonu kontrol etmek için bakarsınız: düşük risk skorları çoğunlukla L0 olmalı; yüksek risk L1 veya L2. Hepsi L1 ise eşikler ayarlanmalı.",
        "info_pdamage_example": "Örnek: p_damaging < 0,2 olan noktalar hep L1 ise motor fazla temkinli olabilir; H_MAX veya güven eşiklerini gevşetmeyi düşünün.",
        "info_quality_cat_meaning": "İnsan incelemesinden sonra her L2 kararına bir kategori verilebilir (örn. false_positive, true_positive). Bu grafik her kategoride kaç karar olduğunu gösterir.",
        "info_quality_cat_purpose": "L2'lerin çoğunun yanlış alarm mı yoksa doğru yükseltme mi olduğunu görmek için bakarsınız. Bu, politika ve eşikleri gevşetme/sıkılaştırma kararını bilgilendirir.",
        "info_quality_cat_example": "Örnek: Çoğu false_positive ise sistem fazla yükseltiyor olabilir; çoğu true_positive ise yükseltme işini yapıyor demektir.",
        "info_quality_heatmap_meaning": "Her mdm_reason (öğenin neden L2'ye gittiği) için grafik, kaç incelemenin Onayladığı / Reddettiğini gösterir. Hangi gerekçelerin override'a yol açtığını görürsünüz.",
        "info_quality_heatmap_purpose": "Hangi yükseltme gerekçelerinin sık Red (override) veya Onay aldığını görmek için bakarsınız. Bu, o gerekçelere göre kural veya eşik ayarlamanıza yardımcı olur.",
        "info_quality_heatmap_example": "Örnek: Bir gerekçe çok Red alıyorsa o driver fazla agresif olabilir; o kural veya eşiği gözden geçirin.",
    },
}

st.set_page_config(
    page_title="MDM Live Audit",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Header: MDM (Model Oversight Engine) büyük ve net */
    .mdm-header { display: flex; align-items: center; gap: 1rem; padding: 0.75rem 0 1rem 0; border-bottom: 2px solid rgba(0,0,0,.15); margin-bottom: 1.25rem; flex-wrap: wrap; }
    .mdm-title-block { display: flex; flex-direction: column; gap: 0.15rem; }
    .mdm-header h1 { margin: 0; font-size: 2.25rem; font-weight: 700; color: #0f172a; letter-spacing: -0.02em; line-height: 1.2; }
    .mdm-header .mdm-subtitle { font-size: 1.05rem; font-weight: 500; color: #475569; letter-spacing: 0.01em; }
    .mdm-header .badge { font-size: 0.7rem; padding: 0.25rem 0.6rem; background: #0ea5e9; color: white; border-radius: 999px; font-weight: 500; }
    /* Sekmeler: birbirinden ayrı, modern pill görünümü */
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; border-bottom: 1px solid rgba(0,0,0,.1); padding-bottom: 0; margin-bottom: 1rem; }
    .stTabs [data-baseweb="tab"] { padding: 0.5rem 1rem; border-radius: 8px 8px 0 0; margin-right: 2px; font-weight: 500; }
    .stTabs [data-baseweb="tab"]:first-child { margin-left: 0; }
    /* Dark theme: header ve sekme kontrastı */
    [data-theme="dark"] .main .block-container,
    [data-theme="dark"] .mdm-header,
    [data-theme="dark"] [data-testid="stMetricLabel"],
    [data-theme="dark"] [data-testid="stMetricValue"] {
        font-family: "Segoe UI", "SF Pro Text", system-ui, -apple-system, sans-serif;
    }
    [data-theme="dark"] .mdm-header h1 { color: #f8fafc; font-weight: 700; }
    [data-theme="dark"] .mdm-header .mdm-subtitle { color: #94a3b8; }
    [data-theme="dark"] .mdm-header { border-bottom-color: rgba(255,255,255,.2); }
    [data-theme="dark"] .stTabs [data-baseweb="tab-list"] { border-bottom-color: rgba(255,255,255,.15); }
    [data-theme="dark"] .stTabs [data-baseweb="tab"] { color: #94a3b8; }
    [data-theme="dark"] .stTabs [data-baseweb="tab"]:focus, [data-theme="dark"] .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #f8fafc; }
    [data-theme="dark"] .stMarkdown p, [data-theme="dark"] .stMarkdown li, [data-theme="dark"] label[data-testid="stWidgetLabel"] {
        color: #cbd5e1 !important;
    }
    [data-theme="dark"] [data-testid="stMetricLabel"] { color: #94a3b8 !important; font-weight: 500; }
    [data-theme="dark"] [data-testid="stMetricValue"] { color: #e2e8f0 !important; font-weight: 600; font-size: 1.2rem; }
    [data-theme="dark"] .stTabs [data-baseweb="tab"] { color: #94a3b8; }
    [data-theme="dark"] .stTabs [data-baseweb="tab"]:focus { color: #e2e8f0; }
    /* Sidebar: hem light hem dark'ta okunaklı */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); }
    [data-testid="stSidebar"] .stMarkdown { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] label { color: #94a3b8 !important; }
    [data-testid="stSidebar"] .stCaptionContainer { color: #94a3b8 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 0.25rem; border-bottom: 1px solid rgba(0,0,0,.08); }
    [data-theme="dark"] .stTabs [data-baseweb="tab-list"] { border-bottom-color: rgba(255,255,255,.08); }
    [data-testid="stMetricValue"] { font-size: 1.2rem; }
    /* Tema uyumu: kullanıcı Koyu seçerse ana alan koyu (Streamlit tema ile uyumlu) */
    [data-theme="dark"] .stDataFrame { background: rgba(15,23,42,.4); }
    [data-theme="dark"] .stExpander { background: rgba(15,23,42,.3); }
    /* Grafik başlığındaki bilgi (ℹ️) ikonunu mavi yap — sadece .chart-info-header içindekiler */
    .chart-info-header [data-testid="stExpander"] summary { color: #2563eb !important; }
    [data-theme="dark"] .chart-info-header [data-testid="stExpander"] summary { color: #60a5fa !important; }
    /* Sidebar radio option text kontrast */
    [data-testid="stSidebar"] div[role="radiogroup"] label span { color: #e2e8f0 !important; opacity: 1 !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] label { opacity: 1 !important; }
</style>
""", unsafe_allow_html=True)


def _t(key: str) -> str:
    lang = st.session_state.get("lang", "en")
    return TEXTS.get(lang, TEXTS["en"]).get(key, key)


def _chart_header_with_info(title_key: str, meaning_key: str, purpose_key: str, example_key: str, expander_key: str) -> None:
    """Grafik başlığı ve yanında tıklanabilir mavi ℹ️; tıklanınca popover (pop-up) ile Anlam, Görev, Örnek gösterir."""
    t = _t
    st.markdown('<div class="chart-info-header">', unsafe_allow_html=True)
    tit, info = st.columns([6, 1])
    with tit:
        st.markdown(f"**{t(title_key)}**")
    with info:
        popover = getattr(st, "popover", None)
        if popover:
            with popover("ℹ️"):
                st.markdown(f"**{t('info_meaning')}**  \n{t(meaning_key)}")
                st.markdown(f"**{t('info_purpose')}**  \n{t(purpose_key)}")
                st.markdown(f"**{t('info_example')}**  \n{t(example_key)}")
        else:
            with st.expander("ℹ️", expanded=False):
                st.markdown(f"**{t('info_meaning')}**  \n{t(meaning_key)}")
                st.markdown(f"**{t('info_purpose')}**  \n{t(purpose_key)}")
                st.markdown(f"**{t('info_example')}**  \n{t(example_key)}")
    st.markdown("</div>", unsafe_allow_html=True)


def _parse_schema_version(s: Any) -> Optional[tuple]:
    """Parse schema_version to (major, minor) or None. E.g. '2.0' -> (2, 0)."""
    if s is None:
        return None
    parts = str(s).strip().split(".", 1)
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        return (major, minor)
    except (ValueError, IndexError):
        return None


def _schema_v2_required(packets: List[Dict[str, Any]]) -> bool:
    """True if any packet is legacy: missing schema_version or schema_version < 2.0 (reject)."""
    min_ver = (2, 0)
    for p in packets:
        sv = _parse_schema_version(p.get("schema_version"))
        if sv is None or sv < min_ver:
            return True
    return False


def _append_review_log(packet: Dict, decision: str, category: str = "", note: str = "") -> None:
    """L2 review kararını kalıcı JSONL'e yazar (L2_override_rate / kategori / reason→override için)."""
    import os
    path = os.environ.get("MDM_REVIEW_LOG") or str(ROOT / "review_log.jsonl")
    entry = {
        "run_id": packet.get("run_id"),
        "ts": packet.get("ts"),
        "revid": packet.get("input", {}).get("revid"),
        "title": (packet.get("input", {}).get("title") or "")[:100],
        "user": packet.get("input", {}).get("user"),
        "mdm_level": packet.get("mdm", {}).get("level"),
        "mdm_reason": packet.get("final_action_reason") or packet.get("mdm", {}).get("escalation_driver") or packet.get("mdm", {}).get("reason", ""),
        "review_decision": decision,
        "review_category": category or "",
        "review_note": (note or "")[:500],
        "review_ts": time.time(),
    }
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _load_review_log() -> List[Dict[str, Any]]:
    """review_log.jsonl dosyasını okur (Kalite paneli için)."""
    import os
    path = os.environ.get("MDM_REVIEW_LOG") or str(ROOT / "review_log.jsonl")
    entries: List[Dict[str, Any]] = []
    try:
        if Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return entries


def _render_quality_panel(packets: List[Dict], t: callable) -> None:
    """Kalite: L2 override rate, kategori dağılımı, reason → override heatmap; Research: policy override + Core→Policy matrix."""
    entries = _load_review_log()
    resolved = [e for e in (entries or []) if e.get("review_decision") in ("approve", "reject")]
    if not resolved:
        st.info(t("quality_no_reviews"))
    else:
        rejects = sum(1 for e in resolved if e.get("review_decision") == "reject")
        override_rate = (rejects / len(resolved)) * 100.0
        st.metric(t("quality_override_rate"), f"{override_rate:.1f}%")
        st.caption(f"Reject: {rejects} / Approve: {len(resolved) - rejects} (n={len(resolved)})")

        # Kategori dağılımı
        _chart_header_with_info("quality_category_dist", "info_quality_cat_meaning", "info_quality_cat_purpose", "info_quality_cat_example", "info_quality_cat")
        from collections import Counter
        cats = Counter(e.get("review_category") or "" for e in resolved)
        cats = {k or "(empty)": v for k, v in cats.items()}
        if cats:
            fig_cat = go.Figure(data=[go.Bar(x=list(cats.keys()), y=list(cats.values()))])
            fig_cat.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=220)
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.caption("—")

        # Reason → Override heatmap: mdm_reason vs review_decision (approve/reject)
        _chart_header_with_info("quality_reason_heatmap", "info_quality_heatmap_meaning", "info_quality_heatmap_purpose", "info_quality_heatmap_example", "info_quality_heatmap")
        reason_reject = Counter()
        reason_approve = Counter()
        for e in resolved:
            r = e.get("mdm_reason") or "(empty)"
            if e.get("review_decision") == "reject":
                reason_reject[r] += 1
            else:
                reason_approve[r] += 1
        all_reasons = sorted(set(reason_reject.keys()) | set(reason_approve.keys()))
        if all_reasons:
            fig_heat = go.Figure(data=[
                go.Bar(name="Approve", x=all_reasons, y=[reason_approve.get(r, 0) for r in all_reasons]),
                go.Bar(name="Reject", x=all_reasons, y=[reason_reject.get(r, 0) for r in all_reasons]),
            ])
            fig_heat.update_layout(barmode="group", margin=dict(l=20, r=20, t=30, b=120), height=280, xaxis_tickangle=-45)
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.caption("—")

    # Research (packet-based): policy override rate + Core→Policy transition matrix
    if packets:
        st.markdown("---")
        st.subheader("Research: Policy override & Core→Policy")
        overrides = [p for p in packets if p.get("mdm", {}).get("core_level") is not None and p.get("mdm", {}).get("core_level") != p.get("mdm", {}).get("level", 0)]
        n_packets = len(packets)
        override_rate_pct = (len(overrides) / n_packets * 100.0) if n_packets else 0
        st.metric("Policy override rate (core_level ≠ final level)", f"{override_rate_pct:.1f}%")
        if overrides:
            from collections import Counter
            override_reasons = Counter(p.get("final_action_reason") or "—" for p in overrides)
            st.caption("Override reason breakdown: " + ", ".join(f"{k}:{v}" for k, v in sorted(override_reasons.items(), key=lambda x: -x[1])))
        # Core→Policy transition matrix
        matrix: Dict[str, Dict[str, int]] = {}
        for p in packets:
            mdm = p.get("mdm", {})
            core = mdm.get("core_level")
            if core is None:
                core = mdm.get("level", 0)
            final = mdm.get("level", 0)
            row = f"L{core}"
            col = f"L{final}"
            if row not in matrix:
                matrix[row] = {}
            matrix[row][col] = matrix[row].get(col, 0) + 1
        if matrix:
            rows = sorted(matrix.keys(), key=lambda x: int(x[1]))
            cols = sorted(set(c for row in matrix.values() for c in row.keys()), key=lambda x: int(x[1]))
            st.caption("Core → Policy (rows=core, cols=final)")
            table_data = [{"Core": r, **{c: matrix.get(r, {}).get(c, 0) for c in cols}} for r in rows]
            st.dataframe(table_data, use_container_width=True, hide_index=True)


def _get_live_module():
    """tools.live_wiki_audit modülünü döndürür; önce package, yoksa dosyadan yükler."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from tools import live_wiki_audit
        return live_wiki_audit
    except ImportError:
        pass
    # tools paket değilse (örn. __init__.py yok) doğrudan dosyadan yükle
    path = ROOT / "tools" / "live_wiki_audit.py"
    if not path.exists():
        raise ImportError(f"Bulunamadı: {path}")
    spec = importlib.util.spec_from_file_location("live_wiki_audit", path, submodule_search_locations=[str(ROOT)])
    if spec is None or spec.loader is None:
        raise ImportError(f"Modül yüklenemedi: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["live_wiki_audit"] = mod
    spec.loader.exec_module(mod)
    return mod


def _sync_live_packets() -> None:
    """Copy from live_wiki_audit.LIVE_PACKETS into session_state."""
    try:
        mod = _get_live_module()
        st.session_state["audit_packets"] = list(mod.LIVE_PACKETS)
    except Exception:
        pass


def _audit_packets() -> List[Dict[str, Any]]:
    if st.session_state.get("live_running"):
        _sync_live_packets()
    return st.session_state.get("audit_packets", [])


def _start_live() -> None:
    # Hata olursa session_state'e yaz (on_click ile çağrıldığında st.error görünmeyebilir)
    if "live_start_error" in st.session_state:
        del st.session_state["live_start_error"]
    try:
        mod = _get_live_module()
        LIVE_PACKETS = mod.LIVE_PACKETS
        run_live_loop = mod.run_live_loop
    except Exception as e:
        import traceback
        st.session_state["live_start_error"] = f"{e}\n\n{traceback.format_exc()}"
        return
    if st.session_state.get("live_running"):
        return
    try:
        stop_ev = threading.Event()
        st.session_state["live_stop_event"] = stop_ev
        LIVE_PACKETS.clear()
        sample_n = 10
        if "sample_every" in st.session_state:
            try:
                sample_n = int(st.session_state["sample_every"])
            except (TypeError, ValueError):
                pass
        sample_n = max(5, min(100, sample_n))
        th = threading.Thread(
            target=run_live_loop,
            args=(LIVE_PACKETS.append, stop_ev),
            kwargs={"sample_every_n": sample_n},
            daemon=True,
        )
        th.start()
        st.session_state["live_thread"] = th
        st.session_state["live_running"] = True
        st.rerun()
    except Exception as e:
        import traceback
        st.session_state["live_start_error"] = f"{e}\n\n{traceback.format_exc()}"


def _stop_live() -> None:
    if not st.session_state.get("live_running"):
        return
    ev = st.session_state.get("live_stop_event")
    if ev:
        ev.set()
    st.session_state["live_running"] = False
    st.rerun()


def _charts(packets: List[Dict], t: callable) -> None:
    """Grafikler: L0/L1/L2 pasta, karar zaman serisi, gecikme zaman serisi."""
    last = packets[-50:] if len(packets) > 50 else packets
    if not last:
        return
    # 1) Level dağılımı (pasta)
    level_counts = [0, 0, 0]
    for p in last:
        lv = p.get("mdm", {}).get("level", 0)
        if 0 <= lv <= 2:
            level_counts[lv] += 1
    fig_pie = go.Figure(data=[go.Pie(
        labels=["L0", "L1", "L2"],
        values=level_counts,
        hole=0.45,
        marker_colors=["#10b981", "#f59e0b", "#ef4444"],
    )])
    fig_pie.update_layout(height=280, margin=dict(t=20, b=20, l=20, r=20), showlegend=True)
    x = list(range(len(last)))
    levels = [p.get("mdm", {}).get("level", 0) for p in last]
    fig_lev = go.Figure()
    fig_lev.add_trace(go.Scatter(x=x, y=levels, mode="lines+markers", line=dict(color="#6366f1", width=2), marker=dict(size=6)))
    fig_lev.update_layout(xaxis_title="Index", yaxis_title="Level", height=260, margin=dict(t=20, b=20, l=20, r=20))
    fig_lev.update_yaxes(tickvals=[0, 1, 2])
    latencies = [p.get("latency_ms") for p in last if p.get("latency_ms") is not None]
    if not latencies:
        latencies = [0] * len(last)
    fig_lat = go.Figure()
    fig_lat.add_trace(go.Scatter(x=list(range(len(latencies))), y=latencies, mode="lines+markers", line=dict(color="#ec4899", width=2), marker=dict(size=5)))
    fig_lat.update_layout(xaxis_title="Index", yaxis_title="ms", height=260, margin=dict(t=20, b=20, l=20, r=20))
    c1, c2, c3 = st.columns(3)
    with c1:
        _chart_header_with_info("chart_levels", "info_levels_meaning", "info_levels_purpose", "info_levels_example", "info_levels")
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        _chart_header_with_info("chart_events", "info_events_meaning", "info_events_purpose", "info_events_example", "info_events")
        st.plotly_chart(fig_lev, use_container_width=True)
    with c3:
        _chart_header_with_info("chart_latency", "info_latency_meaning", "info_latency_purpose", "info_latency_example", "info_latency")
        st.plotly_chart(fig_lat, use_container_width=True)


def _mismatch_matrix(packets: List[Dict], t: callable) -> None:
    """ORES (ALLOW/FLAG) x MDM (L0/L1/L2) matrisi."""
    if not packets:
        return
    st.caption(t("info_mismatch_meaning"))
    counts = {
        ("ALLOW", 0): 0, ("ALLOW", 1): 0, ("ALLOW", 2): 0,
        ("FLAG", 0): 0, ("FLAG", 1): 0, ("FLAG", 2): 0,
    }
    for p in packets:
        ores = ((p.get("external") or {}).get("decision") or "ALLOW").upper()
        if ores not in ("ALLOW", "FLAG"):
            ores = "ALLOW"
        lv = p.get("mdm") or {}
        lv = int(lv.get("level", 0) or 0)
        lv = 0 if lv < 0 else 2 if lv > 2 else lv
        counts[(ores, lv)] = counts.get((ores, lv), 0) + 1
    table = [
        {"ORES": "ALLOW", "L0": counts[("ALLOW", 0)], "L1": counts[("ALLOW", 1)], "L2": counts[("ALLOW", 2)]},
        {"ORES": "FLAG", "L0": counts[("FLAG", 0)], "L1": counts[("FLAG", 1)], "L2": counts[("FLAG", 2)]},
    ]
    st.dataframe(table, hide_index=True, use_container_width=True)


def _reason_breakdown(packets: List[Dict], t: callable) -> None:
    """Escalation driver dağılımı (L1/L2) — teşhis: hangi sinyal L1/L2 tetikledi."""
    if not packets:
        return
    l1_l2 = [p for p in packets if p.get("mdm", {}).get("level") in (1, 2)]
    if not l1_l2:
        return
    from collections import Counter
    # final_action_reason (policy-facing); eski paketlerde escalation_driver / mdm.reason
    drivers = Counter(
        p.get("final_action_reason") or p.get("mdm", {}).get("escalation_driver") or p.get("mdm", {}).get("reason") or "—"
        for p in l1_l2
    )
    labels = list(drivers.keys())
    values = list(drivers.values())
    if not labels:
        return
    fig = go.Figure(data=[go.Bar(x=labels, y=values, marker_color="#6366f1")])
    fig.update_layout(
        xaxis_title="reason",
        yaxis_title="count",
        height=260,
        margin=dict(t=20, b=120, l=50, r=20),
    )
    _chart_header_with_info("chart_reason_breakdown", "info_reason_meaning", "info_reason_purpose", "info_reason_example", "info_reason")
    st.plotly_chart(fig, use_container_width=True)


def _chart_as_norm_histogram(packets: List[Dict], t: callable) -> None:
    """as_norm histogram — kalibrasyon: AS_SOFT_THRESHOLD ile L1 kilidi teşhisi."""
    if not packets:
        return
    last = packets[-200:] if len(packets) > 200 else packets
    values = []
    for p in last:
        unc = (p.get("mdm") or {}).get("uncertainty") or {}
        an = unc.get("as_norm")
        if an is not None:
            values.append(float(an))
    if not values:
        return
    fig = go.Figure(data=[go.Histogram(x=values, nbinsx=24, marker_color="#0ea5e9")])
    fig.update_layout(
        title=t("chart_as_norm_histogram"),
        xaxis_title="as_norm",
        yaxis_title="count",
        height=260,
        margin=dict(t=40, b=50, l=50, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def _chart_drift_driver(packets: List[Dict], t: callable) -> None:
    """drift_driver dağılımı — warmup vs mean/delta (erken drift tetiklemesi teşhisi)."""
    if not packets:
        return
    from collections import Counter
    drivers = Counter(
        ((p.get("mdm") or {}).get("temporal_drift") or {}).get("driver") or "—"
        for p in packets
    )
    labels = list(drivers.keys())
    values = list(drivers.values())
    if not labels:
        return
    fig = go.Figure(data=[go.Bar(x=labels, y=values, marker_color="#10b981")])
    fig.update_layout(
        title=t("chart_drift_driver"),
        xaxis_title="drift_driver",
        yaxis_title="count",
        height=260,
        margin=dict(t=40, b=100, l=50, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def _chart_pdamage_vs_level(packets: List[Dict], t: callable) -> None:
    """p_damaging (ORES) vs MDM level dağılımı."""
    last = packets[-80:] if len(packets) > 80 else packets
    if not last:
        return
    p_dmg = []
    levels = []
    for p in last:
        ext = p.get("external") or {}
        pd = ext.get("p_damaging")
        if pd is not None:
            p_dmg.append(pd)
            levels.append(p.get("mdm", {}).get("level", 0))
    if not p_dmg:
        return
    fig = go.Figure()
    for lv in (0, 1, 2):
        xs = [p_dmg[i] for i in range(len(p_dmg)) if levels[i] == lv]
        ys = [lv] * len(xs)
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name=f"L{lv}", marker=dict(size=8, opacity=0.7)))
    fig.update_layout(
        title=t("chart_pdamage_level"),
        xaxis_title="ores_p_damaging",
        yaxis_title="MDM level",
        yaxis=dict(tickvals=[0, 1, 2]),
        height=260,
        margin=dict(t=40, b=40, l=50, r=20),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_live_monitor(packets: List[Dict], t: callable) -> None:
    if st.session_state.get("main_section") != "monitor":
        return
    if not packets:
        if st.session_state.get("live_running"):
            try:
                mod = _get_live_module()
                status = getattr(mod, "LIVE_STATUS", {})
                err = status.get("error")
                events_seen = status.get("events_seen", 0)
                packets_sent = status.get("packets_sent", 0)
                sample_n = int(st.session_state.get("sample_every", 10))
                if err:
                    st.error(f"EventStreams bağlantı hatası: {err}")
                elif status.get("connected"):
                    if events_seen == 0:
                        st.warning(
                            "EventStreams bağlandı ama henüz olay gelmedi (ilk SSE mesajı bekleniyor). "
                            "Birkaç saniye bekleyin; olmazsa ağ/firewall/proxy kontrol edin (stream.wikimedia.org)."
                        )
                    else:
                        next_at = sample_n * (events_seen // sample_n + 1) if sample_n else 0
                        st.info(
                            f"EventStreams bağlı. Gelen olay: **{events_seen}**, işlenen paket: **{packets_sent}**. "
                            f"Her **{sample_n}** olayda bir paket üretilir (sonraki paket {next_at}. olayda). "
                            "Sidebar'dan N'i 5 yaparsanız ilk paket daha erken gelir."
                        )
                else:
                    st.info("EventStreams'e bağlanılıyor...")
            except Exception:
                st.info("Akış çalışıyor; ilk paket bekleniyor.")
        else:
            st.info(t("no_data"))
        return
    last_n = packets[-200:] if len(packets) > 200 else packets
    level_counts = {0: 0, 1: 0, 2: 0}
    ext_flag = ext_allow = 0
    latencies = []
    for p in last_n:
        level_counts[p.get("mdm", {}).get("level", 0)] = level_counts.get(p.get("mdm", {}).get("level", 0), 0) + 1
        if (p.get("external") or {}).get("decision") == "FLAG":
            ext_flag += 1
        else:
            ext_allow += 1
        if p.get("latency_ms") is not None:
            latencies.append(p["latency_ms"])
    total = len(last_n)
    l2_ratio = (level_counts.get(2, 0) / total * 100) if total else 0
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    with c1:
        st.metric(t("events"), total)
    with c2:
        st.metric("L0", level_counts.get(0, 0))
    with c3:
        st.metric("L1", level_counts.get(1, 0))
    with c4:
        st.metric("L2", level_counts.get(2, 0))
    with c5:
        st.metric(t("metric_l2_ratio"), f"{l2_ratio:.0f}%")
    with c6:
        st.metric(t("external"), f"{ext_flag} / {ext_allow}")
    with c7:
        avg_lat = sum(latencies) / len(latencies) if latencies else 0
        last_lat = latencies[-1] if latencies else "—"
        st.metric(t("avg_latency"), f"{avg_lat:.0f}" if latencies else "—")
        st.caption(f"{t('last_latency')}: {last_lat}")
    _charts(packets, t)
    st.markdown("---")
    st.markdown("### " + t("chart_mismatch"))
    mcol1, mcol2 = st.columns(2)
    with mcol1:
        _mismatch_matrix(packets, t)
    with mcol2:
        _reason_breakdown(packets, t)
    st.markdown("---")
    st.markdown("### " + t("advanced_calibration_expander"))
    with st.expander(t("advanced_calibration_details"), expanded=False):
        st.caption(t("advanced_calibration_caption"))
        cal1, cal2 = st.columns(2)
        with cal1:
            _chart_header_with_info("chart_as_norm_histogram", "info_as_norm_meaning", "info_as_norm_purpose", "info_as_norm_example", "info_as_norm")
            _chart_as_norm_histogram(packets, t)
        with cal2:
            _chart_header_with_info("chart_drift_driver", "info_drift_meaning", "info_drift_purpose", "info_drift_example", "info_drift")
            _chart_drift_driver(packets, t)
        _chart_header_with_info("chart_pdamage_level", "info_pdamage_meaning", "info_pdamage_purpose", "info_pdamage_example", "info_pdamage")
        _chart_pdamage_vs_level(packets, t)
    st.markdown("---")
    level_filter = st.multiselect(t("filter_level"), [0, 1, 2], default=[0, 1, 2], format_func=lambda x: f"L{x}")
    ext_filter = st.multiselect(t("filter_ext"), ["FLAG", "ALLOW"], default=["FLAG", "ALLOW"])
    profile_options = sorted(set(p.get("config_profile") or "—" for p in last_n))
    profile_filter = st.multiselect(t("filter_profile"), profile_options, default=profile_options, key="filter_profile") if profile_options else []
    filter_mismatch = st.checkbox(t("filter_mismatch"), value=False, key="filter_mismatch")
    filtered = [
        p for p in last_n
        if p.get("mdm", {}).get("level") in level_filter
        and (p.get("external") or {}).get("decision") in ext_filter
        and ((p.get("config_profile") or "—") in profile_filter if profile_filter else True)
        and (not filter_mismatch or p.get("mismatch") is True)
    ]
    rows = [decision_packet_to_flat_row(p) for p in filtered]
    if not rows:
        return
    df_event = st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "time": st.column_config.NumberColumn("time", format="%.1f"),
            "p_damaging": st.column_config.NumberColumn("p_damaging", format="%.3f"),
            "latency_ms": st.column_config.NumberColumn("latency_ms", format="%.0f"),
            "input_quality": st.column_config.NumberColumn("input_quality", format="%.2f"),
            "valid_candidate_count": st.column_config.NumberColumn("valid_candidate_count"),
            "frontier_size": st.column_config.NumberColumn("frontier_size"),
        },
        on_select="rerun",
        selection_mode="single-row",
        key="live_monitor_table",
    )
    sel = getattr(getattr(df_event, "selection", None), "rows", None) or []
    if sel and 0 <= sel[0] < len(filtered):
        st.session_state["selected_audit_packet"] = filtered[sel[0]]

    # CSV export: ORES + MDM + tüm frenleme/model alanları
    def _csv_cell(v):
        if v is None:
            return ""
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (list, tuple)):
            return ";".join(str(x) for x in v)
        return str(v)

    csv_rows = [decision_packet_to_csv_row(p) for p in filtered]
    if csv_rows:
        headers = list(csv_rows[0].keys())
        lines = [",".join(headers)]
        for row in csv_rows:
            line = ",".join(
                '"' + _csv_cell(row.get(h)).replace('"', '""') + '"' for h in headers
            )
            lines.append(line)
        csv_content = "\n".join(lines)
        st.download_button(
            "📥 " + t("download_csv"),
            csv_content,
            file_name=f"mdm_audit_{int(time.time())}.csv",
            mime="text/csv",
            key="download_csv_full",
        )


def _human_decision_summary(p: Dict, lang: str = "tr") -> str:
    """İnsanın anlayacağı tek cümle: Bu olay neden L0/L1/L2 aldı? (Sinyal adı değil, anlamı.)"""
    mdm = p.get("mdm", {})
    level = mdm.get("level", 0)
    ext = p.get("external", {})
    ores = (ext.get("decision") or "ALLOW").upper()
    reason = (p.get("final_action_reason") or mdm.get("escalation_driver") or mdm.get("reason") or "").lower()
    if lang == "tr":
        if level == 0:
            if "ores_flag" in reason:
                return "Uygulandı (L0): ORES şüpheli bulmuştu; politika gereği yine de insan incelemesine gönderildi (bu kart detay için)."
            return "Uygulandı (L0): Belirsizlik düşük, eşikler aşılmadı; dış karar (ORES) ile uyumlu. Düzenleme otomatik kabul edildi."
        if level == 1:
            if "confidence" in reason:
                return "Yumuşak fren (L1): Güven skoru düşüktü; sistem dikkatli davrandı. İnsan incelemesi zorunlu değil ama karar yumuşatıldı."
            if "constraint" in reason:
                return "Yumuşak fren (L1): Kısıt eşiği aşıldı. İnsan incelemesi zorunlu değil, ama aksiyon sınırlandı."
            if "drift" in reason:
                return "Yumuşak fren (L1): Zaman içi sapma (drift) tetiklendi. Sistem dikkatli davrandı."
            return "Yumuşak fren (L1): Bir güvenlik eşiği aşıldı; insan incelemesi zorunlu değil ama karar frenlendi."
        if level == 2:
            if "ores_flag" in reason or (ores == "FLAG" and "wiki" in reason):
                return "İnsan incelemesi (L2): ORES bu değişikliği şüpheli buldu (FLAG). Sizin onayınız veya reddiniz gerekiyor — diff'e bakıp karar verin."
            if "confidence" in reason:
                return "İnsan incelemesi (L2): Güven skoru çok düşüktü; sistem 'insan baksın' dedi."
            if "h_critical" in reason or "fail_safe" in reason:
                return "İnsan incelemesi (L2): Güvenlik eşiği (zarar/risk) aşıldı; fail-safe kuralı tetiklendi."
            if "drift" in reason:
                return "İnsan incelemesi (L2): Zaman içi sapma (drift) yüksek; insan onayı istendi."
            return "İnsan incelemesi (L2): Sistem bu düzenlemeyi insan onayına gönderdi. Diff'e bakıp Onayla veya Red deyin."
    else:
        if level == 0:
            return "Applied (L0): Low uncertainty, thresholds not exceeded; consistent with external decision (ORES)."
        if level == 1:
            return "Soft clamp (L1): A safety threshold was exceeded; human review not required but action was constrained."
        return "Human review (L2): This edit was sent for human approval. Check the diff and Approve or Reject."


def _render_decision_detail(packets: List[Dict], t: callable) -> None:
    selected = st.session_state.get("selected_audit_packet")
    if not selected:
        st.info(t("detail_select"))
        return
    p = selected
    mdm = p.get("mdm", {})
    level = mdm.get("level", 0)
    spec = get_level_spec(level)
    lang = st.session_state.get("lang", "en")
    st.subheader(f"{spec.get('dashboard_badge', f'L{level}')}")
    st.caption(spec.get("short", ""))
    # Core vs Policy (policy override varsa: Core Lx → Policy Ly)
    core_level = mdm.get("core_level")
    if core_level is not None and core_level != level:
        reason_display = p.get("final_action_reason") or mdm.get("escalation_driver") or mdm.get("reason") or "—"
        st.caption(f"**Core:** L{core_level} → **Policy:** L{level} ({reason_display})")
    # Engine reason (çekirdek teşhis; policy-facing reason üstte)
    engine_reason = mdm.get("engine_reason")
    if engine_reason:
        st.caption(f"**{t('engine_reason')}:** {engine_reason}")
    # İnsan için özet: Neden bu karar? (L0/L1/L2 hepsi için)
    st.markdown("**Neden bu karar? (İnsan için özet)**")
    st.info(_human_decision_summary(p, lang))
    # Gerçek veri kaynağı: her seviyede Wikipedia linki + diff (varsa)
    inp = p.get("input", {})
    has_wiki = inp.get("title") and (inp.get("revid") or (p.get("external") or {}).get("revid"))
    if has_wiki:
        st.markdown("**Gerçek veri kaynağı (inceleme için)**")
        wiki_url = _wiki_diff_url(p)
        if wiki_url:
            st.markdown(f"🔗 [{t('compare_link')}]({wiki_url})")
        # L2'de diff yoksa: evidence_status + compare link (retry backend'de; burada teşhis)
        evidence_status = p.get("evidence_status")
        if level == 2 and evidence_status:
            st.caption(f"**{t('evidence_status')}:** {evidence_status}")
            if p.get("evidence_error"):
                st.caption(f"Error: {str(p.get('evidence_error'))[:200]}")
        comment = (inp.get("comment") or "").strip()
        if comment:
            st.caption(f"Edit özeti (kullanıcı yazdığı): {comment[:400]}")
        evidence = inp.get("evidence") or {}
        diff_text = evidence.get("diff") or p.get("diff_excerpt") or ""
        if diff_text:
            st.caption("**(−) Eski sürüm | (+) Yeni sürüm**")
            diff_preview = (diff_text[:2500] + "…") if len(diff_text) > 2500 else diff_text
            st.text_area("Yapılan değişiklik (diff)", value=diff_preview, height=180, key="detail_diff", disabled=True)
        else:
            st.caption("Diff bu olay için yok (L0/L1'de bazen çekilmez). Linkten sayfayı açabilirsiniz.")
        st.markdown("---")
    st.markdown("**" + t("detail_explain") + "**")
    st.write(mdm.get("explain", "—"))
    if p.get("latency_ms") is not None:
        st.caption(f"{t('last_latency')}: **{p['latency_ms']}** ms")
    st.markdown("**" + t("detail_external") + "**")
    ext = p.get("external", {})
    st.write(f"decision={ext.get('decision')}, p_damaging={ext.get('p_damaging')}, p_goodfaith={ext.get('p_goodfaith')}")
    if p.get("mdm_input_risk") is not None:
        st.caption(f"mdm_input_risk (MDM'e giden): {p.get('mdm_input_risk')}")
    st.markdown("**Entity**")
    st.code(p.get("entity_id", ""))
    st.markdown("**" + t("detail_signals") + "**")
    st.json(mdm.get("signals", {}))
    # Core / Quality signals (Wiki + SSOT zenginleştirme)
    with st.expander("**" + t("core_signals") + "**", expanded=True):
        drift = mdm.get("temporal_drift") or {}
        def _cell(v):
            if v is None: return "—"
            if isinstance(v, bool): return "true" if v else "false"
            if isinstance(v, (list, tuple)): return ", ".join(str(x) for x in v) if v else "—"
            if isinstance(v, dict): return "; ".join(f"{k}:{v}" for k, v in sorted(v.items())) if v else "—"
            return str(v)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption(t("core_missing_fields"))
            st.write(_cell(mdm.get("missing_fields")))
            st.caption(t("core_valid_candidates"))
            st.write(_cell(mdm.get("valid_candidate_count")))
            st.caption(t("core_input_quality"))
            st.write(_cell(mdm.get("input_quality")))
            st.caption(t("core_frontier_size"))
            st.write(_cell(mdm.get("frontier_size")))
        with c2:
            st.caption(t("core_invalid_reasons"))
            st.write(_cell(mdm.get("invalid_reason_counts")))
            st.caption(t("core_evidence_consistency"))
            st.write(_cell(mdm.get("evidence_consistency")))
            st.caption(t("core_pareto_gap"))
            st.write(_cell(mdm.get("pareto_gap")))
            st.caption(t("core_drift_applied"))
            st.write(_cell(drift.get("applied")))
        with c3:
            st.caption(t("core_selection_reason"))
            st.write(_cell(mdm.get("selection_reason")))
            st.caption(t("core_state_hash"))
            st.code((mdm.get("state_hash") or "—")[:32] + "…" if mdm.get("state_hash") else "—")
            st.caption(t("core_config_hash"))
            st.code((mdm.get("config_hash") or "—")[:32] + "…" if mdm.get("config_hash") else "—")
    inp = p.get("input", {})
    st.markdown("**" + t("detail_content") + "**")
    st.write(f"title: {inp.get('title')}, user: {inp.get('user')}, revid: {inp.get('revid')}, comment: {(inp.get('comment') or '')[:200]}")
    evidence = inp.get("evidence") or {}
    if evidence and not has_wiki:
        st.text_area("Diff / evidence", evidence.get("diff", str(evidence)), height=120)
    review = p.get("review", {})
    if level == 2:
        st.markdown("---")
        st.caption(t("detail_l2_resolve_in_review"))
        category = st.selectbox(t("category"), ["", "false_positive", "irony", "needs_context", "true_positive", "spam", "other"], key="detail_category")
        note = st.text_input(t("note"), key="detail_note")
        if category:
            review["category"] = category
        if note:
            review["note"] = note


def _wiki_diff_url(p: Dict) -> str:
    """Wikipedia'da bu revizyonun diff sayfası linki (insan gözüyle inceleme için)."""
    inp = p.get("input", {})
    title = (inp.get("title") or "").strip()
    revid = inp.get("revid") or (p.get("external") or {}).get("revid")
    if not title or not revid:
        return ""
    # Önceki revizyon: evidence'dan veya revision.old (event'ten); yoksa sadece revid ile diff
    evidence = (inp.get("evidence") or {})
    from_revid = evidence.get("from_revid")
    to_revid = evidence.get("to_revid") or revid
    base = "https://en.wikipedia.org/wiki/Special:Compare"
    if from_revid and to_revid:
        return f"{base}?oldrev={from_revid}&newrev={to_revid}"
    # Tek revizyon: diff=revid ile o revizyona göre değişiklik görünür
    encoded_title = quote_plus(title.replace(" ", "_"))
    return f"https://en.wikipedia.org/w/index.php?title={encoded_title}&diff={revid}&oldid=prev"


def _render_review_queue(packets: List[Dict], t: callable) -> None:
    pending = [p for p in packets if p.get("mdm", {}).get("level") == 2 and (p.get("review") or {}).get("status") == "pending"]
    st.metric(t("review_pending"), len(pending))
    if not pending:
        st.info(t("review_none"))
        return
    st.info(t("review_why_here"))
    st.markdown("---")
    for i, p in enumerate(pending):
        mdm = p.get("mdm", {})
        inp = p.get("input", {})
        title_short = (inp.get("title") or "")[:50]
        user = inp.get("user") or "—"
        with st.expander(f"**{title_short}** · {user}"):
            ores_decision = (p.get("external") or {}).get("decision") or ""
            reason_driver = p.get("final_action_reason") or mdm.get("escalation_driver") or mdm.get("reason") or ""
            if ores_decision == "FLAG" and "ores_flag" in str(reason_driver).lower():
                st.caption(t("review_item_ores"))
            else:
                st.caption(t("review_item_mdm"))
            wiki_url = _wiki_diff_url(p)
            if wiki_url:
                st.markdown(f"🔗 [{t('review_open_wiki')}]({wiki_url})")
            comment = (inp.get("comment") or "").strip()
            if comment:
                st.caption(f"{t('review_edit_summary')}: {comment[:200]}")
            st.markdown(f"**{t('review_change_label')}**")
            evidence = inp.get("evidence") or {}
            diff_text = evidence.get("diff") or p.get("diff_excerpt") or ""
            if diff_text:
                st.caption(t("review_diff_legend"))
                diff_preview = (diff_text[:4000] + "…") if len(diff_text) > 4000 else diff_text
                st.text_area("diff", value=diff_preview, height=240, key=f"rq_diff_{i}", disabled=True, label_visibility="collapsed")
            else:
                st.caption(t("review_diff_unavailable"))
            st.markdown(f"**{t('review_what_to_do')}**")
            st.caption(t("review_approve_means"))
            st.caption(t("review_reject_means"))
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button(t("open_detail"), key=f"rq_detail_{i}"):
                    st.session_state["selected_audit_packet"] = p
                    st.rerun()
            with c2:
                if st.button("✅ " + t("approve"), key=f"rq_approve_{i}"):
                    p.setdefault("review", {})["status"] = "resolved"
                    p["review"]["decision"] = "approve"
                    _append_review_log(p, "approve", p.get("review", {}).get("category", ""), p.get("review", {}).get("note", ""))
                    st.rerun()
            with c3:
                if st.button("❌ " + t("reject"), key=f"rq_reject_{i}"):
                    p.setdefault("review", {})["status"] = "resolved"
                    p["review"]["decision"] = "reject"
                    _append_review_log(p, "reject", p.get("review", {}).get("category", ""), p.get("review", {}).get("note", ""))
                    st.rerun()


def _render_search_audit(packets: List[Dict], t: callable) -> None:
    st.info(t("search_audit_explanation"))
    if not packets:
        st.info(t("no_data"))
        return
    level_filter = st.multiselect(t("filter_level"), [0, 1, 2], default=[0, 1, 2], format_func=lambda x: f"L{x}", key="search_level")
    user_contains = st.text_input("User contains", key="search_user")
    title_contains = st.text_input("Title contains", key="search_title")
    filtered = [p for p in packets if p.get("mdm", {}).get("level") in level_filter]
    if user_contains:
        filtered = [p for p in filtered if user_contains.lower() in (p.get("input", {}).get("user") or "").lower()]
    if title_contains:
        filtered = [p for p in filtered if title_contains.lower() in (p.get("input", {}).get("title") or "").lower()]
    st.caption(f"{t('search_result')}: {len(filtered)}")
    sample_l0 = st.checkbox(t("search_sample_l0"), key="sample_l0")
    if sample_l0:
        l0_only = [p for p in filtered if p.get("mdm", {}).get("level") == 0]
        filtered = l0_only[:: max(1, len(l0_only) // 100)] if len(l0_only) > 100 else l0_only[:10]
    rows = [decision_packet_to_flat_row(p) for p in filtered[:200]]
    if rows:
        search_event = st.dataframe(rows, use_container_width=True, hide_index=True, key="search_table", on_select="rerun", selection_mode="single-row")
        sel = getattr(getattr(search_event, "selection", None), "rows", None) or []
        if sel and 0 <= sel[0] < len(filtered):
            st.session_state["selected_audit_packet"] = filtered[sel[0]]
            st.caption(t("see_detail_tab"))


def main():
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"
    if "audit_packets" not in st.session_state:
        st.session_state["audit_packets"] = []
    if "live_running" not in st.session_state:
        st.session_state["live_running"] = False

    t = _t
    # Dil: 2 seçenek (canlı test için)
    lang = st.sidebar.radio(
        t("language"),
        ["en", "tr"],
        key="lang_radio",
        index=0 if st.session_state.get("lang", "en") == "en" else 1,
        horizontal=True,
        format_func=lambda x: "English" if x == "en" else "Türkçe",
    )
    st.session_state["lang"] = lang
    st.sidebar.markdown("---")
    st.sidebar.markdown("**" + (t("sidebar_section") if "sidebar_section" in (TEXTS.get(lang) or {}) else "Section") + "**")
    opts = ["review", "monitor", "detail", "search", "quality"]
    section = st.sidebar.radio(
        "main_section",
        opts,
        format_func=lambda x: {"review": t("tab_review"), "monitor": t("tab_monitor"), "detail": t("tab_detail"), "search": t("tab_search"), "quality": t("tab_quality")}[x],
        key="main_section",
        label_visibility="collapsed",
    )
    st.sidebar.markdown("---")

    packets = _audit_packets()
    pending_l2 = len([p for p in packets if p.get("mdm", {}).get("level") == 2 and (p.get("review") or {}).get("status") == "pending"])
    header_right = f'<span class="badge">{t("review_pending")}: {pending_l2}</span>' if pending_l2 else ""
    st.markdown(
        f'<div class="mdm-header">'
        f'<div class="mdm-title-block"><h1>{t("title")} <span class="mdm-subtitle">({t("title_full")})</span></h1></div>'
        f'<span class="badge">{t("badge")}</span>{header_right}'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown(f"### ◉ {t('sidebar_data')}")
        if st.session_state.get("live_start_error"):
            st.error("Canlı akış başlatılamadı")
            st.code(st.session_state["live_start_error"][:2000])
            if st.button("Hata kutusunu kapat", key="dismiss_start_error"):
                del st.session_state["live_start_error"]
                st.rerun()
        if st.session_state.get("live_running"):
            st.success(t("live_running"))
            if st.button(t("stop_live"), type="primary"):
                _stop_live()
        else:
            st.caption(t("live_stopped"))
            st.number_input(t("sample_every"), min_value=5, max_value=100, value=10, key="sample_every")
            st.button(t("start_live"), type="primary", key="btn_start_live", on_click=_start_live)
        st.markdown("---")
        st.caption("JSONL dosya yolundan yükle (CLI yazıyorsa)")
        jsonl_path = st.text_input("Dosya yolu", value=st.session_state.get("live_jsonl_path", "mdm_live.jsonl"), key="live_jsonl_path", label_visibility="collapsed", placeholder="mdm_live.jsonl")
        if st.button("Dosyadan yükle", key="load_jsonl_file"):
            if jsonl_path and jsonl_path.strip():
                p = Path(jsonl_path.strip())
                if not p.is_absolute():
                    p = ROOT / p
                if p.exists():
                    try:
                        packets = []
                        with open(p, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    packets.append(json.loads(line))
                                except json.JSONDecodeError:
                                    continue
                        if _schema_v2_required(packets):
                            st.error("Eski şema veya schema_version yok / < 2.0. Yeni export alın: canlı koşu veya mdm ile üretilen JSONL (schema v2.0).")
                            st.session_state["audit_packets"] = []
                        else:
                            st.session_state["audit_packets"] = packets
                            st.success(f"{len(packets)} paket yüklendi: {p.name}")
                    except Exception as e:
                        st.error(f"Okuma hatası: {e}")
                else:
                    st.warning(f"Dosya yok: {p}")
        st.markdown("---")
        st.caption(t("upload_jsonl"))
        uploaded = st.file_uploader("JSONL", type=["jsonl", "json"], key="audit_jsonl", label_visibility="collapsed")
        if uploaded:
            lines = uploaded.read().decode("utf-8").strip().split("\n")
            packets = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    packets.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            if _schema_v2_required(packets):
                st.error("Eski şema veya schema_version yok / < 2.0. Yeni export alın: canlı koşu veya mdm ile üretilen JSONL (schema v2.0).")
                st.session_state["audit_packets"] = []
            else:
                st.session_state["audit_packets"] = packets
                st.success(f"{len(packets)} {t('packets_label')}")

    # Ana alanda bölüm başlığı her zaman görünsün (başlık yana kaymasın)
    sec = st.session_state.get("main_section", "review")
    section_titles = {"review": t("tab_review"), "monitor": t("tab_monitor"), "detail": t("tab_detail"), "search": t("tab_search"), "quality": t("tab_quality")}
    st.subheader(section_titles.get(sec, t("tab_review")))
    if sec == "review":
        _render_review_queue(packets, t)
    elif sec == "monitor":
        _render_live_monitor(packets, t)
    elif sec == "detail":
        _render_decision_detail(packets, t)
    elif sec == "search":
        _render_search_audit(packets, t)
    else:
        _render_quality_panel(packets, t)

    if st.session_state.get("live_running") and sec == "monitor":
        time.sleep(1.5)
        st.rerun()


if __name__ == "__main__":
    main()
