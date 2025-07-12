"""
MySQL/MariaDB database implementation.
Provides MySQL and MariaDB support with connection pooling, SSL, and cloud compatibility.
"""

import logging
import os
from typing import Generator, Optional
from urllib.parse import urlparse, parse_qs
from sqlmodel import create_engine, SQLModel, Session, select
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from .base import DatabaseInterface


class MySQLDatabase(DatabaseInterface):
    """MySQL/MariaDB database implementation with full feature support."""

    def __init__(self, config: dict):
        """Initialize MySQL database."""
        super().__init__(config)
        self._engine = None

    @property
    def engine(self) -> Engine:
        """Get the MySQL engine, creating it if necessary."""
        if self._engine is None:
            self._engine = self.create_engine()
        return self._engine

    def create_engine(self) -> Engine:
        """Create and configure the MySQL engine with connection pooling."""
        connection_string = self.get_connection_string()
        
        # MySQL-specific engine configuration
        engine_kwargs = {
            "poolclass": QueuePool,
            "pool_size": self.config.get("pool_size", 10),
            "max_overflow": self.config.get("max_overflow", 20),
            "pool_pre_ping": True,  # Validate connections before use
            "pool_recycle": self.config.get("pool_recycle", 3600),  # Recycle connections every hour
        }
        
        # Add MySQL-specific connection arguments
        connect_args = self._get_connect_args()
        if connect_args:
            engine_kwargs["connect_args"] = connect_args
        
        engine = create_engine(connection_string, **engine_kwargs)
        logging.info(f"Created MySQL engine with connection pooling (pool_size={engine_kwargs['pool_size']})")
        return engine

    def _get_connect_args(self) -> dict:
        """Get MySQL-specific connection arguments."""
        connect_args = {}
        
        # SSL configuration
        ssl_mode = self.config.get("ssl_mode")
        if ssl_mode and ssl_mode != "DISABLED":
            # MySQL SSL modes: DISABLED, PREFERRED, REQUIRED, VERIFY_CA, VERIFY_IDENTITY
            connect_args["ssl_disabled"] = False
            
            if ssl_mode in ["REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"]:
                connect_args["ssl_check_hostname"] = ssl_mode == "VERIFY_IDENTITY"
                
            # SSL certificate files
            if self.config.get("ssl_cert"):
                connect_args["ssl_cert"] = self.config["ssl_cert"]
            if self.config.get("ssl_key"):
                connect_args["ssl_key"] = self.config["ssl_key"]
            if self.config.get("ssl_ca"):
                connect_args["ssl_ca"] = self.config["ssl_ca"]
        else:
            connect_args["ssl_disabled"] = True
        
        # Connection timeout
        if self.config.get("connect_timeout"):
            connect_args["connect_timeout"] = self.config["connect_timeout"]
        
        # Character set (important for proper UTF-8 support)
        connect_args["charset"] = self.config.get("charset", "utf8mb4")
        
        # SQL mode for strict data validation
        sql_mode = self.config.get("sql_mode", "STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO")
        if sql_mode:
            connect_args["sql_mode"] = sql_mode
        
        # Autocommit mode
        connect_args["autocommit"] = self.config.get("autocommit", False)
        
        return connect_args

    def get_connection_string(self) -> str:
        """Get the MySQL connection string."""
        # Use URL override if provided
        if self.config.get("url"):
            return self._validate_and_enhance_url(self.config["url"])
        
        # Build connection string from individual components
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 3306)
        database = self.config.get("database") or self.config.get("name", "intentverse")
        user = self.config.get("user") or self.config.get("username")
        password = self.config.get("password")
        
        if not user:
            raise ValueError("MySQL user/username is required")
        
        # Determine the driver to use
        driver = self._get_mysql_driver()
        
        # Build the connection string
        if password:
            connection_string = f"mysql+{driver}://{user}:{password}@{host}:{port}/{database}"
        else:
            connection_string = f"mysql+{driver}://{user}@{host}:{port}/{database}"
        
        return self._validate_and_enhance_url(connection_string)

    def _get_mysql_driver(self) -> str:
        """Determine which MySQL driver to use based on availability."""
        # Try drivers in order of preference
        drivers = [
            ("pymysql", "pymysql"),
            ("mysqlclient", "mysqldb"),
            ("mysql-connector-python", "mysqlconnector")
        ]
        
        for package_name, driver_name in drivers:
            try:
                __import__(package_name)
                logging.info(f"Using MySQL driver: {driver_name}")
                return driver_name
            except ImportError:
                continue
        
        raise ImportError(
            "No MySQL driver found. Install one of: pymysql, mysqlclient, or mysql-connector-python"
        )

    def _validate_and_enhance_url(self, url: str) -> str:
        """Validate and enhance the MySQL URL with additional parameters."""
        if not url.startswith("mysql+"):
            # If no driver specified, add the default driver
            if url.startswith("mysql://"):
                driver = self._get_mysql_driver()
                url = url.replace("mysql://", f"mysql+{driver}://")
            else:
                raise ValueError(f"Invalid MySQL URL format: {url}")
        
        # Parse the URL to add additional parameters if needed
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Add charset if not specified
        if "charset" not in query_params:
            charset = self.config.get("charset", "utf8mb4")
            if "?" in url:
                url += f"&charset={charset}"
            else:
                url += f"?charset={charset}"
        
        return url

    def validate_config(self) -> bool:
        """Validate MySQL configuration."""
        # Check for required MySQL driver
        try:
            self._get_mysql_driver()
        except ImportError as e:
            raise ImportError(str(e))
        
        # Validate connection string format
        try:
            connection_string = self.get_connection_string()
            parsed = urlparse(connection_string)
            
            if not parsed.hostname:
                raise ValueError("MySQL host is required")
            
            if not parsed.username:
                raise ValueError("MySQL user is required")
            
            # Validate SSL mode if specified
            ssl_mode = self.config.get("ssl_mode")
            if ssl_mode and ssl_mode not in ["DISABLED", "PREFERRED", "REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"]:
                raise ValueError(f"Invalid SSL mode: {ssl_mode}. Must be one of: DISABLED, PREFERRED, REQUIRED, VERIFY_CA, VERIFY_IDENTITY")
            
            # Validate charset
            charset = self.config.get("charset", "utf8mb4")
            if charset not in ["utf8", "utf8mb4", "latin1"]:
                logging.warning(f"Unusual charset specified: {charset}. Recommended: utf8mb4")
            
        except Exception as e:
            raise ValueError(f"MySQL configuration validation failed: {e}")
        
        return True

    def create_db_and_tables(self) -> None:
        """
        Create the database and all tables using the migration system.
        For MySQL, we assume the database already exists.
        """
        logging.info("Initializing MySQL/MariaDB database...")

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
            logging.info("MySQL/MariaDB database connectivity verified")
        except Exception as e:
            logging.error(f"Failed to connect to MySQL/MariaDB database: {e}")
            raise

        try:
            # Run migrations to ensure database is up to date
            success = self.run_migrations()
            if not success:
                logging.error("Database migrations failed")
                raise RuntimeError("Database migrations failed")
            
            logging.info("MySQL/MariaDB database initialized with migrations")
            
        except Exception as e:
            logging.error(f"Migration system failed, falling back to direct table creation: {e}")
            
            # Fallback: create tables directly (for backward compatibility)
            try:
                SQLModel.metadata.create_all(self.engine)
                logging.warning("Used fallback table creation method for MySQL/MariaDB")
            except Exception as fallback_error:
                logging.error(f"Failed to create MySQL/MariaDB tables: {fallback_error}")
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
        """Run schema migration for MySQL."""
        # For now, we'll use the simple approach of creating all tables
        # In a production system, this would use a proper migration framework
        try:
            SQLModel.metadata.create_all(engine)
            logging.info("MySQL schema migration completed successfully")
        except Exception as e:
            logging.error(f"MySQL schema migration failed: {e}")
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

    def test_connection(self, timeout: float = None) -> tuple[bool, str]:
        """Test the database connection."""
        try:
            with Session(self.engine) as session:
                session.exec(select(1)).first()
            return True, None
        except Exception as e:
            error_msg = f"MySQL connection test failed: {e}"
            logging.error(error_msg)
            return False, error_msg

    def get_database_info(self) -> dict:
        """Get MySQL database information."""
        try:
            with Session(self.engine) as session:
                from sqlalchemy import text
                
                # Get MySQL version
                version_result = session.exec(text("SELECT VERSION()")).first()
                
                # Get current database name
                db_result = session.exec(text("SELECT DATABASE()")).first()
                
                # Check if this is MariaDB
                is_mariadb = "MariaDB" in (version_result[0] if version_result else "")
                
                # Get additional MySQL/MariaDB info
                charset_result = session.exec(text("SELECT @@character_set_database")).first()
                collation_result = session.exec(text("SELECT @@collation_database")).first()
                
                return {
                    "type": "mariadb" if is_mariadb else "mysql",
                    "version": version_result[0] if version_result else "unknown",
                    "database": db_result[0] if db_result else "unknown",
                    "charset": charset_result[0] if charset_result else "unknown",
                    "collation": collation_result[0] if collation_result else "unknown",
                    "connection_pool_size": self.config.get("pool_size", 10),
                    "ssl_mode": self.config.get("ssl_mode", "PREFERRED")
                }
        except Exception as e:
            logging.error(f"Failed to get MySQL database info: {e}")
            return {
                "type": "mysql",
                "version": "unknown",
                "database": "unknown",
                "error": str(e)
            }