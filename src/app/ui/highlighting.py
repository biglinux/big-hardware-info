"""
Terminal output syntax highlighting for Hardware Reporter.

Applies syntax coloring to terminal/log output text using GTK TextBuffer tags.
Colors are consistent with Adwaita theme and used in both GTK views and HTML export.
"""

import re
from typing import Optional

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


# Adwaita theme colors for consistency
COLORS = {
    "path": "#3584e4",      # Blue - filesystem paths
    "number": "#26a269",    # Green - IDs, addresses, numbers
    "keyword": "#ff7800",   # Orange - keywords, vendors
    "comment": "#8d93a8",   # Gray - comments, URLs
    "success": "#33d17a",   # Bright green - enabled, UP, OK
    "warning": "#e5a50a",   # Yellow - warnings
    "error": "#e01b24",     # Red - errors, DOWN
    "osname": "#62a0ea",    # Light blue - OS names
}


def setup_tags(buffer: Gtk.TextBuffer) -> None:
    """Create text tags for syntax highlighting."""
    tag_table = buffer.get_tag_table()
    
    tags = [
        ("path", {"foreground": COLORS["path"]}),
        ("number", {"foreground": COLORS["number"]}),
        ("keyword", {"foreground": COLORS["keyword"], "weight": 600}),
        ("comment", {"foreground": COLORS["comment"]}),
        ("success", {"foreground": COLORS["success"]}),
        ("warning", {"foreground": COLORS["warning"]}),
        ("error", {"foreground": COLORS["error"], "weight": 600}),
        ("osname", {"foreground": COLORS["osname"], "weight": 700}),
    ]
    
    for name, props in tags:
        tag = Gtk.TextTag(name=name)
        for prop, value in props.items():
            tag.set_property(prop, value)
        tag_table.add(tag)


def detect_content_type(text: str) -> str:
    """Detect the type of content for specialized highlighting."""
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


def apply_highlighting(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply syntax highlighting to terminal text."""
    setup_tags(buffer)
    buffer.set_text(text)
    
    content_type = detect_content_type(text)
    
    highlighters = {
        'fstab': _highlight_fstab,
        'lsmod': _highlight_lsmod,
        'dmesg': _highlight_dmesg,
        'journalctl': _highlight_journalctl,
        'v4l2': _highlight_v4l2,
        'lsusb_v': _highlight_lsusb_v,
        'efibootmgr': _highlight_efibootmgr,
        'interrupts': _highlight_interrupts,
        'cmdline': _highlight_cmdline,
        'lspci': _highlight_lspci,
    }
    
    highlighter = highlighters.get(content_type, _highlight_generic)
    highlighter(buffer, text)


def _apply_pattern(buffer: Gtk.TextBuffer, text: str, pattern: str, tag: str, 
                   offset: int = 0, flags: int = 0) -> None:
    """Helper to apply a regex pattern with a tag."""
    for match in re.finditer(pattern, text, flags):
        start = buffer.get_iter_at_offset(offset + match.start())
        end = buffer.get_iter_at_offset(offset + match.end())
        buffer.apply_tag_by_name(tag, start, end)


def _apply_group(buffer: Gtk.TextBuffer, match, group: int, tag: str, offset: int = 0) -> None:
    """Helper to apply tag to a regex match group."""
    if match.group(group):
        start = buffer.get_iter_at_offset(offset + match.start(group))
        end = buffer.get_iter_at_offset(offset + match.end(group))
        buffer.apply_tag_by_name(tag, start, end)


def _highlight_fstab(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply fstab-specific syntax highlighting."""
    lines = text.split('\n')
    offset = 0
    
    mount_opts = [
        'x-systemd.idle-timeout', 'x-systemd.automount', 'compress-force',
        'nospace_cache', 'space_cache', 'skip_balance', 'flushoncommit',
        'metadata_ratio', 'autodefrag', 'noautodefrag', 'nodiratime',
        'strictatime', 'credentials', 'clear_cache', 'subvolid', 'relatime',
        'noatime', 'defaults', 'compress', 'nodiscard', 'nobarrier', 'lazytime',
        'recovery', 'degraded', 'dirsync', 'barrier', 'discard', 'nofail',
        'subvol', 'noexec', 'nosuid', 'noauto', 'nouser', 'errors', 'umask',
        'dmask', 'fmask', 'nodev', 'owner', 'group', 'users', 'async', 'noacl',
        'exec', 'suid', 'user', 'auto', 'sync', 'mode', 'vers', 'zstd', 'lzo',
        'zlib', 'uid', 'gid', 'acl', 'sec', 'ssd', 'nossd', 'rw', 'ro'
    ]
    
    for line in lines:
        stripped = line.strip()
        line_end = offset + len(line)
        
        if stripped.startswith('#'):
            start = buffer.get_iter_at_offset(offset)
            end = buffer.get_iter_at_offset(line_end)
            buffer.apply_tag_by_name("comment", start, end)
            offset = line_end + 1
            continue
        
        # UUID and LABEL
        for match in re.finditer(r'(UUID=)([0-9a-fA-F-]+)', line):
            _apply_group(buffer, match, 1, "keyword", offset)
            _apply_group(buffer, match, 2, "number", offset)
        
        for match in re.finditer(r'(LABEL=)([^\s]+)', line):
            _apply_group(buffer, match, 1, "keyword", offset)
            _apply_group(buffer, match, 2, "number", offset)
        
        # Paths
        _apply_pattern(buffer, line, r'(?<=\s)(\/[^\s,]*)', "path", offset)
        
        # Filesystem types
        _apply_pattern(buffer, line, r'(?<=\s)(ext4|ext3|ext2|btrfs|xfs|ntfs|ntfs3|vfat|fat32|exfat|swap|tmpfs|proc|sysfs|cifs|nfs|nfs4|overlay|squashfs)(?=\s)', "keyword", offset)
        
        # Mount options
        for opt in mount_opts:
            opt_escaped = re.escape(opt)
            for match in re.finditer(f'(?:^|,|\\s)({opt_escaped})(=[^,\\s]*)?(?=,|\\s|$)', line):
                _apply_group(buffer, match, 1, "keyword", offset)
                if match.group(2):
                    _apply_group(buffer, match, 2, "number", offset)
        
        # Dump and pass fields
        for match in re.finditer(r'\s+(\d)\s+(\d)\s*$', line):
            _apply_group(buffer, match, 1, "number", offset)
            _apply_group(buffer, match, 2, "number", offset)
        
        offset = line_end + 1


def _highlight_lsmod(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply lsmod-specific syntax highlighting."""
    lines = text.split('\n')
    offset = 0
    
    for line in lines:
        stripped = line.strip()
        line_end = offset + len(line)
        
        if stripped.startswith('Module') and 'Size' in stripped and 'Used' in stripped:
            start = buffer.get_iter_at_offset(offset)
            end = buffer.get_iter_at_offset(line_end)
            buffer.apply_tag_by_name("comment", start, end)
            offset = line_end + 1
            continue
        
        parts = line.split()
        if len(parts) >= 3:
            try:
                int(parts[1])
                int(parts[2])
                
                # Module name
                mod_start = line.find(parts[0])
                if mod_start >= 0:
                    start = buffer.get_iter_at_offset(offset + mod_start)
                    end = buffer.get_iter_at_offset(offset + mod_start + len(parts[0]))
                    buffer.apply_tag_by_name("keyword", start, end)
                
                # Size
                size_start = line.find(parts[1], mod_start + len(parts[0]))
                if size_start >= 0:
                    start = buffer.get_iter_at_offset(offset + size_start)
                    end = buffer.get_iter_at_offset(offset + size_start + len(parts[1]))
                    buffer.apply_tag_by_name("number", start, end)
                
                # Count
                count_start = line.find(parts[2], size_start + len(parts[1]))
                if count_start >= 0:
                    start = buffer.get_iter_at_offset(offset + count_start)
                    end = buffer.get_iter_at_offset(offset + count_start + len(parts[2]))
                    buffer.apply_tag_by_name("number", start, end)
                
                # Dependencies
                if len(parts) > 3:
                    deps_start = line.find(parts[3], count_start + len(parts[2]))
                    if deps_start >= 0:
                        dep_offset = deps_start
                        for dep in parts[3].split(','):
                            dep_pos = line.find(dep, dep_offset)
                            if dep_pos >= 0:
                                start = buffer.get_iter_at_offset(offset + dep_pos)
                                end = buffer.get_iter_at_offset(offset + dep_pos + len(dep))
                                buffer.apply_tag_by_name("path", start, end)
                                dep_offset = dep_pos + len(dep)
            except (ValueError, IndexError):
                pass
        
        offset = line_end + 1


def _highlight_lspci(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply lspci-specific syntax highlighting."""
    lines = text.split('\n')
    offset = 0
    
    device_types = r'\b(Host bridge|PCI bridge|USB controller|VGA compatible controller|Audio device|SATA controller|ISA bridge|SMBus|Communication controller|Ethernet controller|Non-Volatile memory controller|Network controller|Serial bus controller|Signal processing controller|System peripheral|Memory controller|Encryption controller)\b'
    vendors = r'\b(Intel|NVIDIA|AMD|Realtek|Samsung|Kingston|Broadcom|Qualcomm|Marvell|ASMedia|JMicron|VIA|SanDisk|Western Digital|Seagate|Micron|SK hynix|Crucial|Corsair|ASUS|Gigabyte|MSI)\b'
    
    for line in lines:
        line_end = offset + len(line)
        
        _apply_pattern(buffer, line, r'^([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F])', "number", offset)
        _apply_pattern(buffer, line, r'(\[[0-9a-fA-F]{4}\])', "comment", offset)
        _apply_pattern(buffer, line, r'(\[[0-9a-fA-F]{4}:[0-9a-fA-F]{4}\])', "number", offset)
        _apply_pattern(buffer, line, r'(\(rev\s+[0-9a-fA-F]+\))', "comment", offset)
        _apply_pattern(buffer, line, device_types, "keyword", offset)
        _apply_pattern(buffer, line, vendors, "keyword", offset, re.IGNORECASE)
        
        offset = line_end + 1


def _highlight_dmesg(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply dmesg-specific syntax highlighting."""
    lines = text.split('\n')
    offset = 0
    
    for line in lines:
        line_end = offset + len(line)
        
        # Timestamps
        _apply_pattern(buffer, line, r'^(\[\s*[\d\+\.,]+\s*\])', "comment", offset)
        _apply_pattern(buffer, line, r'^(\[[a-z]{3}\d{2}\s+[\d:]+\])', "comment", offset, re.IGNORECASE)
        
        # Error/warning/success keywords
        _apply_pattern(buffer, line, r'\b(error|fail|failed|failure|fatal|critical|panic|oops|bug|corrupt|invalid)\b', "error", offset, re.IGNORECASE)
        _apply_pattern(buffer, line, r'\b(warning|warn|deprecated|timeout|retry|retrying)\b', "warning", offset, re.IGNORECASE)
        _apply_pattern(buffer, line, r'\b(enabled|initialized|registered|loaded|started|ready|connected|authenticated|associated)\b', "success", offset, re.IGNORECASE)
        
        # Network interfaces and drivers
        _apply_pattern(buffer, line, r'\b(eth\d+|wlan\d+|wlp\d+s\d+|enp\d+s\d+|lo)\b', "path", offset)
        _apply_pattern(buffer, line, r'\b(nvidia|amdgpu|i915|nouveau|radeon|iwlwifi|iwlmvm|r8169|e1000e|ath9k|ath10k|btusb|bluetooth|usb|pci|acpi|drm)\b', "keyword", offset, re.IGNORECASE)
        
        offset = line_end + 1


def _highlight_v4l2(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply v4l2-ctl-specific syntax highlighting."""
    lines = text.split('\n')
    offset = 0
    
    for line in lines:
        line_end = offset + len(line)
        
        match = re.match(r'^(\s*)(\w[\w\s/]+)(\s*:\s*)(.*)$', line)
        if match:
            _apply_group(buffer, match, 2, "keyword", offset)
            if match.group(4):
                _apply_group(buffer, match, 4, "number", offset)
        
        _apply_pattern(buffer, line, r'^(\s+)(Video Capture|Metadata Capture|Streaming|Extended Pix Format|Device Capabilities)', "keyword", offset)
        _apply_pattern(buffer, line, r'(usb-[^\s,]+)', "path", offset)
        _apply_pattern(buffer, line, r'\b(0x[0-9a-fA-F]+)\b', "number", offset)
        _apply_pattern(buffer, line, r"'([A-Z0-9]{4})'", "keyword", offset)
        
        offset = line_end + 1


def _highlight_lsusb_v(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply lsusb -v specific syntax highlighting."""
    lines = text.split('\n')
    offset = 0
    
    for line in lines:
        line_end = offset + len(line)
        
        if line.startswith('Bus '):
            for match in re.finditer(r'(Bus\s+)(\d+)', line):
                _apply_group(buffer, match, 1, "keyword", offset)
                _apply_group(buffer, match, 2, "number", offset)
            
            for match in re.finditer(r'(Device\s+)(\d+)', line):
                _apply_group(buffer, match, 1, "keyword", offset)
                _apply_group(buffer, match, 2, "number", offset)
            
            for match in re.finditer(r'(ID\s+)([0-9a-fA-F]{4}:[0-9a-fA-F]{4})', line):
                _apply_group(buffer, match, 2, "number", offset)
        else:
            _apply_pattern(buffer, line, r'^(\s+)(b\w+|i\w+|wMaxPacketSize|bmAttributes)', "keyword", offset)
            _apply_pattern(buffer, line, r'\b(0x[0-9a-fA-F]+)\b', "number", offset)
            _apply_pattern(buffer, line, r'\b(Hub|Human Interface Device|Mass Storage|Video|Audio|Wireless Controller|Vendor Specific)\b', "keyword", offset)
        
        offset = line_end + 1


def _highlight_efibootmgr(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply efibootmgr-specific syntax highlighting."""
    lines = text.split('\n')
    offset = 0
    
    for line in lines:
        line_end = offset + len(line)
        
        if line.startswith('Boot'):
            for match in re.finditer(r'^(Boot)([0-9A-Fa-f]{4})', line):
                _apply_group(buffer, match, 1, "keyword", offset)
                _apply_group(buffer, match, 2, "number", offset)
            
            for match in re.finditer(r'^Boot[0-9A-Fa-f]{4}(\*)?\s+([^\t]+?)(?:\t|\s{2,}|HD\(|BBS\(|$)', line):
                if match.group(1):
                    _apply_group(buffer, match, 1, "success", offset)
                if match.group(2) and match.group(2).strip():
                    name = match.group(2).strip()
                    name_start = line.find(name, match.start(2))
                    if name_start >= 0:
                        start = buffer.get_iter_at_offset(offset + name_start)
                        end = buffer.get_iter_at_offset(offset + name_start + len(name))
                        buffer.apply_tag_by_name("osname", start, end)
            
            _apply_pattern(buffer, line, r'(HD\([^)]+\))', "comment", offset)
            _apply_pattern(buffer, line, r'(/|\\)(EFI[^\s]*\.efi)', "path", offset, re.IGNORECASE)
            _apply_pattern(buffer, line, r'(BBS\([^)]+\))', "comment", offset)
        else:
            for match in re.finditer(r'^(BootCurrent|Timeout|BootOrder)(:?\s*)(.*)$', line):
                _apply_group(buffer, match, 1, "keyword", offset)
                _apply_group(buffer, match, 3, "number", offset)
        
        offset = line_end + 1


def _highlight_interrupts(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply /proc/interrupts-specific syntax highlighting."""
    lines = text.split('\n')
    offset = 0
    
    for line in lines:
        line_end = offset + len(line)
        
        if 'CPU' in line and line.strip().startswith('CPU'):
            start = buffer.get_iter_at_offset(offset)
            end = buffer.get_iter_at_offset(line_end)
            buffer.apply_tag_by_name("comment", start, end)
            offset = line_end + 1
            continue
        
        for match in re.finditer(r'^(\s*)(\d+)(:)', line):
            _apply_group(buffer, match, 2, "number", offset)
        
        _apply_pattern(buffer, line, r'\b(IO-APIC|PCI-MSI|DMAR-MSI|IR-PCI-MSI|XT-PIC|NMI|LOC|SPU|PMI|IWI|RTR|RES|CAL|TLB)\b', "keyword", offset)
        _apply_pattern(buffer, line, r'\b(edge|fasteoi|level)\b', "path", offset)
        _apply_pattern(buffer, line, r'(xhci_hcd|i915|nvme\S*|ahci\S*|snd_\S+|i8042|rtc0|acpi|timer|iwlwifi|eth\d+|wlan\d+)', "keyword", offset)
        
        offset = line_end + 1


def _highlight_journalctl(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply journalctl-specific syntax highlighting."""
    lines = text.split('\n')
    offset = 0
    
    for line in lines:
        line_end = offset + len(line)
        
        # Timestamp and hostname
        _apply_pattern(buffer, line, r'^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', "comment", offset)
        
        for match in re.finditer(r'^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+(\S+)', line):
            _apply_group(buffer, match, 1, "path", offset)
        
        # Process with PID
        for match in re.finditer(r'(\w+)\[(\d+)\]:', line):
            _apply_group(buffer, match, 1, "keyword", offset)
            _apply_group(buffer, match, 2, "number", offset)
        
        # Log levels
        _apply_pattern(buffer, line, r'<(info|notice|debug)>', "path", offset, re.IGNORECASE)
        _apply_pattern(buffer, line, r'<(warn|warning)>', "warning", offset, re.IGNORECASE)
        _apply_pattern(buffer, line, r'<(err|error|crit|critical|alert|emerg)>', "error", offset, re.IGNORECASE)
        
        # Keywords
        _apply_pattern(buffer, line, r'\b(error|failed|failure|fail)\b', "error", offset, re.IGNORECASE)
        _apply_pattern(buffer, line, r'\b(started|finished|success|connected|enabled)\b', "success", offset, re.IGNORECASE)
        _apply_pattern(buffer, line, r'(\S+\.service)', "keyword", offset)
        
        offset = line_end + 1


def _highlight_cmdline(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply kernel cmdline-specific syntax highlighting."""
    lines = text.split('\n')
    offset = 0
    
    for line in lines:
        line_end = offset + len(line)
        
        # BOOT_IMAGE
        for match in re.finditer(r'(BOOT_IMAGE=)([^\s]+)', line):
            _apply_group(buffer, match, 1, "keyword", offset)
            _apply_group(buffer, match, 2, "path", offset)
        
        # root= with UUID or path
        for match in re.finditer(r'(root=)(UUID=)?([^\s]+)', line):
            _apply_group(buffer, match, 1, "keyword", offset)
            if match.group(2):
                _apply_group(buffer, match, 2, "keyword", offset)
            _apply_group(buffer, match, 3, "number", offset)
        
        # rootflags
        for match in re.finditer(r'(rootflags=)([^\s]+)', line):
            _apply_group(buffer, match, 1, "keyword", offset)
            _apply_group(buffer, match, 2, "number", offset)
        
        # Boolean params
        _apply_pattern(buffer, line, r'(?<=\s)(quiet|splash|ro|rw)(?=\s|$)', "keyword", offset)
        
        # Key=value params
        for match in re.finditer(r'(?<=\s)(\w+\.?\w*)=([^\s]+)', line):
            _apply_group(buffer, match, 1, "keyword", offset)
            _apply_group(buffer, match, 2, "number", offset)
        
        offset = line_end + 1


def _highlight_generic(buffer: Gtk.TextBuffer, text: str) -> None:
    """Apply generic syntax highlighting for terminal text."""
    patterns = [
        (r'(#.*$)', "comment"),
        (r'(/dev/\S+|/etc/\S+|/sys/\S+|/proc/\S+|/var/\S+|/boot/\S+|/home/\S+|/mnt/\S+|/media/\S+|/run/\S+)', "path"),
        (r'(/[\w/\-\.]+)', "path"),
        (r'(https?://\S+)', "comment"),
        (r'(\(rev\s+[0-9a-fA-F]+\))', "comment"),
        (r'(\[[0-9a-fA-F]{4}:[0-9a-fA-F]{4}\])', "number"),
        (r'([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F])', "number"),
        (r'(ID\s+[0-9a-fA-F]{4}:[0-9a-fA-F]{4})', "number"),
        (r'([0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){2,})', "number"),
        (r'(0x[0-9a-fA-F]+)', "number"),
        (r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})', "number"),
        (r'\b(\d+[KMGT]i?B?)\b', "number"),
        (r'\b(\d+[KMGT]?Hz)\b', "number"),
        (r'\b(\d+°C)\b', "number"),
        (r'\b(enabled|UP|OK|PASSED|active|running|idle|mounted|connected|unblocked|authenticated|associated)\b', "success"),
        (r'\b(disabled|dormant|suspended|warning|warn|deprecated|unmounted|disconnected|blocked)\b', "warning"),
        (r'\b(DOWN|FAILED|error|fail|failed|fatal|critical|inactive|missing|unavailable)\b', "error"),
        (r'(Bus\s+\d+)', "keyword"),
        (r'(Device\s+\d+:?)', "keyword"),
        (r'\b(Host|bridge|controller|Intel|AMD|NVIDIA|Realtek|Samsung|Kingston|USB|PCI|SATA|NVMe|ACPI|GPU|CPU|RAM|SSD|HDD|AHCI|Bluetooth|Linux)\b', "keyword"),
    ]
    
    for pattern, tag in patterns:
        try:
            flags = re.MULTILINE | re.IGNORECASE if 'error' in pattern.lower() or 'enabled' in pattern.lower() else re.MULTILINE
            _apply_pattern(buffer, text, pattern, tag, flags=flags)
        except Exception:
            pass
