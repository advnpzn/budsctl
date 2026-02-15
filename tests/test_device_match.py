from budsctl.core.device_match import best_plugin_for_device, match_score
from budsctl.core.model import DetectedDevice, EnumFeature, MatchRules, Plugin, TransportSpec


def _plugin(plugin_id: str, name_tokens: tuple[str, ...], mac_prefixes: tuple[str, ...]) -> Plugin:
    return Plugin(
        id=plugin_id,
        name=plugin_id,
        match=MatchRules(name_contains=name_tokens, mac_prefix=mac_prefixes),
        transport=TransportSpec(type="rfcomm", channel=15),
        features={"anc": EnumFeature(type="enum", values={"on": bytes.fromhex("aa00")})},
    )


def test_match_score_prefers_combined_match() -> None:
    device = DetectedDevice(mac="88:92:CC:00:11:22", name="OnePlus Buds 4")
    plugin = _plugin("p1", ("OnePlus Buds 4",), ("88:92:CC",))
    assert match_score(device, plugin) == 3


def test_best_plugin_prefers_mac_only_over_name_only() -> None:
    device = DetectedDevice(mac="88:92:CC:00:11:22", name="Generic Earbuds")
    name_plugin = _plugin("name", ("Generic",), ("AA:BB:CC",))
    mac_plugin = _plugin("mac", ("Other",), ("88:92:CC",))

    picked = best_plugin_for_device(device, {"name": name_plugin, "mac": mac_plugin})
    assert picked is not None
    assert picked.id == "mac"


def test_no_match_returns_none() -> None:
    device = DetectedDevice(mac="00:00:00:00:00:00", name="Unknown")
    plugin = _plugin("p1", ("OnePlus",), ("88:92:CC",))
    assert best_plugin_for_device(device, {"p1": plugin}) is None
