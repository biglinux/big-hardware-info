"""
UI Widget components for Hardware Reporter.

Provides reusable GTK4 widgets for displaying hardware information
in a visually appealing way.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango, Gdk
import math

from app.utils.i18n import _


class InfoCard(Gtk.Box):
    """
    A card widget for displaying labeled information.
    
    Features a title and a grid of label-value pairs.
    """
    
    def __init__(self, title: str, icon_name: str = None):
        """
        Initialize the card.
        
        Args:
            title: Card title.
            icon_name: Optional icon name for the header.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add_css_class("card")
        self.set_margin_bottom(12)
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.add_css_class("accent")
            header.append(icon)
        
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("title-4")
        title_label.set_halign(Gtk.Align.START)
        header.append(title_label)
        
        self.append(header)
        
        # Separator
        separator = Gtk.Separator()
        separator.set_margin_top(4)
        separator.set_margin_bottom(4)
        self.append(separator)
        
        # Content grid
        self.grid = Gtk.Grid()
        self.grid.set_row_spacing(8)
        self.grid.set_column_spacing(16)
        self.append(self.grid)
        
        self._row = 0
    
    def add_row(self, label: str, value: str, monospace: bool = False):
        """
        Add a label-value row.
        
        Args:
            label: Row label.
            value: Row value.
            monospace: Whether to use monospace font for value.
        """
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("dim-label")
        label_widget.set_halign(Gtk.Align.START)
        label_widget.set_valign(Gtk.Align.START)
        
        value_widget = Gtk.Label(label=value)
        value_widget.set_halign(Gtk.Align.END)
        value_widget.set_hexpand(True)
        value_widget.set_wrap(True)
        value_widget.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        value_widget.set_selectable(True)
        
        if monospace:
            value_widget.add_css_class("monospace")
        
        self.grid.attach(label_widget, 0, self._row, 1, 1)
        self.grid.attach(value_widget, 1, self._row, 1, 1)
        self._row += 1
    
    def add_section(self, title: str):
        """
        Add a section header.
        
        Args:
            title: Section title.
        """
        if self._row > 0:
            spacer = Gtk.Box()
            spacer.set_size_request(-1, 8)
            self.grid.attach(spacer, 0, self._row, 2, 1)
            self._row += 1
        
        label = Gtk.Label(label=title)
        label.add_css_class("heading")
        label.set_halign(Gtk.Align.START)
        self.grid.attach(label, 0, self._row, 2, 1)
        self._row += 1


class ProgressCard(Gtk.Box):
    """
    A card with a progress bar for displaying usage/capacity info.
    """
    
    def __init__(self, title: str, value: float, label: str, 
                 icon_name: str = None, color_class: str = None):
        """
        Initialize the progress card.
        
        Args:
            title: Card title.
            value: Progress value (0.0 to 1.0).
            label: Text to show alongside progress.
            icon_name: Optional icon name.
            color_class: Optional CSS class for coloring.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("card")
        self.set_margin_bottom(12)
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            header.append(icon)
        
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("title-4")
        title_label.set_halign(Gtk.Align.START)
        header.append(title_label)
        
        self.append(header)
        
        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.progress.set_fraction(min(1.0, max(0.0, value)))
        self.progress.set_show_text(False)
        
        if color_class:
            self.progress.add_css_class(color_class)
        elif value > 0.9:
            self.progress.add_css_class("error")
        elif value > 0.75:
            self.progress.add_css_class("warning")
        else:
            self.progress.add_css_class("success")
        
        self.append(self.progress)
        
        # Label
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("caption")
        label_widget.set_halign(Gtk.Align.END)
        self.append(label_widget)


class DeviceRow(Adw.ActionRow):
    """
    A row for displaying device information with actions.
    """
    
    def __init__(self, name: str, subtitle: str = None, 
                 icon_name: str = None, url: str = None):
        """
        Initialize the device row.
        
        Args:
            name: Device name.
            subtitle: Optional subtitle (e.g., device ID).
            icon_name: Optional icon name.
            url: Optional URL for more info.
        """
        super().__init__()
        
        self.set_title(name)
        if subtitle:
            self.set_subtitle(subtitle)
        
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            self.add_prefix(icon)
        
        if url:
            self._url = url
            link_btn = Gtk.Button(icon_name="web-browser-symbolic")
            link_btn.add_css_class("flat")
            link_btn.set_tooltip_text("Open device info online")
            link_btn.set_valign(Gtk.Align.CENTER)
            link_btn.connect("clicked", self._on_link_clicked)
            self.add_suffix(link_btn)
    
    def _on_link_clicked(self, button):
        """Open URL in browser."""
        import subprocess
        subprocess.Popen(["xdg-open", self._url], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)


class StatBox(Gtk.Box):
    """
    A compact stat display widget showing a value with label.
    """
    
    def __init__(self, value: str, label: str, icon_name: str = None):
        """
        Initialize the stat box.
        
        Args:
            value: The main value to display.
            label: Label describing the value.
            icon_name: Optional icon.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.add_css_class("card")
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(24)
            icon.add_css_class("accent")
            self.append(icon)
        
        value_label = Gtk.Label(label=value)
        value_label.add_css_class("title-1")
        self.append(value_label)
        
        desc_label = Gtk.Label(label=label)
        desc_label.add_css_class("dim-label")
        desc_label.add_css_class("caption")
        self.append(desc_label)


class PreformattedText(Gtk.Box):
    """
    A collapsible widget for displaying preformatted text.
    """
    
    def __init__(self, title: str, text: str, expanded: bool = False):
        """
        Initialize the preformatted text widget.
        
        Args:
            title: Section title.
            text: Text content.
            expanded: Whether to start expanded.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("card")
        self.set_margin_bottom(12)
        
        # Create expander
        self.expander = Gtk.Expander(label=title)
        self.expander.set_expanded(expanded)
        
        # Create text view
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(300)
        scroll.set_propagate_natural_height(True)
        
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.add_css_class("view")
        text_view.get_buffer().set_text(text)
        
        scroll.set_child(text_view)
        self.expander.set_child(scroll)
        
        self.append(self.expander)


class CoreGrid(Gtk.FlowBox):
    """
    A grid for displaying CPU core speeds.
    """
    
    def __init__(self, cores: dict):
        """
        Initialize the core grid.
        
        Args:
            cores: Dictionary of core number -> speed.
        """
        super().__init__()
        self.set_selection_mode(Gtk.SelectionMode.NONE)
        self.set_homogeneous(True)
        self.set_max_children_per_line(8)
        self.set_min_children_per_line(4)
        self.set_row_spacing(8)
        self.set_column_spacing(8)
        
        for core_num, speed in sorted(cores.items()):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.add_css_class("card")
            box.set_size_request(80, -1)
            
            # Core number
            label = Gtk.Label(label=f"Core {core_num}")
            label.add_css_class("caption")
            label.add_css_class("dim-label")
            box.append(label)
            
            # Speed
            speed_label = Gtk.Label(label=f"{speed} MHz")
            speed_label.add_css_class("heading")
            box.append(speed_label)
            
            self.insert(box, -1)


class DonutChart(Gtk.Box):
    """
    A simple donut/pie chart widget that shows a fraction as a circular arc.

    This widget uses a DrawingArea to render a donut chart and an overlayed
    centered label with a percent value.
    """

    def __init__(self, fraction: float = 0.0, size: int = 120, thickness: int = 14,
                 primary_color: str = "#4ade80", background_color: str = "#ededed"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("card")
        self.set_margin_bottom(6)

        self._fraction = max(0.0, min(1.0, float(fraction or 0.0)))
        self._size = size
        self._thickness = thickness
        self._primary_color = primary_color
        self._background_color = background_color

        # Use an overlay to place a label centered over the drawing area
        overlay = Gtk.Overlay()
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.set_valign(Gtk.Align.CENTER)
        overlay.set_margin_start(8)
        overlay.set_margin_end(8)

        self._drawing = Gtk.DrawingArea()
        self._drawing.set_content_width(self._size)
        self._drawing.set_content_height(self._size)
        self._drawing.set_hexpand(False)
        self._drawing.set_vexpand(False)
        self._drawing.set_draw_func(self._draw)
        overlay.set_child(self._drawing)

        self._label = Gtk.Label(label=self._format_pct(self._fraction))
        self._label.add_css_class("title-3")
        self._label.set_halign(Gtk.Align.CENTER)
        self._label.set_valign(Gtk.Align.CENTER)
        overlay.add_overlay(self._label)

        self.append(overlay)

    def _format_pct(self, fraction: float) -> str:
        return f"{fraction * 100:.1f}%"

    def set_fraction(self, fraction: float):
        self._fraction = max(0.0, min(1.0, float(fraction or 0.0)))
        self._label.set_text(self._format_pct(self._fraction))
        self._drawing.queue_draw()

    def _draw(self, widget, cr, width, height, _user_data=None):
        # Draw a donut chart using cairo
        ctx = cr
        # Center & radius
        cx = width / 2.0
        cy = height / 2.0
        radius = min(width, height) / 2.0 - self._thickness / 2.0 - 2
        # Draw background ring
        ctx.set_source_rgba(*self._parse_hex(self._background_color))
        ctx.set_line_width(self._thickness)
        ctx.arc(cx, cy, radius, 0, 2 * math.pi)
        ctx.stroke()

        # Draw used arc
        start_angle = -math.pi / 2.0
        end_angle = start_angle + (2 * math.pi * self._fraction)
        ctx.set_source_rgba(*self._parse_hex(self._primary_color))
        ctx.set_line_width(self._thickness)
        ctx.arc(cx, cy, radius, start_angle, end_angle)
        ctx.stroke()

    def _parse_hex(self, hexstr: str):
        # Convert hex color like #rrggbb to r,g,b,a tuple
        try:
            if hexstr.startswith("#"):
                hexstr = hexstr[1:]
            r = int(hexstr[0:2], 16) / 255.0
            g = int(hexstr[2:4], 16) / 255.0
            b = int(hexstr[4:6], 16) / 255.0
            return (r, g, b, 1.0)
        except Exception:
            return (0.2, 0.2, 0.2, 1.0)
