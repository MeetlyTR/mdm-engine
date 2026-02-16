# L2 Case Studies — Content-based Reject appropriateness

Two edits from a live audit were classified as L2 (human review). This document assesses whether the **content** justifies a **Reject** (revert) decision, not just whether the pipeline correctly escalated.

---

## Overview

- **Huseyn Suhrawardy** (~2026-10355-08) and **Pastoral science fiction** (~2026-10385-62), from audit `mdm_audit_1771199061.csv`.
- Both ORES FLAG, `final_action_reason: wiki:ores_flag_disagree`.

---

## Case 1: Huseyn Suhrawardy (~2026-10355-08)

**What changed (diff):** The edit added highly charged language to the biography: phrases like "bloodiest pogroms", "carnage, hindu genocide", and the derogatory nickname "The king of the goondas", attributed to Suhrawardy. Factual sentences about partition and his move to Pakistan were also duplicated in a way that wove in these claims.

![Suhrawardy diff — red/green highlighted text](images/l2_suhrawardy_diff.png)

**Content assessment — Reject appropriate?**  
**Yes.** The added material is one-sided, unencyclopedic, and violates Wikipedia's neutrality and sourcing expectations. A human reviewer is justified in choosing **Reject**.

---

## Case 2: Pastoral science fiction (~2026-10385-62)

**What changed (diff):** A full paragraph describing "Charles Siebert's Wickerby: An Urban Pastoral" was removed. The opening sentence was then re-added on its own. So the edit is a substantive content removal, not a format-only change.

**Edit summary (from the editor):** "Does not appear to be science fiction at all and thus irrelevant to the topic of 'Pastoral Science Fiction'."

![Pastoral diff — paragraph removed, one line re-added](images/l2_pastoral_diff.png)

**Content assessment — Reject appropriate?**  
**Context-dependent.** If the removed paragraph was off-topic, **Approve** can be correct. If the removal was one-sided or wrong, **Reject** is appropriate. Escalating to L2 is correct; the final decision belongs to the reviewer.

---

## Review UI (both cases in queue)

Both items appear in the human review queue with "Open on Wikipedia" and Approve / Reject. When `evidence_status=MISSING` in the audit CSV, the Wikipedia link is essential for the decision.

![Review queue — two L2 cards: Suhrawardy and Pastoral](images/l2_review_ui.png)
