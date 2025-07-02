from sqlmodel import create_engine, SQLModel, Session, select
from sqlalchemy import text
import logging
import os

# The path to our SQLite database file.
# It will be created in the root of the 'core' directory.
DATABASE_URL = "sqlite:///./intentverse.db"

# Create the database engine. The 'connect_args' is needed for SQLite
# to allow it to be used by multiple threads, which FastAPI does.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables():
    """
    Creates the database file and all tables defined by our SQLModel classes.
    For development, we'll recreate the database if schema changes are detected.
    """
    # Use the current engine value (important for testing when engine is overridden)
    current_engine = globals()["engine"]

    logging.info("Initializing database and creating tables...")

    # Import all models to ensure they're registered with SQLModel
    from .models import User, UserGroup, UserGroupLink, AuditLog, ModuleConfiguration, ContentPackVariable

    # Import RBAC models to ensure they're registered
    from .models import (
        Role,
        Permission,
        UserRoleLink,
        GroupRoleLink,
        RolePermissionLink,
    )

    # Check if this is an in-memory database (used for testing)
    is_memory_db = str(current_engine.url).startswith("sqlite:///:memory:")

    if not is_memory_db:
        # Only check for file recreation if using a file-based database
        db_file = "./intentverse.db"
        needs_recreation = False

        if os.path.exists(db_file):
            # Check if we need to recreate due to schema changes
            try:
                # Test if the current schema matches by trying to access new columns
                with Session(current_engine) as session:
                    # Try to query a user with the new email field
                    test_query = select(User.id, User.email).limit(1)
                    session.exec(test_query).first()

                    # Try to query the audit log table
                    test_audit_query = select(AuditLog.id).limit(1)
                    session.exec(test_audit_query).first()

            except Exception as e:
                logging.warning(f"Database schema appears outdated: {e}")
                logging.info("Recreating database...")
                needs_recreation = True

        if needs_recreation:
            # Remove the old database file
            if os.path.exists(db_file):
                os.remove(db_file)
                logging.info("Removed old database file")

    # Create all tables
    SQLModel.metadata.create_all(current_engine)
    logging.info("Database and tables initialized.")


def get_session():
    """
    Dependency function that provides a database session to the API endpoints.
    """
    with Session(engine) as session:
        yield session
