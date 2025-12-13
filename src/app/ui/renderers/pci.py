"""
PCI section renderer.
"""

from typing import Dict, List

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from app.ui import builders as ui
from app.ui.renderers.base import SectionRenderer
from app.utils.i18n import _


# PCI infrastructure keywords
PCI_INFRASTRUCTURE_KEYWORDS = [
    "bridge", "bus", "usb controller", "hub", "host bridge",
    "isa bridge", "pci bridge", "pcie", "smbus", "communication controller",
    "signal processing", "serial bus", "system peripheral", "pic", "dma",
    "rtc", "timer", "watchdog", "sd host", "sd/mmc",
    "sata controller", "ahci", "sata ahci"
]


class PciRenderer(SectionRenderer):
    """Renderer for PCI devices section."""
    
    def render(self) -> None:
        """Render PCI devices."""
        pci_lspci = self.data.get("pci", {})
        pci_inxi = self.data.get("pci_inxi", {})
        
        # Build lookup from inxi for enrichment
        inxi_lookup = {}
        for device in pci_inxi.get("devices", []):
            bus_id = device.get("bus_id", "")
            if bus_id:
                inxi_lookup[bus_id] = device
        
        devices = pci_lspci.get("devices", [])
        
        if not devices:
            self.show_no_data(_("No PCI devices detected"))
            return
        
        # Separate important from infrastructure
        important_devices = []
        infrastructure_devices = []
        
        for device in devices:
            name = device.get("name", "").lower()
            category = device.get("category", "").lower()
            
            is_infra = any(kw in name or kw in category for kw in PCI_INFRASTRUCTURE_KEYWORDS)
            
            if is_infra:
                infrastructure_devices.append(device)
            else:
                important_devices.append(device)
        
        # Hardware Devices Section
        if important_devices:
            self._add_section_title(_("Hardware Devices"))
            for device in important_devices:
                self._render_device_card(device, inxi_lookup)
        
        # Infrastructure Devices (collapsible)
        if infrastructure_devices:
            self._render_infrastructure_expander(infrastructure_devices, inxi_lookup)
    
    def _add_section_title(self, title: str) -> None:
        """Add a section title."""
        lbl = Gtk.Label(label=title)
        lbl.add_css_class("title-4")
        lbl.set_halign(Gtk.Align.START)
        lbl.set_margin_top(12)
        lbl.set_margin_bottom(8)
        self.container.append(lbl)
    
    def _render_device_card(self, device: Dict, inxi_lookup: Dict) -> None:
        """Render a PCI device card."""
        slot = device.get("slot", "")
        inxi_device = inxi_lookup.get(slot, {})
        
        name = device.get("name", "") or inxi_device.get("name", _("Unknown Device"))
        category = device.get("category", "")
        vendor_id = device.get("vendor_id", "")
        device_id = device.get("device_id", "")
        full_id = device.get("full_id", "") or inxi_device.get("chip_id", "")
        driver = inxi_device.get("driver", device.get("driver", ""))
        
        # Build Linux Hardware URL
        linux_hardware_url = ""
        if vendor_id and device_id:
            linux_hardware_url = f"https://linux-hardware.org/?id=pci:{vendor_id}-{device_id}"
        
        card = ui.hero_card()
        
        # Title row
        title_row = ui.row(spacing=12)
        
        title_lbl = ui.label(name, css_classes=["hero-title"], halign=Gtk.Align.START, wrap=True, hexpand=True)
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
        copy_text = self.format_copy_text(name, [
            ("Category", category),
            ("Bus ID", slot),
            ("Chip ID", full_id),
            ("Driver", driver),
        ])
        title_row.append(ui.copy_button(on_click=lambda b: self.copy_to_clipboard(copy_text, name)))
        
        card.append(title_row)
        
        # Two-column layout
        left_items = [
            (_("Category"), category),
            (_("Bus ID"), slot),
            (_("Chip ID"), full_id),
        ]
        
        right_items = [
            (_("Driver"), driver),
            (_("Rev"), device.get("revision", inxi_device.get("rev", ""))),
            (_("Kernel Module"), inxi_device.get("kernel", "")),
        ]
        
        left_items = [(l, v) for l, v in left_items if v]
        right_items = [(l, v) for l, v in right_items if v]
        
        if left_items or right_items:
            columns = self._render_columns(left_items, right_items)
            card.append(columns)
        
        self.container.append(card)
    
    def _render_infrastructure_expander(self, devices: List[Dict], inxi_lookup: Dict) -> None:
        """Render infrastructure devices in an expandable section."""
        expander = Gtk.Expander()
        expander.set_label(_("System Controllers & Bridges ({} devices)").format(len(devices)))
        expander.add_css_class("card")
        expander.set_margin_top(16)
        
        box = ui.box(vertical=True, spacing=8)
        box.set_margin_top(8)
        
        for i, device in enumerate(devices):
            self._render_infrastructure_row(box, device, inxi_lookup)
            
            if i < len(devices) - 1:
                box.append(ui.separator(margins=(4, 4)))
        
        expander.set_child(box)
        self.container.append(expander)
    
    def _render_infrastructure_row(self, container: Gtk.Box, device: Dict, inxi_lookup: Dict) -> None:
        """Render a single infrastructure device row."""
        slot = device.get("slot", "")
        inxi_device = inxi_lookup.get(slot, {})
        
        name = device.get("name", "") or inxi_device.get("name", _("Unknown Device"))
        category = device.get("category", "")
        class_id = device.get("class_id", "")
        vendor_id = device.get("vendor_id", "")
        device_id = device.get("device_id", "")
        full_id = device.get("full_id", "") or inxi_device.get("chip_id", "")
        
        # Build URL
        linux_hardware_url = ""
        if vendor_id and device_id:
            linux_hardware_url = f"https://linux-hardware.org/?id=pci:{vendor_id}-{device_id}"
        
        row = ui.row(spacing=12)
        
        icon = ui.icon("drive-multidisk-symbolic", 20)
        icon.add_css_class("dim-label")
        row.append(icon)
        
        info_box = ui.box(vertical=True, spacing=2)
        info_box.set_hexpand(True)
        
        name_lbl = ui.heading(name)
        name_lbl.set_halign(Gtk.Align.START)
        name_lbl.set_wrap(True)
        name_lbl.set_xalign(0)
        info_box.append(name_lbl)
        
        details = []
        if category:
            details.append(category)
        if slot:
            details.append(f"Bus: {slot}")
        if class_id:
            details.append(f"Class: {class_id}")
        if full_id:
            details.append(f"ID: {full_id}")
        
        if details:
            detail_lbl = ui.label(" • ".join(details), css_classes=["dim-label", "caption"], halign=Gtk.Align.START, wrap=True)
            detail_lbl.set_xalign(0)
            info_box.append(detail_lbl)
        
        row.append(info_box)
        
        # Copy button
        copy_text = self.format_copy_text(name, [
            ("Category", category),
            ("Bus ID", slot),
            ("Class ID", class_id),
            ("Chip ID", full_id),
        ])
        row.append(ui.copy_button(on_click=lambda b: self.copy_to_clipboard(copy_text, name)))
        
        # Info button
        if linux_hardware_url:
            row.append(ui.flat_button(
                label_text=_("info"),
                tooltip=_("View device info on Linux Hardware Database"),
                on_click=lambda b, u=linux_hardware_url: self.open_url(u)
            ))
        
        container.append(row)
    
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
