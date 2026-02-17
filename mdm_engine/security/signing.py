"""SigningProvider interface and stub; timestamp/nonce, replay protection."""

from abc import ABC, abstractmethod
from typing import Any


class SigningProvider(ABC):
    """Sign requests for live API; replay protection via timestamp/nonce."""

    @abstractmethod
    def sign(self, method: str, path: str, body: bytes, timestamp: int, nonce: str) -> str:
        """Return signature string."""
        ...

    @abstractmethod
    def reject_replay(self, timestamp: int, nonce: str, window_sec: int = 60) -> bool:
        """True if request should be rejected (replay or skew)."""
        ...


def canonicalize_request(method: str, path: str, body: bytes) -> bytes:
    """Stub: canonical form for signing."""
    return f"{method}\n{path}\n".encode() + body


class SigningStub(SigningProvider):
    """No real keys; always reject signing / replay check."""

    def sign(self, method: str, path: str, body: bytes, timestamp: int, nonce: str) -> str:
        return ""

    def reject_replay(self, timestamp: int, nonce: str, window_sec: int = 60) -> bool:
        return True  # reject all in stub
