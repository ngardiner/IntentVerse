from typing import Any, Dict, List
from ..base_tool import BaseTool

class WebSearchTool(BaseTool):
    """
    Implements the logic for a mock web search tool.
    NOTE: This is a barebones placeholder.
    """

    def __init__(self, state_manager: Any):
        """
        Initializes the WebSearchTool with a reference to the state manager.
        """
        super().__init__(state_manager)
        if 'web_search' not in self.state_manager.get_full_state():
            self.state_manager.set('web_search', {"search_history": []})

    def search(self, query: str) -> List[Dict[str, str]]:
        """
        Performs a mock web search and returns a list of results.
        """
        print(f"WEB SEARCH: Searching for: {query}")
        
        # In a real implementation, this could call an external search API.
        # For our sandbox, we return consistent mock results.
        mock_results = [
            {
                "title": f"Results for '{query}' | IntentVerse Search",
                "url": f"https://example.com/search?q={query.replace(' ', '+')}",
                "snippet": "This is a mock search result snippet for your query..."
            },
            {
                "title": "The Model Context Protocol (MCP) - Official Docs",
                "url": "https://modelcontextprotocol.io/",
                "snippet": "MCP is an open protocol that standardizes how applications provide context to LLMs."
            }
        ]
        
        search_history = self.state_manager.get('web_search').get("search_history", [])
        search_history.append({"query": query, "results": mock_results})
        self.state_manager.set('web_search', {"search_history": search_history})
        
        return mock_results