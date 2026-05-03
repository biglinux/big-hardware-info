"""Inxi-based hardware information collector."""

import json
import logging
import time
from .base_collector import BaseCollector


logger = logging.getLogger(__name__)


INXI_BASE_COMMAND = ["inxi", "--tty", "-y", "80", "-c", "0"]
INXI_JSON_OUTPUT_ARGS = ["--output", "json", "--output-file", "print"]


def _build_inxi_command(report_args: list[str], filter_sensitive: bool = False) -> list[str]:
    command = [*INXI_BASE_COMMAND, *report_args]
    if filter_sensitive:
        command.append("-z")
    command.extend(INXI_JSON_OUTPUT_ARGS)
    return command


# --tty avoids inxi's IRC-client false-detection that breaks JSON output when
# launched from a desktop entry without a controlling terminal.
# -y 80 pins width so inxi never tries to probe terminal size (would block
# without a tty). -v8 already implies -a, so drop the redundant flag to keep
# the command surface small.
INXI_COMMAND = _build_inxi_command(["-Fxxx", "-v8"])
INXI_COMMAND_FILTERED = _build_inxi_command(["-Fxxx", "-v8"], filter_sensitive=True)
INXI_COMMAND_FALLBACK = _build_inxi_command(["-Fxxx"])


INXI_SECTION_FALLBACKS = (
    ("system", ["-Sxxx"]),
    ("machine", ["-Mxxx"]),
    ("battery", ["-Bxxx"]),
    ("memory", ["-mxxx"]),
    ("cpu", ["-Cxxx", "-f"]),
    ("graphics", ["-Gxxx"]),
    ("audio", ["-Axxx"]),
    ("network", ["-nxxx", "-i"]),
    ("bluetooth", ["-Exxx"]),
    ("logical", ["-Lxxx"]),
    ("raid", ["-Rxxx"]),
    ("drives", ["-Dxxx", "-dxxx"]),
    ("partitions", ["-pxxx", "-jxxx", "-oxxx"]),
    ("usb", ["-Jxxx"]),
    ("sensors", ["-sxxx"]),
    ("repos", ["-r"]),
    ("processes", ["-t", "cm10"]),
    ("info", ["-Ixxx"]),
)


def _looks_like_inxi_failure(stdout: str) -> bool:
    """Return True if stdout is inxi diagnostic text, not JSON.

    inxi often prints human-readable messages (IRC-client warnings, option
    errors) to stdout while still exiting 0. Any non-JSON stdout is treated
    as a failure so the retry + fallback chain can kick in.
    """
    if not stdout:
        return True
    head = stdout.lstrip()[:1]
    return head not in ("[", "{")


class InxiCollector(BaseCollector):
    """Collect hardware info from a single inxi JSON invocation."""

    def __init__(self) -> None:
        super().__init__()
        # Single retry only: a fresh -v8 attempt that already failed once is
        # almost certain to fail the same way again, and a 90s × 3 retry chain
        # made the UI look frozen at 10% on desktop launches.
        self.max_retries = 1
        self.retry_delay = 0.5
        self.attempt_timeout = 45

    def collect(self, filter_sensitive: bool = False) -> dict:
        """Run inxi with retries and return parsed JSON or an error dict."""
        if not self.command_exists("inxi"):
            logger.error("inxi command not found in PATH")
            return {"error": "inxi command not found. Please install inxi."}
        
        command = INXI_COMMAND_FILTERED if filter_sensitive else INXI_COMMAND

        last_error = None
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                logger.info(f"Retrying inxi command (attempt {attempt + 1}/{self.max_retries + 1})")
                time.sleep(self.retry_delay)
            
            success, stdout, stderr = self.run_command(command, timeout=self.attempt_timeout)

            if success and stdout and not _looks_like_inxi_failure(stdout):
                try:
                    data = json.loads(stdout)
                    if stderr:
                        logger.debug("inxi succeeded with stderr: %s", stderr[:200])
                    return {"data": data, "format": "json"}
                except json.JSONDecodeError as e:
                    last_error = f"Failed to parse inxi output: {e}"
                    logger.warning(
                        "JSON parse error on attempt %d: %s. stdout head: %r",
                        attempt + 1, e, stdout[:200],
                    )
            elif success and _looks_like_inxi_failure(stdout):
                last_error = f"inxi returned diagnostic text instead of JSON: {stdout[:200]}"
                logger.warning(
                    "inxi diagnostic output on attempt %d: %s",
                    attempt + 1, stdout[:200],
                )
            else:
                last_error = stderr or "inxi command failed without output"
                logger.warning(
                    "inxi failed on attempt %d: stderr=%r stdout_head=%r",
                    attempt + 1, stderr[:200], stdout[:200],
                )

        logger.info("Trying fallback inxi command with simpler options")
        success, stdout, stderr = self.run_command(INXI_COMMAND_FALLBACK, timeout=30)

        if success and stdout and not _looks_like_inxi_failure(stdout):
            try:
                data = json.loads(stdout)
                logger.info("Fallback command succeeded")
                return {"data": data, "format": "json"}
            except json.JSONDecodeError as e:
                last_error = f"Failed to parse fallback inxi output: {e}"
                logger.error(last_error)
        else:
            logger.error(
                "Fallback inxi failed: stderr=%r stdout_head=%r",
                stderr[:200], stdout[:200],
            )

        section_result = self._collect_sections_individually(filter_sensitive)
        if section_result:
            return section_result

        return {"error": last_error or "inxi command failed after all retries"}

    def _collect_sections_individually(self, filter_sensitive: bool) -> dict | None:
        """Last-resort fallback: one timed-out inxi section must not blank all UI."""
        logger.info("Trying section-by-section inxi fallback")
        data = []
        failed_sections = []

        for name, report_args in INXI_SECTION_FALLBACKS:
            command = _build_inxi_command(report_args, filter_sensitive=filter_sensitive)
            success, stdout, stderr = self.run_command(command, timeout=10)

            if success and stdout and not _looks_like_inxi_failure(stdout):
                try:
                    section_data = json.loads(stdout)
                except json.JSONDecodeError as e:
                    failed_sections.append(name)
                    logger.warning(
                        "Section fallback %s JSON parse error: %s. stdout head: %r",
                        name, e, stdout[:200],
                    )
                    continue

                if isinstance(section_data, list):
                    data.extend(section_data)
                else:
                    data.append(section_data)
                continue

            failed_sections.append(name)
            logger.warning(
                "Section fallback %s failed: stderr=%r stdout_head=%r",
                name, stderr[:200], stdout[:200],
            )

        if not data:
            logger.error("Section-by-section inxi fallback produced no data")
            return None

        if failed_sections:
            logger.warning(
                "Section-by-section inxi fallback returned partial data; failed sections: %s",
                ", ".join(failed_sections),
            )

        return {
            "data": data,
            "format": "json",
            "partial": bool(failed_sections),
            "failed_sections": failed_sections,
        }
