"""
USB section renderer.
"""

from typing import Dict, List

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from app.ui import builders as ui
from app.ui.renderers.base import SectionRenderer
from app.utils.i18n import _


class UsbRenderer(SectionRenderer):
    """Renderer for USB devices section."""
    
    SYSTEM_KEYWORDS = [
        "root hub", "linux foundation", "rate matching hub",
        "host controller", "usb controller"
    ]
    
    def render(self) -> None:
        """Render USB device information."""
        usb_inxi = self.data.get("usb_inxi", {})
        usb_lsusb = self.data.get("usb", {})
        
        # Prefer inxi data
        if usb_inxi.get("devices") or usb_inxi.get("hubs"):
            self._render_inxi_data(usb_inxi)
        elif usb_lsusb.get("devices"):
            self._render_lsusb_data(usb_lsusb)
        else:
            self.show_no_data(_("No USB devices found"))
    
    def _render_inxi_data(self, data: Dict) -> None:
        """Render USB data from inxi."""
        devices = data.get("devices", [])
        hubs = data.get("hubs", [])
        
        if devices:
            self._add_section_title(_("Connected Devices"))
            for device in devices:
                self._render_inxi_device_card(device)
        
        if hubs:
            self._render_hubs_expander(hubs)
    
    def _render_lsusb_data(self, data: Dict) -> None:
        """Render USB data from lsusb."""
        devices = data.get("devices", [])
        
        regular_devices = []
        system_devices = []
        
        for device in devices:
            name = device.get("name", "").lower()
            is_system = any(kw in name for kw in self.SYSTEM_KEYWORDS)
            if is_system:
                system_devices.append(device)
            else:
                regular_devices.append(device)
        
        if regular_devices:
            self._add_section_title(_("Connected Devices"))
            for device in regular_devices:
                self._render_lsusb_device_card(device)
        
        if system_devices:
            self._render_system_usb_expander(system_devices)
    
    def _add_section_title(self, title: str) -> None:
        """Add a section title."""
        lbl = Gtk.Label(label=title)
        lbl.add_css_class("title-4")
        lbl.set_halign(Gtk.Align.START)
        lbl.set_margin_top(12)
        lbl.set_margin_bottom(8)
        self.container.append(lbl)
    
    def _render_inxi_device_card(self, device: Dict) -> None:
        """Render a USB device card using inxi data."""
        name = device.get("name", "")
        info = device.get("info", name)
        chip_id = device.get("chip_id", "")
        
        # Build Linux Hardware URL
        linux_hardware_url = ""
        if chip_id and ":" in chip_id:
            url_id = chip_id.replace(":", "-")
            linux_hardware_url = f"https://linux-hardware.org/?id=usb:{url_id}"
        
        card = ui.hero_card()
        
        # Title row
        title_row = ui.row(spacing=12)
        
        title_lbl = ui.label(info or name, css_classes=["hero-title"], halign=Gtk.Align.START, wrap=True, hexpand=True)
        title_lbl.set_xalign(0)
        title_row.append(title_lbl)
        
        # Info button
        if linux_hardware_url:
            info_btn = ui.flat_button(
                label_text=_("info"),
                tooltip=_("View device info on Linux Hardware Database"),
                on_click=lambda b, u=linux_hardware_url: self.open_url(u)
            )
            info_btn.set_valign(Gtk.Align.CENTER)
            title_row.append(info_btn)
        
        # Copy button
        copy_data = {
            "Name": info or name,
            "Chip ID": chip_id,
            "Bus ID": device.get("bus_id", ""),
            "Driver": device.get("driver", ""),
            "Type": device.get("type", ""),
            "Speed": device.get("speed", ""),
        }
        copy_text = self.format_copy_text(info or name, [(k, v) for k, v in copy_data.items() if v])
        title_row.append(ui.copy_button(on_click=lambda b: self.copy_to_clipboard(copy_text, info or name)))
        
        card.append(title_row)
        
        # Two-column layout
        left_items = [
            (_("Chip ID"), chip_id),
            (_("Bus ID"), device.get("bus_id", "")),
            (_("Class"), device.get("class", device.get("class_id", ""))),
            (_("Type"), device.get("type", "")),
        ]
        
        right_items = [
            (_("Driver"), device.get("driver", "")),
            (_("Speed"), device.get("speed", "")),
            (_("Ports"), device.get("ports", "")),
            (_("Serial"), device.get("serial", "")),
        ]
        
        # Filter empty
        left_items = [(l, v) for l, v in left_items if v]
        right_items = [(l, v) for l, v in right_items if v]
        
        if left_items or right_items:
            columns = self._render_columns(left_items, right_items)
            card.append(columns)
        
        self.container.append(card)
    
    def _render_lsusb_device_card(self, device: Dict, container: Gtk.Box = None) -> None:
        """Render a USB device card using lsusb data."""
        target = container or self.container
        
        name = device.get("name", "Unknown Device")
        chip_id = device.get("id", device.get("chip_id", ""))
        
        # Build URL
        linux_hardware_url = ""
        if chip_id and ":" in chip_id:
            url_id = chip_id.replace(":", "-")
            linux_hardware_url = f"https://linux-hardware.org/?id=usb:{url_id}"
        
        left_items = [
            (_("Device ID"), chip_id),
            (_("Bus"), device.get("bus", "")),
        ]
        
        right_items = [
            (_("Device"), device.get("device", "")),
        ]
        
        left_items = [(l, v) for l, v in left_items if v]
        right_items = [(l, v) for l, v in right_items if v]
        
        title_widgets = []
        if linux_hardware_url:
            title_widgets.append(ui.flat_button(
                label_text=_("info"),
                tooltip=_("View device info on Linux Hardware Database"),
                on_click=lambda b, u=linux_hardware_url: self.open_url(u)
            ))
        
        copy_text = self.format_copy_text(name, [(k, v) for k, v in [("ID", chip_id), ("Bus", device.get("bus", ""))]])
        title_widgets.append(ui.copy_button(on_click=lambda b: self.copy_to_clipboard(copy_text, name)))
        
        card = ui.two_column_card(name, left_items, right_items, title_widgets)
        target.append(card)
    
    def _render_hubs_expander(self, hubs: List[Dict]) -> None:
        """Render USB hubs in an expandable section."""
        expander = Gtk.Expander()
        expander.set_label(_("USB Hubs & Controllers ({})").format(len(hubs)))
        expander.add_css_class("card")
        expander.set_margin_top(16)
        
        box = ui.box(vertical=True, spacing=8)
        box.set_margin_top(8)
        
        for i, hub in enumerate(hubs):
            self._render_hub_row(box, hub)
            
            if i < len(hubs) - 1:
                box.append(ui.separator(margins=(4, 4)))
        
        expander.set_child(box)
        self.container.append(expander)
    
    def _render_hub_row(self, container: Gtk.Box, hub: Dict) -> None:
        """Render a single hub row."""
        row = ui.row(spacing=12)
        
        icon = ui.icon("network-server-symbolic", 20)
        icon.add_css_class("dim-label")
        row.append(icon)
        
        info_box = ui.box(vertical=True, spacing=2)
        info_box.set_hexpand(True)
        
        hub_name = hub.get("info", hub.get("name", _("Hub")))
        name_lbl = ui.heading(hub_name)
        name_lbl.set_halign(Gtk.Align.START)
        name_lbl.set_wrap(True)
        name_lbl.set_xalign(0)
        info_box.append(name_lbl)
        
        chip_id = hub.get("chip_id", "")
        class_id = hub.get("class_id", hub.get("class", ""))
        
        details = []
        if hub.get("ports"):
            details.append(_("{} ports").format(hub['ports']))
        if hub.get("speed"):
            details.append(hub["speed"])
        if hub.get("mode"):
            details.append(_("Mode {}").format(hub['mode']))
        if class_id:
            details.append(f"Class: {class_id}")
        if chip_id:
            details.append(f"ID: {chip_id}")
        
        if details:
            detail_lbl = ui.label(" • ".join(details), css_classes=["dim-label", "caption"], halign=Gtk.Align.START, wrap=True)
            detail_lbl.set_xalign(0)
            info_box.append(detail_lbl)
        
        row.append(info_box)
        
        # Copy button
        copy_data = {
            "Name": hub_name,
            "Ports": hub.get("ports", ""),
            "Speed": hub.get("speed", ""),
            "Mode": hub.get("mode", ""),
            "Class ID": class_id,
            "Chip ID": chip_id,
        }
        copy_text = self.format_copy_text(hub_name, [(k, v) for k, v in copy_data.items() if v])
        row.append(ui.copy_button(on_click=lambda b: self.copy_to_clipboard(copy_text, hub_name)))
        
        # Info button
        if chip_id and ":" in chip_id:
            url_id = chip_id.replace(":", "-")
            linux_hardware_url = f"https://linux-hardware.org/?id=usb:{url_id}"
            row.append(ui.flat_button(
                label_text=_("info"),
                tooltip=_("View device info on Linux Hardware Database"),
                on_click=lambda b, u=linux_hardware_url: self.open_url(u)
            ))
        
        container.append(row)
    
    def _render_system_usb_expander(self, devices: List[Dict]) -> None:
        """Render system USB controllers in an expandable section."""
        expander = Gtk.Expander()
        expander.set_label(_("System USB Controllers ({} devices)").format(len(devices)))
        expander.add_css_class("card")
        expander.set_margin_top(16)
        
        box = ui.box(vertical=True, spacing=8)
        box.set_margin_top(8)
        
        for device in devices:
            self._render_lsusb_device_card(device, box)
        
        expander.set_child(box)
        self.container.append(expander)
    
    def _render_columns(self, left: List, right: List) -> Gtk.Box:
        """Render two-column layout."""
        columns = ui.row(spacing=0)
        
        left_col = ui.box(vertical=True, spacing=8)
        left_col.set_hexpand(True)
        for label, value in left:
            left_col.append(ui.spec_item(label, value))
        columns.append(left_col)
        
        if right:
            sep = ui.separator(vertical=True)
            sep.set_margin_start(24)
            sep.set_margin_end(24)
            columns.append(sep)
            
            right_col = ui.box(vertical=True, spacing=8)
            right_col.set_hexpand(True)
            for label, value in right:
                right_col.append(ui.spec_item(label, value))
            columns.append(right_col)
        
        return columns
