"""
Hardware data collectors package.

This module provides unified access to all hardware information collectors.
Architecture:
- InxiCollector: Executes inxi command ONCE and returns raw JSON
- InxiParser: Parses JSON data into structured dictionaries (NO command execution)
- HardwareCollector: Orchestrates collection using both classes
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_collector import BaseCollector
from .inxi_collector import InxiCollector
from .inxi_parser import InxiParser
from .pci_collector import PciCollector
from .usb_collector import UsbCollector
from .system_collector import SystemCollector
from .logs_collector import LogsCollector
from .webcam_collector import WebcamCollector


class HardwareCollector:
    """
    Unified hardware information collector.
    
    Uses InxiCollector for a SINGLE inxi call, then InxiParser to 
    parse the JSON into structured data.
    """
    
    def __init__(self):
        """Initialize all collectors."""
        self.inxi = InxiCollector()
        self.inxi_parser = InxiParser()
        self.pci = PciCollector()
        self.usb = UsbCollector()
        self.system = SystemCollector()
        self.logs = LogsCollector()
        self.webcam = WebcamCollector()
    
    def collect_all(self, progress_callback=None) -> dict:
        """
        Collect all hardware information efficiently.
        
        Uses a SINGLE inxi command call for best performance.
        
        Args:
            progress_callback: Optional callback(category, progress) for progress updates.
            
        Returns:
            Dictionary containing all collected hardware information.
        """
        data = {}
        
        if progress_callback:
            progress_callback("inxi", 0.1)
        
        # Step 1: Execute inxi command ONCE via InxiCollector
        inxi_result = self.inxi.collect(filter_sensitive=False)
        
        if progress_callback:
            progress_callback("inxi", 0.3)
        
        # Step 2: Parse the JSON data via InxiParser
        if "data" in inxi_result and inxi_result["data"]:
            parsed_data = self.inxi_parser.parse_full(inxi_result["data"])
            data.update(parsed_data)
        elif "error" in inxi_result:
            data["inxi_error"] = inxi_result["error"]
        
        if progress_callback:
            progress_callback("inxi", 0.6)
        
        # Collect additional system data in parallel
        tasks = {
            "pci": self.pci.collect,
            "usb": self.usb.collect,
            "system_extra": self.system.collect,
            "logs": self.logs.collect,
            "webcam": self.webcam.collect,
        }
        
        completed = 0
        total = len(tasks)
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(fn): name for name, fn in tasks.items()}
            
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    if name == "system_extra":
                        # Merge system data without overwriting
                        for k, v in result.items():
                            if k not in data or not data[k]:
                                data[k] = v
                    else:
                        data[name] = result
                except Exception as e:
                    data[name] = {"error": str(e)}
                
                completed += 1
                if progress_callback:
                    progress_callback(name, 0.6 + (0.4 * completed / total))
        
        if progress_callback:
            progress_callback("complete", 1.0)
        
        return data
    
    def collect_for_export(self, filter_sensitive: bool = True) -> dict:
        """
        Collect data for export/upload with optional privacy filtering.
        
        Args:
            filter_sensitive: If True, filter serial numbers, MACs etc.
            
        Returns:
            Dictionary containing collected hardware information.
        """
        inxi_result = self.inxi.collect(filter_sensitive=filter_sensitive)
        
        if "data" in inxi_result and inxi_result["data"]:
            return self.inxi_parser.parse_full(inxi_result["data"])
        
        return {"error": inxi_result.get("error", "Unknown error")}


__all__ = [
    "BaseCollector",
    "InxiCollector",
    "InxiParser",
    "PciCollector",
    "UsbCollector",
    "SystemCollector",
    "LogsCollector",
    "WebcamCollector",
    "HardwareCollector",
]
