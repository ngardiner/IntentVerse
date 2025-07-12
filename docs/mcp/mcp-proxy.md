# MCP Proxy Engine

The MCP Proxy Engine is a powerful component of the IntentVerse MCP Interface that enables seamless integration with external MCP (Model Context Protocol) servers. It acts as a bridge, discovering tools from external MCP servers and making them available as if they were native IntentVerse tools.

## Overview

The MCP Proxy Engine consists of several key components:

- **Discovery Service**: Discovers and manages tools from external MCP servers
- **Proxy Generator**: Creates dynamic proxy functions for external tools
- **Client Manager**: Handles connections to various MCP server types
- **Engine Orchestrator**: Coordinates all proxy operations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Proxy Engine                             │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Discovery     │  │     Proxy       │  │     Client      │ │
│  │   Service       │  │   Generator     │  │    Manager      │ │
│  │                 │  │                 │  │                 │ │
│  │ • Tool Discovery│  │ • Dynamic Proxy │  │ • stdio         │ │
│  │ • Conflict Res. │  │ • Param Mapping │  │ • SSE           │ │
│  │ • Registration  │  │ • Result Proc.  │  │ • HTTP          │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                     │                     │         │
│           └─────────────────────┼─────────────────────┘         │
│                                 │                               │
└─────────────────────────────────┼───────────────────────────────┘
                                  │
                          ┌───────▼────────┐
                          │  FastMCP       │
                          │  Integration   │
                          └────────────────┘
```

## Configuration

The MCP Proxy Engine is configured via the `mcp-proxy.json` file located in the `mcp/` directory.

### Configuration Structure

```json
{
  "version": "1.0",
  "mcpServers": {
    "server-name": {
      "enabled": true,
      "description": "Description of the MCP server",
      "type": "stdio|sse|streamable-http",
      "command": "/path/to/server",  // For stdio type
      "url": "http://server:port",   // For sse/http types
      "args": [],                    // Command arguments (stdio only)
      "env": {},                     // Environment variables
      "headers": {},                 // HTTP headers (sse/http only)
      "settings": {
        "timeout": 30,
        "retry_attempts": 3,
        "retry_delay": 5,
        "tool_prefix": "prefix_",
        "health_check_interval": 60
      }
    }
  },
  "global_settings": {
    "discovery_interval": 300,
    "health_check_interval": 60,
    "max_concurrent_calls": 10,
    "enable_timeline_logging": true,
    "log_level": "INFO"
  }
}
```

### Server Types

#### 1. Stdio Servers
For MCP servers that communicate via stdin/stdout:

```json
{
  "stdio-server": {
    "enabled": true,
    "type": "stdio",
    "command": "/usr/local/bin/my-mcp-server",
    "args": ["--config", "/path/to/config.json"],
    "env": {
      "API_KEY": "your-api-key"
    }
  }
}
```

#### 2. SSE (Server-Sent Events) Servers
For MCP servers that use Server-Sent Events:

```json
{
  "sse-server": {
    "enabled": true,
    "type": "sse",
    "url": "http://127.0.0.1:3000/sse",
    "headers": {
      "Authorization": "Bearer your-token"
    }
  }
}
```

#### 3. HTTP Servers
For MCP servers that use HTTP transport:

```json
{
  "http-server": {
    "enabled": true,
    "type": "streamable-http",
    "url": "http://127.0.0.1:3000/mcp",
    "headers": {
      "X-API-Key": "your-api-key"
    }
  }
}
```

## Features

### Tool Discovery
- **Automatic Discovery**: Automatically discovers tools from all configured MCP servers
- **Conflict Resolution**: Handles naming conflicts between tools from different servers
- **Prefix Support**: Adds configurable prefixes to tool names to avoid conflicts
- **Health Monitoring**: Continuously monitors server health and availability

### Dynamic Proxy Generation
- **Runtime Generation**: Creates proxy functions at runtime for discovered tools
- **Parameter Validation**: Validates parameters according to tool schemas
- **Result Processing**: Processes and enhances results from external tools
- **Error Handling**: Provides comprehensive error handling and logging

### Connection Management
- **Multiple Transports**: Supports stdio, SSE, and HTTP transport protocols
- **Automatic Reconnection**: Automatically reconnects to servers on connection loss
- **Timeout Handling**: Configurable timeouts for all operations
- **Resource Cleanup**: Proper cleanup of connections and resources

## Usage

### Basic Setup

1. **Configure Servers**: Edit `mcp/mcp-proxy.json` to add your MCP servers
2. **Enable Proxy**: The proxy engine is automatically initialized when the MCP Interface starts
3. **Use Tools**: External tools appear alongside native tools in the tool manifest

### Example Configuration

```json
{
  "version": "1.0",
  "mcpServers": {
    "weather-service": {
      "enabled": true,
      "description": "Weather information service",
      "type": "stdio",
      "command": "/usr/local/bin/weather-mcp-server",
      "settings": {
        "tool_prefix": "weather_",
        "timeout": 30
      }
    },
    "database-service": {
      "enabled": true,
      "description": "Database query service",
      "type": "streamable-http",
      "url": "http://db-server:8080/mcp",
      "headers": {
        "Authorization": "Bearer db-token"
      },
      "settings": {
        "tool_prefix": "db_",
        "timeout": 60
      }
    }
  },
  "global_settings": {
    "discovery_interval": 300,
    "max_concurrent_calls": 5,
    "enable_timeline_logging": true
  }
}
```

### Tool Access

Once configured, external tools are available through the standard MCP Interface:

```bash
# Discover all tools (including proxy tools)
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8001/tools/list

# Execute a proxy tool
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name": "weather_get_forecast", "arguments": {"city": "San Francisco"}}' \
     http://localhost:8001/tools/call
```

## API Reference

### Engine Management

The proxy engine provides several management endpoints and methods:

#### Engine Status
```python
# Check if engine is running
engine.is_running  # Returns bool

# Check if engine is initialized
engine.is_initialized  # Returns bool

# Get engine statistics
stats = await engine.get_stats()
```

#### Tool Management
```python
# Get all proxy tools
tools = engine.get_all_tools()

# Get tools from specific server
server_tools = engine.get_tools_by_server("server-name")

# Get specific tool
tool = engine.get_tool("tool-name")
```

#### Server Management
```python
# Refresh tools from all servers
await engine.refresh_tools()

# Get server information
server_info = engine.get_server_info("server-name")

# Check server connection status
status = engine.get_connection_status("server-name")
```

### Proxy Function Generation

The proxy generator creates dynamic functions that:

1. **Validate Parameters**: Check parameter types and requirements
2. **Map Arguments**: Convert arguments to MCP protocol format
3. **Execute Remotely**: Call the external MCP server
4. **Process Results**: Transform results to IntentVerse format
5. **Add Metadata**: Include proxy-specific metadata

#### Generated Function Signature

```python
async def proxy_function(**kwargs) -> Any:
    """
    Dynamically generated proxy function for MCP tool.
    
    This function validates parameters, calls the external MCP tool,
    and processes the result.
    
    Args:
        **kwargs: Tool parameters as defined in the tool schema
        
    Returns:
        The result from the MCP tool execution.
        
    Raises:
        ValueError: If parameters are invalid
        RuntimeError: If the MCP server is unavailable
    """
```

## Monitoring and Debugging

### Timeline Integration

The proxy engine integrates with IntentVerse's timeline system to log:

- **Engine Events**: Start, stop, initialization
- **Discovery Events**: Tool discovery, server connections
- **Proxy Calls**: Tool execution with timing and results
- **Error Events**: Connection failures, tool errors

### Logging

Configure logging levels in the proxy configuration:

```json
{
  "global_settings": {
    "log_level": "DEBUG",  // DEBUG, INFO, WARNING, ERROR
    "enable_timeline_logging": true
  }
}
```

### Health Monitoring

The engine continuously monitors:

- **Server Connectivity**: Regular health checks
- **Tool Availability**: Periodic tool discovery
- **Performance Metrics**: Call timing and success rates
- **Error Rates**: Failed calls and connection issues

## Error Handling

### Common Error Scenarios

1. **Server Unavailable**: Automatic retry with exponential backoff
2. **Tool Not Found**: Clear error messages with suggestions
3. **Parameter Validation**: Detailed validation error messages
4. **Timeout Errors**: Configurable timeouts with graceful degradation
5. **Network Issues**: Automatic reconnection attempts

### Error Response Format

```json
{
  "error": {
    "type": "ProxyError",
    "message": "Server 'weather-service' is unavailable",
    "details": {
      "server_name": "weather-service",
      "last_attempt": "2024-01-15T10:30:00Z",
      "retry_count": 3
    }
  }
}
```

## Performance Considerations

### Optimization Features

- **Connection Pooling**: Reuse connections to external servers
- **Caching**: Cache tool schemas and server information
- **Concurrent Calls**: Support for multiple simultaneous tool calls
- **Lazy Loading**: Load tools on-demand to reduce startup time

### Configuration Tuning

```json
{
  "global_settings": {
    "max_concurrent_calls": 10,     // Limit concurrent proxy calls
    "discovery_interval": 300,      // Tool discovery frequency (seconds)
    "health_check_interval": 60,    // Health check frequency (seconds)
    "connection_timeout": 30,       // Connection timeout (seconds)
    "call_timeout": 60             // Tool call timeout (seconds)
  }
}
```

## Security Considerations

### Authentication
- **Server Authentication**: Support for API keys, tokens, and certificates
- **Secure Transport**: HTTPS/TLS for network communications
- **Credential Management**: Secure storage of server credentials

### Access Control
- **Tool Filtering**: Filter available tools based on user permissions
- **Rate Limiting**: Prevent abuse of external services
- **Audit Logging**: Complete audit trail of proxy operations

### Best Practices
1. Use HTTPS for all network-based MCP servers
2. Implement proper authentication for external servers
3. Set appropriate timeouts to prevent resource exhaustion
4. Monitor proxy usage and set rate limits
5. Regularly update server credentials

## Troubleshooting

### Common Issues

#### Server Connection Failures
```bash
# Check server configuration
cat mcp/mcp-proxy.json

# Check server logs
tail -f logs/mcp-proxy.log

# Test server connectivity
curl -v http://your-mcp-server:port/health
```

#### Tool Discovery Issues
```bash
# Force tool refresh
curl -X POST http://localhost:8001/admin/refresh-tools

# Check discovery logs
grep "discovery" logs/mcp-proxy.log
```

#### Performance Issues
```bash
# Check engine statistics
curl http://localhost:8001/admin/proxy-stats

# Monitor resource usage
top -p $(pgrep -f "mcp.*proxy")
```

### Debug Mode

Enable debug mode for detailed logging:

```json
{
  "global_settings": {
    "log_level": "DEBUG",
    "enable_timeline_logging": true
  }
}
```

## Migration and Upgrades

### Configuration Migration

When upgrading, check for configuration changes:

1. **Backup Configuration**: Always backup `mcp-proxy.json`
2. **Check Schema**: Verify configuration schema compatibility
3. **Test Connections**: Test all server connections after upgrade
4. **Monitor Logs**: Watch logs for any migration issues

### Version Compatibility

The proxy engine maintains backward compatibility for:
- Configuration format (with deprecation warnings)
- Tool schemas (automatic conversion)
- API endpoints (versioned endpoints)

## Examples

### Complete Working Example

Here's a complete example of setting up the MCP Proxy Engine:

1. **Configuration** (`mcp/mcp-proxy.json`):
```json
{
  "version": "1.0",
  "mcpServers": {
    "file-processor": {
      "enabled": true,
      "description": "File processing MCP server",
      "type": "stdio",
      "command": "/usr/local/bin/file-processor-mcp",
      "args": ["--mode", "production"],
      "env": {
        "TEMP_DIR": "/tmp/file-processor"
      },
      "settings": {
        "timeout": 45,
        "retry_attempts": 3,
        "tool_prefix": "file_",
        "health_check_interval": 30
      }
    }
  },
  "global_settings": {
    "discovery_interval": 180,
    "max_concurrent_calls": 8,
    "enable_timeline_logging": true,
    "log_level": "INFO"
  }
}
```

2. **Start the MCP Interface**:
```bash
cd mcp
python -m app.main
```

3. **Verify Tool Discovery**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8001/tools/list | jq '.[] | select(.name | startswith("file_"))'
```

4. **Use Proxy Tool**:
```bash
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name": "file_process_document", "arguments": {"path": "/path/to/doc.pdf"}}' \
     http://localhost:8001/tools/call
```

This comprehensive documentation covers all aspects of the MCP Proxy Engine, from basic setup to advanced troubleshooting. The proxy engine enables IntentVerse to seamlessly integrate with any MCP-compatible external service, greatly expanding its capabilities.