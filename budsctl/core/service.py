"""Service layer used by CLI and future UI frontends."""

from __future__ import annotations

import re
import socket
import subprocess
from collections.abc import Sequence

from budsctl.core.device_match import best_plugin_for_device
from budsctl.core.errors import DeviceDiscoveryError, DeviceSelectionError, FeatureResolutionError
from budsctl.core.model import DetectedDevice, Plugin, ResolvedTarget, SendResult
from budsctl.core.plugin_loader import load_plugins
from budsctl.transports.base import Transport
from budsctl.transports.ble_gatt import BLEGATTTransport
from budsctl.transports.rfcomm import RFCOMMTransport

_DEVICE_LINE_RE = re.compile(r"^Device\s+([0-9A-F:]{17})\s+(.+)$", re.IGNORECASE)
_MAC_RE = re.compile(r"([0-9A-F]{2}(?::[0-9A-F]{2}){5})", re.IGNORECASE)


class BudsService:
    def __init__(
        self,
        *,
        transport: Transport | None = None,
        ble_transport: BLEGATTTransport | None = None,
    ) -> None:
        loaded = load_plugins()
        self.plugins = loaded.plugins
        self.load_warnings = loaded.warnings
        self.runtime_warnings = _runtime_warnings()
        self.rfcomm_transport = transport or RFCOMMTransport()
        self.ble_transport = ble_transport or BLEGATTTransport()

    def list_plugins(self) -> list[Plugin]:
        return sorted(self.plugins.values(), key=lambda p: p.id)

    def list_devices(self) -> list[DetectedDevice]:
        return _discover_devices()

    def resolve_target(
        self,
        plugin_id: str | None,
        device_hint: str | None,
    ) -> ResolvedTarget:
        devices = self.list_devices()

        if not devices:
            raise DeviceSelectionError("No Bluetooth devices found. Ensure your target device is connected.")

        candidates: list[ResolvedTarget] = []
        plugin_override: Plugin | None = None
        if plugin_id:
            plugin_override = self.plugins.get(plugin_id)
            if plugin_override is None:
                raise DeviceSelectionError(f"Unknown plugin '{plugin_id}'. Use 'budsctl list' to inspect available plugins.")

        for device in devices:
            if plugin_override:
                plugin = plugin_override
                if best_plugin_for_device(device, {plugin.id: plugin}) is None:
                    continue
            else:
                plugin = best_plugin_for_device(device, self.plugins)
                if plugin is None:
                    continue
            candidates.append(ResolvedTarget(device=device, plugin=plugin))

        if device_hint:
            hint = device_hint.lower()
            hinted = [
                c
                for c in candidates
                if c.device.mac.lower() == hint
                or hint in c.device.mac.lower()
                or hint in c.device.name.lower()
                or hint in c.plugin.id.lower()
                or hint in c.plugin.name.lower()
            ]
            if not hinted:
                raise DeviceSelectionError(f"No device found matching '{device_hint}'")
            candidates = hinted

        if not candidates:
            if plugin_id:
                raise DeviceSelectionError(
                    f"No connected device matched plugin '{plugin_id}'."
                )
            raise DeviceSelectionError(
                "No connected device matched any plugin. Use --plugin to target explicitly or add a plugin."
            )

        if len(candidates) > 1:
            candidate_desc = ", ".join(f"{c.device.mac} ({c.device.name})" for c in candidates)
            raise DeviceSelectionError(
                f"Multiple candidate devices found: {candidate_desc}. Use --device to choose one."
            )

        return candidates[0]

    def set_feature(
        self,
        feature: str,
        value: str,
        plugin_id: str | None = None,
        device_hint: str | None = None,
    ) -> SendResult:
        target, allowed_values = self.feature_values(
            feature,
            plugin_id=plugin_id,
            device_hint=device_hint,
        )
        payload = target.plugin.features[feature].values.get(value)
        if payload is None:
            allowed = ", ".join(allowed_values)
            raise FeatureResolutionError(
                f"Feature '{feature}' does not support value '{value}'. Allowed: {allowed}"
            )

        if target.plugin.transport.type == "rfcomm":
            if target.plugin.transport.channel is None:
                raise FeatureResolutionError(
                    f"Plugin '{target.plugin.id}' has invalid RFCOMM configuration (missing channel)."
                )
            response = self.rfcomm_transport.send(
                target.device.mac,
                payload,
                channel=target.plugin.transport.channel,
                timeout_s=target.plugin.transport.timeout_s,
            )
        elif target.plugin.transport.type == "ble":
            if not target.plugin.transport.service_uuid or not target.plugin.transport.write_char_uuid:
                raise FeatureResolutionError(
                    f"Plugin '{target.plugin.id}' has invalid BLE configuration (missing UUIDs)."
                )
            response = self.ble_transport.send(
                target.device.mac,
                payload,
                service_uuid=target.plugin.transport.service_uuid,
                write_char_uuid=target.plugin.transport.write_char_uuid,
                notify_char_uuid=target.plugin.transport.notify_char_uuid,
                write_with_response=target.plugin.transport.write_with_response,
                timeout_s=target.plugin.transport.timeout_s,
            )
        else:
            raise FeatureResolutionError(
                f"Unsupported transport type '{target.plugin.transport.type}' for plugin '{target.plugin.id}'."
            )

        return SendResult(
            target=target,
            feature=feature,
            value=value,
            payload_hex=payload.hex(),
            response_hex=response.hex() if response else None,
        )

    def feature_values(
        self,
        feature: str,
        plugin_id: str | None = None,
        device_hint: str | None = None,
    ) -> tuple[ResolvedTarget, tuple[str, ...]]:
        target = self.resolve_target(plugin_id=plugin_id, device_hint=device_hint)
        feature_spec = target.plugin.features.get(feature)
        if feature_spec is None:
            available = ", ".join(sorted(target.plugin.features.keys()))
            raise FeatureResolutionError(
                f"Plugin '{target.plugin.id}' does not define feature '{feature}'. Available: {available}"
            )
        return target, tuple(sorted(feature_spec.values.keys()))

    def feature_catalog(
        self,
        plugin_id: str | None = None,
        device_hint: str | None = None,
    ) -> tuple[ResolvedTarget, dict[str, tuple[str, ...]]]:
        target = self.resolve_target(plugin_id=plugin_id, device_hint=device_hint)
        catalog: dict[str, tuple[str, ...]] = {}
        for feature_name, feature_spec in sorted(target.plugin.features.items()):
            catalog[feature_name] = tuple(sorted(feature_spec.values.keys()))
        return target, catalog


def _discover_devices() -> list[DetectedDevice]:
    bluetoothctl_commands = [
        ["bluetoothctl", "devices", "Connected"],
        ["bluetoothctl", "devices"],
        ["bluetoothctl", "paired-devices"],
    ]
    fallback_commands = [["hcitool", "con"]]

    seen: set[str] = set()
    devices: list[DetectedDevice] = []
    command_errors: list[str] = []

    for cmd in bluetoothctl_commands:
        result = _run_discovery_command(cmd)
        if result is None:
            continue
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if stderr:
                command_errors.append(f"{' '.join(cmd)} -> {stderr}")
            continue

        for line in result.stdout.splitlines():
            match = _DEVICE_LINE_RE.match(line.strip())
            if not match:
                continue
            mac, name = match.group(1).upper(), match.group(2).strip()
            if mac in seen:
                continue
            seen.add(mac)
            devices.append(DetectedDevice(mac=mac, name=name))

    if devices:
        return devices

    for cmd in fallback_commands:
        result = _run_discovery_command(cmd)
        if result is None:
            continue
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if stderr:
                command_errors.append(f"{' '.join(cmd)} -> {stderr}")
            continue

        for line in result.stdout.splitlines():
            match = _MAC_RE.search(line)
            if not match:
                continue
            mac = match.group(1).upper()
            if mac in seen:
                continue
            seen.add(mac)
            devices.append(DetectedDevice(mac=mac, name="<unknown-device>"))

    if devices:
        return devices

    if command_errors:
        joined = " | ".join(command_errors)
        raise DeviceDiscoveryError(
            f"Bluetooth discovery failed. Ensure a working D-Bus/BlueZ session. Details: {joined}"
        )

    return devices


def _run_discovery_command(cmd: Sequence[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None


def _runtime_warnings() -> tuple[str, ...]:
    warnings: list[str] = []
    if not hasattr(socket, "AF_BLUETOOTH") or not hasattr(socket, "BTPROTO_RFCOMM"):
        warnings.append(
            "Python runtime missing AF_BLUETOOTH/BTPROTO_RFCOMM; RFCOMM control commands will fail."
        )
    return tuple(warnings)
