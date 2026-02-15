# Tavsiye Değerlendirmesi: CSV L0 Kalibrasyonu ve Mantık/Telemetri Uyumsuzluğu

Bu doküman, CSV incelemesinden çıkan tavsiyeyi ve “6 net soru”yı kod tarafından yanıtlayarak özetler. Kılavuzlar (AMI_ENGINE_Model_ve_Kilavuz_TR.md / AMI_ENGINE_Model_and_Manual_EN.md) workspace’te bulunamadığı için referans olarak `docs/INVARIANTS_SCHEMA_METRICS.md`, `core/fail_safe.py`, `core/soft_override.py`, `mdm_engine/engine.py` ve `mdm_engine/audit_spec.py` kullanıldı.

---

## 1) Tavsiyedeki tespitler — doğrulama

### 1.1 CSV’deki tablo (özet)

- **86/86 kayıt mdm_level=1**, hiç L0 yok.
- **selection_reason = fail_safe** tüm kayıtlarda.
- **mdm_human_escalation = True** tüm kayıtlarda.
- Buna rağmen: **final_action = APPLY_CLAMPED**, **clamp_applied = True**, **final_action_reason** çoğunlukla **H_high**.

Bu, `docs/INVARIANTS_SCHEMA_METRICS.md` içindeki hard invariant ile çelişiyordu:

- **fail_safe ⇒ level=2 AND final_action=HOLD_REVIEW AND clamp_applied=False.**

Kod tarafında neden böyle olduğu aşağıda açıklanıyor; iki düzeltme yapıldı (fail_safe iken escalation=2 zorlaması, CSV aksiyon sütun sırası).

---

## 2) Altı sorunun cevapları (koda göre)

### S1. Fail-safe koşulunu hangi değişkenle kontrol ediyorsun? (chosen_J/H mi, worst_J/H mi?)

**Cevap (güncel): Fail_safe artık seçilen (chosen) aksiyonun J/H ile tetikleniyor.**

- Önce fail_safe olmadan normal seçim yapılıyor; seçilen aksiyonun J,H’i ile `fail_safe(chosen_J, chosen_H)` çağrılıyor.
- Tetiklenirse → safe_action + escalation=2 (L2/HOLD_REVIEW).
- Tetiklenmezse → normal escalation (confidence, margin, H_high, as_norm) → L0/L1 çıkabiliyor.
- `worst_J` / `worst_H` sadece telemetri (mdm_worst_*) için hesaplanıyor; kararı etkilemiyor.

**Tavsiye doğru:** Fail-safe’in “chosen/best valid candidate” J/H üzerinden hesaplanması veya worst’ün sadece telemetri/alarm için kullanılması gerekiyor.

---

### S2. mdm_worst_J / mdm_worst_H valid adaylar üzerinden mi, yoksa tüm grid (invalid dahil) üzerinden mi?

**Cevap: Tüm grid (invalid dahil) üzerinden.**

- `scored` = constraint doğrulamasından önce oluşturuluyor; `candidates` ise sadece valid olanlar.
- `worst_J` / `worst_H` doğrudan `scored` üzerinden alınıyor.
- Wiki grid’de J=0.5 gibi düşük J ve yüksek H olan noktalar (invalid adaylar) her zaman var → worst_J ≈ 0.5, worst_H ≈ 0.86–0.92 → fail_safe sürekli tetikleniyor.

---

### S3. J_CRIT kaç? (CSV’de J_CRIT yok; default 0.7 mi?)

**Cevap: Evet. Varsayılan J_CRITICAL = 0.7.**

- `mdm_engine/config.py`: `J_CRITICAL = 0.7`, `H_CRITICAL = 0.6`.
- `wiki_calibrated` profilinde sadece `H_CRITICAL = 0.95` override ediliyor; **J_CRITICAL override yok** → 0.7 kullanılıyor.
- worst_J ≈ 0.5 < 0.7 → fail_safe (J_critical) her zaman tetikleniyor.

---

### S4. Fail-safe tetiklenince beklenen sonuç: L2 + HOLD_REVIEW mi, yoksa sizde özel olarak L1 mi?

**Cevap: Doküman ve invariant’a göre L2 + HOLD_REVIEW olmalı. Kodda bug vardı; düzeltildi.**

- `docs/INVARIANTS_SCHEMA_METRICS.md`: fail_safe ⇒ level=2, final_action=HOLD_REVIEW, clamp_applied=False.
- Eski davranış: fail_safe ile selector safe_action döndürüyordu (selection_reason=fail_safe), ama escalation seviyesi **seçilen (safe) aksiyonun** confidence/margin/H’ine göre hesaplandığı için bazen 0 veya 1 çıkıyordu → L0/L1 + APPLY/APPLY_CLAMPED.
- **Yapılan düzeltme:** `fs.override` iken artık **escalation=2** ve **escalation_drivers = ["fail_safe"]** zorlanıyor (`mdm_engine/engine.py`). Böylece fail_safe tetiklenince çıktı her zaman L2 ve export’ta final_action=HOLD_REVIEW olacak.

---

### S5. Aksiyon vektör sırası [severity, compassion, intervention, delay] mi? Export mapping’de swap var mı?

**Cevap: Evet, sıra [severity, compassion, intervention, delay]. Export’ta compassion ↔ intervention swap vardı; düzeltildi.**

- `core/soft_override.py`: `_IDX_SEVERITY=0`, `_IDX_INTERVENTION=2`, `_IDX_DELAY=3` → index 1 = compassion.
- `mdm_engine/config.py`: `SAFE_ACTION = [0.0, 0.5, 0.0, 1.0]` → [severity=0, compassion=0.5, intervention=0, delay=1.0].
- CSV’de mdm_J=0.75, mdm_H=0.0 bu safe_action ile uyumlu; fakat sütunlarda **compassion=0, intervention=0.5** görünüyordu.
- **Eski mapping (`audit_spec.py`):**  
  `mdm_action_intervention = action[1]`, `mdm_action_compassion = action[2]` → **yanlış** (1=compassion, 2=intervention).
- **Düzeltme:**  
  `mdm_action_compassion = action[1]`, `mdm_action_intervention = action[2]` ve yorum eklendi: `# Action vector: [severity, compassion, intervention, delay]`.

---

### S6. selection_reason = fail_safe nerede set ediliyor? (action_selector mı, escalation mı?)

**Cevap: action_selector’da set ediliyor.**

- `core/action_selector.py` satır 68–72:  
  `if fail_safe_result.override and fail_safe_result.safe_action is not None:`  
  `return SelectionResult(action=fail_safe_result.safe_action, score=None, reason="fail_safe", ...)`
- Yani **selection_reason** doğrudan seçim katmanından geliyor; escalation katmanı bunu değiştirmiyor. Çelişki, escalation’ın fail_safe iken L2 zorlamamasından kaynaklanıyordu; o kısım yukarıda düzeltildi.

---

## 3) Diğer sinyaller (tavsiyedeki “üçüncü sinyal”)

- **unc_action_spread_raw = 0, unc_as_norm = 0:**  
  Fail_safe path’te selector tek aksiyon (safe_action) döndürüyor; “candidates” skor listesi normal seçim path’i gibi olmadığı için uncertainty metrikleri (best vs second) anlamlı hesaplanmıyor veya tek adayda 0 çıkıyor. Bu, fail_safe davranışı ile tutarlı; ayrı bir “seçim ayrışmıyor” bug’ı zorunlu değil, ama fail_safe path’te uncertainty’nin nasıl raporlanacağı ileride netleştirilebilir.

---

## 4) wiki_calibrated ile ilgili

- Profil yorumu: “daha fazla L0/L1; fail-safe sadece aşırı H’da”.
- Ancak fail_safe **worst_J/worst_H** ile tetiklendiği için grid’de J=0.5 kalıcı → J_CRITICAL=0.7 her zaman aşılıyor. H_CRITICAL=0.95 yükseltmek tek başına yetmiyor; asıl problem **fail_safe’in grid-wide worst ile kontrol edilmesi**.
- Bu da tavsiyedeki “logic wiring” tespiti ile uyumlu: Kalibrasyon değil, fail_safe koşulunun **chosen (veya en azından valid) adaylar** üzerinden olması gerekiyor.

---

## 5) Yapılan kod değişiklikleri (kısa)

| Ne | Nerede | Değişiklik |
|----|--------|------------|
| Fail_safe ⇒ L2 | `mdm_engine/engine.py` | `fs.override` iken `escalation = 2` ve `escalation_drivers = ["fail_safe"]` zorlanıyor (invariant ile uyum). |
| Fail_safe chosen J/H | `mdm_engine/engine.py` | Fail_safe artık seçilen aksiyonun J,H'i ile tetikleniyor; worst sadece telemetri. L0 dengelenebiliyor. |
| CSV clamp_applied | `mdm_engine/audit_spec.py` | `clamp_applied = bool(clamps) and level==1` (L2'de False; invariant ile uyum). |
| CSV aksiyon sütunları | `mdm_engine/audit_spec.py` | `mdm_action_compassion = action[1]`, `mdm_action_intervention = action[2]`; sıra yorumu eklendi. |

---

## 6) Kılavuzlar ve tavsiye

- **AMI_ENGINE_Model_ve_Kilavuz_TR.md** / **AMI_ENGINE_Model_and_Manual_EN.md** bu workspace’te bulunamadı; bu yüzden doğrudan “kılavuzda hata var” diyemiyoruz.
- **Tavsiye:** Tespitler kodla uyumlu; “fail_safe ve H_high sadece chosen/best valid candidate üzerinden hesaplanmalı” ve “worst-case alarmı ayrı telemetri alanı olmalı, kararı override etmemeli” önerileri mantıklı.
- **Doküman tarafı:** `docs/INVARIANTS_SCHEMA_METRICS.md` ve Phase 2 spec ile uyumlu; çelişki kodda (fail_safe iken L2 zorlanmıyordu ve CSV’de aksiyon sırası yanlıştı), dokümanlarda değil.

İleride yapılabilecekler:

- Fail_safe koşulunu **sadece seçilen (chosen) aksiyonun J/H** ile çalıştırmak; worst_J/worst_H’ı sadece telemetri (mdm_worst_J, mdm_worst_H) veya ayrı alarm alanı olarak kullanmak.
- J_CRITICAL’ı wiki_calibrated’da da override etmek (ör. ≤ 0.5) ki grid’deki tek kötü nokta fail_safe’i her zaman tetiklemesin.

---

## Ek: H_high tetiklemesi ve “selected/plausible” model

### H_high şu an tam olarak neyle tetikleniyor?

**worst_H > H_MAX değil.** H_high, **seçilen aksiyonun H’i** ile tetikleniyor (zaten “selected/plausible” mode).

- **İfade:** `H >= H_MAX` (soft_override’da `h_high_val = H_MAX`).
- **Kullanılan H:** Engine’de `H_for_escalation = selected_H if selected_H is not None else worst_H`; bu değer `compute_escalation_decision` / `compute_escalation_level`’a gidiyor.
- **Sonuç:** H_high tetiklemesi = **selected_H >= H_MAX** (selected_H yoksa fallback worst_H).

Yani L0/L1/L2 escalation kararında (H_high, H_critical, confidence_low, constraint_violation, as_norm_low) kullanılan H **zaten seçilen aksiyonun H’i**. Worst_H sadece (1) fail_safe kararında (override tetiklemesi) ve (2) selected_H yoksa escalation fallback’inde kullanılıyor.

### “Selected/plausible” mode’a çevirince beklenen L0/L1 oranı

- **Şu an:** Fail_safe, **worst_J/worst_H** (tüm grid) ile tetiklendiği için wiki grid’de neredeyse her zaman override → selector safe_action döndürüyor, sonra biz escalation=2 zorluyoruz → **çoğunlukla L2** (önceki CSV’de hep L1 görünmesi eski bug’dan: fail_safe varken escalation 0/1 kalıyordu ve final_action_reason H_high vb. yazılıyordu).
- **Fail_safe’i “chosen” mode’a çevirirsek** (fail_safe sadece **seçilen aksiyonun** J < J_CRIT veya H > H_CRIT ise tetiklensin):
  - Wiki grid’de seçilen aksiyon genelde J ~ 0.59, H ~ 0.17 (ör. wiki_calibrated H_MAX=0.55, H_CRIT=0.95 ile).
  - Fail_safe çok seyrek tetiklenir (chosen J/H kutu içinde).
  - **Beklenen:** Çoğu karar L0; H_high (selected_H >= H_MAX) veya as_norm_low/constraint_margin vb. tetiklenenler L1; sadece gerçekten chosen H > H_CRIT veya J < J_CRIT olanlar L2.
- **Kabaca oran (kalibrasyona bağlı):** Profil ve eşiklere göre değişir; makul hedef wiki_calibrated için **L0 baskın (örn. %50–80), L1 daha az (%15–40), L2 seyrek (%5–15)**. Kesin sayı için mevcut grid + profil ile test koşusu gerekir.

---

## L0 neden hiç gelmiyordu? (Özet ve çözüm)

- **Neden:** Fail_safe **tüm grid** üzerinden worst_J / worst_H ile tetikleniyordu. Wiki grid'de her zaman bir nokta J≈0.5, H≈0.9 olduğu için worst_J < J_CRITICAL(0.7) → fail_safe her kararda tetikleniyor → selector safe_action döndürüyordu → **hiç normal seçim yapılmıyordu** → L0 imkânsızdı.
- **Parametre hatası değil:** Eşikler (J_MIN, H_MAX, wiki_calibrated) makuldü; sorun **fail_safe girdisinin** grid-wide worst olmasıydı.
- **Çözüm (yapıldı):** Fail_safe artık **sadece seçilen (chosen) aksiyonun J/H** ile tetikleniyor. Önce valid adaylardan normal seçim yapılıyor; seçilen aksiyonun J ≥ J_CRIT ve H ≤ H_CRIT ise fail_safe tetiklenmiyor → escalation confidence/margin/H_high/as_norm ile hesaplanıyor → **L0 çıkabiliyor** (örn. `python tools/quick_wiki_test.py` → level=0, driver='none').
- **Yeni CSV/live koşusu:** Aynı wiki_calibrated ile canlı veya JSONL’den üretilen CSV’de L0 satırları görülmeli; oran profil ve eşiklere göre değişir.

---

## Guardrail'lar ve parametre uyarısı

### 1) "Parametre hatası değil" yarım doğru

- **Grid-wide worst** → wiring hatası (L0'ı kilitliyordu); bu düzeltildi.
- **Chosen-mode'da** artık **J_CRIT / H_CRIT kalibrasyonu** L0/L1/L2 oranlarını belirler. Seçilen aksiyonların tipik J aralığı 0.7'nin altındaysa, chosen-mode ile bile fail_safe sık tetiklenir. Yani: "asıl sorun wiring" doğru; "parametreler makul, konu kapanır" değil — **wiki_calibrated'da J_CRIT override (örn. ≤ 0.5) veya eşik ayarı gerekebilir.**

### 2) Fail_safe tetiklenirse çıktı zorunlu L2/HOLD_REVIEW, clamp_applied=False

- Engine: `fs.override` ise `escalation = 2` ve `escalation_drivers = ["fail_safe"]` zorlanıyor (invariant).
- Export: `final_action` level'dan türetiliyor (0→APPLY, 1→APPLY_CLAMPED, 2→HOLD_REVIEW).
- **CSV clamp_applied:** Invariant ile uyum için `clamp_applied = bool(clamps) and level==1` (L2'de her zaman False; sadece L1'de soft clamp varsa True).

### 3) Escalation ile CSV aynı H/J kullanmalı

- Normal path: escalation `H_for_escalation = selected_H` (seçilen aksiyonun H'i) ile hesaplanıyor; CSV'deki mdm_H bu değer.
- Fail_safe path: escalation doğrudan 2 atanıyor; seçilen aksiyon safe_action (mdm_H=0). Fallback worst_H artık escalation kararında kullanılmıyor; sadece telemetri (mdm_worst_H) için yazılıyor.
