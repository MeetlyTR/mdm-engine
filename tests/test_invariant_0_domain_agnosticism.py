"""
INVARIANT 0: Domain-agnosticism in public surface (README + docs only).

Scans README.md and docs/ (excluding docs/examples). Package code (mdm_engine) may
contain domain terms until full quarantine; this test locks doc drift.
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
EXCLUDE = [r"docs[/\\]examples[/\\]", r"docs[/\\]PUBLIC_RELEASE_GUIDE\.md", r"docs[/\\]TERMINOLOGY\.md", r"tests/.*"]


def _find_files(repo_root: Path) -> list[Path]:
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
                    if not any(re.search(pat, rel, re.IGNORECASE) for pat in EXCLUDE):
                        files.append(f)
    return files


def test_invariant_0_docs_domain_agnostic() -> None:
    """README and docs (excluding examples) must not contain domain vocabulary."""
    repo_root = Path(__file__).resolve().parent.parent
    violations = []
    for f in _find_files(repo_root):
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
