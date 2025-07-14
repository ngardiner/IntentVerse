"""
UI Schema for Load Balancer module.
"""

UI_SCHEMA = {
    "module_id": "load_balancer",
    "display_name": "Load Balancer",
    "category": "infrastructure",
    "description": "Mock load balancer environment for traffic distribution and high availability",
    "is_sandbox": True,
    "default_enabled": False,
    "components": [
        {
            "id": "lb_dashboard",
            "type": "dashboard",
            "title": "Load Balancer Dashboard",
            "description": "Overview of load balancer status and traffic distribution",
            "layout": {
                "x": 0,
                "y": 0,
                "w": 12,
                "h": 6
            },
            "props": {
                "module_id": "load_balancer",
                "show_stats": True,
                "show_health_status": True,
                "show_traffic_distribution": True,
                "show_performance_metrics": True
            }
        },
        {
            "id": "lb_virtual_servers",
            "type": "data_table",
            "title": "Virtual Servers",
            "description": "Manage load balancer virtual servers and listeners",
            "layout": {
                "x": 0,
                "y": 6,
                "w": 8,
                "h": 8
            },
            "props": {
                "module_id": "load_balancer",
                "data_source": "virtual_servers",
                "show_search": True,
                "show_filters": True,
                "actions": ["create", "edit", "delete", "enable", "disable", "configure_ssl"]
            }
        },
        {
            "id": "lb_backend_pools",
            "type": "data_table",
            "title": "Backend Pools",
            "description": "Manage backend server pools and health checks",
            "layout": {
                "x": 8,
                "y": 6,
                "w": 4,
                "h": 8
            },
            "props": {
                "module_id": "load_balancer",
                "data_source": "backend_pools",
                "show_health_status": True,
                "show_member_count": True,
                "actions": ["create", "edit", "add_member", "remove_member", "health_check"]
            }
        },
        {
            "id": "lb_traffic_monitor",
            "type": "monitoring_panel",
            "title": "Traffic Monitor",
            "description": "Real-time traffic monitoring and analytics",
            "layout": {
                "x": 0,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "load_balancer",
                "data_source": "traffic_stats",
                "show_real_time": True,
                "show_charts": True,
                "show_top_clients": True,
                "actions": ["export_stats", "reset_counters"]
            }
        },
        {
            "id": "lb_ssl_certificates",
            "type": "configuration_panel",
            "title": "SSL Certificates",
            "description": "Manage SSL certificates and termination",
            "layout": {
                "x": 6,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "load_balancer",
                "data_source": "ssl_certificates",
                "show_expiry_dates": True,
                "show_cipher_suites": True,
                "actions": ["upload_cert", "renew_cert", "configure_ssl"]
            }
        }
    ]
}