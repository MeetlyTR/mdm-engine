"""Post-only quoting: cancel/replace only when needed; order aging; min requote."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mdm_engine.adapters.base import Broker


@dataclass
class OrderRecord:
    """Track order for cancel/replace."""

    order_id: str
    side: str
    price: float
    size_usd: float
    created_ms: int


class OrderManager:
    """Cancel/replace when quote changes; avoid over-cancel via refresh_ms and min_requote_ticks."""

    def __init__(
        self,
        broker: Broker,
        refresh_ms: int = 500,
        min_requote_ticks: float = 1.0,
        tick_size: float = 0.01,
        order_ttl_ms: int = 0,
        post_fill_cooldown_ms: int = 0,
        max_replacements_per_min: int = 0,
    ):
        self.broker = broker
        self.refresh_ms = refresh_ms
        self.min_requote_ticks = min_requote_ticks
        self.tick_size = max(tick_size, 1e-12)
        self.order_ttl_ms = order_ttl_ms
        self.post_fill_cooldown_ms = post_fill_cooldown_ms
        self.max_replacements_per_min = max_replacements_per_min
        self.orders: dict[str, OrderRecord] = {}
        self.last_refresh_ms: int = 0
        self._last_bid: float | None = None
        self._last_ask: float | None = None

    def order_stale(self, now_ms: int) -> bool:
        """True if current quote is older than order_ttl_ms (0 = never stale)."""
        if self.order_ttl_ms <= 0:
            return False
        return (now_ms - self.last_refresh_ms) >= self.order_ttl_ms

    def set_quotes(
        self,
        market_id: str,
        bid_quote: float,
        ask_quote: float,
        size_usd: float,
        now_ms: int,
        effective_refresh_ms: int | None = None,
    ) -> dict[str, Any]:
        """
        Replace only if |new - old| > min_requote_ticks * tick_size (or no previous quote).
        Use effective_refresh_ms when throttled (e.g. from DMC cancel_rate guard).
        """
        refresh_ms = effective_refresh_ms if effective_refresh_ms is not None else self.refresh_ms
        min_move = self.min_requote_ticks * self.tick_size
        skip_requote = False
        force_replace = self.order_stale(now_ms)
        if self._last_bid is not None and self._last_ask is not None and not force_replace:
            if abs(bid_quote - self._last_bid) < min_move and abs(ask_quote - self._last_ask) < min_move:
                skip_requote = True
            if (now_ms - self.last_refresh_ms) < refresh_ms:
                skip_requote = True
        if skip_requote:
            return {"cancel_count": 0, "submitted": 0, "skipped": True}
        self.broker.cancel_all(market_id)
        self.broker.submit_order(market_id, "bid", bid_quote, size_usd, True)
        self.broker.submit_order(market_id, "ask", ask_quote, size_usd, True)
        self.last_refresh_ms = now_ms
        self._last_bid = bid_quote
        self._last_ask = ask_quote
        return {"cancel_count": 1, "submitted": 2, "skipped": False}

    def cancel_all(self, market_id: str | None = None) -> int:
        return self.broker.cancel_all(market_id)
