from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from jose import JWTError, jwt
import os
import secrets
import logging

# Use bcrypt for password hashing, which is a strong and standard choice.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against its hashed version.

    Args:
        plain_password: The password as entered by the user.
        hashed_password: The password as stored in the database.

    Returns:
        True if the password is correct, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hashes a plain password.

    Args:
        password: The plain password to hash.

    Returns:
        The hashed password string.
    """
    return pwd_context.hash(password)


# --- JWT Token Handling ---

# Generate a random secret key on each startup
# This is secure because refresh tokens are stored in the database
# and can be used to get new access tokens after restart
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a new JWT access token.

    Args:
        data: The data to encode in the token, typically contains 'sub' with username
        expires_delta: Optional custom expiration time

    Returns:
        The encoded JWT access token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a new JWT refresh token.

    Args:
        data: The data to encode in the token, typically contains 'sub' with username
        expires_delta: Optional custom expiration time

    Returns:
        The encoded JWT refresh token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )

    # Add a unique token ID (jti) to allow token revocation
    jti = secrets.token_hex(32)
    to_encode.update({"exp": expire, "jti": jti, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, jti, expire


def decode_access_token(token: str) -> Optional[str]:
    """
    Decodes the access token to get the username.

    Args:
        token: The JWT access token to decode

    Returns:
        The username (from the 'sub' claim) if the token is valid, otherwise None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type", "access")  # Default to access for backward compatibility
        
        if username is None:
            return None
        
        # Verify this is an access token
        if token_type != "access":
            logging.warning(f"Token type mismatch: expected 'access', got '{token_type}'")
            return None
            
        return username
    except JWTError as e:
        logging.warning(f"JWT decode error: {e}")
        return None


def decode_refresh_token(token: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Decodes the refresh token to get the username and token ID.

    Args:
        token: The JWT refresh token to decode

    Returns:
        A tuple containing (username, token_id) if valid, otherwise (None, None)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_id: str = payload.get("jti")
        token_type: str = payload.get("type")
        
        if username is None or token_id is None:
            return None, None
            
        # Verify this is a refresh token
        if token_type != "refresh":
            logging.warning(f"Token type mismatch: expected 'refresh', got '{token_type}'")
            return None, None
            
        return username, token_id
    except JWTError as e:
        logging.warning(f"JWT refresh token decode error: {e}")
        return None, None


def verify_token_type(token: str, expected_type: str) -> bool:
    """
    Verifies that a token is of the expected type (access or refresh).

    Args:
        token: The JWT token to verify
        expected_type: The expected token type ('access' or 'refresh')

    Returns:
        True if the token is of the expected type, False otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        return token_type == expected_type
    except JWTError:
        return False