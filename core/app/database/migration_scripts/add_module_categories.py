"""
Migration script to add module categorization support.
This migration adds category support to the module system.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_migration_info() -> Dict[str, Any]:
    """Get migration metadata."""
    return {
        "version": "1.2.0",
        "name": "add_module_categories",
        "description": "Add module categorization support with category management tables",
        "requires": [],
        "creates_tables": ["module_categories"],
        "modifies_tables": ["module_configurations"]
    }

def upgrade_sqlite(cursor) -> None:
    """Apply migration for SQLite database."""
    logger.info("Applying module categories migration for SQLite")
    
    # Create module_categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS module_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            description TEXT,
            is_enabled BOOLEAN DEFAULT FALSE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Add category column to module_configurations if it doesn't exist
    try:
        cursor.execute("ALTER TABLE module_configurations ADD COLUMN category VARCHAR(50) DEFAULT 'productivity'")
        logger.info("Added category column to module_configurations")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            logger.info("Category column already exists in module_configurations")
        else:
            raise
    
    # Insert default categories
    categories = [
        ('productivity', 'Productivity', 'General productivity and data management tools', True, 1),
        ('identity', 'Identity & Access', 'User management and authentication systems', False, 2),
        ('infrastructure', 'Infrastructure', 'Network infrastructure and system management', False, 3),
        ('cloud', 'Cloud Platforms', 'Cloud service provider integrations', False, 4),
        ('security', 'Security & Compliance', 'Security tools and compliance monitoring', False, 5),
        ('devops', 'Development & DevOps', 'Software development and DevOps tooling', False, 6),
        ('business', 'Business Applications', 'Enterprise business applications', False, 7)
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO module_categories 
        (name, display_name, description, is_enabled, sort_order) 
        VALUES (?, ?, ?, ?, ?)
    """, categories)
    
    # Update existing modules to have productivity category
    cursor.execute("""
        UPDATE module_configurations 
        SET category = 'productivity' 
        WHERE category IS NULL OR category = ''
    """)
    
    logger.info("Module categories migration completed for SQLite")

def upgrade_postgresql(cursor) -> None:
    """Apply migration for PostgreSQL database."""
    logger.info("Applying module categories migration for PostgreSQL")
    
    # Create module_categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS module_categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            description TEXT,
            is_enabled BOOLEAN DEFAULT FALSE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Add category column to module_configurations if it doesn't exist
    cursor.execute("""
        DO $$ 
        BEGIN 
            BEGIN
                ALTER TABLE module_configurations ADD COLUMN category VARCHAR(50) DEFAULT 'productivity';
            EXCEPTION
                WHEN duplicate_column THEN 
                    RAISE NOTICE 'Category column already exists in module_configurations';
            END;
        END $$;
    """)
    
    # Insert default categories
    cursor.execute("""
        INSERT INTO module_categories (name, display_name, description, is_enabled, sort_order) 
        VALUES 
            ('productivity', 'Productivity', 'General productivity and data management tools', TRUE, 1),
            ('identity', 'Identity & Access', 'User management and authentication systems', FALSE, 2),
            ('infrastructure', 'Infrastructure', 'Network infrastructure and system management', FALSE, 3),
            ('cloud', 'Cloud Platforms', 'Cloud service provider integrations', FALSE, 4),
            ('security', 'Security & Compliance', 'Security tools and compliance monitoring', FALSE, 5),
            ('devops', 'Development & DevOps', 'Software development and DevOps tooling', FALSE, 6),
            ('business', 'Business Applications', 'Enterprise business applications', FALSE, 7)
        ON CONFLICT (name) DO NOTHING
    """)
    
    # Update existing modules to have productivity category
    cursor.execute("""
        UPDATE module_configurations 
        SET category = 'productivity' 
        WHERE category IS NULL OR category = ''
    """)
    
    logger.info("Module categories migration completed for PostgreSQL")

def upgrade_mysql(cursor) -> None:
    """Apply migration for MySQL database."""
    logger.info("Applying module categories migration for MySQL")
    
    # Create module_categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS module_categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            description TEXT,
            is_enabled BOOLEAN DEFAULT FALSE,
            sort_order INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    
    # Check if category column exists before adding it
    cursor.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'module_configurations' 
        AND COLUMN_NAME = 'category'
    """)
    
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE module_configurations ADD COLUMN category VARCHAR(50) DEFAULT 'productivity'")
        logger.info("Added category column to module_configurations")
    else:
        logger.info("Category column already exists in module_configurations")
    
    # Insert default categories
    cursor.execute("""
        INSERT IGNORE INTO module_categories (name, display_name, description, is_enabled, sort_order) 
        VALUES 
            ('productivity', 'Productivity', 'General productivity and data management tools', TRUE, 1),
            ('identity', 'Identity & Access', 'User management and authentication systems', FALSE, 2),
            ('infrastructure', 'Infrastructure', 'Network infrastructure and system management', FALSE, 3),
            ('cloud', 'Cloud Platforms', 'Cloud service provider integrations', FALSE, 4),
            ('security', 'Security & Compliance', 'Security tools and compliance monitoring', FALSE, 5),
            ('devops', 'Development & DevOps', 'Software development and DevOps tooling', FALSE, 6),
            ('business', 'Business Applications', 'Enterprise business applications', FALSE, 7)
    """)
    
    # Update existing modules to have productivity category
    cursor.execute("""
        UPDATE module_configurations 
        SET category = 'productivity' 
        WHERE category IS NULL OR category = ''
    """)
    
    logger.info("Module categories migration completed for MySQL")

def downgrade_sqlite(cursor) -> None:
    """Rollback migration for SQLite database."""
    logger.info("Rolling back module categories migration for SQLite")
    
    # Remove category column (SQLite doesn't support DROP COLUMN easily)
    # We'll leave the column but clear the data
    cursor.execute("UPDATE module_configurations SET category = NULL")
    
    # Drop module_categories table
    cursor.execute("DROP TABLE IF EXISTS module_categories")
    
    logger.info("Module categories migration rollback completed for SQLite")

def downgrade_postgresql(cursor) -> None:
    """Rollback migration for PostgreSQL database."""
    logger.info("Rolling back module categories migration for PostgreSQL")
    
    # Remove category column
    cursor.execute("ALTER TABLE module_configurations DROP COLUMN IF EXISTS category")
    
    # Drop module_categories table
    cursor.execute("DROP TABLE IF EXISTS module_categories")
    
    logger.info("Module categories migration rollback completed for PostgreSQL")

def downgrade_mysql(cursor) -> None:
    """Rollback migration for MySQL database."""
    logger.info("Rolling back module categories migration for MySQL")
    
    # Remove category column
    cursor.execute("ALTER TABLE module_configurations DROP COLUMN category")
    
    # Drop module_categories table
    cursor.execute("DROP TABLE IF EXISTS module_categories")
    
    logger.info("Module categories migration rollback completed for MySQL")