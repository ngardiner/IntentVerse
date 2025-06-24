import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine, Session, SQLModel
from pathlib import Path
import os

# Adjust imports to match the new structure
from app.main import app
from app.database import get_session
from app.state_manager import StateManager
from app.module_loader import ModuleLoader
from app.auth import get_current_user, get_current_user_or_service, User, UserGroup, UserGroupLink
from app.models import AuditLog
from app.security import get_password_hash, create_access_token

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///./test.db"  # Use a file-based SQLite for consistency in tests
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

def get_session_override():
    """Dependency override to use the test database session."""
    with Session(test_engine) as session:
        yield session

app.dependency_overrides[get_session] = get_session_override

# Test user data
TEST_USER_DATA = {
    "username": "testuser",
    "password": "testpass123",
    "email": "test@example.com",
    "full_name": "Test User",
    "is_admin": True
}

TEST_SERVICE_API_KEY = "test-service-key-12345"

def create_test_user(session: Session) -> User:
    """Create a test user in the database."""
    hashed_password = get_password_hash(TEST_USER_DATA["password"])
    user = User(
        username=TEST_USER_DATA["username"],
        hashed_password=hashed_password,
        email=TEST_USER_DATA["email"],
        full_name=TEST_USER_DATA["full_name"],
        is_admin=TEST_USER_DATA["is_admin"]
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def get_test_token() -> str:
    """Generate a test JWT token for the test user."""
    return create_access_token(data={"sub": TEST_USER_DATA["username"]})

def get_auth_headers() -> dict:
    """Get authentication headers with JWT token."""
    token = get_test_token()
    return {"Authorization": f"Bearer {token}"}

def get_service_headers() -> dict:
    """Get authentication headers with service API key."""
    return {"X-API-Key": TEST_SERVICE_API_KEY}

@pytest.fixture(name="test_user")
def test_user_fixture():
    """Create a test user in the database."""
    with Session(test_engine) as session:
        user = create_test_user(session)
        yield user

@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user):
    """Get authentication headers for API requests."""
    return get_auth_headers()

@pytest.fixture(name="service_headers")
def service_headers_fixture():
    """Get service authentication headers for API requests."""
    return get_service_headers()

@pytest.fixture(name="client")
def client_fixture():
    """
    Pytest fixture to create a TestClient.
    This fixture now correctly handles the application lifespan,
    ensuring the database and modules are initialized before tests run.
    """
    # Set the test service API key
    os.environ["SERVICE_API_KEY"] = TEST_SERVICE_API_KEY
    
    # This context manager will run the startup events before yielding
    with TestClient(app) as client:
        # Manually create tables for the in-memory/test database
        SQLModel.metadata.create_all(test_engine)
        yield client
        # Clean up by dropping tables after tests are done
        SQLModel.metadata.drop_all(test_engine)

@pytest.fixture(name="authenticated_client")
def authenticated_client_fixture(client, test_user):
    """
    Pytest fixture to create a TestClient with authentication headers set.
    """
    client.headers.update(get_auth_headers())
    yield client

@pytest.fixture(name="session")
def session_fixture():
    """
    Pytest fixture to provide a database session for tests.
    """
    with Session(test_engine) as session:
        # Create tables if they don't exist
        SQLModel.metadata.create_all(test_engine)
        yield session

@pytest.fixture(name="service_client")
def service_client_fixture(client):
    """
    Pytest fixture to create a TestClient with service authentication headers set.
    """
    client.headers.update(get_service_headers())
    yield client