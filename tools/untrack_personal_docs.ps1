# Remove Turkish and personal docs from Git tracking (files stay on disk).
# Run from repo root: .\tools\untrack_personal_docs.ps1
# After this, .gitignore will keep them untracked.

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

$toUntrack = @(
    "DURUM_DEGERLENDIRMESI.md",
    "REBUILD_SUMMARY.md",
    "PROJECT_REPORT.md",
    "REPOSITORY_STRUCTURE.md",
    "REVIEW_BUNDLE.md",
    "docs/GITHUB_YUKLEME_ADIMLARI.md",
    "docs/TAVSIYE_CSV_L0_KALIBRASYON_VE_MANTIK.md",
    "docs/TAVSIYE_DEGERLENDIRME_WIKI_CSV.md",
    "docs/CSV_KALIBRASYON_ALANLARI.md",
    "docs/AUDIT_CSV_1771059870_TAVSIYE.md",
    "docs/ADAPTER_VERI_ANALIZI.md",
    "docs/28_CANLI_VERI_VE_PILOT.md",
    "docs/ROADMAP_10_10.md",
    "docs/ACADEMIC_PRESENTATION.md",
    "docs/CORPORATE_PITCH.md",
    "docs/RESEARCH_BRIEF.md",
    "docs/EMAIL_TEMPLATES.md",
    "docs/BRANDING.md",
    "docs/DECIDE_FLOW_SSOT_AND_GAPS.md",
    "docs/ESCALATION_H_HIGH_PLAN.md",
    "docs/DASHBOARD_REFACTOR_PLAN.md",
    "docs/PYPI_LEGACY_NOTE.md",
    "docs/REASON_TERMINOLOGY.md",
    "docs/INVARIANTS_SCHEMA_METRICS.md",
    "docs/GOLDEN_EXAMPLE.md",
    "docs/images/README.md",
    "docs/19_SYSTEM_CHECKUP_NOTLARI.txt",
    "docs/00_ARCHITECTURE_STATUS.txt",
    "docs/21_PHASE_63_64_7_ROADMAP.txt",
    "docs/14_DASHBOARD_NASIL_OKUNUR.txt",
    "docs/22_KULLANICI_SECIMLERI_VE_SONUCLAR.txt",
    "docs/23_TEK_TEST_RASGELE_SENARYOLAR.txt",
    "docs/24_VERI_INCELEME_SONUC.txt",
    "docs/25_TABLO_COCUK_ANLATIMI.txt",
    "docs/27_REALTIME_PROOF_STATUS.txt",
    "docs/18_DASHBOARD_DEMO_VS_OPTIMIZATION.txt",
    "docs/20_CHAOS_AND_CONFIG_PROFILES.txt"
)

foreach ($p in $toUntrack) {
    if (Test-Path $p) {
        git rm --cached $p 2>$null
        Write-Host "Untracked: $p"
    }
}

# Directories: remove all tracked files under them
$dirs = @("docs/reports", "docs/development", "docs/releases")
foreach ($d in $dirs) {
    if (Test-Path $d) {
        Get-ChildItem -Path $d -Recurse -File | ForEach-Object {
            $rel = $_.FullName.Replace($root + [IO.Path]::DirectorySeparatorChar, "").Replace("\", "/")
            git rm --cached $rel 2>$null
            Write-Host "Untracked: $rel"
        }
    }
}

Write-Host "Done. Commit the change to stop tracking these paths; files remain on disk."
