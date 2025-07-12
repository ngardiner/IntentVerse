"""
Tests for PostgreSQL database implementation.
These tests verify the PostgreSQL database functionality without requiring a real PostgreSQL instance.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.engine import Engine

from app.database.postgresql import PostgreSQLDatabase
from app.database.factory import DatabaseFactory


class TestPostgreSQLDatabase:
    """Test PostgreSQL database implementation."""

    def test_postgresql_config_validation(self):
        """Test PostgreSQL configuration validation."""
        # Test valid configuration
        config = {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "user": "test_user",
            "password": "test_pass",
            "ssl_mode": "prefer"
        }
        
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'psycopg2' else __import__(name, *args)):
            db = PostgreSQLDatabase(config)
            assert db.validate_config() is True

    def test_postgresql_config_validation_missing_user(self):
        """Test PostgreSQL configuration validation with missing user."""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "database": "test_db"
        }
        
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'psycopg2' else __import__(name, *args)):
            db = PostgreSQLDatabase(config)
            with pytest.raises(ValueError, match="PostgreSQL user/username is required"):
                db.validate_config()

    def test_postgresql_config_validation_invalid_ssl_mode(self):
        """Test PostgreSQL configuration validation with invalid SSL mode."""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "user": "test_user",
            "ssl_mode": "invalid_mode"
        }
        
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'psycopg2' else __import__(name, *args)):
            db = PostgreSQLDatabase(config)
            with pytest.raises(ValueError, match="Invalid SSL mode"):
                db.validate_config()

    def test_postgresql_config_validation_missing_psycopg2(self):
        """Test PostgreSQL configuration validation when psycopg2 is missing."""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "user": "test_user"
        }
        
        with patch('builtins.__import__', side_effect=lambda name, *args: (_ for _ in ()).throw(ImportError()) if name == 'psycopg2' else __import__(name, *args)):
            db = PostgreSQLDatabase(config)
            with pytest.raises(ImportError, match="PostgreSQL support requires psycopg2"):
                db.validate_config()

    def test_connection_string_from_components(self):
        """Test building connection string from individual components."""
        config = {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "user": "test_user",
            "password": "test_pass"
        }
        
        db = PostgreSQLDatabase(config)
        connection_string = db.get_connection_string()
        
        expected = "postgresql://test_user:test_pass@localhost:5432/test_db"
        assert connection_string == expected

    def test_connection_string_from_url(self):
        """Test using provided URL."""
        config = {
            "url": "postgresql://user:pass@host:5432/dbname"
        }
        
        db = PostgreSQLDatabase(config)
        connection_string = db.get_connection_string()
        
        assert connection_string == "postgresql://user:pass@host:5432/dbname"

    def test_connection_string_with_ssl_mode(self):
        """Test connection string with SSL mode."""
        config = {
            "host": "localhost",
            "user": "test_user",
            "database": "test_db",
            "ssl_mode": "require"
        }
        
        db = PostgreSQLDatabase(config)
        connection_string = db.get_connection_string()
        
        assert "sslmode=require" in connection_string

    def test_connect_args_with_ssl(self):
        """Test connection arguments with SSL configuration."""
        config = {
            "ssl_mode": "require",
            "ssl_cert": "/path/to/cert.pem",
            "ssl_key": "/path/to/key.pem",
            "ssl_ca": "/path/to/ca.pem",
            "connect_timeout": 30,
            "application_name": "TestApp"
        }
        
        db = PostgreSQLDatabase(config)
        connect_args = db._get_connect_args()
        
        assert connect_args["sslmode"] == "require"
        assert connect_args["sslcert"] == "/path/to/cert.pem"
        assert connect_args["sslkey"] == "/path/to/key.pem"
        assert connect_args["sslrootcert"] == "/path/to/ca.pem"
        assert connect_args["connect_timeout"] == 30
        assert connect_args["application_name"] == "TestApp"

    @patch('app.database.postgresql.create_engine')
    def test_create_engine_with_pooling(self, mock_create_engine):
        """Test engine creation with connection pooling."""
        config = {
            "host": "localhost",
            "user": "test_user",
            "database": "test_db",
            "pool_size": 15,
            "max_overflow": 25,
            "pool_recycle": 7200
        }
        
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine
        
        db = PostgreSQLDatabase(config)
        engine = db.create_engine()
        
        # Verify create_engine was called with correct parameters
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        
        # Check connection string
        assert call_args[0][0].startswith("postgresql://")
        
        # Check pooling parameters
        kwargs = call_args[1]
        assert kwargs["pool_size"] == 15
        assert kwargs["max_overflow"] == 25
        assert kwargs["pool_recycle"] == 7200
        assert kwargs["pool_pre_ping"] is True

    def test_factory_registration(self):
        """Test that PostgreSQL is registered in the factory when available."""
        with patch('app.database.factory._POSTGRESQL_AVAILABLE', True):
            supported_types = DatabaseFactory.get_supported_types()
            assert "postgresql" in supported_types

    def test_factory_creation(self):
        """Test creating PostgreSQL database through factory."""
        config = {
            "type": "postgresql",
            "host": "localhost",
            "user": "test_user",
            "database": "test_db"
        }
        
        with patch.dict('sys.modules', {'psycopg2': Mock()}), patch('app.database.factory._POSTGRESQL_AVAILABLE', True):
            with patch('app.database.validation.validate_database_config', return_value=(True, [], [])):
                with patch('app.database.factory._POSTGRESQL_AVAILABLE', True):
                    db = DatabaseFactory.create_database(config)
                    assert isinstance(db, PostgreSQLDatabase)

    @patch('app.database.postgresql.Session')
    def test_database_info(self, mock_session_class):
        """Test getting database information."""
        config = {
            "host": "localhost",
            "user": "test_user",
            "database": "test_db",
            "pool_size": 15,
            "ssl_mode": "prefer"
        }
        
        # Mock session and query results
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        # Mock the exec method to return proper result objects
        version_result = Mock()
        version_result.first.return_value = ("PostgreSQL 14.5",)
        
        db_result = Mock()
        db_result.first.return_value = ("test_db",)
        
        mock_session.exec.side_effect = [version_result, db_result]
        
        with patch('app.database.postgresql.create_engine'):
            db = PostgreSQLDatabase(config)
            db._engine = Mock()  # Mock the engine
            
            info = db.get_database_info()
            
            assert info["type"] == "postgresql"
            assert info["version"] == "PostgreSQL 14.5"
            assert info["database"] == "test_db"
            assert info["connection_pool_size"] == 15
            assert info["ssl_mode"] == "prefer"

    def test_cloud_connection_strings(self):
        """Test various cloud database connection string formats."""
        # AWS RDS
        aws_config = {
            "url": "postgresql://user:pass@mydb.123456789012.us-east-1.rds.amazonaws.com:5432/mydb"
        }
        db = PostgreSQLDatabase(aws_config)
        assert "rds.amazonaws.com" in db.get_connection_string()
        
        # Google Cloud SQL
        gcp_config = {
            "url": "postgresql://user:pass@1.2.3.4:5432/mydb"
        }
        db = PostgreSQLDatabase(gcp_config)
        assert "postgresql://user:pass@1.2.3.4:5432/mydb" == db.get_connection_string()
        
        # Azure Database
        azure_config = {
            "url": "postgresql://user%40server:pass@server.postgres.database.azure.com:5432/mydb"
        }
        db = PostgreSQLDatabase(azure_config)
        assert "azure.com" in db.get_connection_string()


class TestPostgreSQLIntegration:
    """Integration tests for PostgreSQL (require manual testing with real database)."""
    
    def test_real_postgresql_connection_example(self):
        """
        Example test for real PostgreSQL connection.
        This test is skipped by default but can be used for manual testing.
        
        To run this test manually:
        1. Set up a PostgreSQL database
        2. Set environment variables:
           export INTENTVERSE_DB_TYPE=postgresql
           export INTENTVERSE_DB_HOST=localhost
           export INTENTVERSE_DB_USER=test_user
           export INTENTVERSE_DB_PASSWORD=test_pass
           export INTENTVERSE_DB_NAME=test_db
        3. Run: pytest -k test_real_postgresql_connection_example -s
        """
        pytest.skip("Manual test - requires real PostgreSQL database")
        
        # Uncomment and modify for manual testing:
        # config = {
        #     "type": "postgresql",
        #     "host": "localhost",
        #     "port": 5432,
        #     "database": "test_db",
        #     "user": "test_user",
        #     "password": "test_pass",
        #     "ssl_mode": "prefer"
        # }
        # 
        # db = PostgreSQLDatabase(config)
        # assert db.validate_config() is True
        # assert db.test_connection() is True
        # 
        # # Test database info
        # info = db.get_database_info()
        # assert info["type"] == "postgresql"
        # assert "PostgreSQL" in info["version"]