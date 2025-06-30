"""
Tests for API versioning functionality.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.version_manager import version_manager


client = TestClient(app)


def test_api_versions_endpoint():
    """Test the API versions endpoint."""
    response = client.get("/api/versions")
    assert response.status_code == 200
    data = response.json()

    # Check that we have version information
    assert "versions" in data
    assert "current_version" in data
    assert data["current_version"] == "v2"

    # Check that we have at least v1 and v2
    versions = {v["version"] for v in data["versions"]}
    assert "v1" in versions
    assert "v2" in versions


def test_api_version_info_endpoint():
    """Test the API version info endpoint."""
    # Test v1 info
    response = client.get("/api/versions/v1")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "v1"
    assert data["status"] == "stable"

    # Test v2 info
    response = client.get("/api/versions/v2")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "v2"
    assert data["status"] == "current"

    # Test non-existent version
    response = client.get("/api/versions/v999")
    assert response.status_code == 404


def test_url_based_versioning():
    """Test URL-based versioning."""
    # Test v1 endpoint
    response = client.get("/api/v1/ui/layout")
    assert response.status_code == 200
    assert response.headers["X-API-Version"] == "v1"

    # Test v2 endpoint
    response = client.get("/api/v2/ui/layout")
    assert response.status_code == 200
    assert response.headers["X-API-Version"] == "v2"

    # Test v2-specific endpoint
    response = client.get("/api/v2/health")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "v2"
    assert data["status"] == "healthy"


def test_header_based_versioning():
    """Test header-based versioning."""
    # Test with v1 header
    response = client.get(
        "/api/ui/layout", headers={"X-API-Version": "v1"}  # No version in URL
    )
    assert response.status_code == 200
    assert response.headers["X-API-Version"] == "v1"

    # Test with v2 header
    response = client.get(
        "/api/ui/layout", headers={"X-API-Version": "v2"}  # No version in URL
    )
    assert response.status_code == 200
    assert response.headers["X-API-Version"] == "v2"


def test_version_precedence():
    """Test version precedence (URL > header > default)."""
    # URL should take precedence over header
    response = client.get(
        "/api/v1/ui/layout",  # v1 in URL
        headers={"X-API-Version": "v2"},  # v2 in header
    )
    assert response.status_code == 200
    assert response.headers["X-API-Version"] == "v1"  # URL wins

    # Header should take precedence over default
    response = client.get(
        "/api/ui/layout",  # No version in URL
        headers={"X-API-Version": "v1"},  # v1 in header
    )
    assert response.status_code == 200
    assert response.headers["X-API-Version"] == "v1"  # Header wins

    # Default should be used if no version specified
    response = client.get("/api/ui/layout")  # No version anywhere
    assert response.status_code == 200
    assert response.headers["X-API-Version"] == "v2"  # Default is v2


def test_deprecated_version_headers():
    """Test headers for deprecated versions."""
    # First, deprecate v1
    v1 = version_manager.get_version("v1")
    original_status = v1.status
    v1.status = "deprecated"
    version_manager.deprecated_versions.add("v1")

    try:
        # Test that deprecated headers are added
        response = client.get("/api/v1/ui/layout", headers={"X-API-Version": "v1"})
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"
        assert response.headers["X-API-Deprecated"] == "true"
        assert "X-API-Current-Version" in response.headers
        assert response.headers["X-API-Current-Version"] == "v2"
    finally:
        # Restore original status
        v1.status = original_status
        version_manager.deprecated_versions.remove("v1")
