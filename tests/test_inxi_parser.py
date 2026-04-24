"""Tests for InxiParser.parse_full.

These tests pin the shape of the parser's output so renderers can rely on
stable keys. The parser must always return a dict with baseline category
keys even when the input is malformed or empty — that invariant is what
keeps the section renderers from seeing ``None`` values.
"""

from big_hardware_info.collectors.inxi_parser import InxiParser


BASELINE_KEYS = {
    "cpu", "gpu", "memory", "audio", "network",
    "disk", "machine", "system", "battery", "sensors", "bluetooth",
}


def test_parse_full_empty_list() -> None:
    result = InxiParser().parse_full([])
    assert BASELINE_KEYS.issubset(result.keys())
    for key in BASELINE_KEYS:
        assert isinstance(result[key], dict), f"{key} should be dict, got {type(result[key])}"


def test_parse_full_rejects_non_list() -> None:
    result = InxiParser().parse_full(None)  # type: ignore[arg-type]
    assert BASELINE_KEYS.issubset(result.keys())


def test_parse_full_ignores_unknown_sections() -> None:
    result = InxiParser().parse_full([{"999#9#9#Unknown": [{"foo": "bar"}]}])
    # Unknown sections don't crash and don't overwrite baseline keys.
    assert BASELINE_KEYS.issubset(result.keys())
    assert result["cpu"] == {}


def test_parse_full_populates_cpu_section() -> None:
    data = [{
        "000#1#0#CPU": [{
            "001#1#1#Info": "quad core Intel Core i7",
            "002#1#2#model": "Intel Core i7-9700K",
            "003#1#2#bits": 64,
        }],
    }]
    result = InxiParser().parse_full(data)
    assert result["cpu"]["model"] == "Intel Core i7-9700K"
    assert result["cpu"]["bits"] == 64
    assert result["cpu"]["cores"] == 4


def test_parse_full_returns_pci_inxi_even_without_devices() -> None:
    result = InxiParser().parse_full([])
    assert "pci_inxi" in result
    assert result["pci_inxi"]["count"] == 0
