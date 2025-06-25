#!/usr/bin/env python3
"""
Test script to verify MCP test setup
"""

import sys
import subprocess

def test_pytest_installation():
    """Test if pytest can be imported and run"""
    try:
        import pytest
        print("✅ pytest import successful")
        
        # Test pytest version
        result = subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ pytest version: {result.stdout.strip()}")
        else:
            print(f"❌ pytest version check failed: {result.stderr}")
            
    except ImportError as e:
        print(f"❌ pytest import failed: {e}")
        return False
    
    return True

def test_required_packages():
    """Test if all required packages can be imported"""
    packages = ['pytest', 'pytest_asyncio', 'respx', 'httpx', 'fastmcp']
    
    for package in packages:
        try:
            __import__(package)
            print(f"✅ {package} import successful")
        except ImportError as e:
            print(f"❌ {package} import failed: {e}")

if __name__ == "__main__":
    print("Testing MCP test setup...")
    test_pytest_installation()
    test_required_packages()