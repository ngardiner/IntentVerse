import logging
import inspect
from fastmcp import FastMCP
from typing import Dict, Any, Callable, Awaitable, List

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

        async def proxy_func(**kwargs) -> Dict[str, Any]:
            """This is a proxy function. Its signature and docstring are replaced dynamically."""
            logging.info(f"Proxy for '{tool_name}': Forwarding call with params {kwargs} to Core Engine.")
            payload = { "tool_name": tool_name, "parameters": kwargs }
            core_result = await self.core_client.execute_tool(payload)
            return core_result.get("result", {})

        # Dynamically build the function signature that FastMCP will inspect.
        type_map = {'str': str, 'int': int, 'bool': bool, 'list': list, 'dict': dict, 'Any': Any}
        
        sig_params = []
        for p_info in tool_def.get("parameters", []):
            param_type = type_map.get(p_info.get('annotation', 'Any'), Any)
            sig_params.append(
                inspect.Parameter(
                    name=p_info['name'],
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=param_type,
                    default=inspect.Parameter.empty if p_info.get('required') else None
                )
            )
            
        proxy_func.__signature__ = inspect.Signature(parameters=sig_params)
        proxy_func.__doc__ = description
        proxy_func.__name__ = tool_name.replace('.', '_')
        
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
            server.add_tool(dynamic_proxy)

            logging.info(f"  - Registered proxy for tool: '{tool_name}' with signature {dynamic_proxy.__signature__}")