"""
More Info section renderer.
"""

from typing import Dict, List

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from big_hardware_info.ui import builders as ui
from big_hardware_info.ui.renderers.base import SectionRenderer
from big_hardware_info.utils.i18n import _


class MoreInfoRenderer(SectionRenderer):
    """Renderer for additional system information section."""
    
    def render(self) -> None:
        """Render additional system information with terminal-style blocks."""
        system_data = self.data.get("system", {})
        pci_data = self.data.get("pci", {})
        usb_data = self.data.get("usb", {})
        logs_data = self.data.get("logs", {})
        fstab_data = self.data.get("fstab", {})
        modules_data = self.data.get("modules", {})
        mhwd_data = self.data.get("mhwd", {})
        kernel_data = self.data.get("kernel", {})
        cmdline_data = self.data.get("cmdline", {})
        efi_data = self.data.get("efi", {})
        acpi_data = self.data.get("acpi", {})
        rfkill_data = self.data.get("rfkill", {})
        sdio_data = self.data.get("sdio", {})
        
        dmesg = logs_data.get("dmesg_errors", {})
        journal = logs_data.get("journal_errors", {})
        
        # Repositories
        repositories = system_data.get("repositories", "")
        if repositories:
            self._add_terminal_block("Package Repositories", repositories)
        
        # PCI Devices (lspci -nn)
        self._add_pci_block(pci_data)
        
        # USB Devices (lsusb)
        self._add_usb_block(usb_data)
        
        # Webcam (v4l2-ctl)
        self._add_webcam_block()
        
        # SDIO devices
        self._add_sdio_block(sdio_data)
        
        # PCI Detailed
        pci_detailed = pci_data.get("detailed", "") if isinstance(pci_data, dict) else ""
        if pci_detailed:
            self._add_terminal_block("lspci -nvv", pci_detailed)
        
        # USB Detailed
        usb_detailed = usb_data.get("detailed", "") if isinstance(usb_data, dict) else ""
        if usb_detailed:
            self._add_terminal_block("lsusb -v", usb_detailed)
        
        # rfkill
        rfkill_raw = rfkill_data.get("raw", "") if isinstance(rfkill_data, dict) else ""
        if rfkill_raw:
            self._add_terminal_block("rfkill", rfkill_raw)
        
        # /etc/fstab
        fstab_raw = fstab_data.get("raw", "") if isinstance(fstab_data, dict) else ""
        if fstab_raw:
            self._add_terminal_block("/etc/fstab", fstab_raw)
        
        # lsmod
        modules_raw = modules_data.get("raw", "") if isinstance(modules_data, dict) else ""
        if modules_raw:
            self._add_terminal_block("lsmod", modules_raw)
        
        # MHWD driver
        mhwd_drivers = mhwd_data.get("installed_drivers", "") if isinstance(mhwd_data, dict) else ""
        if mhwd_drivers:
            self._add_terminal_block("Mhwd driver", mhwd_drivers)
        
        # MHWD kernel
        mhwd_kernels = mhwd_data.get("installed_kernels", "") if isinstance(mhwd_data, dict) else ""
        if mhwd_kernels:
            self._add_terminal_block("Mhwd kernel", mhwd_kernels)
        
        # Cmdline
        cmdline_raw = cmdline_data.get("raw", "") if isinstance(cmdline_data, dict) else ""
        if cmdline_raw:
            self._add_terminal_block("Cmdline", cmdline_raw)
        
        # EFI Boot Manager
        efi_verbose = ""
        if isinstance(efi_data, dict) and efi_data.get("available"):
            efi_verbose = efi_data.get("verbose", efi_data.get("basic", ""))
        if efi_verbose:
            self._add_terminal_block("efibootmgr", efi_verbose)
        
        # ACPI interrupts
        self._add_acpi_block(acpi_data)
        
        # Dmesg errors
        dmesg_raw = dmesg.get("raw", "")
        if dmesg_raw:
            self._add_terminal_block("Dmesg error", dmesg_raw)
        
        # Journal errors
        journal_raw = journal.get("raw", "")
        if journal_raw:
            self._add_terminal_block("Journald error", journal_raw)
    
    def _add_terminal_block(self, title: str, content: str) -> None:
        """Add a terminal-style text block."""
        self.window._add_terminal_block(title, content)
    
    def _add_pci_block(self, pci_data: Dict) -> None:
        """Add PCI devices block."""
        pci_devices = pci_data.get("devices", []) if isinstance(pci_data, dict) else pci_data
        if pci_devices:
            pci_text = "\n".join(d.get("raw", str(d)) for d in pci_devices if isinstance(d, dict))
            if not pci_text:
                pci_text = str(pci_devices)
            self._add_terminal_block("lspci -nn", pci_text)
    
    def _add_usb_block(self, usb_data: Dict) -> None:
        """Add USB devices block."""
        usb_devices = usb_data.get("devices", []) if isinstance(usb_data, dict) else usb_data
        if usb_devices:
            usb_text = "\n".join(d.get("raw", str(d)) for d in usb_devices if isinstance(d, dict))
            if not usb_text:
                usb_text = str(usb_devices)
            self._add_terminal_block("lsusb", usb_text)
    
    def _add_webcam_block(self) -> None:
        """Add webcam data block."""
        webcam_data = self.data.get("webcam", {})
        webcams = webcam_data.get("devices", [])
        if webcams:
            v4l2_text = ""
            for webcam in webcams:
                if webcam.get("raw"):
                    if v4l2_text:
                        v4l2_text += "\n" + "=" * 60 + "\n\n"
                    v4l2_text += webcam["raw"]
            if v4l2_text:
                self._add_terminal_block("v4l2-ctl --all", v4l2_text)
    
    def _add_sdio_block(self, sdio_data: Dict) -> None:
        """Add SDIO devices block."""
        sdio_devices = []
        if isinstance(sdio_data, dict):
            sdio_devices = sdio_data.get("devices", [])
        
        if sdio_devices:
            sdio_text = ""
            for dev in sdio_devices:
                sdio_text += f"Device: {dev.get('name', 'Unknown')}\n"
                sdio_text += f"  Vendor: {dev.get('vendor', 'Unknown')}\n"
                sdio_text += f"  Device ID: {dev.get('device', 'Unknown')}\n"
                if dev.get('uevent'):
                    sdio_text += f"  Uevent: {dev.get('uevent')}\n"
                sdio_text += "\n"
        else:
            sdio_text = "No SDIO devices detected"
        self._add_terminal_block("SDIO", sdio_text)
    
    def _add_acpi_block(self, acpi_data: Dict) -> None:
        """Add ACPI interrupts block."""
        if isinstance(acpi_data, dict):
            acpi_interrupts = acpi_data.get("interrupts", [])
            if acpi_interrupts:
                acpi_text = "\n".join(
                    f"{i.get('name', '')}: {i.get('value', '')}" 
                    for i in acpi_interrupts
                )
                self._add_terminal_block("ACPI interrupts", acpi_text)
