"""
Base class for hardware data collectors.
"""

import os
import subprocess
import logging
import shutil
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
    # TERM=dumb prevents children (inxi/Perl Term::ReadKey, smartctl, etc) from
    # probing terminal capabilities or width when launched from a desktop entry
    # without a controlling tty — a known cause of multi-minute hangs.
    env["TERM"] = "dumb"
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

            # stdin=DEVNULL avoids children inheriting an odd stdin (closed pipe
            # from a desktop-entry launch, or a non-TTY fd from a CLI wrapper)
            # which makes tools like inxi misdetect their environment.
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=shell,
                stdin=subprocess.DEVNULL,
                env=_build_subprocess_env(),
            )

            return (
                result.returncode == 0,
                result.stdout.strip(),
                result.stderr.strip() if capture_stderr else "",
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
    
