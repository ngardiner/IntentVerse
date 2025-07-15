#!/usr/bin/env python3
"""
Streamable-HTTP MCP Test Server

A test MCP server that implements streamable-HTTP protocol
for testing MCP proxy functionality.
"""

import asyncio
import logging
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def http_hello_world(name: str = "World") -> dict:
    """
    HTTP server specific hello world tool.
    
    Args:
        name: Name to greet
        
    Returns:
        Greeting message from HTTP server
    """
    return {
        "message": f"Hello {name} from HTTP MCP Server!",
        "server_type": "streamable-http",
        "protocol": "Streamable HTTP"
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
        "processed_data": f"HTTP processed: {input_data}",
        "server_name": "http-server",
        "timestamp": asyncio.get_event_loop().time(),
        "tool_name": "common_tool"
    }


async def main():
    """Main entry point for HTTP MCP server."""
    logger.info("Starting HTTP MCP Test Server...")
    
    # Create FastMCP server
    server = FastMCP("HTTP Test Server")
    
    # Register tools
    server.add_tool(http_hello_world)
    server.add_tool(common_tool)
    
    logger.info("Registered tools: http_hello_world, common_tool")
    
    # Run server on port 8003 for streamable-http
    host = "0.0.0.0"
    port = 8003
    
    logger.info(f"Starting streamable-HTTP server on {host}:{port}")
    await server.run_streamable_http_async(host=host, port=port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("HTTP MCP Test Server stopped")