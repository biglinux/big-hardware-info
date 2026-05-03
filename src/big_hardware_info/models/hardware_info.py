"""
Hardware information data model.

Main data structure for storing all collected hardware information.
"""

from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass
class HardwareInfo:
    """
    Main container for all hardware information.
    
    Stores data from all collectors in a unified structure.
    """
    
    # Metadata
    collection_date: str = field(default_factory=lambda: datetime.now().isoformat())
    hostname: str = ""
    
    # Inxi data (main hardware info)
    cpu: Dict[str, Any] = field(default_factory=dict)
    gpu: Dict[str, Any] = field(default_factory=dict)
    machine: Dict[str, Any] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)
    swap: Dict[str, Any] = field(default_factory=dict)
    audio: Dict[str, Any] = field(default_factory=dict)
    network: Dict[str, Any] = field(default_factory=dict)
    battery: Dict[str, Any] = field(default_factory=dict)
    sensors: Dict[str, Any] = field(default_factory=dict)
    bluetooth: Dict[str, Any] = field(default_factory=dict)
    webcam: Dict[str, Any] = field(default_factory=dict)
    
    # Bus/Port Headers (Inxi data)
    usb: Dict[str, Any] = field(default_factory=dict)
    pci: Dict[str, Any] = field(default_factory=dict)
    
    # USB and PCI Inxi data (with driver info)
    usb_inxi: Dict[str, Any] = field(default_factory=dict)
    pci_inxi: Dict[str, Any] = field(default_factory=dict)
    
    # Storage
    disk: Dict[str, Any] = field(default_factory=dict)
    partitions: Dict[str, Any] = field(default_factory=dict)
    unmounted: Dict[str, Any] = field(default_factory=dict)
    logical: Dict[str, Any] = field(default_factory=dict)
    raid: Dict[str, Any] = field(default_factory=dict)
    
    # System
    system: Dict[str, Any] = field(default_factory=dict)
    info: Dict[str, Any] = field(default_factory=dict)
    repos: Dict[str, Any] = field(default_factory=dict)
    
    # Devices
    pci_devices: List[Dict[str, Any]] = field(default_factory=list)
    usb_devices: List[Dict[str, Any]] = field(default_factory=list)
    sdio_devices: List[Dict[str, Any]] = field(default_factory=list)
    
    # Configuration
    kernel: Dict[str, Any] = field(default_factory=dict)
    fstab: Dict[str, Any] = field(default_factory=dict)
    cmdline: Dict[str, Any] = field(default_factory=dict)
    modules: Dict[str, Any] = field(default_factory=dict)
    mhwd: Dict[str, Any] = field(default_factory=dict)
    efi: Dict[str, Any] = field(default_factory=dict)
    acpi: Dict[str, Any] = field(default_factory=dict)
    rfkill: Dict[str, Any] = field(default_factory=dict)
    
    # Root/Admin Data (Collected via pkexec)
    smart_data: Dict[str, Any] = field(default_factory=dict)
    advanced_sensors: Dict[str, Any] = field(default_factory=dict)
    advanced_gpu: Dict[str, Any] = field(default_factory=dict)
    root_collected: bool = False
    
    # Other
    printer: Dict[str, Any] = field(default_factory=dict)
    disk_usage: Dict[str, Any] = field(default_factory=dict)
    install_date: Dict[str, Any] = field(default_factory=dict)
    
    # Logs
    logs: Dict[str, Any] = field(default_factory=dict)
    more_info: Dict[str, Any] = field(default_factory=dict)

    # AI diagnostic command outputs (collected by AiDiagnosticsCollector)
    ai_diag: Dict[str, Any] = field(default_factory=dict)
    
    # Raw inxi output (for display)
    raw_inxi: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HardwareInfo":
        """Create instance from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Category metadata for UI display.
#
# ``name`` and ``description`` store the English SOURCE strings — each call
# site is responsible for wrapping them in ``_()`` at render time. Translating
# at import time was a bug: it froze the strings at whatever locale happened
# to be active when this module first loaded, and it broke tests that
# monkey-patch the translation function (double translation).
CATEGORIES = {
    "summary": {
        "name": "Summary",
        "icon": "view-grid-symbolic",
        "description": "Overview of main hardware",
    },
    "ai_help": {
        "name": "AI Help",
        "icon": "system-help-symbolic",
        "description": "Pre-built prompts to ask an AI chatbot for help",
    },
    "cpu": {
        "name": "Processor",
        "icon": "cpu-symbolic",
        "description": "CPU information",
    },
    "gpu": {
        "name": "Graphics",
        "icon": "video-display-symbolic",
        "description": "Video card information",
    },
    "webcam": {
        "name": "Webcams",
        "icon": "camera-web-symbolic",
        "description": "Camera devices",
    },
    "machine": {
        "name": "Motherboard",
        "icon": "computer-symbolic",
        "description": "Motherboard and BIOS information",
    },
    "memory": {
        "name": "Memory",
        "icon": "memory-symbolic",
        "description": "RAM information",
    },
    "audio": {
        "name": "Audio",
        "icon": "audio-card-symbolic",
        "description": "Sound devices",
    },
    "network": {
        "name": "Network",
        "icon": "network-wired-symbolic",
        "description": "Network devices and connections",
    },
    "disk": {
        "name": "Storage",
        "icon": "drive-harddisk-symbolic",
        "description": "Storage devices",
    },
    "battery": {
        "name": "Battery",
        "icon": "battery-symbolic",
        "description": "Battery status",
    },
    "bluetooth": {
        "name": "Bluetooth",
        "icon": "bluetooth-symbolic",
        "description": "Bluetooth devices",
    },
    "usb": {
        "name": "USB Components",
        "icon": "media-removable-symbolic",
        "description": "USB devices",
    },
    "pci": {
        "name": "PCI Devices",
        "icon": "drive-multidisk-symbolic",
        "description": "PCI devices",
    },
    "system": {
        "name": "System",
        "icon": "system-run-symbolic",
        "description": "System information",
    },
    "printer": {
        "name": "Printers",
        "icon": "printer-symbolic",
        "description": "Printer devices",
    },
    "sensors": {
        "name": "Sensors",
        "icon": "temperature-symbolic",
        "description": "Temperature and fan sensors",
    },
    "more_info": {
        "name": "More Info",
        "icon": "dialog-information-symbolic",
        "description": "Raw system data and logs",
    },
}
