from __future__ import annotations

from budsctl.api import Client, FeatureCatalog
from budsctl.core.model import DetectedDevice


class FakeTransport:
    def send(self, mac: str, payload: bytes, *, channel: int, timeout_s: float = 3.0) -> bytes | None:
        return bytes.fromhex("abcd")


def test_public_client_list_plugins() -> None:
    client = Client(transport=FakeTransport())
    plugins = client.list_plugins()
    assert plugins
    assert any(p.id == "oneplus_buds4" for p in plugins)


def test_public_client_feature_catalog_and_values(monkeypatch) -> None:
    client = Client(transport=FakeTransport())

    monkeypatch.setattr(
        client._service,
        "list_devices",
        lambda: [DetectedDevice(mac="88:92:CC:11:22:33", name="OnePlus Buds 4")],
    )

    target, values = client.get_feature_values("anc", device_hint="oneplus")
    assert target.plugin.id == "oneplus_buds4"
    assert "on" in values

    catalog = client.get_feature_catalog(device_hint="oneplus")
    assert isinstance(catalog, FeatureCatalog)
    assert "anc" in catalog.features


def test_public_client_set_feature(monkeypatch) -> None:
    client = Client(transport=FakeTransport())

    monkeypatch.setattr(
        client._service,
        "list_devices",
        lambda: [DetectedDevice(mac="88:92:CC:11:22:33", name="OnePlus Buds 4")],
    )

    result = client.set_feature("anc", "on", device_hint="oneplus")
    assert result.feature == "anc"
    assert result.value == "on"
    assert result.response_hex == "abcd"
