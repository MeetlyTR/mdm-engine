"""MarketDataSource and Broker abstract interfaces."""

from abc import ABC, abstractmethod
from typing import Any


class MarketDataSource(ABC):
    """Source of market events (book snapshots, etc.)."""

    @abstractmethod
    def next_event(self) -> dict[str, Any] | None:
        """Return next event or None if exhausted."""
        ...


class Broker(ABC):
    """Broker interface: submit/cancel orders, get state (no secrets in interface)."""

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        """Cash, positions, exposure, etc. (redacted)."""
        ...

    @abstractmethod
    def submit_order(
        self,
        market_id: str,
        side: str,
        price: float,
        size_usd: float,
        post_only: bool,
    ) -> dict[str, Any]:
        """Submit order; return result (order_id or error)."""
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order; return True if accepted."""
        ...

    @abstractmethod
    def cancel_all(self, market_id: str | None = None) -> int:
        """Cancel all (optionally for market); return count."""
        ...

    @abstractmethod
    def process_fills(self, now_ms: int) -> list[dict[str, Any]]:
        """Process pending fills up to now_ms; return list of fill events."""
        ...
