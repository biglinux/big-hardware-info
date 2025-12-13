"""
USB device information collector.

Uses lsusb to gather information about USB devices.
"""

import logging
import re
from typing import List, Optional
from .base_collector import BaseCollector


logger = logging.getLogger(__name__)


class UsbCollector(BaseCollector):
    """
    Collector for USB device information.
    
    Uses lsusb to enumerate and describe USB devices.
    """
    
    # Linux Hardware database URL pattern
    LINUX_HARDWARE_URL = "https://linux-hardware.org/?id=usb:{vendor_id}-{device_id}"
    
    def collect(self) -> dict:
        """
        Collect all USB device information.
        
        Returns:
            Dictionary containing USB device data.
        """
        if not self.command_exists("lsusb"):
            return {"error": "lsusb command not found"}
        
        devices = self._get_device_list()
        detailed = self._get_detailed_info()
        
        return {
            "devices": devices,
            "detailed": detailed,
            "count": len(devices),
        }
    
    def _clean_duplicate_name(self, name: str) -> str:
        """
        Clean up device names that have duplicate vendor/product info.
        
        Examples:
            "AKG C44-USB Microphone AKG C44-USB Microphone" -> "AKG C44-USB Microphone"
            "Lenovo Lenovo FHD Webcam Audio" -> "Lenovo FHD Webcam Audio"
        
        Args:
            name: Device name that may have duplicates.
            
        Returns:
            Cleaned device name.
        """
        if not name:
            return name
        
        # Check if the name contains duplicate words by splitting in half
        words = name.split()
        if len(words) >= 4:
            mid = len(words) // 2
            first_half = " ".join(words[:mid])
            second_half = " ".join(words[mid:])
            
            # If the halves are identical, use just one
            if first_half == second_half:
                return first_half
        
        # Also check for leading duplicate word (e.g., "Lenovo Lenovo ...")
        if len(words) >= 2:
            if words[0].lower() == words[1].lower():
                return " ".join(words[1:])
        
        return name
    
    def _get_device_list(self) -> List[dict]:
        """
        Get list of USB devices with basic info.
        
        Returns:
            List of device dictionaries.
        """
        success, stdout, stderr = self.run_command(["lsusb"])
        
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
        Parse a single lsusb output line.
        
        Example line:
        Bus 001 Device 002: ID 8087:8000 Intel Corp.
        
        Args:
            line: Single line from lsusb output.
            
        Returns:
            Dictionary with parsed device info, or None if parse fails.
        """
        try:
            # Pattern: Bus XXX Device XXX: ID XXXX:XXXX Name...
            pattern = r"Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s*(.*)"
            match = re.match(pattern, line)
            
            if not match:
                return None
            
            bus = match.group(1)
            device_num = match.group(2)
            vendor_id = match.group(3)
            device_id = match.group(4)
            raw_name = match.group(5).strip() or "Unknown Device"
            
            # Clean up duplicate vendor/product names
            name = self._clean_duplicate_name(raw_name)
            
            # Build linux-hardware.org URL
            hw_url = self.LINUX_HARDWARE_URL.format(
                vendor_id=vendor_id.lower(),
                device_id=device_id.lower(),
            )
            
            return {
                "bus": bus,
                "device": device_num,
                "vendor_id": vendor_id,
                "device_id": device_id,
                "full_id": f"{vendor_id}:{device_id}",
                "name": name,
                "linux_hardware_url": hw_url,
                "raw": line,
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse USB line: {line}, error: {e}")
            return None
    
    def _get_detailed_info(self) -> str:
        """
        Get detailed USB information.
        
        Returns:
            Raw detailed output from lsusb -v.
        """
        success, stdout, stderr = self.run_command(["lsusb", "-v"], timeout=60)
        return stdout if success else ""
    
    def get_device_ids(self) -> List[str]:
        """
        Get just the list of vendor:device IDs.
        
        Returns:
            List of ID strings in format "XXXX:XXXX".
        """
        success, stdout, stderr = self.run_command(["lsusb"])
        
        if not success:
            return []
        
        ids = []
        for line in stdout.split("\n"):
            match = re.search(r"ID\s+([0-9a-fA-F]{4}:[0-9a-fA-F]{4})", line)
            if match:
                ids.append(match.group(1))
        
        return ids
