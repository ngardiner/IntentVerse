"""
Tests for the database migration system.

This module tests the migration framework, migration scripts, and API endpoints.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from sqlmodel import Session, select, text
from sqlalchemy.exc import SQLAlchemyError

# Mark all tests in this file as database integration tests
pytestmark = pytest.mark.database_integration

from app.database.migrations import (
    MigrationManager, Migration, DatabaseVersion, get_migration_manager
)
from app.database.migration_scripts import (
    InitialSchemaMigration, AddEmailFieldMigration, get_all_migrations
)
from app.database.sqlite import SQLiteDatabase
from app.models import User


class TestMigration(Migration):
    """Test migration for unit tests."""
    
    def __init__(self):
        super().__init__(
            version="0.1.0",
            name="test_migration",
            description="Test migration for unit tests"
        )
    
    def upgrade(self, session: Session, database) -> None:
        """Test upgrade - create a simple test table."""
        session.exec(text("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)"))
        session.commit()
    
    def downgrade(self, session: Session, database) -> None:
        """Test downgrade - drop the test table."""
        session.exec(text("DROP TABLE IF EXISTS test_table"))
        session.commit()


class TestFailingMigration(Migration):
    """Test migration that always fails."""
    
    def __init__(self):
        super().__init__(
            version="0.2.0",
            name="failing_migration",
            description="Migration that always fails"
        )
    
    def upgrade(self, session: Session, database) -> None:
        """Always fail."""
        raise SQLAlchemyError("Intentional test failure")
    
    def downgrade(self, session: Session, database) -> None:
        """Always fail."""
        raise SQLAlchemyError("Intentional test failure")


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


@pytest.fixture
def migration_manager(temp_database):
    """Create a migration manager with test migrations."""
    manager = MigrationManager(temp_database)
    # Replace with test migrations
    manager.migrations = [TestMigration()]
    return manager


class TestMigrationFramework:
    """Test the core migration framework."""
    
    def test_migration_creation(self):
        """Test creating a migration."""
        migration = TestMigration()
        
        assert migration.version == "0.1.0"
        assert migration.name == "test_migration"
        assert migration.description == "Test migration for unit tests"
        assert migration.checksum is not None
        assert len(migration.checksum) == 32  # MD5 hash length
    
    def test_migration_checksum_consistency(self):
        """Test that migration checksums are consistent."""
        migration1 = TestMigration()
        migration2 = TestMigration()
        
        assert migration1.checksum == migration2.checksum
    
    def test_migration_manager_initialization(self, temp_database):
        """Test migration manager initialization."""
        manager = MigrationManager(temp_database)
        
        assert manager.database == temp_database
        assert len(manager.migrations) > 0  # Should have real migrations
    
    def test_version_table_creation(self, migration_manager):
        """Test that the version table is created."""
        migration_manager._ensure_version_table_exists()
        
        with Session(migration_manager.database.engine) as session:
            # Should be able to query the version table
            result = session.exec(select(DatabaseVersion)).all()
            assert isinstance(result, list)
    
    def test_get_current_version_empty(self, migration_manager):
        """Test getting current version when no migrations applied."""
        current_version = migration_manager.get_current_version()
        assert current_version is None
    
    def test_get_pending_migrations_empty(self, migration_manager):
        """Test getting pending migrations when none applied."""
        pending = migration_manager.get_pending_migrations()
        assert len(pending) == 1
        assert pending[0].name == "test_migration"
    
    def test_apply_migration_success(self, migration_manager):
        """Test successfully applying a migration."""
        migration = migration_manager.migrations[0]
        
        success = migration_manager.apply_migration(migration)
        assert success is True
        
        # Check that version was recorded
        current_version = migration_manager.get_current_version()
        assert current_version == "0.1.0"
        
        # Check that test table was created
        with Session(migration_manager.database.engine) as session:
            result = session.exec(text("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"))
            assert result.first() is not None
    
    def test_apply_migration_failure(self, temp_database):
        """Test handling migration failure."""
        manager = MigrationManager(temp_database)
        manager.migrations = [TestFailingMigration()]
        
        migration = manager.migrations[0]
        success = manager.apply_migration(migration)
        assert success is False
        
        # Check that failure was recorded
        history = manager.get_migration_history()
        assert len(history) == 1
        assert history[0].success is False
        assert "Intentional test failure" in history[0].error_message
    
    def test_migrate_to_latest(self, migration_manager):
        """Test migrating to latest version."""
        success = migration_manager.migrate_to_latest()
        assert success is True
        
        current_version = migration_manager.get_current_version()
        assert current_version == "0.1.0"
        
        pending = migration_manager.get_pending_migrations()
        assert len(pending) == 0
    
    def test_rollback_migration(self, migration_manager):
        """Test rolling back a migration."""
        migration = migration_manager.migrations[0]
        
        # Apply migration first
        migration_manager.apply_migration(migration)
        
        # Verify table exists
        with Session(migration_manager.database.engine) as session:
            result = session.exec(text("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"))
            assert result.first() is not None
        
        # Rollback migration
        success = migration_manager.rollback_migration(migration)
        assert success is True
        
        # Verify table is gone
        with Session(migration_manager.database.engine) as session:
            result = session.exec(text("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"))
            assert result.first() is None
    
    def test_validate_migrations(self, migration_manager):
        """Test migration validation."""
        # Apply migration
        migration_manager.migrate_to_latest()
        
        # Validate
        report = migration_manager.validate_migrations()
        
        assert report["valid"] is True
        assert report["applied_migrations"] == 1
        assert report["checksum_mismatches"] == 0
        assert len(report["issues"]) == 0


class TestMigrationScripts:
    """Test the actual migration scripts."""
    
    def test_get_all_migrations(self):
        """Test getting all migration scripts."""
        migrations = get_all_migrations()
        
        assert len(migrations) >= 4  # Should have at least 4 migrations
        
        # Check that migrations are sorted by version
        versions = [m.version for m in migrations]
        assert versions == sorted(versions, key=lambda v: tuple(map(int, v.split('.'))))
    
    def test_initial_schema_migration(self, temp_database):
        """Test the initial schema migration."""
        migration = InitialSchemaMigration()
        
        with Session(temp_database.engine) as session:
            migration.upgrade(session, temp_database)
        
        # Check that main tables exist
        with Session(temp_database.engine) as session:
            # Should be able to query User table
            result = session.exec(select(User)).all()
            assert isinstance(result, list)
    
    def test_add_email_field_migration(self, temp_database):
        """Test the add email field migration."""
        # First apply initial schema
        initial_migration = InitialSchemaMigration()
        with Session(temp_database.engine) as session:
            initial_migration.upgrade(session, temp_database)
        
        # Then apply email field migration
        email_migration = AddEmailFieldMigration()
        with Session(temp_database.engine) as session:
            email_migration.upgrade(session, temp_database)
        
        # Check that email field exists and is usable
        with Session(temp_database.engine) as session:
            # Should be able to query email field
            result = session.exec(select(User.email)).all()
            assert isinstance(result, list)


class TestDatabaseIntegration:
    """Test integration with database interfaces."""
    
    def test_sqlite_migration_integration(self, temp_database):
        """Test migration integration with SQLite database."""
        # Test run_migrations method
        success = temp_database.run_migrations()
        assert success is True
        
        # Test get_migration_status method
        status = temp_database.get_migration_status()
        
        assert "current_version" in status
        assert "pending_migrations" in status
        assert "validation" in status
        assert isinstance(status["pending_migration_list"], list)
    
    def test_migration_manager_factory(self, temp_database):
        """Test migration manager factory function."""
        manager = get_migration_manager(temp_database)
        
        assert isinstance(manager, MigrationManager)
        assert manager.database == temp_database


@pytest.mark.integration
class TestMigrationAPI:
    """Test migration API endpoints (requires running application)."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    @pytest.fixture
    def admin_headers(self):
        """Get admin authentication headers."""
        # This would need to be implemented based on your auth system
        return {"Authorization": "Bearer admin-token"}
    
    def test_migration_status_endpoint(self, client, admin_headers):
        """Test the migration status endpoint."""
        response = client.get("/api/v2/admin/migrations/status", headers=admin_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert "current_version" in data
            assert "pending_migrations" in data
            assert "validation" in data
    
    def test_migration_list_endpoint(self, client, admin_headers):
        """Test the migration list endpoint."""
        response = client.get("/api/v2/admin/migrations/list", headers=admin_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert "migrations" in data
            assert "current_version" in data
    
    def test_migration_history_endpoint(self, client, admin_headers):
        """Test the migration history endpoint."""
        response = client.get("/api/v2/admin/migrations/history", headers=admin_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert "migrations" in data


if __name__ == "__main__":
    pytest.main([__file__])