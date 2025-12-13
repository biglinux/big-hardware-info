"""
Main window for the Big Hardware Info application.

Provides the main UI with sidebar navigation and formatted content display.
"""

import gi
import logging
import threading
import os
import re

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Gdk, Pango

from app.collectors import HardwareCollector
from app.models.hardware_info import HardwareInfo, CATEGORIES
from app.ui.views import VIEW_REGISTRY, CpuSectionView, MemorySectionView
from app.ui.renderers import (
    SummaryRenderer, BatteryRenderer, BluetoothRenderer, SensorsRenderer,
    PrintersRenderer, WebcamsRenderer, SystemRenderer, UsbRenderer,
    PciRenderer, MoreInfoRenderer, MachineRenderer
)
from app.ui import dialogs
from app.ui.search import SearchHandler
from app.export.html_generator import HtmlGenerator
from app.utils.style_manager import StyleManager
from app.utils.i18n import _

logger = logging.getLogger(__name__)

# PCI device classification keywords for separating important devices from infrastructure
PCI_INFRASTRUCTURE_KEYWORDS = [
    "bridge", "bus", "usb controller", "hub", "host bridge",
    "isa bridge", "pci bridge", "pcie", "smbus", "communication controller",
    "signal processing", "serial bus", "system peripheral", "pic", "dma",
    "rtc", "timer", "watchdog", "sd host", "sd/mmc",
    "sata controller", "ahci", "sata ahci"  # Storage controllers go to infrastructure
]


class MainWindow(Adw.ApplicationWindow):
    """Main application window with sidebar navigation."""

    def __init__(self, application, config=None, **kwargs):
        """Initialize the main window."""
        self.app = application
        self.config = config
        
        # Default window size
        default_width = 1200
        default_height = 850
        is_maximized = False
        
        # Load saved window state
        if self.config:
            try:
                default_width = int(self.config.get("window_width", 1200))
                default_height = int(self.config.get("window_height", 850))
                is_maximized = self.config.get("window_maximized", False)
            except (ValueError, TypeError):
                pass
        
        super().__init__(
            application=application,
            title=_("Big Hardware Info"),
            default_width=default_width,
            default_height=default_height,
            **kwargs,
        )
        
        # Initialize state
        self._should_maximize = is_maximized
        self._size_save_timeout_id = None
        
        # Initialize collector
        self.collector = HardwareCollector()
        
        # Collected hardware data
        self.hardware_data = {}
        
        # Current category
        self.current_category = "summary"
        
        # Search filter
        self.search_filter = ""
        
        # Section widgets for scroll navigation
        self.section_widgets = {}
        
        # Search handler
        self.search_handler = SearchHandler(self)
        
        # Scroll tracking state (Task #1)
        self._scroll_tracking_enabled = True
        self._programmatic_scroll = False
        
        # Setup CSS
        self._setup_css()
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self.connect("close-request", self._on_close_request)
        self.connect("notify::default-width", self._on_window_size_changed)
        self.connect("notify::default-height", self._on_window_size_changed)
        self.connect("notify::maximized", self._on_window_state_changed)
        
        # Restore maximized state
        if self._should_maximize:
            GLib.timeout_add(100, self.maximize)
        
        # Start collecting data
        GLib.idle_add(self._start_data_collection)

    def _setup_css(self):
        """
        Set up custom CSS styles using the external StyleManager.
        
        CSS has been extracted to app/resources/style.css for better
        maintainability and separation of concerns.
        """
        style_manager = StyleManager.get_default()
        if not style_manager.load_styles():
            logger.warning("Failed to load external CSS, styles may not apply correctly")

    def setup_ui(self):
        """Setup the user interface following Adwaita/GNOME HIG guidelines.
        
        Modern design: All content in a single scrollable view with smooth
        scroll-to navigation from the sidebar categories.
        """
        # Create ToastOverlay as root widget for toast notifications
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)
        
        # Create NavigationSplitView - the proper Adwaita component for sidebar layouts
        self.split_view = Adw.NavigationSplitView()
        self.toast_overlay.set_child(self.split_view)
        
        # === SIDEBAR ===
        sidebar_toolbar = Adw.ToolbarView()
        
        # Sidebar header with app icon and title (like Control Center)
        sidebar_header = Adw.HeaderBar()
        
        # App icon button (clickable for About)
        app_icon_btn = Gtk.Button()
        app_icon_btn.add_css_class("flat")
        app_icon = Gtk.Image.new_from_icon_name("computer-symbolic")
        app_icon.set_pixel_size(20)
        app_icon_btn.set_child(app_icon)
        app_icon_btn.set_tooltip_text(_("About Big Hardware Info"))
        app_icon_btn.connect("clicked", lambda btn: self.app.activate_action("about", None))
        sidebar_header.pack_start(app_icon_btn)
        
        # Title in sidebar header
        sidebar_title = Adw.WindowTitle.new(_("Big Hardware Info"), "")
        sidebar_header.set_title_widget(sidebar_title)
        
        sidebar_toolbar.add_top_bar(sidebar_header)
        
        # Sidebar content - category list
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_vexpand(True)
        
        self.category_list = Gtk.ListBox()
        self.category_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.category_list.add_css_class("navigation-sidebar")
        self.category_list.connect("row-selected", self._on_category_selected)
        
        # Add categories
        for cat_id, cat_info in CATEGORIES.items():
            row = self._create_category_row(cat_id, cat_info)
            self.category_list.append(row)
        
        # Select first row
        first_row = self.category_list.get_row_at_index(0)
        if first_row:
            self.category_list.select_row(first_row)
        
        sidebar_scroll.set_child(self.category_list)
        sidebar_toolbar.set_content(sidebar_scroll)
        
        # Create sidebar navigation page
        sidebar_page = Adw.NavigationPage.new(sidebar_toolbar, "Categories")
        self.split_view.set_sidebar(sidebar_page)
        
        # === CONTENT ===
        content_toolbar = Adw.ToolbarView()
        
        # Content header
        content_header = Adw.HeaderBar()
        
        # Refresh button on content side
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text(_("Refresh hardware information (Ctrl+R)"))
        refresh_btn.connect("clicked", self._on_refresh_clicked)
        content_header.pack_start(refresh_btn)
        
        # Root access button for restricted data (Task #6)
        self.root_btn = Gtk.Button(icon_name="system-lock-screen-symbolic")
        self.root_btn.set_tooltip_text(_("Collect restricted data (requires admin)"))
        self.root_btn.connect("clicked", self._on_root_access_clicked)
        content_header.pack_start(self.root_btn)
        
        # Search entry in content header (centered)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_("Search..."))
        self.search_entry.set_hexpand(False)
        self.search_entry.set_width_chars(25)
        self.search_entry.connect("search-changed", self.search_handler.on_search_changed)
        content_header.set_title_widget(self.search_entry)
        
        # Menu button
        menu = Gio.Menu()
        menu.append(_("Export Report"), "app.export")
        menu.append(_("Share Online"), "app.share")
        menu.append(_("About"), "app.about")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        content_header.pack_end(menu_btn)
        
        content_toolbar.add_top_bar(content_header)
        
        # Content area with scrolling - this now holds ALL sections
        self.content_scroll = Gtk.ScrolledWindow()
        self.content_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.content_scroll.set_vexpand(True)
        
        # Content container for all sections
        self.content_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_container.set_margin_start(24)
        self.content_container.set_margin_end(24)
        self.content_container.set_margin_top(8)
        self.content_container.set_margin_bottom(24)
        self.content_container.set_spacing(24)
        
        self.content_scroll.set_child(self.content_container)
        content_toolbar.set_content(self.content_scroll)
        
        # Connect scroll signal for auto-updating sidebar (Task #1)
        vadj = self.content_scroll.get_vadjustment()
        vadj.connect("value-changed", self._on_scroll_changed)
        
        # Track section widgets for scroll-to navigation
        self.section_widgets = {}
        
        # Create content navigation page
        content_page = Adw.NavigationPage.new(content_toolbar, _("Big Hardware Info"))
        self.split_view.set_content(content_page)
        
        # Configure split view
        self.split_view.set_min_sidebar_width(200)
        self.split_view.set_max_sidebar_width(300)

    def _create_category_row(self, cat_id: str, cat_info: dict) -> Gtk.ListBoxRow:
        """Create a compact category row for the sidebar."""
        row = Gtk.ListBoxRow()
        row.cat_id = cat_id
        row.add_css_class("category-row")
        
        # Content box
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(2)
        box.set_margin_end(2)
        box.set_margin_top(1)
        box.set_margin_bottom(1)
        
        # Icon
        icon = Gtk.Image.new_from_icon_name(cat_info["icon"])
        icon.set_pixel_size(18)
        icon.add_css_class("category-icon")
        box.append(icon)
        
        # Label
        label = Gtk.Label(label=cat_info["name"])
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.add_css_class("category-label")
        box.append(label)
        
        row.set_child(box)
        return row

    def _clear_content(self):
        """Clear all content from the container."""
        child = self.content_container.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.content_container.remove(child)
            child = next_child

    def _add_header(self, title: str, icon_name: str):
        """Add a section header."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_bottom(6)
        
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(24)
        icon.add_css_class("accent")
        header_box.append(icon)
        
        label = Gtk.Label(label=title)
        label.add_css_class("title-3")
        header_box.append(label)
        
        self.content_container.append(header_box)

    def _show_loading(self):
        """Show loading indicator."""
        self._clear_content()
        
        # Create centered spinner
        spinner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        spinner_box.set_halign(Gtk.Align.CENTER)
        spinner_box.set_valign(Gtk.Align.CENTER)
        spinner_box.set_vexpand(True)
        
        spinner = Gtk.Spinner()
        spinner.set_size_request(48, 48)
        spinner.start()
        spinner_box.append(spinner)
        
        label = Gtk.Label(label="Collecting hardware information...")
        label.add_css_class("dim-label")
        spinner_box.append(label)
        
        # Progress label
        self.progress_label = Gtk.Label(label="")
        self.progress_label.add_css_class("caption")
        spinner_box.append(self.progress_label)
        
        self.content_container.append(spinner_box)

    def _start_data_collection(self):
        """Start background data collection."""
        self._show_loading()
        
        def collect_in_thread():
            def progress_callback(category, progress):
                GLib.idle_add(self._update_progress, category, progress)
            
            data = self.collector.collect_all(progress_callback)
            GLib.idle_add(self._on_data_collected, data)
        
        thread = threading.Thread(target=collect_in_thread, daemon=True)
        thread.start()
        return False

    def _update_progress(self, category: str, progress: float):
        """Update progress indicator."""
        if hasattr(self, "progress_label") and self.progress_label:
            self.progress_label.set_text(f"Loading {category}... ({int(progress * 100)}%)")

    def _on_data_collected(self, data: dict):
        """Handle collected data."""
        self.hardware_data = data
        logger.info("Hardware data collection complete")
        self._update_content()

    def _refresh_data(self):
        """Refresh hardware data."""
        # Save scroll position to restore after refresh
        if hasattr(self, 'content_scroll') and self.content_scroll:
            vadj = self.content_scroll.get_vadjustment()
            self._saved_scroll_position = vadj.get_value()
        else:
            self._saved_scroll_position = None
        
        self.collector.inxi_parser.clear_cache()
        self._start_data_collection()

    def _on_refresh_clicked(self, button):
        """Handle refresh button click."""
        self._refresh_data()

    def _on_root_access_clicked(self, button):
        """Handle root access button click - collect restricted data with pkexec."""
        import subprocess
        import shutil
        
        # Check if pkexec is available
        if not shutil.which("pkexec"):
            dialog = Adw.MessageDialog.new(
                self,
                "Admin Access Unavailable",
                "The pkexec command is not available on this system.",
            )
            dialog.add_response("ok", "OK")
            dialog.present()
            return
        
        # Show spinner while collecting
        button.set_sensitive(False)
        button.set_icon_name("emblem-synchronizing-symbolic")
        
        def collect_root_data():
            """Collect data that requires root privileges.
            
            Uses a single pkexec call with inxi -Fxxxza to collect all data at once,
            so the user only needs to enter the password once.
            """
            root_data = {}
            
            # Single pkexec call to collect all root-required data at once
            # -F = Full output, -xxx = extra extra extra details, -z = privacy filter
            # -a = even more info (all advanced options)
            # This collects: GPU, SMART, sensors, unmounted partitions, and more
            try:
                result = subprocess.run(
                    ["pkexec", "inxi", "-Fxxxza", "--output", "json", "--output-file", "print"],
                    capture_output=True,
                    text=True,
                    timeout=120  # Longer timeout for full collection
                )
                if result.returncode == 0:
                    import json as json_module
                    try:
                        parsed = json_module.loads(result.stdout)
                        # Store the complete data
                        root_data["full_inxi"] = result.stdout
                        
                        # Extract specific sections for backward compatibility
                        for section in parsed:
                            for key, value in section.items():
                                clean_key = key.split("#")[-1] if "#" in key else key
                                if "Graphics" in clean_key:
                                    root_data["gpu_detailed"] = json_module.dumps([section])
                                elif "Drives" in clean_key:
                                    root_data["disk_smart"] = json_module.dumps([section])
                                elif "Sensors" in clean_key:
                                    root_data["sensors_detailed"] = json_module.dumps([section])
                                elif "Unmounted" in clean_key:
                                    root_data["unmounted"] = json_module.dumps([section])
                    except json_module.JSONDecodeError:
                        # Store raw if parsing fails
                        root_data["full_inxi"] = result.stdout
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass
            
            return root_data
        
        def on_complete(root_data):
            """Handle completion of root data collection."""
            button.set_sensitive(True)
            button.set_icon_name("security-high-symbolic")  # Changed icon to show elevated
            
            # Store root data and refresh display
            if root_data:
                # Merge directly into main hardware_data using new model structure
                mapping = {
                    "gpu_detailed": "advanced_gpu",
                    "disk_smart": "smart_data",
                    "sensors_detailed": "advanced_sensors",
                    "unmounted": "unmounted",
                    "full_inxi": "raw_inxi"
                }

                for old_key, new_key in mapping.items():
                    if old_key in root_data:
                        self.hardware_data[new_key] = root_data[old_key]
                
                # Mark as root collected
                self.hardware_data["root_collected"] = True
                
                self._update_content()
                
                # Show success toast
                toast = Adw.Toast.new("Admin data collected successfully")
                toast.set_timeout(2)
                self.toast_overlay.add_toast(toast)
            else:
                # Show error toast
                toast = Adw.Toast.new("Failed to collect admin data")
                toast.set_timeout(3)
                self.toast_overlay.add_toast(toast)
        
        # Run in thread to avoid blocking UI
        import threading
        def thread_func():
            root_data = collect_root_data()
            GLib.idle_add(on_complete, root_data)
        
        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()

    def _on_category_selected(self, listbox, row):
        """Handle category selection - scroll to section."""
        if row is None:
            return
        
        # Update active category CSS class
        current = self.category_list.get_first_child()
        while current:
            current.remove_css_class("active-category")
            current = current.get_next_sibling()
        
        row.add_css_class("active-category")
        self.current_category = row.cat_id
        
        # Scroll to the section widget if it exists
        if row.cat_id in self.section_widgets:
            section = self.section_widgets[row.cat_id]
            # Use scroll_to_child to smoothly scroll to the section
            if hasattr(self, 'content_scroll') and self.content_scroll:
                # Get the vertical adjustment
                vadj = self.content_scroll.get_vadjustment()
                if vadj:
                    # Mark as programmatic scroll to avoid sidebar update loop
                    self._programmatic_scroll = True
                    
                    # Calculate the y position of the section
                    def scroll_to_section():
                        if section.get_mapped():
                            # Get allocation of section
                            allocation = section.get_allocation()
                            # Scroll to position with some padding
                            y_pos = max(0, allocation.y - 8)
                            vadj.set_value(y_pos)
                        # Reset programmatic scroll flag after animation
                        GLib.timeout_add(300, self._reset_programmatic_scroll)
                    # Schedule the scroll after layout is complete
                    GLib.idle_add(scroll_to_section)
    
    def _reset_programmatic_scroll(self):
        """Reset the programmatic scroll flag."""
        self._programmatic_scroll = False
        return False  # Don't repeat
    
    def _on_scroll_changed(self, _adjustment):
        """Handle scroll changes.
        
        Note: Automatic category selection based on scroll is DISABLED.
        Users should click on sidebar categories to navigate.
        This provides more predictable behavior and avoids unexpected jumps.
        """
        # Scroll tracking disabled - categories only change on sidebar click
        pass
    
    def _select_category_without_scroll(self, cat_id: str):
        """Select a category in the sidebar without triggering scroll."""
        self._scroll_tracking_enabled = False
        
        # Find and select the row
        row = self.category_list.get_first_child()
        while row:
            if hasattr(row, 'cat_id') and row.cat_id == cat_id:
                # Update CSS classes
                current = self.category_list.get_first_child()
                while current:
                    current.remove_css_class("active-category")
                    current = current.get_next_sibling()
                row.add_css_class("active-category")
                
                # Select in list (this triggers row-selected but we blocked scroll)
                self.category_list.select_row(row)
                self.current_category = cat_id
                break
            row = row.get_next_sibling()
        
        # Re-enable scroll tracking after a short delay
        GLib.timeout_add(50, self._enable_scroll_tracking)
    
    def _enable_scroll_tracking(self):
        """Re-enable scroll tracking."""
        self._scroll_tracking_enabled = True
        return False  # Don't repeat

    def _update_content(self):
        """Update content area showing ALL categories in a single scroll view."""
        if not hasattr(self, "content_container") or not self.content_container:
            return
            
        self._clear_content()
        self.section_widgets = {}
        
        if not self.hardware_data:
            self._show_loading()
            return
        
        # Show ALL sections in order - each creates a section with header
        self._add_section("summary", self._show_summary)
        self._add_section("cpu", self._show_cpu)
        self._add_section("gpu", self._show_gpu)
        self._add_section("webcam", self._show_webcams)
        self._add_section("machine", self._show_machine)
        self._add_section("memory", self._show_memory)
        self._add_section("audio", self._show_audio)
        self._add_section("network", self._show_network)
        self._add_section("disk", self._show_disk)
        self._add_section("battery", self._show_battery)
        self._add_section("bluetooth", self._show_bluetooth)
        self._add_section("usb", self._show_usb)
        self._add_section("pci", self._show_pci)
        self._add_section("system", self._show_system)
        self._add_section("printer", self._show_printers)  # After System
        self._add_section("sensors", self._show_sensors)
        self._add_section("more_info", self._show_more_info)
        
        # Restore scroll position if saved (after refresh)
        if hasattr(self, '_saved_scroll_position') and self._saved_scroll_position is not None:
            def restore_scroll():
                if hasattr(self, 'content_scroll') and self.content_scroll:
                    vadj = self.content_scroll.get_vadjustment()
                    vadj.set_value(self._saved_scroll_position)
                self._saved_scroll_position = None
                return False
            # Delay restoration to allow content to render
            GLib.timeout_add(50, restore_scroll)

    def _add_section(self, cat_id: str, content_func):
        """Add a section with header to the content container."""
        cat = CATEGORIES.get(cat_id, {})
        
        # Create section container
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        section.cat_id = cat_id
        
        # Skip header and separator for summary section
        if cat_id != "summary":
            # Section header - clickable/visible
            header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            header_box.set_margin_top(16)
            header_box.set_margin_bottom(8)
            
            icon = Gtk.Image.new_from_icon_name(cat.get("icon", "computer-symbolic"))
            icon.set_pixel_size(28)
            icon.add_css_class("accent")
            header_box.append(icon)
            
            label = Gtk.Label(label=cat.get("name", cat_id.title()))
            label.add_css_class("title-2")
            label.set_halign(Gtk.Align.START)
            label.set_hexpand(True)
            header_box.append(label)
            
            # Copy button for this category
            if cat_id != "more_info":  # Skip for More Info section
                copy_btn = self._create_copy_button(cat_id)
                header_box.append(copy_btn)
            
            section.append(header_box)
            
            # Add separator
            separator = Gtk.Separator()
            separator.set_margin_bottom(8)
            section.append(separator)
        
        # Register section for scroll-to navigation
        self.section_widgets[cat_id] = section
        self.content_container.append(section)
        
        # Store current container and temporarily use the section
        original_container = self.content_container
        self.content_container = section
        
        # Call the content function (which appends to self.content_container)
        try:
            content_func()
        finally:
            # Restore original container
            self.content_container = original_container

    # ===============================
    # Category Display Methods
    # ===============================

    def _show_summary(self):
        """Show summary view - delegates to SummaryRenderer."""
        SummaryRenderer(self).render()

    def _show_cpu(self):
        """
        Show CPU information using component-based CpuSectionView.
        
        Delegates rendering to the CpuSectionView component for cleaner
        separation of concerns and maintainability.
        """
        cpu_data = self.hardware_data.get("cpu", {})
        
        # Create and render the CPU view component
        cpu_view = CpuSectionView()
        cpu_view.render(cpu_data)
        
        # Add the view to the content container
        self.content_container.append(cpu_view)

    def _show_gpu(self):
        """
        Show GPU information using component-based GpuSectionView.
        
        Delegates rendering to the GpuSectionView component for cleaner
        separation of concerns and maintainability.
        """
        from app.ui.views import GpuSectionView
        
        gpu_data = self.hardware_data.get("gpu", {})
        
        # Create and render the GPU view component
        gpu_view = GpuSectionView(open_url_callback=self._open_url_with_toast)
        gpu_view.render(gpu_data)
        
        # Add the view to the content container
        self.content_container.append(gpu_view)
    
    def _show_webcams(self):
        """Delegates to WebcamsRenderer."""
        WebcamsRenderer(self).render()


    def _show_memory(self):
        """
        Show memory information using component-based MemorySectionView.
        
        Delegates rendering to the MemorySectionView component for cleaner
        separation of concerns and maintainability.
        """
        memory_data = self.hardware_data.get("memory", {})
        disk_data = self.hardware_data.get("disk", {})
        
        # Create and configure the Memory view component
        memory_view = MemorySectionView()
        memory_view.set_disk_data(disk_data)  # Provide disk data for swap info
        memory_view.render(memory_data)
        
        # Add the view to the content container
        self.content_container.append(memory_view)

    def _show_machine(self):
        """Delegates to MachineRenderer."""
        MachineRenderer(self).render()

    def _show_audio(self):
        """
        Show audio information using component-based AudioSectionView.
        
        Delegates rendering to the AudioSectionView component for cleaner
        separation of concerns and maintainability.
        """
        from app.ui.views import AudioSectionView
        
        audio_data = self.hardware_data.get("audio", {})
        
        # Create and render the Audio view component
        audio_view = AudioSectionView(open_url_callback=self._open_url_with_toast)
        audio_view.render(audio_data)
        
        # Add the view to the content container
        self.content_container.append(audio_view)
        
        if audio_data.get("raw"):
            self._add_raw_expander(_("Full Output"), audio_data["raw"])

    def _show_network(self):
        """
        Show network information using component-based NetworkSectionView.
        
        Delegates rendering to the NetworkSectionView component for cleaner
        separation of concerns and maintainability.
        """
        from app.ui.views import NetworkSectionView
        
        network_data = self.hardware_data.get("network", {})
        
        # Create and render the Network view component
        network_view = NetworkSectionView(open_url_callback=self._open_url_with_toast)
        network_view.render(network_data)
        
        # Add the view to the content container
        self.content_container.append(network_view)
        
        if network_data.get("raw"):
            self._add_raw_expander(_("Full Output"), network_data["raw"])

    def _show_battery(self):
        """Delegates to BatteryRenderer."""
        BatteryRenderer(self).render()

    def _show_bluetooth(self):
        """Delegates to BluetoothRenderer."""
        BluetoothRenderer(self).render()

    def _show_usb(self):
        """Delegates to UsbRenderer."""
        UsbRenderer(self).render()

    def _show_sensors(self):
        """Delegates to SensorsRenderer."""
        SensorsRenderer(self).render()


    def _show_disk(self):
        """
        Show disk/storage information using component-based DiskSectionView.
        
        Delegates rendering to the DiskSectionView component for cleaner
        separation of concerns and maintainability.
        """
        from app.ui.views import DiskSectionView
        
        disk_data = self.hardware_data.get("disk", {})
        
        # Create and render the Disk view component
        disk_view = DiskSectionView()
        disk_view.render(disk_data)
        
        # Add the view to the content container
        self.content_container.append(disk_view)
        
        if disk_data.get("raw"):
            self._add_raw_expander("Full Output", disk_data["raw"])

    def _show_pci(self):
        """Delegates to PciRenderer."""
        PciRenderer(self).render()


    def _show_system(self):
        """Delegates to SystemRenderer."""
        SystemRenderer(self).render()

    def _show_printers(self):
        """Delegates to PrintersRenderer."""
        PrintersRenderer(self).render()


    def _show_more_info(self):
        """Delegates to MoreInfoRenderer."""
        MoreInfoRenderer(self).render()

    # ===============================
    # Helper Methods
    # ===============================

    def _create_info_row(self, label: str, value: str) -> Gtk.Box:
        """Create an info row with label and value."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("info-row")
        
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("dim-label")
        label_widget.set_halign(Gtk.Align.START)
        label_widget.set_width_chars(15)
        label_widget.set_xalign(0)
        row.append(label_widget)
        
        value_widget = Gtk.Label(label=value)
        value_widget.set_halign(Gtk.Align.END)
        value_widget.set_hexpand(True)
        value_widget.set_wrap(True)
        value_widget.set_xalign(1)
        value_widget.set_selectable(True)
        row.append(value_widget)
        
        return row

    def _open_url_with_toast(self, url: str):
        """Open URL in browser and show a toast notification."""
        self._open_url(url)
        
        # Show toast
        if hasattr(self, 'toast_overlay'):
            toast = Adw.Toast.new(_("Opening in browser..."))
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
    
    def _create_copy_button(self, category_id: str) -> Gtk.Button:
        """Create a copy button for category data."""
        btn = Gtk.Button()
        btn.set_icon_name("edit-copy-symbolic")
        btn.add_css_class("flat")
        btn.set_tooltip_text(_("Copy category data to clipboard"))
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda b, cid=category_id: self._copy_category_data(cid))
        return btn
    
    def _copy_category_data(self, category_id: str):
        """Copy category data to clipboard as human-readable text."""
        # Get data for this category
        data = self.hardware_data.get(category_id, {})
        
        if not data:
            if hasattr(self, 'toast_overlay'):
                toast = Adw.Toast.new(_("No data to copy"))
                toast.set_timeout(2)
                self.toast_overlay.add_toast(toast)
            return
        
        # Format data as readable text
        text = self._format_data_as_text(data, category_id)
        
        # Copy to clipboard
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
        
        # Show toast
        if hasattr(self, 'toast_overlay'):
            toast = Adw.Toast.new(_("Data copied to clipboard"))
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
    
    def _format_data_as_text(self, data: dict, title: str = "") -> str:
        """Format dictionary data as human-readable plain text."""
        lines = []
        
        if title:
            # Get category name
            cat_name = CATEGORIES.get(title, {}).get("name", title.title())
            lines.append(f"=== {cat_name} ===")
            lines.append("")
        
        def format_value(key, value, indent: int = 0) -> list:
            """Recursively format key-value pairs."""
            result = []
            prefix = "  " * indent
            
            # Clean up key name (handle non-string keys like integers)
            clean_key = str(key).replace("_", " ").title()
            
            if isinstance(value, dict):
                if clean_key and value:
                    result.append(f"{prefix}{clean_key}:")
                for k, v in value.items():
                    result.extend(format_value(k, v, indent + 1))
            elif isinstance(value, list):
                if value:
                    result.append(f"{prefix}{clean_key}:")
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            result.append(f"{prefix}  [{i + 1}]")
                            for k, v in item.items():
                                result.extend(format_value(k, v, indent + 2))
                        else:
                            result.append(f"{prefix}  - {item}")
            elif value not in (None, "", "N/A", "Unknown"):
                result.append(f"{prefix}{clean_key}: {value}")
            
            return result
        
        for key, value in data.items():
            lines.extend(format_value(key, value))
        
        return "\n".join(lines)
    
    def _copy_text_to_clipboard(self, text: str, title: str = ""):
        """Copy raw text to clipboard with toast feedback."""
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
        
        if hasattr(self, 'toast_overlay'):
            msg = _("Copied: {}").format(title) if title else _("Copied to clipboard")
            toast = Adw.Toast.new(msg)
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)

    def _add_raw_text(self, text: str):
        """Add raw preformatted text."""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(400)
        scroll.set_propagate_natural_height(True)
        
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.add_css_class("raw-text")
        text_view.get_buffer().set_text(text)
        
        scroll.set_child(text_view)
        self.content_container.append(scroll)

    def _add_raw_expander(self, title: str, text: str, expanded: bool = False):
        """Add expandable raw text section."""
        expander = Gtk.Expander(label=title)
        expander.set_expanded(expanded)
        expander.add_css_class("card")
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(300)
        scroll.set_propagate_natural_height(True)
        
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_margin_top(8)
        text_view.get_buffer().set_text(text)
        
        scroll.set_child(text_view)
        expander.set_child(scroll)
        
        self.content_container.append(expander)

    def _add_terminal_block(self, title: str, text: str, max_lines: int = 15):
        """Add a terminal-style block with limited visible lines (Task #5)."""
        # Container card with terminal styling
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class("terminal-card")
        
        # Title bar with copy button
        title_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_bar.add_css_class("terminal-title")
        
        title_label = Gtk.Label(label=title)
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        title_bar.append(title_label)
        
        # Copy button for the block content
        copy_btn = Gtk.Button()
        copy_btn.set_icon_name("edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.set_tooltip_text(_("Copy content to clipboard"))
        copy_btn.set_valign(Gtk.Align.CENTER)
        copy_btn.connect("clicked", lambda b, t=text, n=title: self._copy_text_to_clipboard(t, n))
        title_bar.append(copy_btn)
        
        card.append(title_bar)
        
        # Limit content to max_lines
        lines = text.split('\n')
        total_lines = len(lines)
        visible_content = '\n'.join(lines[:max_lines])
        has_more = total_lines > max_lines
        
        # Content scroll with limited height (15 lines at ~22px per line = 330px)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(330)  # Minimum height to show 15 lines
        scroll.set_max_content_height(330)  # Maximum height to show 15 lines
        scroll.set_propagate_natural_height(False)  # Don't shrink to content
        
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.add_css_class("terminal-text")
        
        # Apply syntax highlighting
        buffer = text_view.get_buffer()
        self._apply_terminal_highlighting(buffer, visible_content)
        
        scroll.set_child(text_view)
        card.append(scroll)
        
        # Show indicator if truncated, with expander to show all
        if has_more:
            expander_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            expander_row.set_margin_start(12)
            expander_row.set_margin_end(12)
            expander_row.set_margin_top(4)
            expander_row.set_margin_bottom(8)
            
            more_label = Gtk.Label(label=f"... {total_lines - max_lines} more lines hidden")
            more_label.add_css_class("dim-label")
            more_label.add_css_class("caption")
            more_label.set_halign(Gtk.Align.START)
            more_label.set_hexpand(True)
            expander_row.append(more_label)
            
            # Toggle button to show all
            toggle_btn = Gtk.ToggleButton(label="Show all")
            toggle_btn.add_css_class("flat")
            toggle_btn.add_css_class("caption")
            toggle_btn.connect("toggled", self._on_terminal_toggle, text_view, text, visible_content, more_label, total_lines, max_lines)
            expander_row.append(toggle_btn)
            
            card.append(expander_row)
        
        self.content_container.append(card)

    def _apply_terminal_highlighting(self, buffer: Gtk.TextBuffer, text: str):
        """Apply syntax highlighting to terminal text.
        
        Delegates to the highlighting module for specialized highlighting.
        """
        from app.ui import highlighting
        highlighting.apply_highlighting(buffer, text)

    def _on_terminal_toggle(self, button, text_view, full_text, short_text, label, total, max_lines):
        """Handle terminal content expand/collapse."""
        buffer = text_view.get_buffer()
        if button.get_active():
            self._apply_terminal_highlighting(buffer, full_text)
            button.set_label("Show less")
            label.set_text(f"Showing all {total} lines")
        else:
            self._apply_terminal_highlighting(buffer, short_text)
            button.set_label("Show all")
            label.set_text(f"... {total - max_lines} more lines hidden")

    def _show_no_data(self, message: str):
        """Show no data message."""
        label = Gtk.Label(label=message)
        label.add_css_class("dim-label")
        label.set_margin_top(32)
        label.set_margin_bottom(32)
        self.content_container.append(label)

    def _create_superuser_required_widget(self, field_name: str) -> Gtk.Widget:
        """Create a clickable widget indicating superuser privileges are required.
        
        Creates a button-style widget that users can click to request elevated
        privileges and reload the hardware information.
        
        Args:
            field_name: The name of the field requiring superuser access
            
        Returns:
            A GTK widget (clickable button) indicating superuser requirement
        """
        button = Gtk.Button()
        button.add_css_class("flat")
        button.add_css_class("superuser-required")
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Lock icon
        icon = Gtk.Image.new_from_icon_name("system-lock-screen-symbolic")
        icon.set_pixel_size(14)
        icon.add_css_class("warning")
        box.append(icon)
        
        # Text
        label = Gtk.Label(label="Requires Administrator")
        label.add_css_class("warning")
        label.add_css_class("caption")
        box.append(label)
        
        button.set_child(box)
        button.set_tooltip_text(f"Click to run as administrator and show {field_name}")
        button.connect("clicked", self._on_superuser_required_clicked)
        
        return button
    
    def _on_superuser_required_clicked(self, button: Gtk.Button):
        """Handle click on superuser required widget.
        
        Triggers a reload of hardware information with elevated privileges.
        """
        # Request elevated privileges and reload
        self._request_elevated_reload()
    
    def _request_elevated_reload(self):
        """Request elevated privileges and reload hardware information.
        
        Uses pkexec to run the data collection with root privileges,
        then reloads the current view with the new data.
        """
        import subprocess
        import json
        import os
        
        # Show a loading indicator
        dialog = Adw.AlertDialog()
        dialog.set_heading("Administrator Access Required")
        dialog.set_body("Some hardware information requires administrator privileges to access. Do you want to reload with elevated access?")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("reload", "Reload as Admin")
        dialog.set_response_appearance("reload", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("reload")
        dialog.set_close_response("cancel")
        
        def on_response(dialog, response):
            if response == "reload":
                self._do_elevated_reload()
        
        dialog.connect("response", on_response)
        dialog.present(self)
    
    def _do_elevated_reload(self):
        """Perform the actual elevated reload of hardware data."""
        import subprocess
        import threading
        
        def run_elevated():
            try:
                # Run inxi with pkexec for elevated privileges
                cmd = ["pkexec", "inxi", "-Fxxxz", "--output-type", "json"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    # Parse the new data
                    import json
                    new_data = json.loads(result.stdout)
                    
                    # Update in main thread
                    GLib.idle_add(self._update_with_elevated_data, new_data)
                else:
                    GLib.idle_add(self._show_elevated_error, "Failed to get elevated data")
            except subprocess.TimeoutExpired:
                GLib.idle_add(self._show_elevated_error, "Operation timed out")
            except Exception as e:
                GLib.idle_add(self._show_elevated_error, str(e))
        
        # Run in background thread
        thread = threading.Thread(target=run_elevated, daemon=True)
        thread.start()
    
    def _update_with_elevated_data(self, new_data):
        """Update the UI with newly collected elevated data.
        
        Args:
            new_data: The new hardware data collected with root privileges
        """
        # Re-parse and update the hardware data
        from app.collectors.inxi_parser import InxiParser
        parser = InxiParser()
        
        # Update the relevant sections
        if isinstance(new_data, list):
            for section in new_data:
                if isinstance(section, dict):
                    parsed = parser._parse_section(section)
                    if parsed:
                        key, value = parsed
                        self.hardware_data[key] = value
        
        # Refresh the current view
        self._show_current_category()
        
        # Show success toast
        toast = Adw.Toast.new("Hardware information updated with administrator access")
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)
    
    def _show_elevated_error(self, error_message: str):
        """Show an error message when elevated reload fails.
        
        Args:
            error_message: The error message to display
        """
        toast = Adw.Toast.new(f"Could not get elevated access: {error_message}")
        toast.set_timeout(5)
        self.toast_overlay.add_toast(toast)
    
    def _show_current_category(self):
        """Refresh and show the currently selected category."""
        # Get current selection and re-show it
        selected = self.sidebar_list.get_selected_row()
        if selected:
            self._on_sidebar_row_selected(self.sidebar_list, selected)

    def _open_url(self, url: str):
        """Open URL in default browser."""
        import subprocess
        subprocess.Popen(["xdg-open", url], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)

    # ===============================
    # Export & Share
    # ===============================

    def _on_export_clicked(self, button):
        """Handle export button click - shows privacy options first."""
        dialogs.show_privacy_export_dialog(self, is_upload=False)

    def _on_share_clicked(self, button):
        """Handle share button click - shows privacy options first."""
        dialogs.show_privacy_export_dialog(self, is_upload=True)

    # ===============================
    # Window State Management
    # ===============================

    def _on_window_size_changed(self, window, _param):
        """Handle window size changes."""
        if not self.is_maximized():
            if self._size_save_timeout_id:
                GLib.source_remove(self._size_save_timeout_id)
            self._size_save_timeout_id = GLib.timeout_add(500, self._save_window_size)

    def _on_window_state_changed(self, window, _param):
        """Handle window state changes."""
        is_maximized = self.is_maximized()
        if self.config:
            self.config.set("window_maximized", is_maximized)

    def _save_window_size(self):
        """Save window size to config."""
        if self.config:
            self.config.set("window_width", self.get_width())
            self.config.set("window_height", self.get_height())
        self._size_save_timeout_id = None
        return False

    def _on_close_request(self, window):
        """Handle window close."""
        if not self.is_maximized():
            self._save_window_size()
        return False
