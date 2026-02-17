"""JSONL writer for PacketV2; path = ./runs/<run_id>/traces.jsonl."""

from __future__ import annotations

import json
from pathlib import Path

from decision_schema.packet_v2 import PacketV2


class TraceLogger:
    """Append PacketV2 as JSONL (input/external must be pre-redacted)."""

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.run_dir / "traces.jsonl"
        self._file = open(self.path, "a", encoding="utf-8")

    def write(self, packet: PacketV2) -> None:
        line = json.dumps(packet.to_dict(), default=str) + "\n"
        self._file.write(line)
        self._file.flush()

    def close(self) -> None:
        self._file.close()
