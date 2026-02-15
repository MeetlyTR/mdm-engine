#!/usr/bin/env python
"""
Review bundle zip oluşturur: masaüstüne mdm_review_bundle.zip.
Hariç: .venv, __pycache__, .git, .pytest_cache, .mypy_cache, *.log, büyük review_log.
Kullanım: python tools/make_review_bundle.py
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path.home() / "Desktop" / "mdm_review_bundle.zip"
EXCLUDE_DIRS = {".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".git", "node_modules", ".egg-info"}


def should_skip(p: Path) -> bool:
    for part in p.parts:
        if part in EXCLUDE_DIRS:
            return True
    try:
        size = p.stat().st_size
    except OSError:
        return True
    if p.suffix == ".pyc" or (p.name.endswith(".log") and size > 100_000):
        return True
    if p.name == "review_log.jsonl" and size > 500_000:
        return True
    if size > 5 * 1024 * 1024:
        return True
    return False


def main():
    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in ROOT.rglob("*"):
            if not f.is_file():
                continue
            try:
                if should_skip(f):
                    continue
                arc = f.relative_to(ROOT)
                zf.write(f, arc)
                count += 1
            except (OSError, ValueError):
                continue
    print(f"OK: {count} dosya → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
