"""
File upload functionality.

Provides upload to filebin.net for easy sharing of hardware reports.
"""

import subprocess
import logging
import json
import os
from typing import Tuple

from big_hardware_info.utils.i18n import _

logger = logging.getLogger(__name__)


def upload_to_filebin(file_path: str) -> Tuple[bool, str]:
    """
    Upload a file to filebin.net.
    
    Args:
        file_path: Path to the file to upload.
        
    Returns:
        Tuple of (success, url_or_error)
    """
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    filename = os.path.basename(file_path)
    
    try:
        # Use curl to upload
        result = subprocess.run(
            [
                "curl",
                "--silent",
                "--data-binary", f"@{file_path}",
                "-H", f"filename: {filename}",
                "https://filebin.net"
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        response_text = result.stdout.lower()
        
        # Check for common error messages
        if "maintenance" in response_text or "down for" in response_text:
            return False, _create_friendly_error(
                "maintenance",
                _("The filebin.net service is temporarily under maintenance. "
                  "Please try again in a few minutes or use the HTML export option.")
            )
        
        if "502" in response_text or "503" in response_text or "504" in response_text:
            return False, _create_friendly_error(
                "server_error",
                _("The filebin.net server is temporarily unavailable. "
                  "Please try again later or use the HTML export option.")
            )
        
        if result.returncode != 0:
            return False, _create_friendly_error(
                "upload_failed",
                _("Failed to upload the file. Please check your internet connection.")
            )
        
        # Parse response to get bin ID
        ID_MARKER = '"id": "'
        try:
            response = json.loads(result.stdout)
            bin_id = response.get("bin", {}).get("id", "")
            
            if bin_id:
                url = f"https://filebin.net/{bin_id}"
                
                # Save URL for reference
                config_dir = os.path.join(
                    os.path.expanduser("~"),
                    ".config",
                    "hardware-reporter"
                )
                os.makedirs(config_dir, exist_ok=True)
                
                with open(os.path.join(config_dir, "last_upload.url"), "w") as f:
                    f.write(url)
                
                return True, url
            else:
                # Try to extract ID from response
                if ID_MARKER in result.stdout:
                    # Parse manually
                    start = result.stdout.find(ID_MARKER) + len(ID_MARKER)
                    end = result.stdout.find('"', start)
                    bin_id = result.stdout[start:end]
                    
                    if bin_id:
                        url = f"https://filebin.net/{bin_id}"
                        return True, url
                
                return False, _create_friendly_error(
                    "no_url",
                    _("The server did not return a valid URL. Please try again.")
                )
                
        except json.JSONDecodeError:
            # Check if HTML response (likely error page)
            if "<html" in result.stdout.lower() or "<!doctype" in result.stdout.lower():
                # Extract text from HTML if possible
                if "maintenance" in result.stdout.lower():
                    return False, _create_friendly_error(
                        "maintenance",
                        _("The filebin.net service is temporarily under maintenance. "
                          "Please try again in a few minutes or use the HTML export option.")
                    )
                return False, _create_friendly_error(
                    "server_error",
                    _("The filebin.net server returned an unexpected response. "
                      "Please try again later or use the HTML export option.")
                )
            
            # Try manual parsing
            if ID_MARKER in result.stdout:
                start = result.stdout.find(ID_MARKER) + len(ID_MARKER)
                end = result.stdout.find('"', start)
                bin_id = result.stdout[start:end]
                
                if bin_id:
                    url = f"https://filebin.net/{bin_id}"
                    return True, url
            
            return False, _create_friendly_error(
                "invalid_response",
                _("Invalid response from server. Please try again.")
            )
            
    except subprocess.TimeoutExpired:
        return False, _create_friendly_error(
            "timeout",
            _("Upload timed out. Please check your internet connection and try again.")
        )
    except FileNotFoundError:
        return False, _create_friendly_error(
            "curl_not_found",
            _("The curl command was not found. Please install curl.")
        )
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return False, _create_friendly_error(
            "unknown",
            _("Upload error: {}").format(str(e))
        )


def _create_friendly_error(error_type: str, message: str) -> str:
    """Create a user-friendly error message.
    
    Args:
        error_type: Type of error for logging
        message: User-friendly message
        
    Returns:
        Formatted error message
    """
    logger.warning(f"Upload error ({error_type}): {message}")
    return message


