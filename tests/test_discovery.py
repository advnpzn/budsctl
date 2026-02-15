from __future__ import annotations

import subprocess

import pytest

from budsctl.core.errors import DeviceDiscoveryError
from budsctl.core.service import _discover_devices


def _cp(cmd: list[str], rc: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(cmd, rc, stdout=stdout, stderr=stderr)


def test_discovery_falls_back_to_hcitool(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, check, capture_output, text):
        if cmd[0] == "bluetoothctl":
            return _cp(cmd, -6, stderr="dbus crashed")
        if cmd[:2] == ["hcitool", "con"]:
            return _cp(cmd, 0, stdout="Connections:\n\t< ACL 88:92:CC:11:22:33 handle 42 state 1 lm MASTER\n")
        raise AssertionError(f"Unexpected cmd: {cmd}")

    monkeypatch.setattr(subprocess, "run", fake_run)

    devices = _discover_devices()
    assert len(devices) == 1
    assert devices[0].mac == "88:92:CC:11:22:33"
    assert devices[0].name == "<unknown-device>"


def test_discovery_raises_when_all_commands_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, check, capture_output, text):
        return _cp(cmd, -6, stderr="dbus crashed")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(DeviceDiscoveryError):
        _discover_devices()
