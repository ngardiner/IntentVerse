import pytest
import httpx
import os
import time

# The URL of our core service, as seen from within the Docker network
CORE_API_URL = os.environ.get("CORE_API_URL", "http://core:8000")
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "test-service-key-12345")

def get_service_headers():
    """Get headers with service API key for authentication."""
    return {"X-API-Key": SERVICE_API_KEY}

@pytest.mark.e2e
def test_write_and_read_end_to_end():
    """
    Performs an end-to-end test of the write/read cycle via the API.
    1. Writes a file using the /execute endpoint.
    2. Reads the filesystem state using the /filesystem/state endpoint.
    3. Asserts that the created file exists in the state.
    """
    # ARRANGE: Define the tool payload and the API client
    write_payload = {
        "tool_name": "filesystem.write_file",
        "parameters": {
            "path": "/e2e-test.txt",
            "content": "End-to-end test was successful!"
        }
    }
    client = httpx.Client(base_url=CORE_API_URL, headers=get_service_headers())

    # ACT (Step 1): Send the request to execute the write_file tool
    print("E2E Test: Executing write_file tool...")
    execute_response = client.post("/api/v1/execute", json=write_payload)
    
    # ASSERT (Step 1): Check if the write command was accepted
    assert execute_response.status_code == 200
    assert execute_response.json()["status"] == "success"

    # ACT (Step 2): Fetch the entire filesystem state to verify the write
    print("E2E Test: Fetching filesystem state...")
    state_response = client.get("/api/v1/filesystem/state")
    
    # ASSERT (Step 2): Check if the state was fetched successfully
    assert state_response.status_code == 200
    fs_state = state_response.json()
    
    # Find the newly created file in the root directory's children
    children = fs_state.get("children", [])
    found_file = next((f for f in children if f.get("name") == "e2e-test.txt"), None)

    assert found_file is not None, "The newly written file was not found in the state."
    assert found_file.get("type") == "file"

@pytest.mark.asyncio
async def test_execute_non_existent_tool_returns_404():
    """
    Verifies that the API returns a 404 Not Found error when a request
    is made to execute a tool that does not exist.
    """
    # Arrange: Define a payload for a tool that should not be registered.
    payload = {
        "tool_name": "nonexistent.tool",
        "parameters": {}
    }
    
    # Act: Make the POST request using an async client.
    async with httpx.AsyncClient(headers=get_service_headers()) as client:
        response = await client.post(f"{CORE_API_URL}/api/v1/execute", json=payload)

    # Assert: Check for a 404 status code and a specific error message.
    assert response.status_code == 404
    
    error_details = response.json()
    assert "detail" in error_details
    assert "Tool 'nonexistent.tool' not found" in error_details["detail"]

@pytest.mark.asyncio
async def test_memory_module_set_and_get_e2e():
    """
    Performs an end-to-end test of the Memory module, verifying both
    the 'set_memory' and 'get_memory' tool calls via the API.
    """
    # Arrange: Define a key and value to be stored in memory.
    test_key = "e2e_test_key_456"
    test_value = "This is a value stored for an async E2E run."

    async with httpx.AsyncClient(headers=get_service_headers()) as client:
        # --- Step 1: Set a value using the 'set_memory' tool ---
        set_payload = {
            "tool_name": "memory.set_memory",
            "parameters": {
                "key": test_key,
                "value": test_value
            }
        }
        
        # Act: Call the 'set_memory' tool.
        set_response = await client.post(f"{CORE_API_URL}/api/v1/execute", json=set_payload)
        
        # Assert: Ensure the call was successful.
        assert set_response.status_code == 200
        set_result = set_response.json()
        assert set_result.get("status") == "success"

        # --- Step 2: Get the value back using the 'get_memory' tool ---
        get_payload = {
            "tool_name": "memory.get_memory",
            "parameters": {
                "key": test_key
            }
        }

        # Act: Call the 'get_memory' tool.
        get_response = await client.post(f"{CORE_API_URL}/api/v1/execute", json=get_payload)

        # Assert: Ensure the call was successful and returned the correct value.
        assert get_response.status_code == 200
        get_result = get_response.json()
        assert "result" in get_result
        assert get_result["result"] == test_value

@pytest.mark.asyncio
async def test_database_module_e2e():
    """
    Performs an end-to-end test of the Database module.
    1. Creates a table using `database.execute_sql`.
    2. Inserts data into the new table.
    3. Queries the data back using `database.query`.
    4. Verifies the returned data is correct.
    """
    table_name = "e2e_test_table"
    async with httpx.AsyncClient(base_url=CORE_API_URL) as client:
        # --- Step 1: Create a table ---
        create_payload = {
            "tool_name": "database.execute_sql",
            "parameters": {
                "sql_query": f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, name TEXT, value REAL);"
            }
        }
        print(f"E2E Test: Creating table '{table_name}'...")
        create_response = await client.post("/api/v1/execute", json=create_payload)
        assert create_response.status_code == 200, f"Failed to create table. Response: {create_response.text}"
        assert create_response.json()["status"] == "success"

        # --- Step 2: Insert data into the table ---
        insert_payload = {
            "tool_name": "database.execute_sql",
            "parameters": {
                "sql_query": f"INSERT INTO {table_name} (id, name, value) VALUES (1, 'e2e_product', 99.99);"
            }
        }
        print(f"E2E Test: Inserting data into '{table_name}'...")
        insert_response = await client.post("/api/v1/execute", json=insert_payload)
        assert insert_response.status_code == 200, f"Failed to insert data. Response: {insert_response.text}"
        assert insert_response.json()["status"] == "success"

        # --- Step 3: Query the data back ---
        query_payload = {
            "tool_name": "database.query",
            "parameters": {
                "sql_query": f"SELECT * FROM {table_name} WHERE id = 1;"
            }
        }
        print(f"E2E Test: Querying data from '{table_name}'...")
        query_response = await client.post("/api/v1/execute", json=query_payload)
        assert query_response.status_code == 200, f"Failed to query data. Response: {query_response.text}"
        
        query_result = query_response.json()
        assert query_result["status"] == "success"
        
        # Verify the content of the result
        data = query_result["result"]
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0] == {"id": 1, "name": "e2e_product", "value": 99.99}