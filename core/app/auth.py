from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, APIKeyHeader
from sqlmodel import Session, select, SQLModel
from typing import Annotated, List, Optional, Dict, Any, Union
from datetime import datetime
import logging
import os

from .database import get_session
from .models import User, UserGroup, UserGroupLink, AuditLog, Role, Permission, UserRoleLink, GroupRoleLink, RolePermissionLink
from .security import get_password_hash, verify_password, create_access_token, decode_access_token
from .rbac import require_permission, require_any_permission, get_permission_checker, PermissionChecker

# --- API Router and Security Scheme ---

router = APIRouter()

# This defines the security scheme. FastAPI will use this to generate docs
# and it provides a dependency to get the token from the Authorization header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# API Key for service-to-service communication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Service API key for internal communication (should be set as environment variable)
SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "dev-service-key-12345")

# --- Audit Logging Functions ---

def log_audit_event(
    session: Session,
    user_id: Optional[int],
    username: str,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None
):
    """
    Log an audit event to the database.
    """
    try:
        audit_log = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )
        session.add(audit_log)
        session.commit()
        logging.info(f"Audit log created: {username} performed {action} on {resource_type}:{resource_id}")
    except Exception as e:
        logging.error(f"Failed to create audit log: {e}")
        # Don't raise the exception to avoid breaking the main operation

def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Extract client IP address and user agent from request.
    """
    # Try to get real IP from headers (in case of proxy/load balancer)
    ip_address = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
        request.headers.get("X-Real-IP") or
        request.client.host if request.client else None
    )
    
    user_agent = request.headers.get("User-Agent")
    
    return ip_address, user_agent


# --- Dependency for Getting Current User ---

def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)]
) -> User:
    """
    Dependency to get the current user from a JWT token.
    This function will be used to protect endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    username = decode_access_token(token)
    if username is None:
        raise credentials_exception
    
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exception
    
    return user

def get_current_user_or_service(
    session: Annotated[Session, Depends(get_session)],
    token: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
    api_key: Annotated[Optional[str], Depends(api_key_header)] = None
) -> Union[User, str]:
    """
    Dependency that allows both JWT token and API key authentication.
    Returns a User object for JWT auth, or "service" string for API key auth.
    """
    # Check API key first (for service-to-service communication)
    if api_key and api_key == SERVICE_API_KEY:
        return "service"
    
    # Fall back to JWT token authentication
    if token:
        username = decode_access_token(token)
        if username:
            user = session.exec(select(User).where(User.username == username)).first()
            if user:
                return user
    
    # If neither authentication method works, raise an exception
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


# --- Data Schemas for API ---

class UserCreate(SQLModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: bool = False

class UserUpdate(SQLModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

class UserPublic(SQLModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None

class UserWithGroups(UserPublic):
    groups: List[str] = []

class Token(SQLModel):
    access_token: str
    token_type: str
    
class GroupCreate(SQLModel):
    name: str
    description: Optional[str] = None
    
class GroupUpdate(SQLModel):
    description: Optional[str] = None
    
class GroupPublic(SQLModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    
class GroupWithUsers(GroupPublic):
    users: List[str] = []

class AuditLogPublic(SQLModel):
    id: int
    user_id: Optional[int] = None
    username: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    timestamp: datetime

# --- RBAC Schemas ---

class PermissionPublic(SQLModel):
    id: int
    name: str
    description: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    created_at: datetime

class PermissionCreate(SQLModel):
    name: str
    description: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None

class RolePublic(SQLModel):
    id: int
    name: str
    description: Optional[str] = None
    is_system_role: bool
    created_at: datetime

class RoleCreate(SQLModel):
    name: str
    description: Optional[str] = None

class RoleUpdate(SQLModel):
    description: Optional[str] = None

class RoleWithPermissions(RolePublic):
    permissions: List[str] = []

class UserWithRoles(UserPublic):
    roles: List[str] = []
    permissions: List[str] = []

class GroupWithRoles(GroupPublic):
    roles: List[str] = []


# --- Endpoints ---

@router.post("/users/", response_model=UserPublic, tags=["Users"])
def create_user(
    user: UserCreate, 
    session: Annotated[Session, Depends(get_session)],
    request: Request,
    current_user: Annotated[User, Depends(require_permission("users.create"))]
):
    """
    Creates a new user.
    """
    ip_address, user_agent = get_client_info(request)
    
    # RBAC handles permission checking, so we can proceed directly
    
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
        log_audit_event(
            session=session,
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else "anonymous",
            action="create_user_failed",
            resource_type="user",
            resource_name=user.username,
            details={"reason": "username_already_exists"},
            ip_address=ip_address,
            user_agent=user_agent,
            status="failure",
            error_message="Username already registered"
        )
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username, 
        hashed_password=hashed_password,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin
    )
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    # Log successful user creation
    log_audit_event(
        session=session,
        user_id=current_user.id if current_user else None,
        username=current_user.username if current_user else "system",
        action="create_user",
        resource_type="user",
        resource_id=str(db_user.id),
        resource_name=db_user.username,
        details={
            "created_user_email": db_user.email,
            "created_user_full_name": db_user.full_name,
            "created_user_is_admin": db_user.is_admin
        },
        ip_address=ip_address,
        user_agent=user_agent,
        status="success"
    )
    
    return db_user


@router.post("/auth/login", response_model=Token, tags=["Authentication"])
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
    request: Request
):
    """
    Authenticates a user and returns a JWT access token.
    """
    try:
        ip_address, user_agent = get_client_info(request)

        user = session.exec(select(User).where(User.username == form_data.username)).first()

        if not user or not verify_password(form_data.password, user.hashed_password):
            # Log failed login attempt
            log_audit_event(
                session=session,
                user_id=user.id if user else None,
                username=form_data.username,
                action="login_failed",
                details={"reason": "invalid_credentials"},
                ip_address=ip_address,
                user_agent=user_agent,
                status="failure",
                error_message="Incorrect username or password"
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last login time
        user.last_login = datetime.utcnow()
        session.add(user)
        session.commit()

        # Log successful login
        log_audit_event(
            session=session,
            user_id=user.id,
            username=user.username,
            action="login_success",
            details={"user_agent": user_agent},
            ip_address=ip_address,
            user_agent=user_agent,
            status="success"
        )

        access_token = create_access_token(
            data={"sub": user.username}
        )

        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.exception("An unhandled exception occurred during login!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred. Check core.log for details.",
        )

@router.get("/users/me", response_model=UserWithRoles, tags=["Users"])
def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    checker: Annotated[PermissionChecker, Depends(get_permission_checker)]
):
    """
    A protected endpoint that returns the currently authenticated user's details with roles and permissions.
    """
    # Get the user's roles
    user_roles = session.exec(
        select(Role)
        .join(UserRoleLink)
        .where(UserRoleLink.user_id == current_user.id)
    ).all()
    
    # Get all permissions
    user_permissions = checker.get_user_permissions(current_user)
    
    # Create a dictionary from the user model
    try:
        user_data = current_user.model_dump()
    except AttributeError:
        # Fallback for older Pydantic versions
        user_data = current_user.dict()
    
    # Add roles and permissions
    user_data['roles'] = [role.name for role in user_roles]
    user_data['permissions'] = sorted(list(user_permissions))
    
    # Create the final response model from the corrected dictionary
    try:
        user_with_roles = UserWithRoles.model_validate(user_data)
    except AttributeError:
        # Fallback for older Pydantic versions
        user_with_roles = UserWithRoles.parse_obj(user_data)
    
    return user_with_roles

@router.get("/users/", response_model=List[UserPublic], tags=["Users"])
def get_users(
    current_user: Annotated[User, Depends(require_permission("users.read"))],
    session: Annotated[Session, Depends(get_session)],
    skip: int = 0, 
    limit: int = 100
):
    """
    Get all users. Requires users.read permission.
    """
    
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return users

@router.get("/users/{user_id}", response_model=UserWithRoles, tags=["Users"])
def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    checker: Annotated[PermissionChecker, Depends(get_permission_checker)]
):
    """
    Get a specific user by ID. Users can view their own details, or with users.read permission can view any user.
    """
    # Allow users to view their own details, or check for permission to view others
    if current_user.id != user_id and not checker.has_permission(current_user, "users.read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own user details or need users.read permission"
        )
    
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get the user's roles and permissions
    user_roles = session.exec(
        select(Role)
        .join(UserRoleLink)
        .where(UserRoleLink.user_id == user.id)
    ).all()
    
    # Get permissions from roles and groups
    user_permissions = checker.get_user_permissions(user)
    
    # Create a dictionary from the user model
    try:
        user_data = user.model_dump()
    except AttributeError:
        # Fallback for older Pydantic versions
        user_data = user.dict()
    
    # Add roles and permissions
    user_data['roles'] = [role.name for role in user_roles]
    user_data['permissions'] = sorted(list(user_permissions))
    
    # Create the final response model from the corrected dictionary
    try:
        user_with_roles = UserWithRoles.model_validate(user_data)
    except AttributeError:
        # Fallback for older Pydantic versions
        user_with_roles = UserWithRoles.parse_obj(user_data)
    
    return user_with_roles

@router.put("/users/{user_id}", response_model=UserPublic, tags=["Users"])
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    checker: Annotated[PermissionChecker, Depends(get_permission_checker)]
):
    """
    Update a user. Users can update their own details, or with users.update permission can update any user.
    """
    # Allow users to update their own details, or check for permission to update others
    if current_user.id != user_id and not checker.has_permission(current_user, "users.update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own user details or need users.update permission"
        )
    
    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields
    if user_update.email is not None:
        db_user.email = user_update.email
    if user_update.full_name is not None:
        db_user.full_name = user_update.full_name
    if user_update.password is not None:
        db_user.hashed_password = get_password_hash(user_update.password)
    
    # Only users with admin permissions can update these fields
    if checker.has_permission(current_user, "admin.all"):
        if user_update.is_active is not None:
            db_user.is_active = user_update.is_active
        if user_update.is_admin is not None:
            db_user.is_admin = user_update.is_admin
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    return db_user

@router.delete("/users/{user_id}", status_code=204, tags=["Users"])
def delete_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_permission("users.delete"))],
    session: Annotated[Session, Depends(get_session)],
    request: Request
):
    """
    Delete a user. Requires users.delete permission.
    """
    ip_address, user_agent = get_client_info(request)
    
    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        log_audit_event(
            session=session,
            user_id=current_user.id,
            username=current_user.username,
            action="delete_user_failed",
            resource_type="user",
            resource_id=str(user_id),
            details={"reason": "user_not_found"},
            ip_address=ip_address,
            user_agent=user_agent,
            status="failure",
            error_message="User not found"
        )
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting the last admin user
    admin_count = session.exec(select(User).where(User.is_admin == True)).all()
    if db_user.is_admin and len(admin_count) <= 1:
        log_audit_event(
            session=session,
            user_id=current_user.id,
            username=current_user.username,
            action="delete_user_failed",
            resource_type="user",
            resource_id=str(user_id),
            resource_name=db_user.username,
            details={"reason": "cannot_delete_last_admin"},
            ip_address=ip_address,
            user_agent=user_agent,
            status="failure",
            error_message="Cannot delete the last administrator"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last administrator"
        )
    
    # Store user info before deletion for audit log
    deleted_user_info = {
        "username": db_user.username,
        "email": db_user.email,
        "full_name": db_user.full_name,
        "is_admin": db_user.is_admin,
        "was_active": db_user.is_active
    }
    
    session.delete(db_user)
    session.commit()
    
    # Log successful user deletion
    log_audit_event(
        session=session,
        user_id=current_user.id,
        username=current_user.username,
        action="delete_user",
        resource_type="user",
        resource_id=str(user_id),
        resource_name=deleted_user_info["username"],
        details=deleted_user_info,
        ip_address=ip_address,
        user_agent=user_agent,
        status="success"
    )
    
# --- Group Management Endpoints ---

@router.post("/groups/", response_model=GroupPublic, tags=["Groups"])
def create_group(
    group: GroupCreate,
    current_user: Annotated[User, Depends(require_permission("groups.create"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Create a new user group. Requires groups.create permission.
    """
    
    existing_group = session.exec(select(UserGroup).where(UserGroup.name == group.name)).first()
    if existing_group:
        raise HTTPException(status_code=400, detail="Group name already exists")
    
    db_group = UserGroup(
        name=group.name,
        description=group.description
    )
    
    session.add(db_group)
    session.commit()
    session.refresh(db_group)
    
    return db_group

@router.get("/groups/", response_model=List[GroupPublic], tags=["Groups"])
def get_groups(
    current_user: Annotated[User, Depends(require_permission("groups.read"))],
    session: Annotated[Session, Depends(get_session)],
    skip: int = 0,
    limit: int = 100
):
    """
    Get all user groups. Requires groups.read permission.
    """
    groups = session.exec(select(UserGroup).offset(skip).limit(limit)).all()
    return groups

@router.get("/groups/{group_id}", response_model=GroupWithUsers, tags=["Groups"])
def get_group(
    group_id: int,
    current_user: Annotated[User, Depends(require_permission("groups.read"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Get a specific group by ID. Requires groups.read permission.
    """
    group = session.exec(select(UserGroup).where(UserGroup.id == group_id)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Get the group's users
    group_users = session.exec(
        select(User)
        .join(UserGroupLink)
        .where(UserGroupLink.group_id == group.id)
    ).all()
    
    # Convert to GroupWithUsers
    group_with_users = GroupWithUsers.from_orm(group)
    group_with_users.users = [user.username for user in group_users]
    
    return group_with_users

@router.put("/groups/{group_id}", response_model=GroupPublic, tags=["Groups"])
def update_group(
    group_id: int,
    group_update: GroupUpdate,
    current_user: Annotated[User, Depends(require_permission("groups.update"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Update a group. Requires groups.update permission.
    """
    
    db_group = session.exec(select(UserGroup).where(UserGroup.id == group_id)).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Update group fields
    if group_update.description is not None:
        db_group.description = group_update.description
    
    session.add(db_group)
    session.commit()
    session.refresh(db_group)
    
    return db_group

@router.delete("/groups/{group_id}", status_code=204, tags=["Groups"])
def delete_group(
    group_id: int,
    current_user: Annotated[User, Depends(require_permission("groups.delete"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Delete a group. Requires groups.delete permission.
    """
    
    db_group = session.exec(select(UserGroup).where(UserGroup.id == group_id)).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    session.delete(db_group)
    session.commit()

# --- User-Group Management Endpoints ---

@router.post("/users/{user_id}/groups/{group_id}", status_code=204, tags=["Users", "Groups"])
def add_user_to_group(
    user_id: int,
    group_id: int,
    current_user: Annotated[User, Depends(require_permission("groups.manage_members"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Add a user to a group. Requires groups.manage_members permission.
    """
    
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    group = session.exec(select(UserGroup).where(UserGroup.id == group_id)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Check if the user is already in the group
    existing_link = session.exec(
        select(UserGroupLink)
        .where(UserGroupLink.user_id == user_id)
        .where(UserGroupLink.group_id == group_id)
    ).first()
    
    if existing_link:
        raise HTTPException(status_code=400, detail="User is already in this group")
    
    # Add the user to the group
    link = UserGroupLink(user_id=user_id, group_id=group_id)
    session.add(link)
    session.commit()

@router.delete("/users/{user_id}/groups/{group_id}", status_code=204, tags=["Users", "Groups"])
def remove_user_from_group(
    user_id: int,
    group_id: int,
    current_user: Annotated[User, Depends(require_permission("groups.manage_members"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Remove a user from a group. Requires groups.manage_members permission.
    """
    
    # Check if the link exists
    link = session.exec(
        select(UserGroupLink)
        .where(UserGroupLink.user_id == user_id)
        .where(UserGroupLink.group_id == group_id)
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="User is not in this group")
    
    # Remove the user from the group
    session.delete(link)
    session.commit()

# --- Audit Log Endpoints ---

@router.get("/audit-logs/", response_model=List[AuditLogPublic], tags=["Audit"])
def get_audit_logs(
    current_user: Annotated[User, Depends(require_permission("audit.read"))],
    session: Annotated[Session, Depends(get_session)],
    request: Request,
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    username: Optional[str] = None,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[AuditLogPublic]:
    """
    Get audit logs. Requires audit.read permission.
    """
    ip_address, user_agent = get_client_info(request)
    
    # Build query with filters
    query = select(AuditLog)
    
    if action:
        query = query.where(AuditLog.action.contains(action))
    if username:
        query = query.where(AuditLog.username.contains(username))
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if status:
        query = query.where(AuditLog.status == status)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(AuditLog.timestamp >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(AuditLog.timestamp <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")
    
    # Order by timestamp (newest first) and apply pagination
    query = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
    
    audit_logs = session.exec(query).all()
    
    # Log the audit log access
    log_audit_event(
        session=session,
        user_id=current_user.id,
        username=current_user.username,
        action="view_audit_logs",
        details={
            "filters": {
                "action": action,
                "username": username,
                "resource_type": resource_type,
                "status": status,
                "start_date": start_date,
                "end_date": end_date
            },
            "results_count": len(audit_logs)
        },
        ip_address=ip_address,
        user_agent=user_agent,
        status="success"
    )
    
    return audit_logs

@router.get("/audit-logs/stats", tags=["Audit"])
def get_audit_log_stats(
    current_user: Annotated[User, Depends(require_permission("audit.read"))],
    session: Annotated[Session, Depends(get_session)],
    request: Request
) -> Dict[str, Any]:
    """
    Get audit log statistics. Requires audit.read permission.
    """
    ip_address, user_agent = get_client_info(request)
    
    # Get total count
    total_logs = session.exec(select(AuditLog)).all()
    total_count = len(total_logs)
    
    # Get counts by status
    success_count = len([log for log in total_logs if log.status == "success"])
    failure_count = len([log for log in total_logs if log.status == "failure"])
    error_count = len([log for log in total_logs if log.status == "error"])
    
    # Get top actions
    action_counts = {}
    for log in total_logs:
        action_counts[log.action] = action_counts.get(log.action, 0) + 1
    
    top_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Get top users
    user_counts = {}
    for log in total_logs:
        user_counts[log.username] = user_counts.get(log.username, 0) + 1
    
    top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Get recent activity (last 24 hours)
    from datetime import timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_logs = [log for log in total_logs if log.timestamp >= yesterday]
    
    stats = {
        "total_logs": total_count,
        "status_breakdown": {
            "success": success_count,
            "failure": failure_count,
            "error": error_count
        },
        "top_actions": [{"action": action, "count": count} for action, count in top_actions],
        "top_users": [{"username": username, "count": count} for username, count in top_users],
        "recent_activity_24h": len(recent_logs)
    }
    
    # Log the stats access
    log_audit_event(
        session=session,
        user_id=current_user.id,
        username=current_user.username,
        action="view_audit_stats",
        details={"stats_generated": True},
        ip_address=ip_address,
        user_agent=user_agent,
        status="success"
    )
    
    return stats


# --- RBAC Management Endpoints ---

@router.get("/roles/", response_model=List[RolePublic], tags=["RBAC"])
def get_roles(
    current_user: Annotated[User, Depends(require_permission("roles.read"))],
    session: Annotated[Session, Depends(get_session)],
    skip: int = 0,
    limit: int = 100
):
    """
    Get all roles. Requires roles.read permission.
    """
    roles = session.exec(select(Role).offset(skip).limit(limit)).all()
    return roles

@router.get("/roles/{role_id}", response_model=RoleWithPermissions, tags=["RBAC"])
def get_role(
    role_id: int,
    current_user: Annotated[User, Depends(require_permission("roles.read"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Get a specific role by ID with its permissions. Requires roles.read permission.
    """
    role = session.exec(select(Role).where(Role.id == role_id)).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Get the role's permissions
    role_permissions = session.exec(
        select(Permission)
        .join(RolePermissionLink)
        .where(RolePermissionLink.role_id == role.id)
    ).all()
    
    # Convert to RoleWithPermissions
    role_with_permissions = RoleWithPermissions.from_orm(role)
    role_with_permissions.permissions = [perm.name for perm in role_permissions]
    
    return role_with_permissions

@router.post("/roles/", response_model=RolePublic, tags=["RBAC"])
def create_role(
    role: RoleCreate,
    current_user: Annotated[User, Depends(require_permission("roles.create"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Create a new role. Requires roles.create permission.
    """
    existing_role = session.exec(select(Role).where(Role.name == role.name)).first()
    if existing_role:
        raise HTTPException(status_code=400, detail="Role name already exists")
    
    db_role = Role(
        name=role.name,
        description=role.description,
        is_system_role=False  # User-created roles are never system roles
    )
    
    session.add(db_role)
    session.commit()
    session.refresh(db_role)
    
    return db_role

@router.put("/roles/{role_id}", response_model=RolePublic, tags=["RBAC"])
def update_role(
    role_id: int,
    role_update: RoleUpdate,
    current_user: Annotated[User, Depends(require_permission("roles.update"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Update a role. Requires roles.update permission.
    """
    db_role = session.exec(select(Role).where(Role.id == role_id)).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Prevent updating system roles
    if db_role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update system roles"
        )
    
    # Update role fields
    if role_update.description is not None:
        db_role.description = role_update.description
    
    session.add(db_role)
    session.commit()
    session.refresh(db_role)
    
    return db_role

@router.delete("/roles/{role_id}", status_code=204, tags=["RBAC"])
def delete_role(
    role_id: int,
    current_user: Annotated[User, Depends(require_permission("roles.delete"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Delete a role. Requires roles.delete permission.
    """
    db_role = session.exec(select(Role).where(Role.id == role_id)).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Prevent deleting system roles
    if db_role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles"
        )
    
    session.delete(db_role)
    session.commit()

@router.get("/permissions/", response_model=List[PermissionPublic], tags=["RBAC"])
def get_permissions(
    current_user: Annotated[User, Depends(require_permission("permissions.read"))],
    session: Annotated[Session, Depends(get_session)],
    skip: int = 0,
    limit: int = 100,
    resource_type: Optional[str] = None
):
    """
    Get all permissions. Requires permissions.read permission.
    """
    query = select(Permission)
    if resource_type:
        query = query.where(Permission.resource_type == resource_type)
    
    permissions = session.exec(query.offset(skip).limit(limit)).all()
    return permissions

@router.post("/permissions/", response_model=PermissionPublic, tags=["RBAC"])
def create_permission(
    permission: PermissionCreate,
    current_user: Annotated[User, Depends(require_permission("admin.all"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Create a new permission. Requires admin.all permission.
    """
    existing_permission = session.exec(select(Permission).where(Permission.name == permission.name)).first()
    if existing_permission:
        raise HTTPException(status_code=400, detail="Permission name already exists")
    
    db_permission = Permission(
        name=permission.name,
        description=permission.description,
        resource_type=permission.resource_type,
        action=permission.action
    )
    
    session.add(db_permission)
    session.commit()
    session.refresh(db_permission)
    
    return db_permission

# --- Role-Permission Management ---

@router.post("/roles/{role_id}/permissions/{permission_id}", status_code=204, tags=["RBAC"])
def assign_permission_to_role(
    role_id: int,
    permission_id: int,
    current_user: Annotated[User, Depends(require_permission("roles.update"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Assign a permission to a role. Requires roles.update permission.
    """
    role = session.exec(select(Role).where(Role.id == role_id)).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    permission = session.exec(select(Permission).where(Permission.id == permission_id)).first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    # Check if the permission is already assigned
    existing_link = session.exec(
        select(RolePermissionLink)
        .where(RolePermissionLink.role_id == role_id)
        .where(RolePermissionLink.permission_id == permission_id)
    ).first()
    
    if existing_link:
        raise HTTPException(status_code=400, detail="Permission is already assigned to this role")
    
    # Assign the permission to the role
    link = RolePermissionLink(role_id=role_id, permission_id=permission_id)
    session.add(link)
    session.commit()

@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=204, tags=["RBAC"])
def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    current_user: Annotated[User, Depends(require_permission("roles.update"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Remove a permission from a role. Requires roles.update permission.
    """
    # Check if the link exists
    link = session.exec(
        select(RolePermissionLink)
        .where(RolePermissionLink.role_id == role_id)
        .where(RolePermissionLink.permission_id == permission_id)
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Permission is not assigned to this role")
    
    # Remove the permission from the role
    session.delete(link)
    session.commit()

# --- User-Role Management ---

@router.post("/users/{user_id}/roles/{role_id}", status_code=204, tags=["RBAC"])
def assign_role_to_user(
    user_id: int,
    role_id: int,
    current_user: Annotated[User, Depends(require_permission("users.manage_roles"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Assign a role to a user. Requires users.manage_roles permission.
    """
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = session.exec(select(Role).where(Role.id == role_id)).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if the role is already assigned
    existing_link = session.exec(
        select(UserRoleLink)
        .where(UserRoleLink.user_id == user_id)
        .where(UserRoleLink.role_id == role_id)
    ).first()
    
    if existing_link:
        raise HTTPException(status_code=400, detail="Role is already assigned to this user")
    
    # Assign the role to the user
    link = UserRoleLink(user_id=user_id, role_id=role_id)
    session.add(link)
    session.commit()

@router.delete("/users/{user_id}/roles/{role_id}", status_code=204, tags=["RBAC"])
def remove_role_from_user(
    user_id: int,
    role_id: int,
    current_user: Annotated[User, Depends(require_permission("users.manage_roles"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Remove a role from a user. Requires users.manage_roles permission.
    """
    # Check if the link exists
    link = session.exec(
        select(UserRoleLink)
        .where(UserRoleLink.user_id == user_id)
        .where(UserRoleLink.role_id == role_id)
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Role is not assigned to this user")
    
    # Remove the role from the user
    session.delete(link)
    session.commit()

# --- Group-Role Management ---

@router.get("/groups/{group_id}/roles", response_model=GroupWithRoles, tags=["RBAC"])
def get_group_roles(
    group_id: int,
    current_user: Annotated[User, Depends(require_permission("groups.read"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Get a group with its assigned roles. Requires groups.read permission.
    """
    group = session.exec(select(UserGroup).where(UserGroup.id == group_id)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Get the group's roles
    group_roles = session.exec(
        select(Role)
        .join(GroupRoleLink)
        .where(GroupRoleLink.group_id == group.id)
    ).all()
    
    # Convert to GroupWithRoles
    group_with_roles = GroupWithRoles.from_orm(group)
    group_with_roles.roles = [role.name for role in group_roles]
    
    return group_with_roles

@router.post("/groups/{group_id}/roles/{role_id}", status_code=204, tags=["RBAC"])
def assign_role_to_group(
    group_id: int,
    role_id: int,
    current_user: Annotated[User, Depends(require_permission("groups.update"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Assign a role to a group. Requires groups.update permission.
    """
    group = session.exec(select(UserGroup).where(UserGroup.id == group_id)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    role = session.exec(select(Role).where(Role.id == role_id)).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if the role is already assigned
    existing_link = session.exec(
        select(GroupRoleLink)
        .where(GroupRoleLink.group_id == group_id)
        .where(GroupRoleLink.role_id == role_id)
    ).first()
    
    if existing_link:
        raise HTTPException(status_code=400, detail="Role is already assigned to this group")
    
    # Assign the role to the group
    link = GroupRoleLink(group_id=group_id, role_id=role_id)
    session.add(link)
    session.commit()

@router.delete("/groups/{group_id}/roles/{role_id}", status_code=204, tags=["RBAC"])
def remove_role_from_group(
    group_id: int,
    role_id: int,
    current_user: Annotated[User, Depends(require_permission("groups.update"))],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Remove a role from a group. Requires groups.update permission.
    """
    # Check if the link exists
    link = session.exec(
        select(GroupRoleLink)
        .where(GroupRoleLink.group_id == group_id)
        .where(GroupRoleLink.role_id == role_id)
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Role is not assigned to this group")
    
    # Remove the role from the group
    session.delete(link)
    session.commit()
