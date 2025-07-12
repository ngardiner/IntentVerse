"""
Comprehensive unit tests for the database abstraction layer.

This module provides CI-friendly tests that don't require external database instances.
Tests cover the factory pattern, configuration handling, and interface compliance.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import OperationalError

from app.database import DatabaseFactory, DatabaseInterface, initialize_database, get_database, reset_database
from app.database.base import DatabaseInterface
from app.database.sqlite import SQLiteDatabase
from app.database.postgresql import PostgreSQLDatabase
from app.database.mysql import MySQLDatabase
from app.config import Config


class TestDatabaseFactory:
    """Test the database factory pattern."""
    
    def test_create_sqlite_database(self):
        """Test creating SQLite database instance."""
        config = {
            "type": "sqlite",
            "url": "sqlite:///:memory:"
        }
        
        database = DatabaseFactory.create_database(config)
        
        assert isinstance(database, SQLiteDatabase)
        assert database.config == config
    
    def test_create_postgresql_database(self):
        """Test creating PostgreSQL database instance."""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": "5432",
            "name": "testdb",
            "user": "testuser",
            "password": "testpass"
        }
        
        database = DatabaseFactory.create_database(config)
        
        assert isinstance(database, PostgreSQLDatabase)
        assert database.config == config
    
    def test_create_mysql_database(self):
        """Test creating MySQL database instance."""
        config = {
            "type": "mysql",
            "host": "localhost",
            "port": "3306",
            "name": "testdb",
            "user": "testuser",
            "password": "testpass"
        }
        
        database = DatabaseFactory.create_database(config)
        
        assert isinstance(database, MySQLDatabase)
        assert database.config == config
    
    def test_create_mariadb_database(self):
        """Test creating MariaDB database instance (uses MySQL implementation)."""
        config = {
            "type": "mariadb",
            "host": "localhost",
            "port": "3306",
            "name": "testdb",
            "user": "testuser",
            "password": "testpass"
        }
        
        database = DatabaseFactory.create_database(config)
        
        assert isinstance(database, MySQLDatabase)
        assert database.config == config
    
    def test_unsupported_database_type(self):
        """Test error handling for unsupported database type."""
        config = {
            "type": "unsupported_db",
            "host": "localhost"
        }
        
        with pytest.raises(ValueError, match="Unsupported database type"):
            DatabaseFactory.create_database(config)
    
    def test_missing_database_type(self):
        """Test error handling for missing database type."""
        config = {
            "host": "localhost"
        }
        
        with pytest.raises(ValueError, match="Database type must be specified"):
            DatabaseFactory.create_database(config)


class TestDatabaseInterface:
    """Test the database interface compliance."""
    
    @pytest.fixture
    def sqlite_database(self):
        """Create a test SQLite database."""
        config = {
            "type": "sqlite",
            "url": "sqlite:///:memory:"
        }
        return SQLiteDatabase(config)
    
    def test_interface_methods_exist(self, sqlite_database):
        """Test that all required interface methods exist."""
        interface_methods = [
            'engine', 'config', 'validate_config', 'create_db_and_tables',
            'run_migrations', 'get_migration_status', 'validate_startup_connection',
            'test_connection', 'get_health_status', 'close'
        ]
        
        for method in interface_methods:
            assert hasattr(sqlite_database, method), f"Missing method: {method}"
    
    def test_engine_property(self, sqlite_database):
        """Test engine property returns SQLAlchemy engine."""
        engine = sqlite_database.engine
        
        assert engine is not None
        assert hasattr(engine, 'execute')  # Basic SQLAlchemy engine check
    
    def test_config_property(self, sqlite_database):
        """Test config property returns configuration."""
        config = sqlite_database.config
        
        assert isinstance(config, dict)
        assert config["type"] == "sqlite"
    
    def test_validate_config(self, sqlite_database):
        """Test configuration validation."""
        # Should not raise exception for valid config
        result = sqlite_database.validate_config()
        assert result is True
    
    def test_create_db_and_tables(self, sqlite_database):
        """Test database and table creation."""
        # Should not raise exception
        sqlite_database.create_db_and_tables()
        
        # Verify engine is accessible
        assert sqlite_database.engine is not None
    
    def test_migration_methods(self, sqlite_database):
        """Test migration-related methods."""
        # Test migration status
        status = sqlite_database.get_migration_status()
        assert isinstance(status, dict)
        assert "current_version" in status
        assert "pending_migrations" in status
        
        # Test run migrations
        result = sqlite_database.run_migrations()
        assert isinstance(result, bool)
    
    def test_health_and_connection_methods(self, sqlite_database):
        """Test health check and connection methods."""
        # Test connection
        success, error = sqlite_database.test_connection()
        assert isinstance(success, bool)
        
        # Test health status
        health = sqlite_database.get_health_status()
        assert isinstance(health, dict)
        assert "status" in health
        assert "timestamp" in health
    
    def test_close_method(self, sqlite_database):
        """Test database connection closing."""
        # Should not raise exception
        sqlite_database.close()


class TestDatabaseInitialization:
    """Test database initialization and global state management."""
    
    def teardown_method(self):
        """Clean up after each test."""
        reset_database()
    
    def test_initialize_database(self):
        """Test database initialization."""
        config = {
            "type": "sqlite",
            "url": "sqlite:///:memory:"
        }
        
        database = initialize_database(config, validate_connection=False)
        
        assert isinstance(database, SQLiteDatabase)
        assert get_database() is database
    
    def test_initialize_database_with_validation(self):
        """Test database initialization with connection validation."""
        config = {
            "type": "sqlite",
            "url": "sqlite:///:memory:"
        }
        
        database = initialize_database(config, validate_connection=True)
        
        assert isinstance(database, SQLiteDatabase)
        assert get_database() is database
    
    @pytest.mark.database_integration
    def test_initialize_database_validation_failure(self):
        """Test database initialization with validation failure."""
        config = {
            "type": "postgresql",
            "host": "nonexistent-host",
            "name": "testdb",
            "user": "testuser"
        }
        
        with pytest.raises(RuntimeError, match="Database initialization failed"):
            initialize_database(config, validate_connection=True)
    
    def test_get_database_before_initialization(self):
        """Test getting database before initialization."""
        with pytest.raises(RuntimeError, match="Database not initialized"):
            get_database()
    
    def test_reset_database(self):
        """Test database reset functionality."""
        config = {
            "type": "sqlite",
            "url": "sqlite:///:memory:"
        }
        
        # Initialize database
        initialize_database(config, validate_connection=False)
        assert get_database() is not None
        
        # Reset database
        reset_database()
        
        # Should raise error after reset
        with pytest.raises(RuntimeError, match="Database not initialized"):
            get_database()


class TestConfigurationIntegration:
    """Test integration with configuration system."""
    
    def test_config_get_database_config(self):
        """Test getting database configuration from Config class."""
        config = Config.get_database_config()
        
        assert isinstance(config, dict)
        assert "type" in config
        assert config["type"] in ["sqlite", "postgresql", "mysql", "mariadb"]
    
    def test_config_validate_database_config(self):
        """Test configuration validation through Config class."""
        is_valid, errors, warnings = Config.validate_database_config()
        
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
        assert isinstance(warnings, list)
    
    @patch.dict(os.environ, {
        "INTENTVERSE_DB_TYPE": "postgresql",
        "INTENTVERSE_DB_HOST": "localhost",
        "INTENTVERSE_DB_NAME": "testdb"
    })
    def test_config_environment_variables(self):
        """Test configuration from environment variables."""
        config = Config.get_database_config()
        
        assert config["type"] == "postgresql"
        assert config["host"] == "localhost"
        assert config["name"] == "testdb"
    
    @patch.dict(os.environ, {
        "INTENTVERSE_DB_URL": "postgresql://user:pass@localhost:5432/testdb"
    })
    def test_config_connection_string(self):
        """Test configuration from connection string."""
        config = Config.get_database_config()
        
        assert "postgresql://" in config["url"]


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_configuration_validation(self):
        """Test handling of invalid configuration during validation."""
        config = {
            "type": "postgresql",
            # Missing required fields
        }
        
        with pytest.raises(ValueError, match="Database configuration validation failed"):
            DatabaseFactory.create_database(config)
    
    def test_database_interface_validation_failure(self):
        """Test handling of database interface validation failure."""
        config = {
            "type": "sqlite",
            "url": "sqlite:///invalid/path/that/does/not/exist.db"
        }
        
        # Mock the validate_config method to fail
        with patch.object(SQLiteDatabase, 'validate_config', side_effect=Exception("Validation failed")):
            with pytest.raises(Exception, match="Database interface validation failed"):
                DatabaseFactory.create_database(config)
    
    @pytest.mark.database_integration
    def test_initialization_cleanup_on_failure(self):
        """Test that initialization cleans up on failure."""
        config = {
            "type": "sqlite",
            "url": "sqlite:///:memory:"
        }
        
        # Mock validation to fail
        with patch.object(SQLiteDatabase, 'validate_startup_connection', return_value=False):
            with pytest.raises(RuntimeError, match="Database initialization failed"):
                initialize_database(config, validate_connection=True)
            
            # Verify cleanup - should not have a database instance
            with pytest.raises(RuntimeError, match="Database not initialized"):
                get_database()


class TestCrossDatabase:
    """Test cross-database compatibility."""
    
    def test_all_database_types_implement_interface(self):
        """Test that all database implementations follow the interface."""
        database_configs = [
            {"type": "sqlite", "url": "sqlite:///:memory:"},
            {"type": "postgresql", "host": "localhost", "name": "test", "user": "test"},
            {"type": "mysql", "host": "localhost", "name": "test", "user": "test"},
            {"type": "mariadb", "host": "localhost", "name": "test", "user": "test"},
        ]
        
        for config in database_configs:
            database = DatabaseFactory.create_database(config)
            
            # Check that all required methods exist
            assert hasattr(database, 'engine')
            assert hasattr(database, 'config')
            assert hasattr(database, 'validate_config')
            assert hasattr(database, 'create_db_and_tables')
            assert hasattr(database, 'run_migrations')
            assert hasattr(database, 'get_migration_status')
            assert hasattr(database, 'test_connection')
            assert hasattr(database, 'get_health_status')
            assert hasattr(database, 'close')
    
    def test_config_normalization_consistency(self):
        """Test that configuration normalization works consistently."""
        from app.config_parser import parse_database_config
        
        configs = [
            {"type": "sqlite", "name": "./test.db"},
            {"type": "postgresql", "host": "localhost", "name": "test"},
            {"type": "mysql", "host": "localhost", "name": "test"},
        ]
        
        for config in configs:
            normalized = parse_database_config(config)
            assert isinstance(normalized, dict)
            assert "type" in normalized
            assert normalized["type"] == config["type"]


class TestPerformanceAndScaling:
    """Test performance-related aspects."""
    
    def test_multiple_database_instances(self):
        """Test creating multiple database instances."""
        configs = [
            {"type": "sqlite", "url": "sqlite:///:memory:"},
            {"type": "sqlite", "url": "sqlite:///:memory:"},
            {"type": "sqlite", "url": "sqlite:///:memory:"},
        ]
        
        databases = []
        for config in configs:
            db = DatabaseFactory.create_database(config)
            databases.append(db)
        
        # All should be separate instances
        assert len(set(id(db) for db in databases)) == len(databases)
        
        # Clean up
        for db in databases:
            db.close()
    
    def test_database_connection_pooling_config(self):
        """Test that connection pooling configuration is handled."""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "name": "test",
            "user": "test",
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 3600
        }
        
        database = DatabaseFactory.create_database(config)
        
        # Should not raise exception and should store config
        assert database.config["pool_size"] == 10
        assert database.config["max_overflow"] == 20
        assert database.config["pool_recycle"] == 3600


if __name__ == "__main__":
    pytest.main([__file__])