"""
Sensors section renderer.
"""

from typing import Dict, List

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from big_hardware_info.ui import builders as ui
from big_hardware_info.ui.renderers.base import SectionRenderer
from big_hardware_info.utils.i18n import _


class SensorsRenderer(SectionRenderer):
    """Renderer for temperature and fan sensor section."""
    
    def render(self) -> None:
        """Render sensor information."""
        sensors_data = self.data.get("sensors", {})
        
        if not sensors_data or (not sensors_data.get("temps") and not sensors_data.get("sensors_cmd") and not sensors_data.get("raw")):
            self.show_no_data(_("No sensor data available"))
            return
        
        # Temperature sensors from inxi
        temps = sensors_data.get("temps", [])
        if temps:
            self._add_section_title(_("System Temperatures"))
            self._render_temps_flow(temps)
        
        # Fan speeds
        fans = sensors_data.get("fans", [])
        if fans:
            self._add_section_title(_("Fan Speeds"))
            self._render_fans_flow(fans)
        
        # Sensors command output (detailed)
        sensors_cmd = sensors_data.get("sensors_cmd", "")
        if sensors_cmd:
            self._add_section_title(_("Detailed Sensor Data (sensors)"))
            self._render_sensors_cmd(sensors_cmd)
        
        # Raw output
        if sensors_data.get("raw"):
            self.add_raw_expander(_("Full Output"), sensors_data["raw"])
    
    def _add_section_title(self, title: str) -> None:
        """Add a section title."""
        lbl = Gtk.Label(label=title)
        lbl.add_css_class("title-4")
        lbl.set_halign(Gtk.Align.START)
        lbl.set_margin_top(12)
        lbl.set_margin_bottom(8)
        self.container.append(lbl)
    
    def _render_temps_flow(self, temps: List[Dict]) -> None:
        """Render temperature sensors in a flow box."""
        flow = ui.flow_box()
        
        for temp in temps:
            card = self._create_temp_card(temp)
            flow.append(card)
        
        self.container.append(flow)
    
    def _create_temp_card(self, temp: Dict) -> Gtk.Box:
        """Create a temperature sensor card."""
        card = ui.box(vertical=True, spacing=8)
        card.add_css_class("card")
        card.add_css_class("stat-card")
        
        # Icon with temperature-based color
        icon = ui.icon("sensors-temperature-symbolic", 24)
        
        temp_value = temp.get("temp", temp.get("value", "N/A"))
        temp_str = ""
        
        if isinstance(temp_value, (int, float)):
            if temp_value > 80:
                icon.add_css_class("error")
            elif temp_value > 60:
                icon.add_css_class("warning")
            else:
                icon.add_css_class("accent")
            temp_str = f"{temp_value}°C"
        else:
            icon.add_css_class("accent")
            temp_str = str(temp_value)
        
        card.append(icon)
        
        # Value
        value_lbl = Gtk.Label(label=temp_str)
        value_lbl.add_css_class("stat-value")
        card.append(value_lbl)
        
        # Name
        name = temp.get("name", temp.get("device", "Sensor"))
        name_lbl = Gtk.Label(label=name)
        name_lbl.add_css_class("stat-label")
        name_lbl.set_wrap(True)
        card.append(name_lbl)
        
        return card
    
    def _render_fans_flow(self, fans: List[Dict]) -> None:
        """Render fan speeds in a flow box."""
        flow = ui.flow_box()
        
        for fan in fans:
            card = self._create_fan_card(fan)
            flow.append(card)
        
        self.container.append(flow)
    
    def _create_fan_card(self, fan: Dict) -> Gtk.Box:
        """Create a fan speed card."""
        card = ui.box(vertical=True, spacing=8)
        card.add_css_class("card")
        card.add_css_class("stat-card")
        
        icon = ui.icon("weather-windy-symbolic", 24, css_class="accent")
        card.append(icon)
        
        # Speed
        speed = fan.get("speed", fan.get("value", "N/A"))
        speed_str = f"{speed} RPM" if isinstance(speed, (int, float)) else str(speed)
        speed_lbl = Gtk.Label(label=speed_str)
        speed_lbl.add_css_class("stat-value")
        card.append(speed_lbl)
        
        # Name
        name = fan.get("name", "Fan")
        name_lbl = Gtk.Label(label=name)
        name_lbl.add_css_class("stat-label")
        card.append(name_lbl)
        
        return card
    
    def _render_sensors_cmd(self, sensors_cmd: str) -> None:
        """Render detailed sensors command output."""
        card = ui.card(spacing=16)
        
        current_adapter = ""
        current_box = None
        
        for line in sensors_cmd.split("\n"):
            line = line.rstrip()
            
            # New adapter (e.g., "coretemp-isa-0000")
            if line and not line.startswith(" ") and ":" not in line:
                if current_box:
                    card.append(current_box)
                
                current_adapter = line
                current_box = ui.box(vertical=True, spacing=8)
                
                adapter_lbl = Gtk.Label(label=current_adapter)
                adapter_lbl.add_css_class("device-title")
                adapter_lbl.set_halign(Gtk.Align.START)
                current_box.append(adapter_lbl)
            
            # Adapter type line
            elif line.startswith("Adapter:") and current_box:
                adapter_type = line.replace("Adapter:", "").strip()
                type_lbl = Gtk.Label(label=adapter_type)
                type_lbl.add_css_class("device-subtitle")
                type_lbl.set_halign(Gtk.Align.START)
                current_box.append(type_lbl)
            
            # Sensor reading line
            elif ":" in line and current_box:
                parts = line.split(":")
                if len(parts) >= 2:
                    sensor_name = parts[0].strip()
                    sensor_value = ":".join(parts[1:]).strip()
                    
                    if sensor_name.lower() == "adapter":
                        continue
                    
                    row = ui.row(spacing=12)
                    
                    name_lbl = Gtk.Label(label=sensor_name)
                    name_lbl.add_css_class("info-label")
                    name_lbl.set_halign(Gtk.Align.START)
                    name_lbl.set_width_chars(20)
                    name_lbl.set_xalign(0)
                    row.append(name_lbl)
                    
                    value_lbl = Gtk.Label(label=sensor_value)
                    value_lbl.add_css_class("info-value")
                    value_lbl.set_halign(Gtk.Align.START)
                    value_lbl.set_selectable(True)
                    
                    # Color code temperatures
                    if "°C" in sensor_value:
                        try:
                            temp_match = sensor_value.split()[0].replace("+", "").replace("°C", "")
                            temp_val = float(temp_match)
                            if temp_val > 80:
                                value_lbl.add_css_class("error")
                            elif temp_val > 60:
                                value_lbl.add_css_class("warning")
                            else:
                                value_lbl.add_css_class("success")
                        except (ValueError, IndexError):
                            pass
                    
                    row.append(value_lbl)
                    current_box.append(row)
        
        # Add last section
        if current_box:
            card.append(current_box)
        
        self.container.append(card)
