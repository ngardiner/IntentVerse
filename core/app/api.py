import logging
import inspect
from fastapi import APIRouter, Path, HTTPException, Depends, Request
from typing import Dict, Any, List, Union, get_origin, get_args, Annotated # Import get_origin, get_args
from sqlmodel import Session

from .module_loader import ModuleLoader
from .state_manager import state_manager
from .modules.timeline.tool import log_tool_execution, log_system_event, log_error
from .auth import get_current_user, get_current_user_or_service, log_audit_event, get_client_info
from .models import User
from .database import get_session

def create_api_routes(module_loader: ModuleLoader, content_pack_manager=None) -> APIRouter:
    """
    Creates and returns the API router, wiring up the endpoints
    to the loaded modules.
    """
    router = APIRouter(prefix="/api/v1")
    
    def require_admin(current_user: User):
        """Helper function to check if user is admin"""
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Only administrators can perform this action"
            )

    # --- UI Endpoints ---

    @router.get("/ui/layout")
    def get_ui_layout(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> Dict[str, Any]:
        """
        Returns the full UI schema for all loaded modules.
        The frontend uses this to dynamically build its layout.
        """
        return {"modules": list(module_loader.get_schemas().values())}

    @router.get("/{module_name}/state")
    def get_module_state(
        current_user: Annotated[User, Depends(get_current_user)],
        module_name: str = Path(..., title="The name of the module")
    ) -> Dict[str, Any]:
        """
        Returns the current state for a specific module.
        Used by UI components to fetch their data.
        """
        state = state_manager.get(module_name)
        if state is None:
            raise HTTPException(status_code=404, detail=f"No state found for module: {module_name}")
        return state

    # --- MCP Endpoints ---

    @router.get("/tools/manifest")
    def get_tools_manifest(
        current_user_or_service: Annotated[Union[User, str], Depends(get_current_user_or_service)]
    ) -> List[Dict[str, Any]]:
        """
        Inspects all loaded tool classes and returns a simplified manifest.
        The MCP Interface uses this to dynamically reconstruct function signatures.
        """
        manifest = []
        tools = module_loader.get_all_tools()

        for module_name, tool_instance in tools.items():
            for method_name, method in inspect.getmembers(tool_instance, inspect.ismethod):
                if not method_name.startswith('_'):
                    full_tool_name = f"{module_name}.{method_name}"
                    description = inspect.getdoc(method) or "No description available."
                    
                    sig = inspect.signature(method)
                    parameters_info = []
                    for param in sig.parameters.values():
                        if param.name == 'self':
                            continue
                        
                        param_annotation_details = {
                            "base_type": 'Any', # e.g., 'str', 'int', 'List'
                            "is_optional": False,
                            "union_types": [] # List of string representations if it's a Union
                        }

                        if param.annotation != inspect.Parameter.empty:
                            param_origin = get_origin(param.annotation)
                            param_args = get_args(param.annotation)

                            if param_origin is Union:
                                # It's a Union type (including Optional which is Union[T, NoneType])
                                non_none_args = [arg for arg in param_args if arg is not type(None)]
                                param_annotation_details["is_optional"] = (type(None) in param_args)

                                # Store string representations of all types in the Union
                                param_annotation_details["union_types"] = [
                                    (arg.__name__ if hasattr(arg, '__name__') else str(arg))
                                    for arg in param_args
                                ]

                                if len(non_none_args) == 1:
                                    # This is typically an Optional[X] where X is the base_type
                                    base_arg = non_none_args[0]
                                    param_annotation_details["base_type"] = base_arg.__name__ if hasattr(base_arg, '__name__') else str(base_arg)
                                elif len(non_none_args) > 1:
                                    # A more complex Union (e.g., Union[str, int])
                                    param_annotation_details["base_type"] = 'Union'
                                else:
                                    param_annotation_details["base_type"] = 'NoneType' # Only None in Union, or empty (unlikely for params)
                            else:
                                # Not a Union. Get the simple name.
                                param_annotation_details["base_type"] = param.annotation.__name__ if hasattr(param.annotation, '__name__') else str(param.annotation)

                        parameters_info.append({
                            "name": param.name,
                            "annotation_details": param_annotation_details,
                            "required": param.default == inspect.Parameter.empty,
                        })

                    manifest.append({
                        "name": full_tool_name,
                        "description": description,
                        "parameters": parameters_info,
                    })
        return manifest
    
    @router.post("/execute")
    def execute_tool(
        payload: Dict[str, Any],
        current_user_or_service: Annotated[Union[User, str], Depends(get_current_user_or_service)],
        session: Annotated[Session, Depends(get_session)],
        request: Request
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

        if not tool_full_name or '.' not in tool_full_name:
            log_audit_event(
                session=session,
                user_id=user_id,
                username=username,
                action="execute_tool_failed",
                details={"reason": "invalid_tool_name_format", "provided_tool_name": tool_full_name},
                ip_address=ip_address,
                user_agent=user_agent,
                status="failure",
                error_message="`tool_name` is required in the format 'module.method'."
            )
            raise HTTPException(status_code=400, detail="`tool_name` is required in the format 'module.method'.")
        
        try:
            module_name, method_name = tool_full_name.split('.', 1)
        except ValueError:
            log_audit_event(
                session=session,
                user_id=user_id,
                username=username,
                action="execute_tool_failed",
                details={"reason": "invalid_tool_name_format", "provided_tool_name": tool_full_name},
                ip_address=ip_address,
                user_agent=user_agent,
                status="failure",
                error_message="`tool_name` is invalid. Expected format 'module.method'."
            )
            raise HTTPException(status_code=400, detail="`tool_name` is invalid. Expected format 'module.method'.")

        tool_instance = module_loader.get_tool(module_name)

        if not tool_instance or not hasattr(tool_instance, method_name):
            log_audit_event(
                session=session,
                user_id=user_id,
                username=username,
                action="execute_tool_failed",
                resource_type="tool",
                resource_name=tool_full_name,
                details={"reason": "tool_not_found", "module_name": module_name, "method_name": method_name},
                ip_address=ip_address,
                user_agent=user_agent,
                status="failure",
                error_message=f"Tool '{tool_full_name}' not found."
            )
            raise HTTPException(status_code=404, detail=f"Tool '{tool_full_name}' not found.")

        try:
            method_to_call = getattr(tool_instance, method_name)
            
            # Validate required parameters are present
            sig = inspect.signature(method_to_call)
            for param in sig.parameters.values():
                if param.name != 'self' and param.default == inspect.Parameter.empty and param.name not in parameters:
                    log_audit_event(
                        session=session,
                        user_id=user_id,
                        username=username,
                        action="execute_tool_failed",
                        resource_type="tool",
                        resource_name=tool_full_name,
                        details={"reason": "missing_required_parameter", "missing_parameter": param.name, "parameters": parameters},
                        ip_address=ip_address,
                        user_agent=user_agent,
                        status="failure",
                        error_message=f"Missing required parameter for '{tool_full_name}': {param.name}"
                    )
                    raise HTTPException(status_code=422, detail=f"Missing required parameter for '{tool_full_name}': {param.name}")

            # Call the tool method with the provided parameters
            result = method_to_call(**parameters)
            
            logging.info(f"Executed tool '{tool_full_name}' with parameters: {parameters}")
            
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
                status="success"
            )
            
            # Log the tool execution to the timeline
            log_tool_execution(tool_full_name, parameters, {"status": "success", "result": result})
            
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
                details={"parameters": parameters, "status_code": e.status_code, "error_detail": e.detail},
                ip_address=ip_address,
                user_agent=user_agent,
                status="failure",
                error_message=f"HTTP Error: {e.detail}"
            )
            
            # Log the error to the timeline
            log_error(
                f"HTTP Error in tool '{tool_full_name}'", 
                f"Status code {e.status_code}: {e.detail}",
                {"status_code": e.status_code, "detail": e.detail}
            )
            # Re-raise HTTP exceptions from the tool logic (e.g., file not found)
            raise e
        except Exception as e:
            # Catch any other unexpected errors from the tool execution
            logging.error(f"ERROR executing tool '{tool_full_name}': {e}", exc_info=True)
            
            # Log the error to audit log
            log_audit_event(
                session=session,
                user_id=user_id,
                username=username,
                action="execute_tool_failed",
                resource_type="tool",
                resource_name=tool_full_name,
                details={"parameters": parameters, "error_type": type(e).__name__, "error_message": str(e)},
                ip_address=ip_address,
                user_agent=user_agent,
                status="error",
                error_message=str(e)
            )
            
            # Log the error to the timeline
            log_error(
                f"Error executing tool '{tool_full_name}'", 
                str(e),
                {"parameters": parameters, "error_type": type(e).__name__}
            )
            
            raise HTTPException(status_code=500, detail=f"An error occurred while executing tool '{tool_full_name}': {str(e)}")

    # --- Content Pack Management Endpoints ---
    
    if content_pack_manager:
        @router.get("/content-packs/available")
        def list_available_content_packs(
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> List[Dict[str, Any]]:
            """
            Returns a list of all available content packs in the content_packs directory.
            """
            return content_pack_manager.list_available_content_packs()
        
        @router.get("/content-packs/loaded")
        def get_loaded_content_packs(
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> List[Dict[str, Any]]:
            """
            Returns information about currently loaded content packs.
            """
            return content_pack_manager.get_loaded_packs_info()
        
        @router.post("/content-packs/export")
        def export_content_pack(
            request: Dict[str, Any],
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Export current system state as a content pack.
            """
            require_admin(current_user)
            from pathlib import Path
            
            filename = request.get("filename", "exported_content_pack.json")
            metadata = request.get("metadata", {})
            
            # Ensure filename ends with .json
            if not filename.endswith('.json'):
                filename += '.json'
            
            output_path = content_pack_manager.content_packs_dir / filename
            
            success = content_pack_manager.export_content_pack(output_path, metadata)
            
            if success:
                return {
                    "status": "success", 
                    "message": f"Content pack exported to {filename}",
                    "path": str(output_path)
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to export content pack")
        
        @router.post("/content-packs/load")
        def load_content_pack(
            request: Dict[str, Any],
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Load a content pack by filename.
            """
            require_admin(current_user)
            filename = request.get("filename")
            if not filename:
                raise HTTPException(status_code=400, detail="Filename is required")
            
            success = content_pack_manager.load_content_pack_by_filename(filename)
            
            if success:
                return {
                    "status": "success",
                    "message": f"Content pack '{filename}' loaded successfully"
                }
            else:
                raise HTTPException(status_code=500, detail=f"Failed to load content pack '{filename}'")
        
        @router.post("/content-packs/unload")
        def unload_content_pack(
            request: Dict[str, Any],
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Unload a content pack by filename or name.
            Note: This only removes it from the loaded packs tracking.
            State and database changes are not reverted.
            """
            require_admin(current_user)
            identifier = request.get("identifier")
            if not identifier:
                raise HTTPException(status_code=400, detail="Pack identifier (filename or name) is required")
            
            success = content_pack_manager.unload_content_pack(identifier)
            
            if success:
                return {
                    "status": "success",
                    "message": f"Content pack '{identifier}' unloaded successfully"
                }
            else:
                raise HTTPException(status_code=404, detail=f"Content pack '{identifier}' not found in loaded packs")
        
        @router.post("/content-packs/clear-all")
        def clear_all_loaded_packs(
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Clear all loaded content packs from tracking.
            Note: This does not revert state or database changes.
            """
            require_admin(current_user)
            success = content_pack_manager.clear_all_loaded_packs()
            
            if success:
                return {
                    "status": "success",
                    "message": "All loaded content packs cleared from tracking"
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to clear loaded content packs")
        
        @router.get("/content-packs/preview/{filename}")
        def preview_content_pack(
            filename: str,
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Preview a content pack without loading it, including validation results.
            """
            preview_result = content_pack_manager.preview_content_pack(filename)
            
            if not preview_result["exists"]:
                raise HTTPException(status_code=404, detail=f"Content pack '{filename}' not found")
            
            return preview_result
        
        @router.post("/content-packs/validate")
        def validate_content_pack(
            request: Dict[str, Any],
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Validate a content pack by filename and return detailed validation results.
            """
            filename = request.get("filename")
            if not filename:
                raise HTTPException(status_code=400, detail="Filename is required")
            
            preview_result = content_pack_manager.preview_content_pack(filename)
            
            if not preview_result["exists"]:
                raise HTTPException(status_code=404, detail=f"Content pack '{filename}' not found")
            
            return {
                "filename": filename,
                "validation": preview_result["validation"]
            }
        
        # --- Remote Content Pack Endpoints ---
        
        @router.get("/content-packs/remote")
        def list_remote_content_packs(
            current_user: Annotated[User, Depends(get_current_user)],
            force_refresh: bool = False
        ) -> List[Dict[str, Any]]:
            """
            Returns a list of all available remote content packs.
            """
            return content_pack_manager.list_remote_content_packs(force_refresh)
        
        @router.get("/content-packs/remote/info/{filename}")
        def get_remote_content_pack_info(
            filename: str,
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Get detailed information about a specific remote content pack.
            """
            pack_info = content_pack_manager.get_remote_content_pack_info(filename)
            if not pack_info:
                raise HTTPException(status_code=404, detail=f"Remote content pack '{filename}' not found")
            return pack_info
        
        @router.post("/content-packs/remote/search")
        def search_remote_content_packs(
            request: Dict[str, Any],
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> List[Dict[str, Any]]:
            """
            Search remote content packs by query, category, or tags.
            """
            query = request.get("query", "")
            category = request.get("category", "")
            tags = request.get("tags", [])
            
            return content_pack_manager.search_remote_content_packs(query, category, tags)
        
        @router.post("/content-packs/remote/download")
        def download_remote_content_pack(
            request: Dict[str, Any],
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Download a remote content pack to local cache.
            """
            require_admin(current_user)
            filename = request.get("filename")
            if not filename:
                raise HTTPException(status_code=400, detail="Filename is required")
            
            downloaded_path = content_pack_manager.download_remote_content_pack(filename)
            
            if downloaded_path:
                return {
                    "status": "success",
                    "message": f"Content pack '{filename}' downloaded successfully",
                    "cache_path": str(downloaded_path)
                }
            else:
                raise HTTPException(status_code=500, detail=f"Failed to download content pack '{filename}'")
        
        @router.post("/content-packs/remote/install")
        def install_remote_content_pack(
            request: Dict[str, Any],
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Download and install a remote content pack.
            """
            require_admin(current_user)
            filename = request.get("filename")
            load_immediately = request.get("load_immediately", True)
            
            if not filename:
                raise HTTPException(status_code=400, detail="Filename is required")
            
            success = content_pack_manager.install_remote_content_pack(filename, load_immediately)
            
            if success:
                action = "installed and loaded" if load_immediately else "installed"
                return {
                    "status": "success",
                    "message": f"Content pack '{filename}' {action} successfully"
                }
            else:
                raise HTTPException(status_code=500, detail=f"Failed to install content pack '{filename}'")
        
        @router.get("/content-packs/remote/repository-info")
        def get_remote_repository_info(
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Get information about the remote repository including statistics.
            """
            return content_pack_manager.get_remote_repository_info()
        
        @router.post("/content-packs/remote/refresh-cache")
        def refresh_remote_cache(
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Force refresh the remote manifest cache.
            """
            require_admin(current_user)
            manifest = content_pack_manager.fetch_remote_manifest(force_refresh=True)
            if manifest:
                return {
                    "status": "success",
                    "message": "Remote cache refreshed successfully",
                    "content_packs_count": len(manifest.get("content_packs", []))
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to refresh remote cache")
        
        @router.post("/content-packs/remote/clear-cache")
        def clear_remote_cache(
            current_user: Annotated[User, Depends(get_current_user)]
        ) -> Dict[str, Any]:
            """
            Clear the remote content pack cache.
            """
            require_admin(current_user)
            success = content_pack_manager.clear_remote_cache()
            if success:
                return {
                    "status": "success",
                    "message": "Remote cache cleared successfully"
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to clear remote cache")

    return router