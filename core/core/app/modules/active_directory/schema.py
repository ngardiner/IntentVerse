"""
UI Schema for Active Directory module.
"""

UI_SCHEMA = {
    "module_id": "active_directory",
    "display_name": "Active Directory",
    "category": "identity",
    "description": "Mock Active Directory environment for user and group management",
    "is_sandbox": True,
    "default_enabled": False,
    "components": [
        {
            "id": "active_directory_dashboard",
            "type": "dashboard",
            "title": "Active Directory Dashboard",
            "description": "Main dashboard for Active Directory management",
            "layout": {
                "x": 0,
                "y": 0,
                "w": 12,
                "h": 8
            },
            "props": {
                "module_id": "active_directory",
                "show_stats": True,
                "show_recent_activity": True
            }
        },
        {
            "id": "active_directory_management",
            "type": "management_panel",
            "title": "Active Directory Management",
            "description": "Management interface for Active Directory",
            "layout": {
                "x": 0,
                "y": 8,
                "w": 12,
                "h": 6
            },
            "props": {
                "module_id": "active_directory",
                "show_actions": True,
                "show_search": True
            }
        }
    ]
}
