# This dictionary defines the UI representation for the Memory module.
# It will be loaded by the module_loader and exposed via the /api/v1/ui/layout endpoint.
UI_SCHEMA = {
    "module_id": "memory",
    "display_name": "Memory",
    "size": "small",
    "components": [
        {
            "component_type": "key_value_viewer",
            "title": "Model's Scratchpad",
            "data_source_api": "/api/v1/memory/state",
            "size": "small",
        }
    ],
}
