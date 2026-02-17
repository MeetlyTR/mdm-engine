"""Event generator built on MicrostructureSim; implements MarketDataSource."""

from __future__ import annotations

from mdm_engine.adapters.base import MarketDataSource
from mdm_engine.sim.microstructure_sim import MicrostructureSim


class SyntheticSource(MarketDataSource):
    """Yield book events from MicrostructureSim until steps exhausted."""

    def __init__(self, sim: MicrostructureSim, steps: int):
        self.sim = sim
        self.steps = steps
        self._step = 0

    def next_event(self) -> dict | None:
        if self._step >= self.steps:
            return None
        book = self.sim.step()
        self._step += 1
        return {
            "ts_ms": book.ts_ms,
            "bid": book.bid,
            "ask": book.ask,
            "bid_depth": book.bid_depth,
            "ask_depth": book.ask_depth,
            "mid": (book.bid + book.ask) / 2.0,
        }
