"""
Battery section renderer.
"""

from typing import Dict, List, Tuple

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from app.ui import builders as ui
from app.ui.renderers.base import SectionRenderer
from app.utils.i18n import _


class BatteryRenderer(SectionRenderer):
    """Renderer for battery section."""
    
    def render(self) -> None:
        """Render battery information."""
        battery_data = self.data.get("battery", {})
        
        # Check for battery data
        batteries = battery_data.get("batteries", [])
        if not batteries and not battery_data.get("charge") and not battery_data.get("raw"):
            self.show_no_data(_("No battery detected (Desktop system)"))
            return
        
        # For backwards compatibility
        if not batteries and battery_data.get("charge"):
            batteries = [{
                "id": battery_data.get("model", "Battery"),
                "charge": battery_data.get("charge", 0),
                "condition": battery_data.get("condition", ""),
                "volts": battery_data.get("volts", ""),
                "model": battery_data.get("model", ""),
                "type": battery_data.get("type", ""),
                "serial": battery_data.get("serial", ""),
                "status": battery_data.get("status", ""),
                "cycles": battery_data.get("cycles", ""),
            }]
        
        for battery in batteries:
            self._render_battery_card(battery)
        
        # Raw output
        if battery_data.get("raw"):
            self.add_raw_expander(_("Full Output"), battery_data["raw"])
    
    def _render_battery_card(self, battery: Dict) -> None:
        """Render a single battery card."""
        # Parse charge
        charge = battery.get("charge", 0)
        if isinstance(charge, str):
            try:
                charge = float(charge.replace("%", "").strip())
            except ValueError:
                charge = 0
        
        status = battery.get("status", "").lower()
        model = battery.get("model", "") or battery.get("id", _("Battery"))
        
        card = ui.card()
        
        # Title row with status badge
        title_row = ui.row(spacing=12)
        
        title_lbl = ui.label(model, css_classes=["title-4"], halign=Gtk.Align.START, wrap=True, hexpand=True)
        title_lbl.set_xalign(0)
        title_row.append(title_lbl)
        
        # Status badge
        if status:
            badge_style = None
            if "charging" in status:
                badge_style = "success"
            elif "discharging" in status:
                badge_style = "warning"
            badge = ui.badge(status, badge_style)
            badge.set_valign(Gtk.Align.CENTER)
            title_row.append(badge)
        
        card.append(title_row)
        
        # Charge bar
        if isinstance(charge, (int, float)) and charge > 0:
            bar_row = ui.row(spacing=8)
            bar_row.set_margin_top(4)
            bar_row.set_margin_bottom(4)
            
            # Custom progress bar (different colors than default)
            bar = Gtk.ProgressBar()
            bar.set_fraction(charge / 100.0)
            bar.add_css_class("usage-bar")
            bar.set_hexpand(True)
            if charge > 50:
                bar.add_css_class("success")
            elif charge > 20:
                bar.add_css_class("warning")
            else:
                bar.add_css_class("error")
            bar_row.append(bar)
            
            percent_label = ui.label(f"{charge:.0f}%", css_classes=["stat-value"])
            bar_row.append(percent_label)
            
            card.append(bar_row)
        
        # Two-column layout
        left_items = self._filter_items([
            (_("Condition"), battery.get("condition", "")),
            (_("Type"), battery.get("type", "")),
            (_("Cycles"), battery.get("cycles", "")),
        ])
        
        right_items = self._filter_items([
            (_("Voltage"), battery.get("volts", "")),
            (_("Min Voltage"), battery.get("volts_min", "")),
            (_("Serial"), battery.get("serial", "")),
        ])
        
        if left_items or right_items:
            columns = self._render_columns(left_items, right_items)
            card.append(columns)
        
        self.container.append(card)
    
    def _filter_items(self, items: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Filter out empty/NA items."""
        return [(l, v) for l, v in items if v and v not in ("N/A", "Unknown", "?", "")]
    
    def _render_columns(self, left: List[Tuple], right: List[Tuple]) -> Gtk.Box:
        """Render two-column layout."""
        columns = ui.row(spacing=0)
        
        # Left column
        left_col = ui.box(vertical=True, spacing=8)
        left_col.set_hexpand(True)
        for label, value in left:
            if self.is_filtered_value(value):
                item = ui.box(vertical=True, spacing=4)
                item.append(ui.label(label, css_classes=["spec-label"], halign=Gtk.Align.START))
                item.append(self.create_superuser_widget(label))
                left_col.append(item)
            else:
                left_col.append(ui.spec_item(label, value))
        columns.append(left_col)
        
        if right:
            # Separator
            sep = ui.separator(vertical=True)
            sep.set_margin_start(24)
            sep.set_margin_end(24)
            columns.append(sep)
            
            # Right column
            right_col = ui.box(vertical=True, spacing=8)
            right_col.set_hexpand(True)
            for label, value in right:
                if self.is_filtered_value(value):
                    item = ui.box(vertical=True, spacing=4)
                    item.append(ui.label(label, css_classes=["spec-label"], halign=Gtk.Align.START))
                    item.append(self.create_superuser_widget(label))
                    right_col.append(item)
                else:
                    right_col.append(ui.spec_item(label, value))
            columns.append(right_col)
        
        return columns
