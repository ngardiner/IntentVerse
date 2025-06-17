"""
Unit tests for the User model.
"""
import pytest
from sqlmodel import Session, create_engine, SQLModel
from app.models import User


@pytest.fixture
def test_engine():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test database session."""
    with Session(test_engine) as session:
        yield session


def test_user_model_creation():
    """Test creating a User model instance."""
    user = User(username="testuser", hashed_password="hashed123")
    assert user.username == "testuser"
    assert user.hashed_password == "hashed123"
    assert user.id is None  # Should be None before saving to DB


def test_user_model_with_id():
    """Test creating a User model with an explicit ID."""
    user = User(id=1, username="testuser", hashed_password="hashed123")
    assert user.id == 1
    assert user.username == "testuser"
    assert user.hashed_password == "hashed123"


def test_user_model_database_operations(test_session):
    """Test saving and retrieving a User from the database."""
    # Create and save a user
    user = User(username="dbuser", hashed_password="dbhashed123")
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    
    # Verify the user was saved with an ID
    assert user.id is not None
    assert user.username == "dbuser"
    assert user.hashed_password == "dbhashed123"
    
    # Retrieve the user from the database
    retrieved_user = test_session.get(User, user.id)
    assert retrieved_user is not None
    assert retrieved_user.username == "dbuser"
    assert retrieved_user.hashed_password == "dbhashed123"


def test_user_model_unique_username(test_session):
    """Test that usernames must be unique."""
    # Create first user
    user1 = User(username="uniqueuser", hashed_password="hash1")
    test_session.add(user1)
    test_session.commit()
    
    # Try to create second user with same username
    user2 = User(username="uniqueuser", hashed_password="hash2")
    test_session.add(user2)
    
    # This should raise an integrity error due to unique constraint
    with pytest.raises(Exception):  # SQLite will raise IntegrityError
        test_session.commit()