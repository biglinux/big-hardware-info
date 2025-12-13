"""
Renderers for hardware category sections.

Each renderer is responsible for displaying a specific category of hardware information.
"""

from app.ui.renderers.base import SectionRenderer
from app.ui.renderers.summary import SummaryRenderer
from app.ui.renderers.battery import BatteryRenderer
from app.ui.renderers.bluetooth import BluetoothRenderer
from app.ui.renderers.sensors import SensorsRenderer
from app.ui.renderers.printers import PrintersRenderer
from app.ui.renderers.webcams import WebcamsRenderer
from app.ui.renderers.system import SystemRenderer
from app.ui.renderers.usb import UsbRenderer
from app.ui.renderers.pci import PciRenderer
from app.ui.renderers.more_info import MoreInfoRenderer
from app.ui.renderers.machine import MachineRenderer

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
