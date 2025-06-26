# Error Handling

IntentVerse provides comprehensive error handling with consistent error responses, detailed error codes, and troubleshooting guidance. This guide covers all error scenarios you may encounter when using the API.

## Error Response Format

All API errors follow a consistent JSON format:

```json
{
  "detail": "Error description",
  "status_code": 400,
  "error_type": "validation_error",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456789"
}
```

### Error Response Fields

- **detail**: Human-readable error description
- **status_code**: HTTP status code (also in response header)
- **error_type**: Categorized error type for programmatic handling
- **timestamp**: When the error occurred (ISO 8601 format)
- **request_id**: Unique identifier for the request (for support)

## HTTP Status Codes

### 2xx Success Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request successful, no response body |

### 4xx Client Error Codes

| Code | Status | Description | Common Causes |
|------|--------|-------------|---------------|
| 400 | Bad Request | Invalid request format or parameters | Missing required fields, invalid JSON, malformed data |
| 401 | Unauthorized | Authentication required or failed | Missing/invalid token, expired token, invalid API key |
| 403 | Forbidden | Insufficient permissions | User lacks required permissions, action not allowed |
| 404 | Not Found | Resource not found | Invalid endpoint, non-existent resource ID |
| 409 | Conflict | Resource conflict | Duplicate username, conflicting state |
| 422 | Unprocessable Entity | Validation error | Invalid data format, constraint violations |
| 429 | Too Many Requests | Rate limit exceeded | Too many requests in time window |

### 5xx Server Error Codes

| Code | Status | Description | Common Causes |
|------|--------|-------------|---------------|
| 500 | Internal Server Error | Unexpected server error | Database errors, unhandled exceptions |
| 502 | Bad Gateway | Upstream service error | External service failures |
| 503 | Service Unavailable | Service temporarily unavailable | Maintenance mode, overload |
| 504 | Gateway Timeout | Request timeout | Long-running operations, network issues |

## Error Categories

### Authentication Errors

#### 401 Unauthorized - Missing Token
```json
{
  "detail": "Could not validate credentials",
  "status_code": 401,
  "error_type": "authentication_error"
}
```

**Causes:**
- Missing Authorization header
- Invalid JWT token format
- Expired token

**Solutions:**
- Include `Authorization: Bearer TOKEN` header
- Obtain a new token via `/auth/login`
- Check token format and expiration

#### 401 Unauthorized - Invalid Credentials
```json
{
  "detail": "Incorrect username or password",
  "status_code": 401,
  "error_type": "authentication_error"
}
```

**Causes:**
- Wrong username or password
- Account disabled
- Account locked

**Solutions:**
- Verify credentials
- Check account status
- Contact administrator if locked

### Authorization Errors

#### 403 Forbidden - Insufficient Permissions
```json
{
  "detail": "Insufficient permissions to execute 'filesystem.write_file'. Required: filesystem.write",
  "status_code": 403,
  "error_type": "authorization_error"
}
```

**Causes:**
- User lacks required permission
- Role doesn't include necessary permissions
- Group permissions not assigned

**Solutions:**
- Request permission from administrator
- Check user roles and permissions
- Verify group membership

#### 403 Forbidden - Admin Only Action
```json
{
  "detail": "Only administrators can perform this action",
  "status_code": 403,
  "error_type": "authorization_error"
}
```

**Causes:**
- Non-admin user attempting admin action
- Admin flag not set on user account

**Solutions:**
- Contact administrator
- Request admin privileges if appropriate

### Validation Errors

#### 400 Bad Request - Missing Required Field
```json
{
  "detail": "Username is required",
  "status_code": 400,
  "error_type": "validation_error"
}
```

**Causes:**
- Required field not provided
- Empty or null values for required fields

**Solutions:**
- Include all required fields
- Check API documentation for required parameters

#### 422 Unprocessable Entity - Invalid Data Format
```json
{
  "detail": "Invalid email format",
  "status_code": 422,
  "error_type": "validation_error",
  "field": "email",
  "value": "invalid-email"
}
```

**Causes:**
- Data doesn't match expected format
- Constraint violations
- Invalid data types

**Solutions:**
- Validate data format before sending
- Check field constraints in documentation
- Use appropriate data types

#### 400 Bad Request - Invalid Tool Name
```json
{
  "detail": "`tool_name` is required in the format 'module.method'.",
  "status_code": 400,
  "error_type": "validation_error"
}
```

**Causes:**
- Tool name missing or malformed
- Incorrect format for tool execution

**Solutions:**
- Use format: `module.method`
- Check available tools via `/api/v1/tools/manifest`

### Resource Errors

#### 404 Not Found - Resource Not Found
```json
{
  "detail": "User not found",
  "status_code": 404,
  "error_type": "resource_error",
  "resource_type": "user",
  "resource_id": "999"
}
```

**Causes:**
- Resource ID doesn't exist
- Resource was deleted
- Incorrect endpoint URL

**Solutions:**
- Verify resource ID exists
- Check if resource was deleted
- Confirm correct endpoint URL

#### 409 Conflict - Resource Already Exists
```json
{
  "detail": "Username already registered",
  "status_code": 409,
  "error_type": "conflict_error",
  "field": "username",
  "value": "existing_user"
}
```

**Causes:**
- Attempting to create duplicate resource
- Unique constraint violation

**Solutions:**
- Use different unique values
- Check if resource already exists
- Update existing resource instead

### Tool Execution Errors

#### 404 Not Found - Tool Not Found
```json
{
  "detail": "Tool 'invalid.method' not found.",
  "status_code": 404,
  "error_type": "tool_error",
  "tool_name": "invalid.method"
}
```

**Causes:**
- Tool doesn't exist
- Module not loaded
- Typo in tool name

**Solutions:**
- Check available tools via manifest
- Verify module is enabled
- Correct tool name spelling

#### 422 Unprocessable Entity - Missing Tool Parameter
```json
{
  "detail": "Missing required parameter for 'filesystem.read_file': file_path",
  "status_code": 422,
  "error_type": "tool_error",
  "tool_name": "filesystem.read_file",
  "missing_parameter": "file_path"
}
```

**Causes:**
- Required parameter not provided
- Parameter name mismatch

**Solutions:**
- Include all required parameters
- Check tool manifest for parameter names
- Verify parameter spelling

#### 500 Internal Server Error - Tool Execution Failed
```json
{
  "detail": "An error occurred while executing tool 'filesystem.read_file': File not found",
  "status_code": 500,
  "error_type": "tool_execution_error",
  "tool_name": "filesystem.read_file",
  "original_error": "FileNotFoundError: [Errno 2] No such file or directory: '/invalid/path.txt'"
}
```

**Causes:**
- Tool logic error
- External dependency failure
- Invalid parameters causing tool failure

**Solutions:**
- Check tool parameters are valid
- Verify external dependencies
- Check system logs for details

### System Errors

#### 500 Internal Server Error - Database Error
```json
{
  "detail": "Database connection failed",
  "status_code": 500,
  "error_type": "database_error",
  "database_error": "Connection timeout"
}
```

**Causes:**
- Database server down
- Connection pool exhausted
- Database corruption

**Solutions:**
- Check database server status
- Restart database service
- Contact system administrator

#### 503 Service Unavailable - Maintenance Mode
```json
{
  "detail": "Service temporarily unavailable for maintenance",
  "status_code": 503,
  "error_type": "maintenance_error",
  "retry_after": 3600
}
```

**Causes:**
- System maintenance
- Service overload
- Planned downtime

**Solutions:**
- Wait for maintenance to complete
- Check service status page
- Retry after specified time

## Content Pack Errors

#### 404 Not Found - Content Pack Not Found
```json
{
  "detail": "Content pack 'invalid-pack.json' not found",
  "status_code": 404,
  "error_type": "content_pack_error",
  "filename": "invalid-pack.json"
}
```

#### 422 Unprocessable Entity - Content Pack Validation Failed
```json
{
  "detail": "Content pack validation failed",
  "status_code": 422,
  "error_type": "content_pack_validation_error",
  "validation_errors": [
    "Module 'invalid_module' not found",
    "Version '2.0.0' not compatible with current version '1.0.0'"
  ]
}
```

## Error Handling Best Practices

### Client-Side Error Handling

#### Python Example

```python
import requests
from requests.exceptions import RequestException
import time

class IntentVerseAPIError(Exception):
    def __init__(self, status_code, error_type, detail, response_data=None):
        self.status_code = status_code
        self.error_type = error_type
        self.detail = detail
        self.response_data = response_data
        super().__init__(f"{status_code}: {detail}")

class IntentVerseClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
    
    def _handle_response(self, response):
        """Handle API response and raise appropriate exceptions."""
        if response.status_code < 400:
            return response.json() if response.content else None
        
        try:
            error_data = response.json()
            error_type = error_data.get('error_type', 'unknown_error')
            detail = error_data.get('detail', 'Unknown error occurred')
        except ValueError:
            error_type = 'unknown_error'
            detail = f"HTTP {response.status_code}: {response.text}"
            error_data = None
        
        raise IntentVerseAPIError(
            status_code=response.status_code,
            error_type=error_type,
            detail=detail,
            response_data=error_data
        )
    
    def execute_tool_with_retry(self, tool_name, parameters, max_retries=3):
        """Execute tool with automatic retry for transient errors."""
        for attempt in range(max_retries + 1):
            try:
                response = self.session.post(
                    f"{self.base_url}/api/v1/execute",
                    json={
                        'tool_name': tool_name,
                        'parameters': parameters
                    }
                )
                return self._handle_response(response)
                
            except IntentVerseAPIError as e:
                if e.status_code in [500, 502, 503, 504] and attempt < max_retries:
                    # Retry for server errors
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Retrying in {wait_time} seconds... (attempt {attempt + 1})")
                    time.sleep(wait_time)
                    continue
                else:
                    # Don't retry for client errors or max retries reached
                    raise
            
            except RequestException as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    print(f"Network error, retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise IntentVerseAPIError(
                        status_code=0,
                        error_type='network_error',
                        detail=f"Network error: {str(e)}"
                    )

# Usage example
client = IntentVerseClient('http://localhost:8000', 'your-token')

try:
    result = client.execute_tool_with_retry(
        'filesystem.read_file',
        {'file_path': '/etc/hosts'}
    )
    print("Success:", result)
    
except IntentVerseAPIError as e:
    if e.error_type == 'authentication_error':
        print("Authentication failed. Please check your token.")
    elif e.error_type == 'authorization_error':
        print("Permission denied. Contact administrator.")
    elif e.error_type == 'tool_error':
        print(f"Tool error: {e.detail}")
    elif e.error_type == 'validation_error':
        print(f"Validation error: {e.detail}")
    else:
        print(f"API error: {e.detail}")
```

#### JavaScript Example

```javascript
class IntentVerseAPIError extends Error {
  constructor(statusCode, errorType, detail, responseData = null) {
    super(`${statusCode}: ${detail}`);
    this.name = 'IntentVerseAPIError';
    this.statusCode = statusCode;
    this.errorType = errorType;
    this.detail = detail;
    this.responseData = responseData;
  }
}

class IntentVerseClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.token = token;
  }
  
  async _handleResponse(response) {
    if (response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      return null;
    }
    
    let errorData;
    try {
      errorData = await response.json();
    } catch (e) {
      errorData = {
        error_type: 'unknown_error',
        detail: `HTTP ${response.status}: ${response.statusText}`
      };
    }
    
    throw new IntentVerseAPIError(
      response.status,
      errorData.error_type || 'unknown_error',
      errorData.detail || 'Unknown error occurred',
      errorData
    );
  }
  
  async executeToolWithRetry(toolName, parameters, maxRetries = 3) {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await fetch(`${this.baseUrl}/api/v1/execute`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            tool_name: toolName,
            parameters: parameters
          })
        });
        
        return await this._handleResponse(response);
        
      } catch (error) {
        if (error instanceof IntentVerseAPIError) {
          // Retry for server errors
          if ([500, 502, 503, 504].includes(error.statusCode) && attempt < maxRetries) {
            const waitTime = Math.pow(2, attempt) * 1000; // Exponential backoff
            console.log(`Retrying in ${waitTime}ms... (attempt ${attempt + 1})`);
            await new Promise(resolve => setTimeout(resolve, waitTime));
            continue;
          }
        } else if (attempt < maxRetries) {
          // Network error, retry
          const waitTime = Math.pow(2, attempt) * 1000;
          console.log(`Network error, retrying in ${waitTime}ms...`);
          await new Promise(resolve => setTimeout(resolve, waitTime));
          continue;
        }
        
        throw error;
      }
    }
  }
  
  async handleApiCall(apiCall) {
    try {
      return await apiCall();
    } catch (error) {
      if (error instanceof IntentVerseAPIError) {
        switch (error.errorType) {
          case 'authentication_error':
            console.error('Authentication failed. Please check your token.');
            // Redirect to login or refresh token
            break;
          case 'authorization_error':
            console.error('Permission denied. Contact administrator.');
            // Show permission error UI
            break;
          case 'validation_error':
            console.error('Validation error:', error.detail);
            // Show validation error to user
            break;
          case 'tool_error':
            console.error('Tool execution error:', error.detail);
            // Show tool error message
            break;
          default:
            console.error('API error:', error.detail);
            // Show generic error message
        }
      } else {
        console.error('Network or unexpected error:', error);
        // Show network error message
      }
      throw error;
    }
  }
}

// Usage example
const client = new IntentVerseClient('http://localhost:8000', 'your-token');

// Execute tool with error handling
client.handleApiCall(async () => {
  return await client.executeToolWithRetry(
    'database.execute_query',
    { query: 'SELECT COUNT(*) FROM users', fetch_results: true }
  );
}).then(result => {
  console.log('Query result:', result);
}).catch(error => {
  // Error already handled in handleApiCall
});
```

### Error Recovery Strategies

#### Token Refresh Strategy

```python
class TokenManager:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        self.token_expires = None
    
    def get_valid_token(self):
        """Get a valid token, refreshing if necessary."""
        if self.token is None or self._is_token_expired():
            self._refresh_token()
        return self.token
    
    def _is_token_expired(self):
        """Check if token is expired or will expire soon."""
        if self.token_expires is None:
            return True
        
        # Refresh token 5 minutes before expiration
        import datetime
        buffer_time = datetime.timedelta(minutes=5)
        return datetime.datetime.now() + buffer_time >= self.token_expires
    
    def _refresh_token(self):
        """Refresh the authentication token."""
        response = requests.post(
            f"{self.base_url}/auth/login",
            data={
                'username': self.username,
                'password': self.password
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            # Assume token expires in 1 hour (adjust based on your setup)
            import datetime
            self.token_expires = datetime.datetime.now() + datetime.timedelta(hours=1)
        else:
            raise Exception("Failed to refresh token")
```

#### Circuit Breaker Pattern

```javascript
class CircuitBreaker {
  constructor(threshold = 5, timeout = 60000) {
    this.threshold = threshold;
    this.timeout = timeout;
    this.failureCount = 0;
    this.lastFailureTime = null;
    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
  }
  
  async execute(operation) {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailureTime > this.timeout) {
        this.state = 'HALF_OPEN';
      } else {
        throw new Error('Circuit breaker is OPEN');
      }
    }
    
    try {
      const result = await operation();
      this._onSuccess();
      return result;
    } catch (error) {
      this._onFailure();
      throw error;
    }
  }
  
  _onSuccess() {
    this.failureCount = 0;
    this.state = 'CLOSED';
  }
  
  _onFailure() {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    
    if (this.failureCount >= this.threshold) {
      this.state = 'OPEN';
    }
  }
}

// Usage
const circuitBreaker = new CircuitBreaker(3, 30000); // 3 failures, 30s timeout

async function callAPI() {
  return await circuitBreaker.execute(async () => {
    const response = await fetch('/api/v1/some-endpoint');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  });
}
```

## Debugging and Troubleshooting

### Enable Debug Logging

Add debug information to your requests:

```bash
# Add request ID for tracking
curl -H "X-Request-ID: debug-123" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/api/v1/ui/layout"
```

### Check System Status

Use debug endpoints to check system health:

```bash
# Check module loader state
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/api/v1/debug/module-loader-state"
```

### Monitor Audit Logs

Check audit logs for detailed error information:

```bash
# Get recent error events
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/audit-logs/?status=failure&limit=10"
```

### Common Troubleshooting Steps

1. **Verify Authentication**
   - Check token format and expiration
   - Verify API key if using service authentication
   - Test with `/users/me` endpoint

2. **Check Permissions**
   - Verify user has required permissions
   - Check role assignments
   - Review group memberships

3. **Validate Request Format**
   - Ensure JSON is valid
   - Check required fields are present
   - Verify data types match expectations

4. **Test with Minimal Request**
   - Start with simplest possible request
   - Add complexity gradually
   - Isolate the problematic component

5. **Check System Status**
   - Verify all modules are loaded
   - Check database connectivity
   - Review system logs

### Getting Support

When reporting issues, include:

1. **Request Details**
   - Full request URL and method
   - Request headers and body
   - Response status and body

2. **Error Information**
   - Complete error response
   - Request ID if available
   - Timestamp of the error

3. **Environment Details**
   - IntentVerse version
   - Client library/language
   - Operating system

4. **Reproduction Steps**
   - Minimal steps to reproduce
   - Expected vs actual behavior
   - Any workarounds found

This comprehensive error handling guide should help you handle all error scenarios effectively and build robust integrations with the IntentVerse API.