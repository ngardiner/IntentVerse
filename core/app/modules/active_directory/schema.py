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
            "id": "ad_dashboard",
            "type": "dashboard",
            "title": "Active Directory Dashboard",
            "description": "Overview of AD domain status and statistics",
            "layout": {
                "x": 0,
                "y": 0,
                "w": 12,
                "h": 6
            },
            "props": {
                "module_id": "active_directory",
                "show_stats": True,
                "show_domain_info": True,
                "show_recent_activity": True
            }
        },
        {
            "id": "ad_users",
            "type": "data_table",
            "title": "User Management",
            "description": "Manage Active Directory users",
            "layout": {
                "x": 0,
                "y": 6,
                "w": 8,
                "h": 8
            },
            "props": {
                "module_id": "active_directory",
                "data_source": "users",
                "show_search": True,
                "show_filters": True,
                "actions": ["create", "edit", "delete", "reset_password", "disable"]
            }
        },
        {
            "id": "ad_groups",
            "type": "data_table", 
            "title": "Group Management",
            "description": "Manage Active Directory groups",
            "layout": {
                "x": 8,
                "y": 6,
                "w": 4,
                "h": 8
            },
            "props": {
                "module_id": "active_directory",
                "data_source": "groups",
                "show_search": True,
                "actions": ["create", "edit", "delete", "manage_members"]
            }
        },
        {
            "id": "ad_ou_structure",
            "type": "tree_view",
            "title": "Organizational Units",
            "description": "Browse and manage OU structure",
            "layout": {
                "x": 0,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "active_directory",
                "data_source": "organizational_units",
                "show_actions": True,
                "expandable": True
            }
        },
        {
            "id": "ad_policies",
            "type": "list_view",
            "title": "Group Policies",
            "description": "Manage Group Policy Objects",
            "layout": {
                "x": 6,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "active_directory",
                "data_source": "group_policies",
                "show_status": True,
                "actions": ["edit", "link", "unlink"]
            }
        }
    ]
}