"""
PostgreSQL database implementation.
Provides PostgreSQL support with connection pooling, SSL, and cloud compatibility.
"""

import logging
import os
from typing import Generator, Optional
from urllib.parse import urlparse, parse_qs
from sqlmodel import create_engine, SQLModel, Session, select
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from .base import DatabaseInterface


class PostgreSQLDatabase(DatabaseInterface):
    """PostgreSQL database implementation with full feature support."""

    def __init__(self, config: dict):
        """Initialize PostgreSQL database."""
        super().__init__(config)
        self._engine = None

    @property
    def engine(self) -> Engine:
        """Get the PostgreSQL engine, creating it if necessary."""
        if self._engine is None:
            self._engine = self.create_engine()
        return self._engine

    def create_engine(self) -> Engine:
        """Create and configure the PostgreSQL engine with connection pooling."""
        connection_string = self.get_connection_string()
        
        # PostgreSQL-specific engine configuration
        engine_kwargs = {
            "poolclass": QueuePool,
            "pool_size": self.config.get("pool_size", 10),
            "max_overflow": self.config.get("max_overflow", 20),
            "pool_pre_ping": True,  # Validate connections before use
            "pool_recycle": self.config.get("pool_recycle", 3600),  # Recycle connections every hour
        }
        
        # Add SSL and connection-specific arguments
        connect_args = self._get_connect_args()
        if connect_args:
            engine_kwargs["connect_args"] = connect_args
        
        engine = create_engine(connection_string, **engine_kwargs)
        logging.info(f"Created PostgreSQL engine with connection pooling (pool_size={engine_kwargs['pool_size']})")
        return engine

    def _get_connect_args(self) -> dict:
        """Get PostgreSQL-specific connection arguments."""
        connect_args = {}
        
        # SSL configuration
        ssl_mode = self.config.get("ssl_mode", "prefer")
        if ssl_mode and ssl_mode != "disable":
            connect_args["sslmode"] = ssl_mode
            
            # SSL certificate files (for client certificate authentication)
            if self.config.get("ssl_cert"):
                connect_args["sslcert"] = self.config["ssl_cert"]
            if self.config.get("ssl_key"):
                connect_args["sslkey"] = self.config["ssl_key"]
            if self.config.get("ssl_ca"):
                connect_args["sslrootcert"] = self.config["ssl_ca"]
        
        # Connection timeout
        if self.config.get("connect_timeout"):
            connect_args["connect_timeout"] = self.config["connect_timeout"]
        
        # Application name for connection tracking
        connect_args["application_name"] = self.config.get("application_name", "IntentVerse")
        
        return connect_args

    def get_connection_string(self) -> str:
        """Get the PostgreSQL connection string."""
        # Use URL override if provided
        if self.config.get("url"):
            return self._validate_and_enhance_url(self.config["url"])
        
        # Build connection string from individual components
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 5432)
        database = self.config.get("database") or self.config.get("name", "intentverse")
        user = self.config.get("user") or self.config.get("username")
        password = self.config.get("password")
        
        if not user:
            raise ValueError("PostgreSQL user/username is required")
        
        # Build the connection string
        if password:
            connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        else:
            connection_string = f"postgresql://{user}@{host}:{port}/{database}"
        
        return self._validate_and_enhance_url(connection_string)

    def _validate_and_enhance_url(self, url: str) -> str:
        """Validate and enhance the PostgreSQL URL with additional parameters."""
        if not url.startswith(("postgresql://", "postgres://")):
            raise ValueError(f"Invalid PostgreSQL URL format: {url}")
        
        # Parse the URL to add additional parameters if needed
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Add SSL mode if not specified and we have SSL config
        if "sslmode" not in query_params and self.config.get("ssl_mode"):
            if "?" in url:
                url += f"&sslmode={self.config['ssl_mode']}"
            else:
                url += f"?sslmode={self.config['ssl_mode']}"
        
        return url

    def validate_config(self) -> bool:
        """Validate PostgreSQL configuration."""
        # Check for required psycopg2 dependency
        try:
            import psycopg2
        except ImportError:
            raise ImportError(
                "PostgreSQL support requires psycopg2. Install with: pip install psycopg2-binary"
            )
        
        # Validate connection string format
        try:
            connection_string = self.get_connection_string()
            parsed = urlparse(connection_string)
            
            if not parsed.hostname:
                raise ValueError("PostgreSQL host is required")
            
            if not parsed.username:
                raise ValueError("PostgreSQL user is required")
            
            # Validate SSL mode if specified
            ssl_mode = self.config.get("ssl_mode")
            if ssl_mode and ssl_mode not in ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]:
                raise ValueError(f"Invalid SSL mode: {ssl_mode}")
            
        except Exception as e:
            raise ValueError(f"PostgreSQL configuration validation failed: {e}")
        
        return True

    def create_db_and_tables(self) -> None:
        """
        Create the database and all tables using the migration system.
        For PostgreSQL, we assume the database already exists.
        """
        logging.info("Initializing PostgreSQL database...")

        # Import all models to ensure they're registered with SQLModel
        from ..models import (
            User, UserGroup, UserGroupLink, AuditLog, ModuleConfiguration, 
            ContentPackVariable, Role, Permission, UserRoleLink, GroupRoleLink,
            RolePermissionLink, RefreshToken, MCPServerInfo, MCPToolInfo
        )

        # Test database connectivity
        try:
            with Session(self.engine) as session:
                # Simple connectivity test
                session.exec(select(1)).first()
            logging.info("PostgreSQL database connectivity verified")
        except Exception as e:
            logging.error(f"Failed to connect to PostgreSQL database: {e}")
            raise

        try:
            # Run migrations to ensure database is up to date
            success = self.run_migrations()
            if not success:
                logging.error("Database migrations failed")
                raise RuntimeError("Database migrations failed")
            
            logging.info("PostgreSQL database initialized with migrations")
            
        except Exception as e:
            logging.error(f"Migration system failed, falling back to direct table creation: {e}")
            
            # Fallback: create tables directly (for backward compatibility)
            try:
                SQLModel.metadata.create_all(self.engine)
                logging.warning("Used fallback table creation method for PostgreSQL")
            except Exception as fallback_error:
                logging.error(f"Failed to create PostgreSQL tables: {fallback_error}")
                raise

    def _check_schema_migration_needed(self, engine: Engine) -> bool:
        """Check if schema migration is needed."""
        try:
            with Session(engine) as session:
                # Try to query key tables to see if they exist and have expected columns
                test_query = select(User.id, User.email).limit(1)
                session.exec(test_query).first()
                
                # Try to query the audit log table
                test_audit_query = select(AuditLog.id).limit(1)
                session.exec(test_audit_query).first()
                
                # Try to query content pack variables table
                test_cpv_query = select(ContentPackVariable.id).limit(1)
                session.exec(test_cpv_query).first()
                
                return False  # All tables exist with expected schema
        except Exception as e:
            logging.info(f"Schema migration needed: {e}")
            return True

    def _run_schema_migration(self, engine: Engine) -> None:
        """Run schema migration for PostgreSQL."""
        # For now, we'll use the simple approach of creating all tables
        # In a production system, this would use a proper migration framework
        try:
            SQLModel.metadata.create_all(engine)
            logging.info("PostgreSQL schema migration completed successfully")
        except Exception as e:
            logging.error(f"PostgreSQL schema migration failed: {e}")
            raise

    def get_session(self) -> Generator[Session, None, None]:
        """
        Dependency function that provides a database session to the API endpoints.
        Uses connection pooling for efficient resource management.
        """
        with Session(self.engine) as session:
            try:
                yield session
            except Exception as e:
                session.rollback()
                logging.error(f"Database session error: {e}")
                raise
            finally:
                session.close()

    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            with Session(self.engine) as session:
                session.exec(select(1)).first()
            return True
        except Exception as e:
            logging.error(f"PostgreSQL connection test failed: {e}")
            return False

    def get_database_info(self) -> dict:
        """Get PostgreSQL database information."""
        try:
            with Session(self.engine) as session:
                # Get PostgreSQL version
                from sqlalchemy import text
                version_result = session.exec(text("SELECT version()")).first()
                
                # Get current database name
                db_result = session.exec(text("SELECT current_database()")).first()
                
                return {
                    "type": "postgresql",
                    "version": version_result[0] if version_result else "unknown",
                    "database": db_result[0] if db_result else "unknown",
                    "connection_pool_size": self.config.get("pool_size", 10),
                    "ssl_mode": self.config.get("ssl_mode", "prefer")
                }
        except Exception as e:
            logging.error(f"Failed to get PostgreSQL database info: {e}")
            return {
                "type": "postgresql",
                "version": "unknown",
                "database": "unknown",
                "error": str(e)
            }