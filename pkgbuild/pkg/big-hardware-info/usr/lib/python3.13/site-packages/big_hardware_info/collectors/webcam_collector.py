"""
Webcam device information collector.

Uses v4l2-ctl to gather detailed webcam information.
"""

import logging
import os
import re
from typing import List, Dict, Optional
from .base_collector import BaseCollector


logger = logging.getLogger(__name__)


class WebcamCollector(BaseCollector):
    """
    Collector for webcam device information.
    
    Uses v4l2-ctl for detailed video device enumeration.
    """
    
    def collect(self) -> dict:
        """
        Collect all webcam device information.
        
        Returns:
            Dictionary containing webcam device data.
        """
        if not self.command_exists("v4l2-ctl"):
            return {
                "devices": [],
                "count": 0,
                "v4l2_available": False,
            }
        
        # Get unique webcams using v4l2-ctl -A
        webcams = self._get_unique_webcams()
        
        return {
            "devices": webcams,
            "count": len(webcams),
            "v4l2_available": True,
        }
    
    def _get_unique_webcams(self) -> List[Dict]:
        """
        Get list of unique webcams using v4l2-ctl -A.
        
        Returns:
            List of webcam dictionaries with deduplicated devices.
        """
        success, stdout, _ = self.run_command(["v4l2-ctl", "-A"], timeout=5)
        
        if not success:
            return []
        
        webcams = []
        current_webcam = None
        
        for line in stdout.split("\n"):
            line = line.strip()
            
            if not line:
                continue
            
            # New webcam entry: "Name (bus-info):"
            if line.endswith("):"):
                if current_webcam:
                    webcams.append(current_webcam)
                
                # Parse name and bus info
                match = re.match(r"(.+?)\s+\((.+?)\):", line)
                if match:
                    current_webcam = {
                        "name": match.group(1).strip(),
                        "bus_info": match.group(2).strip(),
                        "devices": [],
                    }
            
            # Device path entries
            elif line.startswith("/dev/"):
                if current_webcam:
                    current_webcam["devices"].append(line)
        
        # Don't forget the last one
        if current_webcam:
            webcams.append(current_webcam)
        
        # Get USB IDs from lsusb
        usb_ids = self._get_usb_ids()
        
        # Enrich each webcam with detailed info from the first video device
        for webcam in webcams:
            # Find the main video device (video0, video2, etc - not video1, video3)
            main_device = None
            for dev in webcam.get("devices", []):
                if dev.startswith("/dev/video") and "media" not in dev:
                    main_device = dev
                    break
            
            if main_device:
                details = self._get_device_details(main_device)
                webcam.update(details)
                webcam["device_path"] = main_device
            
            # Try to match USB ID from bus_info
            bus_info = webcam.get("bus_info", "")
            for usb_name, usb_id in usb_ids.items():
                # Check if webcam name is in the USB device name
                if webcam.get("name", "").lower() in usb_name.lower() or \
                   usb_name.lower() in webcam.get("name", "").lower():
                    webcam["usb_id"] = usb_id
                    break
        
        return webcams
    
    def _get_usb_ids(self) -> Dict[str, str]:
        """
        Get mapping of USB device names to their IDs.
        
        Returns:
            Dictionary mapping device names to USB IDs.
        """
        if not self.command_exists("lsusb"):
            return {}
        
        success, stdout, _ = self.run_command(["lsusb"], timeout=5)
        
        if not success:
            return {}
        
        usb_ids = {}
        for line in stdout.split("\n"):
            # Parse lines like: Bus 001 Device 004: ID 17ef:4831 Lenovo FHD Webcam Audio
            match = re.search(r"ID\s+([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\s+(.+)$", line)
            if match:
                usb_id = match.group(1)
                name = match.group(2).strip()
                usb_ids[name] = usb_id
        
        return usb_ids
    
    def _get_device_details(self, device_path: str) -> Dict:
        """
        Get detailed info for a specific video device.
        
        Args:
            device_path: Path to the device (e.g., /dev/video0)
            
        Returns:
            Dictionary with device details.
        """
        details = {}
        
        # Get basic info with --all
        success, stdout, _ = self.run_command(
            ["v4l2-ctl", "--all", "-d", device_path],
            timeout=5
        )
        
        if success:
            details["raw"] = stdout
            
            for line in stdout.split("\n"):
                line = line.strip()
                
                if "Driver name" in line:
                    details["driver"] = self._extract_value(line)
                elif "Driver version" in line:
                    details["driver_version"] = self._extract_value(line)
                elif "Width/Height" in line:
                    wh = self._extract_value(line)
                    if wh and "/" in wh:
                        parts = wh.split("/")
                        if len(parts) == 2:
                            details["resolution"] = f"{parts[0].strip()}x{parts[1].strip()}"
                elif "Pixel Format" in line:
                    pf = self._extract_value(line)
                    if pf:
                        match = re.search(r"'(\w+)'", pf)
                        if match:
                            details["pixel_format"] = match.group(1)
                        else:
                            details["pixel_format"] = pf.split()[0] if pf else ""
                elif "Colorspace" in line:
                    details["colorspace"] = self._extract_value(line)
        
        # Get max FPS from format list
        max_fps = self._get_max_fps(device_path)
        if max_fps:
            details["max_fps"] = max_fps
        
        return details
    
    def _get_max_fps(self, device_path: str) -> str:
        """
        Get maximum FPS supported by the device.
        
        Args:
            device_path: Path to the device.
            
        Returns:
            String with max FPS or empty string.
        """
        success, stdout, _ = self.run_command(
            ["v4l2-ctl", "--list-formats-ext", "-d", device_path],
            timeout=10
        )
        
        if not success:
            return ""
        
        max_fps = 0.0
        
        for line in stdout.split("\n"):
            # Look for FPS entries like "Interval: Discrete 0.033s (30.000 fps)"
            match = re.search(r"\((\d+(?:\.\d+)?)\s*fps\)", line)
            if match:
                fps = float(match.group(1))
                if fps > max_fps:
                    max_fps = fps
        
        if max_fps > 0:
            # Format nicely
            if max_fps == int(max_fps):
                return f"{int(max_fps)} fps"
            return f"{max_fps:.1f} fps"
        
        return ""
    
    def _extract_value(self, line: str) -> str:
        """
        Extract value from a "key : value" line.
        
        Args:
            line: Line with colon-separated key-value.
            
        Returns:
            Extracted value string.
        """
        if ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
        return ""
