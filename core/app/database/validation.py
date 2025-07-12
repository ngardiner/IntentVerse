"""
Database configuration validation and connection management.

This module provides enhanced validation, retry logic, and health checking
for database connections across all supported database engines.
"""

import logging
import time
import re
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse
from sqlmodel import Session, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DisconnectionError
from sqlalchemy.engine import Engine

from .base import DatabaseInterface


class DatabaseConfigValidator:
    """
    Validates database configuration and provides helpful error messages.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_type = config.get("type", "sqlite").lower()
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate the database configuration.
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors.clear()
        self.warnings.clear()
        
        # Validate database type
        self._validate_database_type()
        
        # Validate connection parameters
        if self.db_type == "sqlite":
            self._validate_sqlite_config()
        elif self.db_type == "postgresql":
            self._validate_postgresql_config()
        elif self.db_type in ["mysql", "mariadb"]:
            self._validate_mysql_config()
        
        # Validate connection string format if provided
        if self.config.get("url"):
            self._validate_connection_string()
        
        # Validate SSL configuration
        self._validate_ssl_config()
        
        # Validate pool configuration
        self._validate_pool_config()
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_database_type(self):
        """Validate the database type."""
        supported_types = ["sqlite", "postgresql", "mysql", "mariadb"]
        
        if self.db_type not in supported_types:
            self.errors.append(
                f"Unsupported database type: {self.db_type}. "
                f"Supported types: {', '.join(supported_types)}"
            )
    
    def _validate_sqlite_config(self):
        """Validate SQLite-specific configuration."""
        url = self.config.get("url")
        
        if url:
            if not url.startswith("sqlite://"):
                self.errors.append("SQLite URL must start with 'sqlite://'")
            elif url == "sqlite:///:memory:":
                self.warnings.append("Using in-memory SQLite database - data will not persist")
        
        # Check for unnecessary parameters
        unnecessary_params = ["host", "port", "user", "password", "ssl_mode"]
        for param in unnecessary_params:
            if self.config.get(param):
                self.warnings.append(f"Parameter '{param}' is not used with SQLite")
    
    def _validate_postgresql_config(self):
        """Validate PostgreSQL-specific configuration."""
        url = self.config.get("url")
        
        if url:
            if not url.startswith(("postgresql://", "postgres://")):
                self.errors.append("PostgreSQL URL must start with 'postgresql://' or 'postgres://'")
        else:
            # Validate individual parameters
            required_params = ["host", "name"]
            for param in required_params:
                if not self.config.get(param):
                    self.errors.append(f"PostgreSQL requires '{param}' parameter")
            
            # Validate port
            port = self.config.get("port")
            if port:
                try:
                    port_int = int(port)
                    if not (1 <= port_int <= 65535):
                        self.errors.append("PostgreSQL port must be between 1 and 65535")
                except ValueError:
                    self.errors.append("PostgreSQL port must be a valid integer")
        
        # Validate SSL mode
        ssl_mode = self.config.get("ssl_mode")
        if ssl_mode:
            valid_ssl_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
            if ssl_mode not in valid_ssl_modes:
                self.errors.append(
                    f"Invalid PostgreSQL SSL mode: {ssl_mode}. "
                    f"Valid modes: {', '.join(valid_ssl_modes)}"
                )
    
    def _validate_mysql_config(self):
        """Validate MySQL/MariaDB-specific configuration."""
        url = self.config.get("url")
        
        if url:
            if not url.startswith(("mysql://", "mysql+pymysql://", "mysql+mysqldb://", "mysql+mysqlconnector://")):
                self.errors.append(
                    "MySQL URL must start with 'mysql://', 'mysql+pymysql://', "
                    "'mysql+mysqldb://', or 'mysql+mysqlconnector://'"
                )
        else:
            # Validate individual parameters
            required_params = ["host", "name"]
            for param in required_params:
                if not self.config.get(param):
                    self.errors.append(f"MySQL requires '{param}' parameter")
            
            # Validate port
            port = self.config.get("port")
            if port:
                try:
                    port_int = int(port)
                    if not (1 <= port_int <= 65535):
                        self.errors.append("MySQL port must be between 1 and 65535")
                except ValueError:
                    self.errors.append("MySQL port must be a valid integer")
        
        # Validate charset
        charset = self.config.get("charset")
        if charset:
            valid_charsets = ["utf8", "utf8mb4", "latin1", "ascii"]
            if charset not in valid_charsets:
                self.warnings.append(
                    f"Unusual MySQL charset: {charset}. "
                    f"Common charsets: {', '.join(valid_charsets)}"
                )
    
    def _validate_connection_string(self):
        """Validate connection string format."""
        url = self.config.get("url")
        if not url:
            return
        
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if not parsed.scheme:
                self.errors.append("Connection string missing scheme (e.g., 'postgresql://')")
            
            # Check hostname for non-SQLite databases
            if self.db_type != "sqlite" and not parsed.hostname:
                self.errors.append("Connection string missing hostname")
            
            # Check database name for non-SQLite databases
            if self.db_type != "sqlite" and not parsed.path.strip("/"):
                self.errors.append("Connection string missing database name")
                
        except Exception as e:
            self.errors.append(f"Invalid connection string format: {e}")
    
    def _validate_ssl_config(self):
        """Validate SSL configuration."""
        ssl_mode = self.config.get("ssl_mode")
        
        if ssl_mode and self.db_type == "sqlite":
            self.warnings.append("SSL mode is not applicable for SQLite")
    
    def _validate_pool_config(self):
        """Validate connection pool configuration."""
        if self.db_type == "sqlite":
            pool_params = ["pool_size", "max_overflow", "pool_recycle"]
            for param in pool_params:
                if self.config.get(param):
                    self.warnings.append(f"Connection pool parameter '{param}' is not used with SQLite")
            return
        
        # Validate pool size
        pool_size = self.config.get("pool_size")
        if pool_size is not None:
            try:
                pool_size_int = int(pool_size)
                if pool_size_int < 1:
                    self.errors.append("Pool size must be at least 1")
                elif pool_size_int > 100:
                    self.warnings.append("Pool size > 100 may cause resource issues")
            except ValueError:
                self.errors.append("Pool size must be a valid integer")
        
        # Validate max overflow
        max_overflow = self.config.get("max_overflow")
        if max_overflow is not None:
            try:
                max_overflow_int = int(max_overflow)
                if max_overflow_int < 0:
                    self.errors.append("Max overflow must be non-negative")
                elif max_overflow_int > 200:
                    self.warnings.append("Max overflow > 200 may cause resource issues")
            except ValueError:
                self.errors.append("Max overflow must be a valid integer")
        
        # Validate pool recycle
        pool_recycle = self.config.get("pool_recycle")
        if pool_recycle is not None:
            try:
                pool_recycle_int = int(pool_recycle)
                if pool_recycle_int < 0:
                    self.errors.append("Pool recycle must be non-negative")
                elif pool_recycle_int < 300:
                    self.warnings.append("Pool recycle < 300 seconds may cause frequent reconnections")
            except ValueError:
                self.errors.append("Pool recycle must be a valid integer")


class DatabaseConnectionManager:
    """
    Manages database connections with retry logic and health checking.
    """
    
    def __init__(self, database: DatabaseInterface):
        self.database = database
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay in seconds
        self.max_delay = 30.0  # Maximum delay in seconds
        self.backoff_factor = 2.0  # Exponential backoff factor
    
    def test_connection(self, timeout: Optional[float] = None) -> Tuple[bool, Optional[str]]:
        """
        Test database connection with retry logic.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            Tuple of (success, error_message)
        """
        for attempt in range(self.max_retries + 1):
            try:
                with Session(self.database.engine) as session:
                    # Simple connectivity test
                    if self.database.config.get("type") == "sqlite":
                        session.exec(text("SELECT 1"))
                    elif self.database.config.get("type") == "postgresql":
                        session.exec(text("SELECT 1"))
                    elif self.database.config.get("type") in ["mysql", "mariadb"]:
                        session.exec(text("SELECT 1"))
                    
                    session.commit()
                
                if attempt > 0:
                    logging.info(f"Database connection successful after {attempt} retries")
                
                return True, None
                
            except (OperationalError, DisconnectionError, SQLAlchemyError) as e:
                error_msg = str(e)
                
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
                    logging.warning(
                        f"Database connection attempt {attempt + 1} failed: {error_msg}. "
                        f"Retrying in {delay:.1f} seconds..."
                    )
                    time.sleep(delay)
                else:
                    logging.error(f"Database connection failed after {self.max_retries + 1} attempts: {error_msg}")
                    return False, error_msg
            
            except Exception as e:
                # Non-retryable error
                error_msg = f"Database connection failed with non-retryable error: {e}"
                logging.error(error_msg)
                return False, error_msg
        
        return False, "Maximum retry attempts exceeded"
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive database health status.
        
        Returns:
            Dictionary with health status information
        """
        start_time = time.time()
        
        # Test basic connectivity
        connection_success, connection_error = self.test_connection()
        connection_time = time.time() - start_time
        
        health_status = {
            "status": "healthy" if connection_success else "unhealthy",
            "connection_time_ms": round(connection_time * 1000, 2),
            "database_type": self.database.config.get("type"),
            "connection_error": connection_error,
            "timestamp": time.time()
        }
        
        if connection_success:
            # Get additional database-specific information
            try:
                health_status.update(self._get_database_info())
            except Exception as e:
                logging.warning(f"Failed to get database info: {e}")
                health_status["info_error"] = str(e)
        
        return health_status
    
    def _get_database_info(self) -> Dict[str, Any]:
        """Get database-specific information."""
        info = {}
        
        try:
            with Session(self.database.engine) as session:
                db_type = self.database.config.get("type")
                
                if db_type == "postgresql":
                    # PostgreSQL version and settings
                    result = session.exec(text("SELECT version()")).first()
                    if result:
                        info["version"] = result[0]
                    
                    # Connection count
                    result = session.exec(text(
                        "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                    )).first()
                    if result:
                        info["active_connections"] = result[0]
                
                elif db_type in ["mysql", "mariadb"]:
                    # MySQL/MariaDB version
                    result = session.exec(text("SELECT VERSION()")).first()
                    if result:
                        info["version"] = result[0]
                    
                    # Connection count
                    result = session.exec(text("SHOW STATUS LIKE 'Threads_connected'")).first()
                    if result:
                        info["active_connections"] = int(result[1])
                
                elif db_type == "sqlite":
                    # SQLite version
                    result = session.exec(text("SELECT sqlite_version()")).first()
                    if result:
                        info["version"] = result[0]
                    
                    # Database file size (if file-based)
                    url = self.database.config.get("url", "")
                    if not url.endswith(":memory:"):
                        try:
                            import os
                            db_path = url.replace("sqlite:///", "").replace("sqlite://", "")
                            if os.path.exists(db_path):
                                info["file_size_bytes"] = os.path.getsize(db_path)
                        except Exception:
                            pass
        
        except Exception as e:
            logging.warning(f"Failed to get database-specific info: {e}")
        
        return info
    
    def validate_startup_connection(self) -> bool:
        """
        Validate database connection on startup with fail-fast behavior.
        
        Returns:
            True if connection is valid, False otherwise
        """
        logging.info("Validating database connection on startup...")
        
        # First validate configuration
        validator = DatabaseConfigValidator(self.database.config)
        is_valid, errors, warnings = validator.validate()
        
        if not is_valid:
            logging.error("Database configuration validation failed:")
            for error in errors:
                logging.error(f"  - {error}")
            return False
        
        if warnings:
            logging.warning("Database configuration warnings:")
            for warning in warnings:
                logging.warning(f"  - {warning}")
        
        # Test connection
        success, error = self.test_connection()
        
        if not success:
            logging.error(f"Database connection validation failed: {error}")
            return False
        
        logging.info("Database connection validation successful")
        return True


def validate_database_config(config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    Validate database configuration.
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = DatabaseConfigValidator(config)
    return validator.validate()


def test_database_connection(database: DatabaseInterface, timeout: Optional[float] = None) -> Tuple[bool, Optional[str]]:
    """
    Test database connection with retry logic.
    
    Args:
        database: Database interface instance
        timeout: Connection timeout in seconds
        
    Returns:
        Tuple of (success, error_message)
    """
    manager = DatabaseConnectionManager(database)
    return manager.test_connection(timeout)


def get_database_health(database: DatabaseInterface) -> Dict[str, Any]:
    """
    Get database health status.
    
    Args:
        database: Database interface instance
        
    Returns:
        Dictionary with health status information
    """
    manager = DatabaseConnectionManager(database)
    return manager.get_health_status()