"""Core data models used across loader, service, and CLI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchRules:
    name_contains: tuple[str, ...]
    mac_prefix: tuple[str, ...]


@dataclass(frozen=True)
class TransportSpec:
    type: str
    channel: int | None = None
    service_uuid: str | None = None
    write_char_uuid: str | None = None
    notify_char_uuid: str | None = None
    write_with_response: bool = True
    timeout_s: float = 5.0


@dataclass(frozen=True)
class EnumFeature:
    type: str
    values: dict[str, bytes]


@dataclass(frozen=True)
class Plugin:
    id: str
    name: str
    match: MatchRules
    transport: TransportSpec
    features: dict[str, EnumFeature]


@dataclass(frozen=True)
class DetectedDevice:
    mac: str
    name: str


@dataclass(frozen=True)
class ResolvedTarget:
    device: DetectedDevice
    plugin: Plugin


@dataclass(frozen=True)
class SendResult:
    target: ResolvedTarget
    feature: str
    value: str
    payload_hex: str
    response_hex: str | None
