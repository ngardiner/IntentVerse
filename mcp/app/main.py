import sys
import asyncio
import logging
from fastmcp import FastMCP

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

    # Log the MCP start event to the timeline
    # We'll do this after the server is fully initialized to ensure the timeline module is loaded

    # Initialize the client and the registrar
    core_client = CoreClient()
    tool_registrar = ToolRegistrar(core_client)

    # Initialize the MCP Proxy Engine (optional - will gracefully handle if config doesn't exist)
    await tool_registrar.initialize_proxy_engine()

    # Create the FastMCPServer instance
    server = FastMCP("IntentVerse Mock Tool Server")

    # Call the registrar to dynamically load tools from the core engine and proxy tools
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

        # Now that everything is set up, log the MCP start event to the timeline
        try:
            await core_client.execute_tool(
                {
                    "tool_name": "timeline.add_event",
                    "parameters": {
                        "event_type": "system",
                        "title": "MCP Interface Started",
                        "description": "The MCP Interface service has been started and is ready to accept connections.",
                    },
                }
            )
        except Exception as e:
            logging.error(f"Failed to log MCP start event: {e}")
            # Continue even if logging fails

        await server.run_async(transport="streamable-http", host=host, port=port)


async def shutdown(tool_registrar: ToolRegistrar = None):
    """Log the MCP shutdown event to the timeline and cleanup resources."""
    try:
        # Create a temporary client to log the shutdown event
        temp_client = CoreClient()

        # Try to log the shutdown event, but don't worry if it fails
        try:
            await temp_client.execute_tool(
                {
                    "tool_name": "timeline.add_event",
                    "parameters": {
                        "event_type": "system",
                        "title": "MCP Interface Stopped",
                        "description": "The MCP Interface service has been stopped.",
                    },
                }
            )
        except Exception as e:
            logging.debug(f"Could not log MCP shutdown event: {e}")

        await temp_client.close()

        # Shutdown the tool registrar (which will stop the proxy engine)
        if tool_registrar:
            await tool_registrar.shutdown()

    except Exception as e:
        logging.error(f"Error during shutdown: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nShutting down MCP Interface.")
        try:
            asyncio.run(shutdown())
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")
