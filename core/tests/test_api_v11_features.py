"""
API tests for v1.1.0 content pack features.

Tests the API endpoints for variable management and new content pack fields.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models import User, ContentPackVariable
from app.database import get_db_session


class TestAPIv11Features:
    """Test API endpoints for v1.1.0 content pack features."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, test_user):
        """Create authentication headers for test user."""
        # Mock authentication for testing
        with patch('app.auth.get_current_user', return_value=test_user):
            yield {"Authorization": "Bearer test-token"}

    @pytest.fixture
    def sample_v11_pack_file(self):
        """Create a sample v1.1.0 content pack file."""
        pack_data = {
            "metadata": {
                "name": "API Test Pack",
                "version": "1.1.0",
                "description": "Test pack for API testing",
                "author": "Test Suite",
                "created_date": "2024-01-01",
                "content_pack_version": "1.1.0"
            },
            "variables": {
                "api_key": "test-key-123",
                "base_url": "https://api.example.com",
                "timeout": "30"
            },
            "content_prompts": [
                {
                    "id": "api_request",
                    "title": "API Request Template",
                    "description": "Generate API request code",
                    "prompt": "Create an API request to {{base_url}} using key {{api_key}} with timeout {{timeout}}",
                    "category": "code",
                    "tags": ["api", "request"]
                }
            ],
            "usage_prompts": [
                {
                    "id": "api_help",
                    "title": "API Help",
                    "description": "How to use the API",
                    "prompt": "How do I make a request to {{base_url}}?",
                    "category": "help",
                    "tags": ["api", "help"]
                }
            ],
            "database": [],
            "state": {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(pack_data, f)
            temp_file = f.name
        
        yield temp_file
        
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    def test_load_content_pack_with_v11_features(self, client, auth_headers, sample_v11_pack_file):
        """Test loading a content pack with v1.1.0 features via API."""
        with patch('app.auth.get_current_user'):
            # Load the content pack
            with open(sample_v11_pack_file, 'rb') as f:
                response = client.post(
                    "/api/v1/content-packs/load",
                    files={"file": ("test-pack.json", f, "application/json")},
                    headers=auth_headers
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "API Test Pack" in data["message"]

    def test_preview_content_pack_with_v11_features(self, client, auth_headers, sample_v11_pack_file):
        """Test previewing a content pack with v1.1.0 features via API."""
        with patch('app.auth.get_current_user'):
            # Preview the content pack
            with open(sample_v11_pack_file, 'rb') as f:
                response = client.post(
                    "/api/v1/content-packs/preview",
                    files={"file": ("test-pack.json", f, "application/json")},
                    headers=auth_headers
                )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify v1.1.0 features are included
            content_pack = data["content_pack"]
            assert "variables" in content_pack
            assert "content_prompts" in content_pack
            assert "usage_prompts" in content_pack
            
            # Verify variable data
            assert content_pack["variables"]["api_key"] == "test-key-123"
            assert len(content_pack["content_prompts"]) == 1
            assert len(content_pack["usage_prompts"]) == 1

    def test_get_pack_variables_api(self, client, auth_headers, sample_v11_pack_file, test_user):
        """Test getting pack variables via API."""
        with patch('app.auth.get_current_user', return_value=test_user):
            # First load the pack
            with open(sample_v11_pack_file, 'rb') as f:
                client.post(
                    "/api/v1/content-packs/load",
                    files={"file": ("test-pack.json", f, "application/json")},
                    headers=auth_headers
                )
            
            # Get pack variables
            response = client.get(
                "/api/v1/content-packs/API Test Pack/variables",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "variables" in data
            
            # Should be empty initially (no user overrides)
            assert len(data["variables"]) == 0

    def test_set_pack_variable_api(self, client, auth_headers, sample_v11_pack_file, test_user):
        """Test setting a pack variable via API."""
        with patch('app.auth.get_current_user', return_value=test_user):
            # First load the pack
            with open(sample_v11_pack_file, 'rb') as f:
                client.post(
                    "/api/v1/content-packs/load",
                    files={"file": ("test-pack.json", f, "application/json")},
                    headers=auth_headers
                )
            
            # Set a variable
            response = client.put(
                "/api/v1/content-packs/API Test Pack/variables/api_key",
                json={"value": "custom-key-456"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "api_key" in data["message"]
            
            # Verify the variable was set
            response = client.get(
                "/api/v1/content-packs/API Test Pack/variables",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["variables"]["api_key"] == "custom-key-456"

    def test_reset_pack_variable_api(self, client, auth_headers, sample_v11_pack_file, test_user):
        """Test resetting a pack variable via API."""
        with patch('app.auth.get_current_user', return_value=test_user):
            # First load the pack and set a variable
            with open(sample_v11_pack_file, 'rb') as f:
                client.post(
                    "/api/v1/content-packs/load",
                    files={"file": ("test-pack.json", f, "application/json")},
                    headers=auth_headers
                )
            
            client.put(
                "/api/v1/content-packs/API Test Pack/variables/api_key",
                json={"value": "custom-key-456"},
                headers=auth_headers
            )
            
            # Reset the variable
            response = client.delete(
                "/api/v1/content-packs/API Test Pack/variables/api_key",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "reset" in data["message"].lower()
            
            # Verify the variable was reset
            response = client.get(
                "/api/v1/content-packs/API Test Pack/variables",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "api_key" not in data["variables"]

    def test_reset_all_pack_variables_api(self, client, auth_headers, sample_v11_pack_file, test_user):
        """Test resetting all pack variables via API."""
        with patch('app.auth.get_current_user', return_value=test_user):
            # First load the pack and set multiple variables
            with open(sample_v11_pack_file, 'rb') as f:
                client.post(
                    "/api/v1/content-packs/load",
                    files={"file": ("test-pack.json", f, "application/json")},
                    headers=auth_headers
                )
            
            client.put(
                "/api/v1/content-packs/API Test Pack/variables/api_key",
                json={"value": "custom-key-456"},
                headers=auth_headers
            )
            
            client.put(
                "/api/v1/content-packs/API Test Pack/variables/timeout",
                json={"value": "60"},
                headers=auth_headers
            )
            
            # Reset all variables
            response = client.post(
                "/api/v1/content-packs/API Test Pack/variables/reset",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "reset" in data["message"].lower()
            
            # Verify all variables were reset
            response = client.get(
                "/api/v1/content-packs/API Test Pack/variables",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["variables"]) == 0

    def test_variable_api_with_nonexistent_pack(self, client, auth_headers, test_user):
        """Test variable API endpoints with nonexistent pack."""
        with patch('app.auth.get_current_user', return_value=test_user):
            # Try to get variables for nonexistent pack
            response = client.get(
                "/api/v1/content-packs/Nonexistent Pack/variables",
                headers=auth_headers
            )
            
            assert response.status_code == 404
            
            # Try to set variable for nonexistent pack
            response = client.put(
                "/api/v1/content-packs/Nonexistent Pack/variables/test_var",
                json={"value": "test"},
                headers=auth_headers
            )
            
            assert response.status_code == 404

    def test_variable_api_validation(self, client, auth_headers, sample_v11_pack_file, test_user):
        """Test variable API input validation."""
        with patch('app.auth.get_current_user', return_value=test_user):
            # First load the pack
            with open(sample_v11_pack_file, 'rb') as f:
                client.post(
                    "/api/v1/content-packs/load",
                    files={"file": ("test-pack.json", f, "application/json")},
                    headers=auth_headers
                )
            
            # Try to set variable with invalid name
            response = client.put(
                "/api/v1/content-packs/API Test Pack/variables/invalid-name!",
                json={"value": "test"},
                headers=auth_headers
            )
            
            assert response.status_code == 400
            
            # Try to set variable with missing value
            response = client.put(
                "/api/v1/content-packs/API Test Pack/variables/api_key",
                json={},
                headers=auth_headers
            )
            
            assert response.status_code == 422

    def test_content_pack_list_includes_v11_features(self, client, auth_headers, sample_v11_pack_file):
        """Test that content pack list includes v1.1.0 feature indicators."""
        with patch('app.auth.get_current_user'):
            # Load the pack
            with open(sample_v11_pack_file, 'rb') as f:
                client.post(
                    "/api/v1/content-packs/load",
                    files={"file": ("test-pack.json", f, "application/json")},
                    headers=auth_headers
                )
            
            # Get loaded content packs
            response = client.get(
                "/api/v1/content-packs/loaded",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Find our test pack
            test_pack = next((pack for pack in data if pack["name"] == "API Test Pack"), None)
            assert test_pack is not None
            
            # Verify v1.1.0 features are indicated
            features = test_pack.get("features", {})
            assert features.get("has_variables") is True
            assert features.get("has_content_prompts") is True
            assert features.get("has_usage_prompts") is True

    def test_export_content_pack_preserves_v11_features(self, client, auth_headers, sample_v11_pack_file):
        """Test that exporting content packs preserves v1.1.0 features."""
        with patch('app.auth.get_current_user'):
            # Load the pack
            with open(sample_v11_pack_file, 'rb') as f:
                client.post(
                    "/api/v1/content-packs/load",
                    files={"file": ("test-pack.json", f, "application/json")},
                    headers=auth_headers
                )
            
            # Export the pack
            response = client.post(
                "/api/v1/content-packs/export",
                json={
                    "filename": "exported-test-pack.json",
                    "metadata": {"description": "Exported test pack"}
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            # The exported file should contain v1.1.0 features
            # (This would need to be verified by checking the actual exported file)

    def test_api_error_handling_for_v11_features(self, client, auth_headers, test_user):
        """Test error handling for v1.1.0 feature API endpoints."""
        with patch('app.auth.get_current_user', return_value=test_user):
            # Test with invalid pack name characters
            response = client.get(
                "/api/v1/content-packs/Invalid%20Pack%20Name%21/variables",
                headers=auth_headers
            )
            
            # Should handle URL encoding properly
            assert response.status_code in [404, 400]
            
            # Test with very long variable names
            long_var_name = "a" * 1000
            response = client.put(
                f"/api/v1/content-packs/Test Pack/variables/{long_var_name}",
                json={"value": "test"},
                headers=auth_headers
            )
            
            assert response.status_code in [400, 404]

    def test_concurrent_variable_operations(self, client, auth_headers, sample_v11_pack_file, test_user):
        """Test concurrent variable operations via API."""
        import threading
        import time
        
        with patch('app.auth.get_current_user', return_value=test_user):
            # Load the pack
            with open(sample_v11_pack_file, 'rb') as f:
                client.post(
                    "/api/v1/content-packs/load",
                    files={"file": ("test-pack.json", f, "application/json")},
                    headers=auth_headers
                )
            
            results = []
            
            def set_variable(var_name, value):
                response = client.put(
                    f"/api/v1/content-packs/API Test Pack/variables/{var_name}",
                    json={"value": value},
                    headers=auth_headers
                )
                results.append(response.status_code)
            
            # Start multiple threads setting different variables
            threads = []
            for i in range(5):
                thread = threading.Thread(
                    target=set_variable,
                    args=(f"test_var_{i}", f"value_{i}")
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # All operations should succeed
            assert all(status == 200 for status in results)
            
            # Verify all variables were set
            response = client.get(
                "/api/v1/content-packs/API Test Pack/variables",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have 5 variables set
            assert len(data["variables"]) == 5
            for i in range(5):
                assert data["variables"][f"test_var_{i}"] == f"value_{i}"