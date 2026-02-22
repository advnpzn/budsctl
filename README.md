# budsctl

`budsctl` is a CLI-first Bluetooth earbuds control app with pluggable YAML protocol modules.

Developer docs: `docs/README.md`

Reverse engineering guide for creating new device plugins: `docs/reverse-engineering.md`

Changelog: `CHANGELOG.md`

## Requirements

- Linux with BlueZ
- Python 3.12+
- RFCOMM support in kernel/adapter

## Plugin system

Built-ins are shipped under `budsctl/plugins/*.yaml`.
User plugins are loaded from:
- `$XDG_CONFIG_HOME/budsctl/plugins` (fallback `~/.config/budsctl/plugins`)
- `$XDG_DATA_HOME/budsctl/plugins` (fallback `~/.local/share/budsctl/plugins`)

User plugin IDs override built-ins with a warning.

## Example commands

```bash
budsctl list
budsctl devices
budsctl features --device oneplus
budsctl set anc on
budsctl set anc transparency --device 88:92:CC:11:22:33
budsctl set anc off --plugin oneplus_buds4
```

`budsctl` is feature-agnostic: plugin authors can define any feature names (not just `anc`) under `features`, and the CLI will expose and use them dynamically.

## Library usage (public API)

`budsctl` can be used as a Python library via the stable public module `budsctl.api`.

```python
from budsctl.api import Client

client = Client()

for plugin in client.list_plugins():
    print(plugin.id, plugin.name)

catalog = client.get_feature_catalog(device_hint="oneplus")
print(catalog.features)

# Send a command
result = client.set_feature("anc", "on", device_hint="oneplus")
print(result.payload_hex, result.response_hex)
```

## Notes

- Transport uses Python RFCOMM sockets directly (`AF_BLUETOOTH`), no `rfcomm` CLI tool.
- Device listing currently parses `bluetoothctl devices` output.
- Future milestones add stronger auto-detect behavior, TUI, and optional tray/D-Bus integration.

## Development environment

This project is configured to use **system Python** (not uv-managed Python) so Bluetooth socket support is inherited from the OS Python build.

- `uv.toml` sets:
  - `python-preference = "only-system"`
  - `python-downloads = "never"`
- `.python-version` is set to `3` to avoid pinning a specific uv-managed minor version.

Recommended setup after clone:

```bash
uv venv --python python3
uv sync
```

To verify Bluetooth API availability in the venv:

```bash
uv run python -c "import socket; print(hasattr(socket, 'AF_BLUETOOTH'), hasattr(socket, 'BTPROTO_RFCOMM'))"
```
