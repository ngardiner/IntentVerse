"""
Security headers middleware for IntentVerse.

This module implements comprehensive security headers to protect against
common web vulnerabilities and enhance the security posture of the application.
"""

import logging
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add comprehensive security headers to all HTTP responses.
    
    Implements security headers based on OWASP recommendations and modern
    web security best practices.
    """
    
    def __init__(self, app: ASGIApp, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Default security headers configuration
        self.default_headers = {
            # Prevent clickjacking attacks
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable XSS protection in browsers
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy for privacy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy (formerly Feature Policy)
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            ),
            
            # Content Security Policy (CSP)
            "Content-Security-Policy": self._build_csp_header(),
            
            # HTTP Strict Transport Security (HSTS)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Cross-Origin policies
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
            
            # Server information hiding
            "Server": "IntentVerse",
            
            # Cache control for sensitive endpoints
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        
        # Merge with custom configuration
        self.headers = {**self.default_headers, **self.config.get("headers", {})}
        
        # Paths that should have relaxed CSP (for UI assets)
        self.relaxed_csp_paths = self.config.get("relaxed_csp_paths", [
            "/static/", "/assets/", "/favicon.ico", "/manifest.json"
        ])
        
        # API paths that need CORS headers
        self.api_paths = self.config.get("api_paths", ["/api/", "/auth/", "/health/", "/users/"])
    
    def _build_csp_header(self) -> str:
        """Build Content Security Policy header."""
        # Strict CSP for API endpoints
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Relaxed for React dev
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles for UI
            "img-src 'self' data: https:",  # Allow images from self, data URLs, and HTTPS
            "font-src 'self' data:",  # Allow fonts from self and data URLs
            "connect-src 'self'",  # API connections to same origin
            "media-src 'self'",  # Media from same origin
            "object-src 'none'",  # No plugins
            "frame-src 'none'",  # No frames
            "base-uri 'self'",  # Base URI restrictions
            "form-action 'self'",  # Form submissions to same origin
            "frame-ancestors 'none'",  # Prevent framing
            "upgrade-insecure-requests"  # Upgrade HTTP to HTTPS
        ]
        
        return "; ".join(csp_directives)
    
    def _build_relaxed_csp_header(self) -> str:
        """Build relaxed CSP header for UI assets."""
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "img-src 'self' data: https:",
            "font-src 'self' data: https://fonts.gstatic.com",
            "connect-src 'self' ws: wss:",  # Allow WebSocket connections
            "media-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'"
        ]
        
        return "; ".join(csp_directives)
    
    def _should_use_relaxed_csp(self, path: str) -> bool:
        """Check if path should use relaxed CSP."""
        return any(path.startswith(relaxed_path) for relaxed_path in self.relaxed_csp_paths)
    
    def _is_api_path(self, path: str) -> bool:
        """Check if path is an API endpoint."""
        return any(path.startswith(api_path) for api_path in self.api_paths)
    
    def _add_cors_headers(self, response: Response, request: Request) -> None:
        """Add CORS headers for API endpoints."""
        origin = request.headers.get("origin")
        
        # Use centralized CORS configuration
        from .security_config import security_config
        config = security_config.get_security_headers_config()
        allowed_origins = config.get("cors_allowed_origins", ["*"])
        allowed_methods = config.get("cors_allowed_methods", ["GET", "POST", "OPTIONS"])
        allowed_headers = config.get("cors_allowed_headers", ["Content-Type", "Authorization"])
        allow_credentials = config.get("cors_allow_credentials", True)
        max_age = config.get("cors_max_age", 86400)
        
        # Handle wildcard or specific origins
        if "*" in allowed_origins:
            # When using credentials, we can't use wildcard with specific origin
            if allow_credentials and origin:
                response.headers["Access-Control-Allow-Origin"] = origin
            else:
                response.headers["Access-Control-Allow-Origin"] = "*"
        elif origin and origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            # For internal applications, be more permissive
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(allowed_headers)
        response.headers["Access-Control-Allow-Credentials"] = "true" if allow_credentials else "false"
        response.headers["Access-Control-Max-Age"] = str(max_age)
    
    def _add_security_headers(self, response: Response, request: Request) -> None:
        """Add security headers to response."""
        path = request.url.path
        
        # Add all standard security headers
        for header, value in self.headers.items():
            # Skip CSP here, we'll handle it separately
            if header != "Content-Security-Policy":
                response.headers[header] = value
        
        # Add appropriate CSP based on path
        if self._should_use_relaxed_csp(path):
            response.headers["Content-Security-Policy"] = self._build_relaxed_csp_header()
        else:
            response.headers["Content-Security-Policy"] = self._build_csp_header()
        
        # Add CORS headers for API endpoints
        if self._is_api_path(path):
            self._add_cors_headers(response, request)
        
        # Remove server information leakage
        if "server" in response.headers:
            response.headers["server"] = "IntentVerse"
        
        # Add security headers for sensitive endpoints
        if path.startswith(("/auth/", "/api/v", "/admin/")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Add specific headers for file downloads
        if "download" in request.query_params or path.endswith((".pdf", ".doc", ".xls")):
            response.headers["X-Download-Options"] = "noopen"
            response.headers["Content-Disposition"] = "attachment"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add security headers to response."""
        try:
            # Handle preflight CORS requests
            if request.method == "OPTIONS" and self._is_api_path(request.url.path):
                response = Response(status_code=200)
                self._add_cors_headers(response, request)
                return response
            
            # Process the request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response, request)
            
            # Log security header application (debug level)
            self.logger.debug(
                f"Applied security headers to {request.method} {request.url.path}"
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in security headers middleware: {e}")
            # Continue with the request even if header application fails
            response = await call_next(request)
            return response


class SecurityConfig:
    """Configuration class for security headers."""
    
    @staticmethod
    def get_development_config() -> Dict[str, Any]:
        """Get security configuration for development environment."""
        return {
            "headers": {
                # Relaxed HSTS for development
                "Strict-Transport-Security": "max-age=0",
                # Allow framing for development tools
                "X-Frame-Options": "SAMEORIGIN",
            },
            "relaxed_csp_paths": [
                "/static/", "/assets/", "/favicon.ico", "/manifest.json",
                "/", "/login", "/dashboard"  # UI routes
            ],
            "api_paths": ["/api/", "/auth/", "/health/", "/users/"]
        }
    
    @staticmethod
    def get_production_config() -> Dict[str, Any]:
        """Get security configuration for production environment."""
        return {
            "headers": {
                # Strict HSTS for production
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                # Deny all framing in production
                "X-Frame-Options": "DENY",
                # Additional production headers
                "Expect-CT": "max-age=86400, enforce",
            },
            "relaxed_csp_paths": [
                "/static/", "/assets/", "/favicon.ico", "/manifest.json"
            ],
            "api_paths": ["/api/", "/auth/", "/health/", "/users/"]
        }
    
    @staticmethod
    def get_testing_config() -> Dict[str, Any]:
        """Get security configuration for testing environment."""
        return {
            "headers": {
                # Minimal headers for testing
                "Strict-Transport-Security": "max-age=0",
                "X-Frame-Options": "SAMEORIGIN",
            },
            "relaxed_csp_paths": [
                "/static/", "/assets/", "/favicon.ico", "/manifest.json",
                "/", "/test", "/debug"
            ],
            "api_paths": ["/api/", "/auth/", "/health/", "/users/", "/test/"]
        }


def create_security_headers_middleware(environment: str = "production") -> SecurityHeadersMiddleware:
    """
    Create security headers middleware with environment-specific configuration.
    
    Args:
        environment: Environment name (development, production, testing)
        
    Returns:
        Configured SecurityHeadersMiddleware instance
    """
    config_map = {
        "development": SecurityConfig.get_development_config(),
        "production": SecurityConfig.get_production_config(),
        "testing": SecurityConfig.get_testing_config()
    }
    
    config = config_map.get(environment, SecurityConfig.get_production_config())
    
    return lambda app: SecurityHeadersMiddleware(app, config)