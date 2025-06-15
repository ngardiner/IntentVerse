# This dictionary defines the UI representation for the Email module.
# It will be loaded by the module_loader and exposed via the /api/v1/ui/layout endpoint.
UI_SCHEMA = {
  "module_id": "email",
  "display_name": "Email",
  "components": [
    {
      "component_type": "table",
      "title": "Sent Items",
      "data_source_api": "/api/v1/email/sent_items",
      "columns": [
        { "header": "To", "data_key": "to" },
        { "header": "Subject", "data_key": "subject" },
        { "header": "Timestamp", "data_key": "timestamp" }
      ]
    }
  ]
}