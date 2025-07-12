"""
Database factory for creating database instances based on configuration.
"""

import logging
from typing import Dict, Type

from .base import DatabaseInterface
from .sqlite import SQLiteDatabase

# Import PostgreSQL implementation (v1.2.0)
try:
    from .postgresql import PostgreSQLDatabase
    _POSTGRESQL_AVAILABLE = True
except ImportError:
    _POSTGRESQL_AVAILABLE = False
    PostgreSQLDatabase = None

# Import MySQL implementation (v1.2.0)
try:
    from .mysql import MySQLDatabase
    _MYSQL_AVAILABLE = True
except ImportError:
    _MYSQL_AVAILABLE = False
    MySQLDatabase = None


class DatabaseFactory:
    """Factory for creating database instances."""

    # Registry of available database implementations
    _implementations: Dict[str, Type[DatabaseInterface]] = {
        "sqlite": SQLiteDatabase,
    }
    
    # Add PostgreSQL if available (v1.2.0)
    if _POSTGRESQL_AVAILABLE:
        _implementations["postgresql"] = PostgreSQLDatabase
    
    # Add MySQL if available (v1.2.0)
    if _MYSQL_AVAILABLE:
        _implementations["mysql"] = MySQLDatabase
        _implementations["mariadb"] = MySQLDatabase  # MariaDB uses same implementation

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
        db_type = config.get("type")
        
        if not db_type:
            raise ValueError("Database type must be specified in configuration")
        
        db_type = db_type.lower()
        
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
        
        # Enhanced configuration validation
        from .validation import validate_database_config
        
        is_valid, errors, warnings = validate_database_config(config)
        
        if not is_valid:
            error_msg = "Database configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        if warnings:
            logging.warning("Database configuration warnings:")
            for warning in warnings:
                logging.warning(f"  - {warning}")
        
        # Validate basic database interface requirements
        try:
            database.validate_config()
        except Exception as e:
            logging.error(f"Database interface validation failed: {e}")
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


def initialize_database(config: dict, validate_connection: bool = True) -> DatabaseInterface:
    """
    Initialize the global database instance with enhanced validation.
    
    Args:
        config: Database configuration dictionary
        validate_connection: Whether to validate connection on startup (default: True)
        
    Returns:
        DatabaseInterface: The initialized database instance
        
    Raises:
        RuntimeError: If database initialization or validation fails
    """
    global _database_instance
    
    try:
        _database_instance = DatabaseFactory.create_database(config)
        
        # Validate connection on startup if requested
        if validate_connection:
            if not _database_instance.validate_startup_connection():
                raise RuntimeError("Database connection validation failed during initialization")
        
        logging.info("Database initialized successfully")
        return _database_instance
        
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        # Clean up partial initialization
        if _database_instance:
            try:
                _database_instance.close()
            except Exception:
                pass
            _database_instance = None
        raise RuntimeError(f"Database initialization failed: {e}") from e


def reset_database() -> None:
    """Reset the global database instance (mainly for testing)."""
    global _database_instance
    if _database_instance:
        _database_instance.close()
    _database_instance = None