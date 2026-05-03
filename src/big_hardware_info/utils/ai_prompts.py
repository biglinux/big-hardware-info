"""Pre-built AI chatbot prompts for the Linux desktop issues users actually
hit (sourced from Arch/Manjaro/Mint/openSUSE forums + Reddit help threads).

Each prompt is short telegraphic English with relevant hardware context
auto-filled. Reply language is the user's system locale.
"""

from __future__ import annotations

import locale
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from big_hardware_info.utils.ai_context import build_ai_support_context_text
from big_hardware_info.utils.i18n import _


@dataclass(frozen=True)
class Prompt:
    """One ready-to-paste chatbot prompt."""

    key: str
    category: str
    title: str
    summary: str
    body: str
    keywords: tuple[str, ...] = field(default_factory=tuple)
    relevant: bool = False  # auto-flagged when hardware matches


@dataclass(frozen=True)
class PromptCategory:
    key: str
    title: str
    description: str


CATEGORIES: tuple[PromptCategory, ...] = (
    PromptCategory(
        "network",
        _("Network & Bluetooth"),
        _("Wi-Fi, Ethernet, Bluetooth pairing/audio."),
    ),
    PromptCategory(
        "graphics",
        _("Graphics & Display"),
        _("GPU drivers, hybrid graphics, scaling, multi-monitor."),
    ),
    PromptCategory(
        "audio",
        _("Audio"),
        _("Sound, microphone, PipeWire/PulseAudio."),
    ),
    PromptCategory(
        "power",
        _("Power & Thermals"),
        _("Suspend/hibernate, battery, fan, overheating."),
    ),
    PromptCategory(
        "system",
        _("System & Packages"),
        _("Boot, package manager, broken updates, rollback, disk space."),
    ),
    PromptCategory(
        "peripherals",
        _("Peripherals"),
        _("Webcam, touchpad, printer, scanner, USB."),
    ),
    PromptCategory(
        "performance",
        _("Performance"),
        _("Lag, high load, slow boot, wake-up sources."),
    ),
    PromptCategory(
        "other",
        _("Other"),
        _("Apps, Flatpak, generic problem with full snapshot."),
    ),
)


def detect_reply_language() -> str:
    """Return BCP47-ish tag for the running system locale (e.g. ``pt-BR``)."""
    for env in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        raw = os.environ.get(env, "")
        if raw and raw not in ("C", "POSIX"):
            tag = raw.split(".")[0].split(":")[0]
            tag = tag.replace("_", "-").strip()
            if tag:
                return tag
    try:
        loc = locale.getlocale()[0]
        if loc:
            return loc.replace("_", "-")
    except (locale.Error, ValueError):
        pass
    return "en-US"


def build_prompts(hardware_data: dict[str, Any] | None) -> list[Prompt]:
    """Build the ordered prompt catalog with hardware context injected."""
    data = hardware_data or {}
    lang = detect_reply_language()
    ctx = _short_ctx(data)

    builders: list[Callable[[dict, str, str], Prompt]] = [
        # Network & Bluetooth
        _wifi_unstable, _wifi_after_suspend, _ethernet,
        _bluetooth_audio, _bluetooth_pairing,
        # Graphics & Display
        _hybrid_gpu, _wayland_tearing, _fractional_scaling,
        _external_monitor, _blurry_fonts, _vsync_freesync,
        # Audio
        _no_sound, _mic_not_working, _audio_crackle,
        # Power & Thermals
        _suspend_broken, _hibernate_broken, _battery_drain, _overheating,
        # System & Packages
        _pacman_keyring, _dependency_conflict, _boot_fails,
        _post_update_rollback, _disk_full,
        # Peripherals
        _webcam, _touchpad, _printer_scanner,
        # Performance
        _lag_high_load, _slow_boot,
        # Other
        _flatpak_app, _generic,
    ]
    return [b(data, ctx, lang) for b in builders]


# ---------- helpers ---------------------------------------------------------


def _short_ctx(data: dict[str, Any]) -> str:
    system = data.get("system") or {}
    kernel = data.get("kernel") or {}
    distro = system.get("distro") or "?"
    kver = (kernel.get("version") if isinstance(kernel, dict) else "") \
        or system.get("kernel") or "?"
    desktop = system.get("desktop") or "?"
    session = system.get("session_type") or "?"
    return f"{distro}, kernel {kver}, {desktop} ({session})"


def _device_summary(devices: list[dict[str, Any]], fields: tuple[str, ...]) -> str:
    out: list[str] = []
    for dev in devices or []:
        if not isinstance(dev, dict):
            continue
        bits = [str(dev.get(f)) for f in fields if dev.get(f)]
        if bits:
            out.append(" ".join(bits))
    return "; ".join(out) or "?"


def _footer(lang: str) -> str:
    return (
        f"Reply in {lang}. Be terse, technical. Give: 1) likely cause, "
        "2) extra diagnostic commands if needed, 3) fix steps in order, "
        "4) when to escalate. Use code blocks. Diagnostic output below is "
        "already redacted (MAC/IP/UUID/serial/hostname stripped)."
    )


_DIAG_LABELS: dict[str, str] = {
    "rfkill": "rfkill list",
    "nmcli_dev": "nmcli device",
    "nmcli_status": "nmcli general status",
    "ip_link": "ip -br link",
    "iw_reg": "iw reg get",
    "bluetoothctl_show": "bluetoothctl show",
    "bluetoothctl_devices": "bluetoothctl devices",
    "wpctl": "wpctl status",
    "pactl_sinks": "pactl list short sinks",
    "pactl_sources": "pactl list short sources",
    "pactl_cards": "pactl list short cards",
    "xrandr": "xrandr --listmonitors",
    "wlr_randr": "wlr-randr",
    "kscreen": "kscreen-doctor -o",
    "session": "loginctl show-session",
    "cmdline": "/proc/cmdline",
    "mem_sleep": "/sys/power/mem_sleep",
    "acpi_wakeup": "/proc/acpi/wakeup",
    "analyze_blame": "systemd-analyze blame (top 20)",
    "analyze_critical": "systemd-analyze critical-chain",
    "failed_units": "systemctl --failed",
    "dmesg_err": "dmesg (errors, last 30)",
    "journal_err": "journalctl -b -p err (last 30)",
    "df_root": "df -h /",
    "swapon": "swapon --show",
    "lspci_kernel": "lspci -k",
    "lsmod_top": "lsmod (top 30)",
    "glxinfo": "glxinfo -B",
    "vulkan": "vulkaninfo --summary",
    "sensors": "sensors",
    "upower": "upower -i (battery)",
    "charge_thresholds": "battery charge thresholds",
    "tlp_stat": "tlp-stat -s -p",
    "powerprof": "powerprofilesctl list",
    "bt_config": "/etc/bluetooth/main.conf (active lines)",
    "nm_config": "NetworkManager config (active lines)",
    "cups_status": "lpstat -t",
    "cups_config": "/etc/cups/cupsd.conf (active lines)",
    "v4l2_devices": "v4l2-ctl --list-devices",
    "v4l2_formats": "v4l2-ctl --list-formats-ext",
    "top_snapshot": "top -bn1 (top 25 lines)",
    "pressure": "/proc/pressure/{cpu,memory,io}",
    "lspci": "lspci",
    "lsusb": "lsusb",
}


def _diag_block(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Return fenced output blocks for keys present in ``data['ai_diag']``."""
    diag = data.get("ai_diag") or {}
    if not isinstance(diag, dict):
        return ""
    parts: list[str] = []
    for key in keys:
        out = diag.get(key)
        if not out:
            continue
        label = _DIAG_LABELS.get(key, key)
        parts.append(f"### {label}\n```\n{out}\n```")
    if not parts:
        return ""
    return "\n\nCurrent system output (already collected):\n\n" + "\n\n".join(parts)


def _has_hybrid_gpu(data: dict[str, Any]) -> bool:
    devs = (data.get("gpu") or {}).get("devices") or []
    vendors = {
        (d.get("vendor") or d.get("name") or "").lower()[:6]
        for d in devs if isinstance(d, dict)
    }
    return len([v for v in vendors if v]) >= 2


def _has_battery(data: dict[str, Any]) -> bool:
    bat = data.get("battery") or {}
    return bool(bat) and any(bat.get(k) for k in ("status", "state", "charge", "model"))


def _has_bluetooth(data: dict[str, Any]) -> bool:
    return bool((data.get("bluetooth") or {}).get("devices"))


def _has_wifi(data: dict[str, Any]) -> bool:
    for d in (data.get("network") or {}).get("devices", []):
        name = (d.get("name") or "").lower()
        iface = (d.get("IF") or "").lower()
        if "wireless" in name or "wi-fi" in name or "wifi" in name or iface.startswith("wlp") or iface.startswith("wlan"):
            return True
    return False


# ---------- network ---------------------------------------------------------


def _wifi_unstable(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    nics = [
        d for d in (data.get("network") or {}).get("devices", [])
        if isinstance(d, dict) and (
            "wlp" in (d.get("IF") or "").lower()
            or "wlan" in (d.get("IF") or "").lower()
            or "wireless" in (d.get("name") or "").lower()
            or "wi-fi" in (d.get("name") or "").lower()
        )
    ]
    nic_line = _device_summary(nics, ("vendor", "name", "chip_id", "driver"))
    body = (
        "Issue: Wi-Fi unstable on Linux desktop — drops, slow, no networks "
        "visible, weak signal, 5GHz missing.\n"
        f"Setup: {ctx}.\n"
        f"Wi-Fi NIC: {nic_line}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('rfkill', 'nmcli_dev', 'nmcli_status', 'iw_reg', 'ip_link', 'nm_config', 'journal_err'))}"
    )
    return Prompt(
        "wifi_unstable", "network", _("Wi-Fi unstable / drops"),
        _("Disconnects, slow, missing networks, 5 GHz absent"), body,
        ("wifi", "wireless", "iwlwifi", "broadcom", "ath", "drop"),
        relevant=_has_wifi(data),
    )


def _wifi_after_suspend(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Wi-Fi vanishes after suspend/resume on Linux — NIC missing "
        "until reboot, or stays disabled, or NetworkManager unmanaged.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('rfkill', 'nmcli_status', 'ip_link', 'nm_config', 'mem_sleep', 'journal_err'))}"
    )
    return Prompt(
        "wifi_suspend", "network", _("Wi-Fi gone after suspend"),
        _("NIC disappears until reboot after sleep/resume"), body,
        ("wifi", "suspend", "resume", "wake"),
        relevant=_has_wifi(data),
    )


def _ethernet(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Ethernet on Linux — no link, slow speed (1G negotiated as "
        "100M), wake-on-LAN not working, or interface down on boot.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('ip_link', 'nmcli_dev', 'nm_config', 'lspci_kernel', 'journal_err'))}"
    )
    return Prompt(
        "ethernet", "network", _("Ethernet no link / slow"),
        _("Cable connected but no IP, wrong speed, or down on boot"), body,
        ("ethernet", "lan", "rtl", "r8169", "r8168"),
    )


def _bluetooth_audio(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    bt = _device_summary(
        (data.get("bluetooth") or {}).get("devices", []),
        ("vendor", "name", "chip_id", "driver", "bt_version"),
    )
    body = (
        "Issue: Bluetooth audio on Linux — cuts every few seconds, robotic "
        "voice, A2DP profile not selectable, mic profile (HSP/HFP) missing, "
        "or only works after multiple disconnects.\n"
        f"Setup: {ctx}.\n"
        f"BT adapter: {bt}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('bluetoothctl_show', 'bluetoothctl_devices', 'bt_config', 'wpctl', 'pactl_cards', 'rfkill'))}"
    )
    return Prompt(
        "bt_audio", "network", _("Bluetooth audio cuts / mic missing"),
        _("Headphone stutters, no A2DP, mic profile absent"), body,
        ("bluetooth", "a2dp", "hsp", "hfp", "audio", "headset"),
        relevant=_has_bluetooth(data),
    )


def _bluetooth_pairing(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Bluetooth pairing fails on Linux — adapter not detected, "
        "scan empty, device pairs but won't connect, or auto-reconnect fails "
        "after kernel update.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('rfkill', 'bluetoothctl_show', 'bluetoothctl_devices', 'bt_config', 'dmesg_err'))}"
    )
    return Prompt(
        "bt_pairing", "network", _("Bluetooth pairing / detection"),
        _("Adapter missing, won't pair, won't reconnect"), body,
        ("bluetooth", "pair", "scan", "firmware"),
        relevant=_has_bluetooth(data),
    )


# ---------- graphics --------------------------------------------------------


def _hybrid_gpu(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    gpus = (data.get("gpu") or {}).get("devices", [])
    gpu_line = _device_summary(gpus, ("vendor", "name", "chip_id", "driver"))
    info = (data.get("gpu") or {}).get("display_info") or {}
    active = info.get("gpu") or "?"
    renderer = (data.get("gpu") or {}).get("opengl", {}).get("renderer") or "?"
    body = (
        "Issue: Hybrid graphics on Linux — app renders on iGPU instead of "
        "dGPU, dGPU never powers down (battery drain), Wayland uses wrong "
        "GPU, or external HDMI/DP wired to dGPU goes black.\n"
        f"Setup: {ctx}.\n"
        f"GPUs: {gpu_line}.\n"
        f"Active: {active}. OpenGL renderer: {renderer}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('session', 'cmdline', 'glxinfo', 'vulkan', 'lspci_kernel', 'lsmod_top'))}"
    )
    return Prompt(
        "hybrid_gpu", "graphics", _("Hybrid GPU / wrong renderer"),
        _("App uses iGPU, dGPU stays on, external monitor blank"), body,
        ("nvidia", "optimus", "prime", "amdgpu", "intel", "hybrid"),
        relevant=_has_hybrid_gpu(data),
    )


def _wayland_tearing(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Wayland tearing / flicker / black flashes on Linux desktop, "
        "or X11 screen tearing in video and games.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('session', 'cmdline', 'glxinfo', 'xrandr', 'wlr_randr'))}"
    )
    return Prompt(
        "tearing", "graphics", _("Tearing / flicker (Wayland or X11)"),
        _("Visible tearing, black flashes, scroll judder"), body,
        ("wayland", "x11", "tear", "flicker", "vsync"),
    )


def _fractional_scaling(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Fractional scaling on Linux — cursor flicker, blurry GTK3/"
        "Electron apps, refresh rate drops to 60Hz when scaling≠100%, high "
        "GPU usage, or X11 apps under XWayland tiny.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('session', 'xrandr', 'wlr_randr', 'kscreen'))}"
    )
    return Prompt(
        "fractional_scaling", "graphics", _("Fractional scaling / HiDPI"),
        _("Blurry apps, 60Hz cap, cursor flicker, XWayland tiny"), body,
        ("hidpi", "scaling", "fractional", "blurry", "wayland"),
    )


def _external_monitor(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    monitors = (data.get("gpu") or {}).get("monitors", [])
    mon_line = _device_summary(monitors, ("name", "model", "resolution"))
    body = (
        "Issue: External monitor on Linux — not detected, wrong refresh rate "
        "(stuck 60Hz instead of 144/240), HDR not working, or DP daisy-chain "
        "fails.\n"
        f"Setup: {ctx}.\n"
        f"Monitors detected: {mon_line}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('xrandr', 'wlr_randr', 'kscreen', 'session', 'dmesg_err'))}"
    )
    return Prompt(
        "external_monitor", "graphics", _("External monitor / refresh rate"),
        _("Not detected, stuck 60 Hz, no HDR, DP MST"), body,
        ("monitor", "edid", "refresh", "hdmi", "displayport"),
    )


def _blurry_fonts(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Blurry fonts on Linux — Wayland apps look soft, "
        "Electron/Chrome subpixel wrong, or font hinting flat.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('session', 'xrandr', 'wlr_randr', 'kscreen'))}"
    )
    return Prompt(
        "blurry_fonts", "graphics", _("Blurry / bad fonts"),
        _("Soft Wayland fonts, wrong subpixel, Electron blurry"), body,
        ("font", "blurry", "subpixel", "fontconfig"),
    )


def _vsync_freesync(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: VRR / FreeSync / G-Sync on Linux — not engaging, flicker on "
        "low refresh, or only works in fullscreen.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('session', 'cmdline', 'glxinfo', 'xrandr', 'wlr_randr', 'kscreen'))}"
    )
    return Prompt(
        "vrr", "graphics", _("VRR / FreeSync / G-Sync"),
        _("Adaptive sync not engaging or flickering"), body,
        ("vrr", "freesync", "gsync", "adaptive"),
    )


# ---------- audio -----------------------------------------------------------


def _no_sound(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    audio = data.get("audio") or {}
    server = audio.get("server") or "?"
    devs = _device_summary(audio.get("devices", []), ("vendor", "name", "chip_id", "driver"))
    body = (
        "Issue: No sound on Linux / wrong default output / volume slider "
        "does nothing / HDMI audio missing.\n"
        f"Setup: {ctx}. Audio server: {server}.\n"
        f"Audio devices: {devs}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('wpctl', 'pactl_sinks', 'pactl_cards', 'dmesg_err'))}"
    )
    return Prompt(
        "no_sound", "audio", _("No sound / wrong output"),
        _("Silent speakers, HDMI silent, profile won't switch"), body,
        ("audio", "sound", "pipewire", "pulseaudio", "alsa"),
    )


def _mic_not_working(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Microphone on Linux — not detected, very low gain, picks up "
        "speakers (echo), or only works in some apps (Chrome OK, Discord "
        "muted).\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('wpctl', 'pactl_sources', 'pactl_cards'))}"
    )
    return Prompt(
        "mic", "audio", _("Microphone not working"),
        _("No detection, low gain, app-specific mute"), body,
        ("microphone", "mic", "input", "echo"),
    )


def _audio_crackle(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Audio crackle / pop / underrun on Linux under load or with "
        "USB DAC.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('wpctl', 'pactl_sinks', 'pactl_cards', 'dmesg_err'))}"
    )
    return Prompt(
        "audio_crackle", "audio", _("Crackling / underrun"),
        _("Pops under load, USB DAC stutters, BT coexistence"), body,
        ("crackle", "underrun", "xrun", "pop"),
    )


# ---------- power -----------------------------------------------------------


def _suspend_broken(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Suspend on Linux — instant wake-up, black screen on resume, "
        "or laptop never sleeps with lid close.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('mem_sleep', 'acpi_wakeup', 'cmdline', 'journal_err', 'dmesg_err'))}"
    )
    return Prompt(
        "suspend", "power", _("Suspend wakes alone / black screen"),
        _("Instant wake, won't sleep, blank on resume"), body,
        ("suspend", "sleep", "s2idle", "wake"),
        relevant=_has_battery(data),
    )


def _hibernate_broken(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Hibernate on Linux — not available, fails with i/o error, "
        "or boots back to fresh session instead of resuming.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('mem_sleep', 'cmdline', 'swapon', 'df_root', 'journal_err'))}"
    )
    return Prompt(
        "hibernate", "power", _("Hibernate fails / no resume"),
        _("Won't enter, IO error, or session lost on boot"), body,
        ("hibernate", "swap", "resume", "btrfs"),
        relevant=_has_battery(data),
    )


def _battery_drain(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    bat = data.get("battery") or {}
    bat_line = " ".join(str(v) for v in (
        bat.get("model"), bat.get("charge"), bat.get("status"), bat.get("condition"),
    ) if v) or "?"
    body = (
        "Issue: Battery drains fast on Linux laptop, or charge thresholds "
        "ignored, or power-profiles-daemon and TLP fight each other.\n"
        f"Setup: {ctx}.\n"
        f"Battery: {bat_line}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('upower', 'charge_thresholds', 'powerprof', 'tlp_stat'))}"
    )
    return Prompt(
        "battery", "power", _("Battery drain / charging"),
        _("Fast drain, charge limit ignored, ppd vs TLP"), body,
        ("battery", "tlp", "ppd", "drain", "charge"),
        relevant=_has_battery(data),
    )


def _overheating(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    sensors = data.get("sensors") or {}
    body = (
        "Issue: Linux laptop running hot, fan loud, thermal throttling, "
        "shutdown under load, or ambient idle temps too high.\n"
        f"Setup: {ctx}.\n"
        f"Sensors keys present: {list(sensors.keys()) if isinstance(sensors, dict) else '?'}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('sensors', 'powerprof', 'tlp_stat', 'dmesg_err'))}"
    )
    return Prompt(
        "thermals", "power", _("Overheating / fan / throttle"),
        _("High temps, loud fan, shutdown under load"), body,
        ("temperature", "fan", "throttle", "thermal"),
    )


# ---------- system ----------------------------------------------------------


def _pacman_keyring(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: pacman keyring / signature error on Arch-based system "
        "(invalid signature, key unknown, marginal trust).\n"
        f"Setup: {ctx}.\n"
        "Error verbatim: <paste error>.\n"
        "What I tried: <fill in>.\n"
        "Need: safe sequence — pacman -Sy archlinux-keyring "
        "manjaro-keyring, pacman-key --init, --populate, --refresh, "
        "system clock sanity (timedatectl), avoid -Syu before keyring "
        "fix. Distinguish recoverable vs needs live USB.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('df_root',))}"
    )
    return Prompt(
        "keyring", "system", _("pacman keyring / signature error"),
        _("Invalid sig, unknown key, after long no-update"), body,
        ("pacman", "keyring", "signature", "key"),
    )


def _dependency_conflict(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Package manager dependency conflict on Linux — "
        "(pacman/apt/dnf/zypper) refuses to upgrade.\n"
        f"Setup: {ctx}.\n"
        "Error verbatim: <paste error>.\n"
        "What I tried: <fill in>.\n"
        "Need: safe resolution path. For pacman: pacman -Dk, partial "
        "removals, AUR rebuilds. For apt: aptitude solver, broken-held "
        "packages. Avoid forced --overwrite blindly. Identify upstream "
        "issue vs user state.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('df_root',))}"
    )
    return Prompt(
        "dep_conflict", "system", _("Dependency conflict / broken update"),
        _("Refuses upgrade, partial state, held packages"), body,
        ("conflict", "dependency", "broken", "update"),
    )


def _boot_fails(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Linux won't boot — drops to emergency shell, GRUB "
        "rescue prompt, kernel panic, or stuck on splash.\n"
        f"Setup: {ctx}.\n"
        "Last change before break: <fill in>.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('cmdline', 'failed_units', 'analyze_critical', 'journal_err', 'dmesg_err'))}"
    )
    return Prompt(
        "boot", "system", _("Boot fails / emergency shell / GRUB"),
        _("Won't boot, drops to shell, GRUB rescue, panic"), body,
        ("boot", "grub", "initramfs", "panic", "emergency"),
    )


def _post_update_rollback(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Something stopped working on Linux after a system update "
        "(graphics, audio, Wi-Fi, login loop). Want to identify the "
        "regressing package and roll it back without nuking the system.\n"
        f"Setup: {ctx}.\n"
        "What broke: <fill in>. Last working state: <fill in>.\n"
        "Need: walk pacman.log / /var/log/apt/history.log to find "
        "regressing package, downgrade with downgrade tool / "
        "/var/cache/pacman/pkg, IgnorePkg pin, snapper/timeshift/btrfs "
        "rollback path, file upstream bug.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('failed_units', 'journal_err', 'dmesg_err'))}"
    )
    return Prompt(
        "regression", "system", _("Broken after update / rollback"),
        _("Find regressing package, downgrade, snapper rollback"), body,
        ("regression", "rollback", "downgrade", "snapper", "timeshift"),
    )


def _disk_full(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    usage = data.get("disk_usage") or {}
    root_line = (
        f"{usage.get('mount_point', '/')} {usage.get('size', '?')} "
        f"used {usage.get('use_percent', '?')}"
    )
    body = (
        "Issue: Root partition full on Linux / can't update / Btrfs "
        "metadata exhausted / journal logs huge.\n"
        f"Setup: {ctx}.\n"
        f"Root usage: {root_line}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('df_root', 'swapon'))}"
    )
    return Prompt(
        "disk_full", "system", _("Disk full / root partition"),
        _("No space, package cache huge, snapshots eat space"), body,
        ("disk", "full", "space", "btrfs", "snapper"),
    )


# ---------- peripherals -----------------------------------------------------


def _webcam(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    cams = (data.get("webcam") or {}).get("devices", []) \
        or (data.get("gpu") or {}).get("webcams", [])
    cam_line = _device_summary(cams, ("vendor", "name", "chip_id", "driver"))
    body = (
        "Issue: Webcam on Linux — not detected, black image, or Intel IPU6 "
        "needs out-of-tree stack.\n"
        f"Setup: {ctx}.\n"
        f"Camera: {cam_line}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('v4l2_devices', 'v4l2_formats', 'lspci_kernel', 'dmesg_err', 'lsmod_top'))}"
    )
    return Prompt(
        "webcam", "peripherals", _("Webcam not detected / black"),
        _("No /dev/video, IPU6 stack needed, dark image"), body,
        ("webcam", "camera", "uvcvideo", "ipu6", "v4l2"),
    )


def _touchpad(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Touchpad on Linux — gestures missing, palm rejection bad, "
        "tap-to-click off, or wrong driver (PS/2 instead of I2C).\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('cmdline', 'lsmod_top', 'dmesg_err'))}"
    )
    return Prompt(
        "touchpad", "peripherals", _("Touchpad / gestures"),
        _("No gestures, wrong driver, palm rejection bad"), body,
        ("touchpad", "libinput", "gesture", "i2c"),
    )


def _printer_scanner(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Printer / scanner on Linux — not detected, job queued "
        "forever, or driverless IPP fails.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('cups_status', 'cups_config', 'failed_units', 'journal_err'))}"
    )
    return Prompt(
        "printer", "peripherals", _("Printer / scanner"),
        _("Not detected, queue stuck, IPP-everywhere fails"), body,
        ("printer", "scanner", "cups", "ipp", "sane"),
    )


# ---------- performance -----------------------------------------------------


def _lag_high_load(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: System lag / high load average on Linux desktop — UI stutter, "
        "background process pegging CPU, swap thrashing.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('top_snapshot', 'pressure', 'failed_units', 'analyze_blame', 'swapon', 'dmesg_err', 'journal_err'))}"
    )
    return Prompt(
        "lag", "performance", _("System lag / high load"),
        _("UI stutter, CPU peg, swap thrash, OOM"), body,
        ("lag", "slow", "cpu", "load", "thrash"),
    )


def _slow_boot(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Slow boot on Linux — userspace takes too long, one service "
        "blocks startup, or NetworkManager-wait-online stalls boot.\n"
        f"Setup: {ctx}.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('analyze_blame', 'analyze_critical', 'failed_units'))}"
    )
    return Prompt(
        "slow_boot", "performance", _("Slow boot"),
        _("Long boot, service stalls, fsck every time"), body,
        ("boot", "slow", "systemd-analyze"),
    )


# ---------- other -----------------------------------------------------------


def _flatpak_app(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    body = (
        "Issue: Flatpak / Snap app on Linux — won't launch, missing "
        "permission (camera/mic/files), wrong theme, or no GPU "
        "acceleration.\n"
        f"Setup: {ctx}.\n"
        "App: <fill in>. Error: <fill in>.\n"
        "What I tried: <fill in>.\n"
        f"{_footer(lang)}"
        f"{_diag_block(data, ('session', 'glxinfo', 'vulkan'))}"
    )
    return Prompt(
        "flatpak", "other", _("Flatpak / Snap app issue"),
        _("Won't launch, no perms, wrong theme, no GPU"), body,
        ("flatpak", "snap", "sandbox", "portal"),
    )


def _generic(data: dict[str, Any], ctx: str, lang: str) -> Prompt:
    full_ctx = build_ai_support_context_text(data)
    body = (
        "Issue: <describe your Linux desktop problem in one sentence>.\n"
        f"Setup: {ctx}.\n"
        "Symptoms: <fill in>. Reproduce: <fill in>.\n"
        "What I tried: <fill in>.\n"
        "Full hardware/system snapshot below — use only what is relevant.\n"
        f"{_footer(lang)}\n\n"
        f"{full_ctx}"
    )
    return Prompt(
        "generic", "other", _("Generic issue (full snapshot)"),
        _("Anything not covered — includes full report"), body,
        ("generic", "other", "snapshot"),
    )
