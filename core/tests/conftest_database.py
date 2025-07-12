"""
Database configuration for testing with the new abstraction layer.
This module sets up test database configuration before any app modules are imported.
"""

import os
from sqlmodel import create_engine
from sqlalchemy.pool import StaticPool

# Set test database configuration BEFORE importing any app modules
TEST_DATABASE_URL = "sqlite:///:memory:"

# Only override database configuration for unit tests, not integration tests
# Integration tests (marked with @pytest.mark.database_integration) should use
# the actual database configuration provided by CI environment variables
if not os.getenv("INTENTVERSE_DB_TYPE") or os.getenv("INTENTVERSE_DB_TYPE") == "sqlite":
    # Override database configuration for testing only if not already set to a real database
    os.environ["INTENTVERSE_DB_TYPE"] = "sqlite"
    os.environ["INTENTVERSE_DB_URL"] = TEST_DATABASE_URL

# Create test engine with proper configuration for in-memory SQLite
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Use StaticPool to share the same connection
    pool_pre_ping=True,
)

def get_test_engine():
    """Get the test database engine."""
    return test_engine

def override_database_for_testing():
    """Override the database configuration for testing."""
    # Import after setting environment variables
    from app.database import reset_database, initialize_database
    from app.config import Config
    
    # Reset any existing database instance
    reset_database()
    
    # Check if we're running integration tests with a real database
    db_type = os.getenv("INTENTVERSE_DB_TYPE", "sqlite")
    
    if db_type != "sqlite":
        # For integration tests, use the actual database configuration
        # Don't override with SQLite test engine
        config = Config.get_database_config()
        db_instance = initialize_database(config)
        return db_instance._engine if hasattr(db_instance, '_engine') else None
    
    # For unit tests, use SQLite in-memory database
    test_config = {
        "type": "sqlite",
        "url": TEST_DATABASE_URL,
    }
    
    # Initialize with test configuration
    db_instance = initialize_database(test_config)
    
    # Force the database instance to use our test engine
    db_instance._engine = test_engine
    
    # Also override the compatibility layer
    from app import database_compat
    database_compat.engine = test_engine
    
    # Override init_db engine
    from app import init_db
    init_db.engine = test_engine
    
    return test_engine