import inspect
from fastapi import APIRouter, Path, HTTPException
from typing import Dict, Any, List

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
            raise HTTPException(status_code=404, detail=f"No state found for module: {module_name}")
        return state

    # --- MCP Endpoints ---

    @router.get("/tools/manifest")
    def get_tools_manifest() -> List[Dict[str, Any]]:
        """
        NEW: Inspects all loaded tool classes and returns a detailed manifest.
        The MCP Interface uses this to know which tools to register.
        """
        manifest = []
        tools = module_loader.get_tools()
        for module_name, tool_instance in tools.items():
            # Find all public methods on the tool instance
            for method_name, method in inspect.getmembers(tool_instance, inspect.ismethod):
                if not method_name.startswith('_'):
                    full_tool_name = f"{module_name}.{method_name}"
                    docstring = inspect.getdoc(method) or "No description available."
                    
                    # You could add more detailed parameter inspection here if needed
                    
                    manifest.append({
                        "name": full_tool_name,
                        "description": docstring,
                        "parameters": {} # Placeholder for parameter schema
                    })
        return manifest

    @router.post("/execute")
    async def execute_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        The main endpoint for executing a tool command.
        The MCP interface will call this endpoint.
        NOTE: Logic needs to be implemented.
        """
        tool_full_name = payload.get("tool_name")
        parameters = payload.get("parameters", {})

        if not tool_full_name:
            raise HTTPException(status_code=400, detail="`tool_name` is required.")
        
        module_name, method_name = tool_full_name.split('.')
        
        tools = module_loader.get_tools()
        tool_instance = tools.get(module_name)

        if not tool_instance or not hasattr(tool_instance, method_name):
            raise HTTPException(status_code=404, detail=f"Tool '{tool_full_name}' not found.")

        method_to_call = getattr(tool_instance, method_name)
        
        # In a real implementation, you would inspect method_to_call
        # and pass parameters correctly.
        result = method_to_call(**parameters)

        print(f"Executing tool '{tool_full_name}' with parameters: {parameters}")
        return {"status": "success", "result": result}

    return router
