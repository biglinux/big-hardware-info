"""
UI Builder functions for Hardware Reporter.

Factory functions for creating common GTK4 widgets with consistent styling.
Reduces code duplication and ensures visual consistency.
"""

from typing import Any, Callable, Optional, List, Tuple

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango, Gdk

from big_hardware_info.utils.i18n import _


def card(vertical: bool = True, spacing: int = 12, css_classes: List[str] = None) -> Gtk.Box:
    """Create a styled card container."""
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL,
        spacing=spacing
    )
    box.add_css_class("card")
    for cls in (css_classes or []):
        box.add_css_class(cls)
    return box


def hero_card(spacing: int = 12) -> Gtk.Box:
    """Create a hero card with prominent styling."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    box.add_css_class("card")
    box.add_css_class("hero-card")
    return box


def label(
    text: str,
    css_classes: List[str] = None,
    halign: Gtk.Align = None,
    wrap: bool = False,
    selectable: bool = False,
    xalign: float = None,
    hexpand: bool = False
) -> Gtk.Label:
    """Create a styled label."""
    lbl = Gtk.Label(label=text)
    for cls in (css_classes or []):
        lbl.add_css_class(cls)
    if halign is not None:
        lbl.set_halign(halign)
    if xalign is not None:
        lbl.set_xalign(xalign)
    if wrap:
        lbl.set_wrap(True)
    if selectable:
        lbl.set_selectable(True)
    if hexpand:
        lbl.set_hexpand(True)
    return lbl


def title(text: str, level: int = 4) -> Gtk.Label:
    """Create a title label."""
    return label(text, css_classes=[f"title-{level}"], halign=Gtk.Align.START)


def dim_label(text: str, caption: bool = False) -> Gtk.Label:
    """Create a dim (secondary) label."""
    classes = ["dim-label"]
    if caption:
        classes.append("caption")
    return label(text, css_classes=classes, halign=Gtk.Align.START)


def heading(text: str, selectable: bool = True) -> Gtk.Label:
    """Create a heading label for values."""
    return label(text, css_classes=["heading"], halign=Gtk.Align.START, selectable=selectable)


def box(
    vertical: bool = True,
    spacing: int = 8,
    homogeneous: bool = False,
    margin_bottom: int = 0
) -> Gtk.Box:
    """Create a generic box container."""
    b = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL,
        spacing=spacing
    )
    b.set_homogeneous(homogeneous)
    if margin_bottom:
        b.set_margin_bottom(margin_bottom)
    return b


def row(spacing: int = 12) -> Gtk.Box:
    """Create a horizontal row."""
    return box(vertical=False, spacing=spacing)


def icon(name: str, size: int = 24, css_class: str = None) -> Gtk.Image:
    """Create an icon image."""
    img = Gtk.Image.new_from_icon_name(name)
    img.set_pixel_size(size)
    if css_class:
        img.add_css_class(css_class)
    return img


def button(
    label_text: str = None,
    icon_name: str = None,
    css_classes: List[str] = None,
    tooltip: str = None,
    on_click: Callable = None
) -> Gtk.Button:
    """Create a styled button."""
    if label_text:
        btn = Gtk.Button(label=label_text)
    else:
        btn = Gtk.Button()
    
    if icon_name:
        btn.set_icon_name(icon_name)
    
    for cls in (css_classes or []):
        btn.add_css_class(cls)
    
    if tooltip:
        btn.set_tooltip_text(tooltip)
    
    if on_click:
        btn.connect("clicked", on_click)
    
    return btn


def flat_button(
    label_text: str = None,
    icon_name: str = None,
    tooltip: str = None,
    on_click: Callable = None
) -> Gtk.Button:
    """Create a flat button."""
    return button(label_text, icon_name, ["flat"], tooltip, on_click)


def copy_button(tooltip: str = None, on_click: Callable = None) -> Gtk.Button:
    """Create a copy button with clipboard icon."""
    return flat_button(
        icon_name="edit-copy-symbolic",
        tooltip=tooltip or _("Copy to clipboard"),
        on_click=on_click
    )


def pill_button(label_text: str, suggested: bool = True, on_click: Callable = None) -> Gtk.Button:
    """Create a pill-shaped action button."""
    classes = ["pill"]
    if suggested:
        classes.append("suggested-action")
    return button(label_text, css_classes=classes, on_click=on_click)


def separator(vertical: bool = False, margins: Tuple[int, int] = None) -> Gtk.Separator:
    """Create a separator."""
    sep = Gtk.Separator(
        orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL
    )
    if margins:
        sep.set_margin_top(margins[0])
        sep.set_margin_bottom(margins[1])
    return sep


def progress_bar(
    fraction: float,
    hexpand: bool = True,
    show_percentage: bool = True
) -> Gtk.Box:
    """Create a progress bar with optional percentage label."""
    container = row(spacing=10)
    
    bar = Gtk.ProgressBar()
    bar.set_fraction(min(1.0, max(0.0, fraction)))
    bar.add_css_class("usage-bar")
    bar.set_hexpand(hexpand)
    
    # Auto color based on value
    percent = fraction * 100
    if percent > 90:
        bar.add_css_class("error")
    elif percent > 70:
        bar.add_css_class("warning")
    else:
        bar.add_css_class("success")
    
    container.append(bar)
    
    if show_percentage:
        pct = Gtk.Label(label=f"{percent:.1f}%")
        pct.add_css_class("caption")
        pct.set_width_chars(6)
        container.append(pct)
    
    return container


def spec_item(label_text: str, value: str) -> Gtk.Box:
    """Create a spec item with label above value."""
    item = box(vertical=True, spacing=2)
    item.append(dim_label(label_text, caption=True))
    item.append(heading(str(value)))
    return item


def info_row(label_text: str, value: str) -> Gtk.Box:
    """Create a horizontal label-value row."""
    r = row(spacing=12)
    r.add_css_class("info-row")
    
    lbl = dim_label(label_text)
    lbl.set_width_chars(15)
    lbl.set_xalign(0)
    r.append(lbl)
    
    val = label(str(value), halign=Gtk.Align.END, hexpand=True, wrap=True, selectable=True)
    val.set_xalign(1)
    r.append(val)
    
    return r


def grid(row_spacing: int = 4, col_spacing: int = 16) -> Gtk.Grid:
    """Create a configured grid."""
    g = Gtk.Grid()
    g.set_row_spacing(row_spacing)
    g.set_column_spacing(col_spacing)
    return g


def two_column_card(
    title_text: str,
    left_items: List[Tuple[str, Any]],
    right_items: List[Tuple[str, Any]],
    title_row_widgets: List[Gtk.Widget] = None
) -> Gtk.Box:
    """
    Create a card with title and two-column layout.
    
    This is the standard hardware device card pattern.
    
    Args:
        title_text: Card title.
        left_items: List of (label, value) for left column.
        right_items: List of (label, value) for right column.
        title_row_widgets: Optional widgets to add to title row (e.g., copy button).
    """
    card_box = hero_card()
    
    # Title row
    title_row = row(spacing=12)
    
    title_lbl = label(title_text, css_classes=["hero-title"], halign=Gtk.Align.START, wrap=True, hexpand=True)
    title_lbl.set_xalign(0)
    title_row.append(title_lbl)
    
    for w in (title_row_widgets or []):
        w.set_valign(Gtk.Align.CENTER)
        title_row.append(w)
    
    card_box.append(title_row)
    
    # Filter empty values
    left_items = [(l, v) for l, v in left_items if v and str(v) not in ("N/A", "Unknown", "?", "")]
    right_items = [(l, v) for l, v in right_items if v and str(v) not in ("N/A", "Unknown", "?", "")]
    
    if left_items or right_items:
        columns = row(spacing=0)
        
        # Left column
        left_col = box(vertical=True, spacing=8)
        left_col.set_hexpand(True)
        for lbl, val in left_items:
            left_col.append(spec_item(lbl, val))
        columns.append(left_col)
        
        if right_items:
            # Separator
            sep = separator(vertical=True)
            sep.set_margin_start(24)
            sep.set_margin_end(24)
            columns.append(sep)
            
            # Right column
            right_col = box(vertical=True, spacing=8)
            right_col.set_hexpand(True)
            for lbl, val in right_items:
                right_col.append(spec_item(lbl, val))
            columns.append(right_col)
        
        card_box.append(columns)
    
    return card_box


def action_card(
    icon_name: str,
    title_text: str,
    description: str,
    button_text: str,
    on_click: Callable
) -> Gtk.Box:
    """Create an action card with icon, title, description and button."""
    card_box = hero_card()
    
    # Header
    header = row(spacing=12)
    header.append(icon(icon_name, size=32, css_class="accent"))
    header.append(title(title_text))
    header.get_last_child().set_hexpand(True)
    card_box.append(header)
    
    # Description
    desc = label(description, css_classes=["dim-label"], halign=Gtk.Align.START, wrap=True)
    desc.set_xalign(0)
    card_box.append(desc)
    
    # Button row
    btn_row = row()
    btn_row.set_halign(Gtk.Align.END)
    btn_row.set_margin_top(8)
    btn_row.append(pill_button(button_text, on_click=on_click))
    card_box.append(btn_row)
    
    return card_box


def stat_card(icon_name: str, value: str, label_text: str) -> Gtk.Box:
    """Create a stat display card."""
    card_box = card(css_classes=["stat-card"])
    card_box.set_halign(Gtk.Align.CENTER)
    card_box.set_valign(Gtk.Align.CENTER)
    
    card_box.append(icon(icon_name, size=24, css_class="accent"))
    
    val = Gtk.Label(label=value)
    val.add_css_class("stat-value")
    val.set_wrap(True)
    val.set_max_width_chars(20)
    val.set_ellipsize(Pango.EllipsizeMode.END)
    card_box.append(val)
    
    lbl = dim_label(label_text)
    lbl.add_css_class("stat-label")
    card_box.append(lbl)
    
    return card_box


def badge(text: str, style: str = None) -> Gtk.Label:
    """Create a badge/pill label."""
    b = Gtk.Label(label=text.upper())
    b.add_css_class("device-badge")
    if style:
        b.add_css_class(f"{style}-badge")
    return b


def flow_box(
    max_per_line: int = 4,
    min_per_line: int = 2,
    row_spacing: int = 12,
    col_spacing: int = 12
) -> Gtk.FlowBox:
    """Create a responsive flow box grid."""
    fb = Gtk.FlowBox()
    fb.set_selection_mode(Gtk.SelectionMode.NONE)
    fb.set_homogeneous(True)
    fb.set_max_children_per_line(max_per_line)
    fb.set_min_children_per_line(min_per_line)
    fb.set_row_spacing(row_spacing)
    fb.set_column_spacing(col_spacing)
    return fb


def no_data_label(message: str = "No data available") -> Gtk.Label:
    """Create a centered 'no data' message."""
    lbl = dim_label(message)
    lbl.set_margin_top(32)
    lbl.set_margin_bottom(32)
    return lbl


def expander_with_text(title_text: str, content: str, expanded: bool = False) -> Gtk.Expander:
    """Create an expandable section with scrollable text."""
    exp = Gtk.Expander(label=title_text)
    exp.set_expanded(expanded)
    exp.add_css_class("card")
    
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scroll.set_max_content_height(300)
    scroll.set_propagate_natural_height(True)
    
    tv = Gtk.TextView()
    tv.set_editable(False)
    tv.set_cursor_visible(False)
    tv.set_monospace(True)
    tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    tv.set_margin_top(8)
    tv.get_buffer().set_text(content)
    
    scroll.set_child(tv)
    exp.set_child(scroll)
    
    return exp


def copy_to_clipboard(text: str):
    """Copy text to system clipboard."""
    clipboard = Gdk.Display.get_default().get_clipboard()
    clipboard.set(text)
