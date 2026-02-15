"""RFCOMM transport implementation using Python sockets."""

from __future__ import annotations

import socket

from budsctl.core.errors import (
    TransportConnectError,
    TransportSendError,
    TransportTimeoutError,
)


class RFCOMMTransport:
    def send(
        self,
        mac: str,
        payload: bytes,
        *,
        channel: int,
        timeout_s: float = 3.0,
    ) -> bytes | None:
        try:
            af_bluetooth = socket.AF_BLUETOOTH
            btproto_rfcomm = socket.BTPROTO_RFCOMM
        except AttributeError as exc:
            raise TransportConnectError(
                "This Python build does not expose Bluetooth socket APIs (AF_BLUETOOTH/BTPROTO_RFCOMM)."
            ) from exc

        try:
            bt_socket = socket.socket(
                af_bluetooth,
                socket.SOCK_STREAM,
                btproto_rfcomm,
            )
        except OSError as exc:
            raise TransportConnectError(f"Could not create RFCOMM socket: {exc}") from exc
        bt_socket.settimeout(timeout_s)
        try:
            try:
                bt_socket.connect((mac, channel))
            except TimeoutError as exc:
                raise TransportTimeoutError(
                    f"RFCOMM connect timed out for {mac} on channel {channel}"
                ) from exc
            except OSError as exc:
                raise TransportConnectError(
                    f"RFCOMM connect failed for {mac} on channel {channel}: {exc}"
                ) from exc

            try:
                bt_socket.sendall(payload)
            except OSError as exc:
                raise TransportSendError(f"RFCOMM send failed: {exc}") from exc

            try:
                data = bt_socket.recv(1024)
                return data if data else None
            except socket.timeout:
                return None
            except TimeoutError as exc:
                raise TransportTimeoutError("RFCOMM receive timed out") from exc
            except OSError as exc:
                raise TransportSendError(f"RFCOMM receive failed: {exc}") from exc
        finally:
            bt_socket.close()
