"""Build a compact, redacted text block to paste into an AI chatbot.

Goal: small (<50 KB), dedup-friendly, no PII/serials/UUIDs/MACs/IPs. Enough
context for the model to triage hardware/system issues when the user pastes
their problem description plus this report.
"""

from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from typing import Any, Iterable

from big_hardware_info.utils.i18n import _

MAX_BYTES = 50_000
MAX_ERROR_LINES = 30
MAX_LINE_LEN = 400

_PKG_MANAGERS: tuple[tuple[str, str], ...] = (
    ("pacman", "pacman (Arch/Manjaro)"),
    ("apt", "apt (Debian/Ubuntu)"),
    ("dnf", "dnf (Fedora/RHEL)"),
    ("zypper", "zypper (openSUSE)"),
    ("xbps-install", "xbps (Void)"),
    ("emerge", "portage (Gentoo)"),
    ("apk", "apk (Alpine)"),
    ("nix-env", "nix"),
)

_MAC_RE = re.compile(r"\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b", re.IGNORECASE)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_RE = re.compile(
    r"(?=[0-9a-f:]*[a-f])\b[0-9a-f]{0,4}(?::[0-9a-f]{0,4}){2,7}\b",
    re.IGNORECASE,
)
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_HOMEDIR_RE = re.compile(r"/home/[^/\s]+")
_HEX_ADDR_RE = re.compile(r"\b0x[0-9a-f]{4,}\b", re.IGNORECASE)
_PID_RE = re.compile(r"\[\d+\]")
_JOURNAL_PREFIX_RE = re.compile(
    r"^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\S+\s+"
)


def build_ai_support_context_text(
    hardware_data: dict[str, Any] | None,
    max_bytes: int = MAX_BYTES,
) -> str:
    """Return a compact, redacted snapshot suitable for pasting into a chatbot."""
    data = hardware_data or {}
    lines: list[str] = []

    lines.append(_("=== AI Support Context ==="))
    lines.append(
        f"{_('Generated:')} {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    lines.append(_("Paste this below your problem description."))
    lines.append("")

    _system_block(lines, data)
    _hardware_block(lines, data)
    _network_bt_block(lines, data)
    _drivers_block(lines, data)
    _bus_block(lines, data)
    _errors_block(lines, data, "dmesg")
    _errors_block(lines, data, "journal")

    text = redact_sensitive("\n".join(lines).strip()) + "\n"
    return _truncate(text, max_bytes)


def _system_block(lines: list[str], data: dict[str, Any]) -> None:
    system = data.get("system") or {}
    kernel = data.get("kernel") or {}
    install = data.get("install_date") or {}

    distro = _str(system.get("distro"))
    kernel_version = _str(kernel.get("version")) or _str(system.get("kernel"))
    desktop = _str(system.get("desktop")) or _str(system.get("de"))
    session = _str(system.get("session_type"))
    install_date = _str(install.get("estimate")) or _str(system.get("install_date"))
    uptime = _str(system.get("uptime"))
    pkg_mgr = _detect_pkg_manager()

    lines.append(_("[System]"))
    if distro:
        lines.append(f"{_('Distro:')} {distro}")
    if kernel_version:
        lines.append(f"{_('Kernel:')} {kernel_version}")
    if desktop:
        de_line = desktop + (f" ({session})" if session else "")
        lines.append(f"{_('Desktop:')} {de_line}")
    if pkg_mgr:
        lines.append(f"{_('Package Manager:')} {pkg_mgr}")
    if install_date:
        lines.append(f"{_('Install Date:')} {install_date}")
    if uptime:
        lines.append(f"{_('Uptime:')} {uptime}")
    lines.append("")


def _hardware_block(lines: list[str], data: dict[str, Any]) -> None:
    cpu = data.get("cpu") or {}
    memory = data.get("memory") or {}
    gpu = data.get("gpu") or {}
    disk_usage = data.get("disk_usage") or {}
    disk = data.get("disk") or {}
    audio = data.get("audio") or {}
    battery = data.get("battery") or {}
    machine = data.get("machine") or {}

    lines.append(_("[Hardware]"))

    cpu_model = _str(cpu.get("model"))
    cores = cpu.get("cores")
    threads = cpu.get("threads")
    speed = _str(cpu.get("speed") or cpu.get("max_speed"))
    if cpu_model or cores:
        bits = [cpu_model or "?"]
        if cores or threads:
            bits.append(f"{cores or '?'}c/{threads or '?'}t")
        if speed:
            bits.append(f"@ {speed}")
        lines.append(f"{_('CPU:')} {' '.join(bits)}")

    mem_total = _str(memory.get("total"))
    mem_used_pct = memory.get("used_percent")
    if mem_total:
        usage = f" ({mem_used_pct:.0f}% used)" if isinstance(mem_used_pct, (int, float)) else ""
        lines.append(f"{_('RAM:')} {mem_total}{usage}")

    gpu_devices = list(_iter_devices(gpu, "devices"))
    for idx, dev in enumerate(gpu_devices, 1):
        rendered = _format_device_line(dev)
        if not rendered:
            continue
        label = _("GPU:") if len(gpu_devices) == 1 else _("GPU#%d:") % idx
        lines.append(f"{label} {rendered}")

    display_info = gpu.get("display_info") or {}
    server = _str(display_info.get("server"))
    server_v = _str(display_info.get("server_version"))
    compositor = _str(display_info.get("compositor"))
    active_gpu = _str(display_info.get("gpu"))
    driver_loaded = _str(display_info.get("driver_loaded"))
    if server or active_gpu:
        bits = []
        if server:
            bits.append(f"{server} {server_v}".strip())
        if compositor:
            bits.append(f"compositor={compositor}")
        if driver_loaded:
            bits.append(f"loaded={driver_loaded}")
        if active_gpu:
            bits.append(f"active={active_gpu}")
        lines.append(f"{_('Display:')} {', '.join(bits)}")

    opengl = gpu.get("opengl") or {}
    renderer = _str(opengl.get("renderer"))
    if renderer:
        gl_v = _str(opengl.get("version"))
        lines.append(f"{_('OpenGL:')} {gl_v} — {renderer}".rstrip(" —"))

    disk_devices = list(_iter_devices(disk, "devices"))[:4]
    for dev in disk_devices:
        name = _str(dev.get("model")) or _str(dev.get("name"))
        size = _str(dev.get("size"))
        if not name and not size:
            continue
        lines.append(f"{_('Disk:')} {name} {size}".rstrip())

    if disk_usage.get("size"):
        device = _str(disk_usage.get("mount_point") or "/")
        lines.append(
            f"{_('Root:')} {device} "
            f"{_str(disk_usage.get('size'))} "
            f"({_str(disk_usage.get('use_percent'))} used)"
        )

    audio_servers = _str(audio.get("server")) or _str(audio.get("api"))
    if audio_servers:
        lines.append(f"{_('Audio Server:')} {audio_servers}")
    for dev in _iter_devices(audio, "devices"):
        rendered = _format_device_line(dev)
        if rendered:
            lines.append(f"  - {rendered}")

    bat_status = _str(battery.get("status")) or _str(battery.get("state"))
    bat_charge = _str(battery.get("charge")) or _str(battery.get("capacity"))
    if bat_status or bat_charge:
        bits = [b for b in (bat_charge, bat_status) if b]
        lines.append(f"{_('Battery:')} {' '.join(bits)}")

    product = _str(machine.get("product")) or _str(machine.get("model"))
    vendor = _str(machine.get("vendor"))
    if product or vendor:
        lines.append(f"{_('Machine:')} {' '.join(b for b in (vendor, product) if b)}")

    lines.append("")


def _network_bt_block(lines: list[str], data: dict[str, Any]) -> None:
    network = data.get("network") or {}
    bluetooth = data.get("bluetooth") or {}

    net_devices = list(_iter_devices(network, "devices"))
    bt_devices = list(_iter_devices(bluetooth, "devices"))
    if not net_devices and not bt_devices:
        return

    lines.append(_("[Network & Bluetooth]"))
    for dev in net_devices:
        rendered = _format_device_line(dev)
        if not rendered:
            continue
        kind = _network_kind(dev)
        iface = _str(dev.get("IF")) or _str(dev.get("name"))
        state = _str(dev.get("state"))
        suffix_bits = [b for b in (iface, state) if b]
        suffix = f" ({' '.join(suffix_bits)})" if suffix_bits else ""
        lines.append(f"{kind}: {rendered}{suffix}")

    for dev in bt_devices:
        rendered = _format_device_line(dev)
        if not rendered:
            continue
        state = _str(dev.get("state"))
        bt_v = _str(dev.get("bt_version"))
        extras = [b for b in (state, f"bt v{bt_v}" if bt_v else "") if b]
        suffix = f" ({', '.join(extras)})" if extras else ""
        lines.append(f"{_('Bluetooth:')} {rendered}{suffix}")
    lines.append("")


def _network_kind(device: dict[str, Any]) -> str:
    name = (
        _str(device.get("name")).lower()
        + " "
        + _str(device.get("IF")).lower()
    )
    if any(k in name for k in ("wireless", "wi-fi", "wifi", "wlan", "wlp")):
        return _("Wi-Fi")
    if any(k in name for k in ("ethernet", "gigabit", "lan ", "enp", "eth")):
        return _("Ethernet")
    return _("Network")


def _format_device_line(device: dict[str, Any]) -> str:
    """Render `vendor name [chip_id] driver=X` for any inxi-shaped device."""
    vendor = _str(device.get("vendor"))
    name = _str(device.get("name")) or _str(device.get("model"))
    chip = _str(device.get("chip_id"))
    driver = _str(device.get("driver"))
    driver_v = _str(device.get("driver_version") or device.get("v"))

    if not (name or vendor or chip):
        return ""

    label_bits: list[str] = []
    if vendor and name and vendor.lower() not in name.lower():
        label_bits.append(f"{vendor} {name}")
    else:
        label_bits.append(name or vendor)
    if chip:
        label_bits.append(f"[{chip}]")
    if driver:
        drv = f"driver={driver}"
        if driver_v:
            drv += f" {driver_v}"
        label_bits.append(drv)
    return " ".join(label_bits)


def _drivers_block(lines: list[str], data: dict[str, Any]) -> None:
    mhwd = data.get("mhwd") or {}
    drivers_raw = _str(mhwd.get("installed_drivers"))
    kernels_raw = _str(mhwd.get("installed_kernels"))

    drivers = _parse_mhwd_names(drivers_raw)
    kernels = _parse_mhwd_names(kernels_raw)

    if not drivers and not kernels:
        return

    lines.append(_("[Drivers]"))
    if drivers:
        lines.append(f"{_('mhwd:')} {', '.join(drivers)}")
    if kernels:
        lines.append(f"{_('Kernels:')} {', '.join(kernels)}")
    lines.append("")


def _bus_block(lines: list[str], data: dict[str, Any]) -> None:
    """Embed lspci/lsusb output collected by AiDiagnosticsCollector."""
    diag = data.get("ai_diag") or {}
    lspci = _str(diag.get("lspci")) if isinstance(diag, dict) else ""
    lsusb = _str(diag.get("lsusb")) if isinstance(diag, dict) else ""
    if not lspci and not lsusb:
        return
    if lspci:
        lines.append(_("[PCI Bus — lspci]"))
        lines.extend(lspci.splitlines())
        lines.append("")
    if lsusb:
        lines.append(_("[USB Bus — lsusb]"))
        lines.extend(lsusb.splitlines())
        lines.append("")


def _errors_block(
    lines: list[str], data: dict[str, Any], kind: str,
) -> None:
    logs = data.get("logs") or {}
    if kind == "dmesg":
        section = logs.get("dmesg_errors") or {}
        raw_lines: Iterable[str] = section.get("errors") or []
        if not raw_lines:
            raw_lines = (section.get("raw") or "").splitlines()
        title = _("[Recent Errors — dmesg]")
        clean = list(raw_lines)
    else:
        section = logs.get("journal_errors") or {}
        raw_lines = (section.get("raw") or "").splitlines()
        title = _("[Recent Errors — journal]")
        clean = [_JOURNAL_PREFIX_RE.sub("", line) for line in raw_lines]

    deduped = _dedupe_errors(clean, MAX_ERROR_LINES)
    if not deduped:
        return

    lines.append(title)
    for entry in deduped:
        lines.append(f"- {entry}")
    lines.append("")


def _dedupe_errors(raw_lines: Iterable[str], limit: int) -> list[str]:
    """Keep the last `limit` unique error-shaped lines, normalized for dedup."""
    keep: dict[str, str] = {}
    for line in raw_lines:
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        if len(line) > MAX_LINE_LEN:
            line = line[:MAX_LINE_LEN] + "…"
        key = _normalize_for_dedup(line)
        if not key:
            continue
        keep[key] = line
    return list(keep.values())[-limit:]


def _normalize_for_dedup(line: str) -> str:
    text = _PID_RE.sub("[PID]", line)
    text = _HEX_ADDR_RE.sub("0xADDR", text)
    text = re.sub(r"\b\d+\b", "N", text)
    return text.lower().strip()


def redact_sensitive(text: str) -> str:
    text = _MAC_RE.sub("<mac>", text)
    text = _IPV4_RE.sub("<ipv4>", text)
    text = _IPV6_RE.sub("<ipv6>", text)
    text = _UUID_RE.sub("<uuid>", text)
    text = _HOMEDIR_RE.sub("/home/<user>", text)
    return text


def _truncate(text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    cut = encoded[: max_bytes - 32].decode("utf-8", errors="ignore")
    return cut.rstrip() + "\n…[truncated]\n"


def _detect_pkg_manager() -> str:
    for binary, label in _PKG_MANAGERS:
        if shutil.which(binary) or os.path.exists(f"/usr/bin/{binary}"):
            return label
    return ""


def _parse_mhwd_names(raw: str) -> list[str]:
    if not raw:
        return []
    names: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith(("NAME", "-", "=", ">", "Warning")):
            continue
        first = line.split()[0]
        if first and not set(first) <= {"-", "="} and first not in names:
            names.append(first)
    return names[:8]


def _iter_devices(section: dict[str, Any], key: str) -> Iterable[dict[str, Any]]:
    devices = section.get(key)
    if isinstance(devices, list):
        for dev in devices:
            if isinstance(dev, dict):
                yield dev


def _str(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text in ("", "N/A", "Unknown", "?", "None"):
        return ""
    return text
