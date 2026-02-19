# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""CI-0: Workflow file hygiene — CR=0, LF>=10, no control/embedding Unicode, on:/jobs: line-addressable."""

import re
from pathlib import Path

WORKFLOW_DIR = Path(__file__).resolve().parent.parent / ".github" / "workflows"

FORBIDDEN_UNICODE_RANGES = [
    (0x202A, 0x202E),
    (0x2066, 0x2069),
    (0x2028, 0x2029),
]
FORBIDDEN_UNICODE_CHARS = {0xFEFF, 0x200B, 0x200C, 0x200D, 0x2060}
MIN_EXPECTED_NEWLINES = 10


def _contains_forbidden_unicode(text: str) -> list[str]:
    hits: set[str] = set()
    for ch in text:
        cp = ord(ch)
        if cp in FORBIDDEN_UNICODE_CHARS:
            hits.add(f"U+{cp:04X}")
        for a, b in FORBIDDEN_UNICODE_RANGES:
            if a <= cp <= b:
                hits.add(f"U+{cp:04X}")
    return sorted(hits)


def test_invariant_ci_0_workflow_hygiene() -> None:
    assert WORKFLOW_DIR.exists(), f"{WORKFLOW_DIR} does not exist"
    workflow_files = sorted(
        p
        for p in WORKFLOW_DIR.rglob("*")
        if p.is_file() and p.suffix in {".yml", ".yaml"}
    )
    assert workflow_files, "No workflow YAML files found under .github/workflows"
    failures: list[str] = []
    for path in workflow_files:
        b = path.read_bytes()
        if b"\r" in b:
            cr_count = b.count(b"\r")
            failures.append(f"{path}: contains CR bytes (count={cr_count})")
        lf = b.count(b"\n")
        if lf < MIN_EXPECTED_NEWLINES:
            failures.append(
                f"{path}: too few LF newlines (count={lf}); possible single-line YAML"
            )
        try:
            text = b.decode("utf-8")
        except UnicodeDecodeError as e:
            failures.append(f"{path}: not valid UTF-8 ({e})")
            continue
        hits = _contains_forbidden_unicode(text)
        if hits:
            failures.append(f"{path}: forbidden Unicode present: {', '.join(hits)}")
        if not re.search(r"(?m)^\s*on:\s*$", text) and "on:" not in text:
            failures.append(f"{path}: missing 'on:' key")
        if not re.search(r"(?m)^\s*jobs:\s*$", text) and "jobs:" not in text:
            failures.append(f"{path}: missing 'jobs:' key")
    assert not failures, "CI-0 workflow hygiene violations:\n- " + "\n- ".join(failures)
