from big_hardware_info.export.html_generator import HtmlGenerator
from big_hardware_info.models.hardware_info import HardwareInfo


def test_sidebar_uses_translated_names(monkeypatch):
    hw = HardwareInfo()
    gen = HtmlGenerator(hw)

    # Monkeypatch the translation function used by the HTML generator module
    import big_hardware_info.export.html_generator as hg
    monkeypatch.setattr(hg, '_', lambda s: f"X[{s}]")

    sidebar_html = gen._render_sidebar()
    # Ensure that category names are translated in the sidebar
    assert "X[Summary]" in sidebar_html
    assert "X[Processor]" in sidebar_html
    # Ensure aria-label uses translated 'Go to' prefix
    assert "X[Go to]" in sidebar_html
