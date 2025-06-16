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
        self.client = httpx.AsyncClient(base_url=CORE_API_URL)

    async def get_tool_manifest(self) -> List[Dict[str, Any]]:
        """
        Fetches the tool manifest from the Core Engine.
        
        This manifest contains the definitions for all tools that the
        Core Engine has loaded.
        
        Returns:
            A list of tool definition dictionaries.
        """
        try:
            print("CoreClient: Fetching tool manifest from Core Engine...")
            # We'll need to create this endpoint in the core service.
            response = await self.client.get("/api/v1/tools/manifest")
            response.raise_for_status()  # Raises an exception for 4xx or 5xx status codes
            print("CoreClient: Successfully fetched tool manifest.")
            return response.json()
        except httpx.RequestError as e:
            print(f"An error occurred while requesting the tool manifest: {e}")
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
            print(f"CoreClient: Executing tool with payload: {payload}")
            response = await self.client.post("/api/v1/execute", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"An error occurred while executing tool: {e}")
            return {"status": "error", "result": str(e)}

    async def close(self):
        """
        Closes the HTTP client session.
        """
        await self.client.aclose()
