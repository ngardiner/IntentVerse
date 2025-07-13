"""
Database migration scripts for IntentVerse.

This module contains all the migration scripts that define schema changes
across different versions of the application.
"""

import logging
from typing import List
from sqlmodel import Session, text
from sqlalchemy.exc import SQLAlchemyError

from .migrations import Migration
from .base import DatabaseInterface


class InitialSchemaMigration(Migration):
    """
    Initial schema migration - creates all base tables.
    This migration represents the current state of the database schema.
    """
    
    def __init__(self):
        super().__init__(
            version="1.0.0",
            name="initial_schema",
            description="Create initial database schema with all base tables"
        )
    
    def upgrade(self, session: Session, database: DatabaseInterface) -> None:
        """Create all initial tables."""
        from ..models import (
            User, UserGroup, UserGroupLink, AuditLog, ModuleConfiguration,
            ContentPackVariable, Role, Permission, UserRoleLink, GroupRoleLink,
            RolePermissionLink, RefreshToken, MCPServerInfo, MCPToolInfo,
            ModuleCategory
        )
        from sqlmodel import SQLModel
        
        # Create all tables defined in models
        SQLModel.metadata.create_all(database.engine)
        logging.info("Created initial database schema")
    
    def downgrade(self, session: Session, database: DatabaseInterface) -> None:
        """Drop all tables (dangerous - only for development)."""
        from sqlmodel import SQLModel
        
        # This is a destructive operation - only allow in development
        import os
        if os.getenv("INTENTVERSE_ALLOW_DESTRUCTIVE_MIGRATIONS") != "true":
            raise RuntimeError(
                "Destructive migration not allowed. Set INTENTVERSE_ALLOW_DESTRUCTIVE_MIGRATIONS=true to enable."
            )
        
        SQLModel.metadata.drop_all(database.engine)
        logging.warning("Dropped all database tables")


class AddEmailFieldMigration(Migration):
    """
    Migration to add email field to User table.
    This represents the schema change that added email support.
    """
    
    def __init__(self):
        super().__init__(
            version="1.1.0",
            name="add_email_field",
            description="Add email field to User table"
        )
    
    def upgrade(self, session: Session, database: DatabaseInterface) -> None:
        """Add email field to User table."""
        db_type = database.config.get("type", "sqlite").lower()
        
        try:
            if db_type == "sqlite":
                # SQLite doesn't support ALTER COLUMN, so we need to check if column exists
                result = session.exec(text("PRAGMA table_info(user)"))
                columns = [row[1] for row in result]
                
                if "email" not in columns:
                    session.exec(text("ALTER TABLE user ADD COLUMN email VARCHAR"))
                    session.commit()
                    logging.info("Added email column to user table (SQLite)")
                else:
                    logging.info("Email column already exists in user table (SQLite)")
                    
            elif db_type == "postgresql":
                # Check if column exists
                result = session.exec(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'user' AND column_name = 'email'
                """))
                
                if not result.first():
                    session.exec(text("ALTER TABLE \"user\" ADD COLUMN email VARCHAR"))
                    session.exec(text("CREATE INDEX ix_user_email ON \"user\" (email)"))
                    session.commit()
                    logging.info("Added email column to user table (PostgreSQL)")
                else:
                    logging.info("Email column already exists in user table (PostgreSQL)")
                    
            elif db_type in ["mysql", "mariadb"]:
                # Check if column exists
                result = session.exec(text("""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'user' AND COLUMN_NAME = 'email'
                """))
                
                if not result.first():
                    session.exec(text("ALTER TABLE user ADD COLUMN email VARCHAR(255)"))
                    session.exec(text("CREATE INDEX ix_user_email ON user (email)"))
                    session.commit()
                    logging.info("Added email column to user table (MySQL/MariaDB)")
                else:
                    logging.info("Email column already exists in user table (MySQL/MariaDB)")
                    
        except SQLAlchemyError as e:
            logging.error(f"Failed to add email field: {e}")
            raise
    
    def downgrade(self, session: Session, database: DatabaseInterface) -> None:
        """Remove email field from User table."""
        db_type = database.config.get("type", "sqlite").lower()
        
        try:
            if db_type == "sqlite":
                # SQLite doesn't support DROP COLUMN easily, would need table recreation
                logging.warning("SQLite doesn't support dropping columns easily - skipping downgrade")
                
            elif db_type == "postgresql":
                session.exec(text("DROP INDEX IF EXISTS ix_user_email"))
                session.exec(text("ALTER TABLE \"user\" DROP COLUMN IF EXISTS email"))
                session.commit()
                logging.info("Removed email column from user table (PostgreSQL)")
                
            elif db_type in ["mysql", "mariadb"]:
                session.exec(text("DROP INDEX IF EXISTS ix_user_email ON user"))
                session.exec(text("ALTER TABLE user DROP COLUMN IF EXISTS email"))
                session.commit()
                logging.info("Removed email column from user table (MySQL/MariaDB)")
                
        except SQLAlchemyError as e:
            logging.error(f"Failed to remove email field: {e}")
            raise


class AddRefreshTokenTableMigration(Migration):
    """
    Migration to add RefreshToken table for JWT authentication.
    """
    
    def __init__(self):
        super().__init__(
            version="1.1.1",
            name="add_refresh_token_table",
            description="Add RefreshToken table for JWT authentication"
        )
    
    def upgrade(self, session: Session, database: DatabaseInterface) -> None:
        """Create RefreshToken table."""
        from ..models import RefreshToken
        
        # Create the RefreshToken table
        RefreshToken.metadata.create_all(database.engine)
        logging.info("Created RefreshToken table")
    
    def downgrade(self, session: Session, database: DatabaseInterface) -> None:
        """Drop RefreshToken table."""
        db_type = database.config.get("type", "sqlite").lower()
        
        try:
            if db_type == "postgresql":
                session.exec(text("DROP TABLE IF EXISTS refreshtoken"))
            else:
                session.exec(text("DROP TABLE IF EXISTS refreshtoken"))
            session.commit()
            logging.info("Dropped RefreshToken table")
        except SQLAlchemyError as e:
            logging.error(f"Failed to drop RefreshToken table: {e}")
            raise


class AddMCPTablesMigration(Migration):
    """
    Migration to add MCP (Model Context Protocol) related tables.
    """
    
    def __init__(self):
        super().__init__(
            version="1.2.0",
            name="add_mcp_tables",
            description="Add MCP server and tool tracking tables"
        )
    
    def upgrade(self, session: Session, database: DatabaseInterface) -> None:
        """Create MCP tables."""
        from ..models import MCPServerInfo, MCPToolInfo
        
        # Create the MCP tables
        MCPServerInfo.metadata.create_all(database.engine)
        MCPToolInfo.metadata.create_all(database.engine)
        logging.info("Created MCP tables")
    
    def downgrade(self, session: Session, database: DatabaseInterface) -> None:
        """Drop MCP tables."""
        try:
            session.exec(text("DROP TABLE IF EXISTS mcptoolinfo"))
            session.exec(text("DROP TABLE IF EXISTS mcpserverinfo"))
            session.commit()
            logging.info("Dropped MCP tables")
        except SQLAlchemyError as e:
            logging.error(f"Failed to drop MCP tables: {e}")
            raise


class AddModuleCategoriesMigration(Migration):
    """
    Migration to add module categorization support.
    """
    
    def __init__(self):
        super().__init__(
            version="1.2.2",
            name="add_module_categories",
            description="Add module categorization support with category management tables"
        )
    
    def upgrade(self, session: Session, database: DatabaseInterface) -> None:
        """Create module categories table and add default categories."""
        from ..models import ModuleCategory
        from sqlmodel import select
        
        # Create the ModuleCategory table
        ModuleCategory.metadata.create_all(database.engine)
        
        # Add default categories
        default_categories = [
            ("core", "Core", "Essential system modules", True, 1),
            ("data", "Data", "Data management and storage modules", True, 2),
            ("communication", "Communication", "Communication and messaging modules", True, 3),
            ("automation", "Automation", "Automation and workflow modules", True, 4),
            ("integration", "Integration", "Third-party integration modules", True, 5),
            ("utility", "Utility", "Utility and helper modules", True, 6),
        ]
        
        # Use SQLModel to insert categories (database-agnostic)
        for name, display_name, description, is_enabled, sort_order in default_categories:
            # Check if category already exists
            existing = session.exec(
                select(ModuleCategory).where(ModuleCategory.name == name)
            ).first()
            
            if not existing:
                category = ModuleCategory(
                    name=name,
                    display_name=display_name,
                    description=description,
                    is_enabled=is_enabled,
                    sort_order=sort_order
                )
                session.add(category)
        
        session.commit()
        logging.info("Created ModuleCategory table and added default categories")
    
    def downgrade(self, session: Session, database: DatabaseInterface) -> None:
        """Drop module categories table."""
        try:
            # Use SQLModel metadata for database-agnostic table dropping
            ModuleCategory.metadata.drop_all(database.engine, tables=[ModuleCategory.__table__])
            logging.info("Dropped module_categories table")
        except SQLAlchemyError as e:
            logging.error(f"Failed to drop module_categories table: {e}")
            raise


def get_all_migrations() -> List[Migration]:
    """
    Get all available migrations in order.
    
    Returns:
        List of all migration instances
    """
    return [
        InitialSchemaMigration(),
        AddEmailFieldMigration(),
        AddRefreshTokenTableMigration(),
        AddMCPTablesMigration(),
        AddModuleCategoriesMigration(),
    ]