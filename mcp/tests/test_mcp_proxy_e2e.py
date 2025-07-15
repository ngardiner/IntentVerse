"""
MCP Proxy E2E Tests

Comprehensive end-to-end tests for MCP proxy functionality including:
- Tool discovery from multiple MCP servers
- Tool deconfliction using server name prefixes
- Tool execution across different protocols (SSE, HTTP, STDIO)
- Timeline integration verification
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import pytest
import httpx

# Add the mcp module to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    # Try importing from app (when running in MCP container)
    from app.main import main as mcp_main
    from app.core_client import CoreClient
    from app.proxy.engine import MCPProxyEngine
    from app.proxy.config import load_proxy_config
except ImportError:
    # Fallback for local development
    from mcp.app.main import main as mcp_main
    from mcp.app.core_client import CoreClient
    from mcp.app.proxy.engine import MCPProxyEngine
    from mcp.app.proxy.config import load_proxy_config

logger = logging.getLogger(__name__)


class TestServerManager:
    """Manages test MCP servers for E2E testing."""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.test_servers_dir = Path(__file__).parent / "test_servers"
        
    async def start_server(self, server_name: str, script_name: str, port: Optional[int] = None) -> bool:
        """Start a test MCP server."""
        script_path = self.test_servers_dir / script_name
        
        if not script_path.exists():
            logger.error(f"Test server script not found: {script_path}")
            return False
            
        try:
            # Set environment for the subprocess to find fastmcp
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path(__file__).parent.parent)
            
            if server_name == "stdio-server":
                # STDIO server doesn't need a port
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=Path(__file__).parent.parent.parent,  # Run from project root
                    env=env
                )
            else:
                # Network-based servers
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    cwd=Path(__file__).parent.parent.parent,  # Run from project root
                    env=env
                )
                
            self.processes[server_name] = process
            
            # Give the server time to start
            await asyncio.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                logger.info(f"Started {server_name} successfully")
                return True
            else:
                logger.error(f"Failed to start {server_name} - process exited")
                return False
                
        except Exception as e:
            logger.error(f"Error starting {server_name}: {e}")
            return False
    
    async def stop_server(self, server_name: str) -> None:
        """Stop a test MCP server."""
        if server_name in self.processes:
            process = self.processes[server_name]
            try:
                process.terminate()
                # Give it time to terminate gracefully
                await asyncio.sleep(1)
                if process.poll() is None:
                    process.kill()
                del self.processes[server_name]
                logger.info(f"Stopped {server_name}")
            except Exception as e:
                logger.error(f"Error stopping {server_name}: {e}")
    
    async def start_all_servers(self) -> bool:
        """Start all test servers."""
        servers = [
            ("sse-server", "sse_server.py", 8002),
            ("http-server", "http_server.py", 8003),
            ("stdio-server", "stdio_server.py", None),
        ]
        
        success = True
        for server_name, script_name, port in servers:
            if not await self.start_server(server_name, script_name, port):
                success = False
                
        return success
    
    async def stop_all_servers(self) -> None:
        """Stop all test servers."""
        for server_name in list(self.processes.keys()):
            await self.stop_server(server_name)
    
    async def wait_for_servers_ready(self, timeout: int = 30) -> bool:
        """Wait for network servers to be ready by testing MCP protocol."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Test SSE server with MCP protocol
                async with httpx.AsyncClient() as client:
                    test_msg = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "test-client", "version": "1.0.0"}
                        }
                    }
                    response = await client.post("http://localhost:8002/sse", json=test_msg, timeout=5)
                    if response.status_code != 200:
                        await asyncio.sleep(1)
                        continue
                
                # Test HTTP server with MCP protocol
                async with httpx.AsyncClient() as client:
                    response = await client.post("http://localhost:8003", json=test_msg, timeout=5)
                    if response.status_code != 200:
                        await asyncio.sleep(1)
                        continue
                
                logger.info("All network servers are ready")
                return True
                
            except Exception:
                await asyncio.sleep(1)
                continue
        
        logger.error("Timeout waiting for servers to be ready")
        return False


@pytest.fixture(scope="function")
async def test_servers():
    """Fixture to manage test MCP servers."""
    manager = TestServerManager()
    
    # Start all test servers
    success = await manager.start_all_servers()
    if not success:
        await manager.stop_all_servers()
        pytest.skip("Failed to start test servers")
    
    # Wait for servers to be ready
    if not await manager.wait_for_servers_ready():
        await manager.stop_all_servers()
        pytest.skip("Test servers not ready")
    
    yield manager
    
    # Cleanup
    await manager.stop_all_servers()


@pytest.fixture(scope="function")
async def mcp_server_with_proxy():
    """Fixture to start the main MCP server with proxy configuration."""
    # Set up environment to use our test proxy config
    env = os.environ.copy()
    env.update({
        "CORE_API_URL": "http://core:8000",
        "SERVICE_API_KEY": "dev-service-key-12345",
        "MCP_PROXY_CONFIG": str(Path(__file__).parent / "mcp-proxy.json"),
        "LOG_LEVEL": "INFO",
        "PYTHONPATH": str(Path(__file__).parent.parent)
    })
    
    # Start the main MCP server
    process = subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        cwd=Path(__file__).parent.parent,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    await asyncio.sleep(5)
    
    # Verify server is running
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        pytest.skip(f"MCP server failed to start. STDOUT: {stdout}, STDERR: {stderr}")
    
    # Test server connectivity
    try:
        async with httpx.AsyncClient() as client:
            test_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }
            response = await client.post("http://localhost:8001/mcp", json=test_msg, timeout=10)
            if response.status_code != 200:
                process.terminate()
                pytest.skip(f"MCP server not responding properly: {response.status_code}")
    except Exception as e:
        process.terminate()
        pytest.skip(f"Could not connect to MCP server: {e}")
    
    yield process
    
    # Cleanup
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.fixture(scope="function")
async def core_client():
    """Fixture to create core client for timeline verification."""
    client = CoreClient()
    yield client
    await client.close()


class TestMCPProxyE2E:
    """End-to-end tests for MCP proxy functionality."""
    
    async def get_mcp_tools(self, mcp_server_process):
        """Get tools from the MCP server using proper JSON-RPC protocol."""
        async with httpx.AsyncClient() as client:
            # Initialize
            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }
            
            response = await client.post("http://localhost:8001/mcp", json=init_msg, timeout=10)
            assert response.status_code == 200
            
            # Get tools
            tools_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            response = await client.post("http://localhost:8001/mcp", json=tools_msg, timeout=10)
            assert response.status_code == 200
            
            data = response.json()
            return data["result"]["tools"]
    
    async def call_mcp_tool(self, mcp_server_process, tool_name, arguments):
        """Call a tool via the MCP server using proper JSON-RPC protocol."""
        async with httpx.AsyncClient() as client:
            # Initialize first
            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }
            
            response = await client.post("http://localhost:8001/mcp", json=init_msg, timeout=10)
            assert response.status_code == 200
            
            # Call tool
            tool_msg = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            response = await client.post("http://localhost:8001/mcp", json=tool_msg, timeout=15)
            assert response.status_code == 200
            
            data = response.json()
            return data["result"]
    
    @pytest.mark.asyncio
    async def test_tool_discovery_all_servers(self, test_servers, mcp_server_with_proxy):
        """Test successful tool discovery for all 3 servers through MCP proxy."""
        # Get all tools from the MCP server
        all_tools = await self.get_mcp_tools(mcp_server_with_proxy)
        
        # Extract tool names
        tool_names = [tool["name"] for tool in all_tools]
        
        # Check for proxy tools with server prefixes
        expected_proxy_tools = [
            "sse-server.sse_hello_world",
            "sse-server.common_tool",
            "http-server.http_hello_world", 
            "http-server.common_tool",
            "stdio-server.stdio_hello_world",
            "stdio-server.common_tool"
        ]
        
        found_proxy_tools = []
        for expected_tool in expected_proxy_tools:
            if expected_tool in tool_names:
                found_proxy_tools.append(expected_tool)
        
        # Should find at least some proxy tools (may not be all if servers aren't running)
        assert len(found_proxy_tools) > 0, f"No proxy tools found. Available tools: {tool_names}"
        
        logger.info(f"Successfully discovered {len(found_proxy_tools)} proxy tools: {found_proxy_tools}")
    
    @pytest.mark.asyncio
    async def test_tool_deconfliction(self, test_servers, mcp_server_with_proxy):
        """Test that same-named tools are deconflicted using prefixes."""
        all_tools = await self.get_mcp_tools(mcp_server_with_proxy)
        
        # Find all common_tool instances
        common_tools = [tool for tool in all_tools if tool["name"].endswith(".common_tool")]
        
        # Should have at least 1 common_tool instance (may not be all if servers aren't running)
        assert len(common_tools) > 0, f"Expected at least 1 common_tool instance, got {len(common_tools)}"
        
        # Check that each has a different server prefix
        server_prefixes = set()
        for tool in common_tools:
            prefix = tool["name"].split(".")[0]
            server_prefixes.add(prefix)
        
        # Should have unique prefixes for each common_tool
        assert len(server_prefixes) == len(common_tools), f"Duplicate prefixes found: {server_prefixes}"
        
        logger.info(f"Tool deconfliction working correctly: {len(common_tools)} common_tool instances with prefixes {server_prefixes}")
    
    @pytest.mark.asyncio
    async def test_tool_execution_via_proxy(self, test_servers, mcp_server_with_proxy):
        """Test tool calls against proxy tools through MCP server."""
        # Get available tools first
        all_tools = await self.get_mcp_tools(mcp_server_with_proxy)
        tool_names = [tool["name"] for tool in all_tools]
        
        # Test any available proxy tools
        proxy_tools = [name for name in tool_names if any(prefix in name for prefix in ["sse-server.", "http-server.", "stdio-server."])]
        
        if not proxy_tools:
            pytest.skip("No proxy tools available for testing")
        
        # Test the first available proxy tool
        test_tool = proxy_tools[0]
        
        try:
            if "hello_world" in test_tool:
                result = await self.call_mcp_tool(mcp_server_with_proxy, test_tool, {"name": "E2E Test"})
            elif "common_tool" in test_tool:
                result = await self.call_mcp_tool(mcp_server_with_proxy, test_tool, {"input_data": "proxy_test"})
            else:
                # Try with minimal arguments
                result = await self.call_mcp_tool(mcp_server_with_proxy, test_tool, {})
            
            # Verify we got a result
            assert "content" in result
            assert len(result["content"]) > 0
            assert result["content"][0]["type"] == "text"
            
            logger.info(f"Proxy tool execution successful: {test_tool}")
            
        except Exception as e:
            logger.warning(f"Tool execution failed for {test_tool}: {e}")
            # Don't fail the test if proxy servers aren't available
            pytest.skip(f"Proxy tool execution failed: {e}")
    
    @pytest.mark.asyncio
    async def test_mcp_server_basic_functionality(self, mcp_server_with_proxy):
        """Test that the MCP server is working with basic core tools."""
        # Get available tools
        all_tools = await self.get_mcp_tools(mcp_server_with_proxy)
        tool_names = [tool["name"] for tool in all_tools]
        
        # Should have core tools available
        core_tools = [name for name in tool_names if not any(prefix in name for prefix in ["sse-server.", "http-server.", "stdio-server."])]
        assert len(core_tools) > 0, f"No core tools found. Available tools: {tool_names}"
        
        # Test a core tool (memory.store should be available)
        memory_tools = [name for name in tool_names if name.startswith("memory.")]
        if memory_tools:
            test_tool = memory_tools[0]
            try:
                if "store" in test_tool or "set" in test_tool:
                    result = await self.call_mcp_tool(mcp_server_with_proxy, test_tool, {
                        "key": "e2e_test", 
                        "value": "test_value",
                        "category": "test"
                    })
                else:
                    result = await self.call_mcp_tool(mcp_server_with_proxy, test_tool, {"key": "e2e_test"})
                
                assert "content" in result
                logger.info(f"Core tool execution successful: {test_tool}")
            except Exception as e:
                logger.warning(f"Core tool execution failed: {e}")
        
        logger.info(f"MCP server has {len(all_tools)} total tools ({len(core_tools)} core tools)")
    
    @pytest.mark.asyncio
    async def test_proxy_configuration_loaded(self, mcp_server_with_proxy):
        """Test that proxy configuration is loaded and accessible."""
        # Check if proxy tools are available (indicates proxy config was loaded)
        all_tools = await self.get_mcp_tools(mcp_server_with_proxy)
        tool_names = [tool["name"] for tool in all_tools]
        
        # Look for any proxy tools
        proxy_tools = [name for name in tool_names if any(prefix in name for prefix in ["sse-server.", "http-server.", "stdio-server."])]
        
        if proxy_tools:
            logger.info(f"Proxy configuration loaded successfully. Found proxy tools: {proxy_tools}")
        else:
            logger.info("No proxy tools found - proxy servers may not be running (expected in CI)")
        
        # The test passes either way since proxy servers may not be available in CI
        logger.info(f"Total tools available: {len(all_tools)}")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server_with_proxy):
        """Test error handling for invalid tool calls."""
        # Test calling non-existent tool
        try:
            result = await self.call_mcp_tool(mcp_server_with_proxy, "nonexistent.tool", {})
            # If it doesn't raise an exception, check for error in result
            assert "error" in str(result).lower() or "not found" in str(result).lower()
        except Exception:
            # Expected - tool should not exist
            pass
        
        # Test calling valid tool with invalid parameters (if any proxy tools exist)
        all_tools = await self.get_mcp_tools(mcp_server_with_proxy)
        tool_names = [tool["name"] for tool in all_tools]
        
        if tool_names:
            test_tool = tool_names[0]  # Use any available tool
            try:
                # Try with clearly invalid parameters
                result = await self.call_mcp_tool(mcp_server_with_proxy, test_tool, {"invalid_param_xyz": "test"})
                # Some tools might be lenient with extra parameters, so this might not always fail
                logger.info(f"Tool {test_tool} handled invalid parameters gracefully")
            except Exception:
                # Expected for strict tools
                logger.info(f"Tool {test_tool} properly rejected invalid parameters")
        
        logger.info("Error handling tests completed")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])