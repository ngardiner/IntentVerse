"""
Unit tests for v1.1.0 version utility functions.

This module tests the new functions added in v1.1.0 for feature compatibility
and version-specific functionality.
"""

import pytest
from unittest.mock import patch

from app.version_utils import (
    supports_content_pack_variables,
    supports_new_prompt_categories,
    get_feature_compatibility,
    create_v1_1_compatibility_conditions,
    create_backward_compatible_conditions,
    APP_VERSION,
)


class TestFeatureSupport:
    """Tests for feature support functions."""

    @pytest.mark.unit
    def test_supports_content_pack_variables(self):
        """Test content pack variables support detection."""
        # Should return True for v1.1.0+
        result = supports_content_pack_variables()
        assert result == True  # Since APP_VERSION is now 1.1.0

    @pytest.mark.unit
    def test_supports_new_prompt_categories(self):
        """Test new prompt categories support detection."""
        # Should return True for v1.1.0+
        result = supports_new_prompt_categories()
        assert result == True  # Since APP_VERSION is now 1.1.0

    @pytest.mark.unit
    def test_supports_content_pack_variables_with_mock_version(self):
        """Test content pack variables support with different versions."""
        # Test with v1.0.0 (should not support)
        with patch('app.version_utils.APP_VERSION', '1.0.0'):
            result = supports_content_pack_variables()
            assert result == False

        # Test with v1.1.0 (should support)
        with patch('app.version_utils.APP_VERSION', '1.1.0'):
            result = supports_content_pack_variables()
            assert result == True

        # Test with v1.2.0 (should support)
        with patch('app.version_utils.APP_VERSION', '1.2.0'):
            result = supports_content_pack_variables()
            assert result == True

    @pytest.mark.unit
    def test_supports_new_prompt_categories_with_mock_version(self):
        """Test new prompt categories support with different versions."""
        # Test with v1.0.0 (should not support)
        with patch('app.version_utils.APP_VERSION', '1.0.0'):
            result = supports_new_prompt_categories()
            assert result == False

        # Test with v1.1.0 (should support)
        with patch('app.version_utils.APP_VERSION', '1.1.0'):
            result = supports_new_prompt_categories()
            assert result == True

        # Test with v2.0.0 (should support)
        with patch('app.version_utils.APP_VERSION', '2.0.0'):
            result = supports_new_prompt_categories()
            assert result == True


class TestFeatureCompatibility:
    """Tests for get_feature_compatibility function."""

    @pytest.mark.unit
    def test_get_feature_compatibility_structure(self):
        """Test that get_feature_compatibility returns correct structure."""
        result = get_feature_compatibility()
        
        assert isinstance(result, dict)
        assert "content_pack_variables" in result
        assert "new_prompt_categories" in result
        assert "legacy_prompts_field" in result
        assert "variable_token_syntax" in result
        assert "user_variable_overrides" in result

    @pytest.mark.unit
    def test_get_feature_compatibility_values(self):
        """Test that get_feature_compatibility returns correct values."""
        result = get_feature_compatibility()
        
        # For v1.1.0, all new features should be supported
        assert result["content_pack_variables"] == True
        assert result["new_prompt_categories"] == True
        assert result["legacy_prompts_field"] == True  # Always supported
        assert result["variable_token_syntax"] == True
        assert result["user_variable_overrides"] == True

    @pytest.mark.unit
    def test_get_feature_compatibility_with_mock_version(self):
        """Test feature compatibility with different versions."""
        # Test with v1.0.0
        with patch('app.version_utils.APP_VERSION', '1.0.0'):
            result = get_feature_compatibility()
            assert result["content_pack_variables"] == False
            assert result["new_prompt_categories"] == False
            assert result["legacy_prompts_field"] == True  # Always supported
            assert result["variable_token_syntax"] == False
            assert result["user_variable_overrides"] == False

        # Test with v1.1.0
        with patch('app.version_utils.APP_VERSION', '1.1.0'):
            result = get_feature_compatibility()
            assert result["content_pack_variables"] == True
            assert result["new_prompt_categories"] == True
            assert result["legacy_prompts_field"] == True
            assert result["variable_token_syntax"] == True
            assert result["user_variable_overrides"] == True


class TestCompatibilityConditions:
    """Tests for compatibility condition creation functions."""

    @pytest.mark.unit
    def test_create_v1_1_compatibility_conditions(self):
        """Test creation of v1.1.0 compatibility conditions."""
        conditions = create_v1_1_compatibility_conditions()
        
        assert isinstance(conditions, list)
        assert len(conditions) == 1
        
        condition = conditions[0]
        assert condition["type"] == "version_range"
        assert condition["min_version"] == "1.1.0"
        assert condition["max_version"] is None
        assert "v1.1.0" in condition["reason"]

    @pytest.mark.unit
    def test_create_backward_compatible_conditions(self):
        """Test creation of backward compatible conditions."""
        conditions = create_backward_compatible_conditions()
        
        assert isinstance(conditions, list)
        assert len(conditions) == 1
        
        condition = conditions[0]
        assert condition["type"] == "version_range"
        assert condition["min_version"] == "1.0.0"
        assert condition["max_version"] is None
        assert "Compatible with all IntentVerse versions" in condition["reason"]

    @pytest.mark.unit
    def test_compatibility_conditions_with_check_function(self):
        """Test that compatibility conditions work with check_compatibility_conditions."""
        from app.version_utils import check_compatibility_conditions
        
        # Test v1.1.0 conditions
        v1_1_conditions = create_v1_1_compatibility_conditions()
        
        # Should be compatible with v1.1.0
        is_compatible, reasons = check_compatibility_conditions("1.1.0", v1_1_conditions)
        assert is_compatible == True
        assert reasons == []
        
        # Should be compatible with v1.2.0
        is_compatible, reasons = check_compatibility_conditions("1.2.0", v1_1_conditions)
        assert is_compatible == True
        assert reasons == []
        
        # Should not be compatible with v1.0.0
        is_compatible, reasons = check_compatibility_conditions("1.0.0", v1_1_conditions)
        assert is_compatible == False
        assert len(reasons) == 1
        assert "v1.1.0" in reasons[0]
        
        # Test backward compatible conditions
        backward_conditions = create_backward_compatible_conditions()
        
        # Should be compatible with v1.0.0
        is_compatible, reasons = check_compatibility_conditions("1.0.0", backward_conditions)
        assert is_compatible == True
        assert reasons == []
        
        # Should be compatible with v1.1.0
        is_compatible, reasons = check_compatibility_conditions("1.1.0", backward_conditions)
        assert is_compatible == True
        assert reasons == []


class TestIntegrationScenarios:
    """Integration tests for v1.1.0 version utilities."""

    @pytest.mark.unit
    def test_feature_detection_consistency(self):
        """Test that feature detection functions are consistent."""
        # All variable-related features should have the same support status
        variables_supported = supports_content_pack_variables()
        compatibility = get_feature_compatibility()
        
        assert compatibility["content_pack_variables"] == variables_supported
        assert compatibility["variable_token_syntax"] == variables_supported
        assert compatibility["user_variable_overrides"] == variables_supported

    @pytest.mark.unit
    def test_prompt_feature_consistency(self):
        """Test that prompt feature detection is consistent."""
        prompts_supported = supports_new_prompt_categories()
        compatibility = get_feature_compatibility()
        
        assert compatibility["new_prompt_categories"] == prompts_supported

    @pytest.mark.unit
    def test_version_specific_behavior(self):
        """Test version-specific behavior across different versions."""
        test_versions = ["1.0.0", "1.1.0", "1.2.0", "2.0.0"]
        
        for version in test_versions:
            with patch('app.version_utils.APP_VERSION', version):
                # Get feature support for this version
                variables_supported = supports_content_pack_variables()
                prompts_supported = supports_new_prompt_categories()
                
                # v1.1.0+ should support new features
                if version >= "1.1.0":
                    assert variables_supported == True
                    assert prompts_supported == True
                else:
                    assert variables_supported == False
                    assert prompts_supported == False
                
                # Legacy prompts should always be supported
                compatibility = get_feature_compatibility()
                assert compatibility["legacy_prompts_field"] == True

    @pytest.mark.unit
    def test_compatibility_conditions_real_world_scenario(self):
        """Test compatibility conditions in a real-world scenario."""
        from app.version_utils import check_compatibility_conditions
        
        # Scenario: Content pack that uses v1.1.0 features
        pack_with_variables = {
            "metadata": {
                "name": "Test Pack with Variables",
                "compatibility_conditions": create_v1_1_compatibility_conditions()
            }
        }
        
        # Scenario: Content pack that's backward compatible
        pack_backward_compatible = {
            "metadata": {
                "name": "Backward Compatible Pack",
                "compatibility_conditions": create_backward_compatible_conditions()
            }
        }
        
        # Test with current version (should be 1.1.0)
        current_version = APP_VERSION
        
        # Both packs should be compatible with current version
        is_compatible, _ = check_compatibility_conditions(
            current_version, pack_with_variables["metadata"]["compatibility_conditions"]
        )
        assert is_compatible == True
        
        is_compatible, _ = check_compatibility_conditions(
            current_version, pack_backward_compatible["metadata"]["compatibility_conditions"]
        )
        assert is_compatible == True
        
        # Test with v1.0.0
        is_compatible, _ = check_compatibility_conditions(
            "1.0.0", pack_with_variables["metadata"]["compatibility_conditions"]
        )
        assert is_compatible == False  # Should not be compatible
        
        is_compatible, _ = check_compatibility_conditions(
            "1.0.0", pack_backward_compatible["metadata"]["compatibility_conditions"]
        )
        assert is_compatible == True  # Should be compatible