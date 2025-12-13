import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from big_hardware_info.ui.renderers.summary import SummaryRenderer


class DummyWindow:
    def __init__(self):
        self.hardware_data = {}


def test_summary_copy_has_no_placeholders():
    win = DummyWindow()
    renderer = SummaryRenderer(win)

    memory = {"total": "8 GB", "used": "4 GB (50%)", "used_percent": 50}
    disk = {"device": "/dev/sda1", "size": "100 GB", "used": "20 GB", "available": "80 GB", "use_percent": "20%"}

    txt = renderer._format_usage_copy(memory, disk)
    assert "{" not in txt and "}" not in txt
    assert "8 GB" in txt
    assert "/dev/sda1" in txt


def test_system_copy_has_no_placeholders():
    win = DummyWindow()
    renderer = SummaryRenderer(win)

    s = renderer._format_system_copy("Ubuntu", "NVIDIA GPU", "2025-12-01", "5.10.0")
    assert "{" not in s and "}" not in s
    assert "Ubuntu" in s
    assert "NVIDIA GPU" in s
    assert "5.10.0" in s
