from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime

class UserGroup(SQLModel, table=True):
    """
    Represents a user group in the database.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    users: List["User"] = Relationship(back_populates="groups", link_model="UserGroupLink")

class User(SQLModel, table=True):
    """
    Represents the User table in the database.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: Optional[str] = Field(default=None, index=True)
    full_name: Optional[str] = None
    hashed_password: str
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Relationships
    groups: List[UserGroup] = Relationship(back_populates="users", link_model="UserGroupLink")

class UserGroupLink(SQLModel, table=True):
    """
    Link table for many-to-many relationship between User and UserGroup.
    """
    user_id: Optional[int] = Field(
        default=None, foreign_key="user.id", primary_key=True
    )
    group_id: Optional[int] = Field(
        default=None, foreign_key="usergroup.id", primary_key=True
    )