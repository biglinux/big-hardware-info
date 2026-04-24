"""Guard against re-introducing duplicated PCI classification keywords.

The keyword list used to classify PCI devices as 'infrastructure' lived in
three places. It now has a single home in ``utils.constants``. This test
pins that: if someone adds a second copy, the test breaks so we notice.
"""

from big_hardware_info.ui.renderers import pci as pci_renderer
from big_hardware_info.utils.constants import PCI_INFRASTRUCTURE_KEYWORDS


def test_pci_renderer_imports_keywords_from_constants() -> None:
    assert pci_renderer.PCI_INFRASTRUCTURE_KEYWORDS is PCI_INFRASTRUCTURE_KEYWORDS


def test_main_window_does_not_redefine_keywords() -> None:
    from big_hardware_info.ui import main_window
    # Module must not redefine the list — we want one source of truth.
    assert not hasattr(main_window, "PCI_INFRASTRUCTURE_KEYWORDS")
