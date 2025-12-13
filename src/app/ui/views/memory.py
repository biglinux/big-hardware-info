"""
Memory Section View for Hardware Reporter.

Renders detailed memory/RAM information following GNOME HIG guidelines.
"""

from typing import Dict, Any

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

try:
    gi.require_version("Adw", "1")
    from gi.repository import Adw
    HAS_ADW = True
except (ValueError, ImportError):
    HAS_ADW = False

from app.ui.views.base import HardwareSectionView


class MemorySectionView(HardwareSectionView):
    """
    View component for displaying memory information.
    
    Displays:
    - Usage hero card with total memory and usage bar
    - Memory modules (RAM sticks) details
    - Swap/ZRAM section with usage
    - Raw output (collapsible)
    """
    
    CATEGORY_ID = "memory"
    
    def __init__(self, disk_data: Dict[str, Any] = None, **kwargs) -> None:
        """
        Initialize memory view.
        
        Args:
            disk_data: Optional disk data containing swap information.
            **kwargs: Additional arguments passed to parent.
        """
        super().__init__(**kwargs)
        self._disk_data = disk_data or {}
    
    def set_disk_data(self, disk_data: Dict[str, Any]) -> None:
        """
        Set disk data for swap information.
        
        Args:
            disk_data: Disk hardware data containing swap entries.
        """
        self._disk_data = disk_data or {}
    
    def render(self, data: Dict[str, Any]) -> None:
        """
        Render memory information.
        
        Args:
            data: Memory hardware data dictionary.
        """
        self.clear()
        
        if not data:
            self.show_no_data("No memory information available")
            return
        
        # Render sections
        self._render_hero_card(data)
        self._render_modules(data)
        self._render_swap_section()
        self._render_raw_output(data)
    
    def _render_hero_card(self, data: Dict[str, Any]) -> None:
        """Render the main memory usage hero card."""
        hero_card = self.create_hero_card()
        
        # Header with icon
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        icon = Gtk.Image.new_from_icon_name("memory-symbolic")
        icon.set_pixel_size(32)
        icon.add_css_class("accent")
        header.append(icon)
        
        total = data.get("total", "Unknown")
        title = Gtk.Label(label=f"Total Memory: {total}")
        title.add_css_class("hero-title")
        title.set_hexpand(True)
        title.set_halign(Gtk.Align.START)
        header.append(title)
        
        # Copy button for memory info
        copy_btn = Gtk.Button()
        copy_btn.set_icon_name("edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.set_tooltip_text("Copy memory info")
        copy_btn.set_valign(Gtk.Align.CENTER)
        copy_btn.connect("clicked", lambda b, d=data: self._copy_memory_data(d))
        header.append(copy_btn)
        
        hero_card.append(header)
        
        # Usage bar
        used_percent = data.get("used_percent", 0)
        if isinstance(used_percent, (int, float)) and used_percent > 0:
            bar_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            
            # Labels row
            usage_labels = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            usage_labels.set_hexpand(True)
            
            used = data.get("used", "")
            available = data.get("available", "")
            
            # Clean percentage from used string
            used_clean = self.clean_percentage_string(used)
            
            used_label = Gtk.Label(label=f"Used: {used_clean}")
            used_label.add_css_class("info-value")
            used_label.set_halign(Gtk.Align.START)
            usage_labels.append(used_label)
            
            bar_container.append(usage_labels)
            
            # Progress bar
            bar = Gtk.ProgressBar()
            bar.set_fraction(used_percent / 100.0)
            bar.add_css_class("usage-bar")
            if used_percent > 90:
                bar.add_css_class("error")
            elif used_percent > 70:
                bar.add_css_class("warning")
            else:
                bar.add_css_class("success")
            bar_container.append(bar)
            
            # Percentage label
            percent_label = Gtk.Label(label=f"{used_percent:.1f}% used")
            percent_label.add_css_class("info-label")
            percent_label.set_halign(Gtk.Align.END)
            bar_container.append(percent_label)
            
            hero_card.append(bar_container)
        
        # Array Info section (capacity, modules, slots, etc.)
        array_items = []
        if data.get("capacity"):
            array_items.append(("Capacity", data.get("capacity")))
        if data.get("modules_count"):
            array_items.append(("Modules", data.get("modules_count")))
        if data.get("slots"):
            array_items.append(("Slots", data.get("slots")))
        if data.get("max_module_size"):
            note = f" ({data.get('note')})" if data.get("note") else ""
            array_items.append(("Max Module Size", f"{data.get('max_module_size')}{note}"))
        if data.get("ec"):
            array_items.append(("ECC", data.get("ec")))
        
        if array_items:
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.set_margin_top(12)
            sep.set_margin_bottom(12)
            hero_card.append(sep)
            
            # Two-column layout for array info
            columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            
            # Split items between columns
            mid = (len(array_items) + 1) // 2
            left_items = array_items[:mid]
            right_items = array_items[mid:]
            
            # Left column
            left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            left_col.set_hexpand(True)
            for label, value in left_items:
                item = self._create_spec_item(label, str(value))
                left_col.append(item)
            columns_box.append(left_col)
            
            if right_items:
                # Visual separator
                separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                separator.set_margin_start(24)
                separator.set_margin_end(24)
                columns_box.append(separator)
                
                # Right column
                right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
                right_col.set_hexpand(True)
                for label, value in right_items:
                    item = self._create_spec_item(label, str(value))
                    right_col.append(item)
                columns_box.append(right_col)
            
            hero_card.append(columns_box)
        
        self.append(hero_card)
    
    def _create_spec_item(self, label: str, value: str) -> Gtk.Box:
        """Create a spec item with label on top and value below."""
        item_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("caption")
        label_widget.add_css_class("dim-label")
        label_widget.set_halign(Gtk.Align.START)
        item_box.append(label_widget)
        
        value_widget = Gtk.Label(label=value)
        value_widget.add_css_class("heading")
        value_widget.set_halign(Gtk.Align.START)
        value_widget.set_selectable(True)
        item_box.append(value_widget)
        
        return item_box
    
    def _render_modules(self, data: Dict[str, Any]) -> None:
        """Render memory modules (RAM sticks) section in a collapsible expander."""
        modules = data.get("modules", [])
        
        if not modules:
            return
        
        # Create expander for modules
        modules_count = len(modules)
        expander = Gtk.Expander(label=f"Memory Modules ({modules_count})")
        expander.add_css_class("card")
        
        # Content container
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(8)
        
        # Each module in a card inside the expander
        for module in modules:
            slot_card = self._create_module_card(module)
            content.append(slot_card)
        
        expander.set_child(content)
        self.append(expander)
    
    def _create_module_card(self, module: Dict[str, Any]) -> Gtk.Box:
        """
        Create a card for a memory module.
        
        Args:
            module: Memory module data dictionary.
            
        Returns:
            Styled Gtk.Box card.
        """
        slot_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        slot_card.set_hexpand(True)
        
        # Slot header with chip icon
        slot_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        slot_header.set_margin_bottom(4)
        
        slot_icon = Gtk.Image.new_from_icon_name("application-x-firmware-symbolic")
        slot_icon.set_pixel_size(20)
        slot_icon.add_css_class("accent")
        slot_header.append(slot_icon)
        
        # Size and type as title
        size = module.get("size", "Unknown")
        mem_type = module.get("type", "")
        slot_title = Gtk.Label(label=f"{size} {mem_type}".strip())
        slot_title.add_css_class("heading")
        slot_title.set_halign(Gtk.Align.START)
        slot_header.append(slot_title)
        
        slot_card.append(slot_header)
        
        # Build speed display: show both spec and actual if different
        spec_speed = module.get("speed", "")
        actual_speed = module.get("actual_speed", "")
        
        if spec_speed and actual_speed and spec_speed != actual_speed:
            speed_display = f"{actual_speed} (Spec: {spec_speed})"
        elif actual_speed:
            speed_display = actual_speed
        else:
            speed_display = spec_speed
        
        # Info rows
        info_items = [
            ("Slot", module.get("slot", "")),
            ("Speed", speed_display),
            ("Volts", module.get("volts", "")),
            ("Manufacturer", module.get("manufacturer", "")),
            ("Part Number", module.get("part_no", "")),
            ("Serial", module.get("serial", "")),
        ]
        
        for label, value in info_items:
            if value and value not in ("N/A", ""):
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                row.add_css_class("info-row")
                
                label_w = Gtk.Label(label=label)
                label_w.add_css_class("info-label")
                label_w.set_halign(Gtk.Align.START)
                label_w.set_hexpand(True)
                row.append(label_w)
                
                value_w = Gtk.Label(label=value)
                value_w.add_css_class("info-value")
                value_w.set_halign(Gtk.Align.END)
                value_w.set_selectable(True)
                row.append(value_w)
                
                slot_card.append(row)
        
        # Add separator between modules
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(8)
        slot_card.append(sep)
        
        return slot_card
    
    def _render_swap_section(self) -> None:
        """Render Swap/ZRAM section from disk data."""
        swap_entries = self._disk_data.get("swap", [])
        swap_kernel = self._disk_data.get("swap_kernel", {})
        
        if not swap_entries and not swap_kernel:
            return
        
        # Section title
        title = self.create_section_title("Swap / ZRAM")
        self.append(title)
        
        # Kernel settings card
        if swap_kernel and any(swap_kernel.values()):
            self._render_swap_kernel_settings(swap_kernel)
        
        # Swap entries
        for swap in swap_entries:
            self._render_swap_entry(swap)
    
    def _render_swap_kernel_settings(self, swap_kernel: Dict[str, Any]) -> None:
        """Render swap kernel settings card."""
        settings_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        settings_card.add_css_class("card")
        
        settings_header = Gtk.Label(label="Kernel Settings")
        settings_header.add_css_class("device-title")
        settings_header.set_halign(Gtk.Align.START)
        settings_card.append(settings_header)
        
        settings_items = [
            ("Swappiness", swap_kernel.get("swappiness", "")),
            ("Cache Pressure", swap_kernel.get("cache_pressure", "")),
            ("ZSwap", swap_kernel.get("zswap", "")),
            ("Compressor", swap_kernel.get("compressor", "")),
        ]
        
        settings_grid = self.create_info_grid(settings_items, columns=2, column_spacing=32)
        settings_card.append(settings_grid)
        
        self.append(settings_card)
    
    def _render_swap_entry(self, swap: Dict[str, Any]) -> None:
        """Render a single swap entry card."""
        swap_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        swap_card.add_css_class("card")
        
        # Header
        swap_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        # Icon based on type
        swap_type = swap.get("type", "").lower()
        icon_name = "drive-harddisk-solidstate-symbolic" if "zram" in swap_type else "drive-harddisk-symbolic"
        
        swap_icon = Gtk.Image.new_from_icon_name(icon_name)
        swap_icon.set_pixel_size(24)
        swap_icon.add_css_class("accent")
        swap_header.append(swap_icon)
        
        # Title
        swap_id = swap.get("id", "Swap")
        swap_type_display = swap.get("type", "").upper()
        swap_title = Gtk.Label(label=f"{swap_id} ({swap_type_display})")
        swap_title.add_css_class("device-title")
        swap_header.append(swap_title)
        
        # Size badge
        swap_size = swap.get("size", "")
        if swap_size:
            size_badge = Gtk.Label(label=swap_size)
            size_badge.add_css_class("device-badge")
            size_badge.set_halign(Gtk.Align.END)
            size_badge.set_hexpand(True)
            swap_header.append(size_badge)
        
        swap_card.append(swap_header)
        
        # Usage bar
        used_percent = swap.get("used_percent", 0)
        if isinstance(used_percent, (int, float)):
            bar_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            
            bar = Gtk.ProgressBar()
            bar.set_fraction(used_percent / 100.0 if used_percent > 0 else 0)
            bar.add_css_class("usage-bar")
            if used_percent > 80:
                bar.add_css_class("error")
            elif used_percent > 50:
                bar.add_css_class("warning")
            else:
                bar.add_css_class("success")
            bar_container.append(bar)
            
            # Usage info - clean percentage
            used_str = swap.get('used', '')
            used_clean = self.clean_percentage_string(used_str)
            usage_label = Gtk.Label(label=f"Used: {used_clean} ({used_percent:.1f}%)")
            usage_label.add_css_class("info-label")
            usage_label.set_halign(Gtk.Align.END)
            bar_container.append(usage_label)
            
            swap_card.append(bar_container)
        
        # Details
        details = []
        if swap.get("priority"):
            details.append(f"Priority: {swap['priority']}")
        if swap.get("comp"):
            details.append(f"Compression: {swap['comp']}")
        if swap.get("dev"):
            details.append(f"Device: {swap['dev']}")
        
        if details:
            detail_label = Gtk.Label(label=" | ".join(details))
            detail_label.add_css_class("device-subtitle")
            detail_label.set_halign(Gtk.Align.START)
            swap_card.append(detail_label)
        
        self.append(swap_card)
    
    def _render_raw_output(self, data: Dict[str, Any]) -> None:
        """Render raw output in collapsible section."""
        raw = data.get("raw", "")
        
        if raw:
            expander = self.create_raw_expander("Full Output", raw)
            self.append(expander)
    
    def _copy_memory_data(self, data: Dict[str, Any]) -> None:
        """Copy memory data to clipboard as readable text."""
        lines = [
            "=== Memory ===",
            "",
            f"Total: {data.get('total', 'Unknown')}",
            f"Used: {data.get('used', 'N/A')}",
            f"Usage: {data.get('used_percent', 'N/A')}%",
        ]
        
        if data.get("capacity"):
            lines.append(f"Capacity: {data.get('capacity')}")
        if data.get("modules_count"):
            lines.append(f"Modules: {data.get('modules_count')}")
        if data.get("slots"):
            lines.append(f"Slots: {data.get('slots')}")
        
        text = "\n".join(lines)
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
