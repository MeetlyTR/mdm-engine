# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""Secrets provider: env-based or stub. No secrets in code or logs."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class SecretsProvider(ABC):
    """Abstract provider for secrets (API keys, tokens). Use in adapters only; never log values."""

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Return secret for key or None if not set."""
        ...


class EnvSecretsProvider(SecretsProvider):
    """Read secrets from environment variables (e.g. API_KEY -> os.environ['API_KEY'])."""

    def __init__(self, prefix: str = "") -> None:
        self.prefix = prefix

    def get(self, key: str) -> str | None:
        env_key = f"{self.prefix}{key}".replace(".", "_").upper()
        return os.environ.get(env_key)
