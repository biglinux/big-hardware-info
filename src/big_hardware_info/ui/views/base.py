"""Base class and shared widget factories for hardware section views."""

import re
from typing import Any

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from big_hardware_info.utils.i18n import _


class HardwareSectionView(Gtk.Box):
    """Base class for hardware section views (subclasses override ``render``)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)

    def render(self, data: dict[str, Any]) -> None:
        raise NotImplementedError("Subclasses must implement render() method")

    def clear(self) -> None:
        child = self.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.remove(child)
            child = next_child

    def create_section_title(self, title: str) -> Gtk.Label:
        label = Gtk.Label(label=title)
        label.add_css_class("section-title")
        label.set_halign(Gtk.Align.START)
        return label

    def create_hero_card(self) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        card.add_css_class("card")
        card.add_css_class("hero-card")
        return card

    def create_info_row(self, label: str, value: str) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("info-row")
        
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("dim-label")
        label_widget.set_halign(Gtk.Align.START)
        label_widget.set_width_chars(15)
        label_widget.set_xalign(0)
        row.append(label_widget)
        
        value_widget = Gtk.Label(label=value)
        value_widget.set_halign(Gtk.Align.END)
        value_widget.set_hexpand(True)
        value_widget.set_wrap(True)
        value_widget.set_xalign(1)
        value_widget.set_selectable(True)
        row.append(value_widget)
        
        return row
    
    def create_info_grid(
        self,
        items: list[tuple[str, Any]],
        columns: int = 2,
        row_spacing: int = 6,
        column_spacing: int = 48,
    ) -> Gtk.Grid:
        grid = Gtk.Grid()
        grid.set_row_spacing(row_spacing)
        grid.set_column_spacing(column_spacing)

        row = 0
        col = 0

        for label, value in items:
            if not value or value in ("N/A", "Unknown", "?", ""):
                continue

            label_widget = Gtk.Label(label=label)
            label_widget.add_css_class("info-label")
            label_widget.set_halign(Gtk.Align.START)
            label_widget.set_width_chars(14)
            label_widget.set_xalign(0)
            grid.attach(label_widget, col * 2, row, 1, 1)

            value_widget = Gtk.Label(label=str(value))
            value_widget.add_css_class("info-value")
            value_widget.set_halign(Gtk.Align.START)
            value_widget.set_selectable(True)
            value_widget.set_wrap(True)
            value_widget.set_xalign(0)
            value_widget.set_margin_end(16)
            grid.attach(value_widget, col * 2 + 1, row, 1, 1)

            col += 1
            if col >= columns:
                col = 0
                row += 1

        return grid

    def create_flow_box(
        self,
        homogeneous: bool = True,
        max_per_line: int = 4,
        min_per_line: int = 2,
        row_spacing: int = 12,
        column_spacing: int = 12,
    ) -> Gtk.FlowBox:
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(homogeneous)
        flow.set_max_children_per_line(max_per_line)
        flow.set_min_children_per_line(min_per_line)
        flow.set_row_spacing(row_spacing)
        flow.set_column_spacing(column_spacing)
        return flow

    def create_raw_expander(
        self, title: str, text: str, expanded: bool = False,
    ) -> Gtk.Expander:
        expander = Gtk.Expander(label=title)
        expander.set_expanded(expanded)
        expander.add_css_class("card")

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(300)
        scroll.set_propagate_natural_height(True)

        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_margin_top(8)
        text_view.get_buffer().set_text(text)

        scroll.set_child(text_view)
        expander.set_child(scroll)

        return expander

    def _create_spec_item(self, label: str, value: str) -> Gtk.Box:
        """Spec item: small dim caption above bold heading value."""
        item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        label_w = Gtk.Label(label=label)
        label_w.add_css_class("dim-label")
        label_w.add_css_class("caption")
        label_w.set_halign(Gtk.Align.START)
        item.append(label_w)

        value_w = Gtk.Label(label=str(value))
        value_w.add_css_class("heading")
        value_w.set_halign(Gtk.Align.START)
        value_w.set_selectable(True)
        item.append(value_w)

        return item

    def show_no_data(self, message: str | None = None) -> None:
        if message is None:
            message = _("No data available")
        label = Gtk.Label(label=message)
        label.add_css_class("dim-label")
        label.set_margin_top(32)
        label.set_margin_bottom(32)
        self.append(label)

    def clean_percentage_string(self, value: str) -> str:
        if isinstance(value, str) and "(" in value:
            return re.sub(r'\s*\([0-9.]+%\)', '', value).strip()
        return value
