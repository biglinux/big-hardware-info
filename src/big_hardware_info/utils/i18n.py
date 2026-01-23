#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# translation_utils.py - Utilities for translation support
#
import gettext
import os
from typing import Callable

# Determine locale directory (works in AppImage and system install)
locale_dir = "/usr/share/locale"  # Default for system install

# Check if we're in an AppImage
if "APPIMAGE" in os.environ or "APPDIR" in os.environ:
    # Running from AppImage
    # i18n.py is in: src/big_hardware_info/utils/i18n.py
    # We need to get to: usr/share/locale
    script_dir = os.path.dirname(os.path.abspath(__file__))  # src/big_hardware_info/utils
    big_hardware_info_dir = os.path.dirname(script_dir)  # src/big_hardware_info
    src_dir = os.path.dirname(big_hardware_info_dir)  # src
    appdir_root = os.path.dirname(src_dir)  # AppDir root (squashfs-root)
    appimage_locale = os.path.join(appdir_root, "usr", "share", "locale")  # usr/share/locale

    if os.path.isdir(appimage_locale):
        locale_dir = appimage_locale

# Configure the translation text domain for big-hardware-info
gettext.bindtextdomain("big-hardware-info", locale_dir)
gettext.textdomain("big-hardware-info")

# Export _ directly as the translation function with explicit type
_: Callable[[str], str] = gettext.gettext
