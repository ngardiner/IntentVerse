"""
API Version Manager

This module manages API versioning, including version tracking, deprecation,
and compatibility between different API versions.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from fastapi import FastAPI, APIRouter, Request, Response, Depends, HTTPException, Header
from starlette.middleware.base import BaseHTTPMiddleware


class VersionStatus(Enum):
    """Status of an API version"""
    CURRENT = "current"       # The latest stable version
    STABLE = "stable"         # A stable version that is still supported
    DEPRECATED = "deprecated" # A version that is deprecated but still works
    SUNSET = "sunset"         # A version that is no longer supported


class APIVersion:
    """Represents a specific API version"""
    
    def __init__(
        self,
        version: str,
        release_date: datetime,
        status: VersionStatus = VersionStatus.STABLE,
        sunset_date: Optional[datetime] = None,
        description: str = "",
    ):
        self.version = version
        self.release_date = release_date
        self.status = status
        self.sunset_date = sunset_date
        self.description = description
        self.breaking_changes: List[str] = []
        self.new_features: List[str] = []
        self.bug_fixes: List[str] = []
        
    def add_breaking_change(self, description: str) -> None:
        """Add a breaking change to this version"""
        self.breaking_changes.append(description)
        
    def add_new_feature(self, description: str) -> None:
        """Add a new feature to this version"""
        self.new_features.append(description)
        
    def add_bug_fix(self, description: str) -> None:
        """Add a bug fix to this version"""
        self.bug_fixes.append(description)
        
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "version": self.version,
            "release_date": self.release_date.isoformat(),
            "status": self.status.value,
            "sunset_date": self.sunset_date.isoformat() if self.sunset_date else None,
            "description": self.description,
            "breaking_changes": self.breaking_changes,
            "new_features": self.new_features,
            "bug_fixes": self.bug_fixes,
        }


class VersionManager:
    """
    Manages API versions and provides utilities for version-related operations.
    """
    
    def __init__(self):
        self.versions: Dict[str, APIVersion] = {}
        self.current_version: str = "v1"
        self.deprecated_versions: Set[str] = set()
        self.sunset_versions: Set[str] = set()
        
    def register_version(self, version: APIVersion) -> None:
        """Register a new API version"""
        self.versions[version.version] = version
        
        # Update status tracking sets
        if version.status == VersionStatus.CURRENT:
            self.current_version = version.version
        elif version.status == VersionStatus.DEPRECATED:
            self.deprecated_versions.add(version.version)
        elif version.status == VersionStatus.SUNSET:
            self.sunset_versions.add(version.version)
            
    def get_version(self, version: str) -> Optional[APIVersion]:
        """Get information about a specific version"""
        return self.versions.get(version)
    
    def get_all_versions(self) -> List[APIVersion]:
        """Get all registered versions"""
        return list(self.versions.values())
    
    def is_version_supported(self, version: str) -> bool:
        """Check if a version is still supported (not sunset)"""
        return version in self.versions and version not in self.sunset_versions
    
    def is_version_deprecated(self, version: str) -> bool:
        """Check if a version is deprecated"""
        return version in self.deprecated_versions
    
    def get_current_version(self) -> str:
        """Get the current (latest) API version"""
        return self.current_version
    
    def deprecate_version(self, version: str, sunset_date: Optional[datetime] = None) -> None:
        """Mark a version as deprecated with an optional sunset date"""
        if version not in self.versions:
            raise ValueError(f"Version {version} is not registered")
            
        api_version = self.versions[version]
        api_version.status = VersionStatus.DEPRECATED
        
        if sunset_date:
            api_version.sunset_date = sunset_date
            
        self.deprecated_versions.add(version)
        
    def sunset_version(self, version: str) -> None:
        """Mark a version as sunset (no longer supported)"""
        if version not in self.versions:
            raise ValueError(f"Version {version} is not registered")
            
        api_version = self.versions[version]
        api_version.status = VersionStatus.SUNSET
        
        # Remove from deprecated set if it was there
        if version in self.deprecated_versions:
            self.deprecated_versions.remove(version)
            
        self.sunset_versions.add(version)


# Create a global instance of the version manager
version_manager = VersionManager()

# Initialize with v1 as a stable version
v1 = APIVersion(
    version="v1",
    release_date=datetime(2023, 1, 1),
    status=VersionStatus.STABLE,
    description="Initial API version",
)
v1.add_new_feature("Core API functionality")
v1.add_new_feature("Authentication and authorization")
v1.add_new_feature("Module system")
v1.add_new_feature("Content pack management")
v1.add_new_feature("Timeline events")
v1.add_new_feature("WebSocket support for real-time updates")

version_manager.register_version(v1)

# Add v2 as the current version
v2 = APIVersion(
    version="v2",
    release_date=datetime(2023, 7, 1),
    status=VersionStatus.CURRENT,
    description="Enhanced API version with improved module introspection and health checks",
)
v2.add_new_feature("Enhanced health check endpoint with detailed system status")
v2.add_new_feature("Module introspection API for discovering available tools")
v2.add_new_feature("Improved error handling and reporting")
v2.add_new_feature("Support for header-based versioning")

version_manager.register_version(v2)


class VersionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle API versioning via headers and add version headers to responses.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and handle versioning"""
        # Skip non-API requests
        if not request.url.path.startswith("/api"):
            return await call_next(request)
        
        # Extract version from URL path or header
        path_parts = request.url.path.split("/")
        url_version = None
        
        # Check if URL contains version (e.g., /api/v2/...)
        for part in path_parts:
            if part.startswith("v") and len(part) > 1 and part[1:].isdigit():
                url_version = part
                break
        
        # Get version from header if present
        header_version = request.headers.get("X-API-Version")
        
        # Determine which version to use
        version = url_version or header_version or version_manager.get_current_version()
        
        # Check if version is supported
        if not version_manager.is_version_supported(version):
            return Response(
                content=f"API version {version} is no longer supported. Please upgrade to a newer version.",
                status_code=410,  # Gone
                media_type="text/plain",
            )
        
        # Add version to request state for handlers to use
        request.state.api_version = version
        
        # Process the request
        response = await call_next(request)
        
        # Add version headers to response
        response.headers["X-API-Version"] = version
        
        # Add deprecation warning if applicable
        if version_manager.is_version_deprecated(version):
            api_version = version_manager.get_version(version)
            if api_version and api_version.sunset_date:
                response.headers["X-API-Deprecated"] = "true"
                response.headers["X-API-Sunset-Date"] = api_version.sunset_date.isoformat()
                response.headers["X-API-Current-Version"] = version_manager.get_current_version()
        
        return response


def get_api_version(
    request: Request,
    x_api_version: Optional[str] = Header(None, alias="X-API-Version"),
) -> str:
    """
    Dependency to extract API version from request.
    
    Order of precedence:
    1. URL path version (e.g., /api/v2/...)
    2. X-API-Version header
    3. Default to current version
    
    Returns:
        The API version to use
    """
    # Use version from request state (set by middleware)
    if hasattr(request.state, "api_version"):
        return request.state.api_version
    
    # Extract version from URL path
    path_parts = request.url.path.split("/")
    for part in path_parts:
        if part.startswith("v") and len(part) > 1 and part[1:].isdigit():
            return part
    
    # Use header version if present
    if x_api_version:
        return x_api_version
    
    # Default to current version
    return version_manager.get_current_version()


def create_version_router() -> APIRouter:
    """
    Create a router with version-related endpoints.
    """
    router = APIRouter(prefix="/api", tags=["API Versioning"])
    
    @router.get("/versions")
    async def get_api_versions():
        """Get information about all API versions"""
        versions = [v.to_dict() for v in version_manager.get_all_versions()]
        return {
            "versions": versions,
            "current_version": version_manager.get_current_version(),
        }
    
    @router.get("/versions/{version}")
    async def get_api_version_info(version: str):
        """Get information about a specific API version"""
        api_version = version_manager.get_version(version)
        if not api_version:
            raise HTTPException(status_code=404, detail=f"API version {version} not found")
        
        return api_version.to_dict()
    
    return router