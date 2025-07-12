"""
Health check API endpoints for IntentVerse.

Provides REST API endpoints for monitoring database and system health.
"""

import logging
import time
from typing import Dict, Any, Annotated, Union
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .models import User
from .auth import get_current_user_or_service
from .rbac import require_permission
from .database import get_database
from .database.validation import validate_database_config, test_database_connection


class HealthStatus(BaseModel):
    """Health status response model."""
    status: str  # "healthy", "unhealthy", "degraded"
    timestamp: float
    checks: Dict[str, Any]


class DatabaseHealthResponse(BaseModel):
    """Database health response model."""
    status: str
    connection_time_ms: float
    database_type: str
    connection_error: str = None
    version: str = None
    active_connections: int = None
    file_size_bytes: int = None
    info_error: str = None
    timestamp: float


class ConfigValidationResponse(BaseModel):
    """Configuration validation response model."""
    valid: bool
    errors: list[str]
    warnings: list[str]


def create_health_router() -> APIRouter:
    """Create and configure the health check API router."""
    router = APIRouter(prefix="/api/v2/health", tags=["Health Checks"])
    
    @router.get("/", response_model=HealthStatus)
    async def get_system_health():
        """
        Get overall system health status.
        
        This endpoint is public and can be used for load balancer health checks.
        """
        start_time = time.time()
        checks = {}
        overall_status = "healthy"
        
        # Database health check
        try:
            database = get_database()
            db_health = database.get_health_status()
            checks["database"] = db_health
            
            if db_health["status"] != "healthy":
                overall_status = "unhealthy"
                
        except Exception as e:
            checks["database"] = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
            overall_status = "unhealthy"
        
        # Migration status check
        try:
            database = get_database()
            migration_status = database.get_migration_status()
            checks["migrations"] = {
                "status": "healthy" if migration_status["validation"]["valid"] else "degraded",
                "current_version": migration_status["current_version"],
                "pending_migrations": migration_status["pending_migrations"],
                "validation_issues": migration_status["validation"]["issues"]
            }
            
            if not migration_status["validation"]["valid"]:
                overall_status = "degraded" if overall_status == "healthy" else overall_status
                
        except Exception as e:
            checks["migrations"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_status = "unhealthy"
        
        # System uptime check
        checks["system"] = {
            "status": "healthy",
            "uptime_seconds": time.time() - start_time,
            "timestamp": time.time()
        }
        
        return HealthStatus(
            status=overall_status,
            timestamp=time.time(),
            checks=checks
        )
    
    @router.get("/database", response_model=DatabaseHealthResponse)
    async def get_database_health(
        current_user_or_service: Annotated[
            Union[User, str], Depends(get_current_user_or_service)
        ] = None,
    ):
        """
        Get detailed database health status.
        
        Requires authentication for detailed database information.
        """
        try:
            database = get_database()
            health_status = database.get_health_status()
            
            return DatabaseHealthResponse(**health_status)
            
        except Exception as e:
            logging.error(f"Failed to get database health: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get database health: {str(e)}"
            )
    
    @router.post("/database/test")
    async def test_database_connection_endpoint(
        timeout: float = 30.0,
        current_user_or_service: Annotated[
            Union[User, str], Depends(get_current_user_or_service)
        ] = None,
    ):
        """
        Test database connection with optional timeout.
        
        Args:
            timeout: Connection timeout in seconds (default: 30.0)
            
        Requires authentication.
        """
        try:
            database = get_database()
            success, error = database.test_connection(timeout)
            
            return {
                "success": success,
                "error": error,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logging.error(f"Failed to test database connection: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to test database connection: {str(e)}"
            )
    
    @router.get("/database/config/validate", response_model=ConfigValidationResponse)
    async def validate_database_config_endpoint(
        current_user_or_service: Annotated[
            Union[User, str], Depends(get_current_user_or_service)
        ],
    ):
        """
        Validate current database configuration.
        
        Requires admin permissions.
        """
        # Check admin permissions
        if isinstance(current_user_or_service, User):
            require_permission(current_user_or_service, "admin.database")
        
        try:
            database = get_database()
            is_valid, errors, warnings = validate_database_config(database.config)
            
            return ConfigValidationResponse(
                valid=is_valid,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logging.error(f"Failed to validate database config: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to validate database config: {str(e)}"
            )
    
    @router.get("/readiness")
    async def readiness_check():
        """
        Kubernetes/Docker readiness probe endpoint.
        
        Returns 200 if the service is ready to accept traffic.
        """
        try:
            # Check database connectivity
            database = get_database()
            success, error = database.test_connection(timeout=5.0)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Database not ready: {error}"
                )
            
            return {"status": "ready", "timestamp": time.time()}
            
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Readiness check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service not ready: {str(e)}"
            )
    
    @router.get("/liveness")
    async def liveness_check():
        """
        Kubernetes/Docker liveness probe endpoint.
        
        Returns 200 if the service is alive (basic functionality works).
        """
        try:
            # Basic functionality check - just verify we can import and access basic components
            from .database import get_database
            database = get_database()
            
            # Don't test actual connectivity for liveness - just verify the service is running
            return {"status": "alive", "timestamp": time.time()}
            
        except Exception as e:
            logging.error(f"Liveness check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service not alive: {str(e)}"
            )
    
    return router