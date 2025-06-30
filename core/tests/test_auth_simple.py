"""
Simplified authentication tests that focus on the core functionality
using a hybrid approach: unit tests with mocks + integration tests.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.auth import get_current_user, get_current_user_or_service, log_audit_event
from app.models import User, AuditLog


def test_password_hashing():
    """Tests that password hashing and verification work correctly."""
    password = "testpassword"
    hashed_password = get_password_hash(password)
    assert hashed_password != password
    assert verify_password(password, hashed_password)
    assert not verify_password("wrongpassword", hashed_password)


def test_jwt_token_handling():
    """Tests the creation and decoding of JWT tokens."""
    username = "testuser"
    token = create_access_token(data={"sub": username})
    assert isinstance(token, str)

    decoded_username = decode_access_token(token)
    assert decoded_username == username


def test_decode_invalid_token():
    """Tests that decoding an invalid token returns None."""
    assert decode_access_token("invalid.token.string") is None


def test_service_authentication_headers(service_client: TestClient):
    """Test that service authentication headers are properly set."""
    # Test a simple endpoint that should work with service auth
    response = service_client.get("/")
    assert response.status_code == 200
    assert "Welcome to the IntentVerse Core Engine" in response.json()["message"]


def test_protected_endpoint_without_auth(client: TestClient):
    """Tests that accessing a protected endpoint without auth fails."""
    response = client.get("/users/me")
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]


# --- Unit Tests with Mocks ---


@patch("app.auth.get_session")
def test_get_current_user_with_valid_token(mock_get_session):
    """Test get_current_user with a valid token using mocked database."""
    # Create a mock session and user
    mock_session = Mock(spec=Session)
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
    )

    # Mock the database query
    mock_session.exec.return_value.first.return_value = mock_user
    mock_get_session.return_value = mock_session

    # Create a valid token
    token = create_access_token(data={"sub": "testuser"})

    # Test the function
    result = get_current_user(token=token, session=mock_session)

    assert result == mock_user
    assert result.username == "testuser"


@patch("app.auth.get_session")
def test_get_current_user_with_invalid_token(mock_get_session):
    """Test get_current_user with an invalid token."""
    from fastapi import HTTPException

    mock_session = Mock(spec=Session)
    mock_get_session.return_value = mock_session

    # Test with invalid token
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="invalid.token", session=mock_session)

    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in str(exc_info.value.detail)


@patch("app.auth.get_session")
@patch("os.getenv")
def test_get_current_user_or_service_with_api_key(mock_getenv, mock_get_session):
    """Test get_current_user_or_service with valid API key."""
    mock_session = Mock(spec=Session)
    mock_get_session.return_value = mock_session

    # Mock os.getenv to return the test service API key
    mock_getenv.return_value = "test-service-key-12345"

    # Test with valid API key
    result = get_current_user_or_service(
        session=mock_session,
        token=None,
        api_key="test-service-key-12345",  # This matches the test environment key
    )

    assert result == "service"


@patch("app.auth.get_session")
def test_get_current_user_or_service_with_jwt_token(mock_get_session):
    """Test get_current_user_or_service with valid JWT token."""
    # Create a mock session and user
    mock_session = Mock(spec=Session)
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
    )

    # Mock the database query
    mock_session.exec.return_value.first.return_value = mock_user
    mock_get_session.return_value = mock_session

    # Create a valid token
    token = create_access_token(data={"sub": "testuser"})

    # Test the function
    result = get_current_user_or_service(
        session=mock_session, token=token, api_key=None
    )

    assert result == mock_user
    assert result.username == "testuser"


@patch("os.getenv")
def test_log_audit_event_with_mock(mock_getenv):
    """Test audit logging with mocked session."""
    # Mock os.getenv to return a non-test key so audit logging is not skipped
    mock_getenv.return_value = "non-test-key"

    mock_session = Mock(spec=Session)

    # Test audit logging
    log_audit_event(
        session=mock_session,
        user_id=1,
        username="testuser",
        action="test_action",
        resource_type="test_resource",
        status="success",
    )

    # Verify that session.add and session.commit were called
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

    # Verify the audit log object was created correctly
    added_audit_log = mock_session.add.call_args[0][0]
    assert isinstance(added_audit_log, AuditLog)
    assert added_audit_log.username == "testuser"
    assert added_audit_log.action == "test_action"
    assert added_audit_log.status == "success"
