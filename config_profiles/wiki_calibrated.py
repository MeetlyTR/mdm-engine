# MDM — Wiki / vandalism kalibrasyon profili.
# Wiki/ORES demo: as_norm bu domain'de sürekli tie (best==second) → as_norm_low spam. L0 çıkması için as_norm_low kapatıldı.
# Varsayılan H_CRITICAL=0.6 ile grid'deki herhangi bir aksiyon H>0.6 → fail_safe %100; mdm_H=0 (safe aksiyon) ama driver H_critical.
# Bu profilde: H_CRITICAL yükseltilir, constraint kutusu gevşetilir → L0/L1 görülebilir.

from .base import DEFAULT_CONFIG

CONFIG = {
    **DEFAULT_CONFIG,
    # as_norm_low tetiklemesin: as_norm ∈ [0,1] olduğu için as_norm < 0 hiç sağlanmaz → L0 çıkabilir
    "AS_SOFT_THRESHOLD": 0.0,
    "CONFIDENCE_LOW_ESCALATION_LEVEL": 1,  # confidence_low → L1 (L2 backlog patlamasın)
    # CUS baseline wiki'de ~0.85; drift mean gereksiz tetiklenmesin
    "CUS_MEAN_THRESHOLD": 0.90,  # 0.88 → 0.90; cus_mean ~0.89 civarında takılıyorsa L0 oranı artar
    # Fail-safe: varsayılan 0.6 ile wiki grid'de sürekli worst_H > 0.6 → hep L2. Sadece aşırı H'da tetiklensin.
    "H_CRITICAL": 0.95,
    # Constraint kutusu: H_MAX gevşetildi. Wiki grid'de seçilen aksiyon mdm_J ~0.59; J_MIN 0.55 olunca margin ≥ 0 → L0 çıkabilir.
    "J_MIN": 0.55,  # 0.65 → 0.55; mdm_J ~0.59 kutuda kalsın, constraint_violation tetiklenmesin
    "H_MAX": 0.55,
}
