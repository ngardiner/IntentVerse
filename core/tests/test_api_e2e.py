import pytest
import httpx
import time

# The URL of our core service, as seen from within the Docker network
CORE_API_URL = "http://core:8000"

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
    client = httpx.Client(base_url=CORE_API_URL)

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