# Authentication

IntentVerse supports two authentication methods: JWT token authentication for users and API key authentication for service-to-service communication.

## Authentication Methods

### 1. JWT Token Authentication (Users)

JWT (JSON Web Token) authentication is used for user sessions and web UI interactions.

#### Login Flow

**Endpoint:** `POST /auth/login`

**Request:**
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=your_username&password=your_password
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example.token",
  "token_type": "bearer"
}
```

#### Using JWT Tokens

Include the token in the Authorization header for all subsequent requests:

```http
Authorization: Bearer YOUR_JWT_TOKEN_HERE
```

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/ui/layout"
```

### 2. API Key Authentication (Services)

API key authentication is used for service-to-service communication and automated systems.

**Header:**
```http
X-API-Key: your-service-api-key
```

**Example:**
```bash
curl -H "X-API-Key: your-service-api-key" \
  "http://localhost:8000/api/v1/tools/manifest"
```

## Authentication Endpoints

### Login

**POST** `/auth/login`

Authenticates a user and returns a JWT access token.

**Parameters:**
- `username` (string, required): User's username
- `password` (string, required): User's password

**Request Example:**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example.signature",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid credentials
- `500 Internal Server Error`: Server error during authentication

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
  "created_at": "2024-01-01T12:00:00Z",
  "last_login": "2024-01-01T14:30:00Z",
  "roles": ["admin", "user"],
  "permissions": [
    "admin.all",
    "users.read",
    "users.create",
    "users.update",
    "users.delete"
  ]
}
```

## Token Management

### Token Expiration

JWT tokens have a configurable expiration time. When a token expires, you'll receive a `401 Unauthorized` response and need to re-authenticate.

### Token Refresh

Currently, token refresh is not implemented. Users must re-authenticate when tokens expire.

## Security Configuration

### Environment Variables

- `SERVICE_API_KEY`: API key for service authentication (default: "your-service-key")
- `SECRET_KEY`: Secret key for JWT token signing
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time in minutes

### Production Security

For production deployments:

1. **Use HTTPS**: Always use HTTPS to protect tokens in transit
2. **Secure API Keys**: Store service API keys securely and rotate regularly
3. **Strong Passwords**: Enforce strong password policies
4. **Token Expiration**: Set appropriate token expiration times
5. **Audit Logging**: Monitor authentication events in audit logs

## Permission System

IntentVerse uses a Role-Based Access Control (RBAC) system:

### Permission Format

Permissions follow the format: `resource.action`

Examples:
- `users.read` - Read user information
- `users.create` - Create new users
- `filesystem.write` - Write to filesystem
- `admin.all` - Full administrative access

### Default Roles

- **Admin**: Full system access (`admin.all`)
- **User**: Basic user permissions
- **Service**: Automated system access

### Checking Permissions

The API automatically checks permissions for protected endpoints. Users without required permissions receive a `403 Forbidden` response.

## Error Handling

### Authentication Errors

**401 Unauthorized**
```json
{
  "detail": "Could not validate credentials"
}
```

**403 Forbidden**
```json
{
  "detail": "Insufficient permissions to execute 'filesystem.write_file'. Required: filesystem.write"
}
```

### Common Issues

1. **Missing Authorization Header**: Include `Authorization: Bearer TOKEN` header
2. **Expired Token**: Re-authenticate to get a new token
3. **Invalid API Key**: Verify the `X-API-Key` header value
4. **Insufficient Permissions**: Contact administrator for required permissions

## Examples

### Complete Authentication Flow

```bash
# 1. Login to get token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password" | \
  jq -r '.access_token')

# 2. Use token for API calls
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/users/me"

# 3. Access protected endpoints
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/ui/layout"
```

### Service Authentication

```bash
# Using API key for service calls
curl -H "X-API-Key: your-service-api-key" \
  "http://localhost:8000/api/v1/tools/manifest"
```

### JavaScript Example

```javascript
// Login function
async function login(username, password) {
  const response = await fetch('/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: `username=${username}&password=${password}`
  });
  
  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('token', data.access_token);
    return data.access_token;
  } else {
    throw new Error('Authentication failed');
  }
}

// API call with token
async function apiCall(endpoint) {
  const token = localStorage.getItem('token');
  const response = await fetch(endpoint, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (response.status === 401) {
    // Token expired, need to re-authenticate
    localStorage.removeItem('token');
    throw new Error('Authentication required');
  }
  
  return response.json();
}
```

## Audit Logging

All authentication events are logged in the audit system:

- **login_success**: Successful user login
- **login_failed**: Failed login attempt
- **token_expired**: Token expiration events
- **permission_denied**: Access denied due to insufficient permissions

Access audit logs via the `/audit-logs/` endpoint with appropriate permissions.