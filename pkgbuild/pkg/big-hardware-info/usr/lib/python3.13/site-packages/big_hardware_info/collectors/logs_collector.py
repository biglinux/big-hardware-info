"""
System logs collector.

Gathers error and warning logs from dmesg and journald.
"""

import logging
from typing import List, Optional
from .base_collector import BaseCollector


logger = logging.getLogger(__name__)


class LogsCollector(BaseCollector):
    """
    Collector for system error and warning logs.
    
    Gathers information from dmesg and journalctl.
    """
    
    def collect(self) -> dict:
        """
        Collect all log information.
        
        Returns:
            Dictionary containing log data.
        """
        return {
            "dmesg_errors": self.collect_dmesg_errors(),
            "journal_errors": self.collect_journal_errors(),
        }
    
    def collect_dmesg_errors(self) -> dict:
        """
        Collect error and warning messages from dmesg.
        
        Returns:
            Dictionary with dmesg error data.
        """
        if not self.command_exists("dmesg"):
            return {"error": "dmesg command not found"}
        
        # Get errors and warnings without timestamps for cleaner output
        success, stdout, stderr = self.run_command(
            ["dmesg", "-t", "--level=alert,crit,err,warn"],
            timeout=30
        )
        
        if not success:
            # Try without level filtering (older dmesg versions)
            success, stdout, stderr = self.run_command(["dmesg"])
            if not success:
                return {"error": stderr or "dmesg command failed"}
        
        # Parse into structured data
        errors = []
        warnings = []
        
        for line in stdout.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            # Try to categorize
            lower_line = line.lower()
            if "error" in lower_line or "fail" in lower_line or "crit" in lower_line:
                errors.append(line)
            elif "warn" in lower_line:
                warnings.append(line)
            else:
                # Default to warning if we used --level filter
                warnings.append(line)
        
        return {
            "errors": errors,
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "raw": stdout,
        }
    
    def collect_journal_errors(self) -> dict:
        """
        Collect error messages from systemd journal.
        
        Returns:
            Dictionary with journald error data.
        """
        if not self.command_exists("journalctl"):
            return {"error": "journalctl command not found"}
        
        # Get errors from current boot
        success, stdout, stderr = self.run_command(
            ["journalctl", "-p", "err", "-b", "--no-pager"],
            timeout=60
        )
        
        if not success:
            return {"error": stderr or "journalctl command failed"}
        
        # Count errors by unit
        units = {}
        total_errors = 0
        
        for line in stdout.split("\n"):
            line = line.strip()
            if not line or line.startswith("--"):
                continue
            
            total_errors += 1
            
            # Try to extract unit name
            # Format: "Jan 01 00:00:00 hostname unit[pid]: message"
            parts = line.split()
            if len(parts) >= 5:
                unit_part = parts[4]
                # Remove [pid] suffix if present
                unit = unit_part.split("[")[0].rstrip(":")
                units[unit] = units.get(unit, 0) + 1
        
        return {
            "total_errors": total_errors,
            "by_unit": units,
            "raw": stdout,
        }
    
    def collect_recent_errors(self, hours: int = 24) -> dict:
        """
        Collect errors from the last N hours.
        
        Args:
            hours: Number of hours to look back.
            
        Returns:
            Dictionary with recent error data.
        """
        if not self.command_exists("journalctl"):
            return {"error": "journalctl command not found"}
        
        success, stdout, stderr = self.run_command(
            ["journalctl", "-p", "err", f"--since={hours} hours ago", "--no-pager"],
            timeout=60
        )
        
        if not success:
            return {"error": stderr or "journalctl command failed"}
        
        return {
            "hours": hours,
            "raw": stdout,
        }
