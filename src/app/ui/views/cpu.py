"""
CPU Section View for Hardware Reporter.

Renders detailed CPU/Processor information following GNOME HIG guidelines.
"""

from typing import Dict, Any

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from app.ui.views.base import HardwareSectionView


class CpuSectionView(HardwareSectionView):
    """
    View component for displaying CPU information.
    
    Displays:
    - Hero card with model name and key specs
    - Cache information (L1/L2/L3)
    - Technical details (family, stepping, etc.)
    - Thread/core speeds
    - CPU flags
    - Vulnerabilities (collapsible)
    - Raw output (collapsible)
    """
    
    CATEGORY_ID = "cpu"
    
    def render(self, data: Dict[str, Any]) -> None:
        """
        Render CPU information.
        
        Args:
            data: CPU hardware data dictionary.
        """
        self.clear()
        
        if not data:
            self.show_no_data("No CPU information available")
            return
        
        # Render sections
        self._render_hero_card(data)
        self._render_cache_section(data)
        self._render_advanced_info(data)
        self._render_raw_output(data)
    
    def _render_hero_card(self, data: Dict[str, Any]) -> None:
        """Render the main CPU info hero card with modern two-column layout."""
        hero_card = self.create_hero_card()
        
        # Model name row with copy button
        model_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        model = data.get("model", "Unknown Processor")
        model_label = Gtk.Label(label=model)
        model_label.add_css_class("hero-title")
        model_label.set_halign(Gtk.Align.START)
        model_label.set_wrap(True)
        model_label.set_hexpand(True)
        model_row.append(model_label)
        
        # Copy button for CPU info
        copy_btn = Gtk.Button()
        copy_btn.set_icon_name("edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.set_tooltip_text("Copy CPU info")
        copy_btn.set_valign(Gtk.Align.CENTER)
        copy_btn.connect("clicked", lambda b, d=data: self._copy_cpu_data(d))
        model_row.append(copy_btn)
        
        hero_card.append(model_row)
        
        # Build info items
        cores = data.get("cores", 0)
        threads = data.get("threads", 0)
        cores_threads = f"{cores} Cores / {threads} Threads" if cores and threads else str(cores) if cores else "?"
        
        # Build speed display
        speed_display = self._build_speed_display(data)
        
        # Split into two balanced columns
        left_items = [
            ("Cores", cores_threads),
            ("Architecture", data.get("arch", "")),
            ("Bits", f"{data.get('bits', '')} bit" if data.get("bits") else ""),
            ("Speed", speed_display),
        ]
        
        right_items = [
            ("Generation", data.get("gen", "")),
            ("Process", data.get("process", "")),
            ("Built", data.get("built", "")),
            ("Scaling", f"{data.get('scaling_driver', '')} / {data.get('scaling_governor', '')}" 
                       if data.get("scaling_driver") else ""),
        ]
        
        # Filter out empty values
        left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "? MHz", "Unknown", "?", " MHz", " bit", " / ")]
        right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "? MHz", "Unknown", "?", " MHz", " bit", " / ")]
        
        # Modern two-column layout with separator
        columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        # Left column
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_col.set_hexpand(True)
        for label, value in left_items:
            item = self._create_spec_item(label, value)
            left_col.append(item)
        columns_box.append(left_col)
        
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
        
        hero_card.append(columns_box)
        self.append(hero_card)
    
    def _create_spec_item(self, label: str, value: str) -> Gtk.Box:
        """Create a modern spec item with label above value."""
        item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        # Small dim label on top
        label_w = Gtk.Label(label=label)
        label_w.add_css_class("dim-label")
        label_w.add_css_class("caption")
        label_w.set_halign(Gtk.Align.START)
        item.append(label_w)
        
        # Bold value below
        value_w = Gtk.Label(label=str(value))
        value_w.add_css_class("heading")
        value_w.set_halign(Gtk.Align.START)
        value_w.set_selectable(True)
        item.append(value_w)
        
        return item
    
    def _build_speed_display(self, data: Dict[str, Any]) -> str:
        """Build the CPU speed display string."""
        speed_max = data.get("speed_max", "")
        speed_min = data.get("speed_min", "")
        speed_base = data.get("speed_base", "")
        speed_boost = data.get("speed_boost", "")
        
        if speed_base and speed_boost:
            return f"{speed_base}/{speed_boost} MHz (base/boost)"
        elif speed_min and speed_max:
            return f"{speed_min}-{speed_max} MHz"
        elif speed_max:
            return f"Max: {speed_max} MHz"
        
        return ""
    
    def _render_cache_section(self, data: Dict[str, Any]) -> None:
        """Render CPU cache information."""
        cache_l1 = data.get("cache_l1", "")
        cache_l2 = data.get("cache_l2", "")
        cache_l3 = data.get("cache_l3", "")
        
        if not (cache_l1 or cache_l2 or cache_l3):
            return
        
        # Section title
        title = self.create_section_title("Cache")
        self.append(title)
        
        # Cache cards in flow box
        cache_flow = self.create_flow_box(
            max_per_line=3,
            min_per_line=3
        )
        
        for cache_name, cache_val in [("L1", cache_l1), ("L2", cache_l2), ("L3", cache_l3)]:
            if cache_val:
                cache_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                cache_card.add_css_class("card")
                cache_card.add_css_class("stat-card")
                
                name_label = Gtk.Label(label=cache_name)
                name_label.add_css_class("stat-label")
                cache_card.append(name_label)
                
                value_label = Gtk.Label(label=cache_val)
                value_label.add_css_class("heading")  # Normal bold font instead of large stat-value
                cache_card.append(value_label)
                
                cache_flow.append(cache_card)
        
        self.append(cache_flow)
    
    def _render_advanced_info(self, data: Dict[str, Any]) -> None:
        """Render advanced CPU information in a single collapsible section."""
        core_speeds = data.get("core_speeds", {})
        flags = data.get("flags", "")
        vulnerabilities = data.get("vulnerabilities", [])
        
        # Build technical details items
        tech_items = [
            ("Type", data.get("type", "")),
            ("Family", data.get("family", "")),
            ("Model ID", data.get("model_id", "")),
            ("Stepping", data.get("stepping", "")),
            ("Microcode", data.get("microcode", "")),
            ("Bogomips", str(data.get("bogomips", "")) if data.get("bogomips") else ""),
        ]
        tech_items = [(k, v) for k, v in tech_items if v]
        
        # Only render if there's any content
        if not core_speeds and not flags and not vulnerabilities and not tech_items:
            return
        
        # Single collapsible expander for all advanced info
        expander = Gtk.Expander(label="Advanced Information")
        expander.add_css_class("card")
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_top(8)
        
        # Technical Details Section
        if tech_items:
            tech_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            
            tech_title = Gtk.Label(label="Technical Details")
            tech_title.add_css_class("heading")
            tech_title.set_halign(Gtk.Align.START)
            tech_section.append(tech_title)
            
            tech_grid = self.create_info_grid(tech_items, columns=3)
            tech_section.append(tech_grid)
            content_box.append(tech_section)
        
        # Thread Speeds Section
        if core_speeds:
            speeds_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            
            speeds_title = Gtk.Label(label=f"Thread Speeds ({len(core_speeds)})")
            speeds_title.add_css_class("heading")
            speeds_title.set_halign(Gtk.Align.START)
            speeds_section.append(speeds_title)
            
            cores_flow = self.create_flow_box(max_per_line=8, min_per_line=4)
            
            for core_num, speed in sorted(core_speeds.items()):
                core_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                core_box.add_css_class("core-box")
                
                core_label = Gtk.Label(label=f"Thread {core_num}")
                core_label.add_css_class("core-label")
                core_box.append(core_label)
                
                speed_label = Gtk.Label(label=f"{speed} MHz")
                speed_label.add_css_class("core-speed")
                core_box.append(speed_label)
                
                cores_flow.insert(core_box, -1)
            
            speeds_section.append(cores_flow)
            content_box.append(speeds_section)
        
        # CPU Flags Section - displayed as plain text for readability
        if flags:
            flags_list = flags.split()
            
            flags_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            
            flags_title = Gtk.Label(label=f"CPU Flags ({len(flags_list)})")
            flags_title.add_css_class("heading")
            flags_title.set_halign(Gtk.Align.START)
            flags_section.append(flags_title)
            
            # Simple text label for easier reading
            flags_text = Gtk.Label(label=flags)
            flags_text.set_wrap(True)
            flags_text.set_xalign(0)
            flags_text.add_css_class("dim-label")
            flags_text.add_css_class("monospace")
            flags_text.set_selectable(True)
            
            flags_section.append(flags_text)
            content_box.append(flags_section)
        
        # Vulnerabilities Section
        if vulnerabilities:
            vuln_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            
            vuln_title = Gtk.Label(label=f"CPU Vulnerabilities ({len(vulnerabilities)})")
            vuln_title.add_css_class("heading")
            vuln_title.set_halign(Gtk.Align.START)
            vuln_section.append(vuln_title)
            
            for vuln in vulnerabilities:
                vuln_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                
                vuln_type = vuln.get("type", "")
                vuln_status = vuln.get("status", "")
                vuln_mitigation = vuln.get("mitigation", "")
                
                type_label = Gtk.Label(label=vuln_type)
                type_label.add_css_class("info-value")
                type_label.set_halign(Gtk.Align.START)
                type_label.set_width_chars(25)
                type_label.set_xalign(0)
                vuln_row.append(type_label)
                
                status_text = vuln_mitigation if vuln_mitigation else vuln_status
                status_label = Gtk.Label(label=status_text)
                status_label.set_halign(Gtk.Align.START)
                status_label.set_wrap(True)
                status_label.set_xalign(0)
                status_label.set_hexpand(True)
                
                if vuln_status == "Not affected":
                    status_label.add_css_class("success")
                elif vuln_mitigation:
                    status_label.add_css_class("warning")
                
                vuln_row.append(status_label)
                vuln_section.append(vuln_row)
            
            content_box.append(vuln_section)
        
        expander.set_child(content_box)
        self.append(expander)
    
    def _render_raw_output(self, data: Dict[str, Any]) -> None:
        """Render raw output in collapsible section."""
        raw = data.get("raw", "")
        
        if raw:
            expander = self.create_raw_expander("Full Output", raw)
            self.append(expander)
    
    def _copy_cpu_data(self, data: Dict[str, Any]) -> None:
        """Copy CPU data to clipboard as readable text."""
        cores = data.get("cores", 0)
        threads = data.get("threads", 0)
        cores_threads = f"{cores} Cores / {threads} Threads" if cores and threads else ""
        
        lines = [
            "=== Processor ===",
            "",
            f"Model: {data.get('model', 'Unknown')}",
        ]
        
        if cores_threads:
            lines.append(f"Cores/Threads: {cores_threads}")
        if data.get("arch"):
            lines.append(f"Architecture: {data.get('arch')}")
        if data.get("bits"):
            lines.append(f"Bits: {data.get('bits')}")
        if data.get("speed_max"):
            lines.append(f"Max Speed: {data.get('speed_max')} MHz")
        if data.get("cache_l3"):
            lines.append(f"L3 Cache: {data.get('cache_l3')}")
        
        text = "\n".join(lines)
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
