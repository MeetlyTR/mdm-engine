# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""Redact secrets from dicts/logs; never log keys, tokens, raw payloads."""

from __future__ import annotations

import re
from typing import Any

REDACT_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "api-key",
        "secret",
        "password",
        "token",
        "authorization",
        "auth",
        "private_key",
        "privatekey",
        "signature",
        "raw_payload",
        "headers",
    }
)


def _redact_value(_: Any) -> str:
    return "[REDACTED]"


def _normalized_key_set(keys: frozenset[str]) -> set[str]:
    """Normalize keys once for matching (lower, no dashes/underscores/spaces)."""
    return {re.sub(r"[-_\s]", "", x.lower()) for x in keys}


def redact_dict(
    d: dict[str, Any], key_subset: frozenset[str] | None = None
) -> dict[str, Any]:
    """Copy dict with sensitive keys replaced by [REDACTED]; case-insensitive match."""
    keys = key_subset or REDACT_KEYS
    norm_set = _normalized_key_set(keys)
    return _redact_dict_impl(d, norm_set)


def _redact_dict_impl(d: dict[str, Any], norm_set: set[str]) -> dict[str, Any]:
    """Internal: recurse with precomputed normalized key set (avoids per-key set rebuild)."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if re.sub(r"[-_\s]", "", k.lower()) in norm_set:
            out[k] = _redact_value(v)
        elif isinstance(v, dict):
            out[k] = _redact_dict_impl(v, norm_set)
        elif isinstance(v, list):
            out[k] = [
                _redact_dict_impl(x, norm_set) if isinstance(x, dict) else x for x in v
            ]
        else:
            out[k] = v
    return out
