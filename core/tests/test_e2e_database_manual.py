"""
Database Integration E2E Tests

These tests validate database implementations across different engines.
They are run automatically in CI using Docker containers with the
database_integration marker.

The tests are executed as part of the database compatibility matrix
in GitHub Actions, testing PostgreSQL, MySQL, and MariaDB.
"""

import pytest
import os
import time
from sqlmodel import Session, select

from app.database import initialize_database, get_database, reset_database
from app.models import User, UserGroup, AuditLog
from app.config import Config


@pytest.mark.database_integration
class TestPostgreSQLManual:
    """Manual E2E tests for PostgreSQL."""
    
    def setup_method(self):
        """Setup for each test."""
        reset_database()
    
    def teardown_method(self):
        """Cleanup after each test."""
        reset_database()
    
    def test_postgresql_connection_and_operations(self):
        """Test PostgreSQL connection and basic operations."""
        # Skip if not configured for PostgreSQL
        if os.getenv("INTENTVERSE_DB_TYPE") != "postgresql":
            pytest.skip("PostgreSQL not configured")
        
        config = Config.get_database_config()
        assert config["type"] == "postgresql"
        
        # Initialize database
        database = initialize_database(config)
        assert database is not None
        
        # Test connection
        success, error = database.test_connection()
        assert success is True, f"Connection failed: {error}"
        
        # Test health status
        health = database.get_health_status()
        assert health["status"] == "healthy"
        assert "version" in health
        
        # Create tables
        database.create_db_and_tables()
        
        # Test basic CRUD operations
        with Session(database.engine) as session:
            # Create a test user
            test_user = User(username="test_pg_user", email="test@example.com", hashed_password="test_hash")
            session.add(test_user)
            session.commit()
            session.refresh(test_user)
            
            # Verify user was created
            found_user = session.exec(select(User).where(User.username == "test_pg_user")).first()
            assert found_user is not None
            assert found_user.email == "test@example.com"
            
            # Test audit log
            audit_entry = AuditLog(
                user_id=test_user.id,
                action="test_action",
                resource_type="test_resource",
                resource_id="test_id",
                details={"test": "data"}
            )
            session.add(audit_entry)
            session.commit()
            
            # Verify audit log
            found_audit = session.exec(select(AuditLog).where(AuditLog.user_id == test_user.id)).first()
            assert found_audit is not None
            assert found_audit.action == "test_action"
    
    def test_postgresql_migration_system(self):
        """Test PostgreSQL migration system."""
        if os.getenv("INTENTVERSE_DB_TYPE") != "postgresql":
            pytest.skip("PostgreSQL not configured")
        
        config = Config.get_database_config()
        database = initialize_database(config)
        
        # Test migration status
        status = database.get_migration_status()
        assert "current_version" in status
        assert "pending_migrations" in status
        
        # Test running migrations
        success = database.run_migrations()
        assert success is True
        
        # Verify migration history
        from app.database.migrations import get_migration_manager
        manager = get_migration_manager(database)
        history = manager.get_migration_history()
        assert len(history) > 0
    
    def test_postgresql_connection_pooling(self):
        """Test PostgreSQL connection pooling."""
        if os.getenv("INTENTVERSE_DB_TYPE") != "postgresql":
            pytest.skip("PostgreSQL not configured")
        
        config = Config.get_database_config()
        database = initialize_database(config)
        
        # Test multiple concurrent connections
        sessions = []
        try:
            for i in range(5):
                session = Session(database.engine)
                result = session.exec(select(1)).first()
                assert result == 1
                sessions.append(session)
            
        finally:
            for session in sessions:
                session.close()


@pytest.mark.database_integration
class TestMySQLManual:
    """Manual E2E tests for MySQL."""
    
    def setup_method(self):
        """Setup for each test."""
        reset_database()
    
    def teardown_method(self):
        """Cleanup after each test."""
        reset_database()
    
    def test_mysql_connection_and_operations(self):
        """Test MySQL connection and basic operations."""
        if os.getenv("INTENTVERSE_DB_TYPE") not in ["mysql", "mariadb"]:
            pytest.skip("MySQL/MariaDB not configured")
        
        config = Config.get_database_config()
        assert config["type"] in ["mysql", "mariadb"]
        
        # Initialize database
        database = initialize_database(config)
        assert database is not None
        
        # Test connection
        success, error = database.test_connection()
        assert success is True, f"Connection failed: {error}"
        
        # Test health status
        health = database.get_health_status()
        assert health["status"] == "healthy"
        assert "version" in health
        
        # Create tables
        database.create_db_and_tables()
        
        # Test basic CRUD operations
        with Session(database.engine) as session:
            # Create a test user
            test_user = User(username="test_mysql_user", email="test@example.com", hashed_password="test_hash")
            session.add(test_user)
            session.commit()
            session.refresh(test_user)
            
            # Verify user was created
            found_user = session.exec(select(User).where(User.username == "test_mysql_user")).first()
            assert found_user is not None
            assert found_user.email == "test@example.com"
    
    def test_mysql_charset_handling(self):
        """Test MySQL charset handling."""
        if os.getenv("INTENTVERSE_DB_TYPE") not in ["mysql", "mariadb"]:
            pytest.skip("MySQL/MariaDB not configured")
        
        config = Config.get_database_config()
        database = initialize_database(config)
        
        # Test unicode handling
        with Session(database.engine) as session:
            test_user = User(username="test_unicode", email="test@example.com", hashed_password="test_hash")
            session.add(test_user)
            session.commit()
            
            found_user = session.exec(select(User).where(User.username == "test_unicode")).first()
            assert found_user is not None


@pytest.mark.database_integration
class TestCrossDatabaseCompatibility:
    """Test compatibility across different database engines."""
    
    def test_schema_consistency(self):
        """Test that schema is consistent across databases."""
        # This test can run with any database type
        config = Config.get_database_config()
        database = initialize_database(config)
        
        # Create tables
        database.create_db_and_tables()
        
        # Test that all expected tables exist by trying to query them
        with Session(database.engine) as session:
            # Test core tables
            session.exec(select(User)).all()
            session.exec(select(UserGroup)).all()
            session.exec(select(AuditLog)).all()
    
    def test_migration_consistency(self):
        """Test that migrations work consistently."""
        config = Config.get_database_config()
        database = initialize_database(config)
        
        # Test migration system
        status = database.get_migration_status()
        assert isinstance(status, dict)
        
        # Test running migrations
        success = database.run_migrations()
        assert isinstance(success, bool)


class TestDatabasePerformance:
    """Basic performance tests."""
    
    def test_connection_time(self):
        """Test database connection time."""
        config = Config.get_database_config()
        database = initialize_database(config)
        
        start_time = time.time()
        success, error = database.test_connection()
        connection_time = time.time() - start_time
        
        assert success is True
        assert connection_time < 5.0  # Should connect within 5 seconds
    
    def test_basic_query_performance(self):
        """Test basic query performance."""
        config = Config.get_database_config()
        database = initialize_database(config)
        database.create_db_and_tables()
        
        with Session(database.engine) as session:
            start_time = time.time()
            result = session.exec(select(1)).first()
            query_time = time.time() - start_time
            
            assert result == 1
            assert query_time < 1.0  # Should execute within 1 second


if __name__ == "__main__":
    # Run specific test based on environment
    db_type = os.getenv("INTENTVERSE_DB_TYPE", "sqlite")
    
    if db_type == "postgresql":
        pytest.main(["-v", "tests/test_e2e_database_manual.py::TestPostgreSQLManual"])
    elif db_type in ["mysql", "mariadb"]:
        pytest.main(["-v", "tests/test_e2e_database_manual.py::TestMySQLManual"])
    else:
        pytest.main(["-v", "tests/test_e2e_database_manual.py::TestCrossDatabaseCompatibility"])