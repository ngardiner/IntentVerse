import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine, Session, SQLModel
from pathlib import Path

# Adjust imports to match the new structure
from app.main import app
from app.database import get_session
from app.state_manager import StateManager
from app.module_loader import ModuleLoader
from app.auth import get_current_user, User

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///./test.db"  # Use a file-based SQLite for consistency in tests
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

def get_session_override():
    """Dependency override to use the test database session."""
    with Session(test_engine) as session:
        yield session

app.dependency_overrides[get_session] = get_session_override

@pytest.fixture(name="client")
def client_fixture():
    """
    Pytest fixture to create a TestClient.
    This fixture now correctly handles the application lifespan,
    ensuring the database and modules are initialized before tests run.
    """
    # This context manager will run the startup events before yielding
    with TestClient(app) as client:
        # Manually create tables for the in-memory/test database
        SQLModel.metadata.create_all(test_engine)
        yield client
        # Clean up by dropping tables after tests are done
        SQLModel.metadata.drop_all(test_engine)