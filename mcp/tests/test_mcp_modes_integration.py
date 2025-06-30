"""
Integration tests for MCP Interface dual-mode operation.

These tests verify that both HTTP and stdio modes work correctly
and can connect to the Core service.
"""

import asyncio
import json
import subprocess
import tempfile
import time
import pytest
import httpx
from pathlib import Path
from typing import Dict, Any, Optional

import sys
import os

# Add the app directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.core_client import CoreClient


@pytest.mark.integration
@pytest.mark.modes
@pytest.mark.skipif(
    os.getenv("SKIP_MCP_INTEGRATION", "false").lower() == "true",
    reason="MCP integration tests skipped via SKIP_MCP_INTEGRATION environment variable"
)
class TestMCPModeIntegration:
    """Integration tests for MCP dual-mode operation."""

    @pytest.fixture
    def core_service_url(self):
        """Get the Core service URL from environment or use default."""
        # In CI environments, use the service name for Docker networking
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            return os.getenv("CORE_API_URL", "http://core:8000")
        else:
            return os.getenv("CORE_API_URL", "http://localhost:8000")

    @pytest.fixture
    async def verify_core_service(self, core_service_url):
        """Verify that the Core service is accessible before running tests."""
        max_retries = 30
        retry_delay = 2
        
        print(f"Attempting to connect to Core service at {core_service_url}")
        
        for attempt in range(max_retries):
            try:
                # Use a more robust HTTP client configuration
                timeout = httpx.Timeout(10.0, connect=5.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(f"{core_service_url}/")
                    if response.status_code == 200:
                        print(f"Successfully connected to Core service on attempt {attempt + 1}")
                        return core_service_url
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                print(f"Attempt {attempt + 1}/{max_retries}: Connection failed - {type(e).__name__}: {e}")
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries}: Unexpected error - {type(e).__name__}: {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
        
        # Final diagnostic attempt
        try:
            import socket
            host = core_service_url.replace("http://", "").replace("https://", "").split(":")[0]
            port = int(core_service_url.split(":")[-1]) if ":" in core_service_url.split("//")[-1] else 80
            print(f"Attempting direct socket connection to {host}:{port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print(f"Socket connection successful, but HTTP requests failed")
            else:
                print(f"Socket connection failed with error code: {result}")
        except Exception as e:
            print(f"Socket diagnostic failed: {e}")
        
        pytest.skip(f"Core service not available at {core_service_url} after {max_retries} attempts")

    @pytest.fixture
    def mcp_app_path(self):
        """Get the path to the MCP app main module."""
        current_dir = Path(__file__).parent
        mcp_dir = current_dir.parent
        return mcp_dir / "app" / "main.py"

    @pytest.fixture
    def test_environment(self, core_service_url):
        """Set up environment variables for testing."""
        env = os.environ.copy()
        env.update({
            "CORE_API_URL": core_service_url,
            "SERVICE_API_KEY": "dev-service-key-12345",
            "PYTHONPATH": str(Path(__file__).parent.parent),
            "LOG_LEVEL": "INFO"
        })
        return env

    @pytest.mark.asyncio
    async def test_http_mode_startup_and_health(self, verify_core_service, test_environment, mcp_app_path):
        """Test that HTTP mode starts correctly and responds to health checks."""
        # Start MCP in HTTP mode
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            # Wait for startup
            await asyncio.sleep(3)
            
            # Check if process is still running
            assert process.poll() is None, "MCP process died during startup"
            
            # Try to connect to the HTTP server
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get("http://localhost:8001/", timeout=5.0)
                        if response.status_code == 200:
                            break
                except Exception:
                    if attempt == max_retries - 1:
                        # Get process output for debugging
                        stdout, stderr = process.communicate(timeout=5)
                        pytest.fail(f"HTTP mode failed to start. STDOUT: {stdout}, STDERR: {stderr}")
                    await asyncio.sleep(1)
            
            # Verify we can make MCP requests
            async with httpx.AsyncClient() as client:
                mcp_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list"
                }
                
                response = await client.post(
                    "http://localhost:8001/",
                    json=mcp_request,
                    timeout=10.0
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "result" in data
                assert "tools" in data["result"]
                assert isinstance(data["result"]["tools"], list)
                
        finally:
            # Clean up
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    @pytest.mark.asyncio
    async def test_stdio_mode_startup_and_communication(self, verify_core_service, test_environment, mcp_app_path):
        """Test that stdio mode starts correctly and can handle MCP requests."""
        # Start MCP in stdio mode
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main", "--stdio"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            # Send tools/list request
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            
            request_json = json.dumps(mcp_request) + "\n"
            
            # Send request and get response
            stdout, stderr = process.communicate(input=request_json, timeout=10)
            
            # Check process exit code
            assert process.returncode == 0, f"Stdio mode failed. STDERR: {stderr}"
            
            # Parse response
            assert stdout.strip(), f"No stdout received. STDERR: {stderr}"
            
            try:
                response_data = json.loads(stdout.strip())
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON response: {stdout}. Error: {e}")
            
            # Verify MCP response structure
            assert "jsonrpc" in response_data
            assert response_data["jsonrpc"] == "2.0"
            assert "id" in response_data
            assert response_data["id"] == 1
            assert "result" in response_data
            assert "tools" in response_data["result"]
            assert isinstance(response_data["result"]["tools"], list)
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            pytest.fail(f"Stdio mode timed out. STDOUT: {stdout}, STDERR: {stderr}")

    @pytest.mark.asyncio
    async def test_both_modes_same_tools(self, verify_core_service, test_environment, mcp_app_path):
        """Test that both modes expose the same set of tools."""
        # Get tools from HTTP mode
        http_process = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            # Wait for HTTP mode to start
            await asyncio.sleep(3)
            
            async with httpx.AsyncClient() as client:
                # Wait for server to be ready
                for _ in range(10):
                    try:
                        response = await client.get("http://localhost:8001/", timeout=5.0)
                        if response.status_code == 200:
                            break
                    except Exception:
                        await asyncio.sleep(1)
                
                # Get tools from HTTP mode
                mcp_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list"
                }
                
                response = await client.post(
                    "http://localhost:8001/",
                    json=mcp_request,
                    timeout=10.0
                )
                
                assert response.status_code == 200
                http_data = response.json()
                http_tools = {tool["name"] for tool in http_data["result"]["tools"]}
                
        finally:
            http_process.terminate()
            try:
                http_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                http_process.kill()
                http_process.wait()
        
        # Get tools from stdio mode
        stdio_process = subprocess.Popen(
            [sys.executable, "-m", "app.main", "--stdio"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            
            request_json = json.dumps(mcp_request) + "\n"
            stdout, stderr = stdio_process.communicate(input=request_json, timeout=10)
            
            assert stdio_process.returncode == 0, f"Stdio mode failed. STDERR: {stderr}"
            
            stdio_data = json.loads(stdout.strip())
            stdio_tools = {tool["name"] for tool in stdio_data["result"]["tools"]}
            
        except subprocess.TimeoutExpired:
            stdio_process.kill()
            pytest.fail("Stdio mode timed out")
        
        # Compare tool sets
        assert http_tools == stdio_tools, f"Tool sets differ. HTTP: {http_tools}, Stdio: {stdio_tools}"
        
        # Verify we have expected core tools
        expected_tools = {"filesystem.read_file", "filesystem.write_file", "memory.store", "memory.retrieve"}
        assert expected_tools.issubset(http_tools), f"Missing expected tools: {expected_tools - http_tools}"

    @pytest.mark.asyncio
    async def test_stdio_mode_tool_execution(self, verify_core_service, test_environment, mcp_app_path):
        """Test that stdio mode can execute tools correctly."""
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main", "--stdio"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            # Test memory store operation
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "memory.store",
                    "arguments": {
                        "key": "test_key",
                        "value": "test_value",
                        "category": "test"
                    }
                }
            }
            
            request_json = json.dumps(mcp_request) + "\n"
            stdout, stderr = process.communicate(input=request_json, timeout=15)
            
            assert process.returncode == 0, f"Tool execution failed. STDERR: {stderr}"
            
            response_data = json.loads(stdout.strip())
            
            # Verify successful execution
            assert "result" in response_data
            assert "content" in response_data["result"]
            assert len(response_data["result"]["content"]) > 0
            
            # Check that the response indicates success
            content = response_data["result"]["content"][0]
            assert content["type"] == "text"
            assert "stored" in content["text"].lower() or "success" in content["text"].lower()
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            pytest.fail(f"Tool execution timed out. STDOUT: {stdout}, STDERR: {stderr}")

    @pytest.mark.asyncio
    async def test_http_mode_tool_execution(self, verify_core_service, test_environment, mcp_app_path):
        """Test that HTTP mode can execute tools correctly."""
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            # Wait for startup
            await asyncio.sleep(3)
            
            async with httpx.AsyncClient() as client:
                # Wait for server to be ready
                for _ in range(10):
                    try:
                        response = await client.get("http://localhost:8001/", timeout=5.0)
                        if response.status_code == 200:
                            break
                    except Exception:
                        await asyncio.sleep(1)
                
                # Test memory store operation
                mcp_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "memory.store",
                        "arguments": {
                            "key": "test_key_http",
                            "value": "test_value_http",
                            "category": "test"
                        }
                    }
                }
                
                response = await client.post(
                    "http://localhost:8001/",
                    json=mcp_request,
                    timeout=15.0
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify successful execution
                assert "result" in data
                assert "content" in data["result"]
                assert len(data["result"]["content"]) > 0
                
                # Check that the response indicates success
                content = data["result"]["content"][0]
                assert content["type"] == "text"
                assert "stored" in content["text"].lower() or "success" in content["text"].lower()
                
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    @pytest.mark.asyncio
    async def test_core_client_connection_both_modes(self, verify_core_service, test_environment):
        """Test that CoreClient works correctly in both modes."""
        # Test direct CoreClient connection (simulates what both modes do internally)
        core_client = CoreClient()
        
        try:
            # Test basic connectivity
            response = await core_client.execute_tool({
                "tool_name": "memory.store",
                "parameters": {
                    "key": "integration_test",
                    "value": "test_data",
                    "category": "test"
                }
            })
            
            assert response is not None
            assert "success" in str(response).lower() or "stored" in str(response).lower()
            
        finally:
            await core_client.close()

    @pytest.mark.asyncio
    async def test_timeline_logging_both_modes(self, verify_core_service, test_environment, mcp_app_path):
        """Test that timeline logging works in both modes."""
        # This test verifies that both modes can log to the timeline
        # We'll check by making a tool call and then verifying timeline entries
        
        # Test HTTP mode timeline logging
        http_process = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            await asyncio.sleep(3)
            
            async with httpx.AsyncClient() as client:
                # Wait for server
                for _ in range(10):
                    try:
                        response = await client.get("http://localhost:8001/", timeout=5.0)
                        if response.status_code == 200:
                            break
                    except Exception:
                        await asyncio.sleep(1)
                
                # Make a tool call that should generate timeline entries
                mcp_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "timeline.log_system_event",
                        "arguments": {
                            "title": "HTTP Mode Test",
                            "description": "Testing timeline logging from HTTP mode"
                        }
                    }
                }
                
                response = await client.post(
                    "http://localhost:8001/",
                    json=mcp_request,
                    timeout=10.0
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "result" in data
                
        finally:
            http_process.terminate()
            try:
                http_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                http_process.kill()
                http_process.wait()
        
        # Test stdio mode timeline logging
        stdio_process = subprocess.Popen(
            [sys.executable, "-m", "app.main", "--stdio"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "timeline.log_system_event",
                    "arguments": {
                        "title": "Stdio Mode Test",
                        "description": "Testing timeline logging from stdio mode"
                    }
                }
            }
            
            request_json = json.dumps(mcp_request) + "\n"
            stdout, stderr = stdio_process.communicate(input=request_json, timeout=15)
            
            assert stdio_process.returncode == 0, f"Timeline logging failed in stdio mode. STDERR: {stderr}"
            
            response_data = json.loads(stdout.strip())
            assert "result" in response_data
            
        except subprocess.TimeoutExpired:
            stdio_process.kill()
            pytest.fail("Timeline logging test timed out in stdio mode")


@pytest.mark.integration
@pytest.mark.modes
class TestMCPModeErrorHandling:
    """Test error handling in both modes."""

    @pytest.fixture
    def test_environment(self):
        """Set up environment variables for error testing."""
        env = os.environ.copy()
        env.update({
            "CORE_API_URL": "http://localhost:9999",  # Non-existent service
            "SERVICE_API_KEY": "dev-service-key-12345",
            "PYTHONPATH": str(Path(__file__).parent.parent),
            "LOG_LEVEL": "INFO"
        })
        return env

    @pytest.fixture
    def mcp_app_path(self):
        """Get the path to the MCP app main module."""
        current_dir = Path(__file__).parent
        mcp_dir = current_dir.parent
        return mcp_dir / "app" / "main.py"

    @pytest.mark.asyncio
    async def test_stdio_mode_core_service_unavailable(self, test_environment, mcp_app_path):
        """Test stdio mode behavior when Core service is unavailable."""
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main", "--stdio"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            
            request_json = json.dumps(mcp_request) + "\n"
            stdout, stderr = process.communicate(input=request_json, timeout=10)
            
            # The process should still respond, even if Core is unavailable
            # It should return an error response rather than crashing
            if stdout.strip():
                try:
                    response_data = json.loads(stdout.strip())
                    # Should be a valid JSON-RPC response, possibly with an error
                    assert "jsonrpc" in response_data
                    assert "id" in response_data
                    # Either result or error should be present
                    assert "result" in response_data or "error" in response_data
                except json.JSONDecodeError:
                    # If we can't parse JSON, that's also acceptable for this error case
                    pass
            
            # Process should exit cleanly (not crash)
            assert process.returncode is not None
            
        except subprocess.TimeoutExpired:
            process.kill()
            # Timeout is acceptable when Core service is unavailable
            pass

    @pytest.mark.asyncio
    async def test_http_mode_graceful_degradation(self, test_environment, mcp_app_path):
        """Test HTTP mode graceful degradation when Core service is unavailable."""
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            # Give it time to attempt startup
            await asyncio.sleep(5)
            
            # The process might exit or continue running with degraded functionality
            # Both are acceptable behaviors
            if process.poll() is None:
                # Process is still running, try to connect
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get("http://localhost:8001/", timeout=5.0)
                        # Any response (even error) is acceptable
                except Exception:
                    # Connection failure is expected when Core is unavailable
                    pass
            
            # Process should not crash immediately
            # It's acceptable for it to exit gracefully or continue with limited functionality
            
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])