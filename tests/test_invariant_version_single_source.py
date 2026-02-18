"""INV-V1: Version single-source - pyproject version must match package __version__."""

import tomllib
from pathlib import Path

import mdm_engine


def test_version_single_source() -> None:
    """pyproject.toml version must equal mdm_engine.__version__ (no drift)."""
    repo_root = Path(__file__).resolve().parent.parent
    with (repo_root / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)
    pyproject_version = data["project"]["version"]
    assert mdm_engine.__version__ == pyproject_version, (
        "Version drift: pyproject.toml has %r, mdm_engine.__version__ is %r"
        % (pyproject_version, mdm_engine.__version__)
    )
