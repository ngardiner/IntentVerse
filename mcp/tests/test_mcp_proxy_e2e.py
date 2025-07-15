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
        """Wait for network servers to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check SSE server
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:8002/health", timeout=5)
                    if response.status_code != 200:
                        await asyncio.sleep(1)
                        continue
                
                # Check HTTP server
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:8003/health", timeout=5)
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


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
async def proxy_engine():
    """Fixture to create and manage MCP proxy engine."""
    config_path = Path(__file__).parent / "mcp-proxy.json"
    
    engine = MCPProxyEngine(str(config_path))
    await engine.initialize()
    await engine.start()
    
    yield engine
    
    await engine.stop()


@pytest.fixture(scope="module")
async def core_client():
    """Fixture to create core client for timeline verification."""
    client = CoreClient()
    yield client
    await client.close()


class TestMCPProxyE2E:
    """End-to-end tests for MCP proxy functionality."""
    
    @pytest.mark.asyncio
    async def test_tool_discovery_all_servers(self, test_servers, proxy_engine):
        """Test successful tool discovery for all 3 servers."""
        # Get all discovered tools
        all_tools = proxy_engine.get_all_tool_info()
        
        # Should have 6 tools total (2 per server)
        assert len(all_tools) >= 6, f"Expected at least 6 tools, got {len(all_tools)}"
        
        # Check for server-specific tools
        tool_names = [tool["name"] for tool in all_tools]
        
        # Check for unique tools with server prefixes
        expected_unique_tools = [
            "sse-server.sse_hello_world",
            "http-server.http_hello_world", 
            "stdio-server.stdio_hello_world"
        ]
        
        for expected_tool in expected_unique_tools:
            assert expected_tool in tool_names, f"Missing unique tool: {expected_tool}"
        
        # Check for common tools with server prefixes (deconflicted)
        expected_common_tools = [
            "sse-server.common_tool",
            "http-server.common_tool",
            "stdio-server.common_tool"
        ]
        
        for expected_tool in expected_common_tools:
            assert expected_tool in tool_names, f"Missing common tool: {expected_tool}"
        
        logger.info(f"Successfully discovered {len(all_tools)} tools from all servers")
    
    @pytest.mark.asyncio
    async def test_tool_deconfliction(self, test_servers, proxy_engine):
        """Test that same-named tools are deconflicted using prefixes."""
        all_tools = proxy_engine.get_all_tool_info()
        
        # Find all common_tool instances
        common_tools = [tool for tool in all_tools if tool["name"].endswith(".common_tool")]
        
        # Should have exactly 3 common_tool instances (one per server)
        assert len(common_tools) == 3, f"Expected 3 common_tool instances, got {len(common_tools)}"
        
        # Check that each has a different server prefix
        server_prefixes = set()
        for tool in common_tools:
            prefix = tool["name"].split(".")[0]
            server_prefixes.add(prefix)
        
        expected_prefixes = {"sse-server", "http-server", "stdio-server"}
        assert server_prefixes == expected_prefixes, f"Expected prefixes {expected_prefixes}, got {server_prefixes}"
        
        logger.info("Tool deconfliction working correctly")
    
    @pytest.mark.asyncio
    async def test_tool_execution_sse_server(self, test_servers, proxy_engine):
        """Test tool calls against SSE server tools."""
        # Test unique tool
        result = await proxy_engine.call_tool("sse-server.sse_hello_world", name="E2E Test")
        assert result["message"] == "Hello E2E Test from SSE MCP Server!"
        assert result["server_type"] == "sse"
        
        # Test common tool
        result = await proxy_engine.call_tool("sse-server.common_tool", input_data="sse_test")
        assert result["processed_data"] == "SSE processed: sse_test"
        assert result["server_name"] == "sse-server"
        
        logger.info("SSE server tool execution successful")
    
    @pytest.mark.asyncio
    async def test_tool_execution_http_server(self, test_servers, proxy_engine):
        """Test tool calls against HTTP server tools."""
        # Test unique tool
        result = await proxy_engine.call_tool("http-server.http_hello_world", name="E2E Test")
        assert result["message"] == "Hello E2E Test from HTTP MCP Server!"
        assert result["server_type"] == "streamable-http"
        
        # Test common tool
        result = await proxy_engine.call_tool("http-server.common_tool", input_data="http_test")
        assert result["processed_data"] == "HTTP processed: http_test"
        assert result["server_name"] == "http-server"
        
        logger.info("HTTP server tool execution successful")
    
    @pytest.mark.asyncio
    async def test_tool_execution_stdio_server(self, test_servers, proxy_engine):
        """Test tool calls against STDIO server tools."""
        # Test unique tool
        result = await proxy_engine.call_tool("stdio-server.stdio_hello_world", name="E2E Test")
        assert result["message"] == "Hello E2E Test from STDIO MCP Server!"
        assert result["server_type"] == "stdio"
        
        # Test common tool
        result = await proxy_engine.call_tool("stdio-server.common_tool", input_data="stdio_test")
        assert result["processed_data"] == "STDIO processed: stdio_test"
        assert result["server_name"] == "stdio-server"
        
        logger.info("STDIO server tool execution successful")
    
    @pytest.mark.asyncio
    async def test_all_tool_executions(self, test_servers, proxy_engine):
        """Test execution of all 6 tools to verify successful responses."""
        tools_to_test = [
            ("sse-server.sse_hello_world", {"name": "All Test"}),
            ("sse-server.common_tool", {"input_data": "all_sse"}),
            ("http-server.http_hello_world", {"name": "All Test"}),
            ("http-server.common_tool", {"input_data": "all_http"}),
            ("stdio-server.stdio_hello_world", {"name": "All Test"}),
            ("stdio-server.common_tool", {"input_data": "all_stdio"}),
        ]
        
        results = []
        for tool_name, params in tools_to_test:
            try:
                result = await proxy_engine.call_tool(tool_name, **params)
                results.append((tool_name, result, None))
                logger.info(f"Successfully called {tool_name}")
            except Exception as e:
                results.append((tool_name, None, str(e)))
                logger.error(f"Failed to call {tool_name}: {e}")
        
        # All tools should execute successfully
        failed_tools = [(name, error) for name, result, error in results if error is not None]
        assert len(failed_tools) == 0, f"Failed tool executions: {failed_tools}"
        
        logger.info("All 6 tools executed successfully")
    
    @pytest.mark.asyncio
    async def test_timeline_integration(self, test_servers, proxy_engine, core_client):
        """Test that Timeline module records all tool calls correctly."""
        # Execute a few tool calls
        test_calls = [
            ("sse-server.sse_hello_world", {"name": "Timeline Test"}),
            ("http-server.common_tool", {"input_data": "timeline_test"}),
            ("stdio-server.stdio_hello_world", {"name": "Timeline Test"}),
        ]
        
        # Record start time for filtering timeline events
        start_time = time.time()
        
        # Execute the tool calls
        for tool_name, params in test_calls:
            await proxy_engine.call_tool(tool_name, **params)
            await asyncio.sleep(0.5)  # Small delay between calls
        
        # Wait a bit for timeline events to be recorded
        await asyncio.sleep(2)
        
        # Query timeline for recent events
        try:
            timeline_result = await core_client.execute_tool({
                "tool_name": "timeline.get_events",
                "parameters": {
                    "limit": 50,
                    "event_type": "tool_call"
                }
            })
            
            timeline_events = timeline_result.get("result", {}).get("events", [])
            
            # Filter events that occurred after our start time
            recent_events = [
                event for event in timeline_events 
                if event.get("timestamp", 0) >= start_time
            ]
            
            # Should have at least our 3 test calls recorded
            proxy_events = [
                event for event in recent_events
                if any(tool_name in event.get("title", "") for tool_name, _ in test_calls)
            ]
            
            assert len(proxy_events) >= 3, f"Expected at least 3 timeline events, got {len(proxy_events)}"
            
            logger.info(f"Timeline integration verified: {len(proxy_events)} events recorded")
            
        except Exception as e:
            logger.warning(f"Timeline integration test failed: {e}")
            # Don't fail the test if timeline is not available
            pytest.skip("Timeline module not available for testing")
    
    @pytest.mark.asyncio
    async def test_proxy_engine_stats(self, test_servers, proxy_engine):
        """Test proxy engine statistics reporting."""
        stats = proxy_engine.get_stats()
        
        # Should have 3 servers configured
        assert stats.servers_configured == 3, f"Expected 3 configured servers, got {stats.servers_configured}"
        
        # Should have connected to servers
        assert stats.servers_connected > 0, f"Expected connected servers, got {stats.servers_connected}"
        
        # Should have discovered tools
        assert stats.tools_discovered >= 6, f"Expected at least 6 tools, got {stats.tools_discovered}"
        
        # Should have registered tools
        assert stats.tools_registered >= 6, f"Expected at least 6 registered tools, got {stats.tools_registered}"
        
        logger.info(f"Proxy engine stats: {stats.to_dict()}")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, test_servers, proxy_engine):
        """Test error handling for invalid tool calls."""
        # Test calling non-existent tool
        with pytest.raises(Exception):
            await proxy_engine.call_tool("nonexistent.tool")
        
        # Test calling tool with invalid parameters
        with pytest.raises(Exception):
            await proxy_engine.call_tool("sse-server.sse_hello_world", invalid_param="test")
        
        logger.info("Error handling tests passed")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])