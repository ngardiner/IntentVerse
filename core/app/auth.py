from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select, SQLModel
from typing import Annotated, List, Optional, Dict, Any
from datetime import datetime
import logging

from .database import get_session
from .models import User, UserGroup, UserGroupLink, AuditLog
from .security import get_password_hash, verify_password, create_access_token, decode_access_token

# --- API Router and Security Scheme ---

router = APIRouter()

# This defines the security scheme. FastAPI will use this to generate docs
# and it provides a dependency to get the token from the Authorization header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

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
    token: Annotated[str, Depends(oauth2_scheme)],
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
    
    username = decode_access_token(token)
    if username is None:
        raise credentials_exception
    
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exception
    
    return user


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


# --- Endpoints ---

@router.post("/users/", response_model=UserPublic, tags=["Users"])
def create_user(
    user: UserCreate, 
    session: Annotated[Session, Depends(get_session)],
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """
    Creates a new user.
    """
    ip_address, user_agent = get_client_info(request)
    
    # Check if the current user is an admin (except for the first user)
    user_count = session.exec(select(User)).all()
    if len(user_count) > 0 and (not current_user or not current_user.is_admin):
        log_audit_event(
            session=session,
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else "anonymous",
            action="create_user_failed",
            resource_type="user",
            resource_name=user.username,
            details={"reason": "insufficient_permissions"},
            ip_address=ip_address,
            user_agent=user_agent,
            status="failure",
            error_message="Only administrators can create new users"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create new users"
        )
    
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


@router.get("/users/me", response_model=UserWithGroups, tags=["Users"])
def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    A protected endpoint that returns the currently authenticated user's details.
    """
    # Get the user's groups
    user_groups = session.exec(
        select(UserGroup)
        .join(UserGroupLink)
        .where(UserGroupLink.user_id == current_user.id)
    ).all()
    
    # Convert to UserWithGroups
    user_with_groups = UserWithGroups.from_orm(current_user)
    user_with_groups.groups = [group.name for group in user_groups]
    
    return user_with_groups

@router.get("/users/", response_model=List[UserPublic], tags=["Users"])
def get_users(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    skip: int = 0, 
    limit: int = 100
):
    """
    Get all users. Only administrators can access this endpoint.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view all users"
        )
    
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return users

@router.get("/users/{user_id}", response_model=UserWithGroups, tags=["Users"])
def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Get a specific user by ID. Users can view their own details, and administrators can view any user.
    """
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own user details"
        )
    
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get the user's groups
    user_groups = session.exec(
        select(UserGroup)
        .join(UserGroupLink)
        .where(UserGroupLink.user_id == user.id)
    ).all()
    
    # Convert to UserWithGroups
    user_with_groups = UserWithGroups.from_orm(user)
    user_with_groups.groups = [group.name for group in user_groups]
    
    return user_with_groups

@router.put("/users/{user_id}", response_model=UserPublic, tags=["Users"])
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Update a user. Users can update their own details, and administrators can update any user.
    """
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own user details"
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
    
    # Only admins can update these fields
    if current_user.is_admin:
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
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    request: Request
):
    """
    Delete a user. Only administrators can delete users.
    """
    ip_address, user_agent = get_client_info(request)
    
    if not current_user.is_admin:
        log_audit_event(
            session=session,
            user_id=current_user.id,
            username=current_user.username,
            action="delete_user_failed",
            resource_type="user",
            resource_id=str(user_id),
            details={"reason": "insufficient_permissions"},
            ip_address=ip_address,
            user_agent=user_agent,
            status="failure",
            error_message="Only administrators can delete users"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete users"
        )
    
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
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Create a new user group. Only administrators can create groups.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create groups"
        )
    
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
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    skip: int = 0,
    limit: int = 100
):
    """
    Get all user groups.
    """
    groups = session.exec(select(UserGroup).offset(skip).limit(limit)).all()
    return groups

@router.get("/groups/{group_id}", response_model=GroupWithUsers, tags=["Groups"])
def get_group(
    group_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Get a specific group by ID.
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
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Update a group. Only administrators can update groups.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update groups"
        )
    
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
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Delete a group. Only administrators can delete groups.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete groups"
        )
    
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
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Add a user to a group. Only administrators can manage group memberships.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can manage group memberships"
        )
    
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
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Remove a user from a group. Only administrators can manage group memberships.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can manage group memberships"
        )
    
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
    current_user: Annotated[User, Depends(get_current_user)],
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
    Get audit logs. Only administrators can access audit logs.
    """
    ip_address, user_agent = get_client_info(request)
    
    if not current_user.is_admin:
        log_audit_event(
            session=session,
            user_id=current_user.id,
            username=current_user.username,
            action="view_audit_logs_failed",
            details={"reason": "insufficient_permissions"},
            ip_address=ip_address,
            user_agent=user_agent,
            status="failure",
            error_message="Only administrators can view audit logs"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view audit logs"
        )
    
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
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    request: Request
) -> Dict[str, Any]:
    """
    Get audit log statistics. Only administrators can access this.
    """
    ip_address, user_agent = get_client_info(request)
    
    if not current_user.is_admin:
        log_audit_event(
            session=session,
            user_id=current_user.id,
            username=current_user.username,
            action="view_audit_stats_failed",
            details={"reason": "insufficient_permissions"},
            ip_address=ip_address,
            user_agent=user_agent,
            status="failure",
            error_message="Only administrators can view audit statistics"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view audit statistics"
        )
    
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
