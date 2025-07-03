"""
Database factory for creating database instances based on configuration.
"""

import logging
from typing import Dict, Type

from .base import DatabaseInterface
from .sqlite import SQLiteDatabase


class DatabaseFactory:
    """Factory for creating database instances."""

    # Registry of available database implementations
    _implementations: Dict[str, Type[DatabaseInterface]] = {
        "sqlite": SQLiteDatabase,
        # Future implementations will be added here:
        # "postgresql": PostgreSQLDatabase,  # v1.2.0
        # "mysql": MySQLDatabase,            # v1.2.0
    }

    @classmethod
    def create_database(cls, config: dict) -> DatabaseInterface:
        """
        Create a database instance based on configuration.
        
        Args:
            config: Database configuration dictionary
            
        Returns:
            DatabaseInterface: Configured database instance
            
        Raises:
            ValueError: If database type is not supported
        """
        db_type = config.get("type", "sqlite").lower()
        
        if db_type not in cls._implementations:
            available_types = ", ".join(cls._implementations.keys())
            raise ValueError(
                f"Unsupported database type: {db_type}. "
                f"Available types: {available_types}"
            )
        
        implementation_class = cls._implementations[db_type]
        
        logging.info(f"Creating {db_type} database instance")
        
        # Create and validate the database instance
        database = implementation_class(config)
        
        try:
            database.validate_config()
        except Exception as e:
            logging.error(f"Database configuration validation failed: {e}")
            raise
        
        return database

    @classmethod
    def get_supported_types(cls) -> list:
        """Get list of supported database types."""
        return list(cls._implementations.keys())

    @classmethod
    def register_implementation(cls, db_type: str, implementation: Type[DatabaseInterface]) -> None:
        """
        Register a new database implementation.
        
        Args:
            db_type: Database type identifier
            implementation: Database implementation class
        """
        cls._implementations[db_type] = implementation
        logging.info(f"Registered database implementation: {db_type}")


# Global database instance (will be initialized by the factory)
_database_instance: DatabaseInterface = None


def get_database() -> DatabaseInterface:
    """Get the global database instance."""
    global _database_instance
    if _database_instance is None:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    return _database_instance


def initialize_database(config: dict) -> DatabaseInterface:
    """
    Initialize the global database instance.
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        DatabaseInterface: The initialized database instance
    """
    global _database_instance
    _database_instance = DatabaseFactory.create_database(config)
    logging.info("Database initialized successfully")
    return _database_instance


def reset_database() -> None:
    """Reset the global database instance (mainly for testing)."""
    global _database_instance
    if _database_instance:
        _database_instance.close()
    _database_instance = None