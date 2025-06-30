"""
Tests for the rate limiting functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.rate_limiter import limiter, get_rate_limit_key_and_rate

# Create a test client
client = TestClient(app)


def test_rate_limiter_configuration():
    """Test that the rate limiter is properly configured."""
    assert hasattr(app.state, "limiter")
    assert app.state.limiter == limiter


@patch("app.rate_limiter.limiter.limiter.hit")
def test_rate_limit_exceeded(mock_hit):
    """Test that a 429 response is returned when rate limit is exceeded."""
    # Mock the limiter to report rate limit exceeded
    mock_hit.return_value = False

    # Mock the window stats to return some values
    limiter.limiter.get_window_stats = MagicMock(return_value=(60, 0))

    # Make a request to an API endpoint
    response = client.get("/api/v1/ui/layout")

    # Check that the response is a 429 Too Many Requests
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.text

    # Check that the rate limit headers are present
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
    assert "Retry-After" in response.headers


@patch("app.rate_limiter.limiter.limiter.hit")
def test_rate_limit_not_exceeded(mock_hit):
    """Test that requests are allowed when rate limit is not exceeded."""
    # Mock the limiter to report rate limit not exceeded
    mock_hit.return_value = True

    # Mock the window stats to return some values
    limiter.limiter.get_window_stats = MagicMock(return_value=(60, 99))

    # Make a request to an API endpoint
    response = client.get("/")

    # Check that the response is successful
    assert response.status_code == 200

    # Non-API endpoints should not have rate limit headers
    assert "X-RateLimit-Limit" not in response.headers
    assert "X-RateLimit-Remaining" not in response.headers
    assert "X-RateLimit-Reset" not in response.headers


def test_different_rate_limits_for_different_users():
    """Test that different users get different rate limits."""
    # Test unauthenticated user
    with patch("app.rate_limiter.get_remote_address", return_value="127.0.0.1"):
        key, rate = get_rate_limit_key_and_rate(
            MagicMock(state=MagicMock(user=None), headers={})
        )
        assert key == "127.0.0.1"
        assert "30/minute" in rate

    # Test authenticated non-admin user
    mock_user = MagicMock(id=1, is_admin=False)
    key, rate = get_rate_limit_key_and_rate(
        MagicMock(state=MagicMock(user=mock_user), headers={})
    )
    assert key == "user:1"
    assert "100/minute" in rate

    # Test admin user
    mock_admin = MagicMock(id=2, is_admin=True)
    key, rate = get_rate_limit_key_and_rate(
        MagicMock(state=MagicMock(user=mock_admin), headers={})
    )
    assert key == "admin:2"
    assert "200/minute" in rate

    # Test service account
    key, rate = get_rate_limit_key_and_rate(
        MagicMock(state=MagicMock(user=None), headers={"X-Service-API-Key": "test-key"})
    )
    assert key == "service:test-key"
    assert "200/minute" in rate
