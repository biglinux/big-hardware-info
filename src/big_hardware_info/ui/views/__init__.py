"""
UI Views package for Hardware Reporter.

Contains component-based view classes for each hardware category,
following a clean separation of concerns architecture.
"""

from big_hardware_info.ui.views.base import HardwareSectionView
from big_hardware_info.ui.views.cpu import CpuSectionView
from big_hardware_info.ui.views.memory import MemorySectionView
from big_hardware_info.ui.views.gpu import GpuSectionView
from big_hardware_info.ui.views.network import NetworkSectionView
from big_hardware_info.ui.views.audio import AudioSectionView
from big_hardware_info.ui.views.disk import DiskSectionView

# View class registry - maps category IDs to their view classes
VIEW_REGISTRY = {
    "cpu": CpuSectionView,
    "memory": MemorySectionView,
    "gpu": GpuSectionView,
    "network": NetworkSectionView,
    "audio": AudioSectionView,
    "disk": DiskSectionView,
}

__all__ = [
    "HardwareSectionView",
    "CpuSectionView", 
    "MemorySectionView",
    "GpuSectionView",
    "NetworkSectionView",
    "AudioSectionView",
    "DiskSectionView",
    "VIEW_REGISTRY",
]
