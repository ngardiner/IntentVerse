"""
Database migration API endpoints for IntentVerse.

Provides REST API endpoints for managing database migrations.
"""

import logging
from typing import Dict, Any, Annotated, Union
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .models import User
from .auth import get_current_user_or_service
from .rbac import require_permission
from .database import get_database
from .database.migrations import get_migration_manager


class MigrationStatusResponse(BaseModel):
    """Response model for migration status."""
    current_version: str = None
    pending_migrations: int
    pending_migration_list: list[str]
    validation: Dict[str, Any]


class MigrationResponse(BaseModel):
    """Response model for migration operations."""
    success: bool
    message: str
    details: Dict[str, Any] = None


def create_migration_router() -> APIRouter:
    """Create and configure the migration API router."""
    router = APIRouter(prefix="/api/v2/admin/migrations", tags=["Database Migrations"])
    
    @router.get("/status", response_model=MigrationStatusResponse)
    async def get_migration_status(
        current_user_or_service: Annotated[
            Union[User, str], Depends(get_current_user_or_service)
        ],
    ):
        """
        Get the current database migration status.
        
        Requires admin permissions.
        """
        # Check admin permissions
        if isinstance(current_user_or_service, User):
            require_permission(current_user_or_service, "admin.database")
        
        try:
            database = get_database()
            status = database.get_migration_status()
            
            return MigrationStatusResponse(
                current_version=status["current_version"],
                pending_migrations=status["pending_migrations"],
                pending_migration_list=status["pending_migration_list"],
                validation=status["validation"]
            )
            
        except Exception as e:
            logging.error(f"Failed to get migration status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get migration status: {str(e)}"
            )
    
    @router.post("/migrate", response_model=MigrationResponse)
    async def run_migrations(
        target_version: str = None,
        current_user_or_service: Annotated[
            Union[User, str], Depends(get_current_user_or_service)
        ] = None,
    ):
        """
        Run database migrations.
        
        Args:
            target_version: Optional target version to migrate to (defaults to latest)
            
        Requires admin permissions.
        """
        # Check admin permissions
        if isinstance(current_user_or_service, User):
            require_permission(current_user_or_service, "admin.database")
        
        try:
            database = get_database()
            migration_manager = get_migration_manager(database)
            
            if target_version:
                success = migration_manager.migrate_to_version(target_version)
                message = f"Migration to version {target_version}"
            else:
                success = migration_manager.migrate_to_latest()
                message = "Migration to latest version"
            
            if success:
                message += " completed successfully"
                
                # Get updated status
                status_info = database.get_migration_status()
                
                return MigrationResponse(
                    success=True,
                    message=message,
                    details={
                        "current_version": status_info["current_version"],
                        "pending_migrations": status_info["pending_migrations"]
                    }
                )
            else:
                message += " failed"
                return MigrationResponse(
                    success=False,
                    message=message
                )
                
        except Exception as e:
            logging.error(f"Migration failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Migration failed: {str(e)}"
            )
    
    @router.post("/validate", response_model=MigrationResponse)
    async def validate_migrations(
        current_user_or_service: Annotated[
            Union[User, str], Depends(get_current_user_or_service)
        ],
    ):
        """
        Validate migration integrity.
        
        Requires admin permissions.
        """
        # Check admin permissions
        if isinstance(current_user_or_service, User):
            require_permission(current_user_or_service, "admin.database")
        
        try:
            database = get_database()
            migration_manager = get_migration_manager(database)
            
            validation = migration_manager.validate_migrations()
            
            return MigrationResponse(
                success=validation["valid"],
                message="Migration validation completed",
                details=validation
            )
            
        except Exception as e:
            logging.error(f"Migration validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Migration validation failed: {str(e)}"
            )
    
    @router.get("/history")
    async def get_migration_history(
        current_user_or_service: Annotated[
            Union[User, str], Depends(get_current_user_or_service)
        ],
    ):
        """
        Get migration history.
        
        Requires admin permissions.
        """
        # Check admin permissions
        if isinstance(current_user_or_service, User):
            require_permission(current_user_or_service, "admin.database")
        
        try:
            database = get_database()
            migration_manager = get_migration_manager(database)
            
            history = migration_manager.get_migration_history()
            
            return {
                "migrations": [
                    {
                        "version": record.version,
                        "migration_name": record.migration_name,
                        "applied_at": record.applied_at.isoformat(),
                        "execution_time_ms": record.execution_time_ms,
                        "success": record.success,
                        "error_message": record.error_message
                    }
                    for record in history
                ]
            }
            
        except Exception as e:
            logging.error(f"Failed to get migration history: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get migration history: {str(e)}"
            )
    
    @router.get("/list")
    async def list_migrations(
        current_user_or_service: Annotated[
            Union[User, str], Depends(get_current_user_or_service)
        ],
    ):
        """
        List all available migrations.
        
        Requires admin permissions.
        """
        # Check admin permissions
        if isinstance(current_user_or_service, User):
            require_permission(current_user_or_service, "admin.database")
        
        try:
            database = get_database()
            migration_manager = get_migration_manager(database)
            current_version = migration_manager.get_current_version()
            
            migrations = []
            for migration in migration_manager.migrations:
                is_applied = (current_version and 
                            migration_manager._version_to_tuple(migration.version) <= 
                            migration_manager._version_to_tuple(current_version))
                
                migrations.append({
                    "version": migration.version,
                    "name": migration.name,
                    "description": migration.description,
                    "checksum": migration.checksum,
                    "applied": is_applied
                })
            
            return {
                "current_version": current_version,
                "migrations": migrations
            }
            
        except Exception as e:
            logging.error(f"Failed to list migrations: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list migrations: {str(e)}"
            )
    
    return router