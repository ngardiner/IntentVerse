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

    def close(self) -> None:
        """Close database connections (optional override)."""
        if self._engine:
            self._engine.dispose()