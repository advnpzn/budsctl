# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-15

### Added

- Core `budsctl` package structure with CLI-first architecture.
- Typer CLI commands:
  - `budsctl list`
  - `budsctl devices`
  - `budsctl features`
  - `budsctl set <feature> [value]`
- YAML plugin loader with schema validation and semantic checks.
- Built-in sample plugin for OnePlus Buds 4.
- Device matching and target resolution based on name/MAC prefix hints.
- RFCOMM transport over Python socket APIs (no `rfcomm` CLI dependency).
- BLE GATT transport support (`transport.type: ble`) with service/characteristic configuration.
- Public stable Python API (`budsctl.api`) via `Client` and typed models/errors.
- Reverse-engineering documentation for creating new plugins.
- GitHub Actions workflows for CI, release artifacts, and CodeQL analysis.
- MIT license (`advnpzn`).

### Changed

- Project configured to prefer system Python for Bluetooth capability (`uv.toml`, `.python-version`).
- `set` command now allows omitted value and prints available values for the requested feature.
- Device-hint matching expanded to support plugin identifiers/names and partial MAC matching.

### Fixed

- Wheel packaging now includes all Python modules required by CLI entry points.
- Improved CLI error handling to avoid stack traces for domain/runtime errors.
- Discovery behavior now handles `bluetoothctl` failures with fallback and clearer diagnostics.

[Unreleased]: https://github.com/advnpzn/budsctl/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/advnpzn/budsctl/releases/tag/v0.1.0
