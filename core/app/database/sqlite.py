"""
SQLite database implementation.
Maintains the existing SQLite functionality with the new interface.
"""

import logging
import os
from typing import Generator
from sqlmodel import create_engine, SQLModel, Session, select
from sqlalchemy.engine import Engine

from .base import DatabaseInterface


class SQLiteDatabase(DatabaseInterface):
    """SQLite database implementation."""

    def __init__(self, config: dict):
        """Initialize SQLite database."""
        super().__init__(config)
        self._engine = None

    @property
    def engine(self) -> Engine:
        """Get the SQLite engine, creating it if necessary."""
        if self._engine is None:
            self._engine = self.create_engine()
        return self._engine

    def create_engine(self) -> Engine:
        """Create and configure the SQLite engine."""
        connection_string = self.get_connection_string()
        
        # SQLite-specific connection args for thread safety
        connect_args = {"check_same_thread": False}
        
        engine = create_engine(connection_string, connect_args=connect_args)
        logging.info(f"Created SQLite engine with connection: {connection_string}")
        return engine

    def get_connection_string(self) -> str:
        """Get the SQLite connection string."""
        # Use URL override if provided
        if self.config.get("url"):
            return self.config["url"]
        
        # Use default SQLite path
        return "sqlite:///./intentverse.db"

    def validate_config(self) -> bool:
        """Validate SQLite configuration."""
        # SQLite is very forgiving, just check if URL is valid format if provided
        url = self.config.get("url")
        if url and not url.startswith("sqlite://"):
            raise ValueError(f"Invalid SQLite URL format: {url}")
        return True

    def create_db_and_tables(self) -> None:
        """
        Creates the database file and all tables using the migration system.
        """
        logging.info("Initializing SQLite database...")

        # Import all models to ensure they're registered with SQLModel
        from ..models import (
            User, UserGroup, UserGroupLink, AuditLog, ModuleConfiguration, 
            ContentPackVariable, Role, Permission, UserRoleLink, GroupRoleLink,
            RolePermissionLink, RefreshToken, MCPServerInfo, MCPToolInfo,
            ModuleCategory
        )

        # Check if this is an in-memory database (used for testing)
        is_memory_db = str(self.engine.url).startswith("sqlite:///:memory:")
        
        if is_memory_db:
            # For in-memory databases (testing), create all tables directly
            from sqlmodel import SQLModel
            SQLModel.metadata.create_all(self.engine)
            logging.info("Created in-memory SQLite database for testing")
            return

        # For file-based databases, use migration system
        try:
            # Run migrations to ensure database is up to date
            success = self.run_migrations()
            if not success:
                logging.error("Database migrations failed")
                raise RuntimeError("Database migrations failed")
            
            logging.info("SQLite database initialized with migrations")
            
        except Exception as e:
            logging.error(f"Migration system failed, falling back to direct table creation: {e}")
            
            # Fallback: create tables directly (for backward compatibility)
            from sqlmodel import SQLModel
            SQLModel.metadata.create_all(self.engine)
            logging.warning("Used fallback table creation method")

    def get_session(self) -> Generator[Session, None, None]:
        """
        Dependency function that provides a database session to the API endpoints.
        """
        with Session(self.engine) as session:
            yield session