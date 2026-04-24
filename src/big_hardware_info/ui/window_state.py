"""Window size/maximized state persistence.

Debounces size changes and writes them through an ``AppConfig``-like object
so window dimensions survive restarts without thrashing disk on every pixel
the user drags.
"""

from __future__ import annotations

import logging
from typing import Optional, Protocol

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk


logger = logging.getLogger(__name__)


SAVE_DEBOUNCE_MS = 500
RESTORE_MAXIMIZE_DELAY_MS = 100

DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 850


class _ConfigLike(Protocol):
    def get(self, key: str, default=None): ...
    def set(self, key: str, value) -> bool: ...


def read_initial_geometry(config: Optional[_ConfigLike]) -> tuple[int, int, bool]:
    """Return (width, height, maximized) from config with fallback defaults."""
    if config is None:
        return DEFAULT_WIDTH, DEFAULT_HEIGHT, False

    try:
        width = int(config.get("window_width", DEFAULT_WIDTH))
        height = int(config.get("window_height", DEFAULT_HEIGHT))
    except (ValueError, TypeError):
        width, height = DEFAULT_WIDTH, DEFAULT_HEIGHT

    maximized = bool(config.get("window_maximized", False))
    return width, height, maximized


class WindowStatePersister:
    """Persist size/maximize state for a ``Gtk.Window``."""

    def __init__(self, window: Gtk.Window, config: Optional[_ConfigLike]) -> None:
        """Bind size/state signals on ``window`` and prepare debounced saves."""
        self._window = window
        self._config = config
        self._save_timeout_id: Optional[int] = None

        if config is None:
            return

        window.connect("notify::default-width", self._on_size_change)
        window.connect("notify::default-height", self._on_size_change)
        window.connect("notify::maximized", self._on_maximize_change)
        window.connect("close-request", self._on_close_request)

    def restore_maximized_if_needed(self, maximized: bool) -> None:
        """Schedule ``maximize()`` shortly after the window is shown."""
        if maximized:
            GLib.timeout_add(RESTORE_MAXIMIZE_DELAY_MS, self._window.maximize)

    def _on_size_change(self, _window: Gtk.Window, _param) -> None:
        if self._window.is_maximized():
            return
        if self._save_timeout_id is not None:
            GLib.source_remove(self._save_timeout_id)
        self._save_timeout_id = GLib.timeout_add(
            SAVE_DEBOUNCE_MS, self._flush_size,
        )

    def _on_maximize_change(self, _window: Gtk.Window, _param) -> None:
        if self._config is None:
            return
        self._config.set("window_maximized", self._window.is_maximized())

    def _on_close_request(self, _window: Gtk.Window) -> bool:
        if not self._window.is_maximized():
            self._flush_size()
        return False

    def _flush_size(self) -> bool:
        self._save_timeout_id = None
        if self._config is None:
            return False
        self._config.set("window_width", self._window.get_width())
        self._config.set("window_height", self._window.get_height())
        return False
