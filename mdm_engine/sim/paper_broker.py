"""Paper broker: synthetic fills, cash, per-market inventory, cost basis, PnL, counters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mdm_engine.adapters.base import Broker
from mdm_engine.sim.microstructure_sim import MicrostructureSim, BookSnapshot


@dataclass
class PaperState:
    cash: float = 0.0
    positions: dict[str, float] = field(default_factory=dict)
    cost_basis: dict[str, float] = field(default_factory=dict)  # cost paid for current position
    equity_curve: list[float] = field(default_factory=list)
    realized_pnl: float = 0.0
    fill_events: list[dict] = field(default_factory=list)
    # Cumulative counters for summary
    fills_count: int = 0
    position_open_count: int = 0
    position_close_count: int = 0


class PaperBroker(Broker):
    """Simulate fills from book; track cash, inventory, cost basis, PnL, lifecycle counters."""

    def __init__(
        self,
        initial_cash: float = 1000.0,
        sim: MicrostructureSim | None = None,
    ):
        self._state = PaperState(cash=initial_cash)
        self._sim = sim or MicrostructureSim()
        self._book: dict[str, Any] = {}
        self._fill_records: list[dict[str, Any]] = []  # persistent for adverse_selection (fill_ts_ms, fill_mid, side, qty)

    def set_book(self, book: dict[str, Any]) -> None:
        """Update current book snapshot for fill simulation."""
        self._book = book

    def get_state(self) -> dict[str, Any]:
        state = self._state
        positions = dict(state.positions)
        exposure = sum(abs(v) * (self._book.get("mid") or 0.5) for v in positions.values())
        return {
            "cash": state.cash,
            "positions": positions,
            "realized_pnl": state.realized_pnl,
            "equity_curve": list(state.equity_curve),
            "exposure_usd": exposure,
            "fills_count": state.fills_count,
            "position_open_count": state.position_open_count,
            "position_close_count": state.position_close_count,
        }

    def submit_order(
        self,
        market_id: str,
        side: str,
        price: float,
        size_usd: float,
        post_only: bool,
    ) -> dict[str, Any]:
        """Simulate fill; update position, cost_basis, and lifecycle counters."""
        if not self._book:
            return {"order_id": f"paper-{market_id}-{side}", "filled": False}
        book = BookSnapshot(
            bid=self._book["bid"],
            ask=self._book["ask"],
            bid_depth=self._book.get("bid_depth", 100.0),
            ask_depth=self._book.get("ask_depth", 100.0),
            ts_ms=self._book.get("ts_ms", 0),
        )
        filled, fill_price = self._sim.try_fill(
            side, price, size_usd, book, post_only,
            imbalance=self._book.get("imbalance", 0.0),
            depth=book.bid_depth + book.ask_depth,
        )
        if filled and fill_price > 0:
            size = size_usd / fill_price
            if side == "ask":
                size = -size
            prev_pos = self._state.positions.get(market_id, 0.0)
            prev_cost = self._state.cost_basis.get(market_id, 0.0)
            self._state.positions[market_id] = prev_pos + size
            self._state.cost_basis[market_id] = prev_cost + fill_price * size
            self._state.fills_count += 1
            if prev_pos == 0.0 and prev_pos + size != 0.0:
                self._state.position_open_count += 1
            ts_ms = self._book.get("ts_ms", 0)
            fill_mid = (self._book.get("bid", 0.0) + self._book.get("ask", 0.0)) / 2.0 if self._book.get("bid") is not None else fill_price
            self._state.fill_events.append({
                "market_id": market_id,
                "side": side,
                "price": fill_price,
                "size_usd": size_usd,
                "size": size,
            })
            self._fill_records.append({
                "fill_ts_ms": ts_ms,
                "fill_mid": fill_mid,
                "side": side,
                "qty": size_usd,
                "market_id": market_id,
            })
        return {"order_id": f"paper-{market_id}-{side}", "filled": filled}

    def flatten_position(self, market_id: str, mid: float | None = None) -> float:
        """Close position at mid; book realized PnL. Returns PnL from this flatten."""
        pos = self._state.positions.get(market_id, 0.0)
        cost = self._state.cost_basis.get(market_id, 0.0)
        if mid is None:
            mid = self._book.get("mid", 0.5)
        pnl = pos * mid - cost
        self._state.realized_pnl += pnl
        if pos != 0.0:
            self._state.position_close_count += 1
        self._state.positions.pop(market_id, None)
        self._state.cost_basis.pop(market_id, None)
        return pnl

    def get_fill_records(self) -> list[dict[str, Any]]:
        """Return copy of persistent fill records for adverse_selection (fill_ts_ms, fill_mid, side, qty)."""
        return list(self._fill_records)

    def cancel_order(self, order_id: str) -> bool:
        return True

    def cancel_all(self, market_id: str | None = None) -> int:
        return 1

    def process_fills(self, now_ms: int) -> list[dict[str, Any]]:
        """Return recent fills and update equity curve."""
        events = list(self._state.fill_events)
        self._state.fill_events.clear()
        equity = self._state.cash + self._state.realized_pnl
        for m, pos in self._state.positions.items():
            mid = self._book.get("mid", 0.5)
            equity += pos * mid
        self._state.equity_curve.append(equity)
        return events
