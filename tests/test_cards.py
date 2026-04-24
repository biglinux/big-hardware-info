"""Tests for ``ui.cards`` — verifies the i18n import fix doesn't regress.

Before the fix, ``cards.py`` referenced ``_()`` without importing it, so
calling ``create_info_card`` with a falsy value raised ``NameError``.
These tests require a display server; skip cleanly if GTK can't init.
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
        from gi.repository import Gtk
        return Gtk.init_check() if hasattr(Gtk, "init_check") else True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _gtk_available(),
                                reason="GTK not available in this environment")


def test_create_info_card_handles_empty_value() -> None:
    from big_hardware_info.ui.cards import create_info_card
    card = create_info_card(
        title="Title",
        subtitle="sub",
        icon_name="computer-symbolic",
        properties=[("Label", "")],  # empty value must not raise NameError
    )
    assert card is not None
    assert hasattr(card, "searchable_text")


def test_create_info_card_populates_searchable_text() -> None:
    from big_hardware_info.ui.cards import create_info_card
    card = create_info_card(
        title="My Card",
        subtitle="Subtitle",
        icon_name="",
        properties=[("Vendor", "Intel")],
    )
    text = card.searchable_text
    assert "My Card" in text
    assert "Intel" in text
