"""Big Hardware Info application package."""

import sys
import logging
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib  # noqa: E402

from big_hardware_info.ui import MainWindow  # noqa: E402
from big_hardware_info.utils.config import AppConfig  # noqa: E402
from big_hardware_info.utils.i18n import _  # noqa: E402
from big_hardware_info.utils.constants import AppInfo  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BigHardwareInfoApplication(Adw.Application):
    """Application lifecycle, menus, and window management."""

    def __init__(self) -> None:
        super().__init__(
            application_id="br.com.biglinux.bighardwareinfo",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

        self.config = AppConfig()
        self.window: MainWindow | None = None

        GLib.set_application_name(AppInfo.NAME)

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        self._setup_actions()

    def do_activate(self) -> None:
        if not self.window:
            self.window = MainWindow(application=self, config=self.config)

        self.window.present()

    def _setup_actions(self) -> None:
        for name, accel, handler in (
            ("refresh", ["<Ctrl>r", "F5"], self._on_refresh),
            ("export", ["<Ctrl>s"], self._on_export),
            ("share", ["<Ctrl><Shift>s"], self._on_share),
            ("about", [], self._on_about),
            ("quit", ["<Ctrl>q"], self._on_quit),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", handler)
            self.add_action(action)
            if accel:
                self.set_accels_for_action(f"app.{name}", accel)

    def _on_refresh(self, _action: Gio.SimpleAction, _param: GLib.Variant | None) -> None:
        if self.window:
            self.window._refresh_data()

    def _on_export(self, _action: Gio.SimpleAction, _param: GLib.Variant | None) -> None:
        if self.window:
            self.window._on_export_clicked(None)

    def _on_share(self, _action: Gio.SimpleAction, _param: GLib.Variant | None) -> None:
        if self.window:
            self.window._on_share_clicked(None)

    def _on_about(self, _action: Gio.SimpleAction, _param: GLib.Variant | None) -> None:
        dialog = Adw.AboutDialog.new()
        dialog.set_application_name(AppInfo.NAME)
        dialog.set_version(AppInfo.VERSION)
        dialog.set_developer_name(AppInfo.DEVELOPER)
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.set_comments(
            _("View detailed hardware information and share diagnostic reports.\n\n"
              "Collect comprehensive system data including CPU, GPU, memory, "
              "storage, network, and more. Export reports to HTML or share online.")
        )
        dialog.set_website(AppInfo.DEVELOPER_URL)
        dialog.set_issue_url("https://github.com/biglinux/big-hardware-info/issues")
        dialog.set_application_icon("big-hardware-info")

        dialog.set_developers([f"{AppInfo.DEVELOPER} {AppInfo.DEVELOPER_URL}"])
        dialog.set_designers([AppInfo.DEVELOPER])

        dialog.add_credit_section(_("Special Thanks"), [
            "inxi developers",
            "GTK/libadwaita team",
        ])

        dialog.set_translator_credits(_("translator-credits"))
        dialog.set_copyright("© 2024-2025 BigLinux")

        dialog.set_release_notes(_(
            "<p>Big Hardware Info {version} - Complete Rewrite:</p>"
            "<ul>"
            "<li>Comprehensive hardware detection</li>"
            "<li>Export to HTML with modern design</li>"
            "<li>Online sharing via filebin.net</li>"
            "<li>Syntax highlighting for system files</li>"
            "<li>USB/PCIe device distinction</li>"
            "</ul>"
        ).format(version=AppInfo.VERSION))

        dialog.present(self.window)

    def _on_quit(self, _action: Gio.SimpleAction, _param: GLib.Variant | None) -> None:
        self.quit()


def main() -> int:
    app = BigHardwareInfoApplication()
    return app.run(sys.argv)
