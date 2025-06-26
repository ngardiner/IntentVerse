import pytest
import os
from unittest.mock import Mock, AsyncMock

# Import logging configuration
from tests.conftest_logging import configure_test_logging

# Set environment variables for testing before importing application modules
os.environ["CORE_API_URL"] = "http://test-core-api:8000"
os.environ["SERVICE_API_KEY"] = "test-mcp-service-key"

# Import application components
from app.core_client import CoreClient
from app.registrar import ToolRegistrar
from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

@pytest.fixture
def mock_core_client():
    """Provides a mocked instance of CoreClient for testing."""
    client = CoreClient()
    # Mock the asynchronous methods to avoid real network calls
    client.get_tool_manifest = AsyncMock()
    client.execute_tool = AsyncMock()
    return client

@pytest.fixture
def registrar(mock_core_client):
    """Provides a ToolRegistrar instance initialized with a mocked client."""
    return ToolRegistrar(mock_core_client)

@pytest.fixture
def mcp_server():
    """Provides a clean FastMCP server instance for testing."""
    server = FastMCP("Test MCP Server")
    # We replace the real add_tool method with a mock to inspect its calls
    server.add_tool = Mock(wraps=server.add_tool)
    return server

# A sample tool manifest, mimicking the response from the Core Engine API
@pytest.fixture
def sample_tool_manifest():
    """Provides a sample tool manifest for testing the registrar."""
    return [
        {
            "name": "filesystem.read_file",
            "description": "Reads a file from the virtual filesystem.",
            "parameters": [
                {
                    "name": "path",
                    "annotation": "str",
                    "required": True,
                }
            ],
        },
        {
            "name": "email.send_email",
            "description": "Sends an email.",
            "parameters": [
                {"name": "to", "annotation": "str", "required": True},
                {"name": "subject", "annotation": "str", "required": True},
                {"name": "body", "annotation": "str", "required": False},
            ],
        },
        {
            "name": "database.query",
            "description": "Executes a read-only SQL query.",
            "parameters": [
                {"name": "query_string", "annotation": "str", "required": True}
            ]
        }
    ]