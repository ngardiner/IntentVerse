# MCP Interface Running Modes

The IntentVerse MCP Interface supports two distinct running modes to accommodate different client use cases and deployment scenarios.

## Overview

The MCP Interface can operate in:

1. **Streamable HTTP Mode** - A persistent network server for remote connections
2. **Stdio Mode** - An ephemeral process for local, single-session interactions

Both modes provide identical functionality but differ in their connection mechanism and lifecycle.

## Mode Comparison

| Feature | Streamable HTTP Mode | Stdio Mode |
|---------|---------------------|------------|
| **Connection Type** | HTTP over network | stdin/stdout pipes |
| **Lifecycle** | Long-running server | Single-session process |
| **Multiple Clients** | ✅ Supports concurrent connections | ❌ One client per process |
| **Network Required** | ✅ Requires network access | ❌ Local process communication |
| **Resource Usage** | Higher (persistent server) | Lower (on-demand) |
| **Use Cases** | Remote agents, web-based AI | Local AI tools, Claude Desktop |
| **Default Mode** | ✅ Yes | ❌ Requires `--stdio` flag |

## Streamable HTTP Mode

### Description
The default mode where the MCP Interface runs as a persistent HTTP server, accepting connections from multiple clients over the network.

### When to Use
- Remote AI agents or services
- Web-based AI applications
- Multiple concurrent AI sessions
- Development and testing environments
- Production deployments

### Starting HTTP Mode

#### With Docker Compose (Recommended)
```bash
# Start all services including MCP in HTTP mode
docker compose up --build

# MCP server will be available at http://localhost:8001
```

#### With Docker (Standalone)
```bash
# Build the MCP image
docker build -t intentverse-mcp ./mcp

# Run in HTTP mode (default)
docker run -p 8001:8001 --network intentverse-net intentverse-mcp

# Or explicitly specify HTTP mode
docker run -p 8001:8001 --network intentverse-net intentverse-mcp python -m app.main
```

#### Local Development
```bash
cd mcp

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CORE_API_URL=http://localhost:8000
export SERVICE_API_KEY=dev-service-key-12345

# Start in HTTP mode (default)
python -m app.main
```

#### Using the Development Script
```bash
# Starts all services including MCP in HTTP mode
./start-local-dev.sh
```

### Connecting to HTTP Mode

#### From Python (using httpx)
```python
import httpx
import json

# Connect to the MCP server
async with httpx.AsyncClient() as client:
    # Get available tools
    response = await client.post(
        "http://localhost:8001/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
    )
    tools = response.json()
    print(f"Available tools: {tools}")
```

#### Health Check
```bash
# Verify the server is running
curl http://localhost:8001/

# Should return server information
```

## Stdio Mode

### Description
An ephemeral mode where the MCP Interface communicates via stdin/stdout pipes, typically used for single-session, local AI interactions.

### When to Use
- Claude Desktop integration
- Local AI development tools
- Single-session interactions
- Resource-constrained environments
- Secure, isolated AI sessions

### Starting Stdio Mode

#### With Docker (Recommended for Claude Desktop)
```bash
# Interactive stdio mode
docker run -i --rm --network intentverse-net intentverse-mcp --stdio

# For Claude Desktop configuration
docker run -i --rm --network intentverse-net intentverse-mcp python -m app.main --stdio
```

#### Local Development
```bash
cd mcp

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Set environment variables
export CORE_API_URL=http://localhost:8000
export SERVICE_API_KEY=dev-service-key-12345

# Start in stdio mode
python -m app.main --stdio
```

### Claude Desktop Integration

Add this configuration to your Claude Desktop settings:

```json
{
  "mcpServers": {
    "intentverse": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", 
        "--network", "intentverse-net", 
        "intentverse-mcp", 
        "python", "-m", "app.main", "--stdio"
      ]
    }
  }
}
```

**Prerequisites:**
1. IntentVerse must be running (`docker compose up`)
2. Docker images must be built (`docker compose build`)
3. The `intentverse-net` network must exist

### Alternative Claude Desktop Configuration (Local)

If running IntentVerse locally without Docker:

```json
{
  "mcpServers": {
    "intentverse": {
      "command": "python",
      "args": ["-m", "app.main", "--stdio"],
      "cwd": "/path/to/IntentVerse/mcp",
      "env": {
        "CORE_API_URL": "http://localhost:8000",
        "SERVICE_API_KEY": "dev-service-key-12345"
      }
    }
  }
}
```

### Testing Stdio Mode

#### Manual Testing
```bash
# Start stdio mode
cd mcp && python -m app.main --stdio

# Send MCP messages via stdin (JSON-RPC format)
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | python -m app.main --stdio
```

#### Programmatic Testing
```python
import subprocess
import json

# Start stdio process
process = subprocess.Popen(
    ["python", "-m", "app.main", "--stdio"],
    cwd="mcp",
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Send MCP request
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
}

stdout, stderr = process.communicate(json.dumps(request))
response = json.loads(stdout)
print(f"Tools: {response}")
```

## Architecture Considerations

### Shared Core Connection
Both modes connect to the same Core service, ensuring:
- Consistent tool functionality
- Shared state and data
- Unified timeline logging
- Same authentication and security

### Resource Management

#### HTTP Mode
- Single persistent process
- Shared resources across connections
- Connection pooling to Core service
- Higher memory footprint

#### Stdio Mode
- New process per session
- Isolated resources per session
- Individual Core connections
- Lower per-session overhead

### Timeline Logging
Both modes log activities to the Core timeline:
- Tool executions
- Connection events
- Error conditions
- Performance metrics

## Troubleshooting

### Common Issues

#### "Connection Refused" Errors
```bash
# Ensure Core service is running
curl http://localhost:8000/

# Check network connectivity
docker network ls | grep intentverse
```

#### Stdio Mode Not Responding
```bash
# Check if process started correctly
python -m app.main --stdio &
ps aux | grep "app.main"

# Verify environment variables
echo $CORE_API_URL
echo $SERVICE_API_KEY
```

#### Docker Network Issues
```bash
# Recreate the network
docker compose down
docker compose up --build

# Or manually create network
docker network create intentverse-net
```

### Debug Logging

Enable debug logging for troubleshooting:

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Run with verbose output
python -m app.main --stdio
```

### Health Checks

#### HTTP Mode
```bash
# Basic connectivity
curl -f http://localhost:8001/

# Tool availability
curl -X POST http://localhost:8001/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

#### Stdio Mode
```bash
# Quick test
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | \
  timeout 10 python -m app.main --stdio
```

## Performance Considerations

### HTTP Mode
- **Startup Time:** ~2-3 seconds
- **Memory Usage:** ~50-100MB persistent
- **Concurrent Connections:** 100+ supported
- **Response Time:** <50ms typical

### Stdio Mode
- **Startup Time:** ~1-2 seconds per session
- **Memory Usage:** ~30-50MB per session
- **Concurrent Sessions:** Limited by system resources
- **Response Time:** <30ms typical

## Security Considerations

### HTTP Mode
- Network exposure requires firewall configuration
- Authentication via API keys
- HTTPS recommended for production
- Rate limiting may be needed

### Stdio Mode
- Local process isolation
- No network exposure
- Inherits parent process permissions
- Secure for single-user environments

## Best Practices

### Development
- Use HTTP mode for development and testing
- Use stdio mode for Claude Desktop integration
- Monitor logs for both modes
- Test both modes before deployment

### Production
- Use HTTP mode for remote AI services
- Use stdio mode for local AI tools
- Implement proper monitoring
- Configure appropriate resource limits

### Integration
- Always ensure Core service is running first
- Use health checks before connecting
- Implement retry logic for connection failures
- Monitor timeline logs for debugging