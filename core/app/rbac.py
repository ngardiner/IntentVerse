"""
Role-Based Access Control (RBAC) implementation.

This module provides:
- Permission checking functions
- Role management utilities
- RBAC dependency decorators
- Default roles and permissions setup
"""

from typing import List, Set, Optional, Union, Annotated
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
from functools import wraps
import logging

from .database import get_session
from .models import User, Role, Permission, UserRoleLink, GroupRoleLink, RolePermissionLink

logger = logging.getLogger(__name__)

# --- Core Permission System ---

class PermissionChecker:
    """
    Core class for checking user permissions.
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_user_permissions(self, user: User) -> Set[str]:
        """
        Get all permissions for a user (direct roles + group roles).
        
        Args:
            user: The user to check permissions for
            
        Returns:
            Set of permission names the user has
        """
        permissions = set()
        
        # Get permissions from direct user roles
        user_roles = self.session.exec(
            select(Role)
            .join(UserRoleLink)
            .where(UserRoleLink.user_id == user.id)
        ).all()
        
        for role in user_roles:
            role_permissions = self.session.exec(
                select(Permission)
                .join(RolePermissionLink)
                .where(RolePermissionLink.role_id == role.id)
            ).all()
            permissions.update(perm.name for perm in role_permissions)
        
        # Get permissions from group roles
        for group in user.groups:
            group_roles = self.session.exec(
                select(Role)
                .join(GroupRoleLink)
                .where(GroupRoleLink.group_id == group.id)
            ).all()
            
            for role in group_roles:
                role_permissions = self.session.exec(
                    select(Permission)
                    .join(RolePermissionLink)
                    .where(RolePermissionLink.role_id == role.id)
                ).all()
                permissions.update(perm.name for perm in role_permissions)
        
        # Add admin permissions if user is admin (backward compatibility)
        if user.is_admin:
            permissions.add("admin.all")
        
        return permissions
    
    def has_permission(self, user: User, permission: str) -> bool:
        """
        Check if a user has a specific permission.
        
        Args:
            user: The user to check
            permission: The permission name to check
            
        Returns:
            True if user has the permission, False otherwise
        """
        user_permissions = self.get_user_permissions(user)
        
        # Check for exact permission match
        if permission in user_permissions:
            return True
        
        # Check for admin.all permission (grants everything)
        if "admin.all" in user_permissions:
            return True
        
        # Check for wildcard permissions (e.g., "filesystem.*" grants "filesystem.read")
        for perm in user_permissions:
            if perm.endswith(".*"):
                prefix = perm[:-2]  # Remove ".*"
                if permission.startswith(prefix + "."):
                    return True
        
        return False
    
    def has_any_permission(self, user: User, permissions: List[str]) -> bool:
        """
        Check if a user has any of the specified permissions.
        
        Args:
            user: The user to check
            permissions: List of permission names to check
            
        Returns:
            True if user has at least one permission, False otherwise
        """
        return any(self.has_permission(user, perm) for perm in permissions)
    
    def has_all_permissions(self, user: User, permissions: List[str]) -> bool:
        """
        Check if a user has all of the specified permissions.
        
        Args:
            user: The user to check
            permissions: List of permission names to check
            
        Returns:
            True if user has all permissions, False otherwise
        """
        return all(self.has_permission(user, perm) for perm in permissions)


# --- RBAC Dependencies ---

def get_permission_checker(
    session: Annotated[Session, Depends(get_session)]
) -> PermissionChecker:
    """
    Dependency to get a permission checker instance.
    """
    return PermissionChecker(session)


def _get_current_user():
    """Import get_current_user to avoid circular imports."""
    from .auth import get_current_user
    return get_current_user

def _get_current_user_or_service():
    """Import get_current_user_or_service to avoid circular imports."""
    from .auth import get_current_user_or_service
    return get_current_user_or_service

def require_permission(permission: str):
    """
    Dependency factory that creates a dependency requiring a specific permission.
    
    Args:
        permission: The permission name required
        
    Returns:
        A dependency function that checks the permission
    """
    def permission_dependency(
        current_user: Annotated[User, Depends(_get_current_user)],
        checker: Annotated[PermissionChecker, Depends(get_permission_checker)]
    ) -> User:
        if not checker.has_permission(current_user, permission):
            logger.warning(
                f"User {current_user.username} attempted to access resource requiring "
                f"permission '{permission}' but was denied"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        return current_user
    
    return permission_dependency


def require_any_permission(permissions: List[str]):
    """
    Dependency factory that creates a dependency requiring any of the specified permissions.
    
    Args:
        permissions: List of permission names (user needs at least one)
        
    Returns:
        A dependency function that checks the permissions
    """
    def permission_dependency(
        current_user: Annotated[User, Depends(_get_current_user)],
        checker: Annotated[PermissionChecker, Depends(get_permission_checker)]
    ) -> User:
        if not checker.has_any_permission(current_user, permissions):
            logger.warning(
                f"User {current_user.username} attempted to access resource requiring "
                f"any of permissions {permissions} but was denied"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required any of: {', '.join(permissions)}"
            )
        return current_user
    
    return permission_dependency


def require_all_permissions(permissions: List[str]):
    """
    Dependency factory that creates a dependency requiring all of the specified permissions.
    
    Args:
        permissions: List of permission names (user needs all)
        
    Returns:
        A dependency function that checks the permissions
    """
    def permission_dependency(
        current_user: Annotated[User, Depends(_get_current_user)],
        checker: Annotated[PermissionChecker, Depends(get_permission_checker)]
    ) -> User:
        if not checker.has_all_permissions(current_user, permissions):
            logger.warning(
                f"User {current_user.username} attempted to access resource requiring "
                f"all permissions {permissions} but was denied"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required all of: {', '.join(permissions)}"
            )
        return current_user
    
    return permission_dependency


def require_permission_or_service(permission: str):
    """
    Dependency that allows either a user with the required permission OR service authentication.
    
    Args:
        permission: The permission name required for user authentication
        
    Returns:
        A dependency function that checks permission or service auth
    """
    def permission_or_service_dependency(
        current_user_or_service: Annotated[Union[User, str], Depends(_get_current_user_or_service)],
        checker: Annotated[PermissionChecker, Depends(get_permission_checker)]
    ) -> Union[User, str]:
        # If it's service authentication, allow access
        if isinstance(current_user_or_service, str) and current_user_or_service == "service":
            return current_user_or_service
        
        # If it's a user, check permissions
        if isinstance(current_user_or_service, User):
            if not checker.has_permission(current_user_or_service, permission):
                logger.warning(
                    f"User {current_user_or_service.username} attempted to access resource requiring "
                    f"permission '{permission}' but was denied"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {permission}"
                )
            return current_user_or_service
        
        # Should not reach here, but just in case
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return permission_or_service_dependency


# --- Default Permissions and Roles ---

DEFAULT_PERMISSIONS = [
    # User management permissions
    ("users.create", "Create new users", "user", "create"),
    ("users.read", "View user information", "user", "read"),
    ("users.update", "Update user information", "user", "update"),
    ("users.delete", "Delete users", "user", "delete"),
    ("users.manage_roles", "Manage user roles", "user", "manage_roles"),
    
    # Group management permissions
    ("groups.create", "Create new groups", "group", "create"),
    ("groups.read", "View group information", "group", "read"),
    ("groups.update", "Update group information", "group", "update"),
    ("groups.delete", "Delete groups", "group", "delete"),
    ("groups.manage_members", "Manage group members", "group", "manage_members"),
    
    # Role and permission management
    ("roles.create", "Create new roles", "role", "create"),
    ("roles.read", "View role information", "role", "read"),
    ("roles.update", "Update role information", "role", "update"),
    ("roles.delete", "Delete roles", "role", "delete"),
    ("permissions.read", "View permission information", "permission", "read"),
    
    # Filesystem permissions
    ("filesystem.read", "Read files and directories", "filesystem", "read"),
    ("filesystem.write", "Write files and directories", "filesystem", "write"),
    ("filesystem.delete", "Delete files and directories", "filesystem", "delete"),
    ("filesystem.*", "Full filesystem access", "filesystem", "*"),
    
    # Database permissions
    ("database.read", "Read from database", "database", "read"),
    ("database.write", "Write to database", "database", "write"),
    ("database.execute", "Execute database queries", "database", "execute"),
    ("database.*", "Full database access", "database", "*"),
    
    # Email permissions
    ("email.send", "Send emails", "email", "send"),
    ("email.read", "Read email configurations", "email", "read"),
    ("email.*", "Full email access", "email", "*"),
    
    # Web search permissions
    ("web_search.search", "Perform web searches", "web_search", "search"),
    ("web_search.*", "Full web search access", "web_search", "*"),
    
    # Memory permissions
    ("memory.read", "Read from memory store", "memory", "read"),
    ("memory.write", "Write to memory store", "memory", "write"),
    ("memory.*", "Full memory access", "memory", "*"),
    
    # Timeline permissions
    ("timeline.read", "View timeline events", "timeline", "read"),
    ("timeline.write", "Create timeline events", "timeline", "write"),
    ("timeline.*", "Full timeline access", "timeline", "*"),
    
    # Content pack permissions
    ("content_packs.read", "View content packs", "content_pack", "read"),
    ("content_packs.create", "Create content packs", "content_pack", "create"),
    ("content_packs.update", "Update content packs", "content_pack", "update"),
    ("content_packs.delete", "Delete content packs", "content_pack", "delete"),
    ("content_packs.install", "Install content packs", "content_pack", "install"),
    ("content_packs.*", "Full content pack access", "content_pack", "*"),
    
    # Audit permissions
    ("audit.read", "View audit logs", "audit", "read"),
    ("audit.*", "Full audit access", "audit", "*"),
    
    # System permissions
    ("system.debug", "Access debug information", "system", "debug"),
    ("system.config", "Manage system configuration", "system", "config"),
    ("system.*", "Full system access", "system", "*"),
    
    # Admin permission (grants everything)
    ("admin.all", "Full administrative access", "admin", "all"),
]

DEFAULT_ROLES = [
    # System roles
    ("admin", "System Administrator", True, [
        "admin.all"  # Grants everything
    ]),
    
    ("user", "Standard User", True, [
        "users.read",  # Can view own user info
        "groups.read",  # Can view group info
        "timeline.read",  # Can view timeline
    ]),
    
    # Functional roles
    ("filesystem_manager", "Filesystem Manager", False, [
        "filesystem.*",
        "timeline.read",
    ]),
    
    ("database_manager", "Database Manager", False, [
        "database.*",
        "timeline.read",
    ]),
    
    ("content_manager", "Content Pack Manager", False, [
        "content_packs.*",
        "timeline.read",
    ]),
    
    ("user_manager", "User Manager", False, [
        "users.*",
        "groups.*",
        "roles.read",
        "permissions.read",
        "audit.read",
        "timeline.read",
    ]),
    
    ("developer", "Developer", False, [
        "filesystem.read",
        "filesystem.write",
        "database.read",
        "database.execute",
        "web_search.*",
        "memory.*",
        "timeline.*",
        "content_packs.read",
        "system.debug",
    ]),
    
    ("analyst", "Data Analyst", False, [
        "database.read",
        "database.execute",
        "web_search.*",
        "memory.read",
        "timeline.read",
        "audit.read",
    ]),
]


def create_default_permissions(session: Session) -> None:
    """
    Create default permissions in the database.
    """
    logger.info("Creating default permissions...")
    
    for name, description, resource_type, action in DEFAULT_PERMISSIONS:
        existing = session.exec(select(Permission).where(Permission.name == name)).first()
        if not existing:
            permission = Permission(
                name=name,
                description=description,
                resource_type=resource_type,
                action=action
            )
            session.add(permission)
            logger.info(f"Created permission: {name}")
    
    session.commit()


def create_default_roles(session: Session) -> None:
    """
    Create default roles and assign permissions.
    """
    logger.info("Creating default roles...")
    
    for role_name, description, is_system, permission_names in DEFAULT_ROLES:
        existing_role = session.exec(select(Role).where(Role.name == role_name)).first()
        if not existing_role:
            role = Role(
                name=role_name,
                description=description,
                is_system_role=is_system
            )
            session.add(role)
            session.commit()
            session.refresh(role)
            logger.info(f"Created role: {role_name}")
        else:
            role = existing_role
        
        # Assign permissions to role
        for perm_name in permission_names:
            permission = session.exec(select(Permission).where(Permission.name == perm_name)).first()
            if permission:
                # Check if permission is already assigned
                existing_link = session.exec(
                    select(RolePermissionLink)
                    .where(RolePermissionLink.role_id == role.id)
                    .where(RolePermissionLink.permission_id == permission.id)
                ).first()
                
                if not existing_link:
                    link = RolePermissionLink(role_id=role.id, permission_id=permission.id)
                    session.add(link)
                    logger.info(f"Assigned permission {perm_name} to role {role_name}")
    
    session.commit()


def assign_admin_role_to_admins(session: Session) -> None:
    """
    Assign the admin role to all users with is_admin=True.
    """
    logger.info("Assigning admin role to existing admin users...")
    
    admin_role = session.exec(select(Role).where(Role.name == "admin")).first()
    if not admin_role:
        logger.error("Admin role not found!")
        return
    
    admin_users = session.exec(select(User).where(User.is_admin == True)).all()
    for user in admin_users:
        # Check if user already has admin role
        existing_link = session.exec(
            select(UserRoleLink)
            .where(UserRoleLink.user_id == user.id)
            .where(UserRoleLink.role_id == admin_role.id)
        ).first()
        
        if not existing_link:
            link = UserRoleLink(user_id=user.id, role_id=admin_role.id)
            session.add(link)
            logger.info(f"Assigned admin role to user {user.username}")
    
    session.commit()


def assign_user_role_to_users(session: Session) -> None:
    """
    Assign the user role to all users who don't have any roles.
    """
    logger.info("Assigning user role to users without roles...")
    
    user_role = session.exec(select(Role).where(Role.name == "user")).first()
    if not user_role:
        logger.error("User role not found!")
        return
    
    all_users = session.exec(select(User)).all()
    for user in all_users:
        # Check if user has any roles
        existing_roles = session.exec(
            select(UserRoleLink).where(UserRoleLink.user_id == user.id)
        ).all()
        
        if not existing_roles:
            link = UserRoleLink(user_id=user.id, role_id=user_role.id)
            session.add(link)
            logger.info(f"Assigned user role to user {user.username}")
    
    session.commit()


def initialize_rbac_system(session: Session) -> None:
    """
    Initialize the complete RBAC system with default permissions and roles.
    """
    logger.info("Initializing RBAC system...")
    
    try:
        create_default_permissions(session)
        create_default_roles(session)
        assign_admin_role_to_admins(session)
        assign_user_role_to_users(session)
        
        logger.info("RBAC system initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize RBAC system: {e}")
        session.rollback()
        raise