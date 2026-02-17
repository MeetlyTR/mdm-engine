"""Reference PositionManager: TP/SL/time stops (reference implementation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PositionState:
    """Position state for a market."""
    fill_price: float
    fill_size: float
    fill_time_ms: int


class PositionManager:
    """
    Reference PositionManager: manages positions with TP/SL/time stops.
    
    This is a reference implementation. For production, use a private implementation
    or integrate with your position management system.
    """
    
    def __init__(
        self,
        tp_ticks: float = 1.0,
        sl_ticks: float = 3.0,
        tick_size: float = 0.01,
        T_max_ms: int = 120000,
    ):
        self.tp_ticks = tp_ticks
        self.sl_ticks = sl_ticks
        self.tick_size = tick_size
        self.T_max_ms = T_max_ms
        self._positions: dict[str, PositionState] = {}
    
    def register_fill(self, market_id: str, price: float, size: float, now_ms: int) -> None:
        """Register a fill (position opened)."""
        self._positions[market_id] = PositionState(
            fill_price=price,
            fill_size=size,
            fill_time_ms=now_ms,
        )
    
    def should_flatten(self, market_id: str, current_mid: float, now_ms: int) -> tuple[bool, str]:
        """
        Check if position should be flattened.
        
        Returns:
            (should_flatten: bool, reason: str)
        """
        if market_id not in self._positions:
            return False, ""
        
        pos = self._positions[market_id]
        
        # Time stop
        if now_ms - pos.fill_time_ms >= self.T_max_ms:
            return True, "time_stop"
        
        # TP/SL (simplified: assumes long position)
        price_diff_ticks = (current_mid - pos.fill_price) / self.tick_size
        
        if price_diff_ticks >= self.tp_ticks:
            return True, "take_profit"
        
        if price_diff_ticks <= -self.sl_ticks:
            return True, "stop_loss"
        
        return False, ""
    
    def on_position_closed(self, market_id: str) -> None:
        """Called when position is closed."""
        self._positions.pop(market_id, None)
    
    def unrealized_pnl(self, market_id: str, current_mid: float) -> float:
        """Compute unrealized PnL (simplified)."""
        if market_id not in self._positions:
            return 0.0
        pos = self._positions[market_id]
        return (current_mid - pos.fill_price) * pos.fill_size
