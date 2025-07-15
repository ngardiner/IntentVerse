#!/usr/bin/env python3
"""
SSE MCP Test Server

A test MCP server that implements Server-Sent Events (SSE) protocol
for testing MCP proxy functionality.
"""

import asyncio
import logging
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sse_hello_world(name: str = "World") -> dict:
    """
    SSE server specific hello world tool.
    
    Args:
        name: Name to greet
        
    Returns:
        Greeting message from SSE server
    """
    return {
        "message": f"Hello {name} from SSE MCP Server!",
        "server_type": "sse",
        "protocol": "Server-Sent Events"
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
        "processed_data": f"SSE processed: {input_data}",
        "server_name": "sse-server",
        "timestamp": asyncio.get_event_loop().time(),
        "tool_name": "common_tool"
    }


async def main():
    """Main entry point for SSE MCP server."""
    logger.info("Starting SSE MCP Test Server...")
    
    # Create FastMCP server
    server = FastMCP("SSE Test Server")
    
    # Register tools
    server.add_tool(sse_hello_world)
    server.add_tool(common_tool)
    
    logger.info("Registered tools: sse_hello_world, common_tool")
    
    # Run server on port 8002 for SSE
    host = "0.0.0.0"
    port = 8002
    
    logger.info(f"Starting SSE server on {host}:{port}")
    await server.run_sse_async(host=host, port=port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SSE MCP Test Server stopped")