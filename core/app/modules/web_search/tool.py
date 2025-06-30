from typing import Any, Dict, List, Optional
from datetime import datetime
import random
from ..base_tool import BaseTool


class WebSearchTool(BaseTool):
    """
    Implements a mock web search tool that logs search queries and returns realistic-looking results.
    This tool is designed to provide visibility into search queries while giving useful responses.
    """

    def __init__(self, state_manager: Any):
        """
        Initializes the WebSearchTool with a reference to the state manager.
        Sets up the initial state for storing search history.
        """
        super().__init__(state_manager)
        if "web_search" not in self.state_manager.get_full_state():
            self.state_manager.set(
                "web_search", {"search_history": [], "last_search_results": []}
            )

        # Load predefined search topics for more realistic results
        self.search_topics = {
            "programming": [
                {
                    "title": "Python Programming Language",
                    "url": "https://www.python.org/",
                    "snippet": "Python is a programming language that lets you work quickly and integrate systems more effectively.",
                },
                {
                    "title": "JavaScript - MDN Web Docs",
                    "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
                    "snippet": "JavaScript (JS) is a lightweight, interpreted, or just-in-time compiled programming language with first-class functions.",
                },
                {
                    "title": "GitHub: Where the world builds software",
                    "url": "https://github.com/",
                    "snippet": "GitHub is where over 65 million developers shape the future of software, together.",
                },
            ],
            "ai": [
                {
                    "title": "What is Artificial Intelligence (AI)?",
                    "url": "https://www.ibm.com/cloud/learn/what-is-artificial-intelligence",
                    "snippet": "Artificial intelligence is a wide-ranging branch of computer science concerned with building smart machines capable of performing tasks that typically require human intelligence.",
                },
                {
                    "title": "Machine Learning - Stanford University",
                    "url": "https://www.coursera.org/learn/machine-learning",
                    "snippet": "This course provides a broad introduction to machine learning, data mining, and statistical pattern recognition.",
                },
                {
                    "title": "OpenAI",
                    "url": "https://openai.com/",
                    "snippet": "OpenAI is an AI research and deployment company. Our mission is to ensure that artificial general intelligence benefits all of humanity.",
                },
            ],
            "news": [
                {
                    "title": "BBC News - Home",
                    "url": "https://www.bbc.com/news",
                    "snippet": "Visit BBC News for up-to-the-minute news, breaking news, video, audio and feature stories.",
                },
                {
                    "title": "CNN - Breaking News, Latest News and Videos",
                    "url": "https://www.cnn.com/",
                    "snippet": "View the latest news and breaking news today for U.S., world, weather, entertainment, politics and health.",
                },
                {
                    "title": "Reuters - Breaking International News & Views",
                    "url": "https://www.reuters.com/",
                    "snippet": "Reuters provides business, financial, national and international news to professionals via desktop terminals, the world's media organizations, and directly to consumers.",
                },
            ],
        }

    def get_ui_schema(self) -> Dict[str, Any]:
        """Returns the UI schema for the web search module."""
        from .schema import UI_SCHEMA

        return UI_SCHEMA

    def search(self, query: str) -> List[Dict[str, str]]:
        """
        Performs a mock web search and returns a list of results.
        Logs the search query and results in the state manager.

        Args:
            query: The search query string

        Returns:
            A list of dictionaries containing search results with title, URL, and snippet
        """
        print(f"WEB SEARCH: Searching for: {query}")

        # Generate realistic search results based on the query
        results = self._generate_search_results(query)

        # Get the current state
        web_search_state = self.state_manager.get("web_search")
        search_history = web_search_state.get("search_history", [])

        # Add the new search to history with timestamp
        search_entry = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "results_count": len(results),
        }
        search_history.append(search_entry)

        # Keep only the last 20 searches in history
        if len(search_history) > 20:
            search_history = search_history[-20:]

        # Update the state with new history and last results
        self.state_manager.set(
            "web_search",
            {"search_history": search_history, "last_search_results": results},
        )

        return results

    def _generate_search_results(self, query: str) -> List[Dict[str, str]]:
        """
        Generates realistic search results based on the query.

        Args:
            query: The search query string

        Returns:
            A list of dictionaries containing search results
        """
        # Determine which topic the query might be related to
        query_lower = query.lower()

        # Default results if no specific topic matches
        results = []

        # Check if query matches any of our predefined topics
        if any(
            term in query_lower
            for term in [
                "python",
                "javascript",
                "code",
                "programming",
                "developer",
                "software",
            ]
        ):
            results = self._customize_results(self.search_topics["programming"], query)
        elif any(
            term in query_lower
            for term in [
                "ai",
                "artificial intelligence",
                "machine learning",
                "neural",
                "model",
            ]
        ):
            results = self._customize_results(self.search_topics["ai"], query)
        elif any(
            term in query_lower
            for term in ["news", "current events", "today", "latest"]
        ):
            results = self._customize_results(self.search_topics["news"], query)

        # If no specific topic matched or we need more results, add generic ones
        if len(results) < 3:
            generic_results = [
                {
                    "title": f"Results for '{query}' | IntentVerse Search",
                    "url": f"https://example.com/search?q={query.replace(' ', '+')}",
                    "snippet": f"Find the best information about {query} with our comprehensive search results.",
                },
                {
                    "title": f"{query.title()} - Wikipedia",
                    "url": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
                    "snippet": f"Read about {query} on Wikipedia, the free encyclopedia that anyone can edit.",
                },
                {
                    "title": "The Model Context Protocol (MCP) - Official Docs",
                    "url": "https://modelcontextprotocol.io/",
                    "snippet": "MCP is an open protocol that standardizes how applications provide context to LLMs.",
                },
            ]
            results.extend(generic_results)

        # Ensure we return at least 3 but no more than 5 results
        return results[: min(5, max(3, len(results)))]

    def _customize_results(
        self, base_results: List[Dict[str, str]], query: str
    ) -> List[Dict[str, str]]:
        """
        Customizes the base results to include the query terms.

        Args:
            base_results: The base results to customize
            query: The search query

        Returns:
            Customized search results
        """
        customized = []
        for result in base_results:
            # Create a copy to avoid modifying the original
            custom_result = result.copy()

            # Sometimes customize the title to include the query
            if random.random() > 0.7:
                custom_result["title"] = f"{result['title']} - {query.title()}"

            # Sometimes enhance the snippet to include the query
            if random.random() > 0.5:
                custom_result["snippet"] = (
                    f"{result['snippet']} Learn more about {query} here."
                )

            customized.append(custom_result)

        return customized

    def get_search_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Returns the search history.

        Args:
            limit: Maximum number of history items to return

        Returns:
            A list of search history entries
        """
        web_search_state = self.state_manager.get("web_search")
        search_history = web_search_state.get("search_history", [])

        # Return the most recent searches first
        return search_history[-limit:][::-1]

    def clear_search_history(self) -> Dict[str, str]:
        """
        Clears the search history.

        Returns:
            A status message
        """
        web_search_state = self.state_manager.get("web_search")
        web_search_state["search_history"] = []
        self.state_manager.set("web_search", web_search_state)

        return {"status": "success", "message": "Search history cleared successfully"}

    def get_last_search_results(self) -> List[Dict[str, str]]:
        """
        Returns the results of the last search.

        Returns:
            A list of search results
        """
        web_search_state = self.state_manager.get("web_search")
        return web_search_state.get("last_search_results", [])
