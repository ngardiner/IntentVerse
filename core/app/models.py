from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy import JSON
from datetime import datetime


# Link tables for many-to-many relationships
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


class RolePermissionLink(SQLModel, table=True):
    """
    Link table for many-to-many relationship between Role and Permission.
    """

    role_id: Optional[int] = Field(
        default=None, foreign_key="role.id", primary_key=True
    )
    permission_id: Optional[int] = Field(
        default=None, foreign_key="permission.id", primary_key=True
    )


class UserRoleLink(SQLModel, table=True):
    """
    Link table for many-to-many relationship between User and Role.
    """

    user_id: Optional[int] = Field(
        default=None, foreign_key="user.id", primary_key=True
    )
    role_id: Optional[int] = Field(
        default=None, foreign_key="role.id", primary_key=True
    )


class GroupRoleLink(SQLModel, table=True):
    """
    Link table for many-to-many relationship between UserGroup and Role.
    """

    group_id: Optional[int] = Field(
        default=None, foreign_key="usergroup.id", primary_key=True
    )
    role_id: Optional[int] = Field(
        default=None, foreign_key="role.id", primary_key=True
    )


class Permission(SQLModel, table=True):
    """
    Represents a permission in the RBAC system.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        index=True, unique=True
    )  # e.g., "users.create", "filesystem.read", "admin.all"
    description: Optional[str] = None
    resource_type: Optional[str] = Field(
        default=None, index=True
    )  # e.g., "user", "filesystem", "database"
    action: Optional[str] = Field(
        default=None, index=True
    )  # e.g., "create", "read", "write", "delete"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    roles: List["Role"] = Relationship(
        back_populates="permissions", link_model=RolePermissionLink
    )


class Role(SQLModel, table=True):
    """
    Represents a role in the RBAC system.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        index=True, unique=True
    )  # e.g., "admin", "user", "filesystem_manager"
    description: Optional[str] = None
    is_system_role: bool = Field(default=False)  # System roles cannot be deleted
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    permissions: List[Permission] = Relationship(
        back_populates="roles", link_model=RolePermissionLink
    )
    users: List["User"] = Relationship(back_populates="roles", link_model=UserRoleLink)
    groups: List["UserGroup"] = Relationship(
        back_populates="roles", link_model=GroupRoleLink
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
    users: List["User"] = Relationship(
        back_populates="groups", link_model=UserGroupLink
    )
    roles: List[Role] = Relationship(back_populates="groups", link_model=GroupRoleLink)


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
    is_admin: bool = Field(default=False)  # Keep for backward compatibility
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    # Relationships
    groups: List[UserGroup] = Relationship(
        back_populates="users", link_model=UserGroupLink
    )
    roles: List[Role] = Relationship(back_populates="users", link_model=UserRoleLink)


class AuditLog(SQLModel, table=True):
    """
    Represents audit log entries for tracking user actions.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    username: str = Field(index=True)  # Store username for easier querying
    action: str = Field(index=True)  # e.g., "login", "create_user", "delete_file", etc.
    resource_type: Optional[str] = Field(
        default=None, index=True
    )  # e.g., "user", "group", "file", "content_pack"
    resource_id: Optional[str] = Field(
        default=None, index=True
    )  # ID of the affected resource
    resource_name: Optional[str] = Field(
        default=None
    )  # Name/title of the affected resource
    details: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )  # Additional details as JSON
    ip_address: Optional[str] = Field(default=None, index=True)
    user_agent: Optional[str] = Field(default=None)
    status: str = Field(default="success", index=True)  # "success", "failure", "error"
    error_message: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationship to user (optional since user might be deleted)
    user: Optional[User] = Relationship()


class ModuleConfiguration(SQLModel, table=True):
    """
    Represents module and tool configuration settings.
    This table stores whether modules and individual tools are enabled/disabled.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    module_name: str = Field(index=True)  # e.g., "filesystem", "email", "database"
    tool_name: Optional[str] = Field(
        default=None, index=True
    )  # e.g., "read_file", "write_file" (None for module-level config)
    is_enabled: bool = Field(default=True)  # Whether the module/tool is enabled
    configuration: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )  # Additional configuration as JSON
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        # Ensure unique constraint on module_name + tool_name combination
        table_args = ({"sqlite_autoincrement": True},)
