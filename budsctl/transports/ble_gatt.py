"""BLE GATT transport implementation."""

from __future__ import annotations

import asyncio
import time

from budsctl.core.errors import (
    TransportConnectError,
    TransportSendError,
    TransportTimeoutError,
)


class BLEGATTTransport:
    def send(
        self,
        mac: str,
        payload: bytes,
        *,
        service_uuid: str,
        write_char_uuid: str,
        notify_char_uuid: str | None = None,
        write_with_response: bool = True,
        timeout_s: float = 5.0,
    ) -> bytes | None:
        try:
            from bleak import BleakClient  # type: ignore
        except Exception as exc:  # pragma: no cover - import failure path
            raise TransportConnectError(
                "BLE transport requires 'bleak'. Install dependency and retry."
            ) from exc

        async def _run() -> bytes | None:
            response: bytes | None = None

            def _notify_handler(_: int | str, data: bytearray) -> None:
                nonlocal response
                response = bytes(data)

            async with BleakClient(mac, timeout=timeout_s) as client:
                if not client.is_connected:
                    raise TransportConnectError(f"BLE connect failed for {mac}")

                try:
                    if notify_char_uuid:
                        await client.start_notify(notify_char_uuid, _notify_handler)

                    await client.write_gatt_char(
                        write_char_uuid,
                        payload,
                        response=write_with_response,
                    )

                    if notify_char_uuid:
                        deadline = time.monotonic() + timeout_s
                        while response is None and time.monotonic() < deadline:
                            await asyncio.sleep(0.05)
                        if response is None:
                            raise TransportTimeoutError(
                                f"Timed out waiting for BLE notification on {notify_char_uuid}"
                            )
                        return response

                    # If no notify path, attempt direct read from same characteristic.
                    try:
                        data = await client.read_gatt_char(write_char_uuid)
                        return bytes(data) if data else None
                    except Exception:
                        return None
                finally:
                    if notify_char_uuid:
                        try:
                            await client.stop_notify(notify_char_uuid)
                        except Exception:
                            pass

        try:
            return asyncio.run(_run())
        except TransportTimeoutError:
            raise
        except TransportConnectError:
            raise
        except Exception as exc:
            raise TransportSendError(f"BLE GATT send failed: {exc}") from exc
