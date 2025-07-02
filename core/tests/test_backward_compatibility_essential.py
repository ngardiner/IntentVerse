"""
Essential backward compatibility tests for v1.1.0 content pack features.

Tests the core backward compatibility requirements for Step 11.
"""

import pytest
import tempfile
import json
import os
from pathlib import Path

from app.content_pack_manager import ContentPackManager
from app.content_pack_variables import ContentPackVariableManager
from app.variable_resolver import VariableResolver


class TestEssentialBackwardCompatibility:
    """Essential backward compatibility tests between v1.0.0 and v1.1.0 content packs."""

    @pytest.fixture
    def v10_content_pack_minimal(self):
        """Minimal v1.0.0 content pack."""
        return {
            "metadata": {
                "name": "Minimal v1.0 Pack",
                "version": "1.0.0",
                "description": "Minimal v1.0.0 content pack",
                "author": "Test Suite"
            },
            "prompts": [
                {
                    "id": "simple_prompt",
                    "title": "Simple Prompt",
                    "description": "A simple prompt",
                    "prompt": "This is a simple prompt without variables",
                    "category": "general"
                }
            ]
        }

    @pytest.fixture
    def v10_content_pack_complex(self):
        """Complex v1.0.0 content pack with all legacy features."""
        return {
            "metadata": {
                "name": "Complex v1.0 Pack",
                "version": "1.0.0",
                "description": "Complex v1.0.0 content pack with all features",
                "author": "Test Suite",
                "created_date": "2023-01-01",
                "tags": ["legacy", "complex"]
            },
            "prompts": [
                {
                    "id": "email_template",
                    "title": "Email Template",
                    "description": "Generate professional email template",
                    "prompt": "Create a professional email template for business communication",
                    "category": "communication",
                    "tags": ["email", "template", "business"]
                },
                {
                    "id": "report_template", 
                    "title": "Report Template",
                    "description": "Generate report template",
                    "prompt": "Create a structured report template with sections and formatting",
                    "category": "documentation",
                    "tags": ["report", "template", "documentation"]
                }
            ],
            "database": [
                {
                    "table": "legacy_data",
                    "data": [
                        {"id": 1, "name": "Test Item 1"},
                        {"id": 2, "name": "Test Item 2"}
                    ]
                }
            ],
            "state": {
                "initialized": True,
                "version": "1.0.0",
                "legacy_setting": "enabled"
            }
        }

    @pytest.fixture
    def v11_content_pack_with_variables(self):
        """v1.1.0 content pack with variables."""
        return {
            "metadata": {
                "name": "v1.1 Pack with Variables",
                "version": "1.1.0",
                "description": "v1.1.0 content pack with variables",
                "author": "Test Suite"
            },
            "variables": {
                "company_name": "ACME Corp",
                "email_domain": "acme.com"
            },
            "content_prompts": [
                {
                    "name": "Company Email",
                    "content": "Write an email from {{company_name}} using domain {{email_domain}}"
                }
            ],
            "usage_prompts": [
                {
                    "name": "Ask about company",
                    "content": "Tell me about {{company_name}}"
                }
            ]
        }

    @pytest.fixture
    def content_pack_manager(self, session):
        """Create a ContentPackManager instance."""
        from unittest.mock import MagicMock
        mock_state_manager = MagicMock()
        mock_module_loader = MagicMock()
        mock_database_tool = MagicMock()
        
        # Configure mocks to return JSON-serializable data
        mock_database_tool.export_database_content.return_value = []
        mock_module_loader.get_tool.return_value = mock_database_tool
        mock_state_manager.get_full_state.return_value = {
            "test_module": {"test_key": "test_value"}
        }
        
        return ContentPackManager(mock_state_manager, mock_module_loader)

    @pytest.fixture
    def variable_manager(self, session):
        """Create a ContentPackVariableManager instance."""
        return ContentPackVariableManager(session)

    def create_temp_pack_file(self, pack_data):
        """Helper to create temporary content pack file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(pack_data, f)
            return f.name

    def test_v10_pack_validation_passes(self, content_pack_manager, v10_content_pack_minimal, v10_content_pack_complex):
        """Test that v1.0.0 content packs pass validation."""
        # Test minimal pack
        validation_result = content_pack_manager.validate_content_pack_detailed(v10_content_pack_minimal)
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0
        
        # Test complex pack
        validation_result = content_pack_manager.validate_content_pack_detailed(v10_content_pack_complex)
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0

    def test_v10_pack_loading_works(self, content_pack_manager, v10_content_pack_minimal, v10_content_pack_complex):
        """Test that v1.0.0 content packs can be loaded successfully."""
        # Test minimal pack loading
        temp_file = self.create_temp_pack_file(v10_content_pack_minimal)
        try:
            result = content_pack_manager.load_content_pack(Path(temp_file))
            assert result is True
            
            # Verify pack is loaded
            loaded_packs = content_pack_manager.get_loaded_packs_info()
            pack_names = [pack['metadata'].get('name', '') for pack in loaded_packs]
            assert "Minimal v1.0 Pack" in pack_names
        finally:
            os.unlink(temp_file)
        
        # Test complex pack loading
        temp_file = self.create_temp_pack_file(v10_content_pack_complex)
        try:
            result = content_pack_manager.load_content_pack(Path(temp_file))
            assert result is True
            
            # Verify pack is loaded
            loaded_packs = content_pack_manager.get_loaded_packs_info()
            pack_names = [pack['metadata'].get('name', '') for pack in loaded_packs]
            assert "Complex v1.0 Pack" in pack_names
            
            # Verify the pack has legacy features
            loaded_pack = None
            for pack in loaded_packs:
                if pack['metadata'].get('name') == "Complex v1.0 Pack":
                    loaded_pack = pack
                    break
            
            assert loaded_pack is not None
            assert loaded_pack['has_legacy_prompts'] is True
        finally:
            os.unlink(temp_file)

    def test_v11_pack_with_variables_works(self, content_pack_manager, variable_manager, v11_content_pack_with_variables, test_user):
        """Test that v1.1.0 content packs with variables work correctly."""
        # Test validation
        validation_result = content_pack_manager.validate_content_pack_detailed(v11_content_pack_with_variables)
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0
        
        # Test loading
        temp_file = self.create_temp_pack_file(v11_content_pack_with_variables)
        try:
            result = content_pack_manager.load_content_pack(Path(temp_file), user_id=test_user.id)
            assert result is True
            
            # Verify pack is loaded with variable features
            loaded_packs = content_pack_manager.get_loaded_packs_info()
            loaded_pack = None
            for pack in loaded_packs:
                if pack['metadata'].get('name') == "v1.1 Pack with Variables":
                    loaded_pack = pack
                    break
            
            assert loaded_pack is not None
            assert loaded_pack['has_variables'] is True
            assert loaded_pack['has_content_prompts'] is True
            assert loaded_pack['has_usage_prompts'] is True
        finally:
            os.unlink(temp_file)

    def test_variable_system_works(self, content_pack_manager, variable_manager, v11_content_pack_with_variables, test_user):
        """Test that the variable system works end-to-end."""
        pack_name = "v1.1 Pack with Variables"
        
        # Load pack with variables
        temp_file = self.create_temp_pack_file(v11_content_pack_with_variables)
        try:
            result = content_pack_manager.load_content_pack(Path(temp_file), user_id=test_user.id)
            assert result is True
        finally:
            os.unlink(temp_file)
        
        # Test getting pack variables (should be empty initially)
        variables = variable_manager.get_pack_variables(pack_name, test_user.id)
        assert variables == {}
        
        # Test setting a variable override
        success = variable_manager.set_variable_value(pack_name, "company_name", "Custom Corp", test_user.id)
        assert success is True
        
        # Test getting variables after override
        variables = variable_manager.get_pack_variables(pack_name, test_user.id)
        assert variables["company_name"] == "Custom Corp"
        
        # Test variable resolution
        resolver = VariableResolver(variable_manager)
        pack_defaults = {"company_name": "ACME Corp", "email_domain": "acme.com"}
        
        # Should use user override for company_name, default for email_domain
        resolved_text = resolver.resolve_string(
            "Company: {{company_name}}, Email: user@{{email_domain}}", 
            pack_defaults, 
            pack_name, 
            test_user.id
        )
        assert resolved_text == "Company: Custom Corp, Email: user@acme.com"

    def test_backward_compatibility_no_errors(self, content_pack_manager, v10_content_pack_minimal):
        """Test that v1.0.0 content packs don't cause errors in v1.1.0 system."""
        # This is the core backward compatibility requirement
        temp_file = self.create_temp_pack_file(v10_content_pack_minimal)
        try:
            # Should validate without errors
            validation_result = content_pack_manager.validate_content_pack_detailed(v10_content_pack_minimal)
            assert validation_result["is_valid"] is True
            
            # Should load without errors
            result = content_pack_manager.load_content_pack(Path(temp_file))
            assert result is True
            
            # Should appear in loaded packs
            loaded_packs = content_pack_manager.get_loaded_packs_info()
            assert len(loaded_packs) > 0
            
            # Should have correct metadata
            pack = loaded_packs[0]
            assert pack['metadata']['name'] == "Minimal v1.0 Pack"
            assert pack['has_legacy_prompts'] is True
            assert pack['has_variables'] is False
            assert pack['has_content_prompts'] is False
            assert pack['has_usage_prompts'] is False
            
        finally:
            os.unlink(temp_file)