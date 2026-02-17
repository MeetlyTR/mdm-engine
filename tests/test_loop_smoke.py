"""Smoke test: run_loop produces traces and summary."""

import tempfile
from pathlib import Path

import pytest


def test_loop_smoke():
    from ami_engine.sim.microstructure_sim import MicrostructureSim
    from ami_engine.sim.synthetic_source import SyntheticSource
    from ami_engine.sim.paper_broker import PaperBroker
    from ami_engine.loop.run_loop import run_loop
    from ami_engine.mdm.decision_engine import DecisionEngine
    from ami_engine.mdm.position_manager import PositionManager
    from dmc_core.dmc.risk_policy import RiskPolicy

    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        sim = MicrostructureSim(mid0=0.5, seed=42)
        source = SyntheticSource(sim, steps=10)
        broker = PaperBroker(initial_cash=1000.0, sim=sim)
        de = DecisionEngine()
        pm = PositionManager(tp_ticks=1.0, sl_ticks=2.0, tick_size=0.01, T_max_ms=60_000)
        rp = RiskPolicy()
        summary = run_loop(
            run_id="test-run",
            source=source,
            broker=broker,
            decision_engine=de,
            risk_policy=rp,
            position_manager=pm,
            run_dir=run_dir,
            market_id="m1",
            vol_window=5,
        )
        assert summary["steps"] == 10
        assert (run_dir / "traces.jsonl").exists()
        assert (run_dir / "security_audit.jsonl").exists()
        assert "action_counts" in summary
        assert "max_drawdown" in summary
