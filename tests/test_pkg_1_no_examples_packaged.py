# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""PKG-1: docs/examples must not be included in the built wheel/sdist."""

import subprocess
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("build", reason="build package required for PKG-1")

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_PREFIX = "docs/examples"


def test_pkg_1_no_examples_packaged() -> None:
    dist = REPO_ROOT / "dist"
    if dist.exists():
        for f in dist.iterdir():
            f.unlink()
    else:
        dist.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["python", "-m", "build", "--wheel"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    wheels = list((REPO_ROOT / "dist").glob("*.whl"))
    assert wheels, "No wheel produced"
    found = []
    with zipfile.ZipFile(wheels[0]) as z:
        for name in z.namelist():
            norm = name.replace("\\", "/")
            if norm.startswith(EXAMPLES_PREFIX + "/") or "docs/examples" in norm:
                found.append(norm)
    assert not found, f"PKG-1: docs/examples found in wheel: {found}"
