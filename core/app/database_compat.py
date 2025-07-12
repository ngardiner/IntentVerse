"""
Database module - backward compatibility layer.
This file maintains the existing API while using the new database abstraction layer.
"""

import logging
from .config import Config
from .database import initialize_database, get_database, create_db_and_tables as _create_db_and_tables, get_session as _get_session

# Initialize the database using the configuration with enhanced validation
import os
_is_testing = os.getenv("SERVICE_API_KEY") == "test-service-key-12345"
_db_config = Config.get_database_config()
initialize_database(_db_config, validate_connection=not _is_testing)

# Backward compatibility: expose engine directly
engine = get_database().engine


def create_db_and_tables():
    """
    Creates the database file and all tables defined by our SQLModel classes.
    Delegates to the database abstraction layer.
    """
    _create_db_and_tables()


def get_session():
    """
    Dependency function that provides a database session to the API endpoints.
    Delegates to the database abstraction layer.
    
    This function handles the generator pattern correctly for FastAPI dependency injection.
    """
    session_gen = _get_session()
    session = next(session_gen)
    try:
        yield session
    finally:
        session.close()
