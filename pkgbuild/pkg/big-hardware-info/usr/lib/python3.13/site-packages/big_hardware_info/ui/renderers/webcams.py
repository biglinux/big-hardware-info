"""
Webcams section renderer.
"""

from typing import Dict, List, Tuple

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from big_hardware_info.ui import builders as ui
from big_hardware_info.ui.renderers.base import SectionRenderer
from big_hardware_info.utils.i18n import _


class WebcamsRenderer(SectionRenderer):
    """Renderer for webcams section."""
    
    def render(self) -> None:
        """Render webcam devices."""
        # Get v4l2-ctl data from dedicated collector
        webcam_data = self.data.get("webcam", {})
        v4l2_webcams = webcam_data.get("devices", [])
        
        # Get inxi webcam data (has chip_id)
        gpu_data = self.data.get("gpu", {})
        inxi_webcams = gpu_data.get("webcams", [])
        
        # Combine data: use v4l2 as base, enrich with inxi
        webcams = self._merge_webcam_data(v4l2_webcams, inxi_webcams)
        
        if not webcams:
            self.show_no_data("No webcams detected")
            return
        
        for webcam in webcams:
            self._render_webcam_card(webcam)
    
    def _merge_webcam_data(self, v4l2: List[Dict], inxi: List[Dict]) -> List[Dict]:
        """Merge v4l2-ctl and inxi webcam data."""
        if v4l2:
            webcams = []
            for v4l2_cam in v4l2:
                combined = dict(v4l2_cam)
                # Find matching inxi webcam by name
                for inxi_cam in inxi:
                    inxi_name = inxi_cam.get("name", "").lower()
                    v4l2_name = v4l2_cam.get("name", "").lower()
                    if inxi_name and v4l2_name and (inxi_name in v4l2_name or v4l2_name in inxi_name):
                        combined["chip_id"] = inxi_cam.get("chip_id", "")
                        combined["bus_id"] = inxi_cam.get("bus_id", "")
                        combined["type"] = inxi_cam.get("type", "")
                        combined["speed"] = inxi_cam.get("speed", "")
                        break
                webcams.append(combined)
            return webcams
        return inxi  # Fallback to inxi only
    
    def _render_webcam_card(self, webcam: Dict) -> None:
        """Render a single webcam card."""
        card = ui.hero_card()
        
        # Build Linux Hardware URL
        chip_id = webcam.get("chip_id", "")
        linux_hardware_url = ""
        if chip_id and ":" in chip_id:
            url_id = chip_id.replace(":", "-")
            linux_hardware_url = f"https://linux-hardware.org/?id=usb:{url_id}"
        
        # Title row
        title_row = ui.row(spacing=12)
        
        cam_name = webcam.get("name", "Unknown Webcam")
        name_lbl = ui.label(cam_name, css_classes=["hero-title"], halign=Gtk.Align.START, hexpand=True)
        title_row.append(name_lbl)
        
        # Info button
        if linux_hardware_url:
            info_btn = ui.flat_button(
                label_text=_("info"),
                tooltip=_("View device info on Linux Hardware Database\nSee driver compatibility and troubleshooting tips"),
                on_click=lambda b, u=linux_hardware_url: self.open_url(u)
            )
            info_btn.set_valign(Gtk.Align.CENTER)
            title_row.append(info_btn)
        
        # Copy button
        copy_text = self.format_copy_text(cam_name, [
            (_("Resolution"), webcam.get("resolution", "")),
            (_("Format"), webcam.get("pixel_format", "")),
            (_("Chip ID"), chip_id),
            (_("Driver"), webcam.get("driver", "")),
            (_("Colorspace"), webcam.get("colorspace", "")),
            (_("Max FPS"), webcam.get("max_fps", "")),
            (_("Device"), webcam.get("device_path", "")),
        ])
        title_row.append(ui.copy_button(on_click=lambda b: self.copy_to_clipboard(copy_text, cam_name)))
        
        card.append(title_row)
        
        # Two-column layout
        left_items = self._filter_items([
            (_("Resolution"), webcam.get("resolution", "")),
            (_("Format"), webcam.get("pixel_format", "")),
            (_("Chip ID"), webcam.get("chip_id", "")),
            (_("Driver"), webcam.get("driver", "")),
        ])
        
        right_items = self._filter_items([
            (_("Colorspace"), webcam.get("colorspace", "")),
            (_("Max FPS"), webcam.get("max_fps", "")),
            (_("Driver Version"), webcam.get("driver_version", "")),
            (_("Device"), webcam.get("device_path", "")),
        ])
        
        if left_items or right_items:
            columns = ui.row(spacing=0)
            
            # Left column
            left_col = ui.box(vertical=True, spacing=8)
            left_col.set_hexpand(True)
            for label, value in left_items:
                left_col.append(ui.spec_item(label, value))
            columns.append(left_col)
            
            if right_items:
                sep = ui.separator(vertical=True)
                sep.set_margin_start(24)
                sep.set_margin_end(24)
                columns.append(sep)
                
                right_col = ui.box(vertical=True, spacing=8)
                right_col.set_hexpand(True)
                for label, value in right_items:
                    right_col.append(ui.spec_item(label, value))
                columns.append(right_col)
            
            card.append(columns)
        
        self.container.append(card)
    
    def _filter_items(self, items: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Filter out empty items."""
        return [(l, v) for l, v in items if v]
