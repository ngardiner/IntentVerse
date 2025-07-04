import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from pathlib import Path
import os

# Import logging configuration
from tests.conftest_logging import configure_test_logging

# Set the test service API key BEFORE importing any app modules
# Only override if not already set (e.g., by docker-compose for e2e tests)
TEST_SERVICE_API_KEY = "test-service-key-12345"
if "SERVICE_API_KEY" not in os.environ:
    os.environ["SERVICE_API_KEY"] = TEST_SERVICE_API_KEY

# Set up test database configuration using the new abstraction layer
from tests.conftest_database import override_database_for_testing, get_test_engine

# Override database configuration for testing
test_engine = override_database_for_testing()

# Now import the app and other modules
from app.main import app
from app.database_compat import get_session
from app.state_manager import StateManager
from app.module_loader import ModuleLoader
from app.auth import (
    get_current_user,
    get_current_user_or_service,
    User,
    UserGroup,
    UserGroupLink,
)

# Import ALL models to ensure they're registered with SQLModel metadata
from app.models import (
    AuditLog,
    Role,
    Permission,
    UserRoleLink,
    GroupRoleLink,
    RolePermissionLink,
    ModuleConfiguration,
    ContentPackVariable,
    User,
    UserGroup,
    UserGroupLink,
)
from app.security import get_password_hash, create_access_token


def get_session_override():
    """Dependency override to use the test database session."""
    # Use the abstraction layer for session management
    return get_session()


# Override the database session dependency
app.dependency_overrides[get_session] = get_session_override

# Test user data
TEST_USER_DATA = {
    "username": "testuser",
    "password": "testpass123",
    "email": "test@example.com",
    "full_name": "Test User",
    "is_admin": True,
}


def setup_test_database(test_engine):
    """Set up the test database with RBAC system and test data."""
    from app.rbac import initialize_rbac_system

    # Initialize RBAC system first to ensure roles and permissions exist
    with Session(test_engine) as session:
        initialize_rbac_system(session)


def create_test_user(test_engine) -> User:
    """Create a test user in the database."""
    # Check if user already exists
    from sqlmodel import select
    with Session(test_engine) as session:
        existing_user = session.exec(
            select(User).where(User.username == TEST_USER_DATA["username"])
        ).first()
        
        if existing_user:
            return existing_user
        
        hashed_password = get_password_hash(TEST_USER_DATA["password"])
        user = User(
            username=TEST_USER_DATA["username"],
            hashed_password=hashed_password,
            email=TEST_USER_DATA["email"],
            full_name=TEST_USER_DATA["full_name"],
            is_admin=TEST_USER_DATA["is_admin"],
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        
        # Ensure the admin role is assigned to the admin user
        from app.rbac import assign_admin_role_to_admins
        assign_admin_role_to_admins(session)
        
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
    return {"X-API-Key": os.environ.get("SERVICE_API_KEY", TEST_SERVICE_API_KEY)}


@pytest.fixture(name="test_user")
def test_user_fixture():
    """Create a test user in the database."""
    # Ensure tables are created first
    create_test_db_and_tables()
    setup_test_database(test_engine)
    
    user = create_test_user(test_engine)
    yield user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user):
    """Get authentication headers for API requests."""
    return get_auth_headers()


@pytest.fixture(name="service_headers")
def service_headers_fixture():
    """Get service authentication headers for API requests."""
    return get_service_headers()


def create_test_db_and_tables():
    """Create all database tables for testing, ensuring all models are imported."""
    # Import all models to ensure they're registered with SQLModel metadata
    # This matches what's done in app.database.create_db_and_tables()
    from app.models import (
        User,
        UserGroup,
        UserGroupLink,
        AuditLog,
        ModuleConfiguration,
        ContentPackVariable,
        Role,
        Permission,
        UserRoleLink,
        GroupRoleLink,
        RolePermissionLink,
    )

    # Create all tables
    SQLModel.metadata.create_all(test_engine)

    # Verify critical tables exist using the test engine directly
    with Session(test_engine) as session:
        try:
            session.exec(text("SELECT COUNT(*) FROM auditlog")).first()
            session.exec(text("SELECT COUNT(*) FROM user")).first()
            session.exec(text("SELECT COUNT(*) FROM role")).first()
        except Exception as e:
            raise RuntimeError(f"Failed to create test database tables: {e}")


@pytest.fixture(name="client")
def client_fixture():
    """
    Pytest fixture to create a TestClient.
    This fixture now correctly handles the application lifespan,
    ensuring the database and modules are initialized before tests run.
    """
    # Create all database tables
    create_test_db_and_tables()

    # Set up test database with RBAC system
    setup_test_database(test_engine)

    # This context manager will run the startup events before yielding
    with TestClient(app) as client:
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
    # Ensure tables are created
    create_test_db_and_tables()
    
    # Set up test database with RBAC system
    setup_test_database(test_engine)

    with Session(test_engine) as session:
        yield session


@pytest.fixture(name="service_client")
def service_client_fixture(client):
    """
    Pytest fixture to create a TestClient with service authentication headers set.
    """
    client.headers.update(get_service_headers())
    yield client
