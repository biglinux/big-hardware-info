"""
File upload functionality.

Provides upload to filebin.net for easy sharing of hardware reports.
"""

import subprocess
import logging
import json
import os
from typing import Tuple

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
        
        if result.returncode != 0:
            return False, f"Upload failed: {result.stderr}"
        
        # Parse response to get bin ID
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
                if '"id": "' in result.stdout:
                    # Parse manually
                    start = result.stdout.find('"id": "') + 7
                    end = result.stdout.find('"', start)
                    bin_id = result.stdout[start:end]
                    
                    if bin_id:
                        url = f"https://filebin.net/{bin_id}"
                        return True, url
                
                return False, "Could not get upload URL from response"
                
        except json.JSONDecodeError:
            # Try manual parsing
            if '"id": "' in result.stdout:
                start = result.stdout.find('"id": "') + 7
                end = result.stdout.find('"', start)
                bin_id = result.stdout[start:end]
                
                if bin_id:
                    url = f"https://filebin.net/{bin_id}"
                    return True, url
            
            return False, f"Invalid response from server: {result.stdout[:200]}"
            
    except subprocess.TimeoutExpired:
        return False, "Upload timed out"
    except FileNotFoundError:
        return False, "curl command not found. Please install curl."
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return False, str(e)


def upload_to_transfer_sh(file_path: str) -> Tuple[bool, str]:
    """
    Upload a file to transfer.sh (alternative service).
    
    Args:
        file_path: Path to the file to upload.
        
    Returns:
        Tuple of (success, url_or_error)
    """
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    try:
        result = subprocess.run(
            [
                "curl",
                "--silent",
                "--upload-file", file_path,
                f"https://transfer.sh/{os.path.basename(file_path)}"
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode != 0:
            return False, f"Upload failed: {result.stderr}"
        
        url = result.stdout.strip()
        
        if url.startswith("http"):
            return True, url
        else:
            return False, f"Invalid response: {url}"
            
    except subprocess.TimeoutExpired:
        return False, "Upload timed out"
    except FileNotFoundError:
        return False, "curl command not found. Please install curl."
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return False, str(e)
