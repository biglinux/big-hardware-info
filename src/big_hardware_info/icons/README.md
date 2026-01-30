# Big Hardware Info - Bundled Icons

This directory contains SVG icons bundled with the Big Hardware Info application to ensure consistent visual appearance across all systems, regardless of installed icon themes.

## Source

All icons are sourced from the **Papirus Icon Theme** project, specifically from the `bigicons-papient` variant:
- Original source: https://github.com/PapirusDevelopmentTeam/papirus-icon-theme
- Variant: bigicons-papient (symbolic icons 16x16)
- License: GPL-3.0

## Icon List

The project uses 33 icons in total:

### Category Icons (17)
- `view-grid-symbolic.svg` - Overview/Summary
- `cpu-symbolic.svg` - CPU/Processor
- `video-display-symbolic.svg` - GPU/Graphics
- `camera-web-symbolic.svg` - Webcam
- `computer-symbolic.svg` - System/Motherboard
- `memory-symbolic.svg` - Memory/RAM
- `audio-card-symbolic.svg` - Audio
- `network-wired-symbolic.svg` - Network
- `drive-harddisk-symbolic.svg` - Storage/Disk
- `battery-symbolic.svg` - Battery
- `bluetooth-symbolic.svg` - Bluetooth
- `media-removable-symbolic.svg` - USB
- `drive-multidisk-symbolic.svg` - PCI
- `system-run-symbolic.svg` - Processes
- `printer-symbolic.svg` - Printers
- `temperature-symbolic.svg` - Sensors
- `dialog-information-symbolic.svg` - Logs

### Action/UI Icons (16)
- `edit-copy-symbolic.svg` - Copy action
- `view-refresh-symbolic.svg` - Refresh action
- `system-lock-screen-symbolic.svg` - Privacy/Lock
- `open-menu-symbolic.svg` - Menu
- `emblem-synchronizing-symbolic.svg` - Sync/Loading
- `security-high-symbolic.svg` - Security
- `application-x-firmware-symbolic.svg` - UEFI/Firmware
- `drive-harddisk-solidstate-symbolic.svg` - SSD
- `network-server-symbolic.svg` - Server/Network
- `document-save-symbolic.svg` - Save/Export
- `send-to-symbolic.svg` - Share/Upload
- `edit-find-symbolic.svg` - Search
- `emblem-ok-symbolic.svg` - Success/OK
- `dialog-warning-symbolic.svg` - Warning
- `weather-windy-symbolic.svg` - Fan/Cooling
- `sensors-temperature-symbolic.svg` - Temperature sensor

## Technical Details

- **Format**: SVG (Scalable Vector Graphics)
- **Type**: Symbolic icons (use `currentColor` for automatic theme adaptation)
- **Size**: 16x16px (base size, scales to any size)
- **Average file size**: ~700 bytes per icon
- **Total size**: ~23 KB

## Usage

Icons are loaded via the `big_hardware_info.utils.icons` module, which provides:
- `get_icon_path(icon_name)` - Returns absolute path to icon file
- `create_icon_image(icon_name, size)` - Creates Gtk.Image widget
- `icon_from_file(icon_path, size)` - Creates Gtk.Image from file path

The module automatically handles:
- Development environment (running from source)
- Installed environment (system-wide installation)
- Fallback to system icons (if bundled icon not found)

## License

These icons are distributed under the **GPL-3.0 license**, inherited from the Papirus Icon Theme project. See the main LICENSE file for details.

## Credits

- Papirus Icon Theme: https://github.com/PapirusDevelopmentTeam/papirus-icon-theme
- bigicons-papient variant: Part of the Papirus project
- Big Hardware Info: https://github.com/biglinux/big-hardware-info
