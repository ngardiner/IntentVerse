"""
Database configuration for testing with the new abstraction layer.
This module sets up test database configuration before any app modules are imported.
"""

import os
from sqlmodel import create_engine
from sqlalchemy.pool import StaticPool

# Set test database configuration BEFORE importing any app modules
TEST_DATABASE_URL = "sqlite:///:memory:"

# Override database configuration for testing
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
    
    # Create a test configuration
    test_config = {
        "type": "sqlite",
        "url": TEST_DATABASE_URL,
    }
    
    # Initialize with test configuration
    initialize_database(test_config)
    
    # Also override the compatibility layer
    from app import database_compat
    database_compat.engine = test_engine
    
    # Override init_db engine
    from app import init_db
    init_db.engine = test_engine
    
    return test_engine