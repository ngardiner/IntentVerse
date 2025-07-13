"""
Active Directory tool implementation.
Mock Active Directory environment for sandbox testing.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import random
import hashlib
import uuid

# Import the base template from the parent directory
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from base_module_template import SandboxModule
from mock_data_generator import MockDataGenerator

logger = logging.getLogger(__name__)


class ActiveDirectoryTool(SandboxModule):
    """
    Active Directory module implementation for sandbox environment.
    Provides mock AD functionality for learning and testing.
    """
    
    def __init__(self):
        super().__init__(
            module_id="active_directory",
            category="identity",
            display_name="Active Directory",
            description="Mock Active Directory environment for user and group management"
        )
        self.mock_generator = MockDataGenerator()
        self.domain_name = "sandbox.local"
        self.domain_controller = "DC01.sandbox.local"
        self.initialize_mock_data()
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the UI schema for this module."""
        from .schema import UI_SCHEMA
        return UI_SCHEMA
    
    def initialize_mock_data(self) -> Dict[str, Any]:
        """Initialize mock Active Directory data."""
        mock_data = {
            "initialized_at": datetime.utcnow().isoformat(),
            "module_id": self.module_id,
            "data_version": "1.0.0",
            "domain_info": {
                "domain_name": self.domain_name,
                "domain_controller": self.domain_controller,
                "forest_level": "2019",
                "domain_level": "2019",
                "created_date": "2020-01-15T10:00:00Z",
                "is_sandbox": True
            }
        }
        
        # Generate users with AD-specific attributes
        users = self.mock_generator.generate_users(50)
        for user in users:
            user.update({
                "distinguished_name": f"CN={user['display_name']},OU=Users,DC=sandbox,DC=local",
                "sam_account_name": user["username"],
                "user_principal_name": f"{user['username']}@{self.domain_name}",
                "account_expires": None,
                "password_last_set": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
                "last_logon": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                "logon_count": random.randint(10, 500),
                "bad_password_count": random.randint(0, 3),
                "account_locked": random.choice([False, False, False, True]),  # Mostly unlocked
                "enabled": user["status"] == "Active",
                "member_of": random.sample([
                    "CN=Domain Users,CN=Users,DC=sandbox,DC=local",
                    "CN=IT Staff,OU=Groups,DC=sandbox,DC=local",
                    "CN=Managers,OU=Groups,DC=sandbox,DC=local",
                    "CN=Developers,OU=Groups,DC=sandbox,DC=local"
                ], random.randint(1, 3))
            })
        
        mock_data["users"] = users
        
        # Generate groups
        groups = [
            {
                "id": "group_001",
                "name": "Domain Admins",
                "distinguished_name": "CN=Domain Admins,CN=Users,DC=sandbox,DC=local",
                "description": "Designated administrators of the domain",
                "group_type": "Security",
                "group_scope": "Global",
                "member_count": 3,
                "created_date": "2020-01-15T10:00:00Z",
                "is_sandbox": True
            },
            {
                "id": "group_002", 
                "name": "Domain Users",
                "distinguished_name": "CN=Domain Users,CN=Users,DC=sandbox,DC=local",
                "description": "All domain users",
                "group_type": "Security",
                "group_scope": "Global",
                "member_count": len(users),
                "created_date": "2020-01-15T10:00:00Z",
                "is_sandbox": True
            },
            {
                "id": "group_003",
                "name": "IT Staff",
                "distinguished_name": "CN=IT Staff,OU=Groups,DC=sandbox,DC=local",
                "description": "Information Technology staff members",
                "group_type": "Security",
                "group_scope": "Global",
                "member_count": 12,
                "created_date": "2020-02-01T09:00:00Z",
                "is_sandbox": True
            },
            {
                "id": "group_004",
                "name": "Developers",
                "distinguished_name": "CN=Developers,OU=Groups,DC=sandbox,DC=local",
                "description": "Software development team",
                "group_type": "Security",
                "group_scope": "Global",
                "member_count": 8,
                "created_date": "2020-03-15T14:30:00Z",
                "is_sandbox": True
            }
        ]
        
        mock_data["groups"] = groups
        
        # Generate Organizational Units
        organizational_units = [
            {
                "id": "ou_001",
                "name": "Users",
                "distinguished_name": "OU=Users,DC=sandbox,DC=local",
                "description": "Default container for user accounts",
                "parent_dn": "DC=sandbox,DC=local",
                "created_date": "2020-01-15T10:00:00Z",
                "child_objects": 50,
                "is_sandbox": True
            },
            {
                "id": "ou_002",
                "name": "Groups", 
                "distinguished_name": "OU=Groups,DC=sandbox,DC=local",
                "description": "Container for security and distribution groups",
                "parent_dn": "DC=sandbox,DC=local",
                "created_date": "2020-01-15T10:00:00Z",
                "child_objects": 15,
                "is_sandbox": True
            },
            {
                "id": "ou_003",
                "name": "Computers",
                "distinguished_name": "OU=Computers,DC=sandbox,DC=local", 
                "description": "Container for computer accounts",
                "parent_dn": "DC=sandbox,DC=local",
                "created_date": "2020-01-15T10:00:00Z",
                "child_objects": 25,
                "is_sandbox": True
            },
            {
                "id": "ou_004",
                "name": "Servers",
                "distinguished_name": "OU=Servers,OU=Computers,DC=sandbox,DC=local",
                "description": "Server computer accounts",
                "parent_dn": "OU=Computers,DC=sandbox,DC=local",
                "created_date": "2020-01-20T11:00:00Z",
                "child_objects": 8,
                "is_sandbox": True
            }
        ]
        
        mock_data["organizational_units"] = organizational_units
        
        # Generate Group Policy Objects
        group_policies = [
            {
                "id": "gpo_001",
                "name": "Default Domain Policy",
                "distinguished_name": "CN={31B2F340-016D-11D2-945F-00C04FB984F9},CN=Policies,CN=System,DC=sandbox,DC=local",
                "description": "Default domain security and user rights policy",
                "status": "Enabled",
                "created_date": "2020-01-15T10:00:00Z",
                "modified_date": "2023-06-15T14:30:00Z",
                "linked_ous": ["DC=sandbox,DC=local"],
                "settings_count": 25,
                "is_sandbox": True
            },
            {
                "id": "gpo_002",
                "name": "Password Policy",
                "distinguished_name": "CN={A8B2C3D4-E5F6-7890-ABCD-EF1234567890},CN=Policies,CN=System,DC=sandbox,DC=local",
                "description": "Enhanced password complexity requirements",
                "status": "Enabled",
                "created_date": "2020-02-01T09:00:00Z",
                "modified_date": "2023-08-10T16:45:00Z",
                "linked_ous": ["OU=Users,DC=sandbox,DC=local"],
                "settings_count": 8,
                "is_sandbox": True
            },
            {
                "id": "gpo_003",
                "name": "IT Security Policy",
                "distinguished_name": "CN={B9C3D4E5-F6G7-8901-BCDE-F23456789012},CN=Policies,CN=System,DC=sandbox,DC=local",
                "description": "Security settings for IT staff",
                "status": "Enabled",
                "created_date": "2020-03-15T14:30:00Z",
                "modified_date": "2023-09-05T10:15:00Z",
                "linked_ous": ["OU=Groups,DC=sandbox,DC=local"],
                "settings_count": 15,
                "is_sandbox": True
            }
        ]
        
        mock_data["group_policies"] = group_policies
        
        self.mock_data = mock_data
        return mock_data
    
    def get_tools(self) -> Dict[str, Any]:
        """Return available tools for Active Directory management."""
        return {
            "list_users": {
                "name": "list_users",
                "description": "List all domain users with filtering options",
                "method": self.list_users,
                "parameters": {
                    "filter": {"type": "string", "description": "Filter users by name, department, or status"},
                    "ou": {"type": "string", "description": "Filter by Organizational Unit"},
                    "enabled_only": {"type": "boolean", "description": "Show only enabled accounts"}
                },
                "is_sandbox": True
            },
            "create_user": {
                "name": "create_user",
                "description": "Create a new domain user account",
                "method": self.create_user,
                "parameters": {
                    "username": {"type": "string", "required": True},
                    "first_name": {"type": "string", "required": True},
                    "last_name": {"type": "string", "required": True},
                    "email": {"type": "string"},
                    "department": {"type": "string"},
                    "ou": {"type": "string", "description": "Organizational Unit DN"}
                },
                "is_sandbox": True
            },
            "modify_user": {
                "name": "modify_user",
                "description": "Modify user account properties",
                "method": self.modify_user,
                "parameters": {
                    "username": {"type": "string", "required": True},
                    "properties": {"type": "object", "description": "Properties to update"}
                },
                "is_sandbox": True
            },
            "delete_user": {
                "name": "delete_user",
                "description": "Delete a user account",
                "method": self.delete_user,
                "parameters": {
                    "username": {"type": "string", "required": True},
                    "confirm": {"type": "boolean", "required": True}
                },
                "is_sandbox": True
            },
            "reset_password": {
                "name": "reset_password",
                "description": "Reset user password",
                "method": self.reset_password,
                "parameters": {
                    "username": {"type": "string", "required": True},
                    "new_password": {"type": "string", "required": True},
                    "force_change": {"type": "boolean", "description": "Force password change at next logon"}
                },
                "is_sandbox": True
            },
            "authenticate_user": {
                "name": "authenticate_user",
                "description": "Simulate user authentication",
                "method": self.authenticate_user,
                "parameters": {
                    "username": {"type": "string", "required": True},
                    "password": {"type": "string", "required": True}
                },
                "is_sandbox": True
            },
            "list_groups": {
                "name": "list_groups",
                "description": "List all domain groups",
                "method": self.list_groups,
                "parameters": {
                    "filter": {"type": "string", "description": "Filter groups by name or type"},
                    "group_type": {"type": "string", "enum": ["Security", "Distribution"]}
                },
                "is_sandbox": True
            },
            "manage_groups": {
                "name": "manage_groups",
                "description": "Add or remove users from groups",
                "method": self.manage_groups,
                "parameters": {
                    "group_name": {"type": "string", "required": True},
                    "action": {"type": "string", "enum": ["add", "remove"], "required": True},
                    "username": {"type": "string", "required": True}
                },
                "is_sandbox": True
            },
            "get_domain_info": {
                "name": "get_domain_info",
                "description": "Get domain controller and forest information",
                "method": self.get_domain_info,
                "parameters": {},
                "is_sandbox": True
            },
            "search_users": {
                "name": "search_users",
                "description": "Advanced user search with LDAP-style filters",
                "method": self.search_users,
                "parameters": {
                    "ldap_filter": {"type": "string", "description": "LDAP search filter"},
                    "attributes": {"type": "array", "description": "Attributes to return"}
                },
                "is_sandbox": True
            }
        }
    
    def list_users(self, **kwargs) -> Dict[str, Any]:
        """List domain users with filtering options."""
        try:
            users = self.mock_data.get("users", [])
            filter_text = kwargs.get("filter", "").lower()
            ou_filter = kwargs.get("ou", "")
            enabled_only = kwargs.get("enabled_only", False)
            
            # Apply filters
            filtered_users = users
            
            if filter_text:
                filtered_users = [
                    user for user in filtered_users
                    if (filter_text in user["display_name"].lower() or
                        filter_text in user["department"].lower() or
                        filter_text in user["username"].lower())
                ]
            
            if ou_filter:
                filtered_users = [
                    user for user in filtered_users
                    if ou_filter.lower() in user["distinguished_name"].lower()
                ]
            
            if enabled_only:
                filtered_users = [
                    user for user in filtered_users
                    if user.get("enabled", True)
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
                        "ou": ou_filter,
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
    
    def create_user(self, **kwargs) -> Dict[str, Any]:
        """Create a new domain user account."""
        try:
            username = kwargs.get("username")
            first_name = kwargs.get("first_name")
            last_name = kwargs.get("last_name")
            email = kwargs.get("email", f"{username}@{self.domain_name}")
            department = kwargs.get("department", "Users")
            ou = kwargs.get("ou", "OU=Users,DC=sandbox,DC=local")
            
            if not all([username, first_name, last_name]):
                raise ValueError("Username, first_name, and last_name are required")
            
            # Check if user already exists
            existing_users = self.mock_data.get("users", [])
            if any(user["username"] == username for user in existing_users):
                raise ValueError(f"User {username} already exists")
            
            # Create new user
            new_user = {
                "id": f"user_{len(existing_users) + 1:03d}",
                "username": username,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "display_name": f"{first_name} {last_name}",
                "department": department,
                "job_title": f"Employee - {department}",
                "employee_id": f"EMP{len(existing_users) + 1000:04d}",
                "phone": f"+1-555-{random.randint(100, 999):03d}-{random.randint(1000, 9999):04d}",
                "office_location": f"Building {random.choice(['A', 'B', 'C'])}, Floor {random.randint(1, 10)}",
                "status": "Active",
                "created_date": datetime.utcnow().isoformat(),
                "last_login": None,
                "groups": ["Domain Users"],
                "distinguished_name": f"CN={first_name} {last_name},{ou}",
                "sam_account_name": username,
                "user_principal_name": f"{username}@{self.domain_name}",
                "account_expires": None,
                "password_last_set": datetime.utcnow().isoformat(),
                "last_logon": None,
                "logon_count": 0,
                "bad_password_count": 0,
                "account_locked": False,
                "enabled": True,
                "member_of": [f"CN=Domain Users,CN=Users,DC=sandbox,DC=local"],
                "is_sandbox": True
            }
            
            # Add to mock data
            self.mock_data["users"].append(new_user)
            
            return {
                "tool": "create_user",
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "message": f"User {username} created successfully",
                    "user": new_user
                },
                "is_sandbox": True
            }
            
        except Exception as e:
            logger.error(f"Error in create_user: {e}")
            return {
                "tool": "create_user",
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "is_sandbox": True
            }
    
    def authenticate_user(self, **kwargs) -> Dict[str, Any]:
        """Simulate user authentication."""
        try:
            username = kwargs.get("username")
            password = kwargs.get("password")
            
            if not username or not password:
                raise ValueError("Username and password are required")
            
            # Find user
            users = self.mock_data.get("users", [])
            user = next((u for u in users if u["username"] == username), None)
            
            if not user:
                return {
                    "tool": "authenticate_user",
                    "status": "failed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "authenticated": False,
                        "reason": "User not found"
                    },
                    "is_sandbox": True
                }
            
            # Check if account is enabled
            if not user.get("enabled", True):
                return {
                    "tool": "authenticate_user", 
                    "status": "failed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "authenticated": False,
                        "reason": "Account disabled"
                    },
                    "is_sandbox": True
                }
            
            # Check if account is locked
            if user.get("account_locked", False):
                return {
                    "tool": "authenticate_user",
                    "status": "failed", 
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "authenticated": False,
                        "reason": "Account locked"
                    },
                    "is_sandbox": True
                }
            
            # Simulate authentication (always succeeds for demo purposes)
            # In real AD, this would verify against the password hash
            auth_success = len(password) >= 8  # Simple validation for demo
            
            if auth_success:
                # Update last logon
                user["last_logon"] = datetime.utcnow().isoformat()
                user["logon_count"] = user.get("logon_count", 0) + 1
                user["bad_password_count"] = 0
                
                return {
                    "tool": "authenticate_user",
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "authenticated": True,
                        "user_info": {
                            "username": user["username"],
                            "display_name": user["display_name"],
                            "groups": user.get("member_of", []),
                            "last_logon": user["last_logon"]
                        }
                    },
                    "is_sandbox": True
                }
            else:
                # Update bad password count
                user["bad_password_count"] = user.get("bad_password_count", 0) + 1
                if user["bad_password_count"] >= 3:
                    user["account_locked"] = True
                
                return {
                    "tool": "authenticate_user",
                    "status": "failed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "authenticated": False,
                        "reason": "Invalid password",
                        "bad_password_count": user["bad_password_count"]
                    },
                    "is_sandbox": True
                }
                
        except Exception as e:
            logger.error(f"Error in authenticate_user: {e}")
            return {
                "tool": "authenticate_user",
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "is_sandbox": True
            }
    
    def get_domain_info(self, **kwargs) -> Dict[str, Any]:
        """Get domain controller and forest information."""
        try:
            domain_info = self.mock_data.get("domain_info", {})
            users_count = len(self.mock_data.get("users", []))
            groups_count = len(self.mock_data.get("groups", []))
            
            return {
                "tool": "get_domain_info",
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "domain_info": domain_info,
                    "statistics": {
                        "total_users": users_count,
                        "total_groups": groups_count,
                        "enabled_users": len([u for u in self.mock_data.get("users", []) if u.get("enabled", True)]),
                        "locked_accounts": len([u for u in self.mock_data.get("users", []) if u.get("account_locked", False)])
                    }
                },
                "is_sandbox": True
            }
            
        except Exception as e:
            logger.error(f"Error in get_domain_info: {e}")
            return {
                "tool": "get_domain_info",
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "is_sandbox": True
            }
    
    # Additional methods for other tools would be implemented here
    def modify_user(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - modify user account properties."""
        return {
            "tool": "modify_user",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock modify user operation completed"},
            "is_sandbox": True
        }
    
    def delete_user(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - delete user account."""
        return {
            "tool": "delete_user",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock delete user operation completed"},
            "is_sandbox": True
        }
    
    def reset_password(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - reset user password."""
        return {
            "tool": "reset_password",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock password reset operation completed"},
            "is_sandbox": True
        }
    
    def list_groups(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - list domain groups."""
        groups = self.mock_data.get("groups", [])
        return {
            "tool": "list_groups",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"groups": groups, "total_count": len(groups)},
            "is_sandbox": True
        }
    
    def manage_groups(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - manage group membership."""
        return {
            "tool": "manage_groups",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock group management operation completed"},
            "is_sandbox": True
        }
    
    def search_users(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - advanced user search."""
        return {
            "tool": "search_users",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock user search operation completed"},
            "is_sandbox": True
        }