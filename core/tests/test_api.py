"""
Unit tests for the API layer.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
import inspect
import os

from app.api import create_api_routes
from app.module_loader import ModuleLoader
from app.state_manager import StateManager
from app.modules.base_tool import BaseTool
from app.content_pack_manager import ContentPackManager
from app.auth import get_current_user, get_current_user_or_service, User
from app.database import get_session


class MockTool(BaseTool):
    """A mock tool for testing API functionality."""

    def __init__(self, state_manager):
        super().__init__(state_manager)

    def simple_method(self, param1: str) -> str:
        """A simple method for testing."""
        return f"Result: {param1}"

    def method_with_optional(self, required: str, optional: str = "default") -> dict:
        """A method with optional parameters."""
        return {"required": required, "optional": optional}

    def method_with_union(self, value: str | int) -> str:
        """A method with union type parameter."""
        return f"Value: {value}"


class TestAPIRoutes:
    """Test the API routes creation and functionality."""

    @pytest.fixture
    def mock_content_pack_manager(self):
        """Create a mock content pack manager."""
        mock_cpm = Mock(spec=ContentPackManager)

        # Mock list_available_content_packs
        mock_cpm.list_available_content_packs.return_value = [
            {
                "filename": "test_pack.json",
                "path": "/path/to/test_pack.json",
                "metadata": {"name": "Test Pack", "version": "1.0.0"},
                "has_database": True,
                "has_state": True,
                "has_prompts": False,
            }
        ]

        # Mock get_loaded_packs_info
        mock_cpm.get_loaded_packs_info.return_value = [
            {
                "path": "/path/to/test_pack.json",
                "metadata": {"name": "Test Pack", "version": "1.0.0"},
                "loaded_at": "2023-01-01T12:00:00",
            }
        ]

        # Mock export_content_pack
        mock_cpm.export_content_pack.return_value = True
        mock_cpm.content_packs_dir = Path("/path/to/content_packs")

        # Mock load_content_pack_by_filename
        mock_cpm.load_content_pack_by_filename.return_value = True

        # Mock unload_content_pack
        mock_cpm.unload_content_pack.return_value = True

        # Mock clear_all_loaded_packs
        mock_cpm.clear_all_loaded_packs.return_value = True

        # Mock preview_content_pack
        mock_cpm.preview_content_pack.return_value = {
            "filename": "test_pack.json",
            "exists": True,
            "content_pack": {"metadata": {"name": "Test Pack"}},
            "validation": {"is_valid": True, "errors": [], "warnings": []},
            "preview": {
                "metadata": {"name": "Test Pack"},
                "database_preview": ["CREATE TABLE test (id INTEGER)"],
                "state_preview": {"test_module": {"keys": ["key1"]}},
                "prompts_preview": [],
            },
        }

        # Mock remote content pack methods
        mock_cpm.list_remote_content_packs.return_value = [
            {
                "filename": "remote_pack.json",
                "metadata": {"name": "Remote Pack", "version": "1.0.0"},
                "source": "remote",
                "download_url": "https://example.com/remote_pack.json",
            }
        ]

        mock_cpm.get_remote_content_pack_info.return_value = {
            "filename": "remote_pack.json",
            "metadata": {"name": "Remote Pack", "version": "1.0.0"},
            "source": "remote",
            "download_url": "https://example.com/remote_pack.json",
        }

        mock_cpm.search_remote_content_packs.return_value = [
            {
                "filename": "remote_pack.json",
                "metadata": {"name": "Remote Pack", "version": "1.0.0"},
                "source": "remote",
                "download_url": "https://example.com/remote_pack.json",
            }
        ]

        mock_cpm.download_remote_content_pack.return_value = Path(
            "/path/to/cache/remote_pack.json"
        )
        mock_cpm.install_remote_content_pack.return_value = True

        mock_cpm.get_remote_repository_info.return_value = {
            "status": "available",
            "repository_url": "https://example.com/repo",
            "manifest_version": "1.0.0",
            "statistics": {"total_packs": 10},
        }

        mock_cpm.fetch_remote_manifest.return_value = {
            "content_packs": [{"filename": "remote_pack.json"}]
        }

        mock_cpm.clear_remote_cache.return_value = True

        return mock_cpm

    def test_get_ui_layout(self, service_client):
        """Test the UI layout endpoint."""
        # Import the actual module_loader instance from main
        from app.main import module_loader

        # Patch the method on the actual instance
        with patch.object(module_loader, "get_schemas") as mock_get_schemas:
            mock_get_schemas.return_value = {
                "test_module": {"name": "test_module", "description": "Test module"}
            }
            response = service_client.get("/api/v1/ui/layout")

            assert response.status_code == 200
            data = response.json()
            assert "modules" in data
            assert len(data["modules"]) == 1
            mock_get_schemas.assert_called_once()

    def test_get_module_state_existing(self, service_client):
        """Test getting state for an existing module."""
        with patch("app.api.state_manager") as mock_state_manager:
            mock_state_manager.get.return_value = {"status": "ok", "data": "some_value"}
            response = service_client.get("/api/v1/test_module/state")

            assert response.status_code == 200
            assert response.json() == {"status": "ok", "data": "some_value"}
            mock_state_manager.get.assert_called_once_with("test_module")

    def test_get_module_state_nonexistent(self, service_client):
        """Test getting state for a non-existent module."""
        with patch("app.api.state_manager") as mock_state_manager:
            mock_state_manager.get.return_value = None

            response = service_client.get("/api/v1/nonexistent/state")

            assert response.status_code == 404
            assert "No state found for module: nonexistent" in response.json()["detail"]

    def test_get_tools_manifest(self, service_client):
        """Test the tools manifest endpoint."""
        # Import the actual module_loader instance from main
        from app.main import module_loader

        # Patch the method on the actual instance
        with patch.object(module_loader, "get_all_tools") as mock_get_all_tools:
            mock_tool = MockTool(Mock())
            mock_get_all_tools.return_value = {"test_module": mock_tool}

            response = service_client.get("/api/v1/tools/manifest")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

            # Check that our mock tool methods are in the manifest
            method_names = [tool["name"] for tool in data]
            assert "test_module.simple_method" in method_names
            assert "test_module.method_with_optional" in method_names
            assert "test_module.method_with_union" in method_names

            # Check parameter information
            simple_method_manifest = next(
                tool for tool in data if tool["name"] == "test_module.simple_method"
            )
            assert len(simple_method_manifest["parameters"]) == 1
            assert simple_method_manifest["parameters"][0]["name"] == "param1"
            assert simple_method_manifest["parameters"][0]["required"] is True

    def test_execute_tool_success(self, service_client):
        """Test successful tool execution."""
        # Import the actual module_loader instance from main
        from app.main import module_loader

        # Patch the method on the actual instance
        with patch.object(module_loader, "get_tool") as mock_get_tool:
            mock_tool = MockTool(Mock())
            mock_get_tool.return_value = mock_tool

            payload = {
                "tool_name": "test_module.simple_method",
                "parameters": {"param1": "test_value"},
            }

            response = service_client.post("/api/v1/execute", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["result"] == "Result: test_value"

    def test_execute_tool_missing_tool_name(self, service_client):
        """Test tool execution without tool_name."""
        payload = {"parameters": {"param1": "test_value"}}

        response = service_client.post("/api/v1/execute", json=payload)

        assert response.status_code == 400
        assert "`tool_name` is required" in response.json()["detail"]

    def test_execute_tool_invalid_tool_name_format(self, service_client):
        """Test tool execution with invalid tool_name format."""
        payload = {
            "tool_name": "invalid_format",
            "parameters": {"param1": "test_value"},
        }

        response = service_client.post("/api/v1/execute", json=payload)

        assert response.status_code == 400
        assert "is required in the format 'module.method'" in response.json()["detail"]

    def test_execute_tool_nonexistent_tool(self, service_client):
        """Test tool execution with non-existent tool."""
        # Import the actual module_loader instance from main
        from app.main import module_loader

        # Patch the method on the actual instance
        with patch.object(module_loader, "get_tool") as mock_get_tool:
            mock_get_tool.return_value = None

            payload = {
                "tool_name": "nonexistent.method",
                "parameters": {"param1": "test_value"},
            }

            response = service_client.post("/api/v1/execute", json=payload)

            assert response.status_code == 404
            assert "Tool 'nonexistent.method' not found" in response.json()["detail"]

    def test_execute_tool_nonexistent_method(self, service_client):
        """Test tool execution with non-existent method."""
        with patch("app.main.module_loader") as mock_module_loader:
            mock_tool = MockTool(Mock())
            mock_module_loader.get_tool.return_value = mock_tool

            payload = {
                "tool_name": "test_module.nonexistent_method",
                "parameters": {"param1": "test_value"},
            }

            response = service_client.post("/api/v1/execute", json=payload)

            assert response.status_code == 404
            assert (
                "Tool 'test_module.nonexistent_method' not found"
                in response.json()["detail"]
            )

    def test_execute_tool_missing_required_parameter(self, service_client):
        """Test tool execution with missing required parameter."""
        # Import the actual module_loader instance from main
        from app.main import module_loader

        # Patch the method on the actual instance
        with patch.object(module_loader, "get_tool") as mock_get_tool:
            mock_tool = MockTool(Mock())
            mock_get_tool.return_value = mock_tool

            payload = {
                "tool_name": "test_module.simple_method",
                "parameters": {},  # Missing required param1
            }

            response = service_client.post("/api/v1/execute", json=payload)

            assert response.status_code == 422
            assert "Missing required parameter" in response.json()["detail"]
            assert "param1" in response.json()["detail"]

    def test_execute_tool_with_optional_parameters(self, service_client):
        """Test tool execution with optional parameters."""
        # Import the actual module_loader instance from main
        from app.main import module_loader

        # Patch the method on the actual instance
        with patch.object(module_loader, "get_tool") as mock_get_tool:
            mock_tool = MockTool(Mock())
            mock_get_tool.return_value = mock_tool

            payload = {
                "tool_name": "test_module.method_with_optional",
                "parameters": {"required": "test_value"},
            }

            response = service_client.post("/api/v1/execute", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["result"]["required"] == "test_value"
            assert data["result"]["optional"] == "default"

    def test_execute_tool_with_all_parameters(self, service_client):
        """Test tool execution with all parameters provided."""
        # Import the actual module_loader instance from main
        from app.main import module_loader

        # Patch the method on the actual instance
        with patch.object(module_loader, "get_tool") as mock_get_tool:
            mock_tool = MockTool(Mock())
            mock_get_tool.return_value = mock_tool

            payload = {
                "tool_name": "test_module.method_with_optional",
                "parameters": {"required": "test_value", "optional": "custom_value"},
            }

            response = service_client.post("/api/v1/execute", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["result"]["required"] == "test_value"
            assert data["result"]["optional"] == "custom_value"

    def test_execute_tool_method_raises_http_exception(self, service_client):
        """Test tool execution when method raises HTTPException."""
        # Import the actual module_loader instance from main
        from app.main import module_loader

        # Patch the method on the actual instance
        with patch.object(module_loader, "get_tool") as mock_get_tool:
            # Create a mock tool that raises HTTPException
            mock_tool = MockTool(Mock())

            # Create a proper mock function with the correct signature
            def mock_simple_method(param1: str) -> str:
                raise HTTPException(status_code=400, detail="Tool error")

            # Override the simple_method to raise HTTPException
            mock_tool.simple_method = mock_simple_method
            mock_get_tool.return_value = mock_tool

            payload = {
                "tool_name": "test_module.simple_method",
                "parameters": {"param1": "test_value"},
            }

            response = service_client.post("/api/v1/execute", json=payload)

            assert response.status_code == 400
            assert "Tool error" in response.json()["detail"]

    def test_execute_tool_method_raises_generic_exception(self, service_client):
        """Test tool execution when method raises a generic exception."""
        # Import the actual module_loader instance from main
        from app.main import module_loader

        # Patch the method on the actual instance
        with patch.object(module_loader, "get_tool") as mock_get_tool:
            # Create a mock tool that raises ValueError
            mock_tool = MockTool(Mock())

            # Create a proper mock function with the correct signature
            def mock_simple_method(param1: str) -> str:
                raise ValueError("Generic error")

            # Override the simple_method to raise ValueError
            mock_tool.simple_method = mock_simple_method
            mock_get_tool.return_value = mock_tool

            payload = {
                "tool_name": "test_module.simple_method",
                "parameters": {"param1": "test_value"},
            }

            response = service_client.post("/api/v1/execute", json=payload)

            assert response.status_code == 500
            assert "An error occurred while executing tool" in response.json()["detail"]


class TestContentPackVariableAPI:
    """Test the content pack variable management API endpoints."""

    @pytest.fixture
    def mock_content_pack_manager_with_variables(self):
        """Create a mock content pack manager with variable support."""
        mock_cpm = Mock(spec=ContentPackManager)
        
        # Mock variable management methods
        mock_cpm.get_pack_variables.return_value = {
            "email_domain": "example.com",
            "company_name": "ACME Corp"
        }
        mock_cpm.set_pack_variable.return_value = True
        mock_cpm.reset_pack_variables.return_value = True
        
        return mock_cpm

    @pytest.fixture
    def mock_variable_manager(self):
        """Create a mock variable manager."""
        mock_vm = Mock()
        mock_vm.delete_variable.return_value = True
        return mock_vm

    def test_get_pack_variables_success(self, authenticated_client, mock_content_pack_manager_with_variables, mock_variable_manager):
        """Test successful retrieval of pack variables."""
        from app.main import content_pack_manager as main_content_pack_manager
        
        # Patch the methods on the actual content_pack_manager instance
        with patch.object(main_content_pack_manager, 'get_loaded_content_packs', return_value=[{"name": "test_pack", "path": "/path/to/test_pack.json"}]):
            with patch.object(main_content_pack_manager, 'get_pack_variables', return_value={"email_domain": "example.com", "company_name": "ACME Corp"}):
                with patch('app.content_pack_variables.get_variable_manager', return_value=mock_variable_manager):
                    with patch('app.version_utils.supports_content_pack_variables', return_value=True):
                        response = authenticated_client.get("/api/v1/content-packs/test_pack/variables")
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert "status" in data
                        assert data["pack_name"] == "test_pack"
                        assert data["variables"]["email_domain"] == "example.com"
                        assert data["variables"]["company_name"] == "ACME Corp"
                        assert data["variable_count"] == 2
                        
                        # Check that get_pack_variables was called with the correct arguments (including session)
                        call_args = main_content_pack_manager.get_pack_variables.call_args
                        assert call_args[0][:2] == ("test_pack", 1)  # first two positional args
                        assert len(call_args[0]) == 3  # three positional args (pack_name, user_id, session)
                        # Third argument should be a session object
                        from sqlmodel.orm.session import Session
                        assert isinstance(call_args[0][2], Session)

    def test_get_pack_variables_not_supported(self, service_client, mock_content_pack_manager_with_variables, mock_variable_manager):
        """Test getting pack variables when feature is not supported."""
        with patch('app.content_pack_variables.get_variable_manager', return_value=mock_variable_manager):
            with patch('app.version_utils.supports_content_pack_variables', return_value=False):
                response = service_client.get("/api/v1/content-packs/test_pack/variables")
                
                assert response.status_code == 501
                assert "not supported in this version" in response.json()["detail"]

    def test_set_pack_variable_success(self, authenticated_client, mock_content_pack_manager_with_variables, mock_variable_manager):
        """Test successful setting of a pack variable."""
        from app.main import content_pack_manager as main_content_pack_manager
        
        with patch.object(main_content_pack_manager, 'get_loaded_content_packs', return_value=[{"name": "test_pack", "path": "/path/to/test_pack.json"}]):
            with patch.object(main_content_pack_manager, 'set_pack_variable', return_value=True):
                with patch('app.content_pack_variables.get_variable_manager', return_value=mock_variable_manager):
                    with patch('app.version_utils.supports_content_pack_variables', return_value=True):
                        payload = {"value": "new_value"}
                        response = authenticated_client.put("/api/v1/content-packs/test_pack/variables/test_var", json=payload)
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert "status" in data
                        assert data["pack_name"] == "test_pack"
                        assert data["variable_name"] == "test_var"
                        assert data["variable_value"] == "new_value"
                        
                        # Check that set_pack_variable was called with the correct arguments (including session)
                        call_args = main_content_pack_manager.set_pack_variable.call_args
                        assert call_args[0][:4] == ("test_pack", "test_var", "new_value", 1)  # first four positional args
                        assert len(call_args[0]) == 5  # five positional args (pack_name, variable_name, value, user_id, session)
                        # Fifth argument should be a session object
                        from sqlmodel.orm.session import Session
                        assert isinstance(call_args[0][4], Session)

    def test_set_pack_variable_missing_value(self, authenticated_client, mock_content_pack_manager_with_variables, mock_variable_manager):
        """Test setting a pack variable without providing a value."""
        from app.main import content_pack_manager as main_content_pack_manager
        
        with patch.object(main_content_pack_manager, 'get_loaded_content_packs', return_value=[{"name": "test_pack", "path": "/path/to/test_pack.json"}]):
            with patch('app.content_pack_variables.get_variable_manager', return_value=mock_variable_manager):
                with patch('app.version_utils.supports_content_pack_variables', return_value=True):
                    payload = {}
                    response = authenticated_client.put("/api/v1/content-packs/test_pack/variables/test_var", json=payload)
                    
                    assert response.status_code == 422
                    assert "Variable value is required" in response.json()["detail"]

    def test_set_pack_variable_failure(self, authenticated_client, mock_content_pack_manager_with_variables, mock_variable_manager):
        """Test setting a pack variable when the operation fails."""
        from app.main import content_pack_manager as main_content_pack_manager
        
        with patch.object(main_content_pack_manager, 'get_loaded_content_packs', return_value=[{"name": "test_pack", "path": "/path/to/test_pack.json"}]):
            with patch.object(main_content_pack_manager, 'set_pack_variable', return_value=False):
                with patch('app.content_pack_variables.get_variable_manager', return_value=mock_variable_manager):
                    with patch('app.version_utils.supports_content_pack_variables', return_value=True):
                        payload = {"value": "new_value"}
                        response = authenticated_client.put("/api/v1/content-packs/test_pack/variables/test_var", json=payload)
                        
                        assert response.status_code == 500
                        assert "Failed to set variable" in response.json()["detail"]

    def test_reset_pack_variable_success(self, authenticated_client, mock_content_pack_manager_with_variables, mock_variable_manager):
        """Test successful reset of a pack variable."""
        from app.main import content_pack_manager as main_content_pack_manager
        
        with patch.object(main_content_pack_manager, 'get_loaded_content_packs', return_value=[{"name": "test_pack", "path": "/path/to/test_pack.json"}]):
            with patch('app.content_pack_variables.get_variable_manager', return_value=mock_variable_manager):
                with patch('app.version_utils.supports_content_pack_variables', return_value=True):
                    # Set the delete_variable to return True to simulate success
                    mock_variable_manager.delete_variable.return_value = True
                    
                    response = authenticated_client.delete("/api/v1/content-packs/test_pack/variables/test_var")
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert "success" in data
                    assert data["pack_name"] == "test_pack"
                    assert data["variable_name"] == "test_var"
                    assert "reset to default value" in data["message"]
                    
                    mock_variable_manager.delete_variable.assert_called_once_with("test_pack", "test_var", 1)

    def test_reset_pack_variable_not_found(self, authenticated_client, mock_content_pack_manager_with_variables, mock_variable_manager):
        """Test resetting a pack variable that doesn't exist."""
        with patch.object(mock_variable_manager, 'delete_variable', return_value=False):
            with patch('app.content_pack_variables.get_variable_manager', return_value=mock_variable_manager):
                with patch('app.version_utils.supports_content_pack_variables', return_value=True):
                    response = authenticated_client.delete("/api/v1/content-packs/test_pack/variables/test_var")
                    
                    assert response.status_code == 404
                    assert "not found" in response.json()["detail"]

    def test_reset_all_pack_variables_success(self, authenticated_client, mock_content_pack_manager_with_variables, mock_variable_manager):
        """Test successful reset of all pack variables."""
        from app.main import content_pack_manager as main_content_pack_manager
        
        with patch.object(main_content_pack_manager, 'get_loaded_content_packs', return_value=[{"name": "test_pack", "path": "/path/to/test_pack.json"}]):
            with patch.object(main_content_pack_manager, 'reset_pack_variables', return_value=True):
                with patch('app.content_pack_variables.get_variable_manager', return_value=mock_variable_manager):
                    with patch('app.version_utils.supports_content_pack_variables', return_value=True):
                        response = authenticated_client.post("/api/v1/content-packs/test_pack/variables/reset")
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert "success" in data
                        assert data["pack_name"] == "test_pack"
                        assert "All variables reset" in data["message"]
                        
                        # Check that reset_pack_variables was called with the correct arguments (including session)
                        call_args = main_content_pack_manager.reset_pack_variables.call_args
                        assert call_args[0][:2] == ("test_pack", 1)  # first two positional args
                        assert len(call_args[0]) == 3  # three positional args (pack_name, user_id, session)
                        # Third argument should be a session object
                        from sqlmodel.orm.session import Session
                        assert isinstance(call_args[0][2], Session)

    def test_reset_all_pack_variables_failure(self, authenticated_client, mock_content_pack_manager_with_variables, mock_variable_manager):
        """Test resetting all pack variables when the operation fails."""
        from app.main import content_pack_manager as main_content_pack_manager
        
        with patch.object(main_content_pack_manager, 'get_loaded_content_packs', return_value=[{"name": "test_pack", "path": "/path/to/test_pack.json"}]):
            with patch.object(main_content_pack_manager, 'reset_pack_variables', return_value=False):
                with patch('app.content_pack_variables.get_variable_manager', return_value=mock_variable_manager):
                    with patch('app.version_utils.supports_content_pack_variables', return_value=True):
                        response = authenticated_client.post("/api/v1/content-packs/test_pack/variables/reset")
                        
                        assert response.status_code == 500
                        assert "Failed to reset variables" in response.json()["detail"]

    def test_variable_endpoints_require_user_auth(self, service_client, mock_content_pack_manager_with_variables, mock_variable_manager):
        """Test that variable endpoints require user authentication (not service auth)."""
        with patch('app.main.content_pack_manager', mock_content_pack_manager_with_variables):
            with patch('app.content_pack_variables.get_variable_manager', return_value=mock_variable_manager):
                with patch('app.version_utils.supports_content_pack_variables', return_value=True):
                    # Test all variable endpoints with service auth
                    response = service_client.get("/api/v1/content-packs/test_pack/variables")
                    assert response.status_code == 400
                    assert "User authentication required" in response.json()["detail"]
                    
                    response = service_client.put("/api/v1/content-packs/test_pack/variables/test_var", json={"value": "test"})
                    assert response.status_code == 400
                    assert "User authentication required" in response.json()["detail"]
                    
                    response = service_client.delete("/api/v1/content-packs/test_pack/variables/test_var")
                    assert response.status_code == 400
                    assert "User authentication required" in response.json()["detail"]
                    
                    response = service_client.post("/api/v1/content-packs/test_pack/variables/reset")
                    assert response.status_code == 400
                    assert "User authentication required" in response.json()["detail"]
