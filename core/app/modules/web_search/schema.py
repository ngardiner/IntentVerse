# This dictionary defines the UI representation for the Web Search module.
UI_SCHEMA = {
  "module_id": "web_search",
  "display_name": "Web Search",
  "description": "A mock web search tool that logs and displays search queries and results",
  "size": "large",
  "components": [
    {
      "component_type": "table",
      "title": "Last Search Results",
      "description": "Results from the most recent search query",
      "data_source_api": "/api/v1/web_search/state",
      "data_path": "last_search_results",
      "columns": [
        { "header": "Title", "data_key": "title", "width": "30%" },
        { "header": "URL", "data_key": "url", "width": "30%" },
        { "header": "Snippet", "data_key": "snippet", "width": "40%" }
      ]
    },
    {
      "component_type": "table",
      "title": "Search History",
      "description": "Record of recent search queries",
      "data_source_api": "/api/v1/web_search/state",
      "data_path": "search_history",
      "columns": [
        { "header": "Query", "data_key": "query", "width": "60%" },
        { "header": "Timestamp", "data_key": "timestamp", "width": "25%" },
        { "header": "Results", "data_key": "results_count", "width": "15%" }
      ]
    }
  ]
}
