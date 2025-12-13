"""
Hardware information data model.

Main data structure for storing all collected hardware information.
"""

import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


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
    
    # Raw inxi output (for display)
    raw_inxi: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: dict) -> "HardwareInfo":
        """Create instance from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_json(cls, json_str: str) -> "HardwareInfo":
        """Create instance from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def get_summary(self) -> dict:
        """
        Get a summary of key hardware information.
        
        Returns:
            Dictionary with summary data for quick display.
        """
        summary = {
            "hostname": self.hostname,
            "collected": self.collection_date,
        }
        
        # Extract key info from each section
        if self.cpu:
            summary["cpu"] = self._extract_cpu_summary()
        
        if self.memory:
            summary["memory"] = self._extract_memory_summary()
        
        if self.gpu:
            summary["gpu"] = self._extract_gpu_summary()
        
        if self.disk_usage:
            summary["disk"] = self._extract_disk_summary()
        
        if self.kernel:
            summary["kernel"] = self.kernel.get("version", "")
        
        return summary
    
    def _extract_cpu_summary(self) -> str:
        """Extract CPU summary from data."""
        data = self.cpu.get("data", {})
        if isinstance(data, dict):
            # Try to find CPU model name
            for key, value in data.items():
                if "model" in key.lower() or "info" in key.lower():
                    if isinstance(value, str):
                        return value
        return str(data)[:100] if data else "Unknown"
    
    def _extract_memory_summary(self) -> str:
        """Extract memory summary from data."""
        data = self.memory.get("data", {})
        if isinstance(data, dict):
            for key, value in data.items():
                if "total" in key.lower() or "ram" in key.lower():
                    if isinstance(value, str):
                        return value
        return str(data)[:100] if data else "Unknown"
    
    def _extract_gpu_summary(self) -> str:
        """Extract GPU summary from data."""
        data = self.gpu.get("data", {})
        if isinstance(data, dict):
            for key, value in data.items():
                if "device" in key.lower() or "driver" in key.lower():
                    if isinstance(value, str):
                        return value
        return str(data)[:100] if data else "Unknown"
    
    def _extract_disk_summary(self) -> str:
        """Extract disk usage summary."""
        if self.disk_usage:
            size = self.disk_usage.get("size", "")
            used = self.disk_usage.get("used", "")
            available = self.disk_usage.get("available", "")
            if size and used and available:
                return f"{used} / {size} ({available} free)"
        return "Unknown"


# Category metadata for UI display
CATEGORIES = {
    "summary": {
        "name": "Summary",
        "icon": "view-grid-symbolic",
        "description": "Overview of main hardware",
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
