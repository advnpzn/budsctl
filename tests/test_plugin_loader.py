from __future__ import annotations

from pathlib import Path

import pytest

from budsctl.core.errors import PluginValidationError
from budsctl.core.plugin_loader import load_plugins


def _write_plugin(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_packaged_plugin() -> None:
    loaded = load_plugins()
    assert "oneplus_buds4" in loaded.plugins
    plugin = loaded.plugins["oneplus_buds4"]
    assert plugin.transport.channel == 15
    assert plugin.features["anc"].values["on"].hex() == "aa0a00000404480300010102"


def test_invalid_hex_in_user_plugin_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    _write_plugin(
        tmp_path / "cfg" / "budsctl" / "plugins" / "bad.yaml",
        """
id: bad_hex
name: Bad Hex
match:
  name_contains: [\"Bad\"]
  mac_prefix: [\"00:11:22\"]
transport:
  type: rfcomm
  channel: 15
features:
  anc:
    type: enum
    values:
      on: \"xyz\"
""",
    )

    with pytest.raises(PluginValidationError):
        load_plugins()


def test_missing_required_keys_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    _write_plugin(
        tmp_path / "cfg" / "budsctl" / "plugins" / "missing.yaml",
        """
id: missing
name: Missing
match:
  name_contains: [\"Missing\"]
  mac_prefix: [\"AA:BB:CC\"]
transport:
  type: rfcomm
  channel: 1
""",
    )

    with pytest.raises(PluginValidationError):
        load_plugins()


def test_user_plugin_override_packaged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    _write_plugin(
        tmp_path / "cfg" / "budsctl" / "plugins" / "override.yaml",
        """
id: oneplus_buds4
name: User Override
match:
  name_contains: [\"OnePlus Buds 4\"]
  mac_prefix: [\"88:92:CC\"]
transport:
  type: rfcomm
  channel: 16
features:
  anc:
    type: enum
    values:
      on: \"aa00\"
""",
    )

    loaded = load_plugins()
    assert loaded.plugins["oneplus_buds4"].name == "User Override"
    assert loaded.plugins["oneplus_buds4"].transport.channel == 16
    assert any("overrides" in warning for warning in loaded.warnings)


def test_duplicate_yaml_keys_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    _write_plugin(
        tmp_path / "cfg" / "budsctl" / "plugins" / "dup.yaml",
        """
id: dup
name: Duplicate
match:
  name_contains: [\"Duplicate\"]
  mac_prefix: [\"AA:BB:CC\"]
transport:
  type: rfcomm
  channel: 15
features:
  anc:
    type: enum
    values:
      on: \"aa00\"
      on: \"aa01\"
""",
    )

    with pytest.raises(PluginValidationError):
        load_plugins()


def test_ble_plugin_loads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    _write_plugin(
        tmp_path / "cfg" / "budsctl" / "plugins" / "ble.yaml",
        """
id: my_ble_buds
name: My BLE Buds
match:
  name_contains: ["My BLE Buds"]
  mac_prefix: ["AA:BB:CC"]
transport:
  type: ble
  service_uuid: "0000180f-0000-1000-8000-00805f9b34fb"
  write_char_uuid: "00002a19-0000-1000-8000-00805f9b34fb"
  notify_char_uuid: "00002a1a-0000-1000-8000-00805f9b34fb"
  write_with_response: false
  timeout_s: 2.5
features:
  game_mode:
    type: enum
    values:
      on: "aa01"
      off: "aa00"
""",
    )

    loaded = load_plugins()
    plugin = loaded.plugins["my_ble_buds"]
    assert plugin.transport.type == "ble"
    assert plugin.transport.service_uuid == "0000180f-0000-1000-8000-00805f9b34fb"
    assert plugin.transport.write_char_uuid == "00002a19-0000-1000-8000-00805f9b34fb"
    assert plugin.transport.notify_char_uuid == "00002a1a-0000-1000-8000-00805f9b34fb"
    assert plugin.transport.write_with_response is False
    assert plugin.transport.timeout_s == 2.5
