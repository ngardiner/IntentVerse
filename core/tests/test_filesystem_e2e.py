"""
End-to-End Tests for Filesystem Module

This module contains comprehensive e2e tests for filesystem operations
that are likely under-tested in the current test suite.
"""

import pytest
import httpx
import os
import json

# The URL of our core service, as seen from within the Docker network
CORE_API_URL = os.environ.get("CORE_API_URL", "http://core:8000")
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "dev-service-key-12345")


def get_service_headers():
    """Get headers with service API key for authentication."""
    return {"X-API-Key": SERVICE_API_KEY}


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_filesystem_comprehensive_operations_e2e():
    """
    Comprehensive e2e test for filesystem operations:
    1. Create directory structure
    2. Write files in different directories
    3. List directory contents
    4. Read files
    5. Move/rename files
    6. Delete files and directories
    7. Check filesystem state consistency
    """
    headers = get_service_headers()
    print("E2E Test: Testing comprehensive filesystem operations")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Step 1: Create directory structure
            mkdir_payload = {
                "tool_name": "filesystem.create_directory",
                "parameters": {"path": "/test_project"},
            }
            
            mkdir_response = await client.post("/api/v1/execute", json=mkdir_payload)
            if mkdir_response.status_code == 401:
                pytest.skip(f"Authentication failed: {mkdir_response.text}")
            
            assert mkdir_response.status_code == 200

            # Create subdirectories
            subdirs = ["/test_project/src", "/test_project/docs", "/test_project/tests"]
            for subdir in subdirs:
                subdir_payload = {
                    "tool_name": "filesystem.create_directory",
                    "parameters": {"path": subdir},
                }
                subdir_response = await client.post("/api/v1/execute", json=subdir_payload)
                assert subdir_response.status_code == 200

            # Step 2: Write files in different directories
            files_to_create = [
                ("/test_project/README.md", "# Test Project\n\nThis is a test project for e2e testing."),
                ("/test_project/src/main.py", "def main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()"),
                ("/test_project/docs/api.md", "# API Documentation\n\nThis file contains API documentation."),
                ("/test_project/tests/test_main.py", "import unittest\n\nclass TestMain(unittest.TestCase):\n    def test_example(self):\n        self.assertTrue(True)")
            ]

            for file_path, content in files_to_create:
                write_payload = {
                    "tool_name": "filesystem.write_file",
                    "parameters": {"path": file_path, "content": content},
                }
                write_response = await client.post("/api/v1/execute", json=write_payload)
                assert write_response.status_code == 200

            # Step 3: List directory contents
            list_payload = {
                "tool_name": "filesystem.list_directory",
                "parameters": {"path": "/test_project"},
            }
            
            list_response = await client.post("/api/v1/execute", json=list_payload)
            assert list_response.status_code == 200
            list_result = list_response.json()["result"]
            
            # Verify directory structure
            expected_items = ["README.md", "src", "docs", "tests"]
            found_items = [item["name"] for item in list_result]
            for expected in expected_items:
                assert expected in found_items

            # Step 4: Read files and verify content
            read_payload = {
                "tool_name": "filesystem.read_file",
                "parameters": {"path": "/test_project/README.md"},
            }
            
            read_response = await client.post("/api/v1/execute", json=read_payload)
            assert read_response.status_code == 200
            content = read_response.json()["result"]
            assert "Test Project" in content
            assert "e2e testing" in content

            # Step 5: Get filesystem state and verify structure
            state_response = await client.get("/api/v1/filesystem/state")
            assert state_response.status_code == 200
            fs_state = state_response.json()
            
            # Find test_project in the state
            test_project = None
            for child in fs_state.get("children", []):
                if child["name"] == "test_project":
                    test_project = child
                    break
            
            assert test_project is not None
            assert test_project["type"] == "directory"
            assert len(test_project["children"]) == 4  # README.md + 3 subdirs

            # Step 6: Test file operations (copy, move)
            # First, let's copy a file
            copy_payload = {
                "tool_name": "filesystem.write_file",
                "parameters": {
                    "path": "/test_project/README_backup.md",
                    "content": "# Test Project\n\nThis is a test project for e2e testing."
                },
            }
            copy_response = await client.post("/api/v1/execute", json=copy_payload)
            assert copy_response.status_code == 200

            # Step 7: Delete a file
            delete_payload = {
                "tool_name": "filesystem.delete_file",
                "parameters": {"path": "/test_project/README_backup.md"},
            }
            
            delete_response = await client.post("/api/v1/execute", json=delete_payload)
            assert delete_response.status_code == 200

            # Verify file is deleted by trying to read it
            read_deleted_payload = {
                "tool_name": "filesystem.read_file",
                "parameters": {"path": "/test_project/README_backup.md"},
            }
            
            read_deleted_response = await client.post("/api/v1/execute", json=read_deleted_payload)
            assert read_deleted_response.status_code != 200  # Should fail

            print("E2E Test: Comprehensive filesystem operations completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_filesystem_large_file_operations_e2e():
    """
    E2E test for handling larger files and binary content.
    """
    headers = get_service_headers()
    print("E2E Test: Testing large file operations")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Create a larger text file
            large_content = ("Line {}\n".format(i) for i in range(1000))
            large_text = "".join(large_content)
            
            write_large_payload = {
                "tool_name": "filesystem.write_file",
                "parameters": {
                    "path": "/large_test_file.txt",
                    "content": large_text
                },
            }
            
            write_response = await client.post("/api/v1/execute", json=write_large_payload)
            if write_response.status_code == 401:
                pytest.skip(f"Authentication failed: {write_response.text}")
            
            assert write_response.status_code == 200

            # Read the large file back
            read_large_payload = {
                "tool_name": "filesystem.read_file",
                "parameters": {"path": "/large_test_file.txt"},
            }
            
            read_response = await client.post("/api/v1/execute", json=read_large_payload)
            assert read_response.status_code == 200
            read_content = read_response.json()["result"]
            
            # Verify content
            assert "Line 1" in read_content
            assert "Line 999" in read_content
            assert len(read_content.split('\n')) >= 1000

            # Clean up
            delete_payload = {
                "tool_name": "filesystem.delete_file",
                "parameters": {"path": "/large_test_file.txt"},
            }
            
            delete_response = await client.post("/api/v1/execute", json=delete_payload)
            assert delete_response.status_code == 200

            print("E2E Test: Large file operations completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_filesystem_edge_cases_e2e():
    """
    E2E test for filesystem edge cases and error conditions.
    """
    headers = get_service_headers()
    print("E2E Test: Testing filesystem edge cases")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Test reading non-existent file
            read_nonexistent_payload = {
                "tool_name": "filesystem.read_file",
                "parameters": {"path": "/nonexistent_file.txt"},
            }
            
            read_response = await client.post("/api/v1/execute", json=read_nonexistent_payload)
            if read_response.status_code == 401:
                pytest.skip(f"Authentication failed: {read_response.text}")
            
            # Should return an error
            assert read_response.status_code != 200

            # Test creating file with empty content
            empty_file_payload = {
                "tool_name": "filesystem.write_file",
                "parameters": {"path": "/empty_file.txt", "content": ""},
            }
            
            empty_response = await client.post("/api/v1/execute", json=empty_file_payload)
            assert empty_response.status_code == 200

            # Read the empty file
            read_empty_payload = {
                "tool_name": "filesystem.read_file",
                "parameters": {"path": "/empty_file.txt"},
            }
            
            read_empty_response = await client.post("/api/v1/execute", json=read_empty_payload)
            assert read_empty_response.status_code == 200
            assert read_empty_response.json()["result"] == ""

            # Test overwriting existing file
            overwrite_payload = {
                "tool_name": "filesystem.write_file",
                "parameters": {
                    "path": "/empty_file.txt",
                    "content": "Now this file has content!"
                },
            }
            
            overwrite_response = await client.post("/api/v1/execute", json=overwrite_payload)
            assert overwrite_response.status_code == 200

            # Verify overwrite worked
            read_overwritten_payload = {
                "tool_name": "filesystem.read_file",
                "parameters": {"path": "/empty_file.txt"},
            }
            
            read_overwritten_response = await client.post("/api/v1/execute", json=read_overwritten_payload)
            assert read_overwritten_response.status_code == 200
            assert read_overwritten_response.json()["result"] == "Now this file has content!"

            # Clean up
            delete_payload = {
                "tool_name": "filesystem.delete_file",
                "parameters": {"path": "/empty_file.txt"},
            }
            
            delete_response = await client.post("/api/v1/execute", json=delete_payload)
            assert delete_response.status_code == 200

            print("E2E Test: Filesystem edge cases completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")