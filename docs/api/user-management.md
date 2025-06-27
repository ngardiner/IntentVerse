# User Management

IntentVerse provides comprehensive user management capabilities including user accounts, groups, roles, permissions, and audit logging. The system uses Role-Based Access Control (RBAC) for fine-grained permission management.

## Overview

The user management system includes:
- **User Accounts**: Create, update, and manage user accounts
- **Groups**: Organize users into groups for easier management
- **Roles**: Define roles with specific permissions
- **Permissions**: Fine-grained access control
- **Audit Logging**: Track all user actions and changes

## Authentication

User management endpoints require authentication and specific permissions. See [Authentication](authentication.md) for details.

## User Management

### Create User

**POST** `/users/`

Creates a new user account.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `users.create`

**Request Body:**
```json
{
  "username": "john_doe",
  "password": "your_secure_password",
  "email": "john.doe@example.com",
  "full_name": "John Doe",
  "is_admin": false
}
```

**Response:**
```json
{
  "id": 5,
  "username": "john_doe",
  "email": "john.doe@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T12:00:00Z",
  "last_login": null
}
```

### Get All Users

**GET** `/users/`

Returns a list of all users.

**Parameters:**
- `skip` (query, optional): Number of users to skip (default: 0)
- `limit` (query, optional): Maximum number of users to return (default: 100)

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `users.read`

**Response:**
```json
[
  {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "Administrator",
    "is_active": true,
    "is_admin": true,
    "created_at": "2024-01-01T00:00:00Z",
    "last_login": "2024-01-01T12:00:00Z"
  },
  {
    "id": 5,
    "username": "john_doe",
    "email": "john.doe@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "is_admin": false,
    "created_at": "2024-01-01T12:00:00Z",
    "last_login": null
  }
]
```

### Get Current User

**GET** `/users/me`

Returns the currently authenticated user's details with roles and permissions.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "Administrator",
  "is_active": true,
  "is_admin": true,
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T12:00:00Z",
  "roles": ["admin", "user"],
  "permissions": [
    "admin.all",
    "users.read",
    "users.create",
    "users.update",
    "users.delete",
    "groups.read",
    "groups.create",
    "groups.update",
    "groups.delete"
  ]
}
```

### Get User by ID

**GET** `/users/{user_id}`

Returns details for a specific user including roles and permissions.

**Parameters:**
- `user_id` (path, required): The ID of the user

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Permission Requirements:**
- Users can view their own details
- `users.read` permission required to view other users

**Response:**
```json
{
  "id": 5,
  "username": "john_doe",
  "email": "john.doe@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T12:00:00Z",
  "last_login": null,
  "roles": ["user"],
  "permissions": [
    "filesystem.read",
    "database.read",
    "timeline.read"
  ]
}
```

### Update User

**PUT** `/users/{user_id}`

Updates a user's information.

**Parameters:**
- `user_id` (path, required): The ID of the user

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Permission Requirements:**
- Users can update their own details (except admin fields)
- `users.update` permission required to update other users
- `admin.all` permission required to update `is_active` and `is_admin` fields

**Request Body:**
```json
{
  "email": "john.doe.updated@example.com",
  "full_name": "John Doe Updated",
  "password": "your_new_password",
  "is_active": true,
  "is_admin": false
}
```

**Response:**
```json
{
  "id": 5,
  "username": "john_doe",
  "email": "john.doe.updated@example.com",
  "full_name": "John Doe Updated",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T12:00:00Z",
  "last_login": null
}
```

### Delete User

**DELETE** `/users/{user_id}`

Deletes a user account.

**Parameters:**
- `user_id` (path, required): The ID of the user

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `users.delete`

**Response:** `204 No Content`

**Restrictions:**
- Cannot delete the last administrator user
- All user data and associations are removed

## Group Management

### Create Group

**POST** `/groups/`

Creates a new user group.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `groups.create`

**Request Body:**
```json
{
  "name": "developers",
  "description": "Development team members"
}
```

**Response:**
```json
{
  "id": 3,
  "name": "developers",
  "description": "Development team members",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Get All Groups

**GET** `/groups/`

Returns a list of all groups.

**Parameters:**
- `skip` (query, optional): Number of groups to skip (default: 0)
- `limit` (query, optional): Maximum number of groups to return (default: 100)

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `groups.read`

**Response:**
```json
[
  {
    "id": 1,
    "name": "admins",
    "description": "System administrators",
    "created_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": 2,
    "name": "users",
    "description": "Regular users",
    "created_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": 3,
    "name": "developers",
    "description": "Development team members",
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

### Get Group by ID

**GET** `/groups/{group_id}`

Returns details for a specific group including its members.

**Parameters:**
- `group_id` (path, required): The ID of the group

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `groups.read`

**Response:**
```json
{
  "id": 3,
  "name": "developers",
  "description": "Development team members",
  "created_at": "2024-01-01T12:00:00Z",
  "users": ["john_doe", "jane_smith"]
}
```

### Update Group

**PUT** `/groups/{group_id}`

Updates a group's information.

**Parameters:**
- `group_id` (path, required): The ID of the group

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `groups.update`

**Request Body:**
```json
{
  "description": "Updated description for development team"
}
```

**Response:**
```json
{
  "id": 3,
  "name": "developers",
  "description": "Updated description for development team",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Delete Group

**DELETE** `/groups/{group_id}`

Deletes a group.

**Parameters:**
- `group_id` (path, required): The ID of the group

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `groups.delete`

**Response:** `204 No Content`

## User-Group Management

### Add User to Group

**POST** `/users/{user_id}/groups/{group_id}`

Adds a user to a group.

**Parameters:**
- `user_id` (path, required): The ID of the user
- `group_id` (path, required): The ID of the group

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `groups.manage_members`

**Response:** `204 No Content`

### Remove User from Group

**DELETE** `/users/{user_id}/groups/{group_id}`

Removes a user from a group.

**Parameters:**
- `user_id` (path, required): The ID of the user
- `group_id` (path, required): The ID of the group

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `groups.manage_members`

**Response:** `204 No Content`

## Role-Based Access Control (RBAC)

### Get All Roles

**GET** `/roles/`

Returns a list of all roles.

**Parameters:**
- `skip` (query, optional): Number of roles to skip (default: 0)
- `limit` (query, optional): Maximum number of roles to return (default: 100)

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `roles.read`

**Response:**
```json
[
  {
    "id": 1,
    "name": "admin",
    "description": "Full system administrator",
    "is_system_role": true,
    "created_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": 2,
    "name": "user",
    "description": "Regular user with basic permissions",
    "is_system_role": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get Role by ID

**GET** `/roles/{role_id}`

Returns details for a specific role including its permissions.

**Parameters:**
- `role_id` (path, required): The ID of the role

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `roles.read`

**Response:**
```json
{
  "id": 1,
  "name": "admin",
  "description": "Full system administrator",
  "is_system_role": true,
  "created_at": "2024-01-01T00:00:00Z",
  "permissions": [
    "admin.all",
    "users.read",
    "users.create",
    "users.update",
    "users.delete"
  ]
}
```

### Create Role

**POST** `/roles/`

Creates a new role.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `roles.create`

**Request Body:**
```json
{
  "name": "developer",
  "description": "Developer role with development permissions"
}
```

**Response:**
```json
{
  "id": 5,
  "name": "developer",
  "description": "Developer role with development permissions",
  "is_system_role": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Update Role

**PUT** `/roles/{role_id}`

Updates a role's information.

**Parameters:**
- `role_id` (path, required): The ID of the role

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `roles.update`

**Request Body:**
```json
{
  "description": "Updated developer role description"
}
```

**Response:**
```json
{
  "id": 5,
  "name": "developer",
  "description": "Updated developer role description",
  "is_system_role": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Restrictions:**
- Cannot update system roles (`is_system_role: true`)

### Delete Role

**DELETE** `/roles/{role_id}`

Deletes a role.

**Parameters:**
- `role_id` (path, required): The ID of the role

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `roles.delete`

**Response:** `204 No Content`

**Restrictions:**
- Cannot delete system roles

## Permission Management

### Get All Permissions

**GET** `/permissions/`

Returns a list of all permissions.

**Parameters:**
- `skip` (query, optional): Number of permissions to skip (default: 0)
- `limit` (query, optional): Maximum number of permissions to return (default: 100)
- `resource_type` (query, optional): Filter by resource type

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `permissions.read`

**Response:**
```json
[
  {
    "id": 1,
    "name": "users.read",
    "description": "Read user information",
    "resource_type": "users",
    "action": "read",
    "created_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": 2,
    "name": "users.create",
    "description": "Create new users",
    "resource_type": "users",
    "action": "create",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Create Permission

**POST** `/permissions/`

Creates a new permission.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `admin.all`

**Request Body:**
```json
{
  "name": "custom.permission",
  "description": "Custom permission for specific functionality",
  "resource_type": "custom",
  "action": "execute"
}
```

**Response:**
```json
{
  "id": 25,
  "name": "custom.permission",
  "description": "Custom permission for specific functionality",
  "resource_type": "custom",
  "action": "execute",
  "created_at": "2024-01-01T12:00:00Z"
}
```

## Role-Permission Management

### Assign Permission to Role

**POST** `/roles/{role_id}/permissions/{permission_id}`

Assigns a permission to a role.

**Parameters:**
- `role_id` (path, required): The ID of the role
- `permission_id` (path, required): The ID of the permission

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `roles.update`

**Response:** `204 No Content`

### Remove Permission from Role

**DELETE** `/roles/{role_id}/permissions/{permission_id}`

Removes a permission from a role.

**Parameters:**
- `role_id` (path, required): The ID of the role
- `permission_id` (path, required): The ID of the permission

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `roles.update`

**Response:** `204 No Content`

## User-Role Management

### Assign Role to User

**POST** `/users/{user_id}/roles/{role_id}`

Assigns a role to a user.

**Parameters:**
- `user_id` (path, required): The ID of the user
- `role_id` (path, required): The ID of the role

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `users.manage_roles`

**Response:** `204 No Content`

### Remove Role from User

**DELETE** `/users/{user_id}/roles/{role_id}`

Removes a role from a user.

**Parameters:**
- `user_id` (path, required): The ID of the user
- `role_id` (path, required): The ID of the role

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `users.manage_roles`

**Response:** `204 No Content`

## Group-Role Management

### Get Group Roles

**GET** `/groups/{group_id}/roles`

Returns a group with its assigned roles.

**Parameters:**
- `group_id` (path, required): The ID of the group

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `groups.read`

**Response:**
```json
{
  "id": 3,
  "name": "developers",
  "description": "Development team members",
  "created_at": "2024-01-01T12:00:00Z",
  "roles": ["developer", "user"]
}
```

### Assign Role to Group

**POST** `/groups/{group_id}/roles/{role_id}`

Assigns a role to a group.

**Parameters:**
- `group_id` (path, required): The ID of the group
- `role_id` (path, required): The ID of the role

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `groups.update`

**Response:** `204 No Content`

### Remove Role from Group

**DELETE** `/groups/{group_id}/roles/{role_id}`

Removes a role from a group.

**Parameters:**
- `group_id` (path, required): The ID of the group
- `role_id` (path, required): The ID of the role

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `groups.update`

**Response:** `204 No Content`

## Permission System

### Permission Format

Permissions follow the format: `resource.action`

### Standard Permissions

| Permission | Description |
|------------|-------------|
| `admin.all` | Full administrative access |
| `users.read` | Read user information |
| `users.create` | Create new users |
| `users.update` | Update user information |
| `users.delete` | Delete users |
| `users.manage_roles` | Assign/remove roles from users |
| `groups.read` | Read group information |
| `groups.create` | Create new groups |
| `groups.update` | Update group information |
| `groups.delete` | Delete groups |
| `groups.manage_members` | Add/remove users from groups |
| `roles.read` | Read role information |
| `roles.create` | Create new roles |
| `roles.update` | Update roles and assign permissions |
| `roles.delete` | Delete roles |
| `permissions.read` | Read permission information |
| `audit.read` | Read audit logs |
| `system.config` | System configuration access |

### Module Permissions

| Module | Permissions |
|--------|-------------|
| Filesystem | `filesystem.read`, `filesystem.write`, `filesystem.delete` |
| Database | `database.read`, `database.write`, `database.execute` |
| Email | `email.read`, `email.send` |
| Web Search | `web_search.search` |
| Memory | `memory.read`, `memory.write` |
| Timeline | `timeline.read`, `timeline.write` |
| Content Packs | `content_packs.read`, `content_packs.create`, `content_packs.install`, `content_packs.update`, `content_packs.delete` |

## Error Handling

### Common Errors

**400 Bad Request - Username Already Exists**
```json
{
  "detail": "Username already registered"
}
```

**403 Forbidden - Insufficient Permissions**
```json
{
  "detail": "You can only update your own user details or need users.update permission"
}
```

**404 Not Found - User Not Found**
```json
{
  "detail": "User not found"
}
```

**400 Bad Request - Cannot Delete Last Admin**
```json
{
  "detail": "Cannot delete the last administrator"
}
```

## Best Practices

### User Management

1. **Strong Passwords**: Enforce strong password policies
2. **Regular Cleanup**: Remove inactive users regularly
3. **Principle of Least Privilege**: Grant minimum required permissions
4. **Group Organization**: Use groups to simplify permission management
5. **Audit Monitoring**: Monitor user activities through audit logs

### Role Design

1. **Role Hierarchy**: Design roles with clear hierarchy
2. **Specific Permissions**: Use specific permissions rather than broad access
3. **Regular Review**: Review and update roles regularly
4. **Documentation**: Document role purposes and permissions
5. **Testing**: Test role permissions thoroughly

### Security

1. **Regular Audits**: Conduct regular permission audits
2. **Access Reviews**: Review user access periodically
3. **Separation of Duties**: Implement separation of duties where appropriate
4. **Monitoring**: Monitor for suspicious activities
5. **Backup Admins**: Maintain multiple administrator accounts

## Integration Examples

### Python User Management Client

```python
import requests
import json

class UserManager:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def create_user(self, username, password, email, full_name, is_admin=False):
        """Create a new user."""
        payload = {
            'username': username,
            'password': password,
            'email': email,
            'full_name': full_name,
            'is_admin': is_admin
        }
        
        response = requests.post(
            f"{self.base_url}/users/",
            headers=self.headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        return response.json()
    
    def assign_role_to_user(self, user_id, role_id):
        """Assign a role to a user."""
        response = requests.post(
            f"{self.base_url}/users/{user_id}/roles/{role_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.status_code == 204
    
    def get_user_permissions(self, user_id):
        """Get user's effective permissions."""
        response = requests.get(
            f"{self.base_url}/users/{user_id}",
            headers=self.headers
        )
        response.raise_for_status()
        user_data = response.json()
        return user_data.get('permissions', [])

# Usage
manager = UserManager('http://localhost:8000', 'your-admin-token')

# Create a new developer user
user = manager.create_user(
    username='developer1',
    password='your_secure_password',
    email='dev1@company.com',
    full_name='Developer One'
)

# Assign developer role (assuming role ID 3)
manager.assign_role_to_user(user['id'], 3)

# Check user permissions
permissions = manager.get_user_permissions(user['id'])
print(f"User permissions: {permissions}")
```

### JavaScript User Management

```javascript
class UserManager {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }
  
  async createGroup(name, description) {
    const response = await fetch(`${this.baseUrl}/groups/`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        name: name,
        description: description
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create group: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async addUserToGroup(userId, groupId) {
    const response = await fetch(`${this.baseUrl}/users/${userId}/groups/${groupId}`, {
      method: 'POST',
      headers: this.headers
    });
    
    if (!response.ok) {
      throw new Error(`Failed to add user to group: ${response.statusText}`);
    }
    
    return response.status === 204;
  }
  
  async getUsersInGroup(groupId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}`, {
      headers: this.headers
    });
    
    if (!response.ok) {
      throw new Error(`Failed to get group: ${response.statusText}`);
    }
    
    const group = await response.json();
    return group.users;
  }
}

// Usage
const manager = new UserManager('http://localhost:8000', 'your-admin-token');

// Create a development team group
const group = await manager.createGroup(
  'development-team',
  'Development team members'
);

// Add users to the group
await manager.addUserToGroup(5, group.id);  // Add user ID 5
await manager.addUserToGroup(6, group.id);  // Add user ID 6

// Get all users in the group
const users = await manager.getUsersInGroup(group.id);
console.log(`Group members: ${users.join(', ')}`);
```