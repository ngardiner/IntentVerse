"""
UI Schema for Firewall Management module.
"""

UI_SCHEMA = {
    "module_id": "firewall_management",
    "display_name": "Firewall Management",
    "category": "infrastructure",
    "description": "Mock firewall environment for network security management and rule configuration",
    "is_sandbox": True,
    "default_enabled": False,
    "components": [
        {
            "id": "firewall_dashboard",
            "type": "dashboard",
            "title": "Firewall Dashboard",
            "description": "Overview of firewall status, traffic, and security events",
            "layout": {
                "x": 0,
                "y": 0,
                "w": 12,
                "h": 6
            },
            "props": {
                "module_id": "firewall_management",
                "show_stats": True,
                "show_traffic_summary": True,
                "show_threat_alerts": True,
                "show_interface_status": True
            }
        },
        {
            "id": "firewall_rules",
            "type": "data_table",
            "title": "Firewall Rules",
            "description": "Manage firewall rules and access control policies",
            "layout": {
                "x": 0,
                "y": 6,
                "w": 8,
                "h": 8
            },
            "props": {
                "module_id": "firewall_management",
                "data_source": "firewall_rules",
                "show_search": True,
                "show_filters": True,
                "actions": ["create", "edit", "delete", "enable", "disable", "move_up", "move_down"]
            }
        },
        {
            "id": "firewall_interfaces",
            "type": "status_panel",
            "title": "Network Interfaces",
            "description": "Monitor firewall interface status and configuration",
            "layout": {
                "x": 8,
                "y": 6,
                "w": 4,
                "h": 8
            },
            "props": {
                "module_id": "firewall_management",
                "data_source": "network_interfaces",
                "show_status": True,
                "show_traffic_stats": True,
                "actions": ["configure", "reset_stats"]
            }
        },
        {
            "id": "firewall_logs",
            "type": "log_viewer",
            "title": "Security Logs",
            "description": "View firewall logs and security events",
            "layout": {
                "x": 0,
                "y": 14,
                "w": 8,
                "h": 6
            },
            "props": {
                "module_id": "firewall_management",
                "data_source": "security_logs",
                "show_filters": True,
                "show_search": True,
                "real_time": True,
                "actions": ["export", "clear_logs"]
            }
        },
        {
            "id": "firewall_vpn",
            "type": "vpn_panel",
            "title": "VPN Configuration",
            "description": "Manage VPN tunnels and remote access",
            "layout": {
                "x": 8,
                "y": 14,
                "w": 4,
                "h": 6
            },
            "props": {
                "module_id": "firewall_management",
                "data_source": "vpn_tunnels",
                "show_status": True,
                "show_connections": True,
                "actions": ["create_tunnel", "configure", "disconnect"]
            }
        }
    ]
}