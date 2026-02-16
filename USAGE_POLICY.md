# MDM Usage Policy

**Version**: 1.0  
**Last Updated**: 2026-02-13

---

## Summary

MDM is an **ethical decision regulator**. This document defines **prohibited and inappropriate uses** of the library.

---

## Prohibited Uses

### 1. Surveillance and Identification

**PROHIBITED:**
- Person/license plate identification from public camera footage
- Mass surveillance systems
- Personal data collection and processing (GDPR/KVKK violation risk)

**Why:** MDM is domain-agnostic; it does not collect data. Such uses occur in the adapter layer and are **the domain's responsibility**.

### 2. Automatic Sanctions and Punishment

**PROHIBITED:**
- Automatic sanctions without L2 (human escalation)
- Person targeting and punishment automation
- Decision enforcement without human intervention

**Why:** At L2 level, `human_escalation=True` is mandatory. This means "human decision required".

### 3. Personal Data Processing

**PROHIBITED:**
- Processing personal data under GDPR/KVKK
- Direct processing of sensitive information such as health data, financial data

**Note:** Domain adapter must convert this data into **anonymous scores** (e.g., risk score, urgency score).

---

## Inappropriate Uses (Not Recommended)

### 1. Clinical/Operational Decisions Without Domain Knowledge

**Warning:** MDM does not contain domain knowledge. **Domain expert** and **adapter layer** are required for clinical or operational decisions.

### 2. Production with Default Config

**Warning:** Default config (`base`) is intentionally set to **strict**. Use `production_safe` or domain-specific config for production.

---

## Correct Usage Examples

### ✅ Chat Moderation (Risk Score)

```python
# Adapter: Chat message → risk score
risk_score = analyze_message(message)  # Domain adapter
raw_state = {"risk": risk_score, "severity": 0.5, ...}
result = moral_decision_engine(raw_state)
# If L2 → call human moderator
```

### ✅ Sensor/IoT (Physical Risk)

```python
# Adapter: Sensor data → physical risk
physical_risk = analyze_sensors(temp, pressure, ...)  # Domain adapter
raw_state = {"risk": physical_risk, "severity": 0.8, ...}
result = moral_decision_engine(raw_state)
# If L2 → call operator
```

### ✅ Customer Requests (Urgency)

```python
# Adapter: Customer request → urgency score
urgency = analyze_request(request)  # Domain adapter
raw_state = {"risk": urgency, "severity": 0.6, ...}
result = moral_decision_engine(raw_state)
# If L2 → call human agent
```

---

## Human-in-the-Loop Requirement

**Mandatory:** At L2 level (`level == 2` or `human_escalation == True`), **human decision must be obtained**.

```python
result = moral_decision_engine(raw_state)
if result["human_escalation"]:
    # MANDATORY: Get human decision
    human_decision = await get_human_review(result)
    # Apply human decision
```

---

## Constraint Violation → Fail-Safe Requirement

If the adapter layer sends data in a format other than what MDM expects:

- Engine enters **fail-safe** mode
- Returns `human_escalation=True`
- Produces safe default action (`safe_action`)

**In this case:** Adapter layer must be fixed and traces must be examined.

---

## Support Policy

- **Community Support**: Via GitHub Issues
- **Best Effort**: Respond as quickly as possible
- **No SLA**: No guaranteed response time
- **Contact**: See repository maintainer (pyproject.toml) or GitHub Discussions.
- **Security Contact**: Use the repository Security tab or see SECURITY.md.

---

## Legal Disclaimer

This library is provided **"AS IS"**. Usage responsibility belongs to **the user**. Domain-specific legal/ethical requirements (GDPR, KVKK, HIPAA, etc.) must be handled in **the domain adapter layer**.

---

**Last Updated**: 2026-02-13
