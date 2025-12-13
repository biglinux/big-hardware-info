"""
Inxi JSON Parser.

Parses the inxi JSON output into structured data.
This module ONLY parses data - it does NOT execute any commands.
Use InxiCollector to execute inxi commands.
"""

import re
import os
import json
import subprocess
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class InxiParser:
    """
    Parse inxi JSON output into structured data.
    
    This class is responsible ONLY for parsing JSON data.
    It does NOT execute inxi commands - use InxiCollector for that.
    
    The inxi JSON format uses numeric keys with format:
    "NNN#N#N#fieldname" where numbers are ordering metadata.
    """
    
    def __init__(self):
        """Initialize the parser."""
        self._cache = {}
    
    def _clean_key(self, key: str) -> str:
        """
        Extract field name from inxi JSON key.
        
        Args:
            key: Raw key like "000#1#1#Info"
            
        Returns:
            Clean key name like "Info"
        """
        if "#" in key:
            return key.split("#")[-1]
        return key
    
    def parse_full(self, data: List[Dict]) -> Dict[str, Any]:
        """
        Parse full inxi JSON output into structured categories.
        
        This is the MAIN entry point for parsing inxi data.
        
        Args:
            data: List of dictionaries from inxi JSON output.
            
        Returns:
            Dictionary with categorized hardware information.
        """
        result = {
            "cpu": {},
            "gpu": {},
            "memory": {},
            "audio": {},
            "network": {},
            "disk": {},
            "machine": {},
            "system": {},
            "battery": {},
            "sensors": {},
            "bluetooth": {},
        }
        
        if not data or not isinstance(data, list):
            logger.warning("parse_full: Invalid or empty data received")
            return result
        
        # Process each section in the JSON data
        for section in data:
            for key, value in section.items():
                section_name = self._clean_key(key)
                
                if "CPU" in section_name:
                    result["cpu"] = self._parse_cpu_section(value)
                elif "Graphics" in section_name:
                    result["gpu"] = self._parse_gpu_section(value)
                elif "Memory" in section_name:
                    result["memory"] = self._parse_memory_section(value)
                elif "Audio" in section_name:
                    result["audio"] = self._parse_audio_section(value)
                elif "Network" in section_name:
                    result["network"] = self._parse_network_section(value)
                elif "Drives" in section_name:
                    result["disk"] = self._parse_disk_section(value, data)
                elif "System" in section_name:
                    result["system"] = self._parse_system_section(value)
                elif "Machine" in section_name:
                    result["machine"] = self._parse_machine_section(value)
                elif "Battery" in section_name:
                    result["battery"] = self._parse_battery_section(value)
                elif "Sensors" in section_name:
                    result["sensors"] = self._parse_sensors_section(value)
                elif "Info" in section_name:
                    info_data = self._parse_info_section(value)
                    if "system" not in result:
                        result["system"] = {}
                    result["system"].update(info_data)
                elif "Processes" in section_name:
                    result["processes"] = self._parse_processes_section(value)
                elif "Repos" in section_name:
                    result["repos"] = self._parse_repos_section(value)
                elif "USB" in section_name:
                    result["usb_inxi"] = self._parse_usb_section(value)
                elif "Bluetooth" in section_name:
                    result["bluetooth"] = self._parse_bluetooth_section(value)
        
        # Create consolidated PCI devices list from all hardware sections
        result["pci_inxi"] = self._extract_pci_devices(result)
        
        return result
    
    def _extract_pci_devices(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract PCI device information from all hardware sections.
        
        Consolidates PCI devices from GPU, Audio, Network sections
        since inxi doesn't have a dedicated PCI section.
        
        Args:
            parsed_data: The parsed inxi data with all sections.
            
        Returns:
            Dictionary with devices list and device count.
        """
        devices = []
        seen_bus_ids = set()
        
        # Extract from GPU section
        gpu_devices = parsed_data.get("gpu", {}).get("devices", [])
        for device in gpu_devices:
            bus_id = device.get("bus_id", "")
            if bus_id and bus_id not in seen_bus_ids:
                seen_bus_ids.add(bus_id)
                devices.append({
                    "name": device.get("name", ""),
                    "vendor": device.get("vendor", ""),
                    "driver": device.get("driver", ""),
                    "bus_id": bus_id,
                    "chip_id": device.get("chip_id", ""),
                    "class_id": device.get("class_id", "0300"),  # VGA
                    "category": "Graphics",
                    "pcie_gen": device.get("pcie_gen", ""),
                    "pcie_speed": device.get("pcie_speed", ""),
                    "pcie_lanes": device.get("pcie_lanes", ""),
                })
        
        # Extract from Audio section
        audio_devices = parsed_data.get("audio", {}).get("devices", [])
        for device in audio_devices:
            bus_id = device.get("bus_id", "")
            # Only include PCI devices (bus_id format like XX:XX.X)
            if bus_id and ":" in bus_id and "-" not in bus_id:
                if bus_id not in seen_bus_ids:
                    seen_bus_ids.add(bus_id)
                    devices.append({
                        "name": device.get("name", ""),
                        "vendor": device.get("vendor", ""),
                        "driver": device.get("driver", ""),
                        "bus_id": bus_id,
                        "chip_id": device.get("chip_id", ""),
                        "class_id": device.get("class_id", "0403"),  # Audio
                        "category": "Audio",
                        "pcie_gen": device.get("pcie_gen", ""),
                        "pcie_speed": device.get("pcie_speed", ""),
                        "pcie_lanes": device.get("pcie_lanes", ""),
                    })
        
        # Extract from Network section
        network_devices = parsed_data.get("network", {}).get("devices", [])
        for device in network_devices:
            bus_id = device.get("bus_id", "")
            # Only include PCI devices
            if bus_id and ":" in bus_id and "-" not in bus_id:
                if bus_id not in seen_bus_ids:
                    seen_bus_ids.add(bus_id)
                    devices.append({
                        "name": device.get("name", ""),
                        "vendor": device.get("vendor", ""),
                        "driver": device.get("driver", ""),
                        "bus_id": bus_id,
                        "chip_id": device.get("chip_id", ""),
                        "class_id": device.get("class_id", "0200"),  # Network
                        "category": "Network",
                        "pcie_gen": device.get("pcie_gen", ""),
                        "pcie_speed": device.get("pcie_speed", ""),
                        "pcie_lanes": device.get("pcie_lanes", ""),
                    })
        
        # Sort by bus_id for consistent ordering
        devices.sort(key=lambda d: d.get("bus_id", ""))
        
        return {
            "devices": devices,
            "count": len(devices),
        }
    
    # =========================================================================
    # SECTION PARSERS - Parse specific hardware categories
    # =========================================================================
    
    def _parse_cpu_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse CPU data from inxi JSON section."""
        result = {
            "model": "",
            "cores": 0,
            "threads": 0,
            "type": "",
            "bits": 0,
            "arch": "",
            "gen": "",
            "built": "",
            "process": "",
            "family": "",
            "model_id": "",
            "stepping": "",
            "microcode": "",
            "cache_l1": "",
            "cache_l2": "",
            "cache_l3": "",
            "speed_current": 0,
            "speed_min": 0,
            "speed_max": 0,
            "bogomips": 0,
            "scaling_driver": "",
            "scaling_governor": "",
            "core_speeds": {},
            "flags": "",
            "vulnerabilities": [],
            "raw": "",
        }
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            # CPU Info
            if "model" in cleaned:
                result["model"] = cleaned["model"]
            if "type" in cleaned:
                result["type"] = cleaned["type"]
            if "bits" in cleaned:
                result["bits"] = cleaned["bits"]
            if "arch" in cleaned:
                result["arch"] = cleaned["arch"]
            if "gen" in cleaned:
                result["gen"] = cleaned["gen"]
            if "built" in cleaned:
                result["built"] = cleaned["built"]
            if "process" in cleaned:
                result["process"] = cleaned["process"]
            if "family" in cleaned:
                result["family"] = cleaned["family"]
            if "model-id" in cleaned:
                result["model_id"] = cleaned["model-id"]
            if "stepping" in cleaned:
                result["stepping"] = cleaned["stepping"]
            if "microcode" in cleaned:
                result["microcode"] = cleaned["microcode"]
            
            # Cache info
            if "L1" in cleaned:
                result["cache_l1"] = cleaned["L1"]
            if "L2" in cleaned:
                result["cache_l2"] = cleaned["L2"]
            if "L3" in cleaned:
                result["cache_l3"] = cleaned["L3"]
            
            # Parse Info for cores
            info = cleaned.get("Info", "")
            if info:
                if "quad core" in info.lower():
                    result["cores"] = 4
                elif "octa core" in info.lower():
                    result["cores"] = 8
                elif "dual core" in info.lower():
                    result["cores"] = 2
                elif "hexa core" in info.lower():
                    result["cores"] = 6
                match = re.search(r"(\d+)[- ]core", info.lower())
                if match:
                    result["cores"] = int(match.group(1))
            
            # Topology info for cores/threads
            if "cores" in cleaned:
                try:
                    result["cores"] = int(cleaned["cores"])
                except (ValueError, TypeError):
                    pass
            if "threads" in cleaned:
                try:
                    result["threads"] = int(cleaned["threads"])
                except (ValueError, TypeError):
                    pass
            
            # Core speeds (numbered keys)
            for k, v in cleaned.items():
                if k.isdigit():
                    result["core_speeds"][int(k)] = v
            
            # Speed info
            if "avg" in cleaned:
                result["speed_current"] = cleaned["avg"]
            if "min/max" in cleaned:
                minmax = str(cleaned["min/max"]).split("/")
                if len(minmax) == 2:
                    try:
                        result["speed_min"] = int(minmax[0])
                        result["speed_max"] = int(minmax[1])
                    except ValueError:
                        pass
            if "bogomips" in cleaned:
                result["bogomips"] = cleaned["bogomips"]
            if "driver" in cleaned:
                result["scaling_driver"] = cleaned["driver"]
            if "governor" in cleaned:
                result["scaling_governor"] = cleaned["governor"]
            
            # CPU Flags - check both possible key names
            if "Flags" in cleaned:
                result["flags"] = cleaned["Flags"]
            elif "Flags-basic" in cleaned:
                result["flags"] = cleaned["Flags-basic"]
            
            # Vulnerabilities - Type field indicates a vulnerability entry
            if "Type" in cleaned:
                result["vulnerabilities"].append({
                    "type": cleaned["Type"],
                    "status": cleaned.get("status", ""),
                    "mitigation": cleaned.get("mitigation", ""),
                })
        
        # Threads = number of logical processors (fallback)
        if result["threads"] == 0:
            result["threads"] = len(result["core_speeds"])
        
        # Fallback for cores
        if result["threads"] > 0 and result["cores"] == 0:
            result["cores"] = result["threads"] // 2 or result["threads"]
        
        return result
    
    def _parse_gpu_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse GPU data from inxi JSON section."""
        result = {
            "devices": [],
            "webcams": [],
            "displays": [],
            "display_info": {},
            "opengl": {},
            "vulkan": {},
            "egl": {},
            "monitors": [],
        }
        
        webcam_keywords = [
            "webcam", "camera", "cam", "usb2.0", "hd pro",
            "facetime", "isight", "brio", "c920", "c922", "c925",
            "streamcam", "kiyo", "uvc", "integrated_webcam"
        ]
        
        gpu_keywords = [
            "vga", "nvidia", "amd", "radeon", "geforce", "intel hd", "intel uhd",
            "intel iris", "matrox", "quadro", "firepro", "arc ", "display",
            "graphics", "gpu", "rtx", "gtx"
        ]
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            # GPU Devices
            if "Device" in cleaned:
                device_name = cleaned.get("Device", "").lower()
                driver = cleaned.get("driver", "").lower()
                
                is_webcam = any(kw in device_name for kw in webcam_keywords) or "uvcvideo" in driver
                is_gpu = any(kw in device_name for kw in gpu_keywords) or \
                         any(kw in driver for kw in ["nvidia", "amdgpu", "radeon", "i915", "nouveau"])
                
                if is_webcam and not is_gpu:
                    result["webcams"].append({
                        "name": cleaned.get("Device", ""),
                        "driver": cleaned.get("driver", ""),
                        "type": cleaned.get("type", "USB"),
                        "bus_id": cleaned.get("bus-ID", ""),
                        "chip_id": cleaned.get("chip-ID", ""),
                        "serial": cleaned.get("serial", ""),
                        "speed": cleaned.get("speed", ""),
                        "mode": cleaned.get("mode", ""),
                    })
                elif not is_webcam or is_gpu:
                    result["devices"].append({
                        "name": cleaned.get("Device", ""),
                        "vendor": cleaned.get("vendor", ""),
                        "driver": cleaned.get("driver", ""),
                        "driver_version": cleaned.get("v", ""),
                        "bus_id": cleaned.get("bus-ID", ""),
                        "arch": cleaned.get("arch", ""),
                        "chip_id": cleaned.get("chip-ID", ""),
                        "ports_active": cleaned.get("active", ""),
                        "ports_empty": cleaned.get("empty", ""),
                    })
            
            # Display/Server info
            elif "Display" in cleaned or "server" in cleaned:
                result["display_info"] = {
                    "display": cleaned.get("Display", ""),
                    "server": cleaned.get("server", ""),
                    "server_version": cleaned.get("v", ""),
                    "with": cleaned.get("with", ""),
                    "compositor": cleaned.get("compositor", ""),
                    "driver_loaded": cleaned.get("loaded", ""),
                    "gpu": cleaned.get("gpu", ""),
                }
            
            # Monitor info
            elif "Monitor" in cleaned:
                result["monitors"].append({
                    "name": cleaned.get("Monitor", ""),
                    "model": cleaned.get("model", ""),
                    "resolution": cleaned.get("res", ""),
                    "size": cleaned.get("size", ""),
                    "diagonal": cleaned.get("diag", ""),
                    "dpi": cleaned.get("dpi", ""),
                    "gamma": cleaned.get("gamma", ""),
                    "ratio": cleaned.get("ratio", ""),
                })
            
            # OpenGL info
            elif "API" in cleaned and cleaned.get("API") == "OpenGL":
                result["opengl"] = {
                    "version": cleaned.get("v", ""),
                    "compat_version": cleaned.get("compat-v", ""),
                    "vendor": cleaned.get("vendor", ""),
                    "glx_version": cleaned.get("glx-v", ""),
                    "direct_render": cleaned.get("direct-render", ""),
                    "renderer": cleaned.get("renderer", ""),
                    "memory": cleaned.get("memory", ""),
                }
            
            # Vulkan info
            elif "API" in cleaned and cleaned.get("API") == "Vulkan":
                result["vulkan"] = {
                    "version": cleaned.get("v", ""),
                    "layers": cleaned.get("layers", ""),
                    "devices": [],
                }
                if "device" in cleaned:
                    result["vulkan"]["devices"].append({
                        "device": cleaned.get("device", ""),
                        "type": cleaned.get("type", ""),
                        "name": cleaned.get("name", ""),
                        "driver": cleaned.get("driver", ""),
                    })
            
            # EGL info
            elif "API" in cleaned and cleaned.get("API") == "EGL":
                result["egl"] = {
                    "version": cleaned.get("v", ""),
                    "hw": cleaned.get("hw", ""),
                    "platforms": cleaned.get("platforms", ""),
                }
        
        return result
    
    def _parse_memory_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse memory data from inxi JSON section."""
        result = {
            "total": "",
            "used": "",
            "available": "",
            "used_percent": 0,
            "capacity": "",
            "slots": "",
            "ec": "",
            "note": "",
            "max_module_size": "",
            "modules": [],
        }
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            # System RAM info (from "RAM: total" entry)
            if "total" in cleaned and "Device" not in cleaned:
                total_str = str(cleaned.get("total", ""))
                if "GiB" in total_str or "GB" in total_str:
                    if not result["total"]:
                        result["total"] = total_str
            if "used" in cleaned and not result["used"]:
                result["used"] = str(cleaned["used"])
            if "available" in cleaned and not result["available"]:
                result["available"] = str(cleaned["available"])
            
            # Additional RAM info (capacity, slots, etc.)
            if "capacity" in cleaned:
                result["capacity"] = str(cleaned["capacity"])
            if "slots" in cleaned:
                result["slots"] = str(cleaned["slots"])
            if "EC" in cleaned:
                result["ec"] = str(cleaned["EC"])
            if "note" in cleaned:
                result["note"] = str(cleaned["note"])
            if "max-module-size" in cleaned:
                result["max_module_size"] = str(cleaned["max-module-size"])
            if "modules" in cleaned:
                result["modules_count"] = str(cleaned["modules"])
            
            # RAM modules
            if "Device" in cleaned and "size" in cleaned:
                size = cleaned.get("size", "")
                if size and "No Module" not in str(size):
                    # Get both specified and actual speed
                    spec_speed = cleaned.get("spec", cleaned.get("speed", ""))
                    actual_speed = cleaned.get("actual", cleaned.get("configured", ""))
                    
                    result["modules"].append({
                        "size": str(size),
                        "speed": str(spec_speed),
                        "actual_speed": str(actual_speed),
                        "type": str(cleaned.get("type", "")),
                        "slot": str(cleaned.get("Device", "")),
                        "manufacturer": str(cleaned.get("manufacturer", "")),
                        "volts": str(cleaned.get("volts", "")),
                        "part_no": str(cleaned.get("part-no", "")),
                        "serial": str(cleaned.get("serial", "")),
                    })
        
        # Calculate used percentage
        if result["total"] and result["used"]:
            try:
                total_match = re.search(r"([\d.]+)", result["total"])
                used_match = re.search(r"([\d.]+)", result["used"])
                if total_match and used_match:
                    total_val = float(total_match.group(1))
                    used_val = float(used_match.group(1))
                    if total_val > 0:
                        result["used_percent"] = round((used_val / total_val) * 100, 1)
            except (ValueError, ZeroDivisionError):
                pass
        
        return result
    
    def _parse_audio_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse audio data from inxi JSON section."""
        result = {"devices": []}
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            if "Device" in cleaned:
                device_type = cleaned.get("type", "").upper()
                is_usb = device_type == "USB"
                
                device = {
                    "name": cleaned.get("Device", ""),
                    "vendor": cleaned.get("vendor", ""),
                    "driver": cleaned.get("driver", ""),
                    "bus_id": cleaned.get("bus-ID", ""),
                    "chip_id": cleaned.get("chip-ID", ""),
                    "class_id": cleaned.get("class-ID", ""),
                    "type": device_type if device_type else "PCI",
                    "serial": cleaned.get("serial", ""),
                }
                
                # USB devices have different speed/lanes than PCIe
                if is_usb:
                    device["usb_speed"] = cleaned.get("speed", "")
                    device["usb_rev"] = cleaned.get("rev", "")
                else:
                    # PCIe devices
                    device["pcie_gen"] = cleaned.get("gen", "")
                    device["pcie_speed"] = cleaned.get("speed", "")
                    device["pcie_lanes"] = cleaned.get("lanes", "")
                
                result["devices"].append(device)
        
        return result
    
    def _parse_network_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse network data from inxi JSON section."""
        result = {"devices": [], "virtual_devices": []}
        
        current_device = None
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            # Hardware device entry
            if "Device" in cleaned:
                if current_device:
                    result["devices"].append(current_device)
                
                device_type = cleaned.get("type", "").upper()
                is_usb = device_type == "USB"
                
                current_device = {
                    "name": cleaned.get("Device", ""),
                    "vendor": cleaned.get("vendor", ""),
                    "driver": cleaned.get("driver", ""),
                    "bus_id": cleaned.get("bus-ID", ""),
                    "chip_id": cleaned.get("chip-ID", ""),
                    "class_id": cleaned.get("class-ID", ""),
                    "port": cleaned.get("port", ""),
                    "mac": cleaned.get("mac", ""),
                    "type": device_type if device_type else "PCI",
                }
                
                # USB devices have different speed/lanes than PCIe
                if is_usb:
                    current_device["usb_speed"] = cleaned.get("speed", "")
                    current_device["usb_rev"] = cleaned.get("rev", "")
                else:
                    # PCIe devices
                    current_device["pcie_gen"] = cleaned.get("gen", "")
                    current_device["pcie_speed"] = cleaned.get("speed", "")
                    current_device["pcie_lanes"] = cleaned.get("lanes", "")
            
            # Interface entry
            elif "IF" in cleaned or "IF-ID" in cleaned:
                interface_name = cleaned.get("IF", cleaned.get("IF-ID", ""))
                interface_info = {
                    "IF": interface_name,
                    "state": cleaned.get("state", ""),
                    "mac": cleaned.get("mac", ""),
                    "speed": cleaned.get("speed", ""),
                    "duplex": cleaned.get("duplex", ""),
                    "ip": cleaned.get("ip", ""),
                    "ipv6": cleaned.get("ipv6", ""),
                }
                
                # Check if virtual interface
                virtual_keywords = ["veth", "docker", "virbr", "br-", "vbox", "vmnet"]
                is_virtual = any(x in interface_name.lower() for x in virtual_keywords)
                
                if current_device:
                    current_device.update(interface_info)
                    result["devices"].append(current_device)
                    current_device = None
                elif is_virtual:
                    interface_info["name"] = interface_name
                    result["virtual_devices"].append(interface_info)
                else:
                    interface_info["name"] = interface_name
                    result["devices"].append(interface_info)
        
        if current_device:
            result["devices"].append(current_device)
        
        # Add IP addresses from system (for devices and virtual)
        self._add_ip_addresses(result["devices"])
        self._add_ip_addresses(result["virtual_devices"])
        
        # Add routing info
        result.update(self._get_network_routing_info())
        
        return result
    
    def _add_ip_addresses(self, devices: List[Dict[str, Any]]) -> None:
        """Add IP addresses to network devices from system."""
        try:
            result = subprocess.run(
                ["ip", "-j", "addr"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                ip_map = {}
                
                for iface in data:
                    ifname = iface.get("ifname", "")
                    addrs = iface.get("addr_info", [])
                    
                    ipv4 = ""
                    ipv6 = ""
                    for addr in addrs:
                        if addr.get("family") == "inet" and not ipv4:
                            ipv4 = addr.get("local", "")
                        elif addr.get("family") == "inet6" and not ipv6:
                            ipv6 = addr.get("local", "")
                    
                    if ipv4 or ipv6:
                        ip_map[ifname] = {"ipv4": ipv4, "ipv6": ipv6}
                
                for device in devices:
                    ifname = device.get("IF", device.get("name", ""))
                    if ifname and ifname in ip_map:
                        if not device.get("ip"):
                            device["ip"] = ip_map[ifname]["ipv4"]
                        if not device.get("ipv6"):
                            device["ipv6"] = ip_map[ifname]["ipv6"]
        except Exception as e:
            logger.debug(f"Failed to get IP addresses: {e}")
    
    def _get_network_routing_info(self) -> Dict[str, Any]:
        """Get network routing information (gateway, DNS)."""
        result = {"gateway": "", "dns_servers": [], "gateway_interface": ""}
        
        try:
            # Gateway with interface
            gw_result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if gw_result.returncode == 0:
                match = re.search(r"via\s+([\d.]+)(?:\s+dev\s+(\S+))?", gw_result.stdout)
                if match:
                    result["gateway"] = match.group(1)
                    if match.group(2):
                        result["gateway_interface"] = match.group(2)
            
            # DNS - Try resolvectl first (systemd-resolved)
            dns_found = False
            try:
                dns_result = subprocess.run(
                    ["resolvectl", "dns"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if dns_result.returncode == 0:
                    # Parse resolvectl output: "Link 2 (enp3s0): 192.168.1.1"
                    for line in dns_result.stdout.strip().split("\n"):
                        # Extract IPs from each line
                        parts = line.split(":")
                        if len(parts) >= 2:
                            ips = parts[-1].strip().split()
                            for ip in ips:
                                # Validate it looks like an IP
                                if re.match(r"^[\d.]+$|^[a-fA-F0-9:]+$", ip):
                                    if ip not in result["dns_servers"] and ip != "127.0.0.53":
                                        result["dns_servers"].append(ip)
                                        dns_found = True
            except FileNotFoundError:
                pass
            
            # Fallback to resolv.conf if resolvectl didn't work
            if not dns_found and os.path.exists("/etc/resolv.conf"):
                with open("/etc/resolv.conf", "r") as f:
                    for line in f:
                        if line.strip().startswith("nameserver"):
                            parts = line.split()
                            if len(parts) >= 2:
                                dns_ip = parts[1]
                                # Skip local resolver stub
                                if dns_ip not in ("127.0.0.53", "127.0.0.1") and dns_ip not in result["dns_servers"]:
                                    result["dns_servers"].append(dns_ip)
        except Exception as e:
            logger.debug(f"Failed to get routing info: {e}")
        
        return result
    
    def _parse_disk_section(self, items: List[Dict], full_data: List[Dict]) -> Dict[str, Any]:
        """Parse disk data from inxi JSON section."""
        result = {"drives": [], "partitions": [], "swap": [], "total_size": "", "used": "", "used_percent": 0}
        
        # Parse drives and Local Storage summary
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            # Local Storage summary
            if "Local Storage" in cleaned or "total" in cleaned:
                result["total_size"] = str(cleaned.get("total", ""))
                used_str = str(cleaned.get("used", ""))
                result["used"] = used_str
                # Extract percentage from "1.12 TiB (41.1%)"
                match = re.search(r"\(([\d.]+)%\)", used_str)
                if match:
                    result["used_percent"] = float(match.group(1))
                continue
            
            if "model" in cleaned and "size" in cleaned:
                drive_type = "HDD"
                tech = str(cleaned.get("tech", "")).upper()
                if "SSD" in tech:
                    drive_type = "SSD"
                elif "NVME" in tech:
                    drive_type = "NVMe"
                if "nvme" in str(cleaned.get("ID", "")).lower():
                    drive_type = "NVMe"
                
                result["drives"].append({
                    "id": cleaned.get("ID", ""),
                    "model": cleaned.get("model", ""),
                    "size": str(cleaned.get("size", "")),
                    "vendor": cleaned.get("vendor", ""),
                    "type": drive_type,
                    "serial": cleaned.get("serial", ""),
                    "temp": cleaned.get("temp", ""),
                    "speed": cleaned.get("speed", ""),
                    "lanes": cleaned.get("lanes", ""),
                    "firmware": cleaned.get("fw-rev", ""),
                    "scheme": cleaned.get("scheme", ""),
                    "block_physical": cleaned.get("physical", ""),
                    "block_logical": cleaned.get("logical", ""),
                    "maj_min": cleaned.get("maj-min", ""),
                })
        
        # Parse Partition and Swap sections
        for section in full_data:
            for key, value in section.items():
                section_name = self._clean_key(key)
                
                if "Partition" in section_name and isinstance(value, list):
                    for item in value:
                        cleaned = {}
                        for k, v in item.items():
                            clean_key = self._clean_key(k)
                            if v not in (None, "", []):
                                cleaned[clean_key] = v
                        
                        if "ID" in cleaned:
                            used_str = str(cleaned.get("used", ""))
                            used_percent = 0
                            match = re.search(r"\(([\d.]+)%\)", used_str)
                            if match:
                                used_percent = float(match.group(1))
                            
                            result["partitions"].append({
                                "id": cleaned.get("ID", ""),
                                "raw_size": str(cleaned.get("raw-size", "")),
                                "size": str(cleaned.get("size", "")),
                                "used": used_str,
                                "used_percent": used_percent,
                                "fs": cleaned.get("fs", ""),
                                "dev": cleaned.get("dev", ""),
                                "label": cleaned.get("label", ""),
                                "mount": cleaned.get("mount", cleaned.get("mountpoint", "")),
                            })
                
                elif "Swap" in section_name and isinstance(value, list):
                    for item in value:
                        cleaned = {}
                        for k, v in item.items():
                            clean_key = self._clean_key(k)
                            if v not in (None, "", []):
                                cleaned[clean_key] = v
                        
                        if "Kernel" in cleaned or "swappiness" in cleaned:
                            result["swap_kernel"] = {
                                "swappiness": cleaned.get("swappiness", ""),
                                "cache_pressure": cleaned.get("cache-pressure", ""),
                                "zswap": cleaned.get("zswap", ""),
                                "compressor": cleaned.get("compressor", ""),
                            }
                        elif "ID" in cleaned or "type" in cleaned:
                            used_str = str(cleaned.get("used", ""))
                            used_percent = 0
                            match = re.search(r"\(([\d.]+)%\)", used_str)
                            if match:
                                used_percent = float(match.group(1))
                            
                            result["swap"].append({
                                "id": cleaned.get("ID", ""),
                                "type": cleaned.get("type", ""),
                                "size": str(cleaned.get("size", "")),
                                "used": used_str,
                                "used_percent": used_percent,
                                "priority": cleaned.get("priority", ""),
                                "comp": cleaned.get("comp", ""),
                                "dev": cleaned.get("dev", cleaned.get("file", "")),
                            })
        
        return result
    
    def _parse_system_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse system data from inxi JSON section."""
        result = {
            "host": "",
            "kernel": "",
            "kernel_arch": "",
            "kernel_bits": "",
            "compiler": "",
            "compiler_version": "",
            "desktop": "",
            "desktop_version": "",
            "wm": "",
            "dm": "",
            "tk": "",
            "distro": "",
            "init": "",
        }
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            if "Host" in cleaned:
                result["host"] = cleaned["Host"]
            if "Kernel" in cleaned:
                result["kernel"] = cleaned["Kernel"]
            if "arch" in cleaned:
                result["kernel_arch"] = cleaned["arch"]
            if "bits" in cleaned:
                result["kernel_bits"] = str(cleaned["bits"])
            if "compiler" in cleaned:
                result["compiler"] = cleaned["compiler"]
            if "Desktop" in cleaned:
                result["desktop"] = cleaned["Desktop"]
                if "v" in cleaned:
                    result["desktop_version"] = cleaned["v"]
            if "wm" in cleaned:
                result["wm"] = cleaned["wm"]
            if "dm" in cleaned:
                result["dm"] = cleaned["dm"]
            if "tk" in cleaned:
                result["tk"] = cleaned["tk"]
            if "Distro" in cleaned:
                result["distro"] = cleaned["Distro"]
            if "Init" in cleaned:
                result["init"] = cleaned["Init"]
        
        # Collect additional system info
        result.update(self._collect_extra_system_info())
        
        return result
    
    def _collect_extra_system_info(self) -> Dict[str, str]:
        """Collect additional system information from commands."""
        extra = {}
        
        # Uptime
        try:
            result = subprocess.run(["uptime", "-p"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                extra["uptime"] = result.stdout.strip().replace("up ", "")
        except Exception:
            pass
        
        # Hostname
        try:
            result = subprocess.run(["hostname"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                extra["hostname"] = result.stdout.strip()
        except Exception:
            pass
        
        # Shell
        shell_name = os.environ.get("SHELL", "").split("/")[-1]
        extra["shell"] = shell_name
        try:
            if shell_name:
                result = subprocess.run([shell_name, "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    first_line = result.stdout.strip().split('\n')[0]
                    extra["shell"] = first_line
        except Exception:
            pass
        
        # Install date
        try:
            if os.path.exists("/var/log/pacman.log"):
                result = subprocess.run(
                    ["head", "-1", "/var/log/pacman.log"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    match = re.search(r"\[(\d{4}-\d{2}-\d{2})", result.stdout)
                    if match:
                        extra["install_date"] = match.group(1)
        except Exception:
            pass
        
        return extra
    
    def _parse_machine_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse machine data from inxi JSON section."""
        result = {
            "type": "",
            "system": "",
            "product": "",
            "mobo": "",
            "mobo_model": "",
            "mobo_version": "",
            "firmware_type": "",
            "firmware_vendor": "",
            "firmware_version": "",
            "firmware_date": "",
        }
        
        for item in items:
            sorted_keys = sorted(item.keys())
            found_mobo = False
            found_firmware = False
            mobo_v_set = False
            
            for key in sorted_keys:
                value = item[key]
                if value in (None, "", []):
                    continue
                    
                clean_key = self._clean_key(key)
                
                if clean_key == "Type":
                    result["type"] = value
                elif clean_key == "System":
                    result["system"] = value
                elif clean_key == "product":
                    result["product"] = value
                elif clean_key == "Mobo":
                    result["mobo"] = value
                    found_mobo = True
                elif clean_key == "model" and found_mobo:
                    result["mobo_model"] = value
                elif clean_key == "v" and found_mobo and not found_firmware and not mobo_v_set:
                    result["mobo_version"] = value
                    mobo_v_set = True
                elif clean_key == "Firmware":
                    result["firmware_type"] = value
                    found_firmware = True
                elif clean_key == "vendor" and found_firmware:
                    result["firmware_vendor"] = value
                elif clean_key == "v" and found_firmware:
                    result["firmware_version"] = value
                elif clean_key == "date":
                    result["firmware_date"] = value
        
        return result
    
    def _parse_battery_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse battery data from inxi JSON section."""
        result = {
            "present": False,
            "batteries": [],
        }
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            if "ID" in cleaned or "charge" in cleaned:
                result["present"] = True
                
                charge = 0
                if "charge" in cleaned:
                    charge_str = str(cleaned["charge"])
                    match = re.search(r"(\d+(?:\.\d+)?)", charge_str)
                    if match:
                        charge = float(match.group(1))
                
                volts = ""
                if "volts" in cleaned:
                    volts_val = cleaned["volts"]
                    if isinstance(volts_val, (int, float)):
                        volts = f"{volts_val} V"
                    else:
                        volts = str(volts_val)
                
                battery = {
                    "id": cleaned.get("ID", ""),
                    "charge": charge,
                    "condition": cleaned.get("condition", ""),
                    "volts": volts,
                    "volts_min": cleaned.get("min", ""),
                    "model": cleaned.get("model", ""),
                    "type": cleaned.get("type", ""),
                    "serial": cleaned.get("serial", ""),
                    "charging": cleaned.get("charging", ""),
                    "status": cleaned.get("status", ""),
                    "cycles": cleaned.get("cycles", ""),
                }
                result["batteries"].append(battery)
        
        # Backwards compatibility
        if result["batteries"]:
            first = result["batteries"][0]
            result["charge"] = first["charge"]
            result["status"] = first["status"]
            result["condition"] = first["condition"]
            result["model"] = first["model"]
            result["volts"] = first["volts"]
            result["serial"] = first["serial"]
            result["type"] = first["type"]
            result["cycles"] = first["cycles"]
        else:
            result["charge"] = 0
            result["status"] = ""
            result["condition"] = ""
            result["model"] = ""
            result["volts"] = ""
            result["serial"] = ""
            result["type"] = ""
            result["cycles"] = ""
        
        return result
    
    def _parse_sensors_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse sensors data from inxi JSON section."""
        result = {
            "temps": [],
            "fans": [],
            "sensors_cmd": "",
        }
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            if "cpu" in cleaned:
                temp_val = cleaned["cpu"]
                if isinstance(temp_val, (int, float)):
                    result["temps"].append({"name": "CPU", "temp": temp_val})
                elif isinstance(temp_val, str):
                    match = re.search(r"([\d.]+)", temp_val)
                    if match:
                        result["temps"].append({"name": "CPU", "temp": float(match.group(1))})
            
            if "mobo" in cleaned:
                temp_val = cleaned["mobo"]
                if isinstance(temp_val, (int, float)):
                    result["temps"].append({"name": "Motherboard", "temp": temp_val})
            
            if "gpu" in cleaned:
                temp_val = cleaned["gpu"]
                if isinstance(temp_val, (int, float)):
                    result["temps"].append({"name": "GPU", "temp": temp_val})
        
        # Run sensors command
        try:
            sensors_output = subprocess.run(
                ["sensors"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if sensors_output.returncode == 0:
                result["sensors_cmd"] = sensors_output.stdout.strip()
        except Exception as e:
            logger.debug(f"sensors command failed: {e}")
        
        return result
    
    def _parse_info_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse Info section from inxi JSON."""
        result = {}
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            if "total" in cleaned and "available" in cleaned:
                result["memory_total"] = cleaned.get("total", "")
                result["memory_available"] = cleaned.get("available", "")
                result["memory_used"] = cleaned.get("used", "")
            
            if "Processes" in cleaned:
                result["processes"] = str(cleaned.get("Processes", ""))
                result["uptime"] = cleaned.get("uptime", "")
                result["power_states"] = cleaned.get("states", "")
                result["suspend_mode"] = cleaned.get("suspend", "")
                result["hibernate_mode"] = cleaned.get("hibernate", "")
                result["hibernate_image"] = cleaned.get("image", "")
                if "Init" in cleaned:
                    result["init"] = cleaned.get("Init", "")
                    result["init_version"] = cleaned.get("v", "")
                    result["init_services"] = cleaned.get("services", "")
            
            if "Packages" in cleaned:
                result["packages"] = str(cleaned.get("Packages", ""))
                result["shell"] = cleaned.get("Shell", "")
                result["shell_version"] = cleaned.get("v", "")
                result["inxi_version"] = cleaned.get("inxi", "")
                result["gcc_version"] = cleaned.get("gcc", "")
                result["clang_version"] = cleaned.get("clang", "")
            
            # Repos info
            if "Repos" in cleaned:
                result["repos"] = str(cleaned.get("Repos", ""))
        
        return result
    
    def _parse_bluetooth_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse Bluetooth section from inxi JSON."""
        result = {"devices": []}
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            if "Device" in cleaned:
                result["devices"].append({
                    "name": cleaned.get("Device", ""),
                    "vendor": cleaned.get("vendor", ""),
                    "driver": cleaned.get("driver", ""),
                    "bus_id": cleaned.get("bus-ID", ""),
                    "chip_id": cleaned.get("chip-ID", ""),
                    "class_id": cleaned.get("class-ID", ""),
                    "state": cleaned.get("state", ""),
                    "bt_version": cleaned.get("bt-v", ""),
                })
        
        return result
    
    def _parse_processes_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse Processes section from inxi JSON."""
        result = {"cpu_top": [], "memory_top": []}
        
        current_section = None
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            if "CPU top" in cleaned:
                current_section = "cpu"
            elif "Memory top" in cleaned:
                current_section = "memory"
            elif "command" in cleaned:
                process = {
                    "command": cleaned.get("command", ""),
                    "pid": cleaned.get("pid", ""),
                    "cpu": cleaned.get("cpu", ""),
                    "mem": cleaned.get("mem", ""),
                }
                if current_section == "cpu":
                    result["cpu_top"].append(process)
                elif current_section == "memory":
                    result["memory_top"].append(process)
        
        return result
    
    def _parse_repos_section(self, items) -> Dict[str, Any]:
        """Parse Repos section from inxi JSON."""
        result = {"packages": {}, "repos": []}
        
        # Can be list of dicts or mixed with lists (repo URLs)
        if not isinstance(items, list):
            return result
        
        repo_name = ""
        for item in items:
            if isinstance(item, dict):
                cleaned = {}
                for k, v in item.items():
                    clean_key = self._clean_key(k)
                    if v not in (None, "", []):
                        cleaned[clean_key] = v
                
                # Packages info
                if "Packages" in cleaned:
                    result["packages"]["total"] = str(cleaned.get("Packages", ""))
                
                # Package manager counts
                if "pm" in cleaned:
                    pm_name = cleaned.get("pm", "")
                    pm_pkgs = cleaned.get("pkgs", 0)
                    result["packages"][pm_name] = pm_pkgs
                
                # Repo server info
                for key in cleaned:
                    if "repo" in key.lower() or "Active" in key:
                        repo_name = cleaned[key]
            elif isinstance(item, list):
                # This is a list of repo URLs
                for url in item:
                    if url and isinstance(url, str):
                        result["repos"].append({"name": repo_name, "url": url})
        
        return result
    
    def _parse_usb_section(self, items: List[Dict]) -> Dict[str, Any]:
        """Parse USB section from inxi JSON."""
        result = {"devices": [], "hubs": []}
        
        for item in items:
            cleaned = {}
            for k, v in item.items():
                clean_key = self._clean_key(k)
                if v not in (None, "", []):
                    cleaned[clean_key] = v
            
            # Hub entry
            if "Hub" in cleaned:
                hub = {
                    "name": cleaned.get("Hub", ""),
                    "info": cleaned.get("info", ""),
                    "ports": cleaned.get("ports", ""),
                    "rev": cleaned.get("rev", ""),
                    "speed": cleaned.get("speed", ""),
                    "lanes": cleaned.get("lanes", ""),
                    "mode": cleaned.get("mode", ""),
                    "chip_id": cleaned.get("chip-ID", ""),
                    "class_id": cleaned.get("class-ID", ""),
                }
                result["hubs"].append(hub)
            
            # Device entry
            elif "Device" in cleaned:
                device = {
                    "name": cleaned.get("Device", ""),
                    "info": cleaned.get("info", ""),
                    "type": cleaned.get("type", ""),
                    "driver": cleaned.get("driver", ""),
                    "interfaces": cleaned.get("interfaces", ""),
                    "rev": cleaned.get("rev", ""),
                    "speed": cleaned.get("speed", ""),
                    "lanes": cleaned.get("lanes", ""),
                    "mode": cleaned.get("mode", ""),
                    "power": cleaned.get("power", ""),
                    "chip_id": cleaned.get("chip-ID", ""),
                    "class_id": cleaned.get("class-ID", ""),
                    "serial": cleaned.get("serial", ""),
                }
                result["devices"].append(device)
        
        return result
    
    def clear_cache(self):
        """Clear the data cache."""
        self._cache = {}
