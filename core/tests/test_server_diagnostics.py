import os
import httpx
import pytest

# The base URL for the core API, which the test client will target.
# It uses the service name 'core' from docker-compose, which Docker's internal DNS resolves.
CORE_API_URL = "http://core:8000"

@pytest.mark.e2e
def test_server_module_loader_diagnostics():
    """
    Connects to the running core service and calls the debug endpoint
    to check the state of the ModuleLoader.
    """
    client = httpx.Client(base_url=CORE_API_URL)
    
    print("\n--- Running Server Diagnostics Test ---")
    
    # ACT: Call the debug endpoint
    try:
        response = client.get("/api/v1/debug/module-loader-state")
    except httpx.ConnectError as e:
        pytest.fail(f"Could not connect to the core service at {CORE_API_URL}. Is it running? Error: {e}")

    # ASSERT: Check the response and its data
    print(f"Debug endpoint status code: {response.status_code}")
    
    # Try to parse JSON, but print raw text if it fails
    try:
        data = response.json()
        import json
        print("Debug endpoint response data:")
        print(json.dumps(data, indent=2))
    except Exception:
        print("Could not parse JSON from debug endpoint. Raw response text:")
        print(response.text)
        data = {}

    # The server must respond with 200 OK
    assert response.status_code == 200, "The debug endpoint should always be available."

    # The module loader should not have encountered errors
    assert not data.get("errors"), "The module loader reported errors during startup."

    # The module loader must find and load at least one module
    assert data.get("loaded_modules"), "The module loader did not load any modules."

    print("--- Server Diagnostics Test Passed ---")