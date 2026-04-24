"""Export, share, and privacy dialogs for the hardware info app."""

import os
import threading
import logging
from datetime import datetime
from typing import Any, Optional

from big_hardware_info.utils.i18n import _

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib, Gio

from big_hardware_info.ui import builders as ui

logger = logging.getLogger(__name__)


def _merge_hardware_data(
    base_data: dict[str, Any], new_data: dict[str, Any],
) -> dict[str, Any]:
    """Merge new sensitive data over base while keeping IPs from base network."""
    result = dict(base_data)

    for key, value in new_data.items():
        if key != "network":
            result[key] = value
            continue

        base_network = base_data.get("network", {})
        new_network = value

        if not (base_network and new_network):
            result["network"] = new_network or base_network
            continue

        merged_network = dict(base_network)
        base_devices = {
            d.get("IF", d.get("name", "")): d
            for d in base_network.get("devices", [])
        }
        for new_device in new_network.get("devices", []):
            key_name = new_device.get("IF", new_device.get("name", ""))
            if key_name and key_name in base_devices:
                existing = base_devices[key_name]
                if new_device.get("mac") and (
                    not existing.get("mac")
                    or "filter" in existing.get("mac", "").lower()
                ):
                    existing["mac"] = new_device["mac"]
            elif key_name:
                base_devices[key_name] = new_device

        merged_network["devices"] = list(base_devices.values())
        result["network"] = merged_network

    return result


def show_privacy_export_dialog(
    window: Adw.ApplicationWindow, is_upload: bool = False,
) -> None:
    """Ask whether to include sensitive data, then dispatch export or upload."""
    dialog = Adw.AlertDialog()
    
    if is_upload:
        dialog.set_heading(_("Share Report Online"))
        dialog.set_body(_(
            "Your hardware report will be uploaded to filebin.net, "
            "a public file hosting service.\n\n"
            "The generated link will be publicly accessible for 7 days."
        ))
    else:
        dialog.set_heading(_("Export Hardware Report"))
        dialog.set_body(_("Your hardware report will be saved as an HTML file."))
    
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    content.set_margin_top(12)

    privacy_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    privacy_box.add_css_class("card")
    privacy_box.set_margin_start(0)
    privacy_box.set_margin_end(0)
    
    warning_icon = ui.icon("dialog-warning-symbolic", 24)
    warning_icon.add_css_class("warning")
    privacy_box.append(warning_icon)
    
    privacy_label = Gtk.Label(
        label=_("Sensitive data (serial numbers, MAC addresses) can be included. "
              "For privacy, it's recommended to exclude them when sharing.")
    )
    privacy_label.set_wrap(True)
    privacy_label.set_xalign(0)
    privacy_label.add_css_class("caption")
    privacy_box.append(privacy_label)
    
    content.append(privacy_box)

    switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    switch_box.set_margin_top(8)

    switch_label = Gtk.Label(label=_("Include sensitive information"))
    switch_label.set_hexpand(True)
    switch_label.set_xalign(0)
    switch_box.append(switch_label)

    sensitive_switch = Gtk.Switch()
    sensitive_switch.set_active(False)
    sensitive_switch.set_valign(Gtk.Align.CENTER)
    switch_box.append(sensitive_switch)
    
    content.append(switch_box)
    dialog.set_extra_child(content)
    
    if is_upload:
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("share", _("Share"))
        dialog.set_response_appearance("share", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("share")
    else:
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("export", _("Export"))
        dialog.set_response_appearance("export", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("export")
    
    dialog.set_close_response("cancel")
    
    def on_response(dlg, response):
        include_sensitive = sensitive_switch.get_active()
        if is_upload and response == "share":
            start_share_upload(window, filter_sensitive=not include_sensitive)
        elif not is_upload and response == "export":
            show_export_file_dialog(window, filter_sensitive=not include_sensitive)
    
    dialog.connect("response", on_response)
    dialog.present(window)


def _collect_sensitive_via_pkexec() -> Optional[dict[str, Any]]:
    """Run inxi under pkexec on the main thread; ``None`` on cancel/failure."""
    import os
    import subprocess
    import shutil

    if not shutil.which("pkexec"):
        logger.warning("pkexec not available")
        return None

    env = os.environ.copy()
    env["LC_ALL"] = "C"
    env["LANG"] = "C"

    try:
        result = subprocess.run(
            ["pkexec", "inxi", "--tty", "-c", "0", "-Fxxxa", "-v8",
             "--output", "json", "--output-file", "print"],
            capture_output=True,
            text=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
            env=env,
        )
    except subprocess.TimeoutExpired:
        logger.warning("pkexec inxi timed out")
        return None
    except OSError as exc:
        logger.warning("pkexec inxi failed to start: %s", exc)
        return None

    if result.returncode == 126:
        logger.info("User cancelled authentication")
        return None
    if result.returncode != 0 or not result.stdout:
        logger.warning(
            "pkexec inxi failed with code %s: %s",
            result.returncode, result.stderr,
        )
        return None

    stdout_head = result.stdout.lstrip()[:1]
    if stdout_head not in ("[", "{"):
        logger.warning(
            "pkexec inxi returned non-JSON output: %r",
            result.stdout[:200],
        )
        return None

    import json
    from big_hardware_info.collectors.inxi_parser import InxiParser

    try:
        root_data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse root inxi output: %s", exc)
        return None

    parser = InxiParser()
    parsed = parser.parse_full(root_data)
    logger.info("Successfully collected sensitive data with root privileges")
    return parsed


def show_export_file_dialog(
    window: Adw.ApplicationWindow, filter_sensitive: bool = True,
) -> None:
    """Show the HTML save dialog after optionally collecting sensitive data."""
    sensitive_data = None if filter_sensitive else _collect_sensitive_via_pkexec()

    dialog = Gtk.FileDialog()
    dialog.set_title(_("Export Hardware Report"))
    dialog.set_modal(True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dialog.set_initial_name(f"big_hardware_info_{timestamp}.html")

    filter_html = Gtk.FileFilter()
    filter_html.set_name(_("HTML files"))
    filter_html.add_mime_type("text/html")
    filter_html.add_pattern("*.html")

    filters = Gio.ListStore.new(Gtk.FileFilter)
    filters.append(filter_html)
    dialog.set_filters(filters)

    def on_response(dlg: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = dlg.save_finish(result)
        except GLib.Error as exc:
            if exc.code != Gtk.DialogError.DISMISSED:
                logger.error("Export error: %s", exc)
            return
        if file:
            export_to_html(
                window,
                file.get_path(),
                filter_sensitive=filter_sensitive,
                pre_collected_data=sensitive_data,
            )

    dialog.save(window, None, on_response)


def start_share_upload(
    window: Adw.ApplicationWindow, filter_sensitive: bool = True,
) -> None:
    """Generate, upload, and notify the report via filebin in a worker thread."""
    sensitive_data = None if filter_sensitive else _collect_sensitive_via_pkexec()

    progress_dialog = Adw.AlertDialog()
    progress_dialog.set_heading(_("Uploading Report"))
    progress_dialog.set_body(_("Generating and uploading your hardware report..."))

    spinner = Gtk.Spinner()
    spinner.set_size_request(48, 48)
    spinner.start()
    spinner.set_halign(Gtk.Align.CENTER)
    spinner.set_margin_top(16)
    spinner.set_margin_bottom(16)
    progress_dialog.set_extra_child(spinner)

    progress_dialog.add_response("cancel", _("Cancel"))

    window._share_dialog = progress_dialog
    window._share_canceled = False

    def on_progress_response(dialog: Adw.AlertDialog, response: str) -> None:
        if response == "cancel":
            window._share_canceled = True
            dialog.close()
    
    progress_dialog.connect("response", on_progress_response)
    progress_dialog.present(window)

    def share_in_thread() -> None:
        import tempfile

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = os.path.join(tempfile.gettempdir(), f"big_hardware_info_{timestamp}.html")

        try:
            from big_hardware_info.export.html_generator import HtmlGenerator

            export_data = _resolve_export_data(
                window, filter_sensitive, sensitive_data,
            )

            from big_hardware_info.models.hardware_info import HardwareInfo
            hw_info = HardwareInfo.from_dict(export_data)

            generator = HtmlGenerator(hw_info)
            html_content = generator.generate()

            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            if window._share_canceled:
                return

            from big_hardware_info.export.uploader import upload_to_filebin
            success, result = upload_to_filebin(temp_file)

            if not window._share_canceled:
                GLib.idle_add(lambda s=success, r=result: _on_share_complete(window, s, r))

        except Exception as err:
            logger.exception("Share upload failed")
            if not window._share_canceled:
                error_msg = str(err)
                GLib.idle_add(lambda msg=error_msg: _on_share_complete(window, False, msg))

    threading.Thread(target=share_in_thread, daemon=True).start()


def _resolve_export_data(
    window: Adw.ApplicationWindow,
    filter_sensitive: bool,
    pre_collected: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Pick which hardware dict to export: filtered re-collection, root merge, or current."""
    if filter_sensitive:
        from big_hardware_info.collectors.inxi_collector import InxiCollector
        from big_hardware_info.collectors.inxi_parser import InxiParser

        collector = InxiCollector()
        filtered_inxi = collector.collect(filter_sensitive=True)

        if "data" in filtered_inxi:
            parser = InxiParser()
            parsed_filtered = parser.parse_full(filtered_inxi["data"])
            export_data = dict(window.hardware_data)
            export_data.update(parsed_filtered)
            return export_data
        return window.hardware_data

    if pre_collected:
        export_data = _merge_hardware_data(window.hardware_data, pre_collected)
        export_data["root_collected"] = True
        logger.info("Using pre-collected sensitive data for export/upload")
        return export_data

    return window.hardware_data


def _on_share_complete(
    window: Adw.ApplicationWindow, success: bool, result: str,
) -> None:
    if hasattr(window, "_share_dialog") and window._share_dialog:
        window._share_dialog.close()
        window._share_dialog = None

    if success:
        _show_share_success_dialog(window, result)
    else:
        show_share_error(window, result)


def _show_share_success_dialog(window: Adw.ApplicationWindow, url: str) -> None:
    clipboard = Gdk.Display.get_default().get_clipboard()
    clipboard.set(url)

    dialog = Adw.AlertDialog()
    dialog.set_heading(_("Report Uploaded Successfully"))
    dialog.set_body(_("Your report has been uploaded. The link is available for 7 days."))

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    content.set_margin_top(12)

    url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    url_box.add_css_class("card")

    url_entry = Gtk.Entry()
    url_entry.set_text(url)
    url_entry.set_editable(False)
    url_entry.set_hexpand(True)
    url_entry.add_css_class("monospace")
    url_box.append(url_entry)

    copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
    copy_btn.set_tooltip_text(_("Copy URL to clipboard"))
    copy_btn.add_css_class("flat")

    def on_copy_clicked(btn: Gtk.Button) -> None:
        Gdk.Display.get_default().get_clipboard().set(url)
        btn.set_icon_name("emblem-ok-symbolic")
        btn.add_css_class("success")
        GLib.timeout_add(1500, lambda: (btn.set_icon_name("edit-copy-symbolic"), btn.remove_css_class("success")))

    copy_btn.connect("clicked", on_copy_clicked)
    url_box.append(copy_btn)

    content.append(url_box)

    info_label = Gtk.Label(label=_("Tip: Click the copy button or select the URL to copy it."))
    info_label.add_css_class("dim-label")
    info_label.add_css_class("caption")
    content.append(info_label)

    dialog.set_extra_child(content)

    dialog.add_response("close", _("Close"))
    dialog.add_response("open", _("Open in Browser"))
    dialog.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("close")

    window._shared_url = url

    def on_response(dlg: Adw.AlertDialog, response: str) -> None:
        dlg.close()
        if response == "open" and hasattr(window, "_shared_url"):
            window._open_url(window._shared_url)

    dialog.connect("response", on_response)
    dialog.present(window)


def show_share_error(window: Adw.ApplicationWindow, error_message: str) -> None:
    dialog = Adw.AlertDialog()
    dialog.set_heading(_("Upload Failed"))
    dialog.set_body(_("Could not upload the report:\n\n") + str(error_message))
    dialog.add_response("close", _("Close"))
    dialog.present(window)


def export_to_html(
    window: Adw.ApplicationWindow,
    file_path: str,
    filter_sensitive: bool = True,
    pre_collected_data: Optional[dict[str, Any]] = None,
) -> None:
    """Generate the HTML report in a worker thread and notify on completion."""
    from big_hardware_info.export.html_generator import HtmlGenerator

    window.set_cursor(Gdk.Cursor.new_from_name("wait", None))

    def generate_html() -> None:
        try:
            export_data = _resolve_export_data(
                window, filter_sensitive, pre_collected_data,
            )

            from big_hardware_info.models.hardware_info import HardwareInfo
            hw_info = HardwareInfo.from_dict(export_data)

            generator = HtmlGenerator(hw_info)
            html_content = generator.generate()

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            GLib.idle_add(lambda p=file_path: _on_export_complete(window, p, None))

        except Exception as err:
            logger.exception("Export error")
            error_msg = str(err)
            GLib.idle_add(lambda p=file_path, msg=error_msg: _on_export_complete(window, p, msg))

    threading.Thread(target=generate_html, daemon=True).start()


def _on_export_complete(
    window: Adw.ApplicationWindow,
    file_path: str,
    error: Optional[str] = None,
) -> bool:
    window.set_cursor(None)

    if error:
        dialog = Adw.AlertDialog()
        dialog.set_heading(_("Export Failed"))
        dialog.set_body(_("Could not export the report:\n\n") + str(error))
        dialog.add_response("close", _("Close"))
        dialog.present(window)
        return False

    dialog = Adw.AlertDialog()
    dialog.set_heading(_("Report Exported"))
    dialog.set_body(
        _("Report saved successfully to:\n\n") + os.path.basename(file_path)
    )

    dialog.add_response("close", _("Close"))
    dialog.add_response("open", _("Open in Browser"))
    dialog.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("open")
    dialog.set_close_response("close")

    def on_response(dlg: Adw.AlertDialog, response: str) -> None:
        dlg.close()
        if response != "open":
            return
        import subprocess
        try:
            subprocess.Popen(["xdg-open", file_path])
        except OSError as exc:
            logger.error("Failed to open browser: %s", exc)
            error_toast = Adw.Toast.new(_("Failed to open browser"))
            error_toast.set_timeout(3)
            if hasattr(window, "toast_overlay"):
                window.toast_overlay.add_toast(error_toast)

    dialog.connect("response", on_response)
    dialog.present(window)

    return False
