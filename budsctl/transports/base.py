"""Transport interfaces."""

from __future__ import annotations

from typing import Protocol


class Transport(Protocol):
    def send(
        self,
        mac: str,
        payload: bytes,
        *,
        channel: int,
        timeout_s: float = 3.0,
    ) -> bytes | None:
        """Send payload to a device and optionally return a response."""
