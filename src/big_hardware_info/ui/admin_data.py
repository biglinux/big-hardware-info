"""Admin (root) hardware data collection controller.

Runs inxi via pkexec in a background thread, normalizes the response, and
reports completion on the GLib main loop.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
from typing import Callable, Dict

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib

from big_hardware_info.utils.i18n import _


logger = logging.getLogger(__name__)


PKEXEC_TIMEOUT_SEC = 120

INXI_ADMIN_COMMAND = [
    "pkexec", "inxi", "-Fxxxza", "--tty",
    "--output", "json", "--output-file", "print",
]

# Map of inxi section-name substring -> key used by the rest of the UI code.
_SECTION_TO_KEY = (
    ("Graphics", "gpu_detailed"),
    ("Drives", "disk_smart"),
    ("Sensors", "sensors_detailed"),
    ("Unmounted", "unmounted"),
)

# Map raw result keys to the keys consumed by renderers.
RESULT_KEY_MAPPING = {
    "gpu_detailed": "advanced_gpu",
    "disk_smart": "smart_data",
    "sensors_detailed": "advanced_sensors",
    "unmounted": "unmounted",
    "full_inxi": "raw_inxi",
}


class AdminDataController:
    """Coordinate pkexec-based inxi collection and UI feedback."""

    def __init__(
        self,
        window,
        on_complete: Callable[[Dict[str, str]], None],
    ) -> None:
        """Initialize the controller.

        Args:
            window: MainWindow-like instance exposing ``toast_overlay``.
            on_complete: Callback invoked on the main thread with either the
                collected data dict (merged keys) or an empty dict on failure.
        """
        self._window = window
        self._on_complete = on_complete

    def is_available(self) -> bool:
        """Return True when ``pkexec`` is installed."""
        return shutil.which("pkexec") is not None

    def collect(self, button) -> None:
        """Kick off admin collection in a background thread.

        Args:
            button: GTK button to show an in-progress icon on; restored
                when the worker finishes.
        """
        if not self.is_available():
            self._show_unavailable_dialog()
            return

        button.set_sensitive(False)
        button.set_icon_name("emblem-synchronizing-symbolic")

        thread = threading.Thread(
            target=self._worker, args=(button,), daemon=True,
        )
        thread.start()

    def _worker(self, button) -> None:
        raw = self._run_inxi()
        GLib.idle_add(self._finalize, button, raw)

    def _run_inxi(self) -> Dict[str, str]:
        """Run inxi under pkexec and return normalized root data.

        Returns an empty dict if pkexec fails, inxi fails, or the JSON can't
        be parsed into the expected structure. Never raises.
        """
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        env["LANG"] = "C"

        try:
            result = subprocess.run(
                INXI_ADMIN_COMMAND,
                capture_output=True,
                text=True,
                timeout=PKEXEC_TIMEOUT_SEC,
                stdin=subprocess.DEVNULL,
                env=env,
            )
        except subprocess.TimeoutExpired:
            logger.warning("pkexec inxi timed out after %ds", PKEXEC_TIMEOUT_SEC)
            return {}
        except OSError as exc:
            logger.warning("pkexec inxi failed to start: %s", exc)
            return {}

        if result.returncode != 0:
            logger.info(
                "pkexec inxi exited with %s, stderr=%r",
                result.returncode, result.stderr[:200],
            )
            return {}

        stdout = result.stdout.lstrip()
        if not stdout.startswith(("[", "{")):
            logger.warning(
                "pkexec inxi returned non-JSON output: %r",
                result.stdout[:200],
            )
            return {}

        return self._parse_inxi_output(result.stdout)

    @staticmethod
    def _parse_inxi_output(stdout: str) -> Dict[str, str]:
        """Split inxi JSON output into the keys expected by the UI layer."""
        collected: Dict[str, str] = {"full_inxi": stdout}
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            return collected

        for section in parsed:
            if not isinstance(section, dict):
                continue
            for raw_key in section:
                clean = raw_key.split("#")[-1] if "#" in raw_key else raw_key
                for needle, result_key in _SECTION_TO_KEY:
                    if needle in clean:
                        collected[result_key] = json.dumps([section])
                        break
        return collected

    def _finalize(self, button, raw: Dict[str, str]) -> None:
        button.set_sensitive(True)
        button.set_icon_name("security-high-symbolic")

        if raw:
            merged = self._apply_mapping(raw)
            merged["root_collected"] = True
            self._on_complete(merged)
            self._toast(_("Admin data collected successfully"), 2)
        else:
            self._on_complete({})
            self._toast(_("Failed to collect admin data"), 3)

    @staticmethod
    def _apply_mapping(raw: Dict[str, str]) -> Dict[str, object]:
        mapped: Dict[str, object] = {}
        for source, target in RESULT_KEY_MAPPING.items():
            if source in raw:
                mapped[target] = raw[source]
        return mapped

    def _show_unavailable_dialog(self) -> None:
        dialog = Adw.MessageDialog.new(
            self._window,
            _("Admin Access Unavailable"),
            _("The pkexec command is not available on this system."),
        )
        dialog.add_response("ok", _("OK"))
        dialog.present()

    def _toast(self, message: str, seconds: int) -> None:
        overlay = getattr(self._window, "toast_overlay", None)
        if overlay is None:
            return
        toast = Adw.Toast.new(message)
        toast.set_timeout(seconds)
        overlay.add_toast(toast)
