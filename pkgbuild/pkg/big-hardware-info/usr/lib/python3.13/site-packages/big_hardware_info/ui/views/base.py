"""
Base view class for Hardware Reporter section views.

Provides abstract base class and common utilities for rendering
hardware information in a consistent, component-based architecture.
"""

import re
from typing import Any, Optional

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango


class HardwareSectionView(Gtk.Box):
    """
    Base class for hardware section views.
    
    Each hardware category (CPU, GPU, Memory, etc.) should have its own
    view class that inherits from this base. The view is responsible for
    rendering its specific hardware data in a consistent UI style.
    
    Design Rationale:
    - Decouples rendering logic from the main window
    - Enables consistent styling through shared utility methods
    - Allows easy addition of new hardware categories
    - Follows GTK4/Adwaita HIG patterns
    """
    
    # Category identifier (e.g., "cpu", "memory", "gpu")
    CATEGORY_ID: str = ""
    
    def __init__(self, **kwargs) -> None:
        """Initialize the section view as a vertical box container."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, **kwargs)
    
    def render(self, data: dict) -> None:
        """
        Render the hardware data into this view.
        
        Subclasses must implement this method to display their specific
        hardware information. The method should clear any existing content
        and rebuild the UI based on the provided data.
        
        Args:
            data: Dictionary containing hardware information for this category.
        """
        raise NotImplementedError("Subclasses must implement render() method")
    
    def clear(self) -> None:
        """Remove all child widgets from the view."""
        child = self.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.remove(child)
            child = next_child
    
    # =========================================================================
    # Common UI Component Factory Methods
    # =========================================================================
    
    def create_section_title(self, title: str) -> Gtk.Label:
        """
        Create a section title label.
        
        Args:
            title: The section title text.
            
        Returns:
            Styled Gtk.Label widget.
        """
        label = Gtk.Label(label=title)
        label.add_css_class("section-title")
        label.set_halign(Gtk.Align.START)
        return label
    
    def create_hero_card(self) -> Gtk.Box:
        """
        Create a hero card container for primary information display.
        
        The hero card is used for the main/most important information
        in a hardware section, with prominent styling.
        
        Returns:
            Styled Gtk.Box container.
        """
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        card.add_css_class("card")
        card.add_css_class("hero-card")
        return card
    
    def create_card(self, elevated: bool = False) -> Gtk.Box:
        """
        Create a standard card container.
        
        Args:
            elevated: If True, applies elevated card styling with shadow.
            
        Returns:
            Styled Gtk.Box container.
        """
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class("card-elevated" if elevated else "card")
        return card
    
    def create_device_card(self) -> Gtk.Box:
        """
        Create a device card for displaying device information.
        
        Returns:
            Styled horizontal Gtk.Box container.
        """
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        card.add_css_class("card")
        card.add_css_class("device-card")
        return card
    
    def create_info_row(self, label: str, value: str) -> Gtk.Box:
        """
        Create an info row with label and value.
        
        Args:
            label: The row label text.
            value: The row value text.
            
        Returns:
            Gtk.Box containing the label-value pair.
        """
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("info-row")
        
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("dim-label")
        label_widget.set_halign(Gtk.Align.START)
        label_widget.set_width_chars(15)
        label_widget.set_xalign(0)
        row.append(label_widget)
        
        value_widget = Gtk.Label(label=value)
        value_widget.set_halign(Gtk.Align.END)
        value_widget.set_hexpand(True)
        value_widget.set_wrap(True)
        value_widget.set_xalign(1)
        value_widget.set_selectable(True)
        row.append(value_widget)
        
        return row
    
    def create_info_grid(
        self, 
        items: list[tuple[str, Any]], 
        columns: int = 2,
        row_spacing: int = 6,
        column_spacing: int = 48
    ) -> Gtk.Grid:
        """
        Create an info grid with label-value pairs in multiple columns.
        
        Args:
            items: List of (label, value) tuples to display.
            columns: Number of columns for the grid layout.
            row_spacing: Vertical spacing between rows.
            column_spacing: Horizontal spacing between columns.
            
        Returns:
            Gtk.Grid containing the info items.
        """
        grid = Gtk.Grid()
        grid.set_row_spacing(row_spacing)
        grid.set_column_spacing(column_spacing)
        
        row = 0
        col = 0
        
        for label, value in items:
            # Skip empty values
            if not value or value in ("N/A", "Unknown", "?", ""):
                continue
            
            # Label
            label_widget = Gtk.Label(label=label)
            label_widget.add_css_class("info-label")
            label_widget.set_halign(Gtk.Align.START)
            label_widget.set_width_chars(14)
            label_widget.set_xalign(0)
            grid.attach(label_widget, col * 2, row, 1, 1)
            
            # Value
            value_widget = Gtk.Label(label=str(value))
            value_widget.add_css_class("info-value")
            value_widget.set_halign(Gtk.Align.START)
            value_widget.set_selectable(True)
            value_widget.set_wrap(True)
            value_widget.set_xalign(0)
            value_widget.set_margin_end(16)
            grid.attach(value_widget, col * 2 + 1, row, 1, 1)
            
            col += 1
            if col >= columns:
                col = 0
                row += 1
        
        return grid
    
    def create_stat_card(
        self, 
        icon_name: str, 
        value: str, 
        label: str
    ) -> Gtk.Box:
        """
        Create a stat card for displaying key metrics.
        
        Args:
            icon_name: Icon name for the stat.
            value: The main value to display.
            label: Label describing the stat.
            
        Returns:
            Styled Gtk.Box stat card.
        """
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card")
        card.add_css_class("stat-card")
        
        # Icon
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(24)
        icon.add_css_class("accent")
        card.append(icon)
        
        # Value
        value_label = Gtk.Label(label=value)
        value_label.add_css_class("stat-value")
        value_label.set_wrap(True)
        value_label.set_max_width_chars(20)
        value_label.set_ellipsize(Pango.EllipsizeMode.END)
        card.append(value_label)
        
        # Label
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("stat-label")
        card.append(label_widget)
        
        return card
    
    def create_progress_bar(
        self, 
        fraction: float, 
        show_label: bool = True
    ) -> Gtk.Box:
        """
        Create a styled progress bar with optional label.
        
        Args:
            fraction: Progress value from 0.0 to 1.0.
            show_label: If True, shows percentage label.
            
        Returns:
            Gtk.Box containing the progress bar and optional label.
        """
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        bar = Gtk.ProgressBar()
        bar.set_fraction(min(1.0, max(0.0, fraction)))
        bar.add_css_class("usage-bar")
        
        # Color based on value
        percent = fraction * 100
        if percent > 90:
            bar.add_css_class("error")
        elif percent > 70:
            bar.add_css_class("warning")
        else:
            bar.add_css_class("success")
        
        container.append(bar)
        
        if show_label:
            label = Gtk.Label(label=f"{percent:.1f}%")
            label.add_css_class("info-label")
            label.set_halign(Gtk.Align.END)
            container.append(label)
        
        return container
    
    def create_badge(
        self, 
        text: str, 
        style: Optional[str] = None
    ) -> Gtk.Label:
        """
        Create a badge/pill widget.
        
        Args:
            text: Badge text.
            style: Optional style variant: "success", "warning", "error".
            
        Returns:
            Styled Gtk.Label badge.
        """
        badge = Gtk.Label(label=text)
        badge.add_css_class("device-badge")
        
        if style:
            badge.add_css_class(f"{style}-badge")
        
        return badge
    
    def create_flow_box(
        self, 
        homogeneous: bool = True,
        max_per_line: int = 4,
        min_per_line: int = 2,
        row_spacing: int = 12,
        column_spacing: int = 12
    ) -> Gtk.FlowBox:
        """
        Create a flow box for responsive grid layouts.
        
        Args:
            homogeneous: Whether all children should have same size.
            max_per_line: Maximum children per row.
            min_per_line: Minimum children per row.
            row_spacing: Vertical spacing.
            column_spacing: Horizontal spacing.
            
        Returns:
            Configured Gtk.FlowBox.
        """
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(homogeneous)
        flow.set_max_children_per_line(max_per_line)
        flow.set_min_children_per_line(min_per_line)
        flow.set_row_spacing(row_spacing)
        flow.set_column_spacing(column_spacing)
        return flow
    
    def create_raw_expander(
        self, 
        title: str, 
        text: str, 
        expanded: bool = False
    ) -> Gtk.Expander:
        """
        Create an expandable section for raw text output.
        
        Args:
            title: Expander title.
            text: Raw text content.
            expanded: Whether to start expanded.
            
        Returns:
            Gtk.Expander containing scrollable text view.
        """
        expander = Gtk.Expander(label=title)
        expander.set_expanded(expanded)
        expander.add_css_class("card")
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(300)
        scroll.set_propagate_natural_height(True)
        
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_margin_top(8)
        text_view.get_buffer().set_text(text)
        
        scroll.set_child(text_view)
        expander.set_child(scroll)
        
        return expander
    
    def show_no_data(self, message: str = "No data available") -> None:
        """
        Display a "no data" message in the view.
        
        Args:
            message: The message to display.
        """
        label = Gtk.Label(label=message)
        label.add_css_class("dim-label")
        label.set_margin_top(32)
        label.set_margin_bottom(32)
        self.append(label)
    
    def make_searchable(self, widget: Gtk.Widget, text: str) -> Gtk.Widget:
        """
        Mark a widget as searchable with the given text.
        
        Args:
            widget: Widget to mark.
            text: Searchable text content.
            
        Returns:
            The same widget with searchable_text attribute set.
        """
        widget.searchable_text = text
        return widget
    
    def clean_percentage_string(self, value: str) -> str:
        """
        Remove percentage suffix from a string.
        
        Example: "4.51 GiB (28.9%)" -> "4.51 GiB"
        
        Args:
            value: String potentially containing percentage.
            
        Returns:
            String with percentage removed.
        """
        if isinstance(value, str) and "(" in value:
            return re.sub(r'\s*\([0-9.]+%\)', '', value).strip()
        return value
    
    def create_hero_card_with_columns(
        self,
        title: str,
        left_items: list[tuple[str, Any]],
        right_items: list[tuple[str, Any]]
    ) -> Gtk.Box:
        """
        Create a hero card with title and two-column layout.
        
        This is the standard layout used for hardware device cards,
        following the design pattern from Processor and Graphics views.
        
        Args:
            title: The main title (e.g., device name).
            left_items: List of (label, value) tuples for left column.
            right_items: List of (label, value) tuples for right column.
            
        Returns:
            Styled Gtk.Box hero card with two columns.
        """
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("card")
        card.add_css_class("hero-card")
        
        # Title
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("hero-title")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_wrap(True)
        title_label.set_xalign(0)
        card.append(title_label)
        
        # Filter out empty values
        left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "Unknown", "?", "")]
        right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "Unknown", "?", "")]
        
        # Two-column layout with separator
        columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        # Left column
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_col.set_hexpand(True)
        for label, value in left_items:
            item = self._create_spec_item(label, value)
            left_col.append(item)
        columns_box.append(left_col)
        
        # Visual separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        separator.set_margin_start(24)
        separator.set_margin_end(24)
        columns_box.append(separator)
        
        # Right column
        right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right_col.set_hexpand(True)
        for label, value in right_items:
            item = self._create_spec_item(label, value)
            right_col.append(item)
        columns_box.append(right_col)
        
        card.append(columns_box)
        
        return card
    
    def _create_spec_item(self, label: str, value: str) -> Gtk.Box:
        """
        Create a modern spec item with label above value.
        
        Args:
            label: Small label text above the value.
            value: Bold value text.
            
        Returns:
            Gtk.Box with label/value vertical layout.
        """
        item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        # Small dim label on top
        label_w = Gtk.Label(label=label)
        label_w.add_css_class("dim-label")
        label_w.add_css_class("caption")
        label_w.set_halign(Gtk.Align.START)
        item.append(label_w)
        
        # Bold value below
        value_w = Gtk.Label(label=str(value))
        value_w.add_css_class("heading")
        value_w.set_halign(Gtk.Align.START)
        value_w.set_selectable(True)
        item.append(value_w)
        
        return item
