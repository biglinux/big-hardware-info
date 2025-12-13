"""
Printers section renderer.
"""

from typing import Dict, List
import subprocess

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from big_hardware_info.ui import builders as ui
from big_hardware_info.ui.renderers.base import SectionRenderer
from big_hardware_info.utils.i18n import _


class PrintersRenderer(SectionRenderer):
    """Renderer for printers section."""
    
    def render(self) -> None:
        """Render printer information."""
        printer_data = self.data.get("printer", {})
        
        # Try to get printer info from lpstat if not in data
        if not printer_data or not printer_data.get("raw"):
            try:
                result = subprocess.run(
                    ["lpstat", "-p", "-d"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    printer_data = {"raw": result.stdout.strip()}
                else:
                    printer_data = {}
            except Exception:
                printer_data = {}
        
        raw = printer_data.get("raw", "")
        
        if not raw:
            self._render_empty_state()
            return
        
        # Parse and display printer info
        printers, default_printer = self._parse_printers(raw)
        
        if printers:
            for printer in printers:
                self._render_printer_card(printer, default_printer)
        
        # Show raw output
        if raw:
            self.window._add_terminal_block("Printer Details", raw)
    
    def _render_empty_state(self) -> None:
        """Render empty state when no printers found."""
        card = ui.box(vertical=True, spacing=16)
        card.add_css_class("card")
        card.set_valign(Gtk.Align.CENTER)
        card.set_halign(Gtk.Align.CENTER)
        card.set_margin_top(48)
        card.set_margin_bottom(48)
        
        icon = ui.icon("printer-symbolic", 64)
        icon.add_css_class("dim-label")
        card.append(icon)
        
        msg = ui.title("No printers configured", level=3)
        msg.add_css_class("dim-label")
        card.append(msg)
        
        hint = ui.label("Configure printers in System Settings", css_classes=["body", "dim-label"])
        card.append(hint)
        
        self.container.append(card)
    
    def _parse_printers(self, raw: str) -> tuple:
        """Parse printer info from lpstat output."""
        printers = []
        default_printer = ""
        
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("printer "):
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1]
                    status = "Unknown"
                    if "idle" in line.lower():
                        status = "Idle"
                    elif "printing" in line.lower():
                        status = "Printing"
                    elif "disabled" in line.lower():
                        status = "Disabled"
                    
                    enabled = "enabled" in line.lower()
                    printers.append({
                        "name": name,
                        "status": status,
                        "enabled": enabled,
                    })
            elif line.startswith("system default destination:"):
                default_printer = line.replace("system default destination:", "").strip()
        
        return printers, default_printer
    
    def _render_printer_card(self, printer: Dict, default_printer: str) -> None:
        """Render a single printer card."""
        card = ui.row(spacing=16)
        card.add_css_class("card")
        card.add_css_class("device-card")
        
        # Printer icon
        icon = ui.icon("printer-symbolic", 40)
        if printer.get("enabled"):
            icon.add_css_class("accent")
        else:
            icon.add_css_class("dim-label")
        icon.set_valign(Gtk.Align.START)
        card.append(icon)
        
        # Content
        content = ui.box(vertical=True, spacing=8)
        content.set_hexpand(True)
        
        # Header with name and badges
        header = ui.row(spacing=12)
        
        name_lbl = Gtk.Label(label=printer["name"])
        name_lbl.add_css_class("device-title")
        name_lbl.set_halign(Gtk.Align.START)
        name_lbl.set_wrap(True)
        name_lbl.set_xalign(0)
        header.append(name_lbl)
        
        # Default badge
        if printer["name"] == default_printer:
            header.append(ui.badge("DEFAULT", "success"))
        
        # Status badge
        status = printer["status"]
        status_style = None
        if status == "Idle":
            status_style = "success"
        elif status == "Printing":
            status_style = "warning"
        header.append(ui.badge(status, status_style))
        
        content.append(header)
        card.append(content)
        
        self.container.append(card)
