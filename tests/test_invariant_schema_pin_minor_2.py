"""INV: decision-schema dependency pin must be >=0.2,<0.3 (minor=2)."""

import re
import tomllib
from pathlib import Path


def _get_decision_schema_spec(repo_root: Path) -> str | None:
    with (repo_root / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)
    deps = data.get("project", {}).get("dependencies", [])
    for d in deps:
        s = d.strip().lower()
        if "decision-schema" in s or "decision_schema" in s:
            m = re.search(r"decision[-_]schema\s*([^\s]+)", s, re.IGNORECASE)
            return m.group(1).strip("'\"").lower() if m else s
    return None


def test_schema_pin_minor_2() -> None:
    """pyproject must pin decision-schema to >=0.2,<0.3 (tolerant parse)."""
    repo_root = Path(__file__).resolve().parent.parent
    spec = _get_decision_schema_spec(repo_root)
    assert spec is not None, "decision-schema dependency not found in pyproject.toml"
    assert "0.2" in spec and ("<0.3" in spec or ",<0.3" in spec), (
        "decision-schema pin must be >=0.2,<0.3; got %r" % spec
    )
    assert "0.1" not in spec or "0.2" in spec, (
        "decision-schema pin must be 0.2.x range; got %r" % spec
    )
