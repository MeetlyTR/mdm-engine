#!/usr/bin/env python
"""
Review bundle zip: yalnızca GEREKLI dosyaları içerir (whitelist).
Dahili dokümanlar (strateji, raporlar, yol haritası vb.) zip'e eklenmez.
Hariç: .venv, __pycache__, .git, büyük log. Çıktı: masaüstü mdm_review_bundle.zip
Kullanım: python tools/make_review_bundle.py
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path.home() / "Desktop" / "mdm_review_bundle.zip"
EXCLUDE_DIRS = {".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".git", "node_modules", ".egg-info"}

# ---- Gerekli dosyalar whitelist (REVIEW_BUNDLE.md ile uyumlu) ----
ALLOWED_ROOT = {
    "README.md", "REVIEW_BUNDLE_EN.md", "CHANGELOG.md", "pyproject.toml",
    "SECURITY.md", "USAGE_POLICY.md", "CONTRIBUTING.md", "AUDITABILITY.md", "SAFETY_LIMITATIONS.md",
}
ALLOWED_CODE_DIRS = {"mdm_engine", "core", "config_profiles", "visualization", "tests"}
ALLOWED_TOOLS = {"smoke_test.py", "make_review_bundle.py", "live_wiki_audit.py", "quick_wiki_test.py", "csv_export.py"}
ALLOWED_DOCS = {
    "L2_CASE_STUDIES.md", "PACKET_SCHEMA_V2.md", "QUICKSTART.md", "README.md",
    "AUDIT_LEVELS_AND_PACKETS.md", "REPO_DOCS_POLICY.md",
}
ALLOWED_DOCS_IMAGES = True  # docs/images/ klasörü tamamen


def should_skip(p: Path) -> bool:
    try:
        size = p.stat().st_size
    except OSError:
        return True
    if p.suffix == ".pyc":
        return True
    if p.name.endswith(".log") and size > 100_000:
        return True
    if p.name == "review_log.jsonl" and size > 500_000:
        return True
    if size > 5 * 1024 * 1024:
        return True
    return False


def allowed_in_bundle(rel: Path) -> bool:
    parts = rel.parts
    if not parts:
        return False
    if any(p in EXCLUDE_DIRS for p in parts):
        return False
    top = parts[0]
    # Kök dosyalar
    if len(parts) == 1:
        return top in ALLOWED_ROOT or (top.endswith(".toml") and top.startswith("pyproject"))
    # Kod dizinleri (tüm alt dosyalar)
    if top in ALLOWED_CODE_DIRS:
        return True
    # tools/: sadece whitelist
    if top == "tools" and len(parts) == 2:
        return parts[1] in ALLOWED_TOOLS
    if top == "tools":
        return False
    # examples/: tümü
    if top == "examples":
        return True
    # docs/: sadece whitelist + images
    if top == "docs":
        if len(parts) == 2:
            return parts[1] in ALLOWED_DOCS or (parts[1] == "images")
        if len(parts) >= 2 and parts[1] == "images":
            return ALLOWED_DOCS_IMAGES
        return False
    return False


def main():
    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in ROOT.rglob("*"):
            if not f.is_file():
                continue
            try:
                rel = f.relative_to(ROOT)
                if not allowed_in_bundle(rel):
                    continue
                if should_skip(f):
                    continue
                zf.write(f, rel)
                count += 1
            except (OSError, ValueError):
                continue
    print(f"OK: {count} dosya (yalnizca gerekli whitelist) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
