"""Run cheap diagnostic commands so AI prompts can embed real output.

Each entry is a fast (≤8s) read-only command. Results are redacted and
truncated. Goal: chatbot has data without asking the user to run anything.
"""

from __future__ import annotations

import glob
import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from big_hardware_info.collectors.base_collector import BaseCollector
from big_hardware_info.utils.ai_context import redact_sensitive


logger = logging.getLogger(__name__)


PER_OUTPUT_MAX_BYTES = 2048
PER_OUTPUT_MAX_BYTES_LARGE = 6144  # lspci/lsusb/cups config can be big
COMMAND_TIMEOUT_S = 8

_LARGE_OUTPUT_KEYS = frozenset({
    "lspci", "lsusb", "cups_config", "nm_config", "bt_config",
    "top_snapshot",
})


class AiDiagnosticsCollector(BaseCollector):
    """Collect a curated set of diagnostic command outputs in parallel."""

    def collect(self) -> dict:
        tasks: dict[str, Callable[[], tuple[bool, str]]] = {
            "rfkill": lambda: self._run(["rfkill", "list"]),
            "nmcli_dev": lambda: self._run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"],
            ),
            "nmcli_status": lambda: self._run(["nmcli", "general", "status"]),
            "ip_link": lambda: self._run(["ip", "-br", "link"]),
            "iw_reg": lambda: self._run(["iw", "reg", "get"]),
            "bluetoothctl_show": lambda: self._run(["bluetoothctl", "show"]),
            "bluetoothctl_devices": lambda: self._run(
                ["bluetoothctl", "devices"],
            ),
            "wpctl": lambda: self._run(["wpctl", "status"]),
            "pactl_sinks": lambda: self._run(
                ["pactl", "list", "short", "sinks"],
            ),
            "pactl_sources": lambda: self._run(
                ["pactl", "list", "short", "sources"],
            ),
            "pactl_cards": lambda: self._run(["pactl", "list", "short", "cards"]),
            "xrandr": lambda: self._run(["xrandr", "--listmonitors"]),
            "wlr_randr": lambda: self._run(["wlr-randr"]),
            "kscreen": lambda: self._run(["kscreen-doctor", "-o"]),
            "session": lambda: self._session_info(),
            "cmdline": lambda: self._read_text("/proc/cmdline"),
            "mem_sleep": lambda: self._read_text("/sys/power/mem_sleep"),
            "acpi_wakeup": lambda: self._read_text("/proc/acpi/wakeup"),
            "analyze_blame": lambda: self._run_head(
                ["systemd-analyze", "blame"], 20,
            ),
            "analyze_critical": lambda: self._run(
                ["systemd-analyze", "critical-chain"],
            ),
            "failed_units": lambda: self._run(
                ["systemctl", "--failed", "--no-legend", "--no-pager"],
            ),
            "dmesg_err": lambda: self._run_tail(
                ["dmesg", "-t", "--level=alert,crit,err,warn"], 30,
            ),
            "journal_err": lambda: self._run_tail(
                ["journalctl", "-b", "-p", "err", "--no-pager"], 30,
            ),
            "df_root": lambda: self._run(["df", "-h", "/"]),
            "swapon": lambda: self._run(["swapon", "--show"]),
            "lspci_kernel": lambda: self._run(["lspci", "-k"]),
            "lsmod_top": lambda: self._run_head(["lsmod"], 30),
            "glxinfo": lambda: self._run(["glxinfo", "-B"]),
            "vulkan": lambda: self._run(["vulkaninfo", "--summary"]),
            "sensors": lambda: self._run(["sensors"]),
            "upower": lambda: self._upower_battery(),
            "charge_thresholds": lambda: self._charge_thresholds(),
            "tlp_stat": lambda: self._run(["tlp-stat", "-s", "-p"]),
            "powerprof": lambda: self._run(["powerprofilesctl", "list"]),
            "bt_config": lambda: self._filtered_file(
                "/etc/bluetooth/main.conf",
            ),
            "nm_config": lambda: self._nm_config(),
            "cups_status": lambda: self._run(["lpstat", "-t"]),
            "cups_config": lambda: self._filtered_file(
                "/etc/cups/cupsd.conf",
            ),
            "v4l2_devices": lambda: self._run(
                ["v4l2-ctl", "--list-devices"],
            ),
            "v4l2_formats": lambda: self._run(
                ["v4l2-ctl", "--list-formats-ext"],
            ),
            "top_snapshot": lambda: self._top_snapshot(),
            "pressure": lambda: self._pressure(),
            "lspci": lambda: self._run(["lspci"]),
            "lsusb": lambda: self._run(["lsusb"]),
        }

        results: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(fn): name for name, fn in tasks.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    ok, output = future.result()
                except Exception as exc:
                    logger.debug("ai_diag %s failed: %s", name, exc)
                    continue
                if not ok or not output:
                    continue
                cap = (
                    PER_OUTPUT_MAX_BYTES_LARGE
                    if name in _LARGE_OUTPUT_KEYS
                    else PER_OUTPUT_MAX_BYTES
                )
                results[name] = self._sanitize(output, cap)
        return results

    # --- runners -----------------------------------------------------------

    def _run(self, cmd: list[str]) -> tuple[bool, str]:
        if not cmd or not shutil.which(cmd[0]):
            return False, ""
        ok, out, _err = self.run_command(cmd, timeout=COMMAND_TIMEOUT_S)
        return ok, out

    def _run_head(self, cmd: list[str], n: int) -> tuple[bool, str]:
        ok, out = self._run(cmd)
        if not ok:
            return ok, out
        return True, "\n".join(out.splitlines()[:n])

    def _run_tail(self, cmd: list[str], n: int) -> tuple[bool, str]:
        ok, out = self._run(cmd)
        if not ok:
            return ok, out
        return True, "\n".join(out.splitlines()[-n:])

    def _read_text(self, path: str) -> tuple[bool, str]:
        content = self.read_file(path)
        if content is None:
            return False, ""
        return True, content.strip()

    def _session_info(self) -> tuple[bool, str]:
        sid = os.environ.get("XDG_SESSION_ID", "")
        if not sid or not shutil.which("loginctl"):
            return False, ""
        return self._run(
            ["loginctl", "show-session", sid,
             "--property=Type", "--property=Class",
             "--property=Active", "--property=State"],
        )

    def _upower_battery(self) -> tuple[bool, str]:
        if not shutil.which("upower"):
            return False, ""
        ok, listing, _err = self.run_command(
            ["upower", "-e"], timeout=COMMAND_TIMEOUT_S,
        )
        if not ok:
            return False, ""
        battery_line = next(
            (line for line in listing.splitlines() if "BAT" in line), "",
        )
        if not battery_line:
            return False, ""
        return self._run(["upower", "-i", battery_line.strip()])

    def _charge_thresholds(self) -> tuple[bool, str]:
        bits: list[str] = []
        for entry in sorted(os.listdir("/sys/class/power_supply") or []):
            if not entry.startswith("BAT"):
                continue
            base = f"/sys/class/power_supply/{entry}"
            for fname in ("charge_control_start_threshold",
                          "charge_control_end_threshold",
                          "charge_start_threshold",
                          "charge_end_threshold"):
                content = self.read_file(f"{base}/{fname}")
                if content is not None:
                    bits.append(f"{entry}/{fname}: {content.strip()}")
        return (bool(bits), "\n".join(bits))

    # --- file/aggregate runners --------------------------------------------

    def _filtered_file(self, path: str) -> tuple[bool, str]:
        """Read text file dropping comments + blank lines."""
        content = self.read_file(path)
        if content is None:
            return False, ""
        kept: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ";")):
                continue
            kept.append(stripped)
        return (bool(kept), "\n".join(kept))

    def _nm_config(self) -> tuple[bool, str]:
        paths = ["/etc/NetworkManager/NetworkManager.conf"]
        paths.extend(sorted(glob.glob("/etc/NetworkManager/conf.d/*.conf")))
        parts: list[str] = []
        for path in paths:
            ok, body = self._filtered_file(path)
            if ok:
                parts.append(f"# {path}\n{body}")
        return (bool(parts), "\n\n".join(parts))

    def _pressure(self) -> tuple[bool, str]:
        parts: list[str] = []
        for resource in ("cpu", "memory", "io"):
            content = self.read_file(f"/proc/pressure/{resource}")
            if content:
                parts.append(f"# {resource}\n{content.strip()}")
        return (bool(parts), "\n".join(parts))

    def _top_snapshot(self) -> tuple[bool, str]:
        if not shutil.which("top"):
            return False, ""
        ok, out, _err = self.run_command(
            ["top", "-bn1", "-w", "200"], timeout=COMMAND_TIMEOUT_S,
        )
        if not ok:
            return False, ""
        return True, "\n".join(out.splitlines()[:25])

    # --- sanitize ----------------------------------------------------------

    def _sanitize(self, text: str, max_bytes: int) -> str:
        text = redact_sensitive(text.strip())
        encoded = text.encode("utf-8")
        if len(encoded) <= max_bytes:
            return text
        cut = encoded[: max_bytes - 16].decode("utf-8", errors="ignore")
        return cut.rstrip() + "\n…[truncated]"
