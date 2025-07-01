"""
API Routes for v2 of the API.

This module contains the API routes for v2 of the API, which includes
all the functionality of v1 plus new features and improvements.
"""

import logging
import inspect
from fastapi import APIRouter, Path, HTTPException, Depends, Request
from typing import Dict, Any, List, Union, get_origin, get_args, Annotated
from sqlmodel import Session

from .module_loader import ModuleLoader
from .state_manager import state_manager
from .modules.timeline.tool import log_tool_execution, log_system_event, log_error
from .auth import (
    get_current_user,
    get_current_user_or_service,
    log_audit_event,
    get_client_info,
)
from .rbac import require_permission, require_permission_or_service
from .models import User
from .database import get_session
from .version_manager import get_api_version


def create_api_routes_v2(
    module_loader: ModuleLoader, content_pack_manager=None
) -> APIRouter:
    """
    Creates and returns the API router for v2, wiring up the endpoints
    to the loaded modules.
    """
    router = APIRouter(prefix="/api/v2")

    def require_admin(current_user: User):
        """Helper function to check if user is admin"""
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403, detail="Only administrators can perform this action"
            )

    # --- UI Endpoints ---

    @router.get("/ui/layout")
    def get_ui_layout(
        current_user: Annotated[User, Depends(get_current_user_or_service)],
    ) -> Dict[str, Any]:
        """
        Returns the full UI schema for all loaded modules.
        The frontend uses this to dynamically build its layout.
        """
        return {"modules": list(module_loader.get_schemas().values())}

    @router.get("/{module_name}/state")
    def get_module_state(
        module_name: str,
        current_user: Annotated[User, Depends(get_current_user_or_service)],
    ) -> Dict[str, Any]:
        """
        Returns the current state of a module.
        """
        # Check if the module exists
        if module_name not in module_loader.modules:
            raise HTTPException(
                status_code=404, detail=f"Module {module_name} not found"
            )

        # Get the module state
        state = state_manager.get(module_name) or {}
        return state

    @router.post("/{module_name}/state")
    def update_module_state(
        module_name: str,
        state_update: Dict[str, Any],
        current_user: Annotated[User, Depends(get_current_user_or_service)],
    ) -> Dict[str, Any]:
        """
        Updates the state of a module.
        """
        # Check if the module exists
        if module_name not in module_loader.modules:
            raise HTTPException(
                status_code=404, detail=f"Module {module_name} not found"
            )

        # Get the current state
        current_state = state_manager.get(module_name) or {}

        # Update the state
        current_state.update(state_update)
        state_manager.set(module_name, current_state)

        # Log the state update
        log_system_event(
            title=f"Module State Updated: {module_name}",
            description=f"The state of module {module_name} was updated.",
        )

        return current_state

    # --- Tool Execution Endpoint ---

    @router.post("/execute")
    async def execute_tool(
        request: Request,
        tool_request: Dict[str, Any],
        current_user: Annotated[User, Depends(get_current_user_or_service)],
        session: Session = Depends(get_session),
    ) -> Dict[str, Any]:
        """
        Executes a tool with the given parameters.
        """
        # Extract tool name and parameters
        tool_name = tool_request.get("tool_name")
        parameters = tool_request.get("parameters", {})

        # Validate tool name
        if not tool_name:
            raise HTTPException(status_code=400, detail="Tool name is required")

        # Check if the tool exists
        if "." not in tool_name:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tool name format: {tool_name}. Expected format: module_name.tool_name",
            )

        module_name, tool_method = tool_name.split(".", 1)

        if module_name not in module_loader.modules:
            raise HTTPException(
                status_code=404, detail=f"Module {module_name} not found"
            )

        module = module_loader.modules[module_name]
        if not hasattr(module, tool_method):
            raise HTTPException(
                status_code=404,
                detail=f"Tool {tool_method} not found in module {module_name}",
            )

        # Get the tool method
        tool = getattr(module, tool_method)

        # Check if the tool is callable
        if not callable(tool):
            raise HTTPException(
                status_code=400,
                detail=f"{tool_name} is not callable",
            )

        # Check RBAC permissions
        if hasattr(tool, "required_permission"):
            permission = tool.required_permission
            if isinstance(current_user, User):
                require_permission(current_user, permission)
            else:
                # It's a service
                require_permission_or_service(None, permission)

        # Get client information for logging
        client_info = get_client_info(request)

        # Log the tool execution
        log_tool_execution(
            tool_name=tool_name,
            parameters=parameters,
            user_id=current_user.id if isinstance(current_user, User) else None,
            client_info=client_info,
        )

        # Log audit event
        if isinstance(current_user, User):
            log_audit_event(
                user=current_user,
                action=f"execute_tool:{tool_name}",
                resource_type="tool",
                resource_id=tool_name,
                details={"parameters": parameters},
                client_info=client_info,
                session=session,
            )

        try:
            # Execute the tool
            result = tool(**parameters)
            return {"result": result}
        except Exception as e:
            # Log the error
            log_error(
                title=f"Tool Execution Error: {tool_name}",
                description=f"Error executing tool {tool_name}: {str(e)}",
                error_type=type(e).__name__,
                error_details=str(e),
            )
            raise HTTPException(status_code=500, detail=str(e))

    # --- V2 Specific Endpoints ---

    @router.get("/health")
    async def health_check():
        """
        Health check endpoint for v2 API.
        Returns detailed health information about the system.
        """
        return {
            "status": "healthy",
            "version": "v2",
            "modules": {
                name: {
                    "loaded": True,
                    "schema_available": name in module_loader.schemas,
                }
                for name in module_loader.modules
            },
            "state_manager": {"active": True},
        }

    @router.get("/modules")
    async def get_modules(
        current_user: Annotated[User, Depends(get_current_user_or_service)],
    ):
        """
        Get information about all loaded modules.
        """
        modules = {}
        for name, module in module_loader.modules.items():
            # Get all public methods (tools)
            tools = []
            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue

                attr = getattr(module, attr_name)
                if callable(attr):
                    # Get function signature
                    try:
                        sig = inspect.signature(attr)
                        tools.append(
                            {
                                "name": attr_name,
                                "full_name": f"{name}.{attr_name}",
                                "parameters": [
                                    {
                                        "name": param_name,
                                        "required": param.default
                                        == inspect.Parameter.empty,
                                        "default": (
                                            None
                                            if param.default == inspect.Parameter.empty
                                            else param.default
                                        ),
                                        "type": (
                                            str(param.annotation)
                                            if param.annotation
                                            != inspect.Parameter.empty
                                            else "any"
                                        ),
                                    }
                                    for param_name, param in sig.parameters.items()
                                ],
                                "required_permission": getattr(
                                    attr, "required_permission", None
                                ),
                            }
                        )
                    except Exception as e:
                        logging.warning(
                            f"Failed to inspect function {name}.{attr_name}: {e}"
                        )

            modules[name] = {"tools": tools, "schema": module_loader.schemas.get(name)}

        return {"modules": modules}

    return router
