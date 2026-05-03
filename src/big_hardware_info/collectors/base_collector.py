"""
Base class for hardware data collectors.
"""

import os
import pty
import subprocess
import logging
import shutil
import tempfile
from typing import Optional, Tuple
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


# Subprocesses inherit the parent's env by default; force a predictable locale
# so tools that tune output to $LANG (inxi, smartctl, lspci -v) stay parseable,
# and normalize $PATH so /usr/sbin binaries resolve when launched from a
# minimal desktop-entry environment.
def _build_subprocess_env() -> dict:
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    # Desktop launchers often omit TERM. Use a common terminal value instead of
    # "dumb" so command-line tools stay on the same code path as terminal runs.
    env.setdefault("TERM", "xterm-256color")
    # COLUMNS pins width so tools that still ioctl(TIOCGWINSZ) get a sane fallback.
    env.setdefault("COLUMNS", "200")
    env.setdefault("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
    if "/usr/sbin" not in env["PATH"].split(":"):
        env["PATH"] = env["PATH"] + ":/usr/sbin:/sbin"
    return env


class BaseCollector(ABC):
    """
    Abstract base class for hardware information collectors.
    
    Provides common utilities for running shell commands and parsing output.
    """
    
    @abstractmethod
    def collect(self) -> dict:
        """
        Collect hardware information.
        
        Returns:
            Dictionary containing the collected information.
        """
        pass
    
    def run_command(
        self,
        command: list,
        timeout: int = 30,
        shell: bool = False,
        capture_stderr: bool = True,
        use_pkexec: bool = False,
    ) -> Tuple[bool, str, str]:
        """
        Run a shell command and return its output.
        
        Args:
            command: Command to run as list of arguments.
            timeout: Timeout in seconds.
            shell: Whether to run through shell.
            capture_stderr: Whether to capture stderr.
            use_pkexec: Whether to use pkexec for privilege escalation.
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            if use_pkexec:
                # Check if pkexec is available
                if shutil.which("pkexec"):
                    command = ["pkexec"] + command
                else:
                    logger.warning("pkexec not available, running without elevation")
            
            if shell and isinstance(command, list):
                command = " ".join(command)

            # Use regular temporary files instead of stdout/stderr pipes.
            # Some tools spawned by inxi can leave inherited pipe FDs open after
            # the main process exits, making Python wait for EOF until timeout.
            #
            # stdin is a pty slave, not /dev/null: bluez `btmgmt info` (called by
            # `inxi -E`/`-v8`) reads stdin even with a cmdline arg and hangs
            # forever when stdin gives EOF. A pty never EOFs, so it behaves like
            # the interactive shell case where the bug never fires.
            stdin_master_fd, stdin_slave_fd = pty.openpty()
            with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as stdout_file:
                if capture_stderr:
                    stderr_target = tempfile.TemporaryFile(
                        "w+",
                        encoding="utf-8",
                        errors="replace",
                    )
                else:
                    stderr_target = subprocess.DEVNULL

                try:
                    result = subprocess.run(
                        command,
                        stdout=stdout_file,
                        stderr=stderr_target,
                        text=True,
                        timeout=timeout,
                        shell=shell,
                        stdin=stdin_slave_fd,
                        start_new_session=True,
                        env=_build_subprocess_env(),
                    )

                    stdout_file.seek(0)
                    stdout = stdout_file.read().strip()

                    stderr = ""
                    if capture_stderr:
                        stderr_target.seek(0)
                        stderr = stderr_target.read().strip()
                finally:
                    if capture_stderr:
                        stderr_target.close()
                    os.close(stdin_master_fd)
                    os.close(stdin_slave_fd)

            return (
                result.returncode == 0,
                stdout,
                stderr,
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {command}")
            return False, "", "Command timed out"
        except FileNotFoundError as e:
            logger.error(f"Command not found: {e}")
            return False, "", str(e)
        except Exception as e:
            logger.error(f"Error running command {command}: {e}")
            return False, "", str(e)
    
    def command_exists(self, command: str) -> bool:
        """
        Check if a command exists on the system.
        
        Args:
            command: Command name to check.
            
        Returns:
            True if command exists, False otherwise.
        """
        return shutil.which(command) is not None
    
    def read_file(self, path: str) -> Optional[str]:
        """
        Read contents of a file.
        
        Args:
            path: Path to file.
            
        Returns:
            File contents or None if file doesn't exist or can't be read.
        """
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read().strip()
        except (FileNotFoundError, PermissionError, IOError) as e:
            logger.debug(f"Could not read {path}: {e}")
            return None
    
