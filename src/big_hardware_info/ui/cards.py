"""Card factory widgets used by hardware section views."""

from typing import Optional

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from big_hardware_info.ui import builders as ui
from big_hardware_info.utils.i18n import _


def create_info_card(
    title: str,
    subtitle: str = "",
    icon_name: str = "",
    properties: Optional[list[tuple]] = None,
    searchable_extra: str = "",
) -> Gtk.Widget:
    """Create an Adwaita-style info card with optional properties list."""
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    card.add_css_class("card")

    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

    if icon_name:
        icon = ui.icon(icon_name, 48)
        icon.add_css_class("accent")
        header.append(icon)

    title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    title_box.set_valign(Gtk.Align.CENTER)

    title_label = Gtk.Label(label=title)
    title_label.add_css_class("title-3")
    title_label.set_halign(Gtk.Align.START)
    title_label.set_wrap(True)
    title_label.set_selectable(True)
    title_box.append(title_label)

    if subtitle:
        sub_label = Gtk.Label(label=subtitle)
        sub_label.add_css_class("dim-label")
        sub_label.set_halign(Gtk.Align.START)
        sub_label.set_wrap(True)
        sub_label.set_selectable(True)
        title_box.append(sub_label)

    header.append(title_box)
    card.append(header)

    if properties:
        props_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        props_box.set_margin_top(8)

        for prop in properties:
            if len(prop) >= 2:
                label, value = prop[0], prop[1]

                prop_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

                label_widget = Gtk.Label(label=f"{label}:")
                label_widget.add_css_class("dim-label")
                label_widget.set_halign(Gtk.Align.START)
                label_widget.set_width_chars(15)
                label_widget.set_xalign(0)
                prop_row.append(label_widget)

                value_widget = Gtk.Label(label=str(value) if value else _("N/A"))
                value_widget.set_halign(Gtk.Align.START)
                value_widget.set_hexpand(True)
                value_widget.set_wrap(True)
                value_widget.set_xalign(0)
                value_widget.set_selectable(True)
                prop_row.append(value_widget)

                props_box.append(prop_row)

        card.append(props_box)

    searchable_parts = [title, subtitle, searchable_extra]
    if properties:
        for prop in properties:
            if len(prop) >= 2:
                searchable_parts.append(f"{prop[0]} {prop[1]}")

    card.searchable_text = " ".join(filter(None, searchable_parts))

    return card
