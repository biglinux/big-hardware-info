# Big Hardware Info

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![GTK4](https://img.shields.io/badge/GTK-4.0-green.svg)](https://gtk.org/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-yellow.svg)](https://python.org/)
[![Adwaita](https://img.shields.io/badge/Adwaita-1.0-purple.svg)](https://gnome.pages.gitlab.gnome.org/libadwaita/)

A modern GTK4/Adwaita application for viewing and sharing comprehensive hardware information on Linux systems. Built with a focus on usability, accessibility, and modern design principles.

**Version 2.0.0** - Complete rewrite with modern GTK4/Adwaita interface.

## ✨ Features

### 🖥️ Comprehensive Hardware Detection
- **CPU** - Model, cores, threads, cache sizes, clock speeds, virtualization support
- **GPU** - Discrete and integrated graphics, driver info, OpenGL/Vulkan support
- **Memory** - RAM modules, speed, type, capacity, manufacturer details
- **Storage** - Drives, partitions, usage statistics, S.M.A.R.T. data
- **Network** - Ethernet, Wi-Fi, virtual interfaces, IP addresses, MAC addresses
- **Audio** - Sound cards, ALSA devices, running audio services
- **Battery** - Charge status, capacity, health, model info
- **Bluetooth** - Adapters and connected devices
- **Sensors** - Temperature, fan speeds, voltage readings
- **USB** - Connected devices with power and speed info
- **PCI** - All PCI devices including bridges and controllers
- **Webcams** - Camera devices with supported resolutions
- **Printers** - Installed printers and their status

### 🎨 Modern User Interface
- **Native GTK4/Adwaita** - Follows GNOME Human Interface Guidelines
- **Dark Mode Support** - Automatic system theme detection
- **Responsive Layout** - Adapts to different window sizes
- **Sidebar Navigation** - Quick access to all hardware categories
- **Progress Indicators** - Visual feedback during data collection
- **Toast Notifications** - Non-intrusive status messages
- **Loading Cursor** - Visual feedback during operations

### 🔍 Smart Features
- **Global Search** - Filter hardware components across all categories
- **Copy to Clipboard** - Quick copy for any hardware detail
- **Collapsible Sections** - Expand/collapse detailed information
- **Selectable Text** - All values can be selected and copied
- **Monospace Formatting** - Technical data displayed in monospace font

### 📊 System Information Views
- **Summary Overview** - System snapshot with key stats
- **System Files** - View important configuration files:
  - `/etc/fstab` - Filesystem mount configuration
  - `lsmod` - Loaded kernel modules  
  - `lspci` - PCI device listing
  - `lsusb` - USB device listing
  - `efibootmgr` - EFI boot entries
  - `journalctl` - System journal entries
  - `dmesg` - Kernel ring buffer
  - `mhwd` - Manjaro/BigLinux hardware detection
- **Syntax Highlighting** - Code blocks with proper highlighting

### 📤 Export & Share
- **HTML Export** - Generate beautiful, standalone HTML reports
  - Modern dark theme design
  - Syntax highlighting for technical data
  - Responsive layout works on all devices
  - Print-friendly formatting
  - Collapsible sections
- **Privacy Options** - Choose to include/exclude sensitive data:
  - Serial numbers
  - MAC addresses
  - IP addresses
- **Online Sharing** - Upload reports to filebin.net with one click
  - Reports available for 7 days
  - Shareable URL for easy distribution
  - Perfect for forum support threads

### 🔐 Elevated Access
- **Root Data Collection** - Optionally collect restricted data
  - S.M.A.R.T. disk health information
  - Advanced sensor readings
  - Protected system files
- **pkexec Integration** - Secure privilege escalation


### System Dependencies

- Python 3.10+
- GTK 4.0
- libadwaita 1.0
- inxi (for hardware detection)
- Optional: smartmontools (for S.M.A.R.T. data)


## 🔧 Technologies

- **[GTK4](https://gtk.org/)** - Modern UI toolkit
- **[libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/)** - GNOME design patterns
- **[inxi](https://github.com/smxi/inxi)** - System information backend
- **[Python 3](https://python.org/)** - Programming language
- **[Cairo](https://cairographics.org/)** - 2D graphics library for charts

## 📋 Requirements

### Minimum
- Python 3.10
- GTK 4.0
- libadwaita 1.0
- inxi


### Recommended
- smartmontools (for S.M.A.R.T. data)
- lm_sensors (for temperature readings)
- efibootmgr (for EFI boot entries)


## 📜 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.


## 🔗 Links

- 🌐 [BigLinux Website](https://www.biglinux.com.br)
- 🐛 [Report Issues](https://github.com/biglinux/big-hardware-info/issues)
- 📦 [Releases](https://github.com/biglinux/big-hardware-info/releases)
- 💬 [BigLinux Forum](https://forum.biglinux.com.br)
- 📱 [BigLinux Telegram](https://t.me/biglinuxcommunity)

---

Made with ❤️ by the [BigLinux](https://www.biglinux.com.br) team
