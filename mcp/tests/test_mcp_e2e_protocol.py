"""
End-to-end MCP protocol tests with proper initialization sequence.

These tests verify the complete MCP protocol flow including:
1. Proper initialization sequence (initialize -> initialized -> requests)
2. Tool listing functionality
3. Tool execution functionality
4. Both stdio and HTTP modes
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from app.core_client import CoreClient


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.skipif(
    os.getenv("SKIP_MCP_E2E", "false").lower() == "true",
    reason="MCP e2e tests skipped via SKIP_MCP_E2E environment variable",
)
class TestMCPProtocolE2E:
    """End-to-end tests for MCP protocol compliance."""

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

        print(f"\n=== VERIFY_CORE_SERVICE FIXTURE STARTING ===")
        print(f"Attempting to connect to Core service at {core_service_url}")
        print(f"Environment: CI={os.getenv('CI')}, GITHUB_ACTIONS={os.getenv('GITHUB_ACTIONS')}")

        for attempt in range(max_retries):
            try:
                timeout = httpx.Timeout(10.0, connect=5.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(f"{core_service_url}/")
                    if response.status_code == 200:
                        print(f"✅ Successfully connected to Core service on attempt {attempt + 1}")
                        print(f"✅ VERIFY_CORE_SERVICE FIXTURE COMPLETED SUCCESSFULLY")
                        return core_service_url
                    else:
                        print(f"Attempt {attempt + 1}/{max_retries}: Got HTTP {response.status_code}")
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

        print(f"❌ VERIFY_CORE_SERVICE FIXTURE FAILED - CALLING pytest.skip()")
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
            "LOG_LEVEL": "INFO",
        })
        return env

    def create_mcp_messages(self, include_tool_call=False, tool_name="memory.store", tool_args=None):
        """Create proper MCP protocol message sequence."""
        if tool_args is None:
            tool_args = {"key": "test_key", "value": "test_value", "category": "test"}
        
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            },
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
        ]
        
        if include_tool_call:
            messages.append({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": tool_args
                }
            })
        
        return messages

    @pytest.mark.asyncio
    async def test_stdio_protocol_compliance(self, verify_core_service, test_environment, mcp_app_path):
        """Test stdio mode with proper MCP protocol initialization sequence."""
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main", "--stdio"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )

        try:
            messages = self.create_mcp_messages()
            
            # Send all messages
            for msg in messages:
                msg_json = json.dumps(msg) + "\n"
                process.stdin.write(msg_json)
                process.stdin.flush()
            
            # Close stdin to signal end of input
            process.stdin.close()
            
            # Read all responses
            stdout, stderr = process.communicate(timeout=15)
            
            assert process.returncode == 0, f"Process failed. STDERR: {stderr}"
            assert stdout.strip(), f"No stdout received. STDERR: {stderr}"
            
            # Parse responses
            responses = []
            for line in stdout.strip().split('\n'):
                if line.strip():
                    try:
                        response = json.loads(line.strip())
                        responses.append(response)
                    except json.JSONDecodeError as e:
                        pytest.fail(f"Invalid JSON response: {line}. Error: {e}")
            
            # Should have at least 2 responses: initialize response and tools/list response
            assert len(responses) >= 2, f"Expected at least 2 responses, got {len(responses)}: {responses}"
            
            # Verify initialize response
            init_response = responses[0]
            assert init_response["jsonrpc"] == "2.0"
            assert init_response["id"] == 1
            assert "result" in init_response
            assert "capabilities" in init_response["result"]
            
            # Verify tools/list response
            tools_response = responses[1]
            assert tools_response["jsonrpc"] == "2.0"
            assert tools_response["id"] == 2
            assert "result" in tools_response
            assert "tools" in tools_response["result"]
            assert isinstance(tools_response["result"]["tools"], list)
            assert len(tools_response["result"]["tools"]) > 0, "No tools returned"
            
            # Verify tool structure
            for tool in tools_response["result"]["tools"]:
                assert "name" in tool
                assert "description" in tool
                assert "inputSchema" in tool
                
            print(f"✅ Stdio mode: Found {len(tools_response['result']['tools'])} tools")
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            pytest.fail(f"Stdio mode timed out. STDOUT: {stdout}, STDERR: {stderr}")

    @pytest.mark.asyncio
    async def test_stdio_tool_execution(self, verify_core_service, test_environment, mcp_app_path):
        """Test stdio mode tool execution with proper protocol."""
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main", "--stdio"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )

        try:
            messages = self.create_mcp_messages(
                include_tool_call=True,
                tool_name="memory.store",
                tool_args={"key": "e2e_test", "value": "stdio_test_value", "category": "test"}
            )
            
            # Send all messages
            for msg in messages:
                msg_json = json.dumps(msg) + "\n"
                process.stdin.write(msg_json)
                process.stdin.flush()
            
            process.stdin.close()
            stdout, stderr = process.communicate(timeout=20)
            
            assert process.returncode == 0, f"Process failed. STDERR: {stderr}"
            
            # Parse responses
            responses = []
            for line in stdout.strip().split('\n'):
                if line.strip():
                    try:
                        response = json.loads(line.strip())
                        responses.append(response)
                    except json.JSONDecodeError as e:
                        pytest.fail(f"Invalid JSON response: {line}. Error: {e}")
            
            # Should have 3 responses: initialize, tools/list, tools/call
            assert len(responses) >= 3, f"Expected at least 3 responses, got {len(responses)}: {responses}"
            
            # Verify tool execution response
            tool_response = responses[2]
            assert tool_response["jsonrpc"] == "2.0"
            assert tool_response["id"] == 3
            assert "result" in tool_response
            assert "content" in tool_response["result"]
            assert len(tool_response["result"]["content"]) > 0
            
            content = tool_response["result"]["content"][0]
            assert content["type"] == "text"
            assert "text" in content
            
            print(f"✅ Stdio tool execution: {content['text'][:100]}...")
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            pytest.fail(f"Tool execution timed out. STDOUT: {stdout}, STDERR: {stderr}")

    @pytest.mark.asyncio
    async def test_http_protocol_compliance(self, verify_core_service, test_environment, mcp_app_path):
        """Test HTTP mode with proper MCP protocol initialization sequence."""
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for startup
            await asyncio.sleep(3)
            assert process.poll() is None, "MCP process died during startup"

            async with httpx.AsyncClient() as client:
                # Wait for server to be ready
                for attempt in range(15):
                    try:
                        response = await client.get("http://localhost:8001/", timeout=5.0)
                        if response.status_code == 200:
                            break
                    except Exception:
                        if attempt == 14:
                            stdout, stderr = process.communicate(timeout=5)
                            pytest.fail(f"HTTP server failed to start. STDOUT: {stdout}, STDERR: {stderr}")
                        await asyncio.sleep(1)

                # Test proper MCP protocol sequence
                messages = self.create_mcp_messages()
                
                responses = []
                for msg in messages:
                    if msg["method"] == "notifications/initialized":
                        # Skip notifications in HTTP mode (they're not request/response)
                        continue
                        
                    response = await client.post(
                        "http://localhost:8001/",
                        json=msg,
                        timeout=10.0
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    responses.append(data)

                # Verify initialize response
                init_response = responses[0]
                assert init_response["jsonrpc"] == "2.0"
                assert init_response["id"] == 1
                assert "result" in init_response
                assert "capabilities" in init_response["result"]

                # Verify tools/list response
                tools_response = responses[1]
                assert tools_response["jsonrpc"] == "2.0"
                assert tools_response["id"] == 2
                assert "result" in tools_response
                assert "tools" in tools_response["result"]
                assert isinstance(tools_response["result"]["tools"], list)
                assert len(tools_response["result"]["tools"]) > 0, "No tools returned"

                print(f"✅ HTTP mode: Found {len(tools_response['result']['tools'])} tools")

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    @pytest.mark.asyncio
    async def test_http_tool_execution(self, verify_core_service, test_environment, mcp_app_path):
        """Test HTTP mode tool execution with proper protocol."""
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            await asyncio.sleep(3)
            assert process.poll() is None, "MCP process died during startup"

            async with httpx.AsyncClient() as client:
                # Wait for server to be ready
                for attempt in range(15):
                    try:
                        response = await client.get("http://localhost:8001/", timeout=5.0)
                        if response.status_code == 200:
                            break
                    except Exception:
                        if attempt == 14:
                            pytest.fail("HTTP server failed to start")
                        await asyncio.sleep(1)

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
                
                response = await client.post("http://localhost:8001/", json=init_msg, timeout=10.0)
                assert response.status_code == 200
                init_data = response.json()
                assert "result" in init_data

                # Execute tool
                tool_msg = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "memory.store",
                        "arguments": {
                            "key": "e2e_http_test",
                            "value": "http_test_value",
                            "category": "test"
                        }
                    }
                }

                response = await client.post("http://localhost:8001/", json=tool_msg, timeout=15.0)
                assert response.status_code == 200
                tool_data = response.json()

                assert "result" in tool_data
                assert "content" in tool_data["result"]
                assert len(tool_data["result"]["content"]) > 0

                content = tool_data["result"]["content"][0]
                assert content["type"] == "text"
                assert "text" in content

                print(f"✅ HTTP tool execution: {content['text'][:100]}...")

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    @pytest.mark.asyncio
    async def test_cross_mode_tool_consistency(self, verify_core_service, test_environment, mcp_app_path):
        """Test that both modes return the same tools and execute them consistently."""
        # Get tools from stdio mode
        stdio_process = subprocess.Popen(
            [sys.executable, "-m", "app.main", "--stdio"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )

        stdio_tools = set()
        try:
            messages = self.create_mcp_messages()
            for msg in messages:
                msg_json = json.dumps(msg) + "\n"
                stdio_process.stdin.write(msg_json)
                stdio_process.stdin.flush()
            
            stdio_process.stdin.close()
            stdout, stderr = stdio_process.communicate(timeout=15)
            
            assert stdio_process.returncode == 0, f"Stdio process failed. STDERR: {stderr}"
            
            responses = []
            for line in stdout.strip().split('\n'):
                if line.strip():
                    response = json.loads(line.strip())
                    responses.append(response)
            
            tools_response = responses[1]  # tools/list response
            stdio_tools = {tool["name"] for tool in tools_response["result"]["tools"]}
            
        except subprocess.TimeoutExpired:
            stdio_process.kill()
            pytest.fail("Stdio mode timed out")

        # Get tools from HTTP mode
        http_process = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            cwd=Path(mcp_app_path).parent.parent,
            env=test_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        http_tools = set()
        try:
            await asyncio.sleep(3)
            
            async with httpx.AsyncClient() as client:
                # Wait for server
                for _ in range(15):
                    try:
                        response = await client.get("http://localhost:8001/", timeout=5.0)
                        if response.status_code == 200:
                            break
                    except Exception:
                        await asyncio.sleep(1)

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
                
                response = await client.post("http://localhost:8001/", json=init_msg, timeout=10.0)
                assert response.status_code == 200

                # Get tools
                tools_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
                response = await client.post("http://localhost:8001/", json=tools_msg, timeout=10.0)
                assert response.status_code == 200
                
                data = response.json()
                http_tools = {tool["name"] for tool in data["result"]["tools"]}

        finally:
            http_process.terminate()
            try:
                http_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                http_process.kill()
                http_process.wait()

        # Compare tool sets
        assert stdio_tools == http_tools, f"Tool sets differ. Stdio: {stdio_tools}, HTTP: {http_tools}"
        
        # Verify we have expected core tools
        expected_tools = {"memory.store", "memory.retrieve"}
        found_expected = expected_tools.intersection(stdio_tools)
        assert len(found_expected) > 0, f"Missing expected tools. Found: {stdio_tools}"
        
        print(f"✅ Cross-mode consistency: {len(stdio_tools)} tools consistent across both modes")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])