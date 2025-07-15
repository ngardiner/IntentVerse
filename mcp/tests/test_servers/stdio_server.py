#!/usr/bin/env python3
"""
STDIO MCP Test Server

A test MCP server that implements stdio protocol
for testing MCP proxy functionality.
"""

import asyncio
import logging
import sys
from fastmcp import FastMCP

# Configure logging for stdio mode (minimal to avoid interfering with MCP protocol)
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger(__name__)


async def stdio_hello_world(name: str = "World") -> dict:
    """
    STDIO server specific hello world tool.
    
    Args:
        name: Name to greet
        
    Returns:
        Greeting message from STDIO server
    """
    return {
        "message": f"Hello {name} from STDIO MCP Server!",
        "server_type": "stdio",
        "protocol": "Standard Input/Output"
    }


async def common_tool(input_data: str = "test") -> dict:
    """
    Common tool that exists on all test servers.
    This tool should be deconflicted by the proxy using server name prefixes.
    
    Args:
        input_data: Input data to process
        
    Returns:
        Processed data with server identification
    """
    return {
        "processed_data": f"STDIO processed: {input_data}",
        "server_name": "stdio-server",
        "timestamp": asyncio.get_event_loop().time(),
        "tool_name": "common_tool"
    }


async def main():
    """Main entry point for STDIO MCP server."""
    # Only log to stderr in stdio mode to avoid interfering with MCP protocol
    logger.warning("Starting STDIO MCP Test Server...")
    
    # Create FastMCP server
    server = FastMCP("STDIO Test Server")
    
    # Register tools
    server.add_tool(stdio_hello_world)
    server.add_tool(common_tool)
    
    logger.warning("Registered tools: stdio_hello_world, common_tool")
    
    # Run server in stdio mode
    logger.warning("Starting STDIO server")
    await server.run_stdio_async()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("STDIO MCP Test Server stopped")