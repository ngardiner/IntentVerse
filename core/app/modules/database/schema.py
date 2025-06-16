# This dictionary defines the UI representation for the Database module.
UI_SCHEMA = {
  "module_id": "database",
  "display_name": "Database",
  "components": [
    {
      "component_type": "table",
      "title": "Last Query Result",
      "data_source_api": "/api/v1/database/state",
      # Note: The columns would ideally be dynamic based on the query.
      # For the placeholder, we'll assume a fixed structure.
      "columns": [
        { "header": "id", "data_key": "id" },
        { "header": "product_name", "data_key": "product_name" },
        { "header": "price", "data_key": "price" }
      ]
    }
  ]
}
