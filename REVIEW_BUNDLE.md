# MDM Review Bundle — Denetim paketi

Bu belge, dış inceleme için hazırlanan paketin yapısını ve çalıştırma talimatlarını özetler.

---

## Repo yapısı

```
mdm-engine/
├── README.md
├── pyproject.toml
├── REVIEW_BUNDLE.md          # Bu dosya
├── CHANGELOG.md
├── mdm_engine/               # Motor + şema + audit
│   ├── engine.py             # Seçim → fail-safe → escalation → final_action
│   ├── config.py             # Profil / eşik yükleme
│   ├── audit_spec.py         # Decision packet şeması, CSV/JSONL kolonları (schema v2)
│   ├── invariants.py         # Karar invariant’ları
│   ├── trace_types.py        # SCHEMA_VERSION
│   └── cli.py                # mdm dashboard / realtime / tests
├── core/                     # Fail-safe, soft override, confidence, uncertainty
│   ├── fail_safe.py          # Fail-safe & override mantığı
│   ├── soft_override.py      # Soft clamp
│   ├── confidence.py         # Internal/external/input_quality
│   ├── uncertainty.py       # as_norm, divergence, CUS/drift
│   ├── action_selector.py    # Pareto seçim
│   └── state_encoder.py      # State → vektör
├── config_profiles/          # wiki_calibrated, scenario_test, production_safe, vb.
├── tools/
│   ├── live_wiki_audit.py    # EventStreams + ORES + MDM, evidence/diff fetch
│   ├── smoke_test.py         # Tek komut test (sample_packets → L0/L2 + schema v2)
│   └── quick_wiki_test.py    # Hızlı Wikipedia test
├── visualization/
│   └── dashboard.py         # Streamlit UI + review workflow, review_log yazma
├── docs/                     # Şema, invariants, kalibrasyon, audit
├── examples/
│   ├── sample_packets.jsonl # 10 satır schema v2 (L0/L1/L2 karışık)
│   └── sample_mdm_audit.csv # Örnek CSV export
└── tests/
    ├── test_invariants.py
    ├── test_export_invariants.py
    ├── test_live_audit_flow.py
    └── test_schema_v2.py
```

---

## Önemli dosyaların kısa amacı

| Dosya | Amaç |
|-------|------|
| **mdm_engine/engine.py** | Ana akış: raw_state → moral scores → action grid → seçim → fail-safe → escalation → final_action (APPLY / APPLY_CLAMPED / HOLD_REVIEW). |
| **mdm_engine/config.py** | Profil mekanizması, eşikler (J_MIN, H_CRIT, H_MAX, AS_SOFT_THRESHOLD, CUS_MEAN_THRESHOLD, vb.). |
| **core/fail_safe.py** | Fail-safe tetikleme (J/H eşikleri), override ⇒ L2, human_escalation. |
| **core/soft_override.py** | Soft clamp: raw aksiyonu güvenli zarfa çekme. |
| **core/uncertainty.py** | as_norm, divergence, CUS, drift ile belirsizlik metriği. |
| **core/confidence.py** | Internal/external confidence, input_quality, escalation. |
| **mdm_engine/audit_spec.py** | Schema v2, decision_packet_from_engine_result, decision_packet_to_csv_row, flat_row (dashboard tablosu). |
| **visualization/dashboard.py** | Streamlit: Review Queue, Live Monitor, Decision Detail, Search & Audit, Quality. Onayla/Red → review_log. |
| **tools/live_wiki_audit.py** | EventStreams bağlantı, ORES çağrı, MDM pipeline, evidence/diff fetch (Wikipedia). |

---

## Çalıştırma komutları

- **Kurulum:**  
  `pip install -e .`  
  veya  
  `pip install -r requirements.txt` (varsa).

- **Dashboard (Streamlit):**  
  `streamlit run visualization/dashboard.py`  
  (Varsayılan port 8501; `--server.port 8503` ile değiştirilebilir.)

- **Offline demo:**  
  Dashboard’u aç → Sidebar’dan “Dosyadan yükle” veya JSONL yükle → `examples/sample_packets.jsonl` seç. Veriler tabloda ve grafiklerde görünür.

- **Live Wikipedia demo:**  
  Dashboard’ta “Start live stream” → EventStreams + ORES + MDM pipeline çalışır. `tools/live_wiki_audit.py` bu akışı sağlar.

- **CSV export:**  
  Dashboard’ta “Canlı İzleme” veya “Ara & Denetle” altında “CSV indir” butonu. Tam audit (ORES + MDM + clamp/model) indirilir.

- **Review log:**  
  L2 öğelerde Onayla/Red verildiğinde `review_log.jsonl` dosyasına append edilir. Ortam değişkeni: `MDM_REVIEW_LOG` (varsayılan: `review_log.jsonl`). “Kalite” sekmesi bu log’u okur.

- **Tek komut test:**  
  `python tools/smoke_test.py`  
  - `examples/sample_packets.jsonl` okunur.  
  - En az bir L0 ve bir L2 olduğu assert edilir.  
  - Schema v2 export (audit_spec) bozulmuyor assert edilir.

- **Review bundle zip (masaüstüne):**  
  `python tools/make_review_bundle.py`  
  - Masaüstüne `mdm_review_bundle.zip` yazar (.venv, __pycache__, .git, büyük log hariç).

---

## Bilinen sorunlar / notlar

- Dashboard, `mdm_engine` veya `ami_engine` import’unu dener; farklı kurulumlarda bölüm adları veya import yolu değişebilir.
- Live akış EventStreams/ORES’e bağlıdır; ağ/firewall/proxy engelleyebilir.
- Schema v2 zorunludur: paketlerde `mdm` anahtarı olmalı, eski top-level anahtar kabul edilmez.

---

## Güvenlik kontrol listesi (paylaşım öncesi)

- [x] API key yok
- [x] Cookie/session dosyası yok
- [x] Kişisel veri yok
- [x] Örnek veri küçük (10–30 satır)
