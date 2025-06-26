# API Overview

## Architecture

IntentVerse provides a RESTful API built with FastAPI that serves multiple purposes:

1. **Web UI Backend**: Powers the React-based dashboard
2. **MCP Interface**: Enables AI model integration via Model Context Protocol
3. **Content Management**: Handles content pack import/export
4. **User Management**: Provides authentication and authorization

## Base URL

```
http://localhost:8000
```

## API Versioning

The API uses URL-based versioning with the current version being `v1`:

```
/api/v1/{endpoint}
```

**Exception**: Authentication endpoints use `/auth/{endpoint}` without the version prefix.

## Request/Response Format

### Content Type
All requests and responses use JSON format:
```
Content-Type: application/json
```

### Request Structure
```json
{
  "parameter1": "value1",
  "parameter2": "value2"
}
```

### Response Structure
```json
{
  "status": "success|error",
  "data": {...},
  "message": "Optional message"
}
```

## Authentication

IntentVerse supports two authentication methods:

### 1. JWT Token Authentication (Users)
```http
Authorization: Bearer YOUR_JWT_TOKEN_HERE
```

### 2. API Key Authentication (Services)
```http
X-API-Key: your-service-api-key
```

## HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

## Rate Limiting

Currently, no rate limiting is implemented. This may be added in future versions.

## CORS Policy

CORS is enabled for:
- **Origin**: `http://localhost:3000` (Web UI)
- **Methods**: All HTTP methods
- **Headers**: All headers
- **Credentials**: Enabled

## API Categories

### Core API (`/api/v1`)
- Module state management
- UI layout configuration
- System information

### MCP Interface (`/api/v1/tools`, `/api/v1/execute`)
- Tool discovery and execution
- AI model integration
- Dynamic function calling

### Content Packs (`/api/v1/content-packs`)
- Import/export content packs
- Preview and validation
- Pack management

### Authentication (`/auth`)
- User login/logout
- User management
- Group and permission management

### Timeline (`/events`)
- Event logging
- Timeline retrieval
- System monitoring

### Debug (`/api/v1/debug`)
- Development utilities
- System diagnostics
- Module loader state

## Data Types

### Common Types
- **String**: Text data
- **Integer**: Whole numbers
- **Boolean**: true/false values
- **DateTime**: ISO 8601 format (`2024-01-01T12:00:00Z`)
- **Object**: JSON objects
- **Array**: JSON arrays

### Custom Types
- **ModuleState**: Dynamic object representing module data
- **UISchema**: Object defining UI component configuration
- **ContentPack**: Object containing module states and metadata
- **ToolManifest**: Object describing available tools and parameters

## Pagination

For endpoints that return large datasets, pagination is implemented using:

```json
{
  "limit": 50,
  "offset": 0,
  "total": 150,
  "data": [...]
}
```

## Filtering and Sorting

Many endpoints support query parameters for filtering and sorting:

```
GET /api/v1/events?event_type=tool_execution&limit=10
```

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Error description",
  "status_code": 400,
  "error_type": "validation_error"
}
```

See [Error Handling](error-handling.md) for detailed error codes and troubleshooting.

## Security Considerations

1. **HTTPS**: Use HTTPS in production
2. **Token Expiration**: JWT tokens have expiration times
3. **API Key Security**: Keep service API keys secure
4. **Input Validation**: All inputs are validated
5. **Audit Logging**: All operations are logged

## Interactive Documentation

FastAPI automatically generates interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- Browse all available endpoints
- Test API calls directly
- View request/response schemas
- Download OpenAPI specification

## SDK and Client Libraries

Currently, no official SDKs are provided. The API is designed to be easily consumed by any HTTP client.

### Recommended HTTP Clients
- **JavaScript**: axios, fetch
- **Python**: requests, httpx
- **cURL**: Command-line testing
- **Postman**: API testing and development

## Performance Considerations

- **Response Times**: Most endpoints respond within 100ms
- **Concurrent Requests**: Server handles multiple concurrent requests
- **Caching**: Some responses may be cached
- **Database**: SQLite backend for development, consider PostgreSQL for production

## Monitoring and Observability

- **Logging**: Structured JSON logging
- **Audit Trail**: Complete audit log of all operations
- **Health Checks**: Basic health check at root endpoint
- **Metrics**: Consider adding metrics collection for production