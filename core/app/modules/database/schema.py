# This dictionary defines the UI representation for the Database module.
# It provides comprehensive observability for database operations and state.
UI_SCHEMA = {
  "module_id": "database",
  "display_name": "Database",
  "components": [
    {
      "component_type": "switchable_group",
      "title": "Database Details",
      "size": "small",
      "views": [
        {
          "component_type": "key_value",
          "title": "Database Connection Info",
          "data_source_api": "/api/v1/database/state",
          "data_path": "connection_info",
          "display_config": {
            "type": "Type",
            "location": "Location",
            "created_at": "Created At"
          }
        },
        {
          "component_type": "key_value",
          "title": "Last Executed Query",
          "data_source_api": "/api/v1/database/state",
          "data_path": "last_query",
          "display_as": "code_block",
          "language": "sql"
        },
        {
          "component_type": "table",
          "title": "Last Query Result",
          "data_source_api": "/api/v1/database/state",
          "data_path": "last_query_result",
          "dynamic_columns": True,
          "max_rows": 100,
          "description": "Results from the most recent SELECT query"
        },
        {
          "component_type": "query_executor",
          "title": "Execute Query",
          "description": "Enter and execute SQL queries directly"
        }
      ]
    },
    {
      "component_type": "switchable_group",
      "title": "Database Activity",
      "size": "large",
      "views": [
        {
          "component_type": "table",
          "title": "Query History",
          "data_source_api": "/api/v1/database/state",
          "data_path": "query_history",
          "columns": [
            { "header": "Timestamp", "data_key": "timestamp" },
            { "header": "Type", "data_key": "query_type" },
            { "header": "Query", "data_key": "query", "truncate": 50 },
            { "header": "Results", "data_key": "result_count" }
          ],
          "sort_by": "timestamp",
          "sort_order": "desc",
          "max_rows": 20
        },
        {
          "component_type": "table",
          "title": "Database Tables",
          "data_source_api": "/api/v1/database/state",
          "data_path": "tables",
          "data_transform": "object_to_array",
          "columns": [
            { "header": "Table Name", "data_key": "name" },
            { "header": "Columns", "data_key": "column_count" },
            { "header": "Rows", "data_key": "row_count" },
            { "header": "Primary Keys", "data_key": "primary_keys" }
          ]
        }
      ]
    }
  ]
}