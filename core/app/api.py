from fastapi import APIRouter, Path
from typing import Dict, Any

from .module_loader import ModuleLoader
from .state_manager import state_manager

def create_api_routes(module_loader: ModuleLoader) -> APIRouter:
    """
    Creates and returns the API router, wiring up the endpoints
    to the loaded modules.
    """
    router = APIRouter(prefix="/api/v1")

    # --- UI Endpoints ---

    @router.get("/ui/layout")
    def get_ui_layout() -> Dict[str, Any]:
        """
        Returns the full UI schema for all loaded modules.
        The frontend uses this to dynamically build its layout.
        """
        return {"modules": list(module_loader.get_schemas().values())}

    @router.get("/{module_name}/state")
    def get_module_state(module_name: str = Path(..., title="The name of the module")) -> Dict[str, Any]:
        """
        Returns the current state for a specific module.
        Used by UI components to fetch their data.
        """
        state = state_manager.get(module_name)
        if state is None:
            return {"error": f"No state found for module: {module_name}"}
        return state

    # --- MCP Endpoints ---

    @router.post("/execute")
    def execute_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        The main endpoint for executing a tool command.
        The MCP interface will call this endpoint.
        NOTE: This is a placeholder for the MVP.
        """
        # A real implementation would:
        # 1. Parse the payload for module, tool name, and params.
        # 2. Find the correct tool instance from module_loader.get_tools().
        # 3. Call the appropriate method on the instance.
        # 4. Return the result.
        print(f"Executing tool with payload: {payload}")
        return {"status": "success", "result": "Placeholder result from tool execution."}


    return router
