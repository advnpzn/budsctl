"""Device-to-plugin matching logic."""

from __future__ import annotations

from budsctl.core.model import DetectedDevice, Plugin


def _mac_prefix_match(device_mac: str, plugin: Plugin) -> bool:
    upper_mac = device_mac.upper()
    return any(upper_mac.startswith(prefix) for prefix in plugin.match.mac_prefix)


def _name_contains_match(device_name: str, plugin: Plugin) -> bool:
    lower_name = device_name.lower()
    return any(token.lower() in lower_name for token in plugin.match.name_contains)


def match_score(device: DetectedDevice, plugin: Plugin) -> int:
    mac_match = _mac_prefix_match(device.mac, plugin)
    name_match = _name_contains_match(device.name, plugin)
    if mac_match and name_match:
        return 3
    if mac_match:
        return 2
    if name_match:
        return 1
    return 0


def best_plugin_for_device(device: DetectedDevice, plugins: dict[str, Plugin]) -> Plugin | None:
    best: Plugin | None = None
    best_score = 0
    for plugin in plugins.values():
        score = match_score(device, plugin)
        if score > best_score:
            best = plugin
            best_score = score
    return best
