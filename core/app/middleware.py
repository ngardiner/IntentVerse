"""
Middleware for the FastAPI application.
This module contains middleware components for the application.
"""

import logging
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .rate_limiter import rate_limit_request
from .modules.timeline.tool import log_error

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply rate limiting to all API endpoints.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and apply rate limiting.
        
        Args:
            request: The FastAPI request object
            call_next: The next middleware or endpoint handler
            
        Returns:
            Response: The response object
        """
        # Skip rate limiting for non-API endpoints
        if not request.url.path.startswith("/api"):
            return await call_next(request)
        
        # Create a response object that will be updated by the rate limiter
        response = Response()
        
        # Check rate limiting
        rate_limit_response = rate_limit_request(request, response)
        if rate_limit_response:
            return rate_limit_response
        
        # Process the request
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logging.exception(f"Error processing request: {e}")
            # Log the error to the timeline
            try:
                log_error(
                    title="API Request Error",
                    description=f"Error processing request to {request.url.path}: {str(e)}",
                    error_type=type(e).__name__,
                    error_details=str(e),
                )
            except Exception as log_error:
                logging.error(f"Failed to log error to timeline: {log_error}")
            
            # Return a 500 error response
            return Response(
                content='{"detail":"Internal server error"}',
                status_code=500,
                media_type="application/json"
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