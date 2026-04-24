"""Regression guard for the "no items at startup" bug.

``sections.render_all`` must keep rendering the remaining sections when
one renderer raises — that isolation is why the function exists. This
test does NOT spin up GTK; it verifies the contract purely in Python.
"""

from typing import List

from big_hardware_info.ui import sections


class _FakeWindow:
    """Minimal window stub — the render functions under test only need a
    sentinel object to pass around.
    """

    hardware_data: dict = {}
    content_container = None


def test_render_all_isolates_a_raising_section() -> None:
    """One raising renderer does not abort the remaining sections."""
    window = _FakeWindow()
    rendered: List[str] = []

    def good(cat_id: str):
        def _fn(_window):
            rendered.append(cat_id)
        return _fn

    def bad(_window):
        raise RuntimeError("boom")

    fake_sections = (
        ("summary", good("summary")),
        ("cpu", bad),
        ("gpu", good("gpu")),
        ("memory", bad),
        ("disk", good("disk")),
    )

    seen = []

    def add_section(cat_id, content_func):
        content_func()
        seen.append(cat_id)

    sections.render_all(window, add_section, fake_sections)

    # Every section was attempted (no early abort).
    assert seen == ["summary", "cpu", "gpu", "memory", "disk"]
    # Only the non-raising renderers produced output.
    assert rendered == ["summary", "gpu", "disk"]


def test_render_all_isolates_add_section_failures() -> None:
    """A failure in add_section itself also must not abort the loop."""
    window = _FakeWindow()

    fake_sections = (
        ("summary", lambda _w: None),
        ("cpu", lambda _w: None),
        ("gpu", lambda _w: None),
    )

    seen = []
    call_count = {"n": 0}

    def flaky_add_section(cat_id, content_func):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("add_section failed for cpu")
        content_func()
        seen.append(cat_id)

    sections.render_all(window, flaky_add_section, fake_sections)
    assert seen == ["summary", "gpu"]


def test_default_section_list_covers_every_category() -> None:
    """Every id in ``CATEGORIES`` must have a renderer in ``SECTIONS``.

    Keeps the declarative table in sync with the sidebar so we don't end up
    with a visible category that silently has no content.
    """
    from big_hardware_info.models.hardware_info import CATEGORIES

    section_ids = {cat_id for cat_id, _ in sections.SECTIONS}
    assert set(CATEGORIES.keys()) == section_ids
