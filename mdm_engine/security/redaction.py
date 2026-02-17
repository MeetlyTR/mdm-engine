"""Redact secrets from dicts/logs; never log keys, tokens, raw payloads."""

from __future__ import annotations

import re
from typing import Any

REDACT_KEYS = frozenset(
    {
        "api_key", "apikey", "api-key", "secret", "password", "token",
        "authorization", "auth", "private_key", "privatekey",
        "signature", "raw_payload", "headers",
    }
)


def _redact_value(_: Any) -> str:
    return "[REDACTED]"


def redact_dict(d: dict[str, Any], key_subset: frozenset[str] | None = None) -> dict[str, Any]:
    """Copy dict with sensitive keys replaced by [REDACTED]; case-insensitive match."""
    keys = key_subset or REDACT_KEYS
    out: dict[str, Any] = {}
    for k, v in d.items():
        if re.sub(r"[-_\s]", "", k.lower()) in {re.sub(r"[-_\s]", "", x.lower()) for x in keys}:
            out[k] = _redact_value(v)
        elif isinstance(v, dict):
            out[k] = redact_dict(v, keys)
        elif isinstance(v, list):
            out[k] = [redact_dict(x, keys) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out
