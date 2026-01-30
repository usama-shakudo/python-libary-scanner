"""
Utility functions for parsing version information from pip requests
"""

import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def parse_python_version(user_agent: str) -> Optional[str]:
    """
    Extract Python version from pip User-Agent header

    Examples:
        "pip/23.0.1 CPython/3.11.0" -> "3.11.0"
        "pip/20.0.2 CPython/3.8.5" -> "3.8.5"
        "pip/23.1.2 {\"ci\":null,\"cpu\":\"x86_64\",\"distro\":{\"name\":\"Ubuntu\"}" -> None

    Args:
        user_agent: The User-Agent header from the request

    Returns:
        Python version string (e.g., "3.11.0") or None if not found
    """
    if not user_agent:
        return None

    try:
        # Pattern: CPython/3.11.0 or Python/3.11.0
        match = re.search(r'(?:CPython|Python)/(\d+\.\d+\.\d+)', user_agent)
        if match:
            return match.group(1)

        # Fallback: just the version number pattern
        match = re.search(r'(\d+\.\d+\.\d+)', user_agent)
        if match:
            return match.group(1)

    except Exception as e:
        logger.warning(f"Failed to parse Python version from User-Agent '{user_agent}': {e}")

    return None


def parse_package_and_version(package_name: str) -> Tuple[str, Optional[str]]:
    """
    Parse package name and version from pip request

    Examples:
        "numpy" -> ("numpy", None)
        "numpy==1.24.0" -> ("numpy", "1.24.0")
        "numpy>=1.20.0" -> ("numpy", "1.20.0")  # Take specific version if possible
        "requests[security]==2.31.0" -> ("requests", "2.31.0")

    Args:
        package_name: The package name from the request (may include version specifier)

    Returns:
        Tuple of (package_name, version)
    """
    if not package_name:
        return ("", None)

    try:
        # Remove extras like [security]
        package_name = re.sub(r'\[.*?\]', '', package_name)

        # Check for version specifiers: ==, >=, <=, >, <, ~=
        match = re.search(r'^([a-zA-Z0-9_.-]+)(==|>=|<=|>|<|~=)(.+)$', package_name)
        if match:
            name = match.group(1).strip()
            operator = match.group(2)
            version = match.group(3).strip()

            # For ==, we know the exact version
            if operator == '==':
                return (name, version)

            # For other operators, still store the version for reference
            # but mark it as not exact
            return (name, f"{operator}{version}")

        # No version specified
        return (package_name.strip(), None)

    except Exception as e:
        logger.warning(f"Failed to parse package name '{package_name}': {e}")
        return (package_name, None)


def normalize_version(version: Optional[str]) -> str:
    """
    Normalize version string for database storage

    Examples:
        None -> "latest"
        "1.24.0" -> "1.24.0"
        ">=1.20.0" -> ">=1.20.0"

    Args:
        version: Version string or None

    Returns:
        Normalized version string
    """
    if version is None or version.strip() == "":
        return "latest"
    return version.strip()
