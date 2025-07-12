#!/usr/bin/env python3
"""
Database migration CLI tool for IntentVerse.

This script provides manual migration commands as a fallback when automatic
migrations fail or for specific migration scenarios.

Usage:
    python -m app.migration_cli status
    python -m app.migration_cli migrate
    python -m app.migration_cli migrate --target 1.1.0
    python -m app.migration_cli rollback --version 1.1.0
    python -m app.migration_cli validate
"""

import argparse
import logging
import sys
from typing import Optional

from .config import Config
from .database import initialize_database, get_database
from .database.migrations import get_migration_manager
from .logging_config import setup_logging


def setup_cli_logging():
    """Setup logging for CLI usage."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def get_database_instance():
    """Get initialized database instance."""
    config = Config.get_database_config()
    return initialize_database(config)


def cmd_status(args):
    """Show migration status."""
    print("=== Database Migration Status ===")
    
    try:
        database = get_database_instance()
        status = database.get_migration_status()
        
        print(f"Current Version: {status['current_version'] or 'None (fresh database)'}")
        print(f"Pending Migrations: {status['pending_migrations']}")
        
        if status['pending_migration_list']:
            print("\nPending migrations:")
            for migration in status['pending_migration_list']:
                print(f"  - {migration}")
        
        validation = status['validation']
        print(f"\nValidation Status: {'✓ Valid' if validation['valid'] else '✗ Invalid'}")
        print(f"Applied Migrations: {validation['applied_migrations']}")
        
        if validation['issues']:
            print("\nValidation Issues:")
            for issue in validation['issues']:
                print(f"  - {issue}")
                
    except Exception as e:
        print(f"Error getting migration status: {e}")
        return 1
    
    return 0


def cmd_migrate(args):
    """Run database migrations."""
    target_version = getattr(args, 'target', None)
    
    if target_version:
        print(f"=== Migrating to version {target_version} ===")
    else:
        print("=== Migrating to latest version ===")
    
    try:
        database = get_database_instance()
        migration_manager = get_migration_manager(database)
        
        if target_version:
            success = migration_manager.migrate_to_version(target_version)
        else:
            success = migration_manager.migrate_to_latest()
        
        if success:
            print("✓ Migration completed successfully")
            return 0
        else:
            print("✗ Migration failed")
            return 1
            
    except Exception as e:
        print(f"Error during migration: {e}")
        return 1


def cmd_rollback(args):
    """Rollback a migration."""
    version = args.version
    
    print(f"=== Rolling back migration {version} ===")
    print("WARNING: This is a destructive operation!")
    
    # Confirm with user
    confirm = input("Are you sure you want to rollback? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Rollback cancelled")
        return 0
    
    try:
        database = get_database_instance()
        migration_manager = get_migration_manager(database)
        
        # Find the migration to rollback
        migration = None
        for m in migration_manager.migrations:
            if m.version == version:
                migration = m
                break
        
        if not migration:
            print(f"Migration {version} not found")
            return 1
        
        success = migration_manager.rollback_migration(migration)
        
        if success:
            print("✓ Rollback completed successfully")
            return 0
        else:
            print("✗ Rollback failed")
            return 1
            
    except Exception as e:
        print(f"Error during rollback: {e}")
        return 1


def cmd_validate(args):
    """Validate migration integrity."""
    print("=== Validating Migration Integrity ===")
    
    try:
        database = get_database_instance()
        migration_manager = get_migration_manager(database)
        
        validation = migration_manager.validate_migrations()
        
        print(f"Validation Status: {'✓ Valid' if validation['valid'] else '✗ Invalid'}")
        print(f"Applied Migrations: {validation['applied_migrations']}")
        print(f"Checksum Mismatches: {validation['checksum_mismatches']}")
        
        if validation['issues']:
            print("\nIssues Found:")
            for issue in validation['issues']:
                print(f"  - {issue}")
            return 1
        else:
            print("\n✓ All migrations are valid")
            return 0
            
    except Exception as e:
        print(f"Error during validation: {e}")
        return 1


def cmd_list(args):
    """List all available migrations."""
    print("=== Available Migrations ===")
    
    try:
        database = get_database_instance()
        migration_manager = get_migration_manager(database)
        
        current_version = migration_manager.get_current_version()
        
        for migration in migration_manager.migrations:
            status = "✓ Applied" if current_version and migration.version <= current_version else "○ Pending"
            print(f"{status} {migration.version}: {migration.name}")
            if migration.description:
                print(f"    {migration.description}")
        
        return 0
        
    except Exception as e:
        print(f"Error listing migrations: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="IntentVerse Database Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.migration_cli status              # Show migration status
  python -m app.migration_cli migrate             # Migrate to latest
  python -m app.migration_cli migrate --target 1.1.0  # Migrate to specific version
  python -m app.migration_cli rollback --version 1.1.0  # Rollback migration
  python -m app.migration_cli validate            # Validate migrations
  python -m app.migration_cli list                # List all migrations
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show migration status')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run migrations')
    migrate_parser.add_argument('--target', help='Target version to migrate to')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback a migration')
    rollback_parser.add_argument('--version', required=True, help='Version to rollback')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate migration integrity')
    
    # List command
    subparsers.add_parser('list', help='List all available migrations')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_cli_logging()
    
    # Route to appropriate command
    commands = {
        'status': cmd_status,
        'migrate': cmd_migrate,
        'rollback': cmd_rollback,
        'validate': cmd_validate,
        'list': cmd_list,
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())