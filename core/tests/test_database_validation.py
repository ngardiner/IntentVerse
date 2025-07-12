"""
Tests for database configuration validation and connection management.

This module tests the enhanced validation, retry logic, and health checking features.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import OperationalError, DisconnectionError

# Mark all tests in this file as database integration tests
pytestmark = pytest.mark.database_integration

from app.database.validation import (
    DatabaseConfigValidator, DatabaseConnectionManager, 
    validate_database_config, test_database_connection, get_database_health
)
from app.config_parser import DatabaseConfigParser, parse_database_config
from app.database.sqlite import SQLiteDatabase


class TestDatabaseConfigValidator:
    """Test database configuration validation."""
    
    def test_valid_sqlite_config(self):
        """Test validation of valid SQLite configuration."""
        config = {
            "type": "sqlite",
            "url": "sqlite:///./test.db"
        }
        
        validator = DatabaseConfigValidator(config)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_valid_postgresql_config(self):
        """Test validation of valid PostgreSQL configuration."""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": "5432",
            "name": "testdb",
            "user": "testuser",
            "password": "testpass",
            "ssl_mode": "prefer"
        }
        
        validator = DatabaseConfigValidator(config)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_valid_mysql_config(self):
        """Test validation of valid MySQL configuration."""
        config = {
            "type": "mysql",
            "host": "localhost",
            "port": "3306",
            "name": "testdb",
            "user": "testuser",
            "password": "testpass",
            "charset": "utf8mb4"
        }
        
        validator = DatabaseConfigValidator(config)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_invalid_database_type(self):
        """Test validation with invalid database type."""
        config = {
            "type": "invalid_db",
            "host": "localhost"
        }
        
        validator = DatabaseConfigValidator(config)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is False
        assert any("Unsupported database type" in error for error in errors)
    
    def test_missing_postgresql_required_params(self):
        """Test validation with missing PostgreSQL required parameters."""
        config = {
            "type": "postgresql",
            "user": "testuser"
            # Missing host and name
        }
        
        validator = DatabaseConfigValidator(config)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is False
        assert any("requires 'host'" in error for error in errors)
        assert any("requires 'name'" in error for error in errors)
    
    def test_invalid_postgresql_ssl_mode(self):
        """Test validation with invalid PostgreSQL SSL mode."""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "name": "testdb",
            "ssl_mode": "invalid_mode"
        }
        
        validator = DatabaseConfigValidator(config)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is False
        assert any("Invalid PostgreSQL SSL mode" in error for error in errors)
    
    def test_invalid_port_number(self):
        """Test validation with invalid port number."""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "name": "testdb",
            "port": "99999"  # Invalid port
        }
        
        validator = DatabaseConfigValidator(config)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is False
        assert any("port must be between" in error for error in errors)
    
    def test_sqlite_unnecessary_params_warning(self):
        """Test warnings for unnecessary SQLite parameters."""
        config = {
            "type": "sqlite",
            "url": "sqlite:///./test.db",
            "host": "localhost",  # Unnecessary for SQLite
            "user": "testuser"    # Unnecessary for SQLite
        }
        
        validator = DatabaseConfigValidator(config)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is True
        assert any("not used with SQLite" in warning for warning in warnings)
    
    def test_pool_config_validation(self):
        """Test connection pool configuration validation."""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "name": "testdb",
            "pool_size": -1,  # Invalid
            "max_overflow": "invalid"  # Invalid
        }
        
        validator = DatabaseConfigValidator(config)
        is_valid, errors, warnings = validator.validate()
        
        assert is_valid is False
        assert any("Pool size must be at least 1" in error for error in errors)
        assert any("Max overflow must be a valid integer" in error for error in errors)


class TestDatabaseConfigParser:
    """Test database configuration parsing."""
    
    def test_parse_postgresql_connection_string(self):
        """Test parsing PostgreSQL connection string."""
        connection_string = "postgresql://user:pass@localhost:5432/mydb?sslmode=require"
        
        config = DatabaseConfigParser.parse_connection_string(connection_string)
        
        assert config["type"] == "postgresql"
        assert config["host"] == "localhost"
        assert config["port"] == "5432"
        assert config["user"] == "user"
        assert config["password"] == "pass"
        assert config["name"] == "mydb"
        assert config["ssl_mode"] == "require"
        assert config["url"] == connection_string
    
    def test_parse_mysql_connection_string(self):
        """Test parsing MySQL connection string."""
        connection_string = "mysql://user:pass@localhost:3306/mydb?charset=utf8mb4"
        
        config = DatabaseConfigParser.parse_connection_string(connection_string)
        
        assert config["type"] == "mysql"
        assert config["host"] == "localhost"
        assert config["port"] == "3306"
        assert config["user"] == "user"
        assert config["password"] == "pass"
        assert config["name"] == "mydb"
        assert config["charset"] == "utf8mb4"
    
    def test_parse_sqlite_connection_string(self):
        """Test parsing SQLite connection string."""
        connection_string = "sqlite:///./mydb.db"
        
        config = DatabaseConfigParser.parse_connection_string(connection_string)
        
        assert config["type"] == "sqlite"
        assert config["url"] == connection_string
    
    def test_parse_sqlite_memory_connection_string(self):
        """Test parsing SQLite in-memory connection string."""
        connection_string = "sqlite:///:memory:"
        
        config = DatabaseConfigParser.parse_connection_string(connection_string)
        
        assert config["type"] == "sqlite"
        assert config["url"] == connection_string
    
    def test_build_postgresql_connection_string(self):
        """Test building PostgreSQL connection string."""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": "5432",
            "user": "user",
            "password": "pass",
            "name": "mydb",
            "ssl_mode": "require"
        }
        
        connection_string = DatabaseConfigParser.build_connection_string(config)
        
        expected = "postgresql://user:pass@localhost:5432/mydb?sslmode=require"
        assert connection_string == expected
    
    def test_build_mysql_connection_string(self):
        """Test building MySQL connection string."""
        config = {
            "type": "mysql",
            "host": "localhost",
            "port": "3306",
            "user": "user",
            "password": "pass",
            "name": "mydb",
            "charset": "utf8mb4"
        }
        
        connection_string = DatabaseConfigParser.build_connection_string(config)
        
        expected = "mysql://user:pass@localhost:3306/mydb?charset=utf8mb4"
        assert connection_string == expected
    
    def test_build_sqlite_connection_string(self):
        """Test building SQLite connection string."""
        config = {
            "type": "sqlite",
            "name": "./mydb.db"
        }
        
        connection_string = DatabaseConfigParser.build_connection_string(config)
        
        expected = "sqlite:///./mydb.db"
        assert connection_string == expected
    
    def test_normalize_config_with_url(self):
        """Test configuration normalization with URL."""
        config = {
            "type": "postgresql",  # This should be overridden by URL
            "url": "mysql://user:pass@localhost:3306/mydb",
            "host": "override_host"  # This should override parsed host
        }
        
        normalized = DatabaseConfigParser.normalize_config(config)
        
        assert normalized["type"] == "mysql"  # From URL
        assert normalized["host"] == "override_host"  # From config override
        assert normalized["user"] == "user"  # From URL
        assert normalized["name"] == "mydb"  # From URL
    
    def test_validate_connection_string_format(self):
        """Test connection string format validation."""
        # Valid strings
        valid_strings = [
            "postgresql://user:pass@localhost:5432/db",
            "mysql://user:pass@localhost:3306/db",
            "sqlite:///./db.db",
            "sqlite:///:memory:"
        ]
        
        for conn_str in valid_strings:
            is_valid, error = DatabaseConfigParser.validate_connection_string_format(conn_str)
            assert is_valid is True, f"Should be valid: {conn_str}, error: {error}"
        
        # Invalid strings
        invalid_strings = [
            "",  # Empty
            "invalid://localhost/db",  # Unsupported scheme
            "postgresql:///db",  # Missing hostname
            "mysql://localhost",  # Missing database name
        ]
        
        for conn_str in invalid_strings:
            is_valid, error = DatabaseConfigParser.validate_connection_string_format(conn_str)
            assert is_valid is False, f"Should be invalid: {conn_str}"
            assert error is not None


@pytest.fixture
def temp_database():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    config = {
        "type": "sqlite",
        "url": f"sqlite:///{db_path}"
    }
    
    database = SQLiteDatabase(config)
    yield database
    
    # Cleanup
    database.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestDatabaseConnectionManager:
    """Test database connection management."""
    
    def test_successful_connection(self, temp_database):
        """Test successful database connection."""
        manager = DatabaseConnectionManager(temp_database)
        
        success, error = manager.test_connection()
        
        assert success is True
        assert error is None
    
    def test_connection_retry_logic(self, temp_database):
        """Test connection retry logic with mock failures."""
        manager = DatabaseConnectionManager(temp_database)
        manager.max_retries = 2
        manager.base_delay = 0.1  # Speed up test
        
        # Mock the engine to fail first two attempts, succeed on third
        original_engine = temp_database._engine
        
        call_count = 0
        def mock_session_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise OperationalError("Connection failed", None, None)
            else:
                # Return a working session for the third attempt
                from sqlmodel import Session
                return Session(original_engine)
        
        with patch('sqlmodel.Session') as mock_session:
            mock_session.side_effect = mock_session_side_effect
            
            success, error = manager.test_connection()
            
            assert success is True
            assert error is None
            assert call_count == 3  # Should have tried 3 times
    
    def test_connection_max_retries_exceeded(self, temp_database):
        """Test connection failure after max retries."""
        manager = DatabaseConnectionManager(temp_database)
        manager.max_retries = 1
        manager.base_delay = 0.01  # Speed up test
        
        with patch('sqlmodel.Session') as mock_session:
            mock_session.side_effect = OperationalError("Connection failed", None, None)
            
            success, error = manager.test_connection()
            
            assert success is False
            assert error is not None
            assert "Connection failed" in error
    
    def test_get_health_status(self, temp_database):
        """Test getting database health status."""
        manager = DatabaseConnectionManager(temp_database)
        
        health = manager.get_health_status()
        
        assert health["status"] == "healthy"
        assert "connection_time_ms" in health
        assert health["database_type"] == "sqlite"
        assert health["connection_error"] is None
        assert "timestamp" in health
    
    def test_get_health_status_with_failure(self, temp_database):
        """Test health status with connection failure."""
        manager = DatabaseConnectionManager(temp_database)
        
        with patch.object(manager, 'test_connection', return_value=(False, "Connection failed")):
            health = manager.get_health_status()
            
            assert health["status"] == "unhealthy"
            assert health["connection_error"] == "Connection failed"


class TestIntegrationFunctions:
    """Test integration functions."""
    
    def test_validate_database_config_function(self):
        """Test validate_database_config function."""
        config = {
            "type": "sqlite",
            "url": "sqlite:///./test.db"
        }
        
        is_valid, errors, warnings = validate_database_config(config)
        
        assert is_valid is True
        assert isinstance(errors, list)
        assert isinstance(warnings, list)
    
    def test_test_database_connection_function(self, temp_database):
        """Test test_database_connection function."""
        success, error = test_database_connection(temp_database)
        
        assert success is True
        assert error is None
    
    def test_get_database_health_function(self, temp_database):
        """Test get_database_health function."""
        health = get_database_health(temp_database)
        
        assert isinstance(health, dict)
        assert "status" in health
        assert "timestamp" in health


if __name__ == "__main__":
    pytest.main([__file__])