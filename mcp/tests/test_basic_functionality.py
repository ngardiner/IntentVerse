#!/usr/bin/env python3
"""
Basic functionality test for MCP proxy E2E infrastructure.

This test verifies that the test infrastructure files exist and are properly configured.
It doesn't run the actual servers since they require the FastMCP environment.
"""

import sys
import json
from pathlib import Path

def test_infrastructure_files():
    """Test that all required infrastructure files exist and are valid."""
    print("Testing MCP proxy E2E infrastructure files...")
    
    test_dir = Path(__file__).parent
    
    # Check test server files
    server_files = [
        "test_servers/sse_server.py",
        "test_servers/http_server.py", 
        "test_servers/stdio_server.py",
        "test_servers/__init__.py"
    ]
    
    print("\n1. Checking test server files:")
    for server_file in server_files:
        file_path = test_dir / server_file
        if file_path.exists():
            print(f"   ✅ {server_file}")
        else:
            print(f"   ❌ {server_file} - MISSING")
            return False
    
    # Check configuration file
    print("\n2. Checking configuration file:")
    config_file = test_dir / "mcp-proxy.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Validate config structure
            if "mcpServers" in config and len(config["mcpServers"]) == 3:
                print(f"   ✅ mcp-proxy.json (3 servers configured)")
                
                # Check each server
                servers = ["sse-server", "http-server", "stdio-server"]
                for server in servers:
                    if server in config["mcpServers"]:
                        print(f"     ✅ {server} configured")
                    else:
                        print(f"     ❌ {server} missing")
                        return False
            else:
                print(f"   ❌ mcp-proxy.json - Invalid structure")
                return False
        except json.JSONDecodeError as e:
            print(f"   ❌ mcp-proxy.json - Invalid JSON: {e}")
            return False
    else:
        print(f"   ❌ mcp-proxy.json - MISSING")
        return False
    
    # Check test files
    print("\n3. Checking test files:")
    test_files = [
        "test_mcp_proxy_e2e.py",
        "run_e2e_tests.py"
    ]
    
    for test_file in test_files:
        file_path = test_dir / test_file
        if file_path.exists():
            print(f"   ✅ {test_file}")
        else:
            print(f"   ❌ {test_file} - MISSING")
            return False
    
    print("\n✅ All infrastructure files present and valid!")
    return True


def main():
    """Main test function."""
    try:
        success = test_infrastructure_files()
        if success:
            print("\n🎉 Basic infrastructure test PASSED!")
            print("Infrastructure is ready for E2E testing in CI environment.")
            print("Note: Actual server testing requires FastMCP environment (available in CI).")
        return success
    except Exception as e:
        print(f"\n❌ Basic infrastructure test FAILED: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)