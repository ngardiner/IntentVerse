# MCP Interface

The Model Context Protocol (MCP) Interface enables AI models to discover and execute tools within IntentVerse. This interface provides dynamic function calling capabilities for AI integration.

## Overview

The MCP Interface consists of two main endpoints:
1. **Tool Discovery** (`/api/v1/tools/manifest`) - Discover available tools and their signatures
2. **Tool Execution** (`/api/v1/execute`) - Execute tools with parameters

## Authentication

MCP Interface endpoints support both authentication methods:
- **JWT Token**: For user-initiated tool execution
- **API Key**: For service-to-service AI model integration

See [Authentication](authentication.md) for details.

## Tool Discovery

### Get Tools Manifest

**GET** `/api/v1/tools/manifest`

Returns a manifest of all available tools with their signatures and parameter information.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
# OR
X-API-Key: your-service-api-key
```

**Response:**
```json
[
  {
    "name": "filesystem.read_file",
    "description": "Read the contents of a file from the filesystem.",
    "parameters": [
      {
        "name": "file_path",
        "annotation_details": {
          "base_type": "str",
          "is_optional": false,
          "union_types": []
        },
        "required": true
      }
    ]
  },
  {
    "name": "filesystem.write_file",
    "description": "Write content to a file on the filesystem.",
    "parameters": [
      {
        "name": "file_path",
        "annotation_details": {
          "base_type": "str",
          "is_optional": false,
          "union_types": []
        },
        "required": true
      },
      {
        "name": "content",
        "annotation_details": {
          "base_type": "str",
          "is_optional": false,
          "union_types": []
        },
        "required": true
      },
      {
        "name": "create_directories",
        "annotation_details": {
          "base_type": "bool",
          "is_optional": true,
          "union_types": ["bool", "NoneType"]
        },
        "required": false
      }
    ]
  },
  {
    "name": "database.execute_query",
    "description": "Execute a SQL query against the database.",
    "parameters": [
      {
        "name": "query",
        "annotation_details": {
          "base_type": "str",
          "is_optional": false,
          "union_types": []
        },
        "required": true
      },
      {
        "name": "fetch_results",
        "annotation_details": {
          "base_type": "bool",
          "is_optional": true,
          "union_types": ["bool", "NoneType"]
        },
        "required": false
      }
    ]
  }
]
```

**Example:**
```bash
curl -H "X-API-Key: dev-service-key-12345" \
  "http://localhost:8000/api/v1/tools/manifest"
```

## Tool Execution

### Execute Tool

**POST** `/api/v1/execute`

Executes a tool with the provided parameters.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
# OR
X-API-Key: your-service-api-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "tool_name": "module.method",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**Response (Success):**
```json
{
  "status": "success",
  "result": {
    "data": "Tool execution result",
    "metadata": {
      "execution_time": "0.05s",
      "timestamp": "2024-01-01T12:00:00Z"
    }
  }
}
```

**Response (Error):**
```json
{
  "status": "error",
  "detail": "Error message describing what went wrong"
}
```

## Available Tools by Module

### Filesystem Tools

#### filesystem.read_file
Read the contents of a file.

**Parameters:**
- `file_path` (string, required): Path to the file to read

**Example:**
```json
{
  "tool_name": "filesystem.read_file",
  "parameters": {
    "file_path": "/home/user/document.txt"
  }
}
```

#### filesystem.write_file
Write content to a file.

**Parameters:**
- `file_path` (string, required): Path to the file to write
- `content` (string, required): Content to write to the file
- `create_directories` (boolean, optional): Create parent directories if they don't exist

**Example:**
```json
{
  "tool_name": "filesystem.write_file",
  "parameters": {
    "file_path": "/home/user/new_file.txt",
    "content": "Hello, World!",
    "create_directories": true
  }
}
```

#### filesystem.list_directory
List contents of a directory.

**Parameters:**
- `directory_path` (string, required): Path to the directory to list
- `show_hidden` (boolean, optional): Include hidden files in the listing

#### filesystem.create_directory
Create a new directory.

**Parameters:**
- `directory_path` (string, required): Path to the directory to create
- `create_parents` (boolean, optional): Create parent directories if they don't exist

#### filesystem.delete_file
Delete a file.

**Parameters:**
- `file_path` (string, required): Path to the file to delete

### Database Tools

#### database.execute_query
Execute a SQL query.

**Parameters:**
- `query` (string, required): SQL query to execute
- `fetch_results` (boolean, optional): Whether to return query results

**Example:**
```json
{
  "tool_name": "database.execute_query",
  "parameters": {
    "query": "SELECT * FROM users WHERE active = 1 LIMIT 10",
    "fetch_results": true
  }
}
```

#### database.list_tables
List all tables in the database.

**Parameters:** None

#### database.get_table_info
Get information about a specific table.

**Parameters:**
- `table_name` (string, required): Name of the table

### Email Tools

#### email.send_email
Send an email.

**Parameters:**
- `to` (string, required): Recipient email address
- `subject` (string, required): Email subject
- `body` (string, required): Email body content
- `from_email` (string, optional): Sender email address

**Example:**
```json
{
  "tool_name": "email.send_email",
  "parameters": {
    "to": "user@example.com",
    "subject": "Test Email",
    "body": "This is a test email from IntentVerse."
  }
}
```

### Web Search Tools

#### web_search.search_web
Search the web for information.

**Parameters:**
- `query` (string, required): Search query
- `num_results` (integer, optional): Number of results to return

**Example:**
```json
{
  "tool_name": "web_search.search_web",
  "parameters": {
    "query": "Python FastAPI tutorial",
    "num_results": 5
  }
}
```

### Memory Tools

#### memory.store
Store data in memory.

**Parameters:**
- `key` (string, required): Key to store the data under
- `value` (any, required): Value to store
- `ttl` (integer, optional): Time to live in seconds

**Example:**
```json
{
  "tool_name": "memory.store",
  "parameters": {
    "key": "user_preferences",
    "value": {"theme": "dark", "language": "en"},
    "ttl": 3600
  }
}
```

#### memory.retrieve
Retrieve data from memory.

**Parameters:**
- `key` (string, required): Key to retrieve

#### memory.delete
Delete data from memory.

**Parameters:**
- `key` (string, required): Key to delete

### Timeline Tools

#### timeline.get_events
Get timeline events.

**Parameters:**
- `event_type` (string, optional): Filter by event type
- `limit` (integer, optional): Maximum number of events to return

**Example:**
```json
{
  "tool_name": "timeline.get_events",
  "parameters": {
    "event_type": "tool_execution",
    "limit": 50
  }
}
```

#### timeline.add_event
Add an event to the timeline.

**Parameters:**
- `event_type` (string, required): Type of event
- `title` (string, required): Event title
- `description` (string, required): Event description
- `details` (object, optional): Additional event details

## Permission System

Tool execution is subject to permission checks based on the module and method:

### Permission Mapping

| Module | Method | Required Permission |
|--------|--------|-------------------|
| filesystem | read_file, list_directory | `filesystem.read` |
| filesystem | write_file, create_directory | `filesystem.write` |
| filesystem | delete_file, delete_directory | `filesystem.delete` |
| database | execute_query (SELECT) | `database.read` |
| database | execute_query (INSERT/UPDATE/DELETE) | `database.write` |
| database | execute_script | `database.execute` |
| email | send_email | `email.send` |
| email | other methods | `email.read` |
| web_search | search_web | `web_search.search` |
| memory | store, update, delete | `memory.write` |
| memory | retrieve, list_keys | `memory.read` |
| timeline | add_event | `timeline.write` |
| timeline | get_events | `timeline.read` |

### Service Authentication

When using API key authentication, permission checks are bypassed, allowing full access to all tools.

## Error Handling

### Common Errors

**400 Bad Request - Invalid Tool Name**
```json
{
  "detail": "`tool_name` is required in the format 'module.method'."
}
```

**404 Not Found - Tool Not Found**
```json
{
  "detail": "Tool 'invalid.method' not found."
}
```

**422 Unprocessable Entity - Missing Parameter**
```json
{
  "detail": "Missing required parameter for 'filesystem.read_file': file_path"
}
```

**403 Forbidden - Insufficient Permissions**
```json
{
  "detail": "Insufficient permissions to execute 'filesystem.write_file'. Required: filesystem.write"
}
```

**500 Internal Server Error - Tool Execution Error**
```json
{
  "detail": "An error occurred while executing tool 'filesystem.read_file': File not found"
}
```

## Integration Examples

### Python Client

```python
import requests
import json

class IntentVerseClient:
    def __init__(self, base_url, api_key=None, token=None):
        self.base_url = base_url
        self.headers = {}
        
        if api_key:
            self.headers['X-API-Key'] = api_key
        elif token:
            self.headers['Authorization'] = f'Bearer {token}'
    
    def get_tools_manifest(self):
        """Get available tools manifest."""
        response = requests.get(
            f"{self.base_url}/api/v1/tools/manifest",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def execute_tool(self, tool_name, parameters=None):
        """Execute a tool with parameters."""
        payload = {
            "tool_name": tool_name,
            "parameters": parameters or {}
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/execute",
            headers={**self.headers, 'Content-Type': 'application/json'},
            data=json.dumps(payload)
        )
        response.raise_for_status()
        return response.json()

# Usage example
client = IntentVerseClient(
    base_url="http://localhost:8000",
    api_key="dev-service-key-12345"
)

# Get available tools
tools = client.get_tools_manifest()
print(f"Available tools: {len(tools)}")

# Execute a tool
result = client.execute_tool(
    "filesystem.read_file",
    {"file_path": "/etc/hosts"}
)
print(f"File content: {result['result']}")
```

### JavaScript/Node.js Client

```javascript
class IntentVerseClient {
  constructor(baseUrl, options = {}) {
    this.baseUrl = baseUrl;
    this.headers = {};
    
    if (options.apiKey) {
      this.headers['X-API-Key'] = options.apiKey;
    } else if (options.token) {
      this.headers['Authorization'] = `Bearer ${options.token}`;
    }
  }
  
  async getToolsManifest() {
    const response = await fetch(`${this.baseUrl}/api/v1/tools/manifest`, {
      headers: this.headers
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async executeTool(toolName, parameters = {}) {
    const response = await fetch(`${this.baseUrl}/api/v1/execute`, {
      method: 'POST',
      headers: {
        ...this.headers,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        tool_name: toolName,
        parameters: parameters
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Tool execution failed: ${error.detail}`);
    }
    
    return response.json();
  }
}

// Usage example
const client = new IntentVerseClient('http://localhost:8000', {
  apiKey: 'dev-service-key-12345'
});

// Get available tools
const tools = await client.getToolsManifest();
console.log(`Available tools: ${tools.length}`);

// Execute a tool
const result = await client.executeTool('database.execute_query', {
  query: 'SELECT COUNT(*) as user_count FROM users',
  fetch_results: true
});
console.log('Query result:', result.result);
```

### AI Model Integration

```python
# Example integration with an AI model
def create_function_definitions(tools_manifest):
    """Convert tools manifest to function definitions for AI models."""
    functions = []
    
    for tool in tools_manifest:
        function_def = {
            "name": tool["name"].replace(".", "_"),
            "description": tool["description"],
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        
        for param in tool["parameters"]:
            param_type = param["annotation_details"]["base_type"]
            function_def["parameters"]["properties"][param["name"]] = {
                "type": param_type,
                "description": f"Parameter {param['name']}"
            }
            
            if param["required"]:
                function_def["parameters"]["required"].append(param["name"])
        
        functions.append(function_def)
    
    return functions

def execute_function_call(client, function_name, arguments):
    """Execute a function call from AI model."""
    tool_name = function_name.replace("_", ".", 1)  # Convert back to module.method
    
    try:
        result = client.execute_tool(tool_name, arguments)
        return result["result"]
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"
```

## Best Practices

### Tool Discovery
1. **Cache Manifest**: Cache the tools manifest to avoid repeated requests
2. **Dynamic Loading**: Reload manifest when modules are enabled/disabled
3. **Error Handling**: Handle manifest loading errors gracefully

### Tool Execution
1. **Parameter Validation**: Validate parameters before sending requests
2. **Timeout Handling**: Set appropriate timeouts for tool execution
3. **Retry Logic**: Implement retry logic for transient failures
4. **Result Caching**: Cache tool results when appropriate

### Security
1. **Input Sanitization**: Sanitize all tool parameters
2. **Permission Checks**: Verify user permissions before tool execution
3. **Audit Logging**: Log all tool executions for audit purposes
4. **Rate Limiting**: Implement rate limiting for tool execution

### Performance
1. **Batch Operations**: Group related tool calls when possible
2. **Async Execution**: Use asynchronous execution for better performance
3. **Connection Pooling**: Use connection pooling for HTTP requests
4. **Result Streaming**: Stream large results when possible