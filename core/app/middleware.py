"""
Middleware for the FastAPI application.
This module contains middleware components for the application.
"""

import logging
import time
import os
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .rate_limiter import add_rate_limit_headers
from .modules.timeline.tool import log_error as timeline_log_error


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set user state from JWT tokens for rate limiting.
    This runs before rate limiting to ensure user context is available.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Extract user information from JWT token and set it in request state.
        """
        # Initialize user state
        request.state.user = None
        
        try:
            # Try to get JWT token from Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                
                # Decode the token to get user info
                from .security import decode_access_token
                username = decode_access_token(token)
                
                if username:
                    # Get user from database
                    from .database import get_session
                    from .models import User
                    from sqlmodel import Session, select
                    
                    session_gen = get_session()
                    session = next(session_gen)
                    
                    try:
                        user = session.exec(select(User).where(User.username == username)).first()
                        if user:
                            request.state.user = user
                    finally:
                        session.close()
                        
        except Exception as e:
            # Don't fail the request if auth middleware has issues
            logging.debug(f"Auth middleware error (non-critical): {e}")
        
        # Continue with the request
        response = await call_next(request)
        return response


class RateLimitHeaderMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add rate limiting headers to API responses.
    This works in conjunction with slowapi decorators on endpoints.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and add rate limiting headers to the response.

        Args:
            request: The FastAPI request object
            call_next: The next middleware or endpoint handler

        Returns:
            Response: The response object with rate limiting headers
        """
        # Process the request
        try:
            response = await call_next(request)
            
            # Add rate limiting headers for API endpoints and auth endpoints
            if request.url.path.startswith("/api") or request.url.path.startswith("/auth"):
                add_rate_limit_headers(request, response)
            
            return response
        except Exception as e:
            logging.exception(f"Error processing request: {e}")
            # Log the error to the timeline
            try:
                timeline_log_error(
                    title="API Request Error",
                    description=f"Error processing request to {request.url.path}: {str(e)}",
                    details={
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )
            except Exception as log_err:
                logging.error(f"Failed to log error to timeline: {log_err}")

            # Return a 500 error response
            return Response(
                content='{"detail":"Internal server error"}',
                status_code=500,
                media_type="application/json",
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests with timing information.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and log timing information.

        Args:
            request: The FastAPI request object
            call_next: The next middleware or endpoint handler

        Returns:
            Response: The response object
        """
        start_time = time.time()

        # Get client IP and user agent
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Process the request
        try:
            response = await call_next(request)

            # Calculate request processing time
            process_time = time.time() - start_time

            # Log the request
            logging.info(
                f"Request: {request.method} {request.url.path} "
                f"- Status: {response.status_code} "
                f"- Time: {process_time:.4f}s "
                f"- IP: {client_ip} "
                f"- UA: {user_agent}"
            )

            return response
        except Exception as e:
            process_time = time.time() - start_time
            logging.exception(
                f"Request failed: {request.method} {request.url.path} "
                f"- Time: {process_time:.4f}s "
                f"- IP: {client_ip} "
                f"- UA: {user_agent} "
                f"- Error: {str(e)}"
            )
            raise
