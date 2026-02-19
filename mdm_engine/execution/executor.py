# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""Execute final_action via broker; no secrets."""

from __future__ import annotations

from typing import Any

from mdm_engine.adapters.base import Broker
from decision_schema.types import Action, FinalDecision as FinalAction


def execute(
    broker: Broker,
    final_action: FinalAction,
    market_id: str,
    mid: float | None = None,
) -> dict[str, Any]:
    """Execute final action: ACT -> submit bid/ask; EXIT -> cancel then close; CANCEL -> cancel all."""
    result: dict[str, Any] = {
        "action": final_action.action.value,
        "orders": [],
        "cancels": 0,
    }
    if (
        final_action.action == Action.ACT
        and getattr(final_action, "bid_quote", None) is not None
        and getattr(final_action, "ask_quote", None) is not None
        and getattr(final_action, "size_usd", None)
    ):
        broker.submit_order(
            market_id,
            "bid",
            getattr(final_action, "bid_quote"),
            getattr(final_action, "size_usd", 0),
            getattr(final_action, "post_only", False),
        )
        broker.submit_order(
            market_id,
            "ask",
            getattr(final_action, "ask_quote"),
            getattr(final_action, "size_usd", 0),
            getattr(final_action, "post_only", False),
        )
        result["orders"] = ["bid", "ask"]
    elif final_action.action == Action.EXIT:
        result["cancels"] = broker.cancel_all(market_id)
        if hasattr(broker, "flatten_position"):
            broker.flatten_position(market_id, mid)
    elif final_action.action == Action.CANCEL:
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
