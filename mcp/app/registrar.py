from fastmcp import FastMCP
from typing import Dict, Any

from .core_client import CoreClient

class ToolRegistrar:
    """
    Handles the dynamic registration of tools from the Core Engine
    onto the FastMCP Server instance.
    """

    def __init__(self, core_client: CoreClient):
        """
        Initializes the registrar with a client to communicate with the core service.

        Args:
            core_client: An instance of the CoreClient.
        """
        self.core_client = core_client

    def _create_proxy_func_factory(self, tool_name: str) -> Callable[..., Awaitable[Dict[str, Any]]]:
        """A factory that creates and returns a unique async proxy function."""
        async def proxy_func(**kwargs) -> Dict[str, Any]:
            """Proxies a tool call to the Core Engine."""
            print(f"Proxy for '{tool_name}': Forwarding call to Core Engine.")
            payload = {
                "tool_name": tool_name,
                "parameters": kwargs
            }
            return await self.core_client.execute_tool(payload)
        return proxy_func
    
    async def register_tools(self, server: FastMCP):
        """
        Fetches the tool manifest from the core and registers each tool
        with the MCP server instance.
        """
        print("Registrar: Attempting to register tools...")
        tool_manifest = await self.core_client.get_tool_manifest()

        if not tool_manifest:
            print("Registrar: No tool manifest received from Core Engine. No tools will be registered.")
            return

        for tool_def in tool_manifest:
            tool_name = tool_def.get("name")
            description = tool_def.get("description")

            proxy = self._create_proxy_func_factory(tool_name)

            server.add_tool(
                func=proxy,
                name=tool_name,
                description=description,
            )

            print(f"  - Registered proxy for tool: '{tool_name}'")
