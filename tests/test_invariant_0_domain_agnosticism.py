# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""
INVARIANT 0: Domain-agnosticism in public surface (docs + packaged core only).

Scans README.md, docs/ (excluding examples), and packaged core: mdm_engine/mdm + mdm_engine/security.
EXCLUDE_CODE = [] — scan aligns with pyproject allowlist.
"""

import re
from pathlib import Path

FORBIDDEN_TERMS = {
    "trade",
    "trading",
    "trader",
    "market",
    "orderbook",
    "bid",
    "ask",
    "quote",
    "fill",
    "exchange",
    "portfolio",
    "pnl",
    "slippage",
    "spread",
    "liquidity",
    "inventory",
    "exposure",
    "drawdown",
    "flatten",
    "cancel_all",
}

PUBLIC_DOCS = ["README.md", "docs/"]
CODE_DIRS = ["mdm_engine/mdm", "mdm_engine/security"]
EXCLUDE_DOCS = [
    r"docs[/\\]examples[/\\]",
    r"docs[/\\]PUBLIC_RELEASE_GUIDE\.md",
    r"docs[/\\]TERMINOLOGY\.md",
    r"tests/.*",
]
EXCLUDE_CODE: list[str] = []


def _find_doc_files(repo_root: Path) -> list[Path]:
    files = []
    for p in PUBLIC_DOCS:
        path = repo_root / p
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
        else:
            for f in path.rglob("*"):
                if f.is_file() and f.suffix in (".md", ".rst", ".txt"):
                    rel = str(f.relative_to(repo_root)).replace("\\", "/")
                    if not any(
                        re.search(pat, rel, re.IGNORECASE) for pat in EXCLUDE_DOCS
                    ):
                        files.append(f)
    return files


def _find_code_files(repo_root: Path) -> list[Path]:
    files = []
    for code_dir in CODE_DIRS:
        path = repo_root / code_dir
        if not path.exists():
            continue
        for f in path.rglob("*.py"):
            rel = str(f.relative_to(repo_root)).replace("\\", "/")
            if any(re.search(pat, rel) for pat in EXCLUDE_CODE):
                continue
            files.append(f)
    return files


def test_invariant_0_docs_domain_agnostic() -> None:
    """README and docs (excluding examples) must not contain domain vocabulary."""
    repo_root = Path(__file__).resolve().parent.parent
    violations = []
    for f in _find_doc_files(repo_root):
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            lower = line.lower()
            for term in FORBIDDEN_TERMS:
                if term in lower and not line.strip().startswith("#"):
                    violations.append((str(f.relative_to(repo_root)), i, term))
    assert not violations, "INVARIANT 0 (docs) violated: " + str(violations[:15])


def test_invariant_0_core_code_domain_agnostic() -> None:
    """Packaged core (mdm_engine/mdm + mdm_engine/security) must not contain domain vocabulary."""
    repo_root = Path(__file__).resolve().parent.parent
    violations = []
    for f in _find_code_files(repo_root):
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            lower = line.lower()
            for term in FORBIDDEN_TERMS:
                if re.search(r"\b" + re.escape(term) + r"\b", lower):
                    violations.append((str(f.relative_to(repo_root)), i, term))
    assert not violations, "INVARIANT 0 (core code) violated: " + str(violations[:15])
