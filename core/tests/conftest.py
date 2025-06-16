# core/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine, Session, SQLModel
from pathlib import Path

# Adjust the import path to be absolute from the 'core' directory perspective
from app.main import app
from app.database import get_session
from app.state_manager import StateManager
from app.module_loader import ModuleLoader
from app.api import create_api_routes
from app.auth import get_current_user
from app.models import User

# --- Test Database Setup ---
# Use an in-memory SQLite database for testing to keep tests fast and isolated
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

# --- Fixtures ---
@pytest.fixture(name="session")
def session_fixture():
    """
    Pytest fixture to create a new database session for each test.
    It creates all tables before the test runs and drops them afterward.
    """
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """
    Pytest fixture to create a TestClient for the API.
    This client will use the isolated in-memory test database.
    """

    def get_session_override():
        return session
    
    # Replace the app's get_session dependency with our override
    app.dependency_overrides[get_session] = get_session_override
    
    # Yield the client to the test function
    client = TestClient(app)
    yield client
    
    # Clean up the dependency override after the test is done
    app.dependency_overrides.clear()