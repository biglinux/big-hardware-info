"""
Base renderer class for hardware sections.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from big_hardware_info.ui import builders as ui
from big_hardware_info.utils.i18n import _


class SectionRenderer(ABC):
    """Base class for section renderers."""
    
    def __init__(self, window):
        """
        Initialize renderer with reference to main window.
        
        Args:
            window: Reference to MainWindow for callbacks.
        """
        self.window = window
    
    @property
    def data(self) -> Dict[str, Any]:
        """Get hardware data from window."""
        return self.window.hardware_data
    
    @property
    def container(self) -> Gtk.Box:
        """Get content container from window."""
        return self.window.content_container
    
    @abstractmethod
    def render(self) -> None:
        """Render the section content."""
        pass
    
    def copy_to_clipboard(self, text: str, title: str = "") -> None:
        """Copy text to clipboard with feedback."""
        self.window._copy_text_to_clipboard(text, title)
    
    def open_url(self, url: str) -> None:
        """Open URL in default browser."""
        self.window._open_url(url)
    
    def show_no_data(self, message: str) -> None:
        """Show a no-data message."""
        self.container.append(ui.no_data_label(message))
    
    def add_raw_expander(self, title: str, text: str, expanded: bool = False) -> None:
        """Add expandable raw text section."""
        self.container.append(ui.expander_with_text(title, text, expanded))
    
    def is_filtered_value(self, value: str) -> bool:
        """Check if value requires superuser."""
        if not value or not isinstance(value, str):
            return False
        superuser_indicators = [
            "<superuser required>",
            "<superuser/root required>",
            "<requires root>",
        ]
        return any(ind in value.lower().strip() for ind in superuser_indicators)
    
    def create_superuser_widget(self, field_name: str) -> Gtk.Widget:
        """Create a widget indicating superuser requirement."""
        return self.window._create_superuser_required_widget(field_name)
    
    def make_searchable(self, widget: Gtk.Widget, text: str) -> None:
        """Mark widget as searchable."""
        widget.searchable_text = text
    
    def format_copy_text(self, title: str, items: list) -> str:
        """Format items for clipboard copy."""
        lines = [f"=== {title} ===", ""]
        for label, value in items:
            if value:
                lines.append(f"{label}: {value}")
        return "\n".join(lines)
