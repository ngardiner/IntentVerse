import logging
import inspect
import tempfile
import os
from fastapi import APIRouter, Path, HTTPException, Depends, Request, UploadFile, File
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
from .database_compat import get_session
from .rate_limiter import limiter, create_rate_limit_function


def create_api_routes(
    module_loader: ModuleLoader, content_pack_manager=None
) -> APIRouter:
    """
    Creates and returns the API router, wiring up the endpoints
    to the loaded modules.
    """
    router = APIRouter(prefix="/api/v1")

    def require_admin(current_user: User):
        """Helper function to check if user is admin"""
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403, detail="Only administrators can perform this action"
            )

    # --- UI Endpoints ---

    @router.get("/ui/layout")
    def get_ui_layout(
        request: Request,
        current_user: Annotated[User, Depends(get_current_user_or_service)],
    ) -> Dict[str, Any]:
        """
        Returns the full UI schema for all loaded modules.
        The frontend uses this to dynamically build its layout.
        """
        return {"modules": list(module_loader.get_schemas().values())}

    @router.get("/{module_name}/state")
    def get_module_state(
        request: Request,
        current_user: Annotated[User, Depends(get_current_user_or_service)],
        module_name: str = Path(..., title="The name of the module"),
    ) -> Dict[str, Any]:
        """
        Returns the current state for a specific module.
        Used by UI components to fetch their data.
        """
        state = state_manager.get(module_name)
        if state is None:
            raise HTTPException(
                status_code=404, detail=f"No state found for module: {module_name}"
            )
        return state

    # --- MCP Endpoints ---

    @router.get("/tools/manifest")
    def get_tools_manifest(
        request: Request,
        current_user_or_service: Annotated[
            Union[User, str], Depends(get_current_user_or_service)
        ],
    ) -> List[Dict[str, Any]]:
        """
        Inspects all loaded tool classes and returns a simplified manifest.
        The MCP Interface uses this to dynamically reconstruct function signatures.
        """
        manifest = []
        tools = module_loader.get_all_tools()

        for module_name, tool_instance in tools.items():
            for method_name, method in inspect.getmembers(
                tool_instance, inspect.ismethod
            ):
                if not method_name.startswith("_"):
                    full_tool_name = f"{module_name}.{method_name}"
                    description = inspect.getdoc(method) or "No description available."

                    sig = inspect.signature(method)
                    parameters_info = []
                    for param in sig.parameters.values():
                        if param.name == "self":
                            continue

                        param_annotation_details = {
                            "base_type": "Any",  # e.g., 'str', 'int', 'List'
                            "is_optional": False,
                            "union_types": [],  # List of string representations if it's a Union
                        }

                        if param.annotation != inspect.Parameter.empty:
                            param_origin = get_origin(param.annotation)
                            param_args = get_args(param.annotation)

                            if param_origin is Union:
                                # It's a Union type (including Optional which is Union[T, NoneType])
                                non_none_args = [
                                    arg for arg in param_args if arg is not type(None)
                                ]
                                param_annotation_details["is_optional"] = (
                                    type(None) in param_args
                                )

                                # Store string representations of all types in the Union
                                param_annotation_details["union_types"] = [
                                    (
                                        arg.__name__
                                        if hasattr(arg, "__name__")
                                        else str(arg)
                                    )
                                    for arg in param_args
                                ]

                                if len(non_none_args) == 1:
                                    # This is typically an Optional[X] where X is the base_type
                                    base_arg = non_none_args[0]
                                    param_annotation_details["base_type"] = (
                                        base_arg.__name__
                                        if hasattr(base_arg, "__name__")
                                        else str(base_arg)
                                    )
                                elif len(non_none_args) > 1:
                                    # A more complex Union (e.g., Union[str, int])
                                    param_annotation_details["base_type"] = "Union"
                                else:
                                    param_annotation_details["base_type"] = (
                                        "NoneType"  # Only None in Union, or empty (unlikely for params)
                                    )
                            else:
                                # Not a Union. Get the simple name.
                                param_annotation_details["base_type"] = (
                                    param.annotation.__name__
                                    if hasattr(param.annotation, "__name__")
                                    else str(param.annotation)
                                )

                        parameters_info.append(
                            {
                                "name": param.name,
                                "annotation_details": param_annotation_details,
                                "required": param.default == inspect.Parameter.empty,
                            }
                        )

                    manifest.append(
                        {
                            "name": full_tool_name,
                            "description": description,
                            "parameters": parameters_info,
                        }
                    )
        return manifest

    @router.post("/execute")
    @limiter.limit("60/minute")
    def execute_tool(
        request: Request,
        payload: Dict[str, Any],
        current_user_or_service: Annotated[
            Union[User, str], Depends(get_current_user_or_service)
        ],
        session: Annotated[Session, Depends(get_session)],
    ) -> Dict[str, Any]:
        """
        The main endpoint for executing a tool command from the MCP interface.
        The MCP interface will call this endpoint.
        """
        ip_address, user_agent = get_client_info(request)
        tool_full_name = payload.get("tool_name")
        parameters = payload.get("parameters", {})

        # Determine user info for audit logging
        if isinstance(current_user_or_service, str):  # Service authentication
            user_id = None
            username = "service"
        else:  # User authentication
            user_id = current_user_or_service.id
            username = current_user_or_service.username

        if not tool_full_name or "." not in tool_full_name:
            log_audit_event(
                session=session,
                user_id=user_id,
                username=username,
                action="execute_tool_failed",
                details={
                    "reason": "invalid_tool_name_format",
                    "provided_tool_name": tool_full_name,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                status="failure",
                error_message="`tool_name` is required in the format 'module.method'.",
            )
            raise HTTPException(
                status_code=400,
                detail="`tool_name` is required in the format 'module.method'.",
            )

        try:
            module_name, method_name = tool_full_name.split(".", 1)
        except ValueError:
            log_audit_event(
                session=session,
                user_id=user_id,
                username=username,
                action="execute_tool_failed",
                details={
                    "reason": "invalid_tool_name_format",
                    "provided_tool_name": tool_full_name,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                status="failure",
                error_message="`tool_name` is invalid. Expected format 'module.method'.",
            )
            raise HTTPException(
                status_code=400,
                detail="`tool_name` is invalid. Expected format 'module.method'.",
            )

        # Check permissions for tool execution (only for user authentication, not service)
        if isinstance(current_user_or_service, User):
            from .rbac import PermissionChecker

            checker = PermissionChecker(session)

            # Map module names to required permissions
            module_permissions = {
                "filesystem": "filesystem.read",  # Default to read, specific methods may require write/delete
                "database": "database.read",  # Default to read, specific methods may require write/execute
                "email": "email.read",  # Default to read, send methods require email.send
                "web_search": "web_search.search",
                "memory": "memory.read",  # Default to read, write methods require memory.write
                "timeline": "timeline.read",  # Default to read, write methods require timeline.write
                "content_packs": "content_packs.read",  # Default to read, other methods require specific permissions
            }

            # Check for more specific permissions based on method name
            if module_name == "filesystem":
                if method_name in ["write_file", "create_directory"]:
                    required_permission = "filesystem.write"
                elif method_name in ["delete_file", "delete_directory"]:
                    required_permission = "filesystem.delete"
                else:
                    required_permission = "filesystem.read"
            elif module_name == "database":
                if method_name in ["execute_query", "execute_script"]:
                    required_permission = "database.execute"
                elif method_name in ["insert_data", "update_data", "delete_data"]:
                    required_permission = "database.write"
                else:
                    required_permission = "database.read"
            elif module_name == "email":
                if method_name in ["send_email"]:
                    required_permission = "email.send"
                else:
                    required_permission = "email.read"
            elif module_name == "memory":
                if method_name in ["store", "update", "delete"]:
                    required_permission = "memory.write"
                else:
                    required_permission = "memory.read"
            elif module_name == "timeline":
                if method_name in ["add_event", "log_event"]:
                    required_permission = "timeline.write"
                else:
                    required_permission = "timeline.read"
            else:
                # Use default permission for the module
                required_permission = module_permissions.get(
                    module_name, f"{module_name}.*"
                )

            # Check if user has the required permission
            if not checker.has_permission(current_user_or_service, required_permission):
                log_audit_event(
                    session=session,
                    user_id=user_id,
                    username=username,
                    action="execute_tool_failed",
                    resource_type="tool",
                    resource_name=tool_full_name,
                    details={
                        "reason": "insufficient_permissions",
                        "required_permission": required_permission,
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status="failure",
                    error_message=f"Insufficient permissions. Required: {required_permission}",
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions to execute '{tool_full_name}'. Required: {required_permission}",
                )

        tool_instance = module_loader.get_tool(module_name)

        if not tool_instance or not hasattr(tool_instance, method_name):
            log_audit_event(
                session=session,
                user_id=user_id,
                username=username,
                action="execute_tool_failed",
                resource_type="tool",
                resource_name=tool_full_name,
                details={
                    "reason": "tool_not_found",
                    "module_name": module_name,
                    "method_name": method_name,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                status="failure",
                error_message=f"Tool '{tool_full_name}' not found.",
            )
            raise HTTPException(
                status_code=404, detail=f"Tool '{tool_full_name}' not found."
            )

        # Check if the specific tool is enabled
        if not module_loader._is_tool_enabled(module_name, method_name, session):
            log_audit_event(
                session=session,
                user_id=user_id,
                username=username,
                action="execute_tool_failed",
                resource_type="tool",
                resource_name=tool_full_name,
                details={
                    "reason": "tool_disabled",
                    "module_name": module_name,
                    "method_name": method_name,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                status="failure",
                error_message=f"Tool '{tool_full_name}' is disabled.",
            )
            raise HTTPException(
                status_code=403, detail=f"Tool '{tool_full_name}' is disabled."
            )

        try:
            method_to_call = getattr(tool_instance, method_name)

            # Validate required parameters are present
            sig = inspect.signature(method_to_call)
            for param in sig.parameters.values():
                if (
                    param.name != "self"
                    and param.default == inspect.Parameter.empty
                    and param.name not in parameters
                ):
                    log_audit_event(
                        session=session,
                        user_id=user_id,
                        username=username,
                        action="execute_tool_failed",
                        resource_type="tool",
                        resource_name=tool_full_name,
                        details={
                            "reason": "missing_required_parameter",
                            "missing_parameter": param.name,
                            "parameters": parameters,
                        },
                        ip_address=ip_address,
                        user_agent=user_agent,
                        status="failure",
                        error_message=f"Missing required parameter for '{tool_full_name}': {param.name}",
                    )
                    raise HTTPException(
                        status_code=422,
                        detail=f"Missing required parameter for '{tool_full_name}': {param.name}",
                    )

            # Call the tool method with the provided parameters
            result = method_to_call(**parameters)

            logging.info(
                f"Executed tool '{tool_full_name}' with parameters: {parameters}"
            )

            # Log successful tool execution to audit log
            log_audit_event(
                session=session,
                user_id=user_id,
                username=username,
                action="execute_tool",
                resource_type="tool",
                resource_name=tool_full_name,
                details={"parameters": parameters, "result_status": "success"},
                ip_address=ip_address,
                user_agent=user_agent,
                status="success",
            )

            # Log the tool execution to the timeline
            log_tool_execution(
                tool_full_name, parameters, {"status": "success", "result": result}
            )

            return {"status": "success", "result": result}
        except HTTPException as e:
            # Log the error to audit log
            log_audit_event(
                session=session,
                user_id=user_id,
                username=username,
                action="execute_tool_failed",
                resource_type="tool",
                resource_name=tool_full_name,
                details={
                    "parameters": parameters,
                    "status_code": e.status_code,
                    "error_detail": e.detail,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                status="failure",
                error_message=f"HTTP Error: {e.detail}",
            )

            # Log the error to the timeline
            log_error(
                f"HTTP Error in tool '{tool_full_name}'",
                f"Status code {e.status_code}: {e.detail}",
                {"status_code": e.status_code, "detail": e.detail},
            )
            # Re-raise HTTP exceptions from the tool logic (e.g., file not found)
            raise e
        except Exception as e:
            # Catch any other unexpected errors from the tool execution
            logging.error(
                f"ERROR executing tool '{tool_full_name}': {e}", exc_info=True
            )

            # Log the error to audit log
            log_audit_event(
                session=session,
                user_id=user_id,
                username=username,
                action="execute_tool_failed",
                resource_type="tool",
                resource_name=tool_full_name,
                details={
                    "parameters": parameters,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                ip_address=ip_address,
                user_agent=user_agent,
                status="error",
                error_message=str(e),
            )

            # Log the error to the timeline
            log_error(
                f"Error executing tool '{tool_full_name}'",
                str(e),
                {"parameters": parameters, "error_type": type(e).__name__},
            )

            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while executing tool '{tool_full_name}': {str(e)}",
            )

    # --- Version and Compatibility Endpoints ---

    @router.get("/version")
    def get_app_version_info(
        current_user: Annotated[
            User, Depends(get_current_user_or_service)
        ],
    ) -> Dict[str, Any]:
        """
        Get current IntentVerse version information.
        """
        from .version_utils import get_version_info
        return get_version_info()

    @router.post("/compatibility/check")
    def check_content_pack_compatibility(
        request: Dict[str, Any],
        current_user: Annotated[
            User, Depends(get_current_user_or_service)
        ],
    ) -> Dict[str, Any]:
        """
        Check compatibility of content pack conditions against current version.
        """
        from .version_utils import get_app_version, check_compatibility_conditions
        
        compatibility_conditions = request.get("compatibility_conditions", [])
        app_version = get_app_version()
        
        is_compatible, reasons = check_compatibility_conditions(app_version, compatibility_conditions)
        
        return {
            "app_version": app_version,
            "compatible": is_compatible,
            "reasons": reasons,
            "conditions": compatibility_conditions
        }

    # --- Content Pack Management Endpoints ---

    if content_pack_manager:

        @router.get("/content-packs/available")
        def list_available_content_packs(
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.read"))
            ],
        ) -> List[Dict[str, Any]]:
            """
            Returns a list of all available content packs in the content_packs directory.
            """
            return content_pack_manager.list_available_content_packs()

        @router.get("/content-packs/loaded")
        def get_loaded_content_packs(
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.read"))
            ],
        ) -> List[Dict[str, Any]]:
            """
            Returns information about currently loaded content packs.
            """
            return content_pack_manager.get_loaded_content_packs()

        @router.post("/content-packs/export")
        def export_content_pack(
            request: Dict[str, Any],
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.create"))
            ],
        ) -> Dict[str, Any]:
            """
            Export current system state as a content pack.
            """
            from pathlib import Path

            filename = request.get("filename", "exported_content_pack.json")
            metadata = request.get("metadata", {})

            # Ensure filename ends with .json
            if not filename.endswith(".json"):
                filename += ".json"

            output_path = content_pack_manager.content_packs_dir / filename

            success = content_pack_manager.export_content_pack(output_path, metadata)

            if success:
                return {
                    "success": True,
                    "message": f"Content pack exported to {filename}",
                    "path": str(output_path),
                }
            else:
                raise HTTPException(
                    status_code=500, detail="Failed to export content pack"
                )

        @router.post("/content-packs/load")
        def load_content_pack_file(
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.install"))
            ],
            file: UploadFile = File(...),
        ) -> Dict[str, Any]:
            """
            Load a content pack from an uploaded file.
            """
            if not file.filename or not file.filename.endswith('.json'):
                raise HTTPException(status_code=400, detail="File must be a JSON file")

            try:
                # Create a temporary file to store the uploaded content
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    content = file.file.read().decode('utf-8')
                    temp_file.write(content)
                    temp_file_path = temp_file.name

                # Load the content pack from the temporary file
                user_id = current_user.id if isinstance(current_user, User) else None
                success = content_pack_manager.load_content_pack(temp_file_path, user_id)

                # Clean up the temporary file
                os.unlink(temp_file_path)

                if success:
                    # Try to get the pack name from the content
                    try:
                        import json
                        file.file.seek(0)  # Reset file pointer
                        content = file.file.read().decode('utf-8')
                        pack_data = json.loads(content)
                        pack_name = pack_data.get("metadata", {}).get("name", file.filename)
                    except:
                        pack_name = file.filename
                    
                    return {
                        "success": True,
                        "message": f"Content pack '{pack_name}' loaded successfully",
                    }
                else:
                    raise HTTPException(
                        status_code=422, detail=f"Failed to load content pack '{file.filename}'"
                    )
            except Exception as e:
                # Clean up the temporary file if it exists
                if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                raise HTTPException(
                    status_code=422, detail=f"Error processing content pack: {str(e)}"
                )

        @router.post("/content-packs/load-by-filename")
        def load_content_pack_by_filename(
            request: Dict[str, Any],
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.install"))
            ],
        ) -> Dict[str, Any]:
            """
            Load a content pack by filename from the content_packs directory.
            """
            filename = request.get("filename")
            if not filename:
                raise HTTPException(status_code=400, detail="Filename is required")

            success = content_pack_manager.load_content_pack_by_filename(filename)

            if success:
                return {
                    "success": True,
                    "message": f"Content pack '{filename}' loaded successfully",
                }
            else:
                raise HTTPException(
                    status_code=500, detail=f"Failed to load content pack '{filename}'"
                )

        @router.post("/content-packs/unload")
        def unload_content_pack(
            request: Dict[str, Any],
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.delete"))
            ],
        ) -> Dict[str, Any]:
            """
            Unload a content pack by filename or name.
            Note: This only removes it from the loaded packs tracking.
            State and database changes are not reverted.
            """
            identifier = request.get("identifier")
            if not identifier:
                raise HTTPException(
                    status_code=400,
                    detail="Pack identifier (filename or name) is required",
                )

            success = content_pack_manager.unload_content_pack(identifier)

            if success:
                return {
                    "status": "success",
                    "message": f"Content pack '{identifier}' unloaded successfully",
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Content pack '{identifier}' not found in loaded packs",
                )

        @router.post("/content-packs/clear-all")
        def clear_all_loaded_packs(
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.delete"))
            ],
        ) -> Dict[str, Any]:
            """
            Clear all loaded content packs from tracking.
            Note: This does not revert state or database changes.
            """
            success = content_pack_manager.clear_all_loaded_packs()

            if success:
                return {
                    "status": "success",
                    "message": "All loaded content packs cleared from tracking",
                }
            else:
                raise HTTPException(
                    status_code=500, detail="Failed to clear loaded content packs"
                )

        @router.get("/content-packs/preview/{filename}")
        def preview_content_pack_by_filename(
            filename: str,
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.read"))
            ],
        ) -> Dict[str, Any]:
            """
            Preview a content pack by filename without loading it, including validation and compatibility results.
            """
            preview_result = content_pack_manager.preview_content_pack(filename)

            if not preview_result["exists"]:
                raise HTTPException(
                    status_code=404, detail=f"Content pack '{filename}' not found"
                )

            # Add compatibility information
            if preview_result["content_pack"]:
                from .version_utils import get_app_version, check_compatibility_conditions
                
                content_pack = preview_result["content_pack"]
                metadata = content_pack.get("metadata", {})
                compatibility_conditions = metadata.get("compatibility_conditions", [])
                
                app_version = get_app_version()
                is_compatible, reasons = check_compatibility_conditions(app_version, compatibility_conditions)
                
                preview_result["compatibility"] = {
                    "app_version": app_version,
                    "compatible": is_compatible,
                    "reasons": reasons,
                    "conditions": compatibility_conditions,
                    "has_conditions": len(compatibility_conditions) > 0
                }

            return preview_result

        @router.post("/content-packs/preview")
        def preview_content_pack_file(
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.read"))
            ],
            file: UploadFile = File(...),
        ) -> Dict[str, Any]:
            """
            Preview a content pack from an uploaded file without loading it.
            """
            if not file.filename or not file.filename.endswith('.json'):
                raise HTTPException(status_code=400, detail="File must be a JSON file")

            try:
                # Read and parse the uploaded content
                content = file.file.read().decode('utf-8')
                import json
                content_pack = json.loads(content)
                
                # Perform detailed validation
                validation_result = content_pack_manager.validate_content_pack_detailed(content_pack)
                
                # Add compatibility information
                from .version_utils import get_app_version, check_compatibility_conditions
                
                metadata = content_pack.get("metadata", {})
                compatibility_conditions = metadata.get("compatibility_conditions", [])
                
                app_version = get_app_version()
                is_compatible, reasons = check_compatibility_conditions(app_version, compatibility_conditions)
                
                compatibility_info = {
                    "app_version": app_version,
                    "compatible": is_compatible,
                    "reasons": reasons,
                    "conditions": compatibility_conditions,
                    "has_conditions": len(compatibility_conditions) > 0
                }

                return {
                    "filename": file.filename,
                    "exists": True,
                    "content_pack": content_pack,
                    "validation": validation_result,
                    "compatibility": compatibility_info,
                    "preview": {
                        "metadata": metadata,
                        "has_variables": "variables" in content_pack,
                        "has_content_prompts": "content_prompts" in content_pack,
                        "has_usage_prompts": "usage_prompts" in content_pack,
                        "has_prompts": "prompts" in content_pack,
                        "has_database": "database" in content_pack,
                        "has_state": "state" in content_pack,
                    }
                }
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid JSON format: {str(e)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Error processing content pack: {str(e)}"
                )

        @router.post("/content-packs/validate")
        def validate_content_pack(
            request: Dict[str, Any],
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.read"))
            ],
        ) -> Dict[str, Any]:
            """
            Validate a content pack by filename and return detailed validation results.
            """
            filename = request.get("filename")
            if not filename:
                raise HTTPException(status_code=400, detail="Filename is required")

            preview_result = content_pack_manager.preview_content_pack(filename)

            if not preview_result["exists"]:
                raise HTTPException(
                    status_code=404, detail=f"Content pack '{filename}' not found"
                )

            return {"filename": filename, "validation": preview_result["validation"]}

        # --- Content Pack Variable Management Endpoints ---

        @router.get("/content-packs/{pack_name}/variables")
        def get_pack_variables(
            pack_name: str,
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.read"))
            ],
            session: Annotated[Session, Depends(get_session)],
        ) -> Dict[str, Any]:
            """
            Get all variable overrides for a specific content pack and user.
            """
            from .version_utils import supports_content_pack_variables
            
            if not supports_content_pack_variables():
                raise HTTPException(
                    status_code=501, 
                    detail="Content pack variables are not supported in this version"
                )
            
            # For service authentication, we can't get user-specific variables
            if isinstance(current_user, str):
                raise HTTPException(
                    status_code=400,
                    detail="User authentication required for variable management"
                )
            
            try:
                # Check if pack exists
                loaded_packs = content_pack_manager.get_loaded_content_packs()
                pack_exists = any(pack["name"] == pack_name for pack in loaded_packs)
                if not pack_exists:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Content pack '{pack_name}' not found"
                    )
                
                variables = content_pack_manager.get_pack_variables(pack_name, current_user.id, session)
                return {
                    "status": "success",
                    "pack_name": pack_name,
                    "variables": variables,
                    "variable_count": len(variables)
                }
            except HTTPException:
                raise
            except Exception as e:
                logging.error(f"Error getting variables for pack '{pack_name}': {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get variables for content pack '{pack_name}'"
                )

        @router.put("/content-packs/{pack_name}/variables/{variable_name}")
        def set_pack_variable(
            pack_name: str,
            variable_name: str,
            request: Dict[str, Any],
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.update"))
            ],
            session: Annotated[Session, Depends(get_session)],
        ) -> Dict[str, Any]:
            """
            Set a variable value for a specific content pack and user.
            """
            from .version_utils import supports_content_pack_variables
            
            if not supports_content_pack_variables():
                raise HTTPException(
                    status_code=501, 
                    detail="Content pack variables are not supported in this version"
                )
            
            # For service authentication, we can't set user-specific variables
            if isinstance(current_user, str):
                raise HTTPException(
                    status_code=400,
                    detail="User authentication required for variable management"
                )
            
            variable_value = request.get("value")
            if variable_value is None:
                raise HTTPException(
                    status_code=422,
                    detail="Variable value is required"
                )
            
            # Validate variable name
            import re
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', variable_name):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid variable name. Must start with letter or underscore, followed by letters, numbers, or underscores"
                )
            
            try:
                # Check if pack exists
                loaded_packs = content_pack_manager.get_loaded_content_packs()
                pack_exists = any(pack["name"] == pack_name for pack in loaded_packs)
                if not pack_exists:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Content pack '{pack_name}' not found"
                    )
                
                success = content_pack_manager.set_pack_variable(
                    pack_name, variable_name, str(variable_value), current_user.id, session
                )
                
                if success:
                    return {
                        "status": "success",
                        "message": f"Variable '{variable_name}' set successfully",
                        "pack_name": pack_name,
                        "variable_name": variable_name,
                        "variable_value": str(variable_value)
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to set variable '{variable_name}' for content pack '{pack_name}'"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logging.error(f"Error setting variable '{variable_name}' for pack '{pack_name}': {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to set variable '{variable_name}' for content pack '{pack_name}'"
                )

        @router.delete("/content-packs/{pack_name}/variables/{variable_name}")
        def reset_pack_variable(
            pack_name: str,
            variable_name: str,
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.update"))
            ],
            session: Annotated[Session, Depends(get_session)],
        ) -> Dict[str, Any]:
            """
            Reset a specific variable to its default value for a content pack and user.
            """
            from .version_utils import supports_content_pack_variables
            
            if not supports_content_pack_variables():
                raise HTTPException(
                    status_code=501, 
                    detail="Content pack variables are not supported in this version"
                )
            
            # For service authentication, we can't reset user-specific variables
            if isinstance(current_user, str):
                raise HTTPException(
                    status_code=400,
                    detail="User authentication required for variable management"
                )
            
            try:
                # Check if pack exists
                loaded_packs = content_pack_manager.get_loaded_content_packs()
                pack_exists = any(pack["name"] == pack_name for pack in loaded_packs)
                if not pack_exists:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Content pack '{pack_name}' not found"
                    )
                
                from .content_pack_variables import get_variable_manager
                variable_manager = get_variable_manager(session)
                
                success = variable_manager.delete_variable(pack_name, variable_name, current_user.id)
                
                if success:
                    return {
                        "success": True,
                        "message": f"Variable '{variable_name}' reset to default value",
                        "pack_name": pack_name,
                        "variable_name": variable_name
                    }
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Variable '{variable_name}' not found for content pack '{pack_name}'"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logging.error(f"Error resetting variable '{variable_name}' for pack '{pack_name}': {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to reset variable '{variable_name}' for content pack '{pack_name}'"
                )

        @router.post("/content-packs/{pack_name}/variables/reset")
        def reset_all_pack_variables(
            pack_name: str,
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.update"))
            ],
            session: Annotated[Session, Depends(get_session)],
        ) -> Dict[str, Any]:
            """
            Reset all variables to their default values for a content pack and user.
            """
            from .version_utils import supports_content_pack_variables
            
            if not supports_content_pack_variables():
                raise HTTPException(
                    status_code=501, 
                    detail="Content pack variables are not supported in this version"
                )
            
            # For service authentication, we can't reset user-specific variables
            if isinstance(current_user, str):
                raise HTTPException(
                    status_code=400,
                    detail="User authentication required for variable management"
                )
            
            try:
                # Check if pack exists
                loaded_packs = content_pack_manager.get_loaded_content_packs()
                pack_exists = any(pack["name"] == pack_name for pack in loaded_packs)
                if not pack_exists:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Content pack '{pack_name}' not found"
                    )
                
                success = content_pack_manager.reset_pack_variables(pack_name, current_user.id, session)
                
                if success:
                    return {
                        "success": True,
                        "message": f"All variables reset to default values for content pack '{pack_name}'",
                        "pack_name": pack_name
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to reset variables for content pack '{pack_name}'"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logging.error(f"Error resetting all variables for pack '{pack_name}': {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to reset variables for content pack '{pack_name}'"
                )

        # --- Remote Content Pack Endpoints ---

        @router.get("/content-packs/remote")
        def list_remote_content_packs(
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.read"))
            ],
            force_refresh: bool = False,
        ) -> List[Dict[str, Any]]:
            """
            Returns a list of all available remote content packs.
            """
            return content_pack_manager.list_remote_content_packs(force_refresh)

        @router.get("/content-packs/remote/info/{filename}")
        def get_remote_content_pack_info(
            filename: str,
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.read"))
            ],
        ) -> Dict[str, Any]:
            """
            Get detailed information about a specific remote content pack.
            """
            pack_info = content_pack_manager.get_remote_content_pack_info(filename)
            if not pack_info:
                raise HTTPException(
                    status_code=404,
                    detail=f"Remote content pack '{filename}' not found",
                )
            return pack_info

        @router.post("/content-packs/remote/search")
        def search_remote_content_packs(
            request: Dict[str, Any],
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.read"))
            ],
        ) -> List[Dict[str, Any]]:
            """
            Search remote content packs by query, category, or tags.
            """
            query = request.get("query", "")
            category = request.get("category", "")
            tags = request.get("tags", [])

            return content_pack_manager.search_remote_content_packs(
                query, category, tags
            )

        @router.post("/content-packs/remote/download")
        def download_remote_content_pack(
            request: Dict[str, Any],
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.install"))
            ],
        ) -> Dict[str, Any]:
            """
            Download a remote content pack to local cache.
            """
            filename = request.get("filename")
            if not filename:
                raise HTTPException(status_code=400, detail="Filename is required")

            downloaded_path = content_pack_manager.download_remote_content_pack(
                filename
            )

            if downloaded_path:
                return {
                    "status": "success",
                    "message": f"Content pack '{filename}' downloaded successfully",
                    "cache_path": str(downloaded_path),
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to download content pack '{filename}'",
                )

        @router.post("/content-packs/remote/install")
        def install_remote_content_pack(
            request: Dict[str, Any],
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.install"))
            ],
        ) -> Dict[str, Any]:
            """
            Download and install a remote content pack.
            """
            filename = request.get("filename")
            load_immediately = request.get("load_immediately", True)

            if not filename:
                raise HTTPException(status_code=400, detail="Filename is required")

            success = content_pack_manager.install_remote_content_pack(
                filename, load_immediately
            )

            if success:
                action = "installed and loaded" if load_immediately else "installed"
                return {
                    "status": "success",
                    "message": f"Content pack '{filename}' {action} successfully",
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to install content pack '{filename}'",
                )

        @router.get("/content-packs/remote/repository-info")
        def get_remote_repository_info(
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.read"))
            ],
        ) -> Dict[str, Any]:
            """
            Get information about the remote repository including statistics.
            """
            return content_pack_manager.get_remote_repository_info()

        @router.post("/content-packs/remote/refresh-cache")
        def refresh_remote_cache(
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.update"))
            ],
        ) -> Dict[str, Any]:
            """
            Force refresh the remote manifest cache.
            """
            manifest = content_pack_manager.fetch_remote_manifest(force_refresh=True)
            if manifest:
                return {
                    "status": "success",
                    "message": "Remote cache refreshed successfully",
                    "content_packs_count": len(manifest.get("content_packs", [])),
                }
            else:
                raise HTTPException(
                    status_code=500, detail="Failed to refresh remote cache"
                )

        @router.post("/content-packs/remote/clear-cache")
        def clear_remote_cache(
            current_user: Annotated[
                User, Depends(require_permission_or_service("content_packs.delete"))
            ],
        ) -> Dict[str, Any]:
            """
            Clear the remote content pack cache.
            """
            success = content_pack_manager.clear_remote_cache()
            if success:
                return {
                    "status": "success",
                    "message": "Remote cache cleared successfully",
                }
            else:
                raise HTTPException(
                    status_code=500, detail="Failed to clear remote cache"
                )

    # --- Module Configuration Endpoints ---

    @router.get("/modules/status")
    def get_modules_status(
        current_user: Annotated[
            User, Depends(require_permission_or_service("system.config"))
        ],
        session: Annotated[Session, Depends(get_session)],
    ) -> Dict[str, Any]:
        """
        Get the status of all available modules (enabled and disabled).
        """
        modules_status = module_loader.get_module_status(session)
        return {"status": "success", "modules": modules_status}

    @router.post("/modules/{module_name}/toggle")
    def toggle_module(
        module_name: str,
        payload: Dict[str, Any],
        current_user: Annotated[
            User, Depends(require_permission_or_service("system.config"))
        ],
        session: Annotated[Session, Depends(get_session)],
        request: Request,
    ) -> Dict[str, Any]:
        """
        Enable or disable a module.
        """
        ip_address, user_agent = get_client_info(request)
        enabled = payload.get("enabled", True)

        # Validate module exists
        modules_status = module_loader.get_module_status(session)
        if module_name not in modules_status:
            raise HTTPException(
                status_code=404, detail=f"Module '{module_name}' not found"
            )

        # Toggle the module
        success = module_loader.set_module_enabled(module_name, enabled, session)

        if success:
            # Log the action
            log_audit_event(
                session=session,
                user_id=current_user.id if isinstance(current_user, User) else None,
                username=(
                    current_user.username
                    if isinstance(current_user, User)
                    else "service"
                ),
                action="module_toggle",
                resource_type="module",
                resource_id=module_name,
                resource_name=module_name,
                details={
                    "enabled": enabled,
                    "previous_state": modules_status[module_name]["is_enabled"],
                },
                ip_address=ip_address,
                user_agent=user_agent,
                status="success",
            )

            return {
                "status": "success",
                "message": f"Module '{module_name}' {'enabled' if enabled else 'disabled'} successfully",
                "module": {"name": module_name, "enabled": enabled},
            }
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to toggle module '{module_name}'"
            )

    @router.post("/modules/{module_name}/tools/{tool_name}/toggle")
    def toggle_tool(
        module_name: str,
        tool_name: str,
        payload: Dict[str, Any],
        current_user: Annotated[
            User, Depends(require_permission_or_service("system.config"))
        ],
        session: Annotated[Session, Depends(get_session)],
        request: Request,
    ) -> Dict[str, Any]:
        """
        Enable or disable a specific tool within a module.
        """
        ip_address, user_agent = get_client_info(request)
        enabled = payload.get("enabled", True)

        # Validate module and tool exist
        modules_status = module_loader.get_module_status(session)
        if module_name not in modules_status:
            raise HTTPException(
                status_code=404, detail=f"Module '{module_name}' not found"
            )
        
        module_tools = modules_status[module_name].get("tools", {})
        if tool_name not in module_tools:
            raise HTTPException(
                status_code=404, detail=f"Tool '{tool_name}' not found in module '{module_name}'"
            )

        # Toggle the tool
        success = module_loader.set_tool_enabled(module_name, tool_name, enabled, session)

        if success:
            # Log the action
            log_audit_event(
                session=session,
                user_id=current_user.id if isinstance(current_user, User) else None,
                username=(
                    current_user.username
                    if isinstance(current_user, User)
                    else "service"
                ),
                action="tool_toggle",
                resource_type="tool",
                resource_id=f"{module_name}.{tool_name}",
                resource_name=f"{module_name}.{tool_name}",
                details={
                    "enabled": enabled,
                    "module_name": module_name,
                    "tool_name": tool_name,
                    "previous_state": module_tools[tool_name]["is_enabled"],
                },
                ip_address=ip_address,
                user_agent=user_agent,
                status="success",
            )

            return {
                "status": "success",
                "message": f"Tool '{module_name}.{tool_name}' {'enabled' if enabled else 'disabled'} successfully",
                "tool": {
                    "module_name": module_name,
                    "tool_name": tool_name,
                    "enabled": enabled
                },
            }
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to toggle tool '{module_name}.{tool_name}'"
            )

    @router.get("/mcp/servers")
    def get_mcp_servers(
        current_user: Annotated[
            User, Depends(require_permission_or_service("system.view"))
        ],
        session: Annotated[Session, Depends(get_session)],
    ) -> Dict[str, Any]:
        """
        Get information about MCP servers and their tools from stored state.
        """
        from .models import MCPServerInfo, MCPToolInfo
        from datetime import datetime
        
        try:
            # Get all servers from database
            servers = session.query(MCPServerInfo).all()
            
            servers_data = []
            total_tools = 0
            connected_servers = 0
            
            for server in servers:
                if server.is_connected:
                    connected_servers += 1
                
                # Get tools for this server
                tools = session.query(MCPToolInfo).filter(MCPToolInfo.server_name == server.server_name).all()
                
                tools_data = []
                for tool in tools:
                    tools_data.append({
                        "name": tool.tool_name,
                        "display_name": tool.display_name,
                        "description": tool.description or ""
                    })
                
                total_tools += len(tools_data)
                
                servers_data.append({
                    "name": server.server_name,
                    "type": server.server_type,
                    "url": server.server_url,
                    "connected": server.is_connected,
                    "description": server.description or "",
                    "tools_count": len(tools_data),
                    "tools": tools_data
                })
            
            # Get the latest discovery time
            latest_discovery = None
            if servers:
                latest_server = max(servers, key=lambda s: s.last_discovery or datetime.min)
                if latest_server.last_discovery:
                    latest_discovery = latest_server.last_discovery.isoformat() + "Z"
            
            return {
                "status": "success",
                "data": {
                    "servers": servers_data,
                    "stats": {
                        "total_servers": len(servers),
                        "connected_servers": connected_servers,
                        "total_tools": total_tools,
                        "last_discovery": latest_discovery
                    }
                }
            }
            
        except Exception as e:
            log.error(f"Failed to get MCP servers: {e}")
            return {
                "status": "error",
                "message": "Failed to retrieve MCP server information",
                "data": {
                    "servers": [],
                    "stats": {
                        "total_servers": 0,
                        "connected_servers": 0,
                        "total_tools": 0,
                        "last_discovery": None
                    }
                }
            }

    @router.post("/mcp/register-tools")
    def register_mcp_tools(
        payload: Dict[str, Any],
        current_user: Annotated[
            User, Depends(require_permission_or_service("system.config"))
        ],
        session: Annotated[Session, Depends(get_session)],
    ) -> Dict[str, Any]:
        """
        Register MCP tools from external servers.
        """
        from .models import MCPServerInfo, MCPToolInfo
        from datetime import datetime
        
        try:
            server_name = payload.get("server_name")
            tools = payload.get("tools", [])
            
            if not server_name:
                raise ValueError("server_name is required")
            
            # Update or create server info
            existing_server = session.query(MCPServerInfo).filter(MCPServerInfo.server_name == server_name).first()
            if existing_server:
                server_info = existing_server
            else:
                server_info = MCPServerInfo(server_name=server_name, created_at=datetime.utcnow())
                session.add(server_info)
            
            server_info.tools_count = len(tools)
            server_info.is_connected = True
            server_info.last_discovery = datetime.utcnow()
            server_info.updated_at = datetime.utcnow()
            
            # Clear existing tools for this server
            session.query(MCPToolInfo).filter(MCPToolInfo.server_name == server_name).delete()
            
            # Add new tools
            for tool_data in tools:
                tool_info = MCPToolInfo(
                    server_name=server_name,
                    tool_name=tool_data.get("name", ""),
                    display_name=tool_data.get("display_name", tool_data.get("name", "")),
                    description=tool_data.get("description", ""),
                    is_available=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(tool_info)
            
            session.commit()
            
            logging.info(f"Registered {len(tools)} MCP tools from server '{server_name}'")
            
            return {
                "status": "success",
                "message": f"Registered {len(tools)} tools from {server_name}",
                "tools_count": len(tools)
            }
            
        except Exception as e:
            session.rollback()
            logging.error(f"Failed to register MCP tools: {e}")
            return {
                "status": "error",
                "message": f"Failed to register MCP tools: {str(e)}"
            }

    return router
