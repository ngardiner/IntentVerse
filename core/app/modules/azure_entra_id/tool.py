"""
Azure Entra ID tool implementation.
Mock Azure Entra ID environment for sandbox testing.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import random
import uuid

# Import the base template from the parent directory
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from base_module_template import SandboxModule
from mock_data_generator import MockDataGenerator

logger = logging.getLogger(__name__)


class AzureEntraIdTool(SandboxModule):
    """
    Azure Entra ID module implementation for sandbox environment.
    Provides mock Azure AD functionality for learning and testing.
    """
    
    def __init__(self):
        super().__init__(
            module_id="azure_entra_id",
            category="identity",
            display_name="Azure Entra ID",
            description="Mock Azure Entra ID environment for cloud identity and access management"
        )
        self.mock_generator = MockDataGenerator()
        self.tenant_id = str(uuid.uuid4())
        self.tenant_domain = "sandbox.onmicrosoft.com"
        self.initialize_mock_data()
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the UI schema for this module."""
        from .schema import UI_SCHEMA
        return UI_SCHEMA
    
    def initialize_mock_data(self) -> Dict[str, Any]:
        """Initialize mock Azure Entra ID data."""
        mock_data = {
            "initialized_at": datetime.utcnow().isoformat(),
            "module_id": self.module_id,
            "data_version": "1.0.0",
            "tenant_info": {
                "tenant_id": self.tenant_id,
                "tenant_domain": self.tenant_domain,
                "display_name": "Sandbox Organization",
                "country": "US",
                "created_date": "2020-01-15T10:00:00Z",
                "license_type": "Premium P2",
                "is_sandbox": True
            }
        }
        
        # Generate cloud users with Azure AD-specific attributes
        users = self.mock_generator.generate_users(40)
        for user in users:
            user.update({
                "object_id": str(uuid.uuid4()),
                "user_principal_name": f"{user['username']}@{self.tenant_domain}",
                "mail": user["email"],
                "user_type": random.choice(["Member", "Member", "Member", "Guest"]),
                "account_enabled": user["status"] == "Active",
                "creation_type": random.choice(["Invitation", "LocalAccount", "NameCoexistence"]),
                "sign_in_sessions_valid_from": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                "last_sign_in": (datetime.now() - timedelta(hours=random.randint(1, 168))).isoformat() if random.choice([True, False]) else None,
                "mfa_enabled": random.choice([True, False]),
                "risk_level": random.choice(["None", "Low", "Medium", "High"]),
                "assigned_licenses": random.sample([
                    "Microsoft 365 E5",
                    "Azure AD Premium P2", 
                    "Office 365 E3",
                    "Enterprise Mobility + Security E5"
                ], random.randint(1, 2)),
                "directory_roles": random.sample([
                    "User",
                    "Global Reader",
                    "Helpdesk Administrator",
                    "User Administrator"
                ], 1) if random.choice([True, False]) else ["User"],
                "is_sandbox": True
            })
        
        mock_data["users"] = users
        
        # Generate Azure AD groups and roles
        groups_and_roles = [
            {
                "id": str(uuid.uuid4()),
                "display_name": "Global Administrators",
                "description": "Can manage all aspects of Azure AD and Microsoft services",
                "type": "Directory Role",
                "mail_enabled": False,
                "security_enabled": True,
                "member_count": 3,
                "created_date": "2020-01-15T10:00:00Z",
                "is_assignable_to_role": True,
                "is_sandbox": True
            },
            {
                "id": str(uuid.uuid4()),
                "display_name": "IT Administrators",
                "description": "IT department security group",
                "type": "Security Group",
                "mail_enabled": False,
                "security_enabled": True,
                "member_count": 8,
                "created_date": "2020-02-01T09:00:00Z",
                "group_types": ["Unified"],
                "is_sandbox": True
            },
            {
                "id": str(uuid.uuid4()),
                "display_name": "All Company",
                "description": "All company employees",
                "type": "Microsoft 365 Group",
                "mail_enabled": True,
                "security_enabled": False,
                "member_count": len(users),
                "created_date": "2020-01-15T10:00:00Z",
                "group_types": ["Unified"],
                "is_sandbox": True
            },
            {
                "id": str(uuid.uuid4()),
                "display_name": "Developers",
                "description": "Software development team",
                "type": "Security Group",
                "mail_enabled": False,
                "security_enabled": True,
                "member_count": 12,
                "created_date": "2020-03-15T14:30:00Z",
                "is_sandbox": True
            }
        ]
        
        mock_data["groups_and_roles"] = groups_and_roles
        
        # Generate application registrations
        applications = [
            {
                "id": str(uuid.uuid4()),
                "app_id": str(uuid.uuid4()),
                "display_name": "Sandbox Web App",
                "description": "Internal web application for sandbox testing",
                "created_date": "2020-06-15T11:00:00Z",
                "app_type": "Web Application",
                "sign_in_audience": "AzureADMyOrg",
                "redirect_uris": ["https://sandbox-webapp.local/auth/callback"],
                "api_permissions": [
                    "User.Read",
                    "Group.Read.All",
                    "Directory.Read.All"
                ],
                "certificates_count": 1,
                "secrets_count": 2,
                "owners": ["alice.smith@sandbox.onmicrosoft.com"],
                "is_sandbox": True
            },
            {
                "id": str(uuid.uuid4()),
                "app_id": str(uuid.uuid4()),
                "display_name": "Mobile App",
                "description": "Company mobile application",
                "created_date": "2021-03-20T14:30:00Z",
                "app_type": "Public Client",
                "sign_in_audience": "AzureADMyOrg",
                "redirect_uris": ["msauth://com.sandbox.mobile"],
                "api_permissions": [
                    "User.Read",
                    "offline_access"
                ],
                "certificates_count": 0,
                "secrets_count": 0,
                "owners": ["bob.jones@sandbox.onmicrosoft.com"],
                "is_sandbox": True
            },
            {
                "id": str(uuid.uuid4()),
                "app_id": str(uuid.uuid4()),
                "display_name": "API Service",
                "description": "Backend API service",
                "created_date": "2021-08-10T09:15:00Z",
                "app_type": "Web API",
                "sign_in_audience": "AzureADMyOrg",
                "api_permissions": [
                    "Application.ReadWrite.All"
                ],
                "certificates_count": 2,
                "secrets_count": 1,
                "owners": ["admin@sandbox.onmicrosoft.com"],
                "is_sandbox": True
            }
        ]
        
        mock_data["applications"] = applications
        
        # Generate conditional access policies
        conditional_access_policies = [
            {
                "id": str(uuid.uuid4()),
                "display_name": "Require MFA for Admins",
                "description": "Require multi-factor authentication for all administrator roles",
                "state": "Enabled",
                "created_date": "2020-04-01T10:00:00Z",
                "modified_date": "2023-08-15T14:30:00Z",
                "conditions": {
                    "users": ["Global Administrators", "Privileged Role Administrator"],
                    "applications": ["All cloud apps"],
                    "locations": ["Any location"],
                    "device_platforms": ["Any device"]
                },
                "grant_controls": ["Require MFA"],
                "session_controls": [],
                "is_sandbox": True
            },
            {
                "id": str(uuid.uuid4()),
                "display_name": "Block Legacy Authentication",
                "description": "Block legacy authentication protocols",
                "state": "Enabled",
                "created_date": "2020-05-15T11:30:00Z",
                "modified_date": "2023-06-20T16:45:00Z",
                "conditions": {
                    "users": ["All users"],
                    "applications": ["All cloud apps"],
                    "client_apps": ["Exchange ActiveSync clients", "Other clients"]
                },
                "grant_controls": ["Block access"],
                "session_controls": [],
                "is_sandbox": True
            },
            {
                "id": str(uuid.uuid4()),
                "display_name": "Require Compliant Device",
                "description": "Require device compliance for high-risk applications",
                "state": "Report-only",
                "created_date": "2021-02-10T13:00:00Z",
                "modified_date": "2023-09-05T10:15:00Z",
                "conditions": {
                    "users": ["All users"],
                    "applications": ["Office 365", "Azure Management"],
                    "locations": ["Any location"]
                },
                "grant_controls": ["Require device to be marked as compliant"],
                "session_controls": [],
                "is_sandbox": True
            }
        ]
        
        mock_data["conditional_access_policies"] = conditional_access_policies
        
        # Generate MFA settings
        mfa_settings = {
            "global_settings": {
                "default_method": "Microsoft Authenticator",
                "enabled_methods": [
                    "Microsoft Authenticator",
                    "SMS",
                    "Voice call",
                    "OATH hardware tokens"
                ],
                "remember_mfa_days": 14,
                "account_lockout_threshold": 10,
                "account_lockout_duration": 90
            },
            "user_settings": [
                {
                    "user_id": users[0]["object_id"],
                    "username": users[0]["username"],
                    "mfa_status": "Enabled",
                    "default_method": "Microsoft Authenticator",
                    "registered_methods": ["Microsoft Authenticator", "SMS"],
                    "last_activity": (datetime.now() - timedelta(days=2)).isoformat()
                },
                {
                    "user_id": users[1]["object_id"],
                    "username": users[1]["username"],
                    "mfa_status": "Enforced",
                    "default_method": "SMS",
                    "registered_methods": ["SMS", "Voice call"],
                    "last_activity": (datetime.now() - timedelta(hours=6)).isoformat()
                }
            ],
            "is_sandbox": True
        }
        
        mock_data["mfa_settings"] = mfa_settings
        
        self.mock_data = mock_data
        return mock_data
    
    def get_tools(self) -> Dict[str, Any]:
        """Return available tools for Azure Entra ID management."""
        return {
            "list_users": {
                "name": "list_users",
                "description": "List all users in the tenant with filtering options",
                "method": self.list_users,
                "parameters": {
                    "filter": {"type": "string", "description": "Filter users by name, email, or department"},
                    "user_type": {"type": "string", "enum": ["Member", "Guest", "All"]},
                    "enabled_only": {"type": "boolean", "description": "Show only enabled accounts"}
                },
                "is_sandbox": True
            },
            "create_user": {
                "name": "create_user",
                "description": "Create a new user in Azure Entra ID",
                "method": self.create_user,
                "parameters": {
                    "display_name": {"type": "string", "required": True},
                    "user_principal_name": {"type": "string", "required": True},
                    "mail_nickname": {"type": "string", "required": True},
                    "password": {"type": "string", "required": True},
                    "force_change_password": {"type": "boolean", "default": True}
                },
                "is_sandbox": True
            },
            "invite_guest_user": {
                "name": "invite_guest_user",
                "description": "Invite an external user as a guest",
                "method": self.invite_guest_user,
                "parameters": {
                    "email": {"type": "string", "required": True},
                    "display_name": {"type": "string"},
                    "message": {"type": "string", "description": "Custom invitation message"}
                },
                "is_sandbox": True
            },
            "manage_user_licenses": {
                "name": "manage_user_licenses",
                "description": "Assign or remove licenses from users",
                "method": self.manage_user_licenses,
                "parameters": {
                    "user_id": {"type": "string", "required": True},
                    "action": {"type": "string", "enum": ["assign", "remove"], "required": True},
                    "license_sku": {"type": "string", "required": True}
                },
                "is_sandbox": True
            },
            "configure_mfa": {
                "name": "configure_mfa",
                "description": "Configure multi-factor authentication settings",
                "method": self.configure_mfa,
                "parameters": {
                    "user_id": {"type": "string", "required": True},
                    "mfa_status": {"type": "string", "enum": ["Disabled", "Enabled", "Enforced"], "required": True},
                    "default_method": {"type": "string", "enum": ["Microsoft Authenticator", "SMS", "Voice call"]}
                },
                "is_sandbox": True
            },
            "create_conditional_access_policy": {
                "name": "create_conditional_access_policy",
                "description": "Create a new conditional access policy",
                "method": self.create_conditional_access_policy,
                "parameters": {
                    "display_name": {"type": "string", "required": True},
                    "description": {"type": "string"},
                    "conditions": {"type": "object", "required": True},
                    "grant_controls": {"type": "array", "required": True}
                },
                "is_sandbox": True
            },
            "register_application": {
                "name": "register_application",
                "description": "Register a new application in Azure Entra ID",
                "method": self.register_application,
                "parameters": {
                    "display_name": {"type": "string", "required": True},
                    "app_type": {"type": "string", "enum": ["Web Application", "Public Client", "Web API"], "required": True},
                    "redirect_uris": {"type": "array"},
                    "api_permissions": {"type": "array"}
                },
                "is_sandbox": True
            },
            "get_tenant_info": {
                "name": "get_tenant_info",
                "description": "Get tenant information and statistics",
                "method": self.get_tenant_info,
                "parameters": {},
                "is_sandbox": True
            },
            "get_sign_in_logs": {
                "name": "get_sign_in_logs",
                "description": "Retrieve sign-in logs and analytics",
                "method": self.get_sign_in_logs,
                "parameters": {
                    "user_id": {"type": "string", "description": "Filter by specific user"},
                    "application": {"type": "string", "description": "Filter by application"},
                    "days": {"type": "integer", "default": 7, "description": "Number of days to retrieve"}
                },
                "is_sandbox": True
            },
            "manage_directory_roles": {
                "name": "manage_directory_roles",
                "description": "Assign or remove directory roles",
                "method": self.manage_directory_roles,
                "parameters": {
                    "user_id": {"type": "string", "required": True},
                    "role_name": {"type": "string", "required": True},
                    "action": {"type": "string", "enum": ["assign", "remove"], "required": True}
                },
                "is_sandbox": True
            }
        }
    
    def list_users(self, **kwargs) -> Dict[str, Any]:
        """List users in the tenant with filtering options."""
        try:
            users = self.mock_data.get("users", [])
            filter_text = kwargs.get("filter", "").lower()
            user_type = kwargs.get("user_type", "All")
            enabled_only = kwargs.get("enabled_only", False)
            
            # Apply filters
            filtered_users = users
            
            if filter_text:
                filtered_users = [
                    user for user in filtered_users
                    if (filter_text in user["display_name"].lower() or
                        filter_text in user["user_principal_name"].lower() or
                        filter_text in user["department"].lower())
                ]
            
            if user_type != "All":
                filtered_users = [
                    user for user in filtered_users
                    if user.get("user_type", "Member") == user_type
                ]
            
            if enabled_only:
                filtered_users = [
                    user for user in filtered_users
                    if user.get("account_enabled", True)
                ]
            
            return {
                "tool": "list_users",
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "users": filtered_users,
                    "total_count": len(filtered_users),
                    "filters_applied": {
                        "filter": filter_text,
                        "user_type": user_type,
                        "enabled_only": enabled_only
                    }
                },
                "is_sandbox": True
            }
            
        except Exception as e:
            logger.error(f"Error in list_users: {e}")
            return {
                "tool": "list_users",
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "is_sandbox": True
            }
    
    def get_tenant_info(self, **kwargs) -> Dict[str, Any]:
        """Get tenant information and statistics."""
        try:
            tenant_info = self.mock_data.get("tenant_info", {})
            users = self.mock_data.get("users", [])
            applications = self.mock_data.get("applications", [])
            policies = self.mock_data.get("conditional_access_policies", [])
            
            statistics = {
                "total_users": len(users),
                "member_users": len([u for u in users if u.get("user_type") == "Member"]),
                "guest_users": len([u for u in users if u.get("user_type") == "Guest"]),
                "enabled_users": len([u for u in users if u.get("account_enabled", True)]),
                "mfa_enabled_users": len([u for u in users if u.get("mfa_enabled", False)]),
                "total_applications": len(applications),
                "conditional_access_policies": len(policies),
                "enabled_policies": len([p for p in policies if p.get("state") == "Enabled"])
            }
            
            return {
                "tool": "get_tenant_info",
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "tenant_info": tenant_info,
                    "statistics": statistics
                },
                "is_sandbox": True
            }
            
        except Exception as e:
            logger.error(f"Error in get_tenant_info: {e}")
            return {
                "tool": "get_tenant_info",
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "is_sandbox": True
            }
    
    # Mock implementations for other tools
    def create_user(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - create user."""
        return {
            "tool": "create_user",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock user creation completed", "user_id": str(uuid.uuid4())},
            "is_sandbox": True
        }
    
    def invite_guest_user(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - invite guest user."""
        return {
            "tool": "invite_guest_user",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock guest invitation sent", "invitation_id": str(uuid.uuid4())},
            "is_sandbox": True
        }
    
    def manage_user_licenses(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - manage user licenses."""
        return {
            "tool": "manage_user_licenses",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock license management completed"},
            "is_sandbox": True
        }
    
    def configure_mfa(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - configure MFA."""
        return {
            "tool": "configure_mfa",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock MFA configuration completed"},
            "is_sandbox": True
        }
    
    def create_conditional_access_policy(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - create conditional access policy."""
        return {
            "tool": "create_conditional_access_policy",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock conditional access policy created", "policy_id": str(uuid.uuid4())},
            "is_sandbox": True
        }
    
    def register_application(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - register application."""
        return {
            "tool": "register_application",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock application registration completed", "app_id": str(uuid.uuid4())},
            "is_sandbox": True
        }
    
    def get_sign_in_logs(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - get sign-in logs."""
        return {
            "tool": "get_sign_in_logs",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock sign-in logs retrieved", "log_count": random.randint(50, 200)},
            "is_sandbox": True
        }
    
    def manage_directory_roles(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - manage directory roles."""
        return {
            "tool": "manage_directory_roles",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock directory role management completed"},
            "is_sandbox": True
        }