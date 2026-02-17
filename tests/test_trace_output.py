"""Trace output: PacketV2 written as JSONL."""

import tempfile
from pathlib import Path

import pytest
from decision_schema.packet_v2 import PacketV2
from mdm_engine.trace.trace_logger import TraceLogger


def test_trace_logger_writes_jsonl():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        logger = TraceLogger(run_dir)
        packet = PacketV2(
            run_id="r1",
            step=0,
            input={"ts": 1},
            external={"mid": 0.5},
            mdm={"action": "ACT"},
            final_action={"action": "ACT"},
            latency_ms=1,
            mismatch=None,
        )
        logger.write(packet)
        logger.close()
        content = (run_dir / "traces.jsonl").read_text()
        assert "r1" in content
        assert "ACT" in content
