"""
Utility Functions

Common helper functions used across the application.
"""

import os
import json
import hashlib
import uuid
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


import random
import string

def generate_random_id():

    random_id = ''.join(random.choices(string.ascii_uppercase, k=2))

    current_time = datetime.now().strftime('%Y%m%d%H%M%S')

    random_number = ''.join(random.choices(string.digits, k=5))

    generated_id = random_id + current_time + random_number
    return generated_id


def generate_uuid() -> str:
    """Generate a random UUID string"""
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """
    Generate a short random ID

    Args:
        length: Length of the ID (default: 8)

    Returns:
        Random alphanumeric string
    """
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def hash_string(text: str, algorithm: str = 'sha256') -> str:
    """
    Hash a string using the specified algorithm

    Args:
        text: String to hash
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hex digest of the hash
    """
    hasher = hashlib.new(algorithm)
    hasher.update(text.encode('utf-8'))
    return hasher.hexdigest()


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return default


def safe_json_dumps(obj: Any, default: str = '{}') -> str:
    """
    Safely convert object to JSON string

    Args:
        obj: Object to convert
        default: Default value if conversion fails

    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to convert to JSON: {e}")
        return default


def extract_json_object_str(text: str) -> str:
    if not text:
        return text
    candidate = str(text).strip()
    candidate = re.sub(r'^\s*```json\s*|\s*```\s*$', '', candidate, flags=re.DOTALL)
    candidate = candidate.strip()
    if candidate.startswith('{') and candidate.endswith('}'):
        return candidate
    start = candidate.find('{')
    end = candidate.rfind('}')
    if start != -1 and end != -1 and end > start:
        return candidate[start:end + 1]
    return candidate


def robust_json_loads(json_str: str, default: Any = None) -> Any:
    try:
        return json.loads(json_str)
    except Exception:
        try:
            extracted = extract_json_object_str(json_str)
            return json.loads(extracted)
        except Exception as e:
            logger.warning(f"Failed to robust-parse JSON: {e}")
            return default


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if it doesn't

    Args:
        path: Directory path

    Returns:
        Path object
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def get_file_size(path: Union[str, Path]) -> int:
    """
    Get file size in bytes

    Args:
        path: File path

    Returns:
        File size in bytes, or 0 if file doesn't exist
    """
    try:
        return Path(path).stat().st_size
    except (OSError, FileNotFoundError):
        return 0


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def timestamp_to_datetime(timestamp: Union[int, float]) -> datetime:
    """
    Convert Unix timestamp to datetime

    Args:
        timestamp: Unix timestamp (seconds or milliseconds)

    Returns:
        datetime object
    """
    # Handle milliseconds
    if timestamp > 1e10:
        timestamp = timestamp / 1000
    return datetime.fromtimestamp(timestamp)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp (milliseconds)

    Args:
        dt: datetime object

    Returns:
        Unix timestamp in milliseconds
    """
    return int(dt.timestamp() * 1000)


def now_timestamp() -> int:
    """Get current Unix timestamp in milliseconds"""
    return datetime_to_timestamp(datetime.now())


def now_iso() -> str:
    """Get current time in ISO format"""
    return datetime.now().isoformat()


def parse_iso_datetime(iso_string: str) -> Optional[datetime]:
    """
    Parse ISO format datetime string

    Args:
        iso_string: ISO format string

    Returns:
        datetime object or None if parsing fails
    """
    try:
        return datetime.fromisoformat(iso_string)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse datetime: {e}")
        return None


def truncate_string(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate string to maximum length

    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing unsafe characters

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re
    # Remove path separators and other unsafe characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Ensure filename is not empty
    if not filename:
        filename = 'unnamed'
    return filename


def merge_dicts(base: Dict, override: Dict, deep: bool = True) -> Dict:
    """
    Merge two dictionaries

    Args:
        base: Base dictionary
        override: Override dictionary
        deep: Whether to merge nested dicts recursively

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if deep and key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value, deep=True)
        else:
            result[key] = value

    return result


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Split list into chunks

    Args:
        lst: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def remove_none_values(data: Dict) -> Dict:
    """
    Remove None values from dictionary

    Args:
        data: Dictionary to clean

    Returns:
        Dictionary without None values
    """
    return {k: v for k, v in data.items() if v is not None}


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get boolean value from environment variable

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Boolean value
    """
    value = os.environ.get(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def get_env_int(key: str, default: int = 0) -> int:
    """
    Get integer value from environment variable

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Integer value
    """
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid integer value for {key}, using default: {default}")
        return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """
    Get float value from environment variable

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Float value
    """
    try:
        return float(os.environ.get(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid float value for {key}, using default: {default}")
        return default


class Timer:
    """
    Simple context manager for timing code execution

    Usage:
        with Timer("Operation name"):
            # code to time
            pass
    """

    def __init__(self, name: str = "Operation", logger_func=None):
        self.name = name
        self.logger_func = logger_func or logger.info
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.logger_func(f"{self.name} took {elapsed:.3f} seconds")


def validate_email(email: str) -> bool:
    """
    Simple email validation

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def mask_sensitive_data(text: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data (API keys, passwords, etc.)

    Args:
        text: Text to mask
        visible_chars: Number of characters to leave visible at the start

    Returns:
        Masked text
    """
    if not text or len(text) <= visible_chars:
        return "***"
    return text[:visible_chars] + "*" * (len(text) - visible_chars)
