"""
Disk/Storage Section View for Hardware Reporter.

Renders detailed disk and partition information following GNOME HIG guidelines.
"""

from typing import Dict, Any, Optional, Callable

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from app.ui.views.base import HardwareSectionView
from app.utils.i18n import _


class DiskSectionView(HardwareSectionView):
    """
    View component for displaying disk/storage information.
    
    Displays:
    - Total storage summary with usage bar
    - Individual drive cards with two-column layout
    - Mounted partitions with usage indicators
    """
    
    CATEGORY_ID = "disk"
    
    def render(self, data: Dict[str, Any]) -> None:
        """
        Render disk information.
        
        Args:
            data: Disk hardware data dictionary.
        """
        self.clear()
        
        if not data:
            self.show_no_data(_("No disk information available"))
            return
        
        # Storage summary
        self._render_storage_summary(data)
        
        # Individual drives
        drives = data.get("drives", [])
        if drives:
            self._render_drives(drives)
        
        # Partitions
        partitions = data.get("partitions", [])
        if partitions:
            self._render_partitions(partitions)
    
    def _render_storage_summary(self, data: Dict[str, Any]) -> None:
        """Render total storage summary card."""
        total_size = data.get("total_size", "")
        used = data.get("used", "")
        used_percent = data.get("used_percent", 0)
        
        if not total_size and not used:
            return
        
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("card")
        
        # Title
        title_text = _("Total Storage: {}").format(total_size) if total_size else _("Storage")
        title = Gtk.Label(label=title_text)
        title.add_css_class("title-4")
        title.set_halign(Gtk.Align.START)
        card.append(title)
        
        # Usage bar
        if isinstance(used_percent, (int, float)) and used_percent > 0:
            bar_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            bar_row.set_margin_top(4)
            bar_row.set_margin_bottom(4)
            
            bar = Gtk.ProgressBar()
            bar.set_fraction(used_percent / 100.0)
            bar.add_css_class("usage-bar")
            bar.set_hexpand(True)
            
            if used_percent > 90:
                bar.add_css_class("error")
            elif used_percent > 70:
                bar.add_css_class("warning")
            else:
                bar.add_css_class("success")
            
            bar_row.append(bar)
            
            percent_label = Gtk.Label(label=f"{used_percent:.0f}%")
            percent_label.add_css_class("stat-value")
            bar_row.append(percent_label)
            
            card.append(bar_row)
            
            if used:
                used_label = Gtk.Label(label=_("Used: {}").format(used))
                used_label.add_css_class("info-value")
                used_label.set_halign(Gtk.Align.START)
                card.append(used_label)
        
        self.append(card)
    
    def _render_drives(self, drives: list) -> None:
        """Render individual drive cards."""
        title = self.create_section_title(_("Storage Devices"))
        self.append(title)
        
        for drive in drives:
            card = self._create_drive_card(drive)
            self.append(card)
    
    def _create_drive_card(self, drive: Dict[str, Any]) -> Gtk.Box:
        """Create a card for a storage drive."""
        model = drive.get("model", _("Unknown Drive"))
        
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("card")
        
        # Title row
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        title_label = Gtk.Label(label=model)
        title_label.add_css_class("title-4")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_wrap(True)
        title_label.set_xalign(0)
        title_label.set_hexpand(True)
        title_row.append(title_label)
        
        # Type badge
        drive_type = drive.get("type", "")
        if drive_type:
            type_badge = Gtk.Label(label=drive_type.upper())
            type_badge.add_css_class("device-badge")
            if "ssd" in drive_type.lower() or "nvme" in drive_type.lower():
                type_badge.add_css_class("success-badge")
            type_badge.set_valign(Gtk.Align.CENTER)
            title_row.append(type_badge)
        
        # Copy button
        copy_btn = self._create_copy_button(drive, model)
        title_row.append(copy_btn)
        
        card.append(title_row)
        
        # Build columns
        left_items = [
            (_("Size"), drive.get("size", "")),
            (_("Vendor"), drive.get("vendor", "")),
            (_("Speed"), drive.get("speed", "")),
            (_("Device"), drive.get("id", "")),
        ]
        
        right_items = [
            (_("Lanes"), str(drive.get("lanes", "")) if drive.get("lanes") else ""),
            (_("Temp"), drive.get("temp", "")),
            (_("Firmware"), drive.get("firmware", "")),
            (_("Serial"), str(drive.get("serial", ""))),
        ]
        
        # Filter empty values
        left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "Unknown", "?", "")]
        right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "Unknown", "?", "")]
        
        # Two-column layout
        columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        # Left column
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_col.set_hexpand(True)
        for label, value in left_items:
            item = self._create_spec_item(label, value)
            left_col.append(item)
        columns_box.append(left_col)
        
        if right_items:
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
        
        return card
    
    def _render_partitions(self, partitions: list) -> None:
        """Render mounted partitions."""
        title = self.create_section_title(_("Mounted Partitions"))
        self.append(title)
        
        # Deduplicate by device
        device_partitions = {}
        for partition in partitions:
            dev = partition.get("dev", "")
            if not dev:
                continue
            
            if dev not in device_partitions:
                device_partitions[dev] = {
                    "dev": dev,
                    "fs": partition.get("fs", ""),
                    "size": partition.get("size", partition.get("raw_size", "")),
                    "used": partition.get("used", ""),
                    "used_percent": partition.get("used_percent", 0),
                    "uuid": partition.get("uuid", ""),
                    "label": partition.get("label", ""),
                    "mount_points": []
                }
            
            mount_point = partition.get("id", "")
            if mount_point and mount_point not in device_partitions[dev]["mount_points"]:
                device_partitions[dev]["mount_points"].append(mount_point)
        
        for dev, part_info in device_partitions.items():
            card = self._create_partition_card(part_info)
            self.append(card)
    
    def _create_partition_card(self, part_info: Dict[str, Any]) -> Gtk.Box:
        """Create a card for a partition."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card")
        
        # Header row
        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        dev_label = Gtk.Label(label=part_info.get("dev", ""))
        dev_label.add_css_class("device-title")
        dev_label.set_halign(Gtk.Align.START)
        dev_label.set_selectable(True)
        header_row.append(dev_label)
        
        # Label badge
        label = part_info.get("label", "")
        if label and label != "N/A":
            label_badge = Gtk.Label(label=label)
            label_badge.add_css_class("device-badge")
            label_badge.add_css_class("accent")
            header_row.append(label_badge)
        
        # Filesystem badge
        fs = part_info.get("fs", "")
        if fs:
            fs_badge = Gtk.Label(label=fs)
            fs_badge.add_css_class("device-badge")
            header_row.append(fs_badge)
        
        header_row.set_hexpand(True)
        card.append(header_row)
        
        # Usage bar
        used_percent = part_info.get("used_percent", 0)
        if isinstance(used_percent, (int, float)) and used_percent > 0:
            bar_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            
            bar = Gtk.ProgressBar()
            bar.set_fraction(used_percent / 100.0)
            bar.add_css_class("usage-bar")
            bar.set_hexpand(True)
            
            if used_percent > 90:
                bar.add_css_class("error")
            elif used_percent > 70:
                bar.add_css_class("warning")
            else:
                bar.add_css_class("success")
            
            bar_row.append(bar)
            
            percent_label = Gtk.Label(label=f"{used_percent:.0f}%")
            bar_row.append(percent_label)
            
            card.append(bar_row)
        
        # Size info
        size = part_info.get("size", "")
        used = part_info.get("used", "")
        if size or used:
            info_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            
            if size:
                size_item = self._create_spec_item(_("Size"), size)
                info_row.append(size_item)
            
            if used:
                used_item = self._create_spec_item(_("Used"), used)
                info_row.append(used_item)
            
            card.append(info_row)
        
        # Mount points
        mount_points = part_info.get("mount_points", [])
        if mount_points:
            mounts_text = ", ".join(mount_points)
            mounts_item = self._create_spec_item(_("Mounted at"), mounts_text)
            card.append(mounts_item)
        
        return card
    
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
        lines = [f"=== {name} ===", ""]
        
        for key in ["size", "vendor", "type", "speed", "id", "serial", "firmware", "temp"]:
            value = device.get(key, "")
            if value:
                lines.append(f"{key}: {value}")
        
        text = "\n".join(lines)
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
