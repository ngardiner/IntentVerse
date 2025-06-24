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
                "has_prompts": False
            }
        ]
        
        # Mock get_loaded_packs_info
        mock_cpm.get_loaded_packs_info.return_value = [
            {
                "path": "/path/to/test_pack.json",
                "metadata": {"name": "Test Pack", "version": "1.0.0"},
                "loaded_at": "2023-01-01T12:00:00"
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
                "prompts_preview": []
            }
        }
        
        # Mock remote content pack methods
        mock_cpm.list_remote_content_packs.return_value = [
            {
                "filename": "remote_pack.json",
                "metadata": {"name": "Remote Pack", "version": "1.0.0"},
                "source": "remote",
                "download_url": "https://example.com/remote_pack.json"
            }
        ]
        
        mock_cpm.get_remote_content_pack_info.return_value = {
            "filename": "remote_pack.json",
            "metadata": {"name": "Remote Pack", "version": "1.0.0"},
            "source": "remote",
            "download_url": "https://example.com/remote_pack.json"
        }
        
        mock_cpm.search_remote_content_packs.return_value = [
            {
                "filename": "remote_pack.json",
                "metadata": {"name": "Remote Pack", "version": "1.0.0"},
                "source": "remote",
                "download_url": "https://example.com/remote_pack.json"
            }
        ]
        
        mock_cpm.download_remote_content_pack.return_value = Path("/path/to/cache/remote_pack.json")
        mock_cpm.install_remote_content_pack.return_value = True
        
        mock_cpm.get_remote_repository_info.return_value = {
            "status": "available",
            "repository_url": "https://example.com/repo",
            "manifest_version": "1.0.0",
            "statistics": {"total_packs": 10}
        }
        
        mock_cpm.fetch_remote_manifest.return_value = {
            "content_packs": [{"filename": "remote_pack.json"}]
        }
        
        mock_cpm.clear_remote_cache.return_value = True
        
        return mock_cpm
    
    
    
    def test_get_ui_layout(self, service_client):
        """Test the UI layout endpoint."""
        with patch('app.main.module_loader') as mock_module_loader:
            mock_module_loader.get_schemas.return_value = {
                "test_module": {
                    "name": "test_module",
                    "description": "Test module"
                }
            }
            response = service_client.get("/api/v1/ui/layout")
            
            assert response.status_code == 200
            data = response.json()
            assert "modules" in data
            assert len(data["modules"]) == 1
            mock_module_loader.get_schemas.assert_called_once()
    
    def test_get_module_state_existing(self, service_client):
        """Test getting state for an existing module."""
        with patch('app.api.state_manager') as mock_state_manager:
            mock_state_manager.get.return_value = {"status": "ok", "data": "some_value"}
            response = service_client.get("/api/v1/test_module/state")

            assert response.status_code == 200
            assert response.json() == {"status": "ok", "data": "some_value"}
            mock_state_manager.get.assert_called_once_with("test_module")

    def test_get_module_state_nonexistent(self, service_client):
        """Test getting state for a non-existent module."""
        with patch('app.api.state_manager') as mock_state_manager:
            mock_state_manager.get.return_value = None
            
            response = service_client.get("/api/v1/nonexistent/state")
            
            assert response.status_code == 404
            assert "No state found for module: nonexistent" in response.json()["detail"]
    
    def test_get_tools_manifest(self, service_client):
        """Test the tools manifest endpoint."""
        with patch('app.main.module_loader') as mock_module_loader:
            mock_tool = MockTool(Mock())
            mock_module_loader.get_all_tools.return_value = {"test_module": mock_tool}
            
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
        with patch('app.main.module_loader') as mock_module_loader:
            mock_tool = MockTool(Mock())
            mock_module_loader.get_tool.return_value = mock_tool
            
            payload = {
                "tool_name": "test_module.simple_method",
                "parameters": {"param1": "test_value"}
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
            "parameters": {"param1": "test_value"}
        }
        
        response = service_client.post("/api/v1/execute", json=payload)
        
        assert response.status_code == 400
        assert "is required in the format 'module.method'" in response.json()["detail"]
    
    def test_execute_tool_nonexistent_tool(self, service_client):
        """Test tool execution with non-existent tool."""
        with patch('app.main.module_loader') as mock_module_loader:
            mock_module_loader.get_tool.return_value = None
            
            payload = {
                "tool_name": "nonexistent.method",
                "parameters": {"param1": "test_value"}
            }
            
            response = service_client.post("/api/v1/execute", json=payload)
            
            assert response.status_code == 404
            assert "Tool 'nonexistent.method' not found" in response.json()["detail"]
    
    def test_execute_tool_nonexistent_method(self, service_client):
        """Test tool execution with non-existent method."""
        with patch('app.main.module_loader') as mock_module_loader:
            mock_tool = MockTool(Mock())
            mock_module_loader.get_tool.return_value = mock_tool
            
            payload = {
                "tool_name": "test_module.nonexistent_method",
                "parameters": {"param1": "test_value"}
            }
            
            response = service_client.post("/api/v1/execute", json=payload)
            
            assert response.status_code == 404
            assert "Tool 'test_module.nonexistent_method' not found" in response.json()["detail"]
    
    def test_execute_tool_missing_required_parameter(self, service_client):
        """Test tool execution with missing required parameter."""
        with patch('app.main.module_loader') as mock_module_loader:
            mock_tool = MockTool(Mock())
            mock_module_loader.get_tool.return_value = mock_tool
            
            payload = {
                "tool_name": "test_module.simple_method",
                "parameters": {}  # Missing required param1
            }
            
            response = service_client.post("/api/v1/execute", json=payload)
            
            assert response.status_code == 422
            assert "Missing required parameter" in response.json()["detail"]
            assert "param1" in response.json()["detail"]
    
    def test_execute_tool_with_optional_parameters(self, service_client):
        """Test tool execution with optional parameters."""
        with patch('app.main.module_loader') as mock_module_loader:
            mock_tool = MockTool(Mock())
            mock_module_loader.get_tool.return_value = mock_tool
            
            payload = {
                "tool_name": "test_module.method_with_optional",
                "parameters": {"required": "test_value"}
            }
            
            response = service_client.post("/api/v1/execute", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["result"]["required"] == "test_value"
            assert data["result"]["optional"] == "default"
    
    def test_execute_tool_with_all_parameters(self, service_client):
        """Test tool execution with all parameters provided."""
        with patch('app.main.module_loader') as mock_module_loader:
            mock_tool = MockTool(Mock())
            mock_module_loader.get_tool.return_value = mock_tool
            
            payload = {
                "tool_name": "test_module.method_with_optional",
                "parameters": {"required": "test_value", "optional": "custom_value"}
            }
            
            response = service_client.post("/api/v1/execute", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["result"]["required"] == "test_value"
            assert data["result"]["optional"] == "custom_value"
    
    def test_execute_tool_method_raises_http_exception(self, service_client):
        """Test tool execution when method raises HTTPException."""
        with patch('app.main.module_loader') as mock_module_loader:
            mock_tool = Mock()
            mock_method = Mock(side_effect=HTTPException(status_code=400, detail="Tool error"))
            mock_tool.simple_method = mock_method
            
            # Mock the signature inspection
            mock_sig = Mock()
            mock_param = Mock()
            mock_param.name = "param1"
            mock_param.default = inspect.Parameter.empty
            mock_sig.parameters.values.return_value = [mock_param]
            
            mock_module_loader.get_tool.return_value = mock_tool
            
            with patch('app.api.inspect.signature', return_value=mock_sig):
                with patch('app.api.hasattr', return_value=True):
                    with patch('app.api.getattr', return_value=mock_method):
                        payload = {
                            "tool_name": "test_module.simple_method",
                            "parameters": {"param1": "test_value"}
                        }
                        
                        response = service_client.post("/api/v1/execute", json=payload)
            
            assert response.status_code == 400
            assert "Tool error" in response.json()["detail"]
    
    def test_execute_tool_method_raises_generic_exception(self, service_client):
        """Test tool execution when method raises a generic exception."""
        with patch('app.main.module_loader') as mock_module_loader:
            mock_tool = Mock()
            mock_method = Mock(side_effect=ValueError("Generic error"))
            mock_tool.simple_method = mock_method
            
            # Mock the signature inspection
            mock_sig = Mock()
            mock_param = Mock()
            mock_param.name = "param1"
            mock_param.default = inspect.Parameter.empty
            mock_sig.parameters.values.return_value = [mock_param]
            
            mock_module_loader.get_tool.return_value = mock_tool
            
            with patch('app.api.inspect.signature', return_value=mock_sig):
                with patch('app.api.hasattr', return_value=True):
                    with patch('app.api.getattr', return_value=mock_method):
                        payload = {
                            "tool_name": "test_module.simple_method",
                            "parameters": {"param1": "test_value"}
                        }
                        
                        response = service_client.post("/api/v1/execute", json=payload)
            
            assert response.status_code == 500
            assert "An error occurred while executing tool" in response.json()["detail"]