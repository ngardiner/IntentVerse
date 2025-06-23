from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy import JSON
from datetime import datetime

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

class UserGroup(SQLModel, table=True):
    """
    Represents a user group in the database.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    users: List["User"] = Relationship(back_populates="groups", link_model=UserGroupLink)

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
    groups: List[UserGroup] = Relationship(back_populates="users", link_model=UserGroupLink)

class AuditLog(SQLModel, table=True):
    """
    Represents audit log entries for tracking user actions.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    username: str = Field(index=True)  # Store username for easier querying
    action: str = Field(index=True)  # e.g., "login", "create_user", "delete_file", etc.
    resource_type: Optional[str] = Field(default=None, index=True)  # e.g., "user", "group", "file", "content_pack"
    resource_id: Optional[str] = Field(default=None, index=True)  # ID of the affected resource
    resource_name: Optional[str] = Field(default=None)  # Name/title of the affected resource
    details: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # Additional details as JSON
    ip_address: Optional[str] = Field(default=None, index=True)
    user_agent: Optional[str] = Field(default=None)
    status: str = Field(default="success", index=True)  # "success", "failure", "error"
    error_message: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationship to user (optional since user might be deleted)
    user: Optional[User] = Relationship()