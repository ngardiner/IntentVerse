"""
Database migration system for IntentVerse.

This module provides a framework for managing database schema changes across
different database engines (SQLite, PostgreSQL, MySQL).

Features:
- Database version tracking
- Automatic migrations on startup
- Manual migration commands as fallback
- Rollback capability for failed migrations
- Cross-database compatibility
"""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from sqlmodel import Session, SQLModel, Field, select, text
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.exc import SQLAlchemyError

from .base import DatabaseInterface


class DatabaseVersion(SQLModel, table=True):
    """
    Tracks the current database schema version and migration history.
    """
    __tablename__ = "database_version"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    version: str = Field(index=True, unique=True)  # e.g., "1.0.0", "1.1.0", "1.2.0"
    migration_name: str = Field(index=True)  # e.g., "initial_schema", "add_email_field"
    applied_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    checksum: Optional[str] = Field(default=None)  # For migration integrity verification
    execution_time_ms: Optional[int] = Field(default=None)  # Migration execution time
    success: bool = Field(default=True, index=True)
    error_message: Optional[str] = Field(default=None)


class Migration(ABC):
    """
    Abstract base class for database migrations.
    """
    
    def __init__(self, version: str, name: str, description: str = ""):
        self.version = version
        self.name = name
        self.description = description
        self.checksum = self._calculate_checksum()
    
    @abstractmethod
    def upgrade(self, session: Session, database: DatabaseInterface) -> None:
        """
        Apply the migration (upgrade).
        
        Args:
            session: Database session
            database: Database interface for engine-specific operations
        """
        pass
    
    @abstractmethod
    def downgrade(self, session: Session, database: DatabaseInterface) -> None:
        """
        Rollback the migration (downgrade).
        
        Args:
            session: Database session
            database: Database interface for engine-specific operations
        """
        pass
    
    def _calculate_checksum(self) -> str:
        """Calculate a checksum for migration integrity verification."""
        import hashlib
        content = f"{self.version}:{self.name}:{self.description}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def __str__(self) -> str:
        return f"Migration({self.version}, {self.name})"


class MigrationManager:
    """
    Manages database migrations across different database engines.
    """
    
    def __init__(self, database: DatabaseInterface):
        self.database = database
        self.migrations: List[Migration] = []
        self._register_migrations()
    
    def _register_migrations(self) -> None:
        """Register all available migrations."""
        # Import and register migrations
        from .migration_scripts import get_all_migrations
        self.migrations = get_all_migrations()
        
        # Sort migrations by version
        self.migrations.sort(key=lambda m: self._version_to_tuple(m.version))
        
        logging.info(f"Registered {len(self.migrations)} migrations")
    
    def _version_to_tuple(self, version: str) -> tuple:
        """Convert version string to tuple for sorting."""
        try:
            return tuple(map(int, version.split('.')))
        except ValueError:
            # Fallback for non-standard version formats
            return (0, 0, 0)
    
    def _ensure_version_table_exists(self) -> None:
        """Ensure the database_version table exists."""
        try:
            # Create the version tracking table if it doesn't exist
            DatabaseVersion.metadata.create_all(self.database.engine)
            logging.debug("Database version table ensured")
        except Exception as e:
            logging.error(f"Failed to create version table: {e}")
            raise
    
    def get_current_version(self) -> Optional[str]:
        """Get the current database version."""
        try:
            self._ensure_version_table_exists()
            
            with Session(self.database.engine) as session:
                # Get the latest successfully applied migration
                latest = session.exec(
                    select(DatabaseVersion)
                    .where(DatabaseVersion.success == True)
                    .order_by(DatabaseVersion.applied_at.desc())
                ).first()
                
                return latest.version if latest else None
        except Exception as e:
            logging.warning(f"Could not determine current database version: {e}")
            return None
    
    def get_migration_history(self) -> List[DatabaseVersion]:
        """Get the complete migration history."""
        try:
            self._ensure_version_table_exists()
            
            with Session(self.database.engine) as session:
                return list(session.exec(
                    select(DatabaseVersion)
                    .order_by(DatabaseVersion.applied_at.desc())
                ))
        except Exception as e:
            logging.error(f"Failed to get migration history: {e}")
            return []
    
    def get_pending_migrations(self, target_version: Optional[str] = None) -> List[Migration]:
        """
        Get migrations that need to be applied.
        
        Args:
            target_version: Target version to migrate to (None for latest)
            
        Returns:
            List of pending migrations
        """
        current_version = self.get_current_version()
        
        if current_version is None:
            # No migrations applied yet, start from beginning
            pending = self.migrations[:]
        else:
            # Find migrations newer than current version
            current_tuple = self._version_to_tuple(current_version)
            pending = [
                m for m in self.migrations 
                if self._version_to_tuple(m.version) > current_tuple
            ]
        
        if target_version:
            # Filter to only migrations up to target version
            target_tuple = self._version_to_tuple(target_version)
            pending = [
                m for m in pending 
                if self._version_to_tuple(m.version) <= target_tuple
            ]
        
        return pending
    
    def apply_migration(self, migration: Migration) -> bool:
        """
        Apply a single migration.
        
        Args:
            migration: Migration to apply
            
        Returns:
            True if successful, False otherwise
        """
        start_time = datetime.utcnow()
        
        try:
            self._ensure_version_table_exists()
            
            with Session(self.database.engine) as session:
                # Check if migration was already applied
                existing = session.exec(
                    select(DatabaseVersion)
                    .where(DatabaseVersion.version == migration.version)
                    .where(DatabaseVersion.migration_name == migration.name)
                    .where(DatabaseVersion.success == True)
                ).first()
                
                if existing:
                    logging.info(f"Migration {migration} already applied, skipping")
                    return True
                
                logging.info(f"Applying migration: {migration}")
                
                try:
                    # Apply the migration
                    migration.upgrade(session, self.database)
                    session.commit()
                    
                    # Record successful migration
                    execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    version_record = DatabaseVersion(
                        version=migration.version,
                        migration_name=migration.name,
                        applied_at=datetime.utcnow(),
                        checksum=migration.checksum,
                        execution_time_ms=execution_time,
                        success=True
                    )
                    session.add(version_record)
                    session.commit()
                    
                    logging.info(f"Successfully applied migration {migration} in {execution_time}ms")
                    return True
                    
                except Exception as e:
                    session.rollback()
                    
                    # Record failed migration
                    execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    version_record = DatabaseVersion(
                        version=migration.version,
                        migration_name=migration.name,
                        applied_at=datetime.utcnow(),
                        checksum=migration.checksum,
                        execution_time_ms=execution_time,
                        success=False,
                        error_message=str(e)
                    )
                    session.add(version_record)
                    session.commit()
                    
                    logging.error(f"Failed to apply migration {migration}: {e}")
                    raise
                    
        except Exception as e:
            logging.error(f"Migration {migration} failed: {e}")
            return False
    
    def migrate_to_latest(self) -> bool:
        """
        Migrate database to the latest version.
        
        Returns:
            True if all migrations successful, False otherwise
        """
        pending = self.get_pending_migrations()
        
        if not pending:
            logging.info("Database is already at the latest version")
            return True
        
        logging.info(f"Applying {len(pending)} pending migrations")
        
        for migration in pending:
            if not self.apply_migration(migration):
                logging.error(f"Migration failed at {migration}, stopping")
                return False
        
        logging.info("All migrations applied successfully")
        return True
    
    def migrate_to_version(self, target_version: str) -> bool:
        """
        Migrate database to a specific version.
        
        Args:
            target_version: Target version to migrate to
            
        Returns:
            True if successful, False otherwise
        """
        pending = self.get_pending_migrations(target_version)
        
        if not pending:
            logging.info(f"Database is already at version {target_version} or later")
            return True
        
        logging.info(f"Migrating to version {target_version}")
        
        for migration in pending:
            if not self.apply_migration(migration):
                logging.error(f"Migration failed at {migration}, stopping")
                return False
        
        logging.info(f"Successfully migrated to version {target_version}")
        return True
    
    def rollback_migration(self, migration: Migration) -> bool:
        """
        Rollback a specific migration.
        
        Args:
            migration: Migration to rollback
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with Session(self.database.engine) as session:
                logging.info(f"Rolling back migration: {migration}")
                
                try:
                    # Apply the rollback
                    migration.downgrade(session, self.database)
                    session.commit()
                    
                    # Remove the migration record
                    session.exec(
                        text("DELETE FROM database_version WHERE version = :version AND migration_name = :name"),
                        {"version": migration.version, "name": migration.name}
                    )
                    session.commit()
                    
                    logging.info(f"Successfully rolled back migration {migration}")
                    return True
                    
                except Exception as e:
                    session.rollback()
                    logging.error(f"Failed to rollback migration {migration}: {e}")
                    raise
                    
        except Exception as e:
            logging.error(f"Rollback of {migration} failed: {e}")
            return False
    
    def validate_migrations(self) -> Dict[str, Any]:
        """
        Validate the integrity of applied migrations.
        
        Returns:
            Validation report
        """
        report = {
            "valid": True,
            "issues": [],
            "applied_migrations": 0,
            "checksum_mismatches": 0
        }
        
        try:
            history = self.get_migration_history()
            report["applied_migrations"] = len([h for h in history if h.success])
            
            # Check for checksum mismatches
            for record in history:
                if not record.success:
                    continue
                    
                # Find the corresponding migration
                migration = next(
                    (m for m in self.migrations 
                     if m.version == record.version and m.name == record.migration_name), 
                    None
                )
                
                if migration and record.checksum != migration.checksum:
                    report["checksum_mismatches"] += 1
                    report["issues"].append(
                        f"Checksum mismatch for {record.version}:{record.migration_name}"
                    )
                    report["valid"] = False
            
        except Exception as e:
            report["valid"] = False
            report["issues"].append(f"Validation failed: {e}")
        
        return report


def get_migration_manager(database: DatabaseInterface) -> MigrationManager:
    """
    Get a migration manager instance for the given database.
    
    Args:
        database: Database interface
        
    Returns:
        MigrationManager instance
    """
    return MigrationManager(database)