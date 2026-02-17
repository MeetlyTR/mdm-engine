"""
INVARIANT 0: Domain-agnosticism in public surface (docs + core code, examples excluded).

Scans README.md, docs/ (excluding examples), and mdm_engine/mdm/*.py (excluding position_manager.py only).
"""

import re
from pathlib import Path

FORBIDDEN_TERMS = {
    "trade", "trading", "trader", "market", "orderbook",
    "bid", "ask", "quote", "fill", "exchange", "portfolio",
    "pnl", "slippage", "spread", "liquidity", "inventory",
    "exposure", "drawdown", "flatten", "cancel_all",
}

PUBLIC_DOCS = ["README.md", "docs/"]
# Proposal core only (adapters/execution/sim/features are example-domain or legacy)
CODE_DIR = "mdm_engine/mdm"
EXCLUDE_DOCS = [r"docs[/\\]examples[/\\]", r"docs[/\\]PUBLIC_RELEASE_GUIDE\.md", r"docs[/\\]TERMINOLOGY\.md", r"tests/.*"]
# position_manager.py excluded until quarantined (execution state has domain terms)
EXCLUDE_CODE = [r"position_manager\.py$"]


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
                    if not any(re.search(pat, rel, re.IGNORECASE) for pat in EXCLUDE_DOCS):
                        files.append(f)
    return files


def _find_code_files(repo_root: Path) -> list[Path]:
    path = repo_root / CODE_DIR
    if not path.exists():
        return []
    files = []
    for f in path.rglob("*.py"):
        rel = str(f.relative_to(repo_root)).replace("\\", "/")
        if any(re.search(pat, rel) for pat in EXCLUDE_CODE):
            continue
        files.append(f)
    return files  # mdm_engine/mdm/*.py, excluding position_manager.py only


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
    """Proposal core (mdm_engine/mdm/, exclude position_manager only) must not contain domain vocabulary."""
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
                if term in lower:
                    violations.append((str(f.relative_to(repo_root)), i, term))
    assert not violations, "INVARIANT 0 (core code) violated: " + str(violations[:15])
