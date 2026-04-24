"""Tests for window geometry persistence helpers."""

from unittest.mock import MagicMock

from big_hardware_info.ui.window_state import (
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    read_initial_geometry,
)


def test_read_initial_geometry_returns_defaults_without_config() -> None:
    width, height, maximized = read_initial_geometry(None)
    assert width == DEFAULT_WIDTH
    assert height == DEFAULT_HEIGHT
    assert maximized is False


def test_read_initial_geometry_coerces_numeric_strings() -> None:
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "window_width": "1500",
        "window_height": "900",
        "window_maximized": True,
    }.get(key, default)
    width, height, maximized = read_initial_geometry(config)
    assert (width, height) == (1500, 900)
    assert maximized is True


def test_read_initial_geometry_falls_back_on_bad_values() -> None:
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "window_width": "not-a-number",
        "window_height": None,
        "window_maximized": False,
    }.get(key, default)
    width, height, _ = read_initial_geometry(config)
    assert width == DEFAULT_WIDTH
    assert height == DEFAULT_HEIGHT
