import logging
import inspect
from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
from typing import Dict, Any, Callable, Awaitable, List, Optional

from .core_client import CoreClient

class ToolRegistrar:
    """
    Handles the dynamic registration of tools from the Core Engine
    onto the FastMCP Server instance.
    """

    def __init__(self, core_client: CoreClient):
        self.core_client = core_client

    def _create_dynamic_proxy(self, tool_def: Dict[str, Any]) -> Callable[..., Awaitable[Dict[str, Any]]]:
        """
        A factory that creates a proxy function with a dynamic signature
        that matches the original tool method from the Core Engine.
        This allows FastMCP's add_tool method to correctly generate the schema.
        """
        tool_name = tool_def["name"]
        description = tool_def.get("description", "No description available.")

        # A mapping from simple string names to actual Python type objects
        # This is necessary because core/app/api.py extracts the __name__ of the annotation (e.g., 'List' instead of typing.List)
        type_hint_map = {
            'str': str,
            'int': int,
            'bool': bool,
            'float': float,
            'Any': Any,
            'List': List,  # Map 'List' string to typing.List
            'Dict': Dict,  # Map 'Dict' string to typing.Dict
            'Optional': Optional # Map 'Optional' string to typing.Optional
        }

        sig_params = []
        # Initialize __annotations__ dictionary for the proxy function.
        # Pydantic (especially v2) relies heavily on this for schema generation.
        annotations = {}
        # Set the return type annotation for the proxy function
        annotations['return'] = Dict[str, Any]

        for p_info in tool_def.get("parameters", []):
            param_name = p_info['name']
            annotation_name = p_info.get('annotation', 'Any')
            is_required = p_info.get('required', True)

            # Resolve the type hint using our map.
            # For complex generics like 'List[str]', api.py currently only sends 'List'.
            # Pydantic can still generate a schema for `List` if `typing.List` is provided.
            resolved_type = type_hint_map.get(annotation_name, Any)

            sig_params.append(
                inspect.Parameter(
                    name=param_name,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=resolved_type, # Use the resolved type object
                    default=inspect.Parameter.empty if is_required else None
                )
            )
            # Populate the __annotations__ dictionary with the resolved type for each parameter
            annotations[param_name] = resolved_type

        async def proxy_func(**kwargs) -> Dict[str, Any]:
            """This is a proxy function. Its signature and docstring are replaced dynamically."""
            logging.info(f"Proxy for '{tool_name}': Forwarding call with params {kwargs} to Core Engine.")
            payload = { "tool_name": tool_name, "parameters": kwargs }
            core_result = await self.core_client.execute_tool(payload)
            return core_result.get("result", {})

        # Dynamically build the function signature that FastMCP will inspect.
        proxy_func.__signature__ = inspect.Signature(parameters=sig_params)
        proxy_func.__doc__ = description
        proxy_func.__name__ = tool_name.replace('.', '_')
        proxy_func.__annotations__ = annotations
        
        return proxy_func

    async def register_tools(self, server: FastMCP):
        """
        Fetches the tool manifest and registers each tool with the MCP server
        using a dynamically generated, correctly-signed proxy function.
        """
        logging.info("Registrar: Registering tools...")
        tool_manifest = await self.core_client.get_tool_manifest()

        for tool_def in tool_manifest:
            tool_name = tool_def.get("name")
            if not tool_name:
                continue

            dynamic_proxy = self._create_dynamic_proxy(tool_def)

            # Use the library's dynamic registration method.
            # It will inspect our proxy function's signature and docstring.
            server.add_tool(FunctionTool.from_function(dynamic_proxy, name=tool_name))

            logging.info(f"  - Registered proxy for tool: '{tool_name}' with signature {dynamic_proxy.__signature__}")