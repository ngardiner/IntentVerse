# This dictionary defines the UI representation for the Timeline module.
# It will be loaded by the module_loader and exposed via the /api/v1/ui/layout endpoint.
UI_SCHEMA = {
  "module_id": "timeline",
  "display_name": "Timeline",
  "size": "xlarge",
  "components": [
    {
      "component_type": "table",
      "title": "MCP Activity Timeline",
      "data_source_api": "/api/v1/timeline/events",
      "columns": [
        { "header": "Timestamp", "data_key": "timestamp" },
        { "header": "Event Type", "data_key": "event_type" },
        { "header": "Title", "data_key": "title" },
        { "header": "Description", "data_key": "description" },
        { "header": "Status", "data_key": "status" }
      ],
      "sort_by": "timestamp",
      "sort_order": "desc",
      "max_rows": 100,
      "hidden": True  # Set to be hidden by default
    }
  ]
}