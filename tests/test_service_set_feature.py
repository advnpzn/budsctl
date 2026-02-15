from __future__ import annotations

import pytest

from budsctl.core.errors import DeviceSelectionError, FeatureResolutionError
from budsctl.core.model import DetectedDevice, EnumFeature, MatchRules, Plugin, TransportSpec
from budsctl.core.service import BudsService


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, int]] = []

    def send(self, mac: str, payload: bytes, *, channel: int, timeout_s: float = 3.0) -> bytes | None:
        self.calls.append((mac, payload, channel))
        return bytes.fromhex("beef")


class FakeBLETransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, str, str, str | None, bool, float]] = []

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
        self.calls.append(
            (
                mac,
                payload,
                service_uuid,
                write_char_uuid,
                notify_char_uuid,
                write_with_response,
                timeout_s,
            )
        )
        return bytes.fromhex("cafe")


def test_set_feature_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = FakeTransport()
    service = BudsService(transport=transport)

    monkeypatch.setattr(
        service,
        "list_devices",
        lambda: [DetectedDevice(mac="88:92:CC:11:22:33", name="OnePlus Buds 4")],
    )

    result = service.set_feature("anc", "on")
    assert result.feature == "anc"
    assert result.value == "on"
    assert result.payload_hex == "aa0a00000404480300010102"
    assert result.response_hex == "beef"

    assert len(transport.calls) == 1
    mac, payload, channel = transport.calls[0]
    assert mac == "88:92:CC:11:22:33"
    assert payload.hex() == "aa0a00000404480300010102"
    assert channel == 15


def test_multiple_candidates_requires_device(monkeypatch: pytest.MonkeyPatch) -> None:
    service = BudsService(transport=FakeTransport())

    monkeypatch.setattr(
        service,
        "list_devices",
        lambda: [
            DetectedDevice(mac="88:92:CC:11:22:33", name="OnePlus Buds 4"),
            DetectedDevice(mac="88:92:CC:44:55:66", name="OnePlus Buds 4 Pro"),
        ],
    )

    with pytest.raises(DeviceSelectionError):
        service.set_feature("anc", "on")


def test_unknown_feature_value(monkeypatch: pytest.MonkeyPatch) -> None:
    service = BudsService(transport=FakeTransport())

    monkeypatch.setattr(
        service,
        "list_devices",
        lambda: [DetectedDevice(mac="88:92:CC:11:22:33", name="OnePlus Buds 4")],
    )

    with pytest.raises(FeatureResolutionError):
        service.set_feature("anc", "invalid")


def test_device_hint_can_match_plugin_when_name_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = FakeTransport()
    service = BudsService(transport=transport)

    monkeypatch.setattr(
        service,
        "list_devices",
        lambda: [DetectedDevice(mac="88:92:CC:11:22:33", name="<unknown-device>")],
    )

    result = service.set_feature("anc", "on", device_hint="oneplus")
    assert result.target.device.mac == "88:92:CC:11:22:33"


def test_unknown_feature_lists_available_features(monkeypatch: pytest.MonkeyPatch) -> None:
    service = BudsService(transport=FakeTransport())
    monkeypatch.setattr(
        service,
        "list_devices",
        lambda: [DetectedDevice(mac="88:92:CC:11:22:33", name="OnePlus Buds 4")],
    )

    with pytest.raises(FeatureResolutionError) as exc:
        service.set_feature("spatial_audio", "on")

    assert "Available:" in str(exc.value)
    assert "anc" in str(exc.value)


def test_feature_catalog_is_dynamic(monkeypatch: pytest.MonkeyPatch) -> None:
    service = BudsService(transport=FakeTransport())
    monkeypatch.setattr(
        service,
        "list_devices",
        lambda: [DetectedDevice(mac="88:92:CC:11:22:33", name="OnePlus Buds 4")],
    )

    target, catalog = service.feature_catalog(device_hint="oneplus")
    assert target.plugin.id == "oneplus_buds4"
    assert "anc" in catalog
    assert set(catalog["anc"]) == {"adaptive", "off", "on", "transparency"}


def test_set_feature_ble_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    ble_transport = FakeBLETransport()
    service = BudsService(transport=FakeTransport(), ble_transport=ble_transport)

    service.plugins["my_ble_buds"] = Plugin(
        id="my_ble_buds",
        name="My BLE Buds",
        match=MatchRules(name_contains=("My BLE Buds",), mac_prefix=("AA:BB:CC",)),
        transport=TransportSpec(
            type="ble",
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            write_char_uuid="00002a19-0000-1000-8000-00805f9b34fb",
            notify_char_uuid="00002a1a-0000-1000-8000-00805f9b34fb",
            write_with_response=False,
            timeout_s=2.0,
        ),
        features={"game_mode": EnumFeature(type="enum", values={"on": bytes.fromhex("aa01")})},
    )

    monkeypatch.setattr(
        service,
        "list_devices",
        lambda: [DetectedDevice(mac="AA:BB:CC:11:22:33", name="My BLE Buds")],
    )

    result = service.set_feature("game_mode", "on", plugin_id="my_ble_buds", device_hint="AA:BB:CC")
    assert result.response_hex == "cafe"
    assert len(ble_transport.calls) == 1
    call = ble_transport.calls[0]
    assert call[0] == "AA:BB:CC:11:22:33"
    assert call[1].hex() == "aa01"
    assert call[2] == "0000180f-0000-1000-8000-00805f9b34fb"
    assert call[3] == "00002a19-0000-1000-8000-00805f9b34fb"
    assert call[4] == "00002a1a-0000-1000-8000-00805f9b34fb"
    assert call[5] is False
    assert call[6] == 2.0
