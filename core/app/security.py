from passlib.context import CryptContext

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

