"""Typer CLI entrypoint."""

from __future__ import annotations

import typer

from budsctl.core.device_match import best_plugin_for_device
from budsctl.core.errors import BudsctlError
from budsctl.core.service import BudsService

app = typer.Typer(help="Bluetooth earbuds control via pluggable YAML protocols")


def _build_service() -> BudsService:
    service = BudsService()
    for warning in getattr(service, "load_warnings", ()):
        typer.echo(f"Warning: {warning}", err=True)
    for warning in getattr(service, "runtime_warnings", ()):
        typer.echo(f"Warning: {warning}", err=True)
    return service


@app.command("list")
def list_plugins() -> None:
    """List available plugins and their features."""
    try:
        service = _build_service()
        plugins = service.list_plugins()
        if not plugins:
            typer.echo("No plugins loaded")
            raise typer.Exit(code=1)

        for plugin in plugins:
            typer.echo(f"{plugin.id}: {plugin.name}")
            for feature, spec in sorted(plugin.features.items()):
                values = ", ".join(sorted(spec.values.keys()))
                typer.echo(f"  {feature}: {values}")
    except BudsctlError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None


@app.command("devices")
def list_devices() -> None:
    """List currently discoverable Bluetooth devices and matched plugin."""
    try:
        service = _build_service()
        devices = service.list_devices()
        if not devices:
            typer.echo("No Bluetooth devices found")
            return

        for device in devices:
            plugin = best_plugin_for_device(device, service.plugins)
            matched = plugin.id if plugin else "<no-match>"
            typer.echo(f"{device.mac} {device.name} -> {matched}")
    except BudsctlError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None


@app.command("features")
def list_features(
    device: str | None = typer.Option(None, "--device", help="MAC or partial name"),
    plugin: str | None = typer.Option(None, "--plugin", help="Plugin ID"),
) -> None:
    """List features and values for the resolved target plugin."""
    try:
        service = _build_service()
        target, catalog = service.feature_catalog(plugin_id=plugin, device_hint=device)
        typer.echo(f"Target: {target.device.mac} ({target.device.name}) via {target.plugin.id}")
        for feature, values in catalog.items():
            typer.echo(f"  {feature}: {', '.join(values)}")
    except BudsctlError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None


@app.command("set")
def set_feature(
    feature: str,
    value: str | None = typer.Argument(None),
    device: str | None = typer.Option(None, "--device", help="MAC or partial name"),
    plugin: str | None = typer.Option(None, "--plugin", help="Plugin ID"),
) -> None:
    """Set a feature to a named value for a matched device plugin.

    If VALUE is omitted, prints the available values for FEATURE on the resolved target.
    """
    try:
        service = _build_service()
        if value is None:
            target, values = service.feature_values(feature, plugin_id=plugin, device_hint=device)
            value_list = ", ".join(values)
            typer.echo(
                f"Available values for '{feature}' on {target.device.mac} "
                f"({target.plugin.id}): {value_list}"
            )
            return
        result = service.set_feature(feature, value, plugin_id=plugin, device_hint=device)
        typer.echo(
            f"Sent {result.feature}={result.value} to {result.target.device.mac} "
            f"({result.target.plugin.id}) payload={result.payload_hex}"
        )
        if result.response_hex:
            typer.echo(f"response={result.response_hex}")
    except BudsctlError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None


def run() -> None:
    app()


if __name__ == "__main__":
    run()
