"""
System information section renderer.
"""

from typing import Dict, List, Tuple

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from app.ui import builders as ui
from app.ui.renderers.base import SectionRenderer
from app.utils.i18n import _


class SystemRenderer(SectionRenderer):
    """Renderer for system information section."""
    
    def render(self) -> None:
        """Render system information."""
        system_data = self.data.get("system", {})
        
        if not system_data:
            self.show_no_data(_("No system information available"))
            return
        
        # Build derived values
        shell_display = self._build_shell_display(system_data)
        kernel_display = self._build_kernel_display(system_data)
        compilers_display = self._build_compilers_display(system_data)
        
        # Main OS Info Card
        self._render_os_card(system_data, kernel_display, shell_display)
        
        # Compilers if available
        if compilers_display:
            item = ui.spec_item(_("Compilers"), compilers_display)
            item.add_css_class("card")
            self.container.append(item)
        
        # Flatpaks if available
        flatpaks = system_data.get("flatpaks", "")
        if flatpaks and flatpaks not in ("N/A", "Unknown", "?", ""):
            item = ui.spec_item(_("Flatpak Packages"), flatpaks)
            item.add_css_class("card")
            self.container.append(item)
        
        # Top processes
        self._render_processes_section()
        
        # Repositories
        self._render_repos_section()
        
        # Raw output
        if system_data.get("raw"):
            self.add_raw_expander("Full Output", system_data["raw"])
    
    def _build_shell_display(self, data: Dict) -> str:
        """Build shell display string."""
        shell = data.get("shell", "")
        version = data.get("shell_version", "")
        return f"{shell} v{version}" if version else shell
    
    def _build_kernel_display(self, data: Dict) -> str:
        """Build kernel display string."""
        kernel = data.get("kernel", "")
        arch = data.get("kernel_arch", "")
        bits = data.get("kernel_bits", "")
        if arch:
            kernel += f" ({arch}"
            if bits:
                kernel += f", {bits} bit"
            kernel += ")"
        return kernel
    
    def _build_compilers_display(self, data: Dict) -> str:
        """Build compilers display string."""
        compilers = []
        if data.get("gcc_version"):
            compilers.append(f"gcc: {data['gcc_version']}")
        if data.get("clang_version"):
            compilers.append(f"clang: {data['clang_version']}")
        return ", ".join(compilers) if compilers else ""
    
    def _render_os_card(self, data: Dict, kernel_display: str, shell_display: str) -> None:
        """Render the main OS info card."""
        card = ui.card()
        
        # Title row
        distro = data.get("distro", _("Linux"))
        title_row = ui.row(spacing=12)
        
        title_lbl = ui.label(distro, css_classes=["title-4"], halign=Gtk.Align.START, wrap=True, hexpand=True)
        title_lbl.set_xalign(0)
        title_row.append(title_lbl)
        
        # Copy button
        copy_text = self.format_copy_text(distro, [
            ("Hostname", data.get("hostname", "")),
            ("Kernel", kernel_display),
            ("Desktop", f"{data.get('desktop', '')} {data.get('desktop_version', '')}".strip()),
            ("Shell", shell_display),
            ("Init System", data.get("init", "")),
            ("Session Type", data.get("session_type", "")),
            ("Uptime", data.get("uptime", "")),
        ])
        title_row.append(ui.copy_button(on_click=lambda b: self.copy_to_clipboard(copy_text, distro)))
        
        card.append(title_row)
        
        # Two columns
        left_items = self._filter_items([
            (_("Hostname"), data.get("hostname", "")),
            (_("Kernel"), kernel_display),
            (_("Desktop"), f"{data.get('desktop', '')} {data.get('desktop_version', '')}".strip()),
            (_("Window Manager"), data.get("wm", "")),
            (_("Shell"), shell_display),
            (_("Terminal"), data.get("terminal", "")),
        ])
        
        right_items = self._filter_items([
            (_("Init System"), data.get("init", "")),
            (_("Session Type"), data.get("session_type", "")),
            (_("Display Manager"), data.get("dm", "")),
            (_("Compositor"), data.get("compositor", "")),
            (_("Uptime"), data.get("uptime", "")),
            (_("Processes"), data.get("processes", "")),
            (_("Packages"), data.get("packages", "")),
            (_("Locale"), data.get("locale", "")),
        ])
        
        columns = self._render_columns(left_items, right_items)
        card.append(columns)
        
        self.container.append(card)
    
    def _filter_items(self, items: List[Tuple]) -> List[Tuple]:
        """Filter out empty values."""
        return [(l, v) for l, v in items if v and v not in ("N/A", "Unknown", "?", "")]
    
    def _render_columns(self, left: List[Tuple], right: List[Tuple]) -> Gtk.Box:
        """Render two-column layout."""
        columns = ui.row(spacing=0)
        
        left_col = ui.box(vertical=True, spacing=8)
        left_col.set_hexpand(True)
        for label, value in left:
            left_col.append(ui.spec_item(label, value))
        columns.append(left_col)
        
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
    
    def _render_processes_section(self) -> None:
        """Render top processes section."""
        processes_data = self.data.get("processes", {})
        cpu_top = processes_data.get("cpu_top", [])
        memory_top = processes_data.get("memory_top", [])
        
        if not cpu_top and not memory_top:
            return
        
        expander = Gtk.Expander(label=_("Top Processes"))
        expander.add_css_class("card")
        expander.set_margin_top(12)
        
        box = ui.box(vertical=True, spacing=12)
        box.set_margin_top(8)
        
        # CPU top processes
        if cpu_top:
            self._render_process_list(box, _("CPU Usage"), cpu_top[:5], "cpu")
        
        # Memory top processes
        if memory_top:
            if cpu_top:
                sep = ui.separator(margins=(8, 8))
                box.append(sep)
            self._render_process_list(box, _("Memory Usage"), memory_top[:5], "mem")
        
        expander.set_child(box)
        self.container.append(expander)
    
    def _render_process_list(self, container: Gtk.Box, title: str, processes: List[Dict], value_key: str) -> None:
        """Render a list of processes."""
        title_lbl = ui.heading(title)
        title_lbl.set_halign(Gtk.Align.START)
        container.append(title_lbl)
        
        for proc in processes:
            row = ui.row(spacing=12)
            
            cmd_lbl = ui.label(proc.get("command", ""), css_classes=["info-value"], halign=Gtk.Align.START, hexpand=True)
            row.append(cmd_lbl)
            
            val_lbl = ui.label(proc.get(value_key, ""), css_classes=["info-label"])
            row.append(val_lbl)
            
            container.append(row)
    
    def _render_repos_section(self) -> None:
        """Render packages & repositories section."""
        repos_data = self.data.get("repos", {})
        packages = repos_data.get("packages", {})
        repos = repos_data.get("repos", [])
        
        if not packages and not repos:
            return
        
        expander = Gtk.Expander(label=_("Packages & Repositories"))
        expander.add_css_class("card")
        expander.set_margin_top(12)
        
        box = ui.box(vertical=True, spacing=8)
        box.set_margin_top(8)
        
        # Package managers
        if packages:
            grid = ui.grid(row_spacing=4, col_spacing=24)
            row, col = 0, 0
            
            for pm_name, count in packages.items():
                if count and str(count) != "0":
                    pm_lbl = ui.label(pm_name, css_classes=["info-label"], halign=Gtk.Align.START)
                    grid.attach(pm_lbl, col * 2, row, 1, 1)
                    
                    count_lbl = ui.label(str(count), css_classes=["info-value"], halign=Gtk.Align.START)
                    grid.attach(count_lbl, col * 2 + 1, row, 1, 1)
                    
                    col += 1
                    if col >= 3:
                        col = 0
                        row += 1
            
            box.append(grid)
        
        # Repository URLs
        if repos:
            if packages:
                box.append(ui.separator(margins=(8, 8)))
            
            repos_title = ui.heading("Active Repositories")
            repos_title.set_halign(Gtk.Align.START)
            box.append(repos_title)
            
            for repo in repos[:10]:
                url = repo.get("url", "")
                if url:
                    url_lbl = ui.label(url, css_classes=["dim-label", "caption"], halign=Gtk.Align.START, wrap=True, selectable=True)
                    box.append(url_lbl)
        
        expander.set_child(box)
        self.container.append(expander)
