"""
Section renderers for Hardware Reporter.

Contains rendering functions for each hardware category section.
Uses the builders module for consistent and compact UI construction.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from app.ui import builders as ui
from app.utils.i18n import _


def render_summary(
    container: Gtk.Box,
    data: Dict[str, Any],
    on_export: Callable,
    on_share: Callable,
    on_copy: Callable
) -> None:
    """
    Render the summary/overview section.
    
    Args:
        container: Parent container to append widgets to.
        data: Hardware data dictionary.
        on_export: Callback for export button.
        on_share: Callback for share button.
        on_copy: Callback for copy button (takes text and title).
    """
    gpu_data = data.get("gpu", {})
    memory_data = data.get("memory", {})
    system_data = data.get("system", {})
    disk_usage = data.get("disk_usage", {})
    
    # Quick Actions row
    actions_row = ui.row(spacing=16)
    actions_row.set_homogeneous(True)
    actions_row.set_margin_bottom(24)
    
    actions_row.append(ui.action_card(
        "document-save-symbolic",
        "Export Report",
        "Save a complete HTML report of your hardware to share with support or keep for reference.",
        "Export",
        on_export
    ))
    
    actions_row.append(ui.action_card(
        "send-to-symbolic",
        "Share Online",
        "Upload your hardware report to get a shareable link for forums or support tickets.",
        "Share",
        on_share
    ))
    
    container.append(actions_row)
    
    # System Overview - Two cards side by side
    overview_row = ui.row(spacing=16)
    overview_row.set_homogeneous(True)
    overview_row.set_margin_bottom(8)
    
    # Left card - Usage Overview
    left_card = _render_usage_card(memory_data, disk_usage, on_copy)
    overview_row.append(left_card)
    
    # Right card - System Info
    right_card = _render_system_info_card(gpu_data, system_data, on_copy)
    overview_row.append(right_card)
    
    container.append(overview_row)


def _render_usage_card(
    memory_data: Dict[str, Any],
    disk_usage: Dict[str, Any],
    on_copy: Callable
) -> Gtk.Box:
    """Render the usage overview card (RAM + Partition)."""
    card = ui.card()
    
    # Header
    header = ui.row(spacing=8)
    header.append(ui.title(_("Usage Overview")))
    header.get_first_child().set_hexpand(True)
    
    # Build copy text
    def get_copy_text():
        lines = [
            "=== Usage Overview ===",
            "",
            f"Memory RAM: {memory_data.get('total', 'Unknown')}",
            f"  Used: {memory_data.get('used', 'N/A')}",
            f"  Usage: {memory_data.get('used_percent', 'N/A')}%",
            "",
            f"Root Partition: {disk_usage.get('device', disk_usage.get('mount_point', '/'))}",
            f"  Size: {disk_usage.get('size', 'Unknown')}",
            f"  Used: {disk_usage.get('used', 'Unknown')}",
            f"  Free: {disk_usage.get('available', 'Unknown')}",
            f"  Usage: {disk_usage.get('use_percent', 'N/A')}",
        ]
        return "\n".join(lines)
    
    header.append(ui.copy_button(on_click=lambda b: on_copy(get_copy_text(), _("Usage Overview"))))
    card.append(header)
    
    # RAM Section
    ram_total = memory_data.get("total", "Unknown")
    ram_used = memory_data.get("used", "")
    ram_percent = memory_data.get("used_percent", 0)
    
    ram_display = str(ram_total).replace("GiB", "GB") if "GiB" in str(ram_total) else str(ram_total)
    ram_used_clean = ram_used.split("(")[0].strip() if "(" in str(ram_used) else ram_used
    
    ram_row = ui.row(spacing=8)
    ram_row.append(ui.dim_label("Memory RAM:"))
    ram_row.append(ui.heading(ram_display))
    card.append(ram_row)
    
    # RAM details
    details = ui.grid()
    details.attach(ui.dim_label("Used", caption=True), 0, 0, 1, 1)
    details.attach(ui.label(str(ram_used_clean) or "N/A"), 1, 0, 1, 1)
    card.append(details)
    
    # RAM progress bar
    if isinstance(ram_percent, (int, float)) and ram_percent > 0:
        card.append(ui.progress_bar(ram_percent / 100.0))
    
    card.append(ui.separator(margins=(4, 4)))
    
    # Partition Section
    partition = disk_usage.get("device", "") or disk_usage.get("mount_point", "/")
    part_size = disk_usage.get("size", "Unknown")
    used_space = disk_usage.get("used", "Unknown")
    free_space = disk_usage.get("available", "Unknown")
    use_percent_str = disk_usage.get("use_percent", "0%")
    
    used_percent = 0
    try:
        if use_percent_str and use_percent_str != "Unknown":
            used_percent = float(str(use_percent_str).replace("%", "").strip())
    except (ValueError, TypeError):
        pass
    
    part_row = ui.row(spacing=8)
    part_row.append(ui.dim_label("Root Partition:"))
    part_row.append(ui.heading(partition))
    card.append(part_row)
    
    # Partition details
    part_grid = ui.grid()
    part_grid.attach(ui.dim_label("Size", caption=True), 0, 0, 1, 1)
    part_grid.attach(ui.label(part_size), 1, 0, 1, 1)
    part_grid.attach(ui.dim_label("Used", caption=True), 2, 0, 1, 1)
    part_grid.attach(ui.label(used_space), 3, 0, 1, 1)
    part_grid.attach(ui.dim_label("Free", caption=True), 4, 0, 1, 1)
    part_grid.attach(ui.label(free_space), 5, 0, 1, 1)
    card.append(part_grid)
    
    # Partition progress bar
    if used_percent > 0:
        card.append(ui.progress_bar(used_percent / 100.0))
    
    return card


def _render_system_info_card(
    gpu_data: Dict[str, Any],
    system_data: Dict[str, Any],
    on_copy: Callable
) -> Gtk.Box:
    """Render the system info card (GPU, Kernel, Install Date)."""
    card = ui.card()
    
    # Header
    header = ui.row(spacing=8)
    header.append(ui.title(_("System Info")))
    header.get_first_child().set_hexpand(True)
    
    # Gather info
    gpus = gpu_data.get("devices", [])
    gpu_name = gpus[0].get("model", "Unknown") if gpus else "Unknown"
    
    kernel = system_data.get("kernel", "Unknown")
    install_date = system_data.get("install_date", "Unknown")
    
    def get_copy_text():
        lines = [
            "=== System Info ===",
            "",
            f"Video: {gpu_name}",
            f"Kernel: {kernel}",
            f"Install Date: {install_date}",
        ]
        return "\n".join(lines)
    
    header.append(ui.copy_button(on_click=lambda b: on_copy(get_copy_text(), _("System Info"))))
    card.append(header)
    
    # GPU Row
    gpu_row = ui.row(spacing=8)
    gpu_row.append(ui.dim_label("Video:"))
    gpu_lbl = ui.heading(gpu_name)
    gpu_lbl.set_hexpand(True)
    gpu_lbl.set_wrap(True)
    gpu_row.append(gpu_lbl)
    card.append(gpu_row)
    
    card.append(ui.separator(margins=(4, 4)))
    
    # Kernel Row
    kernel_row = ui.row(spacing=8)
    kernel_row.append(ui.dim_label("Kernel:"))
    kernel_row.append(ui.heading(kernel))
    card.append(kernel_row)
    
    card.append(ui.separator(margins=(4, 4)))
    
    # Install Date Row
    date_row = ui.row(spacing=8)
    date_row.append(ui.dim_label("Install Date:"))
    date_row.append(ui.heading(install_date))
    card.append(date_row)
    
    return card


def render_battery(
    container: Gtk.Box,
    data: Dict[str, Any],
    on_copy: Callable
) -> None:
    """Render the battery section."""
    battery_data = data.get("battery", {})
    
    if not battery_data or battery_data.get("status") == "Not present":
        container.append(ui.no_data_label(_("No battery detected")))
        return
    
    # Battery card
    model = battery_data.get("model", "Unknown Battery")
    status = battery_data.get("status", "Unknown")
    charge = battery_data.get("charge", 0)
    
    left_items = [
        (_("Model"), model),
        (_("Status"), status),
        (_("Charge"), f"{charge}%"),
        (_("Vendor"), battery_data.get("vendor", "")),
    ]
    
    right_items = [
        (_("Technology"), battery_data.get("technology", "")),
        (_("Voltage"), battery_data.get("voltage", "")),
        (_("Energy"), battery_data.get("energy", "")),
        (_("Capacity"), battery_data.get("capacity", "")),
    ]
    
    title_widgets = [
        ui.copy_button(on_click=lambda b: on_copy(_format_battery_copy(battery_data), "Battery"))
    ]
    
    card = ui.two_column_card(model, left_items, right_items, title_widgets)
    
    # Add charge bar
    if isinstance(charge, (int, float)) and charge > 0:
        bar_container = ui.box(margin_bottom=0)
        bar_container.append(ui.progress_bar(charge / 100.0))
        card.append(bar_container)
    
    container.append(card)


def _format_battery_copy(data: Dict[str, Any]) -> str:
    """Format battery data for clipboard."""
    lines = [
        f"=== {data.get('model', 'Battery')} ===",
        "",
        f"Status: {data.get('status', 'Unknown')}",
        f"Charge: {data.get('charge', 0)}%",
        f"Vendor: {data.get('vendor', 'N/A')}",
        f"Technology: {data.get('technology', 'N/A')}",
        f"Voltage: {data.get('voltage', 'N/A')}",
        f"Energy: {data.get('energy', 'N/A')}",
        f"Capacity: {data.get('capacity', 'N/A')}",
    ]
    return "\n".join(lines)


def render_bluetooth(
    container: Gtk.Box,
    data: Dict[str, Any],
    on_copy: Callable,
    on_open_url: Callable
) -> None:
    """Render the Bluetooth section."""
    bt_data = data.get("bluetooth", {})
    devices = bt_data.get("devices", [])
    
    if not devices:
        container.append(ui.no_data_label(_("No Bluetooth devices detected")))
        return
    
    for device in devices:
        name = device.get("name", "Unknown Bluetooth Device")
        vendor = device.get("vendor", "")
        bus_id = device.get("bus_id", "")
        chip_id = device.get("chip_id", "")
        driver = device.get("driver", "")
        
        # Build URL if chip_id available
        info_url = ""
        if chip_id and ":" in chip_id:
            url_id = chip_id.replace(":", "-")
            info_url = f"https://linux-hardware.org/?id=usb:{url_id}"
        
        left_items = [
            (_("Vendor"), vendor),
            (_("Chip ID"), chip_id),
        ]
        
        right_items = [
            (_("Bus ID"), bus_id),
            (_("Driver"), driver),
        ]
        
        title_widgets = []
        if info_url:
            title_widgets.append(ui.flat_button(
                label_text=_("info"),
                tooltip=_("View device info on Linux Hardware Database"),
                on_click=lambda b, u=info_url: on_open_url(u)
            ))
        title_widgets.append(ui.copy_button(on_click=lambda b, d=device, n=name: on_copy(
            _format_device_copy(d, n), n
        )))
        
        card = ui.two_column_card(name, left_items, right_items, title_widgets)
        container.append(card)


def render_sensors(
    container: Gtk.Box,
    data: Dict[str, Any],
    on_copy: Callable
) -> None:
    """Render the sensors section."""
    sensors_data = data.get("sensors", {})
    temps = sensors_data.get("temperatures", {})
    fans = sensors_data.get("fans", {})
    
    if not temps and not fans:
        container.append(ui.no_data_label(_("No sensors detected")))
        return
    
    # Temperature sensors
    if temps:
        temp_card = ui.card()
        
        header = ui.row(spacing=8)
        header.append(ui.title(_("Temperatures")))
        header.get_first_child().set_hexpand(True)
        header.append(ui.copy_button(on_click=lambda b: on_copy(_format_temps_copy(temps), "Temperatures")))
        temp_card.append(header)
        
        grid = ui.grid(row_spacing=8, col_spacing=24)
        row = 0
        
        for sensor_name, temp_value in temps.items():
            grid.attach(ui.dim_label(sensor_name), 0, row, 1, 1)
            
            # Color based on temperature
            temp_str = str(temp_value)
            temp_num = 0
            try:
                temp_num = float(temp_str.replace("°C", "").replace("C", "").strip())
            except (ValueError, TypeError):
                pass
            
            temp_lbl = ui.label(temp_str, selectable=True)
            if temp_num > 80:
                temp_lbl.add_css_class("error")
            elif temp_num > 60:
                temp_lbl.add_css_class("warning")
            grid.attach(temp_lbl, 1, row, 1, 1)
            row += 1
        
        temp_card.append(grid)
        container.append(temp_card)
    
    # Fan sensors
    if fans:
        fan_card = ui.card()
        
        header = ui.row(spacing=8)
        header.append(ui.title(_("Fans")))
        header.get_first_child().set_hexpand(True)
        header.append(ui.copy_button(on_click=lambda b: on_copy(_format_fans_copy(fans), "Fans")))
        fan_card.append(header)
        
        grid = ui.grid(row_spacing=8, col_spacing=24)
        row = 0
        
        for fan_name, rpm in fans.items():
            grid.attach(ui.dim_label(fan_name), 0, row, 1, 1)
            grid.attach(ui.label(str(rpm), selectable=True), 1, row, 1, 1)
            row += 1
        
        fan_card.append(grid)
        container.append(fan_card)


def _format_temps_copy(temps: Dict[str, Any]) -> str:
    """Format temperatures for clipboard."""
    lines = ["=== Temperatures ===", ""]
    for name, value in temps.items():
        lines.append(f"{name}: {value}")
    return "\n".join(lines)


def _format_fans_copy(fans: Dict[str, Any]) -> str:
    """Format fans for clipboard."""
    lines = ["=== Fans ===", ""]
    for name, rpm in fans.items():
        lines.append(f"{name}: {rpm}")
    return "\n".join(lines)


def _format_device_copy(device: Dict[str, Any], name: str) -> str:
    """Format device data for clipboard."""
    lines = [f"=== {name} ===", ""]
    for key, value in device.items():
        if value and key not in ("raw",):
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def render_printers(
    container: Gtk.Box,
    data: Dict[str, Any],
    on_copy: Callable
) -> None:
    """Render the printers section."""
    printers = data.get("printers", [])
    
    if not printers:
        container.append(ui.no_data_label(_("No printers detected")))
        return
    
    for printer in printers:
        name = printer.get("name", "Unknown Printer")
        
        left_items = [
            (_("Status"), printer.get("status", "")),
            (_("Location"), printer.get("location", "")),
            (_("Make/Model"), printer.get("make_model", "")),
        ]
        
        right_items = [
            (_("Connection"), printer.get("connection", "")),
            (_("Device URI"), printer.get("device_uri", "")),
            (_("Default"), printer.get("default", "")),
        ]
        
        title_widgets = [
            ui.copy_button(on_click=lambda b, p=printer, n=name: on_copy(_format_device_copy(p, n), n))
        ]
        
        card = ui.two_column_card(name, left_items, right_items, title_widgets)
        container.append(card)


def render_webcams(
    container: Gtk.Box,
    data: Dict[str, Any],
    on_copy: Callable,
    on_open_url: Callable
) -> None:
    """Render the webcams section."""
    webcam_data = data.get("webcam", {})
    v4l2_webcams = webcam_data.get("devices", [])
    
    gpu_data = data.get("gpu", {})
    inxi_webcams = gpu_data.get("webcams", [])
    
    # Combine data
    webcams = []
    if v4l2_webcams:
        for v4l2_cam in v4l2_webcams:
            combined = dict(v4l2_cam)
            for inxi_cam in inxi_webcams:
                inxi_name = inxi_cam.get("name", "").lower()
                v4l2_name = v4l2_cam.get("name", "").lower()
                if inxi_name and v4l2_name and (inxi_name in v4l2_name or v4l2_name in inxi_name):
                    combined.update({
                        "chip_id": inxi_cam.get("chip_id", ""),
                        "bus_id": inxi_cam.get("bus_id", ""),
                        "type": inxi_cam.get("type", ""),
                        "speed": inxi_cam.get("speed", ""),
                    })
                    break
            webcams.append(combined)
    elif inxi_webcams:
        webcams = inxi_webcams
    
    if not webcams:
        container.append(ui.no_data_label(_("No webcams detected")))
        return
    
    for webcam in webcams:
        name = webcam.get("name", "Unknown Webcam")
        chip_id = webcam.get("chip_id", "")
        
        info_url = ""
        if chip_id and ":" in chip_id:
            url_id = chip_id.replace(":", "-")
            info_url = f"https://linux-hardware.org/?id=usb:{url_id}"
        
        left_items = [
            (_("Resolution"), webcam.get("resolution", "")),
            (_("Format"), webcam.get("pixel_format", "")),
            (_("Chip ID"), chip_id),
            (_("Driver"), webcam.get("driver", "")),
        ]
        
        right_items = [
            (_("Colorspace"), webcam.get("colorspace", "")),
            (_("Max FPS"), webcam.get("max_fps", "")),
            (_("Driver Version"), webcam.get("driver_version", "")),
            (_("Device"), webcam.get("device_path", "")),
        ]
        
        title_widgets = []
        if info_url:
            title_widgets.append(ui.flat_button(
                label_text=_("info"),
                tooltip=_("View device info on Linux Hardware Database"),
                on_click=lambda b, u=info_url: on_open_url(u)
            ))
        title_widgets.append(ui.copy_button(on_click=lambda b, w=webcam, n=name: on_copy(
            _format_device_copy(w, n), n
        )))
        
        card = ui.two_column_card(name, left_items, right_items, title_widgets)
        container.append(card)
