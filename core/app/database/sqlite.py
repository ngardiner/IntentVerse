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
        Creates the database file and all tables defined by our SQLModel classes.
        For development, we'll recreate the database if schema changes are detected.
        """
        current_engine = self.engine

        logging.info("Initializing SQLite database and creating tables...")

        # Import all models to ensure they're registered with SQLModel
        from ..models import User, UserGroup, UserGroupLink, AuditLog, ModuleConfiguration, ContentPackVariable

        # Import RBAC models to ensure they're registered
        from ..models import (
            Role,
            Permission,
            UserRoleLink,
            GroupRoleLink,
            RolePermissionLink,
        )

        # Check if this is an in-memory database (used for testing)
        is_memory_db = str(current_engine.url).startswith("sqlite:///:memory:")

        if not is_memory_db:
            # Only check for file recreation if using a file-based database
            db_file = "./intentverse.db"
            needs_recreation = False

            if os.path.exists(db_file):
                # Check if we need to recreate due to schema changes
                try:
                    # Test if the current schema matches by trying to access new columns
                    with Session(current_engine) as session:
                        # Try to query a user with the new email field
                        test_query = select(User.id, User.email).limit(1)
                        session.exec(test_query).first()

                        # Try to query the audit log table
                        test_audit_query = select(AuditLog.id).limit(1)
                        session.exec(test_audit_query).first()

                except Exception as e:
                    logging.warning(f"Database schema appears outdated: {e}")
                    logging.info("Recreating database...")
                    needs_recreation = True

            if needs_recreation:
                # Remove the old database file
                if os.path.exists(db_file):
                    os.remove(db_file)
                    logging.info("Removed old database file")

        # Create all tables
        SQLModel.metadata.create_all(current_engine)
        logging.info("SQLite database and tables initialized.")

    def get_session(self) -> Generator[Session, None, None]:
        """
        Dependency function that provides a database session to the API endpoints.
        """
        with Session(self.engine) as session:
            yield session