"""Card creation utilities for the hardware info application.

This module provides factory functions for creating common UI card widgets.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk


def create_info_card(title: str, subtitle: str = "", icon_name: str = "", 
                     properties: list = None, searchable_extra: str = "") -> Gtk.Widget:
    """
    Create an Adwaita-style info card with optional properties.
    
    Args:
        title: Main title
        subtitle: Optional subtitle
        icon_name: Optional icon
        properties: Optional list of (label, value) tuples
        searchable_extra: Additional text for search
    
    Returns:
        An Adwaita-styled card widget
    """
    # Create card container
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    card.add_css_class("card")
    
    # Header with icon and title
    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    
    if icon_name:
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(48)
        icon.add_css_class("accent")
        header.append(icon)
    
    title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    title_box.set_valign(Gtk.Align.CENTER)
    
    title_label = Gtk.Label(label=title)
    title_label.add_css_class("title-3")
    title_label.set_halign(Gtk.Align.START)
    title_label.set_wrap(True)
    title_label.set_selectable(True)
    title_box.append(title_label)
    
    if subtitle:
        sub_label = Gtk.Label(label=subtitle)
        sub_label.add_css_class("dim-label")
        sub_label.set_halign(Gtk.Align.START)
        sub_label.set_wrap(True)
        sub_label.set_selectable(True)
        title_box.append(sub_label)
    
    header.append(title_box)
    card.append(header)
    
    # Properties list
    if properties:
        props_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        props_box.set_margin_top(8)
        
        for prop in properties:
            if len(prop) >= 2:
                label, value = prop[0], prop[1]
                
                prop_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                
                label_widget = Gtk.Label(label=f"{label}:")
                label_widget.add_css_class("dim-label")
                label_widget.set_halign(Gtk.Align.START)
                label_widget.set_width_chars(15)
                label_widget.set_xalign(0)
                prop_row.append(label_widget)
                
                value_widget = Gtk.Label(label=str(value) if value else "N/A")
                value_widget.set_halign(Gtk.Align.START)
                value_widget.set_hexpand(True)
                value_widget.set_wrap(True)
                value_widget.set_xalign(0)
                value_widget.set_selectable(True)
                prop_row.append(value_widget)
                
                props_box.append(prop_row)
        
        card.append(props_box)
    
    # Build searchable text
    searchable_parts = [title, subtitle, searchable_extra]
    if properties:
        for prop in properties:
            if len(prop) >= 2:
                searchable_parts.append(f"{prop[0]} {prop[1]}")
    
    card.searchable_text = " ".join(filter(None, searchable_parts))
    
    return card


def create_property_list(title: str, icon_name: str, properties: list, searchable_extra: str = "") -> Gtk.Widget:
    """
    Create an Adwaita-style property list card.
    
    Args:
        title: Card title
        icon_name: Icon name for the card header
        properties: List of (label, value) tuples or (label, value, icon) tuples
        searchable_extra: Additional text for search indexing
    
    Returns:
        A GtkListBox with boxed-list style containing AdwActionRows
    """
    import gi
    gi.require_version("Adw", "1")
    from gi.repository import Adw
    
    # Create outer box for the section
    outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    
    # Add title if provided
    if title:
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(20)
            icon.add_css_class("accent")
            title_box.append(icon)
        
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("title-4")
        title_label.set_halign(Gtk.Align.START)
        title_box.append(title_label)
        
        outer_box.append(title_box)
    
    # Create list box with Adwaita styling
    listbox = Gtk.ListBox()
    listbox.set_selection_mode(Gtk.SelectionMode.NONE)
    listbox.add_css_class("boxed-list")
    
    # Build searchable text
    searchable_parts = [title, searchable_extra] if title else [searchable_extra]
    
    # Add properties
    for prop in properties:
        if len(prop) >= 2:
            label = str(prop[0]) if prop[0] else ""
            value = str(prop[1]) if prop[1] else ""
            prop_icon = prop[2] if len(prop) > 2 else None
            
            # Skip empty values
            if not value or value in ("N/A", "Unknown", ""):
                continue
            
            searchable_parts.extend([label, value])
            
            # Create AdwActionRow for each property
            row = Adw.ActionRow()
            row.set_title(label)
            row.set_subtitle(value)
            row.set_subtitle_selectable(True)
            
            if prop_icon:
                icon_widget = Gtk.Image.new_from_icon_name(prop_icon)
                icon_widget.add_css_class("accent")
                row.add_prefix(icon_widget)
            
            listbox.append(row)
    
    outer_box.append(listbox)
    outer_box.searchable_text = " ".join(filter(None, searchable_parts))
    
    return outer_box
