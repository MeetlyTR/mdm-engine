"""Execute final_action via broker; no secrets."""

from __future__ import annotations

from typing import Any

from ami_engine.adapters.base import Broker
from decision_schema.types import Action, FinalDecision as FinalAction


def execute(
    broker: Broker,
    final_action: FinalAction,
    market_id: str,
    mid: float | None = None,
) -> dict[str, Any]:
    """Execute final action: QUOTE -> submit bid/ask; FLATTEN -> cancel then close position + PnL."""
    result: dict[str, Any] = {"action": final_action.action.value, "orders": [], "cancels": 0}
    if final_action.action == Action.QUOTE and final_action.bid_quote is not None and final_action.ask_quote is not None and final_action.size_usd:
        broker.submit_order(
            market_id,
            "bid",
            final_action.bid_quote,
            final_action.size_usd,
            final_action.post_only,
        )
        broker.submit_order(
            market_id,
            "ask",
            final_action.ask_quote,
            final_action.size_usd,
            final_action.post_only,
        )
        result["orders"] = ["bid", "ask"]
    elif final_action.action == Action.FLATTEN:
        result["cancels"] = broker.cancel_all(market_id)
        if hasattr(broker, "flatten_position"):
            broker.flatten_position(market_id, mid)
    elif final_action.action == Action.CANCEL_ALL:
        result["cancels"] = broker.cancel_all(market_id)
    elif final_action.action == Action.STOP:
        result["cancels"] = broker.cancel_all(None)
    return result


class Executor:
    """Thin wrapper around execute."""

    def __init__(self, broker: Broker):
        self.broker = broker

    def run(
        self,
        final_action: FinalAction,
        market_id: str,
        mid: float | None = None,
    ) -> dict[str, Any]:
        return execute(self.broker, final_action, market_id, mid)
