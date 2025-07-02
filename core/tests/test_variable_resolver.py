"""
Unit tests for the variable resolution system.
"""

import pytest
from unittest.mock import Mock, MagicMock

from app.variable_resolver import (
    VariableResolver,
    VariableToken,
    VariableParseError,
    VariableResolutionError,
    create_variable_resolver,
    resolve_string_standalone,
    get_variables_in_text_standalone,
)
from app.content_pack_variables import ContentPackVariableManager


class TestVariableToken:
    """Tests for the VariableToken dataclass."""

    def test_variable_token_creation(self):
        """Test creating a VariableToken instance."""
        token = VariableToken(
            full_match="{{email_domain}}",
            variable_name="email_domain",
            start_pos=10,
            end_pos=25
        )
        
        assert token.full_match == "{{email_domain}}"
        assert token.variable_name == "email_domain"
        assert token.start_pos == 10
        assert token.end_pos == 25


class TestVariableResolver:
    """Tests for the VariableResolver class."""

    @pytest.fixture
    def mock_variable_manager(self):
        """Create a mock ContentPackVariableManager."""
        return Mock(spec=ContentPackVariableManager)

    @pytest.fixture
    def resolver(self, mock_variable_manager):
        """Create a VariableResolver instance with mock manager."""
        return VariableResolver(mock_variable_manager)

    @pytest.fixture
    def resolver_no_manager(self):
        """Create a VariableResolver instance without variable manager."""
        return VariableResolver()

    def test_parse_tokens_simple(self, resolver):
        """Test parsing simple variable tokens."""
        text = "Hello {{name}}, welcome to {{company}}!"
        tokens = resolver.parse_tokens(text)
        
        assert len(tokens) == 2
        assert tokens[0].variable_name == "name"
        assert tokens[0].full_match == "{{name}}"
        assert tokens[1].variable_name == "company"
        assert tokens[1].full_match == "{{company}}"

    def test_parse_tokens_no_tokens(self, resolver):
        """Test parsing text with no variable tokens."""
        text = "Hello world, no variables here!"
        tokens = resolver.parse_tokens(text)
        
        assert len(tokens) == 0

    def test_parse_tokens_complex_names(self, resolver):
        """Test parsing tokens with complex variable names."""
        text = "{{email_domain}} and {{user_name_123}} and {{_private_var}}"
        tokens = resolver.parse_tokens(text)
        
        assert len(tokens) == 3
        assert tokens[0].variable_name == "email_domain"
        assert tokens[1].variable_name == "user_name_123"
        assert tokens[2].variable_name == "_private_var"

    def test_parse_tokens_invalid_names(self, resolver):
        """Test that invalid variable names are not matched."""
        text = "{{123invalid}} {{-invalid}} {{invalid-name}} {{valid_name}}"
        tokens = resolver.parse_tokens(text)
        
        # Only valid_name should be matched
        assert len(tokens) == 1
        assert tokens[0].variable_name == "valid_name"

    def test_validate_variable_name(self, resolver):
        """Test variable name validation."""
        # Valid names
        assert resolver.validate_variable_name("email_domain") == True
        assert resolver.validate_variable_name("user123") == True
        assert resolver.validate_variable_name("_private") == True
        assert resolver.validate_variable_name("CamelCase") == True
        
        # Invalid names
        assert resolver.validate_variable_name("123invalid") == False
        assert resolver.validate_variable_name("-invalid") == False
        assert resolver.validate_variable_name("invalid-name") == False
        assert resolver.validate_variable_name("") == False
        assert resolver.validate_variable_name("invalid.name") == False

    def test_get_variable_value_pack_defaults(self, resolver):
        """Test getting variable value from pack defaults."""
        pack_defaults = {"email_domain": "example.com", "company": "ACME Corp"}
        
        value = resolver.get_variable_value("email_domain", pack_defaults, "test_pack")
        assert value == "example.com"
        
        value = resolver.get_variable_value("company", pack_defaults, "test_pack")
        assert value == "ACME Corp"

    def test_get_variable_value_user_override(self, resolver, mock_variable_manager):
        """Test getting variable value from user override."""
        pack_defaults = {"email_domain": "example.com"}
        mock_variable_manager.get_variable_value.return_value = "custom.com"
        
        value = resolver.get_variable_value("email_domain", pack_defaults, "test_pack", user_id=1)
        
        assert value == "custom.com"
        mock_variable_manager.get_variable_value.assert_called_once_with("test_pack", "email_domain", 1)

    def test_get_variable_value_fallback_to_defaults(self, resolver, mock_variable_manager):
        """Test fallback to pack defaults when user override doesn't exist."""
        pack_defaults = {"email_domain": "example.com"}
        mock_variable_manager.get_variable_value.return_value = None
        
        value = resolver.get_variable_value("email_domain", pack_defaults, "test_pack", user_id=1)
        
        assert value == "example.com"
        mock_variable_manager.get_variable_value.assert_called_once_with("test_pack", "email_domain", 1)

    def test_get_variable_value_not_found(self, resolver):
        """Test error when variable is not found."""
        pack_defaults = {"other_var": "value"}
        
        with pytest.raises(VariableResolutionError) as exc_info:
            resolver.get_variable_value("missing_var", pack_defaults, "test_pack")
        
        assert "not found" in str(exc_info.value)

    def test_resolve_string_simple(self, resolver):
        """Test resolving variables in a simple string."""
        text = "Hello {{name}}, welcome to {{company}}!"
        pack_defaults = {"name": "John", "company": "ACME Corp"}
        
        result = resolver.resolve_string(text, pack_defaults, "test_pack")
        
        assert result == "Hello John, welcome to ACME Corp!"

    def test_resolve_string_no_variables(self, resolver):
        """Test resolving string with no variables."""
        text = "Hello world!"
        pack_defaults = {}
        
        result = resolver.resolve_string(text, pack_defaults, "test_pack")
        
        assert result == "Hello world!"

    def test_resolve_string_with_user_overrides(self, resolver, mock_variable_manager):
        """Test resolving string with user variable overrides."""
        text = "Email: {{email_domain}}"
        pack_defaults = {"email_domain": "example.com"}
        mock_variable_manager.get_variable_value.return_value = "custom.com"
        
        result = resolver.resolve_string(text, pack_defaults, "test_pack", user_id=1)
        
        assert result == "Email: custom.com"

    def test_resolve_string_strict_mode_error(self, resolver):
        """Test that strict mode raises error for missing variables."""
        text = "Hello {{missing_var}}!"
        pack_defaults = {}
        
        with pytest.raises(VariableResolutionError):
            resolver.resolve_string(text, pack_defaults, "test_pack", strict=True)

    def test_resolve_string_non_strict_mode(self, resolver):
        """Test that non-strict mode leaves unresolved variables unchanged."""
        text = "Hello {{name}} and {{missing_var}}!"
        pack_defaults = {"name": "John"}
        
        result = resolver.resolve_string(text, pack_defaults, "test_pack", strict=False)
        
        assert result == "Hello John and {{missing_var}}!"

    def test_resolve_string_non_string_input(self, resolver):
        """Test that non-string input is returned unchanged."""
        pack_defaults = {}
        
        assert resolver.resolve_string(123, pack_defaults, "test_pack") == 123
        assert resolver.resolve_string(None, pack_defaults, "test_pack") is None
        assert resolver.resolve_string(True, pack_defaults, "test_pack") == True

    def test_resolve_data_structure_dict(self, resolver):
        """Test resolving variables in a dictionary."""
        data = {
            "email": "user@{{domain}}",
            "company": "{{company_name}}",
            "settings": {
                "theme": "{{theme}}",
                "language": "en"
            }
        }
        pack_defaults = {
            "domain": "example.com",
            "company_name": "ACME Corp",
            "theme": "dark"
        }
        
        result = resolver.resolve_data_structure(data, pack_defaults, "test_pack")
        
        expected = {
            "email": "user@example.com",
            "company": "ACME Corp",
            "settings": {
                "theme": "dark",
                "language": "en"
            }
        }
        assert result == expected

    def test_resolve_data_structure_list(self, resolver):
        """Test resolving variables in a list."""
        data = [
            "Welcome to {{company}}",
            {"email": "admin@{{domain}}"},
            "{{greeting}} message"
        ]
        pack_defaults = {
            "company": "ACME Corp",
            "domain": "example.com",
            "greeting": "Hello"
        }
        
        result = resolver.resolve_data_structure(data, pack_defaults, "test_pack")
        
        expected = [
            "Welcome to ACME Corp",
            {"email": "admin@example.com"},
            "Hello message"
        ]
        assert result == expected

    def test_resolve_data_structure_mixed_types(self, resolver):
        """Test resolving variables in mixed data types."""
        data = {
            "string": "{{value}}",
            "number": 42,
            "boolean": True,
            "null": None,
            "list": ["{{item1}}", "{{item2}}"],
            "nested": {
                "deep": "{{deep_value}}"
            }
        }
        pack_defaults = {
            "value": "resolved",
            "item1": "first",
            "item2": "second",
            "deep_value": "nested"
        }
        
        result = resolver.resolve_data_structure(data, pack_defaults, "test_pack")
        
        expected = {
            "string": "resolved",
            "number": 42,
            "boolean": True,
            "null": None,
            "list": ["first", "second"],
            "nested": {
                "deep": "nested"
            }
        }
        assert result == expected

    def test_resolve_data_structure_variable_in_keys(self, resolver):
        """Test resolving variables in dictionary keys."""
        data = {
            "{{key_name}}": "value",
            "normal_key": "{{value}}"
        }
        pack_defaults = {
            "key_name": "resolved_key",
            "value": "resolved_value"
        }
        
        result = resolver.resolve_data_structure(data, pack_defaults, "test_pack")
        
        expected = {
            "resolved_key": "value",
            "normal_key": "resolved_value"
        }
        assert result == expected

    def test_get_variables_in_text(self, resolver):
        """Test getting variable names from text."""
        text = "Hello {{name}}, your email is user@{{domain}} and company is {{company}}."
        
        variables = resolver.get_variables_in_text(text)
        
        assert set(variables) == {"name", "domain", "company"}

    def test_get_variables_in_text_duplicates(self, resolver):
        """Test that duplicate variables are returned only once."""
        text = "{{name}} and {{name}} again, plus {{domain}} and {{name}} once more."
        
        variables = resolver.get_variables_in_text(text)
        
        assert set(variables) == {"name", "domain"}

    def test_get_variables_in_text_non_string(self, resolver):
        """Test getting variables from non-string input."""
        assert resolver.get_variables_in_text(123) == []
        assert resolver.get_variables_in_text(None) == []

    def test_get_variables_in_data_structure(self, resolver):
        """Test getting variable names from data structure."""
        data = {
            "email": "user@{{domain}}",
            "{{key_var}}": "value",
            "list": ["{{item1}}", "{{item2}}"],
            "nested": {
                "deep": "{{deep_var}}"
            }
        }
        
        variables = resolver.get_variables_in_data_structure(data)
        
        assert set(variables) == {"domain", "key_var", "item1", "item2", "deep_var"}

    def test_validate_content_pack_variables_valid(self, resolver):
        """Test validation of content pack with all variables defined."""
        content_pack_data = {
            "database": [
                {"email": "user@{{domain}}"},
                {"company": "{{company_name}}"}
            ],
            "prompts": ["Welcome to {{company_name}}"]
        }
        pack_defaults = {
            "domain": "example.com",
            "company_name": "ACME Corp"
        }
        
        result = resolver.validate_content_pack_variables(content_pack_data, pack_defaults)
        
        assert result["valid"] == True
        assert set(result["used_variables"]) == {"domain", "company_name"}
        assert set(result["defined_variables"]) == {"domain", "company_name"}
        assert result["undefined_variables"] == []
        assert result["unused_variables"] == []

    def test_validate_content_pack_variables_undefined(self, resolver):
        """Test validation of content pack with undefined variables."""
        content_pack_data = {
            "database": [{"email": "user@{{domain}}"}],
            "prompts": ["Welcome to {{missing_var}}"]
        }
        pack_defaults = {
            "domain": "example.com"
        }
        
        result = resolver.validate_content_pack_variables(content_pack_data, pack_defaults)
        
        assert result["valid"] == False
        assert set(result["used_variables"]) == {"domain", "missing_var"}
        assert result["undefined_variables"] == ["missing_var"]

    def test_validate_content_pack_variables_unused(self, resolver):
        """Test validation of content pack with unused variables."""
        content_pack_data = {
            "database": [{"email": "user@{{domain}}"}]
        }
        pack_defaults = {
            "domain": "example.com",
            "unused_var": "unused_value"
        }
        
        result = resolver.validate_content_pack_variables(content_pack_data, pack_defaults)
        
        assert result["valid"] == True  # Still valid, just has unused variables
        assert result["unused_variables"] == ["unused_var"]


class TestFactoryAndStandaloneFunctions:
    """Tests for factory and standalone functions."""

    def test_create_variable_resolver(self):
        """Test creating a variable resolver with factory function."""
        resolver = create_variable_resolver()
        assert isinstance(resolver, VariableResolver)
        assert resolver.variable_manager is None

    def test_create_variable_resolver_with_manager(self):
        """Test creating a variable resolver with variable manager."""
        mock_manager = Mock(spec=ContentPackVariableManager)
        resolver = create_variable_resolver(mock_manager)
        assert isinstance(resolver, VariableResolver)
        assert resolver.variable_manager == mock_manager

    def test_resolve_string_standalone(self):
        """Test standalone string resolution function."""
        text = "Hello {{name}}!"
        pack_defaults = {"name": "World"}
        
        result = resolve_string_standalone(text, pack_defaults)
        
        assert result == "Hello World!"

    def test_resolve_string_standalone_strict(self):
        """Test standalone string resolution with strict mode."""
        text = "Hello {{missing}}!"
        pack_defaults = {}
        
        with pytest.raises(VariableResolutionError):
            resolve_string_standalone(text, pack_defaults, strict=True)

    def test_resolve_string_standalone_non_strict(self):
        """Test standalone string resolution with non-strict mode."""
        text = "Hello {{missing}}!"
        pack_defaults = {}
        
        result = resolve_string_standalone(text, pack_defaults, strict=False)
        
        assert result == "Hello {{missing}}!"

    def test_get_variables_in_text_standalone(self):
        """Test standalone function to get variables from text."""
        text = "Hello {{name}}, welcome to {{company}}!"
        
        variables = get_variables_in_text_standalone(text)
        
        assert set(variables) == {"name", "company"}


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_string_resolution(self):
        """Test resolving empty string."""
        resolver = VariableResolver()
        result = resolver.resolve_string("", {}, "test_pack")
        assert result == ""

    def test_malformed_tokens(self):
        """Test handling of malformed variable tokens."""
        resolver = VariableResolver()
        text = "{{incomplete} and {missing_braces} and {{valid_var}}"
        pack_defaults = {"valid_var": "value"}
        
        result = resolver.resolve_string(text, pack_defaults, "test_pack")
        
        # Only valid_var should be resolved
        assert result == "{{incomplete} and {missing_braces} and value"

    def test_nested_braces(self):
        """Test handling of nested braces."""
        resolver = VariableResolver()
        text = "{{{nested_var}}} and {{normal_var}}"
        pack_defaults = {"nested_var": "nested", "normal_var": "normal"}
        
        result = resolver.resolve_string(text, pack_defaults, "test_pack")
        
        # Should resolve the inner variable
        assert result == "{nested} and normal"

    def test_variable_manager_exception(self):
        """Test handling of variable manager exceptions."""
        mock_manager = Mock(spec=ContentPackVariableManager)
        mock_manager.get_variable_value.side_effect = Exception("Database error")
        
        resolver = VariableResolver(mock_manager)
        pack_defaults = {"var": "default"}
        
        with pytest.raises(VariableResolutionError):
            resolver.get_variable_value("var", pack_defaults, "test_pack", user_id=1)

    def test_large_data_structure(self):
        """Test resolving variables in a large data structure."""
        resolver = VariableResolver()
        
        # Create a smaller but still meaningful nested structure
        data = {
            f"key_{i}": {
                "value": "{{" + f"var_{i}" + "}}",
                "nested": ["{{" + f"list_var_{i}" + "}}" for _ in range(3)]
            }
            for i in range(10)
        }
        
        pack_defaults = {
            f"var_{i}": f"value_{i}" for i in range(10)
        }
        pack_defaults.update({
            f"list_var_{i}": f"list_value_{i}" for i in range(10)
        })
        
        result = resolver.resolve_data_structure(data, pack_defaults, "test_pack")
        
        # Verify a few random entries
        assert result["key_0"]["value"] == "value_0"
        assert result["key_5"]["nested"][0] == "list_value_5"
        assert len(result) == 10