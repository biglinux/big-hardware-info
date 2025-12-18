"""
HTML Generator for Hardware Reporter.
Generates a self-contained HTML report mirroring the GTK UI.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from big_hardware_info.models.hardware_info import HardwareInfo, CATEGORIES
from big_hardware_info.utils.i18n import _

logger = logging.getLogger(__name__)

# PCI device classification keywords for separating important devices from infrastructure
PCI_INFRASTRUCTURE_KEYWORDS = [
    "bridge", "bus", "usb controller", "hub", "host bridge",
    "isa bridge", "pci bridge", "pcie", "smbus", "communication controller",
    "signal processing", "serial bus", "system peripheral", "pic", "dma",
    "rtc", "timer", "watchdog", "sd host", "sd/mmc",
    "sata controller", "ahci", "sata ahci"
]

class HtmlGenerator:
    """Generates HTML reports from HardwareInfo data."""
    
    def __init__(self, hardware_info: HardwareInfo):
        """Initialize with hardware data."""
        self.data = hardware_info
        self.raw_data = hardware_info.to_dict()
        
    # Order of sections in the report and sidebar
    SECTION_ORDER = [
        "summary", "cpu", "gpu", "memory", "disk", "system", 
        "machine", "audio", "network", "battery", "bluetooth", 
        "usb", "pci", "webcam", "printer", "sensors", "more_info"
    ]
        
    def generate(self) -> str:
        """
        Generate the complete HTML report.
        
        Returns:
            String containing the full HTML document.
        """
        css = self._get_css()
        js = self._get_js()
        sidebar = self._render_sidebar()
        content = self._render_content()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        title = _("Hardware Report") + f" - {self.data.hostname}"
        
        # Translatable strings for HTML
        search_placeholder = _("Search sections...")
        generated_text = _("Generated:")
        visit_website = _("Visit BigLinux website")
        
        # Determine HTML lang attribute from current locale
        import locale as _locale
        lang_code = _locale.getlocale()[0] or _locale.getdefaultlocale()[0] or "en"
        lang_code = lang_code.split("_")[0] if lang_code else "en"

        return f"""<!DOCTYPE html>
<html lang="{lang_code}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{_("Hardware Report for")} {self.data.hostname}">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        {css}
    </style>
</head>
<body>
    <div class="app-window">
        <!-- Sidebar -->
        <aside class="sidebar" aria-label="{_("Main Navigation")}">
            <div class="sidebar-header">
                <a href="https://www.biglinux.com.br" target="_blank" rel="noopener noreferrer" class="sidebar-title-link" title="{visit_website}">
                    <div class="app-icon" aria-hidden="true">🖥️</div>
                    <div class="app-title">Big Hardware Info</div>
                </a>
            </div>
            
            <nav class="sidebar-content">
                {sidebar}
            </nav>
        </aside>
        
        <!-- Main Content -->
        <main class="main-content">
            <header class="content-header">
                <div class="header-spacer"></div>
                <div class="header-search">
                    <span class="search-icon" aria-hidden="true">🔍</span>
                    <input type="text" id="searchInput" placeholder="{search_placeholder}" aria-label="{search_placeholder}" oninput="filterContent()">
                </div>
                <div class="header-actions">
                    <span class="timestamp">{generated_text} {timestamp}</span>
                </div>
            </header>
            
            <div class="content-scroll" id="contentScroll">
                <div class="content-container">
                    {content}
                </div>
            </div>
        </main>
    </div>
    
    <script>
        {js}
    </script>
</body>
</html>"""

    def _get_css(self) -> str:
        """Get Modern CSS content."""
        return """
        :root {
            /* Modern Dark Palette - harmonized */
            --bg-body: #0d1117;
            --bg-sidebar: #161b22;
            --bg-header: rgba(22, 27, 34, 0.85);
            --bg-card: #21262d;
            --bg-card-hover: #30363d;
            
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            
            --accent-primary: #58a6ff;
            --accent-secondary: #3fb950;
            --accent-hightlight: #79c0ff;
            --accent-bg-color: #58a6ff;
            
            --border-color: rgba(240, 246, 252, 0.1);
            --border-radius: 12px;
            --border-radius-sm: 6px;
            
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.4), 0 2px 4px -1px rgba(0,0,0,0.2);
            
            --success: #3fb950;
            --success-color: #3fb950;
            --warning: #d29922;
            --warning-color: #d29922;
            --error: #f85149;
            --error-color: #e01b24;
            
            /* Syntax Highlighting - matching Adwaita GTK colors */
            --hl-path: #3584e4;      /* Blue - paths */
            --hl-number: #26a269;    /* Green - IDs, addresses, numbers */
            --hl-keyword: #ff7800;   /* Orange - keywords */
            --hl-comment: #8d93a8;   /* Gray - comments, URLs */
            --hl-success: #33d17a;   /* Bright green - success states */
            --hl-warning: #e5a50a;   /* Yellow - warnings */
            --hl-error: #e01b24;     /* Red - errors */
            --hl-osname: #62a0ea;    /* Light blue - OS/partition names */
        }

        /* Reset & Base */
        * { box-sizing: border-box; }
        
        body {
            font-family: 'Outfit', 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-body);
            color: var(--text-primary);
            margin: 0;
            padding: 0;
            height: 100vh;
            overflow: hidden;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }
        
        /* Layout */
        .app-window {
            display: flex;
            height: 100vh;
            width: 100vw;
        }
        
        /* Sidebar */
        .sidebar {
            width: 280px;
            background: linear-gradient(180deg, var(--bg-sidebar) 0%, #0d1117 100%);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            z-index: 10;
        }
        
        .sidebar-header {
            height: 72px;
            display: flex;
            align-items: center;
            padding: 0 24px;
            border-bottom: 1px solid var(--border-color);
            background: rgba(88, 166, 255, 0.03);
        }
        
        .sidebar-title-link {
            display: flex;
            align-items: center;
            text-decoration: none;
            transition: opacity 0.2s;
        }
        .sidebar-title-link:hover { opacity: 0.85; }
        .app-icon { font-size: 1.6rem; margin-right: 14px; filter: drop-shadow(0 2px 4px rgba(88,166,255,0.3)); }
        .app-title { font-weight: 700; font-size: 1.2rem; letter-spacing: -0.02em; color: var(--text-primary); }
        
        .sidebar-content {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }
        
        .nav-item {
            display: flex;
            align-items: center;
            padding: 10px 14px;
            margin-bottom: 4px;
            border-radius: var(--border-radius-sm);
            cursor: pointer;
            transition: all 0.2s ease;
            color: var(--text-secondary);
            font-weight: 500;
            text-decoration: none;
            border: 1px solid transparent;
        }
        
        .nav-item:hover, .nav-item:focus {
            background-color: rgba(88, 166, 255, 0.08);
            color: var(--text-primary);
            transform: translateX(3px);
        }
        
        .nav-item:active { transform: translateX(0); }
        
        .nav-item.active {
            background: linear-gradient(135deg, rgba(88, 166, 255, 0.15) 0%, rgba(63, 185, 80, 0.08) 100%);
            color: var(--accent-primary);
            border-color: rgba(88, 166, 255, 0.25);
            box-shadow: 0 0 12px rgba(88, 166, 255, 0.1);
        }
        
        .nav-icon { margin-right: 12px; min-width: 20px; text-align: center; opacity: 0.8; }
        
        /* Main Content */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            background-color: var(--bg-body);
            min-width: 0;
            position: relative;
        }
        
        .content-header {
            height: 72px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 32px;
            border-bottom: 1px solid var(--border-color);
            background: linear-gradient(90deg, var(--bg-header) 0%, rgba(22, 27, 34, 0.95) 100%);
            backdrop-filter: blur(16px);
            position: sticky;
            top: 0;
            z-index: 5;
        }
        
        .header-search {
            position: relative;
            background: rgba(240, 246, 252, 0.04);
            border-radius: var(--border-radius-sm);
            border: 1px solid var(--border-color);
            padding: 8px 16px;
            width: 320px;
            display: flex;
            align-items: center;
            transition: all 0.25s ease;
        }
        
        .header-search:focus-within {
            border-color: var(--accent-primary);
            background: rgba(240, 246, 252, 0.08);
            box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15);
        }
        
        .header-search input {
            background: transparent;
            border: none;
            color: var(--text-primary);
            margin-left: 10px;
            width: 100%;
            outline: none;
            font-family: inherit;
        }
        
        .search-icon { opacity: 0.6; font-size: 0.9em; }
        .header-spacer { flex: 1; }
        .header-actions { flex: 1; display: flex; justify-content: flex-end; }
        .timestamp { color: var(--text-secondary); font-size: 0.85rem; }
        
        /* content area */
        .content-scroll {
            flex: 1;
            overflow-y: auto;
            padding: 32px;
            scroll-behavior: smooth;
        }
        
        .content-container {
            max-width: 1100px;
            margin: 0 auto;
            padding-bottom: 60px;
        }
        
        /* Components */
        
        /* Section Header */
        h2.title-3 {
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0 0 0 0;
            color: var(--text-primary);
            letter-spacing: -0.01em;
            display: flex;
            align-items: center;
        }
        
        .section-anchor {
            scroll-margin-top: 90px;
            margin-bottom: 40px;
            animation: fadeIn 0.5s ease-out;
            transition: opacity 0.3s, transform 0.3s;
        }
        
        .section-anchor.search-match {
            border-left: 3px solid var(--accent-primary);
            padding-left: 16px;
            margin-left: -19px;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Cards */
        .card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 20px;
            margin-bottom: 16px;
            transition: transform 0.2s, box-shadow 0.2s, background-color 0.2s;
            box-shadow: var(--shadow-sm);
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
            background-color: var(--bg-card-hover);
        }
        
        /* Hero Card Special */
        .card.hero-card {
            background: linear-gradient(145deg, var(--bg-card) 0%, rgba(35, 35, 45, 0.8) 100%);
            border-left: 4px solid var(--accent-primary);
        }
        
        .hero-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--accent-hightlight);
        }
        
        .title-4 {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 12px;
            color: var(--accent-hightlight);
        }
        
        .device-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--accent-hightlight);
        }
        
        /* Typography Utils */
        .heading { font-weight: 600; color: var(--text-primary); }
        .dim-label { color: var(--text-secondary); font-size: 0.9rem; }
        .caption { 
            font-size: 0.75rem; 
            text-transform: uppercase; 
            letter-spacing: 0.05em; 
            font-weight: 600; 
            color: var(--text-muted);
        }
        
        /* Layout Utils */
        .box-horizontal { display: flex; flex-direction: row; gap: 8px; }
        .box-vertical { display: flex; flex-direction: column; }
        
        .separator {
            width: 1px;
            background-color: var(--border-color);
            margin: 0 24px;
        }
        
        .separator-horizontal {
            height: 1px;
            width: 100%;
            background-color: var(--border-color);
            margin: 16px 0;
        }
        
        /* Badges */
        .device-badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 99px;
            font-size: 0.75rem;
            font-weight: 600;
            background-color: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            letter-spacing: 0.02em;
        }
        
        .success-badge { background-color: rgba(44, 182, 125, 0.15); color: var(--success); }
        .warning-badge { background-color: rgba(255, 189, 3, 0.15); color: var(--warning); }
        .accent-badge { background-color: rgba(127, 90, 240, 0.15); color: var(--accent-primary); }
        
        .success-color { color: var(--success); }
        .warning-color { color: var(--warning); }
        .error-color { color: var(--error); }
        
        /* Info Links */
        .info-btn {
            color: var(--accent-hightlight);
            text-decoration: none;
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            transition: background 0.2s;
            font-size: 0.85rem;
        }
        .info-btn:hover { background-color: rgba(61, 169, 252, 0.1); }

        /* Usage Bars */
        .usage-bar { margin-top: 8px; }
        
        /* Details/Summary */
        details {
            margin-bottom: 8px;
            border-radius: var(--border-radius);
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            transition: all 0.2s;
        }
        details[open] { background-color: var(--bg-card-hover); }
        
        summary {
            padding: 12px 20px;
            cursor: pointer;
            font-weight: 600;
            display: flex;
            align-items: center;
            list-style: none;
            outline: none;
            border-radius: var(--border-radius);
            transition: background 0.2s;
        }
        summary:hover { background-color: rgba(255, 255, 255, 0.05); }
        summary::-webkit-details-marker { display: none; }
        
        summary::before {
            content: "▶";
            display: inline-block;
            margin-right: 12px;
            color: var(--accent-primary);
            transition: transform 0.2s;
            font-size: 0.8em;
        }
        details[open] > summary::before { transform: rotate(90deg); }
        
        details > div {
            padding: 0 20px 20px 20px;
            margin-top: 4px;
            border-top: 1px solid var(--border-color);
            padding-top: 16px;
        }
        
        details.flat-expander { border: none; background: transparent; padding: 0; }
        details.flat-expander > summary { padding-left: 0; padding-right: 0; }
        details.flat-expander > div { padding: 8px 0 0 0; border: none; }
        
        /* Terminal / Pre code */
        .terminal-card { font-family: 'JetBrains Mono', 'Fira Code', monospace; }
        .terminal-text { 
            font-size: 0.85rem; 
            color: var(--text-secondary); 
            line-height: 1.6;
        }
        
        /* Syntax Highlighting Classes */
        .hl-path { color: var(--hl-path); }  /* Paths like /dev/xxx */
        .hl-number { color: var(--hl-number); }  /* IDs, addresses, numbers */
        .hl-keyword { color: var(--hl-keyword); font-weight: 600; }  /* Keywords */
        .hl-comment { color: var(--hl-comment); font-style: italic; }  /* Comments, URLs */
        .hl-success { color: var(--hl-success); }  /* Success states */
        .hl-warning { color: var(--hl-warning); }  /* Warnings */
        .hl-error { color: var(--hl-error); font-weight: 600; }  /* Errors */
        .hl-osname { color: var(--hl-osname); font-weight: 700; }  /* OS/partition names */

        /* Responsive */
        @media (max-width: 800px) {
            html, body { 
                height: auto; 
                min-height: 100vh;
                overflow-x: hidden;
                overflow-y: auto;
                -webkit-overflow-scrolling: touch;
            }
            .app-window { 
                flex-direction: column; 
                overflow: visible; 
                height: auto; 
                min-height: 100vh;
            }
            .sidebar { width: 100%; height: auto; border-right: none; border-bottom: 1px solid var(--border-color); }
            .sidebar-content { display: none; /* simple toggle could be exacted but let's just show header on mobile for now */ }
            
            .content-header { 
                padding: 0 16px; 
                height: 60px; 
                position: relative;
                backdrop-filter: none;
            }
            .header-search { width: 100%; max-width: 200px; }
            .content-scroll { 
                padding: 16px; 
                overflow: visible; 
                height: auto;
                flex: none;
            }
            .main-content {
                overflow: visible;
                height: auto;
            }
            
            /* Stack columns on mobile */
            .box-horizontal { flex-direction: column; gap: 16px; }
            .separator { display: none; } 
        }
        """

    def _get_js(self) -> str:
        """Get JavaScript for interactivity."""
        return """
        // ScrollSpy to update Sidebar active state
        document.addEventListener('DOMContentLoaded', () => {
            const scrollContainer = document.getElementById('contentScroll');
            const sections = document.querySelectorAll('.section-anchor');
            const navItems = document.querySelectorAll('.nav-item');
            
            function onScroll() {
                let current = '';
                
                sections.forEach(section => {
                    const sectionTop = section.offsetTop;
                    // Offset for header
                    if (scrollContainer.scrollTop >= sectionTop - 100) {
                        current = section.getAttribute('id');
                    }
                });
                
                navItems.forEach(item => {
                    item.classList.remove('active');
                    if (item.dataset.target === current) {
                        item.classList.add('active');
                        // Ensure sidebar scrolls to active item
                        item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }
                });
            }
            
            scrollContainer.addEventListener('scroll', onScroll);
        });

        // Navigation
        function scrollToSection(id) {
            const element = document.getElementById(id);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth' });
            }
        }
        
        // Search - filters cards within sections and shows only matching items
        function filterContent() {
            const input = document.getElementById('searchInput');
            const filter = input.value.trim().toUpperCase();
            const sections = document.querySelectorAll('.section-anchor');
            const navItems = document.querySelectorAll('.nav-item');
            
            // If empty, show all
            if (filter.length === 0) {
                sections.forEach(section => {
                    section.style.display = "";
                    section.classList.remove('search-match');
                    // Show all cards
                    const cards = section.querySelectorAll('.card');
                    cards.forEach(card => card.style.display = "");
                    // Close any opened details
                    const details = section.querySelectorAll('details');
                    details.forEach(d => d.removeAttribute('data-search-opened'));
                });
                navItems.forEach(nav => nav.style.display = "");
                return;
            }
            
            // Track which sections have matching cards
            const matchingSections = new Set();
            
            sections.forEach(section => {
                let sectionHasMatch = false;
                
                // Check section title
                const title = section.querySelector('h2');
                const titleText = title ? title.textContent.toUpperCase() : '';
                const titleMatch = titleText.indexOf(filter) > -1;
                
                if (titleMatch) {
                    // Title matches - show entire section
                    sectionHasMatch = true;
                    const cards = section.querySelectorAll('.card');
                    cards.forEach(card => card.style.display = "");
                } else {
                    // Check each card individually
                    const cards = section.querySelectorAll('.card');
                    cards.forEach(card => {
                        const cardText = card.textContent.toUpperCase();
                        if (cardText.indexOf(filter) > -1) {
                            card.style.display = "";
                            sectionHasMatch = true;
                            
                            // Expand details inside matching card
                            const cardDetails = card.querySelectorAll('details');
                            cardDetails.forEach(d => {
                                if (d.textContent.toUpperCase().indexOf(filter) > -1) {
                                    d.open = true;
                                    d.setAttribute('data-search-opened', 'true');
                                }
                            });
                        } else {
                            card.style.display = "none";
                        }
                    });
                }
                
                // Also check spec-items and other content outside cards
                if (!sectionHasMatch) {
                    const otherContent = section.querySelectorAll('.spec-item, .info-box, pre');
                    otherContent.forEach(el => {
                        if (el.textContent.toUpperCase().indexOf(filter) > -1) {
                            sectionHasMatch = true;
                        }
                    });
                }
                
                if (sectionHasMatch) {
                    section.style.display = "";
                    section.classList.add('search-match');
                    matchingSections.add(section.id);
                } else {
                    section.style.display = "none";
                    section.classList.remove('search-match');
                }
            });
            
            // Also filter sidebar navigation to match visible sections
            navItems.forEach(nav => {
                const href = nav.getAttribute('href');
                if (href) {
                    const sectionId = href.replace('#', '');
                    const navText = nav.textContent.toUpperCase();
                    if (matchingSections.has(sectionId) || navText.indexOf(filter) > -1) {
                        nav.style.display = "";
                    } else {
                        nav.style.display = "none";
                    }
                }
            });
        }
        
        // Copy to clipboard
        function copyText(text) {
            navigator.clipboard.writeText(text).then(() => {
                // Show toast or something?
                console.log('Copied to clipboard');
            });
        }
        """

    def _render_sidebar(self) -> str:
        """Render sidebar navigation items."""
        html = []
        
        # Helper to render a single item
        def render_item(cid, cinfo):
            icon_map = {
                "view-grid-symbolic": "📊",
                "cpu-symbolic": "🧠",
                "video-display-symbolic": "🖥️",
                "camera-web-symbolic": "📷",
                "computer-symbolic": "💻",
                "memory-symbolic": "💾",
                "audio-card-symbolic": "🔊",
                "network-wired-symbolic": "🌐",
                "drive-harddisk-symbolic": "💿",
                "battery-symbolic": "🔋",
                "bluetooth-symbolic": "🦷",
                "media-removable-symbolic": "🔌",
                "drive-multidisk-symbolic": "🗄️",
                "system-run-symbolic": "⚙️",
                "printer-symbolic": "🖨️",
                "temperature-symbolic": "🌡️",
                "dialog-information-symbolic": "ℹ️"
            }
            icon = icon_map.get(cinfo["icon"], "▪️")
            # Translate the category name for the sidebar so exported HTML is localized
            name = _(cinfo.get("name", cid.title()))
            return f"""
            <a class="nav-item" href="#{cid}" onclick="scrollToSection('{cid}'); return false;" data-target="{cid}" role="menuitem" aria-label="{_('Go to')} {name}">
                <span class="nav-icon" aria-hidden="true">{icon}</span>
                <span class="nav-label">{name}</span>
            </a>
            """

        # Render strictly ordered items first
        for cat_id in self.SECTION_ORDER:
            if cat_id in CATEGORIES:
                html.append(render_item(cat_id, CATEGORIES[cat_id]))
                
        # Render any remaining categories
        for cat_id, cat_info in CATEGORIES.items():
            if cat_id not in self.SECTION_ORDER:
                html.append(render_item(cat_id, cat_info))
                
        return "\n".join(html)

    def _create_expander(self, title: str, content: str, expanded: bool = False, flat: bool = False) -> str:
        """Create a collapsible details/summary element."""
        cls = "flat-expander" if flat else ""
        open_attr = "open" if expanded else ""
        return f"""
        <details class="{cls}" {open_attr}>
            <summary>{title}</summary>
            <div>{content}</div>
        </details>
        """

    def _render_content(self) -> str:
        """Render all content sections."""
        html = []
        
        # Define render order same as main_window
        # Map method names to keys
        method_map = {
            "summary": self._render_summary,
            "cpu": self._render_cpu,
            "gpu": self._render_gpu,
            "memory": self._render_memory,
            "disk": self._render_disk,
            "system": self._render_system,
            "machine": self._render_machine,
            "audio": self._render_audio,
            "network": self._render_network,
            "battery": self._render_battery,
            "bluetooth": self._render_bluetooth,
            "usb": self._render_usb,
            "pci": self._render_pci,
            "webcam": self._render_webcam,
            "printer": self._render_printer,
            "sensors": self._render_sensors,
            "more_info": self._render_more_info
        }

        render_methods = []
        for cat_id in self.SECTION_ORDER:
            if cat_id in method_map:
                render_methods.append((cat_id, method_map[cat_id]))
        
        # Add all other categories generically if not explicitly handled yet
        # (For iterative development)
        for cat_id in CATEGORIES:
            if not any(x[0] == cat_id for x in render_methods):
                render_methods.append((cat_id, self._render_generic))
        
        for cat_id, method in render_methods:
            header = self._render_section_header(cat_id)
            content = method(self.data.to_dict().get(cat_id, {}))
            html.append(f"""
            <section id="{cat_id}" class="section-anchor" aria-labelledby="{cat_id}-header">
                {header}
                {content}
            </section>
            """)
            
        return "\n".join(html)

    def _render_section_header(self, cat_id: str) -> str:
        """Render section header."""
        info = CATEGORIES.get(cat_id, {})
        name = _(info.get("name", cat_id.title()))
        # Icon handling logic (using emoji proxy for now)
        return f"""
        <div class="box-horizontal" style="margin-bottom: 6px; margin-top: 24px; align-items: center;">
            <h2 id="{cat_id}-header" class="title-3">{name}</h2>
        </div>
        """

    def _render_summary(self, data: Dict[str, Any]) -> str:
        """Render summary section matching GTK layout."""
        html = []
        
        # Access full data for summary
        full_data = self.data.to_dict()
        memory = full_data.get("memory", {})
        system = full_data.get("system", {})
        kernel = full_data.get("kernel", {})
        gpu = full_data.get("gpu", {})
        disk_usage = full_data.get("disk_usage", {})
        install_date_data = full_data.get("install_date", {})
        
        # Calculate RAM percent safely
        ram_used_str = memory.get("used", "0")
        ram_total_str = memory.get("total", "0")
        ram_percent = memory.get("used_percent", 0)
        
        # Try to parse from string if not available
        if not ram_percent:
            try:
                if "(" in ram_used_str and "%" in ram_used_str:
                    pct = ram_used_str.split("(")[1].split("%")[0]
                    ram_percent = float(pct)
            except:
                pass
        
        # Generate RAM progress bar color
        ram_color_var = "--accent-bg-color"
        if ram_percent > 80: ram_color_var = "--error-color"
        elif ram_percent > 60: ram_color_var = "--warning-color"
        
        # Parse partition usage
        partition = disk_usage.get("device", "") or disk_usage.get("mount_point", "/")
        part_size = disk_usage.get("size", "Unknown")
        part_used = disk_usage.get("used", "Unknown")
        part_free = disk_usage.get("available", "Unknown")
        part_percent_str = disk_usage.get("use_percent", "0%")
        part_percent = 0
        try:
            if part_percent_str:
                part_percent = float(str(part_percent_str).replace("%", "").strip())
        except:
            pass
        
        part_color_var = "--accent-bg-color"
        if part_percent > 90: part_color_var = "--error-color"
        elif part_percent > 70: part_color_var = "--warning-color"
        
        # Get Video info
        gpu_devices = gpu.get("devices", [])
        gpu_name = gpu_devices[0].get("name", "") if gpu_devices else ""
        
        # Get Install Date
        install_date = ""
        if isinstance(install_date_data, dict):
            install_date = install_date_data.get("estimate", "")
        if not install_date:
            install_date = system.get("install_date", "")
        
        # Get Kernel info
        kernel_version = ""
        if isinstance(kernel, dict):
            kernel_version = kernel.get("version", "")
        if not kernel_version:
            kernel_version = system.get("kernel", "")
        
        html.append(f"""
        <div class="box-horizontal" style="margin-bottom: 24px; gap: 16px;">
            <!-- Usage Overview Card (RAM + Partition) -->
            <div class="card" style="flex: 1;">
                <div class="title-4" style="margin-bottom: 12px;">{_("Usage Overview")}</div>
                
                <!-- Memory RAM -->
                <div class="box-vertical" style="margin-bottom: 12px;">
                    <div class="box-horizontal" style="justify-content: space-between;">
                        <div class="dim-label">{_("Memory RAM:")}</div>
                        <div class="heading">{ram_total_str}</div>
                    </div>
                    <div class="box-horizontal" style="font-size: 0.85em; gap: 12px; margin-top: 4px;">
                        <span class="dim-label">{_("Used:")} {ram_used_str.split("(")[0].strip() if "(" in str(ram_used_str) else ram_used_str}</span>
                    </div>
                    <div class="usage-bar" style="background: rgba(255,255,255,0.1); border-radius: 4px; height: 8px; margin-top: 6px;">
                        <div class="progress" style="width: {ram_percent}%; background-color: var({ram_color_var}); height: 100%; border-radius: 4px;"></div>
                    </div>
                    <div class="caption dim-label" style="text-align: right; margin-top: 2px;">{ram_percent:.1f}%</div>
                </div>
                
                <div class="separator-horizontal"></div>
                
                <!-- Root Partition -->
                <div class="box-vertical" style="margin-top: 12px;">
                    <div class="box-horizontal" style="justify-content: space-between;">
                        <div class="dim-label">{_("Root Partition:")}</div>
                        <div class="heading">{partition}</div>
                    </div>
                    <div class="box-horizontal" style="font-size: 0.85em; gap: 12px; margin-top: 4px;">
                        <span class="dim-label">{_("Size:")} {part_size}</span>
                        <span class="dim-label">{_("Used:")} {part_used}</span>
                        <span class="dim-label">{_("Free:")} {part_free}</span>
                    </div>
                    <div class="usage-bar" style="background: rgba(255,255,255,0.1); border-radius: 4px; height: 8px; margin-top: 6px;">
                        <div class="progress" style="width: {part_percent}%; background-color: var({part_color_var}); height: 100%; border-radius: 4px;"></div>
                    </div>
                    <div class="caption dim-label" style="text-align: right; margin-top: 2px;">{part_percent:.1f}%</div>
                </div>
            </div>
            
            <!-- System Info Card -->
            <div class="card" style="flex: 1;">
                <div class="title-4" style="margin-bottom: 12px;">{_("System Info")}</div>
                {self._create_spec_item("Distro", system.get("distro", ""))}
                {self._create_spec_item("Video", gpu_name) if gpu_name else ""}
                {self._create_spec_item("Install Date", install_date) if install_date else ""}
                {self._create_spec_item("Kernel", kernel_version)}
            </div>
        </div>
        """)
        
        return "\n".join(html)

    def _render_cpu(self, data: Dict[str, Any]) -> str:
        """Render CPU section with complete information matching GTK."""
        model = data.get("model", "Unknown")
        cores = data.get("cores", "?")
        threads = data.get("threads", "?")
        
        html = []
        
        # Build speed display
        speed_max = data.get("speed_max", "")
        speed_min = data.get("speed_min", "")
        speed_base = data.get("speed_base", "")
        speed_boost = data.get("speed_boost", "")
        
        if speed_base and speed_boost:
            speed_display = f"{speed_base}/{speed_boost} MHz (base/boost)"
        elif speed_min and speed_max:
            speed_display = f"{speed_min}-{speed_max} MHz"
        elif speed_max:
            speed_display = f"Max: {speed_max} MHz"
        else:
            speed_display = ""
        
        # Build scaling display
        scaling_driver = data.get("scaling_driver", "")
        scaling_governor = data.get("scaling_governor", "")
        scaling_display = ""
        if scaling_driver:
            scaling_display = f"{scaling_driver} / {scaling_governor}" if scaling_governor else scaling_driver
        
        # Build bits display
        bits = data.get("bits", "")
        bits_display = f"{bits} bit" if bits else ""
        
        # Hero Card
        html.append(f"""
        <div class="card hero-card">
            <div class="box-horizontal" style="justify-content: space-between;">
                <div class="hero-title">{model}</div>
            </div>
            
            <div class="box-horizontal" style="margin-top: 12px;">
                <div class="box-vertical" style="flex: 1;">
                    {self._create_spec_item("Cores", f"{cores} Cores / {threads} Threads")}
                    {self._create_spec_item("Architecture", data.get("arch", ""))}
                    {self._create_spec_item("Bits", bits_display) if bits_display else ""}
                    {self._create_spec_item("Speed", speed_display) if speed_display else ""}
                </div>
                <div class="separator"></div>
                <div class="box-vertical" style="flex: 1;">
                    {self._create_spec_item("Generation", data.get("gen", "")) if data.get("gen") else ""}
                    {self._create_spec_item("Process", data.get("process", "")) if data.get("process") else ""}
                    {self._create_spec_item("Built", data.get("built", "")) if data.get("built") else ""}
                    {self._create_spec_item("Scaling", scaling_display) if scaling_display else ""}
                </div>
            </div>
        </div>
        """)
        
        # Cache Section
        cache_l1 = data.get("cache_l1", "")
        cache_l2 = data.get("cache_l2", "")
        cache_l3 = data.get("cache_l3", "")
        
        if cache_l1 or cache_l2 or cache_l3:
            cache_items = []
            for name, val in [("L1", cache_l1), ("L2", cache_l2), ("L3", cache_l3)]:
                if val:
                    cache_items.append(f"""
                        <div class="card stat-card" style="text-align: center; padding: 12px;">
                            <div class="dim-label caption">{name}</div>
                            <div class="heading">{val}</div>
                        </div>
                    """)
            
            html.append(f"""
            <div class="title-4" style="margin-top: 16px; margin-bottom: 8px;">{_("Cache")}</div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                {''.join(cache_items)}
            </div>
            """)
        
        # Advanced Information (collapsed)
        core_speeds = data.get("core_speeds", {})
        flags = data.get("flags", "")
        vulnerabilities = data.get("vulnerabilities", [])
        
        tech_items = [
            ("Type", data.get("type", "")),
            ("Family", data.get("family", "")),
            ("Model ID", data.get("model_id", "")),
            ("Stepping", data.get("stepping", "")),
            ("Microcode", data.get("microcode", "")),
            ("Bogomips", str(data.get("bogomips", "")) if data.get("bogomips") else ""),
        ]
        tech_items = [(k, v) for k, v in tech_items if v]
        
        has_advanced = core_speeds or flags or vulnerabilities or tech_items
        
        if has_advanced:
            adv_content = []
            
            # Technical Details
            if tech_items:
                tech_rows = "".join([f"""
                    <div class="box-vertical" style="margin-bottom: 8px;">
                        <div class="caption dim-label">{_(k)}</div>
                        <div>{v}</div>
                    </div>
                """ for k, v in tech_items])
                adv_content.append(f"""
                    <div style="margin-bottom: 16px;">
                        <div class="heading" style="margin-bottom: 8px;">{_("Technical Details")}</div>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                            {tech_rows}
                        </div>
                    </div>
                """)
            
            # Thread Speeds
            if core_speeds:
                speeds_html = "".join([f"""
                    <div class="core-box" style="text-align: center; padding: 8px; background: rgba(255,255,255,0.03); border-radius: 6px;">
                        <div class="caption dim-label">{_("Thread")} {num}</div>
                        <div class="core-speed">{speed} MHz</div>
                    </div>
                """ for num, speed in sorted(core_speeds.items())])
                adv_content.append(f"""
                    <div style="margin-bottom: 16px;">
                        <div class="heading" style="margin-bottom: 8px;">{_("Thread Speeds")} ({len(core_speeds)})</div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 8px;">
                            {speeds_html}
                        </div>
                    </div>
                """)
            
            # CPU Flags
            if flags:
                flags_list = flags.split()
                adv_content.append(f"""
                    <div style="margin-bottom: 16px;">
                        <div class="heading" style="margin-bottom: 8px;">{_("CPU Flags")} ({len(flags_list)})</div>
                        <div class="dim-label" style="font-family: monospace; font-size: 0.85em; word-wrap: break-word;">{flags}</div>
                    </div>
                """)
            
            # Vulnerabilities
            if vulnerabilities:
                vuln_rows = ""
                for vuln in vulnerabilities:
                    vuln_type = vuln.get("type", "")
                    vuln_status = vuln.get("status", "")
                    vuln_mitigation = vuln.get("mitigation", "")
                    status_text = vuln_mitigation if vuln_mitigation else vuln_status
                    status_class = "success-color" if vuln_status == "Not affected" else "warning-color" if vuln_mitigation else ""
                    vuln_rows += f"""
                        <div class="box-horizontal" style="gap: 12px; margin-bottom: 4px;">
                            <div style="width: 200px;">{vuln_type}</div>
                            <div style="flex: 1; color: var(--{status_class});" class="dim-label">{status_text}</div>
                        </div>
                    """
                adv_content.append(f"""
                    <div>
                        <div class="heading" style="margin-bottom: 8px;">{_("CPU Vulnerabilities")} ({len(vulnerabilities)})</div>
                        {vuln_rows}
                    </div>
                """)
            
            html.append(self._create_expander(_("Advanced Information"), "".join(adv_content)))
        
        return "\n".join(html)

    def _render_gpu(self, data: Dict[str, Any]) -> str:
        """Render GPU section with complete information matching GTK."""
        html = []
        devices = data.get("devices", [])
        monitors = data.get("monitors", [])
        opengl = data.get("opengl", {})
        vulkan = data.get("vulkan", {})
        egl = data.get("egl", {})
        display_info = data.get("display_info", {})
        
        if not devices:
            return self._render_no_data(_("No graphics devices found"))
        
        # GPU Devices
        for device in devices:
            chip_id = device.get("chip_id", "")
            info_link = self._create_info_link(chip_id, 'pci')
            
            # Video memory from multiple sources
            video_mem = device.get("video_memory", "") or device.get("vram", "") or opengl.get("memory", "")
            
            # PCIe info
            pcie_info = ""
            if device.get("pcie_gen") and device.get("pcie_lanes"):
                pcie_info = f"Gen {device.get('pcie_gen')} x{device.get('pcie_lanes')}"
            
            # Build left/right items
            left_items = [
                ("Vendor", device.get("vendor", "")),
                ("Driver", device.get("driver", "")),
                ("Driver Version", device.get("driver_version", "")),
                ("Video Memory", video_mem),
                ("Architecture", device.get("arch", "")),
            ]
            
            right_items = [
                ("Bus ID", device.get("bus_id", "")),
                ("Chip ID", chip_id),
                ("PCIe", pcie_info),
                ("Active Ports", device.get("ports_active", "")),
                ("Empty Ports", device.get("ports_empty", "")),
            ]
            
            # Filter empty values
            left_items = [(l, v) for l, v in left_items if v and v != "Unknown"]
            right_items = [(l, v) for l, v in right_items if v and v != "Unknown"]
            
            # Add OpenGL version to left column
            if opengl.get("compat_version"):
                left_items.append(("OpenGL", opengl.get("compat_version")))
            
            # Add Vulkan and EGL to right column
            if vulkan.get("version"):
                right_items.append(("Vulkan", vulkan.get("version")))
            if egl.get("version"):
                right_items.append(("EGL", str(egl.get("version"))))
            
            left_html = "".join([self._create_spec_item(l, v) for l, v in left_items])
            right_html = "".join([self._create_spec_item(l, v) for l, v in right_items])
            
            html.append(f"""
            <div class="card hero-card" style="margin-bottom: 16px;">
                <div class="box-horizontal" style="justify-content: space-between; margin-bottom: 12px;">
                    <div class="hero-title">{device.get("name", "Unknown GPU")}</div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        {info_link}
                        <div class="device-badge accent-badge">{device.get("vendor", "")}</div>
                    </div>
                </div>
                
                <div class="box-horizontal">
                    <div class="box-vertical" style="flex: 1;">
                        {left_html}
                    </div>
                    <div class="separator"></div>
                    <div class="box-vertical" style="flex: 1;">
                        {right_html}
                    </div>
                </div>
            </div>
            """)
        
        # Monitors Section
        if monitors:
            html.append(f'<div class="title-4" style="margin-top: 16px; margin-bottom: 8px;">{_("Monitors")}</div>')
            
            for monitor in monitors:
                mon_name = monitor.get("name", monitor.get("model", "Monitor"))
                model = monitor.get("model", "")
                
                # Build monitor items
                mon_items = [
                    ("Model", model if model != mon_name else ""),
                    ("Resolution", monitor.get("resolution", "")),
                    ("Refresh Rate", f"{monitor.get('hz', '')} Hz" if monitor.get("hz") else ""),
                    ("Size", monitor.get("size", "")),
                    ("Diagonal", monitor.get("diagonal", "")),
                    ("Aspect Ratio", monitor.get("ratio", "")),
                    ("DPI", str(monitor.get("dpi", "")) if monitor.get("dpi") else ""),
                    ("Gamma", str(monitor.get("gamma", "")) if monitor.get("gamma") else ""),
                    ("Built Year", str(monitor.get("built", "")) if monitor.get("built") else ""),
                    ("Max Resolution", monitor.get("modes_max", "")),
                    ("Min Resolution", monitor.get("modes_min", "")),
                    ("Serial", monitor.get("serial", "") if monitor.get("serial") and monitor.get("serial") != "0000000000000" else ""),
                    ("Driver", monitor.get("driver", "")),
                    ("Mapped", monitor.get("mapped", "")),
                ]
                mon_items = [(l, v) for l, v in mon_items if v and v not in ("", "Hz")]
                
                mon_details_html = "".join([f"""
                    <div class="box-horizontal" style="margin-bottom: 4px;">
                        <div class="dim-label caption" style="width: 120px;">{l}</div>
                        <div>{v}</div>
                    </div>
                """ for l, v in mon_items])
                
                html.append(f"""
                <div class="card device-card" style="margin-bottom: 8px;">
                    <div class="device-title" style="margin-bottom: 8px;">{mon_name}</div>
                    {mon_details_html}
                </div>
                """)
        
        # Advanced Information (collapsed)
        has_advanced = (
            (display_info and any(display_info.values())) or
            (opengl and any(opengl.values())) or
            (vulkan and vulkan.get("version")) or
            (egl and egl.get("version"))
        )
        
        if has_advanced:
            adv_content = []
            
            # Display Server
            if display_info and any(display_info.values()):
                display_items = [
                    ("Display", display_info.get("display", "")),
                    ("With", display_info.get("with", "")),
                    ("Compositor", display_info.get("compositor", "")),
                    ("Driver Loaded", display_info.get("driver_loaded", "")),
                    ("GPU", display_info.get("gpu", "")),
                ]
                display_items = [(l, v) for l, v in display_items if v]
                if display_items:
                    display_html = "".join([f"""
                        <div class="box-horizontal" style="margin-bottom: 4px;">
                            <div class="dim-label" style="width: 120px;">{_(l)}</div>
                            <div>{v}</div>
                        </div>
                    """ for l, v in display_items])
                    adv_content.append(f"""
                        <div style="margin-bottom: 16px;">
                            <div class="heading" style="margin-bottom: 8px;">{_("Display Server")}</div>
                            {display_html}
                        </div>
                    """)
            
            # OpenGL
            if opengl and any(opengl.values()):
                gl_items = [
                    ("Version", opengl.get("version", "")),
                    ("Compatibility", opengl.get("compat_version", "")),
                    ("Vendor", opengl.get("vendor", "")),
                    ("GLX Version", opengl.get("glx_version", "")),
                    ("Direct Render", opengl.get("direct_render", "")),
                    ("Renderer", opengl.get("renderer", "")),
                    ("Video Memory", opengl.get("memory", "")),
                ]
                gl_items = [(l, v) for l, v in gl_items if v]
                if gl_items:
                    gl_html = "".join([f"""
                        <div class="box-horizontal" style="margin-bottom: 4px;">
                            <div class="dim-label" style="width: 120px;">{_(l)}</div>
                            <div>{v}</div>
                        </div>
                    """ for l, v in gl_items])
                    adv_content.append(f"""
                        <div style="margin-bottom: 16px;">
                            <div class="heading" style="margin-bottom: 8px;">{_("OpenGL")}</div>
                            {gl_html}
                        </div>
                    """)
            
            # Vulkan
            if vulkan and vulkan.get("version"):
                vk_items = [
                    ("Version", vulkan.get("version", "")),
                    ("Layers", vulkan.get("layers", "")),
                ]
                vk_items = [(l, v) for l, v in vk_items if v]
                
                vk_devices = vulkan.get("devices", [])
                vk_html = "".join([f"""
                    <div class="box-horizontal" style="margin-bottom: 4px;">
                        <div class="dim-label" style="width: 120px;">{_(l)}</div>
                        <div>{v}</div>
                    </div>
                """ for l, v in vk_items])
                
                for vk_dev in vk_devices:
                    if vk_dev.get("name"):
                        vk_html += f"""
                            <div class="box-horizontal" style="margin-bottom: 4px;">
                                <div class="dim-label" style="width: 120px;">{_("Device")}</div>
                                <div>{vk_dev.get("name", "")}</div>
                            </div>
                        """
                
                adv_content.append(f"""
                    <div style="margin-bottom: 16px;">
                        <div class="heading" style="margin-bottom: 8px;">{_("Vulkan")}</div>
                        {vk_html}
                    </div>
                """)
            
            # EGL
            if egl and egl.get("version"):
                egl_items = [
                    ("Version", str(egl.get("version", ""))),
                    ("Hardware", egl.get("hw", "")),
                    ("Platforms", egl.get("platforms", "")),
                ]
                egl_items = [(l, v) for l, v in egl_items if v]
                if egl_items:
                    egl_html = "".join([f"""
                        <div class="box-horizontal" style="margin-bottom: 4px;">
                            <div class="dim-label" style="width: 120px;">{_(l)}</div>
                            <div>{v}</div>
                        </div>
                    """ for l, v in egl_items])
                    adv_content.append(f"""
                        <div>
                            <div class="heading" style="margin-bottom: 8px;">{_("EGL")}</div>
                            {egl_html}
                        </div>
                    """)
            
            if adv_content:
                html.append(self._create_expander(_("Advanced Information"), "".join(adv_content)))
        
        return "\n".join(html)

    def _render_memory(self, data: Dict[str, Any]) -> str:
        """Render Memory section matching GTK layout."""
        html = []
        
        # Data extraction
        total = data.get("total", "N/A")
        used = data.get("used", "N/A")
        available = data.get("available", "N/A")
        percent = data.get("used_percent", 0)
        
        capacity = data.get("capacity", "")
        max_size = data.get("max_module_size", "")
        ec = data.get("ec", "")
        slots = data.get("slots", "")
        modules_summary = data.get("modules_count", "")
        if not modules_summary:
            modules_summary = str(len(data.get("modules", [])))
            
        # Determine bar color
        bar_color = "var(--accent-bg-color)"
        if percent > 80: bar_color = "var(--error-color)"
        elif percent > 60: bar_color = "var(--warning-color)"
        
        # 1. Usage Bar Section
        html.append(f"""
        <div class="card" style="margin-bottom: 24px;">
            <div class="box-horizontal" style="justify-content: space-between; margin-bottom: 8px;">
                <div class="title-4">{_("Memory Usage")}</div>
                <div class="heading">{percent}%</div>
            </div>
            
            <div class="usage-bar" style="background: rgba(255,255,255,0.1); border-radius: 4px; height: 12px; margin-bottom: 12px; overflow: hidden;">
                <div class="progress" style="width: {percent}%; background: {bar_color}; height: 100%; border-radius: 4px;"></div>
            </div>
            
            <div class="box-horizontal" style="gap: 16px; font-size: 0.9em;">
                <span class="dim-label">{_("Total:")} <span style="color: var(--text-primary);">{total}</span></span>
                <span class="dim-label">{_("Used:")} <span style="color: var(--text-primary);">{used}</span></span>
            </div>
        </div>
        """)
        
        # 2. General Info Grid
        html.append(f"""
        <div class="card" style="margin-bottom: 24px;">
            <div class="title-4" style="margin-bottom: 16px;">{_("General Information")}</div>
            <div class="box-horizontal" style="gap: 24px;">
                <div class="box-vertical" style="flex: 1;">
                    {self._create_spec_item("Capacity", capacity)}
                    {self._create_spec_item("Modules", modules_summary)}
                    {self._create_spec_item("ECC", ec)}
                </div>
                <div class="separator"></div>
                <div class="box-vertical" style="flex: 1;">
                    {self._create_spec_item("Max Module Size", max_size)}
                    {self._create_spec_item("Slots", slots)}
                </div>
            </div>
        </div>
        """)
        
        # Render Memory Modules
        modules = data.get("modules", [])
        if modules:
            modules_html = []
            for mod in modules:
                if isinstance(mod, dict):
                    size = mod.get("size", "Unknown")
                    mod_type = mod.get("type", "")
                    manufacturer = mod.get("manufacturer", "")
                    
                    # Build speed display: show both spec and actual if different
                    spec_speed = mod.get("speed", "")
                    actual_speed = mod.get("actual_speed", "")
                    
                    if spec_speed and actual_speed and spec_speed != actual_speed:
                        speed_display = f"{actual_speed} (Spec: {spec_speed})"
                    elif actual_speed:
                        speed_display = actual_speed
                    else:
                        speed_display = spec_speed
                    
                    # Build module info
                    info_rows = []
                    if mod.get("slot"):
                        info_rows.append(f'<div class="box-horizontal" style="margin-bottom: 2px;"><span class="dim-label" style="width: 80px;">Slot</span><span>{mod.get("slot")}</span></div>')
                    if speed_display:
                        info_rows.append(f'<div class="box-horizontal" style="margin-bottom: 2px;"><span class="dim-label" style="width: 80px;">Speed</span><span>{speed_display}</span></div>')
                    if mod.get("volts"):
                        info_rows.append(f'<div class="box-horizontal" style="margin-bottom: 2px;"><span class="dim-label" style="width: 80px;">Volts</span><span>{mod.get("volts")}</span></div>')
                    if manufacturer:
                        info_rows.append(f'<div class="box-horizontal" style="margin-bottom: 2px;"><span class="dim-label" style="width: 80px;">Manufacturer</span><span>{manufacturer}</span></div>')
                    # Part Number intentionally not shown
                    if mod.get("serial"):
                        info_rows.append(f'<div class="box-horizontal" style="margin-bottom: 2px;"><span class="dim-label" style="width: 80px;">Serial</span><span>{mod.get("serial")}</span></div>')
                    
                    modules_html.append(f"""
                    <div class="card memory-slot" style="border-left: 3px solid var(--accent-color);">
                        <div class="heading" style="margin-bottom: 8px;">{size} {mod_type}</div>
                        {''.join(info_rows)}
                    </div>
                    """)
            
            if modules_html:
                html.append(self._create_expander(_("Memory Modules") + f" ({len(modules)})", f"""
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px;">
                        {''.join(modules_html)}
                    </div>
                """))
            
        return "\n".join(html)

    def _render_disk(self, data: Dict[str, Any]) -> str:
        """Render Storage section with complete info matching GTK."""
        html = []
        drives = data.get("drives", [])
        
        # Access partitions from multiple potential locations
        full_data = self.data.to_dict()
        partitions = data.get("partitions", []) or full_data.get("partitions", {}) or full_data.get("all_partitions", [])
        
        if not drives:
            return self._render_no_data(_("No storage drives found"))
        
        # Total Storage Summary
        total_size = data.get("total_size", "")
        used = data.get("used", "")
        used_percent = data.get("used_percent", 0)
        
        if total_size or used:
            bar_color = "success-color"
            if used_percent > 90: bar_color = "error-color"
            elif used_percent > 70: bar_color = "warning-color"
            
            html.append(f"""
            <div class="card" style="margin-bottom: 24px;">
                <div class="title-4" style="margin-bottom: 8px;">{_("Total Storage:")} {total_size}</div>
                <div class="box-horizontal" style="align-items: center; gap: 12px; margin-bottom: 4px;">
                    <div style="flex: 1; background: rgba(255,255,255,0.1); border-radius: 4px; height: 8px; overflow: hidden;">
                        <div style="width: {used_percent}%; height: 100%; background: var(--{bar_color}); border-radius: 4px;"></div>
                    </div>
                    <div class="heading">{used_percent:.0f}%</div>
                </div>
                <div class="dim-label">{_("Used:")} {used}</div>
            </div>
            """)
        
        # Section title
        html.append(f'<div class="title-4" style="margin-bottom: 12px; margin-top: 16px;">{_("Storage Devices")}</div>')
            
        for drive in drives:
            model = drive.get("model", "Unknown Drive")
            drive_type = drive.get("type", "")
            
            # Build type badge
            type_badge_class = "success-badge" if "ssd" in drive_type.lower() or "nvme" in drive_type.lower() else ""
            
            # Build left/right items matching GTK
            left_items = [
                ("Size", drive.get("size", "")),
                ("Vendor", drive.get("vendor", "")),
                ("Speed", drive.get("speed", "")),
                ("Device", drive.get("id", "")),
            ]
            
            right_items = [
                ("Lanes", str(drive.get("lanes", "")) if drive.get("lanes") else ""),
                ("Temp", drive.get("temp", "")),
                ("Firmware", drive.get("firmware", "")),
                ("Serial", str(drive.get("serial", ""))),
            ]
            
            # Filter empty values
            left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "Unknown", "?", "")]
            right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "Unknown", "?", "")]
            
            left_html = "".join([self._create_spec_item(l, v) for l, v in left_items])
            right_html = "".join([self._create_spec_item(l, v) for l, v in right_items])
            
            html.append(f"""
            <div class="card" style="margin-bottom: 16px;">
                <div class="box-horizontal" style="justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div class="title-4">{model}</div>
                    <div class="device-badge {type_badge_class}">{drive_type.upper() if drive_type else "DISK"}</div>
                </div>
                
                <div class="box-horizontal">
                    <div class="box-vertical" style="flex: 1;">
                        {left_html}
                    </div>
                    <div class="separator"></div>
                    <div class="box-vertical" style="flex: 1;">
                        {right_html}
                    </div>
                </div>
            </div>
            """)
        
        # Render Partitions in Expander
        if partitions:
            # Consolidate partitions by device ID to handle BTRFS subvolumes
            consolidated_partitions = {}
            part_list = []
            
            # Normalize to list
            if isinstance(partitions, dict):
                for part_id, part_data in partitions.items():
                    if isinstance(part_data, dict):
                        part_list.append(part_data)
                    elif isinstance(part_data, list):
                        part_list.extend([p for p in part_data if isinstance(p, dict)])
            elif isinstance(partitions, list):
                part_list = [p for p in partitions if isinstance(p, dict)]
            
            # Group by device ID
            for part in part_list:
                dev_id = part.get("dev", part.get("id", ""))
                if not dev_id:
                    continue
                
                if dev_id not in consolidated_partitions:
                    consolidated_partitions[dev_id] = part.copy()
                    # Initialize mount points as list
                mount_point = part.get("mount") or part.get("mountpoint") or part.get("id")
                
                # Ensure mount_points list exists
                if "mount_points" not in consolidated_partitions[dev_id]:
                    consolidated_partitions[dev_id]["mount_points"] = []
                
                # Add single mount point if found
                if mount_point and mount_point not in consolidated_partitions[dev_id]["mount_points"]:
                    consolidated_partitions[dev_id]["mount_points"].append(mount_point)
                
                # Check for array style mounts (lsblk)
                mounts = part.get("mountpoints", [])
                if isinstance(mounts, list):
                    for m in mounts:
                        if m and m not in consolidated_partitions[dev_id]["mount_points"]:
                            consolidated_partitions[dev_id]["mount_points"].append(m)
            
            part_html = []
            for dev_id, part in consolidated_partitions.items():
                part_html.append(self._render_partition_item(part))
            
            if part_html:
                html.append(self._create_expander(_("Disk Partitions"), "\n".join(part_html)))
            
        return "\n".join(html)

    def _render_partition_item(self, part: Dict[str, Any]) -> str:
        """Render a single partition item matching GTK format."""
        import re
        
        # Device name (like /dev/nvme0n1p2) - use dev or id 
        dev = part.get("dev", part.get("id", ""))
        
        # Label (badge if present)
        label = part.get("label", "")
        
        # Filesystem badge
        fs = part.get("fs", part.get("filesystem", ""))
        
        # Size - clean percentage from size string
        size = part.get("size", part.get("raw_size", ""))
        if isinstance(size, str):
            size = re.sub(r'\s*\([0-9.]+%\)', '', size).strip()
        
        # Mount points - Handle both single string and list for robust display
        if "mount_points" in part:
            mount_points = part["mount_points"]
        elif "mountpoints" in part:
             # Fallback for lsblk style
             val = part["mountpoints"]
             mount_points = val if isinstance(val, list) else ([val] if val else [])
        else:
            # Fallback for single item w/o consolidation
            val = part.get("mount") or part.get("mountpoint") or part.get("id")
            mount_points = [val] if val else []

        mount_display = ""
        if mount_points:
             # Join with commas
             mount_str = ", ".join(mount_points)
             mount_display = f'<div class="box-horizontal" style="margin-top: 4px;"><span class="caption dim-label" style="margin-right: 8px;">{_("Mounted on:")}</span><span>{mount_str}</span></div>'
             
        # Used and Used percent
        used_str = part.get("used", "")
        used_percent = part.get("used_percent", 0)
        
        # Parse percent from used string if not available
        if not used_percent and used_str:
            match = re.search(r'\(([0-9.]+)%\)', used_str)
            if match:
                try:
                    used_percent = float(match.group(1))
                except:
                    used_percent = 0
        
        # Clean used string for display
        used_clean = re.sub(r'\s*\([0-9.]+%\)', '', str(used_str)).strip() if used_str else ""
        
        # Bar color based on usage
        bar_color = "success-color"
        if used_percent > 90: bar_color = "error-color"
        elif used_percent > 70: bar_color = "warning-color"
        
        # Build badges HTML
        badges_html = ""
        if label and label != "N/A":
            badges_html += f'<div class="device-badge" style="background: var(--accent-bg-color);">{label}</div>'
        if fs:
            badges_html += f'<div class="device-badge">{fs}</div>'
        
        # Build usage display string
        usage_display = (
            f"{_('Used:')} {used_clean} ({used_percent:.1f}%)"
            if used_clean
            else f"{used_percent:.1f}%"
        )
        
        return f"""
        <div class="card" style="margin-bottom: 8px;">
            <div class="box-horizontal" style="justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div class="heading" style="font-family: monospace;">{dev}</div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    {badges_html}
                    <div class="dim-label" style="font-weight: 500;">{size}</div>
                </div>
            </div>
            
            <!-- Mount point -->
            {mount_display}
            
            <!-- Usage bar -->
            <div class="box-horizontal" style="align-items: center; gap: 12px;">
                <div style="flex: 1; background: rgba(255,255,255,0.1); border-radius: 4px; height: 6px; overflow: hidden;">
                    <div style="width: {used_percent}%; height: 100%; background: var(--{bar_color}); border-radius: 4px;"></div>
                </div>
                <div class="dim-label" style="min-width: 100px; text-align: right;">{usage_display}</div>
            </div>
        </div>
        """

    def _render_system(self, data: Dict[str, Any]) -> str:
        """Render System section with complete info matching GTK."""
        html = []
        
        distro = data.get("distro", "Linux")
        
        # Build shell display with version
        shell_name = data.get("shell", "")
        shell_version = data.get("shell_version", "")
        shell_display = f"{shell_name} v{shell_version}" if shell_version else shell_name
        
        # Build kernel display with details
        kernel = data.get("kernel", "") or self.data.kernel.get("version", "")
        kernel_arch = data.get("kernel_arch", "")
        kernel_bits = data.get("kernel_bits", "")
        kernel_display = kernel
        if kernel_arch:
            kernel_display += f" ({kernel_arch}"
            if kernel_bits:
                kernel_display += f", {kernel_bits} bit"
            kernel_display += ")"
        
        # Build left/right items matching GTK
        left_items = [
            ("Hostname", data.get("hostname", "") or self.data.hostname),
            ("Kernel", kernel_display),
            ("Desktop", f"{data.get('desktop', '')} {data.get('desktop_version', '')}".strip()),
            ("Window Manager", data.get("wm", "")),
            ("Shell", shell_display),
            ("Terminal", data.get("terminal", "")),
        ]
        
        right_items = [
            ("Init System", data.get("init", "")),
            ("Session Type", data.get("session_type", "")),
            ("Display Manager", data.get("dm", "")),
            ("Compositor", data.get("compositor", "")),
            ("Uptime", data.get("uptime", "")),
            ("Processes", str(data.get("processes", "")) if data.get("processes") else ""),
            ("Packages", data.get("packages", "")),
            ("Locale", data.get("locale", "")),
        ]
        
        # Filter empty values
        left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "Unknown", "?", "")]
        right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "Unknown", "?", "")]
        
        left_html = "".join([self._create_spec_item(l, v) for l, v in left_items])
        right_html = "".join([self._create_spec_item(l, v) for l, v in right_items])
        
        html.append(f"""
        <div class="card hero-card" style="margin-bottom: 16px;">
            <div class="hero-title">{distro}</div>
            
            <div class="box-horizontal" style="margin-top: 12px;">
                <div class="box-vertical" style="flex: 1;">
                    {left_html}
                </div>
                <div class="separator"></div>
                <div class="box-vertical" style="flex: 1;">
                    {right_html}
                </div>
            </div>
        </div>
        """)
        
        return "\n".join(html)

    def _render_machine(self, data: Dict[str, Any]) -> str:
        """Render Motherboard/Machine section."""
        html = []
        
        # Determine icon based on chassis type (simple heuristic)
        chassis_type = data.get("type", "Desktop")
        icon = "💻" if "Laptop" in chassis_type or "Notebook" in chassis_type else "🖥️"
        
        html.append(f"""
        <div class="card hero-card" style="margin-bottom: 24px;">
            <div class="box-horizontal" style="justify-content: space-between; margin-bottom: 12px;">
                <div class="hero-title">{data.get("product", "Unknown Product")}</div>
                <div class="device-badge accent-badge">{data.get("system", "")}</div>
            </div>
            
            <div class="box-horizontal">
                <div class="box-vertical" style="flex: 1;">
                    {self._create_spec_item("Motherboard", data.get("mobo", "N/A"))}
                    {self._create_spec_item("Model", data.get("mobo_model", "N/A"))}
                    {self._create_spec_item("Version", data.get("mobo_version", "N/A"))}
                </div>
                <div class="separator"></div>
                <div class="box-vertical" style="flex: 1;">
                    {self._create_spec_item("Firmware Vendor", data.get("firmware_vendor", "N/A"))}
                    {self._create_spec_item("Firmware Version", data.get("firmware_version", "N/A"))}
                    {self._create_spec_item("Date", data.get("firmware_date", "N/A"))}
                </div>
            </div>
        </div>
        """)
        return "\n".join(html)

    def _render_audio(self, data: Dict[str, Any]) -> str:
        """Render Audio section."""
        html = []
        devices = data.get("devices", [])
        
        if not devices:
            return self._render_no_data(_("No audio devices found"))
            
        for device in devices:
            chip_id = device.get("chip_id", "")
            device_type = device.get("type", "PCI").upper()
            is_usb = device_type == "USB"
            
            # Choose info link type based on device type
            info_link_type = 'usb' if is_usb else 'pci'
            info_link = self._create_info_link(chip_id, info_link_type)
            
            # Build connection info based on device type
            connection_info = ""
            if is_usb:
                usb_speed = device.get("usb_speed", "")
                usb_rev = device.get("usb_rev", "")
                if usb_speed:
                    connection_info = f"USB {usb_rev} {usb_speed}" if usb_rev else f"USB {usb_speed}"
            else:
                pcie_gen = device.get("pcie_gen", "")
                pcie_speed = device.get("pcie_speed", "")
                pcie_lanes = device.get("pcie_lanes", "")
                if pcie_gen and pcie_lanes:
                    connection_info = f"PCIe Gen {pcie_gen} x{pcie_lanes}"
                elif pcie_speed and pcie_lanes:
                    connection_info = f"PCIe {pcie_speed} x{pcie_lanes}"

            html.append(f"""
            <div class="card" style="margin-bottom: 12px;">
                <div class="box-horizontal" style="justify-content: space-between; margin-bottom: 8px;">
                    <div class="heading">{device.get("name", "Unknown Audio Device")}</div>
                    {info_link}
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                    <div class="box-vertical">
                        <div class="caption dim-label">Vendor</div>
                        <div>{device.get("vendor", "")}</div>
                    </div>
                    <div class="box-vertical">
                        <div class="caption dim-label">Driver</div>
                        <div>{device.get("driver", "N/A")}</div>
                    </div>
                    {self._create_spec_item("Bus ID", device.get("bus_id", ""))}
                    {self._create_spec_item("Chip ID", chip_id)}
                    {self._create_spec_item("Connection", connection_info) if connection_info else ""}
                </div>
            </div>
            """)
        return "\n".join(html)

    def _render_network(self, data: Dict[str, Any]) -> str:
        """Render Network section."""
        html = []
        devices = data.get("devices", [])
        virtual_devices = data.get("virtual_devices", [])
        
        if not devices and not virtual_devices:
            return self._render_no_data(_("No network interfaces found"))
            
        physical = []
        virtual = []
        
        for device in devices:
            # Simple heuristic for virtual/loopback
            name = device.get("name", "").lower()
            ifname = device.get("IF", "").lower()
            if "virtual" in name or "loopback" in name or "veth" in ifname or "docker" in ifname or "br-" in ifname:
                virtual.append(device)
            else:
                physical.append(device)
        
        # Add virtual_devices from data
        virtual.extend(virtual_devices)
                
        # Render Physical
        for device in physical:
            html.append(self._render_network_card(device))
            
        # Render Virtual in Expander
        if virtual:
            virt_html = []
            for device in virtual:
                virt_html.append(self._render_network_card(device))
            html.append(
                self._create_expander(
                    f"{_('Virtual Networks')} ({len(virtual)})", "\n".join(virt_html)
                )
            )
            
        return "\n".join(html)

    def _render_network_card(self, device: Dict[str, Any]) -> str:
        """Helper to render a single network card with complete info."""
        state = device.get("state", "").lower()
        status_badge = ""
        if state:
            badge_class = "success-badge" if "up" in state else ""
            status_badge = f'<div class="device-badge {badge_class}">{state.upper()}</div>'
        
        # Determine device type (USB vs PCIe)
        device_type = device.get("type", "PCI").upper()
        is_usb = device_type == "USB"
        
        # Build chip_id info link
        chip_id = device.get("chip_id", "")
        info_link_type = 'usb' if is_usb else 'pci'
        info_link = self._create_info_link(chip_id, info_link_type) if chip_id else ""
        
        # Build connection info based on device type
        connection_info = ""
        if is_usb:
            usb_speed = device.get("usb_speed", "")
            usb_rev = device.get("usb_rev", "")
            if usb_speed:
                connection_info = f"USB {usb_rev} {usb_speed}" if usb_rev else f"USB {usb_speed}"
        else:
            pcie_gen = device.get("pcie_gen", "")
            pcie_speed = device.get("pcie_speed", "")
            pcie_lanes = device.get("pcie_lanes", "")
            if pcie_gen and pcie_lanes:
                connection_info = f"Gen {pcie_gen} x{pcie_lanes}"
            elif pcie_speed and pcie_lanes:
                connection_info = f"{pcie_speed} x{pcie_lanes}"
            elif device.get("lanes"):
                connection_info = f"x{device.get('lanes')}"
        
        # Build left/right items matching GTK
        left_items = [
            ("Vendor", device.get("vendor", "")),
            ("Driver", device.get("driver", "")),
            ("Interface", device.get("IF", "")),
            ("Speed", device.get("speed", "")),
        ]
        
        connection_label = "USB" if is_usb else "PCIe"
        right_items = [
            ("Bus ID", device.get("bus_id", "")),
            ("Chip ID", chip_id),
            ("MAC", device.get("mac", "")),
            (connection_label, connection_info),
        ]
        
        # Filter empty values
        left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "Unknown", "?")]
        right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "Unknown", "?")]
        
        left_html = "".join([self._create_spec_item(l, v) for l, v in left_items])
        right_html = "".join([self._create_spec_item(l, v) for l, v in right_items])
        
        return f"""
        <div class="card" style="margin-bottom: 16px;">
            <div class="box-horizontal" style="justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div class="title-4">{device.get("name", "Unknown Interface")}</div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    {status_badge}
                    {info_link}
                </div>
            </div>
            
            <div class="box-horizontal">
                <div class="box-vertical" style="flex: 1;">
                    {left_html}
                </div>
                <div class="separator"></div>
                <div class="box-vertical" style="flex: 1;">
                    {right_html}
                </div>
            </div>
        </div>
        """
        
    def _render_battery(self, data: Dict[str, Any]) -> str:
        """Render Battery section with two-column layout matching GTK."""
        html = []
        
        batteries = data.get("batteries", [])
        
        # Backwards compatibility: if no batteries list, create one from root data
        if not batteries and data.get("charge"):
            batteries = [{
                "id": data.get("model", "Battery"),
                "charge": data.get("charge", 0),
                "condition": data.get("condition", ""),
                "volts": data.get("volts", ""),
                "model": data.get("model", ""),
                "type": data.get("type", ""),
                "serial": data.get("serial", ""),
                "status": data.get("status", ""),
                "cycles": data.get("cycles", ""),
                "volts_min": data.get("volts_min", ""),
            }]
        
        if not batteries:
            return self._render_no_data(_("No battery detected (Desktop system)"))
        
        # Display each battery
        for battery in batteries:
            # Parse charge value
            charge = battery.get("charge", 0)
            if isinstance(charge, str):
                try:
                    charge = float(charge.replace("%", "").strip())
                except ValueError:
                    charge = 0
            
            status = battery.get("status", "").lower()
            model = battery.get("model", "") or battery.get("id", "Battery")
            
            # Color based on charge
            bar_color = "success-color"
            if charge <= 20: bar_color = "error-color"
            elif charge <= 50: bar_color = "warning-color"
            
            status_badge_class = ""
            if "charging" in status:
                status_badge_class = "success-badge"
            elif "discharging" in status:
                status_badge_class = "warning-badge"
            
            # Build left/right items matching GTK layout
            left_items = [
                ("Condition", battery.get("condition", "")),
                ("Type", battery.get("type", "")),
                ("Cycles", str(battery.get("cycles", "")) if battery.get("cycles") else ""),
            ]
            
            right_items = [
                ("Voltage", battery.get("volts", "")),
                ("Min Voltage", battery.get("volts_min", "")),
                ("Serial", battery.get("serial", "")),
            ]
            
            # Filter empty values
            left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "Unknown", "?", "")]
            right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "Unknown", "?", "")]
            
            left_html = "".join([self._create_spec_item(l, v) for l, v in left_items])
            right_html = "".join([self._create_spec_item(l, v) for l, v in right_items])
            
            html.append(f"""
            <div class="card" style="margin-bottom: 16px;">
                <div class="box-horizontal" style="justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div class="title-4">{model}</div>
                    <div class="device-badge {status_badge_class}">{status.upper() if status else "UNKNOWN"}</div>
                </div>
                
                <!-- Charge bar -->
                <div class="box-horizontal" style="align-items: center; gap: 12px; margin-bottom: 12px;">
                    <div style="flex: 1; background: rgba(255,255,255,0.1); border-radius: 4px; height: 8px; overflow: hidden;">
                        <div style="width: {charge}%; height: 100%; background: var(--{bar_color}); border-radius: 4px;"></div>
                    </div>
                    <div class="stat-value">{charge:.0f}%</div>
                </div>
                
                <!-- Two-column layout -->
                <div class="box-horizontal">
                    <div class="box-vertical" style="flex: 1;">
                        {left_html}
                    </div>
                    <div class="separator"></div>
                    <div class="box-vertical" style="flex: 1;">
                        {right_html}
                    </div>
                </div>
            </div>
            """)
                
        return "\n".join(html)
        
    def _render_bluetooth(self, data: Dict[str, Any]) -> str:
        """Render Bluetooth section."""
        html = []
        devices = data.get("devices", [])
        
        if not devices:
            return self._render_no_data(_("No Bluetooth devices found"))
            
        for device in devices:
            chip_id = device.get("chip_id", "")
            info_link = self._create_info_link(chip_id, 'usb')  # Bluetooth typically uses USB
            
            # Get status badge
            status = device.get("status", "")
            status_badge = ""
            if status:
                badge_class = "success-badge" if "up" in status.lower() or "running" in status.lower() else ""
                status_badge = f'<div class="device-badge {badge_class}">{status.upper()}</div>'
            
            html.append(f"""
            <div class="card" style="margin-bottom: 12px;">
                <div class="box-horizontal" style="justify-content: space-between; margin-bottom: 8px; align-items: center;">
                    <div class="heading">{device.get("name", "Unknown Device")}</div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        {status_badge}
                        {info_link}
                    </div>
                </div>
                <div class="box-horizontal" style="gap: 16px;">
                    {self._create_spec_item("Driver", device.get("driver", "N/A"))}
                    {self._create_spec_item("Bus ID", device.get("bus_id", "N/A"))}
                    {self._create_spec_item("Chip ID", chip_id)}
                </div>
            </div>
            """)
        return "\n".join(html)

    def _render_usb(self, data: Dict[str, Any]) -> str:
        """Render USB section preferring inxi data."""
        html = []
        
        # Prefer inxi data over lsusb
        full_data = self.data.to_dict()
        usb_inxi = full_data.get("usb_inxi", {})
        
        if usb_inxi.get("devices") or usb_inxi.get("hubs"):
            devices = usb_inxi.get("devices", [])
            hubs = usb_inxi.get("hubs", [])
            
            # Connected Devices Section
            if devices:
                html.append(
                    f'<div class="title-4" style="margin-bottom: 12px;">{_("Connected Devices")}</div>'
                )
                for device in devices:
                    html.append(self._render_usb_item(device))
            
            # USB Hubs in Expander
            if hubs:
                hub_html = []
                for hub in hubs:
                    hub_html.append(self._render_usb_item(hub))
                html.append(
                    self._create_expander(
                        f"{_('USB Hubs & Controllers')} ({len(hubs)})",
                        "\n".join(hub_html),
                    )
                )
                
            return "\n".join(html) if html else self._render_no_data(_("No USB devices found"))
        
        # Fallback to lsusb data
        devices = data.get("devices", [])
        
        if not devices:
            return self._render_no_data(_("No USB devices found"))
            
        hubs = []
        peripherals = []
        
        for device in devices:
            name = device.get("name", "").lower()
            if "hub" in name or "root hub" in name:
                hubs.append(device)
            else:
                peripherals.append(device)
                
        # Peripherals first
        for device in peripherals:
            html.append(self._render_usb_item(device))
            
        # Hubs in expander
        if hubs:
            hub_html = []
            for device in hubs:
                hub_html.append(self._render_usb_item(device))
            html.append(
                self._create_expander(
                    f"{_('USB Hubs')} ({len(hubs)})", "\n".join(hub_html)
                )
            )
            
        return "\n".join(html)

    def _render_usb_item(self, device: Dict[str, Any]) -> str:
        """Render a single USB device card with two-column layout (same as GTK)."""
        name = device.get("name", "")
        info = device.get("info", name)
        
        # Build chip_id and info link
        chip_id = device.get("chip_id", "")
        info_link = self._create_info_link(chip_id, 'usb')
        
        # Get type badge
        dev_type = device.get("type", "")
        type_badge = f'<div class="device-badge">{dev_type.upper()}</div>' if dev_type else ""
        
        # Split info into two columns like GTK
        left_items = [
            ("Driver", device.get("driver", "")),
            ("Speed", device.get("speed", "")),
            ("Power", device.get("power", "")),
        ]
        
        right_items = [
            ("Chip ID", chip_id),
            ("Mode", device.get("mode", "")),
        ]
        
        # Filter out empty values
        left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "Unknown", "?", "")]
        right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "Unknown", "?", "")]
        
        left_html = "".join([self._create_spec_item(l, v) for l, v in left_items])
        right_html = "".join([self._create_spec_item(l, v) for l, v in right_items])
        
        return f"""
        <div class="card" style="margin-bottom: 12px;">
            <div class="box-horizontal" style="justify-content: space-between; margin-bottom: 8px; align-items: center;">
                <div class="heading">{info if info else name}</div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    {type_badge}
                    {info_link}
                </div>
            </div>
            
            <div class="box-horizontal">
                <div class="box-vertical" style="flex: 1;">
                    {left_html}
                </div>
                <div class="separator"></div>
                <div class="box-vertical" style="flex: 1;">
                    {right_html}
                </div>
            </div>
        </div>
        """

    def _render_pci(self, data: Dict[str, Any]) -> str:
        """Render PCI section using lspci data enriched with pci_inxi (same as GTK)."""
        html = []
        
        # Get data same as GTK
        full_data = self.data.to_dict()
        pci_lspci = full_data.get("pci", {})
        pci_inxi = full_data.get("pci_inxi", {})
        
        # Build a lookup from inxi data for enrichment (by bus_id)
        inxi_lookup = {}
        for device in pci_inxi.get("devices", []):
            bus_id = device.get("bus_id", "")
            if bus_id:
                inxi_lookup[bus_id] = device
        
        # Get devices from lspci (ALL PCI devices)
        devices = pci_lspci.get("devices", [])
        
        if not devices:
            return self._render_no_data(_("No PCI devices found"))
        
        # Separate important devices from infrastructure using keywords
        important_devices = []
        infrastructure_devices = []
        
        for device in devices:
            name = device.get("name", "").lower()
            category = device.get("category", "").lower()
            
            # Check if it's an infrastructure device
            is_infrastructure = any(kw in name or kw in category for kw in PCI_INFRASTRUCTURE_KEYWORDS)
            
            if is_infrastructure:
                infrastructure_devices.append(device)
            else:
                important_devices.append(device)
        
        # Render important devices as standard cards
        if important_devices:
            for device in important_devices:
                html.append(self._render_pci_item(device, inxi_lookup))
        
        # Render infrastructure devices in a collapsible expander
        if infrastructure_devices:
            infra_html = []
            for device in infrastructure_devices:
                infra_html.append(self._render_pci_item(device, inxi_lookup))
            html.append(
                self._create_expander(
                    f"{_('System Controllers & Bridges')} ({len(infrastructure_devices)} {_('devices')})",
                    "\n".join(infra_html),
                )
            )
             
        return "\n".join(html)
        
    def _render_pci_item(self, device: Dict[str, Any], inxi_lookup: Dict[str, Any] = None) -> str:
        """Render a single PCI device card with driver from inxi_lookup (same as GTK)."""
        if inxi_lookup is None:
            inxi_lookup = {}
        
        # Get slot/bus_id from lspci
        slot = device.get("slot", "")
        
        # Try to enrich with inxi data using bus_id
        inxi_device = inxi_lookup.get(slot, {})
        
        # Build name - prefer lspci name
        name = device.get("name", "") or inxi_device.get("name", "Unknown Device")
        
        # Build IDs
        vendor_id = device.get("vendor_id", "")
        device_id = device.get("device_id", "")
        full_id = device.get("full_id", "") or inxi_device.get("chip_id", "")
        
        # Build chip_id for info link
        chip_id = f"{vendor_id}:{device_id}" if vendor_id and device_id else full_id
        info_link = self._create_info_link(chip_id, 'pci')
        
        # Get driver from inxi if available (same as GTK)
        driver = inxi_device.get("driver", "")
        
        # Build PCIe info string from inxi if available
        pcie_info = ""
        if inxi_device.get("pcie_gen") and inxi_device.get("pcie_lanes"):
            pcie_info = f"Gen {inxi_device.get('pcie_gen')} x{inxi_device.get('pcie_lanes')}"
        elif inxi_device.get("pcie_speed") and inxi_device.get("pcie_lanes"):
            pcie_info = f"{inxi_device.get('pcie_speed')} x{inxi_device.get('pcie_lanes')}"
        
        # Get device details
        category = device.get("category", "")
        class_id = device.get("class_id", "")
        
        # Build left/right items like GTK
        left_items = [
            ("Category", category),
            ("Driver", driver),
            ("Class ID", class_id),
        ]
        
        right_items = [
            ("Bus ID", slot),
            ("Chip ID", chip_id),
            ("PCIe", pcie_info),
        ]
        
        # Filter empty values
        left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "Unknown", "?", "")]
        right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "Unknown", "?", "")]
        
        left_html = "".join([self._create_spec_item(l, v) for l, v in left_items])
        right_html = "".join([self._create_spec_item(l, v) for l, v in right_items])
        
        return f"""
        <div class="card" style="margin-bottom: 12px;">
            <div class="box-horizontal" style="justify-content: space-between; margin-bottom: 8px;">
                <div class="heading">{name}</div>
                {info_link}
            </div>


            
            <div class="box-horizontal">
                <div class="box-vertical" style="flex: 1;">
                    {left_html}
                </div>
                <div class="separator"></div>
                <div class="box-vertical" style="flex: 1;">
                    {right_html}
                </div>
            </div>
        </div>
        """
        
    def _render_webcam(self, data: Dict[str, Any]) -> str:
        """Render Webcam section."""
        html = []
        devices = data.get("devices", [])
        
        if not devices:
            return self._render_no_data(_("No webcams found"))
            
        for device in devices:
            chip_id = device.get("chip_id", "")
            info_link = self._create_info_link(chip_id, 'usb') if chip_id else ""
            
            # Build left/right items matching GTK
            left_items = [
                ("Resolution", device.get("resolution", "")),
                ("Format", device.get("pixel_format", "")),
                ("Chip ID", chip_id),
                ("Driver", device.get("driver", "")),
            ]
            
            right_items = [
                ("Colorspace", device.get("colorspace", "")),
                ("Max FPS", device.get("max_fps", "")),
                ("Driver Version", device.get("driver_version", "")),
                ("Device", device.get("device_path", "")),
            ]
            
            # Filter empty values
            left_items = [(l, v) for l, v in left_items if v and v not in ("N/A", "")]
            right_items = [(l, v) for l, v in right_items if v and v not in ("N/A", "")]
            
            left_html = "".join([self._create_spec_item(l, v) for l, v in left_items])
            right_html = "".join([self._create_spec_item(l, v) for l, v in right_items])
            
            html.append(f"""
            <div class="card hero-card" style="margin-bottom: 12px;">
                <div class="box-horizontal" style="justify-content: space-between; margin-bottom: 12px; align-items: center;">
                    <div class="hero-title">{device.get("name", "Unknown Webcam")}</div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        {info_link}
                    </div>
                </div>
                <div class="box-horizontal">
                    <div class="box-vertical" style="flex: 1;">
                        {left_html}
                    </div>
                    <div class="separator"></div>
                    <div class="box-vertical" style="flex: 1;">
                        {right_html}
                    </div>
                </div>
            </div>
            """)
        return "\n".join(html)

    def _render_printer(self, data: Dict[str, Any]) -> str:
        """Render Printers section with GTK-like display."""
        html = []
        
        raw = data.get("raw", "")
        if not raw:
            # Try getting from printers key (different data format)
            printers_str = data.get("printers", "")
            if printers_str:
                raw = printers_str
        
        if not raw:
            return self._render_no_data(_("No printers configured"))
        
        # Parse lpstat output
        printers = []
        default_printer = ""
        
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("printer "):
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1]
                    status = "Unknown"
                    if "idle" in line.lower():
                        status = "Idle"
                    elif "printing" in line.lower():
                        status = "Printing"
                    elif "disabled" in line.lower() or "inativa" in line.lower():
                        status = "Disabled"
                    
                    enabled = "enabled" in line.lower() or "habilitada" in line.lower()
                    printers.append({
                        "name": name,
                        "status": status,
                        "enabled": enabled,
                    })
            elif "default destination:" in line.lower() or "destino padrão" in line.lower():
                default_printer = line.split(":")[-1].strip()
        
        # If no printers parsed from format, try simple display
        if not printers and raw:
            # Just display the raw info nicely
            html.append(f"""
            <div class="card terminal-card">
                <div class="terminal-title">{_("Printer Status")}</div>
                <div class="terminal-text">{raw}</div>
            </div>
            """)
            return "\n".join(html)
        
        # Display parsed printers
        for printer in printers:
            status_class = ""
            if printer["status"] == "Idle":
                status_class = "success-badge"
            elif printer["status"] == "Printing":
                status_class = "warning-badge"
            
            default_badge = ""
            if printer["name"] == default_printer:
                default_badge = '<div class="device-badge success-badge" style="margin-left: 8px;">DEFAULT</div>'
            
            html.append(f"""
            <div class="card device-card" style="margin-bottom: 8px;">
                <div class="box-horizontal" style="align-items: center; gap: 16px;">
                    <div style="font-size: 1.5em; opacity: 0.7;">🖨️</div>
                    <div class="box-vertical" style="flex: 1;">
                        <div class="device-title">{printer["name"]}</div>
                    </div>
                    {default_badge}
                    <div class="device-badge {status_class}">{printer["status"]}</div>
                </div>
            </div>
            """)
        
        # Show raw output
        if raw:
            html.append(f"""
            <div class="card terminal-card" style="margin-top: 16px;">
                <div class="terminal-title">{_("Printer Details")}</div>
                <div class="terminal-text" style="max-height: 300px; overflow: auto;">{raw}</div>
            </div>
            """)
        
        return "\n".join(html)

    def _render_sensors(self, data: Dict[str, Any]) -> str:
        """Render Sensors section with complete info matching GTK."""
        html = []
        temps = data.get("temps", [])
        fans = data.get("fans", [])
        sensors_cmd = data.get("sensors_cmd", "")
        
        if not temps and not fans and not sensors_cmd:
            return self._render_no_data(_("No sensors detected"))
            
        if temps:
            html.append(
                f'<div class="title-4" style="margin-bottom: 12px;">{_("System Temperatures")}</div>'
            )
            html.append('<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px;">')
            
            for temp in temps:
                val = temp.get("temp", temp.get("value", 0))
                if isinstance(val, str):
                    try:
                        val = float(val.replace("°C", "").replace("C", "").strip())
                    except:
                        val = 0
                
                color = "accent-color"
                if val > 80: color = "error-color"
                elif val > 60: color = "warning-color"
                
                name = temp.get("name", temp.get("device", "Sensor"))
                
                html.append(f"""
                <div class="card stat-card">
                    <div class="stat-label">{name}</div>
                    <div class="stat-value" style="color: var(--{color});">{val}°C</div>
                </div>
                """)
            html.append('</div>')
            
        if fans:
            html.append(
                f'<div class="title-4" style="margin-bottom: 12px;">{_("Fan Speeds")}</div>'
            )
            html.append('<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px;">')
            for fan in fans:
                speed = fan.get("speed", fan.get("value", "N/A"))
                speed_str = f"{speed} RPM" if isinstance(speed, (int, float)) else str(speed)
                name = fan.get("name", "Fan")
                
                html.append(f"""
                <div class="card stat-card">
                    <div class="stat-label">{name}</div>
                    <div class="stat-value">{speed_str}</div>
                </div>
                """)
            html.append('</div>')
        
        # Detailed Sensor Data (sensors command output)
        if sensors_cmd:
            escaped_cmd = self._apply_syntax_highlighting(sensors_cmd)
            html.append(f"""
            <div class="card terminal-card" style="margin-top: 16px;">
                <div class="terminal-title">{_("Detailed Sensor Data (sensors)")}</div>
                <div class="terminal-text" style="max-height: 500px; overflow: auto; white-space: pre-wrap;">{escaped_cmd}</div>
            </div>
            """)
            
        return "\n".join(html)

    def _render_more_info(self, data: Dict[str, Any]) -> str:
        """Render More Info section with all raw outputs matching GTK."""
        html = []
        
        # Access full data
        full_data = self.data.to_dict()
        
        # Get all data sources just like GTK _show_more_info
        system_data = full_data.get("system", {})
        pci_data = full_data.get("pci", {})
        usb_data = full_data.get("usb", {})
        logs_data = full_data.get("logs", {})
        fstab_data = full_data.get("fstab", {})
        modules_data = full_data.get("modules", {})
        mhwd_data = full_data.get("mhwd", {})
        kernel_data = full_data.get("kernel", {})
        cmdline_data = full_data.get("cmdline", {})
        efi_data = full_data.get("efi", {})
        acpi_data = full_data.get("acpi", {})
        rfkill_data = full_data.get("rfkill", {})
        sdio_data = full_data.get("sdio", {})
        webcam_data = full_data.get("webcam", {})
        
        def add_terminal_block(title: str, content: str, highlight: bool = True):
            if content:
                if highlight:
                    highlighted_content = self._apply_syntax_highlighting(str(content))
                else:
                    highlighted_content = str(content).replace("<", "&lt;").replace(">", "&gt;")
                    
                html.append(f"""
                <div class="card terminal-card" style="margin-bottom: 16px;">
                    <div class="terminal-title">{title}</div>
                    <div class="terminal-text" style="max-height: 400px; overflow: auto; white-space: pre-wrap;">{highlighted_content}</div>
                </div>
                """)
        
        # Package Repositories
        repositories = system_data.get("repositories", "")
        add_terminal_block(_("Package Repositories"), repositories)
        
        # PCI Devices (lspci -nn)
        if isinstance(pci_data, dict):
            pci_devices = pci_data.get("devices", [])
            if pci_devices:
                pci_text = "\n".join(d.get("raw", str(d)) for d in pci_devices if isinstance(d, dict) and d.get("raw"))
                add_terminal_block("lspci -nn", pci_text)
        
        # USB Devices (lsusb)
        if isinstance(usb_data, dict):
            usb_devices = usb_data.get("devices", [])
            if usb_devices:
                usb_text = "\n".join(d.get("raw", str(d)) for d in usb_devices if isinstance(d, dict) and d.get("raw"))
                add_terminal_block("lsusb", usb_text)
        
        # Webcam (v4l2-ctl)
        if isinstance(webcam_data, dict):
            webcams = webcam_data.get("devices", [])
            if webcams:
                v4l2_text = "\n\n".join(w.get("raw", "") for w in webcams if w.get("raw"))
                add_terminal_block("v4l2-ctl --all", v4l2_text)
        
        # SDIO devices (always show)
        sdio_text = ""
        if isinstance(sdio_data, dict):
            sdio_devices = sdio_data.get("devices", [])
            if sdio_devices:
                for dev in sdio_devices:
                    sdio_text += f"Device: {dev.get('name', 'Unknown')}\n"
                    sdio_text += f"  Vendor: {dev.get('vendor', 'Unknown')}\n"
                    sdio_text += f"  Device ID: {dev.get('device', 'Unknown')}\n\n"
            else:
                sdio_text = _("No SDIO devices detected")
        else:
            sdio_text = _("No SDIO devices detected")
        add_terminal_block(_("SDIO"), sdio_text)
        
        # PCI Detailed (lspci -nvv)
        if isinstance(pci_data, dict):
            pci_detailed = pci_data.get("detailed", "")
            add_terminal_block("lspci -nvv", pci_detailed)
        
        # USB Detailed (lsusb -v)
        if isinstance(usb_data, dict):
            usb_detailed = usb_data.get("detailed", "")
            add_terminal_block("lsusb -v", usb_detailed)
        
        # rfkill
        if isinstance(rfkill_data, dict):
            rfkill_raw = rfkill_data.get("raw", "")
            add_terminal_block("rfkill", rfkill_raw)
        
        # /etc/fstab
        if isinstance(fstab_data, dict):
            fstab_raw = fstab_data.get("raw", "")
            add_terminal_block("/etc/fstab", fstab_raw)
        
        # lsmod
        if isinstance(modules_data, dict):
            modules_raw = modules_data.get("raw", "")
            add_terminal_block("lsmod", modules_raw)
        
        # MHWD driver
        if isinstance(mhwd_data, dict):
            mhwd_drivers = mhwd_data.get("installed_drivers", "")
            add_terminal_block(_("Mhwd driver"), mhwd_drivers)
            mhwd_kernels = mhwd_data.get("installed_kernels", "")
            add_terminal_block(_("Mhwd kernel"), mhwd_kernels)
        
        # Cmdline
        if isinstance(cmdline_data, dict):
            cmdline_raw = cmdline_data.get("raw", "")
            add_terminal_block(_("Cmdline"), cmdline_raw)
        
        # EFI Boot Manager
        if isinstance(efi_data, dict) and efi_data.get("available"):
            efi_verbose = efi_data.get("verbose", efi_data.get("basic", ""))
            add_terminal_block("efibootmgr", efi_verbose)
        
        # ACPI interrupts
        if isinstance(acpi_data, dict):
            acpi_interrupts = acpi_data.get("interrupts", [])
            if acpi_interrupts:
                acpi_text = "\n".join(
                    f"{i.get('name', 'Unknown')}: {i.get('count', 0)}"
                    for i in acpi_interrupts
                )
                add_terminal_block(_("ACPI Interrupts"), acpi_text)
        
        # Logs - dmesg errors
        if isinstance(logs_data, dict):
            dmesg = logs_data.get("dmesg_errors", {})
            if isinstance(dmesg, dict) and dmesg.get("raw"):
                add_terminal_block(_("dmesg (errors)"), dmesg.get("raw", ""))
            
            journal = logs_data.get("journal_errors", {})
            if isinstance(journal, dict) and journal.get("raw"):
                add_terminal_block(_("journalctl (errors)"), journal.get("raw", ""))
        
        if not html:
            return self._render_no_data(_("No additional information available"))
        
        return "\n".join(html)

    def _apply_syntax_highlighting(self, text: str) -> str:
        """Apply detailed syntax highlighting to terminal output.
        
        Colors are consistent with GTK Adwaita theme:
        - hl-path (blue): Filesystem paths like /dev/, /etc/, /sys/
        - hl-number (green): IDs, addresses, hex values, numbers with units
        - hl-keyword (orange): Hardware vendors, bus types, device types, mount options
        - hl-comment (gray): Comments, URLs, revision info
        - hl-success (bright green): enabled, UP, OK, active, running
        - hl-warning (yellow): disabled, dormant, suspended, warning
        - hl-error (red): DOWN, FAILED, error, critical
        
        Enhanced highlighting for:
        - fstab: mount options, filesystem types, UUID/LABEL, dump/pass values
        - lsmod: module names, sizes, dependency chains
        """
        import re
        if not text:
            return text
        
        # Escape HTML first
        text = str(text).replace("<", "&lt;").replace(">", "&gt;")
        
        def safe_sub(pattern, repl, source, flags=0):
            """Apply regex only to text outside of HTML tags."""
            parts = re.split(r'(<[^>]+>)', source)
            for i, part in enumerate(parts):
                if not part.startswith('<'):
                    parts[i] = re.sub(pattern, repl, part, flags=flags)
            return "".join(parts)
        
        # Detect content type
        content_type = self._detect_content_type_for_highlight(text)
        
        if content_type == 'fstab':
            return self._apply_fstab_html_highlighting(text, safe_sub)
        elif content_type == 'lsmod':
            return self._apply_lsmod_html_highlighting(text, safe_sub)
        elif content_type == 'dmesg':
            return self._apply_dmesg_html_highlighting(text, safe_sub)
        elif content_type == 'journalctl':
            return self._apply_journalctl_html_highlighting(text, safe_sub)
        elif content_type == 'v4l2':
            return self._apply_v4l2_html_highlighting(text, safe_sub)
        elif content_type == 'lsusb_v':
            return self._apply_lsusb_v_html_highlighting(text, safe_sub)
        elif content_type == 'efibootmgr':
            return self._apply_efibootmgr_html_highlighting(text, safe_sub)
        elif content_type == 'interrupts':
            return self._apply_interrupts_html_highlighting(text, safe_sub)
        elif content_type == 'cmdline':
            return self._apply_cmdline_html_highlighting(text, safe_sub)
        elif content_type == 'lspci':
            return self._apply_lspci_html_highlighting(text, safe_sub)
        else:
            return self._apply_generic_html_highlighting(text, safe_sub)
    
    def _detect_content_type_for_highlight(self, text: str) -> str:
        """Detect the type of content for specialized highlighting."""
        import re
        lines = text.strip().split('\n')
        
        # Check for lsmod
        for line in lines[:3]:
            if 'Module' in line and 'Size' in line and 'Used' in line:
                return 'lsmod'
        
        # Check for fstab
        for line in lines[:10]:
            if 'UUID=' in line or 'LABEL=' in line:
                if any(fs in line for fs in ['ext4', 'btrfs', 'xfs', 'vfat', 'ntfs', 'swap', 'tmpfs']):
                    return 'fstab'
            if line.strip().startswith('#') and 'fstab' in line.lower():
                return 'fstab'
        
        # Check for lspci
        for line in lines[:3]:
            if re.match(r'^[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F]', line):
                return 'lspci'
        
        # Check for lsusb -v
        for line in lines[:10]:
            if 'Device Descriptor:' in line or 'bDescriptorType' in line:
                return 'lsusb_v'
        
        # Check for v4l2-ctl
        for line in lines[:5]:
            if 'Driver Info:' in line or 'Driver name' in line or 'v4l2' in line.lower():
                return 'v4l2'
        
        # Check for efibootmgr
        for line in lines[:5]:
            if 'BootCurrent:' in line or 'BootOrder:' in line or line.startswith('Boot0'):
                return 'efibootmgr'
        
        # Check for ACPI interrupts (/proc/interrupts)
        if any('CPU' in line for line in lines[:2]):
            if any('IO-APIC' in line or 'PCI-MSI' in line for line in lines[:10]):
                return 'interrupts'
        
        # Check for journalctl
        for line in lines[:5]:
            if re.match(r'^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\w+', line):
                return 'journalctl'
        
        # Check for cmdline (single line with boot params)
        if len(lines) == 1 and ('BOOT_IMAGE=' in text or 'root=' in text):
            return 'cmdline'
        
        # Check for dmesg
        for line in lines[:5]:
            if re.match(r'^\[\s*[\d\+\.,]+\s*\]', line) or re.match(r'^\[[a-z]{3}\d{2}\s', line):
                return 'dmesg'
        
        return 'generic'
    
    def _apply_fstab_html_highlighting(self, text: str, safe_sub) -> str:
        """Apply fstab-specific syntax highlighting for HTML."""
        import re
        
        # Mount options sorted by length (longest first to prevent partial matches)
        mount_opts = [
            'x-systemd.idle-timeout', 'x-systemd.automount',
            'compress-force', 'nospace_cache', 'space_cache', 'skip_balance',
            'flushoncommit', 'metadata_ratio', 'autodefrag', 'noautodefrag',
            'nodiratime', 'strictatime', 'credentials', 'clear_cache',
            'subvolid', 'relatime', 'noatime', 'defaults', 'compress',
            'nodiscard', 'nobarrier', 'lazytime', 'recovery', 'degraded',
            'dirsync', 'barrier', 'discard', 'nofail', 'subvol',
            'noexec', 'nosuid', 'noauto', 'nouser', 'errors', 'umask',
            'dmask', 'fmask', 'nodev', 'owner', 'group', 'users',
            'async', 'noacl', 'exec', 'suid', 'user', 'auto', 'sync',
            'mode', 'vers', 'zstd', 'lzo', 'zlib', 'uid', 'gid',
            'acl', 'sec', 'ssd', 'nossd', 'rw', 'ro'
        ]
        
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Comment lines - entire line in gray
            if stripped.startswith('#'):
                highlighted_lines.append(f'<span class="hl-comment">{line}</span>')
                continue
            
            result = line
            
            # UUID= with value (standard format)
            result = safe_sub(
                r'(UUID=)([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})',
                r'<span class="hl-keyword">\1</span><span class="hl-number">\2</span>',
                result
            )
            
            # UUID= short format (vfat)
            result = safe_sub(
                r'(UUID=)([0-9A-Fa-f]{4}-[0-9A-Fa-f]{4})',
                r'<span class="hl-keyword">\1</span><span class="hl-number">\2</span>',
                result
            )
            
            # LABEL= with value
            result = safe_sub(
                r'(LABEL=)([^\s]+)',
                r'<span class="hl-keyword">\1</span><span class="hl-number">\2</span>',
                result
            )
            
            # Paths (including just /)
            result = safe_sub(r'(?<=\s)(\/[^\s,]*)', r'<span class="hl-path">\1</span>', result)
            
            # Filesystem types
            result = safe_sub(
                r'(?<=\s)(ext4|ext3|ext2|btrfs|xfs|ntfs|ntfs3|vfat|fat32|exfat|swap|tmpfs|proc|sysfs|cifs|nfs|nfs4|overlay|squashfs)(?=\s)',
                r'<span class="hl-keyword">\1</span>',
                result
            )
            
            # Mount options (sorted by length)
            def make_opt_repl(m):
                prefix = m.group(0)[0] if m.group(0)[0] in ", " else ""
                opt_span = f'<span class="hl-keyword">{m.group(1)}</span>'
                val_span = f'<span class="hl-number">{m.group(2)}</span>' if m.group(2) else ""
                return prefix + opt_span + val_span
            
            for opt in mount_opts:
                opt_escaped = re.escape(opt)
                # Option with value
                result = safe_sub(
                    f'(?:^|,|\\s)({opt_escaped})(=[^,\\s]*)?(?=,|\\s|$)',
                    make_opt_repl,
                    result
                )
            
            # Dump and pass fields at end of line
            result = safe_sub(
                r'\s+(\d)\s+(\d)\s*$',
                r' <span class="hl-number">\1</span> <span class="hl-number">\2</span>',
                result
            )
            
            highlighted_lines.append(result)
        
        return '\n'.join(highlighted_lines)
    
    def _apply_lsmod_html_highlighting(self, text: str, safe_sub) -> str:
        """Apply lsmod-specific syntax highlighting for HTML."""
        import re
        
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Header line
            if stripped.startswith('Module') and 'Size' in stripped and 'Used' in stripped:
                highlighted_lines.append(f'<span class="hl-comment">{line}</span>')
                continue
            
            # Parse lsmod line: module_name    size  used_count  dependencies
            parts = line.split()
            if len(parts) >= 3:
                try:
                    int(parts[1])  # size
                    int(parts[2])  # used count
                    
                    result = line
                    
                    # Module name (keyword)
                    result = safe_sub(
                        f'^({re.escape(parts[0])})',
                        r'<span class="hl-keyword">\1</span>',
                        result
                    )
                    
                    # Size (number)
                    result = safe_sub(
                        f'\\s({re.escape(parts[1])})\\s',
                        r' <span class="hl-number">\1</span> ',
                        result
                    )
                    
                    # Used count (number)
                    result = safe_sub(
                        f'\\s({re.escape(parts[2])})(\\s|$)',
                        r' <span class="hl-number">\1</span>\2',
                        result
                    )
                    
                    # Dependencies (path color)
                    if len(parts) > 3:
                        deps = parts[3]
                        for dep in deps.rstrip(',').split(','):
                            if dep:
                                result = safe_sub(
                                    f'({re.escape(dep)})',
                                    r'<span class="hl-path">\1</span>',
                                    result
                                )
                    
                    highlighted_lines.append(result)
                    continue
                except (ValueError, IndexError):
                    pass
            
            highlighted_lines.append(line)
        
        return '\n'.join(highlighted_lines)
    
    def _apply_lspci_html_highlighting(self, text: str, safe_sub) -> str:
        """Apply lspci-specific syntax highlighting for HTML."""
        import re
        
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            result = line
            
            # PCI address at start (00:00.0)
            result = safe_sub(r'^([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F])', r'<span class="hl-number">\1</span>', result)
            
            # Device class in brackets [0600]
            result = safe_sub(r'(\[[0-9a-fA-F]{4}\])', r'<span class="hl-comment">\1</span>', result)
            
            # Vendor:Device ID [8086:0c00]
            result = safe_sub(r'(\[[0-9a-fA-F]{4}:[0-9a-fA-F]{4}\])', r'<span class="hl-number">\1</span>', result)
            
            # Revision (rev xx)
            result = safe_sub(r'(\(rev\s+[0-9a-fA-F]+\))', r'<span class="hl-comment">\1</span>', result)
            
            # Device types
            device_types = r'\b(Host bridge|PCI bridge|USB controller|VGA compatible controller|Audio device|SATA controller|ISA bridge|SMBus|Communication controller|Ethernet controller|Non-Volatile memory controller|Network controller|Serial bus controller|Signal processing controller|System peripheral|Memory controller|Encryption controller)\b'
            result = safe_sub(device_types, r'<span class="hl-keyword">\1</span>', result)
            
            # Vendor names
            vendors = r'\b(Intel|NVIDIA|AMD|Realtek|Samsung|Kingston|Broadcom|Qualcomm|Marvell|ASMedia|JMicron|VIA|SanDisk|Western Digital|Seagate|Micron|SK hynix|Crucial|Corsair|ASUS|Gigabyte|MSI)\b'
            result = safe_sub(vendors, r'<span class="hl-keyword">\1</span>', result, flags=re.IGNORECASE)
            
            highlighted_lines.append(result)
        
        return '\n'.join(highlighted_lines)
    
    def _apply_dmesg_html_highlighting(self, text: str, safe_sub) -> str:
        """Apply dmesg-specific syntax highlighting for HTML."""
        import re
        
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            result = line
            
            # Timestamp at start
            result = safe_sub(r'^(\[\s*[\d\+\.,]+\s*\])', r'<span class="hl-comment">\1</span>', result)
            result = safe_sub(r'^(\[[a-z]{3}\d{2}\s+[\d:]+\])', r'<span class="hl-comment">\1</span>', result, flags=re.IGNORECASE)
            
            # Error keywords
            result = safe_sub(r'\b(error|fail|failed|failure|fatal|critical|panic|oops|bug|corrupt|invalid)\b', r'<span class="hl-error">\1</span>', result, flags=re.IGNORECASE)
            
            # Warning keywords  
            result = safe_sub(r'\b(warning|warn|deprecated|timeout|retry|retrying)\b', r'<span class="hl-warning">\1</span>', result, flags=re.IGNORECASE)
            
            # Success/state keywords
            result = safe_sub(r'\b(enabled|initialized|registered|loaded|started|ready|connected|authenticated|associated)\b', r'<span class="hl-success">\1</span>', result, flags=re.IGNORECASE)
            
            # Network interfaces
            result = safe_sub(r'\b(eth\d+|wlan\d+|wlp\d+s\d+|enp\d+s\d+|lo)\b', r'<span class="hl-path">\1</span>', result)
            
            # Kernel modules/drivers
            result = safe_sub(r'\b(nvidia|amdgpu|i915|nouveau|radeon|iwlwifi|iwlmvm|r8169|e1000e|ath9k|ath10k|btusb|bluetooth|usb|pci|acpi|drm)\b', r'<span class="hl-keyword">\1</span>', result, flags=re.IGNORECASE)
            
            highlighted_lines.append(result)
        
        return '\n'.join(highlighted_lines)
    
    def _apply_v4l2_html_highlighting(self, text: str, safe_sub) -> str:
        """Apply v4l2-ctl-specific syntax highlighting for HTML."""
        import re
        
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            result = line
            
            # Key: value pattern
            match = re.match(r'^(\s*)(\w[\w\s/]+)(\s*:\s*)(.*)$', line)
            if match:
                result = f'{match.group(1)}<span class="hl-keyword">{match.group(2)}</span>{match.group(3)}<span class="hl-number">{match.group(4)}</span>'
            
            # Capabilities/Flags in indented list
            result = safe_sub(r'^(\s+)(Video Capture|Metadata Capture|Streaming|Extended Pix Format|Device Capabilities)', r'\1<span class="hl-keyword">\2</span>', result)
            
            # Device paths
            result = safe_sub(r'(usb-[^\s,]+)', r'<span class="hl-path">\1</span>', result)
            
            # Hex values
            result = safe_sub(r'\b(0x[0-9a-fA-F]+)\b', r'<span class="hl-number">\1</span>', result)
            
            # Format/codec names 'MJPG'
            result = safe_sub(r"'([A-Z0-9]{4})'", r"'<span class=\"hl-keyword\">\1</span>'", result)
            
            highlighted_lines.append(result)
        
        return '\n'.join(highlighted_lines)
    
    def _apply_lsusb_v_html_highlighting(self, text: str, safe_sub) -> str:
        """Apply lsusb -v specific syntax highlighting for HTML."""
        import re
        
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            result = line
            
            # Bus/Device header line
            if line.startswith('Bus '):
                result = safe_sub(r'(Bus\s+)(\d+)', r'<span class="hl-keyword">\1</span><span class="hl-number">\2</span>', result)
                result = safe_sub(r'(Device\s+)(\d+)', r'<span class="hl-keyword">\1</span><span class="hl-number">\2</span>', result)
                result = safe_sub(r'(ID\s+)([0-9a-fA-F]{4}:[0-9a-fA-F]{4})', r'\1<span class="hl-number">\2</span>', result)
            else:
                # Descriptor field names
                result = safe_sub(r'^(\s+)(b\w+|i\w+|wMaxPacketSize|bmAttributes)', r'\1<span class="hl-keyword">\2</span>', result)
                
                # Hex values
                result = safe_sub(r'\b(0x[0-9a-fA-F]+)\b', r'<span class="hl-number">\1</span>', result)
                
                # Device class info
                result = safe_sub(r'\b(Hub|Human Interface Device|Mass Storage|Video|Audio|Wireless Controller|Vendor Specific)\b', r'<span class="hl-keyword">\1</span>', result)
            
            highlighted_lines.append(result)
        
        return '\n'.join(highlighted_lines)
    
    def _apply_efibootmgr_html_highlighting(self, text: str, safe_sub) -> str:
        """Apply efibootmgr-specific syntax highlighting for HTML."""
        import re
        
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            result = line
            
            # Boot entry lines
            if line.startswith('Boot'):
                # Boot number
                result = safe_sub(r'^(Boot)([0-9A-Fa-f]{4})', r'<span class="hl-keyword">\1</span><span class="hl-number">\2</span>', result)
                # Active marker *
                result = safe_sub(r'(Boot[0-9A-Fa-f]{4})(\*)', r'\1<span class="hl-success">\2</span>', result)
                # OS/partition name - highlight prominently with bold blue (after Boot0000* and before HD( or BBS( or tabs)
                result = safe_sub(r'(\*|\d{4})\s+([^\t]+?)(\t|\s{2,}|HD\(|BBS\(|$)', 
                                  r'\1 <span class="hl-osname">\2</span>\3', result)
                # HD(...) path info
                result = safe_sub(r'(HD\([^)]+\))', r'<span class="hl-comment">\1</span>', result)
                # EFI file path (\EFI\...\*.efi)
                result = safe_sub(r'(/|\\)(EFI[^\s<]*\.efi)', r'<span class="hl-path">\1\2</span>', result, flags=re.IGNORECASE)
                # BBS(...) for UEFI devices
                result = safe_sub(r'(BBS\([^)]+\))', r'<span class="hl-comment">\1</span>', result)
            else:
                # Key: Value lines
                result = safe_sub(r'^(BootCurrent|Timeout|BootOrder)(:?\s*)(.*)$', r'<span class="hl-keyword">\1</span>\2<span class="hl-number">\3</span>', result)
            
            highlighted_lines.append(result)
        
        return '\n'.join(highlighted_lines)
    
    def _apply_interrupts_html_highlighting(self, text: str, safe_sub) -> str:
        """Apply /proc/interrupts-specific syntax highlighting for HTML."""
        import re
        
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            # Header line with CPUs
            if 'CPU' in line and line.strip().startswith('CPU'):
                highlighted_lines.append(f'<span class="hl-comment">{line}</span>')
                continue
            
            result = line
            
            # IRQ number at start
            result = safe_sub(r'^(\s*)(\d+)(:)', r'\1<span class="hl-number">\2</span>\3', result)
            
            # Controller types
            result = safe_sub(r'\b(IO-APIC|PCI-MSI|DMAR-MSI|IR-PCI-MSI|XT-PIC|NMI|LOC|SPU|PMI|IWI|RTR|RES|CAL|TLB)\b', r'<span class="hl-keyword">\1</span>', result)
            
            # Trigger types
            result = safe_sub(r'\b(edge|fasteoi|level)\b', r'<span class="hl-path">\1</span>', result)
            
            # Device names at end
            result = safe_sub(r'(xhci_hcd|i915|nvme\S*|ahci\S*|snd_\S+|i8042|rtc0|acpi|timer|iwlwifi|eth\d+|wlan\d+)', r'<span class="hl-keyword">\1</span>', result)
            
            highlighted_lines.append(result)
        
        return '\n'.join(highlighted_lines)
    
    def _apply_journalctl_html_highlighting(self, text: str, safe_sub) -> str:
        """Apply journalctl-specific syntax highlighting for HTML."""
        import re
        
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            result = line
            
            # Timestamp at start
            result = safe_sub(r'^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', r'<span class="hl-comment">\1</span>', result)
            
            # Hostname (after timestamp)
            result = safe_sub(r'^<span class="hl-comment">([^<]+)</span>\s+(\S+)', r'<span class="hl-comment">\1</span> <span class="hl-path">\2</span>', result)
            
            # Process name with PID
            result = safe_sub(r'(\w+)\[(\d+)\]:', r'<span class="hl-keyword">\1</span>[<span class="hl-number">\2</span>]:', result)
            
            # Log levels/tags
            result = safe_sub(r'<(info|notice|debug)>', r'<<span class="hl-path">\1</span>>', result, flags=re.IGNORECASE)
            result = safe_sub(r'<(warn|warning)>', r'<<span class="hl-warning">\1</span>>', result, flags=re.IGNORECASE)
            result = safe_sub(r'<(err|error|crit|critical|alert|emerg)>', r'<<span class="hl-error">\1</span>>', result, flags=re.IGNORECASE)
            
            # Error keywords
            result = safe_sub(r'\b(error|failed|failure|fail)\b', r'<span class="hl-error">\1</span>', result, flags=re.IGNORECASE)
            
            # Success keywords
            result = safe_sub(r'\b(started|finished|success|connected|enabled)\b', r'<span class="hl-success">\1</span>', result, flags=re.IGNORECASE)
            
            # Service names
            result = safe_sub(r'(\S+\.service)', r'<span class="hl-keyword">\1</span>', result)
            
            highlighted_lines.append(result)
        
        return '\n'.join(highlighted_lines)
    
    def _apply_cmdline_html_highlighting(self, text: str, safe_sub) -> str:
        """Apply kernel cmdline-specific syntax highlighting for HTML."""
        import re
        
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            result = line
            
            # BOOT_IMAGE=
            result = safe_sub(r'(BOOT_IMAGE=)([^\s]+)', r'<span class="hl-keyword">\1</span><span class="hl-path">\2</span>', result)
            
            # root= with UUID or path
            result = safe_sub(r'(root=)(UUID=)?([^\s]+)', r'<span class="hl-keyword">\1</span><span class="hl-keyword">\2</span><span class="hl-number">\3</span>', result)
            
            # rootflags=
            result = safe_sub(r'(rootflags=)([^\s]+)', r'<span class="hl-keyword">\1</span><span class="hl-number">\2</span>', result)
            
            # Boolean params
            result = safe_sub(r'(?<=\s)(quiet|splash|ro|rw)(?=\s|$)', r'<span class="hl-keyword">\1</span>', result)
            
            # Key=value params (generic)
            result = safe_sub(r'(?<=\s)(\w+\.?\w*)=([^\s]+)', r'<span class="hl-keyword">\1</span>=<span class="hl-number">\2</span>', result)
            
            highlighted_lines.append(result)
        
        return '\n'.join(highlighted_lines)
    
    def _apply_generic_html_highlighting(self, text: str, safe_sub) -> str:
        """Apply generic syntax highlighting for HTML."""
        import re
        
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            # Check if line is a comment (starts with #)
            stripped = line.strip()
            if stripped.startswith('#'):
                highlighted_lines.append(f'<span class="hl-comment">{line}</span>')
                continue
            
            result = line
            
            # Paths (blue)
            result = safe_sub(r'(/dev/\S+|/etc/\S+|/sys/\S+|/proc/\S+|/var/\S+|/boot/\S+|/home/\S+|/mnt/\S+|/media/\S+|/run/\S+)', r'<span class="hl-path">\1</span>', result)
            result = safe_sub(r'(/[\w/\-\.]+)', r'<span class="hl-path">\1</span>', result)
            
            # Comments/URLs (gray)
            result = safe_sub(r'(https?://\S+)', r'<span class="hl-comment">\1</span>', result)
            result = safe_sub(r'(\(rev\s+[0-9a-fA-F]+\))', r'<span class="hl-comment">\1</span>', result)
            
            # Identifiers / Addresses (green)
            result = safe_sub(r'(\[[0-9a-fA-F]{4}:[0-9a-fA-F]{4}\])', r'<span class="hl-number">\1</span>', result)
            result = safe_sub(r'\b([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F])\b', r'<span class="hl-number">\1</span>', result)
            result = safe_sub(r'(ID\s+[0-9a-fA-F]{4}:[0-9a-fA-F]{4})', r'<span class="hl-number">\1</span>', result)
            result = safe_sub(r'\b([0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){2,})\b', r'<span class="hl-number">\1</span>', result)
            result = safe_sub(r'\b(0x[0-9a-fA-F]+)\b', r'<span class="hl-number">\1</span>', result)
            
            # UUIDs
            result = safe_sub(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})', r'<span class="hl-number">\1</span>', result)
            
            # Numbers with units
            result = safe_sub(r'\b(\d+[KMGT]i?B)\b', r'<span class="hl-number">\1</span>', result, flags=re.IGNORECASE)
            result = safe_sub(r'\b(\d+\.?\d*)\s*(Hz|kHz|MHz|GHz)\b', r'<span class="hl-number">\1 \2</span>', result, flags=re.IGNORECASE)
            result = safe_sub(r'\b([+-]?\d+\.?\d*)\s*(°C|C)\b', r'<span class="hl-number">\1\2</span>', result)
            result = safe_sub(r'\b(\d+\.?\d*)\s*(V|W|A)\b', r'<span class="hl-number">\1 \2</span>', result)
            result = safe_sub(r'\b(\d+)\s*RPM\b', r'<span class="hl-number">\1 RPM</span>', result, flags=re.IGNORECASE)
            
            # Status states
            result = safe_sub(r'\b(enabled|UP|OK|PASSED|active|running|idle|mounted|connected|unblocked|authenticated|associated)\b', r'<span class="hl-success">\1</span>', result, flags=re.IGNORECASE)
            result = safe_sub(r'\b(disabled|dormant|suspended|warning|warn|deprecated|unmounted|disconnected|blocked)\b', r'<span class="hl-warning">\1</span>', result, flags=re.IGNORECASE)
            result = safe_sub(r'\b(DOWN|FAILED|error|fail|failed|fatal|critical|inactive|missing|unavailable)\b', r'<span class="hl-error">\1</span>', result, flags=re.IGNORECASE)
            
            # Keywords (orange)
            result = safe_sub(r'\b(Host|bridge|controller|Intel|AMD|NVIDIA|Realtek|Samsung|Kingston|USB|PCI|SATA|NVMe|ACPI|GPU|CPU|RAM|SSD|HDD|AHCI|Bluetooth|Linux)\b', 
                           r'<span class="hl-keyword">\1</span>', result)
            result = safe_sub(r'(Bus\s+\d+)', r'<span class="hl-keyword">\1</span>', result)
            result = safe_sub(r'(Device\s+\d+:?)', r'<span class="hl-keyword">\1</span>', result)
            
            highlighted_lines.append(result)
        
        return '\n'.join(highlighted_lines)

    def _render_generic(self, data: Dict[str, Any]) -> str:
        """Generic renderer for NotImplemented sections."""
        return f"""
        <div class="card">
            <div class="dim-label">Section implementation pending...</div>
            <pre style="font-size: 0.8em; overflow: auto;">{json.dumps(data, indent=2)[:500]}...</pre>
        </div>
        """

    def _render_no_data(self, message: str) -> str:
        """Render empty state."""
        return f'<div class="card"><div class="dim-label" style="text-align: center; padding: 20px;">{message}</div></div>'

    def _create_stat_card(self, icon: str, value: str, label: str) -> str:
        icon_html = f'<div style="font-size: 24px; margin-bottom: 4px;">{icon}</div>' if icon else ""
        # Auto-translate the label for i18n
        translated_label = _(label)
        return f"""
        <div class="card stat-card" style="flex: 1; text-align: center;">
            {icon_html}
            <div class="heading" style="font-size: 1.2em;">{value}</div>
            <div class="caption dim-label">{translated_label}</div>
        </div>
        """
    def _create_info_row(self, label: str, value: str) -> str:
        if not value: return ""
        # Auto-translate the label for i18n
        translated_label = _(label)
        return f"""
        <div class="info-row" style="display: flex; padding: 4px 0; border-bottom: 1px solid var(--borders);">
            <div class="dim-label" style="width: 120px;">{translated_label}</div>
            <div style="flex: 1; text-align: right;">{value}</div>
        </div>
        """

    def _create_spec_item(self, label: str, value: str) -> str:
        if not value: return ""
        # Auto-translate the label for i18n
        translated_label = _(label)
        return f"""
        <div class="box-vertical" style="margin-bottom: 8px;">
            <div class="caption dim-label">{translated_label}</div>
            <div class="heading">{value}</div>
        </div>
        """

    def _create_info_link(self, chip_id: str, dev_type: str = 'pci') -> str:
        """
        Create an HTML info link to linux-hardware.org.
        
        Args:
            chip_id: Device chip ID in format "vendor_id:device_id"
            dev_type: Device type - 'pci' or 'usb'
        
        Returns:
            HTML anchor tag styled as info button, or empty string if invalid.
        """
        if not chip_id or ':' not in chip_id:
            return ""
        
        try:
            vendor_id, device_id = chip_id.split(':', 1)
            url = f"https://linux-hardware.org/?id={dev_type}:{vendor_id}-{device_id}"
            return f'<a href="{url}" class="info-btn" target="_blank" title="View on Linux Hardware Database">info</a>'
        except ValueError:
            return ""
