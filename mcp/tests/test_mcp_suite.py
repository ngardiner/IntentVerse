import pytest
import inspect
import os
from typing import Any, Dict
import httpx
import respx

from app.registrar import ToolRegistrar
from app.core_client import CoreClient
from fastmcp.tools import FunctionTool
from fastmcp import FastMCP

# --- Unit Tests for ToolRegistrar ---

class TestRegistrarUnit:
    """
    Unit tests for the ToolRegistrar, focusing on the dynamic creation
    of proxy functions without needing a live server.
    """

    @pytest.fixture
    def registrar_instance(self):
        """Provides a ToolRegistrar with a simple mocked CoreClient."""
        return ToolRegistrar(CoreClient())

    def test_create_dynamic_proxy_simple(self, registrar_instance):
        """
        Tests if the proxy function is created with the correct signature
        for a tool with simple, required parameters.
        """
        # ARRANGE: Define a simple tool
        tool_def = {
            "name": "test.simple",
            "description": "A simple test tool.",
            "parameters": [{
                "name": "param1", "annotation": "str", "required": True
            }]
        }

        # ACT: Create the proxy function
        proxy_func = registrar_instance._create_dynamic_proxy(tool_def)

        # ASSERT: Check the function's signature
        sig = inspect.signature(proxy_func)
        assert "param1" in sig.parameters
        assert sig.parameters["param1"].annotation == str
        assert sig.parameters["param1"].default == inspect.Parameter.empty

    def test_create_dynamic_proxy_with_optional_param(self, registrar_instance):
        """
        Tests if the proxy function correctly handles optional parameters.
        """
        # ARRANGE: Define a tool with an optional parameter
        tool_def = {
            "name": "test.optional",
            "description": "A tool with an optional parameter.",
            "parameters": [{
                "name": "optional_param", "annotation": "str", "required": False
            }]
        }

        # ACT: Create the proxy
        proxy_func = registrar_instance._create_dynamic_proxy(tool_def)

        # ASSERT: Check that the parameter has a default value
        sig = inspect.signature(proxy_func)
        assert "optional_param" in sig.parameters
        assert sig.parameters["optional_param"].default is None # Optional params default to None

    def test_create_dynamic_proxy_no_params(self, registrar_instance):
        """
        Tests if a proxy is correctly created for a tool with no parameters.
        """
        # ARRANGE: Define a parameter-less tool
        tool_def = {
            "name": "test.no_params",
            "description": "A tool with no parameters.",
            "parameters": []
        }

        # ACT: Create the proxy
        proxy_func = registrar_instance._create_dynamic_proxy(tool_def)

        # ASSERT: Check that the signature has no parameters
        sig = inspect.signature(proxy_func)
        assert len(sig.parameters) == 0


# --- Integration Tests for MCP Service ---

class TestMCPIntegration:
    """
    Integration tests for the MCP service. These tests mock the external
    Core Engine API to verify the MCP's internal logic.
    """

    @respx.mock
    @pytest.mark.asyncio
    async def test_tool_registration(self, registrar, mcp_server, sample_tool_manifest):
        """
        Tests that the registrar correctly fetches a tool manifest and
        registers each tool with the FastMCP server.
        """
        # ARRANGE: Mock the Core API endpoint for the tool manifest
        respx.get(f"{os.environ['CORE_API_URL']}/api/v1/tools/manifest").mock(
            return_value=httpx.Response(200, json=sample_tool_manifest)
        )
        # Mock the timeline logging call to prevent errors during this test
        respx.post(f"{os.environ['CORE_API_URL']}/api/v1/execute").mock(
            return_value=httpx.Response(200, json={"status": "success"})
        )

        # ACT: Run the tool registration process
        await registrar.register_tools(mcp_server)

        # ASSERT: Check that add_tool was called for each tool in the manifest
        assert mcp_server.add_tool.call_count == len(sample_tool_manifest)
        
        # Verify the names of the registered tools
        call_args_list = mcp_server.add_tool.call_args_list
        registered_tool_names = [call.args[0].name for call in call_args_list]
        expected_tool_names = [tool['name'] for tool in sample_tool_manifest]
        assert sorted(registered_tool_names) == sorted(expected_tool_names)


    @respx.mock
    @pytest.mark.asyncio
    async def test_mcp_request_handling(self, registrar, sample_tool_manifest):
        """
        Tests that a call to a registered tool is correctly translated
        into a REST API request to the Core Engine.
        """
        # ARRANGE: Mock the manifest and execute endpoints
        manifest_url = f"{os.environ['CORE_API_URL']}/api/v1/tools/manifest"
        execute_url = f"{os.environ['CORE_API_URL']}/api/v1/execute"
        
        # Mock the manifest call for setup
        respx.get(manifest_url).mock(return_value=httpx.Response(200, json=sample_tool_manifest))
        # Mock the execute call, which we will inspect
        execute_route = respx.post(execute_url).mock(return_value=httpx.Response(200, json={"status": "success", "result": "mocked result"}))
        
        # Create a real FastMCP server to register tools against
        server = FastMCP("Integration Test Server")
        await registrar.register_tools(server)

        # Get the dynamically created proxy function for a specific tool
        filesystem_tool = server.get_tool("filesystem.read_file")
        assert filesystem_tool is not None

        # ACT: Call the tool's proxy function as the MCP server would
        test_path = "/test/file.txt"
        await filesystem_tool.function(path=test_path)

        # ASSERT: Check that the execute endpoint was called with the correct payload
        assert execute_route.called
        
        request_payload = execute_route.calls.last.request.content
        import json
        assert json.loads(request_payload) == {
            "tool_name": "filesystem.read_file",
            "parameters": {"path": test_path}
        }

    @respx.mock
    @pytest.mark.asyncio
    async def test_core_api_error_handling(self, registrar, sample_tool_manifest):
        """
        Tests that when the Core Engine API returns an error, the MCP
        client correctly processes and returns the error.
        """
        # ARRANGE: Mock the manifest and a failing execute endpoint
        manifest_url = f"{os.environ['CORE_API_URL']}/api/v1/tools/manifest"
        execute_url = f"{os.environ['CORE_API_URL']}/api/v1/execute"
        
        respx.get(manifest_url).mock(return_value=httpx.Response(200, json=sample_tool_manifest))
        
        # Mock the execute endpoint to return a 404 Not Found error
        error_detail = "File not found in core engine"
        respx.post(execute_url).mock(
            return_value=httpx.Response(404, json={"detail": error_detail})
        )
        
        # Create a real CoreClient to test its error handling
        core_client = CoreClient()

        # ACT: Attempt to execute a tool that will result in an error
        # We call the client directly here to test its error handling logic
        result = await core_client.execute_tool({
            "tool_name": "filesystem.read_file",
            "parameters": {"path": "/nonexistent.txt"}
        })

        # ASSERT: The CoreClient should catch the HTTP error and format a response
        assert result["status"] == "error"
        assert "404" in result["result"]
        assert "Not Found" in result["result"]
        assert error_detail in result["result"]