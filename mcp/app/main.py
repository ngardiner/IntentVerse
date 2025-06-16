import sys
import asyncio
import logging
from fastmcp import FastMCP

# Import the components we just built
from .registrar import ToolRegistrar
from .core_client import CoreClient
from .logging_config import setup_logging

async def main():
    """
    The main entry point for the MCP Interface service.

    This function initializes the MCP server and, based on command-line arguments,
    runs it in either Streamable HTTP mode or stdio mode.
    """
    setup_logging()
    logging.info("Starting IntentVerse MCP Interface...")

    # Initialize the client and the registrar
    core_client = CoreClient()
    tool_registrar = ToolRegistrar(core_client)

    # Create the FastMCPServer instance
    server = FastMCP("IntentVerse Mock Tool Server")

    # Call the registrar to dynamically load tools from the core engine
    await tool_registrar.register_tools(server)

    # Check for the --stdio flag to determine the run mode
    if "--stdio" in sys.argv:
        logging.info("Running in stdio mode.")
        await server.run_stdio()
    else:
        # This runs the server as a persistent web server
        host = "0.0.0.0"
        port = 8001
        logging.info(f"Running in Streamable HTTP mode on {host}:{port}")
        await server.run(host=host, port=port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nShutting down MCP Interface.")
    # In a real app, you might want to gracefully close the client connection
    # finally:
    #     asyncio.run(core_client.close())