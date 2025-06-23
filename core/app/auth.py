from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select, SQLModel
from typing import Annotated, List, Optional
from datetime import datetime

from .database import get_session
from .models import User, UserGroup, UserGroupLink
from .security import get_password_hash, verify_password, create_access_token, decode_access_token

# --- API Router and Security Scheme ---

router = APIRouter()

# This defines the security scheme. FastAPI will use this to generate docs
# and it provides a dependency to get the token from the Authorization header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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


# --- Endpoints ---

@router.post("/users/", response_model=UserPublic, tags=["Users"])
def create_user(
    user: UserCreate, 
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """
    Creates a new user.
    """
    # Check if the current user is an admin (except for the first user)
    user_count = session.exec(select(User)).all()
    if len(user_count) > 0 and (not current_user or not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create new users"
        )
    
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
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
    
    return db_user


@router.post("/auth/login", response_model=Token, tags=["Authentication"])
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Authenticates a user and returns a JWT access token.
    """
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login time
    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()
        
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
    session: Annotated[Session, Depends(get_session)]
):
    """
    Delete a user. Only administrators can delete users.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete users"
        )
    
    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting the last admin user
    admin_count = session.exec(select(User).where(User.is_admin == True)).all()
    if db_user.is_admin and len(admin_count) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last administrator"
        )
    
    session.delete(db_user)
    session.commit()
    
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
