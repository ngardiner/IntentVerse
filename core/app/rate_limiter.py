"""
Rate limiting configuration for the API endpoints.
This module provides rate limiting functionality to protect the API from abuse.
"""

import logging
import os
from typing import Optional, Tuple
from fastapi import Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configure the rate limiter
# Rate limiting strategy:
# - UI/State endpoints: NO rate limiting (frequent polling needed)
# - Execute endpoints: 60 requests per minute (actual operations)
# - Login endpoint: 30 requests per minute (anti-brute force)
# - Service accounts: Higher limits for automation
DEFAULT_AUTH_LIMIT = os.getenv("RATE_LIMIT_AUTH", "100/minute")
DEFAULT_UNAUTH_LIMIT = os.getenv("RATE_LIMIT_UNAUTH", "30/minute")
DEFAULT_ADMIN_LIMIT = os.getenv("RATE_LIMIT_ADMIN", "200/minute")

# Service API key for internal communication
SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "dev-service-key-12345")

def get_rate_limit_key(request: Request) -> str:
    """
    Get the rate limiting key for the request.
    This function is used by slowapi to determine the rate limit bucket.
    """
    try:
        key, _ = get_rate_limit_key_and_rate(request)
        return key
    except Exception as e:
        logging.warning(f"Error getting rate limit key, falling back to IP: {e}")
        return get_remote_address(request)

# Initialize the limiter with our custom key function
limiter = Limiter(key_func=get_rate_limit_key)


def get_user_identifier(request: Request) -> str:
    """
    Get a unique identifier for the current user.
    For authenticated users, use their user ID.
    For unauthenticated users, use their IP address.
    """
    # Try to get the user from the request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user:
        return f"user:{user.id}"
    return get_remote_address(request)


def get_rate_limit_key_and_rate(request: Request) -> Tuple[str, str]:
    """
    Determine the rate limit key and rate based on the request.

    Returns:
        Tuple[str, str]: The rate limit key and the rate limit string
    """
    # Check for service API key first (highest priority)
    api_key = request.headers.get("X-API-Key")
    service_key = request.headers.get("X-Service-API-Key")
    
    if api_key == SERVICE_API_KEY or service_key == SERVICE_API_KEY:
        return f"service:{api_key or service_key}", DEFAULT_ADMIN_LIMIT
    
    # Try to get the user from the request state (set by auth middleware)
    user = getattr(request.state, "user", None)

    # If it's an admin user, use a higher limit
    if user and getattr(user, "is_admin", False):
        return f"admin:{user.id}", DEFAULT_ADMIN_LIMIT

    # If it's an authenticated user, use the standard limit
    if user:
        return f"user:{user.id}", DEFAULT_AUTH_LIMIT

    # For unauthenticated users, use a lower limit based on IP
    return get_remote_address(request), DEFAULT_UNAUTH_LIMIT


def get_rate_limit_for_request(request: Request) -> str:
    """
    Get the rate limit string for the current request.
    This is used by slowapi decorators.
    """
    try:
        _, rate = get_rate_limit_key_and_rate(request)
        return rate
    except Exception as e:
        logging.warning(f"Error getting rate limit, using default: {e}")
        return DEFAULT_UNAUTH_LIMIT


# Create a lambda function that slowapi can use
def create_rate_limit_function():
    """Create a rate limit function for slowapi decorators."""
    return lambda request: get_rate_limit_for_request(request)


def add_rate_limit_headers(request: Request, response: Response) -> None:
    """
    Add rate limiting headers to the response.
    This should be called after the rate limiting check.
    """
    try:
        key, rate = get_rate_limit_key_and_rate(request)
        
        # Parse the rate limit to get the limit number
        limit_str = rate.split("/")[0]
        
        # Add basic rate limit headers (slowapi handles the actual limiting)
        response.headers["X-RateLimit-Limit"] = limit_str
        response.headers["X-RateLimit-Remaining"] = limit_str  # Simplified for now
        response.headers["X-RateLimit-Reset"] = "0"
            
    except Exception as e:
        logging.warning(f"Error adding rate limit headers: {e}")
        # Add minimal headers as fallback
        response.headers["X-RateLimit-Limit"] = "30"
        response.headers["X-RateLimit-Remaining"] = "30"
        response.headers["X-RateLimit-Reset"] = "0"


# Custom rate limit exceeded handler
async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    """
    response = Response(
        content='{"detail":"Rate limit exceeded. Please try again later."}',
        status_code=429,
        media_type="application/json"
    )
    
    # Add rate limit headers
    try:
        key, rate = get_rate_limit_key_and_rate(request)
        limit_str = rate.split("/")[0]
        
        response.headers["X-RateLimit-Limit"] = limit_str
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = "60"
        response.headers["Retry-After"] = "60"
        
    except Exception as e:
        logging.warning(f"Error adding headers to rate limit response: {e}")
        response.headers["X-RateLimit-Limit"] = "30"
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = "60"
        response.headers["Retry-After"] = "60"
    
    return response
