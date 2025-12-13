"""
System information collector.

Gathers various system configuration and state information.
"""

import os
import logging
from datetime import datetime
from typing import Optional, List
from .base_collector import BaseCollector


logger = logging.getLogger(__name__)


class SystemCollector(BaseCollector):
    """
    Collector for system configuration and state.
    
    Gathers information from various system sources like /proc, /etc,
    and system commands.
    """
    
    def collect(self) -> dict:
        """
        Collect all system information with parallel execution for performance.
        
        Returns:
            Dictionary containing system data.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Define collectors to run in parallel
        collectors = {
            "kernel": self.collect_kernel,
            "disk_usage": self.collect_disk_usage,
            "fstab": self.collect_fstab,
            "mhwd": self.collect_mhwd,
            "modules": self.collect_modules,
            "cmdline": self.collect_cmdline,
            "efi": self.collect_efi,
            "acpi": self.collect_acpi,
            "printer": self.collect_printer,
            "rfkill": self.collect_rfkill,
            "sdio": self.collect_sdio,
            "install_date": self.collect_install_date,
        }
        
        result = {}
        
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(func): name for name, func in collectors.items()}
            
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result[name] = future.result(timeout=10)
                except Exception as e:
                    result[name] = {"error": str(e)}
        
        return result
    
    def collect_kernel(self) -> dict:
        """
        Collect kernel information.
        
        Returns:
            Dictionary with kernel details.
        """
        kernel_version = ""
        success, stdout, _ = self.run_command(["uname", "-r"])
        if success:
            kernel_version = stdout
        
        kernel_name = ""
        success, stdout, _ = self.run_command(["uname", "-s"])
        if success:
            kernel_name = stdout
        
        machine = ""
        success, stdout, _ = self.run_command(["uname", "-m"])
        if success:
            machine = stdout
        
        return {
            "version": kernel_version,
            "name": kernel_name,
            "machine": machine,
        }
    
    def collect_disk_usage(self) -> dict:
        """
        Collect disk usage information for root partition.
        
        Returns:
            Dictionary with disk usage data.
        """
        success, stdout, _ = self.run_command(["df", "-h", "/"])
        
        if not success:
            return {"error": "Could not get disk usage"}
        
        lines = stdout.split("\n")
        if len(lines) < 2:
            return {"error": "Invalid df output"}
        
        # Parse the second line (first is header)
        parts = lines[1].split()
        if len(parts) < 6:
            return {"raw": stdout}
        
        return {
            "device": parts[0],
            "size": parts[1],
            "used": parts[2],
            "available": parts[3],
            "use_percent": parts[4],
            "mount_point": parts[5],
        }
    
    def collect_fstab(self) -> dict:
        """
        Collect /etc/fstab contents.
        
        Returns:
            Dictionary with fstab data.
        """
        content = self.read_file("/etc/fstab")
        
        if content is None:
            return {"error": "Could not read /etc/fstab"}
        
        # Parse fstab entries
        entries = []
        for line in content.split("\n"):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            
            parts = line.split()
            if len(parts) >= 4:
                entries.append({
                    "device": parts[0],
                    "mount_point": parts[1],
                    "type": parts[2],
                    "options": parts[3],
                    "dump": parts[4] if len(parts) > 4 else "0",
                    "pass": parts[5] if len(parts) > 5 else "0",
                })
        
        return {
            "entries": entries,
            "raw": content,
        }
    
    def collect_mhwd(self) -> dict:
        """
        Collect MHWD (Manjaro Hardware Detection) information.
        
        Returns:
            Dictionary with MHWD data.
        """
        result = {
            "installed_drivers": "",
            "installed_kernels": "",
            "available": self.command_exists("mhwd"),
        }
        
        if not result["available"]:
            return result
        
        # Get installed drivers
        success, stdout, _ = self.run_command(["mhwd", "-li"])
        if success:
            # Remove ANSI escape codes
            import re
            clean = re.sub(r'\x1B\[[0-9;]*[mG]', '', stdout)
            result["installed_drivers"] = clean
        
        # Get installed kernels
        success, stdout, _ = self.run_command(["mhwd-kernel", "-li"])
        if success:
            clean = re.sub(r'\x1B\[[0-9;]*[mG]', '', stdout)
            result["installed_kernels"] = clean
        
        return result
    
    def collect_modules(self) -> dict:
        """
        Collect loaded kernel modules.
        
        Returns:
            Dictionary with lsmod output.
        """
        success, stdout, _ = self.run_command(["lsmod"])
        
        if not success:
            return {"error": "Could not get module list"}
        
        # Parse lsmod output
        modules = []
        lines = stdout.split("\n")
        
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 3:
                modules.append({
                    "name": parts[0],
                    "size": parts[1],
                    "used_by": parts[2] if len(parts) > 2 else "0",
                    "dependencies": parts[3] if len(parts) > 3 else "",
                })
        
        return {
            "modules": modules,
            "count": len(modules),
            "raw": stdout,
        }
    
    def collect_cmdline(self) -> dict:
        """
        Collect kernel command line.
        
        Returns:
            Dictionary with boot parameters.
        """
        content = self.read_file("/proc/cmdline")
        
        if content is None:
            return {"error": "Could not read /proc/cmdline"}
        
        return {
            "raw": content,
            "parameters": content.split(),
        }
    
    def collect_efi(self) -> dict:
        """
        Collect EFI boot information.
        
        Returns:
            Dictionary with EFI boot entries.
        """
        if not self.command_exists("efibootmgr"):
            return {"available": False, "error": "efibootmgr not found"}
        
        # Check if system is EFI
        if not os.path.exists("/sys/firmware/efi"):
            return {"available": False, "reason": "System is not EFI"}
        
        result = {"available": True}
        
        # Basic info
        success, stdout, _ = self.run_command(["efibootmgr"])
        if success:
            result["basic"] = stdout
        
        # Verbose info
        success, stdout, _ = self.run_command(["efibootmgr", "-v"])
        if success:
            result["verbose"] = stdout
        
        return result
    
    def collect_acpi(self) -> dict:
        """
        Collect ACPI interrupt information.
        
        Returns:
            Dictionary with ACPI data.
        """
        result = {"interrupts": []}
        
        acpi_path = "/sys/firmware/acpi/interrupts"
        if not os.path.isdir(acpi_path):
            return {"error": "ACPI interrupts not available"}
        
        try:
            for filename in os.listdir(acpi_path):
                filepath = os.path.join(acpi_path, filename)
                content = self.read_file(filepath)
                if content and ("enabled" in content or "disabled" in content):
                    result["interrupts"].append({
                        "name": filename,
                        "value": content,
                    })
        except PermissionError:
            result["error"] = "Permission denied reading ACPI data"
        
        return result
    
    def collect_printer(self) -> dict:
        """
        Collect printer information.
        
        Returns:
            Dictionary with printer data.
        """
        result = {
            "printers": "",
            "status": "",
            "queue": "",
        }
        
        if not self.command_exists("lpstat"):
            return {"error": "lpstat not found (CUPS not installed?)"}
        
        # Get printer list
        success, stdout, _ = self.run_command(["lpstat", "-p"])
        if success:
            result["printers"] = stdout
        
        # Get printer status
        success, stdout, _ = self.run_command(["lpstat", "-s"])
        if success:
            result["status"] = stdout
        
        # Get print queue
        if self.command_exists("lpq"):
            success, stdout, _ = self.run_command(["lpq"])
            if success:
                result["queue"] = stdout
        
        return result
    
    def collect_rfkill(self) -> dict:
        """
        Collect rfkill (wireless device) status.
        
        Returns:
            Dictionary with rfkill data.
        """
        if not self.command_exists("rfkill"):
            return {"error": "rfkill not found"}
        
        success, stdout, _ = self.run_command(["rfkill", "list"])
        
        if not success:
            return {"error": "Could not get rfkill list"}
        
        return {
            "raw": stdout,
        }
    
    def collect_sdio(self) -> dict:
        """
        Collect SDIO device information.
        
        Returns:
            Dictionary with SDIO device data.
        """
        sdio_path = "/sys/bus/sdio/devices"
        
        if not os.path.isdir(sdio_path):
            return {"devices": [], "available": False}
        
        devices = []
        try:
            for device_name in os.listdir(sdio_path):
                device_path = os.path.join(sdio_path, device_name)
                
                vendor_file = os.path.join(device_path, "vendor")
                device_file = os.path.join(device_path, "device")
                uevent_file = os.path.join(device_path, "uevent")
                
                vendor = self.read_file(vendor_file) or ""
                device_id = self.read_file(device_file) or ""
                uevent = self.read_file(uevent_file) or ""
                
                # Extract hex IDs
                vendor_hex = vendor.replace("0x", "") if vendor else ""
                device_hex = device_id.replace("0x", "") if device_id else ""
                
                devices.append({
                    "name": device_name,
                    "vendor": vendor_hex,
                    "device": device_hex,
                    "uevent": uevent,
                })
        except PermissionError:
            return {"error": "Permission denied reading SDIO data"}
        
        return {
            "devices": devices,
            "available": True,
        }
    
    def collect_install_date(self) -> dict:
        """
        Estimate system install date from /etc modification time.
        
        Returns:
            Dictionary with install date estimate.
        """
        try:
            # Get oldest file in /etc
            success, stdout, _ = self.run_command(
                ["ls", "-lct", "/etc"],
                shell=False
            )
            
            if success:
                lines = stdout.split("\n")
                if lines:
                    # Last line is oldest
                    oldest = lines[-1] if lines[-1].strip() else lines[-2] if len(lines) > 1 else ""
                    parts = oldest.split()
                    if len(parts) >= 8:
                        date_str = " ".join(parts[5:8])
                        return {
                            "estimate": date_str,
                            "method": "/etc oldest file",
                        }
            
            return {"error": "Could not determine install date"}
            
        except Exception as e:
            return {"error": str(e)}
