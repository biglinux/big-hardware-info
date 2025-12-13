"""
Big Hardware Info - Application Package.

A modern GTK4/Adwaita application for viewing and sharing hardware information.
"""

import sys
import os
import logging
import gi

# Add parent directory to path when running directly
if __name__ == "__main__":
    _parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _parent not in sys.path:
        sys.path.insert(0, _parent)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib  # noqa: E402

from app.ui import MainWindow  # noqa: E402
from app.utils.config import AppConfig  # noqa: E402
from app.utils.i18n import _  # noqa: E402


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BigHardwareInfoApplication(Adw.Application):
    """
    Main application class.
    
    Handles application lifecycle, menus, and window management.
    """
    
    def __init__(self):
        """Initialize the application."""
        super().__init__(
            application_id="org.biglinux.BigHardwareInfo",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        
        self.config = AppConfig()
        self.window = None
        
        GLib.set_application_name(_("Big Hardware Info"))
        
    def do_startup(self):
        """Called when the application starts."""
        Adw.Application.do_startup(self)
        
        # Set up actions
        self._setup_actions()
        
    def do_activate(self):
        """Called when the application is activated."""
        if not self.window:
            self.window = MainWindow(application=self, config=self.config)
        
        self.window.present()
        
    def _setup_actions(self):
        """Set up application actions."""
        # Refresh action
        action = Gio.SimpleAction.new("refresh", None)
        action.connect("activate", self._on_refresh)
        self.add_action(action)
        self.set_accels_for_action("app.refresh", ["<Ctrl>r", "F5"])
        
        # Export action
        action = Gio.SimpleAction.new("export", None)
        action.connect("activate", self._on_export)
        self.add_action(action)
        self.set_accels_for_action("app.export", ["<Ctrl>s"])
        
        # Share action
        action = Gio.SimpleAction.new("share", None)
        action.connect("activate", self._on_share)
        self.add_action(action)
        self.set_accels_for_action("app.share", ["<Ctrl><Shift>s"])
        
        # About action
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self._on_about)
        self.add_action(action)
        
        # Quit action
        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self._on_quit)
        self.add_action(action)
        self.set_accels_for_action("app.quit", ["<Ctrl>q"])
        
    def _on_refresh(self, _action, _param):
        """Handle refresh action."""
        if self.window:
            self.window._refresh_data()
            
    def _on_export(self, _action, _param):
        """Handle export action."""
        if self.window:
            self.window._on_export_clicked(None)
            
    def _on_share(self, _action, _param):
        """Handle share action."""
        if self.window:
            self.window._on_share_clicked(None)
            
    def _on_about(self, _action, _param):
        """Show about dialog."""
        dialog = Adw.AboutDialog.new()
        dialog.set_application_name(_("Big Hardware Info"))
        dialog.set_version("2.0.0")
        dialog.set_developer_name("BigLinux Team")
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.set_comments(
            _("View detailed hardware information and share diagnostic reports.\n\n"
              "Collect comprehensive system data including CPU, GPU, memory, "
              "storage, network, and more. Export reports to HTML or share online.")
        )
        dialog.set_website("https://www.biglinux.com.br")
        dialog.set_issue_url("https://github.com/biglinux/big-hardware-info/issues")
        dialog.set_application_icon("big-hardware-info")
        
        dialog.set_developers([
            "BigLinux Team https://www.biglinux.com.br",
        ])
        
        dialog.set_designers([
            "BigLinux Team",
        ])
        
        # Add credits section
        dialog.add_credit_section(_("Special Thanks"), [
            "inxi developers",
            "GTK/libadwaita team",
        ])
        
        dialog.set_translator_credits(_("translator-credits"))
        dialog.set_copyright("© 2024-2025 BigLinux")
        
        # Add release notes
        dialog.set_release_notes(_(
            "<p>Big Hardware Info 2.0.0 - Complete Rewrite:</p>"
            "<ul>"
            "<li>Comprehensive hardware detection</li>"
            "<li>Export to HTML with modern design</li>"
            "<li>Online sharing via termbin.com</li>"
            "<li>Syntax highlighting for system files</li>"
            "<li>USB/PCIe device distinction</li>"
            "</ul>"
        ))
        
        dialog.present(self.window)
        
    def _on_quit(self, _action, _param):
        """Handle quit action."""
        self.quit()


def main():
    """Application entry point."""
    app = BigHardwareInfoApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
