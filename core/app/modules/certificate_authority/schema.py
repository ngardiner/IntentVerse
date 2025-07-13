"""
UI Schema for Certificate Authority module.
"""

UI_SCHEMA = {
    "module_id": "certificate_authority",
    "display_name": "Certificate Authority",
    "category": "identity",
    "description": "Mock PKI Certificate Authority environment for certificate lifecycle management",
    "is_sandbox": True,
    "default_enabled": False,
    "components": [
        {
            "id": "ca_dashboard",
            "type": "dashboard",
            "title": "Certificate Authority Dashboard",
            "description": "Overview of PKI infrastructure and certificate statistics",
            "layout": {
                "x": 0,
                "y": 0,
                "w": 12,
                "h": 6
            },
            "props": {
                "module_id": "certificate_authority",
                "show_stats": True,
                "show_ca_info": True,
                "show_expiring_certs": True,
                "show_recent_activity": True
            }
        },
        {
            "id": "ca_certificates",
            "type": "data_table",
            "title": "Certificate Management",
            "description": "Manage issued certificates and their lifecycle",
            "layout": {
                "x": 0,
                "y": 6,
                "w": 8,
                "h": 8
            },
            "props": {
                "module_id": "certificate_authority",
                "data_source": "certificates",
                "show_search": True,
                "show_filters": True,
                "actions": ["issue", "renew", "revoke", "view_details", "download"]
            }
        },
        {
            "id": "ca_templates",
            "type": "list_view",
            "title": "Certificate Templates",
            "description": "Manage certificate templates and policies",
            "layout": {
                "x": 8,
                "y": 6,
                "w": 4,
                "h": 8
            },
            "props": {
                "module_id": "certificate_authority",
                "data_source": "certificate_templates",
                "show_status": True,
                "actions": ["create", "edit", "duplicate", "disable"]
            }
        },
        {
            "id": "ca_crl",
            "type": "status_panel",
            "title": "Certificate Revocation Lists",
            "description": "Manage CRL publication and OCSP services",
            "layout": {
                "x": 0,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "certificate_authority",
                "data_source": "crl_status",
                "show_publication_points": True,
                "show_ocsp_status": True,
                "actions": ["publish_crl", "configure_ocsp"]
            }
        },
        {
            "id": "ca_requests",
            "type": "data_table",
            "title": "Certificate Requests",
            "description": "Pending and processed certificate requests",
            "layout": {
                "x": 6,
                "y": 14,
                "w": 6,
                "h": 6
            },
            "props": {
                "module_id": "certificate_authority",
                "data_source": "certificate_requests",
                "show_status_filter": True,
                "actions": ["approve", "deny", "view_csr"]
            }
        }
    ]
}