from sqlmodel import create_engine, SQLModel, Session

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
    """
    print("Initializing database and creating tables...")
    # This command inspects the engine and creates the tables if they don't exist.
    SQLModel.metadata.create_all(engine)
    print("Database and tables initialized.")

def get_session():
    """
    Dependency function that provides a database session to the API endpoints.
    """
    with Session(engine) as session:
        yield session