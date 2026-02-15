"""Plugin loading and validation for YAML-based budsctl plugins."""

from __future__ import annotations

import logging
import json
import os
import re
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

import yaml
from jsonschema import ValidationError, validators

from budsctl.core.errors import PluginLoadError, PluginValidationError
from budsctl.core.model import EnumFeature, MatchRules, Plugin, TransportSpec

_HEX_RE = re.compile(r"^[0-9a-f]+$")
_UUID_RE = re.compile(r"^[0-9a-f]{4}$|^[0-9a-f]{8}$|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_MAX_PAYLOAD_BYTES = 512
LOGGER = logging.getLogger(__name__)


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


UniqueKeyLoader.yaml_implicit_resolvers = {
    key: list(value) for key, value in yaml.SafeLoader.yaml_implicit_resolvers.items()
}

for first_char, mappings in list(UniqueKeyLoader.yaml_implicit_resolvers.items()):
    UniqueKeyLoader.yaml_implicit_resolvers[first_char] = [
        (tag, regexp)
        for tag, regexp in mappings
        if tag != "tag:yaml.org,2002:bool"
    ]


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.Node, deep: bool = False) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise PluginValidationError(f"Duplicate key '{key}' in YAML document")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True)
class LoadedPlugins:
    plugins: dict[str, Plugin]
    warnings: tuple[str, ...]


def _load_schema_validator() -> Any:
    schema_text = resources.files("budsctl.schemas").joinpath("plugin.schema.json").read_text(
        encoding="utf-8"
    )
    schema = json.loads(schema_text)
    validator_cls = validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)


def _plugin_dirs() -> tuple[Path, Path]:
    xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    xdg_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return xdg_config / "budsctl/plugins", xdg_data / "budsctl/plugins"


def _read_yaml(path: Path | Traversable) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PluginLoadError(f"Could not read plugin file {path}: {exc}") from exc

    try:
        loaded = yaml.load(content, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise PluginValidationError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(loaded, dict):
        raise PluginValidationError(f"Plugin file {path} must contain a mapping at root")
    return loaded


def _normalize_hex(value: str, *, context: str) -> bytes:
    normalized = value.strip().lower().replace(" ", "")
    if len(normalized) == 0:
        raise PluginValidationError(f"{context} must not be empty")
    if len(normalized) % 2 != 0:
        raise PluginValidationError(f"{context} must have even-length hex")
    if not _HEX_RE.match(normalized):
        raise PluginValidationError(f"{context} must contain only [0-9a-f]")
    payload = bytes.fromhex(normalized)
    if len(payload) > _MAX_PAYLOAD_BYTES:
        raise PluginValidationError(
            f"{context} exceeds max payload size {_MAX_PAYLOAD_BYTES} bytes"
        )
    return payload


def _normalize_mac_prefix(prefix: str) -> str:
    return prefix.strip().upper()


def _normalize_uuid(value: str, *, context: str) -> str:
    normalized = value.strip().lower()
    if not _UUID_RE.match(normalized):
        raise PluginValidationError(
            f"{context} must be a 16-bit, 32-bit, or 128-bit UUID string"
        )
    return normalized


def _normalize_bool(value: Any, *, context: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    raise PluginValidationError(f"{context} must be boolean true/false")


def _build_plugin(doc: dict[str, Any], source: Path | Traversable) -> Plugin:
    validator = _load_schema_validator()
    try:
        validator.validate(doc)
    except ValidationError as exc:
        path = ".".join(str(p) for p in exc.path)
        where = f" ({path})" if path else ""
        raise PluginValidationError(f"Schema validation failed for {source}{where}: {exc.message}") from exc

    features: dict[str, EnumFeature] = {}
    for feature_name, feature_spec in doc["features"].items():
        values: dict[str, bytes] = {}
        for value_name, hex_payload in feature_spec["values"].items():
            context = f"{doc['id']}.{feature_name}.{value_name}"
            values[value_name] = _normalize_hex(hex_payload, context=context)
        features[feature_name] = EnumFeature(type="enum", values=values)

    transport_type = doc["transport"]["type"]
    transport = TransportSpec(type=transport_type)
    if transport_type == "rfcomm":
        transport = TransportSpec(
            type="rfcomm",
            channel=int(doc["transport"]["channel"]),
            timeout_s=float(doc["transport"].get("timeout_s", 3.0)),
        )
    elif transport_type == "ble":
        transport = TransportSpec(
            type="ble",
            service_uuid=_normalize_uuid(
                doc["transport"]["service_uuid"],
                context=f"{doc['id']}.transport.service_uuid",
            ),
            write_char_uuid=_normalize_uuid(
                doc["transport"]["write_char_uuid"],
                context=f"{doc['id']}.transport.write_char_uuid",
            ),
            notify_char_uuid=_normalize_uuid(
                doc["transport"]["notify_char_uuid"],
                context=f"{doc['id']}.transport.notify_char_uuid",
            )
            if "notify_char_uuid" in doc["transport"]
            else None,
            write_with_response=_normalize_bool(
                doc["transport"].get("write_with_response", True),
                context=f"{doc['id']}.transport.write_with_response",
            ),
            timeout_s=float(doc["transport"].get("timeout_s", 5.0)),
        )
    else:
        raise PluginValidationError(
            f"Unsupported transport type '{transport_type}' in {source}"
        )

    return Plugin(
        id=doc["id"],
        name=doc["name"],
        match=MatchRules(
            name_contains=tuple(doc["match"].get("name_contains", [])),
            mac_prefix=tuple(_normalize_mac_prefix(p) for p in doc["match"].get("mac_prefix", [])),
        ),
        transport=transport,
        features=features,
    )


def _iter_packaged_plugin_paths() -> list[Traversable]:
    plugin_root = resources.files("budsctl.plugins")
    return [item for item in plugin_root.iterdir() if item.name.endswith((".yml", ".yaml"))]


def _iter_user_plugin_paths() -> list[Path]:
    paths: list[Path] = []
    for directory in _plugin_dirs():
        if not directory.exists() or not directory.is_dir():
            continue
        paths.extend(sorted(p for p in directory.iterdir() if p.suffix in {".yml", ".yaml"}))
    return paths


def load_plugins() -> LoadedPlugins:
    plugins: dict[str, Plugin] = {}
    warnings: list[str] = []

    for path in sorted(_iter_packaged_plugin_paths(), key=lambda p: p.name):
        doc = _read_yaml(path)
        plugin = _build_plugin(doc, path)
        plugins[plugin.id] = plugin

    for path in _iter_user_plugin_paths():
        doc = _read_yaml(path)
        plugin = _build_plugin(doc, path)
        if plugin.id in plugins:
            warning = f"User plugin '{plugin.id}' overrides packaged plugin"
            LOGGER.warning(warning)
            warnings.append(warning)
        plugins[plugin.id] = plugin

    return LoadedPlugins(plugins=plugins, warnings=tuple(warnings))
