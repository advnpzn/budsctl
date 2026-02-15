# Reverse Engineering Guide: Build Your Own Plugin

This guide explains how to derive Bluetooth command payloads from a vendor app and convert them into a `budsctl` YAML plugin.

Use this only for devices you own and in jurisdictions where reverse engineering for interoperability is permitted.

## Goal

Produce a plugin with:

- device match rules (`name_contains`, `mac_prefix`)
- transport metadata (currently RFCOMM in budsctl v1)
- feature/value payload map (`features.<feature>.values.<value> = <hex>`)

## Prerequisites

- Linux machine with BlueZ
- Device paired and controllable via official app
- Tools (recommended):
  - `btmon` (packet capture)
  - `bluetoothctl` (device info)
  - Wireshark (optional, for analysis)
  - `adb` (if capturing from Android HCI snoop logs)

## Capture topology (important)

Capture on the host/controller that is actually sending control commands to the earbuds.

- If your Linux laptop sends commands, `btmon` on Linux is the right source.
- If your Android app sends commands directly, Linux `btmon` usually will not see those control frames.
- In Android-app flows, prefer Android HCI snoop logs and pull them with `adb`.

## 1) Identify your device and MAC prefix

Get known devices:

```bash
bluetoothctl devices
```

Take note of:

- full MAC (e.g., `88:92:CC:E5:DA:FF`)
- first 3 bytes as prefix (e.g., `88:92:CC`)
- visible device name string

These become:

- `match.mac_prefix`
- `match.name_contains`

## 2) Capture Bluetooth traffic while toggling one setting

Start capture in terminal 1:

```bash
sudo btmon | tee btmon.log
```

In terminal 2 or phone app, toggle exactly one feature state at a time, for example:

- ANC off -> on
- ANC on -> transparency
- game mode off -> on

Capture each transition separately. Keep a short timeline (timestamps + action you performed).

Before feature toggles, capture a short idle baseline (30-60 seconds) to identify background noise frames.

For cleaner traces:

- disable multipoint temporarily
- disconnect other paired hosts from the earbuds
- disable auto/reactive features if possible (in-ear detection, adaptive ANC, head tracking)

## 2.1) Capture using gestures too (recommended)

Many devices trigger the same protocol commands via gestures (tap/double-tap/hold) as via vendor app buttons.

Gesture capture is useful when:

- app UI does not expose every mode
- a gesture-only feature exists (for example, cycle ANC mode)
- you want to confirm app and gesture emit the same payload

Recommended method:

1. capture app-triggered transition first (baseline)
2. capture the same transition via gesture
3. compare payloads and keep only stable command bytes seen in both

Note: gesture traces often include extra events (status sync/telemetry), so treat them as noisier than app traces.
Also note: some gestures are handled fully on-device and may not emit a host-originated control frame at all.

## 2.2) Android app capture via Bluetooth HCI snoop log

If the vendor app runs on Android and controls the device directly, this is often the most reliable source.

1. On Android: enable Developer options.
2. Enable **Bluetooth HCI snoop log**.
3. Reproduce one setting toggle at a time in the vendor app.
4. Pull the bugreport/logs to your laptop:

```bash
adb bugreport bugreport.zip
```

5. Extract and inspect the Bluetooth snoop file from the bugreport package (file names vary by Android version/vendor).
6. Open the snoop capture in Wireshark and diff app actions by timestamp.

Alternative on some devices:

```bash
adb pull /sdcard/btsnoop_hci.log
```

If file path is unavailable, use `adb bugreport`, which is more portable across Android variants.

## 3) Identify transport and isolate payload frames

Not all headsets use RFCOMM. Some use BLE GATT writes/notifications; others may mix transports.

Common patterns:

- Classic Bluetooth + RFCOMM socket channel
- BLE GATT characteristic write/notify flow
- Hybrid model (one transport for control, another for telemetry)

Current `budsctl` v1 plugin/runtime support:

- `transport.type: rfcomm` (channel `1..30`)
- `transport.type: ble` (service/write characteristic, optional notify characteristic)

In `btmon.log`, search for sent data blocks around each action timestamp.

Helpful pattern search:

```bash
rg -n "RFCOMM|Data|Sent|ACL" btmon.log
```

You are looking for payload bytes that change predictably with each app action, regardless of whether the underlying link is RFCOMM or BLE.

## 4) Derive command candidates with diffing

For each feature:

1. record payload for value A
2. record payload for value B
3. repeat same toggle multiple times to confirm stability (recommended: at least 5 repeats per transition)

Only keep bytes that are consistent across repeats.
Validate both directions when relevant (for example `off -> on` and `on -> off`).

If two different features emit different frames, map them to separate plugin feature keys.
If payloads include rolling counters, checksums, nonces, or session-derived bytes, note them explicitly; static enum payload mapping may be insufficient for current plugin v1.

## 5) Find transport details

### If protocol is RFCOMM

There are two practical methods:

- infer from capture/session metadata if visible (including SDP/service records when available)
- probe candidate channels with controlled trials and keep the one that reliably changes device state

In plugin, set:

```yaml
transport:
  type: rfcomm
  channel: <n>
```

`budsctl` currently accepts channels `1..30`.

### If protocol is BLE

Capture and document:

- service UUID
- characteristic UUID used for writes
- write type (with response / without response)
- notification characteristic(s)
- payload frames per feature value
- ATT operation for each frame (`Write Request`, `Write Command`, `Notification`, `Indication`)
- direction (host->device vs device->host)
- connection handle/context

Map these fields directly into plugin YAML using `transport.type: ble`.

## 6) Convert to YAML plugin

Create `~/.config/budsctl/plugins/<your_id>.yaml`:

```yaml
id: my_buds_model
name: My Buds Model

match:
  name_contains: ["My Buds Model"]
  mac_prefix: ["12:34:56"]

transport:
  type: rfcomm
  channel: 15

features:
  anc:
    type: enum
    values:
      on: "aa0a00000404480300010102"
      off: "aa0a000004044a0300010101"

  game_mode:
    type: enum
    values:
      on: "bb0101"
      off: "bb0100"
```

Notes:

- feature names are arbitrary (`anc`, `game_mode`, `spatial_audio`, etc.)
- value labels are arbitrary (`on/off/high/low/...`)
- payload must be valid hex, even length

## 7) Validate and test with CLI

Inspect loaded plugin/features:

```bash
budsctl list
budsctl features --plugin my_buds_model
```

Test values on a specific device:

```bash
budsctl set anc on --plugin my_buds_model --device 12:34:56:AA:BB:CC
budsctl set anc off --plugin my_buds_model --device 12:34:56:AA:BB:CC
```

If command fails with unsupported value, inspect allowed set:

```bash
budsctl set anc --plugin my_buds_model --device 12:34:56:AA:BB:CC
```

## 8) Troubleshooting

### Device found as `<unknown-device>`

Your discovery fallback path was used. Target by MAC with `--device`.

### `No device found matching ...`

Use exact MAC in `--device` or force plugin with `--plugin`.

### `Feature ... does not support value ...`

Your YAML value label or feature name is incorrect; check `budsctl features` output.

### Transport errors

- Ensure Python has Bluetooth socket support (`AF_BLUETOOTH`, `BTPROTO_RFCOMM`).
- Ensure adapter/device is connected and channel is correct.

### Empty or irrelevant capture

- Ensure you are capturing on the host that sends commands (Linux `btmon` vs Android HCI snoop).
- Ensure only one active controller is connected during capture (disable multipoint for testing).

## 9) Share your plugin

When stable:

1. include tested feature/value matrix in PR description
2. mention device firmware/app version used for capture
3. include at least one real-world verification for each value mapping

This helps maintainers validate protocol drift across firmware updates.

If your device uses BLE, share your capture notes (UUIDs + payload map) in the issue/PR so BLE transport support can be added later without redoing capture work.

## 10) PR capture checklist template

Copy this into your PR description when submitting a new plugin:

```md
## Device / environment

- Device model:
- Firmware version:
- Vendor app + version:
- Host used for capture (Linux/Android):
- Capture source (`btmon`, Android HCI snoop, both):

## Transport evidence

- Transport observed (RFCOMM / BLE / hybrid):
- If RFCOMM: channel:
- If BLE: service UUID(s), write characteristic UUID(s), notify characteristic UUID(s):

## Match rules

- `name_contains`:
- `mac_prefix`:

## Feature mapping evidence

| Feature | Value | Payload (hex) | Capture source | Repeats | Verified on-device |
|---|---|---|---|---:|---|
| anc | on | aa... | app/gesture | 5 | yes |
| anc | off | aa... | app/gesture | 5 | yes |

## Validation

- `budsctl list` output checked: yes/no
- `budsctl features --plugin <id>` checked: yes/no
- `budsctl set <feature> <value> --plugin <id> --device <mac>` verified: yes/no

## Notes / limitations

- Any counters/checksums/nonces/session bytes observed:
- Any values not yet mapped:
- Any firmware-dependent behavior:
```
