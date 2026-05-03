"""AI Help section: searchable, grouped list of ready-made chatbot prompts.

UX:
    [ Heading + didactic intro ]
    [ Search bar — filters rows by title/keyword/category ]
    [ PreferencesGroup per category, ActionRow per prompt ]
    Row click → dialog with editable text, language hint, Copy / Reset / Close.
"""

from __future__ import annotations

from typing import Optional

import gi
gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GLib, Gtk

from big_hardware_info.ui import builders as ui
from big_hardware_info.ui.renderers.base import SectionRenderer
from big_hardware_info.utils.ai_prompts import (
    CATEGORIES,
    Prompt,
    build_prompts,
    detect_reply_language,
)
from big_hardware_info.utils.i18n import _


class AiHelpRenderer(SectionRenderer):
    """Render didactic intro + searchable, grouped list of prompts."""

    def render(self) -> None:
        lang = detect_reply_language()
        prompts = build_prompts(self.data)

        self.container.append(self._build_intro(lang, len(prompts)))
        search_entry = self._build_search_entry()
        self.container.append(search_entry)

        groups = self._build_groups(prompts)
        groups_box = ui.box(vertical=True, spacing=8)
        for group in groups.values():
            groups_box.append(group)

        expander = Gtk.Expander(
            label=_("Show prompt list (%d available)") % len(prompts),
        )
        expander.set_expanded(False)
        expander.set_child(groups_box)
        expander.set_margin_top(4)
        self.container.append(expander)

        search_entry.connect(
            "search-changed",
            lambda entry: self._on_search_changed(
                groups, expander, entry.get_text(),
            ),
        )

    def _on_search_changed(
        self,
        groups: dict[str, "Adw.PreferencesGroup"],
        expander: Gtk.Expander,
        query: str,
    ) -> None:
        self._apply_filter(groups, query)
        if query.strip():
            expander.set_expanded(True)

    # ---------------- intro -------------------------------------------------

    def _build_intro(self, lang: str, count: int) -> Gtk.Widget:
        wrapper = ui.box(vertical=True, spacing=8)
        wrapper.set_margin_bottom(12)

        heading = ui.title(_("AI Help — Ready Prompts"))
        heading.set_xalign(0)

        subtitle = ui.label(
            _(
                "%(n)d ready-made prompts for the Linux desktop issues "
                "people actually report — Wi-Fi, hybrid GPU, suspend, "
                "Bluetooth audio, broken updates, and more. Click a row "
                "to review, edit the <fill in> placeholders, then copy. "
                "Each prompt asks the chatbot to reply in your system "
                "language (%(lang)s) and lists the diagnostic angles so "
                "answers stay focused. Sensitive data (MAC, IP, serial, "
                "UUID, hostname) is redacted before injection."
            ) % {"n": count, "lang": lang},
            css_classes=["dim-label"],
            selectable=True,
            wrap=True,
        )
        subtitle.set_xalign(0)

        wrapper.append(heading)
        wrapper.append(subtitle)
        return wrapper

    def _build_search_entry(self) -> Gtk.SearchEntry:
        entry = Gtk.SearchEntry()
        entry.set_placeholder_text(
            _("Filter prompts (e.g. wifi, suspend, nvidia, pacman)…"),
        )
        entry.set_margin_bottom(8)
        return entry

    # ---------------- groups ------------------------------------------------

    def _build_groups(
        self, prompts: list[Prompt],
    ) -> dict[str, Adw.PreferencesGroup]:
        groups: dict[str, Adw.PreferencesGroup] = {}
        rows_per_group: dict[str, list[Adw.ActionRow]] = {}

        for cat in CATEGORIES:
            group = Adw.PreferencesGroup()
            group.set_title(GLib.markup_escape_text(cat.title))
            group.set_description(GLib.markup_escape_text(cat.description))
            group.set_margin_bottom(4)
            groups[cat.key] = group
            rows_per_group[cat.key] = []

        for prompt in prompts:
            row = self._build_row(prompt)
            target = groups.get(prompt.category)
            if target is None:
                continue
            target.add(row)
            rows_per_group[prompt.category].append(row)

        for cat_key, rows in rows_per_group.items():
            if not rows:
                groups[cat_key].set_visible(False)
            self.make_searchable(
                groups[cat_key],
                " ".join(self._row_search_text(r) for r in rows),
            )

        return groups

    def _build_row(self, prompt: Prompt) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(prompt.title)
        row.set_subtitle(prompt.summary)
        row.set_activatable(True)

        copy_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        copy_btn.set_tooltip_text(_("Copy prompt to clipboard"))
        copy_btn.set_valign(Gtk.Align.CENTER)
        copy_btn.add_css_class("flat")
        copy_btn.connect(
            "clicked",
            lambda _b, p=prompt: self.copy_to_clipboard(p.body, p.title),
        )
        row.add_suffix(copy_btn)

        edit_btn = Gtk.Button.new_from_icon_name("document-edit-symbolic")
        edit_btn.set_tooltip_text(_("Open editor / preview"))
        edit_btn.set_valign(Gtk.Align.CENTER)
        edit_btn.add_css_class("flat")
        edit_btn.connect(
            "clicked",
            lambda _b, p=prompt: self._open_dialog(p),
        )
        row.add_suffix(edit_btn)

        row.connect("activated", lambda _r, p=prompt: self._open_dialog(p))

        row._prompt_search_text = self._prompt_search_text(prompt)  # type: ignore[attr-defined]
        return row

    # ---------------- search ------------------------------------------------

    def _row_search_text(self, row: Adw.ActionRow) -> str:
        return getattr(row, "_prompt_search_text", "")

    def _prompt_search_text(self, prompt: Prompt) -> str:
        return " ".join(
            (prompt.title, prompt.summary, prompt.category, *prompt.keywords),
        ).lower()

    def _apply_filter(
        self, groups: dict[str, Adw.PreferencesGroup], query: str,
    ) -> None:
        needle = query.strip().lower()
        for group in groups.values():
            visible_rows = 0
            row = group.get_first_child()  # internal box; iterate via list_box
            for action_row in self._iter_action_rows(group):
                text = getattr(action_row, "_prompt_search_text", "")
                visible = (not needle) or (needle in text)
                action_row.set_visible(visible)
                if visible:
                    visible_rows += 1
            group.set_visible(visible_rows > 0)

    def _iter_action_rows(self, group: Adw.PreferencesGroup):
        # PreferencesGroup hides its internal listbox; descend through children.
        stack: list[Gtk.Widget] = [group]
        while stack:
            widget = stack.pop()
            if isinstance(widget, Adw.ActionRow):
                yield widget
                continue
            child = widget.get_first_child() if hasattr(widget, "get_first_child") else None
            while child is not None:
                stack.append(child)
                child = child.get_next_sibling()

    # ---------------- dialog ------------------------------------------------

    def _open_dialog(self, prompt: Prompt) -> None:
        dialog = Adw.Dialog()
        dialog.set_title(prompt.title)
        dialog.set_content_width(720)
        dialog.set_content_height(560)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle.new(prompt.title, prompt.summary))
        toolbar.add_top_bar(header)

        body_box = ui.box(vertical=True, spacing=8)
        body_box.set_margin_top(12)
        body_box.set_margin_bottom(12)
        body_box.set_margin_start(12)
        body_box.set_margin_end(12)

        hint = ui.label(
            _(
                "Edit the <fill in> placeholders below, then press Copy. "
                "The chatbot will reply in %(lang)s."
            ) % {"lang": detect_reply_language()},
            css_classes=["dim-label"],
            wrap=True,
        )
        hint.set_xalign(0)
        body_box.append(hint)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        text_view = Gtk.TextView()
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_top_margin(8)
        text_view.set_bottom_margin(8)
        text_view.set_left_margin(8)
        text_view.set_right_margin(8)
        buffer = text_view.get_buffer()
        buffer.set_text(prompt.body)

        scrolled.set_child(text_view)
        body_box.append(scrolled)

        action_row = ui.row(spacing=8)
        reset_btn = Gtk.Button.new_with_label(_("Reset"))
        reset_btn.set_tooltip_text(_("Restore the original template"))
        reset_btn.connect(
            "clicked",
            lambda _b, b=buffer, body=prompt.body: b.set_text(body),
        )
        action_row.append(reset_btn)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        action_row.append(spacer)

        close_btn = Gtk.Button.new_with_label(_("Close"))
        close_btn.connect("clicked", lambda _b: dialog.close())
        action_row.append(close_btn)

        copy_btn = Gtk.Button.new_with_label(_("Copy"))
        copy_btn.add_css_class("suggested-action")
        copy_btn.connect(
            "clicked",
            lambda _b, b=buffer, t=prompt.title: self._copy_buffer(b, t),
        )
        action_row.append(copy_btn)
        body_box.append(action_row)

        toolbar.set_content(body_box)
        dialog.set_child(toolbar)

        parent = self._toplevel_window()
        if parent is not None:
            dialog.present(parent)
        else:
            dialog.present()

    def _copy_buffer(self, buffer: Gtk.TextBuffer, title: str) -> None:
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, True)
        self.copy_to_clipboard(text, title)

    def _toplevel_window(self) -> Optional[Gtk.Widget]:
        widget = self.window
        if hasattr(widget, "get_window"):
            return widget
        return None
