"""
Base class for hardware data collectors.
"""

import subprocess
import logging
import shutil
from typing import Optional, Tuple
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


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
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=shell,
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
    
    def parse_key_value(self, text: str, separator: str = ":") -> dict:
        """
        Parse text with key:value pairs into a dictionary.
        
        Args:
            text: Text to parse.
            separator: Character separating key from value.
            
        Returns:
            Dictionary of key-value pairs.
        """
        result = {}
        for line in text.split("\n"):
            if separator in line:
                parts = line.split(separator, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key:
                        result[key] = value
        return result
