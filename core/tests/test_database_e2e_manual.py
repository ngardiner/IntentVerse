"""
Manual End-to-End Database Tests

These tests require actual database instances and are designed for manual testing
during development. They are not run in CI but provide comprehensive validation
of real database connectivity and operations.

Usage:
    # Test with local PostgreSQL
    pytest tests/test_database_e2e_manual.py::TestPostgreSQLManual -v
    
    # Test with local MySQL
    pytest tests/test_database_e2e_manual.py::TestMySQLManual -v
    
    # Test with Docker databases
    docker-compose -f docs/deploy/docker-compose.postgresql.yml up -d
    pytest tests/test_database_e2e_manual.py::TestPostgreSQLManual -v
    docker-compose -f docs/deploy/docker-compose.postgresql.yml down
"""

import pytest
import os
import time
from sqlmodel import Session, select
from sqlalchemy.exc import OperationalError

from app.database import DatabaseFactory, initialize_database, reset_database
from app.models import User, UserGroup, AuditLog
from app.database.migrations import get_migration_manager


# Mark all tests in this module as manual E2E tests
pytestmark = pytest.mark.e2e


class DatabaseE2ETestBase:
    """Base class for E2E database tests."""
    
    def setup_method(self):
        """Setup before each test."""
        reset_database()
    
    def teardown_method(self):
        """Cleanup after each test."""
        reset_database()
    
    def test_basic_connectivity(self, config):
        """Test basic database connectivity."""
        database = DatabaseFactory.create_database(config)
        
        # Test connection
        success, error = database.test_connection()
        assert success, f"Connection failed: {error}"
        
        # Test health status
        health = database.get_health_status()
        assert health["status"] == "healthy"
        assert health["database_type"] == config["type"]
        
        database.close()
    
    def test_database_initialization(self, config):
        """Test full database initialization."""
        database = initialize_database(config, validate_connection=True)
        
        # Should be able to get the database instance
        from app.database import get_database
        assert get_database() is database
        
        # Test that tables can be created
        database.create_db_and_tables()
        
        # Verify engine is working
        with Session(database.engine) as session:
            result = session.exec(select(1)).first()
            assert result == 1
    
    def test_migration_system(self, config):
        """Test migration system with real database."""
        database = initialize_database(config, validate_connection=True)
        
        # Test migration status
        status = database.get_migration_status()
        assert isinstance(status, dict)
        assert "current_version" in status
        
        # Test running migrations
        success = database.run_migrations()
        assert success, "Migrations should succeed"
        
        # Test migration manager
        manager = get_migration_manager(database)
        validation = manager.validate_migrations()
        assert validation["valid"], f"Migration validation failed: {validation['issues']}"
    
    def test_crud_operations(self, config):
        """Test basic CRUD operations."""
        database = initialize_database(config, validate_connection=True)
        database.create_db_and_tables()
        
        with Session(database.engine) as session:
            # Create
            user = User(username="testuser", email="test@example.com")
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Read
            found_user = session.exec(select(User).where(User.username == "testuser")).first()
            assert found_user is not None
            assert found_user.username == "testuser"
            assert found_user.email == "test@example.com"
            
            # Update
            found_user.email = "updated@example.com"
            session.add(found_user)
            session.commit()
            
            # Verify update
            updated_user = session.exec(select(User).where(User.username == "testuser")).first()
            assert updated_user.email == "updated@example.com"
            
            # Delete
            session.delete(updated_user)
            session.commit()
            
            # Verify delete
            deleted_user = session.exec(select(User).where(User.username == "testuser")).first()
            assert deleted_user is None
    
    def test_transaction_handling(self, config):
        """Test transaction handling and rollback."""
        database = initialize_database(config, validate_connection=True)
        database.create_db_and_tables()
        
        with Session(database.engine) as session:
            try:
                # Start transaction
                user1 = User(username="user1", email="user1@example.com")
                session.add(user1)
                session.flush()  # Flush but don't commit
                
                # This should work
                user2 = User(username="user2", email="user2@example.com")
                session.add(user2)
                session.flush()
                
                # Simulate an error and rollback
                session.rollback()
                
                # Verify rollback worked
                users = session.exec(select(User)).all()
                assert len(users) == 0
                
            except Exception as e:
                session.rollback()
                raise
    
    def test_concurrent_connections(self, config):
        """Test multiple concurrent connections."""
        database = initialize_database(config, validate_connection=True)
        database.create_db_and_tables()
        
        # Create multiple sessions
        sessions = []
        try:
            for i in range(5):
                session = Session(database.engine)
                sessions.append(session)
                
                # Each session should be able to query
                result = session.exec(select(1)).first()
                assert result == 1
        
        finally:
            # Clean up sessions
            for session in sessions:
                session.close()
    
    def test_performance_basic(self, config):
        """Test basic performance characteristics."""
        database = initialize_database(config, validate_connection=True)
        database.create_db_and_tables()
        
        # Test connection time
        start_time = time.time()
        success, error = database.test_connection()
        connection_time = time.time() - start_time
        
        assert success, f"Connection failed: {error}"
        assert connection_time < 5.0, f"Connection took too long: {connection_time}s"
        
        # Test bulk operations
        with Session(database.engine) as session:
            start_time = time.time()
            
            # Insert multiple records
            users = []
            for i in range(100):
                user = User(username=f"user{i}", email=f"user{i}@example.com")
                users.append(user)
            
            session.add_all(users)
            session.commit()
            
            insert_time = time.time() - start_time
            assert insert_time < 10.0, f"Bulk insert took too long: {insert_time}s"
            
            # Query all records
            start_time = time.time()
            all_users = session.exec(select(User)).all()
            query_time = time.time() - start_time
            
            assert len(all_users) == 100
            assert query_time < 5.0, f"Query took too long: {query_time}s"


class TestPostgreSQLManual(DatabaseE2ETestBase):
    """Manual E2E tests for PostgreSQL."""
    
    @pytest.fixture
    def config(self):
        """PostgreSQL configuration for testing."""
        return {
            "type": "postgresql",
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "name": os.getenv("POSTGRES_DB", "intentverse_test"),
            "user": os.getenv("POSTGRES_USER", "intentverse"),
            "password": os.getenv("POSTGRES_PASSWORD", "intentverse_password"),
            "ssl_mode": os.getenv("POSTGRES_SSL_MODE", "prefer"),
        }
    
    def test_postgresql_specific_features(self, config):
        """Test PostgreSQL-specific features."""
        database = initialize_database(config, validate_connection=True)
        database.create_db_and_tables()
        
        with Session(database.engine) as session:
            # Test PostgreSQL version query
            result = session.exec("SELECT version()").first()
            assert "PostgreSQL" in result[0]
            
            # Test connection count query
            result = session.exec(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            ).first()
            assert isinstance(result[0], int)
            assert result[0] >= 1  # At least our connection
    
    def test_postgresql_ssl_connection(self, config):
        """Test PostgreSQL SSL connection modes."""
        ssl_modes = ["disable", "prefer", "require"]
        
        for ssl_mode in ssl_modes:
            test_config = config.copy()
            test_config["ssl_mode"] = ssl_mode
            
            try:
                database = DatabaseFactory.create_database(test_config)
                success, error = database.test_connection()
                
                # Connection should work (may fail for require if SSL not available)
                if ssl_mode == "require" and not success:
                    pytest.skip(f"SSL required but not available: {error}")
                else:
                    assert success, f"Connection failed with SSL mode {ssl_mode}: {error}"
                
                database.close()
            except Exception as e:
                if ssl_mode == "require":
                    pytest.skip(f"SSL required but not available: {e}")
                else:
                    raise
    
    def test_postgresql_connection_pooling(self, config):
        """Test PostgreSQL connection pooling."""
        pool_config = config.copy()
        pool_config.update({
            "pool_size": 5,
            "max_overflow": 10,
            "pool_recycle": 3600
        })
        
        database = initialize_database(pool_config, validate_connection=True)
        
        # Test multiple connections
        sessions = []
        try:
            for i in range(8):  # More than pool_size but less than pool_size + max_overflow
                session = Session(database.engine)
                sessions.append(session)
                
                result = session.exec(select(1)).first()
                assert result == 1
        
        finally:
            for session in sessions:
                session.close()


class TestMySQLManual(DatabaseE2ETestBase):
    """Manual E2E tests for MySQL/MariaDB."""
    
    @pytest.fixture
    def config(self):
        """MySQL configuration for testing."""
        return {
            "type": "mysql",
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": os.getenv("MYSQL_PORT", "3306"),
            "name": os.getenv("MYSQL_DATABASE", "intentverse_test"),
            "user": os.getenv("MYSQL_USER", "intentverse"),
            "password": os.getenv("MYSQL_PASSWORD", "intentverse_password"),
            "charset": "utf8mb4",
        }
    
    def test_mysql_specific_features(self, config):
        """Test MySQL-specific features."""
        database = initialize_database(config, validate_connection=True)
        database.create_db_and_tables()
        
        with Session(database.engine) as session:
            # Test MySQL version query
            result = session.exec("SELECT VERSION()").first()
            version = result[0]
            assert any(db in version.lower() for db in ["mysql", "mariadb"])
            
            # Test connection count query
            result = session.exec("SHOW STATUS LIKE 'Threads_connected'").first()
            assert result[0] == "Threads_connected"
            assert int(result[1]) >= 1  # At least our connection
    
    def test_mysql_charset_handling(self, config):
        """Test MySQL charset handling."""
        charsets = ["utf8", "utf8mb4"]
        
        for charset in charsets:
            test_config = config.copy()
            test_config["charset"] = charset
            
            database = DatabaseFactory.create_database(test_config)
            success, error = database.test_connection()
            assert success, f"Connection failed with charset {charset}: {error}"
            
            database.close()
    
    def test_mysql_emoji_support(self, config):
        """Test MySQL emoji support with utf8mb4."""
        utf8mb4_config = config.copy()
        utf8mb4_config["charset"] = "utf8mb4"
        
        database = initialize_database(utf8mb4_config, validate_connection=True)
        database.create_db_and_tables()
        
        with Session(database.engine) as session:
            # Test emoji in username and email
            emoji_user = User(username="test_user_😀", email="emoji😀@example.com")
            session.add(emoji_user)
            session.commit()
            session.refresh(emoji_user)
            
            # Verify emoji was stored correctly
            found_user = session.exec(
                select(User).where(User.username == "test_user_😀")
            ).first()
            assert found_user is not None
            assert found_user.username == "test_user_😀"
            assert found_user.email == "emoji😀@example.com"
    
    def test_mysql_connection_pooling(self, config):
        """Test MySQL connection pooling."""
        pool_config = config.copy()
        pool_config.update({
            "pool_size": 5,
            "max_overflow": 10,
            "pool_recycle": 3600
        })
        
        database = initialize_database(pool_config, validate_connection=True)
        
        # Test multiple connections
        sessions = []
        try:
            for i in range(8):  # More than pool_size but less than pool_size + max_overflow
                session = Session(database.engine)
                sessions.append(session)
                
                result = session.exec(select(1)).first()
                assert result == 1
        
        finally:
            for session in sessions:
                session.close()


class TestCloudDatabasesManual(DatabaseE2ETestBase):
    """Manual E2E tests for cloud databases (AWS RDS, Google Cloud SQL, etc.)."""
    
    @pytest.mark.skipif(
        not os.getenv("CLOUD_DB_TEST_ENABLED"),
        reason="Cloud database testing not enabled"
    )
    def test_aws_rds_postgresql(self):
        """Test AWS RDS PostgreSQL connection."""
        config = {
            "type": "postgresql",
            "host": os.getenv("AWS_RDS_HOST"),
            "port": os.getenv("AWS_RDS_PORT", "5432"),
            "name": os.getenv("AWS_RDS_DB"),
            "user": os.getenv("AWS_RDS_USER"),
            "password": os.getenv("AWS_RDS_PASSWORD"),
            "ssl_mode": "require",
        }
        
        # Skip if required env vars not set
        if not all([config["host"], config["name"], config["user"], config["password"]]):
            pytest.skip("AWS RDS credentials not configured")
        
        self.test_basic_connectivity(config)
        self.test_crud_operations(config)
    
    @pytest.mark.skipif(
        not os.getenv("CLOUD_DB_TEST_ENABLED"),
        reason="Cloud database testing not enabled"
    )
    def test_aws_rds_mysql(self):
        """Test AWS RDS MySQL connection."""
        config = {
            "type": "mysql",
            "host": os.getenv("AWS_RDS_MYSQL_HOST"),
            "port": os.getenv("AWS_RDS_MYSQL_PORT", "3306"),
            "name": os.getenv("AWS_RDS_MYSQL_DB"),
            "user": os.getenv("AWS_RDS_MYSQL_USER"),
            "password": os.getenv("AWS_RDS_MYSQL_PASSWORD"),
            "ssl_mode": "REQUIRED",
        }
        
        # Skip if required env vars not set
        if not all([config["host"], config["name"], config["user"], config["password"]]):
            pytest.skip("AWS RDS MySQL credentials not configured")
        
        self.test_basic_connectivity(config)
        self.test_crud_operations(config)


if __name__ == "__main__":
    print("Manual E2E Database Tests")
    print("=" * 50)
    print()
    print("These tests require actual database instances.")
    print("Set up databases using Docker Compose:")
    print()
    print("PostgreSQL:")
    print("  docker-compose -f docs/deploy/docker-compose.postgresql.yml up -d")
    print("  pytest tests/test_database_e2e_manual.py::TestPostgreSQLManual -v")
    print()
    print("MySQL:")
    print("  docker-compose -f docs/deploy/docker-compose.mysql.yml up -d")
    print("  pytest tests/test_database_e2e_manual.py::TestMySQLManual -v")
    print()
    print("Run all manual tests:")
    print("  pytest tests/test_database_e2e_manual.py -v")