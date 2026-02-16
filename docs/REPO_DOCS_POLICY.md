# Repo documentation policy (English only)

The public repo keeps **only English** and **only docs necessary** for core engine, ORES integration, and live testing. Turkish documents and personal/internal notes are **not tracked** (see `.gitignore`).

**Working notes / internal docs:** The repo must **not** contain the author’s **MDM working notes** (internal drafts, operational notes, Turkish notes, strategy/roadmap drafts, reports, or any “my notes” style docs). Those stay local only and are listed in `.gitignore`. The public repo keeps only English, product/schema-level docs and code needed for core, ORES, and live testing.

---

## In repo (tracked)

| Category | Files |
|----------|--------|
| **Root** | README.md, CHANGELOG.md, SECURITY.md, USAGE_POLICY.md, CONTRIBUTING.md, AUDITABILITY.md, SAFETY_LIMITATIONS.md, pyproject.toml |
| **Review bundle (EN)** | REVIEW_BUNDLE_EN.md (structure and run instructions for external review) |
| **Docs (EN, core/schema)** | docs/README.md, docs/PACKET_SCHEMA_V2.md, docs/AUDIT_LEVELS_AND_PACKETS.md, docs/QUICKSTART.md, docs/ADAPTER_GUIDE.md, docs/CALIBRATION_GUIDE.md, docs/ARCHITECTURE.md, docs/TERMINOLOGY.md |
| **L2 examples** | docs/L2_CASE_STUDIES.md (English only), docs/images/ (screenshots for L2 cases) |
| **Specs** | docs/specs/*.txt, docs/05_B3_CONFIDENCE_SPEC.txt, docs/06_PHASE_44*.txt through docs/17_*.txt, docs/12_*.txt, docs/13_*.txt |
| **Examples** | examples/README.md, examples/sample_*.jsonl, examples/sample_*.csv |

---

## Not in repo (ignored locally)

- **Turkish docs:** REVIEW_BUNDLE.md, DURUM_DEGERLENDIRMESI.md, GITHUB_YUKLEME_*, TAVSIYE_*, CSV_KALIBRASYON_*, AUDIT_CSV_*_TAVSIYE.md, ADAPTER_VERI_ANALIZI.md, 28_CANLI_VERI_VE_PILOT.md, docs/images/README.md (TR).
- **Personal / internal:** REBUILD_SUMMARY.md, PROJECT_REPORT.md, REPOSITORY_STRUCTURE.md, ROADMAP_10_10.md, ACADEMIC_PRESENTATION.md, CORPORATE_PITCH.md, RESEARCH_BRIEF.md, EMAIL_TEMPLATES.md, BRANDING.md, DECIDE_FLOW_*, ESCALATION_H_HIGH_PLAN.md, DASHBOARD_REFACTOR_PLAN.md, PYPI_LEGACY_NOTE.md, REASON_TERMINOLOGY.md, INVARIANTS_*, GOLDEN_EXAMPLE.md.
- **Turkish / personal .txt:** docs/19_SYSTEM_CHECKUP_NOTLARI.txt, docs/00_ARCHITECTURE_STATUS.txt, docs/21_PHASE_63_64_7_ROADMAP.txt, docs/14_DASHBOARD_NASIL_OKUNUR.txt, docs/22_* through docs/27_*.txt, docs/18_*.txt, docs/20_*.txt, docs/reports/, docs/development/, docs/releases/.

These remain on your machine but are not committed. Run once from repo root if they were previously tracked:  
`powershell -ExecutionPolicy Bypass -File tools/untrack_personal_docs.ps1`  
Then commit; files remain on disk but are no longer tracked.
