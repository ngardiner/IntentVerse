"""
Abstract base class for database implementations.
Defines the interface that all database engines must implement.
"""

from abc import ABC, abstractmethod
from typing import Generator
from sqlmodel import Session, SQLModel
from sqlalchemy.engine import Engine


class DatabaseInterface(ABC):
    """Abstract interface for database implementations."""

    def __init__(self, config: dict):
        """
        Initialize the database with configuration.
        
        Args:
            config: Database configuration dictionary
        """
        self.config = config
        self._engine = None

    @property
    @abstractmethod
    def engine(self) -> Engine:
        """Get the database engine."""
        pass

    @abstractmethod
    def create_engine(self) -> Engine:
        """Create and configure the database engine."""
        pass

    @abstractmethod
    def create_db_and_tables(self) -> None:
        """Create the database and all tables."""
        pass

    @abstractmethod
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session."""
        pass

    @abstractmethod
    def get_connection_string(self) -> str:
        """Get the connection string for this database."""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the database configuration."""
        pass

    def run_migrations(self, target_version: str = None) -> bool:
        """
        Run database migrations.
        
        Args:
            target_version: Target version to migrate to (None for latest)
            
        Returns:
            True if successful, False otherwise
        """
        from .migrations import get_migration_manager
        
        migration_manager = get_migration_manager(self)
        
        if target_version:
            return migration_manager.migrate_to_version(target_version)
        else:
            return migration_manager.migrate_to_latest()

    def get_migration_status(self) -> dict:
        """
        Get the current migration status.
        
        Returns:
            Dictionary with migration status information
        """
        from .migrations import get_migration_manager
        
        migration_manager = get_migration_manager(self)
        current_version = migration_manager.get_current_version()
        pending = migration_manager.get_pending_migrations()
        validation = migration_manager.validate_migrations()
        
        return {
            "current_version": current_version,
            "pending_migrations": len(pending),
            "pending_migration_list": [f"{m.version}:{m.name}" for m in pending],
            "validation": validation
        }

    def validate_startup_connection(self) -> bool:
        """
        Validate database connection on startup with fail-fast behavior.
        
        Returns:
            True if connection is valid, False otherwise
        """
        from .validation import DatabaseConnectionManager
        
        manager = DatabaseConnectionManager(self)
        return manager.validate_startup_connection()

    def test_connection(self, timeout: float = None) -> tuple[bool, str]:
        """
        Test database connection with retry logic.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            Tuple of (success, error_message)
        """
        from .validation import DatabaseConnectionManager
        
        manager = DatabaseConnectionManager(self)
        return manager.test_connection(timeout)

    def get_health_status(self) -> dict:
        """
        Get comprehensive database health status.
        
        Returns:
            Dictionary with health status information
        """
        from .validation import DatabaseConnectionManager
        
        manager = DatabaseConnectionManager(self)
        return manager.get_health_status()

    def close(self) -> None:
        """Close database connections (optional override)."""
        if self._engine:
            self._engine.dispose()