"""
Database module for IntentVerse.
Provides database abstraction layer with support for multiple database engines.
"""

from .factory import (
    DatabaseFactory,
    get_database,
    initialize_database,
    reset_database,
)
from .base import DatabaseInterface

# Backward compatibility functions that maintain the existing API
def create_db_and_tables():
    """Create database and tables using the current database instance."""
    database = get_database()
    database.create_db_and_tables()


def get_session():
    """Get a database session using the current database instance."""
    database = get_database()
    return database.get_session()


# For backward compatibility, expose the engine property
def get_engine():
    """Get the database engine (backward compatibility)."""
    database = get_database()
    return database.engine


__all__ = [
    "DatabaseFactory",
    "DatabaseInterface", 
    "get_database",
    "initialize_database",
    "reset_database",
    "create_db_and_tables",
    "get_session",
    "get_engine",
]

# Migration system exports
from .migrations import get_migration_manager, MigrationManager, Migration, DatabaseVersion
from .migration_scripts import get_all_migrations

__all__.extend([
    "get_migration_manager",
    "MigrationManager", 
    "Migration",
    "DatabaseVersion",
    "get_all_migrations",
])