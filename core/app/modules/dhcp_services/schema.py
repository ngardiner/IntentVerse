"""
UI Schema for DHCP Services module.
"""

UI_SCHEMA = {
    "module_id": "dhcp_services",
    "display_name": "DHCP Services",
    "category": "infrastructure",
    "description": "Mock DHCP server environment for dynamic IP address management",
    "is_sandbox": True,
    "default_enabled": False,
    "components": [
        {
            "id": "dhcp_dashboard",
            "type": "dashboard",
            "title": "DHCP Dashboard",
            "description": "Overview of DHCP server status and lease statistics",
            "layout": {
                "x": 0,
                "y": 0,
                "w": 12,
                "h": 6
            },
            "props": {
                "module_id": "dhcp_services",
                "show_stats": True,
                "show_server_status": True,
                "show_scope_utilization": True,
                "show_recent_activity": True
            }
        },
        {
            "id": "dhcp_scopes",
            "type": "data_table",
            "title": "DHCP Scopes",
            "description": "Manage DHCP scopes and IP address ranges",
            "layout": {
                "x": 0,
                "y": 6,
                "w": 8,
                "h": 8
            },
            "props": {
                "module_id": "dhcp_services",
                "data_source": "dhcp_scopes",
                "show_search": True,
                "show_filters": True,
                "actions": ["create", "edit", "delete", "activate", "deactivate", "reconcile"]
            }
        },
        {
            "id": "dhcp_leases",
            "type": "data_table",
            "title": "Active Leases",
            "description": "Monitor active DHCP leases and reservations",
            "layout": {
                "x": 8,
                "y": 6,
                "w": 4,
                "h": 8
            },
            "props": {
                "module_id": "dhcp_services",
                "data_source": "dhcp_leases",
                "show_search": True,
                "show_lease_time": True,
                "actions": ["release", "renew", "convert_to_reservation"]
            }
        },
        {
            "id": "dhcp_reservations",
            "type": "data_table",
            "title": "Reservations",
            "description": "Manage DHCP reservations for specific devices",
            "layout": {
                "x": 0,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "dhcp_services",
                "data_source": "dhcp_reservations",
                "show_search": True,
                "show_mac_addresses": True,
                "actions": ["create", "edit", "delete", "activate"]
            }
        },
        {
            "id": "dhcp_options",
            "type": "configuration_panel",
            "title": "DHCP Options",
            "description": "Configure DHCP server and scope options",
            "layout": {
                "x": 6,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "dhcp_services",
                "data_source": "dhcp_options",
                "show_global_options": True,
                "show_scope_options": True,
                "actions": ["configure", "reset_to_default"]
            }
        }
    ]
}