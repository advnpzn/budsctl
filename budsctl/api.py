"""Stable public API for building tooling on top of budsctl.

This module is the supported integration surface for third-party callers.
Avoid importing from private/internal modules unless intentionally depending on
non-stable internals.
"""

from __future__ import annotations

from dataclasses import dataclass

from budsctl.core.errors import (
    BudsctlError,
    DeviceDiscoveryError,
    DeviceSelectionError,
    FeatureResolutionError,
    PluginLoadError,
    PluginValidationError,
    TransportConnectError,
    TransportError,
    TransportSendError,
    TransportTimeoutError,
)
from budsctl.core.model import (
    DetectedDevice,
    EnumFeature,
    MatchRules,
    Plugin,
    ResolvedTarget,
    SendResult,
    TransportSpec,
)
from budsctl.core.service import BudsService
from budsctl.transports.ble_gatt import BLEGATTTransport
from budsctl.transports.base import Transport

__all__ = [
    "BudsctlError",
    "DeviceDiscoveryError",
    "DeviceSelectionError",
    "FeatureResolutionError",
    "PluginLoadError",
    "PluginValidationError",
    "TransportError",
    "TransportConnectError",
    "TransportSendError",
    "TransportTimeoutError",
    "DetectedDevice",
    "EnumFeature",
    "MatchRules",
    "Plugin",
    "ResolvedTarget",
    "SendResult",
    "TransportSpec",
    "BLEGATTTransport",
    "FeatureCatalog",
    "Client",
]


@dataclass(frozen=True)
class FeatureCatalog:
    """Feature/value catalog for a resolved target device plugin."""

    target: ResolvedTarget
    features: dict[str, tuple[str, ...]]


class Client:
    """Public client for interacting with budsctl core capabilities.

    A `Client` instance wraps plugin loading, device discovery/matching, and
    RFCOMM send operations behind a stable API intended for third-party tools
    (GUI/TUI/services/scripts).
    """

    def __init__(
        self,
        *,
        transport: Transport | None = None,
        ble_transport: BLEGATTTransport | None = None,
    ) -> None:
        self._service = BudsService(transport=transport, ble_transport=ble_transport)

    @property
    def load_warnings(self) -> tuple[str, ...]:
        return self._service.load_warnings

    @property
    def runtime_warnings(self) -> tuple[str, ...]:
        return self._service.runtime_warnings

    def list_plugins(self) -> list[Plugin]:
        return self._service.list_plugins()

    def list_devices(self) -> list[DetectedDevice]:
        return self._service.list_devices()

    def resolve_target(
        self,
        *,
        plugin_id: str | None = None,
        device_hint: str | None = None,
    ) -> ResolvedTarget:
        return self._service.resolve_target(plugin_id=plugin_id, device_hint=device_hint)

    def get_feature_values(
        self,
        feature: str,
        *,
        plugin_id: str | None = None,
        device_hint: str | None = None,
    ) -> tuple[ResolvedTarget, tuple[str, ...]]:
        return self._service.feature_values(
            feature,
            plugin_id=plugin_id,
            device_hint=device_hint,
        )

    def get_feature_catalog(
        self,
        *,
        plugin_id: str | None = None,
        device_hint: str | None = None,
    ) -> FeatureCatalog:
        target, features = self._service.feature_catalog(
            plugin_id=plugin_id,
            device_hint=device_hint,
        )
        return FeatureCatalog(target=target, features=features)

    def set_feature(
        self,
        feature: str,
        value: str,
        *,
        plugin_id: str | None = None,
        device_hint: str | None = None,
    ) -> SendResult:
        return self._service.set_feature(
            feature,
            value,
            plugin_id=plugin_id,
            device_hint=device_hint,
        )
