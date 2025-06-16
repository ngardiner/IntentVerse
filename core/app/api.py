import inspect
from fastapi import APIRouter, Path, HTTPException, Depends
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
        Inspects all loaded tool classes and returns a detailed manifest.
        The MCP Interface uses this to know which tools to register.
        """
        manifest = []
        tools = module_loader.get_tools()
        for module_name, tool_instance in tools.items():
            # Find all public methods on the tool instance (ignore methods starting with '_')
            for method_name, method in inspect.getmembers(tool_instance, inspect.ismethod):
                if not method_name.startswith('_'):
                    full_tool_name = f"{module_name}.{method_name}"
                    description = inspect.getdoc(method) or "No description available."
                    
                    # Get parameters using inspect.signature
                    sig = inspect.signature(method)
                    parameters_schema = {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    }
                    for param in sig.parameters.values():
                        if param.name == 'self':
                            continue
                        
                        # A simple mapping from Python types to JSON schema types
                        type_map = {str: "string", int: "integer", bool: "boolean", list: "array", dict: "object"}
                        param_info = {"type": type_map.get(param.annotation, "string")}

                        parameters_schema["properties"][param.name] = param_info
                        
                        if param.default == inspect.Parameter.empty:
                            parameters_schema["required"].append(param.name)

                    manifest.append({
                        "name": full_tool_name,
                        "description": description,
                        "parameters": parameters_schema,
                    })
        return manifest

    @router.post("/execute")
    def execute_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        The main endpoint for executing a tool command from the MCP interface.
        The MCP interface will call this endpoint.
        """
        tool_full_name = payload.get("tool_name")
        parameters = payload.get("parameters", {})

        if not tool_full_name or '.' not in tool_full_name:
            raise HTTPException(status_code=400, detail="`tool_name` is required in the format 'module.method'.")
        
        try:
            module_name, method_name = tool_full_name.split('.', 1)
        except ValueError:
             raise HTTPException(status_code=400, detail="`tool_name` is invalid. Expected format 'module.method'.")

        tool_instance = module_loader.get_tool(module_name)

        if not tool_instance or not hasattr(tool_instance, method_name):
            raise HTTPException(status_code=404, detail=f"Tool '{tool_full_name}' not found.")

        try:
            method_to_call = getattr(tool_instance, method_name)
            
            # Validate required parameters are present
            sig = inspect.signature(method_to_call)
            for param in sig.parameters.values():
                if param.name != 'self' and param.default == inspect.Parameter.empty and param.name not in parameters:
                     raise HTTPException(status_code=422, detail=f"Missing required parameter for '{tool_full_name}': {param.name}")

            # Call the tool method with the provided parameters
            result = method_to_call(**parameters)
            
            print(f"Executed tool '{tool_full_name}' with parameters: {parameters}")
            return {"status": "success", "result": result}
        except HTTPException as e:
            # Re-raise HTTP exceptions from the tool logic (e.g., file not found)
            raise e
        except Exception as e:
            # Catch any other unexpected errors from the tool execution
            print(f"ERROR executing tool '{tool_full_name}': {e}")
            raise HTTPException(status_code=500, detail=f"An error occurred while executing tool '{tool_full_name}': {str(e)}")

    return router