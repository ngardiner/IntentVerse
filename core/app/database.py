from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import text
import logging
import os

# The path to our SQLite database file.
# It will be created in the root of the 'core' directory.
DATABASE_URL = "sqlite:///./intentverse.db"

# Create the database engine. The 'connect_args' is needed for SQLite
# to allow it to be used by multiple threads, which FastAPI does.
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

def create_db_and_tables():
    """
    Creates the database file and all tables defined by our SQLModel classes.
    For development, we'll recreate the database if schema changes are detected.
    """
    logging.info("Initializing database and creating tables...")
    
    # Import all models to ensure they're registered with SQLModel
    from .models import User, UserGroup, UserGroupLink, AuditLog
    
    # Check if database exists and has the expected schema
    db_file = "./intentverse.db"
    needs_recreation = False
    
    if os.path.exists(db_file):
        # Check if we need to recreate due to schema changes
        try:
            # Test if the current schema matches by trying to access new columns
            with Session(engine) as session:
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
    SQLModel.metadata.create_all(engine)
    logging.info("Database and tables initialized.")

def get_session():
    """
    Dependency function that provides a database session to the API endpoints.
    """
    with Session(engine) as session:
        yield session