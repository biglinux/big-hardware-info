"""Shared application constants."""


class AppInfo:
    """Application information."""
    NAME = "Big Hardware Info"
    VERSION = "2.0.0"
    DEVELOPER = "BigLinux Team"
    DEVELOPER_URL = "https://www.biglinux.com.br"


# PCI device classification keywords
PCI_INFRASTRUCTURE_KEYWORDS = frozenset([
    "bridge", "bus", "usb controller", "hub", "host bridge",
    "isa bridge", "pci bridge", "pcie", "smbus", "communication controller",
    "signal processing", "serial bus", "system peripheral", "pic", "dma",
    "rtc", "timer", "watchdog", "sd host", "sd/mmc",
    "sata controller", "ahci", "sata ahci"
])
