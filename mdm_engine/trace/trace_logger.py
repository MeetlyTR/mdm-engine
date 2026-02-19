# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""JSONL writer for PacketV2; path = ./runs/<run_id>/traces.jsonl."""

from __future__ import annotations

import json
from pathlib import Path

from decision_schema.packet_v2 import PacketV2


class TraceLogger:
    """
    Append PacketV2 as JSONL (input/external must be pre-redacted).

    Performance: Flushes every N writes (default: every write for safety, set flush_every_n for batch).
    """

    def __init__(self, run_dir: Path, flush_every_n: int = 1):
        """
        Initialize trace logger.

        Args:
            run_dir: Directory for traces.jsonl
            flush_every_n: Flush every N writes (1 = flush every write, higher = batch flush)
        """
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.run_dir / "traces.jsonl"
        self._file = open(self.path, "a", encoding="utf-8")
        self._flush_every_n = flush_every_n
        self._write_count = 0

    def write(self, packet: PacketV2) -> None:
        """Write packet to JSONL (flush based on flush_every_n)."""
        line = json.dumps(packet.to_dict(), default=str) + "\n"
        self._file.write(line)
        self._write_count += 1
        if self._write_count >= self._flush_every_n:
            self._file.flush()
            self._write_count = 0

    def flush(self) -> None:
        """Force flush buffer."""
        self._file.flush()

    def close(self) -> None:
        """Close file (flushes before closing)."""
        self.flush()
        self._file.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit (ensures flush and close)."""
        self.close()
