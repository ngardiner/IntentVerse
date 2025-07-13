"""
UI Schema for Azure Entra ID module.
"""

UI_SCHEMA = {
    "module_id": "azure_entra_id",
    "display_name": "Azure Entra ID",
    "category": "identity",
    "description": "Mock Azure Entra ID environment for cloud identity and access management",
    "is_sandbox": True,
    "default_enabled": False,
    "components": [
        {
            "id": "entra_dashboard",
            "type": "dashboard",
            "title": "Azure Entra ID Dashboard",
            "description": "Overview of tenant status and identity statistics",
            "layout": {
                "x": 0,
                "y": 0,
                "w": 12,
                "h": 6
            },
            "props": {
                "module_id": "azure_entra_id",
                "show_stats": True,
                "show_tenant_info": True,
                "show_sign_ins": True,
                "show_security_alerts": True
            }
        },
        {
            "id": "entra_users",
            "type": "data_table",
            "title": "User Management",
            "description": "Manage Azure Entra ID users and guest accounts",
            "layout": {
                "x": 0,
                "y": 6,
                "w": 8,
                "h": 8
            },
            "props": {
                "module_id": "azure_entra_id",
                "data_source": "users",
                "show_search": True,
                "show_filters": True,
                "actions": ["create", "edit", "delete", "reset_password", "block_sign_in", "invite_guest"]
            }
        },
        {
            "id": "entra_applications",
            "type": "data_table",
            "title": "App Registrations",
            "description": "Manage application registrations and service principals",
            "layout": {
                "x": 8,
                "y": 6,
                "w": 4,
                "h": 8
            },
            "props": {
                "module_id": "azure_entra_id",
                "data_source": "applications",
                "show_search": True,
                "actions": ["register", "configure", "delete", "manage_permissions"]
            }
        },
        {
            "id": "entra_conditional_access",
            "type": "policy_manager",
            "title": "Conditional Access",
            "description": "Manage conditional access policies",
            "layout": {
                "x": 0,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "azure_entra_id",
                "data_source": "conditional_access_policies",
                "show_status": True,
                "actions": ["create", "edit", "enable", "disable", "test"]
            }
        },
        {
            "id": "entra_mfa",
            "type": "security_panel",
            "title": "Multi-Factor Authentication",
            "description": "Configure MFA settings and methods",
            "layout": {
                "x": 6,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "azure_entra_id",
                "data_source": "mfa_settings",
                "show_methods": True,
                "show_enforcement": True,
                "actions": ["configure", "enforce", "bypass"]
            }
        }
    ]
}