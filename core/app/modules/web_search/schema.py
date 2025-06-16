# This dictionary defines the UI representation for the Web Search module.
UI_SCHEMA = {
  "module_id": "web_search",
  "display_name": "Web Search",
  "components": [
    {
      "component_type": "table",
      "title": "Last Search Results",
      "data_source_api": "/api/v1/web_search/state",
      "columns": [
        { "header": "Title", "data_key": "title" },
        { "header": "URL", "data_key": "url" },
        { "header": "Snippet", "data_key": "snippet" }
      ]
    }
  ]
}
