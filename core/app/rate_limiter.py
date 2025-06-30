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
# Default limits are:
# - 100 requests per minute for authenticated users
# - 30 requests per minute for unauthenticated users
DEFAULT_AUTH_LIMIT = os.getenv("RATE_LIMIT_AUTH", "100/minute")
DEFAULT_UNAUTH_LIMIT = os.getenv("RATE_LIMIT_UNAUTH", "30/minute")
DEFAULT_ADMIN_LIMIT = os.getenv("RATE_LIMIT_ADMIN", "200/minute")

# Initialize the limiter with the remote address as the key function
limiter = Limiter(key_func=get_remote_address)

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
    # Try to get the user from the request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    
    # If it's a service account, use a higher limit
    service_key = request.headers.get("X-Service-API-Key")
    if service_key:
        return f"service:{service_key}", DEFAULT_ADMIN_LIMIT
    
    # If it's an admin user, use a higher limit
    if user and getattr(user, "is_admin", False):
        return f"admin:{user.id}", DEFAULT_ADMIN_LIMIT
    
    # If it's an authenticated user, use the standard limit
    if user:
        return f"user:{user.id}", DEFAULT_AUTH_LIMIT
    
    # For unauthenticated users, use a lower limit
    return get_remote_address(request), DEFAULT_UNAUTH_LIMIT

def rate_limit_request(request: Request, response: Response) -> Optional[Response]:
    """
    Apply rate limiting to the request.
    
    Args:
        request: The FastAPI request object
        response: The FastAPI response object
        
    Returns:
        Optional[Response]: A response object if the rate limit is exceeded, None otherwise
    """
    key, rate = get_rate_limit_key_and_rate(request)
    
    # Check if the request exceeds the rate limit
    limiter_check = limiter.limiter.hit(rate, key)
    if not limiter_check:
        logging.warning(f"Rate limit exceeded for {key}")
        
        # Create a custom response for rate limit exceeded
        error_response = Response(
            content='{"detail":"Rate limit exceeded"}',
            status_code=429,
            media_type="application/json"
        )
        
        # Add rate limit headers
        remaining = limiter.limiter.get_window_stats(rate, key)[1]
        reset = limiter.limiter.get_window_stats(rate, key)[0]
        
        error_response.headers["X-RateLimit-Limit"] = rate.split("/")[0]
        error_response.headers["X-RateLimit-Remaining"] = str(remaining)
        error_response.headers["X-RateLimit-Reset"] = str(reset)
        error_response.headers["Retry-After"] = str(reset)
        
        return error_response
    
    # Add rate limit headers to the response
    remaining = limiter.limiter.get_window_stats(rate, key)[1]
    reset = limiter.limiter.get_window_stats(rate, key)[0]
    
    response.headers["X-RateLimit-Limit"] = rate.split("/")[0]
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset)
    
    return None