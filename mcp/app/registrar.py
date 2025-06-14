from fastmcp import FastMCPServer
from typing import Dict, Any

from .core_client import CoreClient

class ToolRegistrar:
    """
    Handles the dynamic registration of tools from the Core Engine
    onto the FastMCPServer instance.
    """

    def __init__(self, core_client: CoreClient):
        """
        Initializes the registrar with a client to communicate with the core service.

        Args:
            core_client: An instance of the CoreClient.
        """
        self.core_client = core_client

    async def register_tools(self, server: FastMCPServer):
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
            # For each tool definition from the core, we create a
            # unique "proxy" function that will be exposed to the AI.
            
            tool_name = tool_def.get("name")
            description = tool_def.get("description")

            # Create the proxy function dynamically
            async def create_proxy_func(name: str, **kwargs):
                print(f"Proxy for '{name}': Forwarding call to Core Engine.")
                payload = {
                    "tool_name": name,
                    "parameters": kwargs
                }
                # When the AI calls this tool, we simply pass the request
                # on to the Core Engine's /execute endpoint.
                return await self.core_client.execute_tool(payload)

            # To make each function unique in the loop, we use a factory
            # or a closure. Here we define a new function inside the loop.
            # We need to give it a unique name for Python's sake.
            proxy_func = create_proxy_func
            
            # The name provided to the @server.tool decorator is what the LLM will see.
            # We add the proxy function itself to the server.
            # Note: The signature for the LLM is just the function's docstring and name.
            # A more advanced version could dynamically build a function with a perfect signature.
            # For now, we expect the LLM to know the parameters.
            
            # Programmatically add the tool
            server.add_tool(
                func=proxy_func,
                name=tool_name,
                description=description,
            )

            print(f"  - Registered proxy for tool: '{tool_name}'")
