"""
GPU Section View for Hardware Reporter.

Renders detailed GPU/Graphics information following GNOME HIG guidelines.
"""

from typing import Dict, Any, Optional

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from app.ui.views.base import HardwareSectionView
from app.utils.i18n import _


class GpuSectionView(HardwareSectionView):
    """
    View component for displaying GPU information.
    
    Displays:
    - Hero cards for each GPU device
    - Monitor information
    - OpenGL/Vulkan/EGL details (collapsible)
    - Display server info
    """
    
    CATEGORY_ID = "gpu"
    
    def __init__(self, open_url_callback=None, **kwargs) -> None:
        """Initialize the GPU section view.
        
        Args:
            open_url_callback: Optional callback for opening URLs.
        """
        super().__init__(**kwargs)
        self._open_url_callback = open_url_callback
    
    def render(self, data: Dict[str, Any]) -> None:
        """
        Render GPU information.
        
        Args:
            data: GPU hardware data dictionary.
        """
        self.clear()
        
        if not data:
            self.show_no_data(_("No GPU information available"))
            return
        
        devices = data.get("devices", [])
        opengl = data.get("opengl", {})
        
        # Get video memory from OpenGL if not available per device
        opengl_memory = opengl.get("memory", "") if opengl else ""
        
        if devices:
            self._render_gpu_devices(data, devices, opengl_memory)
        else:
            self.show_no_data(_("No GPU devices found"))
        
        # Monitors
        monitors = data.get("monitors", [])
        if monitors:
            self._render_monitors(monitors)
        
        # Advanced info (collapsible)
        self._render_advanced_info(data)
    
    def _render_gpu_devices(self, data: Dict[str, Any], devices: list, opengl_memory: str) -> None:
        """Render GPU device hero cards."""
        opengl = data.get("opengl", {})
        vulkan = data.get("vulkan", {})
        egl = data.get("egl", {})
        
        for device in devices:
            card = self._create_gpu_card(device, opengl_memory, opengl, vulkan, egl)
            self.append(card)
    
    def _create_gpu_card(
        self, 
        device: Dict[str, Any], 
        opengl_memory: str,
        opengl: Dict[str, Any],
        vulkan: Dict[str, Any],
        egl: Dict[str, Any]
    ) -> Gtk.Box:
        """Create a hero card for a GPU device."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("card")
        card.add_css_class("hero-card")
        
        # Build Linux Hardware URL from chip_id
        chip_id = device.get("chip_id", "")
        linux_hardware_url = ""
        if chip_id and ":" in chip_id:
            vendor_id, device_id = chip_id.split(":", 1)
            linux_hardware_url = f"https://linux-hardware.org/?id=pci:{vendor_id}-{device_id}"
        
        # Title row
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        name = device.get("name", _("Unknown GPU"))
        name_label = Gtk.Label(label=name)
        name_label.add_css_class("hero-title")
        name_label.set_halign(Gtk.Align.START)
        name_label.set_wrap(True)
        name_label.set_xalign(0)
        name_label.set_hexpand(True)
        title_row.append(name_label)
        
        # Copy button
        copy_btn = self._create_copy_button(device, name)
        title_row.append(copy_btn)
        
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
        
        card.append(title_row)
        
        # Video memory
        video_mem = device.get("video_memory", "") or device.get("vram", "") or opengl_memory
        
        # PCIe info
        pcie_info = ""
        if device.get("pcie_gen") and device.get("pcie_lanes"):
            pcie_info = f"Gen {device.get('pcie_gen')} x{device.get('pcie_lanes')}"
        
        # Build two columns
        left_items = [
            (_("Vendor"), device.get("vendor", "")),
            (_("Driver"), device.get("driver", "")),
            (_("Driver Version"), device.get("driver_version", "")),
            (_("Video Memory"), video_mem),
            (_("Architecture"), device.get("arch", "")),
        ]
        
        right_items = [
            (_("Bus ID"), device.get("bus_id", "")),
            (_("Chip ID"), device.get("chip_id", "")),
            (_("PCIe"), pcie_info),
            (_("Active Ports"), device.get("ports_active", "")),
            (_("Empty Ports"), device.get("ports_empty", "")),
        ]
        
        # Filter empty values
        left_items = [(l, v) for l, v in left_items if v and v != "Unknown"]
        right_items = [(l, v) for l, v in right_items if v and v != "Unknown"]
        
        # Two-column layout
        columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        # Left column
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_col.set_hexpand(True)
        for label, value in left_items:
            item = self._create_spec_item(label, value)
            left_col.append(item)
        
        if opengl.get("compat_version"):
            item = self._create_spec_item("OpenGL", opengl.get("compat_version"))
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
        
        if vulkan.get("version"):
            item = self._create_spec_item("Vulkan", vulkan.get("version"))
            right_col.append(item)
        if egl.get("version"):
            item = self._create_spec_item("EGL", str(egl.get("version")))
            right_col.append(item)
        
        columns_box.append(right_col)
        card.append(columns_box)
        
        return card
    
    def _render_monitors(self, monitors: list) -> None:
        """Render monitor information cards."""
        title = self.create_section_title(_("Monitors"))
        self.append(title)
        
        for monitor in monitors:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            card.add_css_class("card")
            card.add_css_class("device-card")
            
            mon_name = monitor.get("name", monitor.get("model", _("Monitor")))
            model = monitor.get("model", "")
            
            # Name row
            name_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            name_row.set_margin_bottom(8)
            
            name_label = Gtk.Label(label=mon_name)
            name_label.add_css_class("device-title")
            name_label.set_halign(Gtk.Align.START)
            name_label.set_hexpand(True)
            name_row.append(name_label)
            
            copy_btn = self._create_copy_button(monitor, mon_name)
            name_row.append(copy_btn)
            
            card.append(name_row)
            
            mon_items = [
                (_("Model"), model if model != mon_name else ""),
                (_("Resolution"), monitor.get("resolution", "")),
                (_("Refresh Rate"), f"{monitor.get('hz', '')} Hz" if monitor.get("hz") else ""),
                (_("Size"), monitor.get("size", "")),
                (_("Diagonal"), monitor.get("diagonal", "")),
                (_("Aspect Ratio"), monitor.get("ratio", "")),
                (_("DPI"), str(monitor.get("dpi", "")) if monitor.get("dpi") else ""),
                (_("Gamma"), str(monitor.get("gamma", "")) if monitor.get("gamma") else ""),
                (_("Built Year"), str(monitor.get("built", "")) if monitor.get("built") else ""),
                (_("Max Resolution"), monitor.get("modes_max", "")),
                (_("Min Resolution"), monitor.get("modes_min", "")),
                (_("Serial"), monitor.get("serial", "") if monitor.get("serial") and monitor.get("serial") != "0000000000000" else ""),
                (_("Driver"), monitor.get("driver", "")),
                (_("Mapped"), monitor.get("mapped", "")),
            ]
            
            for label, value in mon_items:
                if value and value not in ("", "Hz"):
                    row = self.create_info_row(label, str(value))
                    card.append(row)
            
            self.append(card)
    
    def _render_advanced_info(self, data: Dict[str, Any]) -> None:
        """Render advanced GPU information in collapsible section."""
        display_info = data.get("display_info", {})
        opengl = data.get("opengl", {})
        vulkan = data.get("vulkan", {})
        egl = data.get("egl", {})
        
        has_advanced = (
            (display_info and any(display_info.values())) or
            (opengl and any(opengl.values())) or
            (vulkan and vulkan.get("version")) or
            (egl and egl.get("version"))
        )
        
        if not has_advanced:
            return
        
        expander = Gtk.Expander(label=_("Advanced Information"))
        expander.add_css_class("card")
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(8)
        
        # Display Server
        if display_info and any(display_info.values()):
            section = self._create_detail_section(
                _("Display Server"),
                [
                    (_("Display"), display_info.get("display", "")),
                    (_("With"), display_info.get("with", "")),
                    (_("Compositor"), display_info.get("compositor", "")),
                    (_("Driver Loaded"), display_info.get("driver_loaded", "")),
                    (_("GPU"), display_info.get("gpu", "")),
                ]
            )
            content.append(section)
        
        # OpenGL
        if opengl and any(opengl.values()):
            section = self._create_detail_section(
                "OpenGL",
                [
                    (_("Version"), opengl.get("version", "")),
                    (_("Compatibility"), opengl.get("compat_version", "")),
                    (_("Vendor"), opengl.get("vendor", "")),
                    (_("GLX Version"), opengl.get("glx_version", "")),
                    (_("Direct Render"), opengl.get("direct_render", "")),
                    (_("Renderer"), opengl.get("renderer", "")),
                    (_("Video Memory"), opengl.get("memory", "")),
                ]
            )
            content.append(section)
        
        # Vulkan
        if vulkan and vulkan.get("version"):
            section = self._create_detail_section(
                "Vulkan",
                [
                    (_("Version"), vulkan.get("version", "")),
                    (_("Driver Version"), vulkan.get("driver_version", "")),
                    (_("Device"), vulkan.get("device_name", "")),
                    (_("Device Type"), vulkan.get("device_type", "")),
                ]
            )
            content.append(section)
        
        # EGL
        if egl and egl.get("version"):
            section = self._create_detail_section(
                "EGL",
                [
                    (_("Version"), str(egl.get("version", ""))),
                    (_("Vendor"), egl.get("vendor", "")),
                ]
            )
            content.append(section)
        
        expander.set_child(content)
        self.append(expander)
    
    def _create_detail_section(self, title: str, items: list) -> Gtk.Box:
        """Create a detail section with title and info rows."""
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("heading")
        title_label.set_halign(Gtk.Align.START)
        section.append(title_label)
        
        for label, value in items:
            if value:
                row = self.create_info_row(label, str(value))
                section.append(row)
        
        return section
    
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
        
        for key, value in device.items():
            if value and key not in ("raw",):
                lines.append(f"{key}: {value}")
        
        text = "\n".join(lines)
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
