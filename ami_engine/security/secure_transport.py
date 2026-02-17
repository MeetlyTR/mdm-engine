"""Wrapper for HTTP/WS: enforces rate limit, backoff, redaction. Stub for SIM."""

from ami_engine.security.rate_limit import RateLimiter, backoff_with_jitter
from ami_engine.security.redaction import redact_dict


class SecureTransport:
    """Centralize retry policy, circuit breaker, redaction for any live client."""

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        max_retries: int = 3,
    ):
        self.rate_limiter = rate_limiter or RateLimiter(rate=1.0, capacity=10)
        self.max_retries = max_retries

    def prepare_outgoing(self, payload: dict) -> dict:
        """Redact before sending to logs/traces (not before sending to API)."""
        return redact_dict(payload)
