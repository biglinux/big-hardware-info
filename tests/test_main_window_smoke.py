"""End-to-end smoke test for MainWindow with partial/dirty data.

This is the regression test for the "no items appear at startup" bug. It
spins up the real MainWindow (GTK), feeds it deliberately corrupt data
(``memory=None``, missing inxi sections), and asserts that every section
in the registry still produced a widget. Before the fault isolation fix
the count was near zero.
"""

from __future__ import annotations

import os

import pytest


def _gtk_available() -> bool:
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return False
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Gtk
        return True if not hasattr(Gtk, "init_check") else bool(Gtk.init_check())
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _gtk_available(),
    reason="GTK/Adwaita not available in this environment",
)


def test_main_window_renders_every_section_despite_broken_data() -> None:
    """With memory=None and a bare inxi_error, 17 sections still appear."""
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, GLib, Gio

    from big_hardware_info.collectors import HardwareCollector
    from big_hardware_info.ui import MainWindow
    from big_hardware_info.ui import sections
    from big_hardware_info.utils.config import AppConfig

    # Stub the collector — we don't want real hardware calls during tests.
    def fake_collect(self, progress_callback=None):
        return {
            "inxi_error": "simulated",
            "memory": None,          # known crash path for SummaryRenderer
            "gpu": {},
            "cpu": {},
            "system": {},
        }

    HardwareCollector.collect_all = fake_collect  # type: ignore[method-assign]

    rendered_count = {"value": 0}
    app_result = {"code": None}

    class _TestApp(Adw.Application):
        def __init__(self) -> None:
            super().__init__(
                application_id="test.biglinux.bhi.smoke",
                flags=Gio.ApplicationFlags.FLAGS_NONE,
            )

        def do_activate(self) -> None:
            window = MainWindow(application=self, config=AppConfig())
            window.present()

            def _check() -> bool:
                rendered_count["value"] = len(window.section_widgets)
                self.quit()
                return False

            GLib.timeout_add(2500, _check)

    app_result["code"] = _TestApp().run([])

    assert rendered_count["value"] == len(sections.SECTIONS), (
        f"Expected every section to survive one renderer crash; "
        f"got {rendered_count['value']} / {len(sections.SECTIONS)}"
    )
