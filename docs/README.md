# budsctl Documentation

This folder contains developer-facing documentation for all supported integration interfaces.

## Documents

- [Python API](./api.md)
- [CLI Interface](./cli.md)
- [Plugin YAML Interface](./plugins.md)
- [Reverse Engineering Guide](./reverse-engineering.md)

## Stability model

- `budsctl.api` is the supported stable library surface for external tooling.
- CLI commands in `budsctl.cli` are supported for end users and scripts.
- Plugin YAML schema in `budsctl/schemas/plugin.schema.json` is the contract for community plugins.
- Direct imports from `budsctl.core.*` and `budsctl.transports.*` are internal unless re-exported by `budsctl.api`.
