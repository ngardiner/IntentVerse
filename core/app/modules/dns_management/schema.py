"""
UI Schema for DNS Management module.
"""

UI_SCHEMA = {
    "module_id": "dns_management",
    "display_name": "DNS Management",
    "category": "infrastructure",
    "description": "Mock DNS server environment for domain name system administration",
    "is_sandbox": True,
    "default_enabled": False,
    "components": [
        {
            "id": "dns_dashboard",
            "type": "dashboard",
            "title": "DNS Dashboard",
            "description": "Overview of DNS server status and query statistics",
            "layout": {
                "x": 0,
                "y": 0,
                "w": 12,
                "h": 6
            },
            "props": {
                "module_id": "dns_management",
                "show_stats": True,
                "show_server_status": True,
                "show_query_rate": True,
                "show_zone_health": True
            }
        },
        {
            "id": "dns_zones",
            "type": "data_table",
            "title": "DNS Zones",
            "description": "Manage DNS zones and domain configurations",
            "layout": {
                "x": 0,
                "y": 6,
                "w": 8,
                "h": 8
            },
            "props": {
                "module_id": "dns_management",
                "data_source": "dns_zones",
                "show_search": True,
                "show_filters": True,
                "actions": ["create", "edit", "delete", "transfer", "reload"]
            }
        },
        {
            "id": "dns_records",
            "type": "data_table",
            "title": "DNS Records",
            "description": "Manage DNS resource records",
            "layout": {
                "x": 8,
                "y": 6,
                "w": 4,
                "h": 8
            },
            "props": {
                "module_id": "dns_management",
                "data_source": "dns_records",
                "show_search": True,
                "show_type_filter": True,
                "actions": ["create", "edit", "delete", "validate"]
            }
        },
        {
            "id": "dns_queries",
            "type": "monitoring_panel",
            "title": "Query Monitor",
            "description": "Monitor DNS queries and resolution performance",
            "layout": {
                "x": 0,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "dns_management",
                "data_source": "dns_queries",
                "show_real_time": True,
                "show_charts": True,
                "actions": ["analyze", "block_domain", "cache_clear"]
            }
        },
        {
            "id": "dns_forwarders",
            "type": "configuration_panel",
            "title": "DNS Forwarders",
            "description": "Configure DNS forwarding and caching",
            "layout": {
                "x": 6,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "dns_management",
                "data_source": "dns_forwarders",
                "show_status": True,
                "show_performance": True,
                "actions": ["add_forwarder", "remove_forwarder", "test_connectivity"]
            }
        }
    ]
}