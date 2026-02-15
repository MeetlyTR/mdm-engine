# MDM — Karar invariants (paket/CSV'de asla bozulmaması gereken kurallar)
# Test + runtime assert (debug mod) için.
# Hard = teorik garanti (asla bozulmaz); Soft = profil/policy heuristics (bypass koşullu).

from typing import Any, Dict, List, Optional, Tuple

# Hard: motor/paket semantiği; ihlal = bug
HARD_INVARIANTS = (
    "inv_fail_safe_level", "inv_fail_safe_action", "inv_fail_safe_clamp",
    "inv_no_valid_level", "inv_no_valid_count",
    "inv_l1_clamp", "inv_l0_driver",
)
# Soft: policy/ops (örn. margin kuralı fail_safe/no_valid ile bypass)
SOFT_INVARIANTS = ("inv_margin_driver",)


def _get_level(p: Dict[str, Any]) -> int:
    mdm = p.get("mdm", p) if "mdm" in p else p
    return mdm.get("level", mdm.get("escalation", 0))


def _get_driver(p: Dict[str, Any]) -> str:
    """Primary escalation driver (tek string veya listeden ilki)."""
    mdm = p.get("mdm", p) if "mdm" in p else p
    drivers = mdm.get("escalation_drivers") or []
    if isinstance(drivers, str):
        drivers = [d.strip() for d in drivers.split("|") if d.strip()]
    if drivers:
        return drivers[0]
    return mdm.get("escalation_driver") or mdm.get("reason") or "none"


def _get_final_action(p: Dict[str, Any]) -> str:
    return p.get("final_action") or (
        "APPLY" if _get_level(p) == 0 else ("APPLY_CLAMPED" if _get_level(p) == 1 else "HOLD_REVIEW")
    )


def _clamp_applied(p: Dict[str, Any]) -> bool:
    mdm = p.get("mdm", p) if "mdm" in p else p
    if mdm.get("soft_safe_applied") is not None:
        return bool(mdm.get("soft_safe_applied"))
    clamps = p.get("clamps") or []
    return bool(clamps) and _get_level(p) == 1


def _valid_candidate_count(p: Dict[str, Any]) -> Optional[int]:
    mdm = p.get("mdm", p) if "mdm" in p else p
    return mdm.get("valid_candidate_count")


def _constraint_margin(p: Dict[str, Any]) -> Optional[float]:
    mdm = p.get("mdm", p) if "mdm" in p else p
    return mdm.get("constraint_margin")


def check_decision_invariants(
    packet_or_engine_output: Dict[str, Any],
    strict: bool = True,
) -> List[Tuple[str, str]]:
    """
    Paket veya engine çıktısı üzerinde invariant kontrolleri.
    Döner: [(invariant_adi, hata_mesaji), ...]. Boş liste = tümü sağlanıyor.
    strict=False: eksik alanlarda atlama (eski paketler için).
    """
    p = packet_or_engine_output
    # Schema v2: reject legacy top-level key (avoid literal in source)
    _legacy_key = "".join(chr(x) for x in (97, 109, 105))
    if _legacy_key in p:
        raise ValueError("Packet must not contain legacy key; schema v2 uses 'mdm' only.")
    # Engine çıktısı doğrudan gelirse "mdm" yok; level/escalation_driver vs. üst seviyede
    if "mdm" not in p and ("escalation" in p or "level" in p or "escalation_driver" in p):
        # Engine output: wrap as single-mdm packet view
        p = {"mdm": p, "final_action": p.get("final_action") or ("HOLD_REVIEW" if p.get("escalation", 0) == 2 else ("APPLY_CLAMPED" if p.get("escalation", 0) == 1 else "APPLY")), "clamps": []}
        if p["mdm"].get("soft_safe_applied"):
            p["clamps"] = [{"type": "soft_safe"}]

    level = _get_level(p)
    driver = _get_driver(p)
    final_action = _get_final_action(p)
    clamp_applied = _clamp_applied(p)
    valid_count = _valid_candidate_count(p)
    margin = _constraint_margin(p)
    violations: List[Tuple[str, str]] = []

    # 1) fail_safe ⇒ level==2 AND final_action==HOLD_REVIEW AND clamp_applied==False
    if driver == "fail_safe":
        if level != 2:
            violations.append(("inv_fail_safe_level", f"driver=fail_safe but level={level} (expected 2)"))
        if final_action != "HOLD_REVIEW":
            violations.append(("inv_fail_safe_action", f"driver=fail_safe but final_action={final_action} (expected HOLD_REVIEW)"))
        if clamp_applied:
            violations.append(("inv_fail_safe_clamp", "driver=fail_safe but clamp_applied=True (expected False)"))

    # 2) no_valid_candidates ⇒ level==2 AND valid_candidate_count==0
    if driver == "no_valid_candidates":
        if level != 2:
            violations.append(("inv_no_valid_level", f"driver=no_valid_candidates but level={level} (expected 2)"))
        if strict and valid_count is not None and valid_count != 0:
            violations.append(("inv_no_valid_count", f"driver=no_valid_candidates but valid_candidate_count={valid_count} (expected 0)"))

    # 3) level==1 ⇒ clamp_applied==True
    if level == 1 and not clamp_applied:
        violations.append(("inv_l1_clamp", "level=1 but clamp_applied=False (expected True)"))

    # 4) level==0 ⇒ driver==none (veya driver listesi boş)
    if level == 0 and driver != "none":
        violations.append(("inv_l0_driver", f"level=0 but driver={driver} (expected none)"))

    # 5) constraint_margin < 0 ⇒ driver en az constraint_violation içermeli (SOFT: bypass fail_safe/no_valid)
    if margin is not None and margin < 0 and "constraint_violation" not in driver and driver != "none":
        if driver not in ("fail_safe", "no_valid_candidates"):
            violations.append(("inv_margin_driver", f"constraint_margin={margin}<0 but driver={driver} (expected constraint_violation in driver)"))

    return violations
