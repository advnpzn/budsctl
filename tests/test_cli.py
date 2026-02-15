from __future__ import annotations

from typer.testing import CliRunner

from budsctl import cli
from budsctl.core.model import DetectedDevice, EnumFeature, MatchRules, Plugin, ResolvedTarget, SendResult, TransportSpec


class FakeService:
    def __init__(self) -> None:
        self.plugins = {
            "oneplus_buds4": Plugin(
                id="oneplus_buds4",
                name="OnePlus Buds 4",
                match=MatchRules(name_contains=("OnePlus Buds 4",), mac_prefix=("88:92:CC",)),
                transport=TransportSpec(type="rfcomm", channel=15),
                features={
                    "anc": EnumFeature(
                        type="enum",
                        values={
                            "on": bytes.fromhex("aa00"),
                            "off": bytes.fromhex("aa01"),
                        },
                    )
                },
            )
        }

    def list_plugins(self):
        return list(self.plugins.values())

    def list_devices(self):
        return [DetectedDevice(mac="88:92:CC:11:22:33", name="OnePlus Buds 4")]

    def set_feature(self, feature, value, plugin_id=None, device_hint=None):
        return SendResult(
            target=ResolvedTarget(
                device=DetectedDevice(mac="88:92:CC:11:22:33", name="OnePlus Buds 4"),
                plugin=self.plugins["oneplus_buds4"],
            ),
            feature=feature,
            value=value,
            payload_hex="aa00",
            response_hex=None,
        )

    def feature_values(self, feature, plugin_id=None, device_hint=None):
        return (
            ResolvedTarget(
                device=DetectedDevice(mac="88:92:CC:11:22:33", name="OnePlus Buds 4"),
                plugin=self.plugins["oneplus_buds4"],
            ),
            ("off", "on"),
        )

    def feature_catalog(self, plugin_id=None, device_hint=None):
        return (
            ResolvedTarget(
                device=DetectedDevice(mac="88:92:CC:11:22:33", name="OnePlus Buds 4"),
                plugin=self.plugins["oneplus_buds4"],
            ),
            {"anc": ("off", "on")},
        )


runner = CliRunner()


def test_list_command(monkeypatch):
    monkeypatch.setattr(cli, "BudsService", FakeService)
    result = runner.invoke(cli.app, ["list"])
    assert result.exit_code == 0
    assert "oneplus_buds4" in result.stdout
    assert "anc: off, on" in result.stdout


def test_devices_command(monkeypatch):
    monkeypatch.setattr(cli, "BudsService", FakeService)
    result = runner.invoke(cli.app, ["devices"])
    assert result.exit_code == 0
    assert "88:92:CC:11:22:33" in result.stdout


def test_set_command(monkeypatch):
    monkeypatch.setattr(cli, "BudsService", FakeService)
    result = runner.invoke(cli.app, ["set", "anc", "on"])
    assert result.exit_code == 0
    assert "Sent anc=on" in result.stdout


def test_features_command(monkeypatch):
    monkeypatch.setattr(cli, "BudsService", FakeService)
    result = runner.invoke(cli.app, ["features", "--device", "oneplus"])
    assert result.exit_code == 0
    assert "Target: 88:92:CC:11:22:33" in result.stdout
    assert "anc: off, on" in result.stdout


def test_set_command_without_value_shows_available_values(monkeypatch):
    monkeypatch.setattr(cli, "BudsService", FakeService)
    result = runner.invoke(cli.app, ["set", "anc", "--device", "oneplus"])
    assert result.exit_code == 0
    assert "Available values for 'anc'" in result.stdout
    assert "off, on" in result.stdout


def test_set_command_error_is_clean(monkeypatch):
    class FailingService(FakeService):
        def set_feature(self, feature, value, plugin_id=None, device_hint=None):
            from budsctl.core.errors import DeviceSelectionError

            raise DeviceSelectionError("No device found matching 'oneplus'")

    monkeypatch.setattr(cli, "BudsService", FailingService)
    result = runner.invoke(cli.app, ["set", "anc", "on", "--device", "oneplus"])
    assert result.exit_code == 1
    assert "Error: No device found matching 'oneplus'" in result.stderr
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def test_runtime_warning_is_printed(monkeypatch):
    class WarnService(FakeService):
        def __init__(self) -> None:
            super().__init__()
            self.runtime_warnings = ("Python runtime missing AF_BLUETOOTH/BTPROTO_RFCOMM",)
            self.load_warnings = ()

    monkeypatch.setattr(cli, "BudsService", WarnService)
    result = runner.invoke(cli.app, ["list"])
    assert result.exit_code == 0
    assert "Warning: Python runtime missing AF_BLUETOOTH/BTPROTO_RFCOMM" in result.stderr
