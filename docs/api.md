# Python API (`budsctl.api`)

Use `budsctl.api` to build custom apps (TUI/GUI/tray/service) on top of budsctl.

## Import surface

```python
from budsctl.api import (
    Client,
    FeatureCatalog,
    BudsctlError,
    DeviceDiscoveryError,
    DeviceSelectionError,
    FeatureResolutionError,
    PluginLoadError,
    PluginValidationError,
    TransportError,
    TransportConnectError,
    TransportSendError,
    TransportTimeoutError,
)
```

## Core types

- `Client`: main entry point for plugin loading, discovery, and control.
- `FeatureCatalog`: resolved target and feature/value mapping.
- Data models (re-exported): `Plugin`, `DetectedDevice`, `ResolvedTarget`, `SendResult`, etc.

## Client interface

### `Client(transport: Transport | None = None)`

Creates a client. If `transport` is omitted, default RFCOMM transport is used.

### Properties

- `load_warnings -> tuple[str, ...]`: plugin-loading warnings (e.g., overrides).
- `runtime_warnings -> tuple[str, ...]`: environment warnings (e.g., missing Bluetooth socket API).

### Methods

- `list_plugins() -> list[Plugin]`
- `list_devices() -> list[DetectedDevice]`
- `resolve_target(plugin_id: str | None = None, device_hint: str | None = None) -> ResolvedTarget`
- `get_feature_values(feature: str, plugin_id: str | None = None, device_hint: str | None = None) -> tuple[ResolvedTarget, tuple[str, ...]]`
- `get_feature_catalog(plugin_id: str | None = None, device_hint: str | None = None) -> FeatureCatalog`
- `set_feature(feature: str, value: str, plugin_id: str | None = None, device_hint: str | None = None) -> SendResult`

## Examples

### 1) Inspect plugins and devices

```python
from budsctl.api import Client

client = Client()

for warning in client.load_warnings + client.runtime_warnings:
    print("warning:", warning)

for plugin in client.list_plugins():
    print(plugin.id, plugin.name)

for dev in client.list_devices():
    print(dev.mac, dev.name)
```

### 2) Show features for a target

```python
from budsctl.api import Client

client = Client()
catalog = client.get_feature_catalog(device_hint="oneplus")

print("target:", catalog.target.device.mac, catalog.target.plugin.id)
for feature, values in catalog.features.items():
    print(feature, "=>", ", ".join(values))
```

### 3) Send a command

```python
from budsctl.api import Client

client = Client()
result = client.set_feature("anc", "on", device_hint="oneplus")
print(result.payload_hex, result.response_hex)
```

### 4) Error handling

```python
from budsctl.api import Client, DeviceSelectionError, FeatureResolutionError, TransportError

client = Client()

try:
    client.set_feature("anc", "on", device_hint="oneplus")
except DeviceSelectionError as e:
    print("device selection failed:", e)
except FeatureResolutionError as e:
    print("feature/value issue:", e)
except TransportError as e:
    print("transport failed:", e)
```

## Custom transport injection

For simulation or testing, inject any object matching the transport protocol (`send(mac, payload, *, channel, timeout_s)`).

```python
from budsctl.api import Client

class FakeTransport:
    def send(self, mac, payload, *, channel, timeout_s=3.0):
        print("SEND", mac, channel, payload.hex())
        return bytes.fromhex("beef")

client = Client(transport=FakeTransport())
```
