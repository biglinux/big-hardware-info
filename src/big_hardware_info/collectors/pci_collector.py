"""
PCI device information collector.

Uses lspci to gather information about PCI devices.
"""

import logging
import re
from typing import List, Optional
from .base_collector import BaseCollector


logger = logging.getLogger(__name__)


class PciCollector(BaseCollector):
    """
    Collector for PCI device information.
    
    Uses lspci to enumerate and describe PCI devices.
    """
    
    # Linux Hardware database URL pattern
    LINUX_HARDWARE_URL = "https://linux-hardware.org/?id=pci:{vendor_id}-{device_id}"
    
    def collect(self) -> dict:
        """
        Collect all PCI device information.
        
        Returns:
            Dictionary containing PCI device data.
        """
        if not self.command_exists("lspci"):
            return {"error": "lspci command not found"}
        
        devices = self._get_device_list()
        detailed = self._get_detailed_info()
        
        return {
            "devices": devices,
            "detailed": detailed,
            "count": len(devices),
        }
    
    def _get_device_list(self) -> List[dict]:
        """
        Get list of PCI devices with basic info.
        
        Returns:
            List of device dictionaries.
        """
        # Use -nn to get both names and numeric IDs
        success, stdout, stderr = self.run_command(["lspci", "-nn"])
        
        if not success:
            return []
        
        devices = []
        for line in stdout.split("\n"):
            if not line.strip():
                continue
            
            device = self._parse_device_line(line)
            if device:
                devices.append(device)
        
        return devices
    
    def _parse_device_line(self, line: str) -> Optional[dict]:
        """
        Parse a single lspci -nn output line.
        
        Example line:
        00:00.0 Host bridge [0600]: Intel Corporation Device [8086:a70d] (rev 01)
        
        Args:
            line: Single line from lspci output.
            
        Returns:
            Dictionary with parsed device info, or None if parse fails.
        """
        try:
            # Split by first space to get slot
            parts = line.split(" ", 1)
            if len(parts) < 2:
                return None
            
            slot = parts[0]
            rest = parts[1]
            
            # Extract category (e.g., "Host bridge")
            category_match = re.match(r"^([^[]+)", rest)
            category = category_match.group(1).strip() if category_match else "Unknown"
            
            # Remove category from rest
            rest = rest[len(category):] if category != "Unknown" else rest
            
            # Extract class ID [XXXX]
            class_match = re.search(r"\[([0-9a-fA-F]{4})\]", rest)
            class_id = class_match.group(1) if class_match else ""
            
            # Extract vendor and name
            name_match = re.search(r":\s*(.+?)\s*\[[0-9a-fA-F]{4}:[0-9a-fA-F]{4}\]", rest)
            name = name_match.group(1).strip() if name_match else category
            
            # Extract vendor:device ID [XXXX:XXXX]
            id_match = re.search(r"\[([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\]", rest)
            vendor_id = id_match.group(1) if id_match else ""
            device_id = id_match.group(2) if id_match else ""
            
            # Extract revision if present
            rev_match = re.search(r"\(rev\s+([0-9a-fA-F]+)\)", rest)
            revision = rev_match.group(1) if rev_match else ""
            
            # Build linux-hardware.org URL
            hw_url = ""
            if vendor_id and device_id:
                hw_url = self.LINUX_HARDWARE_URL.format(
                    vendor_id=vendor_id.lower(),
                    device_id=device_id.lower(),
                )
            
            return {
                "slot": slot,
                "category": category,
                "name": name,
                "class_id": class_id,
                "vendor_id": vendor_id,
                "device_id": device_id,
                "full_id": f"{vendor_id}:{device_id}" if vendor_id and device_id else "",
                "revision": revision,
                "linux_hardware_url": hw_url,
                "raw": line,
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse PCI line: {line}, error: {e}")
            return None
    
    def _get_detailed_info(self) -> str:
        """
        Get detailed PCI information.
        
        Returns:
            Raw detailed output from lspci -vvv.
        """
        success, stdout, stderr = self.run_command(["lspci", "-nvv"])
        return stdout if success else ""
    
    def get_device_ids(self) -> List[str]:
        """
        Get just the list of vendor:device IDs.
        
        Returns:
            List of ID strings in format "XXXX:XXXX".
        """
        success, stdout, stderr = self.run_command(["lspci", "-n"])
        
        if not success:
            return []
        
        ids = []
        for line in stdout.split("\n"):
            parts = line.split()
            if len(parts) >= 3:
                # ID is usually the 3rd field
                id_part = parts[2]
                if ":" in id_part:
                    ids.append(id_part)
        
        return ids
