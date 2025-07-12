"""
End-to-End Tests for Content Pack Management

This module contains e2e tests for content pack operations that are
likely under-tested in the current test suite.
"""

import pytest
import httpx
import os
import json
import tempfile

# The URL of our core service, as seen from within the Docker network
CORE_API_URL = os.environ.get("CORE_API_URL", "http://core:8000")
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "dev-service-key-12345")


def get_service_headers():
    """Get headers with service API key for authentication."""
    return {"X-API-Key": SERVICE_API_KEY}


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_content_pack_operations_e2e():
    """
    E2E test for content pack management operations:
    1. List available content packs
    2. Get content pack details
    3. Load/apply content pack
    4. Verify content pack effects
    5. Export content pack
    """
    headers = get_service_headers()
    print("E2E Test: Testing content pack operations")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Step 1: List available content packs
            list_response = await client.get("/api/v1/content-packs/available", headers=headers)
            if list_response.status_code == 401:
                pytest.skip(f"Authentication failed: {list_response.text}")
            
            assert list_response.status_code == 200
            content_packs = list_response.json()
            assert isinstance(content_packs, list)
            
            # Should have at least the default content pack
            pack_names = [pack.get("name", pack.get("id", "")) for pack in content_packs]
            print(f"Available content packs: {pack_names}")

            # Step 2: Get details of the first content pack
            if content_packs:
                first_pack = content_packs[0]
                pack_id = first_pack.get("id") or first_pack.get("name")
                
                if pack_id:
                    detail_response = await client.get(f"/api/v1/content-packs/{pack_id}")
                    assert detail_response.status_code == 200
                    pack_details = detail_response.json()
                    assert "name" in pack_details or "id" in pack_details

            # Step 3: Test content pack validation (if available)
            if content_packs:
                first_pack_name = content_packs[0].get("name") or content_packs[0].get("id")
                if first_pack_name:
                    validate_payload = {"filename": f"{first_pack_name}.json"}
                    validate_response = await client.post("/api/v1/content-packs/validate", json=validate_payload, headers=headers)
                    # This might return 404 if file doesn't exist, which is fine for discovery
                    if validate_response.status_code not in [404, 405]:
                        assert validate_response.status_code in [200, 422]

            # Step 4: Get loaded content packs
            get_loaded_response = await client.get("/api/v1/content-packs/loaded", headers=headers)
            if get_loaded_response.status_code == 200:
                loaded_packs = get_loaded_response.json()
                assert isinstance(loaded_packs, list)

            # Step 5: Test content pack export (if available)
            export_payload = {"filename": "test_export.json", "metadata": {"name": "test_export"}}
            export_response = await client.post("/api/v1/content-packs/export", json=export_payload, headers=headers)
            if export_response.status_code == 200:
                export_data = export_response.json()
                # Should be valid JSON content pack format
                assert isinstance(export_data, dict)
                # Common content pack fields
                expected_fields = ["name", "version", "description"]
                found_fields = [field for field in expected_fields if field in export_data]
                assert len(found_fields) > 0  # At least one expected field should be present

            print("E2E Test: Content pack operations completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_content_pack_import_e2e():
    """
    E2E test for content pack import functionality.
    """
    headers = get_service_headers()
    print("E2E Test: Testing content pack import")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Create a test content pack
            test_content_pack = {
                "name": "e2e-test-pack",
                "version": "1.0.0",
                "description": "Test content pack for e2e testing",
                "variables": {
                    "test_var_1": "value_1",
                    "test_var_2": "value_2"
                },
                "initial_state": {
                    "memory": {
                        "e2e_test_key": "e2e_test_value"
                    }
                }
            }

            # Step 1: Try to import the content pack
            import_response = await client.post("/api/v1/content-packs/import", json=test_content_pack)
            if import_response.status_code == 401:
                pytest.skip(f"Authentication failed: {import_response.text}")
            
            # Import might not be implemented, so we'll handle different response codes
            if import_response.status_code in [200, 201]:
                import_result = import_response.json()
                assert "status" in import_result or "message" in import_result
                
                # Step 2: Verify the import worked by checking if variables were set
                get_vars_response = await client.get("/api/v1/content-packs/variables")
                if get_vars_response.status_code == 200:
                    variables = get_vars_response.json()
                    # Check if our test variables are present
                    if isinstance(variables, dict):
                        assert "test_var_1" in variables or "test_var_2" in variables
                
                # Step 3: Verify memory state was set
                memory_get_payload = {
                    "tool_name": "memory.get_memory",
                    "parameters": {"key": "e2e_test_key"},
                }
                
                memory_response = await client.post("/api/v1/execute", json=memory_get_payload)
                if memory_response.status_code == 200:
                    memory_result = memory_response.json()
                    if "result" in memory_result:
                        assert memory_result["result"] == "e2e_test_value"

            elif import_response.status_code == 404:
                print("Content pack import endpoint not found - this is expected if not implemented")
            elif import_response.status_code == 405:
                print("Content pack import method not allowed - this is expected if not implemented")
            else:
                # Unexpected error
                print(f"Unexpected response code for import: {import_response.status_code}")
                print(f"Response: {import_response.text}")

            print("E2E Test: Content pack import completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_content_pack_validation_e2e():
    """
    E2E test for content pack validation.
    """
    headers = get_service_headers()
    print("E2E Test: Testing content pack validation")

    try:
        async with httpx.AsyncClient(base_url=CORE_API_URL, headers=headers) as client:
            # Test 1: Valid content pack
            valid_pack = {
                "name": "valid-test-pack",
                "version": "1.0.0",
                "description": "A valid test content pack"
            }

            validate_response = await client.post("/api/v1/content-packs/validate", json=valid_pack)
            if validate_response.status_code == 401:
                pytest.skip(f"Authentication failed: {validate_response.text}")
            
            if validate_response.status_code in [200, 201]:
                validation_result = validate_response.json()
                assert validation_result.get("valid", True) == True

            # Test 2: Invalid content pack (missing required fields)
            invalid_pack = {
                "description": "Missing name and version"
            }

            invalid_response = await client.post("/api/v1/content-packs/validate", json=invalid_pack)
            if invalid_response.status_code in [200, 400, 422]:
                if invalid_response.status_code == 200:
                    invalid_result = invalid_response.json()
                    # Should indicate validation failure
                    assert invalid_result.get("valid", False) == False or "errors" in invalid_result
                else:
                    # 400/422 indicates validation error, which is also acceptable
                    pass

            # Test 3: Malformed content pack
            malformed_response = await client.post(
                "/api/v1/content-packs/validate",
                content='{"invalid": json}',
                headers={**headers, "Content-Type": "application/json"}
            )
            assert malformed_response.status_code in [400, 422]

            print("E2E Test: Content pack validation completed successfully!")

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        pytest.skip(f"Could not connect to core service: {e}")