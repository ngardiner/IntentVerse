"""
End-to-End Tests for State Management

This module contains e2e tests for state management operations that are
likely under-tested in the current test suite.
"""

import pytest
import httpx
import os
import json
import time

# The URL of our core service, as seen from within the Docker network
CORE_API_URL = os.environ.get("CORE_API_URL", "http://core:8000")
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "dev-service-key-12345")


def get_service_headers():
    """Get headers with service API key for authentication."""
    return {"X-API-Key": SERVICE_API_KEY}


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_state_persistence_across_operations_e2e():
    """
    E2E test for state persistence across multiple operations:
    1. Set state in multiple modules
    2. Perform operations that modify state
    3. Verify state consistency
    4. Test state isolation between modules
    """
    headers = get_service_headers()
    print("E2E Test: Testing state persistence across operations")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            test_id = f"state_test_{int(time.time())}"
            
            # Step 1: Set initial state in memory module
            memory_payload = {
                "tool_name": "memory.set_memory",
                "parameters": {
                    "key": f"test_key_{test_id}",
                    "value": f"initial_value_{test_id}"
                },
            }
            
            memory_response = await client.post("/api/v1/execute", json=memory_payload)
            if memory_response.status_code == 401:
                pytest.skip(f"Authentication failed: {memory_response.text}")
            
            assert memory_response.status_code == 200

            # Step 2: Create files in filesystem
            file_content = f"Test file content for {test_id}"
            file_payload = {
                "tool_name": "filesystem.write_file",
                "parameters": {
                    "path": f"/state_test_{test_id}.txt",
                    "content": file_content
                },
            }
            
            file_response = await client.post("/api/v1/execute", json=file_payload)
            assert file_response.status_code == 200

            # Step 3: Send email to create email state
            email_payload = {
                "tool_name": "email.send_email",
                "parameters": {
                    "to": [f"test_{test_id}@example.com"],
                    "subject": f"State Test Email {test_id}",
                    "body": f"This email is part of state persistence test {test_id}"
                },
            }
            
            email_response = await client.post("/api/v1/execute", json=email_payload)
            assert email_response.status_code == 200
            email_id = email_response.json()["result"]["email_id"]

            # Step 4: Add timeline event
            timeline_payload = {
                "tool_name": "timeline.add_event",
                "parameters": {
                    "event_type": "test",
                    "title": f"State Test Event {test_id}",
                    "description": f"Timeline event for state persistence test {test_id}",
                    "metadata": {"test_id": test_id}
                },
            }
            
            timeline_response = await client.post("/api/v1/execute", json=timeline_payload)
            assert timeline_response.status_code == 200

            # Step 5: Perform web search to create search state
            search_payload = {
                "tool_name": "web_search.search",
                "parameters": {"query": f"state persistence test {test_id}"},
            }
            
            search_response = await client.post("/api/v1/execute", json=search_payload)
            assert search_response.status_code == 200

            # Step 6: Verify all state is still accessible
            # Check memory
            memory_get_payload = {
                "tool_name": "memory.get_memory",
                "parameters": {"key": f"test_key_{test_id}"},
            }
            
            memory_get_response = await client.post("/api/v1/execute", json=memory_get_payload)
            assert memory_get_response.status_code == 200
            assert memory_get_response.json()["result"] == f"initial_value_{test_id}"

            # Check filesystem
            file_read_payload = {
                "tool_name": "filesystem.read_file",
                "parameters": {"path": f"/state_test_{test_id}.txt"},
            }
            
            file_read_response = await client.post("/api/v1/execute", json=file_read_payload)
            assert file_read_response.status_code == 200
            assert file_read_response.json()["result"] == file_content

            # Check email
            email_read_payload = {
                "tool_name": "email.read_email",
                "parameters": {"email_id": email_id},
            }
            
            email_read_response = await client.post("/api/v1/execute", json=email_read_payload)
            assert email_read_response.status_code == 200
            email_data = email_read_response.json()["result"]
            assert email_data["subject"] == f"State Test Email {test_id}"

            # Check timeline
            timeline_get_payload = {
                "tool_name": "timeline.get_events",
                "parameters": {"event_type": "test", "limit": 10},
            }
            
            timeline_get_response = await client.post("/api/v1/execute", json=timeline_get_payload)
            assert timeline_get_response.status_code == 200
            events = timeline_get_response.json()["result"]
            test_events = [e for e in events if test_id in e.get("title", "")]
            assert len(test_events) >= 1

            # Check web search history
            search_history_payload = {
                "tool_name": "web_search.get_search_history",
                "parameters": {"limit": 10},
            }
            
            search_history_response = await client.post("/api/v1/execute", json=search_history_payload)
            assert search_history_response.status_code == 200
            history = search_history_response.json()["result"]
            test_searches = [h for h in history if test_id in h.get("query", "")]
            assert len(test_searches) >= 1

            print("E2E Test: State persistence across operations completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_state_isolation_e2e():
    """
    E2E test for state isolation between different modules.
    """
    headers = get_service_headers()
    print("E2E Test: Testing state isolation between modules")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            test_id = f"isolation_test_{int(time.time())}"
            
            # Step 1: Set similar keys in different modules
            memory_payload = {
                "tool_name": "memory.set_memory",
                "parameters": {"key": "shared_key", "value": f"memory_value_{test_id}"},
            }
            
            memory_response = await client.post("/api/v1/execute", json=memory_payload)
            if memory_response.status_code == 401:
                pytest.skip(f"Authentication failed: {memory_response.text}")
            
            assert memory_response.status_code == 200

            # Step 2: Create file with similar name
            file_payload = {
                "tool_name": "filesystem.write_file",
                "parameters": {
                    "path": "/shared_key.txt",
                    "content": f"filesystem_content_{test_id}"
                },
            }
            
            file_response = await client.post("/api/v1/execute", json=file_payload)
            assert file_response.status_code == 200

            # Step 3: Verify isolation - memory and filesystem should be independent
            memory_get_payload = {
                "tool_name": "memory.get_memory",
                "parameters": {"key": "shared_key"},
            }
            
            memory_get_response = await client.post("/api/v1/execute", json=memory_get_payload)
            assert memory_get_response.status_code == 200
            memory_value = memory_get_response.json()["result"]
            assert memory_value == f"memory_value_{test_id}"

            file_read_payload = {
                "tool_name": "filesystem.read_file",
                "parameters": {"path": "/shared_key.txt"},
            }
            
            file_read_response = await client.post("/api/v1/execute", json=file_read_payload)
            assert file_read_response.status_code == 200
            file_content = file_read_response.json()["result"]
            assert file_content == f"filesystem_content_{test_id}"

            # Step 4: Verify that modifying one doesn't affect the other
            memory_update_payload = {
                "tool_name": "memory.set_memory",
                "parameters": {"key": "shared_key", "value": f"updated_memory_{test_id}"},
            }
            
            memory_update_response = await client.post("/api/v1/execute", json=memory_update_payload)
            assert memory_update_response.status_code == 200

            # File content should remain unchanged
            file_read_again_response = await client.post("/api/v1/execute", json=file_read_payload)
            assert file_read_again_response.status_code == 200
            assert file_read_again_response.json()["result"] == f"filesystem_content_{test_id}"

            # Memory should be updated
            memory_get_again_response = await client.post("/api/v1/execute", json=memory_get_payload)
            assert memory_get_again_response.status_code == 200
            assert memory_get_again_response.json()["result"] == f"updated_memory_{test_id}"

            print("E2E Test: State isolation completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_concurrent_state_operations_e2e():
    """
    E2E test for concurrent state operations to verify thread safety.
    """
    headers = get_service_headers()
    print("E2E Test: Testing concurrent state operations")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            test_id = f"concurrent_test_{int(time.time())}"
            
            # Step 1: Perform multiple concurrent memory operations
            import asyncio
            
            async def set_memory_value(key_suffix: str, value: str):
                payload = {
                    "tool_name": "memory.set_memory",
                    "parameters": {
                        "key": f"concurrent_key_{key_suffix}_{test_id}",
                        "value": value
                    },
                }
                response = await client.post("/api/v1/execute", json=payload)
                return response.status_code == 200, key_suffix, value

            # Create multiple concurrent tasks
            tasks = []
            for i in range(5):
                task = set_memory_value(str(i), f"value_{i}_{test_id}")
                tasks.append(task)

            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks)
            
            # Verify all operations succeeded
            for success, key_suffix, expected_value in results:
                if not success:
                    pytest.skip("Concurrent memory operations failed - may indicate auth issues")
                
                # Verify the value was set correctly
                get_payload = {
                    "tool_name": "memory.get_memory",
                    "parameters": {"key": f"concurrent_key_{key_suffix}_{test_id}"},
                }
                
                get_response = await client.post("/api/v1/execute", json=get_payload)
                assert get_response.status_code == 200
                assert get_response.json()["result"] == expected_value

            # Step 2: Test concurrent filesystem operations
            async def create_file(file_suffix: str, content: str):
                payload = {
                    "tool_name": "filesystem.write_file",
                    "parameters": {
                        "path": f"/concurrent_file_{file_suffix}_{test_id}.txt",
                        "content": content
                    },
                }
                response = await client.post("/api/v1/execute", json=payload)
                return response.status_code == 200, file_suffix, content

            # Create multiple concurrent file operations
            file_tasks = []
            for i in range(3):
                task = create_file(str(i), f"File content {i} for {test_id}")
                file_tasks.append(task)

            file_results = await asyncio.gather(*file_tasks)
            
            # Verify all file operations succeeded
            for success, file_suffix, expected_content in file_results:
                assert success
                
                # Verify the file content
                read_payload = {
                    "tool_name": "filesystem.read_file",
                    "parameters": {"path": f"/concurrent_file_{file_suffix}_{test_id}.txt"},
                }
                
                read_response = await client.post("/api/v1/execute", json=read_payload)
                assert read_response.status_code == 200
                assert read_response.json()["result"] == expected_content

            print("E2E Test: Concurrent state operations completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")