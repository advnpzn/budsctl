from __future__ import annotations

import socket

import pytest

from budsctl.core.errors import TransportConnectError
from budsctl.transports.rfcomm import RFCOMMTransport


def test_missing_bluetooth_constants_raises_clean_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(socket, "AF_BLUETOOTH", raising=False)
    monkeypatch.delattr(socket, "BTPROTO_RFCOMM", raising=False)

    transport = RFCOMMTransport()
    with pytest.raises(TransportConnectError):
        transport.send("88:92:CC:11:22:33", b"\xaa\x00", channel=15)
