"""
Tests for MySQL/MariaDB database implementation.
These tests verify the MySQL database functionality without requiring a real MySQL instance.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.engine import Engine

from app.database.mysql import MySQLDatabase
from app.database.factory import DatabaseFactory


class TestMySQLDatabase:
    """Test MySQL database implementation."""

    def test_mysql_config_validation(self):
        """Test MySQL configuration validation."""
        # Test valid configuration
        config = {
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "test_db",
            "user": "test_user",
            "password": "test_pass",
            "ssl_mode": "PREFERRED"
        }
        
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'pymysql' else __import__(name, *args)):
            db = MySQLDatabase(config)
            assert db.validate_config() is True

    def test_mysql_config_validation_missing_user(self):
        """Test MySQL configuration validation with missing user."""
        config = {
            "type": "mysql",
            "host": "localhost",
            "database": "test_db"
        }
        
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'pymysql' else __import__(name, *args)):
            db = MySQLDatabase(config)
            with pytest.raises(ValueError, match="MySQL user/username is required"):
                db.validate_config()

    def test_mysql_config_validation_invalid_ssl_mode(self):
        """Test MySQL configuration validation with invalid SSL mode."""
        config = {
            "type": "mysql",
            "host": "localhost",
            "user": "test_user",
            "ssl_mode": "invalid_mode"
        }
        
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'pymysql' else __import__(name, *args)):
            db = MySQLDatabase(config)
            with pytest.raises(ValueError, match="Invalid SSL mode"):
                db.validate_config()

    def test_mysql_config_validation_missing_driver(self):
        """Test MySQL configuration validation when no MySQL driver is available."""
        config = {
            "type": "mysql",
            "host": "localhost",
            "user": "test_user"
        }
        
        def mock_import(name, *args):
            if name in ['pymysql', 'mysqlclient', 'mysql-connector-python']:
                raise ImportError()
            return __import__(name, *args)
        
        with patch('builtins.__import__', side_effect=mock_import):
            db = MySQLDatabase(config)
            with pytest.raises(ImportError, match="No MySQL driver found"):
                db.validate_config()

    def test_connection_string_from_components(self):
        """Test building connection string from individual components."""
        config = {
            "host": "localhost",
            "port": 3306,
            "database": "test_db",
            "user": "test_user",
            "password": "test_pass"
        }
        
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'pymysql' else __import__(name, *args)):
            db = MySQLDatabase(config)
            connection_string = db.get_connection_string()
            
            expected = "mysql+pymysql://test_user:test_pass@localhost:3306/test_db?charset=utf8mb4"
            assert connection_string == expected

    def test_connection_string_from_url(self):
        """Test using provided URL."""
        config = {
            "url": "mysql+pymysql://user:pass@host:3306/dbname"
        }
        
        db = MySQLDatabase(config)
        connection_string = db.get_connection_string()
        
        assert "mysql+pymysql://user:pass@host:3306/dbname" in connection_string

    def test_connection_string_with_charset(self):
        """Test connection string with custom charset."""
        config = {
            "host": "localhost",
            "user": "test_user",
            "database": "test_db",
            "charset": "utf8"
        }
        
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'pymysql' else __import__(name, *args)):
            db = MySQLDatabase(config)
            connection_string = db.get_connection_string()
            
            assert "charset=utf8" in connection_string

    def test_mysql_driver_detection(self):
        """Test MySQL driver detection logic."""
        config = {"host": "localhost", "user": "test_user", "database": "test_db"}
        
        # Test pymysql detection
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'pymysql' else __import__(name, *args)):
            db = MySQLDatabase(config)
            driver = db._get_mysql_driver()
            assert driver == "pymysql"
        
        # Test mysqlclient detection (when pymysql not available)
        def mock_import_mysqlclient(name, *args):
            if name == 'pymysql':
                raise ImportError()
            elif name == 'mysqlclient':
                return Mock()
            return __import__(name, *args)
        
        with patch('builtins.__import__', side_effect=mock_import_mysqlclient):
            db = MySQLDatabase(config)
            driver = db._get_mysql_driver()
            assert driver == "mysqldb"

    def test_connect_args_with_ssl(self):
        """Test connection arguments with SSL configuration."""
        config = {
            "ssl_mode": "REQUIRED",
            "ssl_cert": "/path/to/cert.pem",
            "ssl_key": "/path/to/key.pem",
            "ssl_ca": "/path/to/ca.pem",
            "connect_timeout": 30,
            "charset": "utf8mb4",
            "sql_mode": "STRICT_TRANS_TABLES",
            "autocommit": True
        }
        
        db = MySQLDatabase(config)
        connect_args = db._get_connect_args()
        
        assert connect_args["ssl_disabled"] is False
        assert connect_args["ssl_cert"] == "/path/to/cert.pem"
        assert connect_args["ssl_key"] == "/path/to/key.pem"
        assert connect_args["ssl_ca"] == "/path/to/ca.pem"
        assert connect_args["connect_timeout"] == 30
        assert connect_args["charset"] == "utf8mb4"
        assert connect_args["sql_mode"] == "STRICT_TRANS_TABLES"
        assert connect_args["autocommit"] is True

    def test_connect_args_ssl_disabled(self):
        """Test connection arguments with SSL disabled."""
        config = {
            "ssl_mode": "DISABLED"
        }
        
        db = MySQLDatabase(config)
        connect_args = db._get_connect_args()
        
        assert connect_args["ssl_disabled"] is True

    @patch('app.database.mysql.create_engine')
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
        
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'pymysql' else __import__(name, *args)):
            db = MySQLDatabase(config)
            engine = db.create_engine()
            
            # Verify create_engine was called with correct parameters
            mock_create_engine.assert_called_once()
            call_args = mock_create_engine.call_args
            
            # Check connection string
            assert call_args[0][0].startswith("mysql+")
            
            # Check pooling parameters
            kwargs = call_args[1]
            assert kwargs["pool_size"] == 15
            assert kwargs["max_overflow"] == 25
            assert kwargs["pool_recycle"] == 7200
            assert kwargs["pool_pre_ping"] is True

    def test_factory_registration(self):
        """Test that MySQL is registered in the factory when available."""
        with patch('app.database.factory._MYSQL_AVAILABLE', True):
            supported_types = DatabaseFactory.get_supported_types()
            assert "mysql" in supported_types
            assert "mariadb" in supported_types

    def test_factory_creation_mysql(self):
        """Test creating MySQL database through factory."""
        config = {
            "type": "mysql",
            "host": "localhost",
            "user": "test_user",
            "name": "test_db"
        }
        
        with patch('sys.modules', {'pymysql': Mock()}), patch('app.database.factory._MYSQL_AVAILABLE', True):
            with patch('app.database.validation.validate_database_config', return_value=(True, [], [])):
                with patch('app.database.factory._MYSQL_AVAILABLE', True):
                    db = DatabaseFactory.create_database(config)
                    assert isinstance(db, MySQLDatabase)

    def test_factory_creation_mariadb(self):
        """Test creating MariaDB database through factory (uses MySQL implementation)."""
        config = {
            "type": "mariadb",
            "host": "localhost",
            "user": "test_user",
            "name": "test_db"
        }
        
        with patch('sys.modules', {'pymysql': Mock()}), patch('app.database.factory._MYSQL_AVAILABLE', True):
            with patch('app.database.validation.validate_database_config', return_value=(True, [], [])):
                with patch('app.database.factory._MYSQL_AVAILABLE', True):
                    db = DatabaseFactory.create_database(config)
                    assert isinstance(db, MySQLDatabase)

    @patch('app.database.mysql.Session')
    def test_database_info_mysql(self, mock_session_class):
        """Test getting MySQL database information."""
        config = {
            "host": "localhost",
            "user": "test_user",
            "database": "test_db",
            "pool_size": 15,
            "ssl_mode": "PREFERRED"
        }
        
        # Mock session and query results for MySQL
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        version_result = Mock()
        version_result.first.return_value = ("8.0.32",)
        
        db_result = Mock()
        db_result.first.return_value = ("test_db",)
        
        charset_result = Mock()
        charset_result.first.return_value = ("utf8mb4",)
        
        collation_result = Mock()
        collation_result.first.return_value = ("utf8mb4_unicode_ci",)
        
        mock_session.exec.side_effect = [version_result, db_result, charset_result, collation_result]
        
        with patch('app.database.mysql.create_engine'):
            db = MySQLDatabase(config)
            db._engine = Mock()  # Mock the engine
            
            info = db.get_database_info()
            
            assert info["type"] == "mysql"
            assert info["version"] == "8.0.32"
            assert info["database"] == "test_db"
            assert info["charset"] == "utf8mb4"
            assert info["collation"] == "utf8mb4_unicode_ci"
            assert info["connection_pool_size"] == 15
            assert info["ssl_mode"] == "PREFERRED"

    @patch('app.database.mysql.Session')
    def test_database_info_mariadb(self, mock_session_class):
        """Test getting MariaDB database information."""
        config = {
            "host": "localhost",
            "user": "test_user",
            "database": "test_db"
        }
        
        # Mock session and query results for MariaDB
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        version_result = Mock()
        version_result.first.return_value = ("10.6.12-MariaDB",)
        
        db_result = Mock()
        db_result.first.return_value = ("test_db",)
        
        charset_result = Mock()
        charset_result.first.return_value = ("utf8mb4",)
        
        collation_result = Mock()
        collation_result.first.return_value = ("utf8mb4_general_ci",)
        
        mock_session.exec.side_effect = [version_result, db_result, charset_result, collation_result]
        
        with patch('app.database.mysql.create_engine'):
            db = MySQLDatabase(config)
            db._engine = Mock()  # Mock the engine
            
            info = db.get_database_info()
            
            assert info["type"] == "mariadb"  # Should detect MariaDB from version string
            assert info["version"] == "10.6.12-MariaDB"
            assert info["database"] == "test_db"

    def test_cloud_connection_strings(self):
        """Test various cloud database connection string formats."""
        # AWS RDS MySQL
        aws_config = {
            "url": "mysql://user:pass@mydb.123456789012.us-east-1.rds.amazonaws.com:3306/mydb"
        }
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'pymysql' else __import__(name, *args)):
            db = MySQLDatabase(aws_config)
            connection_string = db.get_connection_string()
            assert "rds.amazonaws.com" in connection_string
            assert "mysql+pymysql" in connection_string
        
        # Google Cloud SQL MySQL
        gcp_config = {
            "url": "mysql://user:pass@1.2.3.4:3306/mydb"
        }
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'pymysql' else __import__(name, *args)):
            db = MySQLDatabase(gcp_config)
            connection_string = db.get_connection_string()
            assert "mysql+pymysql://user:pass@1.2.3.4:3306/mydb" in connection_string
        
        # Azure Database for MySQL
        azure_config = {
            "url": "mysql://user%40server:pass@server.mysql.database.azure.com:3306/mydb"
        }
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'pymysql' else __import__(name, *args)):
            db = MySQLDatabase(azure_config)
            connection_string = db.get_connection_string()
            assert "azure.com" in connection_string

    def test_charset_validation_warning(self):
        """Test that unusual charsets generate warnings."""
        config = {
            "host": "localhost",
            "user": "test_user",
            "database": "test_db",
            "charset": "unusual_charset"
        }
        
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'pymysql' else __import__(name, *args)):
            with patch('app.database.mysql.logging') as mock_logging:
                db = MySQLDatabase(config)
                db.validate_config()
                
                # Should log a warning about unusual charset
                mock_logging.warning.assert_called_once()
                assert "unusual charset" in mock_logging.warning.call_args[0][0].lower()


class TestMySQLIntegration:
    """Integration tests for MySQL (require manual testing with real database)."""
    
    def test_real_mysql_connection_example(self):
        """
        Example test for real MySQL connection.
        This test is skipped by default but can be used for manual testing.
        
        To run this test manually:
        1. Set up a MySQL database
        2. Set environment variables:
           export INTENTVERSE_DB_TYPE=mysql
           export INTENTVERSE_DB_HOST=localhost
           export INTENTVERSE_DB_USER=test_user
           export INTENTVERSE_DB_PASSWORD=test_pass
           export INTENTVERSE_DB_NAME=test_db
        3. Run: pytest -k test_real_mysql_connection_example -s
        """
        pytest.skip("Manual test - requires real MySQL database")
        
        # Uncomment and modify for manual testing:
        # config = {
        #     "type": "mysql",
        #     "host": "localhost",
        #     "port": 3306,
        #     "database": "test_db",
        #     "user": "test_user",
        #     "password": "test_pass",
        #     "ssl_mode": "PREFERRED"
        # }
        # 
        # db = MySQLDatabase(config)
        # assert db.validate_config() is True
        # assert db.test_connection() is True
        # 
        # # Test database info
        # info = db.get_database_info()
        # assert info["type"] in ["mysql", "mariadb"]
        # assert len(info["version"]) > 0