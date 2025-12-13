"""Search functionality for the hardware info application.

This module handles global search across all hardware categories
and displays unified search results.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib

from big_hardware_info.utils.i18n import _
from big_hardware_info.ui.cards import create_info_card


class SearchHandler:
    """Handles search functionality for the main window."""
    
    def __init__(self, window):
        """Initialize with a reference to the main window.
        
        Args:
            window: MainWindow instance
        """
        self.window = window
        self._search_timeout_id = None
    
    @property
    def hardware_data(self):
        return self.window.hardware_data
    
    @property
    def content_container(self):
        return self.window.content_container
    
    def on_search_changed(self, entry):
        """Handle search entry changes with debouncing."""
        if self._search_timeout_id:
            GLib.source_remove(self._search_timeout_id)
            self._search_timeout_id = None
        
        # Schedule debounced search (200ms delay)
        self._search_timeout_id = GLib.timeout_add(200, lambda: self._perform_search(entry))
    
    def _perform_search(self, entry):
        """Perform the actual search after debounce delay."""
        self._search_timeout_id = None
        search_text = entry.get_text().lower().strip()
        self.window.search_filter = search_text
        
        if search_text:
            self.show_global_results(search_text)
        else:
            self.window._update_content()
        
        return False
    
    def show_global_results(self, search_text: str):
        """Search across all hardware data and show unified results."""
        if not self.hardware_data:
            return
        
        self.window._clear_content()
        self.window._add_header(f'{_("Search Results for")} "{search_text}"', "edit-find-symbolic")
        
        results_found = False
        
        # Define search categories
        categories = [
            ("cpu", _("Processor"), "cpu-symbolic", self._show_cpu_cards),
            ("gpu", _("Graphics"), "video-display-symbolic", self._show_gpu_cards),
            ("memory", _("Memory"), "memory-symbolic", self._show_memory_cards),
            ("machine", _("Motherboard"), "computer-symbolic", self._show_machine_cards),
            ("audio", _("Audio"), "audio-card-symbolic", self._show_audio_cards),
            ("network", _("Network"), "network-wired-symbolic", self._show_network_cards),
            ("disk", _("Storage"), "drive-harddisk-symbolic", self._show_disk_cards),
            ("pci", _("PCI Devices"), "pci-symbolic", self._show_pci_cards),
            ("usb", _("USB Devices"), "usb-symbolic", self._show_usb_cards),
        ]
        
        for data_key, title, icon, show_func in categories:
            data = self.hardware_data.get(data_key, {})
            if self._matches_search(data, search_text):
                self._add_section_header(title, icon)
                show_func(search_text)
                results_found = True
        
        # Special case for system (has two data sources)
        system_data = self.hardware_data.get("system", {})
        sys_info = self.hardware_data.get("system_info", {})
        if self._matches_search(system_data, search_text) or self._matches_search(sys_info, search_text):
            self._add_section_header(_("System"), "computer-symbolic")
            self._show_system_cards(search_text)
            results_found = True
        
        if not results_found:
            self._show_no_results()
    
    def _matches_search(self, data: dict, search_text: str) -> bool:
        """Check if any value in data matches the search text."""
        if not data:
            return False
        
        def search_recursive(obj):
            if isinstance(obj, dict):
                return any(search_recursive(v) for v in obj.values())
            elif isinstance(obj, list):
                return any(search_recursive(item) for item in obj)
            elif isinstance(obj, str):
                return search_text in obj.lower()
            elif obj is not None:
                return search_text in str(obj).lower()
            return False
        
        return search_recursive(data)
    
    def _add_section_header(self, title: str, icon_name: str):
        """Add a section header for search results."""
        section_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        section_box.set_margin_top(16)
        section_box.set_margin_bottom(8)
        
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(20)
        icon.add_css_class("accent")
        section_box.append(icon)
        
        label = Gtk.Label(label=title)
        label.add_css_class("title-4")
        label.set_halign(Gtk.Align.START)
        section_box.append(label)
        
        self.content_container.append(section_box)
    
    def _create_card(self, title: str, subtitle: str, icon: str, props=None):
        """Create an info card using the cards module."""
        return create_info_card(title, subtitle, icon, props)
    
    def _show_cpu_cards(self, search_text: str):
        """Show CPU info cards filtered by search."""
        cpu_data = self.hardware_data.get("cpu", {})
        model = cpu_data.get("model", "Unknown")
        if search_text in model.lower() or search_text in "cpu processor":
            card = self._create_card(
                model, 
                f"{cpu_data.get('cores', 'N/A')} cores, {cpu_data.get('threads', 'N/A')} threads",
                "cpu-symbolic"
            )
            self.content_container.append(card)
    
    def _show_gpu_cards(self, search_text: str):
        """Show GPU info cards filtered by search."""
        gpu_data = self.hardware_data.get("gpu", {})
        for device in gpu_data.get("devices", []):
            name = device.get("name", "Unknown")
            driver = device.get("driver", "")
            if search_text in name.lower() or search_text in driver.lower() or search_text in "gpu video graphics nvidia amd intel":
                card = self._create_card(name, f"Driver: {driver}", "video-display-symbolic")
                self.content_container.append(card)
    
    def _show_memory_cards(self, search_text: str):
        """Show memory info cards filtered by search."""
        memory_data = self.hardware_data.get("memory", {})
        
        total = memory_data.get("total", "Unknown")
        if search_text in str(total).lower() or search_text in "memory ram":
            card = self._create_card(
                f"{_('System Memory')}: {total}",
                f"{_('Used')}: {memory_data.get('used', 'N/A')}",
                "memory-symbolic"
            )
            self.content_container.append(card)
        
        # Search in memory modules
        for module in memory_data.get("modules", []):
            if isinstance(module, dict):
                size = module.get("size", "")
                speed = module.get("speed", "")
                manufacturer = module.get("manufacturer", "")
                part_number = module.get("part_number", "")
                module_type = module.get("type", "")
                slot = module.get("slot", "")
                
                module_text = f"{size} {speed} {manufacturer} {part_number} {module_type} {slot}".lower()
                if search_text in module_text:
                    title = f"{manufacturer} {part_number}".strip() or f"{size} {module_type}"
                    subtitle = f"{size} @ {speed}" if speed else size
                    
                    props = []
                    if slot:
                        props.append((_("Slot"), slot))
                    if module_type:
                        props.append((_("Type"), module_type))
                    if manufacturer:
                        props.append((_("Manufacturer"), manufacturer))
                    if part_number:
                        props.append((_("Part Number"), part_number))
                    
                    card = self._create_card(title, subtitle, "memory-symbolic", props)
                    self.content_container.append(card)
    
    def _show_machine_cards(self, search_text: str):
        """Show machine/motherboard cards filtered by search."""
        machine_data = self.hardware_data.get("machine", {})
        
        sys_vendor = machine_data.get("system", "")
        sys_product = machine_data.get("product", "")
        mobo_vendor = machine_data.get("mobo_vendor", "")
        mobo_model = machine_data.get("mobo_model", "")
        
        if isinstance(sys_vendor, str) and (search_text in sys_vendor.lower() or search_text in sys_product.lower()):
            card = self._create_card(
                f"{sys_vendor} {sys_product}".strip() or _("System"),
                _("System Information"),
                "computer-symbolic"
            )
            self.content_container.append(card)
        
        if isinstance(mobo_vendor, str) and (search_text in mobo_vendor.lower() or search_text in mobo_model.lower() or search_text in "motherboard placa"):
            card = self._create_card(
                f"{mobo_vendor} {mobo_model}".strip() or _("Motherboard"),
                _("Motherboard"),
                "computer-symbolic"
            )
            self.content_container.append(card)
    
    def _show_audio_cards(self, search_text: str):
        """Show audio cards filtered by search."""
        audio_data = self.hardware_data.get("audio", {})
        for device in audio_data.get("devices", []):
            name = device.get("name", "Unknown")
            driver = device.get("driver", "")
            if search_text in name.lower() or search_text in driver.lower() or search_text in "audio sound":
                card = self._create_card(name, f"Driver: {driver}", "audio-card-symbolic")
                self.content_container.append(card)
    
    def _show_network_cards(self, search_text: str):
        """Show network cards filtered by search."""
        network_data = self.hardware_data.get("network", {})
        for device in network_data.get("devices", []):
            name = device.get("name", "Unknown")
            driver = device.get("driver", "")
            interface = device.get("interface", "")
            if search_text in name.lower() or search_text in driver.lower() or search_text in interface.lower() or search_text in "network ethernet wifi":
                card = self._create_card(name, f"Interface: {interface}", "network-wired-symbolic")
                self.content_container.append(card)
    
    def _show_disk_cards(self, search_text: str):
        """Show disk/storage cards filtered by search."""
        disk_data = self.hardware_data.get("disk", {})
        for drive in disk_data.get("drives", []):
            model = drive.get("model", "Unknown")
            size = drive.get("size", "")
            if search_text in model.lower() or search_text in "disk ssd nvme hdd storage":
                card = self._create_card(model, f"Size: {size}", "drive-harddisk-symbolic")
                self.content_container.append(card)
    
    def _show_pci_cards(self, search_text: str):
        """Show PCI cards filtered by search."""
        pci_data = self.hardware_data.get("pci", {})
        for device in pci_data.get("devices", []):
            name = device.get("name", "Unknown")
            driver = device.get("driver", "")
            if search_text in name.lower() or search_text in driver.lower():
                card = self._create_card(name, f"Driver: {driver}", "pci-symbolic")
                self.content_container.append(card)
    
    def _show_usb_cards(self, search_text: str):
        """Show USB cards filtered by search."""
        usb_data = self.hardware_data.get("usb", {})
        for device in usb_data.get("devices", []):
            name = device.get("name", "Unknown")
            vendor = device.get("vendor", "")
            if search_text in name.lower() or search_text in vendor.lower() or search_text in "usb":
                card = self._create_card(name, f"Vendor: {vendor}", "usb-symbolic")
                self.content_container.append(card)
    
    def _show_system_cards(self, search_text: str):
        """Show system info cards filtered by search."""
        system_data = self.hardware_data.get("system", {})
        sys_info = self.hardware_data.get("system_info", {})
        
        distro = system_data.get("distro", "")
        kernel = sys_info.get("kernel", "")
        
        if search_text in distro.lower() or search_text in kernel.lower() or search_text in "system linux kernel":
            props = []
            if distro:
                props.append((_("Distribution"), distro))
            if kernel:
                props.append((_("Kernel"), kernel))
            
            card = self._create_card(
                distro or _("System Information"),
                f"Kernel: {kernel}",
                "computer-symbolic",
                props
            )
            self.content_container.append(card)
    
    def _show_no_results(self):
        """Show a message when no search results are found."""
        child = self.content_container.get_first_child()
        while child:
            if getattr(child, 'is_no_results', False):
                child.set_visible(True)
                return
            child = child.get_next_sibling()
        
        no_results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        no_results.set_halign(Gtk.Align.CENTER)
        no_results.set_valign(Gtk.Align.CENTER)
        no_results.set_vexpand(True)
        no_results.is_no_results = True
        
        icon = Gtk.Image.new_from_icon_name("edit-find-symbolic")
        icon.set_pixel_size(64)
        icon.add_css_class("dim-label")
        no_results.append(icon)
        
        label = Gtk.Label(label=_("No results found"))
        label.add_css_class("title-2")
        no_results.append(label)
        
        sublabel = Gtk.Label(label=_("Try a different search term"))
        sublabel.add_css_class("dim-label")
        no_results.append(sublabel)
        
        self.content_container.append(no_results)
