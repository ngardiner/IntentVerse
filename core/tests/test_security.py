"""
Unit tests for security functions.
"""
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

from app.security import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    decode_access_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)


class TestPasswordHashing:
    """Test password hashing and verification functions."""
    
    def test_password_hashing_and_verification(self):
        """Test that password hashing and verification work correctly."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        
        # Hash should be different from original password
        assert hashed != password
        assert len(hashed) > 0
        
        # Verification should work
        assert verify_password(password, hashed) is True
        
        # Wrong password should fail verification
        assert verify_password("wrongpassword", hashed) is False
    
    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2
    
    def test_same_password_produces_different_hashes(self):
        """Test that the same password produces different hashes (due to salt)."""
        password = "samepassword"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
    
    def test_empty_password_handling(self):
        """Test handling of empty passwords."""
        empty_password = ""
        hashed = get_password_hash(empty_password)
        
        assert verify_password(empty_password, hashed) is True
        assert verify_password("nonempty", hashed) is False


class TestJWTTokenHandling:
    """Test JWT token creation and decoding functions."""
    
    def test_create_and_decode_access_token(self):
        """Test creating and decoding a valid access token."""
        username = "testuser"
        token = create_access_token(data={"sub": username})
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode the token
        decoded_username = decode_access_token(token)
        assert decoded_username == username
    
    def test_create_token_with_custom_expiration(self):
        """Test creating a token with custom expiration time."""
        username = "testuser"
        custom_expires = timedelta(minutes=60)
        token = create_access_token(data={"sub": username}, expires_delta=custom_expires)
        
        # Decode manually to check expiration
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        
        # Check that expiration is approximately 60 minutes from now
        expected_exp = datetime.now(timezone.utc) + custom_expires
        actual_exp = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        
        # Allow for small time differences (within 5 seconds)
        time_diff = abs((actual_exp - expected_exp).total_seconds())
        assert time_diff < 5
    
    def test_create_token_with_default_expiration(self):
        """Test creating a token with default expiration time."""
        username = "testuser"
        token = create_access_token(data={"sub": username})
        
        # Decode manually to check expiration
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        
        # Check that expiration is approximately ACCESS_TOKEN_EXPIRE_MINUTES from now
        expected_exp = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        actual_exp = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        
        # Allow for small time differences (within 5 seconds)
        time_diff = abs((actual_exp - expected_exp).total_seconds())
        assert time_diff < 5
    
    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        invalid_token = "invalid.token.here"
        result = decode_access_token(invalid_token)
        assert result is None
    
    def test_decode_expired_token(self):
        """Test decoding an expired token."""
        username = "testuser"
        # Create a token that expires immediately
        past_time = timedelta(seconds=-1)
        token = create_access_token(data={"sub": username}, expires_delta=past_time)
        
        # Decoding should return None for expired token
        result = decode_access_token(token)
        assert result is None
    
    def test_decode_token_without_sub_claim(self):
        """Test decoding a token without 'sub' claim."""
        # Create a token manually without 'sub' claim
        payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=30)}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        result = decode_access_token(token)
        assert result is None
    
    def test_decode_token_with_wrong_secret(self):
        """Test that tokens signed with wrong secret are rejected."""
        username = "testuser"
        wrong_secret = "wrong_secret_key"
        
        # Create token with wrong secret
        payload = {
            "sub": username,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
        token = jwt.encode(payload, wrong_secret, algorithm=ALGORITHM)
        
        # Decoding should fail
        result = decode_access_token(token)
        assert result is None
    
    def test_create_token_with_additional_data(self):
        """Test creating a token with additional data beyond username."""
        username = "testuser"
        additional_data = {
            "sub": username,
            "role": "admin",
            "permissions": ["read", "write"]
        }
        token = create_access_token(data=additional_data)
        
        # Decode manually to check all data is preserved
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload.get("sub") == username
        assert payload.get("role") == "admin"
        assert payload.get("permissions") == ["read", "write"]
        
        # Our decode function should still return the username
        decoded_username = decode_access_token(token)
        assert decoded_username == username