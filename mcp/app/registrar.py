import logging
import inspect
from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
from typing import (
    Dict,
    Any,
    Callable,
    Awaitable,
    List,
    Optional,
    Union,
    get_origin,
    get_args,
)

from .core_client import CoreClient
from .proxy import MCPProxyEngine


class ToolRegistrar:
    """
    Handles the dynamic registration of tools from the Core Engine
    onto the FastMCP Server instance.
    """

    def __init__(self, core_client: CoreClient):
        self.core_client = core_client
        self.proxy_engine: Optional[MCPProxyEngine] = None

    def _create_dynamic_proxy(
        self, tool_def: Dict[str, Any]
    ) -> Callable[..., Awaitable[Dict[str, Any]]]:
        """
        A factory that creates a proxy function with a dynamic signature
        that matches the original tool method from the Core Engine.
        This allows FastMCP's add_tool method to correctly generate the schema.
        """
        tool_name = tool_def["name"]
        description = tool_def.get("description", "No description available.")

        # Define a mapping for basic types and generic origins.
        # This map will be used by our parser to resolve string names to actual type objects.
        base_type_map = {
            "str": str,
            "int": int,
            "bool": bool,
            "float": float,
            "Any": Any,
            "List": List,  # Corresponds to typing.List
            "Dict": Dict,  # Corresponds to typing.Dict
            "Optional": Optional,  # Corresponds to typing.Optional (which is Union[T, None])
            "Union": Union,  # Corresponds to typing.Union
        }

        # Helper function to parse annotation strings recursively into Python type objects
        def parse_annotation_string(annotation_str: str):
            annotation_str = annotation_str.strip()

            # Handle simple, non-generic types first (e.g., 'str', 'int', 'Any')
            if annotation_str in base_type_map:
                return base_type_map[annotation_str]

            # Handle generic types (e.g., 'List[str]', 'Optional[int]', 'Dict[str, Any]')
            # Look for the pattern 'Origin[Args]'
            if "[" in annotation_str and annotation_str.endswith("]"):
                # Split the string to get the generic origin part and the arguments part
                origin_str, args_str_raw = annotation_str.split("[", 1)
                args_str = args_str_raw[:-1]  # Remove the closing ']'

                # Resolve the origin type (e.g., 'List' -> typing.List)
                origin_type = base_type_map.get(origin_str, Any)

                # Parse the arguments string, handling nested generics and commas.
                # This logic is crucial for correctly splitting arguments like in Dict[str, Union[int, str]]
                args_list_str = []
                balance = 0  # To track nested brackets
                current_arg_chars = []
                for char in args_str:
                    if char == "[":
                        balance += 1
                    elif char == "]":
                        balance -= 1
                    elif char == "," and balance == 0:
                        # Comma outside of nested brackets indicates a new argument
                        args_list_str.append("".join(current_arg_chars).strip())
                        current_arg_chars = []
                        continue
                    current_arg_chars.append(char)

                # Add the last argument
                if current_arg_chars:
                    args_list_str.append("".join(current_arg_chars).strip())

                # Recursively parse each argument string into its type object
                parsed_args = tuple(
                    parse_annotation_string(arg) for arg in args_list_str
                )

                # Special handling for Optional: Optional[T] is syntactic sugar for Union[T, None]
                # Reconstruct the generic type with its arguments
                if origin_type is Optional:
                    if len(parsed_args) == 1:
                        # For Optional[T], create Union[T, type(None)]
                        return Union[parsed_args[0], type(None)]
                    else:
                        logging.warning(
                            f"Unexpected number of arguments for Optional: {annotation_str}. Falling back to Any."
                        )
                        return Any
                elif origin_type is not Any:
                    try:
                        # Attempt to reconstruct the generic type (e.g., List[str], Dict[str, Any])
                        return origin_type[parsed_args]
                    except TypeError:
                        # This can happen if the number of args is wrong for the origin type
                        logging.warning(
                            f"TypeError when applying arguments {parsed_args} to origin {origin_type} for annotation: {annotation_str}. Falling back to Any."
                        )
                        return Any

                # Fallback for unresolvable generic origins
                return Any

            # Fallback for any other unparsed string that is not a simple or generic type
            logging.warning(
                f"Could not parse annotation string: '{annotation_str}'. Falling back to Any."
            )
            return Any

        sig_params = []
        # Initialize __annotations__ dictionary, which is critical for Pydantic v2
        annotations = {}
        # Parse the return type annotation
        annotations["return"] = parse_annotation_string(tool_def.get("returns", "Any"))

        for p_info in tool_def.get("parameters", []):
            param_name = p_info["name"]
            annotation_str = p_info.get("annotation", "Any")
            is_required = p_info.get("required", True)

            # Use the new helper function to get the correct Python type object
            resolved_type = parse_annotation_string(annotation_str)

            sig_params.append(
                inspect.Parameter(
                    name=param_name,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=resolved_type,  # Assign the correctly parsed type object
                    default=inspect.Parameter.empty if is_required else None,
                )
            )
            # Populate the __annotations__ dictionary for the proxy function
            annotations[param_name] = resolved_type

        async def proxy_func(**kwargs) -> Dict[str, Any]:
            """This is a proxy function. Its signature and docstring are replaced dynamically."""
            logging.info(
                f"Proxy for '{tool_name}': Forwarding call with params {kwargs} to Core Engine."
            )
            payload = {"tool_name": tool_name, "parameters": kwargs}
            core_result = await self.core_client.execute_tool(payload)
            # Return only the 'result' part, as FastMCP expects the direct tool output
            return core_result.get("result", {})

        # Set the dynamic signature, docstring, name, and crucially, the annotations
        proxy_func.__signature__ = inspect.Signature(parameters=sig_params)
        proxy_func.__doc__ = description
        proxy_func.__name__ = tool_name.replace(".", "_")
        proxy_func.__annotations__ = annotations

        return proxy_func

    async def initialize_proxy_engine(self, config_path: Optional[str] = None) -> None:
        """
        Initialize the MCP Proxy Engine.

        Args:
            config_path: Path to proxy configuration file
        """
        try:
            self.proxy_engine = MCPProxyEngine(config_path)
            await self.proxy_engine.initialize()
            logging.info("MCP Proxy Engine initialized successfully")
        except Exception as e:
            logging.warning(f"Failed to initialize MCP Proxy Engine: {e}")
            self.proxy_engine = None

    async def register_tools(self, server: FastMCP):
        """
        Fetches the tool manifest and registers each tool with the MCP server
        using a dynamically generated, correctly-signed proxy function.
        Also registers proxy tools from external MCP servers if proxy engine is available.
        """
        logging.info("Registrar: Registering tools...")

        # Register core tools
        await self._register_core_tools(server)

        # Register proxy tools if proxy engine is available
        await self._register_proxy_tools(server)

    async def _register_core_tools(self, server: FastMCP):
        """Register core tools from the Core Engine."""
        logging.info("Registering core tools...")
        tool_manifest = await self.core_client.get_tool_manifest()

        # List of method names that should be excluded from MCP tool registration
        excluded_methods = [
            "get_ui_schema",           # UI-specific method
            "load_content_pack_database",  # Database content pack loading
            "export_database_content"      # Database content exporting
        ]

        for tool_def in tool_manifest:
            tool_name = tool_def.get("name")
            if not tool_name:
                continue

            # Filter out UI-specific methods that should not be exposed to MCP clients
            should_exclude = False
            for excluded_method in excluded_methods:
                if tool_name == excluded_method or tool_name.endswith(f".{excluded_method}"):
                    should_exclude = True
                    break
            
            if should_exclude:
                logging.debug(f"Excluding UI-specific method from MCP registration: {tool_name}")
                continue

            dynamic_proxy = self._create_dynamic_proxy(tool_def)

            # Add the dynamically created function as a tool to the FastMCP server
            server.add_tool(FunctionTool.from_function(dynamic_proxy, name=tool_name))

            logging.info(
                f"  - Registered core tool: '{tool_name}' with signature {dynamic_proxy.__signature__}"
            )

            # Only log tool registration for non-timeline tools to avoid circular dependencies
            if not tool_name.startswith("timeline."):
                try:
                    await self.core_client.execute_tool(
                        {
                            "tool_name": "timeline.add_event",
                            "parameters": {
                                "event_type": "system",
                                "title": f"Core Tool Registered: {tool_name}",
                                "description": f"The core tool '{tool_name}' has been registered with the MCP Interface.",
                                "details": {
                                    "tool_name": tool_name,
                                    "description": tool_def.get(
                                        "description", "No description available."
                                    ),
                                    "source": "core_engine",
                                },
                            },
                        }
                    )
                except Exception as e:
                    # This is expected to fail for the first few tools before timeline is registered
                    logging.debug(f"Could not log tool registration event: {e}")

    async def _register_proxy_tools(self, server: FastMCP):
        """Register proxy tools from external MCP servers."""
        if not self.proxy_engine:
            logging.info("No proxy engine available, skipping proxy tool registration")
            return

        try:
            logging.info("Starting MCP Proxy Engine and registering proxy tools...")

            # Start the proxy engine
            await self.proxy_engine.start()

            # Register proxy tools with FastMCP server
            proxy_tools_count = await self.proxy_engine.register_proxy_tools(server)

            logging.info(
                f"Registered {proxy_tools_count} proxy tools from external MCP servers"
            )

            # Log proxy tool registration summary
            try:
                stats = self.proxy_engine.get_stats()
                await self.core_client.execute_tool(
                    {
                        "tool_name": "timeline.add_event",
                        "parameters": {
                            "event_type": "system",
                            "title": "MCP Proxy Tools Registered",
                            "description": f"Successfully registered {proxy_tools_count} proxy tools from {stats.servers_connected} external MCP servers.",
                            "details": {
                                "proxy_tools_count": proxy_tools_count,
                                "servers_connected": stats.servers_connected,
                                "servers_configured": stats.servers_configured,
                                "conflicts_detected": stats.conflicts_detected,
                                "source": "mcp_proxy",
                            },
                        },
                    }
                )
            except Exception as e:
                logging.debug(f"Could not log proxy tool registration summary: {e}")

        except Exception as e:
            logging.error(f"Failed to register proxy tools: {e}")

    async def shutdown(self):
        """Shutdown the registrar and cleanup resources."""
        if self.proxy_engine:
            try:
                await self.proxy_engine.stop()
                logging.info("MCP Proxy Engine stopped")
            except Exception as e:
                logging.error(f"Error stopping proxy engine: {e}")

    def get_proxy_engine_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get statistics from the proxy engine.

        Returns:
            Proxy engine statistics if available, None otherwise
        """
        if self.proxy_engine and self.proxy_engine.is_running:
            return self.proxy_engine.get_stats().to_dict()
        return None

    def get_proxy_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific proxy tool.

        Args:
            tool_name: Name of the proxy tool

        Returns:
            Tool information if found, None otherwise
        """
        if self.proxy_engine:
            return self.proxy_engine.get_tool_info(tool_name)
        return None

    def get_all_proxy_tools(self) -> List[Dict[str, Any]]:
        """
        Get information about all proxy tools.

        Returns:
            List of proxy tool information
        """
        if self.proxy_engine:
            return self.proxy_engine.get_all_tool_info()
        return []
