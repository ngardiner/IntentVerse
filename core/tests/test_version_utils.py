"""
Unit tests for version utility functions.

This module tests all functions in app.version_utils to ensure proper
semantic version handling and compatibility checking.
"""

import pytest
from packaging import version

from app.version_utils import (
    APP_VERSION,
    get_app_version,
    parse_version,
    compare_versions,
    is_version_compatible,
    check_compatibility_conditions,
    get_version_info,
)


class TestGetAppVersion:
    """Tests for get_app_version function."""

    @pytest.mark.unit
    def test_get_app_version_returns_string(self):
        """Test that get_app_version returns a string."""
        result = get_app_version()
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_get_app_version_returns_app_version_constant(self):
        """Test that get_app_version returns the APP_VERSION constant."""
        result = get_app_version()
        assert result == APP_VERSION

    @pytest.mark.unit
    def test_get_app_version_is_valid_semver(self):
        """Test that get_app_version returns a valid semantic version."""
        result = get_app_version()
        # Should not raise an exception
        version.parse(result)

    @pytest.mark.unit
    def test_app_version_constant_format(self):
        """Test that APP_VERSION constant follows semantic versioning."""
        assert isinstance(APP_VERSION, str)
        # Should match X.Y.Z format
        parts = APP_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()


class TestParseVersion:
    """Tests for parse_version function."""

    @pytest.mark.unit
    def test_parse_valid_version(self):
        """Test parsing valid semantic version strings."""
        test_cases = [
            "1.0.0",
            "0.1.0",
            "10.20.30",
            "999.999.999",
        ]
        
        for version_str in test_cases:
            result = parse_version(version_str)
            assert isinstance(result, version.Version)
            assert str(result) == version_str

    @pytest.mark.unit
    def test_parse_invalid_version_format(self):
        """Test that invalid version formats raise ValueError."""
        invalid_versions = [
            "1.0",           # Missing patch
            "1",             # Missing minor and patch
            "1.0.0.0",       # Too many parts
            "v1.0.0",        # Has 'v' prefix
            "1.0.0-alpha",   # Has pre-release
            "1.0.0+build",   # Has build metadata
            "1.a.0",         # Non-numeric part
            "1.0.a",         # Non-numeric part
            "",              # Empty string
            "1.0.",          # Trailing dot
            ".1.0.0",        # Leading dot
            "1..0.0",        # Double dot
            "1.0.0 ",        # Trailing space
            " 1.0.0",        # Leading space
        ]
        
        for invalid_version in invalid_versions:
            with pytest.raises(ValueError, match="Invalid semantic version format"):
                parse_version(invalid_version)

    @pytest.mark.unit
    def test_parse_version_edge_cases(self):
        """Test edge cases for version parsing."""
        # Zero versions
        result = parse_version("0.0.0")
        assert str(result) == "0.0.0"
        
        # Large numbers
        result = parse_version("999999.999999.999999")
        assert str(result) == "999999.999999.999999"


class TestCompareVersions:
    """Tests for compare_versions function."""

    @pytest.mark.unit
    def test_compare_equal_versions(self):
        """Test comparing equal versions."""
        test_cases = [
            ("1.0.0", "1.0.0"),
            ("0.0.0", "0.0.0"),
            ("10.20.30", "10.20.30"),
        ]
        
        for v1, v2 in test_cases:
            assert compare_versions(v1, v2) == 0
            assert compare_versions(v2, v1) == 0

    @pytest.mark.unit
    def test_compare_different_versions(self):
        """Test comparing different versions."""
        test_cases = [
            # (smaller, larger)
            ("1.0.0", "1.0.1"),  # Patch difference
            ("1.0.0", "1.1.0"),  # Minor difference
            ("1.0.0", "2.0.0"),  # Major difference
            ("0.9.9", "1.0.0"),  # Cross major boundary
            ("1.9.9", "2.0.0"),  # Cross major boundary
            ("1.0.9", "1.1.0"),  # Cross minor boundary
        ]
        
        for smaller, larger in test_cases:
            assert compare_versions(smaller, larger) == -1
            assert compare_versions(larger, smaller) == 1

    @pytest.mark.unit
    def test_compare_versions_with_invalid_input(self):
        """Test that invalid version strings raise ValueError."""
        with pytest.raises(ValueError):
            compare_versions("1.0", "1.0.0")
        
        with pytest.raises(ValueError):
            compare_versions("1.0.0", "invalid")

    @pytest.mark.unit
    def test_compare_versions_comprehensive(self):
        """Test comprehensive version comparison scenarios."""
        versions = ["0.1.0", "0.2.0", "1.0.0", "1.0.1", "1.1.0", "2.0.0"]
        
        # Test that each version is less than all subsequent versions
        for i in range(len(versions)):
            for j in range(i + 1, len(versions)):
                assert compare_versions(versions[i], versions[j]) == -1
                assert compare_versions(versions[j], versions[i]) == 1


class TestIsVersionCompatible:
    """Tests for is_version_compatible function."""

    @pytest.mark.unit
    def test_version_within_range(self):
        """Test versions that are within the compatible range."""
        test_cases = [
            # (app_version, min_version, max_version, expected)
            ("1.5.0", "1.0.0", "2.0.0", True),
            ("1.0.0", "1.0.0", "2.0.0", True),  # Equal to min
            ("2.0.0", "1.0.0", "2.0.0", True),  # Equal to max
            ("1.0.0", "1.0.0", None, True),     # No max version
            ("10.0.0", "1.0.0", None, True),    # No max version, high app version
        ]
        
        for app_ver, min_ver, max_ver, expected in test_cases:
            result = is_version_compatible(app_ver, min_ver, max_ver)
            assert result == expected, f"Failed for {app_ver} in [{min_ver}, {max_ver}]"

    @pytest.mark.unit
    def test_version_outside_range(self):
        """Test versions that are outside the compatible range."""
        test_cases = [
            # (app_version, min_version, max_version, expected)
            ("0.9.0", "1.0.0", "2.0.0", False),  # Below min
            ("2.1.0", "1.0.0", "2.0.0", False),  # Above max
            ("0.9.9", "1.0.0", None, False),     # Below min, no max
        ]
        
        for app_ver, min_ver, max_ver, expected in test_cases:
            result = is_version_compatible(app_ver, min_ver, max_ver)
            assert result == expected, f"Failed for {app_ver} in [{min_ver}, {max_ver}]"

    @pytest.mark.unit
    def test_version_compatible_edge_cases(self):
        """Test edge cases for version compatibility."""
        # Same version for all parameters
        assert is_version_compatible("1.0.0", "1.0.0", "1.0.0") == True
        
        # Zero versions
        assert is_version_compatible("0.0.0", "0.0.0", "1.0.0") == True
        assert is_version_compatible("0.0.1", "0.0.0", "0.0.0") == False

    @pytest.mark.unit
    def test_version_compatible_invalid_input(self):
        """Test that invalid version strings raise ValueError."""
        with pytest.raises(ValueError):
            is_version_compatible("invalid", "1.0.0", "2.0.0")
        
        with pytest.raises(ValueError):
            is_version_compatible("1.0.0", "invalid", "2.0.0")
        
        with pytest.raises(ValueError):
            is_version_compatible("1.0.0", "1.0.0", "invalid")


class TestCheckCompatibilityConditions:
    """Tests for check_compatibility_conditions function."""

    @pytest.mark.unit
    def test_empty_conditions(self):
        """Test that empty conditions return universal compatibility."""
        is_compatible, reasons = check_compatibility_conditions("1.0.0", [])
        assert is_compatible == True
        assert reasons == []

    @pytest.mark.unit
    def test_single_compatible_condition(self):
        """Test single compatibility condition that passes."""
        conditions = [
            {
                "type": "version_range",
                "min_version": "1.0.0",
                "max_version": "2.0.0",
                "reason": "Test compatibility"
            }
        ]
        
        is_compatible, reasons = check_compatibility_conditions("1.5.0", conditions)
        assert is_compatible == True
        assert reasons == []

    @pytest.mark.unit
    def test_single_incompatible_condition_below_min(self):
        """Test single compatibility condition that fails (below minimum)."""
        conditions = [
            {
                "type": "version_range",
                "min_version": "1.0.0",
                "max_version": "2.0.0",
                "reason": "Test compatibility"
            }
        ]
        
        is_compatible, reasons = check_compatibility_conditions("0.9.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 1
        assert "Test compatibility" in reasons[0]
        assert "requires 1.0.0 <= version <= 2.0.0" in reasons[0]
        assert "got 0.9.0" in reasons[0]

    @pytest.mark.unit
    def test_single_incompatible_condition_above_max(self):
        """Test single compatibility condition that fails (above maximum)."""
        conditions = [
            {
                "type": "version_range",
                "min_version": "1.0.0",
                "max_version": "2.0.0",
                "reason": "Test compatibility"
            }
        ]
        
        is_compatible, reasons = check_compatibility_conditions("2.1.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 1
        assert "Test compatibility" in reasons[0]
        assert "requires 1.0.0 <= version <= 2.0.0" in reasons[0]
        assert "got 2.1.0" in reasons[0]

    @pytest.mark.unit
    def test_condition_without_max_version(self):
        """Test compatibility condition without max_version."""
        conditions = [
            {
                "type": "version_range",
                "min_version": "1.0.0",
                "reason": "Minimum version requirement"
            }
        ]
        
        # Should pass for version >= min_version
        is_compatible, reasons = check_compatibility_conditions("1.0.0", conditions)
        assert is_compatible == True
        assert reasons == []
        
        is_compatible, reasons = check_compatibility_conditions("10.0.0", conditions)
        assert is_compatible == True
        assert reasons == []
        
        # Should fail for version < min_version
        is_compatible, reasons = check_compatibility_conditions("0.9.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 1
        assert "requires version >= 1.0.0" in reasons[0]
        assert "got 0.9.0" in reasons[0]

    @pytest.mark.unit
    def test_multiple_compatible_conditions(self):
        """Test multiple compatibility conditions that all pass."""
        conditions = [
            {
                "type": "version_range",
                "min_version": "1.0.0",
                "max_version": "3.0.0",
                "reason": "First requirement"
            },
            {
                "type": "version_range",
                "min_version": "1.5.0",
                "reason": "Second requirement"
            }
        ]
        
        is_compatible, reasons = check_compatibility_conditions("2.0.0", conditions)
        assert is_compatible == True
        assert reasons == []

    @pytest.mark.unit
    def test_multiple_conditions_with_failures(self):
        """Test multiple compatibility conditions with some failures."""
        conditions = [
            {
                "type": "version_range",
                "min_version": "1.0.0",
                "max_version": "2.0.0",
                "reason": "First requirement"
            },
            {
                "type": "version_range",
                "min_version": "2.5.0",
                "reason": "Second requirement"
            }
        ]
        
        is_compatible, reasons = check_compatibility_conditions("2.0.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 1
        assert "Second requirement" in reasons[0]
        assert "requires version >= 2.5.0" in reasons[0]

    @pytest.mark.unit
    def test_condition_missing_min_version(self):
        """Test compatibility condition missing min_version."""
        conditions = [
            {
                "type": "version_range",
                "max_version": "2.0.0",
                "reason": "Invalid condition"
            }
        ]
        
        is_compatible, reasons = check_compatibility_conditions("1.0.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 1
        assert "missing min_version" in reasons[0]

    @pytest.mark.unit
    def test_unknown_condition_type(self):
        """Test unknown compatibility condition type."""
        conditions = [
            {
                "type": "unknown_type",
                "min_version": "1.0.0",
                "reason": "Unknown condition"
            }
        ]
        
        is_compatible, reasons = check_compatibility_conditions("1.0.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 1
        assert "Unknown compatibility condition type: unknown_type" in reasons[0]

    @pytest.mark.unit
    def test_condition_with_invalid_version(self):
        """Test compatibility condition with invalid version format."""
        conditions = [
            {
                "type": "version_range",
                "min_version": "invalid",
                "reason": "Invalid version"
            }
        ]
        
        is_compatible, reasons = check_compatibility_conditions("1.0.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 1
        assert "Invalid version in compatibility condition" in reasons[0]

    @pytest.mark.unit
    def test_condition_default_reason(self):
        """Test compatibility condition with default reason."""
        conditions = [
            {
                "type": "version_range",
                "min_version": "2.0.0"
                # No reason provided
            }
        ]
        
        is_compatible, reasons = check_compatibility_conditions("1.0.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 1
        assert "Version compatibility requirement" in reasons[0]

    @pytest.mark.unit
    def test_complex_compatibility_scenario(self):
        """Test complex compatibility scenario with multiple conditions."""
        conditions = [
            {
                "type": "version_range",
                "min_version": "1.0.0",
                "max_version": "1.999.999",
                "reason": "Uses v1.x API"
            },
            {
                "type": "version_range",
                "min_version": "1.2.0",
                "reason": "Requires feature from v1.2.0"
            }
        ]
        
        # Test version that satisfies both conditions
        is_compatible, reasons = check_compatibility_conditions("1.5.0", conditions)
        assert is_compatible == True
        assert reasons == []
        
        # Test version that fails first condition (too high)
        is_compatible, reasons = check_compatibility_conditions("2.0.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 1
        assert "Uses v1.x API" in reasons[0]
        
        # Test version that fails second condition (too low)
        is_compatible, reasons = check_compatibility_conditions("1.1.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 1
        assert "Requires feature from v1.2.0" in reasons[0]
        
        # Test version that fails both conditions
        is_compatible, reasons = check_compatibility_conditions("0.9.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 2


class TestGetVersionInfo:
    """Tests for get_version_info function."""

    @pytest.mark.unit
    def test_get_version_info_structure(self):
        """Test that get_version_info returns correct structure."""
        result = get_version_info()
        
        assert isinstance(result, dict)
        assert "version" in result
        assert "major" in result
        assert "minor" in result
        assert "patch" in result
        assert "semantic_version" in result

    @pytest.mark.unit
    def test_get_version_info_values(self):
        """Test that get_version_info returns correct values."""
        result = get_version_info()
        
        # Should match APP_VERSION
        assert result["version"] == APP_VERSION
        assert result["semantic_version"] == True
        
        # Parse expected values from APP_VERSION
        parts = APP_VERSION.split(".")
        expected_major = int(parts[0])
        expected_minor = int(parts[1])
        expected_patch = int(parts[2])
        
        assert result["major"] == expected_major
        assert result["minor"] == expected_minor
        assert result["patch"] == expected_patch

    @pytest.mark.unit
    def test_get_version_info_types(self):
        """Test that get_version_info returns correct types."""
        result = get_version_info()
        
        assert isinstance(result["version"], str)
        assert isinstance(result["major"], int)
        assert isinstance(result["minor"], int)
        assert isinstance(result["patch"], int)
        assert isinstance(result["semantic_version"], bool)

    @pytest.mark.unit
    def test_get_version_info_consistency(self):
        """Test that get_version_info is consistent with other functions."""
        result = get_version_info()
        
        # Should be consistent with get_app_version()
        assert result["version"] == get_app_version()
        
        # Should be parseable by parse_version()
        parsed = parse_version(result["version"])
        assert parsed.major == result["major"]
        assert parsed.minor == result["minor"]
        assert parsed.micro == result["patch"]


class TestIntegrationScenarios:
    """Integration tests combining multiple version utility functions."""

    @pytest.mark.unit
    def test_real_world_compatibility_scenario(self):
        """Test a real-world compatibility checking scenario."""
        # Simulate a content pack that requires IntentVerse 1.0.0+
        content_pack_conditions = [
            {
                "type": "version_range",
                "min_version": "1.0.0",
                "reason": "Requires v1.0+ database features"
            }
        ]
        
        # Test with current app version
        current_version = get_app_version()
        is_compatible, reasons = check_compatibility_conditions(
            current_version, content_pack_conditions
        )
        
        # Should be compatible since APP_VERSION is "1.0.0"
        assert is_compatible == True
        assert reasons == []

    @pytest.mark.unit
    def test_version_comparison_with_app_version(self):
        """Test version comparison using the actual app version."""
        current_version = get_app_version()
        
        # Test comparisons
        assert compare_versions(current_version, current_version) == 0
        assert compare_versions("0.9.0", current_version) == -1
        assert compare_versions("1.2.0", current_version) == 1

    @pytest.mark.unit
    def test_compatibility_with_version_info(self):
        """Test compatibility checking using version info."""
        version_info = get_version_info()
        current_version = version_info["version"]
        
        # Create conditions based on version info
        conditions = [
            {
                "type": "version_range",
                "min_version": f"{version_info['major']}.0.0",
                "max_version": f"{version_info['major']}.999.999",
                "reason": f"Compatible with v{version_info['major']}.x only"
            }
        ]
        
        is_compatible, reasons = check_compatibility_conditions(current_version, conditions)
        assert is_compatible == True
        assert reasons == []

    @pytest.mark.unit
    def test_edge_case_version_boundaries(self):
        """Test edge cases around version boundaries."""
        # Test exact boundary conditions
        conditions = [
            {
                "type": "version_range",
                "min_version": "1.0.0",
                "max_version": "2.0.0",
                "reason": "Boundary test"
            }
        ]
        
        # Test exact boundaries
        assert check_compatibility_conditions("1.0.0", conditions)[0] == True
        assert check_compatibility_conditions("2.0.0", conditions)[0] == True
        
        # Test just outside boundaries
        assert check_compatibility_conditions("0.9.9", conditions)[0] == False
        assert check_compatibility_conditions("2.0.1", conditions)[0] == False

    @pytest.mark.unit
    def test_performance_with_many_conditions(self):
        """Test performance with many compatibility conditions."""
        # Create many conditions
        conditions = []
        for i in range(100):
            conditions.append({
                "type": "version_range",
                "min_version": "1.0.0",
                "reason": f"Condition {i}"
            })
        
        # Should still work efficiently
        is_compatible, reasons = check_compatibility_conditions("1.5.0", conditions)
        assert is_compatible == True
        assert reasons == []
        
        # Test with failing version
        is_compatible, reasons = check_compatibility_conditions("0.9.0", conditions)
        assert is_compatible == False
        assert len(reasons) == 100  # All conditions should fail