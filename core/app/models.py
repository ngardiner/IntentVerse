from typing import Optional
from sqlmodel import Field, SQLModel

class User(SQLModel, table=True):
    """
    Represents the User table in the database.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str