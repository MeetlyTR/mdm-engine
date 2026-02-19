# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""RateLimiter: token bucket and start_full policy."""

from mdm_engine.security.rate_limit import RateLimiter


def test_start_full_first_allow_succeeds() -> None:
    """start_full=True => tokens start at capacity; first allow() returns True and consumes one."""
    limiter = RateLimiter(rate=1.0, capacity=10, start_full=True)
    assert limiter.tokens == 10.0
    assert limiter.allow() is True
    assert 0 <= limiter.tokens <= limiter.capacity
    assert limiter.tokens < 10.0  # at least one token consumed (cost=1)


def test_start_full_false_default_behavior() -> None:
    """start_full=False (default) => tokens start at 0; first allow() may deny until refill."""
    limiter = RateLimiter(rate=0.1, capacity=10)
    assert limiter.tokens == 0.0
    # First call: refill adds some tokens over 0 time delta; might still be < 1
    # So we only assert invariant: tokens in [0, capacity]
    assert 0 <= limiter.tokens <= limiter.capacity


def test_tokens_clamped_to_capacity() -> None:
    """tokens are always in [0, capacity] after __post_init__."""
    limiter = RateLimiter(rate=1.0, capacity=5, tokens=99.0)
    assert limiter.tokens == 5.0
    limiter2 = RateLimiter(rate=1.0, capacity=5, tokens=-1.0)
    assert limiter2.tokens == 0.0
