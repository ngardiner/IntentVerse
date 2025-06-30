# This dictionary defines the UI representation for the File System module.
# It will be loaded by the module_loader and exposed via the /api/v1/ui/layout endpoint.
UI_SCHEMA = {
    "module_id": "filesystem",
    "display_name": "File System",
    "size": "small",
    "components": [
        {
            "component_type": "file_tree",
            "title": "Virtual File System",
            "data_source_api": "/api/v1/filesystem/state",
            "size": "small",
        }
    ],
}
