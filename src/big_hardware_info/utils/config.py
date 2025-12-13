"""
Application configuration management.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AppConfig:
    """Manage application configuration settings."""

    def __init__(self):
        """Initialize the configuration manager."""
        # Determine config directory
        self.config_dir = os.path.join(
            os.path.expanduser("~"), ".config", "hardware-reporter"
        )

        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)

        self.config_file = os.path.join(self.config_dir, "config.json")

        # Default settings
        self.defaults = {
            "last_export_directory": str(Path.home()),
            "default_export_format": "html",
            "auto_upload": False,
            "upload_service": "filebin.net",
            "window_width": 1100,
            "window_height": 800,
            "window_maximized": False,
            "sidebar_width": 280,
            "show_advanced_info": False,
            "theme": "system",  # system, light, dark
        }

        # Load configuration
        self.config = self.load_config()

        # Track which keys have been modified in this instance
        self.modified_keys = set()

    def load_config(self) -> dict:
        """Load configuration from file or create defaults if not found."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                    logger.info(f"Loaded configuration from {self.config_file}")

                    # Make sure all default keys are present
                    for key, value in self.defaults.items():
                        if key not in config:
                            config[key] = value

                    return config
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")

        # If file doesn't exist or there's an error, use defaults
        logger.info("Using default configuration")
        self.save_config(self.defaults)  # Save defaults for next time
        return self.defaults.copy()

    def save_config(self, config: Optional[dict] = None) -> bool:
        """Save configuration to file."""
        if config is None:
            # Reload the file first to get latest values from other instances
            try:
                if os.path.exists(self.config_file):
                    with open(self.config_file, "r") as f:
                        file_config = json.load(f)
                    # Update our config with file values, but preserve our modified keys
                    for key, value in file_config.items():
                        if key not in self.modified_keys:
                            self.config[key] = value
            except Exception as e:
                logger.warning(f"Could not reload config before save: {str(e)}")

            config = self.config

        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Saved configuration to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set a configuration value and save it."""
        self.config[key] = value
        self.modified_keys.add(key)  # Track that this key was modified
        return self.save_config()

    def reset(self) -> bool:
        """Reset configuration to defaults."""
        self.config = self.defaults.copy()
        self.modified_keys.clear()
        return self.save_config()
