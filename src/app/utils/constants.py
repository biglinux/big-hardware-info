"""
Constants module for Big Hardware Info.
Contains shared constants used across the application.
"""

# Syntax highlighting tag names
class SyntaxTags:
    """Tag names for text buffer syntax highlighting."""
    PATH = "path"
    NUMBER = "number"
    KEYWORD = "keyword"
    COMMENT = "comment"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    OSNAME = "osname"

# Syntax highlighting colors (Adwaita-compatible)
class SyntaxColors:
    """Colors for syntax highlighting."""
    PATH = "#3584e4"      # Blue - paths, filenames
    NUMBER = "#26a269"    # Green - IDs, addresses, numbers
    KEYWORD = "#ff7800"   # Orange - keywords, labels
    COMMENT = "#8d93a8"   # Gray - comments, URLs, descriptions
    SUCCESS = "#33d17a"   # Bright green - success states
    WARNING = "#e5a50a"   # Yellow - warnings
    ERROR = "#e01b24"     # Red - errors, critical
    OSNAME = "#62a0ea"    # Light blue - OS/partition names

# CSS class names for status indicators
class StatusClasses:
    """CSS class names for status-based styling."""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ACCENT = "accent"
    DIM_LABEL = "dim-label"

# Usage thresholds for resource bars
class UsageThresholds:
    """Threshold percentages for usage indicators."""
    WARNING = 75
    CRITICAL = 90

# Search and filtering
class SearchConfig:
    """Search configuration constants."""
    DEBOUNCE_MS = 200
    MIN_CHARS = 1

# Inxi collector configuration
class InxiConfig:
    """Configuration for inxi data collection."""
    MAX_RETRIES = 2
    RETRY_DELAY = 1.0
    TIMEOUT = 30

# Application metadata
class AppInfo:
    """Application information."""
    NAME = "Big Hardware Info"
    VERSION = "2.0.0"
    WEBSITE = "https://github.com/biglinux/big-hardware-info"
    DEVELOPER = "BigLinux Team"
    DEVELOPER_URL = "https://www.biglinux.com.br"
    LICENSE = "GPL-3.0"

# File export defaults
class ExportDefaults:
    """Default values for file exports."""
    HTML_PREFIX = "hardware_report_"
    JSON_PREFIX = "hardware_data_"
    HTML_EXTENSION = ".html"
    JSON_EXTENSION = ".json"

# PCI device classification keywords
PCI_INFRASTRUCTURE_KEYWORDS = frozenset([
    "bridge", "bus", "usb controller", "hub", "host bridge",
    "isa bridge", "pci bridge", "pcie", "smbus", "communication controller",
    "signal processing", "serial bus", "system peripheral", "pic", "dma",
    "rtc", "timer", "watchdog", "sd host", "sd/mmc",
    "sata controller", "ahci", "sata ahci"
])
