# Testing MCP Modes

This document describes how to test the MCP Interface dual-mode functionality to ensure both HTTP and stdio modes work correctly.

## Overview

The IntentVerse MCP Interface supports two running modes:
- **HTTP Mode**: Persistent server for multiple concurrent connections
- **Stdio Mode**: Ephemeral process for single-session interactions

Testing both modes ensures that:
1. Both modes can connect to the Core service
2. Both modes expose the same tools
3. Both modes can execute tools correctly
4. Timeline logging works in both modes
5. Error handling is graceful in both modes

## Test Types

### 1. Standalone Test Script

A simple, self-contained test script that doesn't require pytest infrastructure.

**Location**: `test_mcp_modes.py` (in project root)

**Usage**:
```bash
# Basic test (assumes Core at localhost:8000)
python test_mcp_modes.py

# Test with custom Core URL
python test_mcp_modes.py --core-url http://localhost:8000

# Test with Docker Core service
python test_mcp_modes.py --core-url http://core:8000
```

**What it tests**:
- Core service connectivity
- HTTP mode startup and tool listing
- HTTP mode tool execution
- Stdio mode tool listing
- Stdio mode tool execution

### 2. Pytest Integration Tests

Comprehensive pytest-based integration tests with detailed error handling.

**Location**: `mcp/tests/test_mcp_modes_integration.py`

**Usage**:
```bash
# Run all mode tests
cd mcp
python -m pytest tests/test_mcp_modes_integration.py -v

# Run only mode-specific tests
python -m pytest -m modes -v

# Run with custom Core URL
CORE_API_URL=http://localhost:8000 python -m pytest tests/test_mcp_modes_integration.py -v
```

**What it tests**:
- HTTP mode startup and health checks
- Stdio mode communication
- Tool consistency between modes
- Tool execution in both modes
- Timeline logging functionality
- Error handling when Core service is unavailable
- Graceful degradation scenarios

### 3. Test Runner Script

Convenient script to run mode tests with options.

**Location**: `mcp/run_mode_tests.py`

**Usage**:
```bash
cd mcp

# Run pytest-based tests
python run_mode_tests.py

# Run standalone tests
python run_mode_tests.py --standalone

# Custom Core URL
python run_mode_tests.py --core-url http://localhost:8000
```

## Prerequisites

### Required Services
1. **IntentVerse Core service** must be running
2. **Network connectivity** between test environment and Core service

### Required Dependencies
```bash
pip install pytest httpx
```

### Environment Setup

#### Docker Environment
```bash
# Start Core service
docker compose up core

# Run tests
python test_mcp_modes.py --core-url http://localhost:8000
```

#### Local Development Environment
```bash
# Start Core service
cd core
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal, run tests
python test_mcp_modes.py
```

## Test Scenarios

### 1. Basic Functionality Tests

#### HTTP Mode Tests
- ✅ Server starts without errors
- ✅ Server responds to health checks
- ✅ Server accepts MCP requests
- ✅ `tools/list` returns expected tools
- ✅ Tool execution works correctly
- ✅ Timeline logging functions

#### Stdio Mode Tests
- ✅ Process starts and accepts input
- ✅ Process responds with valid JSON-RPC
- ✅ `tools/list` returns expected tools
- ✅ Tool execution works correctly
- ✅ Process exits cleanly
- ✅ Timeline logging functions

### 2. Consistency Tests
- ✅ Both modes expose identical tool sets
- ✅ Tool execution results are consistent
- ✅ Both modes connect to same Core service
- ✅ Timeline entries are created in both modes

### 3. Error Handling Tests
- ✅ Graceful handling when Core service unavailable
- ✅ Proper error responses for invalid requests
- ✅ Clean process termination on errors
- ✅ Meaningful error messages

## Running Tests in CI/CD

### GitHub Actions Example
```yaml
name: MCP Mode Tests
on: [push, pull_request]

jobs:
  test-mcp-modes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r core/requirements.txt
          pip install -r mcp/requirements.txt
          pip install pytest httpx
      
      - name: Start Core service
        run: |
          cd core
          uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          sleep 5
      
      - name: Run MCP mode tests
        run: |
          python test_mcp_modes.py
          cd mcp && python -m pytest tests/test_mcp_modes_integration.py -v
```

### Docker Compose Testing
```yaml
# docker-compose.test.yml
version: '3.8'
services:
  core:
    build: ./core
    ports:
      - "8000:8000"
    environment:
      - SERVICE_API_KEY=test-key
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 5s
      timeout: 5s
      retries: 10

  mcp-mode-tests:
    build: ./mcp
    depends_on:
      core:
        condition: service_healthy
    environment:
      - CORE_API_URL=http://core:8000
      - SERVICE_API_KEY=test-key
    command: python -m pytest tests/test_mcp_modes_integration.py -v
```

## Troubleshooting Test Issues

### Common Problems

#### "Core service not available"
```bash
# Check if Core is running
curl http://localhost:8000/

# Check Core logs
docker compose logs core

# Restart Core service
docker compose restart core
```

#### "Connection refused" in tests
```bash
# Check port availability
lsof -i :8000  # Core service
lsof -i :8001  # MCP HTTP mode

# Check firewall settings
sudo ufw status

# Check Docker network
docker network ls
```

#### "Module not found" errors
```bash
# Install test dependencies
pip install pytest httpx

# Check Python path
echo $PYTHONPATH

# Install in development mode
cd mcp && pip install -e .
```

#### Stdio mode hangs
```bash
# Check for deadlocks in stdio communication
timeout 10 python test_mcp_modes.py

# Enable debug logging
LOG_LEVEL=DEBUG python test_mcp_modes.py

# Check for zombie processes
ps aux | grep python
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Set debug environment
export LOG_LEVEL=DEBUG
export CORE_API_URL=http://localhost:8000

# Run with verbose output
python test_mcp_modes.py

# Or with pytest
cd mcp && python -m pytest tests/test_mcp_modes_integration.py -v -s
```

### Manual Testing

For manual verification of modes:

#### HTTP Mode
```bash
# Start HTTP mode
cd mcp && python -m app.main

# In another terminal, test
curl -X POST http://localhost:8001/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

#### Stdio Mode
```bash
# Test stdio mode
cd mcp
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | python -m app.main --stdio
```

## Test Coverage

The test suite covers:

### Functional Coverage
- ✅ Mode selection (--stdio flag)
- ✅ Core service connectivity
- ✅ Tool discovery and listing
- ✅ Tool execution
- ✅ Timeline integration
- ✅ Error handling
- ✅ Process lifecycle

### Integration Coverage
- ✅ MCP ↔ Core communication
- ✅ FastMCP framework integration
- ✅ JSON-RPC protocol compliance
- ✅ Environment variable handling
- ✅ Network connectivity
- ✅ Process management

### Edge Cases
- ✅ Core service unavailable
- ✅ Invalid MCP requests
- ✅ Network timeouts
- ✅ Process termination
- ✅ Resource cleanup

## Performance Benchmarks

Expected performance characteristics:

### HTTP Mode
- **Startup Time**: < 3 seconds
- **Response Time**: < 50ms for tool/list
- **Tool Execution**: < 500ms for simple tools
- **Memory Usage**: ~50-100MB

### Stdio Mode
- **Startup Time**: < 2 seconds
- **Response Time**: < 30ms for tool/list
- **Tool Execution**: < 400ms for simple tools
- **Memory Usage**: ~30-50MB per session

### Performance Testing
```bash
# Time startup
time python -m app.main --stdio < /dev/null

# Measure tool execution
time echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | python -m app.main --stdio
```

## Best Practices

### Test Development
1. **Always test both modes** for any new functionality
2. **Use consistent test data** across modes
3. **Test error conditions** as well as success paths
4. **Verify cleanup** of resources and processes
5. **Mock external dependencies** when possible

### Test Execution
1. **Run tests in clean environment** (fresh containers/venvs)
2. **Verify Core service health** before running tests
3. **Check for resource leaks** after test runs
4. **Use appropriate timeouts** for async operations
5. **Log test results** for debugging

### Continuous Integration
1. **Run mode tests on every commit**
2. **Test against multiple Python versions**
3. **Include performance regression tests**
4. **Test in Docker and local environments**
5. **Fail fast on critical mode functionality**