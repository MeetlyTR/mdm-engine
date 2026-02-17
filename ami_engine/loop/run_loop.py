"""Event loop: latency measurement, PacketV2, trace, MDM+DMC, execution."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ami_engine.adapters.base import MarketDataSource, Broker
from ami_engine.features.feature_builder import build_features
from ami_engine.execution.executor import Executor
from ami_engine.trace.trace_logger import TraceLogger
from ami_engine.security.redaction import redact_dict
from ami_engine.security.audit import AuditLogger
from decision_schema.packet_v2 import PacketV2
from decision_schema.types import Action, FinalDecision as FinalAction
from ami_engine.mdm.decision_engine import DecisionEngine
from ami_engine.mdm.position_manager import PositionManager
from dmc_core.dmc.risk_policy import RiskPolicy
from dmc_core.dmc.modulator import modulate
from dmc_core.metrics.pnl_metrics import max_drawdown, adverse_selection_avg_ticks


def run_loop(
    run_id: str,
    source: MarketDataSource,
    broker: Broker,
    decision_engine: DecisionEngine,
    risk_policy: RiskPolicy,
    position_manager: PositionManager,
    run_dir: Path,
    market_id: str,
    vol_window: int = 50,
    mid_history_max: int = 200,
    window_5m_steps: int = 300,
    tick_size: float = 0.01,
    sigma_short_steps: int = 20,
    sigma_long_steps: int = 100,
    fee_ticks: float = 0.0,
    slippage_ticks: float = 0.5,
    buffer_ticks: float = 0.5,
    post_fill_cooldown_ms: int = 0,
    enable_quote_budget: bool = False,
    quote_window_ms: int = 60_000,
    quote_cap_per_window: int = 25,
    quote_budget_cooldown_ms: int = 10_000,
) -> dict[str, Any]:
    """
    Run until source exhausts. Each step: get event -> features -> MDM -> DMC -> execute -> trace.
    Returns summary: action_counts, latencies, equity, max_drawdown, etc.
    """
    run_dir = Path(run_dir)
    trace_logger = TraceLogger(run_dir)
    audit_logger = AuditLogger(run_dir)
    executor = Executor(broker)

    action_counts: dict[str, int] = {}
    latencies_ms: list[int] = []
    mid_history: list[float] = []
    mid_series: list[tuple[int, float]] = []  # (ts_ms, mid) for adverse_selection, keep ~70s
    spread_history: list[float] = []
    depth_history: list[float] = []
    staleness_history: list[int] = []
    step = 0
    last_event_ts_ms = 0
    cancel_timestamps_ms: list[int] = []  # time-windowed cancel count (dt_ms-aware)
    errors_in_window = 0
    recent_failures = 0
    throttle_refresh_until_ms = 0
    adverse_cooldown_until_ms = 0
    cancel_rate_triggered_count = 0
    throttle_hold_steps = 0
    orders_submitted = 0
    orders_canceled = 0
    cooldown_until_ms = 0
    hold_reason_counts: dict[str, int] = {}
    mismatch_reason_counts: dict[str, int] = {}
    adverse_15_ticks_last = 0.0
    adverse_60_ticks_last = 0.0
    quote_timestamps_ms: list[int] = []
    quote_budget_until_ms = 0
    initial_equity: float | None = None
    consecutive_loss_streak = 0
    streak_cooldown_until_ms = 0
    open_orders_count = 0
    ops_cooldown_until_ms = 0
    stopped_reason: str | None = None

    try:
        _live_fetch_retries = 3
        _live_fetch_backoff_sec = [0.5, 1.0, 2.0]

        while True:
            t0 = time.perf_counter()
            event = None
            last_exc = None
            for attempt in range(_live_fetch_retries):
                try:
                    event = source.next_event()
                    break
                except Exception as e:
                    last_exc = e
                    if attempt < _live_fetch_retries - 1:
                        time.sleep(_live_fetch_backoff_sec[min(attempt, len(_live_fetch_backoff_sec) - 1)])
            if event is None and last_exc is not None:
                hold_reason_counts["live_fetch_error"] = hold_reason_counts.get("live_fetch_error", 0) + 1
                break
            if event is None:
                break

            now_ms = event.get("ts_ms", step)
            last_event_ts_ms = now_ms
            mid = event.get("mid", (event.get("bid", 0) + event.get("ask", 0)) / 2.0)
            bid = event.get("bid", 0.0)
            ask = event.get("ask", 0.0)
            depth = event.get("bid_depth", 0.0) + event.get("ask_depth", 0.0)
            spread = max(0.0, ask - bid) if (bid and ask) else 0.0

            mid_history.append(mid)
            if len(mid_history) > mid_history_max:
                mid_history.pop(0)
            mid_series.append((now_ms, mid))
            mid_series[:] = [(t, m) for t, m in mid_series if t >= now_ms - 70_000]
            spread_history.append(spread)
            if len(spread_history) > window_5m_steps:
                spread_history.pop(0)
            depth_history.append(depth)
            if len(depth_history) > window_5m_steps:
                depth_history.pop(0)
            staleness_ms = now_ms - last_event_ts_ms
            staleness_history.append(staleness_ms)
            if len(staleness_history) > window_5m_steps:
                staleness_history.pop(0)

            # Features (5m regime, weighted imbalance, microprice, vwap, pressure, sigma_spike_z, cost_ticks)
            feats = build_features(
                bid=bid,
                ask=ask,
                bid_depth=event.get("bid_depth", 0.0),
                ask_depth=event.get("ask_depth", 0.0),
                top_n_bids=None,
                top_n_asks=None,
                mid_history=mid_history,
                vol_window=vol_window,
                last_event_ts_ms=last_event_ts_ms,
                now_ms=now_ms,
                spread_history=spread_history,
                depth_history=depth_history,
                staleness_history=staleness_history,
                window_5m_steps=window_5m_steps,
                tick_size=tick_size,
                sigma_short_steps=sigma_short_steps,
                sigma_long_steps=sigma_long_steps,
                fee_ticks=fee_ticks,
                slippage_ticks=slippage_ticks,
                buffer_ticks=buffer_ticks,
            )

            # 5m regime filter: trade only when vol/spread/depth within bounds
            sigma_5m = feats.get("sigma_5m", feats["sigma"])
            spread_med_5m = feats.get("spread_med_5m", spread)
            spread_med_5m_bps = (spread_med_5m / mid * 10000.0) if mid >= 1e-9 else 0.0
            depth_p10_5m = feats.get("depth_p10_5m", depth)
            regime_ok = (
                sigma_5m <= getattr(risk_policy, "sigma_5m_max", 0.02)
                and spread_med_5m_bps <= getattr(risk_policy, "spread_med_5m_max_bps", 100.0)
                and depth_p10_5m >= getattr(risk_policy, "depth_p10_5m_min", 50.0)
            )
            min_depth_p10_market = getattr(risk_policy, "min_depth_p10_market", 0.0)
            market_ok = (min_depth_p10_market <= 0.0) or (depth_p10_5m >= min_depth_p10_market)

            # Paper broker: set book for fill sim
            if hasattr(broker, "set_book"):
                broker.set_book(event)

            state = broker.get_state()
            positions = state.get("positions", {})
            inventory = positions.get(market_id, 0.0)
            current_exposure_usd = state.get("exposure_usd", 0.0)
            daily_realized_pnl_usd = state.get("realized_pnl", 0.0)
            equity_curve = state.get("equity_curve", [])
            current_equity = equity_curve[-1] if equity_curve else (state.get("cash", 0.0) + state.get("realized_pnl", 0.0) + current_exposure_usd)
            if initial_equity is None:
                initial_equity = current_equity
            equity_floor_usd = getattr(risk_policy, "equity_floor_usd", 0.0)
            max_drawdown_stop_usd = getattr(risk_policy, "max_drawdown_stop_usd", 0.0)
            if equity_floor_usd > 0 and current_equity <= equity_floor_usd:
                stopped_reason = "equity_floor"
                break
            if max_drawdown_stop_usd > 0 and initial_equity is not None and current_equity < initial_equity - max_drawdown_stop_usd:
                stopped_reason = "drawdown_stop"
                break

            # Cancel-rate: time-windowed (son cancel_window_ms içinde kaç cancel)
            cancel_window_ms = getattr(risk_policy, "cancel_window_ms", 10_000)
            cancel_timestamps_ms[:] = [t for t in cancel_timestamps_ms if t >= now_ms - cancel_window_ms]
            cancels_in_window = len(cancel_timestamps_ms)

            # Quote budget limiter: cap QUOTEs per window (sim_balanced 25–80 target)
            quote_timestamps_ms[:] = [t for t in quote_timestamps_ms if t >= now_ms - quote_window_ms]
            if enable_quote_budget and len(quote_timestamps_ms) >= quote_cap_per_window:
                quote_budget_until_ms = now_ms + quote_budget_cooldown_ms

            # Adverse selection (15s / 60s) for DMC guard
            adverse_15_ticks = 0.0
            adverse_60_ticks = 0.0
            if hasattr(broker, "get_fill_records"):
                fill_records = broker.get_fill_records()
                if fill_records and mid_series:
                    adverse_15_ticks = adverse_selection_avg_ticks(
                        fill_records, mid_series, 15_000, tick_size
                    )
                    adverse_60_ticks = adverse_selection_avg_ticks(
                        fill_records, mid_series, 60_000, tick_size
                    )
            adverse_15_ticks_last = adverse_15_ticks
            adverse_60_ticks_last = adverse_60_ticks

            # MDM (regime_ok false -> HOLD); pass features dict
            features = {
                "mid": feats["mid"],
                "bid_depth": feats["bid_depth"],
                "ask_depth": feats["ask_depth"],
                "depth": feats["depth"],
                "sigma": feats["sigma"],
                "inventory": inventory,
                "position_manager": position_manager,
                "market_id": market_id,
                "now_ms": now_ms,
                "current_exposure_usd": current_exposure_usd,
                "spread_ok": feats["spread_bps"] < risk_policy.max_spread_bps,
                "depth_ok": feats["depth"] >= risk_policy.min_depth,
                "sigma_stable": feats["sigma"] < 0.05,
                "regime_ok": regime_ok,
                "market_ok": market_ok,
                **feats,  # Include all feature fields
            }
            proposal = decision_engine.propose(features)

            # DMC context (adverse_selection_avg, sigma_spike_z, cost_ticks, tp_ticks for guards)
            context = {
                "now_ms": now_ms,
                "last_event_ts_ms": last_event_ts_ms,
                "depth": feats["depth"],
                "spread_bps": feats["spread_bps"],
                "current_total_exposure_usd": current_exposure_usd,
                "abs_inventory": abs(inventory),
                "cancels_in_window": cancels_in_window,
                "daily_realized_pnl_usd": daily_realized_pnl_usd,
                "errors_in_window": errors_in_window,
                "steps_in_window": step + 1,
                "recent_failures": recent_failures,
                "adverse_selection_avg": 0.0,
                "adverse_15_ticks": adverse_15_ticks,
                "adverse_60_ticks": adverse_60_ticks,
                "sigma_spike_z": feats.get("sigma_spike_z", 0.0),
                "cost_ticks": feats.get("cost_ticks", 0.0),
                "tp_ticks": getattr(risk_policy, "tp_ticks", 1.0),
            }
            final_action, mismatch = modulate(proposal, risk_policy, context)
            if mismatch.flags and "cancel_rate" in mismatch.flags:
                cancel_rate_triggered_count += 1
            if mismatch.flags and "cancel_rate" in mismatch.flags and mismatch.throttle_refresh_ms:
                throttle_refresh_until_ms = now_ms + mismatch.throttle_refresh_ms

            adverse_cooldown_ms = getattr(risk_policy, "adverse_cooldown_ms", 0)
            if mismatch.flags and "adverse_selection" in mismatch.flags and adverse_cooldown_ms > 0:
                adverse_cooldown_until_ms = now_ms + adverse_cooldown_ms
                executor.run(FinalAction(action=Action.CANCEL_ALL), market_id, mid=feats["mid"])

            throttle_forced_hold = (
                throttle_refresh_until_ms > 0
                and now_ms < throttle_refresh_until_ms
                and proposal.action == Action.QUOTE
            )
            adverse_cooldown_hold = (
                adverse_cooldown_until_ms > 0
                and now_ms < adverse_cooldown_until_ms
                and proposal.action == Action.QUOTE
            )
            quote_budget_hold = (
                enable_quote_budget
                and quote_budget_until_ms > 0
                and now_ms < quote_budget_until_ms
                and proposal.action == Action.QUOTE
            )
            if final_action.action == Action.QUOTE and now_ms < throttle_refresh_until_ms:
                final_action = FinalAction(action=Action.HOLD)
            if final_action.action == Action.QUOTE and now_ms < adverse_cooldown_until_ms:
                final_action = FinalAction(action=Action.HOLD)
            if final_action.action == Action.QUOTE and now_ms < quote_budget_until_ms:
                final_action = FinalAction(action=Action.HOLD)
            if final_action.action == Action.QUOTE and now_ms < streak_cooldown_until_ms:
                final_action = FinalAction(action=Action.HOLD)
            if final_action.action == Action.QUOTE and now_ms < ops_cooldown_until_ms:
                final_action = FinalAction(action=Action.HOLD)
            max_open_orders = getattr(risk_policy, "max_open_orders", 0)
            if max_open_orders > 0 and final_action.action == Action.QUOTE and open_orders_count >= max_open_orders:
                final_action = FinalAction(action=Action.HOLD)
            min_order_usd = getattr(risk_policy, "min_order_usd", 0.0)
            if min_order_usd > 0 and final_action.action == Action.QUOTE:
                size_usd = final_action.size_usd if final_action.size_usd is not None else (proposal.size_usd if proposal.size_usd is not None else 0.0)
                if size_usd < min_order_usd:
                    final_action = FinalAction(action=Action.HOLD)
            if final_action.action == Action.QUOTE and now_ms < cooldown_until_ms:
                final_action = FinalAction(action=Action.HOLD)

            realized_pnl_before = state.get("realized_pnl", 0.0)

            # Execute (pass mid for FLATTEN so broker can close at mid and book PnL)
            exec_result = executor.run(final_action, market_id, mid=feats["mid"])

            if final_action.action == Action.FLATTEN:
                position_manager.on_position_closed(market_id)
                state_after = broker.get_state()
                close_pnl = state_after.get("realized_pnl", 0.0) - realized_pnl_before
                if close_pnl < 0:
                    consecutive_loss_streak += 1
                else:
                    consecutive_loss_streak = 0
                max_consec = getattr(risk_policy, "max_consecutive_losses", 0)
                streak_cooldown_ms = getattr(risk_policy, "streak_cooldown_ms", 120_000)
                if max_consec > 0 and consecutive_loss_streak >= max_consec:
                    streak_cooldown_until_ms = now_ms + streak_cooldown_ms
                    executor.run(FinalAction(action=Action.CANCEL_ALL), market_id, mid=feats["mid"])
                    open_orders_count = 0
                else:
                    open_orders_count = 0
            elif final_action.action == Action.CANCEL_ALL:
                open_orders_count = 0
            if final_action.action == Action.QUOTE:
                if exec_result.get("orders"):
                    orders_submitted += len(exec_result["orders"])
                    open_orders_count += min(2, len(exec_result["orders"]))  # bid+ask
                quote_timestamps_ms.append(now_ms)
            n_cancels = exec_result.get("cancels", 0)
            orders_canceled += n_cancels
            for _ in range(n_cancels):
                cancel_timestamps_ms.append(now_ms)
            if final_action.action == Action.CANCEL_ALL:
                open_orders_count = 0

            # Sync PositionManager with broker fills; post-fill cooldown (no quote for X ms)
            if hasattr(broker, "process_fills"):
                fills = broker.process_fills(now_ms)
                for fill_event in fills:
                    fmid = fill_event.get("market_id", market_id)
                    position_manager.register_fill(
                        fmid,
                        fill_event.get("price", feats["mid"]),
                        fill_event.get("size", 0.0),
                        now_ms,
                    )
                if fills and post_fill_cooldown_ms > 0:
                    cooldown_until_ms = now_ms + post_fill_cooldown_ms

            latency_ms = int((time.perf_counter() - t0) * 1000)
            latencies_ms.append(latency_ms)

            # PacketV2 (redact input/external)
            packet = PacketV2(
                run_id=run_id,
                step=step,
                input=redact_dict(event),
                external=redact_dict({**feats, "inventory": inventory}),
                mdm={
                    "action": proposal.action.value,
                    "confidence": proposal.confidence,
                    "reasons": proposal.reasons,
                },
                final_action={
                    "action": final_action.action.value,
                    "bid_quote": final_action.bid_quote,
                    "ask_quote": final_action.ask_quote,
                    "size_usd": final_action.size_usd,
                },
                latency_ms=latency_ms,
                mismatch={"flags": mismatch.flags, "reason_codes": mismatch.reason_codes} if mismatch.flags else None,
            )
            trace_logger.write(packet)

            action_key = final_action.action.value
            action_counts[action_key] = action_counts.get(action_key, 0) + 1
            loss_streak_hold = (
                streak_cooldown_until_ms > 0
                and now_ms < streak_cooldown_until_ms
                and proposal.action == Action.QUOTE
            )
            ops_cooldown_hold = (
                ops_cooldown_until_ms > 0
                and now_ms < ops_cooldown_until_ms
                and proposal.action == Action.QUOTE
            )
            if final_action.action == Action.HOLD:
                if throttle_forced_hold:
                    throttle_hold_steps += 1
                    hold_reason_counts["throttle_active"] = hold_reason_counts.get("throttle_active", 0) + 1
                elif adverse_cooldown_hold:
                    hold_reason_counts["adverse_cooldown"] = hold_reason_counts.get("adverse_cooldown", 0) + 1
                elif quote_budget_hold:
                    hold_reason_counts["quote_budget"] = hold_reason_counts.get("quote_budget", 0) + 1
                elif loss_streak_hold:
                    hold_reason_counts["loss_streak"] = hold_reason_counts.get("loss_streak", 0) + 1
                elif ops_cooldown_hold:
                    hold_reason_counts["ops_cooldown"] = hold_reason_counts.get("ops_cooldown", 0) + 1
                elif mismatch.flags:
                    for f in mismatch.flags:
                        hold_reason_counts[f] = hold_reason_counts.get(f, 0) + 1
                    for r in mismatch.reason_codes:
                        mismatch_reason_counts[r] = mismatch_reason_counts.get(r, 0) + 1
                else:
                    reason = proposal.reasons[0] if proposal.reasons else "mdm_hold"
                    hold_reason_counts[reason] = hold_reason_counts.get(reason, 0) + 1
            step += 1
    finally:
        trace_logger.close()
        audit_logger.log("run_complete", {"run_id": run_id, "steps": step})
        audit_logger.close()

    state = broker.get_state()
    equity_curve = state.get("equity_curve", [])
    if not equity_curve and state.get("cash") is not None:
        equity_curve = [state.get("cash", 0.0) + state.get("realized_pnl", 0.0)]

    summary = {
        "run_id": run_id,
        "steps": step,
        "action_counts": action_counts,
        "avg_latency_ms": sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0,
        "final_equity": equity_curve[-1] if equity_curve else 0.0,
        "realized_pnl": state.get("realized_pnl", 0.0),
        "max_drawdown": max_drawdown(equity_curve),
        "throttle_events": 0,
        "error_count": 0,
        "orders_submitted": orders_submitted,
        "orders_canceled": orders_canceled,
        "fills_count": state.get("fills_count", 0),
        "position_open_count": state.get("position_open_count", 0),
        "position_close_count": state.get("position_close_count", 0),
        "hold_reason_counts": hold_reason_counts,
        "mismatch_reason_counts": mismatch_reason_counts,
        "cancel_rate_triggered_count": cancel_rate_triggered_count,
        "throttle_hold_steps": throttle_hold_steps,
        "adverse_15_ticks": adverse_15_ticks_last,
        "adverse_60_ticks": adverse_60_ticks_last,
        "stopped_reason": stopped_reason,
    }
    return summary
