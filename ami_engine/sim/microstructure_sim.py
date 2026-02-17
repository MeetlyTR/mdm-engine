"""Simulate book: mid random walk, spread, depth, fills with slippage."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class BookSnapshot:
    bid: float
    ask: float
    bid_depth: float
    ask_depth: float
    ts_ms: int


class MicrostructureSim:
    """Generate book updates; random walk mid, spread/depth dynamics."""

    def __init__(
        self,
        mid0: float = 0.5,
        tick_size: float = 0.01,
        spread_min: float = 0.02,
        vol: float = 0.001,
        seed: int | None = None,
        fee_bps: float = 0.0,
        dt_ms: int = 100,
    ):
        self.mid = mid0
        self.tick_size = tick_size
        self.spread_min = spread_min
        self.vol = vol
        self.rng = random.Random(seed)
        self.fee_bps = fee_bps
        self.dt_ms = max(1, dt_ms)
        self._ts_ms = 0

    def step(self) -> BookSnapshot:
        """One step: evolve mid, spread, depth; return snapshot. Time advances by dt_ms."""
        self._ts_ms += self.dt_ms
        self.mid = max(0.01, self.mid + self.rng.gauss(0, self.vol))
        spread = self.spread_min + self.rng.uniform(0, 0.02)
        half = spread / 2.0
        bid = round((self.mid - half) / self.tick_size) * self.tick_size
        ask = round((self.mid + half) / self.tick_size) * self.tick_size
        if ask <= bid:
            ask = bid + self.tick_size
        bid_depth = max(10.0, 100.0 + self.rng.gauss(0, 20))
        ask_depth = max(10.0, 100.0 + self.rng.gauss(0, 20))
        return BookSnapshot(bid=bid, ask=ask, bid_depth=bid_depth, ask_depth=ask_depth, ts_ms=self._ts_ms)

    def try_fill(
        self,
        side: str,
        price: float,
        size_usd: float,
        book: BookSnapshot,
        post_only: bool,
        imbalance: float = 0.0,
        depth: float = 200.0,
    ) -> tuple[bool, float]:
        """
        If order crosses: post-only rejects; otherwise fill with slippage.
        If post-only inside spread: fill with prob from depth + |imbalance| (so sim sees fills).
        """
        # Base prob for post-only inside spread (0.45 for SIM calibration; can tighten for live)
        depth_factor = min(0.4, (depth / 300.0) * 0.3)
        imb_factor = min(0.3, abs(imbalance) * 0.5)
        base_prob = 0.45 + depth_factor + imb_factor  # ~0.45–0.95

        if side == "bid":
            if price >= book.ask:
                if post_only:
                    return False, 0.0
                fill = book.ask + self.tick_size * 0.5
                return True, fill
            if price >= book.bid:
                if self.rng.random() < base_prob:
                    return True, price
                # Mid crossed our bid (aggressor would hit us): partial fill chance
                if self.rng.random() < 0.2:
                    return True, price
        else:
            if price <= book.bid:
                if post_only:
                    return False, 0.0
                fill = book.bid - self.tick_size * 0.5
                return True, fill
            if price <= book.ask:
                if self.rng.random() < base_prob:
                    return True, price
                if self.rng.random() < 0.2:
                    return True, price
        return False, 0.0
