"""INVARIANT 2: mdm_engine must not import dmc_core, ops_health_core, eval_calibration_core."""

import ast
from pathlib import Path

FORBIDDEN = {"dmc_core", "ops_health_core", "eval_calibration_core"}


def test_invariant_2_no_cross_core_imports() -> None:
    root = Path(__file__).resolve().parent.parent
    pkg = root / "mdm_engine"
    if not pkg.is_dir():
        return
    violations = []
    for py in pkg.rglob("*.py"):
        if "__pycache__" in str(py) or py.name.startswith("_"):
            continue
        try:
            t = ast.parse(py.read_text(encoding="utf-8"))
        except Exception:
            continue
        rel = py.relative_to(root)
        for node in ast.walk(t):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in FORBIDDEN:
                        violations.append((str(rel), node.lineno or 0, a.name))
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in FORBIDDEN:
                    violations.append((str(rel), node.lineno or 0, node.module))
    assert not violations, "INVARIANT 2: " + str(violations)
