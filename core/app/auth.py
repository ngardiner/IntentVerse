from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import Annotated

from .database import get_session
from .models import User
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

class UserPublic(SQLModel):
    id: int
    username: str

class Token(SQLModel):
    access_token: str
    token_type: str


# --- Endpoints ---

@router.post("/users/", response_model=UserPublic, tags=["Users"])
def create_user(user: UserCreate, session: Annotated[Session, Depends(get_session)]):
    """
    Creates a new user. This is needed so we can test the login.
    """
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    
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
        
    access_token = create_access_token(
        data={"sub": user.username}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserPublic, tags=["Users"])
def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    """
    A protected endpoint that returns the currently authenticated user's details.
    """
    return current_user
