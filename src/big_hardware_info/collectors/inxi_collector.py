"""
Inxi-based hardware information collector.

Uses a single inxi command with JSON output for comprehensive hardware data.
"""

import json
import logging
import time
from .base_collector import BaseCollector


logger = logging.getLogger(__name__)


# Standard inxi command for full hardware info
# --tty: Forces inxi to act as if running in a real terminal (fixes IRC/Background error)
# -c 0: Disable color codes to ensure clean JSON parsing
# -Fxxxa: Full report with maximum extra data
# -v8: Maximum verbosity level
# --output json: Output in JSON format
# --output-file print: Print to stdout instead of file
INXI_COMMAND = ["inxi", "--tty", "-c", "0", "-Fxxxa", "-v8", "--output", "json", "--output-file", "print"]

# Command with filtering enabled (for export/upload with privacy)
# -z: Filter sensitive information (serial numbers, MAC addresses, etc.)
INXI_COMMAND_FILTERED = ["inxi", "--tty", "-c", "0", "-Fxxxa", "-v8", "-z", "--output", "json", "--output-file", "print"]

# Simplified fallback command (fewer options, more compatible)
INXI_COMMAND_FALLBACK = ["inxi", "--tty", "-c", "0", "-Fxxx", "--output", "json", "--output-file", "print"]


class InxiCollector(BaseCollector):
    """
    Collector that uses inxi for hardware information.
    
    inxi provides comprehensive hardware and system information in a 
    structured JSON format. We use a single command to collect all data.
    """
    
    def __init__(self):
        """Initialize the collector."""
        super().__init__()
        self.max_retries = 2
        self.retry_delay = 1.0  # seconds
    
    def collect(self, filter_sensitive: bool = False) -> dict:
        """
        Collect full hardware information using inxi with retry logic.
        
        Args:
            filter_sensitive: If True, filter out sensitive information like
                            serial numbers and MAC addresses. Useful for
                            export/upload features. Default False.
        
        Returns:
            Dictionary containing all hardware information from inxi.
        """
        if not self.command_exists("inxi"):
            logger.error("inxi command not found in PATH")
            return {"error": "inxi command not found. Please install inxi."}
        
        command = INXI_COMMAND_FILTERED if filter_sensitive else INXI_COMMAND
        
        # Try with retry logic
        last_error = None
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                logger.info(f"Retrying inxi command (attempt {attempt + 1}/{self.max_retries + 1})")
                time.sleep(self.retry_delay)
            
            success, stdout, stderr = self.run_command(command, timeout=60)
            
            if success and stdout:
                try:
                    data = json.loads(stdout)
                    return {"data": data, "format": "json"}
                except json.JSONDecodeError as e:
                    last_error = f"Failed to parse inxi output: {e}"
                    logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
            else:
                last_error = stderr or "inxi command failed without output"
                logger.warning(f"inxi failed on attempt {attempt + 1}: {last_error}")
        
        # Try fallback command with simpler options
        logger.info("Trying fallback inxi command with simpler options")
        success, stdout, stderr = self.run_command(INXI_COMMAND_FALLBACK, timeout=60)
        
        if success and stdout:
            try:
                data = json.loads(stdout)
                logger.info("Fallback command succeeded")
                return {"data": data, "format": "json"}
            except json.JSONDecodeError as e:
                last_error = f"Failed to parse fallback inxi output: {e}"
                logger.error(last_error)
        
        return {"error": last_error or "inxi command failed after all retries"}
