"""
Summary section renderer.
"""

from typing import Dict, Any

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from big_hardware_info.ui import builders as ui
from big_hardware_info.ui.renderers.base import SectionRenderer
from big_hardware_info.utils.i18n import _


class SummaryRenderer(SectionRenderer):
    """Renderer for summary/overview section."""
    
    def render(self) -> None:
        """Render summary section with quick actions and system overview."""
        gpu_data = self.data.get("gpu", {})
        memory_data = self.data.get("memory", {})
        system_data = self.data.get("system", {})
        disk_usage = self.data.get("disk_usage", {})
        
        # Quick Actions row
        actions_row = ui.row(spacing=16)
        actions_row.set_homogeneous(True)
        actions_row.set_margin_bottom(24)

        actions_row.append(
            ui.action_card(
                "document-save-symbolic",
                _("Export Report"),
                _(
                    "Save a complete HTML report of your hardware to share with support or keep for reference."
                ),
                _("Export"),
                lambda b: self.window.app.activate_action("export", None),
            )
        )

        actions_row.append(
            ui.action_card(
                "send-to-symbolic",
                _("Share Online"),
                _(
                    "Upload your hardware report to get a shareable link for forums or support tickets."
                ),
                _("Share"),
                lambda b: self.window.app.activate_action("share", None),
            )
        )
        
        self.container.append(actions_row)
        
        # Overview row - two cards side by side
        overview_row = ui.row(spacing=16)
        overview_row.set_homogeneous(True)
        overview_row.set_margin_bottom(8)
        
        # Left card - Usage Overview
        overview_row.append(self._render_usage_card(memory_data, disk_usage))
        
        # Right card - System Info
        overview_row.append(self._render_system_info_card(gpu_data, system_data))
        
        # Make row searchable
        searchable = self._build_searchable_text(memory_data, disk_usage, gpu_data, system_data)
        self.make_searchable(overview_row, searchable)
        
        self.container.append(overview_row)
    
    def _render_usage_card(self, memory_data: Dict, disk_usage: Dict) -> Gtk.Box:
        """Render the usage overview card (RAM + Partition)."""
        card = ui.card()
        
        # Header with copy button
        header = ui.row(spacing=8)
        title = ui.title(_("Usage Overview"))
        title.set_hexpand(True)
        header.append(title)
        
        copy_text = self._format_usage_copy(memory_data, disk_usage)
        header.append(ui.copy_button(on_click=lambda b: self.copy_to_clipboard(copy_text, _("Usage Overview"))))
        card.append(header)
        
        # RAM Section
        ram_total = memory_data.get("total", "Unknown")
        ram_used = memory_data.get("used", "")
        ram_percent = memory_data.get("used_percent", 0)
        
        ram_display = str(ram_total).replace("GiB", "GB") if "GiB" in str(ram_total) else str(ram_total)
        ram_used_clean = str(ram_used).split("(")[0].strip() if "(" in str(ram_used) else ram_used
        
        ram_row = ui.row(spacing=8)
        ram_row.append(ui.dim_label(_("Memory RAM:")))
        ram_row.append(ui.heading(ram_display))
        card.append(ram_row)
        
        # RAM details
        details = ui.grid()
        details.attach(ui.dim_label(_("Used"), caption=True), 0, 0, 1, 1)
        details.attach(ui.label(str(ram_used_clean) or "N/A", halign=Gtk.Align.START), 1, 0, 1, 1)
        card.append(details)
        
        # RAM progress bar
        if isinstance(ram_percent, (int, float)) and ram_percent > 0:
            card.append(ui.progress_bar(ram_percent / 100.0))
        
        card.append(ui.separator(margins=(4, 4)))
        
        # Partition Section
        partition = disk_usage.get("device", "") or disk_usage.get("mount_point", "/")
        part_size = disk_usage.get("size", "Unknown")
        used_space = disk_usage.get("used", "Unknown")
        free_space = disk_usage.get("available", "Unknown")
        use_percent_str = disk_usage.get("use_percent", "0%")
        
        used_percent = 0
        try:
            if use_percent_str and use_percent_str != "Unknown":
                used_percent = float(str(use_percent_str).replace("%", "").strip())
        except (ValueError, TypeError):
            pass
        
        part_row = ui.row(spacing=8)
        part_row.append(ui.dim_label(_("Root Partition:")))
        part_row.append(ui.heading(partition))
        card.append(part_row)
        
        # Partition details grid
        part_grid = ui.grid()
        col = 0
        for lbl, val in [
            (_("Size"), part_size),
            (_("Used"), used_space),
            (_("Free"), free_space),
        ]:
            part_grid.attach(ui.dim_label(lbl, caption=True), col, 0, 1, 1)
            part_grid.attach(ui.label(val, halign=Gtk.Align.START), col + 1, 0, 1, 1)
            col += 2
        card.append(part_grid)
        
        # Partition progress bar
        if used_percent > 0:
            card.append(ui.progress_bar(used_percent / 100.0))
        
        return card
    
    def _render_system_info_card(self, gpu_data: Dict, system_data: Dict) -> Gtk.Box:
        """Render the system info card (Distro, GPU, Install Date, Kernel)."""
        card = ui.card()
        
        # Header with copy button
        header = ui.row(spacing=8)
        title = ui.title(_("System Info"))
        title.set_hexpand(True)
        header.append(title)
        
        gpus = gpu_data.get("devices", [])
        gpu_name = gpus[0].get("model", gpus[0].get("name", "Unknown")) if gpus else "Unknown"
        distro = system_data.get("distro", "")
        kernel = self._get_kernel(system_data)
        install_date = self._get_install_date(system_data)
        
        copy_text = self._format_system_copy(distro, gpu_name, install_date, kernel)
        header.append(ui.copy_button(on_click=lambda b: self.copy_to_clipboard(copy_text, _("System Info"))))
        card.append(header)
        
        # Info items
        items = [
            (_("Distro"), distro),
            (_("Video"), gpu_name),
            (_("Install Date"), install_date),
            (_("Kernel"), kernel),
        ]
        
        for label, value in items:
            if value:
                section = ui.box(vertical=True, spacing=4)
                section.append(ui.dim_label(label, caption=True))
                val_lbl = ui.heading(value)
                val_lbl.set_wrap(True)
                val_lbl.set_xalign(0)
                section.append(val_lbl)
                card.append(section)
        
        return card
    
    def _get_kernel(self, system_data: Dict) -> str:
        """Get kernel version from data."""
        kernel_data = self.data.get("kernel", {})
        kernel = kernel_data.get("version", "") if isinstance(kernel_data, dict) else ""
        return kernel or system_data.get("kernel", "Unknown")
    
    def _get_install_date(self, system_data: Dict) -> str:
        """Get install date from data."""
        install_data = self.data.get("install_date", {})
        date = install_data.get("estimate", "") if isinstance(install_data, dict) else ""
        return date or system_data.get("install_date", "")
    
    def _format_usage_copy(self, memory: Dict, disk: Dict) -> str:
        """Format usage data for clipboard."""
        return "\n".join([
            _("=== Usage Overview ==="),
            "",
            _("Memory RAM: {memory}").format(memory=memory.get("total", "Unknown")),
            _("  Used: {used}").format(used=memory.get("used", "N/A")),
            _("  Usage: {usage}%").format(usage=memory.get("used_percent", "N/A")),
            "",
            _("Root Partition: {partition}").format(
                partition=disk.get("device", disk.get("mount_point", "/"))
            ),
            _("  Size: {size}").format(size=disk.get("size", "Unknown")),
            _("  Used: {used}").format(used=disk.get("used", "Unknown")),
            _("  Free: {free}").format(free=disk.get("available", "Unknown")),
            _("  Usage: {usage}").format(usage=disk.get("use_percent", "N/A")),
        ])
    
    def _format_system_copy(self, distro: str, gpu: str, date: str, kernel: str) -> str:
        """Format system info for clipboard."""
        lines = [_("=== System Info ==="), ""]
        if distro:
            lines.append(_("Distro: {distro}").format(distro=distro))
        if gpu:
            lines.append(_("Video: {video}").format(video=gpu))
        if date:
            lines.append(_("Install Date: {date}").format(date=date))
        lines.append(_("Kernel: {kernel}").format(kernel=kernel or "Unknown"))
        return "\n".join(lines)
    
    def _build_searchable_text(self, memory: Dict, disk: Dict, gpu: Dict, system: Dict) -> str:
        """Build searchable text for the section."""
        parts = []
        parts.append(f"Memory RAM {memory.get('total', '')}")
        parts.append(f"Partition {disk.get('device', '')}")
        if system.get("distro"):
            parts.append(f"Distro {system['distro']}")
        gpus = gpu.get("devices", [])
        if gpus:
            parts.append(f"Video GPU {gpus[0].get('model', gpus[0].get('name', ''))}")
        parts.append(f"Kernel {system.get('kernel', '')}")
        return " ".join(parts)
