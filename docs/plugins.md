# Plugin YAML Interface

Plugins define device matching and feature payloads. The schema contract is in:

- `budsctl/schemas/plugin.schema.json`

Current transport support in `budsctl` v1 includes:

- `transport.type: rfcomm`
- `transport.type: ble` (BLE GATT write/optional notify)

## Discovery locations

Plugins are loaded in this order:

1. Built-ins: packaged `budsctl/plugins/*.yaml`
2. User config dir: `$XDG_CONFIG_HOME/budsctl/plugins` (fallback `~/.config/budsctl/plugins`)
3. User data dir: `$XDG_DATA_HOME/budsctl/plugins` (fallback `~/.local/share/budsctl/plugins`)

If a user plugin has the same `id` as a built-in, it overrides it with a warning.

## Required structure (v1)

```yaml
id: your_plugin_id
name: Human Device Name

match:
  name_contains: ["Name token"]
  mac_prefix: ["AA:BB:CC"]

transport:
  type: rfcomm
  channel: 15

features:
  some_feature:
    type: enum
    values:
      option_a: "aa00"
      option_b: "aa01"
```

## Field reference

- `id` (`str`): unique plugin identifier.
- `name` (`str`): display label.
- `match.name_contains` (`list[str]`): case-insensitive substrings against device name.
- `match.mac_prefix` (`list[str]`): MAC prefix candidates.
- `transport.type`: `rfcomm` or `ble`.
- For `rfcomm`:
  - `transport.channel` (`int`): allowed range `1..30`.
  - optional `transport.timeout_s` (`float` > 0).
- For `ble`:
  - `transport.service_uuid` (`str`): 16/32/128-bit UUID format.
  - `transport.write_char_uuid` (`str`): characteristic UUID for writes.
  - optional `transport.notify_char_uuid` (`str`): characteristic UUID for notifications.
  - optional `transport.write_with_response` (`bool`, default `true`).
  - optional `transport.timeout_s` (`float` > 0).
- `features` (`map[str, feature]`): arbitrary feature names (not limited to ANC).
- `feature.type`: currently `enum`.
- `feature.values` (`map[str, hex]`): arbitrary value labels mapped to payload hex.

## Validation and safety rules

- YAML duplicate keys are rejected.
- Root document must be a mapping.
- Schema validation is enforced.
- Hex payloads are normalized and validated:
  - lowercase hex only (`[0-9a-f]`)
  - even length
  - max payload size: `512` bytes

## Examples

### Example: ANC + game mode

```yaml
id: mybuds_x
name: MyBuds X

match:
  name_contains: ["MyBuds X"]
  mac_prefix: ["12:34:56"]

transport:
  type: rfcomm
  channel: 15

features:
  anc:
    type: enum
    values:
      on: "aa0a0001"
      off: "aa0a0002"

  game_mode:
    type: enum
    values:
      on: "bb0101"
      off: "bb0100"
```

Use it from CLI:

```bash
budsctl features --plugin mybuds_x
budsctl set game_mode on --plugin mybuds_x --device 12:34:56:AA:BB:CC
```

### Example: BLE transport

```yaml
id: mybuds_ble
name: MyBuds BLE

match:
  name_contains: ["MyBuds BLE"]
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
```

## Common errors

- `Schema validation failed ...`: required fields missing/invalid.
- `Duplicate key ...`: YAML duplicated key at same level.
- `... must have even-length hex` / `... only [0-9a-f]`: invalid payload encoding.
