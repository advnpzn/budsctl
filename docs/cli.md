# CLI Interface

Command entrypoint: `budsctl`

## Commands

### `budsctl list`

Lists loaded plugins and their available feature values.

Example:

```bash
budsctl list
```

### `budsctl devices`

Lists discovered Bluetooth devices and the matched plugin (if any).

Example:

```bash
budsctl devices
```

### `budsctl features [--device <hint>] [--plugin <id>]`

Lists all features and value options for the resolved target.

Options:

- `--device`: MAC or partial name/plugin hint.
- `--plugin`: force a specific plugin ID.

Examples:

```bash
budsctl features --device oneplus
budsctl features --plugin oneplus_buds4
```

### `budsctl set <feature> [value] [--device <hint>] [--plugin <id>]`

Sets a feature value for the resolved target.

Behavior:

- If `value` is provided: sends command payload.
- If `value` is omitted: prints allowed values for the feature.

Options:

- `--device`: MAC or partial name/plugin hint.
- `--plugin`: force a specific plugin ID.

Examples:

```bash
budsctl set anc on --device oneplus
budsctl set anc --device oneplus
budsctl set anc transparency --plugin oneplus_buds4
```

## Exit and error model

- Success: exit code `0`.
- Domain/validation/transport failures: exit code `1` with clean `Error: ...` message.
- Startup warnings may be shown on stderr (plugin override/runtime support warnings).

## Target resolution behavior

- Device discovery runs first.
- Device matching uses plugin match rules.
- If multiple targets remain, command fails and asks for `--device`.
