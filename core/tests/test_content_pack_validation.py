"""
Unit tests for content pack validation with v1.1.0 features.

Tests validation of new fields (variables, content_prompts, usage_prompts)
while ensuring backward compatibility with v1.0.0 content packs.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile

from app.content_pack_manager import ContentPackManager
from app.state_manager import StateManager
from app.module_loader import ModuleLoader


@pytest.fixture
def state_manager():
    """Provides a mock StateManager."""
    return Mock(spec=StateManager)


@pytest.fixture
def module_loader():
    """Provides a mock ModuleLoader."""
    mock_loader = Mock(spec=ModuleLoader)
    mock_db_tool = Mock()
    mock_db_tool.load_content_pack_database.return_value = None
    mock_db_tool.export_database_content.return_value = ["-- MOCK SQL EXPORT"]
    mock_loader.get_tool.return_value = mock_db_tool
    return mock_loader


@pytest.fixture
def temp_content_packs_dir():
    """Creates a temporary directory for content packs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def content_pack_manager(state_manager, module_loader, temp_content_packs_dir):
    """Provides a ContentPackManager instance."""
    manager = ContentPackManager(state_manager, module_loader)
    manager.content_packs_dir = temp_content_packs_dir
    return manager


class TestBackwardCompatibility:
    """Tests for backward compatibility with v1.0.0 content packs."""

    def test_validate_v1_0_content_pack(self, content_pack_manager):
        """Test that v1.0.0 content packs validate successfully."""
        v1_0_pack = {
            "metadata": {
                "name": "Legacy Pack",
                "summary": "A v1.0.0 content pack",
                "version": "1.0.0"
            },
            "database": [
                "CREATE TABLE users (id INTEGER PRIMARY KEY);",
                "INSERT INTO users (id) VALUES (1);"
            ],
            "prompts": [
                {
                    "name": "Welcome Prompt",
                    "content": "Welcome to our system!"
                }
            ],
            "state": {
                "filesystem": {
                    "type": "directory",
                    "name": "/",
                    "children": []
                }
            }
        }

        validation = content_pack_manager.validate_content_pack_detailed(v1_0_pack)

        assert validation["is_valid"] == True
        assert len(validation["errors"]) == 0
        assert validation["summary"]["has_metadata"] == True
        assert validation["summary"]["has_database"] == True
        assert validation["summary"]["has_prompts"] == True
        assert validation["summary"]["has_state"] == True
        assert validation["summary"]["database_statements"] == 2
        assert validation["summary"]["prompts_count"] == 1

    def test_validate_minimal_v1_0_pack(self, content_pack_manager):
        """Test validation of minimal v1.0.0 content pack."""
        minimal_pack = {
            "prompts": [
                {
                    "name": "Simple Prompt",
                    "content": "Hello world"
                }
            ]
        }

        validation = content_pack_manager.validate_content_pack_detailed(minimal_pack)

        assert validation["is_valid"] == True
        assert len(validation["errors"]) == 0
        # Should have warnings about missing metadata
        assert any("metadata" in warning.lower() for warning in validation["warnings"])

    def test_validate_empty_content_pack_fails(self, content_pack_manager):
        """Test that empty content pack fails validation."""
        empty_pack = {}

        validation = content_pack_manager.validate_content_pack_detailed(empty_pack)

        assert validation["is_valid"] == False
        assert len(validation["errors"]) > 0
        assert any("must contain at least one" in error for error in validation["errors"])


class TestVariablesValidation:
    """Tests for variables section validation."""

    def test_validate_valid_variables_section(self, content_pack_manager):
        """Test validation of valid variables section."""
        pack_with_variables = {
            "metadata": {"name": "Variables Pack", "version": "1.1.0"},
            "variables": {
                "email_domain": "example.com",
                "company_name": "ACME Corp",
                "user_count": "100"
            },
            "database": [
                "INSERT INTO settings (key, value) VALUES ('domain', '{{email_domain}}');"
            ]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_variables)

        assert validation["is_valid"] == True
        assert validation["summary"]["has_variables"] == True
        assert validation["summary"]["variables_count"] == 3

    def test_validate_invalid_variable_names(self, content_pack_manager):
        """Test validation of invalid variable names."""
        pack_with_invalid_vars = {
            "metadata": {"name": "Invalid Variables Pack"},
            "variables": {
                "123invalid": "value1",  # Cannot start with number
                "invalid-name": "value2",  # Cannot contain hyphen
                "invalid.name": "value3",  # Cannot contain dot
                "valid_name": "value4"  # This one is valid
            },
            "prompts": [{"name": "Test", "content": "Test"}]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_invalid_vars)

        assert validation["is_valid"] == False
        error_messages = " ".join(validation["errors"])
        assert "123invalid" in error_messages
        assert "invalid-name" in error_messages
        assert "invalid.name" in error_messages
        # valid_name should not appear in errors

    def test_validate_non_string_variable_values(self, content_pack_manager):
        """Test validation of non-string variable values."""
        pack_with_non_string_vars = {
            "metadata": {"name": "Non-String Variables Pack"},
            "variables": {
                "string_var": "valid",
                "number_var": 123,  # Invalid - must be string
                "boolean_var": True,  # Invalid - must be string
                "null_var": None  # Invalid - must be string
            },
            "prompts": [{"name": "Test", "content": "Test"}]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_non_string_vars)

        assert validation["is_valid"] == False
        error_messages = " ".join(validation["errors"])
        assert "number_var" in error_messages
        assert "boolean_var" in error_messages
        assert "null_var" in error_messages

    def test_validate_variables_not_dict(self, content_pack_manager):
        """Test validation when variables section is not a dictionary."""
        pack_with_invalid_vars = {
            "metadata": {"name": "Invalid Variables Structure"},
            "variables": ["not", "a", "dictionary"],
            "prompts": [{"name": "Test", "content": "Test"}]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_invalid_vars)

        assert validation["is_valid"] == False
        assert any("Variables section must be an object" in error for error in validation["errors"])

    def test_validate_undefined_variables_warning(self, content_pack_manager):
        """Test that undefined variables generate warnings."""
        pack_with_undefined_vars = {
            "metadata": {"name": "Undefined Variables Pack"},
            "variables": {
                "defined_var": "value"
            },
            "database": [
                "INSERT INTO test (value) VALUES ('{{defined_var}}');",
                "INSERT INTO test (value) VALUES ('{{undefined_var}}');"
            ]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_undefined_vars)

        # Should be valid but have warnings
        assert validation["is_valid"] == True
        warning_messages = " ".join(validation["warnings"])
        assert "undefined_var" in warning_messages
        assert "used but not defined" in warning_messages

    def test_validate_unused_variables_warning(self, content_pack_manager):
        """Test that unused variables generate warnings."""
        pack_with_unused_vars = {
            "metadata": {"name": "Unused Variables Pack"},
            "variables": {
                "used_var": "value",
                "unused_var": "value"
            },
            "database": [
                "INSERT INTO test (value) VALUES ('{{used_var}}');"
            ]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_unused_vars)

        # Should be valid but have warnings
        assert validation["is_valid"] == True
        warning_messages = " ".join(validation["warnings"])
        assert "unused_var" in warning_messages
        assert "defined but not used" in warning_messages


class TestContentPromptsValidation:
    """Tests for content_prompts section validation."""

    def test_validate_valid_content_prompts(self, content_pack_manager):
        """Test validation of valid content_prompts section."""
        pack_with_content_prompts = {
            "metadata": {"name": "Content Prompts Pack", "version": "1.1.0"},
            "content_prompts": [
                {
                    "name": "Create Email",
                    "content": "Create an email template for {{company_name}}"
                },
                {
                    "name": "Generate Report",
                    "content": "Generate a monthly report",
                    "description": "Optional description"
                }
            ]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_content_prompts)

        assert validation["is_valid"] == True
        assert validation["summary"]["has_content_prompts"] == True
        assert validation["summary"]["content_prompts_count"] == 2

    def test_validate_content_prompts_not_array(self, content_pack_manager):
        """Test validation when content_prompts is not an array."""
        pack_with_invalid_prompts = {
            "metadata": {"name": "Invalid Content Prompts"},
            "content_prompts": {"not": "an array"},
            "prompts": [{"name": "Test", "content": "Test"}]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_invalid_prompts)

        assert validation["is_valid"] == False
        assert any("Content prompts section must be an array" in error for error in validation["errors"])

    def test_validate_content_prompt_missing_fields(self, content_pack_manager):
        """Test validation of content prompts with missing required fields."""
        pack_with_incomplete_prompts = {
            "metadata": {"name": "Incomplete Content Prompts"},
            "content_prompts": [
                {
                    "name": "Valid Prompt",
                    "content": "This is valid"
                },
                {
                    "name": "Missing Content"
                    # Missing 'content' field
                },
                {
                    "content": "Missing Name"
                    # Missing 'name' field
                },
                {
                    # Missing both fields
                }
            ]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_incomplete_prompts)

        assert validation["is_valid"] == False
        error_messages = " ".join(validation["errors"])
        assert "Content prompt 2 missing required fields" in error_messages
        assert "Content prompt 3 missing required fields" in error_messages
        assert "Content prompt 4 missing required fields" in error_messages

    def test_validate_content_prompt_not_object(self, content_pack_manager):
        """Test validation when content prompt is not an object."""
        pack_with_invalid_prompt_structure = {
            "metadata": {"name": "Invalid Prompt Structure"},
            "content_prompts": [
                "not an object",
                123,
                {"name": "Valid", "content": "Valid"}
            ]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_invalid_prompt_structure)

        assert validation["is_valid"] == False
        error_messages = " ".join(validation["errors"])
        assert "Content prompt 1 must be an object" in error_messages
        assert "Content prompt 2 must be an object" in error_messages


class TestUsagePromptsValidation:
    """Tests for usage_prompts section validation."""

    def test_validate_valid_usage_prompts(self, content_pack_manager):
        """Test validation of valid usage_prompts section."""
        pack_with_usage_prompts = {
            "metadata": {"name": "Usage Prompts Pack", "version": "1.1.0"},
            "usage_prompts": [
                {
                    "name": "Send Welcome Email",
                    "content": "Send a welcome email to new users"
                },
                {
                    "name": "Generate Monthly Report",
                    "content": "Create and send the monthly analytics report",
                    "category": "reporting"
                }
            ]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_usage_prompts)

        assert validation["is_valid"] == True
        assert validation["summary"]["has_usage_prompts"] == True
        assert validation["summary"]["usage_prompts_count"] == 2

    def test_validate_usage_prompts_not_array(self, content_pack_manager):
        """Test validation when usage_prompts is not an array."""
        pack_with_invalid_prompts = {
            "metadata": {"name": "Invalid Usage Prompts"},
            "usage_prompts": "not an array",
            "prompts": [{"name": "Test", "content": "Test"}]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_invalid_prompts)

        assert validation["is_valid"] == False
        assert any("Usage prompts section must be an array" in error for error in validation["errors"])

    def test_validate_usage_prompt_missing_fields(self, content_pack_manager):
        """Test validation of usage prompts with missing required fields."""
        pack_with_incomplete_prompts = {
            "metadata": {"name": "Incomplete Usage Prompts"},
            "usage_prompts": [
                {
                    "name": "Valid Prompt",
                    "content": "This is valid"
                },
                {
                    "name": "Missing Content"
                    # Missing 'content' field
                },
                {
                    "content": "Missing Name"
                    # Missing 'name' field
                }
            ]
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack_with_incomplete_prompts)

        assert validation["is_valid"] == False
        error_messages = " ".join(validation["errors"])
        assert "Usage prompt 2 missing required fields" in error_messages
        assert "Usage prompt 3 missing required fields" in error_messages


class TestMixedFieldsValidation:
    """Tests for content packs with multiple v1.1.0 fields."""

    def test_validate_full_v1_1_content_pack(self, content_pack_manager):
        """Test validation of complete v1.1.0 content pack with all new fields."""
        full_v1_1_pack = {
            "metadata": {
                "name": "Complete v1.1.0 Pack",
                "summary": "A complete content pack using all v1.1.0 features",
                "version": "1.1.0"
            },
            "variables": {
                "email_domain": "example.com",
                "company_name": "ACME Corp"
            },
            "content_prompts": [
                {
                    "name": "Create Welcome Email",
                    "content": "Create a welcome email for {{company_name}} using domain {{email_domain}}"
                }
            ],
            "usage_prompts": [
                {
                    "name": "Send Welcome",
                    "content": "Send the welcome email to new users"
                }
            ],
            "prompts": [
                {
                    "name": "Legacy Prompt",
                    "content": "This is for backward compatibility"
                }
            ],
            "database": [
                "CREATE TABLE companies (name VARCHAR(255));",
                "INSERT INTO companies (name) VALUES ('{{company_name}}');"
            ],
            "state": {
                "email": {
                    "inbox": [],
                    "sent": []
                }
            }
        }

        validation = content_pack_manager.validate_content_pack_detailed(full_v1_1_pack)

        assert validation["is_valid"] == True
        assert len(validation["errors"]) == 0
        
        # Check all sections are detected
        assert validation["summary"]["has_metadata"] == True
        assert validation["summary"]["has_variables"] == True
        assert validation["summary"]["has_content_prompts"] == True
        assert validation["summary"]["has_usage_prompts"] == True
        assert validation["summary"]["has_prompts"] == True
        assert validation["summary"]["has_database"] == True
        assert validation["summary"]["has_state"] == True
        
        # Check counts
        assert validation["summary"]["variables_count"] == 2
        assert validation["summary"]["content_prompts_count"] == 1
        assert validation["summary"]["usage_prompts_count"] == 1
        assert validation["summary"]["prompts_count"] == 1
        assert validation["summary"]["database_statements"] == 2

    def test_validate_mixed_valid_invalid_fields(self, content_pack_manager):
        """Test validation of pack with mix of valid and invalid fields."""
        mixed_pack = {
            "metadata": {
                "name": "Mixed Pack"
                # Missing recommended fields - should generate warnings
            },
            "variables": {
                "valid_var": "value",
                "123invalid": "value"  # Invalid variable name
            },
            "content_prompts": [
                {
                    "name": "Valid Prompt",
                    "content": "Valid content"
                },
                {
                    "name": "Invalid Prompt"
                    # Missing content field
                }
            ],
            "usage_prompts": [
                {
                    "name": "Valid Usage",
                    "content": "Valid usage content"
                }
            ],
            "database": [
                "CREATE TABLE test (id INT);",
                ""  # Empty statement - should generate warning
            ]
        }

        validation = content_pack_manager.validate_content_pack_detailed(mixed_pack)

        assert validation["is_valid"] == False
        assert len(validation["errors"]) > 0
        assert len(validation["warnings"]) > 0
        
        # Should have errors for invalid variable name and missing prompt content
        error_messages = " ".join(validation["errors"])
        assert "123invalid" in error_messages
        assert "Content prompt 2 missing required fields" in error_messages
        
        # Should have warnings for missing metadata and empty database statement
        warning_messages = " ".join(validation["warnings"])
        assert "metadata" in warning_messages.lower()
        assert "empty" in warning_messages.lower()


class TestValidationSummary:
    """Tests for validation summary information."""

    def test_validation_summary_structure(self, content_pack_manager):
        """Test that validation summary contains expected fields."""
        pack = {
            "metadata": {"name": "Test"},
            "variables": {"var1": "value1"},
            "content_prompts": [{"name": "prompt1", "content": "content1"}],
            "usage_prompts": [{"name": "usage1", "content": "usage_content1"}],
            "prompts": [{"name": "legacy1", "content": "legacy_content1"}],
            "database": ["CREATE TABLE test (id INT);"],
            "state": {"module1": {}}
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack)
        summary = validation["summary"]

        # Check that all expected summary fields are present
        expected_fields = [
            "has_metadata", "has_database", "has_state", "has_prompts",
            "has_variables", "has_content_prompts", "has_usage_prompts",
            "database_statements", "state_modules", "prompts_count",
            "variables_count", "content_prompts_count", "usage_prompts_count"
        ]
        
        for field in expected_fields:
            assert field in summary

        # Check counts are correct
        assert summary["variables_count"] == 1
        assert summary["content_prompts_count"] == 1
        assert summary["usage_prompts_count"] == 1
        assert summary["prompts_count"] == 1
        assert summary["database_statements"] == 1

    def test_validation_summary_empty_sections(self, content_pack_manager):
        """Test validation summary with empty sections."""
        pack = {
            "metadata": {"name": "Empty Sections Test"},
            "variables": {},
            "content_prompts": [],
            "usage_prompts": [],
            "prompts": [],
            "database": [],
            "state": {}
        }

        validation = content_pack_manager.validate_content_pack_detailed(pack)
        summary = validation["summary"]

        # All sections should be detected as present but with zero counts
        assert summary["has_variables"] == True
        assert summary["has_content_prompts"] == True
        assert summary["has_usage_prompts"] == True
        assert summary["has_prompts"] == True
        assert summary["has_database"] == True
        assert summary["has_state"] == True
        
        assert summary["variables_count"] == 0
        assert summary["content_prompts_count"] == 0
        assert summary["usage_prompts_count"] == 0
        assert summary["prompts_count"] == 0
        assert summary["database_statements"] == 0


class TestValidationErrorHandling:
    """Tests for validation error handling and edge cases."""

    def test_validate_non_dict_input(self, content_pack_manager):
        """Test validation of non-dictionary input."""
        validation = content_pack_manager.validate_content_pack_detailed("not a dict")

        assert validation["is_valid"] == False
        assert any("must be a JSON object" in error for error in validation["errors"])

    def test_validate_null_input(self, content_pack_manager):
        """Test validation of null input."""
        validation = content_pack_manager.validate_content_pack_detailed(None)

        assert validation["is_valid"] == False
        assert any("must be a JSON object" in error for error in validation["errors"])

    def test_validate_with_variable_resolver_error(self, content_pack_manager):
        """Test validation when variable resolver throws an error."""
        pack_with_variables = {
            "metadata": {"name": "Variable Error Test"},
            "variables": {"test_var": "value"},
            "database": ["INSERT INTO test VALUES ('{{test_var}}');"]
        }

        # Mock the variable resolver to throw an error
        with patch.object(content_pack_manager, 'variable_resolver') as mock_resolver:
            mock_resolver.validate_content_pack_variables.side_effect = Exception("Resolver error")
            
            validation = content_pack_manager.validate_content_pack_detailed(pack_with_variables)

            # Should still be valid, but have a warning about validation failure
            assert validation["is_valid"] == True
            warning_messages = " ".join(validation["warnings"])
            assert "Could not validate variable usage" in warning_messages

    def test_validate_large_content_pack(self, content_pack_manager):
        """Test validation of a large content pack."""
        large_pack = {
            "metadata": {"name": "Large Pack"},
            "variables": {f"var_{i}": f"value_{i}" for i in range(100)},
            "content_prompts": [
                {"name": f"prompt_{i}", "content": f"content_{i}"}
                for i in range(50)
            ],
            "usage_prompts": [
                {"name": f"usage_{i}", "content": f"usage_content_{i}"}
                for i in range(30)
            ],
            "database": [f"CREATE TABLE table_{i} (id INT);" for i in range(20)]
        }

        validation = content_pack_manager.validate_content_pack_detailed(large_pack)

        assert validation["is_valid"] == True
        assert validation["summary"]["variables_count"] == 100
        assert validation["summary"]["content_prompts_count"] == 50
        assert validation["summary"]["usage_prompts_count"] == 30
        assert validation["summary"]["database_statements"] == 20