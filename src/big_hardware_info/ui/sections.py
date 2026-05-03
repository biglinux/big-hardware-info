"""Declarative registry of content sections rendered by the main window.

Each entry links a ``CATEGORIES`` id to a renderer callable. The callable
receives the ``MainWindow`` as its sole argument and is expected to append
widgets to ``window.content_container``.

Rendering is delegated through :func:`render_all` which isolates every
section in its own ``try/except`` so a single failure can't blank the UI.
"""

from __future__ import annotations

import logging
from typing import Callable, Iterable, Tuple

from big_hardware_info.ui.renderers import (
    AiHelpRenderer,
    BatteryRenderer,
    BluetoothRenderer,
    MachineRenderer,
    MoreInfoRenderer,
    PciRenderer,
    PrintersRenderer,
    SensorsRenderer,
    SummaryRenderer,
    SystemRenderer,
    UsbRenderer,
    WebcamsRenderer,
)
from big_hardware_info.ui.views import (
    AudioSectionView,
    CpuSectionView,
    DiskSectionView,
    GpuSectionView,
    MemorySectionView,
    NetworkSectionView,
)


logger = logging.getLogger(__name__)


SectionRenderFn = Callable[[object], None]


def _render_summary(window) -> None:
    SummaryRenderer(window).render()


def _render_ai_help(window) -> None:
    AiHelpRenderer(window).render()


def _render_cpu(window) -> None:
    view = CpuSectionView()
    view.render(window.hardware_data.get("cpu", {}) or {})
    window.content_container.append(view)


def _render_gpu(window) -> None:
    view = GpuSectionView(open_url_callback=window._open_url_with_toast)
    view.render(window.hardware_data.get("gpu", {}) or {})
    window.content_container.append(view)


def _render_webcams(window) -> None:
    WebcamsRenderer(window).render()


def _render_machine(window) -> None:
    MachineRenderer(window).render()


def _render_memory(window) -> None:
    view = MemorySectionView()
    view.set_disk_data(window.hardware_data.get("disk", {}) or {})
    view.render(window.hardware_data.get("memory", {}) or {})
    window.content_container.append(view)


def _render_audio(window) -> None:
    view = AudioSectionView(open_url_callback=window._open_url_with_toast)
    audio_data = window.hardware_data.get("audio", {}) or {}
    view.render(audio_data)
    window.content_container.append(view)
    raw = audio_data.get("raw") if isinstance(audio_data, dict) else None
    if raw:
        window._add_raw_expander(_full_output_label(), raw)


def _render_network(window) -> None:
    view = NetworkSectionView(open_url_callback=window._open_url_with_toast)
    net_data = window.hardware_data.get("network", {}) or {}
    view.render(net_data)
    window.content_container.append(view)
    raw = net_data.get("raw") if isinstance(net_data, dict) else None
    if raw:
        window._add_raw_expander(_full_output_label(), raw)


def _render_disk(window) -> None:
    view = DiskSectionView()
    disk_data = window.hardware_data.get("disk", {}) or {}
    view.render(disk_data)
    window.content_container.append(view)
    raw = disk_data.get("raw") if isinstance(disk_data, dict) else None
    if raw:
        window._add_raw_expander(_full_output_label(), raw)


def _render_battery(window) -> None:
    BatteryRenderer(window).render()


def _render_bluetooth(window) -> None:
    BluetoothRenderer(window).render()


def _render_usb(window) -> None:
    UsbRenderer(window).render()


def _render_pci(window) -> None:
    PciRenderer(window).render()


def _render_system(window) -> None:
    SystemRenderer(window).render()


def _render_printers(window) -> None:
    PrintersRenderer(window).render()


def _render_sensors(window) -> None:
    SensorsRenderer(window).render()


def _render_more_info(window) -> None:
    MoreInfoRenderer(window).render()


def _full_output_label() -> str:
    # Imported lazily to avoid a hard gettext dependency at module load.
    from big_hardware_info.utils.i18n import _
    return _("Full Output")


#: Declarative list of (category_id, renderer) tuples, in display order.
SECTIONS: Tuple[Tuple[str, SectionRenderFn], ...] = (
    ("summary", _render_summary),
    ("ai_help", _render_ai_help),
    ("cpu", _render_cpu),
    ("gpu", _render_gpu),
    ("webcam", _render_webcams),
    ("machine", _render_machine),
    ("memory", _render_memory),
    ("audio", _render_audio),
    ("network", _render_network),
    ("disk", _render_disk),
    ("battery", _render_battery),
    ("bluetooth", _render_bluetooth),
    ("usb", _render_usb),
    ("pci", _render_pci),
    ("system", _render_system),
    ("printer", _render_printers),
    ("sensors", _render_sensors),
    ("more_info", _render_more_info),
)


def render_all(
    window,
    add_section: Callable[[str, Callable[[], None]], None],
    sections: Iterable[Tuple[str, SectionRenderFn]] = SECTIONS,
) -> None:
    """Render every section, isolating exceptions per section.

    A renderer that raises is logged but does not abort the remaining
    sections — that isolation is the point of this function. The
    ``add_section`` callable comes from the window and owns the per-section
    header + container swap; we only wrap its ``content_func`` so a failure
    inside a renderer does not propagate to the caller.
    """
    for cat_id, renderer in sections:
        def content_func(_cat_id=cat_id, _renderer=renderer) -> None:
            try:
                _renderer(window)
            except Exception:
                logger.exception(
                    "Renderer for section %s raised — section left empty",
                    _cat_id,
                )
        try:
            add_section(cat_id, content_func)
        except Exception:
            logger.exception(
                "add_section failed for %s — skipping", cat_id,
            )
