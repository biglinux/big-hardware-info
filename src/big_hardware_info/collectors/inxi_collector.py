"""Inxi-based hardware information collector."""

import json
import logging
import time
from .base_collector import BaseCollector


logger = logging.getLogger(__name__)


# --tty avoids inxi's IRC-client false-detection that breaks JSON output when
# launched from a desktop entry without a controlling terminal.
INXI_COMMAND = ["inxi", "--tty", "-c", "0", "-Fxxxa", "-v8", "--output", "json", "--output-file", "print"]
INXI_COMMAND_FILTERED = ["inxi", "--tty", "-c", "0", "-Fxxxa", "-v8", "-z", "--output", "json", "--output-file", "print"]
INXI_COMMAND_FALLBACK = ["inxi", "--tty", "-c", "0", "-Fxxx", "--output", "json", "--output-file", "print"]

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
        self.max_retries = 2
        self.retry_delay = 1.0

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
            
            success, stdout, stderr = self.run_command(command, timeout=90)

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
        success, stdout, stderr = self.run_command(INXI_COMMAND_FALLBACK, timeout=90)

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

        return {"error": last_error or "inxi command failed after all retries"}
