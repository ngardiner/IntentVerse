# MCP Proxy API Reference

This document provides a comprehensive API reference for the MCP Proxy Engine endpoints and programmatic interfaces.

## Overview

The MCP Proxy Engine exposes several APIs for:
- Managing proxy servers and connections
- Monitoring proxy operations
- Controlling tool discovery and registration
- Accessing proxy statistics and health information

## Base URLs

- **MCP Interface**: `http://localhost:8001` (default)
- **Core Service**: `http://localhost:8000` (for admin operations)

## Authentication

All proxy API endpoints support the same authentication methods as the main MCP Interface:

```http
Authorization: Bearer <jwt-token>
# OR
X-API-Key: <service-api-key>
```

## Proxy Management Endpoints

### Get Proxy Engine Status

**GET** `/admin/proxy-status`

Returns the current status of the MCP Proxy Engine.

**Response:**
```json
{
  "status": "running",
  "initialized": true,
  "servers_configured": 3,
  "servers_connected": 2,
  "tools_discovered": 15,
  "uptime_seconds": 3600.5
}
```

**Response Fields:**
- `status`: Engine status (`"running"`, `"stopped"`, `"initializing"`)
- `initialized`: Whether the engine is fully initialized
- `servers_configured`: Number of servers in configuration
- `servers_connected`: Number of successfully connected servers
- `tools_discovered`: Total number of discovered tools
- `uptime_seconds`: Engine uptime in seconds

### Get Proxy Engine Statistics

**GET** `/admin/proxy-stats`

Returns detailed statistics about the proxy engine operations.

**Response:**
```json
{
  "servers_configured": 3,
  "servers_connected": 2,
  "tools_discovered": 15,
  "proxy_functions_generated": 15,
  "tools_registered": 15,
  "conflicts_detected": 1,
  "uptime_seconds": 3600.5,
  "last_discovery": 1642248000.0,
  "generation_stats": {
    "total_functions": 15,
    "functions_by_server": {
      "weather-api": 5,
      "db-tools": 10
    },
    "servers_represented": 2,
    "oldest_function": 1642244400.0,
    "newest_function": 1642248000.0
  }
}
```

### Refresh Proxy Tools

**POST** `/admin/refresh-proxy-tools`

Forces a refresh of all proxy tools from connected servers.

**Request Body:** None

**Response:**
```json
{
  "success": true,
  "tools_discovered": 18,
  "tools_registered": 18,
  "servers_refreshed": 2,
  "refresh_time": 2.5
}
```

### Get Server Status

**GET** `/admin/servers`

Returns status information for all configured MCP servers.

**Response:**
```json
{
  "servers": [
    {
      "name": "weather-api",
      "enabled": true,
      "connected": true,
      "type": "streamable-http",
      "url": "https://weather-mcp.example.com/mcp",
      "tools_count": 5,
      "last_health_check": "2024-01-15T10:30:00Z",
      "connection_status": "healthy",
      "error_count": 0
    },
    {
      "name": "db-tools",
      "enabled": true,
      "connected": false,
      "type": "stdio",
      "command": "/opt/db-tools/mcp-server",
      "tools_count": 0,
      "last_health_check": "2024-01-15T10:29:45Z",
      "connection_status": "failed",
      "error_count": 3,
      "last_error": "Connection timeout"
    }
  ]
}
```

### Get Specific Server Status

**GET** `/admin/servers/{server_name}`

Returns detailed status for a specific server.

**Path Parameters:**
- `server_name`: Name of the server as configured in `mcp-proxy.json`

**Response:**
```json
{
  "name": "weather-api",
  "enabled": true,
  "connected": true,
  "type": "streamable-http",
  "url": "https://weather-mcp.example.com/mcp",
  "server_info": {
    "name": "Weather MCP Server",
    "version": "1.2.0",
    "protocol_version": "2024-11-05"
  },
  "tools": [
    {
      "name": "weather_get_current",
      "description": "Get current weather for a location",
      "proxy_name": "weather_get_current"
    }
  ],
  "connection_details": {
    "connected_at": "2024-01-15T09:00:00Z",
    "last_health_check": "2024-01-15T10:30:00Z",
    "health_status": "healthy",
    "response_time_ms": 150
  },
  "statistics": {
    "total_calls": 42,
    "successful_calls": 40,
    "failed_calls": 2,
    "average_response_time_ms": 200,
    "last_call": "2024-01-15T10:25:00Z"
  }
}
```

## Tool Management Endpoints

### List Proxy Tools

**GET** `/tools/proxy`

Returns all tools discovered through the proxy engine.

**Query Parameters:**
- `server`: Filter by server name
- `prefix`: Filter by tool name prefix
- `enabled`: Filter by enabled status (`true`/`false`)

**Response:**
```json
{
  "tools": [
    {
      "name": "weather_get_current",
      "description": "Get current weather for a location",
      "server_name": "weather-api",
      "original_name": "get_current",
      "proxy_metadata": {
        "created_at": 1642244400.0,
        "server_type": "streamable-http",
        "proxy_version": "1.0"
      },
      "schema": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "Location to get weather for"
          }
        },
        "required": ["location"]
      }
    }
  ],
  "total_count": 15,
  "servers_represented": 2
}
```

### Get Proxy Tool Details

**GET** `/tools/proxy/{tool_name}`

Returns detailed information about a specific proxy tool.

**Path Parameters:**
- `tool_name`: Name of the proxy tool

**Response:**
```json
{
  "name": "weather_get_current",
  "description": "Get current weather for a location",
  "server_name": "weather-api",
  "original_name": "get_current",
  "proxy_metadata": {
    "created_at": 1642244400.0,
    "server_type": "streamable-http",
    "proxy_version": "1.0",
    "last_called": 1642247000.0,
    "call_count": 15
  },
  "schema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "Location to get weather for"
      },
      "units": {
        "type": "string",
        "enum": ["metric", "imperial"],
        "default": "metric"
      }
    },
    "required": ["location"]
  },
  "parameter_info": {
    "location": {
      "type": "str",
      "required": true,
      "description": "Location to get weather for"
    },
    "units": {
      "type": "str",
      "required": false,
      "default": "metric",
      "choices": ["metric", "imperial"]
    }
  }
}
```

## Tool Execution

### Execute Proxy Tool

**POST** `/tools/call`

Executes a proxy tool (same endpoint as native tools).

**Request Body:**
```json
{
  "name": "weather_get_current",
  "arguments": {
    "location": "San Francisco, CA",
    "units": "metric"
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "temperature": 18.5,
    "condition": "Partly Cloudy",
    "humidity": 65,
    "wind_speed": 12.5
  },
  "metadata": {
    "tool_name": "weather_get_current",
    "server_name": "weather-api",
    "execution_time_ms": 250,
    "proxy_metadata": {
      "proxy_version": "1.0",
      "server_type": "streamable-http",
      "original_tool": "get_current"
    }
  }
}
```

## Configuration Management

### Get Proxy Configuration

**GET** `/admin/proxy-config`

Returns the current proxy configuration.

**Response:**
```json
{
  "version": "1.0",
  "mcpServers": {
    "weather-api": {
      "enabled": true,
      "description": "Weather information service",
      "type": "streamable-http",
      "url": "https://weather-mcp.example.com/mcp",
      "settings": {
        "timeout": 30,
        "tool_prefix": "weather_"
      }
    }
  },
  "global_settings": {
    "discovery_interval": 300,
    "max_concurrent_calls": 10,
    "enable_timeline_logging": true
  }
}
```

### Validate Configuration

**POST** `/admin/validate-proxy-config`

Validates a proxy configuration without applying it.

**Request Body:**
```json
{
  "version": "1.0",
  "mcpServers": {
    "test-server": {
      "enabled": true,
      "type": "stdio",
      "command": "/path/to/server"
    }
  }
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "Server 'test-server' has no timeout configured, using default"
  ],
  "servers_validated": 1
}
```

## Health and Monitoring

### Health Check

**GET** `/health/proxy`

Returns health status of the proxy engine and all servers.

**Response:**
```json
{
  "status": "healthy",
  "engine_status": "running",
  "servers": {
    "weather-api": {
      "status": "healthy",
      "last_check": "2024-01-15T10:30:00Z",
      "response_time_ms": 150
    },
    "db-tools": {
      "status": "unhealthy",
      "last_check": "2024-01-15T10:29:45Z",
      "error": "Connection timeout"
    }
  },
  "overall_health": "degraded"
}
```

### Get Proxy Metrics

**GET** `/metrics/proxy`

Returns detailed metrics for monitoring and alerting.

**Response:**
```json
{
  "engine_metrics": {
    "uptime_seconds": 3600.5,
    "tools_discovered": 15,
    "tools_registered": 15,
    "servers_connected": 2,
    "discovery_cycles": 12,
    "last_discovery_duration_ms": 500
  },
  "call_metrics": {
    "total_calls": 150,
    "successful_calls": 145,
    "failed_calls": 5,
    "average_response_time_ms": 200,
    "calls_per_minute": 2.5,
    "error_rate_percent": 3.33
  },
  "server_metrics": {
    "weather-api": {
      "calls": 100,
      "success_rate": 98.0,
      "avg_response_time_ms": 150,
      "last_error": null
    },
    "db-tools": {
      "calls": 50,
      "success_rate": 90.0,
      "avg_response_time_ms": 300,
      "last_error": "2024-01-15T10:15:00Z"
    }
  }
}
```

## Error Responses

### Standard Error Format

All proxy API endpoints use a consistent error format:

```json
{
  "error": {
    "type": "ProxyError",
    "code": "SERVER_UNAVAILABLE",
    "message": "MCP server 'weather-api' is not available",
    "details": {
      "server_name": "weather-api",
      "last_attempt": "2024-01-15T10:30:00Z",
      "retry_count": 3
    },
    "timestamp": "2024-01-15T10:30:15Z"
  }
}
```

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `ENGINE_NOT_INITIALIZED` | Proxy engine not initialized | 503 |
| `SERVER_NOT_FOUND` | Specified server not configured | 404 |
| `SERVER_UNAVAILABLE` | Server not connected or responding | 503 |
| `TOOL_NOT_FOUND` | Proxy tool not found | 404 |
| `INVALID_PARAMETERS` | Tool parameters validation failed | 400 |
| `TIMEOUT_ERROR` | Tool call or server operation timed out | 408 |
| `CONFIGURATION_ERROR` | Invalid proxy configuration | 400 |
| `DISCOVERY_FAILED` | Tool discovery operation failed | 500 |

## Rate Limiting

Proxy API endpoints are subject to rate limiting:

- **Tool Execution**: Limited by `max_concurrent_calls` setting
- **Discovery Operations**: Limited to prevent server overload
- **Admin Operations**: Standard API rate limits apply

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248000
```

## WebSocket Support

### Real-time Proxy Events

**WebSocket** `/ws/proxy-events`

Subscribe to real-time proxy engine events:

```javascript
const ws = new WebSocket('ws://localhost:8001/ws/proxy-events');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Proxy event:', data);
};
```

**Event Types:**
- `server_connected`: Server connection established
- `server_disconnected`: Server connection lost
- `tool_discovered`: New tool discovered
- `tool_call_started`: Proxy tool call initiated
- `tool_call_completed`: Proxy tool call finished
- `discovery_cycle_completed`: Tool discovery cycle finished

**Event Format:**
```json
{
  "type": "tool_call_completed",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "tool_name": "weather_get_current",
    "server_name": "weather-api",
    "duration_ms": 250,
    "success": true
  }
}
```

## SDK and Client Libraries

### Python Client Example

```python
import httpx
import asyncio

class MCPProxyClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def get_proxy_status(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/admin/proxy-status",
                headers=self.headers
            )
            return response.json()
    
    async def call_proxy_tool(self, tool_name: str, arguments: dict):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tools/call",
                headers=self.headers,
                json={"name": tool_name, "arguments": arguments}
            )
            return response.json()

# Usage
client = MCPProxyClient("http://localhost:8001", "your-token")
status = await client.get_proxy_status()
result = await client.call_proxy_tool("weather_get_current", {"location": "NYC"})
```

### JavaScript Client Example

```javascript
class MCPProxyClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  async getProxyStatus() {
    const response = await fetch(`${this.baseUrl}/admin/proxy-status`, {
      headers: this.headers
    });
    return response.json();
  }

  async callProxyTool(toolName, arguments) {
    const response = await fetch(`${this.baseUrl}/tools/call`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ name: toolName, arguments })
    });
    return response.json();
  }
}

// Usage
const client = new MCPProxyClient('http://localhost:8001', 'your-token');
const status = await client.getProxyStatus();
const result = await client.callProxyTool('weather_get_current', { location: 'NYC' });
```

This comprehensive API reference provides all the information needed to interact with the MCP Proxy Engine programmatically.