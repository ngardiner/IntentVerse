"""
MCP Client for connecting to external MCP servers.

This module provides the MCPClient class that handles connections to external
MCP servers using various transport protocols (stdio, SSE, HTTP, WebSocket).
"""

import asyncio
import json
import logging
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path

import httpx

from .config import ServerConfig

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Represents a tool discovered from an MCP server."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str

    def __post_init__(self):
        """Validate tool after initialization."""
        if not self.name:
            raise ValueError("Tool name cannot be empty")
        if not self.description:
            raise ValueError("Tool description cannot be empty")
        if not isinstance(self.input_schema, dict):
            raise ValueError("Tool input_schema must be a dictionary")

    @classmethod
    def from_mcp_response(
        cls, tool_data: Dict[str, Any], server_name: str
    ) -> "MCPTool":
        """Create MCPTool from MCP server response data."""
        return cls(
            name=tool_data.get("name", ""),
            description=tool_data.get("description", ""),
            input_schema=tool_data.get("inputSchema", {}),
            server_name=server_name,
        )

    def to_core_tool_format(self, tool_prefix: str = "") -> Dict[str, Any]:
        """Convert to core engine tool format."""
        prefixed_name = f"{tool_prefix}{self.name}" if tool_prefix else self.name

        # Convert MCP input schema to core tool format
        parameters = []
        properties = self.input_schema.get("properties", {})
        required = self.input_schema.get("required", [])

        for param_name, param_info in properties.items():
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", "")

            # Map JSON Schema types to Python types
            type_mapping = {
                "string": "str",
                "integer": "int",
                "number": "float",
                "boolean": "bool",
                "array": "list",
                "object": "dict",
            }

            parameters.append(
                {
                    "name": param_name,
                    "annotation": type_mapping.get(param_type, "str"),
                    "description": param_desc,
                    "required": param_name in required,
                    "default": param_info.get("default"),
                }
            )

        # Use the stored original name if available, otherwise use current name
        original_name = getattr(self, "_original_name", self.name)

        return {
            "name": prefixed_name,
            "description": self.description,
            "parameters": parameters,
            "metadata": {
                "source": "mcp_proxy",
                "server_name": self.server_name,
                "original_name": original_name,
                "input_schema": self.input_schema,
            },
        }

    def __str__(self) -> str:
        return f"MCPTool({self.name} from {self.server_name})"

    def __repr__(self) -> str:
        return f"MCPTool(name={self.name}, server={self.server_name})"


@dataclass
class MCPServerInfo:
    """Information about an MCP server."""

    name: str
    version: str
    protocol_version: str = "2024-11-05"
    capabilities: Optional[Dict[str, Any]] = None

    @classmethod
    def from_mcp_response(
        cls, info_data: Dict[str, Any], server_name: str
    ) -> "MCPServerInfo":
        """Create MCPServerInfo from MCP server response."""
        return cls(
            name=info_data.get("name", server_name),
            version=info_data.get("version", "unknown"),
            protocol_version=info_data.get("protocolVersion", "2024-11-05"),
            capabilities=info_data.get("capabilities", {}),
        )


class ConnectionState(Enum):
    """Connection state enumeration."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class MCPMessage:
    """Represents an MCP protocol message."""

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        msg = {"jsonrpc": self.jsonrpc}

        if self.id is not None:
            msg["id"] = self.id
        if self.method is not None:
            msg["method"] = self.method
        if self.params is not None:
            msg["params"] = self.params
        if self.result is not None:
            msg["result"] = self.result
        if self.error is not None:
            msg["error"] = self.error

        return msg

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPMessage":
        """Create message from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
        )

    def is_request(self) -> bool:
        """Check if this is a request message."""
        return self.method is not None and self.id is not None

    def is_response(self) -> bool:
        """Check if this is a response message."""
        return self.id is not None and (
            self.result is not None or self.error is not None
        )

    def is_notification(self) -> bool:
        """Check if this is a notification message."""
        return self.method is not None and self.id is None


class MCPTransport(ABC):
    """Abstract base class for MCP transport implementations."""

    def __init__(self, server_config: ServerConfig):
        self.server_config = server_config
        self.state = ConnectionState.DISCONNECTED
        self._message_handlers: List[Callable[[MCPMessage], None]] = []
        self._error_handlers: List[Callable[[Exception], None]] = []

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the MCP server."""
        pass

    @abstractmethod
    async def send_message(self, message: MCPMessage) -> None:
        """Send a message to the MCP server."""
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if the connection is healthy."""
        pass

    def add_message_handler(self, handler: Callable[[MCPMessage], None]) -> None:
        """Add a message handler."""
        self._message_handlers.append(handler)

    def add_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Add an error handler."""
        self._error_handlers.append(handler)

    def _handle_message(self, message: MCPMessage) -> None:
        """Handle incoming message."""
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    def _handle_error(self, error: Exception) -> None:
        """Handle error."""
        for handler in self._error_handlers:
            try:
                handler(error)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")


class StdioTransport(MCPTransport):
    """Transport for stdio-based MCP servers."""

    def __init__(self, server_config: ServerConfig):
        super().__init__(server_config)
        self.process: Optional[subprocess.Popen] = None
        self._read_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Start the MCP server process and establish stdio connection."""
        if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return

        self.state = ConnectionState.CONNECTING
        logger.info(f"Starting stdio MCP server: {self.server_config.command}")

        try:
            # Start the process
            self.process = subprocess.Popen(
                [self.server_config.command] + (self.server_config.args or []),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, **(self.server_config.env or {})},
                text=True,
                bufsize=0,
            )

            # Start reading messages
            self._read_task = asyncio.create_task(self._read_messages())

            self.state = ConnectionState.CONNECTED
            logger.info(f"Connected to stdio MCP server: {self.server_config.name}")

        except Exception as e:
            self.state = ConnectionState.FAILED
            logger.error(
                f"Failed to start stdio MCP server {self.server_config.name}: {e}"
            )
            self._handle_error(e)
            raise

    async def disconnect(self) -> None:
        """Stop the MCP server process."""
        if self.state == ConnectionState.DISCONNECTED:
            return

        logger.info(f"Disconnecting from stdio MCP server: {self.server_config.name}")

        # Cancel read task
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        # Terminate process
        if self.process:
            try:
                self.process.terminate()
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        f"Force killing stdio MCP server: {self.server_config.name}"
                    )
                    self.process.kill()
                    self.process.wait()
            except Exception as e:
                logger.error(f"Error terminating process: {e}")

        self.process = None
        self.state = ConnectionState.DISCONNECTED

    async def send_message(self, message: MCPMessage) -> None:
        """Send a message to the stdio MCP server."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Not connected to stdio MCP server")

        try:
            message_json = json.dumps(message.to_dict()) + "\n"
            self.process.stdin.write(message_json)
            self.process.stdin.flush()
            logger.debug(f"Sent message to {self.server_config.name}: {message.method}")
        except Exception as e:
            logger.error(f"Failed to send message to {self.server_config.name}: {e}")
            self._handle_error(e)
            raise

    async def is_healthy(self) -> bool:
        """Check if the stdio connection is healthy."""
        if not self.process:
            return False

        # Check if process is still running
        return self.process.poll() is None

    async def _read_messages(self) -> None:
        """Read messages from the stdio MCP server."""
        if not self.process or not self.process.stdout:
            return

        try:
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self.process.stdout.readline
                )

                if not line:  # EOF
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    message_data = json.loads(line)
                    message = MCPMessage.from_dict(message_data)
                    self._handle_message(message)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from {self.server_config.name}: {e}")
                except Exception as e:
                    logger.error(
                        f"Error processing message from {self.server_config.name}: {e}"
                    )

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):
                logger.error(f"Error reading from {self.server_config.name}: {e}")
                self._handle_error(e)
                self.state = ConnectionState.FAILED


class SSETransport(MCPTransport):
    """Transport for Server-Sent Events based MCP servers."""

    def __init__(self, server_config: ServerConfig):
        super().__init__(server_config)
        self.session: Optional[Any] = None
        self._connection_context = None

    async def connect(self) -> None:
        """Connect to the SSE MCP server using the official MCP SSE client."""
        if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return

        self.state = ConnectionState.CONNECTING
        logger.info(f"Connecting to SSE MCP server: {self.server_config.url}")

        try:
            from mcp.client.sse import sse_client
            from mcp import ClientSession
            
            # Connect using the official MCP SSE client
            logger.info(f"Using MCP SSE client to connect to {self.server_config.url}")
            self._connection_context = sse_client(self.server_config.url)
            read, write = await self._connection_context.__aenter__()
            
            # Create MCP session
            self.session = ClientSession(read, write)
            await self.session.__aenter__()

            self.state = ConnectionState.CONNECTED
            logger.info(f"SSE MCP server {self.server_config.name} connected successfully using official client")

        except Exception as e:
            self.state = ConnectionState.FAILED
            error_msg = f"Failed to connect to SSE MCP server {self.server_config.name}: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            self._handle_error(e)
            raise RuntimeError(error_msg) from e

    async def disconnect(self) -> None:
        """Disconnect from the SSE MCP server."""
        if self.state == ConnectionState.DISCONNECTED:
            return

        logger.info(f"Disconnecting from SSE MCP server: {self.server_config.name}")

        # Close MCP session
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing MCP session: {e}")
            self.session = None

        # Close connection context
        if self._connection_context:
            try:
                await self._connection_context.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing connection context: {e}")
            self._connection_context = None

        self.state = ConnectionState.DISCONNECTED
        logger.info(f"Disconnected from SSE MCP server: {self.server_config.name}")

    async def send_message(self, message: MCPMessage) -> None:
        """Send a message using the MCP session - not needed for SSE transport."""
        # This method is not used for SSE transport as the MCP session handles communication
        raise NotImplementedError("SSE transport uses MCP session directly, not send_message")
    
    def _get_post_url(self) -> str:
        """Get the correct URL for POST requests."""
        # Use announced message endpoint if available
        message_endpoint = getattr(self, '_message_endpoint', None)
        if message_endpoint:
            if message_endpoint.startswith('/'):
                # Relative URL - construct full URL
                from urllib.parse import urljoin, urlparse
                base_url = self.server_config.url
                # Remove /sse from the end if present to get base URL
                parsed = urlparse(base_url)
                if parsed.path.endswith('/sse'):
                    base_url = base_url.replace('/sse', '')
                return urljoin(base_url, message_endpoint)
            elif message_endpoint.startswith('http'):
                # Absolute URL
                return message_endpoint
        
        # Default to the SSE URL for POST requests
        return self.server_config.url

    async def is_healthy(self) -> bool:
        """Check if the SSE connection is healthy."""
        return self.session is not None and self.state == ConnectionState.CONNECTED

    # All SSE parsing logic removed - using official MCP SSE client instead


class HTTPTransport(MCPTransport):
    """Transport for HTTP-based MCP servers."""

    def __init__(self, server_config: ServerConfig):
        super().__init__(server_config)
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """Connect to the HTTP MCP server."""
        if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return

        self.state = ConnectionState.CONNECTING
        logger.info(f"Connecting to HTTP MCP server: {self.server_config.url}")

        try:
            # Create HTTP client
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.server_config.settings.timeout),
                headers=self.server_config.headers or {},
            )

            # Test connection
            response = await self.client.get(self.server_config.url)
            response.raise_for_status()

            self.state = ConnectionState.CONNECTED
            logger.info(f"Connected to HTTP MCP server: {self.server_config.name}")

        except Exception as e:
            self.state = ConnectionState.FAILED
            logger.error(
                f"Failed to connect to HTTP MCP server {self.server_config.name}: {e}"
            )
            self._handle_error(e)
            raise

    async def disconnect(self) -> None:
        """Disconnect from the HTTP MCP server."""
        if self.state == ConnectionState.DISCONNECTED:
            return

        logger.info(f"Disconnecting from HTTP MCP server: {self.server_config.name}")

        if self.client:
            await self.client.aclose()
            self.client = None

        self.state = ConnectionState.DISCONNECTED

    async def send_message(self, message: MCPMessage) -> None:
        """Send a message to the HTTP MCP server."""
        if not self.client:
            raise RuntimeError("Not connected to HTTP MCP server")

        try:
            response = await self.client.post(
                self.server_config.url,
                json=message.to_dict(),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            # Handle response if it's a request
            if message.is_request():
                response_data = response.json()
                response_message = MCPMessage.from_dict(response_data)
                self._handle_message(response_message)

            logger.debug(f"Sent message to {self.server_config.name}: {message.method}")
        except Exception as e:
            logger.error(f"Failed to send message to {self.server_config.name}: {e}")
            self._handle_error(e)
            raise

    async def is_healthy(self) -> bool:
        """Check if the HTTP connection is healthy."""
        if not self.client:
            return False

        try:
            response = await self.client.head(self.server_config.url)
            return response.status_code < 400
        except Exception:
            return False


class MCPClient:
    """
    Client for connecting to external MCP servers.

    Handles connection management, message routing, and health checking
    for various MCP transport protocols.
    """

    def __init__(self, server_config: ServerConfig):
        """
        Initialize MCP client.

        Args:
            server_config: Configuration for the MCP server to connect to
        """
        self.server_config = server_config
        self.transport: Optional[MCPTransport] = None
        self._message_id_counter = 0
        self._pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        self._last_health_check = 0.0
        self._connection_attempts = 0

        # Tool discovery cache
        self._discovered_tools: List[MCPTool] = []
        self._server_info: Optional[MCPServerInfo] = None
        self._last_discovery = 0.0

        # Create appropriate transport
        self._create_transport()

    def _create_transport(self) -> None:
        """Create the appropriate transport for the server type."""
        if self.server_config.type == "stdio":
            self.transport = StdioTransport(self.server_config)
        elif self.server_config.type == "sse":
            self.transport = SSETransport(self.server_config)
        elif self.server_config.type in ["streamable-http", "http"]:
            self.transport = HTTPTransport(self.server_config)
        else:
            raise ValueError(f"Unsupported transport type: {self.server_config.type}")

        # Add message and error handlers
        self.transport.add_message_handler(self._handle_message)
        self.transport.add_error_handler(self._handle_error)

    async def connect(self) -> None:
        """
        Connect to the MCP server.

        Raises:
            RuntimeError: If connection fails
        """
        if not self.transport:
            raise RuntimeError("No transport available")

        try:
            await self.transport.connect()
            self._connection_attempts = 0
            logger.info(
                f"Successfully connected to MCP server: {self.server_config.name}"
            )
        except Exception as e:
            self._connection_attempts += 1
            logger.error(
                f"Failed to connect to MCP server {self.server_config.name}: {e}"
            )
            raise

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self.transport:
            await self.transport.disconnect()

        # Cancel any pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """
        Send a request to the MCP server and wait for response.

        Args:
            method: The method name to call
            params: Parameters for the method
            timeout: Request timeout in seconds

        Returns:
            The result from the server

        Raises:
            RuntimeError: If not connected or request fails
            asyncio.TimeoutError: If request times out
        """
        if not self.transport or self.transport.state != ConnectionState.CONNECTED:
            raise RuntimeError("Not connected to MCP server")

        # Generate unique message ID
        message_id = self._get_next_message_id()

        # Create request message
        message = MCPMessage(id=message_id, method=method, params=params or {})

        # Create future for response
        response_future = asyncio.Future()
        self._pending_requests[message_id] = response_future

        try:
            # Send message
            await self.transport.send_message(message)

            # Wait for response
            timeout = timeout or self.server_config.settings.timeout
            response = await asyncio.wait_for(response_future, timeout=timeout)

            return response

        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {method} on {self.server_config.name}")
            raise
        except Exception as e:
            logger.error(
                f"Request failed for {method} on {self.server_config.name}: {e}"
            )
            raise
        finally:
            # Clean up pending request
            self._pending_requests.pop(message_id, None)

    async def initialize_server(self) -> MCPServerInfo:
        """
        Initialize the MCP server connection and get server info.

        Returns:
            Server information

        Raises:
            RuntimeError: If initialization fails
        """
        if not self.is_connected:
            raise RuntimeError("Must be connected before initializing server")

        try:
            logger.info(f"Initializing MCP server {self.server_config.name}...")
            
            # For SSE servers, use the MCP session directly
            if self.server_config.type == "sse" and hasattr(self.transport, 'session') and self.transport.session:
                logger.info(f"Using MCP session to initialize {self.server_config.name}")
                result = await self.transport.session.initialize()
                
                # Convert MCP session result to our format
                server_info = result.serverInfo
                self._server_info = MCPServerInfo(
                    name=server_info.name,
                    version=server_info.version,
                    protocol_version=result.protocolVersion,
                    capabilities=result.capabilities.__dict__ if result.capabilities else {}
                )
                
                logger.info(f"Successfully initialized SSE MCP server {self.server_config.name}: {self._server_info.name} v{self._server_info.version}")
                return self._server_info
            
            # For other server types, use the old method
            init_timeout = 15.0 if self.server_config.type == "sse" else 30.0
            
            result = await self.send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "mcp-proxy-client", "version": "1.0.0"},
                },
                timeout=init_timeout
            )

            # Validate result
            if not isinstance(result, dict):
                raise ValueError(f"Invalid initialize response: {result}")

            # Parse server info
            self._server_info = MCPServerInfo.from_mcp_response(
                result, self.server_config.name
            )

            # Send initialized notification
            await self.send_notification("notifications/initialized")

            logger.info(
                f"Successfully initialized MCP server {self.server_config.name}: {self._server_info.name} v{self._server_info.version}"
            )
            return self._server_info

        except asyncio.TimeoutError:
            error_msg = f"Initialization timeout for {self.server_config.name}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_details = f"{type(e).__name__}: {str(e)}"
            error_msg = f"Failed to initialize MCP server {self.server_config.name}: {error_details}"
            logger.error(error_msg)
            raise RuntimeError(f"Initialization failed for {self.server_config.name}: {error_details}") from e

    async def discover_tools(self, force_refresh: bool = False) -> List[MCPTool]:
        """
        Discover tools available on the MCP server.

        Args:
            force_refresh: If True, bypass cache and fetch fresh tool list

        Returns:
            List of discovered tools

        Raises:
            RuntimeError: If not connected or discovery fails
        """
        if not self.is_connected:
            raise RuntimeError("Must be connected before discovering tools")

        # Check cache
        now = time.time()
        cache_valid = (
            not force_refresh
            and self._discovered_tools
            and (now - self._last_discovery) < 300  # 5 minute cache
        )

        if cache_valid:
            logger.debug(f"Using cached tools for {self.server_config.name}")
            return self._discovered_tools

        try:
            logger.info(f"Discovering tools from MCP server: {self.server_config.name}")

            # For SSE servers, use the MCP session directly
            if self.server_config.type == "sse" and hasattr(self.transport, 'session') and self.transport.session:
                logger.info(f"Using MCP session to discover tools from {self.server_config.name}")
                result = await self.transport.session.list_tools()
                
                # Convert MCP session result to our format
                tools_data = []
                for tool in result.tools:
                    tools_data.append({
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    })
                
                logger.debug(f"Raw tools data from {self.server_config.name}: {len(tools_data)} tools")
            else:
                # For other server types, use the old method
                discovery_timeout = 20.0 if self.server_config.type == "sse" else 30.0
                result = await self.send_request("tools/list", timeout=discovery_timeout)

                # Validate response structure
                if not isinstance(result, dict):
                    raise ValueError(f"Invalid tools/list response: {result}")

                # Parse tools from response
                tools_data = result.get("tools", [])
                if not isinstance(tools_data, list):
                    raise ValueError("Expected 'tools' to be a list in response")
                
                logger.debug(f"Raw tools data from {self.server_config.name}: {len(tools_data)} tools")
                
            # Apply filter to exclude UI-specific methods
            try:
                from .discovery_filter import filter_tools
                filtered_tools_data = filter_tools(tools_data)
                logger.debug(f"Filtered out {len(tools_data) - len(filtered_tools_data)} UI-specific methods")
            except ImportError:
                logger.warning("Discovery filter not available, using all tools")
                filtered_tools_data = tools_data

            # Convert to MCPTool objects
            discovered_tools = []
            for i, tool_data in enumerate(filtered_tools_data):
                try:
                    if not isinstance(tool_data, dict):
                        logger.warning(f"Tool {i} is not a dict: {type(tool_data)}")
                        continue
                        
                    tool = MCPTool.from_mcp_response(tool_data, self.server_config.name)
                    discovered_tools.append(tool)
                    logger.debug(f"Discovered tool: {tool.name}")
                except Exception as e:
                    logger.warning(
                        f"Failed to parse tool {i} from {self.server_config.name}: {e}"
                    )
                    continue

            # Update cache
            self._discovered_tools = discovered_tools
            self._last_discovery = now

            logger.info(
                f"Successfully discovered {len(discovered_tools)} tools from {self.server_config.name}"
            )
            return discovered_tools

        except asyncio.TimeoutError:
            error_msg = f"Tool discovery timeout for {self.server_config.name}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_details = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Failed to discover tools from {self.server_config.name}: {error_details}")
            # Don't re-raise, return empty list to allow partial functionality
            logger.warning(f"Returning empty tool list for {self.server_config.name}")
            return []

    async def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        Get detailed schema for a specific tool.

        Args:
            tool_name: Name of the tool to get schema for

        Returns:
            Tool schema information

        Raises:
            RuntimeError: If not connected or tool not found
        """
        if not self.is_connected:
            raise RuntimeError("Must be connected before getting tool schema")

        try:
            # First check if we have the tool in our cache
            for tool in self._discovered_tools:
                if tool.name == tool_name:
                    return tool.input_schema

            # If not in cache, try to get it directly
            result = await self.send_request("tools/get", {"name": tool_name})
            return result.get("inputSchema", {})

        except Exception as e:
            logger.error(
                f"Failed to get schema for tool {tool_name} from {self.server_config.name}: {e}"
            )
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If not connected or tool call fails
        """
        if not self.is_connected:
            raise RuntimeError("Must be connected before calling tools")

        try:
            logger.debug(f"Calling tool {tool_name} on {self.server_config.name}")

            result = await self.send_request(
                "tools/call", {"name": tool_name, "arguments": arguments}
            )

            # Extract content from result
            content = result.get("content", [])
            if isinstance(content, list) and len(content) > 0:
                # Return the first content item's text if available
                first_content = content[0]
                if isinstance(first_content, dict):
                    return first_content.get("text", result)

            return result

        except Exception as e:
            logger.error(
                f"Failed to call tool {tool_name} on {self.server_config.name}: {e}"
            )
            raise

    def get_discovered_tools(self) -> List[MCPTool]:
        """
        Get the list of currently discovered tools (from cache).

        Returns:
            List of discovered tools
        """
        return self._discovered_tools.copy()

    def get_server_info(self) -> Optional[MCPServerInfo]:
        """
        Get server information.

        Returns:
            Server info if available, None otherwise
        """
        return self._server_info

    def get_tool_by_name(self, tool_name: str) -> Optional[MCPTool]:
        """
        Get a specific tool by name from discovered tools.

        Args:
            tool_name: Name of the tool to find

        Returns:
            MCPTool if found, None otherwise
        """
        for tool in self._discovered_tools:
            if tool.name == tool_name:
                return tool
        return None

    def clear_tool_cache(self) -> None:
        """Clear the tool discovery cache."""
        self._discovered_tools.clear()
        self._last_discovery = 0.0
        logger.debug(f"Cleared tool cache for {self.server_config.name}")

    async def send_notification(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send a notification to the MCP server (no response expected).

        Args:
            method: The method name to call
            params: Parameters for the method

        Raises:
            RuntimeError: If not connected
        """
        if not self.transport or self.transport.state != ConnectionState.CONNECTED:
            raise RuntimeError("Not connected to MCP server")

        message = MCPMessage(method=method, params=params or {})

        await self.transport.send_message(message)

    async def is_healthy(self) -> bool:
        """
        Check if the connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.transport:
            return False

        # Use cached result if recent
        now = time.time()
        if (
            now - self._last_health_check
        ) < self.server_config.settings.health_check_interval:
            return self.transport.state == ConnectionState.CONNECTED

        # Perform health check
        try:
            is_healthy = await self.transport.is_healthy()
            self._last_health_check = now
            return is_healthy
        except Exception as e:
            logger.error(f"Health check failed for {self.server_config.name}: {e}")
            return False

    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to the MCP server.

        Returns:
            True if reconnection successful, False otherwise
        """
        if self.transport and self.transport.state == ConnectionState.CONNECTED:
            return True

        max_attempts = self.server_config.settings.retry_attempts
        delay = self.server_config.settings.retry_delay

        for attempt in range(max_attempts):
            try:
                logger.info(
                    f"Reconnection attempt {attempt + 1}/{max_attempts} for {self.server_config.name}"
                )

                # Disconnect first
                await self.disconnect()

                # Wait before retry
                if attempt > 0:
                    await asyncio.sleep(delay * (2**attempt))  # Exponential backoff

                # Attempt connection
                await self.connect()
                return True

            except Exception as e:
                logger.warning(
                    f"Reconnection attempt {attempt + 1} failed for {self.server_config.name}: {e}"
                )

        logger.error(f"All reconnection attempts failed for {self.server_config.name}")
        return False

    def _get_next_message_id(self) -> int:
        """Get the next message ID."""
        self._message_id_counter += 1
        return self._message_id_counter

    def _handle_message(self, message: MCPMessage) -> None:
        """Handle incoming message from the transport."""
        if message.is_response() and message.id in self._pending_requests:
            # Handle response to pending request
            future = self._pending_requests[message.id]
            if not future.done():
                if message.error:
                    error = Exception(f"MCP Error: {message.error}")
                    future.set_exception(error)
                else:
                    future.set_result(message.result)
        elif message.is_notification():
            # Handle notification (could be used for events)
            logger.debug(
                f"Received notification from {self.server_config.name}: {message.method}"
            )
        else:
            logger.warning(
                f"Unhandled message from {self.server_config.name}: {message.to_dict()}"
            )

    def _handle_error(self, error: Exception) -> None:
        """Handle transport error."""
        error_details = f"{type(error).__name__}: {str(error)}"
        logger.error(f"Transport error for {self.server_config.name}: {error_details}")

        # Cancel any pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(error)
        self._pending_requests.clear()

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return (
            self.transport is not None
            and self.transport.state == ConnectionState.CONNECTED
        )

    @property
    def connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self.transport.state if self.transport else ConnectionState.DISCONNECTED

    def __str__(self) -> str:
        """String representation."""
        return f"MCPClient({self.server_config.name}, {self.connection_state.value})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"MCPClient(name={self.server_config.name}, "
            f"type={self.server_config.type}, "
            f"state={self.connection_state.value})"
        )
    
    async def diagnose_connection(self) -> Dict[str, Any]:
        """
        Comprehensive connection diagnostics for debugging.
        
        Returns:
            Dictionary with diagnostic information
        """
        diagnostics = {
            "server_name": self.server_config.name,
            "server_type": self.server_config.type,
            "server_url": self.server_config.url,
            "connection_state": self.connection_state.value,
            "is_connected": self.is_connected,
            "connection_attempts": self._connection_attempts,
            "discovered_tools_count": len(self._discovered_tools),
            "server_info": self._server_info.__dict__ if self._server_info else None,
            "last_discovery": self._last_discovery,
            "last_health_check": self._last_health_check,
        }
        
        # SSE-specific diagnostics
        if self.server_config.type == "sse":
            diagnostics.update({
                "mcp_session_active": self.transport.session is not None if hasattr(self.transport, 'session') else False,
            })
        
        # Test basic connectivity
        if self.transport and hasattr(self.transport, 'client') and self.transport.client:
            try:
                test_response = await self.transport.client.head(
                    self.server_config.url, 
                    timeout=5.0
                )
                diagnostics["connectivity_test"] = {
                    "status": "success",
                    "status_code": test_response.status_code,
                    "headers": dict(test_response.headers)
                }
            except Exception as e:
                diagnostics["connectivity_test"] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return diagnostics


# Import os for environment variables
import os
