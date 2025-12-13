"""
Renderers for hardware category sections.

Each renderer is responsible for displaying a specific category of hardware information.
"""

from big_hardware_info.ui.renderers.base import SectionRenderer
from big_hardware_info.ui.renderers.summary import SummaryRenderer
from big_hardware_info.ui.renderers.battery import BatteryRenderer
from big_hardware_info.ui.renderers.bluetooth import BluetoothRenderer
from big_hardware_info.ui.renderers.sensors import SensorsRenderer
from big_hardware_info.ui.renderers.printers import PrintersRenderer
from big_hardware_info.ui.renderers.webcams import WebcamsRenderer
from big_hardware_info.ui.renderers.system import SystemRenderer
from big_hardware_info.ui.renderers.usb import UsbRenderer
from big_hardware_info.ui.renderers.pci import PciRenderer
from big_hardware_info.ui.renderers.more_info import MoreInfoRenderer
from big_hardware_info.ui.renderers.machine import MachineRenderer

__all__ = [
    "SectionRenderer",
    "SummaryRenderer",
    "BatteryRenderer",
    "BluetoothRenderer",
    "SensorsRenderer",
    "PrintersRenderer",
    "WebcamsRenderer",
    "SystemRenderer",
    "UsbRenderer",
    "PciRenderer",
    "MoreInfoRenderer",
    "MachineRenderer",
]
