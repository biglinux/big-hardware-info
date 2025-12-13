"""
UI Views package for Hardware Reporter.

Contains component-based view classes for each hardware category,
following a clean separation of concerns architecture.
"""

from app.ui.views.base import HardwareSectionView
from app.ui.views.cpu import CpuSectionView
from app.ui.views.memory import MemorySectionView
from app.ui.views.gpu import GpuSectionView
from app.ui.views.network import NetworkSectionView
from app.ui.views.audio import AudioSectionView
from app.ui.views.disk import DiskSectionView

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
