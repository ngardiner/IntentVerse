"""
Tests for server diagnostics endpoints.

This test file includes:
1. TestServerDiagnosticsUnit: Fast unit tests that directly test the debug endpoint function
2. TestServerDiagnosticsIntegration: Integration tests using TestClient with mocked dependencies  
3. test_server_module_loader_diagnostics: E2E test that connects to a running service (skipped if unavailable)

The unit tests use database mocking similar to the auth test cases to avoid 
database dependencies and improve test performance and reliability.
"""
import os
import httpx
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import User

# The base URL for the core API, which the test client will target.
# It uses the service name 'core' from docker-compose, which Docker's internal DNS resolves.
CORE_API_URL = os.environ.get("CORE_API_URL", "http://core:8000")

# For e2e tests, use the environment variable value (which will be set correctly in docker-compose)
# or fall back to the same default as the auth module
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "dev-service-key-12345")

def get_service_headers():
    """Get headers with service API key for authentication."""
    return {"X-API-Key": SERVICE_API_KEY}


@pytest.mark.unit
class TestServerDiagnosticsUnit:
    """Unit tests for server diagnostics endpoints using mocked dependencies."""
    
    @pytest.fixture
    def mock_auth_user(self):
        """Create a mock authenticated user."""
        return User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_admin=False
        )
    
    def test_debug_module_loader_state_function_success(self, mock_auth_user):
        """Test the debug module loader state function directly with successful module loading."""
        from app.main import get_module_loader_state
        
        # Mock the module loader to simulate successful loading
        with patch('app.main.module_loader') as mock_module_loader:
            mock_module_loader.modules_path.exists.return_value = True
            mock_module_loader.modules_path.__str__.return_value = "/app/modules"
            mock_module_loader.errors = []
            mock_module_loader.modules = {
                "filesystem": Mock(),
                "database": Mock(),
                "email": Mock()
            }
            
            result = get_module_loader_state(current_user_or_service=mock_auth_user)
            
            # Verify the response structure
            assert "modules_path_calculated" in result
            assert "modules_path_exists" in result
            assert "loading_errors" in result
            assert "loaded_modules" in result
            
            # Verify the values
            assert result["modules_path_calculated"] == "/app/modules"
            assert result["modules_path_exists"] is True
            assert result["loading_errors"] == []
            assert len(result["loaded_modules"]) == 3
            assert "filesystem" in result["loaded_modules"]
            assert "database" in result["loaded_modules"]
            assert "email" in result["loaded_modules"]
    
    def test_debug_module_loader_state_function_with_errors(self, mock_auth_user):
        """Test the debug module loader state function with loading errors."""
        from app.main import get_module_loader_state
        
        # Mock the module loader to simulate errors
        with patch('app.main.module_loader') as mock_module_loader:
            mock_module_loader.modules_path.exists.return_value = True
            mock_module_loader.modules_path.__str__.return_value = "/app/modules"
            mock_module_loader.errors = ["Failed to load module 'broken_module': ImportError"]
            mock_module_loader.modules = {"filesystem": Mock()}
            
            result = get_module_loader_state(current_user_or_service=mock_auth_user)
            
            # Verify error reporting
            assert len(result["loading_errors"]) == 1
            assert "Failed to load module 'broken_module'" in result["loading_errors"][0]
            assert len(result["loaded_modules"]) == 1
    
    def test_debug_module_loader_state_function_missing_path(self, mock_auth_user):
        """Test the debug module loader state function when modules path doesn't exist."""
        from app.main import get_module_loader_state
        
        # Mock the module loader to simulate missing modules path
        with patch('app.main.module_loader') as mock_module_loader:
            mock_module_loader.modules_path.exists.return_value = False
            mock_module_loader.modules_path.__str__.return_value = "/nonexistent/modules"
            mock_module_loader.errors = []
            mock_module_loader.modules = {}
            
            result = get_module_loader_state(current_user_or_service=mock_auth_user)
            
            # Verify missing path is reported
            assert result["modules_path_exists"] is False
            assert result["modules_path_calculated"] == "/nonexistent/modules"
            assert result["loaded_modules"] == []


@pytest.mark.integration
class TestServerDiagnosticsIntegration:
    """Integration tests for server diagnostics endpoints using TestClient."""
    
    @pytest.fixture
    def mock_auth_user(self):
        """Create a mock authenticated user."""
        return User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_admin=False
        )
    
    @pytest.fixture
    def mock_client(self, mock_auth_user):
        """Create a test client with mocked authentication and module loader."""
        from app.main import app
        
        # Mock the database session
        mock_session = Mock(spec=Session)
        mock_session.exec.return_value.first.return_value = mock_auth_user
        
        # Mock the get_session dependency
        def mock_get_session():
            return mock_session
        
        # Mock the get_current_user_or_service dependency
        def mock_get_current_user_or_service():
            return mock_auth_user
        
        # Override dependencies
        from app.database import get_session
        from app.auth import get_current_user_or_service
        
        app.dependency_overrides[get_session] = mock_get_session
        app.dependency_overrides[get_current_user_or_service] = mock_get_current_user_or_service
        
        with TestClient(app) as client:
            yield client
        
        # Clean up dependency overrides
        if get_session in app.dependency_overrides:
            del app.dependency_overrides[get_session]
        if get_current_user_or_service in app.dependency_overrides:
            del app.dependency_overrides[get_current_user_or_service]
    
    def test_debug_module_loader_state_endpoint_success(self, mock_client):
        """Test the debug module loader state endpoint with successful module loading."""
        # Mock the module loader to simulate successful loading
        with patch('app.main.module_loader') as mock_module_loader:
            mock_module_loader.modules_path.exists.return_value = True
            mock_module_loader.modules_path.__str__.return_value = "/app/modules"
            mock_module_loader.errors = []
            mock_module_loader.modules = {
                "filesystem": Mock(),
                "database": Mock(),
                "email": Mock()
            }
            
            response = mock_client.get("/api/v1/debug/module-loader-state")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify the response structure
            assert "modules_path_calculated" in data
            assert "modules_path_exists" in data
            assert "loading_errors" in data
            assert "loaded_modules" in data
            
            # Verify the values
            assert data["modules_path_calculated"] == "/app/modules"
            assert data["modules_path_exists"] is True
            assert data["loading_errors"] == []
            assert len(data["loaded_modules"]) == 3
            assert "filesystem" in data["loaded_modules"]
            assert "database" in data["loaded_modules"]
            assert "email" in data["loaded_modules"]

@pytest.mark.e2e
def test_server_module_loader_diagnostics():
    """
    Connects to the running core service and calls the debug endpoint
    to check the state of the ModuleLoader.
    
    This test is marked as e2e and will be skipped if the service is not available.
    """
    headers = get_service_headers()
    client = httpx.Client(base_url=CORE_API_URL, headers=headers)
    
    print("\n--- Running Server Diagnostics E2E Test ---")
    print(f"Using API key: {SERVICE_API_KEY[:10]}...")  # Only show first 10 chars for security
    print(f"Headers: {headers}")
    
    # ACT: Call the debug endpoint
    try:
        response = client.get("/api/v1/debug/module-loader-state")
    except httpx.ConnectError as e:
        pytest.skip(f"Could not connect to the core service at {CORE_API_URL}. Skipping e2e test. Error: {e}")

    # ASSERT: Check the response and its data
    print(f"Debug endpoint status code: {response.status_code}")
    
    # If we get a 401, provide helpful debugging information
    if response.status_code == 401:
        print("Authentication failed! This could be due to:")
        print("1. Incorrect SERVICE_API_KEY environment variable")
        print("2. Service not configured to accept API key authentication")
        print("3. API key header not being sent correctly")
        print(f"Expected API key: {SERVICE_API_KEY}")
        print(f"Response headers: {dict(response.headers)}")
    
    # Try to parse JSON, but print raw text if it fails
    try:
        data = response.json()
        import json
        print("Debug endpoint response data:")
        print(json.dumps(data, indent=2))
    except Exception:
        print("Could not parse JSON from debug endpoint. Raw response text:")
        print(response.text)
        data = {}

    # The server must respond with 200 OK
    assert response.status_code == 200, f"The debug endpoint should return 200 OK, but got {response.status_code}. Response: {response.text}"

    # The module loader should not have encountered errors  
    assert not data.get("loading_errors"), f"The module loader reported errors during startup: {data.get('loading_errors')}"

    # The module loader must find and load at least one module
    assert data.get("loaded_modules"), f"The module loader did not load any modules. Loaded modules: {data.get('loaded_modules')}"

    print("--- Server Diagnostics E2E Test Passed ---")