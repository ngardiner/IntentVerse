#!/usr/bin/env python3
"""
Basic functionality test for MCP proxy E2E infrastructure.

This is a simple test to verify that the test servers can be started
and basic functionality works before running the full E2E suite.
"""

import asyncio
import sys
from pathlib import Path

# Add the mcp module to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_servers.sse_server import sse_hello_world, common_tool as sse_common
from test_servers.http_server import http_hello_world, common_tool as http_common
from test_servers.stdio_server import stdio_hello_world, common_tool as stdio_common


async def test_server_tools():
    """Test that all server tools work correctly."""
    print("Testing MCP test server tools...")
    
    # Test SSE server tools
    print("\n1. Testing SSE server tools:")
    result = await sse_hello_world("Test")
    print(f"   sse_hello_world: {result}")
    
    result = await sse_common("sse_test")
    print(f"   common_tool: {result}")
    
    # Test HTTP server tools
    print("\n2. Testing HTTP server tools:")
    result = await http_hello_world("Test")
    print(f"   http_hello_world: {result}")
    
    result = await http_common("http_test")
    print(f"   common_tool: {result}")
    
    # Test STDIO server tools
    print("\n3. Testing STDIO server tools:")
    result = await stdio_hello_world("Test")
    print(f"   stdio_hello_world: {result}")
    
    result = await stdio_common("stdio_test")
    print(f"   common_tool: {result}")
    
    print("\n✅ All server tools working correctly!")
    return True


async def main():
    """Main test function."""
    try:
        success = await test_server_tools()
        if success:
            print("\n🎉 Basic functionality test PASSED!")
            print("Ready to run full E2E test suite with: python mcp/tests/run_e2e_tests.py")
        return success
    except Exception as e:
        print(f"\n❌ Basic functionality test FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)