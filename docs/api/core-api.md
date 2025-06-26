# Core API

The Core API provides endpoints for managing module state, UI layout configuration, and system operations. All Core API endpoints are prefixed with `/api/v1`.

## Authentication

All Core API endpoints require authentication via JWT token or API key. See [Authentication](authentication.md) for details.

## UI Layout Management

### Get UI Layout

**GET** `/api/v1/ui/layout`

Returns the complete UI schema for all loaded modules. The frontend uses this to dynamically build its layout.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "modules": [
    {
      "name": "filesystem",
      "displayName": "File System",
      "description": "File system operations and management",
      "version": "1.0.0",
      "components": [
        {
          "type": "file_browser",
          "title": "File Browser",
          "props": {
            "rootPath": "/",
            "allowUpload": true,
            "allowDelete": true
          }
        }
      ]
    },
    {
      "name": "database",
      "displayName": "Database",
      "description": "Database operations and query execution",
      "version": "1.0.0",
      "components": [
        {
          "type": "query_editor",
          "title": "SQL Query Editor",
          "props": {
            "syntax": "sql",
            "autoComplete": true
          }
        }
      ]
    }
  ]
}
```

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/ui/layout"
```

## Module State Management

### Get Module State

**GET** `/api/v1/{module_name}/state`

Returns the current state for a specific module. Used by UI components to fetch their data.

**Parameters:**
- `module_name` (path, required): The name of the module

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Response Example (filesystem module):**
```json
{
  "current_directory": "/home/user",
  "files": [
    {
      "name": "document.txt",
      "type": "file",
      "size": 1024,
      "modified": "2024-01-01T12:00:00Z"
    },
    {
      "name": "projects",
      "type": "directory",
      "size": null,
      "modified": "2024-01-01T10:00:00Z"
    }
  ],
  "permissions": {
    "read": true,
    "write": true,
    "delete": true
  }
}
```

**Response Example (database module):**
```json
{
  "connection_status": "connected",
  "database_info": {
    "type": "sqlite",
    "path": "/app/test.db",
    "size": "2.5 MB"
  },
  "recent_queries": [
    {
      "query": "SELECT * FROM users LIMIT 10",
      "timestamp": "2024-01-01T12:00:00Z",
      "execution_time": "0.05s"
    }
  ],
  "tables": [
    {
      "name": "users",
      "row_count": 150,
      "columns": ["id", "username", "email", "created_at"]
    },
    {
      "name": "audit_logs",
      "row_count": 1250,
      "columns": ["id", "user_id", "action", "timestamp"]
    }
  ]
}
```

**Error Responses:**
- `404 Not Found`: Module not found or no state available
- `403 Forbidden`: Insufficient permissions to access module state

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/filesystem/state"
```

## Module Management

### Get Module Status

**GET** `/api/v1/modules/status`

Returns the status of all available modules (enabled and disabled).

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `system.config`

**Response:**
```json
{
  "status": "success",
  "modules": {
    "filesystem": {
      "name": "filesystem",
      "display_name": "File System",
      "description": "File system operations and management",
      "version": "1.0.0",
      "is_enabled": true,
      "is_loaded": true,
      "has_errors": false,
      "error_message": null,
      "dependencies": [],
      "config": {
        "max_file_size": "100MB",
        "allowed_extensions": ["*"]
      }
    },
    "database": {
      "name": "database",
      "display_name": "Database",
      "description": "Database operations and query execution",
      "version": "1.0.0",
      "is_enabled": true,
      "is_loaded": true,
      "has_errors": false,
      "error_message": null,
      "dependencies": [],
      "config": {
        "connection_timeout": 30,
        "max_query_time": 60
      }
    },
    "email": {
      "name": "email",
      "display_name": "Email",
      "description": "Email sending and management",
      "version": "1.0.0",
      "is_enabled": false,
      "is_loaded": false,
      "has_errors": false,
      "error_message": null,
      "dependencies": [],
      "config": {
        "smtp_server": "localhost",
        "smtp_port": 587
      }
    }
  }
}
```

### Toggle Module

**POST** `/api/v1/modules/{module_name}/toggle`

Enable or disable a module.

**Parameters:**
- `module_name` (path, required): The name of the module

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `system.config`

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Module 'email' enabled successfully",
  "module": {
    "name": "email",
    "enabled": true
  }
}
```

**Error Responses:**
- `404 Not Found`: Module not found
- `500 Internal Server Error`: Failed to toggle module

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/modules/email/toggle" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

## Debug Endpoints

### Get Module Loader State

**GET** `/api/v1/debug/module-loader-state`

Returns a snapshot of the ModuleLoader's state for debugging purposes.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "modules_path_calculated": "/app/modules",
  "modules_path_exists": true,
  "loading_errors": [],
  "loaded_modules": [
    "filesystem",
    "database",
    "email",
    "web_search",
    "memory",
    "timeline"
  ]
}
```

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/debug/module-loader-state"
```

## Available Modules

IntentVerse includes several built-in modules:

### Filesystem Module
- **Purpose**: File system operations and management
- **Capabilities**: Read, write, delete files and directories
- **State**: Current directory, file listings, permissions
- **Tools**: `read_file`, `write_file`, `list_directory`, `create_directory`, `delete_file`

### Database Module
- **Purpose**: Database operations and query execution
- **Capabilities**: Execute SQL queries, manage database connections
- **State**: Connection status, table information, recent queries
- **Tools**: `execute_query`, `list_tables`, `get_table_info`, `execute_script`

### Email Module
- **Purpose**: Email sending and management
- **Capabilities**: Send emails, manage email templates
- **State**: SMTP configuration, sent email history
- **Tools**: `send_email`, `validate_email`, `get_email_templates`

### Web Search Module
- **Purpose**: Web search and information retrieval
- **Capabilities**: Search the web, retrieve web content
- **State**: Search history, cached results
- **Tools**: `search_web`, `get_page_content`, `extract_links`

### Memory Module
- **Purpose**: Persistent data storage and retrieval
- **Capabilities**: Store and retrieve key-value data
- **State**: Stored data, memory usage statistics
- **Tools**: `store`, `retrieve`, `delete`, `list_keys`, `clear_all`

### Timeline Module
- **Purpose**: Event logging and timeline management
- **Capabilities**: Log events, retrieve timeline data
- **State**: Recent events, event statistics
- **Tools**: `get_events`, `add_event`, `clear_events`

## Error Handling

### Common Error Responses

**400 Bad Request**
```json
{
  "detail": "Invalid module name format"
}
```

**403 Forbidden**
```json
{
  "detail": "Insufficient permissions. Required: system.config"
}
```

**404 Not Found**
```json
{
  "detail": "No state found for module: invalid_module"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Failed to toggle module 'email'"
}
```

## Best Practices

### Module State Management

1. **Polling**: Poll module state endpoints periodically to keep UI in sync
2. **Caching**: Cache module state locally and update when needed
3. **Error Handling**: Handle module state errors gracefully
4. **Permissions**: Check user permissions before accessing module state

### Performance Considerations

1. **Selective Loading**: Only load state for modules currently displayed
2. **Batch Requests**: Use multiple concurrent requests for different modules
3. **State Diffing**: Compare state changes to minimize UI updates
4. **Lazy Loading**: Load module state on-demand when users navigate to modules

### Integration Patterns

```javascript
// React hook for module state management
function useModuleState(moduleName) {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchState() {
      try {
        setLoading(true);
        const response = await fetch(`/api/v1/${moduleName}/state`, {
          headers: {
            'Authorization': `Bearer ${getToken()}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          setState(data);
          setError(null);
        } else {
          setError(`Failed to load ${moduleName} state`);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchState();
    
    // Poll for updates every 30 seconds
    const interval = setInterval(fetchState, 30000);
    return () => clearInterval(interval);
  }, [moduleName]);

  return { state, loading, error, refetch: fetchState };
}
```