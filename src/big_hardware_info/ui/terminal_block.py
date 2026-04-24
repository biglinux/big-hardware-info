"""Terminal-style output block widget.

Renders a monospace block with syntax highlighting, a copy button, and an
expand/collapse toggle when the content exceeds a visible-lines threshold.
"""

from typing import Callable, Optional

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from big_hardware_info.ui import builders as ui
from big_hardware_info.ui import highlighting
from big_hardware_info.utils.i18n import _


DEFAULT_MAX_LINES = 15
LINE_HEIGHT_PX = 22


def create_terminal_block(
    title: str,
    text: str,
    max_lines: int = DEFAULT_MAX_LINES,
    on_copy: Optional[Callable[[str, str], None]] = None,
) -> Gtk.Widget:
    """Build a terminal-style block widget.

    Args:
        title: Title shown in the header.
        text: Full text content to display.
        max_lines: How many lines to show before collapsing.
        on_copy: Optional callback ``(text, title)`` invoked by the copy button.

    Returns:
        A ``Gtk.Box`` ready to be appended to a container.
    """
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    card.add_css_class("terminal-card")

    card.append(_build_title_bar(title, text, on_copy))

    lines = text.split("\n")
    total_lines = len(lines)
    visible_text = "\n".join(lines[:max_lines])

    text_view = _build_text_view()
    scroll = _build_scroll(max_lines, text_view)
    highlighting.apply_highlighting(text_view.get_buffer(), visible_text)

    card.append(scroll)

    if total_lines > max_lines:
        card.append(_build_expander_row(
            text_view, text, visible_text, total_lines, max_lines,
        ))

    return card


def _build_title_bar(
    title: str,
    text: str,
    on_copy: Optional[Callable[[str, str], None]],
) -> Gtk.Box:
    bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    bar.add_css_class("terminal-title")

    title_label = Gtk.Label(label=title)
    title_label.set_halign(Gtk.Align.START)
    title_label.set_hexpand(True)
    bar.append(title_label)

    if on_copy is not None:
        copy_btn = ui.copy_button(
            tooltip=_("Copy content to clipboard"),
            on_click=lambda _btn: on_copy(text, title),
        )
        copy_btn.set_valign(Gtk.Align.CENTER)
        bar.append(copy_btn)

    return bar


def _build_text_view() -> Gtk.TextView:
    view = Gtk.TextView()
    view.set_editable(False)
    view.set_cursor_visible(False)
    view.set_monospace(True)
    view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    view.add_css_class("terminal-text")
    return view


def _build_scroll(max_lines: int, child: Gtk.Widget) -> Gtk.ScrolledWindow:
    height = max_lines * LINE_HEIGHT_PX
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scroll.set_min_content_height(height)
    scroll.set_max_content_height(height)
    scroll.set_propagate_natural_height(False)
    scroll.set_child(child)
    return scroll


def _build_expander_row(
    text_view: Gtk.TextView,
    full_text: str,
    short_text: str,
    total_lines: int,
    max_lines: int,
) -> Gtk.Box:
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    row.set_margin_start(12)
    row.set_margin_end(12)
    row.set_margin_top(4)
    row.set_margin_bottom(8)

    more_label = Gtk.Label(
        label=f"... {total_lines - max_lines} " + _("more lines hidden")
    )
    more_label.add_css_class("dim-label")
    more_label.add_css_class("caption")
    more_label.set_halign(Gtk.Align.START)
    more_label.set_hexpand(True)
    row.append(more_label)

    toggle = Gtk.ToggleButton(label=_("Show all"))
    toggle.add_css_class("flat")
    toggle.add_css_class("caption")
    toggle.connect(
        "toggled",
        _on_toggle,
        text_view,
        full_text,
        short_text,
        more_label,
        total_lines,
        max_lines,
    )
    row.append(toggle)
    return row


def _on_toggle(
    button: Gtk.ToggleButton,
    text_view: Gtk.TextView,
    full_text: str,
    short_text: str,
    label: Gtk.Label,
    total_lines: int,
    max_lines: int,
) -> None:
    buffer = text_view.get_buffer()
    if button.get_active():
        highlighting.apply_highlighting(buffer, full_text)
        button.set_label(_("Show less"))
        label.set_text(_("Showing all") + f" {total_lines} " + _("lines"))
    else:
        highlighting.apply_highlighting(buffer, short_text)
        button.set_label(_("Show all"))
        label.set_text(
            f"... {total_lines - max_lines} " + _("more lines hidden")
        )
