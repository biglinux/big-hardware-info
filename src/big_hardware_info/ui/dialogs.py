"""Dialog helpers for the hardware info application.

This module contains helper functions and classes for creating and managing
various dialogs used in the application (export, share, privacy, etc.).
"""

import os
import threading
import logging
from datetime import datetime
from gettext import gettext as _

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib, Gio

logger = logging.getLogger(__name__)


def show_privacy_export_dialog(window, is_upload: bool = False):
    """Show privacy options dialog before exporting or uploading.
    
    Displays a dialog with a switch to include/exclude sensitive data
    such as serial numbers, MAC addresses, etc.
    
    Args:
        window: Parent window instance
        is_upload: If True, this is for upload; if False, for export.
    """
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
    
    # Create content box for the switch
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    content.set_margin_top(12)
    
    # Privacy warning card
    privacy_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    privacy_box.add_css_class("card")
    privacy_box.set_margin_start(0)
    privacy_box.set_margin_end(0)
    
    warning_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
    warning_icon.set_pixel_size(24)
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
    
    # Switch row for sensitive data
    switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    switch_box.set_margin_top(8)
    
    switch_label = Gtk.Label(label=_("Include sensitive information"))
    switch_label.set_hexpand(True)
    switch_label.set_xalign(0)
    switch_box.append(switch_label)
    
    sensitive_switch = Gtk.Switch()
    sensitive_switch.set_active(False)  # Default: don't include sensitive info
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


def show_export_file_dialog(window, filter_sensitive: bool = True):
    """Show the file save dialog for export.
    
    Args:
        window: Parent window instance
        filter_sensitive: If True, filter out sensitive data.
    """
    dialog = Gtk.FileDialog()
    dialog.set_title(_("Export Hardware Report"))
    dialog.set_modal(True)
    
    # Set default filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dialog.set_initial_name(f"big_hardware_info_{timestamp}.html")
    
    # Set filter
    filter_html = Gtk.FileFilter()
    filter_html.set_name(_("HTML files"))
    filter_html.add_mime_type("text/html")
    filter_html.add_pattern("*.html")
    
    filters = Gio.ListStore.new(Gtk.FileFilter)
    filters.append(filter_html)
    dialog.set_filters(filters)
    
    def on_response(dlg, result):
        try:
            file = dlg.save_finish(result)
            if file:
                file_path = file.get_path()
                export_to_html(window, file_path, filter_sensitive=filter_sensitive)
        except GLib.Error as e:
            if e.code != Gtk.DialogError.DISMISSED:
                logger.error(f"Export error: {e}")
    
    dialog.save(window, None, on_response)


def start_share_upload(window, filter_sensitive: bool = True):
    """Start the share upload process with progress dialog.
    
    Args:
        window: Parent window instance
        filter_sensitive: If True, filter out sensitive data like serial
                        numbers and MAC addresses.
    """
    # Create progress dialog
    progress_dialog = Adw.AlertDialog()
    progress_dialog.set_heading(_("Uploading Report"))
    progress_dialog.set_body(_("Generating and uploading your hardware report..."))
    
    # Add spinner
    spinner = Gtk.Spinner()
    spinner.set_size_request(48, 48)
    spinner.start()
    spinner.set_halign(Gtk.Align.CENTER)
    spinner.set_margin_top(16)
    spinner.set_margin_bottom(16)
    progress_dialog.set_extra_child(spinner)
    
    # Add cancel button
    progress_dialog.add_response("cancel", _("Cancel"))
    
    # Store dialog reference on window
    window._share_dialog = progress_dialog
    window._share_canceled = False
    
    def on_progress_response(dialog, response):
        if response == "cancel":
            window._share_canceled = True
            dialog.close()
    
    progress_dialog.connect("response", on_progress_response)
    progress_dialog.present(window)
    
    # Do everything in background thread to avoid UI freeze
    def share_in_thread():
        import tempfile
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = os.path.join(tempfile.gettempdir(), f"big_hardware_info_{timestamp}.html")
        
        try:
            # Generate HTML in thread
            from big_hardware_info.export.html_generator import HtmlGenerator
            
            # If filtering sensitive data, collect fresh with -z flag
            if filter_sensitive:
                from big_hardware_info.collectors.inxi_collector import InxiCollector
                from big_hardware_info.collectors.inxi_parser import InxiParser
                
                collector = InxiCollector()
                filtered_inxi = collector.collect(filter_sensitive=True)
                
                if "data" in filtered_inxi:
                    # Parse the filtered data
                    parser = InxiParser()
                    parsed_filtered = parser.parse_full(filtered_inxi["data"])
                    
                    # Start with current data and update with filtered
                    export_data = dict(window.hardware_data)
                    for key, value in parsed_filtered.items():
                        export_data[key] = value
                else:
                    export_data = window.hardware_data
            else:
                export_data = window.hardware_data
            
            # Create strongly typed HardwareInfo object for the generator
            from big_hardware_info.models.hardware_info import HardwareInfo
            hw_info = HardwareInfo.from_dict(export_data)

            generator = HtmlGenerator(hw_info)
            html_content = generator.generate()
            
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            if window._share_canceled:
                return
            
            # Upload
            from big_hardware_info.export.uploader import upload_to_filebin
            success, result = upload_to_filebin(temp_file)
            
            if not window._share_canceled:
                GLib.idle_add(lambda s=success, r=result: _on_share_complete(window, s, r))
                
        except Exception as err:
            if not window._share_canceled:
                error_msg = str(err)
                GLib.idle_add(lambda msg=error_msg: _on_share_complete(window, False, msg))
    
    threading.Thread(target=share_in_thread, daemon=True).start()


def _on_share_complete(window, success: bool, result: str):
    """Handle share completion - shows result dialog."""
    # Close progress dialog
    if hasattr(window, "_share_dialog") and window._share_dialog:
        window._share_dialog.close()
        window._share_dialog = None
    
    if success:
        _show_share_success_dialog(window, result)
    else:
        show_share_error(window, result)


def _show_share_success_dialog(window, url: str):
    """Show success dialog with URL and copy button."""
    # Copy URL to clipboard
    clipboard = Gdk.Display.get_default().get_clipboard()
    clipboard.set(url)
    
    dialog = Adw.AlertDialog()
    dialog.set_heading(_("Report Uploaded Successfully"))
    dialog.set_body(_("Your report has been uploaded. The link is available for 7 days."))
    
    # Create content with URL entry and copy button
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    content.set_margin_top(12)
    
    # URL display box
    url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    url_box.add_css_class("card")
    
    # Editable URL entry for easy selection
    url_entry = Gtk.Entry()
    url_entry.set_text(url)
    url_entry.set_editable(False)
    url_entry.set_hexpand(True)
    url_entry.add_css_class("monospace")
    url_box.append(url_entry)
    
    # Copy button
    copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
    copy_btn.set_tooltip_text(_("Copy URL to clipboard"))
    copy_btn.add_css_class("flat")
    
    def on_copy_clicked(btn):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(url)
        # Show feedback
        btn.set_icon_name("emblem-ok-symbolic")
        btn.add_css_class("success")
        GLib.timeout_add(1500, lambda: (btn.set_icon_name("edit-copy-symbolic"), btn.remove_css_class("success")))
    
    copy_btn.connect("clicked", on_copy_clicked)
    url_box.append(copy_btn)
    
    content.append(url_box)
    
    # Info label
    info_label = Gtk.Label(label=_("Tip: Click the copy button or select the URL to copy it."))
    info_label.add_css_class("dim-label")
    info_label.add_css_class("caption")
    content.append(info_label)
    
    dialog.set_extra_child(content)
    
    # Add buttons
    dialog.add_response("close", _("Close"))
    dialog.add_response("open", _("Open in Browser"))
    dialog.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("close")
    
    # Store URL for later
    window._shared_url = url
    
    def on_response(dlg, response):
        dlg.close()
        if response == "open" and hasattr(window, "_shared_url"):
            window._open_url(window._shared_url)
    
    dialog.connect("response", on_response)
    dialog.present(window)


def show_share_error(window, error_message: str):
    """Show share error dialog."""
    dialog = Adw.AlertDialog()
    dialog.set_heading(_("Upload Failed"))
    dialog.set_body(
        _("Could not upload the report:\n\n{error}").format(error=error_message)
    )
    dialog.add_response("close", _("Close"))
    dialog.present(window)


def export_to_html(window, file_path: str, filter_sensitive: bool = True):
    """Export hardware data to HTML file.
    
    Args:
        window: Parent window instance
        file_path: Path to save the HTML file.
        filter_sensitive: If True, filter out sensitive data like serial
                        numbers and MAC addresses.
    """
    from big_hardware_info.export.html_generator import HtmlGenerator
    
    # Set cursor to wait (loading)
    window.set_cursor(Gdk.Cursor.new_from_name("wait", None))
    
    def generate_html():
        """Generate HTML in background to avoid blocking the UI loop."""
        try:
            # If filtering sensitive data, recollect with -z flag and re-parse
            if filter_sensitive:
                from big_hardware_info.collectors.inxi_collector import InxiCollector
                from big_hardware_info.collectors.inxi_parser import InxiParser
                
                collector = InxiCollector()
                filtered_inxi = collector.collect(filter_sensitive=True)
                
                if "data" in filtered_inxi:
                    # Parse the filtered data
                    parser = InxiParser()
                    parsed_filtered = parser.parse_full(filtered_inxi["data"])
                    
                    # Start with current data and update with filtered
                    export_data = dict(window.hardware_data)
                    for key, value in parsed_filtered.items():
                        export_data[key] = value
                else:
                    export_data = window.hardware_data
            else:
                export_data = window.hardware_data
            
            # Create strongly typed HardwareInfo object for the generator
            from big_hardware_info.models.hardware_info import HardwareInfo
            hw_info = HardwareInfo.from_dict(export_data)

            generator = HtmlGenerator(hw_info)
            html_content = generator.generate()
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Schedule UI update on main thread
            GLib.idle_add(lambda p=file_path: _on_export_complete(window, p, None))
            
        except Exception as err:
            logger.error(f"Export error: {err}")
            error_msg = str(err)
            GLib.idle_add(lambda p=file_path, msg=error_msg: _on_export_complete(window, p, msg))
    
    # Run in background thread
    threading.Thread(target=generate_html, daemon=True).start()


def _on_export_complete(window, file_path: str, error: str = None):
    """Handle export completion - restore cursor and show dialog."""
    # Restore cursor
    window.set_cursor(None)
    
    if error:
        # Show error dialog
        dialog = Adw.AlertDialog()
        dialog.set_heading(_("Export Failed"))
        dialog.set_body(
            _("Could not export the report:\n\n{error}").format(error=error)
        )
        dialog.add_response("close", _("Close"))
        dialog.present(window)
    else:
        # Show success dialog asking if user wants to open in browser
        dialog = Adw.AlertDialog()
        dialog.set_heading(_("Report Exported"))
        dialog.set_body(
            _("Report saved successfully to:\n\n{file}").format(
                file=os.path.basename(file_path)
            )
        )
        
        dialog.add_response("close", _("Close"))
        dialog.add_response("open", _("Open in Browser"))
        dialog.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("open")
        dialog.set_close_response("close")
        
        def on_response(dlg, response):
            dlg.close()
            if response == "open":
                import subprocess
                try:
                    subprocess.Popen(["xdg-open", file_path])
                except Exception as e:
                    logger.error(f"Failed to open browser: {e}")
                    error_toast = Adw.Toast.new(_("Failed to open browser"))
                    error_toast.set_timeout(3)
                    if hasattr(window, "toast_overlay"):
                        window.toast_overlay.add_toast(error_toast)
        
        dialog.connect("response", on_response)
        dialog.present(window)
    
    return False
