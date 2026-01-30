"""
Icon management module for Big Hardware Info.

This module provides utilities to load bundled SVG icons for the application,
ensuring consistent visual appearance regardless of the system's installed icon themes.

Icons are loaded from multiple possible locations:
1. Installed location: /usr/share/big-hardware-info/icons/
2. Development location: src/big_hardware_info/icons/
3. Fallback: System icon theme (via Gtk.Image.new_from_icon_name)
"""

from pathlib import Path
from typing import Optional
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Gio, GLib


# Possible icon directory paths (checked in order)
_ICON_PATHS = [
    Path("/usr/share/big-hardware-info/icons"),
    Path(__file__).parent.parent / "icons",
]


def get_icon_path(icon_name: str) -> Optional[Path]:
    """
    Get the absolute path to a bundled icon file.

    Args:
        icon_name: Icon name (e.g., "cpu-symbolic" or "cpu-symbolic.svg")

    Returns:
        Path object if icon found, None otherwise
    """
    # Ensure .svg extension
    if not icon_name.endswith('.svg'):
        icon_name = f"{icon_name}.svg"

    # Search in all known icon directories
    for icon_dir in _ICON_PATHS:
        icon_path = icon_dir / icon_name
        if icon_path.exists() and icon_path.is_file():
            return icon_path

    return None


def icon_from_file(icon_path: Path, size: int = 16) -> Gtk.Image:
    """
    Create a Gtk.Image widget from an icon file path.

    Args:
        icon_path: Absolute path to the icon file
        size: Pixel size for the icon (default: 16)

    Returns:
        Gtk.Image widget displaying the icon
    """
    # Create a Gio.File from the path
    gfile = Gio.File.new_for_path(str(icon_path))

    # Create a FileIcon from the Gio.File
    file_icon = Gio.FileIcon.new(gfile)

    # Create Gtk.Image from the FileIcon
    image = Gtk.Image.new_from_gicon(file_icon)
    image.set_pixel_size(size)

    return image


def create_icon_image(icon_name: str, size: int = 16, use_fallback: bool = True) -> Gtk.Image:
    """
    Create a Gtk.Image widget for the specified icon.

    This function attempts to load bundled icons first, and falls back
    to system icon theme if the icon is not found and fallback is enabled.

    Args:
        icon_name: Icon name (e.g., "cpu-symbolic")
        size: Pixel size for the icon (default: 16)
        use_fallback: If True, use system icon theme as fallback (default: True)

    Returns:
        Gtk.Image widget displaying the icon

    Examples:
        >>> icon = create_icon_image("cpu-symbolic", 24)
        >>> icon = create_icon_image("video-display-symbolic")
        >>> icon = create_icon_image("custom-icon", use_fallback=False)
    """
    # Remove .svg extension if present (for consistency)
    icon_name_clean = icon_name.replace('.svg', '')

    # Try to find bundled icon
    icon_path = get_icon_path(icon_name_clean)

    if icon_path is not None:
        # Load from bundled icon
        return icon_from_file(icon_path, size)

    # Fallback to system icon theme
    if use_fallback:
        image = Gtk.Image.new_from_icon_name(icon_name_clean)
        image.set_pixel_size(size)
        return image

    # No icon found and fallback disabled
    # Return a placeholder image
    image = Gtk.Image.new_from_icon_name("image-missing")
    image.set_pixel_size(size)
    return image


def is_icon_available(icon_name: str) -> bool:
    """
    Check if a bundled icon is available.

    Args:
        icon_name: Icon name to check

    Returns:
        True if icon exists in bundled icons, False otherwise
    """
    return get_icon_path(icon_name) is not None


def list_bundled_icons() -> list[str]:
    """
    List all available bundled icons.

    Returns:
        List of icon names (without .svg extension)
    """
    icons = []

    for icon_dir in _ICON_PATHS:
        if icon_dir.exists() and icon_dir.is_dir():
            for icon_file in icon_dir.glob("*.svg"):
                icon_name = icon_file.stem  # Filename without extension
                if icon_name not in icons:
                    icons.append(icon_name)

    return sorted(icons)


# Preload icon directory for faster lookups (optional optimization)
def _preload_icon_cache() -> dict[str, Path]:
    """
    Preload all icon paths into a cache dictionary.

    This is an internal optimization function that can be called at startup
    to speed up icon lookups.

    Returns:
        Dictionary mapping icon names to their paths
    """
    cache = {}

    for icon_dir in _ICON_PATHS:
        if icon_dir.exists() and icon_dir.is_dir():
            for icon_file in icon_dir.glob("*.svg"):
                icon_name = icon_file.stem
                if icon_name not in cache:
                    cache[icon_name] = icon_file

    return cache


# Optional: Create cache at module import time
# Uncomment the following lines to enable icon caching:
# _ICON_CACHE = _preload_icon_cache()
