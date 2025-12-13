"""
Bluetooth section renderer.
"""

from typing import Dict

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from big_hardware_info.ui import builders as ui
from big_hardware_info.ui.renderers.base import SectionRenderer
from big_hardware_info.utils.i18n import _


class BluetoothRenderer(SectionRenderer):
    """Renderer for Bluetooth section."""
    
    def render(self) -> None:
        """Render Bluetooth devices."""
        bt_data = self.data.get("bluetooth", {})
        devices = bt_data.get("devices", [])
        
        if not devices:
            self.show_no_data(_("No Bluetooth devices detected"))
            return
        
        for device in devices:
            self._render_device_card(device)
    
    def _render_device_card(self, device: Dict) -> None:
        """Render a Bluetooth device card."""
        name = device.get("name", "Unknown Bluetooth Device")
        vendor = device.get("vendor", "")
        bus_id = device.get("bus_id", "")
        chip_id = device.get("chip_id", "")
        driver = device.get("driver", "")
        
        # Build hardware info URL
        info_url = ""
        if chip_id and ":" in chip_id:
            url_id = chip_id.replace(":", "-")
            info_url = f"https://linux-hardware.org/?id=usb:{url_id}"
        
        left_items = [
            (_("Vendor"), vendor),
            (_("Chip ID"), chip_id),
        ]
        
        right_items = [
            (_("Bus ID"), bus_id),
            (_("Driver"), driver),
        ]
        
        title_widgets = []
        if info_url:
            title_widgets.append(ui.flat_button(
                label_text=_("info"),
                tooltip=_("View device info on Linux Hardware Database"),
                on_click=lambda b, u=info_url: self.open_url(u)
            ))
        
        copy_text = self.format_copy_text(name, [
            ("Vendor", vendor),
            ("Chip ID", chip_id),
            ("Bus ID", bus_id),
            ("Driver", driver),
        ])
        title_widgets.append(ui.copy_button(
            on_click=lambda b: self.copy_to_clipboard(copy_text, name)
        ))
        
        card = ui.two_column_card(name, left_items, right_items, title_widgets)
        self.container.append(card)
