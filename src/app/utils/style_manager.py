"""
Style Manager for Hardware Reporter application.

Handles loading and applying CSS stylesheets from external files,
following proper resource management patterns for GTK4/Adwaita applications.
"""

from pathlib import Path
from typing import Optional
import logging

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk

logger = logging.getLogger(__name__)


class StyleManager:
    """
    Manages CSS styling for the application.
    
    Loads CSS from external files and applies them to the application's
    display, following GNOME HIG guidelines for theming.
    """
    
    _instance: Optional["StyleManager"] = None
    _provider: Optional[Gtk.CssProvider] = None
    
    def __new__(cls) -> "StyleManager":
        """Singleton pattern to ensure only one StyleManager exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_default(cls) -> "StyleManager":
        """Get the default StyleManager instance."""
        return cls()
    
    @property
    def css_path(self) -> Path:
        """Get the path to the CSS file."""
        # Navigate from app/utils/ to app/resources/
        return Path(__file__).parent.parent / "resources" / "style.css"
    
    def load_styles(self) -> bool:
        """
        Load and apply CSS styles from the external stylesheet.
        
        Returns:
            True if styles were loaded successfully, False otherwise.
        """
        try:
            css_file = self.css_path
            
            if not css_file.exists():
                logger.warning(f"CSS file not found: {css_file}")
                return False
            
            # Create CSS provider if not exists
            if self._provider is None:
                self._provider = Gtk.CssProvider()
            
            # Load CSS from file
            self._provider.load_from_path(str(css_file))
            
            # Apply to default display
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    self._provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
                logger.info(f"CSS styles loaded from: {css_file}")
                return True
            else:
                logger.error("No default display available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load CSS styles: {e}")
            return False
    
    def reload_styles(self) -> bool:
        """
        Reload CSS styles from the stylesheet file.
        
        Useful for development when modifying styles without restarting.
        
        Returns:
            True if styles were reloaded successfully, False otherwise.
        """
        return self.load_styles()
    
    def unload_styles(self) -> None:
        """Remove the CSS provider from the display."""
        if self._provider is not None:
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.remove_provider_for_display(
                    display,
                    self._provider
                )
                logger.info("CSS styles unloaded")
            self._provider = None


def load_application_styles() -> bool:
    """
    Convenience function to load application styles.
    
    Returns:
        True if styles were loaded successfully, False otherwise.
    """
    return StyleManager.get_default().load_styles()
