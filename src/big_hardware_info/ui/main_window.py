"""Main application window with sidebar navigation and scrollable content."""

from __future__ import annotations

import logging
import subprocess
import threading
from typing import Any, Callable, Dict, Optional

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from big_hardware_info.collectors import HardwareCollector
from big_hardware_info.models.hardware_info import CATEGORIES
from big_hardware_info.ui import builders as ui
from big_hardware_info.ui import dialogs
from big_hardware_info.ui import sections as section_registry
from big_hardware_info.ui.admin_data import AdminDataController
from big_hardware_info.ui.search import SearchHandler
from big_hardware_info.ui.terminal_block import create_terminal_block
from big_hardware_info.ui.window_state import (
    WindowStatePersister,
    read_initial_geometry,
)
from big_hardware_info.utils.config import AppConfig
from big_hardware_info.utils.constants import AppInfo
from big_hardware_info.utils.i18n import _
from big_hardware_info.utils.style_manager import StyleManager


logger = logging.getLogger(__name__)


class MainWindow(Adw.ApplicationWindow):
    """Main application window with sidebar navigation."""

    def __init__(
        self,
        application: Adw.Application,
        config: Optional[AppConfig] = None,
        **kwargs: Any,
    ) -> None:
        self.app = application
        self.config = config

        width, height, maximized = read_initial_geometry(config)

        super().__init__(
            application=application,
            title=AppInfo.NAME,
            default_width=width,
            default_height=height,
            **kwargs,
        )

        self.collector = HardwareCollector()
        self.hardware_data: Dict[str, Any] = {}
        self.section_widgets: Dict[str, Gtk.Widget] = {}
        self.search_handler = SearchHandler(self)
        self._saved_scroll_position: Optional[float] = None
        self._admin_controller = AdminDataController(
            self, on_complete=self._merge_admin_data,
        )

        if not StyleManager.get_default().load_styles():
            logger.warning(
                "Failed to load external CSS, styles may not apply correctly",
            )

        self._build_ui()
        self._window_state = WindowStatePersister(self, config)
        self._window_state.restore_maximized_if_needed(maximized)

        GLib.idle_add(self._start_data_collection)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Build the split-view layout with sidebar + scrollable content."""
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        self.split_view = Adw.NavigationSplitView()
        self.toast_overlay.set_child(self.split_view)

        self.split_view.set_sidebar(self._build_sidebar())
        self.split_view.set_content(self._build_content_page())
        self.split_view.set_min_sidebar_width(200)
        self.split_view.set_max_sidebar_width(300)

    def _build_sidebar(self) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()

        header = Adw.HeaderBar()
        app_icon_btn = Gtk.Button()
        app_icon_btn.add_css_class("flat")
        app_icon_btn.set_child(ui.icon("computer-symbolic", 20))
        app_icon_btn.set_tooltip_text(_("About") + " " + AppInfo.NAME)
        app_icon_btn.connect(
            "clicked",
            lambda _btn: self.app.activate_action("about", None),
        )
        header.pack_start(app_icon_btn)
        header.set_title_widget(Adw.WindowTitle.new(AppInfo.NAME, ""))
        toolbar.add_top_bar(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        self.category_list = Gtk.ListBox()
        self.category_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.category_list.add_css_class("navigation-sidebar")
        self.category_list.connect("row-selected", self._on_category_selected)

        for cat_id, cat_info in CATEGORIES.items():
            self.category_list.append(self._create_category_row(cat_id, cat_info))

        first_row = self.category_list.get_row_at_index(0)
        if first_row is not None:
            self.category_list.select_row(first_row)

        scroll.set_child(self.category_list)
        toolbar.set_content(scroll)

        return Adw.NavigationPage.new(toolbar, "Categories")

    def _build_content_page(self) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(self._build_content_header())

        self.content_scroll = Gtk.ScrolledWindow()
        self.content_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC,
        )
        self.content_scroll.set_vexpand(True)

        self.content_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_container.set_margin_start(24)
        self.content_container.set_margin_end(24)
        self.content_container.set_margin_top(8)
        self.content_container.set_margin_bottom(24)
        self.content_container.set_spacing(24)

        self.content_scroll.set_child(self.content_container)
        toolbar.set_content(self.content_scroll)

        return Adw.NavigationPage.new(toolbar, AppInfo.NAME)

    def _build_content_header(self) -> Adw.HeaderBar:
        header = Adw.HeaderBar()

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text(_("Refresh hardware information (Ctrl+R)"))
        refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.pack_start(refresh_btn)

        self.root_btn = Gtk.Button(icon_name="system-lock-screen-symbolic")
        self.root_btn.set_tooltip_text(_("Collect restricted data (requires admin)"))
        self.root_btn.connect("clicked", self._on_root_access_clicked)
        header.pack_start(self.root_btn)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_("Search..."))
        self.search_entry.set_hexpand(False)
        self.search_entry.set_width_chars(25)
        self.search_entry.connect(
            "search-changed", self.search_handler.on_search_changed,
        )
        header.set_title_widget(self.search_entry)

        menu = Gio.Menu()
        menu.append(_("Export Report"), "app.export")
        menu.append(_("Share Online"), "app.share")
        menu.append(_("About"), "app.about")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_btn)

        return header

    def _create_category_row(self, cat_id: str, cat_info: dict) -> Gtk.ListBoxRow:
        """Create a compact category row for the sidebar."""
        row = Gtk.ListBoxRow()
        row.cat_id = cat_id
        row.add_css_class("category-row")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(2)
        box.set_margin_end(2)
        box.set_margin_top(1)
        box.set_margin_bottom(1)

        icon_widget = ui.icon(cat_info["icon"], 18)
        icon_widget.add_css_class("category-icon")
        box.append(icon_widget)

        label = Gtk.Label(label=_(cat_info["name"]))
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.add_css_class("category-label")
        box.append(label)

        row.set_child(box)
        return row

    # ------------------------------------------------------------------
    # Content rendering
    # ------------------------------------------------------------------
    def _clear_content(self) -> None:
        """Remove every child from the main content container."""
        child = self.content_container.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.content_container.remove(child)
            child = next_child

    def _show_loading(self) -> None:
        """Replace content with a centered spinner + progress label."""
        self._clear_content()

        spinner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        spinner_box.set_halign(Gtk.Align.CENTER)
        spinner_box.set_valign(Gtk.Align.CENTER)
        spinner_box.set_vexpand(True)

        spinner = Gtk.Spinner()
        spinner.set_size_request(48, 48)
        spinner.start()
        spinner_box.append(spinner)

        label = Gtk.Label(label=_("Collecting hardware information..."))
        label.add_css_class("dim-label")
        spinner_box.append(label)

        self.progress_label = Gtk.Label(label="")
        self.progress_label.add_css_class("caption")
        spinner_box.append(self.progress_label)

        self.content_container.append(spinner_box)

    def _start_data_collection(self) -> bool:
        """Kick off background hardware collection and show the spinner."""
        self._show_loading()

        def worker() -> None:
            def progress_callback(category: str, progress: float) -> None:
                GLib.idle_add(self._update_progress, category, progress)

            data = self.collector.collect_all(progress_callback)
            GLib.idle_add(self._on_data_collected, data)

        threading.Thread(target=worker, daemon=True).start()
        return False

    def _update_progress(self, category: str, progress: float) -> bool:
        if getattr(self, "progress_label", None) is not None:
            self.progress_label.set_text(
                f"{_('Loading')} {category}... ({int(progress * 100)}%)",
            )
        return False

    def _on_data_collected(self, data: Dict[str, object]) -> bool:
        self.hardware_data = data
        logger.info("Hardware data collection complete")
        self._update_content()
        return False

    def _refresh_data(self) -> None:
        """Refresh hardware data, preserving the current scroll position."""
        if getattr(self, "content_scroll", None) is not None:
            vadj = self.content_scroll.get_vadjustment()
            self._saved_scroll_position = vadj.get_value() if vadj else None
        else:
            self._saved_scroll_position = None

        self._start_data_collection()

    def _update_content(self) -> None:
        """Render every section into the main content container."""
        if getattr(self, "content_container", None) is None:
            return

        self._clear_content()
        self.section_widgets = {}

        if not self.hardware_data:
            self._show_loading()
            return

        section_registry.render_all(self, self._add_section)
        self._restore_scroll_position()

    def _restore_scroll_position(self) -> None:
        if self._saved_scroll_position is None:
            return
        saved = self._saved_scroll_position
        self._saved_scroll_position = None

        def restore() -> bool:
            if getattr(self, "content_scroll", None) is not None:
                vadj = self.content_scroll.get_vadjustment()
                if vadj is not None:
                    vadj.set_value(saved)
            return False

        GLib.timeout_add(50, restore)

    def _add_section(self, cat_id: str, content_func: Callable[[], None]) -> None:
        """Add a section header + its content to the container.

        The content function is called with ``content_container`` pointing
        at the per-section ``Gtk.Box`` so renderers can ``append`` freely.
        Exceptions raised inside ``content_func`` are re-raised — isolation
        is handled one level up by :func:`sections.render_all`.
        """
        cat = CATEGORIES.get(cat_id, {})

        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        section.cat_id = cat_id

        if cat_id != "summary":
            section.append(self._create_section_header(cat_id, cat))
            separator = Gtk.Separator()
            separator.set_margin_bottom(8)
            section.append(separator)

        self.section_widgets[cat_id] = section
        self.content_container.append(section)

        original_container = self.content_container
        self.content_container = section
        try:
            content_func()
        finally:
            self.content_container = original_container

    def _create_section_header(self, cat_id: str, cat: dict) -> Gtk.Box:
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_margin_top(16)
        header.set_margin_bottom(8)

        icon_widget = ui.icon(cat.get("icon", "computer-symbolic"), 28)
        icon_widget.add_css_class("accent")
        header.append(icon_widget)

        label = Gtk.Label(label=_(cat.get("name", cat_id.title())))
        label.add_css_class("title-2")
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        header.append(label)

        if cat_id != "more_info":
            header.append(self._create_copy_button(cat_id))

        return header

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------
    def _on_category_selected(self, _listbox, row: Optional[Gtk.ListBoxRow]) -> None:
        """Scroll to the selected section when the user clicks a category."""
        if row is None:
            return

        current = self.category_list.get_first_child()
        while current is not None:
            current.remove_css_class("active-category")
            current = current.get_next_sibling()

        row.add_css_class("active-category")

        section = self.section_widgets.get(row.cat_id)
        if section is None or getattr(self, "content_scroll", None) is None:
            return
        vadj = self.content_scroll.get_vadjustment()
        if vadj is None:
            return

        def scroll_to_section() -> bool:
            if section.get_mapped():
                allocation = section.get_allocation()
                vadj.set_value(max(0, allocation.y - 8))
            return False

        GLib.idle_add(scroll_to_section)

    def _on_refresh_clicked(self, _button) -> None:
        self._refresh_data()

    def _on_root_access_clicked(self, button) -> None:
        self._admin_controller.collect(button)

    def _on_export_clicked(self, _button) -> None:
        dialogs.show_privacy_export_dialog(self, is_upload=False)

    def _on_share_clicked(self, _button) -> None:
        dialogs.show_privacy_export_dialog(self, is_upload=True)

    def _merge_admin_data(self, admin_data: Dict[str, object]) -> None:
        """Merge data from AdminDataController and rebuild content."""
        if not admin_data:
            return
        self.hardware_data.update(admin_data)
        self._update_content()

    # ------------------------------------------------------------------
    # Helpers used by renderers
    # ------------------------------------------------------------------
    def _open_url(self, url: str) -> None:
        """Open ``url`` in the system's default browser."""
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _open_url_with_toast(self, url: str) -> None:
        """Open ``url`` and show a brief toast notification."""
        self._open_url(url)
        self._show_toast(_("Opening in browser..."), 2)

    def _copy_text_to_clipboard(self, text: str, title: str = "") -> None:
        """Copy raw text to the clipboard and show a confirmation toast."""
        Gdk.Display.get_default().get_clipboard().set(text)
        msg = (_("Copied:") + " " + title) if title else _("Copied to clipboard")
        self._show_toast(msg, 2)

    def _add_raw_expander(
        self, title: str, text: str, expanded: bool = False,
    ) -> None:
        """Append an expandable scrollable text section to the container."""
        expander = Gtk.Expander(label=title)
        expander.set_expanded(expanded)
        expander.add_css_class("card")

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(300)
        scroll.set_propagate_natural_height(True)

        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_margin_top(8)
        text_view.get_buffer().set_text(text)

        scroll.set_child(text_view)
        expander.set_child(scroll)
        self.content_container.append(expander)

    def _add_terminal_block(self, title: str, text: str, max_lines: int = 15) -> None:
        """Append a monospace terminal block widget to the container."""
        widget = create_terminal_block(
            title, text, max_lines, on_copy=self._copy_text_to_clipboard,
        )
        self.content_container.append(widget)

    def _create_superuser_required_widget(self, field_name: str) -> Gtk.Widget:
        """Create the pill-style "Requires Administrator" button.

        Clicking it opens a confirmation dialog and, on accept, runs the
        admin data collection path (same pkexec flow as the header button).
        """
        button = Gtk.Button()
        button.add_css_class("flat")
        button.add_css_class("superuser-required")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        lock_icon = ui.icon("system-lock-screen-symbolic", 14)
        lock_icon.add_css_class("warning")
        box.append(lock_icon)

        label = Gtk.Label(label=_("Requires Administrator"))
        label.add_css_class("warning")
        label.add_css_class("caption")
        box.append(label)

        button.set_child(box)
        button.set_tooltip_text(
            _("Click to run as administrator and show") + " " + field_name,
        )
        button.connect("clicked", self._on_superuser_required_clicked)
        return button

    def _on_superuser_required_clicked(self, button: Gtk.Button) -> None:
        """Ask for confirmation, then reuse the admin collection flow."""
        dialog = Adw.AlertDialog()
        dialog.set_heading(_("Administrator Access Required"))
        dialog.set_body(
            _(
                "Some hardware information requires administrator privileges "
                "to access. Do you want to reload with elevated access?",
            ),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("reload", _("Reload as Admin"))
        dialog.set_response_appearance(
            "reload", Adw.ResponseAppearance.SUGGESTED,
        )
        dialog.set_default_response("reload")
        dialog.set_close_response("cancel")

        def on_response(_dialog, response: str) -> None:
            if response == "reload":
                self._admin_controller.collect(self.root_btn)

        dialog.connect("response", on_response)
        dialog.present(self)

    # ------------------------------------------------------------------
    # Copy helpers
    # ------------------------------------------------------------------
    def _create_copy_button(self, category_id: str) -> Gtk.Button:
        """Create the per-section copy-to-clipboard button."""
        btn = Gtk.Button()
        btn.set_icon_name("edit-copy-symbolic")
        btn.add_css_class("flat")
        btn.set_tooltip_text(_("Copy category data to clipboard"))
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect(
            "clicked",
            lambda _b, cid=category_id: self._copy_category_data(cid),
        )
        return btn

    def _copy_category_data(self, category_id: str) -> None:
        """Copy the current data for ``category_id`` to the clipboard."""
        data = self.hardware_data.get(category_id, {})
        if not data:
            self._show_toast(_("No data to copy"), 2)
            return

        text = self._format_data_as_text(data, category_id)
        Gdk.Display.get_default().get_clipboard().set(text)
        self._show_toast(_("Data copied to clipboard"), 2)

    @staticmethod
    def _format_data_as_text(data: dict, title: str = "") -> str:
        """Render a nested dict/list structure as human-readable text."""
        lines: list[str] = []
        if title:
            source_name = CATEGORIES.get(title, {}).get("name", title.title())
            lines.append(f"=== {_(source_name)} ===")
            lines.append("")

        def format_value(key, value, indent: int = 0) -> list[str]:
            prefix = "  " * indent
            clean_key = str(key).replace("_", " ").title()
            if isinstance(value, dict):
                if clean_key and value:
                    return [f"{prefix}{clean_key}:"] + [
                        line
                        for k, v in value.items()
                        for line in format_value(k, v, indent + 1)
                    ]
                return []
            if isinstance(value, list):
                if not value:
                    return []
                out = [f"{prefix}{clean_key}:"]
                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        out.append(f"{prefix}  [{idx + 1}]")
                        for k, v in item.items():
                            out.extend(format_value(k, v, indent + 2))
                    else:
                        out.append(f"{prefix}  - {item}")
                return out
            if value in (None, "", "N/A", "Unknown"):
                return []
            return [f"{prefix}{clean_key}: {value}"]

        for key, value in data.items():
            lines.extend(format_value(key, value))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Toast helper
    # ------------------------------------------------------------------
    def _show_toast(self, message: str, seconds: int) -> None:
        overlay = getattr(self, "toast_overlay", None)
        if overlay is None:
            return
        toast = Adw.Toast.new(message)
        toast.set_timeout(seconds)
        overlay.add_toast(toast)
