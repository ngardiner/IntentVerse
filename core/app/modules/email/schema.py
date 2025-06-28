# This dictionary defines the UI representation for the Email module.
# It will be loaded by the module_loader and exposed via the /api/v1/ui/layout endpoint.
UI_SCHEMA = {
  "module_id": "email",
  "display_name": "Email",
  "size": "large",
  "component_type": "switchable_group",
  "components": [
    {
      "component_type": "table",
      "title": "Inbox",
      "data_source_api": "/api/v1/email/state",
      "data_path": "inbox",
      "columns": [
        { "header": "Date", "data_key": "timestamp" },
        { "header": "From", "data_key": "from" },
        { "header": "Subject", "data_key": "subject" }
      ]
    },
    {
      "component_type": "table",
      "title": "Sent Items",
      "data_source_api": "/api/v1/email/state",
      "data_path": "sent_items",
      "columns": [
        { "header": "Date", "data_key": "timestamp" },
        { "header": "To", "data_key": "to" },
        { "header": "Subject", "data_key": "subject" }
      ]
    },
    {
      "component_type": "table",
      "title": "Drafts",
      "data_source_api": "/api/v1/email/state",
      "data_path": "drafts",
      "columns": [
        { "header": "Date", "data_key": "timestamp" },
        { "header": "To", "data_key": "to" },
        { "header": "Subject", "data_key": "subject" }
      ]
    }
  ]
}