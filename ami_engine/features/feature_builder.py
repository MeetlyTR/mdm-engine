"""Build features from book snapshot: mid, spread, depth, imbalance, sigma, staleness, 5m regime,
   weighted imbalance, microprice, vwap, pressure, sigma_spike_z, cost_ticks."""

from __future__ import annotations

import math
import numpy as np
from typing import Any


def _weighted_imbalance(
    top_n_bids: list[tuple[float, float]],
    top_n_asks: list[tuple[float, float]],
    lambda_decay: float,
    eps: float = 1e-9,
) -> float:
    """I^(w)_t = (B^w - A^w) / (B^w + A^w + eps), w_i = exp(-lambda*(i-1))."""
    Bw = sum(math.exp(-lambda_decay * (i - 1)) * q for i, (_, q) in enumerate(top_n_bids, 1))
    Aw = sum(math.exp(-lambda_decay * (i - 1)) * q for i, (_, q) in enumerate(top_n_asks, 1))
    total = Bw + Aw
    if total < eps:
        return 0.0
    return (Bw - Aw) / total


def _microprice(p_b: float, p_a: float, B1: float, A1: float, eps: float = 1e-9) -> float:
    """mu_t = (p_a*B1 + p_b*A1) / (A1+B1+eps)."""
    denom = A1 + B1 + eps
    return (p_a * B1 + p_b * A1) / denom


def _vwap_pressure(
    top_n_bids: list[tuple[float, float]],
    top_n_asks: list[tuple[float, float]],
    mid: float,
    tick_size: float,
    eps: float = 1e-9,
) -> tuple[float, float, float]:
    """VWAP^b, VWAP^a, pressure_ticks = ((mid-VWAP^b)-(VWAP^a-mid))/tick."""
    if not top_n_bids or not top_n_asks:
        return mid, mid, 0.0
    sum_b = sum(q for _, q in top_n_bids)
    sum_a = sum(q for _, q in top_n_asks)
    vwap_b = sum(p * q for p, q in top_n_bids) / (sum_b + eps)
    vwap_a = sum(p * q for p, q in top_n_asks) / (sum_a + eps)
    pressure_ticks = ((mid - vwap_b) - (vwap_a - mid)) / max(tick_size, 1e-12)
    return vwap_b, vwap_a, pressure_ticks


def _sigma_spike_z(
    mid_history: list[float],
    short_steps: int,
    long_steps: int,
    eps: float = 1e-9,
) -> float:
    """z_t = (sigma_short - mean(sigma_long)) / (std(sigma_long) + eps)."""
    if len(mid_history) < max(short_steps, long_steps) + 2:
        return 0.0
    arr = np.array(mid_history[-long_steps - 2 :], dtype=float)
    arr = np.maximum(arr, eps)
    rets = np.diff(np.log(arr))
    if len(rets) < short_steps:
        return 0.0
    # Rolling sigma over short window for last step
    sigma_short = float(np.std(rets[-short_steps:]))
    # Sigma over full long window for distribution
    sigma_long_vals = [float(np.std(rets[i : i + short_steps])) for i in range(len(rets) - short_steps + 1)]
    if not sigma_long_vals:
        return 0.0
    mu_l = float(np.mean(sigma_long_vals))
    std_l = float(np.std(sigma_long_vals))
    if std_l < eps:
        return 0.0
    return (sigma_short - mu_l) / (std_l + eps)


def _rolling_5m_aggregates(
    mid_history: list[float],
    spread_history: list[float],
    depth_history: list[float],
    staleness_history: list[int],
    window_5m: int,
    eps: float = 1e-9,
) -> dict[str, float]:
    """sigma_5m, spread_med_5m, depth_p10_5m, staleness_max_5m. Empty history -> safe defaults."""
    n = min(len(mid_history), len(spread_history), len(depth_history), window_5m)
    if n < 2:
        return {
            "sigma_5m": 0.0,
            "spread_med_5m": 0.0,
            "depth_p10_5m": float("inf"),
            "staleness_max_5m": 0,
        }
    mids = np.array(mid_history[-n:], dtype=float)
    mids = np.maximum(mids, eps)
    rets = np.diff(np.log(mids))
    sigma_5m = float(np.std(rets)) if len(rets) else 0.0
    spreads = np.array(spread_history[-n:], dtype=float)
    spread_med_5m = float(np.median(spreads))
    depths = np.array(depth_history[-n:], dtype=float)
    depth_p10_5m = float(np.percentile(depths, 10)) if len(depths) else 0.0
    staleness_max_5m = int(max(staleness_history[-n:], default=0))
    return {
        "sigma_5m": sigma_5m,
        "spread_med_5m": spread_med_5m,
        "depth_p10_5m": depth_p10_5m,
        "staleness_max_5m": staleness_max_5m,
    }


def build_features(
    bid: float,
    ask: float,
    bid_depth: float,
    ask_depth: float,
    top_n_bids: list[tuple[float, float]] | None,
    top_n_asks: list[tuple[float, float]] | None,
    mid_history: list[float],
    vol_window: int,
    last_event_ts_ms: int,
    now_ms: int,
    eps: float = 1e-9,
    spread_history: list[float] | None = None,
    depth_history: list[float] | None = None,
    staleness_history: list[int] | None = None,
    window_5m_steps: int = 300,
    imbalance_lambda: float = 0.7,
    tick_size: float = 0.01,
    sigma_short_steps: int = 20,
    sigma_long_steps: int = 100,
    fee_ticks: float = 0.0,
    slippage_ticks: float = 0.5,
    buffer_ticks: float = 0.5,
) -> dict[str, Any]:
    """Mid, spread, depth, imbalance (simple + weighted), sigma, staleness, 5m regime,
       microprice, vwap, pressure, sigma_spike_z, cost_ticks."""
    # Single-level fallback when top_n not provided
    bids_levels = top_n_bids if top_n_bids else [(bid, bid_depth)]
    asks_levels = top_n_asks if top_n_asks else [(ask, ask_depth)]
    if not bids_levels:
        bids_levels = [(bid, bid_depth)]
    if not asks_levels:
        asks_levels = [(ask, ask_depth)]

    mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else bid or ask
    spread = max(0.0, ask - bid)
    depth_bid = sum(q for _, q in bids_levels)
    depth_ask = sum(q for _, q in asks_levels)
    total = depth_bid + depth_ask
    imbalance = (depth_bid - depth_ask) / total if total >= eps else 0.0
    depth = total

    # Weighted imbalance I^(w)
    imbalance_w = _weighted_imbalance(bids_levels, asks_levels, imbalance_lambda, eps)

    # Microprice and alpha in ticks
    p_b, p_a = bid, ask
    B1, A1 = depth_bid, depth_ask
    if bids_levels:
        p_b, B1 = bids_levels[0][0], bids_levels[0][1]
    if asks_levels:
        p_a, A1 = asks_levels[0][0], asks_levels[0][1]
    microprice = _microprice(p_b, p_a, B1, A1, eps)
    microprice_alpha_ticks = (microprice - mid) / max(tick_size, 1e-12)

    # VWAP and pressure
    vwap_bid, vwap_ask, pressure_ticks = _vwap_pressure(
        bids_levels, asks_levels, mid, tick_size, eps
    )

    # Sigma from mid returns
    if len(mid_history) >= 2 and vol_window > 0:
        arr = np.array(mid_history[-vol_window - 1 :], dtype=float)
        arr = np.maximum(arr, eps)
        rets = np.diff(np.log(arr))
        sigma = float(np.std(rets)) if len(rets) else 0.0
    else:
        sigma = 0.0

    # Vol spike z (short vs long window)
    sigma_spike_z = _sigma_spike_z(mid_history, sigma_short_steps, sigma_long_steps, eps)

    cost_ticks = fee_ticks + slippage_ticks + buffer_ticks
    staleness_ms = now_ms - last_event_ts_ms

    out: dict[str, Any] = {
        "mid": mid,
        "bid": bid,
        "ask": ask,
        "spread": spread,
        "spread_bps": spread / mid * 10000.0 if mid >= eps else 0.0,
        "depth": depth,
        "bid_depth": depth_bid,
        "ask_depth": depth_ask,
        "imbalance": imbalance,
        "imbalance_w": imbalance_w,
        "microprice": microprice,
        "microprice_alpha_ticks": microprice_alpha_ticks,
        "vwap_bid": vwap_bid,
        "vwap_ask": vwap_ask,
        "pressure_ticks": pressure_ticks,
        "sigma": sigma,
        "sigma_spike_z": sigma_spike_z,
        "cost_ticks": cost_ticks,
        "staleness_ms": staleness_ms,
        "last_event_ts_ms": last_event_ts_ms,
        "now_ms": now_ms,
    }

    # 5m rolling regime aggregates (for regime filter)
    if spread_history is not None and depth_history is not None and staleness_history is not None:
        agg = _rolling_5m_aggregates(
            mid_history,
            spread_history,
            depth_history,
            staleness_history,
            window_5m_steps,
            eps,
        )
        out["sigma_5m"] = agg["sigma_5m"]
        out["spread_med_5m"] = agg["spread_med_5m"]
        out["depth_p10_5m"] = agg["depth_p10_5m"]
        out["staleness_max_5m"] = agg["staleness_max_5m"]
    else:
        out["sigma_5m"] = sigma
        out["spread_med_5m"] = spread
        out["depth_p10_5m"] = depth
        out["staleness_max_5m"] = staleness_ms

    return out
