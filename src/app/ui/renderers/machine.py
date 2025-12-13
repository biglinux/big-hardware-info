"""Machine/Motherboard section renderer."""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk

from app.ui.renderers.base import SectionRenderer
from app.utils.i18n import _


class MachineRenderer(SectionRenderer):
    """Renders machine/motherboard information with modern two-column layout."""
    
    def render(self):
        """Render the machine/motherboard section."""
        machine_data = self.data.get("machine", {})
        
        if not machine_data:
            self.show_no_data(_("No motherboard information available"))
            return
        
        # Hero card with motherboard model as title
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("card")
        card.add_css_class("hero-card")
        
        # Title: Motherboard model or system name
        mobo_title = machine_data.get("mobo_model") or machine_data.get("product") or _("Motherboard")
        title_label = Gtk.Label(label=mobo_title)
        title_label.add_css_class("hero-title")
        title_label.set_halign(Gtk.Align.START)
        card.append(title_label)
        
        # Two columns of info
        left_items = [
            (_("Manufacturer"), machine_data.get("mobo", "")),
            (_("Type"), machine_data.get("type", "")),
            (_("System"), machine_data.get("system", "")),
            (_("Firmware"), machine_data.get("firmware_type", "")),
        ]
        
        right_items = [
            (_("Version"), machine_data.get("mobo_version", "")),
            (_("BIOS Vendor"), machine_data.get("firmware_vendor", "")),
            (_("BIOS Version"), machine_data.get("firmware_version", "")),
            (_("BIOS Date"), machine_data.get("firmware_date", "")),
        ]
        
        # Filter empty values
        left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "Unknown")]
        right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "Unknown")]
        
        # Two-column layout with separator
        columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        # Left column
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_col.set_hexpand(True)
        for label, value in left_items:
            item = self._create_spec_item(label, value)
            left_col.append(item)
        columns_box.append(left_col)
        
        if right_items:
            # Visual separator
            separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            separator.set_margin_start(24)
            separator.set_margin_end(24)
            columns_box.append(separator)
            
            # Right column
            right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            right_col.set_hexpand(True)
            for label, value in right_items:
                item = self._create_spec_item(label, value)
                right_col.append(item)
            columns_box.append(right_col)
        
        card.append(columns_box)
        self.container.append(card)
        
        if machine_data.get("raw"):
            self.add_raw_expander(_("Full Output"), machine_data["raw"])
    
    def _create_spec_item(self, label: str, value: str) -> Gtk.Box:
        """Create a specification item with label and value."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("dim-label")
        label_widget.add_css_class("caption")
        label_widget.set_halign(Gtk.Align.START)
        box.append(label_widget)
        
        value_widget = Gtk.Label(label=value)
        value_widget.set_halign(Gtk.Align.START)
        value_widget.set_selectable(True)
        value_widget.set_wrap(True)
        box.append(value_widget)
        
        return box
