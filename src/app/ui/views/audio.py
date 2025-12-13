"""
Audio Section View for Hardware Reporter.

Renders detailed audio device information following GNOME HIG guidelines.
"""

from typing import Dict, Any, Optional, Callable

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from app.ui.views.base import HardwareSectionView
from app.utils.i18n import _


class AudioSectionView(HardwareSectionView):
    """
    View component for displaying audio device information.
    
    Displays:
    - Audio device cards with two-column layout
    - USB/PCIe connection info
    - Linux Hardware DB links
    """
    
    CATEGORY_ID = "audio"
    
    def __init__(
        self, 
        open_url_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> None:
        """Initialize the audio section view.
        
        Args:
            open_url_callback: Callback for opening URLs.
        """
        super().__init__(**kwargs)
        self._open_url_callback = open_url_callback
    
    def render(self, data: Dict[str, Any]) -> None:
        """
        Render audio information.
        
        Args:
            data: Audio hardware data dictionary.
        """
        self.clear()
        
        if not data:
            self.show_no_data(_("No audio information available"))
            return
        
        devices = data.get("devices", [])
        
        if not devices:
            self.show_no_data(_("No audio devices found"))
            return
        
        for device in devices:
            card = self._create_audio_card(device)
            self.append(card)
        
        # Raw output
        if data.get("raw"):
            expander = self.create_raw_expander(_("Full Output"), data["raw"])
            self.append(expander)
    
    def _create_audio_card(self, device: Dict[str, Any]) -> Gtk.Box:
        """Create a card for an audio device."""
        name = device.get("name", _("Unknown Audio Device"))
        
        # Build Linux Hardware URL
        chip_id = device.get("chip_id", "")
        linux_hardware_url = ""
        if chip_id and ":" in chip_id:
            vendor_id, device_id = chip_id.split(":", 1)
            linux_hardware_url = f"https://linux-hardware.org/?id=pci:{vendor_id}-{device_id}"
        
        # Connection info (USB or PCIe)
        connection_info = ""
        connection_label = ""
        if device.get("type") == "USB":
            connection_label = _("USB")
            usb_rev = device.get("usb_rev", "")
            usb_speed = device.get("usb_speed", "")
            if usb_rev and usb_speed:
                connection_info = f"{usb_rev} {usb_speed}"
            elif usb_speed:
                connection_info = usb_speed
            elif usb_rev:
                connection_info = usb_rev
        else:
            connection_label = _("PCIe")
            if device.get("pcie_gen") and device.get("pcie_lanes"):
                connection_info = f"Gen {device.get('pcie_gen')} x{device.get('pcie_lanes')}"
            elif device.get("pcie_speed") and device.get("pcie_lanes"):
                connection_info = f"{device.get('pcie_speed')} x{device.get('pcie_lanes')}"
        
        # Build columns
        left_items = [
            (_("Vendor"), device.get("vendor", "")),
            (_("Driver"), device.get("driver", "")),
            (_("Class ID"), device.get("class_id", "")),
        ]
        
        right_items = [
            (_("Bus ID"), device.get("bus_id", "")),
            (_("Chip ID"), chip_id),
            (connection_label, connection_info),
        ]
        
        # Filter empty values
        left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "Unknown", "?", "")]
        right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "Unknown", "?", "")]
        
        # Create card
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("card")
        
        # Title row
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        title_label = Gtk.Label(label=name)
        title_label.add_css_class("title-4")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_wrap(True)
        title_label.set_xalign(0)
        title_label.set_hexpand(True)
        title_row.append(title_label)
        
        # Info button
        if linux_hardware_url and self._open_url_callback:
            link_btn = Gtk.Button(label=_("info"))
            link_btn.add_css_class("flat")
            link_btn.set_tooltip_text(
                _("View device info on Linux Hardware Database\n"
                  "See driver compatibility and troubleshooting tips")
            )
            link_btn.set_valign(Gtk.Align.CENTER)
            link_btn.connect("clicked", lambda b, u=linux_hardware_url: self._open_url_callback(u))
            title_row.append(link_btn)
        
        # Copy button
        copy_btn = self._create_copy_button(device, name)
        title_row.append(copy_btn)
        
        card.append(title_row)
        
        # Two-column layout
        columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        # Left column
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_col.set_hexpand(True)
        for label, value in left_items:
            item = self._create_spec_item(label, value)
            left_col.append(item)
        columns_box.append(left_col)
        
        # Separator
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
        
        return card
    
    def _create_copy_button(self, device: Dict[str, Any], name: str) -> Gtk.Button:
        """Create a copy button for device data."""
        btn = Gtk.Button()
        btn.set_icon_name("edit-copy-symbolic")
        btn.add_css_class("flat")
        btn.set_tooltip_text(_("Copy device info"))
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda b, d=device, n=name: self._copy_device_data(d, n))
        return btn
    
    def _copy_device_data(self, device: Dict[str, Any], name: str) -> None:
        """Copy device data to clipboard."""
        lines = [
            f"=== {name} ===",
            "",
        ]
        
        for key in ["vendor", "driver", "bus_id", "chip_id", "class_id"]:
            value = device.get(key, "")
            if value:
                lines.append(f"{key}: {value}")
        
        text = "\n".join(lines)
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
