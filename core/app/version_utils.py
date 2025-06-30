"""
Version utility functions for IntentVerse.

This module provides utilities for semantic version comparison and compatibility checking.
"""

import re
from typing import List, Tuple, Optional
from packaging import version


# Application version - single source of truth
APP_VERSION = "1.0.0"


def get_app_version() -> str:
    """Get the current IntentVerse application version."""
    return APP_VERSION


def parse_version(version_str: str) -> version.Version:
    """
    Parse a semantic version string into a Version object.

    Args:
        version_str: Version string in format "X.Y.Z"

    Returns:
        packaging.version.Version object

    Raises:
        ValueError: If version string is not valid semantic version
    """
    if not re.match(r"^\d+\.\d+\.\d+$", version_str):
        raise ValueError(f"Invalid semantic version format: {version_str}")

    return version.parse(version_str)


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two semantic version strings.

    Args:
        version1: First version string
        version2: Second version string

    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2

    Raises:
        ValueError: If either version string is invalid
    """
    v1 = parse_version(version1)
    v2 = parse_version(version2)

    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0


def is_version_compatible(
    app_version: str, min_version: str, max_version: Optional[str] = None
) -> bool:
    """
    Check if an application version is compatible with the specified version range.

    Args:
        app_version: The application version to check
        min_version: Minimum required version (inclusive)
        max_version: Maximum allowed version (inclusive), None means no upper limit

    Returns:
        True if app_version is within the compatible range, False otherwise

    Raises:
        ValueError: If any version string is invalid
    """
    app_ver = parse_version(app_version)
    min_ver = parse_version(min_version)

    # Check minimum version requirement
    if app_ver < min_ver:
        return False

    # Check maximum version requirement if specified
    if max_version is not None:
        max_ver = parse_version(max_version)
        if app_ver > max_ver:
            return False

    return True


def check_compatibility_conditions(
    app_version: str, compatibility_conditions: List[dict]
) -> Tuple[bool, List[str]]:
    """
    Check if an application version satisfies all compatibility conditions.

    Args:
        app_version: The application version to check
        compatibility_conditions: List of compatibility condition objects

    Returns:
        Tuple of (is_compatible, list_of_failure_reasons)

    Example compatibility_conditions:
        [
            {
                "type": "version_range",
                "min_version": "1.0.0",
                "max_version": "2.0.0",
                "reason": "Uses API that changed in v2.1"
            }
        ]
    """
    if not compatibility_conditions:
        # Empty conditions = universal compatibility
        return True, []

    failure_reasons = []

    for condition in compatibility_conditions:
        condition_type = condition.get("type")

        if condition_type == "version_range":
            min_version = condition.get("min_version")
            max_version = condition.get("max_version")
            reason = condition.get("reason", "Version compatibility requirement")

            if not min_version:
                failure_reasons.append(
                    "Invalid compatibility condition: missing min_version"
                )
                continue

            try:
                if not is_version_compatible(app_version, min_version, max_version):
                    if max_version:
                        failure_reasons.append(
                            f"{reason} (requires {min_version} <= version <= {max_version}, got {app_version})"
                        )
                    else:
                        failure_reasons.append(
                            f"{reason} (requires version >= {min_version}, got {app_version})"
                        )
            except ValueError as e:
                failure_reasons.append(
                    f"Invalid version in compatibility condition: {e}"
                )
        else:
            failure_reasons.append(
                f"Unknown compatibility condition type: {condition_type}"
            )

    return len(failure_reasons) == 0, failure_reasons


def get_version_info() -> dict:
    """
    Get comprehensive version information for the application.

    Returns:
        Dictionary with version information
    """
    return {
        "version": APP_VERSION,
        "major": int(APP_VERSION.split(".")[0]),
        "minor": int(APP_VERSION.split(".")[1]),
        "patch": int(APP_VERSION.split(".")[2]),
        "semantic_version": True,
    }
