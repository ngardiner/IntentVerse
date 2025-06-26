import logging
import httpx
import os
from typing import Dict, Any, List

# The base URL for the core service API, using the Docker service name.
CORE_API_URL = os.environ.get("CORE_API_URL", "http://core:8000")

class CoreClient:
    """
    An asynchronous HTTP client for communicating with the Core Engine API.
    """

    def __init__(self):
        """
        Initializes the asynchronous HTTP client.
        """
        # Get the service API key from environment variable
        self.api_key = os.environ.get("SERVICE_API_KEY", "dev-service-key-12345")
        
        # Set up headers with API key for service authentication
        headers = {
            "X-API-Key": self.api_key
        }
        
        self.client = httpx.AsyncClient(base_url=CORE_API_URL, headers=headers)

    async def get_tool_manifest(self) -> List[Dict[str, Any]]:
        """
        Fetches the tool manifest from the Core Engine.
        
        This manifest contains the definitions for all tools that the
        Core Engine has loaded.
        
        Returns:
            A list of tool definition dictionaries.
        """
        try:
            logging.info("CoreClient: Fetching tool manifest from Core Engine...")
            response = await self.client.get("/api/v1/tools/manifest")
            response.raise_for_status()  # Raises an exception for 4xx or 5xx status codes
            logging.info("CoreClient: Successfully fetched tool manifest.")
            return response.json()
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            # Extract error details from HTTP response if available
            error_message = str(e)
            if isinstance(e, httpx.HTTPStatusError):
                try:
                    # Try to extract error detail from JSON response
                    response_data = e.response.json()
                    if "detail" in response_data:
                        error_message = f"{str(e)} - {response_data['detail']}"
                except Exception:
                    # If we can't parse the response, just use the original error message
                    pass
            
            logging.error(f"An error occurred while requesting the tool manifest: {error_message}")
            return []

    async def execute_tool(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends a tool execution request to the Core Engine.

        Args:
            payload: The dictionary containing the tool name and parameters.

        Returns:
            A dictionary containing the result of the tool execution.
        """
        try:
            # Skip logging timeline events to avoid infinite recursion
            if payload.get("tool_name", "").startswith("timeline."):
                logging.debug(f"CoreClient: Executing timeline tool: {payload['tool_name']}")
            else:
                logging.info(f"CoreClient: Executing tool with payload: {payload}")
                
                # Log the tool execution to the timeline
                try:
                    await self.client.post("/api/v1/execute", json={
                        "tool_name": "timeline.log_tool_execution",
                        "parameters": {
                            "tool_name": payload["tool_name"],
                            "parameters": payload.get("parameters", {}),
                            "result": {"status": "pending"}
                        }
                    })
                except Exception as e:
                    logging.error(f"Failed to log tool execution to timeline: {e}")
                
            response = await self.client.post("/api/v1/execute", json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Log the tool execution result to the timeline if it's not a timeline tool
            if not payload.get("tool_name", "").startswith("timeline."):
                try:
                    await self.client.post("/api/v1/execute", json={
                        "tool_name": "timeline.log_tool_execution",
                        "parameters": {
                            "tool_name": payload["tool_name"],
                            "parameters": payload.get("parameters", {}),
                            "result": result
                        }
                    })
                except Exception as e:
                    logging.error(f"Failed to log tool execution result to timeline: {e}")
            
            return result
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logging.error(f"An error occurred while executing tool: {e}")
            
            # Extract error details from HTTP response if available
            error_message = str(e)
            if isinstance(e, httpx.HTTPStatusError):
                try:
                    # Try to extract error detail from JSON response
                    response_data = e.response.json()
                    if "detail" in response_data:
                        error_message = f"{str(e)} - {response_data['detail']}"
                except Exception:
                    # If we can't parse the response, just use the original error message
                    pass
            
            # Log the error to the timeline if it's not a timeline tool
            if not payload.get("tool_name", "").startswith("timeline."):
                try:
                    await self.client.post("/api/v1/execute", json={
                        "tool_name": "timeline.log_error",
                        "parameters": {
                            "title": f"Error executing tool: {payload.get('tool_name')}",
                            "description": error_message,
                            "details": {
                                "tool_name": payload.get("tool_name"),
                                "parameters": payload.get("parameters", {}),
                                "error": error_message
                            }
                        }
                    })
                except Exception as log_error:
                    logging.error(f"Failed to log error to timeline: {log_error}")
            
            return {"status": "error", "result": error_message}

    async def close(self):
        """
        Closes the HTTP client session.
        """
        await self.client.aclose()