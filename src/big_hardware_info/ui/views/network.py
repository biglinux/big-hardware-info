"""
Network Section View for Hardware Reporter.

Renders detailed network device information following GNOME HIG guidelines.
"""

from typing import Dict, Any, Optional, Callable

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from big_hardware_info.ui.views.base import HardwareSectionView
from big_hardware_info.utils.i18n import _


class NetworkSectionView(HardwareSectionView):
    """
    View component for displaying network device information.
    
    Displays:
    - Network device cards with two-column layout
    - IP address information with copy buttons
    - Virtual networks in collapsible section
    - Status badges for connection state
    """
    
    CATEGORY_ID = "network"
    
    def __init__(
        self, 
        open_url_callback: Optional[Callable[[str], None]] = None,
        copy_text_callback: Optional[Callable[[str, str], None]] = None,
        **kwargs
    ) -> None:
        """Initialize the network section view.
        
        Args:
            open_url_callback: Callback for opening URLs.
            copy_text_callback: Callback for copying text to clipboard.
        """
        super().__init__(**kwargs)
        self._open_url_callback = open_url_callback
        self._copy_text_callback = copy_text_callback
    
    def render(self, data: Dict[str, Any]) -> None:
        """
        Render network information.
        
        Args:
            data: Network hardware data dictionary.
        """
        self.clear()
        
        if not data:
            self.show_no_data(_("No network information available"))
            return
        
        devices = data.get("devices", [])
        virtual_devices = data.get("virtual_devices", [])
        
        if not devices:
            self.show_no_data(_("No network devices found"))
        else:
            for device in devices:
                card = self._create_network_card(device)
                self.append(card)
        
        # Virtual networks (collapsible)
        if virtual_devices:
            self._render_virtual_networks(virtual_devices)
    
    def _create_network_card(self, device: Dict[str, Any]) -> Gtk.Box:
        """Create a card for a network device."""
        name = device.get("name", _("Unknown Network Device"))
        
        # Build Linux Hardware URL from chip_id
        chip_id = device.get("chip_id", "")
        linux_hardware_url = ""
        if chip_id and ":" in chip_id:
            vendor_id, device_id = chip_id.split(":", 1)
            linux_hardware_url = f"https://linux-hardware.org/?id=pci:{vendor_id}-{device_id}"
        
        # Build connection info string (USB or PCIe)
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
            elif device.get("lanes"):
                connection_info = f"x{device.get('lanes')}"
        
        state = device.get("state", "").lower()
        
        # Build columns
        left_items = [
            (_("Vendor"), device.get("vendor", "")),
            (_("Driver"), device.get("driver", "")),
            (_("Interface"), device.get("IF", "")),
            (_("Speed"), device.get("speed", "")),
        ]
        
        right_items = [
            (_("Bus ID"), device.get("bus_id", "")),
            (_("Chip ID"), chip_id),
            (_("MAC"), device.get("mac", "")),
            (connection_label, connection_info),
        ]
        
        # Filter empty values
        left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "Unknown", "?", "")]
        right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "Unknown", "?", "")]
        
        # Create card
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("card")
        
        # Title row with status badge
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        title_label = Gtk.Label(label=name)
        title_label.add_css_class("title-4")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_wrap(True)
        title_label.set_xalign(0)
        title_label.set_hexpand(True)
        title_row.append(title_label)
        
        # Status badge
        if state:
            state_badge = Gtk.Label(label=state.upper())
            state_badge.add_css_class("device-badge")
            if "up" in state:
                state_badge.add_css_class("success-badge")
            state_badge.set_valign(Gtk.Align.CENTER)
            title_row.append(state_badge)
        
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
        
        # IP addresses
        ipv4 = device.get("ip", "")
        ipv6 = device.get("ipv6", "")
        
        if ipv4 or ipv6:
            ip_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            ip_box.set_margin_top(8)
            
            if ipv4:
                ip4_row = self._create_ip_row(_("IPv4"), ipv4)
                ip_box.append(ip4_row)
            
            if ipv6:
                ip6_row = self._create_ip_row(_("IPv6"), ipv6)
                ip_box.append(ip6_row)
            
            card.append(ip_box)
        
        return card
    
    def _create_ip_row(self, label: str, ip: str) -> Gtk.Box:
        """Create an IP address row with copy button."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        item = self._create_spec_item(label, ip)
        item.set_hexpand(True)
        row.append(item)
        
        copy_btn = Gtk.Button()
        copy_btn.set_icon_name("edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.set_tooltip_text(_("Copy {label}").format(label=label))
        copy_btn.set_valign(Gtk.Align.CENTER)
        
        if self._copy_text_callback:
            copy_btn.connect("clicked", lambda b, i=ip, l=label: self._copy_text_callback(i, l))
        else:
            copy_btn.connect("clicked", lambda b, i=ip: self._copy_to_clipboard(i))
        
        row.append(copy_btn)
        return row
    
    def _render_virtual_networks(self, virtual_devices: list) -> None:
        """Render virtual networks in collapsible section with full details."""
        expander = Gtk.Expander(
            label=_("Virtual Networks ({count})").format(count=len(virtual_devices))
        )
        expander.add_css_class("card")
        expander.set_margin_top(12)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        content.set_margin_start(8)
        content.set_margin_end(8)
        
        for vnet in virtual_devices:
            # Create a card-like box for each virtual network
            vnet_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            vnet_card.add_css_class("card")
            vnet_card.set_margin_top(4)
            vnet_card.set_margin_bottom(4)
            
            # Header row with name and status
            header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            header_row.set_margin_start(12)
            header_row.set_margin_end(12)
            header_row.set_margin_top(12)
            
            # Icon with status
            vnet_icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
            vnet_icon.set_pixel_size(24)
            state = vnet.get("state", "").lower()
            if "up" in state:
                vnet_icon.add_css_class("success")
            header_row.append(vnet_icon)
            
            # Name
            vnet_name = vnet.get("IF", vnet.get("name", _("Virtual")))
            name_label = Gtk.Label(label=vnet_name)
            name_label.add_css_class("heading")
            name_label.set_halign(Gtk.Align.START)
            name_label.set_hexpand(True)
            header_row.append(name_label)
            
            # State badge
            state_text = vnet.get("state", "")
            if state_text:
                state_badge = Gtk.Label(label=state_text)
                state_badge.add_css_class("device-badge")
                if "up" in state_text.lower():
                    state_badge.add_css_class("success")
                elif "down" in state_text.lower():
                    state_badge.add_css_class("dim-label")
                header_row.append(state_badge)
            
            vnet_card.append(header_row)
            
            # Details in two columns
            details_grid = Gtk.Grid()
            details_grid.set_column_spacing(24)
            details_grid.set_row_spacing(6)
            details_grid.set_margin_start(12)
            details_grid.set_margin_end(12)
            details_grid.set_margin_bottom(12)
            
            row_idx = 0
            
            # Type
            vnet_type = vnet.get("type", "")
            if vnet_type:
                type_label = Gtk.Label(label=_("Type:"))
                type_label.add_css_class("dim-label")
                type_label.set_halign(Gtk.Align.END)
                type_value = Gtk.Label(label=vnet_type)
                type_value.set_halign(Gtk.Align.START)
                type_value.set_selectable(True)
                details_grid.attach(type_label, 0, row_idx, 1, 1)
                details_grid.attach(type_value, 1, row_idx, 1, 1)
                row_idx += 1
            
            # Driver
            driver = vnet.get("driver", "")
            if driver:
                driver_label = Gtk.Label(label=_("Driver:"))
                driver_label.add_css_class("dim-label")
                driver_label.set_halign(Gtk.Align.END)
                driver_value = Gtk.Label(label=driver)
                driver_value.set_halign(Gtk.Align.START)
                driver_value.set_selectable(True)
                details_grid.attach(driver_label, 0, row_idx, 1, 1)
                details_grid.attach(driver_value, 1, row_idx, 1, 1)
                row_idx += 1
            
            # MAC Address
            mac = vnet.get("mac", "")
            if mac:
                mac_label = Gtk.Label(label=_("MAC:"))
                mac_label.add_css_class("dim-label")
                mac_label.set_halign(Gtk.Align.END)
                mac_value = Gtk.Label(label=mac)
                mac_value.set_halign(Gtk.Align.START)
                mac_value.set_selectable(True)
                mac_value.add_css_class("monospace")
                details_grid.attach(mac_label, 2, 0, 1, 1)
                details_grid.attach(mac_value, 3, 0, 1, 1)
            
            # IP Address (IPv4)
            ip = vnet.get("ip", "")
            if ip:
                ip_label = Gtk.Label(label=_("IPv4:"))
                ip_label.add_css_class("dim-label")
                ip_label.set_halign(Gtk.Align.END)
                ip_value = Gtk.Label(label=ip)
                ip_value.set_halign(Gtk.Align.START)
                ip_value.set_selectable(True)
                ip_value.add_css_class("monospace")
                details_grid.attach(ip_label, 2, 1, 1, 1)
                details_grid.attach(ip_value, 3, 1, 1, 1)
            
            # IPv6 Address
            ipv6 = vnet.get("ipv6", "")
            if ipv6:
                ipv6_label = Gtk.Label(label=_("IPv6:"))
                ipv6_label.add_css_class("dim-label")
                ipv6_label.set_halign(Gtk.Align.END)
                ipv6_value = Gtk.Label(label=ipv6)
                ipv6_value.set_halign(Gtk.Align.START)
                ipv6_value.set_selectable(True)
                ipv6_value.set_wrap(True)
                ipv6_value.set_max_width_chars(35)
                ipv6_value.add_css_class("monospace")
                details_grid.attach(ipv6_label, 2, 2, 1, 1)
                details_grid.attach(ipv6_value, 3, 2, 1, 1)
            
            # Speed (if available)
            speed = vnet.get("speed", "")
            if speed:
                speed_label = Gtk.Label(label=_("Speed:"))
                speed_label.add_css_class("dim-label")
                speed_label.set_halign(Gtk.Align.END)
                speed_value = Gtk.Label(label=speed)
                speed_value.set_halign(Gtk.Align.START)
                speed_value.set_selectable(True)
                details_grid.attach(speed_label, 0, row_idx, 1, 1)
                details_grid.attach(speed_value, 1, row_idx, 1, 1)
                row_idx += 1
            
            # Bus ID (if available)
            bus_id = vnet.get("bus_id", vnet.get("bus-id", ""))
            if bus_id:
                bus_label = Gtk.Label(label=_("Bus ID:"))
                bus_label.add_css_class("dim-label")
                bus_label.set_halign(Gtk.Align.END)
                bus_value = Gtk.Label(label=bus_id)
                bus_value.set_halign(Gtk.Align.START)
                bus_value.set_selectable(True)
                bus_value.add_css_class("monospace")
                details_grid.attach(bus_label, 0, row_idx, 1, 1)
                details_grid.attach(bus_value, 1, row_idx, 1, 1)
            
            if row_idx > 0 or mac or ip or ipv6:
                vnet_card.append(details_grid)
            
            content.append(vnet_card)
        
        expander.set_child(content)
        self.append(expander)
    
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
        
        for key in ["vendor", "driver", "IF", "speed", "bus_id", "chip_id", "mac", "ip", "ipv6"]:
            value = device.get(key, "")
            if value:
                lines.append(f"{key}: {value}")
        
        text = "\n".join(lines)
        self._copy_to_clipboard(text)
    
    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard."""
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
