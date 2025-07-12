"""
Comprehensive End-to-End Tests for IntentVerse Core Engine

This module contains comprehensive e2e tests to improve coverage across
all major modules and API endpoints that are currently under-tested.

Current e2e coverage gaps identified:
1. Email module operations (send, list, read, drafts)
2. Web search functionality 
3. Timeline events and logging
4. Authentication and authorization flows
5. Content pack management operations
6. API v2 endpoints
7. Health and migration endpoints
8. Error handling and edge cases
9. Multi-module workflows
10. State persistence across operations
"""

import pytest
import httpx
import os
import time
import json
from typing import Dict, Any

# The URL of our core service, as seen from within the Docker network
CORE_API_URL = os.environ.get("CORE_API_URL", "http://core:8000")
# Use the same default as the auth module to ensure consistency in e2e tests
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "dev-service-key-12345")


def get_service_headers():
    """Get headers with service API key for authentication."""
    return {"X-API-Key": SERVICE_API_KEY}


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_email_module_complete_workflow_e2e():
    """
    Comprehensive e2e test for email module covering:
    1. Send email
    2. List emails in sent items
    3. Create draft
    4. Update draft
    5. List drafts
    6. Read specific email
    """
    headers = get_service_headers()
    print("E2E Test: Testing complete email workflow")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Step 1: Send an email
            send_payload = {
                "tool_name": "email.send_email",
                "parameters": {
                    "to": ["test@example.com", "user@test.com"],
                    "subject": "E2E Test Email",
                    "body": "This is a test email sent during e2e testing.",
                    "cc": ["cc@example.com"]
                },
            }
            
            send_response = await client.post("/api/v1/execute", json=send_payload)
            if send_response.status_code == 401:
                pytest.skip(f"Authentication failed: {send_response.text}")
            
            assert send_response.status_code == 200
            send_result = send_response.json()
            assert send_result["status"] == "success"
            email_id = send_result["result"]["email_id"]
            assert email_id.startswith("sent-")

            # Step 2: List sent emails
            list_sent_payload = {
                "tool_name": "email.list_emails",
                "parameters": {"folder": "sent_items", "limit": 10},
            }
            
            list_response = await client.post("/api/v1/execute", json=list_sent_payload)
            assert list_response.status_code == 200
            list_result = list_response.json()
            assert len(list_result["result"]) >= 1
            
            # Verify our sent email is in the list
            sent_emails = list_result["result"]
            found_email = next((e for e in sent_emails if e["email_id"] == email_id), None)
            assert found_email is not None
            assert found_email["subject"] == "E2E Test Email"
            assert "test@example.com" in found_email["to"]

            # Step 3: Create a draft
            draft_payload = {
                "tool_name": "email.create_draft",
                "parameters": {
                    "to": ["draft@example.com"],
                    "subject": "Draft Email",
                    "body": "This is a draft email."
                },
            }
            
            draft_response = await client.post("/api/v1/execute", json=draft_payload)
            assert draft_response.status_code == 200
            draft_result = draft_response.json()
            draft_id = draft_result["result"]["email_id"]
            assert draft_id.startswith("draft-")

            # Step 4: Update the draft
            update_draft_payload = {
                "tool_name": "email.update_draft",
                "parameters": {
                    "email_id": draft_id,
                    "subject": "Updated Draft Email",
                    "body": "This draft has been updated during e2e testing."
                },
            }
            
            update_response = await client.post("/api/v1/execute", json=update_draft_payload)
            assert update_response.status_code == 200

            # Step 5: List drafts
            list_drafts_payload = {
                "tool_name": "email.list_emails",
                "parameters": {"folder": "drafts"},
            }
            
            drafts_response = await client.post("/api/v1/execute", json=list_drafts_payload)
            assert drafts_response.status_code == 200
            drafts_result = drafts_response.json()
            assert len(drafts_result["result"]) >= 1
            
            # Verify our draft is in the list with updated content
            drafts = drafts_result["result"]
            found_draft = next((d for d in drafts if d["email_id"] == draft_id), None)
            assert found_draft is not None
            assert found_draft["subject"] == "Updated Draft Email"

            # Step 6: Read the specific sent email
            read_payload = {
                "tool_name": "email.read_email",
                "parameters": {"email_id": email_id},
            }
            
            read_response = await client.post("/api/v1/execute", json=read_payload)
            assert read_response.status_code == 200
            read_result = read_response.json()
            email_content = read_result["result"]
            assert email_content["subject"] == "E2E Test Email"
            assert email_content["body"] == "This is a test email sent during e2e testing."
            assert email_content["cc"] == ["cc@example.com"]

            print("E2E Test: Email module workflow completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_web_search_module_e2e():
    """
    E2E test for web search module covering:
    1. Perform search
    2. Get search history
    3. Get last search results
    4. Clear search history
    """
    headers = get_service_headers()
    print("E2E Test: Testing web search module")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Step 1: Perform a search
            search_payload = {
                "tool_name": "web_search.search",
                "parameters": {"query": "artificial intelligence machine learning"},
            }
            
            search_response = await client.post("/api/v1/execute", json=search_payload)
            if search_response.status_code == 401:
                pytest.skip(f"Authentication failed: {search_response.text}")
            
            assert search_response.status_code == 200
            search_result = search_response.json()
            results = search_result["result"]
            assert len(results) >= 3
            assert len(results) <= 5
            
            # Verify result structure
            for result in results:
                assert "title" in result
                assert "url" in result
                assert "snippet" in result
                assert result["url"].startswith("http")

            # Step 2: Perform another search to build history
            search2_payload = {
                "tool_name": "web_search.search",
                "parameters": {"query": "python programming tutorial"},
            }
            
            search2_response = await client.post("/api/v1/execute", json=search2_payload)
            assert search2_response.status_code == 200

            # Step 3: Get search history
            history_payload = {
                "tool_name": "web_search.get_search_history",
                "parameters": {"limit": 5},
            }
            
            history_response = await client.post("/api/v1/execute", json=history_payload)
            assert history_response.status_code == 200
            history_result = history_response.json()
            history = history_result["result"]
            assert len(history) >= 2
            
            # Verify history structure and content
            assert history[0]["query"] == "python programming tutorial"  # Most recent first
            assert history[1]["query"] == "artificial intelligence machine learning"
            assert "timestamp" in history[0]
            assert "results_count" in history[0]

            # Step 4: Get last search results
            last_results_payload = {
                "tool_name": "web_search.get_last_search_results",
                "parameters": {},
            }
            
            last_response = await client.post("/api/v1/execute", json=last_results_payload)
            assert last_response.status_code == 200
            last_result = last_response.json()
            last_results = last_result["result"]
            assert len(last_results) >= 3

            # Step 5: Clear search history
            clear_payload = {
                "tool_name": "web_search.clear_search_history",
                "parameters": {},
            }
            
            clear_response = await client.post("/api/v1/execute", json=clear_payload)
            assert clear_response.status_code == 200
            clear_result = clear_response.json()
            assert clear_result["result"]["status"] == "success"

            # Step 6: Verify history is cleared
            history_check_response = await client.post("/api/v1/execute", json=history_payload)
            assert history_check_response.status_code == 200
            empty_history = history_check_response.json()["result"]
            assert len(empty_history) == 0

            print("E2E Test: Web search module completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_timeline_module_e2e():
    """
    E2E test for timeline module covering:
    1. Add timeline events
    2. Get events with filtering
    3. Get events by date range
    4. Verify event structure and persistence
    """
    headers = get_service_headers()
    print("E2E Test: Testing timeline module")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Step 1: Add a timeline event
            add_event_payload = {
                "tool_name": "timeline.add_event",
                "parameters": {
                    "title": "E2E Test Event",
                    "description": "This event was created during e2e testing",
                    "event_type": "test",
                    "metadata": {"test_run": "comprehensive_e2e", "module": "timeline"}
                },
            }
            
            add_response = await client.post("/api/v1/execute", json=add_event_payload)
            if add_response.status_code == 401:
                pytest.skip(f"Authentication failed: {add_response.text}")
            
            assert add_response.status_code == 200
            add_result = add_response.json()
            event_id = add_result["result"]["event_id"]
            assert event_id is not None

            # Step 2: Add another event with different type
            add_event2_payload = {
                "tool_name": "timeline.add_event",
                "parameters": {
                    "title": "Second E2E Event",
                    "description": "Another test event",
                    "event_type": "system",
                    "metadata": {"priority": "high"}
                },
            }
            
            add2_response = await client.post("/api/v1/execute", json=add_event2_payload)
            assert add2_response.status_code == 200

            # Step 3: Get all events
            get_events_payload = {
                "tool_name": "timeline.get_events",
                "parameters": {"limit": 10},
            }
            
            events_response = await client.post("/api/v1/execute", json=get_events_payload)
            assert events_response.status_code == 200
            events_result = events_response.json()
            events = events_result["result"]
            assert len(events) >= 2
            
            # Verify our events are in the timeline
            test_events = [e for e in events if e["title"] in ["E2E Test Event", "Second E2E Event"]]
            assert len(test_events) >= 2

            # Step 4: Get events filtered by type
            filtered_payload = {
                "tool_name": "timeline.get_events",
                "parameters": {"event_type": "test", "limit": 5},
            }
            
            filtered_response = await client.post("/api/v1/execute", json=filtered_payload)
            assert filtered_response.status_code == 200
            filtered_result = filtered_response.json()
            filtered_events = filtered_result["result"]
            
            # All returned events should be of type "test"
            for event in filtered_events:
                if event["title"] == "E2E Test Event":
                    assert event["event_type"] == "test"
                    assert event["description"] == "This event was created during e2e testing"
                    assert "metadata" in event
                    assert event["metadata"]["test_run"] == "comprehensive_e2e"

            print("E2E Test: Timeline module completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multi_module_workflow_e2e():
    """
    E2E test that combines multiple modules in a realistic workflow:
    1. Create a file with search results
    2. Send an email about the file
    3. Log the workflow in timeline
    4. Store workflow metadata in memory
    5. Query database for workflow tracking
    """
    headers = get_service_headers()
    print("E2E Test: Testing multi-module workflow")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            workflow_id = f"workflow_{int(time.time())}"
            
            # Step 1: Perform a web search
            search_payload = {
                "tool_name": "web_search.search",
                "parameters": {"query": "FastAPI Python web framework"},
            }
            
            search_response = await client.post("/api/v1/execute", json=search_payload)
            if search_response.status_code == 401:
                pytest.skip(f"Authentication failed: {search_response.text}")
            
            assert search_response.status_code == 200
            search_results = search_response.json()["result"]

            # Step 2: Create a file with search results
            file_content = f"Search Results for FastAPI:\n\n"
            for i, result in enumerate(search_results[:3], 1):
                file_content += f"{i}. {result['title']}\n   {result['url']}\n   {result['snippet']}\n\n"

            write_file_payload = {
                "tool_name": "filesystem.write_file",
                "parameters": {
                    "path": f"/search_results_{workflow_id}.txt",
                    "content": file_content,
                },
            }
            
            write_response = await client.post("/api/v1/execute", json=write_file_payload)
            assert write_response.status_code == 200

            # Step 3: Send an email about the file
            email_payload = {
                "tool_name": "email.send_email",
                "parameters": {
                    "to": ["team@example.com"],
                    "subject": f"Search Results Report - {workflow_id}",
                    "body": f"Please find the FastAPI search results in file: /search_results_{workflow_id}.txt\n\nThis was generated automatically by the e2e workflow.",
                },
            }
            
            email_response = await client.post("/api/v1/execute", json=email_payload)
            assert email_response.status_code == 200
            email_id = email_response.json()["result"]["email_id"]

            # Step 4: Log the workflow in timeline
            timeline_payload = {
                "tool_name": "timeline.add_event",
                "parameters": {
                    "title": f"Multi-Module Workflow Completed",
                    "description": f"Completed workflow {workflow_id}: search -> file -> email",
                    "event_type": "workflow",
                    "metadata": {
                        "workflow_id": workflow_id,
                        "email_id": email_id,
                        "file_path": f"/search_results_{workflow_id}.txt",
                        "search_query": "FastAPI Python web framework"
                    }
                },
            }
            
            timeline_response = await client.post("/api/v1/execute", json=timeline_payload)
            assert timeline_response.status_code == 200

            # Step 5: Store workflow metadata in memory
            memory_payload = {
                "tool_name": "memory.set_memory",
                "parameters": {
                    "key": f"workflow_metadata_{workflow_id}",
                    "value": json.dumps({
                        "status": "completed",
                        "steps": ["search", "file_creation", "email", "timeline"],
                        "email_id": email_id,
                        "timestamp": time.time()
                    })
                },
            }
            
            memory_response = await client.post("/api/v1/execute", json=memory_payload)
            assert memory_response.status_code == 200

            # Step 6: Create a database table to track workflows
            create_table_payload = {
                "tool_name": "database.execute_sql",
                "parameters": {
                    "sql_query": """
                    CREATE TABLE IF NOT EXISTS workflow_tracking (
                        id INTEGER PRIMARY KEY,
                        workflow_id TEXT UNIQUE,
                        status TEXT,
                        email_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                },
            }
            
            db_create_response = await client.post("/api/v1/execute", json=create_table_payload)
            assert db_create_response.status_code == 200

            # Step 7: Insert workflow record
            insert_payload = {
                "tool_name": "database.execute_sql",
                "parameters": {
                    "sql_query": f"""
                    INSERT INTO workflow_tracking (workflow_id, status, email_id)
                    VALUES ('{workflow_id}', 'completed', '{email_id}');
                    """
                },
            }
            
            db_insert_response = await client.post("/api/v1/execute", json=insert_payload)
            assert db_insert_response.status_code == 200

            # Step 8: Query the workflow record
            query_payload = {
                "tool_name": "database.query",
                "parameters": {
                    "sql_query": f"SELECT * FROM workflow_tracking WHERE workflow_id = '{workflow_id}';"
                },
            }
            
            query_response = await client.post("/api/v1/execute", json=query_payload)
            assert query_response.status_code == 200
            query_result = query_response.json()["result"]
            assert len(query_result) == 1
            assert query_result[0]["workflow_id"] == workflow_id
            assert query_result[0]["status"] == "completed"
            assert query_result[0]["email_id"] == email_id

            # Step 9: Verify memory storage
            memory_get_payload = {
                "tool_name": "memory.get_memory",
                "parameters": {"key": f"workflow_metadata_{workflow_id}"},
            }
            
            memory_get_response = await client.post("/api/v1/execute", json=memory_get_payload)
            assert memory_get_response.status_code == 200
            stored_metadata = json.loads(memory_get_response.json()["result"])
            assert stored_metadata["status"] == "completed"
            assert stored_metadata["email_id"] == email_id
            assert len(stored_metadata["steps"]) == 4

            print("E2E Test: Multi-module workflow completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_v2_endpoints_e2e():
    """
    E2E test for API v2 endpoints to ensure they work correctly.
    """
    headers = get_service_headers()
    print("E2E Test: Testing API v2 endpoints")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Test API v2 execute endpoint
            v2_payload = {
                "tool_name": "memory.set_memory",
                "parameters": {"key": "v2_test", "value": "API v2 working"},
            }
            
            v2_response = await client.post("/api/v2/execute", json=v2_payload)
            if v2_response.status_code == 401:
                pytest.skip(f"Authentication failed: {v2_response.text}")
            
            assert v2_response.status_code == 200
            v2_result = v2_response.json()
            assert v2_result["status"] == "success"

            # Verify the value was stored by retrieving it via v1 API
            get_payload = {
                "tool_name": "memory.get_memory",
                "parameters": {"key": "v2_test"},
            }
            
            get_response = await client.post("/api/v1/execute", json=get_payload)
            assert get_response.status_code == 200
            assert get_response.json()["result"] == "API v2 working"

            print("E2E Test: API v2 endpoints completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_health_and_status_endpoints_e2e():
    """
    E2E test for health check and status endpoints.
    """
    headers = get_service_headers()
    print("E2E Test: Testing health and status endpoints")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Test root endpoint
            root_response = await client.get("/")
            assert root_response.status_code == 200
            root_data = root_response.json()
            assert "message" in root_data
            assert "IntentVerse" in root_data["message"]

            # Test health endpoint
            health_response = await client.get("/health")
            assert health_response.status_code == 200
            health_data = health_response.json()
            assert health_data["status"] == "healthy"
            assert "timestamp" in health_data

            # Test version endpoint
            version_response = await client.get("/version")
            assert version_response.status_code == 200
            version_data = version_response.json()
            assert "version" in version_data
            assert "api_versions" in version_data

            print("E2E Test: Health and status endpoints completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_error_handling_e2e():
    """
    E2E test for error handling scenarios.
    """
    headers = get_service_headers()
    print("E2E Test: Testing error handling scenarios")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Test invalid tool name
            invalid_tool_payload = {
                "tool_name": "invalid.nonexistent_tool",
                "parameters": {},
            }
            
            invalid_response = await client.post("/api/v1/execute", json=invalid_tool_payload)
            if invalid_response.status_code == 401:
                pytest.skip(f"Authentication failed: {invalid_response.text}")
            
            assert invalid_response.status_code == 404
            error_data = invalid_response.json()
            assert "detail" in error_data
            assert "not found" in error_data["detail"].lower()

            # Test invalid parameters
            invalid_params_payload = {
                "tool_name": "memory.set_memory",
                "parameters": {"invalid_param": "value"},  # Missing required 'key' and 'value'
            }
            
            invalid_params_response = await client.post("/api/v1/execute", json=invalid_params_payload)
            assert invalid_params_response.status_code in [400, 422]  # Bad request or validation error

            # Test malformed JSON
            malformed_response = await client.post(
                "/api/v1/execute", 
                content='{"invalid": json}',
                headers={**headers, "Content-Type": "application/json"}
            )
            assert malformed_response.status_code == 422

            print("E2E Test: Error handling scenarios completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")