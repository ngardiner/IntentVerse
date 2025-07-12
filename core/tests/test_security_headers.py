"""
Tests for security headers middleware.

This module tests the comprehensive security headers implementation
to ensure proper protection against common web vulnerabilities.
"""

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.security_headers import SecurityHeadersMiddleware, SecurityConfig, create_security_headers_middleware
from app.security_config import SecurityConfigManager, SecuritySettings


class TestSecurityHeadersMiddleware:
    """Test security headers middleware functionality."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with security middleware."""
        app = FastAPI()
        
        # Add security middleware with testing config
        config = SecurityConfig.get_testing_config()
        app.add_middleware(SecurityHeadersMiddleware, config=config)
        
        @app.get("/api/test")
        async def test_api():
            return {"message": "test"}
        
        @app.get("/")
        async def test_ui():
            return {"message": "ui"}
        
        @app.get("/static/test.js")
        async def test_static():
            return {"message": "static"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_basic_security_headers(self, client):
        """Test that basic security headers are applied."""
        response = client.get("/api/test")
        
        assert response.status_code == 200
        
        # Check essential security headers
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers
        
        # Check header values
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "strict-origin-when-cross-origin" in response.headers["Referrer-Policy"]
    
    def test_csp_header_content(self, client):
        """Test Content Security Policy header content."""
        response = client.get("/api/test")
        
        csp = response.headers.get("Content-Security-Policy", "")
        
        # Check essential CSP directives
        assert "default-src 'self'" in csp
        assert "object-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "base-uri 'self'" in csp
    
    def test_cors_headers_for_api(self, client):
        """Test CORS headers are added for API endpoints."""
        # Test preflight request
        response = client.options("/api/test", headers={"Origin": "http://localhost:3000"})
        
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
        
        # Test actual API request
        response = client.get("/api/test", headers={"Origin": "http://localhost:3000"})
        assert "Access-Control-Allow-Origin" in response.headers
    
    def test_no_cors_for_non_api(self, client):
        """Test CORS headers are not added for non-API endpoints."""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        
        # CORS headers should not be present for non-API endpoints
        assert "Access-Control-Allow-Origin" not in response.headers
    
    def test_relaxed_csp_for_static_assets(self, client):
        """Test relaxed CSP for static assets."""
        response = client.get("/static/test.js")
        
        csp = response.headers.get("Content-Security-Policy", "")
        
        # Should have relaxed CSP for static assets
        assert "default-src 'self'" in csp
        # Should not have upgrade-insecure-requests for static assets
        assert "upgrade-insecure-requests" not in csp
    
    def test_cache_control_for_sensitive_endpoints(self, client):
        """Test cache control headers for sensitive endpoints."""
        response = client.get("/api/test")
        
        # API endpoints should have no-cache headers
        assert "Cache-Control" in response.headers
        assert "no-store" in response.headers["Cache-Control"]
        assert "no-cache" in response.headers["Cache-Control"]
    
    def test_server_header_customization(self, client):
        """Test server header customization."""
        response = client.get("/api/test")
        
        # Should have custom server header
        assert response.headers.get("Server") == "IntentVerse"
    
    def test_permissions_policy_header(self, client):
        """Test Permissions Policy header."""
        response = client.get("/api/test")
        
        permissions_policy = response.headers.get("Permissions-Policy", "")
        
        # Check that dangerous permissions are disabled
        assert "geolocation=()" in permissions_policy
        assert "microphone=()" in permissions_policy
        assert "camera=()" in permissions_policy
    
    def test_cross_origin_headers(self, client):
        """Test Cross-Origin headers."""
        response = client.get("/api/test")
        
        assert "Cross-Origin-Embedder-Policy" in response.headers
        assert "Cross-Origin-Opener-Policy" in response.headers
        assert "Cross-Origin-Resource-Policy" in response.headers
        
        assert response.headers["Cross-Origin-Embedder-Policy"] == "require-corp"
        assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
        assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"


class TestSecurityConfig:
    """Test security configuration classes."""
    
    def test_development_config(self):
        """Test development configuration."""
        config = SecurityConfig.get_development_config()
        
        assert isinstance(config, dict)
        assert "headers" in config
        assert "relaxed_csp_paths" in config
        
        # Development should have relaxed HSTS
        assert config["headers"]["Strict-Transport-Security"] == "max-age=0"
        
        # Should allow more paths for development
        assert "/" in config["relaxed_csp_paths"]
    
    def test_production_config(self):
        """Test production configuration."""
        config = SecurityConfig.get_production_config()
        
        assert isinstance(config, dict)
        assert "headers" in config
        
        # Production should have strict HSTS
        hsts = config["headers"]["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts
        assert "preload" in hsts
        
        # Should deny all framing
        assert config["headers"]["X-Frame-Options"] == "DENY"
    
    def test_testing_config(self):
        """Test testing configuration."""
        config = SecurityConfig.get_testing_config()
        
        assert isinstance(config, dict)
        assert "headers" in config
        
        # Testing should have minimal headers
        assert config["headers"]["Strict-Transport-Security"] == "max-age=0"
        assert "/test" in config["relaxed_csp_paths"]


class TestSecurityConfigManager:
    """Test security configuration manager."""
    
    def test_default_settings(self):
        """Test default security settings."""
        manager = SecurityConfigManager()
        settings = manager.settings
        
        assert isinstance(settings, SecuritySettings)
        assert settings.environment in ["development", "production", "testing"]
        assert isinstance(settings.force_https, bool)
        assert isinstance(settings.hsts_max_age, int)
    
    @patch.dict("os.environ", {
        "INTENTVERSE_ENVIRONMENT": "development",
        "INTENTVERSE_DEBUG": "true",
        "INTENTVERSE_FORCE_HTTPS": "false"
    })
    def test_environment_variable_loading(self):
        """Test loading settings from environment variables."""
        manager = SecurityConfigManager()
        # Clear cached settings
        manager._settings = None
        
        settings = manager.settings
        
        assert settings.environment == "development"
        assert settings.debug_mode is True
        assert settings.force_https is False
    
    def test_security_headers_config_generation(self):
        """Test security headers configuration generation."""
        manager = SecurityConfigManager()
        config = manager.get_security_headers_config()
        
        assert isinstance(config, dict)
        assert "headers" in config
        assert "cors_enabled" in config
        assert "environment" in config
        
        # Check essential headers are present
        headers = config["headers"]
        assert "X-Frame-Options" in headers
        assert "X-Content-Type-Options" in headers
        assert "Content-Security-Policy" in headers or "Content-Security-Policy-Report-Only" in headers
    
    def test_csp_header_building(self):
        """Test CSP header building."""
        manager = SecurityConfigManager()
        csp = manager._build_csp_header()
        
        assert isinstance(csp, str)
        assert "default-src 'self'" in csp
        assert "object-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp
    
    def test_permissions_policy_building(self):
        """Test Permissions Policy building."""
        manager = SecurityConfigManager()
        policy = manager._build_permissions_policy()
        
        assert isinstance(policy, str)
        assert "geolocation=()" in policy
        assert "microphone=()" in policy
        assert "camera=()" in policy
    
    @patch.dict("os.environ", {
        "INTENTVERSE_ENVIRONMENT": "production",
        "INTENTVERSE_DEBUG": "true"  # This should trigger a warning
    })
    def test_configuration_validation(self):
        """Test configuration validation warnings."""
        manager = SecurityConfigManager()
        # Clear cached settings
        manager._settings = None
        
        warnings = manager.validate_configuration()
        
        assert isinstance(warnings, list)
        # Should warn about debug mode in production
        assert any("debug mode" in warning.lower() for warning in warnings)


class TestSecurityMiddlewareFactory:
    """Test security middleware factory function."""
    
    def test_create_development_middleware(self):
        """Test creating middleware for development."""
        middleware_factory = create_security_headers_middleware("development")
        
        assert callable(middleware_factory)
        
        # Test that it returns a middleware instance
        app = FastAPI()
        middleware = middleware_factory(app)
        assert isinstance(middleware, SecurityHeadersMiddleware)
    
    def test_create_production_middleware(self):
        """Test creating middleware for production."""
        middleware_factory = create_security_headers_middleware("production")
        
        assert callable(middleware_factory)
        
        app = FastAPI()
        middleware = middleware_factory(app)
        assert isinstance(middleware, SecurityHeadersMiddleware)
    
    def test_create_testing_middleware(self):
        """Test creating middleware for testing."""
        middleware_factory = create_security_headers_middleware("testing")
        
        assert callable(middleware_factory)
        
        app = FastAPI()
        middleware = middleware_factory(app)
        assert isinstance(middleware, SecurityHeadersMiddleware)
    
    def test_unknown_environment_defaults_to_production(self):
        """Test that unknown environment defaults to production config."""
        middleware_factory = create_security_headers_middleware("unknown_env")
        
        assert callable(middleware_factory)
        
        app = FastAPI()
        middleware = middleware_factory(app)
        assert isinstance(middleware, SecurityHeadersMiddleware)


class TestSecurityIntegration:
    """Test security headers integration with full application."""
    
    @pytest.fixture
    def app_with_security(self):
        """Create app with security middleware."""
        app = FastAPI()
        
        # Add security middleware
        security_middleware = create_security_headers_middleware("testing")
        app.add_middleware(security_middleware)
        
        @app.get("/api/v1/test")
        async def api_endpoint():
            return {"message": "api"}
        
        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}
        
        @app.options("/api/v1/test")
        async def api_options():
            return {"message": "options"}
        
        return app
    
    def test_full_security_headers_integration(self, app_with_security):
        """Test full security headers integration."""
        client = TestClient(app_with_security)
        
        response = client.get("/api/v1/test")
        
        # Check that all major security headers are present
        expected_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options", 
            "X-XSS-Protection",
            "Referrer-Policy",
            "Content-Security-Policy",
            "Permissions-Policy",
            "Cross-Origin-Embedder-Policy",
            "Cross-Origin-Opener-Policy",
            "Cross-Origin-Resource-Policy"
        ]
        
        for header in expected_headers:
            assert header in response.headers, f"Missing security header: {header}"
    
    def test_cors_preflight_handling(self, app_with_security):
        """Test CORS preflight request handling."""
        client = TestClient(app_with_security)
        
        response = client.options(
            "/api/v1/test",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization"
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers


if __name__ == "__main__":
    pytest.main([__file__])