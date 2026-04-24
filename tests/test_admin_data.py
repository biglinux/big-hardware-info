"""Tests for AdminDataController — pkexec-based inxi collection."""

import json
import subprocess
from unittest.mock import MagicMock, patch

from big_hardware_info.ui.admin_data import (
    AdminDataController,
    RESULT_KEY_MAPPING,
)


def _make_controller():
    window = MagicMock()
    window.toast_overlay = None
    on_complete = MagicMock()
    return AdminDataController(window, on_complete), on_complete


def _fake_run(returncode: int, stdout: str = "", stderr: str = ""):
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def test_run_inxi_returns_empty_on_non_zero_exit() -> None:
    controller, _ = _make_controller()
    with patch("big_hardware_info.ui.admin_data.subprocess.run",
               return_value=_fake_run(127)):
        assert controller._run_inxi() == {}


def test_run_inxi_returns_empty_on_timeout() -> None:
    controller, _ = _make_controller()
    with patch("big_hardware_info.ui.admin_data.subprocess.run",
               side_effect=subprocess.TimeoutExpired(cmd="inxi", timeout=1)):
        assert controller._run_inxi() == {}


def test_run_inxi_returns_empty_on_oserror() -> None:
    controller, _ = _make_controller()
    with patch("big_hardware_info.ui.admin_data.subprocess.run",
               side_effect=FileNotFoundError()):
        assert controller._run_inxi() == {}


def test_parse_inxi_output_extracts_known_sections() -> None:
    sample = json.dumps([
        {"000#1#0#Graphics": [{"device": "GPU0"}]},
        {"001#1#0#Drives": [{"model": "NVMe0"}]},
        {"002#1#0#Sensors": [{"temp": 40}]},
        {"003#1#0#Unmounted": [{"device": "/dev/sdb1"}]},
        {"004#1#0#Other": [{"ignore": "me"}]},
    ])
    parsed = AdminDataController._parse_inxi_output(sample)
    assert parsed["full_inxi"] == sample
    assert "gpu_detailed" in parsed
    assert "disk_smart" in parsed
    assert "sensors_detailed" in parsed
    assert "unmounted" in parsed


def test_parse_inxi_output_handles_invalid_json() -> None:
    parsed = AdminDataController._parse_inxi_output("not-json")
    assert parsed == {"full_inxi": "not-json"}


def test_apply_mapping_remaps_keys_for_ui() -> None:
    raw = {
        "gpu_detailed": "a",
        "disk_smart": "b",
        "sensors_detailed": "c",
        "unmounted": "d",
        "full_inxi": "e",
        "irrelevant": "skip",
    }
    mapped = AdminDataController._apply_mapping(raw)
    for src, dst in RESULT_KEY_MAPPING.items():
        assert mapped[dst] == raw[src]
    assert "irrelevant" not in mapped
