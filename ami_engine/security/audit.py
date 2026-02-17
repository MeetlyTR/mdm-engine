"""Security audit: write to ./runs/<run_id>/security_audit.jsonl; no secrets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AuditLogger:
    """Append audit events (redacted) to security_audit.jsonl."""

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.run_dir / "security_audit.jsonl"
        self._file = open(self.path, "a", encoding="utf-8")

    def log(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """Write one audit line; payload must not contain secrets."""
        line = json.dumps({"event": event_type, **(payload or {})}, default=str) + "\n"
        self._file.write(line)
        self._file.flush()

    def close(self) -> None:
        self._file.close()
