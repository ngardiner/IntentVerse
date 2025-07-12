# MCP Proxy Quick Start Guide

This guide helps you quickly set up and use the MCP Proxy Engine to connect external MCP servers to IntentVerse.

## 5-Minute Setup

### Step 1: Configure Your First MCP Server

Edit `mcp/mcp-proxy.json`:

```json
{
  "version": "1.0",
  "mcpServers": {
    "my-first-server": {
      "enabled": true,
      "description": "My first external MCP server",
      "type": "stdio",
      "command": "/path/to/your/mcp-server",
      "settings": {
        "tool_prefix": "ext_",
        "timeout": 30
      }
    }
  },
  "global_settings": {
    "discovery_interval": 300,
    "enable_timeline_logging": true
  }
}
```

### Step 2: Start the MCP Interface

```bash
cd mcp
python -m app.main
```

### Step 3: Verify Connection

```bash
# Check if your external tools are discovered
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8001/tools/list | grep "ext_"
```

### Step 4: Use External Tools

```bash
# Call an external tool
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name": "ext_your_tool", "arguments": {"param": "value"}}' \
     http://localhost:8001/tools/call
```

## Common Server Types

### Stdio Server (Local Process)
```json
{
  "local-tool": {
    "enabled": true,
    "type": "stdio",
    "command": "/usr/local/bin/my-tool",
    "args": ["--config", "config.json"]
  }
}
```

### HTTP Server (Remote Service)
```json
{
  "remote-api": {
    "enabled": true,
    "type": "streamable-http",
    "url": "https://api.example.com/mcp",
    "headers": {
      "Authorization": "Bearer your-token"
    }
  }
}
```

### SSE Server (Event Stream)
```json
{
  "event-service": {
    "enabled": true,
    "type": "sse",
    "url": "https://events.example.com/mcp/sse",
    "headers": {
      "X-API-Key": "your-key"
    }
  }
}
```

## Configuration Options

### Essential Settings
```json
{
  "settings": {
    "timeout": 30,              // Tool call timeout (seconds)
    "retry_attempts": 3,        // Retry failed connections
    "tool_prefix": "prefix_",   // Prefix for tool names
    "health_check_interval": 60 // Health check frequency
  }
}
```

### Global Settings
```json
{
  "global_settings": {
    "discovery_interval": 300,      // Tool discovery frequency
    "max_concurrent_calls": 10,     // Max simultaneous calls
    "enable_timeline_logging": true, // Log to timeline
    "log_level": "INFO"             // Logging level
  }
}
```

## Troubleshooting

### Server Won't Connect
1. Check server configuration in `mcp-proxy.json`
2. Verify server is running and accessible
3. Check logs: `tail -f logs/mcp-proxy.log`
4. Test manually: `curl -v http://your-server/health`

### Tools Not Appearing
1. Check if server is enabled: `"enabled": true`
2. Verify tool discovery: Look for discovery events in timeline
3. Check for naming conflicts (use prefixes)
4. Force refresh: `curl -X POST http://localhost:8001/admin/refresh-tools`

### Tool Calls Failing
1. Check parameter format matches tool schema
2. Verify server authentication (headers, tokens)
3. Check timeout settings
4. Monitor error logs for specific error messages

## Best Practices

### Security
- Use HTTPS for remote servers
- Store credentials securely
- Set appropriate timeouts
- Monitor access logs

### Performance
- Use connection pooling for high-traffic servers
- Set reasonable discovery intervals
- Limit concurrent calls
- Cache tool schemas when possible

### Reliability
- Configure retry attempts
- Set health check intervals
- Monitor server availability
- Have fallback strategies

## Example Configurations

### Weather Service
```json
{
  "weather-api": {
    "enabled": true,
    "description": "Weather information service",
    "type": "streamable-http",
    "url": "https://weather-mcp.example.com/mcp",
    "headers": {
      "X-API-Key": "weather-api-key"
    },
    "settings": {
      "tool_prefix": "weather_",
      "timeout": 15,
      "retry_attempts": 2
    }
  }
}
```

### Database Tools
```json
{
  "db-tools": {
    "enabled": true,
    "description": "Database query tools",
    "type": "stdio",
    "command": "/opt/db-tools/mcp-server",
    "env": {
      "DB_CONNECTION": "postgresql://user:pass@localhost/db"
    },
    "settings": {
      "tool_prefix": "db_",
      "timeout": 60,
      "retry_attempts": 1
    }
  }
}
```

### File Processing
```json
{
  "file-processor": {
    "enabled": true,
    "description": "Document processing service",
    "type": "sse",
    "url": "https://docs.example.com/mcp/events",
    "headers": {
      "Authorization": "Bearer doc-token"
    },
    "settings": {
      "tool_prefix": "doc_",
      "timeout": 120,
      "health_check_interval": 30
    }
  }
}
```

## Monitoring

### Check Engine Status
```bash
# Get proxy engine statistics
curl http://localhost:8001/admin/proxy-stats

# Check server connections
curl http://localhost:8001/admin/server-status

# View timeline events
curl http://localhost:8001/timeline | grep -i proxy
```

### Log Analysis
```bash
# Monitor proxy operations
tail -f logs/mcp-proxy.log | grep -E "(ERROR|WARN)"

# Check discovery events
grep "discovery" logs/mcp-proxy.log

# Monitor tool calls
grep "proxy_call" logs/mcp-proxy.log
```

## Next Steps

1. **Read Full Documentation**: See `docs/mcp/mcp-proxy.md` for complete details
2. **Explore Examples**: Check `mcp/tests/` for working examples
3. **Join Community**: Get help and share configurations
4. **Contribute**: Submit improvements and new features

## Support

- **Documentation**: `docs/mcp/`
- **Examples**: `mcp/tests/proxy/`
- **Logs**: `logs/mcp-proxy.log`
- **Timeline**: View proxy events in IntentVerse timeline

Happy proxying! 🚀