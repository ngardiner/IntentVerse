"""
Sample data for Active Directory module.
Contains realistic but clearly marked sandbox data for testing and demonstration.
"""

SAMPLE_DATA = {
    "module_info": {
        "category": "identity",
        "created_at": "2024-01-15T10:00:00Z",
        "data_version": "1.0.0"
    },
    "domain_scenarios": {
        "basic_setup": {
            "name": "Basic Domain Setup",
            "description": "Standard Active Directory domain with typical organizational structure",
            "user_count": 50,
            "group_count": 8,
            "ou_count": 6
        },
        "security_incident": {
            "name": "Security Incident Response",
            "description": "Scenario with locked accounts and security events for training",
            "locked_accounts": 5,
            "failed_logins": 25,
            "suspicious_activity": True
        },
        "migration_scenario": {
            "name": "Domain Migration",
            "description": "Large organization with complex OU structure for migration testing",
            "user_count": 200,
            "group_count": 25,
            "ou_count": 15
        }
    },
    "sample_users": [
        {
            "username": "alice.smith",
            "display_name": "Alice Smith",
            "email": "alice.smith@sandbox.local",
            "department": "IT",
            "title": "System Administrator",
            "enabled": True,
            "groups": ["Domain Admins", "IT Staff"]
        },
        {
            "username": "bob.jones",
            "display_name": "Bob Jones", 
            "email": "bob.jones@sandbox.local",
            "department": "Engineering",
            "title": "Software Developer",
            "enabled": True,
            "groups": ["Developers", "Domain Users"]
        },
        {
            "username": "charlie.brown",
            "display_name": "Charlie Brown",
            "email": "charlie.brown@sandbox.local",
            "department": "Sales",
            "title": "Sales Manager",
            "enabled": False,
            "groups": ["Managers", "Domain Users"]
        }
    ],
    "sample_groups": [
        {
            "name": "Domain Admins",
            "description": "Designated administrators of the domain",
            "type": "Security",
            "scope": "Global",
            "members": ["alice.smith", "admin"]
        },
        {
            "name": "IT Staff",
            "description": "Information Technology staff members",
            "type": "Security", 
            "scope": "Global",
            "members": ["alice.smith", "bob.jones", "it.admin"]
        },
        {
            "name": "Developers",
            "description": "Software development team",
            "type": "Security",
            "scope": "Global", 
            "members": ["bob.jones", "dev1", "dev2"]
        }
    ],
    "sample_ous": [
        {
            "name": "Corporate",
            "dn": "OU=Corporate,DC=sandbox,DC=local",
            "description": "Corporate users and resources"
        },
        {
            "name": "IT Department",
            "dn": "OU=IT Department,OU=Corporate,DC=sandbox,DC=local",
            "description": "Information Technology department"
        },
        {
            "name": "Engineering",
            "dn": "OU=Engineering,OU=Corporate,DC=sandbox,DC=local",
            "description": "Engineering department"
        }
    ],
    "learning_objectives": [
        "Understand Active Directory user management",
        "Learn group policy implementation",
        "Practice authentication troubleshooting",
        "Explore organizational unit structure",
        "Simulate security incident response"
    ]
}