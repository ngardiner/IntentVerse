"""
Security configuration management for IntentVerse.

This module provides centralized security configuration including
environment-specific settings and security policy management.

NOTE: This application is designed for internal/local use and is open source.
Security defaults are set to be functional out-of-the-box rather than
maximally restrictive. Users can tighten security via environment variables
if deploying in more sensitive environments.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class SecuritySettings:
    """Security settings configuration."""
    
    # Environment
    environment: str = "development"
    debug_mode: bool = False
    
    # HTTPS settings
    force_https: bool = False
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True
    
    # Content Security Policy
    csp_enabled: bool = True
    csp_report_only: bool = False
    csp_report_uri: Optional[str] = None
    
    # CORS settings
    cors_enabled: bool = True
    cors_allowed_origins: List[str] = None
    cors_allowed_methods: List[str] = None
    cors_allowed_headers: List[str] = None
    cors_allow_credentials: bool = True
    cors_max_age: int = 86400  # 24 hours
    
    # Frame options
    frame_options: str = "SAMEORIGIN"  # DENY, SAMEORIGIN, or ALLOW-FROM
    
    # Additional security headers
    content_type_options: bool = True
    xss_protection: bool = True
    referrer_policy: str = "strict-origin-when-cross-origin"
    
    # Server information
    hide_server_header: bool = True
    custom_server_header: str = "IntentVerse"
    
    # Cache control for sensitive endpoints
    no_cache_paths: List[str] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.cors_allowed_origins is None:
            self.cors_allowed_origins = self._get_default_cors_origins()
        
        if self.cors_allowed_methods is None:
            self.cors_allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        
        if self.cors_allowed_headers is None:
            self.cors_allowed_headers = [
                "Content-Type", "Authorization", "X-Requested-With", "Accept", 
                "Origin", "Cache-Control", "Pragma", "X-API-Key"
            ]
        
        if self.no_cache_paths is None:
            self.no_cache_paths = [
                "/auth/", "/api/v", "/admin/", "/user/", "/settings/"
            ]
    
    def _get_default_cors_origins(self) -> List[str]:
        """Get default CORS origins based on environment."""
        # For internal applications, allow all origins by default
        # Users can restrict this via INTENTVERSE_CORS_ORIGINS if needed
        return ["*"]


class SecurityConfigManager:
    """Manages security configuration for the application."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._settings = None
    
    @property
    def settings(self) -> SecuritySettings:
        """Get current security settings."""
        if self._settings is None:
            self._settings = self._load_settings()
        return self._settings
    
    def _load_settings(self) -> SecuritySettings:
        """Load security settings from environment variables."""
        environment = os.getenv("INTENTVERSE_ENVIRONMENT", "development").lower()
        debug_mode = os.getenv("INTENTVERSE_DEBUG", "false").lower() == "true"
        
        # HTTPS settings - default to false for easier local setup
        force_https = os.getenv("INTENTVERSE_FORCE_HTTPS", "false").lower() == "true"
        hsts_max_age = int(os.getenv("INTENTVERSE_HSTS_MAX_AGE", "31536000"))
        
        # CSP settings - default to false for easier setup
        csp_enabled = os.getenv("INTENTVERSE_CSP_ENABLED", "false").lower() == "true"
        csp_report_only = os.getenv("INTENTVERSE_CSP_REPORT_ONLY", "false").lower() == "true"
        csp_report_uri = os.getenv("INTENTVERSE_CSP_REPORT_URI")
        
        # CORS settings
        cors_enabled = os.getenv("INTENTVERSE_CORS_ENABLED", "true").lower() == "true"
        cors_origins = os.getenv("INTENTVERSE_CORS_ORIGINS")
        cors_allowed_origins = cors_origins.split(",") if cors_origins else None
        cors_methods = os.getenv("INTENTVERSE_CORS_METHODS")
        cors_allowed_methods = cors_methods.split(",") if cors_methods else None
        cors_headers = os.getenv("INTENTVERSE_CORS_HEADERS")
        cors_allowed_headers = cors_headers.split(",") if cors_headers else None
        
        # Frame options
        frame_options = os.getenv("INTENTVERSE_FRAME_OPTIONS", "SAMEORIGIN").upper()
        
        # Server header
        hide_server_header = os.getenv("INTENTVERSE_HIDE_SERVER", "true").lower() == "true"
        custom_server_header = os.getenv("INTENTVERSE_SERVER_HEADER", "IntentVerse")
        
        settings = SecuritySettings(
            environment=environment,
            debug_mode=debug_mode,
            force_https=force_https,
            hsts_max_age=hsts_max_age,
            csp_enabled=csp_enabled,
            csp_report_only=csp_report_only,
            csp_report_uri=csp_report_uri,
            cors_enabled=cors_enabled,
            cors_allowed_origins=cors_allowed_origins,
            cors_allowed_methods=cors_allowed_methods,
            cors_allowed_headers=cors_allowed_headers,
            frame_options=frame_options,
            hide_server_header=hide_server_header,
            custom_server_header=custom_server_header
        )
        
        self.logger.info(f"Loaded security settings for environment: {environment}")
        if debug_mode:
            self.logger.debug(f"Security settings: {settings}")
        
        return settings
    
    def get_security_headers_config(self) -> Dict[str, Any]:
        """Get configuration for security headers middleware."""
        settings = self.settings
        
        # Build CSP header
        csp_header = self._build_csp_header()
        if settings.csp_report_only:
            csp_header_name = "Content-Security-Policy-Report-Only"
        else:
            csp_header_name = "Content-Security-Policy"
        
        # Build HSTS header
        hsts_parts = [f"max-age={settings.hsts_max_age}"]
        if settings.hsts_include_subdomains:
            hsts_parts.append("includeSubDomains")
        if settings.hsts_preload:
            hsts_parts.append("preload")
        hsts_header = "; ".join(hsts_parts)
        
        # Base security headers - relaxed for internal applications
        headers = {
            "X-Frame-Options": settings.frame_options,
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": settings.referrer_policy,
        }
        
        # Only add restrictive headers in production with HTTPS
        if settings.environment == "production" and settings.force_https:
            headers.update({
                "X-XSS-Protection": "1; mode=block",
                "Cross-Origin-Embedder-Policy": "require-corp",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Resource-Policy": "same-origin",
            })
        
        # Add CSP if enabled
        if settings.csp_enabled:
            headers[csp_header_name] = csp_header
        
        # Add HSTS if HTTPS is forced
        if settings.force_https:
            headers["Strict-Transport-Security"] = hsts_header
        
        # Add server header
        if settings.hide_server_header:
            headers["Server"] = settings.custom_server_header
        
        # Permissions policy
        headers["Permissions-Policy"] = self._build_permissions_policy()
        
        return {
            "headers": headers,
            "cors_enabled": settings.cors_enabled,
            "cors_allowed_origins": settings.cors_allowed_origins,
            "cors_allowed_methods": settings.cors_allowed_methods,
            "cors_allowed_headers": settings.cors_allowed_headers,
            "cors_allow_credentials": settings.cors_allow_credentials,
            "cors_max_age": settings.cors_max_age,
            "no_cache_paths": settings.no_cache_paths,
            "environment": settings.environment
        }
    
    def _build_csp_header(self) -> str:
        """Build Content Security Policy header."""
        settings = self.settings
        
        if settings.environment == "development":
            # Relaxed CSP for development
            directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                "img-src 'self' data: https:",
                "font-src 'self' data: https://fonts.gstatic.com",
                "connect-src 'self' ws: wss:",
                "media-src 'self'",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'"
            ]
        else:
            # Reasonable CSP for production - still functional for internal apps
            directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Allow inline scripts for functionality
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                "img-src 'self' data: https: http:",  # Allow external images
                "font-src 'self' data: https://fonts.gstatic.com",
                "connect-src 'self' ws: wss: https: http:",  # Allow websockets and external APIs
                "media-src 'self'",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'self'"  # Allow same-origin framing
            ]
        
        # Add report URI if configured
        if settings.csp_report_uri:
            directives.append(f"report-uri {settings.csp_report_uri}")
        
        return "; ".join(directives)
    
    def _build_permissions_policy(self) -> str:
        """Build Permissions Policy header."""
        # Reasonable permissions policy - only restrict clearly unnecessary features
        policies = [
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "fullscreen=(self)"
        ]
        
        return ", ".join(policies)
    
    def validate_configuration(self) -> List[str]:
        """Validate security configuration and return any warnings."""
        warnings = []
        settings = self.settings
        
        # Check for insecure development settings in production
        if settings.environment == "production":
            if settings.debug_mode:
                warnings.append("Debug mode is enabled in production")
            
            if not settings.force_https:
                warnings.append("HTTPS is not enforced in production")
            
            if settings.frame_options == "SAMEORIGIN":
                warnings.append("Frame options allow same-origin framing in production")
            
            if settings.csp_report_only:
                warnings.append("CSP is in report-only mode in production")
        
        # Check HSTS configuration
        if settings.force_https and settings.hsts_max_age < 86400:
            warnings.append("HSTS max-age is less than 24 hours")
        
        # Check CORS configuration - only warn in production
        if settings.environment == "production" and settings.cors_enabled and "*" in settings.cors_allowed_origins:
            warnings.append("CORS allows all origins (wildcard) in production")
        
        return warnings


# Global security config manager instance
security_config = SecurityConfigManager()